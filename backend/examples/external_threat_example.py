"""Example usage of the External Threat agent."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.external_threat import external_threat_agent
from app.models import CustomerBehavior, OrchestratorState, Transaction, TransactionSignals


async def demo_high_risk_transaction():
    """Demonstrate External Threat agent with a high-risk transaction."""
    print("=" * 70)
    print("EXTERNAL THREAT AGENT - HIGH RISK TRANSACTION")
    print("=" * 70)

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-THREAT-001",
            customer_id="C-THREAT-001",
            amount=5000.0,
            currency="USD",
            country="IR",  # Iran - FATF blacklist
            channel="web_unknown",
            device_id="D-999",
            timestamp=datetime(2025, 1, 15, 3, 0, 0, tzinfo=timezone.utc),
            merchant_id="M-999",  # Merchant on watchlist
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-THREAT-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=10.0,
            is_off_hours=True,
            is_foreign=True,
            is_unknown_device=True,
            channel_risk="high",
            flags=["high_amount_ratio_10.0x", "transaction_off_hours"],
        ),
        "status": "processing",
        "trace": [],
    }

    print("\n[Transaction Details]")
    print(f"  Amount: ${state['transaction'].amount:.2f}")
    print(f"  Country: {state['transaction'].country} (Iran - FATF blacklist)")
    print(f"  Merchant: {state['transaction'].merchant_id} (on watchlist)")
    print(f"  Channel: {state['transaction'].channel}")
    print(f"  Time: {state['transaction'].timestamp}")

    print("\n[Running External Threat Agent...]")
    result = await external_threat_agent(state)

    threat_intel = result["threat_intel"]

    print(f"\n[THREAT LEVEL: {threat_intel.threat_level:.2f}]")
    print(f"\n[Threat Sources Detected: {len(threat_intel.sources)}]")
    for i, source in enumerate(threat_intel.sources, 1):
        print(f"  {i}. {source.source_name}")
        print(f"     Confidence: {source.confidence:.2f}")

    if "trace" in result:
        trace = result["trace"][0]
        print(f"\n[Execution]")
        print(f"  Duration: {trace.duration_ms:.2f}ms")
        print(f"  Status: {trace.status}")

    print("\n" + "=" * 70)


async def demo_clean_transaction():
    """Demonstrate External Threat agent with a clean transaction."""
    print("\n" + "=" * 70)
    print("EXTERNAL THREAT AGENT - CLEAN TRANSACTION")
    print("=" * 70)

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-CLEAN-001",
            customer_id="C-CLEAN-001",
            amount=500.0,
            currency="USD",
            country="US",
            channel="app",
            device_id="D-01",
            timestamp=datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
            merchant_id="M-001",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-CLEAN-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=1.0,
            is_off_hours=False,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="low",
            flags=[],
        ),
        "status": "processing",
        "trace": [],
    }

    print("\n[Transaction Details]")
    print(f"  Amount: ${state['transaction'].amount:.2f}")
    print(f"  Country: {state['transaction'].country} (clean)")
    print(f"  Merchant: {state['transaction'].merchant_id} (clean)")
    print(f"  Channel: {state['transaction'].channel}")

    print("\n[Running External Threat Agent...]")
    result = await external_threat_agent(state)

    threat_intel = result["threat_intel"]

    print(f"\n[THREAT LEVEL: {threat_intel.threat_level:.2f}]")
    if threat_intel.sources:
        print(f"\n[Threat Sources: {len(threat_intel.sources)}]")
        for source in threat_intel.sources:
            print(f"  - {source.source_name}: {source.confidence:.2f}")
    else:
        print("\n[No external threats detected]")

    print("\n" + "=" * 70)


async def demo_medium_risk():
    """Demonstrate External Threat agent with medium-risk country."""
    print("\n" + "=" * 70)
    print("EXTERNAL THREAT AGENT - MEDIUM RISK")
    print("=" * 70)

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-MED-001",
            customer_id="C-MED-001",
            amount=2000.0,
            currency="BRL",
            country="BR",  # Brazil - medium risk
            channel="mobile",
            device_id="D-05",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-MED-001",
            usual_amount_avg=1000.0,
            usual_hours="08:00-22:00",
            usual_countries=["BR"],
            usual_devices=["D-05"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=2.0,
            is_off_hours=False,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="medium",
            flags=["elevated_amount_2.0x"],
        ),
        "status": "processing",
        "trace": [],
    }

    print("\n[Transaction Details]")
    print(f"  Amount: {state['transaction'].amount:.2f} {state['transaction'].currency}")
    print(f"  Country: {state['transaction'].country} (Brazil - elevated fraud rates)")
    print(f"  Channel: {state['transaction'].channel}")

    print("\n[Running External Threat Agent...]")
    result = await external_threat_agent(state)

    threat_intel = result["threat_intel"]

    print(f"\n[THREAT LEVEL: {threat_intel.threat_level:.2f}]")
    if threat_intel.sources:
        print(f"\n[Threat Sources: {len(threat_intel.sources)}]")
        for source in threat_intel.sources:
            print(f"  - {source.source_name}: {source.confidence:.2f}")

    print("\n" + "=" * 70)


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("EXTERNAL THREAT AGENT DEMONSTRATIONS")
    print("=" * 70)
    print("\nNOTE: This agent uses SIMULATED threat feeds for portfolio demo.")
    print("In production, this would query real threat intelligence APIs.")
    print("\nSimulated Threat Feeds:")
    print("  - High-risk countries (FATF blacklist/graylist)")
    print("  - Merchant watchlist (fraud reports)")
    print("  - Known fraud patterns")
    print("\n" + "=" * 70)

    await demo_high_risk_transaction()
    await demo_clean_transaction()
    await demo_medium_risk()

    print("\n[SUMMARY]")
    print("The External Threat agent:")
    print("  ✓ Checks transactions against simulated threat feeds")
    print("  ✓ Uses LLM for nuanced threat interpretation")
    print("  ✓ Falls back to deterministic scoring if LLM fails")
    print("  ✓ Returns ThreatIntelResult with threat_level (0.0-1.0)")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
