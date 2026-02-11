"""Explainability Agent - generates customer and audit explanations for fraud decisions.

This module implements Phase 5 of the fraud detection pipeline:
- Generates customer-facing explanation (simple, empathetic, no jargon)
- Generates audit explanation (technical, detailed, with citations)
- Uses single LLM call for efficiency
- Falls back to deterministic templates if LLM fails
"""

import asyncio
import json
import re
from typing import Optional

from langchain_ollama import ChatOllama

from ..dependencies import get_llm
from ..models import (
    AggregatedEvidence,
    DebateArguments,
    ExplanationResult,
    FraudDecision,
    OrchestratorState,
    PolicyMatchResult,
)
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

# ============================================================================
# PROMPT TEMPLATE (Spanish)
# ============================================================================

EXPLAINABILITY_PROMPT = """Eres un experto en comunicación de decisiones de fraude financiero. Tu tarea es generar DOS explicaciones para la misma decisión: una para el cliente y otra para auditoría interna.

**CONTEXTO DE LA DECISIÓN:**

**Transacción:**
- ID: {transaction_id}
- Decisión final: {decision}
- Confianza: {confidence:.2f}

**Señales clave detectadas:**
{signals}

**Políticas aplicadas:**
{policies}

**Evidencia consolidada:**
- Puntaje de riesgo compuesto: {composite_risk_score}/100
- Categoría de riesgo: {risk_category}

**Debate adversarial:**
- Argumento pro-fraude (confianza {pro_fraud_confidence:.2f}):
  {pro_fraud_argument}
- Argumento pro-cliente (confianza {pro_customer_confidence:.2f}):
  {pro_customer_argument}

**INSTRUCCIONES:**

Genera DOS versiones de la explicación:

**1. EXPLICACIÓN PARA EL CLIENTE:**
   - Lenguaje simple y empático
   - Sin jerga técnica ni detalles internos
   - Explica qué pasó y qué debe hacer el cliente
   - Transmite seguridad y profesionalismo
   - NUNCA mencionar: políticas internas, algoritmos, scores, debates
   - 2-3 oraciones máximo

**2. EXPLICACIÓN PARA AUDITORÍA:**
   - Técnica y detallada
   - Incluye todas las citaciones (policy_ids, señales, scores)
   - Documenta el razonamiento del debate
   - Lista los agentes que participaron en el análisis
   - Suficiente detalle para reconstruir la decisión
   - 4-6 oraciones

**3. FACTORES CLAVE:**
   - Lista 2-4 factores principales que influyeron en la decisión
   - Usar términos descriptivos (ej: "monto elevado", "horario inusual")

**4. ACCIONES RECOMENDADAS:**
   - Para el cliente o el banco
   - Específicas y accionables
   - 1-3 acciones

**FORMATO DE SALIDA (JSON estricto):**
{{
  "customer_explanation": "Su transacción requiere verificación adicional debido a un patrón de actividad inusual. Le enviaremos un código de confirmación por SMS.",
  "audit_explanation": "Transacción T-1001 (S/1800, 03:15 AM) analizada por 8 agentes. Riesgo compuesto: 68.5/100 (high). Señales: monto 3.6x promedio, horario nocturno, dispositivo conocido. Políticas aplicadas: FP-01 (relevancia 0.92). Debate: pro-fraude 0.78 vs pro-cliente 0.55. Decisión: CHALLENGE (confianza 0.72). Sin amenazas externas detectadas.",
  "key_factors": ["monto_elevado_3.6x", "horario_nocturno", "politica_FP-01"],
  "recommended_actions": ["verificar_via_sms", "contactar_cliente", "monitorear_proximas_24h"]
}}

**IMPORTANTE:**
- Responde SOLO con el JSON, sin texto adicional
- La explicación al cliente debe ser amigable y clara
- La explicación de auditoría debe ser completa y técnica
- Adapta el tono según la decisión ({decision})
"""

# ============================================================================
# PARSING HELPER
# ============================================================================


