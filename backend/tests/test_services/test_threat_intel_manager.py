"""Test script for ThreatIntelManager (full orchestration)."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path for standalone execution
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.models import Transaction, TransactionSignals
from app.services.threat_intel.manager import ThreatIntelManager


async def main():
    """Test threat intel manager with high-risk transaction."""
    manager = ThreatIntelManager()

    # High-risk transaction (blacklist country + high amount + foreign)
    tx = Transaction(
        transaction_id="TEST-HIGH-RISK",
        customer_id="C-001",
        amount=10000,
        currency="USD",
        country="IR",  # Iran - blacklist
        channel="web",
        device_id="D-999",
        timestamp=datetime.now(UTC),
        merchant_id="M-TEST",
    )

    signals = TransactionSignals(
        amount_ratio=10.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["very_high_amount", "blacklist_country"],
    )

    print("Analyzing transaction with all providers (may take 10-15 seconds)...")
    result = await manager.analyze(tx, signals)

    print(f"\n{'='*60}")
    print(f"Threat Level: {result.threat_level}")
    print(f"Sources: {len(result.sources)}")
    print(f"{'='*60}")

    for s in result.sources:
        print(f"  - {s.source_name}: {s.confidence}")

    print(f"\n{'='*60}")

    # Evaluate result
    if result.threat_level >= 0.9:
        print("[OK] High threat level detected (>= 0.9) - EXPECTED for blacklist country!")
    elif result.threat_level >= 0.7:
        print("[WARN] Moderate threat level (0.7-0.9) - may vary based on OSINT results")
    else:
        print(f"[ERROR] Low threat level ({result.threat_level}) - unexpected for IR country")

    if len(result.sources) >= 1:
        print(
            f"[OK] Multiple sources detected ({len(result.sources)}) - providers working!"
        )
    else:
        print("[ERROR] No sources detected - check provider configuration")

    print("\n[OK] Threat intel manager test completed!")


if __name__ == "__main__":
    asyncio.run(main())
