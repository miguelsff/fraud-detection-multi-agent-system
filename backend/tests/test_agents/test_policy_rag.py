"""Tests for the Policy RAG agent."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.agents.policy_rag import policy_rag_agent
from app.agents.policy_utils import (
    build_rag_query as _build_query_from_signals,
    parse_policy_matches as _parse_llm_response,
)
from app.models import (
    BehavioralSignals,
    CustomerBehavior,
    OrchestratorState,
    Transaction,
    TransactionSignals,
)


def test_build_query_from_signals_full():
    """Test query building with all signals present."""
    transaction = Transaction(
        transaction_id="T-001",
        customer_id="C-001",
        amount=1800.0,
        currency="PEN",
        country="US",
        channel="web_unknown",
        device_id="D-99",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",
    )

    transaction_signals = TransactionSignals(
        amount_ratio=3.5,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["high_amount_ratio_3.5x"],
    )

    behavioral_signals = BehavioralSignals(
        deviation_score=0.85,
        anomalies=["off_hours_transaction", "amount_spike", "unusual_hour"],
        velocity_alert=True,
    )

    query = _build_query_from_signals(
        transaction, transaction_signals, behavioral_signals
    )

    assert "1800" in query or "1800.0" in query
    assert "PEN" in query
    assert "monto muy superior" in query or "monto elevado" in query
    assert "fuera del horario" in query
    assert "país extranjero" in query or "US" in query
    assert "dispositivo no reconocido" in query
    assert "alto riesgo" in query


def test_build_query_from_signals_none():
    """Test query building when signals are None."""
    transaction = Transaction(
        transaction_id="T-001",
        customer_id="C-001",
        amount=500.0,
        currency="PEN",
        country="PE",
        channel="app",
        device_id="D-01",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",
    )

    query = _build_query_from_signals(transaction, None, None)

    # Should still produce a query with base info
    assert "500" in query or "500.0" in query
    assert "PEN" in query
    assert query  # Not empty


def test_build_query_with_moderate_amount():
    """Test query with moderate amount ratio."""
    transaction = Transaction(
        transaction_id="T-002",
        customer_id="C-002",
        amount=1000.0,
        currency="PEN",
        country="PE",
        channel="app",
        device_id="D-01",
        timestamp=datetime.now(timezone.utc),
        merchant_id="M-001",
    )

    transaction_signals = TransactionSignals(
        amount_ratio=2.2,  # Between 2.0 and 3.0
        is_foreign=False,
        is_unknown_device=False,
        channel_risk="low",
        flags=[],
    )

    query = _build_query_from_signals(transaction, transaction_signals, None)

    assert "monto elevado" in query
    assert "monto muy superior" not in query


def test_parse_llm_response_valid_json():
    """Test parsing valid JSON response."""
    response = """{
  "matches": [
    {
      "policy_id": "FP-01",
      "description": "High amount transaction",
      "relevance_score": 0.92
    },
    {
      "policy_id": "FP-04",
      "description": "Off-hours transaction",
      "relevance_score": 0.75
    }
  ]
}"""

    matches = _parse_llm_response(response)

    assert len(matches) == 2
    assert matches[0].policy_id == "FP-01"
    assert matches[0].relevance_score == 0.92
    assert matches[1].policy_id == "FP-04"


def test_parse_llm_response_json_in_markdown():
    """Test parsing JSON wrapped in markdown code block."""
    response = """Here's my analysis:

