"""External Threat Agent - modular threat intelligence with real OSINT and sanctions screening.

Integrates with multiple threat intelligence providers:
- FATF country risk lists (blacklist, graylist, elevated risk)
- OSINT web search (DuckDuckGo for fraud reports and sanctions alerts)
- OpenSanctions API (sanctions screening - optional with API key)
- LLM interpretation for nuanced threat assessment

Uses a provider-based architecture for easy extension with additional threat sources.
"""

import asyncio
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
from .constants import AGENT_TIMEOUTS
from .threat_utils import calculate_baseline_from_sources, classify_provider_type, parse_threat_analysis

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
    """External Threat agent - modular threat intelligence with real providers."""
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")

        providers = _get_enabled_providers()
        logger.info("providers_initialized", providers=[p.provider_name for p in providers])

        all_sources = await _gather_threat_intel(providers, transaction, transaction_signals)

        if not all_sources:
            logger.info("no_threats_detected", transaction_id=transaction.transaction_id)
            return {"threat_intel": ThreatIntelResult(threat_level=0.0, sources=[])}

        baseline_threat_level = calculate_baseline_from_sources(all_sources)
        logger.debug("baseline_calculated", baseline=baseline_threat_level, sources_count=len(all_sources))

        llm = get_llm()
        llm_threat_level, explanation = await _call_llm_for_threat_analysis(
            llm, transaction, transaction_signals, all_sources, behavioral_signals,
        )

        final_threat_level = llm_threat_level if llm_threat_level is not None else baseline_threat_level

        result = ThreatIntelResult(threat_level=final_threat_level, sources=all_sources)

        logger.info(
            "external_threat_completed",
            threat_level=final_threat_level, baseline=baseline_threat_level,
            sources_count=len(all_sources), llm_used=llm_threat_level is not None,
        )

        return {"threat_intel": result}

    except Exception as e:
        logger.error("external_threat_error", error=str(e), exc_info=True)
        return {"threat_intel": ThreatIntelResult(threat_level=0.0, sources=[])}


def _get_enabled_providers() -> list[ThreatProvider]:
    """Return list of enabled threat intelligence providers based on config."""
    providers: list[ThreatProvider] = [CountryRiskProvider()]

    if settings.threat_intel_enable_osint:
        providers.append(OSINTSearchProvider(max_results=settings.threat_intel_osint_max_results))

    if settings.threat_intel_enable_sanctions and settings.opensanctions_api_key.get_secret_value():
        providers.append(SanctionsProvider())

    return providers


async def _gather_threat_intel(
    providers: list[ThreatProvider],
    transaction: Transaction,
    signals: TransactionSignals | None,
) -> list[ThreatSource]:
    """Execute all providers in parallel with timeout per provider."""
    tasks = [
        asyncio.wait_for(provider.lookup(transaction, signals), timeout=AGENT_TIMEOUTS.provider_lookup)
        for provider in providers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_sources = []
    for provider, result in zip(providers, results):
        if isinstance(result, Exception):
            logger.warning("provider_failed", provider=provider.provider_name, error=str(result), error_type=type(result).__name__)
        elif isinstance(result, list):
            all_sources.extend(result)
            logger.debug("provider_success", provider=provider.provider_name, sources_count=len(result))

    return all_sources


async def _call_llm_for_threat_analysis(
    llm: ChatOllama,
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    threat_sources: list[ThreatSource],
    behavioral_signals=None,
) -> tuple[Optional[float], str]:
    """Call LLM to interpret threat intelligence sources."""
    # Build threat feeds summary
    threat_feeds_summary_parts = []
    for source in threat_sources:
        provider_type = classify_provider_type(source.source_name)
        threat_feeds_summary_parts.append(
            f"- [{provider_type}] {source.source_name}: confianza {source.confidence:.2f}"
        )
    threat_feeds_summary = "\n".join(threat_feeds_summary_parts)

    # Build signals summary
    signals_parts = []
    if transaction_signals:
        signals_parts.append(f"- Ratio de monto: {transaction_signals.amount_ratio:.2f}x")
        signals_parts.append(f"- País extranjero: {transaction_signals.is_foreign}")
        signals_parts.append(f"- Dispositivo desconocido: {transaction_signals.is_unknown_device}")
        signals_parts.append(f"- Riesgo del canal: {transaction_signals.channel_risk}")

    if behavioral_signals:
        is_off_hours = "off_hours_transaction" in behavioral_signals.anomalies
        signals_parts.append(f"- Fuera de horario: {is_off_hours}")

    signals_summary = "\n".join(signals_parts) if signals_parts else "No hay señales disponibles"

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
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=AGENT_TIMEOUTS.llm_call)
        return parse_threat_analysis(response.content)
    except asyncio.TimeoutError:
        logger.error("llm_timeout_threat_analysis", timeout_seconds=AGENT_TIMEOUTS.llm_call)
        return None, "LLM timeout"
    except Exception as e:
        logger.error("llm_call_failed_threat_analysis", error=str(e))
        return None, f"LLM error: {str(e)}"
