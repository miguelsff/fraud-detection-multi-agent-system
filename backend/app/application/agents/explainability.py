"""Explainability Agent - generates customer and audit explanations for fraud decisions.

Implements Phase 5. Uses llm_port from config["configurable"].
"""

import re

from langchain_core.runnables import RunnableConfig

from app.domain.models import (
    AggregatedEvidence,
    DebateArguments,
    ExplanationResult,
    FraudDecision,
    OrchestratorState,
    PolicyMatchResult,
)
from app.application.ports.llm import LLMPort
from app.application.prompts.explainability import EXPLAINABILITY_PROMPT
from app.utils.fallback_factories import (
    create_minimal_debate,
    create_minimal_evidence,
    get_customer_explanation,
)
from app.utils.llm_utils import parse_json_response
from app.utils.logger import get_logger
from app.utils.timing import timed_agent

logger = get_logger(__name__)


def _parse_explanation_response(
    response_text: str,
) -> tuple[str | None, str | None, list[str], list[str]]:
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
            logger.info(
                "explanation_response_parsed_json",
                factors_count=len(key_factors),
                actions_count=len(recommended_actions),
            )
            return customer_explanation, audit_explanation, key_factors, recommended_actions

    # Stage 2: Regex fallback
    try:
        customer_match = re.search(
            r'"?customer_explanation"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL
        )
        customer_explanation = customer_match.group(1) if customer_match else None

        audit_match = re.search(
            r'"?audit_explanation"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL
        )
        audit_explanation = audit_match.group(1) if audit_match else None

        factors_match = re.search(
            r'"?key_factors"?\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL
        )
        key_factors = re.findall(r'"([^"]+)"', factors_match.group(1)) if factors_match else []

        actions_match = re.search(
            r'"?recommended_actions"?\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL
        )
        recommended_actions = (
            re.findall(r'"([^"]+)"', actions_match.group(1)) if actions_match else []
        )

        if customer_explanation and audit_explanation:
            logger.info(
                "explanation_response_parsed_regex",
                factors_count=len(key_factors),
                actions_count=len(recommended_actions),
            )
            return customer_explanation, audit_explanation, key_factors, recommended_actions
    except Exception as e:
        logger.error("regex_parse_failed_explanation", error=str(e))

    logger.error("explanation_response_parse_failed_completely")
    return None, None, [], []


async def _call_llm_for_explanation(
    llm_port: LLMPort | None,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: PolicyMatchResult | None,
    debate: DebateArguments,
) -> tuple[str | None, str | None, list[str], list[str], dict]:
    """Call LLM for explanation generation."""
    signals_text = "\n- ".join(decision.signals) if decision.signals else "ninguna"

    if policy_matches and policy_matches.matches:
        policies_text = "\n".join(
            [
                f"- {match.policy_id}: {match.description} (relevancia: {match.relevance_score:.2f})"
                for match in policy_matches.matches
            ]
        )
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

    if not llm_port:
        logger.warning("explainability_no_llm_port_in_config")
        return None, None, [], [], {"fallback_reason": "no_llm_port_in_config"}

    content, llm_trace = await llm_port.invoke(prompt, agent_name="explainability")

    if content:
        customer_exp, audit_exp, key_factors, actions = _parse_explanation_response(content)
        return customer_exp, audit_exp, key_factors, actions, llm_trace
    return None, None, [], [], llm_trace


