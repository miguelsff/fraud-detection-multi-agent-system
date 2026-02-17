"""WebSocket connection manager singleton.

Extracted from routers/websocket.py to avoid circular imports
when the orchestrator needs to broadcast events.
"""

from datetime import UTC, datetime

from fastapi import WebSocket

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._event_buffers: dict[str, list[dict]] = {}
        self._pending_cleanup: set[str] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients.

        Resilient: disconnects broken sockets without crashing.
        """
        broken: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                broken.append(connection)

        for ws in broken:
            self.disconnect(ws)

    async def broadcast_agent_event(
        self,
        transaction_id: str,
        event: str,
        agent: str | None = None,
        data: dict | None = None,
    ):
        """Broadcast a standardised agent pipeline event.

        Args:
            transaction_id: The transaction being analysed.
            event: Event type (agent_started, agent_completed, decision_ready, analysis_error).
            agent: Agent name (e.g. "TransactionContext").
            data: Optional extra payload.
        """
        message: dict = {
            "transaction_id": transaction_id,
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if agent is not None:
            message["agent"] = agent
        if data is not None:
            message["data"] = data

        # Buffer event for late-connecting clients
        self._event_buffers.setdefault(transaction_id, []).append(message)

        # Mark buffer for cleanup when analysis finishes
        if event in ("decision_ready", "analysis_error"):
            self._pending_cleanup.add(transaction_id)

        await self.broadcast(message)

    async def replay_events(self, websocket: WebSocket, transaction_id: str):
        """Send all buffered events for a transaction to a newly connected client."""
        events = self._event_buffers.get(transaction_id, [])
        for event in events:
            try:
                await websocket.send_json(event)
            except Exception:
                break
        # Clean up completed analysis buffers after replay
        if transaction_id in self._pending_cleanup:
            self._event_buffers.pop(transaction_id, None)
            self._pending_cleanup.discard(transaction_id)


manager = ConnectionManager()
