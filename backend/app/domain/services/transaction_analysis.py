"""Transaction analysis domain service — pure deterministic signal computation.

Extracted from agents/transaction_context.py. No I/O, no infrastructure imports.
"""

from ..constants import AMOUNT_THRESHOLDS
from ..models import CustomerBehavior, Transaction, TransactionSignals


def analyze_transaction_signals(
    transaction: Transaction,
    customer_behavior: CustomerBehavior,
) -> TransactionSignals:
    """Compute contextual signals by comparing transaction against customer history.

    This is fully deterministic (no LLM calls).

    Args:
        transaction: The financial transaction to analyze.
        customer_behavior: Historical behavior profile for the customer.

    Returns:
        TransactionSignals with amount_ratio, foreign/device flags, channel_risk, and flags list.
    """
    # 1. Amount ratio
    if customer_behavior.usual_amount_avg > 0:
        amount_ratio = transaction.amount / customer_behavior.usual_amount_avg
    else:
        amount_ratio = 0.0

    # 2. Foreign country check
    is_foreign = transaction.country not in customer_behavior.usual_countries

    # 3. Unknown device check
    is_unknown_device = transaction.device_id not in customer_behavior.usual_devices

    # 4. Channel risk mapping
    channel_lower = transaction.channel.lower()
    if channel_lower in ("web_unknown", "web-unknown"):
        channel_risk = "high"
    elif channel_lower == "mobile":
        channel_risk = "medium"
    elif channel_lower in ("app", "web"):
        channel_risk = "low"
    else:
        channel_risk = "medium"

    # 5. Build flags list
    flags: list[str] = []

    if amount_ratio > AMOUNT_THRESHOLDS.high_ratio:
        flags.append(f"high_amount_ratio_{amount_ratio:.1f}x")
    elif amount_ratio > AMOUNT_THRESHOLDS.elevated_ratio:
        flags.append(f"elevated_amount_{amount_ratio:.1f}x")

    if is_foreign:
        flags.append(f"foreign_country_{transaction.country}")

    if is_unknown_device:
        flags.append(f"unknown_device_{transaction.device_id}")

    if channel_risk == "high":
        flags.append("high_risk_channel")

    return TransactionSignals(
        amount_ratio=amount_ratio,
        is_foreign=is_foreign,
        is_unknown_device=is_unknown_device,
        channel_risk=channel_risk,
        flags=flags,
    )
