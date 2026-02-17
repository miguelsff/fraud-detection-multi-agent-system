"""OSINT search provider using DuckDuckGo."""

import asyncio
from datetime import datetime

from duckduckgo_search import DDGS

from app.config import settings
from app.models import ThreatSource, Transaction, TransactionSignals
from app.utils.logger import get_logger

from .base import ThreatProvider

logger = get_logger(__name__)


class OSINTSearchProvider(ThreatProvider):
    """Provider that searches OSINT sources via DuckDuckGo for threat intelligence."""

    def __init__(self, max_results: int = 5):
        """Initialize OSINT search provider.

        Args:
            max_results: Maximum results per search query
        """
        self._max_results = max_results

    @property
    def provider_name(self) -> str:
        return "osint_web_search"

    async def lookup(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> list[ThreatSource]:
        """Search OSINT sources for transaction-related threats.

        Executes 2-3 queries:
        1. "{merchant_id} fraud report"
        2. "{country} financial fraud alert {year}"
        3. "{country} sanctions risk" (if country has signals)
        """
        if not settings.threat_intel_enable_osint:
            logger.info("osint_search_disabled")
            return []

        try:
            # Build search queries
            queries = self._build_search_queries(transaction, signals)

            # Execute searches with timeout
            all_sources = await asyncio.wait_for(
                self._execute_searches(queries),
                timeout=10.0,  # 10s global timeout
            )

            # Deduplicate
            unique_sources = self._deduplicate_sources(all_sources)

            logger.info(
                "osint_search_completed",
                queries_count=len(queries),
                results_count=len(unique_sources),
            )

            return unique_sources

        except asyncio.TimeoutError:
            logger.warning("osint_search_timeout", timeout_seconds=10)
            return []
        except Exception as e:
            logger.error("osint_search_error", error=str(e), exc_info=True)
            return []

    def _build_search_queries(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None,
    ) -> list[str]:
        """Build 2-3 search queries based on transaction."""
        queries = []
        current_year = datetime.now().year

        # Query 1: Merchant fraud reports
        queries.append(f"{transaction.merchant_id} fraud report")

        # Query 2: Country fraud alerts (recent)
        queries.append(f"{transaction.country} financial fraud alert {current_year}")

        # Query 3: Sanctions risk (only if country signals are present)
        if signals and signals.is_foreign:
            queries.append(f"{transaction.country} sanctions risk")

        return queries[:3]  # Max 3 queries (rate limiting)

    async def _execute_searches(self, queries: list[str]) -> list[ThreatSource]:
        """Execute all search queries in parallel."""
        tasks = [self._search(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_sources = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "osint_query_failed",
                    query_index=i,
                    error=str(result),
                )
            elif isinstance(result, list):
                all_sources.extend(result)

        return all_sources

    async def _search(self, query: str) -> list[ThreatSource]:
        """Execute single DuckDuckGo search query.

        DDGS is synchronous, so execute in thread pool.
        """
        loop = asyncio.get_event_loop()

        try:
            # Run synchronous DDGS in executor
            results = await loop.run_in_executor(
                None, lambda: DDGS().text(query, max_results=self._max_results)
            )

            if not results:
                return []

            # Convert results to ThreatSource
            sources = []
            for result in results:
                confidence = self._calculate_confidence(result)

                if confidence >= 0.4:  # Threshold for relevance
                    sources.append(
                        ThreatSource(
                            source_name="osint_web_search",
                            confidence=confidence,
                        )
                    )

            return sources

        except Exception as e:
            logger.warning("ddg_search_error", query=query[:50], error=str(e))
            return []

    def _calculate_confidence(self, result: dict) -> float:
        """Calculate confidence score based on search result content.

        Args:
            result: DuckDuckGo search result (dict with 'title', 'body')

        Returns:
            Confidence score 0.0-1.0
        """
        text = f"{result.get('title', '')} {result.get('body', '')}".lower()

        # High confidence keywords
        if any(kw in text for kw in ["fraud", "scam", "blacklist"]):
            return 0.7

        # Medium-high confidence
        if any(kw in text for kw in ["sanctions", "warning", "alert"]):
            return 0.6

        # Medium confidence
        if any(kw in text for kw in ["risk", "suspicious", "investigation"]):
            return 0.5

        # Low confidence (generic match)
        return 0.4

    def _deduplicate_sources(self, sources: list[ThreatSource]) -> list[ThreatSource]:
        """Remove duplicate sources, keeping highest confidence."""
        seen = {}
        for source in sources:
            key = source.source_name
            if key not in seen or source.confidence > seen[key].confidence:
                seen[key] = source

        return list(seen.values())
