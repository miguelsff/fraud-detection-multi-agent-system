"""Tests for the Evidence Aggregation agent."""

from datetime import datetime, timezone

import pytest

from app.agents.evidence_aggregator import (
    _aggregate_citations,
    _aggregate_signals,
    _calculate_composite_score,
    _determine_risk_category,
    evidence_aggregation_agent,
)
from app.models import (
    BehavioralSignals,
    CustomerBehavior,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    ThreatIntelResult,
    ThreatSource,
    Transaction,
    TransactionSignals,
)


@pytest.mark.unit
def test_calculate_composite_score_all_inputs():
    """Test composite score calculation with all inputs provided."""
    transaction_signals = TransactionSignals(
        amount_ratio=3.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["high_amount_ratio_3.0x", "transaction_off_hours"],
    )

    behavioral_signals = BehavioralSignals(
        deviation_score=0.8,
        anomalies=["amount_spike", "unusual_hour"],
        velocity_alert=True,
    )

    policy_matches = PolicyMatchResult(
        matches=[
            PolicyMatch(
                policy_id="FP-01",
                description="High amount",
                relevance_score=0.9,
            ),
            PolicyMatch(
                policy_id="FP-04",
                description="Off hours",
                relevance_score=0.75,
            ),
        ],
        chunk_ids=["fp-01-section-0", "fp-04-section-0"],
    )

    threat_intel = ThreatIntelResult(
        threat_level=0.7,
        sources=[
            ThreatSource(source_name="high_risk_country_IR", confidence=0.8)
        ],
    )

    score = _calculate_composite_score(
        transaction_signals,
        behavioral_signals,
        policy_matches,
        threat_intel,
    )

    # Score should be high given all high-risk inputs
    assert 60.0 <= score <= 100.0
    assert isinstance(score, float)


@pytest.mark.unit
def test_calculate_composite_score_low_risk():
    """Test composite score with low-risk inputs."""
    transaction_signals = TransactionSignals(
        amount_ratio=1.0,
        is_off_hours=False,
        is_foreign=False,
        is_unknown_device=False,
        channel_risk="low",
        flags=[],
    )

    behavioral_signals = BehavioralSignals(
        deviation_score=0.1,
        anomalies=[],
        velocity_alert=False,
    )

    policy_matches = PolicyMatchResult(matches=[], chunk_ids=[])

    threat_intel = ThreatIntelResult(threat_level=0.0, sources=[])

    score = _calculate_composite_score(
        transaction_signals,
        behavioral_signals,
        policy_matches,
        threat_intel,
    )

    # Score should be low
    assert score < 30.0


@pytest.mark.unit
def test_calculate_composite_score_none_inputs():
    """Test graceful degradation with None inputs."""
    score = _calculate_composite_score(None, None, None, None)

    # Should return 0.0 when all inputs are None
    assert score == 0.0


@pytest.mark.unit
def test_calculate_composite_score_partial_inputs():
    """Test score calculation with some inputs missing."""
    transaction_signals = TransactionSignals(
        amount_ratio=2.5,
        is_off_hours=False,
        is_foreign=True,
        is_unknown_device=False,
        channel_risk="medium",
        flags=["elevated_amount_2.5x"],
    )

    # Only transaction signals provided, rest are None
    score = _calculate_composite_score(transaction_signals, None, None, None)

    # Should have some score from transaction signals only
    assert 0.0 < score < 50.0


@pytest.mark.unit
def test_aggregate_signals_all_sources():
    """Test signal aggregation from all sources."""
    transaction_signals = TransactionSignals(
        amount_ratio=3.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["high_amount_ratio_3.0x", "transaction_off_hours"],
    )

    behavioral_signals = BehavioralSignals(
        deviation_score=0.8,
        anomalies=["amount_spike", "unusual_hour"],
        velocity_alert=True,
    )

    policy_matches = PolicyMatchResult(
        matches=[
            PolicyMatch(
                policy_id="FP-01",
                description="Test",
                relevance_score=0.9,
            )
        ],
        chunk_ids=["fp-01-section-0"],
    )

    threat_intel = ThreatIntelResult(
        threat_level=0.7,
        sources=[
            ThreatSource(source_name="high_risk_country_IR", confidence=0.8)
        ],
    )

    signals = _aggregate_signals(
        transaction_signals,
        behavioral_signals,
        policy_matches,
        threat_intel,
    )

    # Should have signals from all sources
    assert len(signals) > 0
    assert "high_amount_ratio_3.0x" in signals
    assert "amount_spike" in signals
    assert "policy_match_FP-01" in signals
    assert "threat_high_risk_country_IR" in signals


@pytest.mark.unit
def test_aggregate_signals_no_duplicates():
    """Test that duplicate signals are removed."""
    transaction_signals = TransactionSignals(
        amount_ratio=3.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["flag1", "flag2", "flag1"],  # Duplicate flag1
    )

    signals = _aggregate_signals(transaction_signals, None, None, None)

    # Should have no duplicates
    assert len(signals) == len(set(signals))
    assert signals.count("flag1") == 1


@pytest.mark.unit
def test_aggregate_signals_empty_inputs():
    """Test signal aggregation with empty inputs."""
    signals = _aggregate_signals(None, None, None, None)

    assert signals == []


