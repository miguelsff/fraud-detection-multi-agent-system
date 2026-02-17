"""Unit tests for explainability agent."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.explainability import (
    _call_llm_for_explanation,
    _enhance_audit_explanation,
    _enhance_customer_explanation,
    _generate_fallback_explanations,
    _get_safe_customer_template,
    _parse_explanation_response,
    explainability_agent,
)
from app.models import (
    AggregatedEvidence,
    DebateArguments,
    FraudDecision,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    Transaction,
)


# ============================================================================
# PARSING TESTS
# ============================================================================


def test_parse_explanation_response_valid_json():
    """Test parsing valid JSON response."""
    response_text = """```json
{
  "customer_explanation": "Su transacción ha sido aprobada.",
  "audit_explanation": "Transacción T-001 aprobada con confianza 0.85.",
  "key_factors": ["bajo_riesgo", "cliente_conocido"],
  "recommended_actions": ["aprobar", "monitorear"]
}
```"""

    customer, audit, factors, actions = _parse_explanation_response(response_text)

    assert customer == "Su transacción ha sido aprobada."
    assert audit == "Transacción T-001 aprobada con confianza 0.85."
    assert factors == ["bajo_riesgo", "cliente_conocido"]
    assert actions == ["aprobar", "monitorear"]


def test_parse_explanation_response_minimal():
    """Test parsing minimal response without factors/actions."""
    response_text = """{
  "customer_explanation": "Explicación al cliente.",
  "audit_explanation": "Explicación de auditoría."
}"""

    customer, audit, factors, actions = _parse_explanation_response(response_text)

    assert customer == "Explicación al cliente."
    assert audit == "Explicación de auditoría."
    assert factors == []
    assert actions == []


def test_parse_explanation_response_regex_fallback():
    """Test regex fallback when JSON parsing fails."""
    response_text = """
Las explicaciones son:
"customer_explanation": "Mensaje para el cliente"
"audit_explanation": "Mensaje de auditoría"
"key_factors": ["factor1", "factor2"]
"recommended_actions": ["accion1"]
"""

    customer, audit, factors, actions = _parse_explanation_response(response_text)

    assert customer == "Mensaje para el cliente"
    assert audit == "Mensaje de auditoría"
    assert factors == ["factor1", "factor2"]
    assert actions == ["accion1"]


def test_parse_explanation_response_invalid():
    """Test complete parse failure returns (None, None, [], [])."""
    response_text = "This is completely invalid text"

    customer, audit, factors, actions = _parse_explanation_response(response_text)

    assert customer is None
    assert audit is None
    assert factors == []
    assert actions == []


# ============================================================================
# FALLBACK GENERATION TESTS
# ============================================================================


def test_generate_fallback_explanations_approve():
    """Test fallback explanations for APPROVE decision."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-001",
        decision="APPROVE",
        confidence=0.85,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=20.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.30,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.85,
        pro_customer_evidence=[],
    )

    customer, audit = _generate_fallback_explanations(
        decision,
        evidence,
        None,
        debate,
    )

    assert "procesada exitosamente" in customer or "aprobada" in customer
    assert "T-001" in audit
    assert "APPROVE" in audit
    assert "0.85" in audit or "0.8" in audit


def test_generate_fallback_explanations_challenge():
    """Test fallback explanations for CHALLENGE decision."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-002",
        decision="CHALLENGE",
        confidence=0.72,
        signals=["high_amount"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=55.0,
        all_signals=["high_amount"],
        all_citations=[],
        risk_category="medium",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.70,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.60,
        pro_customer_evidence=[],
    )

    customer, audit = _generate_fallback_explanations(
        decision,
        evidence,
        None,
        debate,
    )

    assert "verificar" in customer.lower()
    assert "CHALLENGE" in audit
    assert "medium" in audit


def test_generate_fallback_explanations_block():
    """Test fallback explanations for BLOCK decision."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-003",
        decision="BLOCK",
        confidence=0.88,
        signals=["high_amount", "unknown_device"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=75.0,
        all_signals=["high_amount", "unknown_device"],
        all_citations=[],
        risk_category="high",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.90,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.40,
        pro_customer_evidence=[],
    )

    customer, audit = _generate_fallback_explanations(
        decision,
        evidence,
        None,
        debate,
    )

    assert "bloqueado" in customer.lower() or "bloqueada" in customer.lower()
    assert "BLOCK" in audit
    assert "high" in audit


