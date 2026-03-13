"""WebSocket broadcast adapter — implements BroadcastPort."""

from .connection_manager import ConnectionManager


class WebSocketBroadcastAdapter:
    """BroadcastPort implementation backed by WebSocket ConnectionManager."""

    def __init__(self, connection_manager: ConnectionManager):
        self._manager = connection_manager

    @property
    def manager(self) -> ConnectionManager:
        """Expose the underlying ConnectionManager for WebSocket endpoint use."""
        return self._manager

    async def broadcast_agent_event(
        self,
        transaction_id: str,
        event: str,
        agent: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Broadcast a standardized agent pipeline event via WebSocket."""
        await self._manager.broadcast_agent_event(
            transaction_id=transaction_id,
            event=event,
            agent=agent,
            data=data,
        )
