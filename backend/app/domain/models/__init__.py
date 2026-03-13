"""Domain models — Pydantic v2 models for the fraud detection pipeline."""

from .debate import DebateArguments
from .decision import DecisionType, ExplanationResult, FraudDecision
from .evidence import (
    AggregatedEvidence,
    PolicyMatch,
    PolicyMatchResult,
    RiskCategory,
    ThreatIntelResult,
    ThreatSource,
)
from .signals import BehavioralSignals, TransactionSignals
from .trace import AgentTraceEntry, OrchestratorState
from .transaction import CustomerBehavior, Transaction

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
]
