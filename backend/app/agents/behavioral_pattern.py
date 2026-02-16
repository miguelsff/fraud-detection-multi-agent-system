"""Behavioral Pattern Agent - deterministic behavioral deviation analysis.

This agent analyzes transaction behavior against customer historical patterns
to detect anomalies and calculate a deviation score. It is fully deterministic
(no LLM calls) and uses statistical analysis of behavioral signals.

Outputs:
- deviation_score: Normalized behavioral deviation (0.0-1.0)
- anomalies: List of detected behavioral anomalies
- velocity_alert: Flag for high-velocity transactions
"""

from ..models import BehavioralSignals, OrchestratorState
from ..utils.logger import get_logger
from ..utils.timing import timed_agent
from .constants import AMOUNT_THRESHOLDS, BEHAVIORAL_WEIGHTS
from .shared_utils import is_time_in_range, parse_usual_hours

logger = get_logger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def calculate_amount_zscore(amount: float, usual_avg: float) -> float:
    """Calculate normalized deviation score for transaction amount.

    Uses a piecewise linear function that maps amount ratios to deviation scores:
    - ratio <= 1.0 → score 0.0-0.1 (below or equal to average = minimal deviation)
    - ratio 1.0-2.0 → score 0.1-0.3 (slightly elevated)
    - ratio 2.0-3.0 → score 0.3-0.5 (moderately elevated)
    - ratio 3.0-5.0 → score 0.5-0.7 (high deviation)
    - ratio >= 5.0 → score 0.7-1.0 (very high deviation)

    Args:
        amount: Transaction amount
        usual_avg: Customer's usual average amount

    Returns:
        Normalized deviation score between 0.0 and 1.0
    """
    if usual_avg <= 0:
        return 0.0

    # Calculate ratio
    ratio = amount / usual_avg

    # Piecewise linear mapping for intuitive interpretation
    if ratio <= 1.0:
        # Below/equal average: minimal deviation (0.0-0.1)
        # ratio 0.5 → 0.05, ratio 1.0 → 0.1
        score = max(0.0, ratio * 0.1)
    elif ratio <= 2.0:
        # 1x-2x average: slightly elevated (0.1-0.3)
        score = 0.1 + (ratio - 1.0) * 0.2
    elif ratio <= 3.0:
        # 2x-3x average: moderately elevated (0.3-0.5)
        score = 0.3 + (ratio - 2.0) * 0.2
    elif ratio <= 5.0:
        # 3x-5x average: high deviation (0.5-0.7)
        score = 0.5 + (ratio - 3.0) * 0.1
    else:
        # >5x average: very high deviation (0.7-1.0)
        # Asymptotic approach to 1.0
        score = 0.7 + min(0.3, (ratio - 5.0) * 0.03)

    return min(1.0, score)


# ============================================================================
# MAIN AGENT FUNCTION
# ============================================================================


