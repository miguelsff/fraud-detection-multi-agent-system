"""Unit tests for decision arbiter agent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.decision_arbiter import (
    _call_llm_for_decision,
    _extract_agent_trace,
    _parse_decision_response,
    decision_arbiter_agent,
)
from app.utils.decision_utils import (
    apply_safety_overrides as _apply_safety_overrides,
    build_citations_external as _build_citations_external,
    build_citations_internal as _build_citations_internal,
    generate_audit_explanation as _generate_audit_explanation,
    generate_customer_explanation as _generate_customer_explanation,
    generate_fallback_decision as _generate_fallback_decision,
)
from app.models import (
    AggregatedEvidence,
    AgentTraceEntry,
    DebateArguments,
    OrchestratorState,
    Transaction,
)


# ============================================================================
# PARSING TESTS
# ============================================================================


def test_parse_decision_response_valid_json():
    """Test parsing valid JSON response."""
    response_text = """```json
{
  "decision": "BLOCK",
  "confidence": 0.85,
  "reasoning": "Puntaje de riesgo alto justifica bloqueo."
}
```"""

    decision, confidence, reasoning = _parse_decision_response(response_text)

    assert decision == "BLOCK"
    assert confidence == 0.85
    assert reasoning == "Puntaje de riesgo alto justifica bloqueo."


def test_parse_decision_response_all_decisions():
    """Test parsing all valid decision types."""
    for decision_type in ["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]:
        response_text = f'{{"decision": "{decision_type}", "confidence": 0.7, "reasoning": "Test"}}'
        decision, confidence, reasoning = _parse_decision_response(response_text)
        assert decision == decision_type
        assert confidence == 0.7


def test_parse_decision_response_regex_fallback():
    """Test regex fallback when JSON parsing fails."""
    response_text = """
La decisión es:
"decision": "CHALLENGE"
"confidence": 0.72
"reasoning": "Requiere verificación adicional"
"""

    decision, confidence, reasoning = _parse_decision_response(response_text)

    assert decision == "CHALLENGE"
    assert confidence == 0.72
    assert reasoning == "Requiere verificación adicional"


def test_parse_decision_response_clamps_confidence():
    """Test that confidence is clamped to [0.0, 1.0]."""
    # Test upper bound
    response_text_high = '{"decision": "APPROVE", "confidence": 1.5, "reasoning": "Test"}'
    _, confidence_high, _ = _parse_decision_response(response_text_high)
    assert confidence_high == 1.0

    # Test lower bound
    response_text_low = '{"decision": "BLOCK", "confidence": -0.2, "reasoning": "Test"}'
    _, confidence_low, _ = _parse_decision_response(response_text_low)
    assert confidence_low == 0.0


def test_parse_decision_response_invalid_decision():
    """Test that invalid decision types are rejected."""
    response_text = '{"decision": "INVALID_TYPE", "confidence": 0.7, "reasoning": "Test"}'
    decision, confidence, reasoning = _parse_decision_response(response_text)

    # Should fail to parse due to invalid decision type
    assert decision is None or decision not in ["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]


def test_parse_decision_response_invalid():
    """Test complete parse failure returns (None, None, None)."""
    response_text = "This is completely invalid text"
    decision, confidence, reasoning = _parse_decision_response(response_text)

    assert decision is None
    assert confidence is None
    assert reasoning is None


# ============================================================================
# FALLBACK GENERATION TESTS
# ============================================================================


def test_generate_fallback_decision_low():
    """Test fallback decision for low risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=25.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )

    decision, confidence, reasoning = _generate_fallback_decision(evidence)

    assert decision == "APPROVE"
    assert confidence == 0.75
    assert "bajo" in reasoning.lower()


def test_generate_fallback_decision_medium():
    """Test fallback decision for medium risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=45.0,
        all_signals=["signal1"],
        all_citations=[],
        risk_category="medium",
    )

    decision, confidence, reasoning = _generate_fallback_decision(evidence)

    assert decision == "CHALLENGE"
    assert confidence == 0.70
    assert "medio" in reasoning.lower()


def test_generate_fallback_decision_high():
    """Test fallback decision for high risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=70.0,
        all_signals=["signal1", "signal2"],
        all_citations=[],
        risk_category="high",
    )

    decision, confidence, reasoning = _generate_fallback_decision(evidence)

    assert decision == "BLOCK"
    assert confidence == 0.80
    assert "alto" in reasoning.lower()


def test_generate_fallback_decision_critical():
    """Test fallback decision for critical risk."""
    evidence = AggregatedEvidence(
        composite_risk_score=92.0,
        all_signals=["signal1", "signal2", "signal3"],
        all_citations=[],
        risk_category="critical",
    )

    decision, confidence, reasoning = _generate_fallback_decision(evidence)

    assert decision == "BLOCK"
    assert confidence == 0.90
    assert "crítico" in reasoning.lower()


