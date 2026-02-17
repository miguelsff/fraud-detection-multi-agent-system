"""Tests for Behavioral Pattern agent (NOT YET IMPLEMENTED).

These tests will automatically skip until the BehavioralPattern agent is implemented.
Once implemented, remove the skipif condition and the tests will run.
"""

import pytest

from app.models import BehavioralSignals, OrchestratorState

# Check if agent exists
try:
    from app.agents.behavioral_pattern import behavioral_pattern_agent

    AGENT_EXISTS = True
except ImportError:
    AGENT_EXISTS = False

# Skip all tests in this module if agent doesn't exist
pytestmark = pytest.mark.skipif(
    not AGENT_EXISTS, reason="BehavioralPattern agent not implemented yet"
)


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.skip_if_no_behavioral
async def test_low_deviation_t1003(
    transaction_t1003, customer_behavior_c503
):
    """Test T-1003 produces low deviation score (normal transaction).

    T-1003 characteristics:
    - Amount: 250 PEN (0.5x avg 500) - LOW deviation
    - Country: PE (usual) - NO deviation
    - Time: 14:30 (normal hours) - NO deviation
    - Device: D-03 (known) - NO deviation

    Expected: Low deviation score, no velocity alert, no anomalies.
    """
    state: OrchestratorState = {
        "transaction": transaction_t1003,
        "customer_behavior": customer_behavior_c503,
        "status": "processing",
        "trace": [],
    }

    result = await behavioral_pattern_agent(state)

    assert "behavioral_signals" in result
    assert isinstance(result["behavioral_signals"], BehavioralSignals)
    assert result["behavioral_signals"].deviation_score < 0.3
    assert result["behavioral_signals"].velocity_alert is False
    assert len(result["behavioral_signals"].anomalies) == 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.skip_if_no_behavioral
async def test_high_deviation_t1002(
    transaction_t1002, customer_behavior_c502
):
    """Test T-1002 produces high deviation score (suspicious).

    T-1002 characteristics:
    - Amount: 8500 USD (17x avg 500) - VERY HIGH deviation
    - Country: NG (not in usual [PE, CL]) - HIGH deviation
    - Time: 02:00 (off-hours) - HIGH deviation
    - Device: D-99 (not in usual [D-03]) - HIGH deviation

    Expected: High deviation score (>0.7), multiple anomalies detected.
    """
    state: OrchestratorState = {
        "transaction": transaction_t1002,
        "customer_behavior": customer_behavior_c502,
        "status": "processing",
        "trace": [],
    }

    result = await behavioral_pattern_agent(state)

    assert "behavioral_signals" in result
    assert isinstance(result["behavioral_signals"], BehavioralSignals)
    assert result["behavioral_signals"].deviation_score > 0.7
    assert len(result["behavioral_signals"].anomalies) > 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.skip_if_no_behavioral
async def test_velocity_alert_t1006(
    transaction_t1006, customer_behavior_c506
):
    """Test T-1006 triggers velocity alert (extreme transaction).

    T-1006 characteristics:
    - Amount: 15000 USD (30x avg 500) - EXTREME deviation
    - Country: RU (not in usual [PE]) - HIGH deviation
    - Time: 01:00 (off-hours) - HIGH deviation
    - Device: D-88 (not in usual [D-01]) - HIGH deviation

    Expected: Velocity alert triggered, very high deviation score, multiple anomalies.
    """
    state: OrchestratorState = {
        "transaction": transaction_t1006,
        "customer_behavior": customer_behavior_c506,
        "status": "processing",
        "trace": [],
    }

    result = await behavioral_pattern_agent(state)

    assert "behavioral_signals" in result
    assert isinstance(result["behavioral_signals"], BehavioralSignals)
    assert result["behavioral_signals"].velocity_alert is True
    assert result["behavioral_signals"].deviation_score > 0.8
    assert len(result["behavioral_signals"].anomalies) >= 3


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.skip_if_no_behavioral
async def test_moderate_deviation_t1001(
    transaction_t1001, customer_behavior_c501
):
    """Test T-1001 produces moderate deviation score.

    T-1001 characteristics:
    - Amount: 1800 PEN (3.6x avg 500) - MODERATE deviation
    - Country: PE (usual) - NO deviation
    - Time: 03:15 (off-hours) - MODERATE deviation
    - Device: D-01 (known) - NO deviation

    Expected: Moderate deviation score (0.4-0.6), some anomalies.
    """
    state: OrchestratorState = {
        "transaction": transaction_t1001,
        "customer_behavior": customer_behavior_c501,
        "status": "processing",
        "trace": [],
    }

    result = await behavioral_pattern_agent(state)

    assert "behavioral_signals" in result
    assert isinstance(result["behavioral_signals"], BehavioralSignals)
    assert 0.4 <= result["behavioral_signals"].deviation_score <= 0.6
    assert result["behavioral_signals"].velocity_alert is False
    assert len(result["behavioral_signals"].anomalies) > 0


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.skip_if_no_behavioral
async def test_state_trace_updated(
    transaction_t1003, customer_behavior_c503
):
    """Test that agent updates trace correctly."""
    state: OrchestratorState = {
        "transaction": transaction_t1003,
        "customer_behavior": customer_behavior_c503,
        "status": "processing",
        "trace": [],
    }

    result = await behavioral_pattern_agent(state)

    # Trace should be updated with agent execution
    assert "trace" in result
    assert len(result["trace"]) > 0
    assert result["trace"][0].agent_name == "behavioral_pattern"
    assert result["trace"][0].status == "success"
    assert result["trace"][0].duration_ms >= 0
