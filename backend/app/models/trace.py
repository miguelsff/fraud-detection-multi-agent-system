"""Agent trace entry and LangGraph orchestrator state models."""

import operator
from datetime import UTC, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

from .debate import DebateArguments
from .decision import ExplanationResult, FraudDecision
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
    status: Literal["success", "error", "timeout", "skipped", "fallback"]

    # LLM interaction fields (populated only for LLM-based agents)
    llm_prompt: Optional[str] = None
    llm_response_raw: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_tokens_used: Optional[int] = None

    # RAG query fields (populated only for PolicyRAG agent)
    rag_query: Optional[str] = None
    rag_scores: Optional[dict[str, float]] = None

    # Error handling fields
    fallback_reason: Optional[str] = None
    error_details: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_name": "policy_rag",
                "timestamp": "2025-01-15T03:15:01Z",
                "duration_ms": 125.5,
                "input_summary": '{"transaction_id": "T-1001", "amount": 1800.00}',
                "output_summary": "3 policy matches found",
                "status": "success",
                "llm_prompt": "Analyze this transaction for fraud...",
                "llm_response_raw": "Based on the analysis...",
                "llm_model": "llama3.2",
                "llm_temperature": 0.0,
                "llm_tokens_used": 450,
                "rag_query": "high amount off-hours transaction",
                "rag_scores": {"chunk_001": 0.92, "chunk_045": 0.87},
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
