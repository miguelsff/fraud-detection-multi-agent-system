"""Shared fallback factory functions for pipeline resilience.

Provides safe default objects when upstream phases fail, used by
decision_arbiter and explainability agents.
"""

from app.application.models import AggregatedEvidence, DebateArguments

# Customer-facing explanation templates keyed by decision type.
# Single source of truth — used by decision_arbiter (initial explanation)
# and explainability (fallback & safe-replacement templates).
CUSTOMER_EXPLANATION_TEMPLATES: dict[str, str] = {
    "APPROVE": ("Su transacción ha sido aprobada. Todo está en orden."),
    "CHALLENGE": (
        "Por seguridad, necesitamos verificar esta transacción. Le contactaremos pronto."
    ),
    "BLOCK": (
        "Por su seguridad, hemos bloqueado esta transacción. "
        "Si usted la autorizó, contáctenos de inmediato."
    ),
    "ESCALATE_TO_HUMAN": (
        "Su transacción está en revisión. Nuestro equipo la analizará y le contactaremos pronto."
    ),
}

CUSTOMER_EXPLANATION_DEFAULT = "Su transacción está siendo procesada. Le mantendremos informado."


def get_customer_explanation(decision: str) -> str:
    """Return the customer-facing explanation template for a decision type."""
    return CUSTOMER_EXPLANATION_TEMPLATES.get(decision, CUSTOMER_EXPLANATION_DEFAULT)


def create_minimal_debate() -> DebateArguments:
    """Create minimal debate arguments when the debate phase failed."""
    return DebateArguments(
        pro_fraud_argument="Análisis de debate no disponible.",
        pro_fraud_confidence=0.50,
        pro_fraud_evidence=["debate_unavailable"],
        pro_customer_argument="Análisis de debate no disponible.",
        pro_customer_confidence=0.50,
        pro_customer_evidence=["debate_unavailable"],
    )


def create_minimal_evidence() -> AggregatedEvidence:
    """Create minimal evidence when the evidence phase failed."""
    return AggregatedEvidence(
        composite_risk_score=0.0,
        all_signals=[],
        all_citations=[],
        risk_category="low",
    )
