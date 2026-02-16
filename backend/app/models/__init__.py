"""Pydantic v2 models for the fraud detection multi-agent system."""

from .transaction import Transaction, CustomerBehavior
from .analyze_request import AnalyzeRequest
from .signals import TransactionSignals, BehavioralSignals
from .evidence import PolicyMatch, PolicyMatchResult, ThreatSource, ThreatIntelResult, AggregatedEvidence, RiskCategory
from .debate import DebateArguments
from .decision import DecisionType, FraudDecision, ExplanationResult
from .trace import AgentTraceEntry, OrchestratorState
from .policy import PolicyAction, PolicySeverity, PolicyBase, PolicyCreate, PolicyUpdate, PolicyResponse

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
