"""Health check endpoint."""
from datetime import datetime, UTC
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
    }
