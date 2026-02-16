"""Explainability Agent - generates customer and audit explanations for fraud decisions.

This module implements Phase 5 of the fraud detection pipeline:
- Generates customer-facing explanation (simple, empathetic, no jargon)
- Generates audit explanation (technical, detailed, with citations)
- Uses single LLM call for efficiency
- Falls back to deterministic templates if LLM fails
"""

import asyncio
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
from .constants import AGENT_TIMEOUTS
from .llm_utils import parse_json_response

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
    """Parse LLM response to extract explanations, factors, and actions."""
    # Stage 1: JSON parsing
    data = parse_json_response(response_text, "customer_explanation", "explainability")
    if data:
        customer_explanation = data.get("customer_explanation")
        audit_explanation = data.get("audit_explanation")
        key_factors = data.get("key_factors", [])
        recommended_actions = data.get("recommended_actions", [])

        if customer_explanation and audit_explanation:
            if not isinstance(key_factors, list):
                key_factors = []
            if not isinstance(recommended_actions, list):
                recommended_actions = []
            logger.info("explanation_response_parsed_json", factors_count=len(key_factors), actions_count=len(recommended_actions))
            return customer_explanation, audit_explanation, key_factors, recommended_actions

    # Stage 2: Regex fallback
    try:
        customer_match = re.search(r'"?customer_explanation"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL)
        customer_explanation = customer_match.group(1) if customer_match else None

        audit_match = re.search(r'"?audit_explanation"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL)
        audit_explanation = audit_match.group(1) if audit_match else None

        factors_match = re.search(r'"?key_factors"?\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
        key_factors = re.findall(r'"([^"]+)"', factors_match.group(1)) if factors_match else []

        actions_match = re.search(r'"?recommended_actions"?\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
        recommended_actions = re.findall(r'"([^"]+)"', actions_match.group(1)) if actions_match else []

        if customer_explanation and audit_explanation:
            logger.info("explanation_response_parsed_regex", factors_count=len(key_factors), actions_count=len(recommended_actions))
            return customer_explanation, audit_explanation, key_factors, recommended_actions
    except Exception as e:
        logger.error("regex_parse_failed_explanation", error=str(e))

    logger.error("explanation_response_parse_failed_completely")
    return None, None, [], []


# ============================================================================
# LLM CALL
# ============================================================================


async def _call_llm_for_explanation(
    llm: ChatOllama,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: Optional[PolicyMatchResult],
    debate: DebateArguments,
) -> tuple[Optional[str], Optional[str], list[str], list[str]]:
    """Call LLM for explanation generation."""
    signals_text = "\n- ".join(decision.signals) if decision.signals else "ninguna"

    if policy_matches and policy_matches.matches:
        policies_text = "\n".join([
            f"- {match.policy_id}: {match.description} (relevancia: {match.relevance_score:.2f})"
            for match in policy_matches.matches
        ])
    else:
        policies_text = "Ninguna política específica aplicada"

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
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=AGENT_TIMEOUTS.llm_call)
        return _parse_explanation_response(response.content)
    except asyncio.TimeoutError:
        logger.error("llm_timeout_explanation", timeout_seconds=AGENT_TIMEOUTS.llm_call)
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
    """Generate deterministic explanations when LLM fails."""
    decision_type = decision.decision

    customer_templates = {
        "APPROVE": "Su transacción ha sido procesada exitosamente. No se detectaron problemas de seguridad.",
        "CHALLENGE": "Por seguridad, necesitamos verificar esta transacción. "
                     "Le enviaremos un código de verificación. "
                     "Esto es un procedimiento estándar para proteger su cuenta.",
        "BLOCK": "Por su seguridad, hemos bloqueado esta transacción debido a patrones inusuales. "
                 "Si usted autorizó esta transacción, por favor contáctenos de inmediato al "
                 "número en el reverso de su tarjeta.",
        "ESCALATE_TO_HUMAN": "Su transacción está siendo revisada por nuestro equipo de seguridad. "
                            "Le contactaremos dentro de las próximas 24 horas. "
                            "Gracias por su paciencia.",
    }

    policy_summary = "sin políticas" if not policy_matches or not policy_matches.matches else \
        f"{len(policy_matches.matches)} políticas aplicadas"

    audit_explanation = (
        f"Transacción {decision.transaction_id}: Decisión {decision_type} (confianza {decision.confidence:.2f}). "
        f"Riesgo compuesto: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category}). "
        f"Debate: pro-fraude {debate.pro_fraud_confidence:.2f} vs "
        f"pro-cliente {debate.pro_customer_confidence:.2f}. "
        f"Señales: {len(decision.signals)} detectadas. "
        f"{policy_summary}. "
        f"Explicación generada por fallback determinístico."
    )

    customer_explanation = customer_templates.get(
        decision_type, "Su transacción está siendo procesada. Le mantendremos informado.",
    )

    logger.info("fallback_explanations_generated", decision=decision_type, has_policies=bool(policy_matches and policy_matches.matches))
    return customer_explanation, audit_explanation


# ============================================================================
# EXPLANATION ENHANCEMENT
# ============================================================================


def _enhance_customer_explanation(customer_explanation: str, decision_type: str) -> str:
    """Ensure customer explanation doesn't reveal internal system details."""
    forbidden_keywords = [
        "score", "puntaje", "algoritmo", "modelo", "agente", "política",
        "policy", "FP-", "debate", "confianza:", "confidence", "LLM", "threshold",
    ]

    explanation_lower = customer_explanation.lower()
    for keyword in forbidden_keywords:
        if keyword.lower() in explanation_lower:
            logger.warning("customer_explanation_contains_internal_details", keyword=keyword, using_safe_template=True)
            return _get_safe_customer_template(decision_type)

    return customer_explanation


def _get_safe_customer_template(decision_type: str) -> str:
    """Get safe customer explanation template."""
    safe_templates = {
        "APPROVE": "Su transacción ha sido aprobada. Todo está en orden.",
        "CHALLENGE": "Por seguridad, necesitamos verificar esta transacción. Le contactaremos pronto.",
        "BLOCK": "Por su seguridad, hemos bloqueado esta transacción. Si usted la autorizó, contáctenos de inmediato.",
        "ESCALATE_TO_HUMAN": "Su transacción está en revisión. Nuestro equipo la analizará y le contactaremos pronto.",
    }
    return safe_templates.get(decision_type, "Su transacción está siendo procesada. Le mantendremos informado.")


def _enhance_audit_explanation(
    audit_explanation: str,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: Optional[PolicyMatchResult],
) -> str:
    """Enhance audit explanation with required details if missing."""
    missing_parts = []

    if decision.transaction_id not in audit_explanation:
        missing_parts.append(f"ID: {decision.transaction_id}")
    if decision.decision not in audit_explanation:
        missing_parts.append(f"Decisión: {decision.decision} ({decision.confidence:.2f})")
    if str(evidence.composite_risk_score) not in audit_explanation:
        missing_parts.append(f"Riesgo: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category})")

    if policy_matches and policy_matches.matches:
        policy_ids = [m.policy_id for m in policy_matches.matches]
        missing_policies = [pid for pid in policy_ids if pid not in audit_explanation]
        if missing_policies:
            missing_parts.append(f"Políticas: {', '.join(policy_ids)}")

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
    """Explainability Agent - generates customer and audit explanations."""
    try:
        decision = state.get("decision")
        evidence = state.get("evidence")
        policy_matches = state.get("policy_matches")
        debate = state.get("debate")

        if not decision:
            logger.error("explainability_no_decision")
            return _build_error_explanation()

        if not evidence:
            logger.warning("explainability_no_evidence")
            evidence = _create_minimal_evidence()

        if not debate:
            logger.warning("explainability_no_debate")
            debate = _create_minimal_debate()

        llm = get_llm()
        customer_explanation, audit_explanation, key_factors, recommended_actions = \
            await _call_llm_for_explanation(llm, decision, evidence, policy_matches, debate)

        if not customer_explanation or not audit_explanation:
            logger.warning("explainability_llm_failed_using_fallback")
            customer_explanation, audit_explanation = _generate_fallback_explanations(
                decision, evidence, policy_matches, debate,
            )

        customer_explanation = _enhance_customer_explanation(customer_explanation, decision.decision)
        audit_explanation = _enhance_audit_explanation(audit_explanation, decision, evidence, policy_matches)

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
        return _build_error_explanation()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _create_minimal_evidence() -> AggregatedEvidence:
    """Create minimal evidence when evidence phase failed."""
    return AggregatedEvidence(
        composite_risk_score=0.0, all_signals=[], all_citations=[], risk_category="low",
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
    """Build error explanation when agent fails critically."""
    logger.error("explainability_critical_error")
    return {
        "explanation": ExplanationResult(
            customer_explanation="Su transacción está siendo procesada. Le contactaremos si necesitamos más información.",
            audit_explanation="ERROR: Explainability agent failed. Explanations could not be generated. Manual review required.",
        )
    }
