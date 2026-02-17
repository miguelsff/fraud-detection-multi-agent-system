"""Simple seed script that uses HTTP requests to populate the database."""
import json
import requests
import time

def main():
    # Load synthetic data
    with open("data/synthetic_data.json", "r") as f:
        data = json.load(f)

    base_url = "http://localhost:8000/api/v1"

    print(f"Seeding {len(data)} transactions...")

    for i, item in enumerate(data, 1):
        transaction = item["transaction"]
        customer_behavior = item["customer_behavior"]

        print(f"\n[{i}/{len(data)}] Analyzing {transaction['transaction_id']}...")
        print(f"  Expected: {item['expected_outcome']}")
        print(f"  Reason: {item['reason']}")

        # Submit for analysis
        try:
            response = requests.post(
                f"{base_url}/transactions/analyze",
                json={
                    "transaction": transaction,
                    "customer_behavior": customer_behavior
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                print(f"  OK Decision: {result['decision']} (confidence: {result['confidence']:.2f})")
            else:
                print(f"  ERROR: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"  ERROR Exception: {str(e)}")

        # Brief pause to avoid overwhelming the system
        if i < len(data):
            time.sleep(1)

    print("\nSeeding complete!")

    # Get analytics
    try:
        response = requests.get(f"{base_url}/analytics/summary")
        if response.status_code == 200:
            analytics = response.json()
            print("\nAnalytics Summary:")
            print(f"  Total analyzed: {analytics['total_analyzed']}")
            print(f"  Avg confidence: {analytics['avg_confidence']:.2%}")
            print(f"  Escalation rate: {analytics['escalation_rate']:.2%}")
            print(f"  Decisions breakdown:")
            for decision, count in analytics['decisions_breakdown'].items():
                print(f"    - {decision}: {count}")
    except Exception as e:
        print(f"\nFailed to get analytics: {e}")

if __name__ == "__main__":
    main()
