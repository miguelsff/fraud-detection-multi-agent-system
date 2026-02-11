"""External Threat Agent - simulated threat intelligence lookup and LLM interpretation.

NOTE: This is a SIMULATED implementation for portfolio demonstration.
In production, this would integrate with real threat intelligence APIs such as:
- OSINT feeds (OpenPhish, URLhaus, abuse.ch)
- Commercial threat intel (ThreatMetrix, Recorded Future, Chainalysis)
- Payment network watchlists (Visa RiskRecon, Mastercard MATCH)
- Government sanctions lists (OFAC SDN, EU Consolidated List)
"""

import asyncio
import json
import re
from typing import Optional

from langchain_ollama import ChatOllama

from ..dependencies import get_llm
from ..models import OrchestratorState, ThreatIntelResult, ThreatSource, Transaction, TransactionSignals
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

# ============================================================================
# SIMULATED THREAT FEEDS (Hardcoded for Portfolio Demo)
# ============================================================================
# In production, these would be:
# - Real-time API calls to threat intelligence providers
# - Database lookups of merchant watchlists
# - OSINT aggregation services
# - Payment network fraud alerts
# ============================================================================

THREAT_FEEDS = {
    # High-risk countries (simplified for demo - based on FATF gray/blacklist)
    "high_risk_countries": {
        "KP": {"risk_score": 1.0, "reason": "FATF blacklist - high money laundering risk"},
        "IR": {"risk_score": 1.0, "reason": "FATF blacklist - sanctions risk"},
        "MM": {"risk_score": 0.9, "reason": "FATF graylist - AML deficiencies"},
        "PK": {"risk_score": 0.7, "reason": "FATF graylist - terrorism financing concerns"},
        "NG": {"risk_score": 0.6, "reason": "High fraud jurisdiction"},
        "RU": {"risk_score": 0.8, "reason": "Sanctions risk - OFAC"},
        "CN": {"risk_score": 0.5, "reason": "Capital controls - unusual cross-border activity"},
        "VE": {"risk_score": 0.9, "reason": "FATF graylist - weak AML controls"},
    },
    # Medium-risk countries (emerging markets with elevated fraud)
    "medium_risk_countries": {
        "BR": {"risk_score": 0.4, "reason": "Elevated fraud rates - e-commerce"},
        "IN": {"risk_score": 0.3, "reason": "High volume of card testing attacks"},
        "ID": {"risk_score": 0.4, "reason": "Identity theft concerns"},
        "PH": {"risk_score": 0.3, "reason": "Social engineering fraud"},
        "MX": {"risk_score": 0.4, "reason": "Organized crime involvement"},
    },
    # Merchant watchlist (reported merchants)
    "merchant_watchlist": {
        "M-999": {"risk_score": 0.95, "reason": "Multiple fraud reports - chargeback rate >5%"},
        "M-888": {"risk_score": 0.85, "reason": "Suspected front company"},
        "M-777": {"risk_score": 0.70, "reason": "Unusual transaction patterns"},
        "M-666": {"risk_score": 0.90, "reason": "Operating in sanctioned sector"},
    },
    # Known fraud patterns (device/IP combinations)
    "fraud_patterns": {
        "web_unknown_foreign": {
            "risk_score": 0.6,
            "reason": "High-risk channel from foreign country",
        },
        "high_amount_new_device": {
            "risk_score": 0.7,
            "reason": "Large transaction from unrecognized device",
        },
        "off_hours_foreign": {
            "risk_score": 0.5,
            "reason": "Unusual timing from foreign location",
        },
    },
}

THREAT_ANALYSIS_PROMPT = """Eres un analista de inteligencia de amenazas financieras. Evalúa el nivel de amenaza externa para esta transacción basándote en las fuentes de inteligencia disponibles.

**TRANSACCIÓN:**
- ID: {transaction_id}
- Monto: {amount} {currency}
- País: {country}
- Canal: {channel}
- Merchant: {merchant_id}

**FUENTES DE INTELIGENCIA DE AMENAZAS DETECTADAS:**
{threat_feeds_summary}

**SEÑALES DE CONTEXTO:**
{signals_summary}

**INSTRUCCIONES:**
1. Evalúa el nivel de amenaza general en una escala de 0.0 a 1.0
   - 0.0-0.3: Amenaza baja (información contextual)
   - 0.3-0.6: Amenaza media (monitoreo recomendado)
   - 0.6-0.8: Amenaza alta (verificación requerida)
   - 0.8-1.0: Amenaza crítica (bloqueo recomendado)

2. Considera:
   - Severidad de cada fuente de inteligencia
   - Combinación de múltiples señales
   - Contexto de la transacción

**FORMATO DE SALIDA (JSON estricto):**
{{
  "threat_level": 0.75,
  "explanation": "País de alto riesgo (IR) con merchant en watchlist (M-999). Combinación sugiere amenaza alta."
}}

**IMPORTANTE:**
- threat_level debe estar entre 0.0 y 1.0
- Responde SOLO con el JSON, sin texto adicional
"""


