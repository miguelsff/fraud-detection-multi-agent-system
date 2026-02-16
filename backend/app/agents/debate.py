"""Adversarial Debate Agents - Pro-Fraud and Pro-Customer argumentation.

This module implements Phase 3 of the fraud detection pipeline:
- Pro-Fraud Agent: Argues WHY the transaction IS fraudulent (skeptical stance)
- Pro-Customer Agent: Argues WHY the transaction is LEGITIMATE (defender stance)

Both agents execute in parallel and provide balanced perspectives for the Decision Arbiter.
"""

from app.prompts.debate import PRO_CUSTOMER_PROMPT, PRO_FRAUD_PROMPT

from ..dependencies import get_llm
from ..models import OrchestratorState
from ..utils.debate_utils import (
    call_debate_llm,
    generate_fallback_pro_customer,
    generate_fallback_pro_fraud,
)
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)


# ============================================================================
# MAIN AGENT FUNCTIONS
# ============================================================================


@timed_agent("debate_pro_fraud")
async def debate_pro_fraud_agent(state: OrchestratorState) -> dict:
    """Pro-Fraud Debate Agent - argues WHY transaction IS fraudulent."""
    try:
        evidence = state.get("evidence")

        if not evidence:
            logger.warning("pro_fraud_no_evidence_found")
            return {
                "pro_fraud_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_fraud_confidence": 0.50,
                "pro_fraud_evidence": ["no_evidence"],
            }

        # Use GPT-3.5 for debate arguments (cost optimization)
        llm = get_llm(use_gpt4=False)
        argument, confidence, evidence_cited, llm_trace = await call_debate_llm(
            llm, evidence, PRO_FRAUD_PROMPT
        )

        if argument and confidence is not None:
            logger.info(
                "debate_pro_fraud_completed",
                confidence=confidence,
                evidence_count=len(evidence_cited),
            )
            return {
                "pro_fraud_argument": argument,
                "pro_fraud_confidence": confidence,
                "pro_fraud_evidence": evidence_cited,
                "_llm_trace": llm_trace,
            }

        logger.warning("pro_fraud_llm_failed_using_fallback")
        fallback = generate_fallback_pro_fraud(evidence)
        fallback["_error_trace"] = {"fallback_reason": "llm_failed_using_deterministic_fallback"}
        return fallback

    except Exception as e:
        logger.error("debate_pro_fraud_error", error=str(e), exc_info=True)
        return {
            "pro_fraud_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_fraud_confidence": 0.50,
            "pro_fraud_evidence": ["error_occurred"],
            "_error_trace": {"error_details": str(e)},
        }


@timed_agent("debate_pro_customer")
async def debate_pro_customer_agent(state: OrchestratorState) -> dict:
    """Pro-Customer Debate Agent - argues WHY transaction IS legitimate."""
    try:
        evidence = state.get("evidence")

        if not evidence:
            logger.warning("pro_customer_no_evidence_found")
            return {
                "pro_customer_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_customer_confidence": 0.50,
                "pro_customer_evidence": ["no_evidence"],
            }

        # Use GPT-3.5 for debate arguments (cost optimization)
        llm = get_llm(use_gpt4=False)
        argument, confidence, evidence_cited, llm_trace = await call_debate_llm(
            llm, evidence, PRO_CUSTOMER_PROMPT
        )

        if argument and confidence is not None:
            logger.info(
                "debate_pro_customer_completed",
                confidence=confidence,
                evidence_count=len(evidence_cited),
            )
            return {
                "pro_customer_argument": argument,
                "pro_customer_confidence": confidence,
                "pro_customer_evidence": evidence_cited,
                "_llm_trace": llm_trace,
            }

        logger.warning("pro_customer_llm_failed_using_fallback")
        fallback = generate_fallback_pro_customer(evidence)
        fallback["_error_trace"] = {"fallback_reason": "llm_failed_using_deterministic_fallback"}
        return fallback

    except Exception as e:
        logger.error("debate_pro_customer_error", error=str(e), exc_info=True)
        return {
            "pro_customer_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_customer_confidence": 0.50,
            "pro_customer_evidence": ["error_occurred"],
            "_error_trace": {"error_details": str(e)},
        }