# ============================================================================
# SAFETY OVERRIDE TESTS
# ============================================================================


def test_safety_override_critical_score():
    """Test safety override for critical risk score > 85."""
    evidence = AggregatedEvidence(
        composite_risk_score=92.0,
        all_signals=[],
        all_citations=[],
        risk_category="critical",
    )

    # Original decision: APPROVE (should be overridden)
    decision, confidence, reasoning = _apply_safety_overrides(
        "APPROVE",
        0.60,
        "Original reasoning",
        evidence.composite_risk_score,
    )

    assert decision == "BLOCK"  # Overridden
    assert confidence >= 0.85  # Confidence increased
    assert "OVERRIDE DE SEGURIDAD" in reasoning


def test_safety_override_low_confidence():
    """Test safety override for low confidence < 0.55."""
    evidence = AggregatedEvidence(
        composite_risk_score=50.0,
        all_signals=[],
        all_citations=[],
        risk_category="medium",
    )

    # Original decision with low confidence
    decision, confidence, reasoning = _apply_safety_overrides(
        "CHALLENGE",
        0.45,  # Low confidence
        "Original reasoning",
        evidence.composite_risk_score,
    )

    assert decision == "ESCALATE_TO_HUMAN"  # Overridden
    assert "ESCALADO POR BAJA CONFIANZA" in reasoning


def test_safety_override_no_override_needed():
    """Test no override when conditions are not met."""
    evidence = AggregatedEvidence(
        composite_risk_score=60.0,  # Not > 85
        all_signals=[],
        all_citations=[],
        risk_category="high",
    )

    # Good confidence, reasonable score
    decision, confidence, reasoning = _apply_safety_overrides(
        "BLOCK",
        0.80,  # Good confidence
        "Original reasoning",
        evidence.composite_risk_score,
    )

    assert decision == "BLOCK"  # No change
    assert confidence == 0.80  # No change
    assert reasoning == "Original reasoning"  # No change


def test_safety_override_both_conditions():
    """Test override when both conditions are met (critical score takes priority)."""
    evidence = AggregatedEvidence(
        composite_risk_score=90.0,  # Critical
        all_signals=[],
        all_citations=[],
        risk_category="critical",
    )

    decision, confidence, reasoning = _apply_safety_overrides(
        "APPROVE",
        0.45,  # Low confidence
        "Original",
        evidence.composite_risk_score,
    )

    # Critical score override takes priority
    assert decision == "BLOCK"
    assert "OVERRIDE DE SEGURIDAD" in reasoning


# ============================================================================
# CITATION BUILDER TESTS
# ============================================================================


def test_build_citations_internal():
    """Test building internal citations from policy matches."""
    evidence = AggregatedEvidence(
        composite_risk_score=60.0,
        all_signals=[],
        all_citations=[
            "FP-01: Transacciones nocturnas > 3x promedio",
            "FP-02: Dispositivo no reconocido",
            "Threat: merchant_watchlist (confidence: 0.85)",  # Should be ignored
        ],
        risk_category="high",
    )

    citations = _build_citations_internal(evidence)

    assert len(citations) == 2
    assert citations[0]["policy_id"] == "FP-01"
    assert "nocturnas" in citations[0]["text"]
    assert citations[1]["policy_id"] == "FP-02"


def test_build_citations_internal_no_policies():
    """Test building internal citations when no policies exist."""
    evidence = AggregatedEvidence(
        composite_risk_score=20.0,
        all_signals=[],
        all_citations=["Threat: some_threat (confidence: 0.3)"],
        risk_category="low",
    )

    citations = _build_citations_internal(evidence)

    assert citations == []  # No policy citations


def test_build_citations_external():
    """Test building external citations from threat intel."""
    evidence = AggregatedEvidence(
        composite_risk_score=60.0,
        all_signals=[],
        all_citations=[
            "FP-01: Policy match",  # Should be ignored
            "Threat: merchant_watchlist (confidence: 0.85)",
            "Threat: high_risk_country_IR (confidence: 1.0)",
        ],
        risk_category="high",
    )

    citations = _build_citations_external(evidence)

    assert len(citations) == 2
    assert citations[0]["source"] == "merchant_watchlist"
    assert "0.85" in citations[0]["detail"]
    assert citations[1]["source"] == "high_risk_country_IR"


def test_build_citations_external_no_threats():
    """Test building external citations when no threats exist."""
    evidence = AggregatedEvidence(
        composite_risk_score=20.0,
        all_signals=[],
        all_citations=["FP-01: Policy only"],
        risk_category="low",
    )

    citations = _build_citations_external(evidence)

    # Should have placeholder
    assert len(citations) == 1
    assert citations[0]["source"] == "external_threat_check"


