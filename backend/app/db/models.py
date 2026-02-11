"""SQLAlchemy ORM models for audit trail and persistence.

These are SQLAlchemy models (for database), NOT Pydantic models (for API).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TransactionRecord(Base):
    """Stores complete transaction data and final decision.

    Attributes:
        id: Primary key
        transaction_id: Unique transaction identifier from external system
        raw_data: Complete transaction payload as JSONB
        decision: Final decision ("approve" or "reject")
        confidence: Confidence score (0.0 - 1.0)
        created_at: Timestamp when record was created
    """

    __tablename__ = "transaction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # PostgreSQL JSONB
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # "approve" or "reject"
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)  # 0.0000 - 1.0000
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_transaction_records_created_at", "created_at"),
        Index("ix_transaction_records_transaction_id", "transaction_id"),
    )

    def __repr__(self) -> str:
        return f"<TransactionRecord(id={self.id}, transaction_id={self.transaction_id}, decision={self.decision})>"


class AgentTrace(Base):
    """Traces individual agent executions within a transaction.

    Attributes:
        id: Primary key
        transaction_id: Reference to parent transaction
        agent_name: Name of the agent (e.g., "PatternAnalyzer", "RiskScorer")
        duration_ms: Execution time in milliseconds
        input_summary: Brief summary of agent input
        output_summary: Brief summary of agent output
        status: Execution status ("success", "error", "timeout")
        created_at: Timestamp when trace was created
    """

    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("transaction_records.transaction_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success", "error", "timeout"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_agent_traces_transaction_id", "transaction_id"),
        Index("ix_agent_traces_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentTrace(id={self.id}, agent={self.agent_name}, status={self.status})>"


class HITLCase(Base):
    """Human-in-the-Loop cases requiring manual review.

    Attributes:
        id: Primary key
        transaction_id: Reference to transaction requiring review
        status: Case status ("pending" or "resolved")
        assigned_to: User/analyst assigned to review (nullable)
        resolution: Final human decision and notes (nullable)
        resolved_at: Timestamp when case was resolved (nullable)
        created_at: Timestamp when case was created
    """

    __tablename__ = "hitl_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("transaction_records.transaction_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # "pending" or "resolved"
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_hitl_cases_transaction_id", "transaction_id"),
        Index("ix_hitl_cases_status", "status"),
        Index("ix_hitl_cases_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<HITLCase(id={self.id}, transaction_id={self.transaction_id}, status={self.status})>"
