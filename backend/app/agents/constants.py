"""Centralized business constants for the fraud detection pipeline.

Single source of truth for all magic numbers, weights, and thresholds
used across agents. Uses Pydantic BaseModel for validation and documentation.
"""

from pydantic import BaseModel


class BehavioralWeights(BaseModel):
    """Additive deviation score factors for behavioral signals."""

    off_hours: float = 0.04
    foreign_country: float = 0.20
    new_device: float = 0.12


class AmountThresholds(BaseModel):
    """Amount ratio thresholds for anomaly detection."""

    high_ratio: float = 3.0  # "amount_3x_above_average" anomaly
    elevated_ratio: float = 2.0  # "high_amount_new_device" combo
    velocity_ratio: float = 5.0  # velocity_alert trigger


class EvidenceWeights(BaseModel):
    """Weights for composite risk score calculation."""

    behavioral: float = 0.30
    policy: float = 0.25
    threat: float = 0.20
    transaction: float = 0.25


class RiskThresholds(BaseModel):
    """Thresholds for risk category classification (0-100 scale)."""

    low_max: float = 30.0
    medium_max: float = 60.0
    high_max: float = 80.0


class SafetyOverrides(BaseModel):
    """Safety override thresholds for the Decision Arbiter."""

    critical_risk_threshold: float = 85.0
    low_confidence_threshold: float = 0.55


class AgentTimeouts(BaseModel):
    """Timeout values in seconds for async operations."""

    llm_call: float = 30.0
    pipeline: float = 60.0
    provider_lookup: float = 15.0


# Singleton instances
BEHAVIORAL_WEIGHTS = BehavioralWeights()
AMOUNT_THRESHOLDS = AmountThresholds()
EVIDENCE_WEIGHTS = EvidenceWeights()
RISK_THRESHOLDS = RiskThresholds()
SAFETY_OVERRIDES = SafetyOverrides()
AGENT_TIMEOUTS = AgentTimeouts()

# Max policies for normalization (based on current policy count)
MAX_POLICIES = 6.0
