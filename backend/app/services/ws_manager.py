"""WebSocket connection manager singleton.

Extracted from routers/websocket.py to avoid circular imports
when the orchestrator needs to broadcast events.
"""

from datetime import UTC, datetime

from fastapi import WebSocket

from ..utils.logger import get_logger

logger = get_logger(__name__)

MAX_BUFFER_SIZE: int = 100
MAX_BUFFER_AGE_SECONDS: int = 3600


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
        """Broadcast a standardised agent pipeline event."""
        message: dict = {
            "transaction_id": transaction_id,
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if agent is not None:
            message["agent"] = agent
        if data is not None:
            message["data"] = data

        self._event_buffers.setdefault(transaction_id, []).append(message)

        if event in ("decision_ready", "analysis_error"):
            self._pending_cleanup.add(transaction_id)

        # Prevent unbounded buffer growth
        if len(self._event_buffers) > MAX_BUFFER_SIZE:
            self._cleanup_stale_buffers()

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

    def _cleanup_stale_buffers(self) -> None:
        """Remove buffers older than MAX_BUFFER_AGE_SECONDS, prioritizing completed analyses."""
        now = datetime.now(UTC)
        stale_ids: list[str] = []

        # First pass: remove completed (pending_cleanup) buffers
        for tid in list(self._pending_cleanup):
            stale_ids.append(tid)

        # Second pass: remove buffers older than TTL
        for tid, events in self._event_buffers.items():
            if tid in stale_ids:
                continue
            if events:
                try:
                    first_ts = datetime.fromisoformat(events[0]["timestamp"])
                    age = (now - first_ts).total_seconds()
                    if age > MAX_BUFFER_AGE_SECONDS:
                        stale_ids.append(tid)
                except (KeyError, ValueError):
                    stale_ids.append(tid)

        removed = 0
        for tid in stale_ids:
            self._event_buffers.pop(tid, None)
            self._pending_cleanup.discard(tid)
            removed += 1

        if removed:
            logger.debug(
                "stale_buffers_cleaned", removed=removed, remaining=len(self._event_buffers)
            )


manager = ConnectionManager()