def test_generate_fallback_explanations_escalate():
    """Test fallback explanations for ESCALATE_TO_HUMAN decision."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-004",
        decision="ESCALATE_TO_HUMAN",
        confidence=0.45,
        signals=["ambiguous"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=50.0,
        all_signals=["ambiguous"],
        all_citations=[],
        risk_category="medium",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.55,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.55,
        pro_customer_evidence=[],
    )

    customer, audit = _generate_fallback_explanations(
        decision,
        evidence,
        None,
        debate,
    )

    assert "revisión" in customer.lower() or "revisada" in customer.lower()
    assert "ESCALATE_TO_HUMAN" in audit


def test_generate_fallback_explanations_with_policies():
    """Test fallback explanations include policy information."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-005",
        decision="BLOCK",
        confidence=0.85,
        signals=["policy_match"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=70.0,
        all_signals=["policy_match"],
        all_citations=[],
        risk_category="high",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.80,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.50,
        pro_customer_evidence=[],
    )

    policy_matches = PolicyMatchResult(
        matches=[
            PolicyMatch(policy_id="FP-01", description="Test policy", relevance_score=0.9)
        ],
        chunk_ids=["chunk1"],
    )

    customer, audit = _generate_fallback_explanations(
        decision,
        evidence,
        policy_matches,
        debate,
    )

    assert "1 políticas aplicadas" in audit


# ============================================================================
# ENHANCEMENT TESTS
# ============================================================================


def test_enhance_customer_explanation_safe():
    """Test enhancement accepts safe customer explanation."""
    explanation = "Su transacción requiere verificación adicional por seguridad."

    enhanced = _enhance_customer_explanation(explanation, "CHALLENGE")

    assert enhanced == explanation  # No change


def test_enhance_customer_explanation_contains_score():
    """Test enhancement detects 'score' keyword."""
    explanation = "Su transacción tiene un score de riesgo de 75."

    enhanced = _enhance_customer_explanation(explanation, "CHALLENGE")

    # Should be replaced with safe template
    assert "score" not in enhanced.lower()
    assert "verificar" in enhanced.lower()


def test_enhance_customer_explanation_contains_policy():
    """Test enhancement detects policy references."""
    explanation = "Su transacción viola la política FP-01."

    enhanced = _enhance_customer_explanation(explanation, "BLOCK")

    # Should be replaced with safe template
    assert "FP-" not in enhanced
    assert "bloqueado" in enhanced.lower() or "bloqueada" in enhanced.lower()


def test_enhance_customer_explanation_contains_confidence():
    """Test enhancement detects 'confidence' keyword."""
    explanation = "Tenemos una confianza: 0.85 en esta decisión."

    enhanced = _enhance_customer_explanation(explanation, "APPROVE")

    # Should be replaced with safe template
    assert "confianza:" not in enhanced.lower()


def test_get_safe_customer_template():
    """Test safe customer template generation."""
    templates = {
        "APPROVE": _get_safe_customer_template("APPROVE"),
        "CHALLENGE": _get_safe_customer_template("CHALLENGE"),
        "BLOCK": _get_safe_customer_template("BLOCK"),
        "ESCALATE_TO_HUMAN": _get_safe_customer_template("ESCALATE_TO_HUMAN"),
    }

    # All templates should be non-empty
    assert all(templates.values())

    # Check key phrases
    assert "aprobada" in templates["APPROVE"].lower() or "orden" in templates["APPROVE"].lower()
    assert "verificar" in templates["CHALLENGE"].lower()
    assert "bloqueado" in templates["BLOCK"].lower() or "bloqueada" in templates["BLOCK"].lower()
    assert "revisión" in templates["ESCALATE_TO_HUMAN"].lower()


def test_enhance_audit_explanation_complete():
    """Test enhancement leaves complete audit explanation unchanged."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-001",
        decision="CHALLENGE",
        confidence=0.72,
        signals=["test"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=55.0,
        all_signals=["test"],
        all_citations=[],
        risk_category="medium",
    )

    # Complete explanation with all required elements
    explanation = "Transacción T-001: CHALLENGE (0.72). Riesgo: 55.0/100 (medium)."

    enhanced = _enhance_audit_explanation(explanation, decision, evidence, None)

    # Should be unchanged (all elements present)
    assert "T-001" in enhanced
    assert "CHALLENGE" in enhanced


def test_enhance_audit_explanation_missing_elements():
    """Test enhancement adds missing audit elements."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-002",
        decision="BLOCK",
        confidence=0.85,
        signals=["test"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=75.0,
        all_signals=["test"],
        all_citations=[],
        risk_category="high",
    )

    # Incomplete explanation missing transaction ID and risk score
    explanation = "Decision was made based on evidence."

    enhanced = _enhance_audit_explanation(explanation, decision, evidence, None)

    # Should add missing elements
    assert "T-002" in enhanced
    assert "BLOCK" in enhanced or "0.85" in enhanced
    assert "75" in enhanced or "high" in enhanced


