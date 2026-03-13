"""Risk scoring domain service — pure functions for evidence aggregation.

Extracted from agents/evidence_aggregator.py. No I/O, no infrastructure imports.
"""

from ..constants import EVIDENCE_WEIGHTS, MAX_POLICIES, RISK_THRESHOLDS
from ..models import (
    BehavioralSignals,
    PolicyMatchResult,
    RiskCategory,
    ThreatIntelResult,
    TransactionSignals,
)


def calculate_composite_score(
    transaction_signals: TransactionSignals | None,
    behavioral_signals: BehavioralSignals | None,
    policy_matches: PolicyMatchResult | None,
    threat_intel: ThreatIntelResult | None,
) -> float:
    """Calculate weighted composite risk score from all signal sources.

    Formula:
        composite_score = (
            behavioral_score * 0.30 +
            policy_score * 0.25 +
            threat_score * 0.20 +
            transaction_score * 0.25
        ) * 100

    Each component is normalized to [0.0, 1.0] before weighting.

    Returns:
        Composite risk score in range [0.0, 100.0]
    """
    behavioral_score = behavioral_signals.deviation_score if behavioral_signals else 0.0

    if policy_matches and policy_matches.matches:
        match_count_score = min(1.0, len(policy_matches.matches) / MAX_POLICIES)
        avg_relevance = sum(m.relevance_score for m in policy_matches.matches) / len(
            policy_matches.matches
        )
        policy_score = (match_count_score + avg_relevance) / 2.0
    else:
        policy_score = 0.0

    threat_score = threat_intel.threat_level if threat_intel else 0.0

    if transaction_signals:
        amount_ratio = transaction_signals.amount_ratio
        amount_score = (
            min(1.0, amount_ratio / EVIDENCE_WEIGHTS.amount_normalization_factor)
            * EVIDENCE_WEIGHTS.amount_max_contribution
        )
        flag_count = len(transaction_signals.flags)
        flag_score = min(
            EVIDENCE_WEIGHTS.flag_max_contribution,
            flag_count * EVIDENCE_WEIGHTS.flag_weight,
        )
        transaction_score = min(1.0, amount_score + flag_score)
    else:
        transaction_score = 0.0

    weighted_sum = (
        behavioral_score * EVIDENCE_WEIGHTS.behavioral
        + policy_score * EVIDENCE_WEIGHTS.policy
        + threat_score * EVIDENCE_WEIGHTS.threat
        + transaction_score * EVIDENCE_WEIGHTS.transaction
    )

    return round(weighted_sum * 100.0, 2)


def aggregate_signals(
    transaction_signals: TransactionSignals | None,
    behavioral_signals: BehavioralSignals | None,
    policy_matches: PolicyMatchResult | None,
    threat_intel: ThreatIntelResult | None,
) -> list[str]:
    """Aggregate all signals/flags from collection agents.

    Returns:
        Consolidated list of unique signal strings (order preserved).
    """
    signals: list[str] = []

    if transaction_signals and transaction_signals.flags:
        signals.extend(transaction_signals.flags)

    if behavioral_signals and behavioral_signals.anomalies:
        signals.extend(behavioral_signals.anomalies)

    if policy_matches and policy_matches.matches:
        for match in policy_matches.matches:
            signals.append(f"policy_match_{match.policy_id}")

    if threat_intel and threat_intel.sources:
        for source in threat_intel.sources:
            signals.append(f"threat_{source.source_name}")

    seen: set[str] = set()
    unique_signals: list[str] = []
    for signal in signals:
        if signal not in seen:
            seen.add(signal)
            unique_signals.append(signal)

    return unique_signals


def aggregate_citations(
    policy_matches: PolicyMatchResult | None,
    threat_intel: ThreatIntelResult | None,
) -> list[str]:
    """Aggregate all citations (policy descriptions + threat sources).

    Returns:
        List of citation strings for audit trail.
    """
    citations: list[str] = []

    if policy_matches and policy_matches.matches:
        for match in policy_matches.matches:
            citations.append(f"{match.policy_id}: {match.description}")

    if threat_intel and threat_intel.sources:
        for source in threat_intel.sources:
            citations.append(f"Threat: {source.source_name} (confidence: {source.confidence:.2f})")

    return citations


def determine_risk_category(composite_score: float) -> RiskCategory:
    """Determine risk category based on composite score.

    Thresholds:
    - [0.0, 30.0): low
    - [30.0, 60.0): medium
    - [60.0, 80.0): high
    - [80.0, 100.0]: critical
    """
    if composite_score < RISK_THRESHOLDS.low_max:
        return "low"
    elif composite_score < RISK_THRESHOLDS.medium_max:
        return "medium"
    elif composite_score < RISK_THRESHOLDS.high_max:
        return "high"
    else:
        return "critical"
