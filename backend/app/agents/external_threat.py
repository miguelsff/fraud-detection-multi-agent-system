"""External Threat Agent - modular threat intelligence with real OSINT and sanctions screening.

Integrates with multiple threat intelligence providers:
- FATF country risk lists (blacklist, graylist, elevated risk)
- OSINT web search (DuckDuckGo for fraud reports and sanctions alerts)
- OpenSanctions API (sanctions screening - optional with API key)
- LLM interpretation for nuanced threat assessment

Uses a provider-based architecture for easy extension with additional threat sources.
"""

import asyncio
import json
import re
from typing import Optional

from langchain_ollama import ChatOllama

from ..config import settings
from ..dependencies import get_llm
from ..models import OrchestratorState, ThreatIntelResult, ThreatSource, Transaction, TransactionSignals
from ..services.threat_intel import (
    CountryRiskProvider,
    OSINTSearchProvider,
    SanctionsProvider,
    ThreatProvider,
)
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

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

**TIPO DE FUENTES:**
- FATF Lists: Blacklist/graylist de países de alto riesgo (FATF oficial)
- OSINT Search: Búsqueda web de reportes de fraude y sanciones
- Sanctions API: Screening contra listas de sanciones internacionales

**INSTRUCCIONES:**
1. Evalúa el nivel de amenaza general en una escala de 0.0 a 1.0
   - 0.0-0.3: Amenaza baja (información contextual)
   - 0.3-0.6: Amenaza media (monitoreo recomendado)
   - 0.6-0.8: Amenaza alta (verificación requerida)
   - 0.8-1.0: Amenaza crítica (bloqueo recomendado)

2. Considera:
   - **Tipo de fuente**: FATF es oficial, OSINT es indicativa, Sanctions es crítica
   - **Severidad**: Confidence score de cada fuente (0.0-1.0)
   - **Combinación**: Múltiples fuentes independientes aumentan confianza
   - **Contexto**: Señales de la transacción que agravan/mitigan

**FORMATO DE SALIDA (JSON estricto):**
{{
  "threat_level": 0.75,
  "explanation": "País en blacklist FATF (IR) con confianza 1.0. OSINT confirma alertas de sanciones recientes. Combinación de fuentes oficiales sugiere amenaza alta."
}}

