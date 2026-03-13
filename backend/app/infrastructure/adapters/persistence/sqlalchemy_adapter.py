"""SQLAlchemy persistence adapter — implements PersistencePort."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.utils.logger import get_logger
from .orm_models import AgentTrace, HITLCase, TransactionRecord

logger = get_logger(__name__)


class SQLAlchemyPersistenceAdapter:
    """PersistencePort implementation backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    def _session(self) -> AsyncSession:
        """Create a new session from the factory (caller should use as context manager)."""
        return self._session_factory()

    async def save_transaction_record(
        self,
        transaction_id: str,
        raw_data: dict,
        decision: str,
        confidence: float,
        analysis_state: dict | None = None,
    ) -> None:
        """Persist a transaction record with its analysis state."""
        async with self._session() as session:
            record = TransactionRecord(
                transaction_id=transaction_id,
                raw_data=raw_data,
                decision=decision,
                confidence=confidence,
                analysis_state=analysis_state,
            )
            session.add(record)
            await session.commit()

    async def save_agent_traces(
        self,
        transaction_id: str,
        traces: list[dict],
    ) -> None:
        """Persist agent trace entries for a transaction."""
        async with self._session() as session:
            for entry in traces:
                trace_row = AgentTrace(
                    transaction_id=transaction_id,
                    agent_name=entry["agent_name"],
                    duration_ms=int(entry["duration_ms"]),
                    input_summary=entry.get("input_summary"),
                    output_summary=entry.get("output_summary"),
                    status=entry["status"],
                    llm_prompt=entry.get("llm_prompt"),
                    llm_response_raw=entry.get("llm_response_raw"),
                    llm_model=entry.get("llm_model"),
                    llm_temperature=entry.get("llm_temperature"),
                    llm_tokens_used=entry.get("llm_tokens_used"),
                    rag_query=entry.get("rag_query"),
                    rag_scores=entry.get("rag_scores"),
                    fallback_reason=entry.get("fallback_reason"),
                    error_details=entry.get("error_details"),
                )
                session.add(trace_row)
            await session.commit()

    async def create_hitl_case(self, transaction_id: str) -> None:
        """Create a Human-in-the-Loop case for manual review."""
        async with self._session() as session:
            case = HITLCase(
                transaction_id=transaction_id,
                status="pending",
            )
            session.add(case)
            await session.commit()

    async def get_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        """Retrieve a transaction record with full analysis state."""
        async with self._session() as session:
            stmt = select(TransactionRecord).where(
                TransactionRecord.transaction_id == transaction_id
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return None

            state = record.analysis_state or {}

            # Look up associated HITL case
            hitl_stmt = select(HITLCase).where(HITLCase.transaction_id == transaction_id)
            hitl_result = await session.execute(hitl_stmt)
            hitl_case = hitl_result.scalar_one_or_none()

            hitl_data = None
            if hitl_case:
                hitl_data = {
                    "case_id": hitl_case.id,
                    "status": hitl_case.status,
                    "resolution": hitl_case.resolution,
                    "resolved_at": hitl_case.resolved_at.isoformat()
                    if hitl_case.resolved_at
                    else None,
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

    async def get_transaction_trace(self, transaction_id: str) -> list[dict] | None:
        """Retrieve agent traces for a transaction."""
        async with self._session() as session:
            stmt = select(AgentTrace).where(AgentTrace.transaction_id == transaction_id)
            result = await session.execute(stmt)
            traces = result.scalars().all()

            if not traces:
                return None

            return [
                {
                    "agent_name": t.agent_name,
                    "duration_ms": t.duration_ms,
                    "input_summary": t.input_summary,
                    "output_summary": t.output_summary,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "llm_prompt": t.llm_prompt,
                    "llm_response_raw": t.llm_response_raw,
                    "llm_model": t.llm_model,
                    "llm_temperature": float(t.llm_temperature) if t.llm_temperature else None,
                    "llm_tokens_used": t.llm_tokens_used,
                    "rag_query": t.rag_query,
                    "rag_scores": t.rag_scores,
                    "fallback_reason": t.fallback_reason,
                    "error_details": t.error_details,
                }
                for t in traces
            ]

    async def list_transactions(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """List analyzed transactions (paginated, newest first)."""
        async with self._session() as session:
            stmt = (
                select(TransactionRecord)
                .order_by(TransactionRecord.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
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

    async def get_hitl_queue(self, status: str = "pending") -> list[dict]:
        """Retrieve HITL cases filtered by status."""
        async with self._session() as session:
            stmt = (
                select(HITLCase)
                .where(HITLCase.status == status)
                .order_by(HITLCase.created_at.asc())
            )
            result = await session.execute(stmt)
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

    async def resolve_hitl_case(self, case_id: int, resolution: str) -> dict | None:
        """Resolve a HITL case. Returns None if not found or already resolved."""
        async with self._session() as session:
            stmt = select(HITLCase).where(HITLCase.id == case_id)
            result = await session.execute(stmt)
            case = result.scalar_one_or_none()

            if not case:
                return None

            if case.status != "pending":
                return None

            case.status = "resolved"
            case.resolution = resolution
            case.resolved_at = datetime.now(UTC)

            await session.commit()

            return {"status": "resolved", "case_id": case_id}

    async def get_analytics_summary(self) -> dict:
        """Get aggregated analytics summary."""
        async with self._session() as session:
            # Total count
            total_stmt = select(func.count(TransactionRecord.id))
            total = (await session.execute(total_stmt)).scalar_one()

            # Decisions breakdown
            decisions_stmt = select(
                TransactionRecord.decision, func.count(TransactionRecord.id)
            ).group_by(TransactionRecord.decision)
            decisions_result = await session.execute(decisions_stmt)
            decisions_breakdown = {row[0]: row[1] for row in decisions_result.all()}

            # Avg confidence
            avg_conf_stmt = select(func.avg(TransactionRecord.confidence))
            avg_confidence = (await session.execute(avg_conf_stmt)).scalar_one()

            # Avg processing time (from traces)
            avg_time_stmt = select(func.avg(AgentTrace.duration_ms))
            avg_time = (await session.execute(avg_time_stmt)).scalar_one()

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
