"""Tests for the External Threat agent."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.agents.external_threat import (
    _calculate_baseline_threat_level,
    _lookup_threat_feeds,
    _parse_threat_analysis_response,
    external_threat_agent,
)
from app.models import (
    CustomerBehavior,
    OrchestratorState,
    ThreatSource,
    Transaction,
    TransactionSignals,
)


def test_lookup_threat_feeds_high_risk_country():
    """Test threat detection for high-risk country."""
    transaction = Transaction(
        transaction_id="T-001",
        customer_id="C-001",
        amount=1000.0,
        currency="USD",
        country="IR",  # Iran - high risk
        channel="app",
        device_id="D-01",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",
    )

    sources = _lookup_threat_feeds(transaction, None)

    assert len(sources) == 1
    assert sources[0].source_name == "high_risk_country_IR"
    assert sources[0].confidence == 1.0


def test_lookup_threat_feeds_merchant_watchlist():
    """Test threat detection for merchant on watchlist."""
    transaction = Transaction(
        transaction_id="T-002",
        customer_id="C-002",
        amount=1000.0,
        currency="USD",
        country="US",
        channel="app",
        device_id="D-01",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-999",  # On watchlist
    )

    sources = _lookup_threat_feeds(transaction, None)

    assert len(sources) == 1
    assert sources[0].source_name == "merchant_watchlist_M-999"
    assert sources[0].confidence == 0.95


def test_lookup_threat_feeds_fraud_pattern():
    """Test threat detection for known fraud pattern."""
    transaction = Transaction(
        transaction_id="T-003",
        customer_id="C-003",
        amount=2000.0,
        currency="USD",
        country="US",
        channel="web_unknown",
        device_id="D-99",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",
    )

    transaction_signals = TransactionSignals(
        amount_ratio=4.0,  # High amount
        is_off_hours=False,
        is_foreign=True,  # Foreign
        is_unknown_device=True,  # Unknown device
        channel_risk="high",  # High risk channel
        flags=["high_amount_ratio_4.0x"],
    )

    sources = _lookup_threat_feeds(transaction, transaction_signals)

    # Should detect:
    # 1. web_unknown_foreign (high channel + foreign)
    # 2. high_amount_new_device (amount > 3.0 + unknown device)
    assert len(sources) >= 2
    source_names = [s.source_name for s in sources]
    assert "fraud_pattern_web_unknown_foreign" in source_names
    assert "fraud_pattern_high_amount_new_device" in source_names


def test_lookup_threat_feeds_multiple_threats():
    """Test detection of multiple threat sources."""
    transaction = Transaction(
        transaction_id="T-004",
        customer_id="C-004",
        amount=5000.0,
        currency="USD",
        country="IR",  # High-risk country
        channel="web_unknown",
        device_id="D-99",
        timestamp=datetime(2025, 1, 15, 3, 0, 0, tzinfo=timezone.utc),
        merchant_id="M-999",  # Watchlist
    )

    transaction_signals = TransactionSignals(
        amount_ratio=5.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["high_amount_ratio_5.0x"],
    )

    sources = _lookup_threat_feeds(transaction, transaction_signals)

    # Should detect:
    # 1. High-risk country (IR)
    # 2. Merchant watchlist
    # 3. Multiple fraud patterns
    assert len(sources) >= 3
    source_names = [s.source_name for s in sources]
    assert any("high_risk_country" in name for name in source_names)
    assert any("merchant_watchlist" in name for name in source_names)


def test_lookup_threat_feeds_no_threats():
    """Test clean transaction with no threats."""
    transaction = Transaction(
        transaction_id="T-005",
        customer_id="C-005",
        amount=500.0,
        currency="USD",
        country="US",  # Safe country
        channel="app",
        device_id="D-01",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",  # Clean merchant
    )

    transaction_signals = TransactionSignals(
        amount_ratio=1.0,
        is_off_hours=False,
        is_foreign=False,
        is_unknown_device=False,
        channel_risk="low",
        flags=[],
    )

    sources = _lookup_threat_feeds(transaction, transaction_signals)

    assert len(sources) == 0


def test_calculate_baseline_threat_level_single_source():
    """Test baseline calculation with single source."""
    sources = [
        ThreatSource(source_name="test_source", confidence=0.7)
    ]

    level = _calculate_baseline_threat_level(sources)

    assert level == 0.7


def test_calculate_baseline_threat_level_multiple_sources():
    """Test baseline calculation with multiple sources."""
    sources = [
        ThreatSource(source_name="source1", confidence=0.6),
        ThreatSource(source_name="source2", confidence=0.8),
        ThreatSource(source_name="source3", confidence=0.5),
    ]

    level = _calculate_baseline_threat_level(sources)

    # Should use max (0.8) + bonus for multiple sources
    # 0.8 + 0.1 * (3-1) = 0.8 + 0.2 = 1.0
    assert level == 1.0


def test_calculate_baseline_threat_level_empty():
    """Test baseline calculation with no sources."""
    sources = []

    level = _calculate_baseline_threat_level(sources)

    assert level == 0.0


def test_parse_threat_analysis_response_valid_json():
    """Test parsing valid JSON response."""
    response = """{
  "threat_level": 0.75,
  "explanation": "High-risk country with merchant on watchlist"
}"""

    threat_level, explanation = _parse_threat_analysis_response(response)

    assert threat_level == 0.75
    assert "High-risk country" in explanation


def test_parse_threat_analysis_response_json_in_markdown():
    """Test parsing JSON in markdown code block."""
    response = """Here's my analysis:

