"""Country risk provider using FATF lists."""

import json
from pathlib import Path

from app.models import ThreatSource, Transaction, TransactionSignals
from app.utils.logger import get_logger

from .base import ThreatProvider

logger = get_logger(__name__)


class CountryRiskProvider(ThreatProvider):
    """Provider that checks countries against FATF blacklist/graylist."""

    def __init__(self, data_file: str = "data/fatf_lists.json"):
        """Initialize provider and load FATF lists from JSON.

        Args:
            data_file: Path to FATF lists JSON (relative to project root)
        """
        self._data_file = data_file
        self._lists = self._load_fatf_lists()
        logger.info(
            "country_risk_provider_initialized",
            blacklist_count=len(self._lists["blacklist"]),
            graylist_count=len(self._lists["graylist"]),
            elevated_count=len(self._lists["elevated_risk"]),
        )

    @property
    def provider_name(self) -> str:
        return "country_risk_fatf"

    def _load_fatf_lists(self) -> dict:
        """Load FATF lists from JSON file."""
        # Path relativo a backend/
        data_path = Path(__file__).parent.parent.parent.parent / self._data_file

        try:
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)

            logger.info("fatf_lists_loaded", source=data.get("source"))
            return data

        except FileNotFoundError:
            logger.error("fatf_lists_not_found", path=str(data_path))
            return {"blacklist": {}, "graylist": {}, "elevated_risk": {}}
        except json.JSONDecodeError as e:
            logger.error("fatf_lists_invalid_json", error=str(e))
            return {"blacklist": {}, "graylist": {}, "elevated_risk": {}}

    async def lookup(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> list[ThreatSource]:
        """Check if transaction country is in FATF lists."""
        country = transaction.country
        sources = []

        # Check blacklist (highest risk)
        if country in self._lists["blacklist"]:
            entry = self._lists["blacklist"][country]
            sources.append(
                ThreatSource(
                    source_name=f"fatf_blacklist_{country}",
                    confidence=entry["risk_score"],
                )
            )
            logger.info(
                "country_risk_detected",
                country=country,
                list="blacklist",
                reason=entry["reason"],
            )

        # Check graylist
        elif country in self._lists["graylist"]:
            entry = self._lists["graylist"][country]
            sources.append(
                ThreatSource(
                    source_name=f"fatf_graylist_{country}",
                    confidence=entry["risk_score"],
                )
            )
            logger.info(
                "country_risk_detected",
                country=country,
                list="graylist",
                reason=entry["reason"],
            )

        # Check elevated risk
        elif country in self._lists["elevated_risk"]:
            entry = self._lists["elevated_risk"][country]
            sources.append(
                ThreatSource(
                    source_name=f"elevated_risk_{country}",
                    confidence=entry["risk_score"],
                )
            )
            logger.debug(
                "country_risk_detected",
                country=country,
                list="elevated_risk",
                reason=entry["reason"],
            )

        return sources
