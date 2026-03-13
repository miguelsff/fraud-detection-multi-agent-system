"""Adversarial Debate Agents - Pro-Fraud and Pro-Customer argumentation.

Implements Phase 3 of the fraud detection pipeline.
Uses llm_port from config["configurable"] instead of direct get_llm() import.
"""

from langchain_core.runnables import RunnableConfig

from app.domain.models import OrchestratorState
from app.application.ports.llm import LLMPort
from app.application.prompts.debate import PRO_CUSTOMER_PROMPT, PRO_FRAUD_PROMPT
from app.utils.debate_utils import (
    call_debate_llm_via_port,
    generate_fallback_pro_customer,
    generate_fallback_pro_fraud,
)
from app.utils.logger import get_logger
from app.utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("debate_pro_fraud")
async def debate_pro_fraud_agent(state: OrchestratorState, config: RunnableConfig = None) -> dict:
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

        configurable = (config or {}).get("configurable", {})
        llm_port: LLMPort | None = configurable.get("llm_port")

        if not llm_port:
            logger.warning("pro_fraud_no_llm_port_using_fallback")
            fallback = generate_fallback_pro_fraud(evidence)
            fallback["_error_trace"] = {"fallback_reason": "no_llm_port_in_config"}
            return fallback

        argument, confidence, evidence_cited, llm_trace = await call_debate_llm_via_port(
            llm_port, evidence, PRO_FRAUD_PROMPT
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
async def debate_pro_customer_agent(
    state: OrchestratorState, config: RunnableConfig = None
) -> dict:
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

        configurable = (config or {}).get("configurable", {})
        llm_port: LLMPort | None = configurable.get("llm_port")

        if not llm_port:
            logger.warning("pro_customer_no_llm_port_using_fallback")
            fallback = generate_fallback_pro_customer(evidence)
            fallback["_error_trace"] = {"fallback_reason": "no_llm_port_in_config"}
            return fallback

        argument, confidence, evidence_cited, llm_trace = await call_debate_llm_via_port(
            llm_port, evidence, PRO_CUSTOMER_PROMPT
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