@timed_agent("behavioral_pattern")
async def behavioral_pattern_agent(state: OrchestratorState) -> dict:
    """Behavioral Pattern Agent - deterministic behavioral deviation analysis.

    Analyzes transaction behavior against customer historical patterns to
    detect anomalies. This agent is fully deterministic (no LLM calls).

    Args:
        state: LangGraph orchestrator state containing transaction and customer_behavior

    Returns:
        State update dict with behavioral_signals field containing:
        - deviation_score: float (0.0-1.0) - normalized behavioral deviation
        - anomalies: list[str] - detected behavioral anomalies
        - velocity_alert: bool - high-velocity transaction flag

    Deviation Score Calculation:
        1. Base score from amount z-score normalization
        2. Add BEHAVIORAL_WEIGHTS.off_hours (+0.2) if outside usual hours
        3. Add BEHAVIORAL_WEIGHTS.foreign_country (+0.3) if unusual country
        4. Add BEHAVIORAL_WEIGHTS.new_device (+0.2) if unknown device
        5. Clamp final result to [0.0, 1.0]

    Note:
        - Never crashes - returns safe fallback on any error
        - Logs all calculations for auditability
    """
    try:
        transaction = state["transaction"]
        customer_behavior = state["customer_behavior"]

        # ====================================================================
        # 1. CALCULATE BASE DEVIATION SCORE FROM AMOUNT Z-SCORE
        # ====================================================================
        base_score = calculate_amount_zscore(
            transaction.amount,
            customer_behavior.usual_amount_avg,
        )
        logger.debug(
            "amount_zscore_calculated",
            amount=transaction.amount,
            usual_avg=customer_behavior.usual_amount_avg,
            base_score=base_score,
        )

        # ====================================================================
        # 2. CHECK BEHAVIORAL FACTORS
        # ====================================================================

        # 2a. Off-hours check
        try:
            start_time, end_time = parse_usual_hours(customer_behavior.usual_hours)
            transaction_time = transaction.timestamp.time()
            is_off_hours = not is_time_in_range(transaction_time, start_time, end_time)
        except (ValueError, AttributeError) as e:
            logger.warning("usual_hours_parse_failed", error=str(e))
            is_off_hours = False

        # 2b. Foreign country check
        is_foreign = transaction.country not in customer_behavior.usual_countries

        # 2c. New device check
        is_new_device = transaction.device_id not in customer_behavior.usual_devices

        # 2d. Calculate amount ratio for threshold checks
        if customer_behavior.usual_amount_avg > 0:
            amount_ratio = transaction.amount / customer_behavior.usual_amount_avg
        else:
            amount_ratio = 0.0

        # ====================================================================
        # 3. CALCULATE FINAL DEVIATION SCORE WITH BEHAVIORAL FACTORS
        # ====================================================================
        deviation_score = base_score

        if is_off_hours:
            deviation_score += BEHAVIORAL_WEIGHTS.off_hours
            logger.debug("deviation_factor_added", factor="off_hours", value=BEHAVIORAL_WEIGHTS.off_hours)

        if is_foreign:
            deviation_score += BEHAVIORAL_WEIGHTS.foreign_country
            logger.debug("deviation_factor_added", factor="foreign_country", value=BEHAVIORAL_WEIGHTS.foreign_country)

        if is_new_device:
            deviation_score += BEHAVIORAL_WEIGHTS.new_device
            logger.debug("deviation_factor_added", factor="new_device", value=BEHAVIORAL_WEIGHTS.new_device)

        # Clamp to [0.0, 1.0] and round to avoid floating-point precision issues
        deviation_score = round(max(0.0, min(1.0, deviation_score)), 2)

        # ====================================================================
        # 4. BUILD ANOMALIES LIST
        # ====================================================================
        anomalies = []

        # 4a. High amount (3x above average)
        if amount_ratio > AMOUNT_THRESHOLDS.high_ratio:
            anomalies.append("amount_3x_above_average")

        # 4b. Off-hours transaction
        if is_off_hours:
            anomalies.append("off_hours_transaction")

        # 4c. Foreign country
        if is_foreign:
            anomalies.append(f"foreign_country_{transaction.country}")

        # 4d. New device
        if is_new_device:
            anomalies.append(f"new_device_{transaction.device_id}")

        # 4e. High amount + new device combo (elevated risk)
        if amount_ratio > AMOUNT_THRESHOLDS.elevated_ratio and is_new_device:
            anomalies.append("high_amount_new_device")

        # ====================================================================
        # 5. VELOCITY ALERT CHECK
        # ====================================================================
        # In a real system, this would compare against recent transaction history
        # For now, we use a simple threshold: amount > 5x usual average
        velocity_alert = amount_ratio > AMOUNT_THRESHOLDS.velocity_ratio

        # ====================================================================
        # 6. BUILD BEHAVIORAL SIGNALS OBJECT
        # ====================================================================
        behavioral_signals = BehavioralSignals(
            deviation_score=deviation_score,
            anomalies=anomalies,
            velocity_alert=velocity_alert,
        )

        logger.info(
            "behavioral_pattern_completed",
            deviation_score=deviation_score,
            anomalies_count=len(anomalies),
            velocity_alert=velocity_alert,
        )

        return {"behavioral_signals": behavioral_signals}

    except Exception as e:
        logger.error("behavioral_pattern_error", error=str(e), exc_info=True)

        # Fallback to safe default signals
        fallback_signals = BehavioralSignals(
            deviation_score=0.0,
            anomalies=[f"error_in_analysis: {str(e)}"],
            velocity_alert=False,
        )

        return {"behavioral_signals": fallback_signals}
