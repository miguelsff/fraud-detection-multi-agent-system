"""Evidence Aggregation Agent - consolidates signals from all collection agents.

Implements Phase 2 (Consolidation). Delegates core scoring logic to domain services.
"""

from app.domain.models import AggregatedEvidence, OrchestratorState
from app.domain.services.risk_scoring import (
    aggregate_citations,
    aggregate_signals,
    calculate_composite_score,
    determine_risk_category,
)
from app.utils.logger import get_logger
from app.utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("evidence_aggregation")
async def evidence_aggregation_agent(state: OrchestratorState, **kwargs) -> dict:
    """Evidence Aggregation agent - consolidates all collection agent outputs.

    Delegates to domain/services/risk_scoring.py for pure scoring logic.

    Args:
        state: Orchestrator state with outputs from Phase 1 agents

    Returns:
        Dict with evidence field containing AggregatedEvidence
    """
    try:
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")
        policy_matches = state.get("policy_matches")
        threat_intel = state.get("threat_intel")

        composite_score = calculate_composite_score(
            transaction_signals,
            behavioral_signals,
            policy_matches,
            threat_intel,
        )

        all_signals = aggregate_signals(
            transaction_signals,
            behavioral_signals,
            policy_matches,
            threat_intel,
        )

        all_citations = aggregate_citations(
            policy_matches,
            threat_intel,
        )

        risk_category = determine_risk_category(composite_score)

        evidence = AggregatedEvidence(
            composite_risk_score=composite_score,
            all_signals=all_signals,
            all_citations=all_citations,
            risk_category=risk_category,
        )

        logger.info(
            "evidence_aggregation_completed",
            composite_score=composite_score,
            risk_category=risk_category,
            signals_count=len(all_signals),
            citations_count=len(all_citations),
        )

        return {"evidence": evidence}

    except Exception as e:
        logger.error("evidence_aggregation_error", error=str(e), exc_info=True)
        return {
            "evidence": AggregatedEvidence(
                composite_risk_score=0.0,
                all_signals=[],
                all_citations=[],
                risk_category="low",
            )
        }
