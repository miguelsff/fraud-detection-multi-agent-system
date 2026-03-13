"""Safety overrides domain service — pure decision override logic.

Extracted from utils/decision_utils.py. No I/O, no infrastructure imports.
"""

from ..constants import SAFETY_OVERRIDES
from ..models import AggregatedEvidence


def apply_safety_overrides(
    decision: str,
    confidence: float,
    reasoning: str,
    composite_score: float,
) -> tuple[str, float, str]:
    """Apply safety overrides to ensure critical cases are handled properly.

    Override Rules:
    1. If composite_risk_score > critical_risk_threshold -> always BLOCK
    2. If confidence < low_confidence_threshold -> ESCALATE_TO_HUMAN

    Returns:
        Tuple of (final_decision, final_confidence, final_reasoning)
    """
    original_decision = decision

    # Override 1: Critical risk score -> always BLOCK
    if composite_score > SAFETY_OVERRIDES.critical_risk_threshold:
        if decision != "BLOCK":
            decision = "BLOCK"
            confidence = max(confidence, 0.85)
            reasoning = (
                f"OVERRIDE DE SEGURIDAD: Puntaje de riesgo crítico ({composite_score}/100) "
                f"requiere bloqueo inmediato independientemente del análisis. {reasoning}"
            )

    # Override 2: Low confidence -> ESCALATE_TO_HUMAN
    if confidence < SAFETY_OVERRIDES.low_confidence_threshold:
        if decision != "ESCALATE_TO_HUMAN":
            decision = "ESCALATE_TO_HUMAN"
            reasoning = (
                f"ESCALADO POR BAJA CONFIANZA: Confianza {confidence:.2f} < {SAFETY_OVERRIDES.low_confidence_threshold}. "
                f"Caso requiere revisión humana. Decisión original: {original_decision}. {reasoning}"
            )

    return decision, confidence, reasoning


def generate_fallback_decision(evidence: AggregatedEvidence) -> tuple[str, float, str]:
    """Generate deterministic decision when LLM fails.

    Maps risk_category to decision type and confidence.
    """
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    mappings = {
        "low": (
            "APPROVE",
            0.75,
            f"Puntaje de riesgo bajo ({composite_score}/100). Señales mínimas de fraude. Transacción aprobada.",
        ),
        "medium": (
            "ESCALATE_TO_HUMAN" if composite_score >= 55 else "CHALLENGE",
            0.55 if composite_score >= 55 else 0.70,
            f"Puntaje de riesgo medio-alto ({composite_score}/100). Señales mixtas requieren revisión humana."
            if composite_score >= 55
            else f"Puntaje de riesgo medio ({composite_score}/100). Verificación adicional recomendada antes de aprobar.",
        ),
        "high": (
            "BLOCK",
            0.80,
            f"Puntaje de riesgo alto ({composite_score}/100). Señales significativas de fraude justifican bloqueo.",
        ),
        "critical": (
            "BLOCK",
            0.90,
            f"Puntaje de riesgo crítico ({composite_score}/100). Múltiples señales de alto riesgo. Bloqueo inmediato requerido.",
        ),
    }

    decision, confidence, reasoning = mappings.get(
        risk_category,
        (
            "ESCALATE_TO_HUMAN",
            0.50,
            "Categoría de riesgo no clasificada. Revisión humana requerida.",
        ),
    )

    return decision, confidence, reasoning
