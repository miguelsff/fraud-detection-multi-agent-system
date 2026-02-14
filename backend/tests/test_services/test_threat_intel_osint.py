"""Test script for OSINTSearchProvider."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path for standalone execution
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.models import Transaction, TransactionSignals
from app.services.threat_intel.osint_search import OSINTSearchProvider


async def main():
    """Test OSINT provider with a suspicious transaction."""
    provider = OSINTSearchProvider(max_results=3)

    tx = Transaction(
        transaction_id="TEST-OSINT",
        customer_id="C-001",
        amount=5000,
        currency="USD",
        country="NG",  # Nigeria (high fraud)
        channel="web",
        device_id="D-999",
        timestamp=datetime.now(UTC),
        merchant_id="M-SUSPICIOUS",
    )

    signals = TransactionSignals(
        amount_ratio=5.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["high_amount", "foreign"],
    )

    print("Executing OSINT search (this may take 10-15 seconds)...")
    sources = await provider.lookup(tx, signals)

    print(f"\nOSINT sources found: {len(sources)}")
    for s in sources:
        print(f"  - {s.source_name}: {s.confidence}")

    if len(sources) > 0:
        print("\n[OK] OSINT provider test completed successfully!")
    else:
        print(
            "\n[WARN] No OSINT sources found (this is normal if web search is disabled or queries didn't match)"
        )


if __name__ == "__main__":
    asyncio.run(main())
