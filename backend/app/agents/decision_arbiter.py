"""Decision Arbiter Agent - evaluates debate arguments and makes final fraud decision.

This module implements Phase 4 of the fraud detection pipeline:
- Evaluates pro-fraud and pro-customer arguments from Phase 3
- Considers consolidated evidence from Phase 2
- Makes final decision: APPROVE, CHALLENGE, BLOCK, or ESCALATE_TO_HUMAN
- Applies safety overrides for critical cases
- Generates initial explanations (to be enhanced by Phase 5)
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
    DecisionType,
    FraudDecision,
    OrchestratorState,
)
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

# ============================================================================
# PROMPT TEMPLATE (Spanish)
# ============================================================================

DECISION_ARBITER_PROMPT = """Eres un JUEZ IMPARCIAL evaluando una transacción financiera sospechosa de fraude. Tu tarea es analizar la evidencia y los argumentos de ambas partes para tomar una decisión justa.

**EVIDENCIA CONSOLIDADA:**
- Puntaje de riesgo compuesto: {composite_risk_score}/100
- Categoría de riesgo: {risk_category}
- Señales detectadas: {all_signals}
- Citaciones: {all_citations}

**ARGUMENTO PRO-FRAUDE (confianza: {pro_fraud_confidence}):**
{pro_fraud_argument}
Evidencia citada: {pro_fraud_evidence}

**ARGUMENTO PRO-CLIENTE (confianza: {pro_customer_confidence}):**
{pro_customer_argument}
Evidencia citada: {pro_customer_evidence}

**REGLAS DE DECISIÓN:**

1. **APPROVE** (aprobar transacción):
   - Evidencia claramente a favor del cliente
   - Puntaje de riesgo bajo (< 30)
   - Argumento pro-cliente significativamente más fuerte
   - Confianza alta en la decisión

2. **CHALLENGE** (solicitar verificación adicional):
   - Dudas razonables sobre la transacción
   - Puntaje de riesgo medio (30-60)
   - Argumentos balanceados o ligeramente sospechosos
   - Verificación del cliente puede resolver dudas

3. **BLOCK** (bloquear transacción):
   - Evidencia fuerte de fraude
   - Puntaje de riesgo alto (60-85)
   - Argumento pro-fraude significativamente más fuerte
   - Riesgo inaceptable para el banco

4. **ESCALATE_TO_HUMAN** (escalar a revisión humana):
   - Caso ambiguo que requiere juicio humano
   - Confianza baja en cualquier dirección (< 0.6)
   - Múltiples señales contradictorias
   - Contexto complejo que excede capacidad automatizada

**INSTRUCCIONES:**
1. Analiza cuidadosamente la evidencia y ambos argumentos
2. Considera el puntaje de riesgo compuesto como indicador principal
3. Evalúa la confianza de cada argumento
4. Aplica las reglas de decisión
5. Proporciona razonamiento claro y conciso (2-3 oraciones)

**FORMATO DE SALIDA (JSON estricto):**
{{
  "decision": "APPROVE|CHALLENGE|BLOCK|ESCALATE_TO_HUMAN",
  "confidence": 0.75,
  "reasoning": "El puntaje de riesgo de 68.5 combinado con el argumento pro-fraude (confianza 0.78) supera al argumento pro-cliente (0.55). Las señales de monto elevado y horario nocturno justifican bloqueo preventivo."
}}