@timed_agent("external_threat")
async def external_threat_agent(state: OrchestratorState) -> dict:
    """External Threat agent - simulated threat intelligence lookup.

    Simulates external threat intelligence gathering by checking hardcoded
    threat feeds and using LLM to interpret combined threat signals.

    NOTE: In production, this would query real threat intelligence APIs.

    Args:
        state: Orchestrator state with transaction and signals

    Returns:
        Dict with threat_intel field containing ThreatIntelResult
    """
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")

        # 1. Lookup in simulated threat feeds
        threat_sources = _lookup_threat_feeds(transaction, transaction_signals)

        # 2. If no threats detected, return empty result
        if not threat_sources:
            logger.info("no_threats_detected", transaction_id=transaction.transaction_id)
            return {
                "threat_intel": ThreatIntelResult(
                    threat_level=0.0,
                    sources=[],
                )
            }

        # 3. Calculate deterministic baseline threat level
        baseline_threat_level = _calculate_baseline_threat_level(threat_sources)

        # 4. Use LLM for nuanced interpretation
        llm = get_llm()
        llm_threat_level, explanation = await _call_llm_for_threat_analysis(
            llm,
            transaction,
            transaction_signals,
            threat_sources,
        )

        # 5. Use LLM result if available, otherwise fallback to baseline
        final_threat_level = llm_threat_level if llm_threat_level is not None else baseline_threat_level

        result = ThreatIntelResult(
            threat_level=final_threat_level,
            sources=threat_sources,
        )

        logger.info(
            "external_threat_completed",
            threat_level=final_threat_level,
            sources_count=len(threat_sources),
            llm_used=llm_threat_level is not None,
        )

        return {"threat_intel": result}

    except Exception as e:
        logger.error("external_threat_error", error=str(e), exc_info=True)
        # Fallback to empty result
        return {
            "threat_intel": ThreatIntelResult(
                threat_level=0.0,
                sources=[],
            )
        }


def _lookup_threat_feeds(
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
) -> list[ThreatSource]:
    """Lookup transaction attributes in simulated threat feeds.

    Args:
        transaction: Transaction to check
        transaction_signals: Optional contextual signals

    Returns:
        List of ThreatSource objects for detected threats
    """
    sources = []

    # Check country risk
    country = transaction.country
    if country in THREAT_FEEDS["high_risk_countries"]:
        threat = THREAT_FEEDS["high_risk_countries"][country]
        sources.append(
            ThreatSource(
                source_name=f"high_risk_country_{country}",
                confidence=threat["risk_score"],
            )
        )
        logger.debug(
            "threat_detected",
            source="high_risk_country",
            country=country,
            reason=threat["reason"],
        )
    elif country in THREAT_FEEDS["medium_risk_countries"]:
        threat = THREAT_FEEDS["medium_risk_countries"][country]
        sources.append(
            ThreatSource(
                source_name=f"medium_risk_country_{country}",
                confidence=threat["risk_score"],
            )
        )
        logger.debug(
            "threat_detected",
            source="medium_risk_country",
            country=country,
            reason=threat["reason"],
        )

    # Check merchant watchlist
    merchant_id = transaction.merchant_id
    if merchant_id in THREAT_FEEDS["merchant_watchlist"]:
        threat = THREAT_FEEDS["merchant_watchlist"][merchant_id]
        sources.append(
            ThreatSource(
                source_name=f"merchant_watchlist_{merchant_id}",
                confidence=threat["risk_score"],
            )
        )
        logger.debug(
            "threat_detected",
            source="merchant_watchlist",
            merchant_id=merchant_id,
            reason=threat["reason"],
        )

    # Check fraud patterns (requires signals)
    if transaction_signals:
        # Pattern: web_unknown from foreign country
        if (
            transaction_signals.channel_risk == "high"
            and transaction_signals.is_foreign
        ):
            pattern = THREAT_FEEDS["fraud_patterns"]["web_unknown_foreign"]
            sources.append(
                ThreatSource(
                    source_name="fraud_pattern_web_unknown_foreign",
                    confidence=pattern["risk_score"],
                )
            )

        # Pattern: high amount with unknown device
        if (
            transaction_signals.amount_ratio > 3.0
            and transaction_signals.is_unknown_device
        ):
            pattern = THREAT_FEEDS["fraud_patterns"]["high_amount_new_device"]
            sources.append(
                ThreatSource(
                    source_name="fraud_pattern_high_amount_new_device",
                    confidence=pattern["risk_score"],
                )
            )

        # Pattern: off-hours from foreign country
        if transaction_signals.is_off_hours and transaction_signals.is_foreign:
            pattern = THREAT_FEEDS["fraud_patterns"]["off_hours_foreign"]
            sources.append(
                ThreatSource(
                    source_name="fraud_pattern_off_hours_foreign",
                    confidence=pattern["risk_score"],
                )
            )

    return sources


