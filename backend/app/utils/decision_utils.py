"""Helper functions extracted from decision_arbiter.py.

Provides safety overrides, citation builders, explanation generators,
and fallback decision logic for the Decision Arbiter agent.
"""

import re

from app.models import AggregatedEvidence, DebateArguments
from app.utils.logger import get_logger

from ..constants import SAFETY_OVERRIDES

logger = get_logger(__name__)


def apply_safety_overrides(
    decision: str,
    confidence: float,
    reasoning: str,
    composite_score: float,
) -> tuple[str, float, str]:
    """Apply safety overrides to ensure critical cases are handled properly.

    Override Rules:
    1. If composite_risk_score > critical_risk_threshold → always BLOCK
    2. If confidence < low_confidence_threshold → ESCALATE_TO_HUMAN

    Returns:
        Tuple of (final_decision, final_confidence, final_reasoning)
    """
    original_decision = decision

    # Override 1: Critical risk score → always BLOCK
    if composite_score > SAFETY_OVERRIDES.critical_risk_threshold:
        if decision != "BLOCK":
            logger.warning(
                "safety_override_critical_score",
                original_decision=decision,
                composite_score=composite_score,
                new_decision="BLOCK",
            )
            decision = "BLOCK"
            confidence = max(confidence, 0.85)
            reasoning = (
                f"OVERRIDE DE SEGURIDAD: Puntaje de riesgo crítico ({composite_score}/100) "
                f"requiere bloqueo inmediato independientemente del análisis. {reasoning}"
            )

    # Override 2: Low confidence → ESCALATE_TO_HUMAN
    if confidence < SAFETY_OVERRIDES.low_confidence_threshold:
        if decision != "ESCALATE_TO_HUMAN":
            logger.warning(
                "safety_override_low_confidence",
                original_decision=decision,
                confidence=confidence,
                new_decision="ESCALATE_TO_HUMAN",
            )
            decision = "ESCALATE_TO_HUMAN"
            reasoning = (
                f"ESCALADO POR BAJA CONFIANZA: Confianza {confidence:.2f} < {SAFETY_OVERRIDES.low_confidence_threshold}. "
                f"Caso requiere revisión humana. Decisión original: {original_decision}. {reasoning}"
            )

    if decision != original_decision:
        logger.info(
            "safety_override_applied",
            original=original_decision,
            final=decision,
            reason="critical_score"
            if composite_score > SAFETY_OVERRIDES.critical_risk_threshold
            else "low_confidence",
        )

    return decision, confidence, reasoning


def build_citations_internal(evidence: AggregatedEvidence) -> list[dict]:
    """Build internal citations from policy matches.

    Returns:
        List of citation dicts with policy_id and text
    """
    citations = []
    for citation in evidence.all_citations:
        if citation.startswith("FP-"):
            parts = citation.split(":", 1)
            if len(parts) == 2:
                citations.append({"policy_id": parts[0].strip(), "text": parts[1].strip()})
    return citations


def build_citations_external(evidence: AggregatedEvidence) -> list[dict]:
    """Build external citations from threat intelligence.

    Returns:
        List of citation dicts with source and detail
    """
    citations = []
    for citation in evidence.all_citations:
        if citation.startswith("Threat:"):
            match = re.match(r"Threat:\s*(.+?)\s*\(confidence:\s*([\d.]+)\)", citation)
            if match:
                citations.append(
                    {
                        "source": match.group(1),
                        "detail": f"Confidence: {match.group(2)}",
                    }
                )
            else:
                citations.append(
                    {
                        "source": "external_threat",
                        "detail": citation.replace("Threat: ", ""),
                    }
                )

    if not citations:
        citations.append(
            {
                "source": "external_threat_check",
                "detail": "No external threats detected",
            }
        )

    return citations


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

    logger.info(
        "fallback_decision_generated",
        risk_category=risk_category,
        decision=decision,
        confidence=confidence,
    )
    return decision, confidence, reasoning


def generate_customer_explanation(decision: str) -> str:
    """Generate customer-facing explanation based on decision."""
    templates = {
        "APPROVE": "Su transacción ha sido aprobada. Todo está en orden.",
        "CHALLENGE": "Hemos detectado actividad inusual en su cuenta. "
        "Por seguridad, necesitamos verificar esta transacción. "
        "Le contactaremos pronto.",
        "BLOCK": "Por su seguridad, hemos bloqueado esta transacción debido a actividad sospechosa. "
        "Si usted autorizó esta transacción, por favor contáctenos de inmediato.",
        "ESCALATE_TO_HUMAN": "Su transacción está en revisión. "
        "Nuestro equipo de seguridad la analizará y le contactaremos pronto.",
    }
    return templates.get(
        decision,
        "Su transacción está siendo procesada. Le contactaremos si necesitamos más información.",
    )


def generate_audit_explanation(
    decision: str,
    confidence: float,
    reasoning: str,
    evidence: AggregatedEvidence,
    debate: DebateArguments,
) -> str:
    """Generate audit trail explanation with full context."""
    audit_parts = [
        f"DECISIÓN: {decision} (confianza: {confidence:.2f})",
        f"Riesgo compuesto: {evidence.composite_risk_score:.1f}/100 ({evidence.risk_category})",
        f"Debate adversarial: pro-fraude {debate.pro_fraud_confidence:.2f} vs "
        f"pro-cliente {debate.pro_customer_confidence:.2f}",
        f"Razonamiento: {reasoning}",
    ]

    if evidence.all_signals:
        audit_parts.append(
            f"Señales detectadas ({len(evidence.all_signals)}): {', '.join(evidence.all_signals[:5])}"
        )

    return " | ".join(audit_parts)