**IMPORTANTE:**
- Responde SOLO con el JSON, sin texto adicional
- La confianza debe estar entre 0.0 y 1.0
- El razonamiento debe ser objetivo e imparcial
- Decisión final: {decision_type}
"""

# ============================================================================
# PARSING HELPER
# ============================================================================


def _parse_decision_response(response_text: str) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """Parse LLM response to extract decision, confidence, and reasoning.

    Two-stage parsing strategy:
    1. JSON parsing: Look for JSON in markdown code blocks or raw JSON
    2. Regex fallback: Extract fields via regex if JSON parsing fails

    Args:
        response_text: Raw text response from LLM

    Returns:
        Tuple of (decision, confidence, reasoning)
        Returns (None, None, None) if parsing fails completely

    Note:
        - Validates decision is one of: APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN
        - Clamps confidence to [0.0, 1.0]
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
            json_match = re.search(r'\{.*"decision".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        # Extract fields
        decision = data.get("decision")
        confidence = data.get("confidence")
        reasoning = data.get("reasoning")

        # Validate decision type
        valid_decisions = ["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]
        if decision and decision in valid_decisions:
            # Clamp confidence to [0.0, 1.0]
            if confidence is not None:
                confidence = max(0.0, min(1.0, float(confidence)))

            logger.info("decision_response_parsed_json", decision=decision, confidence=confidence)
            return decision, confidence, reasoning

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("json_parse_failed_decision", error=str(e), attempting_regex=True)

    # ========== STAGE 2: REGEX FALLBACK ==========
    try:
        # Extract decision: "decision": "APPROVE|CHALLENGE|BLOCK|ESCALATE_TO_HUMAN"
        decision_match = re.search(
            r'"?decision"?\s*:\s*"?(APPROVE|CHALLENGE|BLOCK|ESCALATE_TO_HUMAN)"?',
            response_text,
            re.IGNORECASE,
        )
        decision = decision_match.group(1).upper() if decision_match else None

        # Extract confidence: "confidence": 0.XX
        confidence_match = re.search(
            r'"?confidence"?\s*:\s*(0\.\d+|1\.0|0|1)',
            response_text,
            re.IGNORECASE,
        )
        confidence = None
        if confidence_match:
            confidence = float(confidence_match.group(1))
            confidence = max(0.0, min(1.0, confidence))

        # Extract reasoning: "reasoning": "..."
        reasoning_match = re.search(
            r'"?reasoning"?\s*:\s*"([^"]+)"',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        reasoning = reasoning_match.group(1) if reasoning_match else None

        if decision and confidence is not None:
            logger.info("decision_response_parsed_regex", decision=decision, confidence=confidence)
            return decision, confidence, reasoning

    except Exception as e:
        logger.error("regex_parse_failed_decision", error=str(e))

    # ========== PARSING FAILED ==========
    logger.error("decision_response_parse_failed_completely")
    return None, None, None


# ============================================================================
# LLM CALL HELPER
# ============================================================================


async def _call_llm_for_decision(
    llm: ChatOllama,
    evidence: AggregatedEvidence,
    debate: DebateArguments,
) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """Call LLM for decision making.

    Args:
        llm: ChatOllama instance
        evidence: AggregatedEvidence from Phase 2
        debate: DebateArguments from Phase 3

    Returns:
        Tuple of (decision, confidence, reasoning)
        Returns (None, None, None) if LLM call fails

    Note:
        - Includes 30-second timeout
        - Delegates parsing to _parse_decision_response()
    """
    # Format prompt with evidence and debate data
    prompt = DECISION_ARBITER_PROMPT.format(
        composite_risk_score=evidence.composite_risk_score,
        risk_category=evidence.risk_category,
        all_signals=", ".join(evidence.all_signals) if evidence.all_signals else "ninguna",
        all_citations="\n- ".join(evidence.all_citations) if evidence.all_citations else "ninguna",
        pro_fraud_confidence=debate.pro_fraud_confidence,
        pro_fraud_argument=debate.pro_fraud_argument,
        pro_fraud_evidence=", ".join(debate.pro_fraud_evidence) if debate.pro_fraud_evidence else "ninguna",
        pro_customer_confidence=debate.pro_customer_confidence,
        pro_customer_argument=debate.pro_customer_argument,
        pro_customer_evidence=", ".join(debate.pro_customer_evidence) if debate.pro_customer_evidence else "ninguna",
        decision_type="una de: APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN",
    )

    try:
        # Call LLM with timeout
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=30.0)
        response_text = response.content

        # Parse response
        return _parse_decision_response(response_text)

    except asyncio.TimeoutError:
        logger.error("llm_timeout_decision", timeout_seconds=30)
        return None, None, None
    except Exception as e:
        logger.error("llm_call_failed_decision", error=str(e))
        return None, None, None


# ============================================================================
# DETERMINISTIC FALLBACK
# ============================================================================


def _generate_fallback_decision(evidence: AggregatedEvidence) -> tuple[str, float, str]:
    """Generate deterministic decision when LLM fails.

    Maps risk_category to decision type and confidence.

    Args:
        evidence: AggregatedEvidence from Phase 2

    Returns:
        Tuple of (decision, confidence, reasoning)

    Mapping:
        - low → APPROVE (0.75 confidence)
        - medium → CHALLENGE (0.70 confidence)
        - high → BLOCK (0.80 confidence)
        - critical → BLOCK (0.90 confidence)
    """
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    # Risk category → (decision, confidence, reasoning template)
    mappings = {
        "low": (
            "APPROVE",
            0.75,
            f"Puntaje de riesgo bajo ({composite_score}/100). Señales mínimas de fraude. Transacción aprobada.",
        ),
        "medium": (
            "CHALLENGE",
            0.70,
            f"Puntaje de riesgo medio ({composite_score}/100). Verificación adicional recomendada antes de aprobar.",
        ),
        "high": (
            "BLOCK",
            0.80,
            f"Puntaje de riesgo alto ({composite_score}/100). Señales significativas de fraude justifican bloqueo.",
        ),
        "critical": (
            "BLOCK",
            0.90,
            f"Puntaje de riesgo crítico ({composite_score}/100). Múltiples señales de alto riesgo. Bloqueo inmediato requerido.",
        ),
    }

    decision, confidence, reasoning = mappings.get(
        risk_category,
        ("ESCALATE_TO_HUMAN", 0.50, "Categoría de riesgo no clasificada. Revisión humana requerida."),
    )

    logger.info(
        "fallback_decision_generated",
        risk_category=risk_category,
        decision=decision,
        confidence=confidence,
    )

    return decision, confidence, reasoning


# ============================================================================
# SAFETY OVERRIDES
# ============================================================================


def _apply_safety_overrides(
    decision: str,
    confidence: float,
    reasoning: str,
    evidence: AggregatedEvidence,
) -> tuple[str, float, str]:
    """Apply safety overrides to ensure critical cases are handled properly.

    Override Rules:
    1. If composite_risk_score > 85 → always BLOCK (critical risk)
    2. If confidence < 0.55 → ESCALATE_TO_HUMAN (low confidence)

    Args:
        decision: Original decision from LLM or fallback
        confidence: Original confidence
        reasoning: Original reasoning
        evidence: AggregatedEvidence for safety checks

    Returns:
        Tuple of (final_decision, final_confidence, final_reasoning)
        May be modified by safety overrides
    """
    original_decision = decision
    composite_score = evidence.composite_risk_score

    # Override 1: Critical risk score → always BLOCK
    if composite_score > 85.0:
        if decision != "BLOCK":
            logger.warning(
                "safety_override_critical_score",
                original_decision=decision,
                composite_score=composite_score,
                new_decision="BLOCK",
            )
            decision = "BLOCK"
            confidence = max(confidence, 0.85)  # Ensure high confidence
            reasoning = (
                f"OVERRIDE DE SEGURIDAD: Puntaje de riesgo crítico ({composite_score}/100) "
                f"requiere bloqueo inmediato independientemente del análisis. {reasoning}"
            )

    # Override 2: Low confidence → ESCALATE_TO_HUMAN
    if confidence < 0.55:
        if decision != "ESCALATE_TO_HUMAN":
            logger.warning(
                "safety_override_low_confidence",
                original_decision=decision,
                confidence=confidence,
                new_decision="ESCALATE_TO_HUMAN",
            )
            decision = "ESCALATE_TO_HUMAN"
            reasoning = (
                f"ESCALADO POR BAJA CONFIANZA: Confianza {confidence:.2f} < 0.55. "
                f"Caso requiere revisión humana. Decisión original: {original_decision}. {reasoning}"
            )

    if decision != original_decision:
        logger.info(
            "safety_override_applied",
            original=original_decision,
            final=decision,
            reason="critical_score" if composite_score > 85.0 else "low_confidence",
        )

    return decision, confidence, reasoning


# ============================================================================
# CITATION BUILDERS
# ============================================================================


def _build_citations_internal(evidence: AggregatedEvidence) -> list[dict]:
    """Build internal citations from policy matches.

    Args:
        evidence: AggregatedEvidence with policy match citations

    Returns:
        List of citation dicts with policy_id and text
    """
    citations = []

    # Extract policy citations from all_citations
    # Format: "FP-01: Description text"
    for citation in evidence.all_citations:
        # Match pattern: "FP-XX: text" or "Threat: ..." (skip threats)
        if citation.startswith("FP-"):
            parts = citation.split(":", 1)
            if len(parts) == 2:
                policy_id = parts[0].strip()
                text = parts[1].strip()
                citations.append({"policy_id": policy_id, "text": text})

    return citations


def _build_citations_external(evidence: AggregatedEvidence) -> list[dict]:
    """Build external citations from threat intelligence.

    Args:
        evidence: AggregatedEvidence with threat intel citations

    Returns:
        List of citation dicts with source and detail
    """
    citations = []

    # Extract threat citations from all_citations
    # Format: "Threat: source_name (confidence: 0.XX)"
    for citation in evidence.all_citations:
        if citation.startswith("Threat:"):
            # Parse "Threat: source_name (confidence: 0.XX)"
            match = re.match(r"Threat:\s*(.+?)\s*\(confidence:\s*([\d.]+)\)", citation)
            if match:
                source_name = match.group(1)
                confidence = match.group(2)
                citations.append({
                    "source": source_name,
                    "detail": f"Confidence: {confidence}",
                })
            else:
                # Fallback: just use the whole string
                citations.append({
                    "source": "external_threat",
                    "detail": citation.replace("Threat: ", ""),
                })

    # If no threats found, add placeholder
    if not citations:
        citations.append({
            "source": "external_threat_check",
            "detail": "No external threats detected",
        })

    return citations


# ============================================================================
# EXPLANATION GENERATORS
# ============================================================================


def _generate_customer_explanation(decision: str, reasoning: str) -> str:
    """Generate customer-facing explanation based on decision.

    Args:
        decision: Decision type
        reasoning: Internal reasoning

    Returns:
        Customer-friendly explanation string (Spanish)
    """
    # Decision → customer-friendly message
    templates = {
        "APPROVE": "Su transacción ha sido aprobada. Todo está en orden.",
        "CHALLENGE": "Hemos detectado actividad inusual en su cuenta. "
        "Por seguridad, necesitamos verificar esta transacción. "
        "Le contactaremos pronto.",
        "BLOCK": "Por su seguridad, hemos bloqueado esta transacción debido a actividad sospechosa. "
        "Si usted autorizó esta transacción, por favor contáctenos de inmediato.",
        "ESCALATE_TO_HUMAN": "Su transacción está en revisión. "
        "Nuestro equipo de seguridad la analizará y le contactaremos pronto.",
    }

    return templates.get(
        decision,
        "Su transacción está siendo procesada. Le contactaremos si necesitamos más información.",
    )


def _generate_audit_explanation(
    decision: str,
    confidence: float,
    reasoning: str,
    evidence: AggregatedEvidence,
    debate: DebateArguments,
) -> str:
    """Generate audit trail explanation with full context.

    Args:
        decision: Decision type
        confidence: Decision confidence
        reasoning: Decision reasoning
        evidence: AggregatedEvidence
        debate: DebateArguments

    Returns:
        Detailed audit explanation string (Spanish)
    """
    # Build comprehensive audit log
    audit_parts = [
        f"DECISIÓN: {decision} (confianza: {confidence:.2f})",
        f"Riesgo compuesto: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category})",
        f"Debate adversarial: pro-fraude {debate.pro_fraud_confidence:.2f} vs "
        f"pro-cliente {debate.pro_customer_confidence:.2f}",
        f"Razonamiento: {reasoning}",
    ]

    # Add signal count
    if evidence.all_signals:
        audit_parts.append(f"Señales detectadas ({len(evidence.all_signals)}): {', '.join(evidence.all_signals[:5])}")

    return " | ".join(audit_parts)


# ============================================================================
# MAIN AGENT FUNCTION
# ============================================================================


@timed_agent("decision_arbiter")
async def decision_arbiter_agent(state: OrchestratorState) -> dict:
    """Decision Arbiter Agent - makes final fraud decision.

    Evaluates evidence and debate arguments to produce final decision with
    safety overrides for critical cases.

    Args:
        state: Orchestrator state with evidence and debate fields

    Returns:
        Dict with decision field containing FraudDecision

    Note:
        - Uses LLM for nuanced decision-making
        - Applies safety overrides (critical score → BLOCK, low confidence → ESCALATE)
        - Falls back to deterministic decision on LLM failure
        - Generates both customer and audit explanations
    """
    try:
        # Extract inputs from state
        evidence = state.get("evidence")
        debate = state.get("debate")
        transaction = state["transaction"]

        # Validate required inputs
        if not evidence:
            logger.error("decision_arbiter_no_evidence")
            return _build_error_decision(transaction.transaction_id, "No evidence available")

        if not debate:
            logger.warning("decision_arbiter_no_debate")
            # Continue with evidence-only decision
            debate = _create_minimal_debate()

        # Get LLM instance
        llm = get_llm()

        # Call LLM for decision
        decision, confidence, reasoning = await _call_llm_for_decision(llm, evidence, debate)

        # If LLM failed, use deterministic fallback
        if not decision or confidence is None:
            logger.warning("decision_arbiter_llm_failed_using_fallback")
            decision, confidence, reasoning = _generate_fallback_decision(evidence)

        # Apply safety overrides
        decision, confidence, reasoning = _apply_safety_overrides(
            decision,
            confidence,
            reasoning,
            evidence,
        )

        # Build citations
        citations_internal = _build_citations_internal(evidence)
        citations_external = _build_citations_external(evidence)

        # Generate explanations
        explanation_customer = _generate_customer_explanation(decision, reasoning)
        explanation_audit = _generate_audit_explanation(
            decision,
            confidence,
            reasoning,
            evidence,
            debate,
        )

        # Build agent trace (list of agent names that have executed)
        agent_trace = _extract_agent_trace(state)

        # Construct FraudDecision
        fraud_decision = FraudDecision(
            transaction_id=transaction.transaction_id,
            decision=decision,  # type: ignore
            confidence=confidence,
            signals=evidence.all_signals,
            citations_internal=citations_internal,
            citations_external=citations_external,
            explanation_customer=explanation_customer,
            explanation_audit=explanation_audit,
            agent_trace=agent_trace,
        )

        logger.info(
            "decision_arbiter_completed",
            decision=decision,
            confidence=confidence,
            composite_score=evidence.composite_risk_score,
            risk_category=evidence.risk_category,
        )

        return {"decision": fraud_decision}

    except Exception as e:
        logger.error("decision_arbiter_error", error=str(e), exc_info=True)
        # Return error decision
        transaction = state.get("transaction")
        transaction_id = transaction.transaction_id if transaction else "UNKNOWN"
        return _build_error_decision(transaction_id, f"Decision error: {str(e)}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _create_minimal_debate() -> DebateArguments:
    """Create minimal debate arguments when debate phase failed."""
    return DebateArguments(
        pro_fraud_argument="Análisis de debate no disponible.",
        pro_fraud_confidence=0.50,
        pro_fraud_evidence=["debate_unavailable"],
        pro_customer_argument="Análisis de debate no disponible.",
        pro_customer_confidence=0.50,
        pro_customer_evidence=["debate_unavailable"],
    )


def _extract_agent_trace(state: OrchestratorState) -> list[str]:
    """Extract agent trace from state.

    Args:
        state: OrchestratorState with trace field

    Returns:
        List of agent names that have executed
    """
    trace = state.get("trace", [])
    return [entry.agent_name for entry in trace] if trace else []


def _build_error_decision(transaction_id: str, error_message: str) -> dict:
    """Build error decision when agent fails critically.

    Args:
        transaction_id: Transaction ID
        error_message: Error description

    Returns:
        Dict with error FraudDecision
    """
    logger.error("decision_arbiter_critical_error", transaction_id=transaction_id, error=error_message)

    error_decision = FraudDecision(
        transaction_id=transaction_id,
        decision="ESCALATE_TO_HUMAN",
        confidence=0.0,
        signals=["decision_arbiter_error"],
        citations_internal=[{"policy_id": "ERROR", "text": error_message}],
        citations_external=[{"source": "system_error", "detail": "Decision arbiter failed"}],
        explanation_customer="Su transacción está en revisión. Nuestro equipo la analizará pronto.",
        explanation_audit=f"ERROR: {error_message}. Escalado automático a revisión humana.",
        agent_trace=["decision_arbiter_error"],
    )

    return {"decision": error_decision}
