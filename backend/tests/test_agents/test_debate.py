"""Unit tests for debate agents (pro-fraud and pro-customer)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.debate import (
    debate_pro_customer_agent,
    debate_pro_fraud_agent,
    PRO_CUSTOMER_PROMPT,
    PRO_FRAUD_PROMPT,
)
from app.agents.debate_utils import (
    call_debate_llm as _call_llm_for_debate,
    _parse_debate_response,
    generate_fallback_pro_fraud as _generate_fallback_pro_fraud,
    generate_fallback_pro_customer as _generate_fallback_pro_customer,
)
from app.models import AggregatedEvidence, OrchestratorState


# ============================================================================
# PARSING TESTS
# ============================================================================


def test_parse_debate_response_valid_json():
    """Test parsing valid JSON response."""
    response_text = """```json
{
  "argument": "La transacción presenta múltiples señales de fraude.",
  "confidence": 0.78,
  "evidence_cited": ["amount_ratio_3.6x", "off_hours", "unknown_device"]
}
```"""

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument == "La transacción presenta múltiples señales de fraude."
    assert confidence == 0.78
    assert evidence == ["amount_ratio_3.6x", "off_hours", "unknown_device"]


def test_parse_debate_response_json_in_markdown():
    """Test parsing JSON inside markdown code block."""
    response_text = """Aquí está mi análisis:

```json
{
  "argument": "El cliente tiene historial positivo.",
  "confidence": 0.65,
  "evidence_cited": ["known_device", "same_country"]
}
```

Espero que esto ayude."""

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument == "El cliente tiene historial positivo."
    assert confidence == 0.65
    assert evidence == ["known_device", "same_country"]


def test_parse_debate_response_raw_json():
    """Test parsing raw JSON without code blocks."""
    response_text = """{"argument": "Transacción sospechosa.", "confidence": 0.82, "evidence_cited": ["signal1", "signal2"]}"""

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument == "Transacción sospechosa."
    assert confidence == 0.82
    assert evidence == ["signal1", "signal2"]


def test_parse_debate_response_regex_fallback():
    """Test regex fallback when JSON parsing fails."""
    response_text = """
Mi análisis indica:
"argument": "Esta es una transacción de alto riesgo"
"confidence": 0.85
"evidence_cited": ["high_amount", "foreign_country"]
"""

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument == "Esta es una transacción de alto riesgo"
    assert confidence == 0.85
    assert evidence == ["high_amount", "foreign_country"]


def test_parse_debate_response_clamps_confidence():
    """Test that confidence is clamped to [0.0, 1.0]."""
    # Test upper bound
    response_text_high = '{"argument": "Test", "confidence": 1.5, "evidence_cited": []}'
    _, confidence_high, _ = _parse_debate_response(response_text_high)
    assert confidence_high == 1.0

    # Test lower bound
    response_text_low = '{"argument": "Test", "confidence": -0.2, "evidence_cited": []}'
    _, confidence_low, _ = _parse_debate_response(response_text_low)
    assert confidence_low == 0.0


def test_parse_debate_response_missing_evidence():
    """Test handling when evidence_cited is missing."""
    response_text = '{"argument": "Test argument", "confidence": 0.7}'

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument == "Test argument"
    assert confidence == 0.7
    assert evidence == []  # Should default to empty list


def test_parse_debate_response_invalid():
    """Test complete parse failure returns (None, None, [])."""
    response_text = "This is completely invalid text with no JSON or recognizable patterns"

    argument, confidence, evidence = _parse_debate_response(response_text)

    assert argument is None
    assert confidence is None
    assert evidence == []


# ============================================================================
# FALLBACK GENERATION TESTS
# ============================================================================


def test_generate_fallback_pro_fraud_critical():
    """Test pro-fraud fallback for critical risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=92.5,
        all_signals=["high_amount", "unknown_device", "off_hours"],
        all_citations=["FP-01: Critical policy match"],
        risk_category="critical",
    )

    result = _generate_fallback_pro_fraud(evidence)

    assert "pro_fraud_argument" in result
    assert "CRÍTICO" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.90
    assert result["pro_fraud_evidence"] == ["high_amount", "unknown_device", "off_hours"]


def test_generate_fallback_pro_fraud_high():
    """Test pro-fraud fallback for high risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=75.0,
        all_signals=["amount_spike", "foreign_country"],
        all_citations=["FP-02: High risk policy"],
        risk_category="high",
    )

    result = _generate_fallback_pro_fraud(evidence)

    assert "pro_fraud_argument" in result
    assert "ALTO" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.75
    assert len(result["pro_fraud_evidence"]) == 2


def test_generate_fallback_pro_fraud_medium():
    """Test pro-fraud fallback for medium risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=55.0,
        all_signals=["minor_flag"],
        all_citations=[],
        risk_category="medium",
    )

    result = _generate_fallback_pro_fraud(evidence)

    assert "MEDIO" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.55