```json
{
  "threat_level": 0.85,
  "explanation": "Critical threat detected"
}
```
"""

    threat_level, explanation = _parse_threat_analysis_response(response)

    assert threat_level == 0.85
    assert "Critical" in explanation


def test_parse_threat_analysis_response_clamps_values():
    """Test that threat_level is clamped to [0.0, 1.0]."""
    response = """{
  "threat_level": 1.5,
  "explanation": "Test"
}"""

    threat_level, explanation = _parse_threat_analysis_response(response)

    assert threat_level == 1.0  # Clamped from 1.5


def test_parse_threat_analysis_response_regex_fallback():
    """Test regex fallback when JSON parsing fails."""
    response = """
    Based on analysis, threat_level: 0.65
    High risk detected.
    """

    threat_level, explanation = _parse_threat_analysis_response(response)

    assert threat_level == 0.65
    assert explanation == "Extracted via regex"


def test_parse_threat_analysis_response_parse_failure():
    """Test behavior when parsing completely fails."""
    response = "No valid data here"

    threat_level, explanation = _parse_threat_analysis_response(response)

    assert threat_level is None
    assert "Parse failed" in explanation


@pytest.mark.asyncio
@patch("app.agents.external_threat.get_llm")
async def test_external_threat_agent_with_threats(mock_get_llm):
    """Test external threat agent with detected threats."""
    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = """{
  "threat_level": 0.85,
  "explanation": "High-risk country (IR) with merchant on watchlist"
}"""
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_get_llm.return_value = mock_llm

    # Build state with high-risk transaction
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-001",
            customer_id="C-001",
            amount=5000.0,
            currency="USD",
            country="IR",  # High-risk
            channel="web_unknown",
            device_id="D-99",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-999",  # Watchlist
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=10.0,
            is_off_hours=False,
            is_foreign=True,
            is_unknown_device=True,
            channel_risk="high",
            flags=["high_amount_ratio_10.0x"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await external_threat_agent(state)

    # Assertions
    assert "threat_intel" in result
    threat_intel = result["threat_intel"]
    assert threat_intel.threat_level == 0.85
    assert len(threat_intel.sources) >= 2  # At least country + merchant

    # Trace should be added by decorator
    assert "trace" in result


@pytest.mark.asyncio
async def test_external_threat_agent_no_threats():
    """Test external threat agent with clean transaction."""
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-002",
            customer_id="C-002",
            amount=500.0,
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
            amount_ratio=1.0,
            is_off_hours=False,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="low",
            flags=[],
        ),
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await external_threat_agent(state)

    # Should return empty threat intel
    assert result["threat_intel"].threat_level == 0.0
    assert len(result["threat_intel"].sources) == 0


@pytest.mark.asyncio
@patch("app.agents.external_threat.get_llm")
async def test_external_threat_agent_llm_failure_fallback(mock_get_llm):
    """Test agent uses baseline when LLM fails."""
    # Mock LLM to raise exception
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
    mock_get_llm.return_value = mock_llm

    # Build state with threats
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-003",
            customer_id="C-003",
            amount=1000.0,
            currency="USD",
            country="NG",  # Medium-risk country
            channel="app",
            device_id="D-01",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-001",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-003",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await external_threat_agent(state)

    # Should use baseline calculation (not 0.0)
    threat_intel = result["threat_intel"]
    assert threat_intel.threat_level > 0.0  # Baseline from threat feeds
    assert len(threat_intel.sources) >= 1  # Should have detected country


@pytest.mark.asyncio
async def test_external_threat_agent_error_fallback():
    """Test agent returns empty result on exception."""
    # Create state that will cause an error (missing required field)
    state: OrchestratorState = {
        "status": "processing",
        "trace": [],
    }

    result = await external_threat_agent(state)

    # Should return empty ThreatIntelResult, not crash
    assert result["threat_intel"].threat_level == 0.0
    assert result["threat_intel"].sources == []
