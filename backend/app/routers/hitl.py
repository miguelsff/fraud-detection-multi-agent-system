"""Human-in-the-Loop (HITL) endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import HITLCase
from ..dependencies import get_db

router = APIRouter()


@router.get("/queue")
async def get_queue(
    status: str = Query("pending", pattern="^(pending|resolved)$"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve HITL cases by status."""
    stmt = select(HITLCase).where(HITLCase.status == status).order_by(HITLCase.created_at.asc())
    result = await db.execute(stmt)
    cases = result.scalars().all()

    return [
        {
            "id": c.id,
            "transaction_id": c.transaction_id,
            "status": c.status,
            "assigned_to": c.assigned_to,
            "resolution": c.resolution,
            "created_at": c.created_at.isoformat(),
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        }
        for c in cases
    ]


class ResolveRequest(BaseModel):
    """Request model for resolving HITL cases."""

    resolution: str  # "APPROVE" or "BLOCK"
    reason: str


@router.post("/{case_id}/resolve")
async def resolve_case(
    case_id: int,
    request: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a HITL case."""
    stmt = select(HITLCase).where(HITLCase.id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="HITL case not found")

    if case.status != "pending":
        raise HTTPException(status_code=400, detail="Case already resolved")

    case.status = "resolved"
    case.resolution = f"{request.resolution}: {request.reason}"
    case.resolved_at = datetime.now(UTC)

    await db.commit()

    return {"status": "resolved", "case_id": case_id}
