"""Base interface for threat intelligence providers."""

from abc import ABC, abstractmethod

from app.models import ThreatSource, Transaction, TransactionSignals


class ThreatProvider(ABC):
    """Abstract base class for all threat intelligence providers.

    Each provider must:
    - Implement async lookup() method
    - Return list[ThreatSource] or empty list on failure
    - Handle its own errors (never raise exceptions to caller)
    - Log with structlog for observability
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider (used in logs and traces)."""

    @abstractmethod
    async def lookup(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> list[ThreatSource]:
        """Lookup threats related to this transaction.

        Args:
            transaction: Transaction to analyze
            signals: Optional contextual signals from transaction_context agent

        Returns:
            List of ThreatSource objects. Empty list if no threats or on error.

        Note:
            Must handle all exceptions internally. Never propagate to caller.
        """