def test_generate_fallback_pro_fraud_low():
    """Test pro-fraud fallback for low risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=25.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )

    result = _generate_fallback_pro_fraud(evidence)

    assert "BAJO" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.30
    assert result["pro_fraud_evidence"] == ["risk_score_elevated"]  # Default when no signals


def test_generate_fallback_pro_customer_critical():
    """Test pro-customer fallback for critical risk (inverse confidence)."""
    evidence = AggregatedEvidence(
        composite_risk_score=92.5,
        all_signals=["high_amount", "unknown_device"],
        all_citations=["FP-01: Critical"],
        risk_category="critical",
    )

    result = _generate_fallback_pro_customer(evidence)

    assert "pro_customer_argument" in result
    assert "crítico" in result["pro_customer_argument"]
    assert result["pro_customer_confidence"] == 0.20  # Low legitimacy confidence for critical risk
    assert "possible_legitimate_context" in result["pro_customer_evidence"]


def test_generate_fallback_pro_customer_high():
    """Test pro-customer fallback for high risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=78.0,
        all_signals=["signal1"],
        all_citations=[],
        risk_category="high",
    )

    result = _generate_fallback_pro_customer(evidence)

    assert "alto" in result["pro_customer_argument"]
    assert result["pro_customer_confidence"] == 0.35


def test_generate_fallback_pro_customer_medium():
    """Test pro-customer fallback for medium risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=55.0,
        all_signals=["flag1"],
        all_citations=[],
        risk_category="medium",
    )

    result = _generate_fallback_pro_customer(evidence)

    assert "medio" in result["pro_customer_argument"]
    assert result["pro_customer_confidence"] == 0.60


def test_generate_fallback_pro_customer_low():
    """Test pro-customer fallback for low risk (high legitimacy confidence)."""
    evidence = AggregatedEvidence(
        composite_risk_score=20.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )

    result = _generate_fallback_pro_customer(evidence)

    assert "bajo" in result["pro_customer_argument"]
    assert result["pro_customer_confidence"] == 0.85  # High legitimacy confidence for low risk


# ============================================================================
# LLM CALL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_call_llm_for_debate_success():
    """Test successful LLM call for debate."""
    evidence = AggregatedEvidence(
        composite_risk_score=68.5,
        all_signals=["high_amount", "off_hours"],
        all_citations=["FP-01: Policy match"],
        risk_category="high",
    )

    # Mock LLM response
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = """```json
{
  "argument": "Transacción de alto riesgo con múltiples señales.",
  "confidence": 0.78,
  "evidence_cited": ["high_amount", "off_hours", "FP-01"]
}
```"""
    mock_llm.ainvoke.return_value = mock_response

    argument, confidence, evidence_cited = await _call_llm_for_debate(
        mock_llm,
        evidence,
        PRO_FRAUD_PROMPT,
    )

    assert argument == "Transacción de alto riesgo con múltiples señales."
    assert confidence == 0.78
    assert evidence_cited == ["high_amount", "off_hours", "FP-01"]
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_for_debate_timeout():
    """Test LLM timeout handling."""
    evidence = AggregatedEvidence(
        composite_risk_score=50.0,
        all_signals=[],
        all_citations=[],
        risk_category="medium",
    )

    # Mock LLM to raise TimeoutError
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = TimeoutError("LLM timeout")

    with patch("app.agents.debate_utils.asyncio.wait_for", side_effect=TimeoutError):
        argument, confidence, evidence_cited = await _call_llm_for_debate(
            mock_llm,
            evidence,
            PRO_FRAUD_PROMPT,
        )

    assert argument is None
    assert confidence is None
    assert evidence_cited == []


@pytest.mark.asyncio
async def test_call_llm_for_debate_exception():
    """Test LLM exception handling."""
    evidence = AggregatedEvidence(
        composite_risk_score=50.0,
        all_signals=[],
        all_citations=[],
        risk_category="medium",
    )

    # Mock LLM to raise exception
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("LLM error")

    argument, confidence, evidence_cited = await _call_llm_for_debate(
        mock_llm,
        evidence,
        PRO_FRAUD_PROMPT,
    )

    assert argument is None
    assert confidence is None
    assert evidence_cited == []


# ============================================================================
# AGENT INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_debate_pro_fraud_agent_success():
    """Test pro-fraud agent with successful LLM call."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=72.0,
            all_signals=["high_amount", "unknown_device"],
            all_citations=["FP-01: High risk"],
            risk_category="high",
        ),
    }

    # Mock LLM
    with patch("app.agents.debate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "argument": "Alta probabilidad de fraude.",
            "confidence": 0.80,
            "evidence_cited": ["high_amount", "unknown_device"],
        })
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await debate_pro_fraud_agent(state)

    assert "pro_fraud_argument" in result
    assert "pro_fraud_confidence" in result
    assert "pro_fraud_evidence" in result
    assert result["pro_fraud_argument"] == "Alta probabilidad de fraude."
    assert result["pro_fraud_confidence"] == 0.80
    assert result["pro_fraud_evidence"] == ["high_amount", "unknown_device"]


