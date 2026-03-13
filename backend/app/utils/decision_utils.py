"""Helper functions for the Decision Arbiter agent.

Safety overrides and fallback decision logic are re-exported from domain layer.
Citation builders and explanation generators remain here (they use domain models
but are presentation-layer concerns, not pure domain logic).
"""

import re

from app.domain.models import AggregatedEvidence, DebateArguments

# Re-export domain safety overrides for backward compatibility
from app.domain.services.safety_overrides import (  # noqa: F401
    apply_safety_overrides,
    generate_fallback_decision,
)
from .logger import get_logger

logger = get_logger(__name__)


def build_citations_internal(evidence: AggregatedEvidence) -> list[dict]:
    """Build internal citations from policy matches."""
    citations = []
    for citation in evidence.all_citations:
        if citation.startswith("FP-"):
            parts = citation.split(":", 1)
            if len(parts) == 2:
                citations.append({"policy_id": parts[0].strip(), "text": parts[1].strip()})
    return citations


def build_citations_external(evidence: AggregatedEvidence) -> list[dict]:
    """Build external citations from threat intelligence."""
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
