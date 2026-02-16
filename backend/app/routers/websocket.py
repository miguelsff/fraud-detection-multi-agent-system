"""WebSocket and Analytics endpoints."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentTrace, TransactionRecord
from ..dependencies import get_db
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time transaction analysis updates.

    Emits events like:
    - agent_started: When an agent begins processing
    - agent_completed: When an agent finishes processing
    - decision_ready: When final decision is made
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, broadcast handled by pipeline
            data = await websocket.receive_text()
            logger.debug("ws_received", data=data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("ws_disconnected")


@router.get("/analytics/summary")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    """Get aggregated analytics summary.

    Returns:
        - total_analyzed: Total number of transactions analyzed
        - decisions_breakdown: Count of each decision type
        - avg_confidence: Average confidence score
        - avg_processing_time_ms: Average processing time in milliseconds
        - escalation_rate: Percentage of cases escalated to human review
    """
    # Total count
    total_stmt = select(func.count(TransactionRecord.id))
    total = (await db.execute(total_stmt)).scalar_one()

    # Decisions breakdown
    decisions_stmt = select(TransactionRecord.decision, func.count(TransactionRecord.id)).group_by(
        TransactionRecord.decision
    )
    decisions_result = await db.execute(decisions_stmt)
    decisions_breakdown = {row[0]: row[1] for row in decisions_result.all()}

    # Avg confidence
    avg_conf_stmt = select(func.avg(TransactionRecord.confidence))
    avg_confidence = (await db.execute(avg_conf_stmt)).scalar_one()

    # Avg processing time (from traces)
    avg_time_stmt = select(func.avg(AgentTrace.duration_ms))
    avg_time = (await db.execute(avg_time_stmt)).scalar_one()

    # Escalation rate
    escalate_count = decisions_breakdown.get("ESCALATE_TO_HUMAN", 0)
    escalation_rate = escalate_count / total if total > 0 else 0.0

    return {
        "total_analyzed": total,
        "decisions_breakdown": decisions_breakdown,
        "avg_confidence": round(avg_confidence, 2) if avg_confidence else 0.0,
        "avg_processing_time_ms": round(avg_time, 2) if avg_time else 0.0,
        "escalation_rate": round(escalation_rate, 3),
    }