@pytest.mark.asyncio
async def test_debate_pro_customer_agent_success():
    """Test pro-customer agent with successful LLM call."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=45.0,
            all_signals=["minor_flag"],
            all_citations=[],
            risk_category="medium",
        ),
    }

    # Mock LLM
    with patch("app.agents.debate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "argument": "Transacción probablemente legítima.",
            "confidence": 0.65,
            "evidence_cited": ["customer_history"],
        })
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await debate_pro_customer_agent(state)

    assert "pro_customer_argument" in result
    assert "pro_customer_confidence" in result
    assert "pro_customer_evidence" in result
    assert result["pro_customer_argument"] == "Transacción probablemente legítima."
    assert result["pro_customer_confidence"] == 0.65


@pytest.mark.asyncio
async def test_debate_pro_fraud_agent_llm_timeout():
    """Test pro-fraud agent fallback on LLM timeout."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=88.0,
            all_signals=["critical_signal"],
            all_citations=["FP-01"],
            risk_category="critical",
        ),
    }

    # Mock LLM timeout
    with patch("app.agents.debate.get_llm") as mock_get_llm, \
         patch("app.agents.debate_utils.asyncio.wait_for", side_effect=TimeoutError):
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm

        result = await debate_pro_fraud_agent(state)

    # Should use fallback
    assert "pro_fraud_argument" in result
    assert "CRÍTICO" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.90


@pytest.mark.asyncio
async def test_debate_pro_customer_agent_parse_failure():
    """Test pro-customer agent fallback on parse failure."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=30.0,
            all_signals=[],
            all_citations=[],
            risk_category="low",
        ),
    }

    # Mock LLM with invalid response
    with patch("app.agents.debate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "This is invalid text with no JSON"
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await debate_pro_customer_agent(state)

    # Should use fallback
    assert "pro_customer_argument" in result
    assert "bajo" in result["pro_customer_argument"].lower()
    assert result["pro_customer_confidence"] == 0.85


@pytest.mark.asyncio
async def test_debate_agents_no_evidence():
    """Test both agents when evidence is missing."""
    state: OrchestratorState = {}

    result_fraud = await debate_pro_fraud_agent(state)
    result_customer = await debate_pro_customer_agent(state)

    # Both should return safe defaults
    assert result_fraud["pro_fraud_confidence"] == 0.50
    assert "no_evidence" in result_fraud["pro_fraud_evidence"]

    assert result_customer["pro_customer_confidence"] == 0.50
    assert "no_evidence" in result_customer["pro_customer_evidence"]


@pytest.mark.asyncio
async def test_debate_pro_fraud_agent_exception_handling():
    """Test pro-fraud agent handles exceptions gracefully."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=50.0,
            all_signals=[],
            all_citations=[],
            risk_category="medium",
        ),
    }

    # Mock get_llm to raise exception
    with patch("app.agents.debate.get_llm", side_effect=Exception("Test error")):
        result = await debate_pro_fraud_agent(state)

    # Should return error fallback
    assert "pro_fraud_argument" in result
    assert "Error" in result["pro_fraud_argument"]
    assert result["pro_fraud_confidence"] == 0.50
    assert result["pro_fraud_evidence"] == ["error_occurred"]


@pytest.mark.asyncio
async def test_debate_pro_customer_agent_exception_handling():
    """Test pro-customer agent handles exceptions gracefully."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=50.0,
            all_signals=[],
            all_citations=[],
            risk_category="medium",
        ),
    }

    # Mock get_llm to raise exception
    with patch("app.agents.debate.get_llm", side_effect=Exception("Test error")):
        result = await debate_pro_customer_agent(state)

    # Should return error fallback
    assert "pro_customer_argument" in result
    assert "Error" in result["pro_customer_argument"]
    assert result["pro_customer_confidence"] == 0.50
    assert result["pro_customer_evidence"] == ["error_occurred"]


@pytest.mark.asyncio
async def test_debate_agents_partial_state_update():
    """Test that agents return partial state updates (not DebateArguments object)."""
    state: OrchestratorState = {
        "evidence": AggregatedEvidence(
            composite_risk_score=60.0,
            all_signals=["test"],
            all_citations=[],
            risk_category="medium",
        ),
    }

    with patch("app.agents.debate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "argument": "Test",
            "confidence": 0.7,
            "evidence_cited": ["test"],
        })
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result_fraud = await debate_pro_fraud_agent(state)
        result_customer = await debate_pro_customer_agent(state)

    # Should return dicts, not model instances
    assert isinstance(result_fraud, dict)
    assert isinstance(result_customer, dict)

    # Should contain their respective fields (plus trace from @timed_agent)
    assert set(result_fraud.keys()) == {
        "pro_fraud_argument",
        "pro_fraud_confidence",
        "pro_fraud_evidence",
        "trace",
    }
    assert set(result_customer.keys()) == {
        "pro_customer_argument",
        "pro_customer_confidence",
        "pro_customer_evidence",
        "trace",
    }
