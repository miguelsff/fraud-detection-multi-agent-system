"""Tests for shared fallback factory functions."""

from app.utils.fallback_factories import (
    CUSTOMER_EXPLANATION_TEMPLATES,
    create_minimal_debate,
    create_minimal_evidence,
    get_customer_explanation,
)


def test_create_minimal_debate_returns_valid():
    """Test that minimal debate has all required fields."""
    debate = create_minimal_debate()

    assert debate.pro_fraud_argument
    assert debate.pro_customer_argument
    assert debate.pro_fraud_confidence == 0.50
    assert debate.pro_customer_confidence == 0.50
    assert len(debate.pro_fraud_evidence) > 0
    assert len(debate.pro_customer_evidence) > 0


def test_create_minimal_evidence_returns_valid():
    """Test that minimal evidence has safe defaults."""
    evidence = create_minimal_evidence()

    assert evidence.composite_risk_score == 0.0
    assert evidence.all_signals == []
    assert evidence.all_citations == []
    assert evidence.risk_category == "low"


def test_customer_explanation_templates_all_decisions():
    """Test that a template exists for every decision type."""
    for decision in ["APPROVE", "CHALLENGE", "BLOCK", "ESCALATE_TO_HUMAN"]:
        explanation = get_customer_explanation(decision)
        assert explanation, f"Missing template for {decision}"
        assert decision not in explanation  # Should not leak decision name


def test_customer_explanation_unknown_decision():
    """Test fallback for unknown decision type."""
    explanation = get_customer_explanation("UNKNOWN")
    assert "procesada" in explanation.lower() or "mantendremos" in explanation.lower()


def test_templates_dict_has_all_four_decisions():
    """Verify the SSOT dict covers all decision types."""
    assert set(CUSTOMER_EXPLANATION_TEMPLATES.keys()) == {
        "APPROVE",
        "CHALLENGE",
        "BLOCK",
        "ESCALATE_TO_HUMAN",
    }
