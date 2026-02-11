"""Pydantic v2 models for the fraud detection multi-agent system."""

from .transaction import Transaction, CustomerBehavior
from .signals import TransactionSignals, BehavioralSignals
from .evidence import PolicyMatch, PolicyMatchResult, ThreatSource, ThreatIntelResult, AggregatedEvidence
from .debate import DebateArguments
from .decision import FraudDecision, ExplanationResult
from .trace import AgentTraceEntry, OrchestratorState

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
    "DebateArguments",
    "FraudDecision",
    "ExplanationResult",
    "AgentTraceEntry",
    "OrchestratorState",
]
