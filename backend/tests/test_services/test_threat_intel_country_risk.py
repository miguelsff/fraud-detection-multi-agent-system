"""Test script for CountryRiskProvider."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path for standalone execution
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.models import Transaction
from app.services.threat_intel.country_risk import CountryRiskProvider


async def main():
    """Test country risk provider with different country types."""
    provider = CountryRiskProvider()

    # Test blacklist country (Iran)
    tx_iran = Transaction(
        transaction_id="TEST-IR",
        customer_id="C-001",
        amount=100,
        currency="USD",
        country="IR",
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )

    sources = await provider.lookup(tx_iran)
    print(f"Iran (blacklist): {len(sources)} sources")
    for s in sources:
        print(f"  - {s.source_name}: {s.confidence}")

    # Test graylist country (Venezuela)
    tx_venezuela = Transaction(
        transaction_id="TEST-VE",
        customer_id="C-001",
        amount=100,
        currency="USD",
        country="VE",
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )

    sources = await provider.lookup(tx_venezuela)
    print(f"\nVenezuela (graylist): {len(sources)} sources")
    for s in sources:
        print(f"  - {s.source_name}: {s.confidence}")

    # Test elevated risk country (Russia)
    tx_russia = Transaction(
        transaction_id="TEST-RU",
        customer_id="C-001",
        amount=100,
        currency="USD",
        country="RU",
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )

    sources = await provider.lookup(tx_russia)
    print(f"\nRussia (elevated risk): {len(sources)} sources")
    for s in sources:
        print(f"  - {s.source_name}: {s.confidence}")

    # Test safe country (Peru)
    tx_peru = Transaction(
        transaction_id="TEST-PE",
        customer_id="C-001",
        amount=100,
        currency="PEN",
        country="PE",
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )

    sources = await provider.lookup(tx_peru)
    print(f"\nPeru (safe): {len(sources)} sources")

    print("\n[OK] Country risk provider test completed!")


if __name__ == "__main__":
    asyncio.run(main())
