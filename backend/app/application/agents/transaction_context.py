"""Transaction Context Agent - deterministic analysis of transaction signals."""

from app.domain.models import OrchestratorState, TransactionSignals
from app.domain.services.transaction_analysis import analyze_transaction_signals
from app.utils.timing import timed_agent


@timed_agent("transaction_context")
async def transaction_context_agent(state: OrchestratorState, **kwargs) -> dict:
    """Analyze transaction in the context of customer behavior.

    This is a deterministic agent (no LLM calls) that computes contextual signals
    by comparing the current transaction against the customer's historical behavior.
    Delegates to domain service for pure business logic.

    Args:
        state: LangGraph orchestrator state containing transaction and customer_behavior

    Returns:
        State update dict with transaction_signals field
    """
    try:
        transaction = state["transaction"]
        customer_behavior = state["customer_behavior"]

        signals = analyze_transaction_signals(transaction, customer_behavior)

        return {"transaction_signals": signals}

    except Exception as e:
        fallback_signals = TransactionSignals(
            amount_ratio=0.0,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="medium",
            flags=[f"error_in_analysis: {str(e)}"],
        )
        return {"transaction_signals": fallback_signals}