```json
{
  "matches": [
    {
      "policy_id": "FP-02",
      "description": "Foreign country",
      "relevance_score": 0.88
    }
  ]
}
```
"""

    matches = _parse_llm_response(response)
    assert len(matches) == 1
    assert matches[0].policy_id == "FP-02"


def test_parse_llm_response_regex_fallback():
    """Test regex fallback when JSON parsing fails."""
    response = """
    Based on the analysis:
    - FP-01 applies with score: 0.85
    - FP-03 is relevant with relevance: 0.72
    """

    matches = _parse_llm_response(response)

    assert len(matches) >= 1  # At least one match found by regex
    assert any(m.policy_id == "FP-01" for m in matches)


def test_parse_llm_response_clamps_scores():
    """Test that scores outside 0.0-1.0 are clamped."""
    response = """{
  "matches": [
    {
      "policy_id": "FP-01",
      "description": "Test",
      "relevance_score": 1.5
    },
    {
      "policy_id": "FP-02",
      "description": "Test",
      "relevance_score": -0.2
    }
  ]
}"""

    matches = _parse_llm_response(response)

    # FP-01 should be clamped to 1.0
    fp01 = next((m for m in matches if m.policy_id == "FP-01"), None)
    assert fp01 is not None
    assert fp01.relevance_score == 1.0

    # FP-02 with negative score should be filtered out (< 0.5)
    fp02 = next((m for m in matches if m.policy_id == "FP-02"), None)
    assert fp02 is None  # Filtered because score would be 0.0 after clamp


def test_parse_llm_response_filters_low_scores():
    """Test that matches with score < 0.5 are filtered."""
    response = """{
  "matches": [
    {
      "policy_id": "FP-01",
      "description": "High score",
      "relevance_score": 0.9
    },
    {
      "policy_id": "FP-02",
      "description": "Low score",
      "relevance_score": 0.3
    }
  ]
}"""

    matches = _parse_llm_response(response)

    assert len(matches) == 1
    assert matches[0].policy_id == "FP-01"


@pytest.mark.asyncio
@patch("app.agents.policy_rag.query_policies")
@patch("app.agents.policy_rag.get_llm")
async def test_policy_rag_agent_success(mock_get_llm, mock_query_policies):
    """Test successful policy RAG agent execution."""
    # Mock RAG results
    mock_query_policies.return_value = [
        {
            "id": "fp-01-section-0",
            "text": "## FP-01: Test Policy\nDescription...",
            "metadata": {"policy_id": "FP-01"},
            "score": 0.95,
        }
    ]

    # Mock LLM
    mock_llm = AsyncMock()
    mock_response = Mock()
    mock_response.content = """{
  "matches": [
    {
      "policy_id": "FP-01",
      "description": "Test policy applies",
      "relevance_score": 0.90
    }
  ]
}"""
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_get_llm.return_value = mock_llm

    # Build state
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-001",
            customer_id="C-001",
            amount=1000.0,
            currency="PEN",
            country="PE",
            channel="app",
            device_id="D-01",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-001",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=2.0,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="low",
            flags=[],
        ),
        "status": "processing",
        "trace": [],
    }

    # Execute agent
    result = await policy_rag_agent(state)

    # Assertions
    assert "policy_matches" in result
    policy_matches = result["policy_matches"]
    assert len(policy_matches.matches) == 1
    assert policy_matches.matches[0].policy_id == "FP-01"
    assert len(policy_matches.chunk_ids) == 1

    # Trace should be added by decorator
    assert "trace" in result


@pytest.mark.asyncio
@patch("app.agents.policy_rag.query_policies")
async def test_policy_rag_agent_no_rag_results(mock_query_policies):
    """Test agent behavior when ChromaDB returns no results."""
    mock_query_policies.return_value = []

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-001",
            customer_id="C-001",
            amount=1000.0,
            currency="PEN",
            country="PE",
            channel="app",
            device_id="D-01",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-001",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01"],
        ),
        "status": "processing",
        "trace": [],
    }

    result = await policy_rag_agent(state)

    assert result["policy_matches"].matches == []
    assert result["policy_matches"].chunk_ids == []


@pytest.mark.asyncio
async def test_policy_rag_agent_error_fallback():
    """Test agent returns empty result on exception."""
    # Create state that will cause an error (missing required field)
    state: OrchestratorState = {
        "status": "processing",
        "trace": [],
    }

    result = await policy_rag_agent(state)

    # Should return empty PolicyMatchResult, not crash
    assert result["policy_matches"].matches == []
    assert result["policy_matches"].chunk_ids == []
