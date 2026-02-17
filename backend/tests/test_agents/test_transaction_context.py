"""Tests for the Transaction Context agent."""

from datetime import datetime, timezone

import pytest

from app.agents.transaction_context import transaction_context_agent
from app.models import CustomerBehavior, OrchestratorState, Transaction


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_normal_transaction(
    transaction_t1003, customer_behavior_c503
):
    """Test T-1003: Normal transaction with low amount (APPROVE expected).

    T-1003 characteristics:
    - Amount: 250 PEN (0.5x avg 500) - LOW
    - Country: PE (usual)
    - Time: 14:30 (normal hours)
    - Device: D-03 (known)

    Expected: Low risk signals, no flags.
    """
    # Arrange
    state: OrchestratorState = {
        "transaction": transaction_t1003,
        "customer_behavior": customer_behavior_c503,
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    assert "transaction_signals" in result
    signals = result["transaction_signals"]

    # T-1003: amount=250, avg=500 → ratio=0.5 (low)
    assert signals.amount_ratio == 0.5
    assert signals.is_foreign is False
    assert signals.is_unknown_device is False
    assert signals.channel_risk == "low"
    assert len(signals.flags) == 0  # No risk flags

    # Trace entry should be added by decorator
    assert "trace" in result
    assert len(result["trace"]) == 1
    assert result["trace"][0].agent_name == "transaction_context"
    assert result["trace"][0].status == "success"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_high_amount_off_hours(
    transaction_t1001, customer_behavior_c501
):
    """Test T-1001: High amount (3.6x) → CHALLENGE expected.

    T-1001 characteristics:
    - Amount: 1800 PEN (3.6x avg 500) - HIGH
    - Country: PE (usual)
    - Time: 03:15 (off-hours - will be detected by behavioral_pattern agent)
    - Device: D-01 (known)

    Expected: High amount ratio flag.
    Note: Off-hours detection is now in behavioral_pattern agent.
    """
    # Arrange
    state: OrchestratorState = {
        "transaction": transaction_t1001,
        "customer_behavior": customer_behavior_c501,
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]

    # T-1001: amount=1800, avg=500 → ratio=3.6
    assert signals.amount_ratio == 3.6
    assert signals.is_foreign is False
    assert signals.is_unknown_device is False
    assert signals.channel_risk == "low"

    # Check flags
    assert len(signals.flags) == 1
    assert any("high_amount_ratio" in flag for flag in signals.flags)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_foreign_unknown_device(
    transaction_t1002, customer_behavior_c502
):
    """Test T-1002: Very high amount + unusual country + unknown device → BLOCK expected.

    T-1002 characteristics:
    - Amount: 8500 USD (17x avg 500) - VERY HIGH
    - Country: NG (Nigeria, not in usual [PE, CL]) - FOREIGN
    - Time: 02:00 (off-hours - will be detected by behavioral_pattern agent)
    - Device: D-99 (not in usual [D-03]) - UNKNOWN

    Expected: Multiple risk flags (amount, foreign, device).
    Note: Off-hours detection is now in behavioral_pattern agent.
    """
    # Arrange
    state: OrchestratorState = {
        "transaction": transaction_t1002,
        "customer_behavior": customer_behavior_c502,
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]

    # T-1002: amount=8500, avg=500 → ratio=17.0
    assert signals.amount_ratio == 17.0
    assert signals.is_foreign is True
    assert signals.is_unknown_device is True
    assert signals.channel_risk == "medium"  # mobile channel

    # Check flags - should have multiple risk indicators
    assert len(signals.flags) >= 3
    assert any("high_amount_ratio" in flag for flag in signals.flags)
    assert any("foreign_country" in flag for flag in signals.flags)
    assert any("unknown_device" in flag for flag in signals.flags)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_zero_usual_amount():
    """Test transaction with zero usual_amount_avg (edge case)."""
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1004",
            customer_id="C-504",
            amount=100.00,
            currency="PEN",
            country="PE",
            channel="app",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-504",
            usual_amount_avg=0.0,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]

    # Should not divide by zero
    assert signals.amount_ratio == 0.0
    assert len(signals.flags) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_mobile_channel():
    """Test transaction with mobile channel (medium risk)."""
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1005",
            customer_id="C-505",
            amount=500.00,
            currency="PEN",
            country="PE",
            channel="mobile",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-505",
            usual_amount_avg=500.00,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]
    assert signals.channel_risk == "medium"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_transaction_context_overnight_hours():
    """Test transaction with overnight usual_hours (22:00-06:00).

    Note: Off-hours detection is now handled by behavioral_pattern agent.
    This test verifies transaction_context doesn't use customer_behavior.usual_hours.
    """
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1006",
            customer_id="C-506",
            amount=500.00,
            currency="PEN",
            country="PE",
            channel="app",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 23, 30, 0, tzinfo=timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-506",
            usual_amount_avg=500.00,
            usual_hours="22:00-06:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]
    # Verify basic signals are set correctly
    assert signals.amount_ratio == 1.0
    assert signals.is_foreign is False
    assert signals.is_unknown_device is False
    assert signals.channel_risk == "low"
