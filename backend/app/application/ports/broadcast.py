"""Broadcast port — interface for real-time event broadcasting."""

from typing import Protocol


class BroadcastPort(Protocol):
    """Port for broadcasting pipeline events to connected clients."""

    async def broadcast_agent_event(
        self,
        transaction_id: str,
        event: str,
        agent: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Broadcast a standardized agent pipeline event.

        Args:
            transaction_id: ID of the transaction being analyzed.
            event: Event type (agent_started, agent_completed, decision_ready, etc.).
            agent: Name of the agent (optional).
            data: Additional event data (optional).
        """
        ...
