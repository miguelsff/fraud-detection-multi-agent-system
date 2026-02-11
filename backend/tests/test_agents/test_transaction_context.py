"""Tests for the Transaction Context agent."""

from datetime import datetime, timezone

import pytest

from app.agents.transaction_context import transaction_context_agent
from app.models import CustomerBehavior, OrchestratorState, Transaction


@pytest.mark.asyncio
async def test_transaction_context_normal_transaction():
    """Test transaction context agent with a normal transaction."""
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1001",
            customer_id="C-501",
            amount=500.00,
            currency="PEN",
            country="PE",
            channel="app",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-501",
            usual_amount_avg=500.00,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01", "D-02"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    assert "transaction_signals" in result
    signals = result["transaction_signals"]

    assert signals.amount_ratio == 1.0
    assert signals.is_off_hours is False
    assert signals.is_foreign is False
    assert signals.is_unknown_device is False
    assert signals.channel_risk == "low"
    assert len(signals.flags) == 0

    # Trace entry should be added by decorator
    assert "trace" in result
    assert len(result["trace"]) == 1
    assert result["trace"][0].agent_name == "transaction_context"
    assert result["trace"][0].status == "success"


@pytest.mark.asyncio
async def test_transaction_context_high_amount_off_hours():
    """Test transaction with high amount and off-hours."""
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1002",
            customer_id="C-502",
            amount=1800.00,
            currency="PEN",
            country="PE",
            channel="web",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 3, 15, 0, tzinfo=timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-502",
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

    assert signals.amount_ratio == 3.6
    assert signals.is_off_hours is True
    assert signals.is_foreign is False
    assert signals.is_unknown_device is False
    assert signals.channel_risk == "low"

    # Check flags
    assert len(signals.flags) == 2
    assert any("high_amount_ratio" in flag for flag in signals.flags)
    assert "transaction_off_hours" in signals.flags


@pytest.mark.asyncio
async def test_transaction_context_foreign_unknown_device():
    """Test transaction from foreign country with unknown device."""
    # Arrange
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1003",
            customer_id="C-503",
            amount=600.00,
            currency="USD",
            country="US",
            channel="web_unknown",
            device_id="D-99",
            timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            merchant_id="M-201",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-503",
            usual_amount_avg=500.00,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01", "D-02"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Act
    result = await transaction_context_agent(state)

    # Assert
    signals = result["transaction_signals"]

    assert signals.amount_ratio == 1.2
    assert signals.is_off_hours is False
    assert signals.is_foreign is True
    assert signals.is_unknown_device is True
    assert signals.channel_risk == "high"

    # Check flags
    assert len(signals.flags) == 3
    assert any("foreign_country" in flag for flag in signals.flags)
    assert any("unknown_device" in flag for flag in signals.flags)
    assert "high_risk_channel" in signals.flags


@pytest.mark.asyncio
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
async def test_transaction_context_overnight_hours():
    """Test transaction with overnight usual_hours (22:00-06:00)."""
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
    # Transaction at 23:30 should be within overnight range 22:00-06:00
    assert signals.is_off_hours is False
