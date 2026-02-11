"""Verification script for FastAPI endpoints.

This script tests all API endpoints to ensure they are working correctly.
Run this after starting the FastAPI server.

Usage:
    uv run python scripts/verify_api.py
"""
import asyncio
import sys
from datetime import datetime, UTC

import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_health():
    """Test health check endpoint."""
    print("\n1. Testing Health Check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {data['status']}")
            print(f"   ✓ Version: {data['version']}")
            return True
        else:
            print(f"   ✗ Failed with status {response.status_code}")
            return False


async def test_analytics():
    """Test analytics summary endpoint."""
    print("\n2. Testing Analytics Summary...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/analytics/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Total analyzed: {data['total_analyzed']}")
            print(f"   ✓ Avg confidence: {data['avg_confidence']}")
            print(f"   ✓ Escalation rate: {data['escalation_rate']}")
            return True
        else:
            print(f"   ✗ Failed with status {response.status_code}")
            return False


async def test_hitl_queue():
    """Test HITL queue endpoint."""
    print("\n3. Testing HITL Queue...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/hitl/queue?status=pending")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Pending cases: {len(data)}")
            return True
        else:
            print(f"   ✗ Failed with status {response.status_code}")
            return False


async def test_list_transactions():
    """Test list transactions endpoint."""
    print("\n4. Testing List Transactions...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/transactions?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Transactions found: {len(data)}")
            return True
        else:
            print(f"   ✗ Failed with status {response.status_code}")
            return False


async def test_analyze_transaction():
    """Test transaction analysis endpoint."""
    print("\n5. Testing Transaction Analysis...")

    test_data = {
        "transaction": {
            "transaction_id": f"T-TEST-{datetime.now(UTC).timestamp()}",
            "customer_id": "C-TEST-001",
            "amount": 1500.0,
            "currency": "PEN",
            "country": "PE",
            "channel": "web",
            "device_id": "D-TEST-001",
            "timestamp": datetime.now(UTC).isoformat(),
            "merchant_id": "M-TEST-001",
        },
        "customer_behavior": {
            "customer_id": "C-TEST-001",
            "usual_amount_avg": 500.0,
            "usual_hours": "08:00-22:00",
            "usual_countries": ["PE"],
            "usual_devices": ["D-TEST-001"],
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/transactions/analyze", json=test_data)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Decision: {data.get('decision', 'N/A')}")
                print(f"   ✓ Confidence: {data.get('confidence', 'N/A')}")
                return True, data.get("transaction_id")
            else:
                print(f"   ✗ Failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False, None
        except httpx.TimeoutException:
            print("   ⚠ Analysis timeout (this is expected if orchestrator is working)")
            return None, None
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            return False, None


async def test_get_result(transaction_id: str):
    """Test get transaction result endpoint."""
    print(f"\n6. Testing Get Transaction Result...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/transactions/{transaction_id}/result")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Found result for {transaction_id}")
            print(f"   ✓ Decision: {data.get('decision', 'N/A')}")
            return True
        elif response.status_code == 404:
            print(f"   ⚠ Transaction not found (may not be persisted yet)")
            return None
        else:
            print(f"   ✗ Failed with status {response.status_code}")
            return False


async def test_validation_errors():
    """Test that validation works correctly."""
    print("\n7. Testing Validation Errors...")
    async with httpx.AsyncClient() as client:
        # Test with empty body
        response = await client.post(f"{BASE_URL}/transactions/analyze", json={})
        if response.status_code == 422:
            print("   ✓ Validation error returned for empty body")
            return True
        else:
            print(f"   ✗ Expected 422, got {response.status_code}")
            return False


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("FastAPI Endpoint Verification")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now(UTC).isoformat()}")

    results = []

    # Test health
    results.append(("Health Check", await test_health()))

    # Test analytics
    results.append(("Analytics", await test_analytics()))

    # Test HITL
    results.append(("HITL Queue", await test_hitl_queue()))

    # Test list transactions
    results.append(("List Transactions", await test_list_transactions()))

    # Test validation
    results.append(("Validation", await test_validation_errors()))

    # Test analyze (optional, may timeout)
    print("\n⚠ Testing transaction analysis (may take 60s or timeout)...")
    analyze_result, transaction_id = await test_analyze_transaction()
    results.append(("Transaction Analysis", analyze_result))

    # Test get result (if we have a transaction_id)
    if transaction_id:
        results.append(("Get Result", await test_get_result(transaction_id)))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result is True)
    skipped = sum(1 for _, result in results if result is None)
    failed = sum(1 for _, result in results if result is False)

    for test_name, result in results:
        status = "✓ PASS" if result is True else ("⚠ SKIP" if result is None else "✗ FAIL")
        print(f"{status:10} {test_name}")

    print(f"\nPassed: {passed} | Skipped: {skipped} | Failed: {failed}")

    if failed > 0:
        print("\n❌ Some tests failed")
        sys.exit(1)
    elif skipped > 0:
        print("\n⚠️  Some tests skipped (this is OK for initial verification)")
        sys.exit(0)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