@pytest.mark.unit
def test_aggregate_citations_with_policies_and_threats():
    """Test citation aggregation from policies and threats."""
    policy_matches = PolicyMatchResult(
        matches=[
            PolicyMatch(
                policy_id="FP-01",
                description="High amount transaction detected",
                relevance_score=0.9,
            ),
            PolicyMatch(
                policy_id="FP-04",
                description="Off-hours transaction pattern",
                relevance_score=0.75,
            ),
        ],
        chunk_ids=["fp-01-section-0", "fp-04-section-0"],
    )

    threat_intel = ThreatIntelResult(
        threat_level=0.7,
        sources=[
            ThreatSource(source_name="high_risk_country_IR", confidence=0.9),
            ThreatSource(source_name="merchant_watchlist_M-999", confidence=0.85),
        ],
    )

    citations = _aggregate_citations(policy_matches, threat_intel)

    assert len(citations) == 4  # 2 policies + 2 threats
    assert any("FP-01" in c for c in citations)
    assert any("FP-04" in c for c in citations)
    assert any("high_risk_country_IR" in c for c in citations)
    assert any("merchant_watchlist_M-999" in c for c in citations)


@pytest.mark.unit
def test_aggregate_citations_empty_inputs():
    """Test citation aggregation with empty inputs."""
    citations = _aggregate_citations(None, None)

    assert citations == []


@pytest.mark.unit
def test_determine_risk_category_low():
    """Test risk category determination for low risk."""
    assert _determine_risk_category(0.0) == "low"
    assert _determine_risk_category(15.5) == "low"
    assert _determine_risk_category(29.9) == "low"


@pytest.mark.unit
def test_determine_risk_category_medium():
    """Test risk category determination for medium risk."""
    assert _determine_risk_category(30.0) == "medium"
    assert _determine_risk_category(45.0) == "medium"
    assert _determine_risk_category(59.9) == "medium"


@pytest.mark.unit
def test_determine_risk_category_high():
    """Test risk category determination for high risk."""
    assert _determine_risk_category(60.0) == "high"
    assert _determine_risk_category(70.0) == "high"
    assert _determine_risk_category(79.9) == "high"


@pytest.mark.unit
def test_determine_risk_category_critical():
    """Test risk category determination for critical risk."""
    assert _determine_risk_category(80.0) == "critical"
    assert _determine_risk_category(90.0) == "critical"
    assert _determine_risk_category(100.0) == "critical"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_evidence_aggregation_agent_full_state():
    """Test evidence aggregation agent with complete state."""
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-001",
            customer_id="C-001",
            amount=1800.0,
            currency="PEN",
            country="IR",
            channel="web_unknown",
            device_id="D-999",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-999",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=3.6,
            is_off_hours=True,
            is_foreign=True,
            is_unknown_device=True,
            channel_risk="high",
            flags=["high_amount_ratio_3.6x", "transaction_off_hours"],
        ),
        "behavioral_signals": BehavioralSignals(
            deviation_score=0.85,
            anomalies=["amount_spike", "unusual_hour"],
            velocity_alert=True,
        ),
        "policy_matches": PolicyMatchResult(
            matches=[
                PolicyMatch(
                    policy_id="FP-01",
                    description="High amount",
                    relevance_score=0.92,
                ),
                PolicyMatch(
                    policy_id="FP-06",
                    description="Multiple risk factors",
                    relevance_score=0.88,
                ),
            ],
            chunk_ids=["fp-01-section-0", "fp-06-section-0"],
        ),
        "threat_intel": ThreatIntelResult(
            threat_level=0.85,
            sources=[
                ThreatSource(source_name="high_risk_country_IR", confidence=1.0),
                ThreatSource(source_name="merchant_watchlist_M-999", confidence=0.95),
            ],
        ),
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await evidence_aggregation_agent(state)

    # Assertions
    assert "evidence" in result
    evidence = result["evidence"]

    # Composite score should be high given all high-risk inputs
    assert evidence.composite_risk_score >= 60.0

    # Should have signals from all sources
    assert len(evidence.all_signals) > 0
    assert any("high_amount_ratio" in s for s in evidence.all_signals)
    assert any("amount_spike" in s for s in evidence.all_signals)
    assert any("policy_match" in s for s in evidence.all_signals)
    assert any("threat_" in s for s in evidence.all_signals)

    # Should have citations
    assert len(evidence.all_citations) > 0
    assert any("FP-01" in c for c in evidence.all_citations)
    assert any("Threat:" in c for c in evidence.all_citations)

    # Risk category should be high or critical
    assert evidence.risk_category in ("high", "critical")

    # Trace should be added by decorator
    assert "trace" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_evidence_aggregation_agent_partial_state():
    """Test evidence aggregation with partial state (some agents failed)."""
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-002",
            customer_id="C-002",
            amount=600.0,
            currency="USD",
            country="US",
            channel="app",
            device_id="D-01",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-001",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-002",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=1.2,
            is_off_hours=False,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="low",
            flags=[],
        ),
        # behavioral_signals, policy_matches, threat_intel are None (agents failed)
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await evidence_aggregation_agent(state)

    # Should still work with degraded inputs
    evidence = result["evidence"]
    assert evidence.composite_risk_score >= 0.0
    assert evidence.composite_risk_score < 100.0
    assert evidence.risk_category == "low"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_evidence_aggregation_agent_error_fallback():
    """Test agent returns safe defaults on error."""
    # Create state that will cause an error (missing required fields)
    state: OrchestratorState = {
        "status": "processing",
        "trace": [],
    }

    result = await evidence_aggregation_agent(state)

    # Should return safe default evidence
    evidence = result["evidence"]
    assert evidence.composite_risk_score == 0.0
    assert evidence.all_signals == []
    assert evidence.all_citations == []
    assert evidence.risk_category == "low"
