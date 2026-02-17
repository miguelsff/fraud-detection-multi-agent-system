"""Transaction Context Agent - deterministic analysis of transaction signals."""

from ..models import OrchestratorState, TransactionSignals
from ..utils.timing import timed_agent


@timed_agent("transaction_context")
async def transaction_context_agent(state: OrchestratorState) -> dict:
    """Analyze transaction in the context of customer behavior.

    This is a deterministic agent (no LLM calls) that computes contextual signals
    by comparing the current transaction against the customer's historical behavior.

    Args:
        state: LangGraph orchestrator state containing transaction and customer_behavior

    Returns:
        State update dict with transaction_signals field
    """
    try:
        transaction = state["transaction"]
        customer_behavior = state["customer_behavior"]

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
        if channel_lower == "web_unknown" or channel_lower == "web-unknown":
            channel_risk = "high"
        elif channel_lower == "mobile":
            channel_risk = "medium"
        elif channel_lower in ("app", "web"):
            channel_risk = "low"
        else:
            channel_risk = "medium"  # Default for unknown channels

        # 5. Build flags list
        flags = []

        if amount_ratio > 3.0:
            flags.append(f"high_amount_ratio_{amount_ratio:.1f}x")
        elif amount_ratio > 2.0:
            flags.append(f"elevated_amount_{amount_ratio:.1f}x")

        if is_foreign:
            flags.append(f"foreign_country_{transaction.country}")

        if is_unknown_device:
            flags.append(f"unknown_device_{transaction.device_id}")

        if channel_risk == "high":
            flags.append("high_risk_channel")

        # Build the signals object
        signals = TransactionSignals(
            amount_ratio=amount_ratio,
            is_foreign=is_foreign,
            is_unknown_device=is_unknown_device,
            channel_risk=channel_risk,
            flags=flags,
        )

        return {"transaction_signals": signals}

    except Exception as e:
        # Fallback to empty/safe signals if anything fails
        fallback_signals = TransactionSignals(
            amount_ratio=0.0,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="medium",
            flags=[f"error_in_analysis: {str(e)}"],
        )
        return {"transaction_signals": fallback_signals}
