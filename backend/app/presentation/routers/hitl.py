"""Human-in-the-Loop (HITL) endpoints."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter()


@router.get("/queue")
async def get_queue(
    request: Request,
    status: str = Query("pending", pattern="^(pending|resolved)$"),
):
    """Retrieve HITL cases by status."""
    container = request.app.state.container
    return await container.persistence.get_hitl_queue(status=status)


class ResolveRequest(BaseModel):
    """Request model for resolving HITL cases."""

    resolution: str  # "APPROVE" or "BLOCK"
    reason: str


@router.post("/{case_id}/resolve")
async def resolve_case(
    request: Request,
    case_id: int,
    body: ResolveRequest,
):
    """Resolve a HITL case."""
    container = request.app.state.container
    resolution_text = f"{body.resolution}: {body.reason}"
    result = await container.persistence.resolve_hitl_case(case_id, resolution_text)

    if not result:
        raise HTTPException(status_code=404, detail="HITL case not found or already resolved")

    return result
