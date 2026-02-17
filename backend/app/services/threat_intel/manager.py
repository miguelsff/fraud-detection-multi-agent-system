"""Threat Intelligence Manager - orchestrates all providers."""

import asyncio

from app.models import ThreatIntelResult, ThreatSource, Transaction, TransactionSignals
from app.utils.logger import get_logger

from .base import ThreatProvider
from .country_risk import CountryRiskProvider
from .osint_search import OSINTSearchProvider
from .sanctions_screening import SanctionsProvider

logger = get_logger(__name__)


class ThreatIntelManager:
    """Orchestrates multiple threat intelligence providers."""

    def __init__(self):
        """Initialize manager with all active providers."""
        self._providers: list[ThreatProvider] = [
            CountryRiskProvider(),
            OSINTSearchProvider(),
            SanctionsProvider(),
        ]

        logger.info(
            "threat_intel_manager_initialized",
            providers=[p.provider_name for p in self._providers],
        )

    async def analyze(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> ThreatIntelResult:
        """Analyze transaction using all providers.

        Args:
            transaction: Transaction to analyze
            signals: Optional contextual signals

        Returns:
            ThreatIntelResult with aggregated threat level and sources
        """
        # Execute all providers in parallel
        tasks = [provider.lookup(transaction, signals) for provider in self._providers]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all sources (flatten + handle exceptions)
        all_sources = []
        for i, result in enumerate(results):
            provider_name = self._providers[i].provider_name

            if isinstance(result, Exception):
                logger.error(
                    "provider_failed",
                    provider=provider_name,
                    error=str(result),
                )
            elif isinstance(result, list):
                all_sources.extend(result)
                logger.debug(
                    "provider_completed",
                    provider=provider_name,
                    sources_count=len(result),
                )

        # Calculate aggregate threat level
        threat_level = self._calculate_threat_level(all_sources)

        return ThreatIntelResult(
            threat_level=threat_level,
            sources=all_sources,
        )

    def _calculate_threat_level(self, sources: list[ThreatSource]) -> float:
        """Calculate aggregate threat level from all sources.

        Strategy:
        - Use max confidence as primary signal
        - Add 0.1 bonus for each additional source (multi-source)
        - Clamp to 1.0
        """
        if not sources:
            return 0.0

        max_confidence = max(s.confidence for s in sources)
        multi_source_bonus = 0.1 * (len(sources) - 1) if len(sources) > 1 else 0.0

        threat_level = min(1.0, max_confidence + multi_source_bonus)

        return round(threat_level, 2)
