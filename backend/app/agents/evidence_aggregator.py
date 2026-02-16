"""Evidence Aggregation Agent - consolidates signals from all collection agents.

This agent implements Phase 2 (Consolidation) of the fraud detection pipeline.
It aggregates outputs from all Phase 1 agents:
- TransactionContext (transaction_signals)
- BehavioralPattern (behavioral_signals)
- PolicyRAG (policy_matches)
- ExternalThreat (threat_intel)

The aggregation uses a weighted scoring system with graceful degradation
for missing inputs (e.g., if an upstream agent failed).
"""

from typing import Optional

from ..constants import EVIDENCE_WEIGHTS, MAX_POLICIES, RISK_THRESHOLDS
from ..models import (
    AggregatedEvidence,
    BehavioralSignals,
    OrchestratorState,
    PolicyMatchResult,
    RiskCategory,
    ThreatIntelResult,
    TransactionSignals,
)
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("evidence_aggregation")
async def evidence_aggregation_agent(state: OrchestratorState) -> dict:
    """Evidence Aggregation agent - consolidates all collection agent outputs.

    This is a deterministic agent that aggregates signals, citations, and
    scores from upstream agents using weighted averaging.

    Args:
        state: Orchestrator state with outputs from Phase 1 agents

    Returns:
        Dict with evidence field containing AggregatedEvidence

    Note:
        Implements graceful degradation - if any input is None, uses safe
        defaults (0.0 score, empty list) to ensure pipeline continues.
    """
    try:
        # Extract inputs from state (with None-safe access)
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")
        policy_matches = state.get("policy_matches")
        threat_intel = state.get("threat_intel")

        # 1. Calculate composite risk score (weighted average)
        composite_score = _calculate_composite_score(
            transaction_signals,
            behavioral_signals,
            policy_matches,
            threat_intel,
        )

        # 2. Aggregate all signals/flags
        all_signals = _aggregate_signals(
            transaction_signals,
            behavioral_signals,
            policy_matches,
            threat_intel,
        )

        # 3. Aggregate all citations (policies + threat sources)
        all_citations = _aggregate_citations(
            policy_matches,
            threat_intel,
        )

        # 4. Determine risk category based on composite score
        risk_category = _determine_risk_category(composite_score)

        # Build aggregated evidence
        evidence = AggregatedEvidence(
            composite_risk_score=composite_score,
            all_signals=all_signals,
            all_citations=all_citations,
            risk_category=risk_category,
        )

        logger.info(
            "evidence_aggregation_completed",
            composite_score=composite_score,
            risk_category=risk_category,
            signals_count=len(all_signals),
            citations_count=len(all_citations),
        )

        return {"evidence": evidence}

    except Exception as e:
        logger.error("evidence_aggregation_error", error=str(e), exc_info=True)
        # Fallback to safe default evidence
        return {
            "evidence": AggregatedEvidence(
                composite_risk_score=0.0,
                all_signals=[],
                all_citations=[],
                risk_category="low",
            )
        }