_FALLBACK_CUSTOMER_TEMPLATES = {
    "APPROVE": "Su transacción ha sido procesada exitosamente. No se detectaron problemas de seguridad.",
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


def _generate_fallback_explanations(
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: PolicyMatchResult | None,
    debate: DebateArguments,
) -> tuple[str, str]:
    """Generate deterministic explanations when LLM fails."""
    decision_type = decision.decision

    policy_summary = (
        "sin políticas"
        if not policy_matches or not policy_matches.matches
        else f"{len(policy_matches.matches)} políticas aplicadas"
    )

    audit_explanation = (
        f"Transacción {decision.transaction_id}: Decisión {decision_type} (confianza {decision.confidence:.2f}). "
        f"Riesgo compuesto: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category}). "
        f"Debate: pro-fraude {debate.pro_fraud_confidence:.2f} vs "
        f"pro-cliente {debate.pro_customer_confidence:.2f}. "
        f"Señales: {len(decision.signals)} detectadas. "
        f"{policy_summary}. "
        f"Explicación generada por fallback determinístico."
    )

    customer_explanation = _FALLBACK_CUSTOMER_TEMPLATES.get(
        decision_type,
        "Su transacción está siendo procesada. Le mantendremos informado.",
    )

    logger.info(
        "fallback_explanations_generated",
        decision=decision_type,
        has_policies=bool(policy_matches and policy_matches.matches),
    )
    return customer_explanation, audit_explanation


def _enhance_customer_explanation(customer_explanation: str, decision_type: str) -> str:
    """Ensure customer explanation doesn't reveal internal system details."""
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

    explanation_lower = customer_explanation.lower()
    for keyword in forbidden_keywords:
        if keyword.lower() in explanation_lower:
            logger.warning(
                "customer_explanation_contains_internal_details",
                keyword=keyword,
                using_safe_template=True,
            )
            return get_customer_explanation(decision_type)

    return customer_explanation


def _enhance_audit_explanation(
    audit_explanation: str,
    decision: FraudDecision,
    evidence: AggregatedEvidence,
    policy_matches: PolicyMatchResult | None,
) -> str:
    """Enhance audit explanation with required details if missing."""
    missing_parts = []

    if decision.transaction_id not in audit_explanation:
        missing_parts.append(f"ID: {decision.transaction_id}")
    if decision.decision not in audit_explanation:
        missing_parts.append(f"Decisión: {decision.decision} ({decision.confidence:.2f})")
    if str(evidence.composite_risk_score) not in audit_explanation:
        missing_parts.append(
            f"Riesgo: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category})"
        )

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


@timed_agent("explainability")
async def explainability_agent(state: OrchestratorState, config: RunnableConfig = None) -> dict:
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
            evidence = create_minimal_evidence()

        if not debate:
            logger.warning("explainability_no_debate")
            debate = create_minimal_debate()

        configurable = (config or {}).get("configurable", {})
        llm_port: LLMPort | None = configurable.get("llm_port")

        (
            customer_explanation,
            audit_explanation,
            key_factors,
            recommended_actions,
            llm_trace,
        ) = await _call_llm_for_explanation(llm_port, decision, evidence, policy_matches, debate)

        if not customer_explanation or not audit_explanation:
            logger.warning("explainability_llm_failed_using_fallback")
            customer_explanation, audit_explanation = _generate_fallback_explanations(
                decision,
                evidence,
                policy_matches,
                debate,
            )
            llm_trace["fallback_reason"] = "llm_failed_using_deterministic_fallback"

        customer_explanation = _enhance_customer_explanation(
            customer_explanation, decision.decision
        )
        audit_explanation = _enhance_audit_explanation(
            audit_explanation, decision, evidence, policy_matches
        )

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

        result = {"explanation": explanation_result}
        if llm_trace.get("llm_prompt"):
            result["_llm_trace"] = llm_trace
        if llm_trace.get("fallback_reason"):
            result["_error_trace"] = {"fallback_reason": llm_trace["fallback_reason"]}

        return result

    except Exception as e:
        logger.error("explainability_error", error=str(e), exc_info=True)
        return _build_error_explanation()


def _build_error_explanation() -> dict:
    """Build error explanation when agent fails critically."""
    logger.error("explainability_critical_error")
    return {
        "explanation": ExplanationResult(
            customer_explanation="Su transacción está siendo procesada. Le contactaremos si necesitamos más información.",
            audit_explanation="ERROR: Explainability agent failed. Explanations could not be generated. Manual review required.",
        )
    }