def test_enhance_audit_explanation_adds_policies():
    """Test enhancement adds policy IDs if missing."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-003",
        decision="CHALLENGE",
        confidence=0.70,
        signals=["test"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=60.0,
        all_signals=["test"],
        all_citations=[],
        risk_category="high",
    )

    policy_matches = PolicyMatchResult(
        matches=[
            PolicyMatch(policy_id="FP-01", description="Test", relevance_score=0.9),
            PolicyMatch(policy_id="FP-02", description="Test", relevance_score=0.8),
        ],
        chunk_ids=["chunk1", "chunk2"],
    )

    # Explanation without policy mentions
    explanation = "Transacción T-003: CHALLENGE (0.70). Riesgo: 60.0/100."

    enhanced = _enhance_audit_explanation(explanation, decision, evidence, policy_matches)

    # Should add policy IDs
    assert "FP-01" in enhanced
    assert "FP-02" in enhanced


# ============================================================================
# LLM CALL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_call_llm_for_explanation_success():
    """Test successful LLM call for explanation."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-001",
        decision="CHALLENGE",
        confidence=0.72,
        signals=["high_amount"],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=60.0,
        all_signals=["high_amount"],
        all_citations=[],
        risk_category="high",
    )

    debate = DebateArguments(
        pro_fraud_argument="Fraude probable",
        pro_fraud_confidence=0.75,
        pro_fraud_evidence=["e1"],
        pro_customer_argument="Podría ser legítimo",
        pro_customer_confidence=0.60,
        pro_customer_evidence=["e2"],
    )

    # Mock LLM response
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = """```json
{
  "customer_explanation": "Necesitamos verificar esta transacción.",
  "audit_explanation": "Transacción T-001 requiere verificación adicional.",
  "key_factors": ["monto_elevado"],
  "recommended_actions": ["verificar_sms"]
}
```"""
    mock_llm.ainvoke.return_value = mock_response

    customer, audit, factors, actions, llm_trace = await _call_llm_for_explanation(
        mock_llm,
        decision,
        evidence,
        None,
        debate,
    )

    assert customer == "Necesitamos verificar esta transacción."
    assert audit == "Transacción T-001 requiere verificación adicional."
    assert factors == ["monto_elevado"]
    assert actions == ["verificar_sms"]
    assert isinstance(llm_trace, dict)


@pytest.mark.asyncio
async def test_call_llm_for_explanation_timeout():
    """Test LLM timeout handling."""
    from datetime import datetime, UTC

    decision = FraudDecision(
        transaction_id="T-001",
        decision="APPROVE",
        confidence=0.80,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="",
        explanation_audit="",
        agent_trace=[],
    )

    evidence = AggregatedEvidence(
        composite_risk_score=25.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )

    debate = DebateArguments(
        pro_fraud_argument="Test",
        pro_fraud_confidence=0.30,
        pro_fraud_evidence=[],
        pro_customer_argument="Test",
        pro_customer_confidence=0.80,
        pro_customer_evidence=[],
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = TimeoutError("LLM timeout")

    with patch("app.agents.explainability.asyncio.wait_for", side_effect=TimeoutError):
        customer, audit, factors, actions, llm_trace = await _call_llm_for_explanation(
            mock_llm,
            decision,
            evidence,
            None,
            debate,
        )

    assert customer is None
    assert audit is None
    assert factors == []
    assert actions == []
    assert isinstance(llm_trace, dict)


# ============================================================================
# AGENT INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_explainability_agent_success():
    """Test explainability agent with successful LLM call."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-001",
            customer_id="C-001",
            amount=1800.0,
            currency="PEN",
            merchant_id="M-001",
            timestamp=datetime.now(UTC),
            country="PE",
            channel="web",
            device_id="D-001",
        ),
        "decision": FraudDecision(
            transaction_id="T-001",
            decision="CHALLENGE",
            confidence=0.72,
            signals=["high_amount"],
            citations_internal=[],
            citations_external=[],
            explanation_customer="",
            explanation_audit="",
            agent_trace=[],
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=60.0,
            all_signals=["high_amount"],
            all_citations=[],
            risk_category="high",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Probable fraude",
            pro_fraud_confidence=0.75,
            pro_fraud_evidence=["e1"],
            pro_customer_argument="Podría ser legítimo",
            pro_customer_confidence=0.60,
            pro_customer_evidence=["e2"],
        ),
        "policy_matches": None,
    }

    with patch("app.agents.explainability.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.model = "test-model"
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "customer_explanation": "Necesitamos verificar esta transacción.",
            "audit_explanation": "Transacción T-001 analizada.",
            "key_factors": ["monto"],
            "recommended_actions": ["verificar"],
        })
        del mock_response.response_metadata
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await explainability_agent(state)

    assert "explanation" in result
    assert result["explanation"].customer_explanation
    assert result["explanation"].audit_explanation


@pytest.mark.asyncio
async def test_explainability_agent_llm_timeout_uses_fallback():
    """Test explainability uses fallback when LLM times out."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "decision": FraudDecision(
            transaction_id="T-002",
            decision="APPROVE",
            confidence=0.85,
            signals=[],
            citations_internal=[],
            citations_external=[],
            explanation_customer="",
            explanation_audit="",
            agent_trace=[],
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=20.0,
            all_signals=[],
            all_citations=[],
            risk_category="low",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Bajo riesgo",
            pro_fraud_confidence=0.25,
            pro_fraud_evidence=[],
            pro_customer_argument="Legítimo",
            pro_customer_confidence=0.85,
            pro_customer_evidence=[],
        ),
        "policy_matches": None,
    }

    with patch("app.agents.explainability.get_llm") as mock_get_llm, \
         patch("app.agents.explainability.asyncio.wait_for", side_effect=TimeoutError):
        mock_llm = AsyncMock()
        mock_llm.model = "test-model"
        mock_get_llm.return_value = mock_llm

        result = await explainability_agent(state)

    # Should use fallback
    assert "explanation" in result
    assert "procesada" in result["explanation"].customer_explanation or \
           "aprobada" in result["explanation"].customer_explanation
    assert "T-002" in result["explanation"].audit_explanation


