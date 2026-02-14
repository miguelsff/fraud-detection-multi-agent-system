"""Quick test for refactored external_threat agent."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path for standalone execution
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.agents.external_threat import external_threat_agent
from app.models import OrchestratorState, Transaction, TransactionSignals


async def main():
    """Test refactored external threat agent."""
    print("Testing refactored external_threat_agent...")
    print("=" * 60)

    # Create a high-risk transaction (Iran - blacklist country)
    transaction = Transaction(
        transaction_id="TEST-REFACTOR-001",
        customer_id="C-001",
        amount=10000,
        currency="USD",
        country="IR",  # Iran - FATF blacklist
        channel="web",
        device_id="D-UNKNOWN",
        timestamp=datetime.now(UTC),
        merchant_id="M-TEST",
    )

    # Create signals
    signals = TransactionSignals(
        amount_ratio=10.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["very_high_amount", "blacklist_country"],
    )

    # Create orchestrator state
    state: OrchestratorState = {
        "transaction": transaction,
        "transaction_signals": signals,
        "behavior_analysis": None,
        "policy_matches": None,
        "threat_intel": None,
        "evidence": None,
        "debate_result": None,
        "decision": None,
        "explanations": None,
    }

    print(f"\nTransaction: {transaction.transaction_id}")
    print(f"Country: {transaction.country} (Iran - FATF blacklist)")
    print(f"Amount: ${transaction.amount:,.2f}")
    print(f"Signals: {len(signals.flags)} flags")
    print("\nExecuting external_threat_agent...\n")

    # Execute agent
    result = await external_threat_agent(state)

    # Extract result
    threat_intel = result["threat_intel"]

    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Threat Level: {threat_intel.threat_level}")
    print(f"Sources: {len(threat_intel.sources)}")
    print("\nSources detected:")
    for source in threat_intel.sources:
        print(f"  - {source.source_name}: {source.confidence}")

    print("\n" + "=" * 60)

    # Validation
    if threat_intel.threat_level >= 0.9:
        print("[OK] High threat level detected (>= 0.9) - EXPECTED for IR!")
    elif threat_intel.threat_level >= 0.7:
        print("[WARN] Moderate threat (0.7-0.9) - may vary based on OSINT")
    else:
        print(f"[ERROR] Low threat ({threat_intel.threat_level}) - unexpected for IR")

    if len(threat_intel.sources) >= 1:
        print(f"[OK] Sources detected ({len(threat_intel.sources)})")
    else:
        print("[ERROR] No sources detected")

    # Check that providers are being used
    source_names = [s.source_name for s in threat_intel.sources]
    has_fatf = any("fatf" in name.lower() for name in source_names)
    has_osint = any("osint" in name.lower() for name in source_names)

    if has_fatf:
        print("[OK] FATF provider working (country risk detected)")
    else:
        print("[WARN] No FATF sources (unexpected for IR)")

    if has_osint:
        print("[OK] OSINT provider working (web search active)")
    else:
        print("[INFO] No OSINT sources (may be disabled or no matches)")

    print("\n[OK] Refactored agent test completed!")


if __name__ == "__main__":
    asyncio.run(main())
