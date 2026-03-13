"""Behavioral analysis domain service — pure deterministic deviation scoring.

Extracted from agents/behavioral_pattern.py. No I/O, no infrastructure imports.
"""

from ..constants import AMOUNT_THRESHOLDS, BEHAVIORAL_WEIGHTS
from ..models import BehavioralSignals, CustomerBehavior, Transaction


def calculate_amount_zscore(amount: float, usual_avg: float) -> float:
    """Calculate normalized deviation score for transaction amount.

    Uses a piecewise linear function that maps amount ratios to deviation scores:
    - ratio <= 1.0 -> score 0.0-0.1
    - ratio 1.0-2.0 -> score 0.1-0.3
    - ratio 2.0-3.0 -> score 0.3-0.5
    - ratio 3.0-5.0 -> score 0.5-0.7
    - ratio >= 5.0 -> score 0.7-1.0

    Returns:
        Normalized deviation score between 0.0 and 1.0
    """
    if usual_avg <= 0:
        return 0.0

    ratio = amount / usual_avg

    if ratio <= 1.0:
        score = max(0.0, ratio * 0.1)
    elif ratio <= 2.0:
        score = 0.1 + (ratio - 1.0) * 0.2
    elif ratio <= 3.0:
        score = 0.3 + (ratio - 2.0) * 0.2
    elif ratio <= 5.0:
        score = 0.5 + (ratio - 3.0) * 0.1
    else:
        score = 0.7 + min(0.3, (ratio - 5.0) * 0.03)

    return min(1.0, score)


def analyze_behavioral_signals(
    transaction: Transaction,
    customer_behavior: CustomerBehavior,
    is_off_hours: bool,
) -> BehavioralSignals:
    """Compute behavioral deviation signals from customer history.

    This is fully deterministic (no LLM calls).

    Args:
        transaction: The financial transaction to analyze.
        customer_behavior: Historical behavior profile.
        is_off_hours: Whether the transaction is outside usual hours
                      (caller must compute this from customer_behavior.usual_hours).

    Returns:
        BehavioralSignals with deviation_score, anomalies, and velocity_alert.
    """
    # 1. Base deviation score from amount
    base_score = calculate_amount_zscore(
        transaction.amount,
        customer_behavior.usual_amount_avg,
    )

    # 2. Behavioral factors
    is_foreign = transaction.country not in customer_behavior.usual_countries
    is_new_device = transaction.device_id not in customer_behavior.usual_devices

    if customer_behavior.usual_amount_avg > 0:
        amount_ratio = transaction.amount / customer_behavior.usual_amount_avg
    else:
        amount_ratio = 0.0

    # 3. Final deviation score with behavioral factors
    deviation_score = base_score

    if is_off_hours:
        deviation_score += BEHAVIORAL_WEIGHTS.off_hours

    if is_foreign:
        deviation_score += BEHAVIORAL_WEIGHTS.foreign_country

    if is_new_device:
        deviation_score += BEHAVIORAL_WEIGHTS.new_device

    deviation_score = round(max(0.0, min(1.0, deviation_score)), 2)

    # 4. Anomalies list
    anomalies: list[str] = []

    if amount_ratio > AMOUNT_THRESHOLDS.high_ratio:
        anomalies.append("amount_3x_above_average")

    if is_off_hours:
        anomalies.append("off_hours_transaction")

    if is_foreign:
        anomalies.append(f"foreign_country_{transaction.country}")

    if is_new_device:
        anomalies.append(f"new_device_{transaction.device_id}")

    if amount_ratio > AMOUNT_THRESHOLDS.elevated_ratio and is_new_device:
        anomalies.append("high_amount_new_device")

    # 5. Velocity alert
    velocity_alert = amount_ratio > AMOUNT_THRESHOLDS.velocity_ratio

    return BehavioralSignals(
        deviation_score=deviation_score,
        anomalies=anomalies,
        velocity_alert=velocity_alert,
    )