@pytest.mark.asyncio
async def test_explainability_agent_sanitizes_customer_explanation():
    """Test that customer explanation is sanitized."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "decision": FraudDecision(
            transaction_id="T-003",
            decision="BLOCK",
            confidence=0.88,
            signals=["critical"],
            citations_internal=[],
            citations_external=[],
            explanation_customer="",
            explanation_audit="",
            agent_trace=[],
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=80.0,
            all_signals=["critical"],
            all_citations=[],
            risk_category="high",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Fraude confirmado",
            pro_fraud_confidence=0.90,
            pro_fraud_evidence=["e1"],
            pro_customer_argument="Muy sospechoso",
            pro_customer_confidence=0.30,
            pro_customer_evidence=[],
        ),
        "policy_matches": None,
    }

    with patch("app.agents.explainability.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.model = "test-model"
        mock_response = MagicMock()
        # LLM returns explanation with internal details (should be sanitized)
        mock_response.content = json.dumps({
            "customer_explanation": "Su transacción tiene un score de 80 y viola la política FP-01.",
            "audit_explanation": "Test audit",
            "key_factors": [],
            "recommended_actions": [],
        })
        del mock_response.response_metadata
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = await explainability_agent(state)

    # Customer explanation should be replaced with safe template
    assert "score" not in result["explanation"].customer_explanation.lower()
    assert "FP-" not in result["explanation"].customer_explanation


@pytest.mark.asyncio
async def test_explainability_agent_no_decision():
    """Test explainability when decision is missing."""
    state: OrchestratorState = {}

    result = await explainability_agent(state)

    # Should return error explanation
    assert "explanation" in result
    assert "procesada" in result["explanation"].customer_explanation.lower()
    assert "ERROR" in result["explanation"].audit_explanation


@pytest.mark.asyncio
async def test_explainability_agent_exception_handling():
    """Test explainability handles exceptions gracefully."""
    from datetime import datetime, UTC

    state: OrchestratorState = {
        "decision": FraudDecision(
            transaction_id="T-004",
            decision="CHALLENGE",
            confidence=0.70,
            signals=[],
            citations_internal=[],
            citations_external=[],
            explanation_customer="",
            explanation_audit="",
            agent_trace=[],
        ),
        "evidence": AggregatedEvidence(
            composite_risk_score=50.0,
            all_signals=[],
            all_citations=[],
            risk_category="medium",
        ),
        "debate": DebateArguments(
            pro_fraud_argument="Test",
            pro_fraud_confidence=0.60,
            pro_fraud_evidence=[],
            pro_customer_argument="Test",
            pro_customer_confidence=0.60,
            pro_customer_evidence=[],
        ),
        "policy_matches": None,
    }

    with patch("app.agents.explainability.get_llm", side_effect=Exception("Test error")):
        result = await explainability_agent(state)

    # Should return error explanation
    assert "explanation" in result
    assert "ERROR" in result["explanation"].audit_explanation
