"""Pydantic v2 models for the fraud detection multi-agent system.

Re-exports from domain.models for backward compatibility.
API-specific models (policy, analyze_request) remain here.
"""

# Domain models — re-exported for backward compatibility
from app.domain.models import (
    AgentTraceEntry,
    AggregatedEvidence,
    BehavioralSignals,
    CustomerBehavior,
    DebateArguments,
    DecisionType,
    ExplanationResult,
    FraudDecision,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    RiskCategory,
    ThreatIntelResult,
    ThreatSource,
    Transaction,
    TransactionSignals,
)

# API-specific models (not domain)
from .analyze_request import AnalyzeRequest
from .policy import (
    PolicyAction,
    PolicyBase,
    PolicyCreate,
    PolicyResponse,
    PolicySeverity,
    PolicyUpdate,
)

__all__ = [
    "Transaction",
    "CustomerBehavior",
    "TransactionSignals",
    "BehavioralSignals",
    "PolicyMatch",
    "PolicyMatchResult",
    "ThreatSource",
    "ThreatIntelResult",
    "AggregatedEvidence",
    "RiskCategory",
    "DebateArguments",
    "DecisionType",
    "FraudDecision",
    "ExplanationResult",
    "AgentTraceEntry",
    "OrchestratorState",
    "PolicyAction",
    "PolicySeverity",
    "PolicyBase",
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "AnalyzeRequest",
]
