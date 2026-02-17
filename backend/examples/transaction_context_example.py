"""Example usage of the Transaction Context agent."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.transaction_context import transaction_context_agent
from app.models import CustomerBehavior, OrchestratorState, Transaction


async def main():
    """Demonstrate the Transaction Context agent with a suspicious transaction."""
    # Create a suspicious transaction scenario
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1001",
            customer_id="C-501",
            amount=1800.00,  # 3.6x the usual amount
            currency="PEN",
            country="US",  # Foreign country
            channel="web_unknown",  # High-risk channel
            device_id="D-99",  # Unknown device
            timestamp=datetime(2025, 1, 15, 3, 15, 0, tzinfo=timezone.utc),  # Off-hours
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-501",
            usual_amount_avg=500.00,
            usual_hours="08:00-22:00",
            usual_countries=["PE"],
            usual_devices=["D-01", "D-02"],
        ),
        "status": "processing",
        "trace": [],
    }

    # Run the agent
    result = await transaction_context_agent(state)

    # Display results
    print("=" * 60)
    print("TRANSACTION CONTEXT ANALYSIS")
    print("=" * 60)
    print(f"\nTransaction ID: {state['transaction'].transaction_id}")
    print(f"Customer ID: {state['transaction'].customer_id}")
    print(f"Amount: {state['transaction'].amount} {state['transaction'].currency}")
    print(f"Country: {state['transaction'].country}")
    print(f"Channel: {state['transaction'].channel}")
    print(f"Device: {state['transaction'].device_id}")
    print(f"Timestamp: {state['transaction'].timestamp}")

    print("\n" + "=" * 60)
    print("SIGNALS DETECTED")
    print("=" * 60)
    signals = result["transaction_signals"]
    print(f"\nAmount Ratio: {signals.amount_ratio:.2f}x usual")
    print(f"Off-Hours: {signals.is_off_hours}")
    print(f"Foreign Country: {signals.is_foreign}")
    print(f"Unknown Device: {signals.is_unknown_device}")
    print(f"Channel Risk: {signals.channel_risk}")

    print("\n" + "=" * 60)
    print("FLAGS RAISED")
    print("=" * 60)
    if signals.flags:
        for i, flag in enumerate(signals.flags, 1):
            print(f"{i}. {flag}")
    else:
        print("No flags raised - transaction appears normal")

    print("\n" + "=" * 60)
    print("TRACE INFORMATION")
    print("=" * 60)
    trace_entry = result["trace"][0]
    print(f"\nAgent: {trace_entry.agent_name}")
    print(f"Duration: {trace_entry.duration_ms:.2f}ms")
    print(f"Status: {trace_entry.status}")
    print(f"Output: {trace_entry.output_summary}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
