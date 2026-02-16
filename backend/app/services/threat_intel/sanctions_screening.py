"""Sanctions screening provider using OpenSanctions API."""

import asyncio

import httpx

from app.config import settings
from app.models import ThreatSource, Transaction, TransactionSignals
from app.utils.logger import get_logger

from .base import ThreatProvider

logger = get_logger(__name__)


class SanctionsProvider(ThreatProvider):
    """Provider that screens against OpenSanctions API."""

    def __init__(self):
        """Initialize sanctions provider."""
        self._api_key = settings.opensanctions_api_key.get_secret_value()
        self._base_url = "https://api.opensanctions.org"
        self._cache = {}  # Simple in-memory cache

    @property
    def provider_name(self) -> str:
        return "opensanctions_api"

    async def lookup(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> list[ThreatSource]:
        """Screen merchant against OpenSanctions."""
        # Skip if no API key configured
        if not self._api_key:
            logger.debug("opensanctions_skipped", reason="no_api_key")
            return []

        if not settings.threat_intel_enable_sanctions:
            logger.info("opensanctions_disabled")
            return []

        try:
            # Check cache first
            cache_key = f"merchant:{transaction.merchant_id}"
            if cache_key in self._cache:
                logger.debug("opensanctions_cache_hit", merchant_id=transaction.merchant_id)
                return self._cache[cache_key]

            # Search OpenSanctions
            sources = await self._search_opensanctions(transaction.merchant_id)

            # Cache result
            self._cache[cache_key] = sources

            logger.info(
                "opensanctions_completed",
                merchant_id=transaction.merchant_id,
                matches=len(sources),
            )

            return sources

        except Exception as e:
            logger.error("opensanctions_error", error=str(e), exc_info=True)
            return []

    async def _search_opensanctions(self, merchant_id: str) -> list[ThreatSource]:
        """Search OpenSanctions API for merchant."""
        url = f"{self._base_url}/search/default"
        headers = {"Authorization": f"ApiKey {self._api_key}"}
        params = {"q": merchant_id, "limit": 5}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse results
            sources = []
            for match in data.get("results", []):
                score = match.get("score", 0.0)

                # Only include high-confidence matches
                if score >= 0.5:
                    confidence = self._map_score_to_confidence(score)
                    sources.append(
                        ThreatSource(
                            source_name=f"opensanctions_{match.get('schema', 'unknown')}",
                            confidence=confidence,
                        )
                    )

            return sources

        except httpx.HTTPStatusError as e:
            logger.warning("opensanctions_http_error", status=e.response.status_code)
            return []
        except asyncio.TimeoutError:
            logger.warning("opensanctions_timeout")
            return []

    def _map_score_to_confidence(self, score: float) -> float:
        """Map OpenSanctions score (0-1) to confidence (0-1).

        OpenSanctions scores:
        - 1.0 = exact match
        - 0.9-1.0 = very high confidence
        - 0.7-0.9 = high confidence
        - 0.5-0.7 = medium confidence
        """
        if score >= 0.9:
            return 0.95
        elif score >= 0.7:
            return 0.85
        elif score >= 0.5:
            return 0.70
        else:
            return 0.50
