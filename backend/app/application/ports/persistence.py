"""Persistence port — interface for database operations."""

from typing import Any, Protocol


class PersistencePort(Protocol):
    """Port for all database persistence operations.

    Covers transaction records, agent traces, HITL cases, and analytics.
    """

    async def save_transaction_record(
        self,
        transaction_id: str,
        raw_data: dict,
        decision: str,
        confidence: float,
        analysis_state: dict | None = None,
    ) -> None:
        """Persist a transaction record with its analysis state."""
        ...

    async def save_agent_traces(
        self,
        transaction_id: str,
        traces: list[dict],
    ) -> None:
        """Persist agent trace entries for a transaction."""
        ...

    async def create_hitl_case(
        self,
        transaction_id: str,
    ) -> None:
        """Create a Human-in-the-Loop case for manual review."""
        ...

    async def get_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        """Retrieve a transaction record with full analysis state.

        Returns None if not found.
        """
        ...

    async def get_transaction_trace(self, transaction_id: str) -> list[dict] | None:
        """Retrieve agent traces for a transaction.

        Returns None if not found.
        """
        ...

    async def list_transactions(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """List analyzed transactions (paginated, newest first)."""
        ...

    async def get_hitl_queue(self, status: str = "pending") -> list[dict]:
        """Retrieve HITL cases filtered by status."""
        ...

    async def resolve_hitl_case(
        self,
        case_id: int,
        resolution: str,
    ) -> dict | None:
        """Resolve a HITL case. Returns None if case not found or already resolved."""
        ...

    async def get_analytics_summary(self) -> dict:
        """Get aggregated analytics (total, breakdown, avg confidence, etc.)."""
        ...
