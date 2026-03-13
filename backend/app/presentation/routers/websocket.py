"""WebSocket and Analytics endpoints."""

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.infrastructure.adapters.broadcast.connection_manager import manager
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time transaction analysis updates."""
    transaction_id = websocket.query_params.get("transaction_id")
    await manager.connect(websocket)
    if transaction_id:
        await manager.replay_events(websocket, transaction_id)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("ws_received", data=data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("ws_disconnected")


@router.get("/analytics/summary")
async def get_analytics(request: Request):
    """Get aggregated analytics summary."""
    container = request.app.state.container
    return await container.persistence.get_analytics_summary()