def _calculate_baseline_threat_level(sources: list[ThreatSource]) -> float:
    """Calculate baseline threat level from sources (deterministic fallback).

    Uses weighted average with emphasis on highest confidence sources.

    Args:
        sources: List of ThreatSource objects

    Returns:
        Threat level between 0.0 and 1.0
    """
    if not sources:
        return 0.0

    # Use max confidence as primary signal
    max_confidence = max(s.confidence for s in sources)

    # If multiple sources, increase threat level
    multi_source_bonus = 0.1 * (len(sources) - 1) if len(sources) > 1 else 0.0

    # Calculate final level (clamped to 1.0)
    threat_level = min(1.0, max_confidence + multi_source_bonus)

    return round(threat_level, 2)


async def _call_llm_for_threat_analysis(
    llm: ChatOllama,
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    threat_sources: list[ThreatSource],
) -> tuple[Optional[float], str]:
    """Call LLM to interpret threat intelligence sources.

    Args:
        llm: ChatOllama instance
        transaction: Transaction object
        transaction_signals: Optional contextual signals
        threat_sources: Detected threat sources

    Returns:
        Tuple of (threat_level, explanation). threat_level is None if LLM fails.
    """
    # Build threat feeds summary
    threat_feeds_summary_parts = []
    for source in threat_sources:
        threat_feeds_summary_parts.append(
            f"- {source.source_name}: confianza {source.confidence:.2f}"
        )
    threat_feeds_summary = "\n".join(threat_feeds_summary_parts)

    # Build signals summary
    signals_parts = []
    if transaction_signals:
        signals_parts.append(f"- Ratio de monto: {transaction_signals.amount_ratio:.2f}x")
        signals_parts.append(f"- Fuera de horario: {transaction_signals.is_off_hours}")
        signals_parts.append(f"- País extranjero: {transaction_signals.is_foreign}")
        signals_parts.append(f"- Dispositivo desconocido: {transaction_signals.is_unknown_device}")
        signals_parts.append(f"- Riesgo del canal: {transaction_signals.channel_risk}")
    signals_summary = "\n".join(signals_parts) if signals_parts else "No hay señales disponibles"

    # Format prompt
    prompt = THREAT_ANALYSIS_PROMPT.format(
        transaction_id=transaction.transaction_id,
        amount=transaction.amount,
        currency=transaction.currency,
        country=transaction.country,
        channel=transaction.channel,
        merchant_id=transaction.merchant_id,
        threat_feeds_summary=threat_feeds_summary,
        signals_summary=signals_summary,
    )

    try:
        # Call LLM with timeout
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=30.0)
        response_text = response.content

        # Parse response
        threat_level, explanation = _parse_threat_analysis_response(response_text)
        return threat_level, explanation

    except asyncio.TimeoutError:
        logger.error("llm_timeout_threat_analysis", timeout_seconds=30)
        return None, "LLM timeout"
    except Exception as e:
        logger.error("llm_call_failed_threat_analysis", error=str(e))
        return None, f"LLM error: {str(e)}"


def _parse_threat_analysis_response(response_text: str) -> tuple[Optional[float], str]:
    """Parse LLM response to extract threat level and explanation.

    Args:
        response_text: Raw text response from LLM

    Returns:
        Tuple of (threat_level, explanation). threat_level is None if parsing fails.
    """
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*"threat_level".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        # Extract and validate threat_level
        threat_level = float(data["threat_level"])
        threat_level = max(0.0, min(1.0, threat_level))  # Clamp to [0.0, 1.0]

        explanation = data.get("explanation", "No explanation provided")

        logger.info("llm_threat_response_parsed_json", threat_level=threat_level)
        return threat_level, explanation

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("json_parse_failed_threat_analysis", error=str(e))

        # Regex fallback: look for "threat_level": 0.XX
        pattern = r'"?threat_level"?\s*:\s*(0\.\d+|1\.0|0|1)'
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            threat_level = float(match.group(1))
            threat_level = max(0.0, min(1.0, threat_level))
            logger.info("llm_threat_response_parsed_regex", threat_level=threat_level)
            return threat_level, "Extracted via regex"

        return None, "Parse failed"
