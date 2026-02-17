"""Decision Arbiter Agent - evaluates debate arguments and makes final fraud decision.

This module implements Phase 4 of the fraud detection pipeline:
- Evaluates pro-fraud and pro-customer arguments from Phase 3
- Considers consolidated evidence from Phase 2
- Makes final decision: APPROVE, CHALLENGE, BLOCK, or ESCALATE_TO_HUMAN
- Applies safety overrides for critical cases
- Generates initial explanations (to be enhanced by Phase 5)
"""

import asyncio
import re
from typing import Optional

from langchain_core.language_models import BaseChatModel

from ..constants import AGENT_TIMEOUTS
from ..dependencies import get_llm
from ..models import (
    AggregatedEvidence,
    DebateArguments,
    FraudDecision,
    OrchestratorState,
)
from ..prompts.decision import DECISION_ARBITER_PROMPT
from ..utils.decision_utils import (
    apply_safety_overrides,
    build_citations_external,
    build_citations_internal,
    generate_audit_explanation,
    generate_customer_explanation,
    generate_fallback_decision,
)
from ..utils.llm_utils import clamp_float, parse_json_response
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

VALID_DECISIONS = {"APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"}


# ============================================================================
# PARSING HELPER
# ============================================================================


def _parse_decision_response(
    response_text: str,
) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """Parse LLM response to extract decision, confidence, and reasoning.

    Two-stage parsing: JSON first, regex fallback.

    Returns:
        Tuple of (decision, confidence, reasoning)
    """
    # Stage 1: JSON parsing
    data = parse_json_response(response_text, "decision", "decision_arbiter")
    if data:
        decision = data.get("decision")
        confidence = data.get("confidence")
        reasoning = data.get("reasoning")

        if decision and decision in VALID_DECISIONS and confidence is not None:
            confidence = clamp_float(confidence)
            logger.info("decision_response_parsed_json", decision=decision, confidence=confidence)
            return decision, confidence, reasoning

    # Stage 2: Regex fallback
    try:
        decision_match = re.search(
            r'"?decision"?\s*:\s*"?(APPROVE|CHALLENGE|BLOCK|ESCALATE_TO_HUMAN)"?',
            response_text,
            re.IGNORECASE,
        )
        decision = decision_match.group(1).upper() if decision_match else None

        confidence_match = re.search(
            r'"?confidence"?\s*:\s*(0\.\d+|1\.0|0|1)', response_text, re.IGNORECASE
        )
        confidence = clamp_float(float(confidence_match.group(1))) if confidence_match else None

        reasoning_match = re.search(
            r'"?reasoning"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL
        )
        reasoning = reasoning_match.group(1) if reasoning_match else None

        if decision and confidence is not None:
            logger.info("decision_response_parsed_regex", decision=decision, confidence=confidence)
            return decision, confidence, reasoning
    except Exception as e:
        logger.error("regex_parse_failed_decision", error=str(e))

    logger.error("decision_response_parse_failed_completely")
    return None, None, None


# ============================================================================
# LLM CALL HELPER
# ============================================================================


