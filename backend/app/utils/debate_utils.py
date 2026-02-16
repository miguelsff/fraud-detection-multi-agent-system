"""Helper functions extracted from debate.py.

Provides shared LLM calling logic, parsing, and fallback generation
for both pro-fraud and pro-customer debate agents.
"""

import asyncio
import re
from typing import Optional

from langchain_ollama import ChatOllama

from app.models import AggregatedEvidence
from app.utils.llm_utils import clamp_float, parse_json_response
from app.utils.logger import get_logger

from ..constants import AGENT_TIMEOUTS

logger = get_logger(__name__)


async def call_debate_llm(
    llm: ChatOllama,
    evidence: AggregatedEvidence,
    prompt_template: str,
) -> tuple[Optional[str], Optional[float], list[str], dict]:
    """Call LLM for debate argument generation with parsing.

    Args:
        llm: ChatOllama instance
        evidence: AggregatedEvidence from Phase 2
        prompt_template: Prompt template (PRO_FRAUD_PROMPT or PRO_CUSTOMER_PROMPT)

    Returns:
        Tuple of (argument, confidence, evidence_cited, llm_trace_metadata)
    """
    prompt = prompt_template.format(
        composite_risk_score=evidence.composite_risk_score,
        risk_category=evidence.risk_category,
        all_signals=", ".join(evidence.all_signals) if evidence.all_signals else "ninguna",
        all_citations="\n- ".join(evidence.all_citations) if evidence.all_citations else "ninguna",
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

        argument, confidence, evidence_cited = _parse_debate_response(response.content)
        return argument, confidence, evidence_cited, llm_trace

    except asyncio.TimeoutError:
        logger.error("llm_timeout_debate", timeout_seconds=AGENT_TIMEOUTS.llm_call)
        llm_trace["llm_response_raw"] = f"TIMEOUT after {AGENT_TIMEOUTS.llm_call}s"
        return None, None, [], llm_trace
    except Exception as e:
        logger.error("llm_call_failed_debate", error=str(e))
        llm_trace["llm_response_raw"] = f"ERROR: {str(e)}"
        return None, None, [], llm_trace


def _parse_debate_response(response_text: str) -> tuple[Optional[str], Optional[float], list[str]]:
    """Parse LLM response to extract argument, confidence, and evidence.

    Two-stage parsing: JSON first, regex fallback.
    """
    # Stage 1: JSON parsing
    data = parse_json_response(response_text, "argument", "debate")
    if data:
        argument = data.get("argument")
        confidence = data.get("confidence")
        evidence_cited = data.get("evidence_cited", [])

        if argument and confidence is not None:
            confidence = clamp_float(confidence)
            if not isinstance(evidence_cited, list):
                evidence_cited = []
            logger.info("debate_response_parsed_json")
            return argument, confidence, evidence_cited

    # Stage 2: Regex fallback
    try:
        confidence_match = re.search(
            r'"?confidence"?\s*:\s*(0\.\d+|1\.0|0|1)', response_text, re.IGNORECASE
        )
        confidence = clamp_float(float(confidence_match.group(1))) if confidence_match else None

        argument_match = re.search(
            r'"?argument"?\s*:\s*"([^"]+)"', response_text, re.IGNORECASE | re.DOTALL
        )
        argument = argument_match.group(1) if argument_match else None

        evidence_match = re.search(
            r'"?evidence_cited"?\s*:\s*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL
        )
        evidence_cited = []
        if evidence_match:
            evidence_cited = re.findall(r'"([^"]+)"', evidence_match.group(1))

        if argument and confidence is not None:
            logger.info("debate_response_parsed_regex", confidence=confidence)
            return argument, confidence, evidence_cited
    except Exception as e:
        logger.error("regex_parse_failed_debate", error=str(e))

    logger.error("debate_response_parse_failed_completely")
    return None, None, []


def generate_fallback_pro_fraud(evidence: AggregatedEvidence) -> dict:
    """Generate deterministic pro-fraud argument when LLM fails."""
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    risk_mappings = {
        "critical": (
            0.90,
            f"La transacción presenta riesgo CRÍTICO (puntaje {composite_score}/100). "
            "Múltiples señales de alto riesgo sugieren alta probabilidad de fraude. "
            "Se recomienda bloqueo inmediato.",
        ),
        "high": (
            0.75,
            f"La transacción presenta riesgo ALTO (puntaje {composite_score}/100). "
            "Señales combinadas indican probabilidad considerable de fraude. "
            "Verificación adicional requerida.",
        ),
        "medium": (
            0.55,
            f"La transacción presenta riesgo MEDIO (puntaje {composite_score}/100). "
            "Algunas señales de riesgo presentes. Monitoreo recomendado.",
        ),
        "low": (
            0.30,
            f"La transacción presenta riesgo BAJO (puntaje {composite_score}/100). "
            "Señales de riesgo mínimas. Probabilidad de fraude reducida.",
        ),
    }

    confidence, argument = risk_mappings.get(
        risk_category,
        (0.50, "Nivel de riesgo no clasificado. Análisis adicional requerido."),
    )
    evidence_cited = evidence.all_signals[:3] if evidence.all_signals else ["risk_score_elevated"]

    logger.info("pro_fraud_fallback_generated", risk_category=risk_category, confidence=confidence)
    return {
        "pro_fraud_argument": argument,
        "pro_fraud_confidence": confidence,
        "pro_fraud_evidence": evidence_cited,
    }


def generate_fallback_pro_customer(evidence: AggregatedEvidence) -> dict:
    """Generate deterministic pro-customer argument when LLM fails."""
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    risk_mappings = {
        "critical": (
            0.20,
            f"Aunque el puntaje de riesgo es crítico ({composite_score}/100), "
            "podría existir un contexto legítimo no capturado por las señales automáticas. "
            "Se requiere revisión humana para confirmar.",
        ),
        "high": (
            0.35,
            f"El puntaje de riesgo es alto ({composite_score}/100), "
            "pero las señales podrían tener explicaciones legítimas. "
            "El contexto del cliente debe considerarse antes de bloquear.",
        ),
        "medium": (
            0.60,
            f"El puntaje de riesgo es medio ({composite_score}/100). "
            "Las señales detectadas podrían corresponder a comportamiento legítimo atípico. "
            "Probabilidad razonable de transacción válida.",
        ),
        "low": (
            0.85,
            f"El puntaje de riesgo es bajo ({composite_score}/100). "
            "Las señales de fraude son mínimas. Alta probabilidad de transacción legítima.",
        ),
    }

    confidence, argument = risk_mappings.get(
        risk_category,
        (0.50, "Nivel de riesgo no clasificado. Revisión recomendada."),
    )

    evidence_cited = ["possible_legitimate_context", "customer_history_unknown"]
    if evidence.all_signals:
        evidence_cited.append(f"review_needed_{evidence.all_signals[0]}")

    logger.info(
        "pro_customer_fallback_generated", risk_category=risk_category, confidence=confidence
    )
    return {
        "pro_customer_argument": argument,
        "pro_customer_confidence": confidence,
        "pro_customer_evidence": evidence_cited,
    }