def _parse_explanation_response(response_text: str) -> tuple[Optional[str], Optional[str], list[str], list[str]]:
    """Parse LLM response to extract explanations, factors, and actions.

    Two-stage parsing strategy:
    1. JSON parsing: Look for JSON in markdown code blocks or raw JSON
    2. Regex fallback: Extract fields via regex if JSON parsing fails

    Args:
        response_text: Raw text response from LLM

    Returns:
        Tuple of (customer_explanation, audit_explanation, key_factors, recommended_actions)
        Returns (None, None, [], []) if parsing fails completely

    Note:
        - Logs which parsing method succeeded
    """
    # ========== STAGE 1: JSON PARSING ==========
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*"customer_explanation".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        # Extract fields
        customer_explanation = data.get("customer_explanation")
        audit_explanation = data.get("audit_explanation")
        key_factors = data.get("key_factors", [])
        recommended_actions = data.get("recommended_actions", [])

        # Validate required fields
        if customer_explanation and audit_explanation:
            # Ensure lists
            if not isinstance(key_factors, list):
                key_factors = []
            if not isinstance(recommended_actions, list):
                recommended_actions = []

            logger.info(
                "explanation_response_parsed_json",
                factors_count=len(key_factors),
                actions_count=len(recommended_actions),
            )
            return customer_explanation, audit_explanation, key_factors, recommended_actions

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("json_parse_failed_explanation", error=str(e), attempting_regex=True)

    # ========== STAGE 2: REGEX FALLBACK ==========
    try:
        # Extract customer_explanation: "customer_explanation": "..."
        customer_match = re.search(
            r'"?customer_explanation"?\s*:\s*"([^"]+)"',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        customer_explanation = customer_match.group(1) if customer_match else None

        # Extract audit_explanation: "audit_explanation": "..."
        audit_match = re.search(
            r'"?audit_explanation"?\s*:\s*"([^"]+)"',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        audit_explanation = audit_match.group(1) if audit_match else None

        # Extract key_factors: ["factor1", "factor2", ...]
        factors_match = re.search(
            r'"?key_factors"?\s*:\s*\[(.*?)\]',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        key_factors = []
        if factors_match:
            # Extract quoted strings from the list
            factors = re.findall(r'"([^"]+)"', factors_match.group(1))
            key_factors = factors

        # Extract recommended_actions: ["action1", "action2", ...]
        actions_match = re.search(
            r'"?recommended_actions"?\s*:\s*\[(.*?)\]',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        recommended_actions = []
        if actions_match:
            # Extract quoted strings from the list
            actions = re.findall(r'"([^"]+)"', actions_match.group(1))
            recommended_actions = actions

        if customer_explanation and audit_explanation:
            logger.info(
                "explanation_response_parsed_regex",
                factors_count=len(key_factors),
                actions_count=len(recommended_actions),
            )
            return customer_explanation, audit_explanation, key_factors, recommended_actions

    except Exception as e:
        logger.error("regex_parse_failed_explanation", error=str(e))

    # ========== PARSING FAILED ==========
    logger.error("explanation_response_parse_failed_completely")
    return None, None, [], []


# ============================================================================
# LLM CALL HELPER
# ============================================================================


async def _call_llm_for_explanation(
    llm: ChatOllama,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: Optional[PolicyMatchResult],
    debate: DebateArguments,
) -> tuple[Optional[str], Optional[str], list[str], list[str]]:
    """Call LLM for explanation generation.

    Args:
        llm: ChatOllama instance
        decision: FraudDecision from Phase 4
        evidence: AggregatedEvidence from Phase 2
        policy_matches: PolicyMatchResult from Phase 1
        debate: DebateArguments from Phase 3

    Returns:
        Tuple of (customer_explanation, audit_explanation, key_factors, recommended_actions)
        Returns (None, None, [], []) if LLM call fails

    Note:
        - Includes 30-second timeout
        - Delegates parsing to _parse_explanation_response()
    """
    # Build signals summary
    signals_text = "\n- ".join(decision.signals) if decision.signals else "ninguna"

    # Build policies summary
    if policy_matches and policy_matches.matches:
        policies_text = "\n".join([
            f"- {match.policy_id}: {match.description} (relevancia: {match.relevance_score:.2f})"
            for match in policy_matches.matches
        ])
    else:
        policies_text = "Ninguna política específica aplicada"

    # Format prompt
    prompt = EXPLAINABILITY_PROMPT.format(
        transaction_id=decision.transaction_id,
        decision=decision.decision,
        confidence=decision.confidence,
        signals=signals_text,
        policies=policies_text,
        composite_risk_score=evidence.composite_risk_score,
        risk_category=evidence.risk_category,
        pro_fraud_confidence=debate.pro_fraud_confidence,
        pro_fraud_argument=debate.pro_fraud_argument,
        pro_customer_confidence=debate.pro_customer_confidence,
        pro_customer_argument=debate.pro_customer_argument,
    )

    try:
        # Call LLM with timeout
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=30.0)
        response_text = response.content

        # Parse response
        return _parse_explanation_response(response_text)

    except asyncio.TimeoutError:
        logger.error("llm_timeout_explanation", timeout_seconds=30)
        return None, None, [], []
    except Exception as e:
        logger.error("llm_call_failed_explanation", error=str(e))
        return None, None, [], []


# ============================================================================
# DETERMINISTIC FALLBACK TEMPLATES
# ============================================================================


def _generate_fallback_explanations(
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: Optional[PolicyMatchResult],
    debate: DebateArguments,
) -> tuple[str, str]:
    """Generate deterministic explanations when LLM fails.

    Uses decision-type-specific templates.

    Args:
        decision: FraudDecision from Phase 4
        evidence: AggregatedEvidence
        policy_matches: PolicyMatchResult
        debate: DebateArguments

    Returns:
        Tuple of (customer_explanation, audit_explanation)
    """
    decision_type = decision.decision
    transaction_id = decision.transaction_id
    confidence = decision.confidence
    composite_score = evidence.composite_risk_score
    risk_category = evidence.risk_category

    # Decision-specific customer explanations
    customer_templates = {
        "APPROVE": (
            "Su transacción ha sido procesada exitosamente. "
            "No se detectaron problemas de seguridad."
        ),
        "CHALLENGE": (
            "Por seguridad, necesitamos verificar esta transacción. "
            "Le enviaremos un código de verificación. "
            "Esto es un procedimiento estándar para proteger su cuenta."
        ),
        "BLOCK": (
            "Por su seguridad, hemos bloqueado esta transacción debido a patrones inusuales. "
            "Si usted autorizó esta transacción, por favor contáctenos de inmediato al "
            "número en el reverso de su tarjeta."
        ),
        "ESCALATE_TO_HUMAN": (
            "Su transacción está siendo revisada por nuestro equipo de seguridad. "
            "Le contactaremos dentro de las próximas 24 horas. "
            "Gracias por su paciencia."
        ),
    }

    # Build audit explanation
    policy_summary = "sin políticas" if not policy_matches or not policy_matches.matches else \
        f"{len(policy_matches.matches)} políticas aplicadas"

    audit_explanation = (
        f"Transacción {transaction_id}: Decisión {decision_type} (confianza {confidence:.2f}). "
        f"Riesgo compuesto: {composite_score:.1f}/100 ({risk_category}). "
        f"Debate: pro-fraude {debate.pro_fraud_confidence:.2f} vs "
        f"pro-cliente {debate.pro_customer_confidence:.2f}. "
        f"Señales: {len(decision.signals)} detectadas. "
        f"{policy_summary}. "
        f"Explicación generada por fallback determinístico."
    )

    customer_explanation = customer_templates.get(
        decision_type,
        "Su transacción está siendo procesada. Le mantendremos informado.",
    )

    logger.info(
        "fallback_explanations_generated",
        decision=decision_type,
        has_policies=bool(policy_matches and policy_matches.matches),
    )

    return customer_explanation, audit_explanation


# ============================================================================
# EXPLANATION ENHANCEMENT
# ============================================================================


def _enhance_customer_explanation(
    customer_explanation: str,
    decision_type: str,
) -> str:
    """Enhance customer explanation with safety checks.

    Ensures customer explanation:
    - Does not reveal internal system details
    - Is empathetic and professional
    - Provides actionable guidance

    Args:
        customer_explanation: Raw customer explanation
        decision_type: Decision type

    Returns:
        Enhanced customer explanation
    """
    # Keywords that should NOT appear in customer explanations
    forbidden_keywords = [
        "score",
        "puntaje",
        "algoritmo",
        "modelo",
        "agente",
        "política",
        "policy",
        "FP-",
        "debate",
        "confianza:",
        "confidence",
        "LLM",
        "threshold",
    ]

    # Check for forbidden keywords (case-insensitive)
    explanation_lower = customer_explanation.lower()
    for keyword in forbidden_keywords:
        if keyword.lower() in explanation_lower:
            logger.warning(
                "customer_explanation_contains_internal_details",
                keyword=keyword,
                using_safe_template=True,
            )
            # Fall back to safe template
            return _get_safe_customer_template(decision_type)

    # Explanation is safe, return as-is
    return customer_explanation


def _get_safe_customer_template(decision_type: str) -> str:
    """Get safe customer explanation template.

    Args:
        decision_type: Decision type

    Returns:
        Safe customer explanation
    """
    safe_templates = {
        "APPROVE": "Su transacción ha sido aprobada. Todo está en orden.",
        "CHALLENGE": (
            "Por seguridad, necesitamos verificar esta transacción. "
            "Le contactaremos pronto."
        ),
        "BLOCK": (
            "Por su seguridad, hemos bloqueado esta transacción. "
            "Si usted la autorizó, contáctenos de inmediato."
        ),
        "ESCALATE_TO_HUMAN": (
            "Su transacción está en revisión. "
            "Nuestro equipo la analizará y le contactaremos pronto."
        ),
    }

    return safe_templates.get(
        decision_type,
        "Su transacción está siendo procesada. Le mantendremos informado.",
    )


def _enhance_audit_explanation(
    audit_explanation: str,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: Optional[PolicyMatchResult],
) -> str:
    """Enhance audit explanation with required details.

    Ensures audit explanation includes:
    - Transaction ID
    - Decision type and confidence
    - Risk score and category
    - Policy IDs
    - Key signals

    Args:
        audit_explanation: Raw audit explanation
        decision: FraudDecision
        evidence: AggregatedEvidence
        policy_matches: PolicyMatchResult

    Returns:
        Enhanced audit explanation
    """
    # Check if explanation already includes key details
    required_elements = {
        "transaction_id": decision.transaction_id in audit_explanation,
        "decision": decision.decision in audit_explanation,
        "confidence": str(decision.confidence) in audit_explanation or f"{decision.confidence:.2f}" in audit_explanation,
        "risk_score": str(evidence.composite_risk_score) in audit_explanation,
    }

    # Collect missing parts
    missing_parts = []

    if not required_elements["transaction_id"]:
        missing_parts.append(f"ID: {decision.transaction_id}")

    if not required_elements["decision"]:
        missing_parts.append(f"Decisión: {decision.decision} ({decision.confidence:.2f})")

    if not required_elements["risk_score"]:
        missing_parts.append(f"Riesgo: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category})")

    # Add policy IDs if not mentioned (check individual policy IDs, not the full string)
    if policy_matches and policy_matches.matches:
        policy_ids = [m.policy_id for m in policy_matches.matches]
        # Check if ANY policy ID is missing from the explanation
        missing_policies = [pid for pid in policy_ids if pid not in audit_explanation]
        if missing_policies:
            policy_ids_str = ", ".join(policy_ids)
            missing_parts.append(f"Políticas: {policy_ids_str}")

    if missing_parts:
        enhancement = " | ".join(missing_parts)
        audit_explanation = f"{audit_explanation} | {enhancement}"
        logger.debug("audit_explanation_enhanced", added_elements=len(missing_parts))

    return audit_explanation


# ============================================================================
# MAIN AGENT FUNCTION
# ============================================================================


@timed_agent("explainability")
async def explainability_agent(state: OrchestratorState) -> dict:
    """Explainability Agent - generates customer and audit explanations.

    Generates two types of explanations:
    1. Customer-facing: Simple, empathetic, no technical jargon
    2. Audit: Technical, detailed, with full citations

    Args:
        state: Orchestrator state with decision, evidence, policy_matches, debate

    Returns:
        Dict with explanation field containing ExplanationResult

    Note:
        - Uses single LLM call for efficiency
        - Falls back to deterministic templates if LLM fails
        - Validates customer explanation contains no internal details
        - Ensures audit explanation includes all required citations
    """
    try:
        # Extract inputs from state
        decision = state.get("decision")
        evidence = state.get("evidence")
        policy_matches = state.get("policy_matches")
        debate = state.get("debate")

        # Validate required inputs
        if not decision:
            logger.error("explainability_no_decision")
            return _build_error_explanation()

        if not evidence:
            logger.warning("explainability_no_evidence")
            # Continue with decision-only explanations
            evidence = _create_minimal_evidence()

        if not debate:
            logger.warning("explainability_no_debate")
            # Continue with minimal debate
            debate = _create_minimal_debate()

        # Get LLM instance
        llm = get_llm()

        # Call LLM for explanations
        customer_explanation, audit_explanation, key_factors, recommended_actions = \
            await _call_llm_for_explanation(llm, decision, evidence, policy_matches, debate)

        # If LLM failed, use deterministic fallback
        if not customer_explanation or not audit_explanation:
            logger.warning("explainability_llm_failed_using_fallback")
            customer_explanation, audit_explanation = _generate_fallback_explanations(
                decision,
                evidence,
                policy_matches,
                debate,
            )

        # Enhance and validate explanations
        customer_explanation = _enhance_customer_explanation(
            customer_explanation,
            decision.decision,
        )

        audit_explanation = _enhance_audit_explanation(
            audit_explanation,
            decision,
            evidence,
            policy_matches,
        )

        # Build ExplanationResult
        explanation_result = ExplanationResult(
            customer_explanation=customer_explanation,
            audit_explanation=audit_explanation,
        )

        logger.info(
            "explainability_completed",
            customer_length=len(customer_explanation),
            audit_length=len(audit_explanation),
            key_factors_count=len(key_factors),
            actions_count=len(recommended_actions),
        )

        return {"explanation": explanation_result}

    except Exception as e:
        logger.error("explainability_error", error=str(e), exc_info=True)
        # Return error explanation
        return _build_error_explanation()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _create_minimal_evidence() -> AggregatedEvidence:
    """Create minimal evidence when evidence phase failed."""
    return AggregatedEvidence(
        composite_risk_score=0.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )


def _create_minimal_debate() -> DebateArguments:
    """Create minimal debate arguments when debate phase failed."""
    return DebateArguments(
        pro_fraud_argument="Análisis no disponible.",
        pro_fraud_confidence=0.50,
        pro_fraud_evidence=[],
        pro_customer_argument="Análisis no disponible.",
        pro_customer_confidence=0.50,
        pro_customer_evidence=[],
    )


def _build_error_explanation() -> dict:
    """Build error explanation when agent fails critically.

    Returns:
        Dict with error ExplanationResult
    """
    logger.error("explainability_critical_error")

    error_explanation = ExplanationResult(
        customer_explanation=(
            "Su transacción está siendo procesada. "
            "Le contactaremos si necesitamos más información."
        ),
        audit_explanation=(
            "ERROR: Explainability agent failed. "
            "Explanations could not be generated. "
            "Manual review required."
        ),
    )

    return {"explanation": error_explanation}