**IMPORTANTE:**
- threat_level debe estar entre 0.0 y 1.0
- Menciona el TIPO de fuente en la explicación (FATF/OSINT/Sanctions)
- Responde SOLO con el JSON, sin texto adicional
"""


@timed_agent("external_threat")
async def external_threat_agent(state: OrchestratorState) -> dict:
    """External Threat agent - modular threat intelligence with real providers.

    Orchestrates multiple threat intelligence providers in parallel:
    - CountryRiskProvider (FATF lists from JSON)
    - OSINTSearchProvider (DuckDuckGo web search - optional)
    - SanctionsProvider (OpenSanctions API - optional)

    Then uses LLM for nuanced interpretation of combined threat signals.

    Args:
        state: Orchestrator state with transaction and signals

    Returns:
        Dict with threat_intel field containing ThreatIntelResult
    """
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")

        # 1. Initialize enabled providers based on config
        providers = _get_enabled_providers()
        logger.info(
            "providers_initialized",
            providers=[p.provider_name for p in providers],
        )

        # 2. Execute ALL providers in PARALLEL with asyncio.gather
        all_sources = await _gather_threat_intel(providers, transaction, transaction_signals)

        # 3. If no threats detected, return empty result
        if not all_sources:
            logger.info(
                "no_threats_detected", transaction_id=transaction.transaction_id
            )
            return {
                "threat_intel": ThreatIntelResult(
                    threat_level=0.0,
                    sources=[],
                )
            }

        # 4. Calculate deterministic baseline from all sources
        baseline_threat_level = _calculate_baseline_from_sources(all_sources)
        logger.debug(
            "baseline_calculated",
            baseline=baseline_threat_level,
            sources_count=len(all_sources),
        )

        # 5. Use LLM for nuanced interpretation
        llm = get_llm()
        llm_threat_level, explanation = await _call_llm_for_threat_analysis(
            llm,
            transaction,
            transaction_signals,
            all_sources,
        )

        # 6. Final threat level: LLM if available, otherwise baseline
        final_threat_level = (
            llm_threat_level if llm_threat_level is not None else baseline_threat_level
        )

        result = ThreatIntelResult(
            threat_level=final_threat_level,
            sources=all_sources,
        )

        logger.info(
            "external_threat_completed",
            threat_level=final_threat_level,
            baseline=baseline_threat_level,
            sources_count=len(all_sources),
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


def _get_enabled_providers() -> list[ThreatProvider]:
    """Return list of enabled threat intelligence providers based on config.

    CountryRiskProvider is always enabled (local JSON, no API required).
    OSINT and Sanctions providers are enabled based on settings.

    Returns:
        List of enabled ThreatProvider instances
    """
    providers: list[ThreatProvider] = []

    # CountryRisk always enabled (local, no API)
    providers.append(CountryRiskProvider())

    # OSINT enabled via config flag
    if settings.threat_intel_enable_osint:
        providers.append(OSINTSearchProvider(max_results=settings.threat_intel_osint_max_results))

    # Sanctions enabled if config flag AND API key present
    if settings.threat_intel_enable_sanctions and settings.opensanctions_api_key:
        providers.append(SanctionsProvider())

    return providers


async def _gather_threat_intel(
    providers: list[ThreatProvider],
    transaction: Transaction,
    signals: TransactionSignals | None,
) -> list[ThreatSource]:
    """Execute all providers in parallel with timeout per provider.

    Uses asyncio.gather with return_exceptions=True to ensure one provider
    failure never blocks others.

    Args:
        providers: List of threat intelligence providers
        transaction: Transaction to analyze
        signals: Optional contextual signals

    Returns:
        Combined list of ThreatSource from all successful providers
    """
    # Create tasks with 15s timeout per provider
    tasks = [
        asyncio.wait_for(
            provider.lookup(transaction, signals),
            timeout=15.0,  # Per-provider timeout
        )
        for provider in providers
    ]

    # Execute in parallel, collect exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine results, log failures
    all_sources = []
    for provider, result in zip(providers, results):
        if isinstance(result, Exception):
            logger.warning(
                "provider_failed",
                provider=provider.provider_name,
                error=str(result),
                error_type=type(result).__name__,
            )
        elif isinstance(result, list):
            all_sources.extend(result)
            logger.debug(
                "provider_success",
                provider=provider.provider_name,
                sources_count=len(result),
            )

    return all_sources


def _calculate_baseline_from_sources(sources: list[ThreatSource]) -> float:
    """Calculate deterministic baseline threat level from all sources.

    Strategy:
    - Use max confidence as primary signal (highest risk source)
    - Add 0.1 bonus for each additional source (multi-source corroboration)
    - Clamp result to [0.0, 1.0]

    Args:
        sources: List of ThreatSource from all providers

    Returns:
        Baseline threat level between 0.0 and 1.0
    """
    if not sources:
        return 0.0

    # Primary signal: highest confidence source
    max_confidence = max(s.confidence for s in sources)

    # Multi-source bonus: +0.1 per additional source (capped)
    multi_source_bonus = 0.1 * (len(sources) - 1) if len(sources) > 1 else 0.0

    # Calculate final level (clamp to 1.0)
    threat_level = min(1.0, max_confidence + multi_source_bonus)

    return round(threat_level, 2)


def _classify_provider_type(source_name: str) -> str:
    """Classify provider type based on source_name for LLM context.

    Args:
        source_name: Name of the threat source (e.g., "fatf_blacklist_IR", "osint_web_search")

    Returns:
        Human-readable provider type: "FATF", "OSINT", or "Sanctions"
    """
    source_lower = source_name.lower()

    if any(keyword in source_lower for keyword in ["fatf", "blacklist", "graylist", "elevated_risk"]):
        return "FATF"
    elif any(keyword in source_lower for keyword in ["osint", "web_search"]):
        return "OSINT"
    elif any(keyword in source_lower for keyword in ["sanctions", "opensanctions"]):
        return "Sanctions"
    else:
        return "Unknown"


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
    # Build threat feeds summary with provider type classification
    threat_feeds_summary_parts = []
    for source in threat_sources:
        # Classify provider type based on source_name
        provider_type = _classify_provider_type(source.source_name)
        threat_feeds_summary_parts.append(
            f"- [{provider_type}] {source.source_name}: confianza {source.confidence:.2f}"
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
