"""Agent trace entry and LangGraph orchestrator state models."""

import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import TypedDict

from .decision import ExplanationResult, FraudDecision
from .debate import DebateArguments
from .evidence import AggregatedEvidence, PolicyMatchResult, ThreatIntelResult
from .signals import BehavioralSignals, TransactionSignals
from .transaction import CustomerBehavior, Transaction


class AgentTraceEntry(BaseModel):
    """A single trace entry recording an agent's execution."""

    agent_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float = Field(ge=0)
    input_summary: str
    output_summary: str
    status: Literal["success", "error", "timeout", "skipped"]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_name": "transaction_context",
                "timestamp": "2025-01-15T03:15:01Z",
                "duration_ms": 12.5,
                "input_summary": "Transaction T-1001, amount=1800.00 PEN",
                "output_summary": "6 signals generated, 2 flags raised",
                "status": "success",
            }
        }
    )


class OrchestratorState(TypedDict, total=False):
    """LangGraph shared state for the fraud detection pipeline.

    This is a TypedDict (not BaseModel) as required by LangGraph's StateGraph.
    The `trace` field uses an Annotated reducer for append-only semantics.

    Required fields: transaction, customer_behavior, status, trace.
    Optional fields are populated by agents as the pipeline progresses.
    """

    # Required fields
    transaction: Transaction
    customer_behavior: CustomerBehavior
    status: str
    trace: Annotated[list[AgentTraceEntry], operator.add]

    # Phase 1 — Parallel Collection
    transaction_signals: Optional[TransactionSignals]
    behavioral_signals: Optional[BehavioralSignals]
    policy_matches: Optional[PolicyMatchResult]
    threat_intel: Optional[ThreatIntelResult]

    # Phase 2 — Consolidation
    evidence: Optional[AggregatedEvidence]

    # Phase 3 — Adversarial Debate
    debate: Optional[DebateArguments]

    # Phase 4 — Decision
    decision: Optional[FraudDecision]

    # Phase 5 — Explanation
    explanation: Optional[ExplanationResult]
