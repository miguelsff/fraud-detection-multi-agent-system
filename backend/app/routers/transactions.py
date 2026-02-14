"""Transaction analysis endpoints."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models import Transaction, CustomerBehavior, FraudDecision
from ..agents.orchestrator import analyze_transaction
from ..db.models import TransactionRecord, AgentTrace
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class AnalyzeRequest(BaseModel):
    """Request model for transaction analysis."""
    transaction: Transaction
    customer_behavior: CustomerBehavior


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
        raise HTTPException(status_code=504, detail="Analysis timeout (>60s)")
    except Exception as e:
        logger.error(
            "analysis_error",
            transaction_id=request.transaction.transaction_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
            logger.error("batch_item_failed", transaction_id=req.transaction.transaction_id, error=str(e))
            results.append({
                "status": "error",
                "transaction_id": req.transaction.transaction_id,
                "error": str(e),
            })

    return results


@router.get("/{transaction_id}/result")
async def get_result(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve analysis result from database."""
    stmt = select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": record.transaction_id,
        "raw_data": record.raw_data,
        "decision": record.decision,
        "confidence": record.confidence,
        "created_at": record.created_at.isoformat(),
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
        }
        for t in traces
    ]


@router.get("")
async def list_transactions(
    limit: int = 50,
    offset: int = 0,
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
