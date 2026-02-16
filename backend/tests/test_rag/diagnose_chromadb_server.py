"""Test ChromaDB HTTP Server - Diagnostic script.

This script tests all ChromaDB API endpoints to verify the server is working correctly.

Usage:
    python test_chromadb_server.py
"""

import json
import sys
import urllib.request
import urllib.error


def test_endpoint(name: str, url: str, expected_status: int = 200) -> bool:
    """Test a single endpoint."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ChromaDB-Tester'})
        response = urllib.request.urlopen(req, timeout=5)

        status_code = response.status
        status_icon = "[OK]" if status_code == expected_status else "[FAIL]"
        print(f"{status_icon} {name}")
        print(f"   URL: {url}")
        print(f"   Status: {status_code}")

        if status_code == 200:
            try:
                data = json.loads(response.read().decode('utf-8'))
                # Pretty print first 500 chars
                json_str = json.dumps(data, indent=2)
                preview = json_str[:500] + "..." if len(json_str) > 500 else json_str
                print(f"   Response: {preview}")
            except Exception:
                print(f"   Response: (binary or non-JSON data)")
        else:
            print(f"   Error: Status {status_code}")

        print()
        return status_code == expected_status

    except urllib.error.URLError as e:
        print(f"[FAIL] {name}")
        print(f"   URL: {url}")
        if hasattr(e, 'reason'):
            print(f"   Error: Connection failed - {e.reason}")
        elif hasattr(e, 'code'):
            print(f"   Error: HTTP {e.code}")
        else:
            print(f"   Error: {str(e)}")
        print()
        return False
    except Exception as e:
        print(f"[FAIL] {name}")
        print(f"   URL: {url}")
        print(f"   Error: {str(e)}")
        print()
        return False


def main():
    """Main test function."""
    print("\n" + "=" * 80)
    print("ChromaDB Server Diagnostic Test")
    print("=" * 80)
    print("\nTesting ChromaDB server at http://localhost:8888")
    print("Make sure you've started the server with: python view_db.py\n")
    print("-" * 80 + "\n")

    base_url = "http://localhost:8888"
    tenant = "default_tenant"
    database = "default_database"

    tests = [
        ("Heartbeat (API v2)", f"{base_url}/api/v2/heartbeat"),
        ("List Tenants", f"{base_url}/api/v2/tenants"),
        ("List Collections (Full Path)",
         f"{base_url}/api/v2/tenants/{tenant}/databases/{database}/collections"),
        ("Get fraud_policies Collection",
         f"{base_url}/api/v2/tenants/{tenant}/databases/{database}/collections/fraud_policies"),
        ("Count Documents in fraud_policies",
         f"{base_url}/api/v2/tenants/{tenant}/databases/{database}/collections/fraud_policies/count"),
    ]

    results = []
    for name, url in tests:
        result = test_endpoint(name, url)
        results.append((name, result))

    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        icon = "[OK]" if result else "[FAIL]"
        print(f"{icon} {name}")

    print("-" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    if passed == total:
        print("\n[OK] All tests passed! ChromaDB server is working correctly.")
        print("\nUse these settings in ChromaDB Admin UI:")
        print("   - Connection string: http://localhost:8888")
        print("   - Tenant: default_tenant")
        print("   - Database: default_database")
        print("   - Authentication: No Auth")
        print("\n[WARNING] If ChromaDB Admin UI still shows 404, it may be incompatible")
        print("   with ChromaDB API v2. Try using ChromaDB Admin UI v0.8.0+")
    else:
        print(f"\n[ERROR] {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("   1. Make sure ChromaDB server is running: python view_db.py")
        print("   2. Check that port 8888 is not blocked by firewall")
        print("   3. Verify database exists: ls data/chroma/")
        sys.exit(1)


if __name__ == "__main__":
    main()
