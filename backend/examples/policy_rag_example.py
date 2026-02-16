"""Example usage of the Policy RAG agent."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.policy_rag import policy_rag_agent
from app.models import (
    BehavioralSignals,
    CustomerBehavior,
    OrchestratorState,
    Transaction,
    TransactionSignals,
)


async def main():
    """Demonstrate the Policy RAG agent with a high-risk transaction."""
    # Create a high-risk transaction scenario
    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-1001",
            customer_id="C-501",
            amount=1800.00,  # 3.6x the usual amount
            currency="PEN",
            country="US",  # Foreign country
            channel="web_unknown",  # High-risk channel
            device_id="D-999",  # Unknown device
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
        "transaction_signals": TransactionSignals(
            amount_ratio=3.6,
            is_off_hours=True,
            is_foreign=True,
            is_unknown_device=True,
            channel_risk="high",
            flags=[
                "high_amount_ratio_3.6x",
                "transaction_off_hours",
                "foreign_country_US",
                "unknown_device_D-999",
                "high_risk_channel",
            ],
        ),
        "behavioral_signals": BehavioralSignals(
            deviation_score=0.92,
            anomalies=["amount_spike", "unusual_hour", "foreign_location"],
            velocity_alert=False,
        ),
        "status": "processing",
        "trace": [],
    }

    # Run the agent
    print("=" * 70)
    print("POLICY RAG AGENT DEMONSTRATION")
    print("=" * 70)
    print("\n[1] Transaction Details:")
    print(f"    ID: {state['transaction'].transaction_id}")
    print(f"    Customer: {state['transaction'].customer_id}")
    print(f"    Amount: {state['transaction'].amount} {state['transaction'].currency}")
    print(f"    Country: {state['transaction'].country}")
    print(f"    Channel: {state['transaction'].channel}")
    print(f"    Device: {state['transaction'].device_id}")
    print(f"    Timestamp: {state['transaction'].timestamp}")

    print("\n[2] Detected Signals:")
    if state.get("transaction_signals"):
        ts = state["transaction_signals"]
        print(f"    Amount Ratio: {ts.amount_ratio:.2f}x")
        print(f"    Off-Hours: {ts.is_off_hours}")
        print(f"    Foreign: {ts.is_foreign}")
        print(f"    Unknown Device: {ts.is_unknown_device}")
        print(f"    Channel Risk: {ts.channel_risk}")
        print(f"    Flags: {', '.join(ts.flags)}")

    if state.get("behavioral_signals"):
        bs = state["behavioral_signals"]
        print(f"\n    Behavioral Deviation: {bs.deviation_score:.2f}")
        print(f"    Anomalies: {', '.join(bs.anomalies)}")

    print("\n[3] Running Policy RAG Agent...")
    print("    (This will query ChromaDB and call the LLM)")

    result = await policy_rag_agent(state)

    print("\n" + "=" * 70)
    print("POLICY MATCHES FOUND")
    print("=" * 70)

    policy_matches = result["policy_matches"]

    if policy_matches.matches:
        print(f"\nFound {len(policy_matches.matches)} relevant policies:\n")
        for i, match in enumerate(policy_matches.matches, 1):
            print(f"{i}. {match.policy_id} (relevance: {match.relevance_score:.2f})")
            print(f"   {match.description}")
            print()
    else:
        print("\nNo policy matches found (score >= 0.5)")

    print("=" * 70)
    print("METADATA")
    print("=" * 70)
    print(f"\nChromaDB chunks used: {len(policy_matches.chunk_ids)}")
    if policy_matches.chunk_ids:
        print(f"Chunk IDs: {', '.join(policy_matches.chunk_ids[:3])}")

    if "trace" in result:
        trace_entry = result["trace"][0]
        print(f"\nAgent: {trace_entry.agent_name}")
        print(f"Duration: {trace_entry.duration_ms:.2f}ms")
        print(f"Status: {trace_entry.status}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\nNOTE: This example requires:")
    print("  1. Policies ingested into ChromaDB (run: python -m app.rag.ingest)")
    print("  2. Ollama running with qwen3:30b model")
    print()
    asyncio.run(main())
