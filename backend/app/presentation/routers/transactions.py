"""Transaction analysis endpoints."""

import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel

from app.application.agents.orchestrator import analyze_transaction
from app.application.models import AnalyzeRequest, FraudDecision
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _get_container(request: Request):
    """Get the container from app state."""
    return request.app.state.container


@router.post("/analyze", response_model=FraudDecision)
async def analyze(
    request: Request,
    body: AnalyzeRequest,
):
    """Run fraud detection pipeline on a transaction."""
    container = _get_container(request)
    try:
        decision = await analyze_transaction(
            body.transaction,
            body.customer_behavior,
            container=container,
        )
        logger.info(
            "transaction_analyzed",
            transaction_id=body.transaction.transaction_id,
            decision=decision.decision,
        )
        return decision
    except asyncio.TimeoutError:
        logger.error("analysis_timeout", transaction_id=body.transaction.transaction_id)
        raise HTTPException(
            status_code=504, detail="Analysis timeout (exceeded configured pipeline timeout)"
        )
    except Exception as e:
        logger.error(
            "analysis_error",
            transaction_id=body.transaction.transaction_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


class AnalyzeStartResponse(BaseModel):
    transaction_id: str
    status: str = "analyzing"


async def _run_analysis_background(transaction, customer_behavior, transaction_id: str, container):
    """Background task that runs the full pipeline and broadcasts via WS."""
    try:
        await analyze_transaction(
            transaction,
            customer_behavior,
            container=container,
        )
    except asyncio.TimeoutError:
        logger.error("background_analysis_timeout", transaction_id=transaction_id)
        await container.broadcast.broadcast_agent_event(
            transaction_id, "analysis_error", data={"error": "Analysis timeout"}
        )
    except Exception as e:
        logger.error(
            "background_analysis_error",
            transaction_id=transaction_id,
            error=str(e),
            exc_info=True,
        )
        await container.broadcast.broadcast_agent_event(
            transaction_id, "analysis_error", data={"error": str(e)}
        )


@router.post("/analyze/start", response_model=AnalyzeStartResponse, status_code=202)
async def analyze_start(
    request: Request,
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """Start fraud detection pipeline in background and return immediately."""
    container = _get_container(request)
    transaction_id = body.transaction.transaction_id
    background_tasks.add_task(
        _run_analysis_background,
        body.transaction,
        body.customer_behavior,
        transaction_id,
        container,
    )
    logger.info("analysis_started_background", transaction_id=transaction_id)
    return AnalyzeStartResponse(transaction_id=transaction_id)


MAX_BATCH_SIZE: int = 20


@router.post("/analyze/batch")
async def analyze_batch(
    request: Request,
    requests: list[AnalyzeRequest],
):
    """Batch analyze multiple transactions in parallel."""
    container = _get_container(request)
    if len(requests) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(requests)} exceeds maximum of {MAX_BATCH_SIZE}",
        )

    async def _analyze_one(req: AnalyzeRequest) -> dict:
        try:
            decision = await analyze_transaction(
                req.transaction, req.customer_behavior, container=container
            )
            return {"status": "ok", "decision": decision}
        except Exception as e:
            logger.error(
                "batch_item_failed", transaction_id=req.transaction.transaction_id, error=str(e)
            )
            return {
                "status": "error",
                "transaction_id": req.transaction.transaction_id,
                "error": str(e),
            }

    results = await asyncio.gather(*[_analyze_one(req) for req in requests])
    return list(results)


@router.get("/{transaction_id}/result")
async def get_result(
    request: Request,
    transaction_id: str,
):
    """Retrieve complete analysis result from database."""
    container = _get_container(request)
    result = await container.persistence.get_transaction(transaction_id)

    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return result


@router.get("/{transaction_id}/trace")
async def get_trace(
    request: Request,
    transaction_id: str,
):
    """Retrieve agent execution trace from database."""
    container = _get_container(request)
    traces = await container.persistence.get_transaction_trace(transaction_id)

    if not traces:
        raise HTTPException(status_code=404, detail="Trace not found")

    return traces


@router.get("")
async def list_transactions(
    request: Request,
    limit: int = Query(default=10, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List analyzed transactions (paginated)."""
    container = _get_container(request)
    return await container.persistence.list_transactions(limit=limit, offset=offset)
