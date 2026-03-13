"""Behavioral Pattern Agent - deterministic behavioral deviation analysis.

This agent analyzes transaction behavior against customer historical patterns
to detect anomalies and calculate a deviation score. It is fully deterministic
(no LLM calls). Delegates core logic to domain service.
"""

from app.domain.models import BehavioralSignals, OrchestratorState
from app.domain.services.behavioral_analysis import analyze_behavioral_signals
from app.utils.logger import get_logger
from app.utils.shared_utils import is_time_in_range, parse_usual_hours
from app.utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("behavioral_pattern")
async def behavioral_pattern_agent(state: OrchestratorState, **kwargs) -> dict:
    """Behavioral Pattern Agent - deterministic behavioral deviation analysis.

    Delegates core scoring logic to domain/services/behavioral_analysis.py.

    Args:
        state: LangGraph orchestrator state containing transaction and customer_behavior

    Returns:
        State update dict with behavioral_signals field
    """
    try:
        transaction = state["transaction"]
        customer_behavior = state["customer_behavior"]

        # Off-hours check (uses time parsing utility — only non-pure part)
        try:
            start_time, end_time = parse_usual_hours(customer_behavior.usual_hours)
            transaction_time = transaction.timestamp.time()
            is_off_hours = not is_time_in_range(transaction_time, start_time, end_time)
        except (ValueError, AttributeError) as e:
            logger.warning("usual_hours_parse_failed", error=str(e))
            is_off_hours = False

        # Delegate to domain service
        behavioral_signals = analyze_behavioral_signals(
            transaction, customer_behavior, is_off_hours
        )

        logger.info(
            "behavioral_pattern_completed",
            deviation_score=behavioral_signals.deviation_score,
            anomalies_count=len(behavioral_signals.anomalies),
            velocity_alert=behavioral_signals.velocity_alert,
        )

        return {"behavioral_signals": behavioral_signals}

    except Exception as e:
        logger.error("behavioral_pattern_error", error=str(e), exc_info=True)

        fallback_signals = BehavioralSignals(
            deviation_score=0.0,
            anomalies=[f"error_in_analysis: {str(e)}"],
            velocity_alert=False,
        )

        return {"behavioral_signals": fallback_signals}