# ============================================================================
# EXPLANATION GENERATOR TESTS
# ============================================================================


def test_generate_customer_explanation_approve():
    """Test customer explanation for APPROVE decision."""
    explanation = _generate_customer_explanation("APPROVE")

    assert "aprobada" in explanation.lower()
    assert "orden" in explanation.lower()


def test_generate_customer_explanation_challenge():
    """Test customer explanation for CHALLENGE decision."""
    explanation = _generate_customer_explanation("CHALLENGE")

    assert "verificar" in explanation.lower()
    assert "inusual" in explanation.lower()


def test_generate_customer_explanation_block():
    """Test customer explanation for BLOCK decision."""
    explanation = _generate_customer_explanation("BLOCK")

    assert "bloqueado" in explanation.lower() or "bloqueada" in explanation.lower()
    assert "sospechosa" in explanation.lower()


def test_generate_customer_explanation_escalate():
    """Test customer explanation for ESCALATE_TO_HUMAN decision."""
    explanation = _generate_customer_explanation("ESCALATE_TO_HUMAN")

    assert "revisión" in explanation.lower()


def test_generate_audit_explanation():
    """Test audit explanation generation."""
    evidence = AggregatedEvidence(
        composite_risk_score=68.5,
        all_signals=["high_amount", "off_hours"],
        all_citations=[],
        risk_category="high",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test fraud",
        pro_fraud_confidence=0.78,
        pro_fraud_evidence=["e1"],
        pro_customer_argument="Test customer",
        pro_customer_confidence=0.55,
        pro_customer_evidence=["e2"],
    )

    explanation = _generate_audit_explanation(
        "BLOCK",
        0.80,
        "Test reasoning",
        evidence,
        debate,
    )

    assert "BLOCK" in explanation
    assert "0.80" in explanation or "0.8" in explanation
    assert "68.5" in explanation
    assert "0.78" in explanation
    assert "0.55" in explanation


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_extract_agent_trace():
    """Test extracting agent trace from state."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "trace": [
            AgentTraceEntry(
                agent_name="transaction_context",
                timestamp=datetime.now(UTC),
                duration_ms=10.0,
                input_summary="Test",
                output_summary="Test",
                status="success",
            ),
            AgentTraceEntry(
                agent_name="evidence_aggregation",
                timestamp=datetime.now(UTC),
                duration_ms=5.0,
                input_summary="Test",
                output_summary="Test",
                status="success",
            ),
        ],
    }

    trace = _extract_agent_trace(state)

    assert trace == ["transaction_context", "evidence_aggregation"]


def test_extract_agent_trace_empty():
    """Test extracting agent trace when empty."""
    state: OrchestratorState = {}

    trace = _extract_agent_trace(state)

    assert trace == []


# ============================================================================
# LLM CALL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_call_llm_for_decision_success():
    """Test successful LLM call for decision."""
    evidence = AggregatedEvidence(
        composite_risk_score=68.5,
        all_signals=["high_amount", "off_hours"],
        all_citations=["FP-01: Policy match"],
        risk_category="high",
    )

    debate = DebateArguments(
        pro_fraud_argument="Fraude probable",
        pro_fraud_confidence=0.78,
        pro_fraud_evidence=["e1"],
        pro_customer_argument="Podría ser legítimo",
        pro_customer_confidence=0.55,
        pro_customer_evidence=["e2"],
    )

    # Mock LLM response
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = """```json
{
  "decision": "BLOCK",
  "confidence": 0.82,
  "reasoning": "Evidencia fuerte de fraude"
}
```"""
    mock_llm.ainvoke.return_value = mock_response

    decision, confidence, reasoning = await _call_llm_for_decision(mock_llm, evidence, debate)

    assert decision == "BLOCK"
    assert confidence == 0.82
    assert reasoning == "Evidencia fuerte de fraude"


@pytest.mark.asyncio
async def test_call_llm_for_decision_timeout():
    """Test LLM timeout handling."""
    evidence = AggregatedEvidence(
        composite_risk_score=50.0,
        all_signals=[],
        all_citations=[],
        risk_category="medium",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.6,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.6,
        pro_customer_evidence=[],
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = TimeoutError("LLM timeout")

    with patch("app.agents.decision_arbiter.asyncio.wait_for", side_effect=TimeoutError):
        decision, confidence, reasoning = await _call_llm_for_decision(mock_llm, evidence, debate)

    assert decision is None
    assert confidence is None
    assert reasoning is None


# ============================================================================
# AGENT INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_decision_arbiter_agent_success():
    """Test decision arbiter agent with successful LLM call."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1001",
            customer_id="C-001",
            amount=1800.0,
            currency="PEN",
            merchant_id="M-001",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="web",
            device_id="D-001",
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=72.0,
            all_signals=["high_amount", "off_hours"],
            all_citations=["FP-01: Nocturnal transaction"],
            risk_category="high",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Alta probabilidad de fraude",
            pro_fraud_confidence=0.80,
            pro_fraud_evidence=["e1", "e2"],
            pro_customer_argument="Podría ser legítimo",
            pro_customer_confidence=0.60,
            pro_customer_evidence=["e3"],
        ),
        "trace": [],
    }

    with patch("app.agents.decision_arbiter.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "decision": "BLOCK",
            "confidence": 0.85,
            "reasoning": "Evidencia fuerte de fraude",
        })
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await decision_arbiter_agent(state)

    assert "decision" in result
    assert result["decision"].decision == "BLOCK"
    assert result["decision"].confidence == 0.85
    assert result["decision"].transaction_id == "T-1001"