async def _call_llm_for_decision(
    llm: BaseChatModel,
    evidence: AggregatedEvidence,
    debate: DebateArguments,
) -> tuple[Optional[str], Optional[float], Optional[str], dict]:
    """Call LLM for decision making with timeout.

    Returns:
        Tuple of (decision, confidence, reasoning, llm_trace_metadata)
    """
    prompt = DECISION_ARBITER_PROMPT.format(
        composite_risk_score=evidence.composite_risk_score,
        risk_category=evidence.risk_category,
        all_signals=", ".join(evidence.all_signals) if evidence.all_signals else "ninguna",
        all_citations="\n- ".join(evidence.all_citations) if evidence.all_citations else "ninguna",
        pro_fraud_confidence=debate.pro_fraud_confidence,
        pro_fraud_argument=debate.pro_fraud_argument,
        pro_fraud_evidence=", ".join(debate.pro_fraud_evidence)
        if debate.pro_fraud_evidence
        else "ninguna",
        pro_customer_confidence=debate.pro_customer_confidence,
        pro_customer_argument=debate.pro_customer_argument,
        pro_customer_evidence=", ".join(debate.pro_customer_evidence)
        if debate.pro_customer_evidence
        else "ninguna",
        decision_type="una de: APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN",
    )

    # Initialize LLM trace metadata
    llm_trace = {
        "llm_prompt": prompt,
        "llm_model": llm.model,
        "llm_temperature": 0.0,
    }

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=AGENT_TIMEOUTS.llm_call)

        # Capture raw response
        llm_trace["llm_response_raw"] = response.content

        # Capture token usage if available
        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("usage", {})
            llm_trace["llm_tokens_used"] = usage.get("total_tokens")

        decision, confidence, reasoning = _parse_decision_response(response.content)
        return decision, confidence, reasoning, llm_trace

    except asyncio.TimeoutError:
        logger.error("llm_timeout_decision", timeout_seconds=AGENT_TIMEOUTS.llm_call)
        llm_trace["llm_response_raw"] = f"TIMEOUT after {AGENT_TIMEOUTS.llm_call}s"
        return None, None, None, llm_trace
    except Exception as e:
        logger.error("llm_call_failed_decision", error=str(e))
        llm_trace["llm_response_raw"] = f"ERROR: {str(e)}"
        return None, None, None, llm_trace


# ============================================================================
# MAIN AGENT FUNCTION
# ============================================================================


@timed_agent("decision_arbiter")
async def decision_arbiter_agent(state: OrchestratorState) -> dict:
    """Decision Arbiter Agent - makes final fraud decision.

    Evaluates evidence and debate arguments to produce final decision with
    safety overrides for critical cases.
    """
    try:
        evidence = state.get("evidence")
        debate = state.get("debate")
        transaction = state["transaction"]

        if not evidence:
            logger.error("decision_arbiter_no_evidence")
            return _build_error_decision(transaction.transaction_id, "No evidence available")

        if not debate:
            logger.warning("decision_arbiter_no_debate")
            debate = _create_minimal_debate()

        # Use GPT-4 for critical decision making (high-stakes reasoning)
        llm = get_llm(use_gpt4=True)
        decision, confidence, reasoning, llm_trace = await _call_llm_for_decision(
            llm, evidence, debate
        )

        if not decision or confidence is None:
            logger.warning("decision_arbiter_llm_failed_using_fallback")
            decision, confidence, reasoning = generate_fallback_decision(evidence)
            # Mark fallback in trace
            llm_trace["fallback_reason"] = "llm_failed_using_deterministic_fallback"

        decision, confidence, reasoning = apply_safety_overrides(
            decision,
            confidence,
            reasoning,
            evidence.composite_risk_score,
        )

        fraud_decision = FraudDecision(
            transaction_id=transaction.transaction_id,
            decision=decision,  # type: ignore
            confidence=confidence,
            signals=evidence.all_signals,
            citations_internal=build_citations_internal(evidence),
            citations_external=build_citations_external(evidence),
            explanation_customer=generate_customer_explanation(decision),
            explanation_audit=generate_audit_explanation(
                decision, confidence, reasoning, evidence, debate
            ),
            agent_trace=_extract_agent_trace(state),
        )

        logger.info(
            "decision_arbiter_completed",
            decision=decision,
            confidence=confidence,
            composite_score=evidence.composite_risk_score,
            risk_category=evidence.risk_category,
        )

        result = {"decision": fraud_decision}
        if llm_trace.get("llm_prompt"):
            result["_llm_trace"] = llm_trace
        if llm_trace.get("fallback_reason"):
            result["_error_trace"] = {"fallback_reason": llm_trace["fallback_reason"]}

        return result

    except Exception as e:
        logger.error("decision_arbiter_error", error=str(e), exc_info=True)
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
    """Extract agent trace from state."""
    trace = state.get("trace", [])
    return [entry.agent_name for entry in trace] if trace else []


def _build_error_decision(transaction_id: str, error_message: str) -> dict:
    """Build error decision when agent fails critically."""
    logger.error(
        "decision_arbiter_critical_error", transaction_id=transaction_id, error=error_message
    )

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