def _calculate_composite_score(
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
    policy_matches: Optional[PolicyMatchResult],
    threat_intel: Optional[ThreatIntelResult],
) -> float:
    """Calculate weighted composite risk score from all signal sources.

    Formula:
        composite_score = (
            behavioral_score × 0.30 +
            policy_score × 0.25 +
            threat_score × 0.20 +
            transaction_score × 0.25
        ) × 100

    Each component is normalized to [0.0, 1.0] before weighting.

    Args:
        transaction_signals: Signals from TransactionContext agent
        behavioral_signals: Signals from BehavioralPattern agent
        policy_matches: Matches from PolicyRAG agent
        threat_intel: Intelligence from ExternalThreat agent

    Returns:
        Composite risk score in range [0.0, 100.0]
    """
    # Extract normalized scores from each source (with None-safe defaults)

    # 1. Behavioral score (already normalized 0.0-1.0)
    behavioral_score = behavioral_signals.deviation_score if behavioral_signals else 0.0

    # 2. Policy score (normalize by max policies)
    if policy_matches and policy_matches.matches:
        # Count of matches normalized by max possible policies
        # Also consider average relevance score
        match_count_score = min(1.0, len(policy_matches.matches) / MAX_POLICIES)
        avg_relevance = sum(m.relevance_score for m in policy_matches.matches) / len(
            policy_matches.matches
        )
        policy_score = (match_count_score + avg_relevance) / 2.0
    else:
        policy_score = 0.0

    # 3. Threat score (already normalized 0.0-1.0)
    threat_score = threat_intel.threat_level if threat_intel else 0.0

    # 4. Transaction score (normalize amount_ratio)
    if transaction_signals:
        # Amount ratio: normalize with sigmoid-like function
        # 1.0x = 0.0, 2.0x = ~0.33, 3.0x = ~0.5, 5.0x = ~0.67, 10.0x = ~0.8
        amount_ratio = transaction_signals.amount_ratio
        amount_score = min(1.0, amount_ratio / 3.0) * 0.5  # Cap at 0.5 for amount alone

        # Add bonus for other transaction flags
        flag_count = len(transaction_signals.flags)
        flag_score = min(0.5, flag_count * 0.1)  # Each flag adds 0.1, max 0.5

        transaction_score = min(1.0, amount_score + flag_score)
    else:
        transaction_score = 0.0

    # Calculate weighted average
    weighted_sum = (
        behavioral_score * EVIDENCE_WEIGHTS.behavioral
        + policy_score * EVIDENCE_WEIGHTS.policy
        + threat_score * EVIDENCE_WEIGHTS.threat
        + transaction_score * EVIDENCE_WEIGHTS.transaction
    )

    # Convert to 0-100 scale and round
    composite_score = round(weighted_sum * 100.0, 2)

    logger.debug(
        "composite_score_calculated",
        behavioral=behavioral_score,
        policy=policy_score,
        threat=threat_score,
        transaction=transaction_score,
        composite=composite_score,
    )

    return composite_score


def _aggregate_signals(
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
    policy_matches: Optional[PolicyMatchResult],
    threat_intel: Optional[ThreatIntelResult],
) -> list[str]:
    """Aggregate all signals/flags from collection agents.

    Args:
        transaction_signals: Transaction context signals
        behavioral_signals: Behavioral pattern signals
        policy_matches: Policy match results
        threat_intel: Threat intelligence results

    Returns:
        Consolidated list of signal strings
    """
    signals = []

    # 1. Transaction signals (flags)
    if transaction_signals and transaction_signals.flags:
        signals.extend(transaction_signals.flags)

    # 2. Behavioral signals (anomalies)
    if behavioral_signals and behavioral_signals.anomalies:
        signals.extend(behavioral_signals.anomalies)

    # 3. Policy matches (as signal tags)
    if policy_matches and policy_matches.matches:
        for match in policy_matches.matches:
            signals.append(f"policy_match_{match.policy_id}")

    # 4. Threat intel sources (as signal tags)
    if threat_intel and threat_intel.sources:
        for source in threat_intel.sources:
            signals.append(f"threat_{source.source_name}")

    # Remove duplicates while preserving order
    seen = set()
    unique_signals = []
    for signal in signals:
        if signal not in seen:
            seen.add(signal)
            unique_signals.append(signal)

    return unique_signals


def _aggregate_citations(
    policy_matches: Optional[PolicyMatchResult],
    threat_intel: Optional[ThreatIntelResult],
) -> list[str]:
    """Aggregate all citations (policy descriptions + threat sources).

    Args:
        policy_matches: Policy match results
        threat_intel: Threat intelligence results

    Returns:
        List of citation strings for audit trail
    """
    citations = []

    # 1. Policy citations (with descriptions)
    if policy_matches and policy_matches.matches:
        for match in policy_matches.matches:
            citation = f"{match.policy_id}: {match.description}"
            citations.append(citation)

    # 2. Threat source citations
    if threat_intel and threat_intel.sources:
        for source in threat_intel.sources:
            citation = f"Threat: {source.source_name} (confidence: {source.confidence:.2f})"
            citations.append(citation)

    return citations


def _determine_risk_category(composite_score: float) -> RiskCategory:
    """Determine risk category based on composite score.

    Thresholds:
    - [0.0, 30.0): low
    - [30.0, 60.0): medium
    - [60.0, 80.0): high
    - [80.0, 100.0]: critical

    Args:
        composite_score: Composite risk score (0.0-100.0)

    Returns:
        Risk category string
    """
    if composite_score < RISK_THRESHOLDS.low_max:
        return "low"
    elif composite_score < RISK_THRESHOLDS.medium_max:
        return "medium"
    elif composite_score < RISK_THRESHOLDS.high_max:
        return "high"
    else:
        return "critical"