@pytest.mark.asyncio
async def test_decision_arbiter_agent_llm_timeout_uses_fallback():
    """Test decision arbiter uses fallback when LLM times out."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1002",
            customer_id="C-002",
            amount=500.0,
            currency="PEN",
            merchant_id="M-002",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="mobile",
            device_id="D-002",
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=25.0,
            all_signals=[],
            all_citations=[],
            risk_category="low",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Riesgo bajo",
            pro_fraud_confidence=0.30,
            pro_fraud_evidence=[],
            pro_customer_argument="Legítimo",
            pro_customer_confidence=0.85,
            pro_customer_evidence=["e1"],
        ),
        "trace": [],
    }

    with patch("app.agents.decision_arbiter.get_llm") as mock_get_llm, \
         patch("app.agents.decision_arbiter.asyncio.wait_for", side_effect=TimeoutError):
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm

        result = await decision_arbiter_agent(state)

    # Should use fallback based on low risk_category
    assert result["decision"].decision == "APPROVE"
    assert result["decision"].confidence == 0.75


@pytest.mark.asyncio
async def test_decision_arbiter_agent_safety_override_critical():
    """Test safety override for critical risk score."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1003",
            customer_id="C-003",
            amount=5000.0,
            currency="PEN",
            merchant_id="M-003",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="web",
            device_id="D-003",
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=92.0,  # Critical > 85
            all_signals=["critical1", "critical2"],
            all_citations=[],
            risk_category="critical",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Fraude crítico",
            pro_fraud_confidence=0.95,
            pro_fraud_evidence=["e1"],
            pro_customer_argument="Muy sospechoso",
            pro_customer_confidence=0.20,
            pro_customer_evidence=[],
        ),
        "trace": [],
    }

    with patch("app.agents.decision_arbiter.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        # LLM suggests CHALLENGE, but should be overridden to BLOCK
        mock_response.content = json.dumps({
            "decision": "CHALLENGE",
            "confidence": 0.70,
            "reasoning": "Test",
        })
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await decision_arbiter_agent(state)

    # Should override to BLOCK due to critical score
    assert result["decision"].decision == "BLOCK"
    assert "OVERRIDE DE SEGURIDAD" in result["decision"].explanation_audit


@pytest.mark.asyncio
async def test_decision_arbiter_agent_no_evidence():
    """Test decision arbiter when evidence is missing."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1004",
            customer_id="C-004",
            amount=1000.0,
            currency="PEN",
            merchant_id="M-004",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="web",
            device_id="D-004",
        ),
        "trace": [],
    }

    result = await decision_arbiter_agent(state)

    # Should escalate to human due to missing evidence
    assert result["decision"].decision == "ESCALATE_TO_HUMAN"
    assert result["decision"].confidence == 0.0


@pytest.mark.asyncio
async def test_decision_arbiter_agent_exception_handling():
    """Test decision arbiter handles exceptions gracefully."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1005",
            customer_id="C-005",
            amount=1000.0,
            currency="PEN",
            merchant_id="M-005",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="web",
            device_id="D-005",
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=50.0,
            all_signals=[],
            all_citations=[],
            risk_category="medium",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Test",
            pro_fraud_confidence=0.6,
            pro_fraud_evidence=[],
            pro_customer_argument="Test",
            pro_customer_confidence=0.6,
            pro_customer_evidence=[],
        ),
        "trace": [],
    }

    with patch("app.agents.decision_arbiter.get_llm", side_effect=Exception("Test error")):
        result = await decision_arbiter_agent(state)

    # Should return error decision with ESCALATE_TO_HUMAN
    assert result["decision"].decision == "ESCALATE_TO_HUMAN"
    assert "error" in result["decision"].explanation_audit.lower()
