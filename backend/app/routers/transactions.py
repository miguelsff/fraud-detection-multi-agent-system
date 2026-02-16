"""Transaction analysis endpoints."""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.orchestrator import analyze_transaction
from ..db.engine import async_session
from ..db.models import AgentTrace, HITLCase, TransactionRecord
from ..dependencies import get_db
from ..models import AnalyzeRequest, FraudDecision
from ..services.ws_manager import manager
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class PaginationParams(BaseModel):
    limit: int = Field(10, ge=1, le=1000)
    offset: int = Field(0, ge=0)


@router.post("/analyze", response_model=FraudDecision)
async def analyze(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run fraud detection pipeline on a transaction."""
    try:
        decision = await analyze_transaction(
            request.transaction,
            request.customer_behavior,
            db,
        )
        logger.info(
            "transaction_analyzed",
            transaction_id=request.transaction.transaction_id,
            decision=decision.decision,
        )
        return decision
    except asyncio.TimeoutError:
        logger.error("analysis_timeout", transaction_id=request.transaction.transaction_id)
        raise HTTPException(status_code=504, detail="Analysis timeout (exceeded configured pipeline timeout)")
    except Exception as e:
        logger.error(
            "analysis_error",
            transaction_id=request.transaction.transaction_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


class AnalyzeStartResponse(BaseModel):
    transaction_id: str
    status: str = "analyzing"


async def _run_analysis_background(transaction, customer_behavior, transaction_id: str):
    """Background task that runs the full pipeline and broadcasts via WS."""
    try:
        async with async_session() as db:
            await analyze_transaction(
                transaction,
                customer_behavior,
                db,
                broadcast_fn=manager.broadcast_agent_event,
            )
    except asyncio.TimeoutError:
        logger.error("background_analysis_timeout", transaction_id=transaction_id)
        await manager.broadcast_agent_event(
            transaction_id, "analysis_error", data={"error": "Analysis timeout"}
        )
    except Exception as e:
        logger.error(
            "background_analysis_error",
            transaction_id=transaction_id,
            error=str(e),
            exc_info=True,
        )
        await manager.broadcast_agent_event(
            transaction_id, "analysis_error", data={"error": str(e)}
        )


@router.post("/analyze/start", response_model=AnalyzeStartResponse, status_code=202)
async def analyze_start(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """Start fraud detection pipeline in background and return immediately.

    Returns 202 Accepted with the transaction_id. The client should listen
    on the WebSocket for real-time agent progress events.
    """
    transaction_id = request.transaction.transaction_id
    background_tasks.add_task(
        _run_analysis_background,
        request.transaction,
        request.customer_behavior,
        transaction_id,
    )
    logger.info("analysis_started_background", transaction_id=transaction_id)
    return AnalyzeStartResponse(transaction_id=transaction_id)


@router.post("/analyze/batch")
async def analyze_batch(
    requests: list[AnalyzeRequest],
    db: AsyncSession = Depends(get_db),
):
    """Batch analyze multiple transactions."""
    results = []
    for req in requests:
        try:
            decision = await analyze_transaction(req.transaction, req.customer_behavior, db)
            results.append({"status": "ok", "decision": decision})
        except Exception as e:
            logger.error(
                "batch_item_failed", transaction_id=req.transaction.transaction_id, error=str(e)
            )
            results.append(
                {
                    "status": "error",
                    "transaction_id": req.transaction.transaction_id,
                    "error": str(e),
                }
            )

    return results


@router.get("/{transaction_id}/result")
async def get_result(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete analysis result from database."""
    stmt = select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Parse analysis_state (may be None for old records)
    state = record.analysis_state or {}

    # Look up associated HITL case (if any)
    hitl_stmt = select(HITLCase).where(HITLCase.transaction_id == transaction_id)
    hitl_result = await db.execute(hitl_stmt)
    hitl_case = hitl_result.scalar_one_or_none()

    hitl_data = None
    if hitl_case:
        hitl_data = {
            "case_id": hitl_case.id,
            "status": hitl_case.status,
            "resolution": hitl_case.resolution,
            "resolved_at": hitl_case.resolved_at.isoformat() if hitl_case.resolved_at else None,
        }

    return {
        "transaction_id": record.transaction_id,
        "transaction": record.raw_data,
        "customer_behavior": state.get("customer_behavior"),
        "transaction_signals": state.get("transaction_signals"),
        "behavioral_signals": state.get("behavioral_signals"),
        "policy_matches": state.get("policy_matches"),
        "threat_intel": state.get("threat_intel"),
        "evidence": state.get("evidence"),
        "debate": state.get("debate"),
        "explanation": state.get("explanation"),
        "decision": record.decision,
        "confidence": float(record.confidence),
        "analyzed_at": record.created_at.isoformat(),
        "hitl": hitl_data,
    }


@router.get("/{transaction_id}/trace")
async def get_trace(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve agent execution trace from database."""
    stmt = select(AgentTrace).where(AgentTrace.transaction_id == transaction_id)
    result = await db.execute(stmt)
    traces = result.scalars().all()

    if not traces:
        raise HTTPException(status_code=404, detail="Trace not found")

    return [
        {
            "agent_name": t.agent_name,
            "duration_ms": t.duration_ms,
            "input_summary": t.input_summary,
            "output_summary": t.output_summary,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            # LLM interaction fields
            "llm_prompt": t.llm_prompt,
            "llm_response_raw": t.llm_response_raw,
            "llm_model": t.llm_model,
            "llm_temperature": float(t.llm_temperature) if t.llm_temperature else None,
            "llm_tokens_used": t.llm_tokens_used,
            # RAG query fields
            "rag_query": t.rag_query,
            "rag_scores": t.rag_scores,
            # Error handling fields
            "fallback_reason": t.fallback_reason,
            "error_details": t.error_details,
        }
        for t in traces
    ]


@router.get("")
async def list_transactions(
    limit: int = Query(default=10, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List analyzed transactions (paginated)."""
    stmt = (
        select(TransactionRecord)
        .order_by(TransactionRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "raw_data": r.raw_data,
            "decision": r.decision,
            "confidence": r.confidence,
            "analyzed_at": r.created_at.isoformat(),
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
