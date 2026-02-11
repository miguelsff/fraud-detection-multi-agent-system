"""Example usage of the Evidence Aggregation agent."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.evidence_aggregator import evidence_aggregation_agent
from app.models import (
    BehavioralSignals,
    CustomerBehavior,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    ThreatIntelResult,
    ThreatSource,
    Transaction,
    TransactionSignals,
)


async def demo_high_risk_aggregation():
    """Demonstrate Evidence Aggregation with high-risk inputs from all agents."""
    print("=" * 70)
    print("EVIDENCE AGGREGATION - HIGH RISK TRANSACTION")
    print("=" * 70)

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-AGG-001",
            customer_id="C-AGG-001",
            amount=5000.0,
            currency="USD",
            country="IR",
            channel="web_unknown",
            device_id="D-999",
            timestamp=datetime(2025, 1, 15, 3, 0, 0, tzinfo=timezone.utc),
            merchant_id="M-999",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-AGG-001",
            usual_amount_avg=500.0,
            usual_hours="08:00-22:00",
            usual_countries=["US"],
            usual_devices=["D-01"],
        ),
        # Phase 1 Agent Outputs
        "transaction_signals": TransactionSignals(
            amount_ratio=10.0,
            is_off_hours=True,
            is_foreign=True,
            is_unknown_device=True,
            channel_risk="high",
            flags=[
                "high_amount_ratio_10.0x",
                "transaction_off_hours",
                "foreign_country_IR",
                "unknown_device_D-999",
                "high_risk_channel",
            ],
        ),
        "behavioral_signals": BehavioralSignals(
            deviation_score=0.92,
            anomalies=["amount_spike", "unusual_hour", "foreign_location"],
            velocity_alert=False,
        ),
        "policy_matches": PolicyMatchResult(
            matches=[
                PolicyMatch(
                    policy_id="FP-01",
                    description="Transacción con monto 10x superior al promedio",
                    relevance_score=0.95,
                ),
                PolicyMatch(
                    policy_id="FP-02",
                    description="Transacción desde país de alto riesgo (Irán)",
                    relevance_score=0.98,
                ),
                PolicyMatch(
                    policy_id="FP-03",
                    description="Dispositivo no reconocido en transacción de alto monto",
                    relevance_score=0.90,
                ),
                PolicyMatch(
                    policy_id="FP-06",
                    description="Combinación de 5 factores de riesgo detectados",
                    relevance_score=0.99,
                ),
            ],
            chunk_ids=["fp-01-section-0", "fp-02-section-0", "fp-03-section-0", "fp-06-section-0"],
        ),
        "threat_intel": ThreatIntelResult(
            threat_level=0.95,
            sources=[
                ThreatSource(source_name="high_risk_country_IR", confidence=1.0),
                ThreatSource(source_name="merchant_watchlist_M-999", confidence=0.95),
                ThreatSource(source_name="fraud_pattern_web_unknown_foreign", confidence=0.6),
                ThreatSource(source_name="fraud_pattern_high_amount_new_device", confidence=0.7),
            ],
        ),
        "status": "processing",
        "trace": [],
    }

    print("\n[INPUTS FROM PHASE 1 AGENTS]")
    print(f"  TransactionContext: {len(state['transaction_signals'].flags)} flags")
    print(f"  BehavioralPattern: deviation_score = {state['behavioral_signals'].deviation_score:.2f}")
    print(f"  PolicyRAG: {len(state['policy_matches'].matches)} policy matches")
    print(f"  ExternalThreat: threat_level = {state['threat_intel'].threat_level:.2f}")

    print("\n[Running Evidence Aggregation Agent...]")
    result = await evidence_aggregation_agent(state)

    evidence = result["evidence"]

    print("\n" + "=" * 70)
    print("AGGREGATED EVIDENCE")
    print("=" * 70)
    print(f"\n[COMPOSITE RISK SCORE: {evidence.composite_risk_score:.2f}/100]")
    print(f"[RISK CATEGORY: {evidence.risk_category.upper()}]")

    print(f"\n[ALL SIGNALS: {len(evidence.all_signals)}]")
    for i, signal in enumerate(evidence.all_signals[:10], 1):  # Show first 10
        print(f"  {i}. {signal}")
    if len(evidence.all_signals) > 10:
        print(f"  ... and {len(evidence.all_signals) - 10} more")

    print(f"\n[ALL CITATIONS: {len(evidence.all_citations)}]")
    for i, citation in enumerate(evidence.all_citations, 1):
        print(f"  {i}. {citation[:70]}{'...' if len(citation) > 70 else ''}")

    if "trace" in result:
        trace = result["trace"][0]
        print(f"\n[EXECUTION]")
        print(f"  Duration: {trace.duration_ms:.2f}ms")
        print(f"  Status: {trace.status}")

    print("\n" + "=" * 70)


async def demo_low_risk_aggregation():
    """Demonstrate Evidence Aggregation with low-risk inputs."""
    print("\n" + "=" * 70)
    print("EVIDENCE AGGREGATION - LOW RISK TRANSACTION")
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
        "behavioral_signals": BehavioralSignals(
            deviation_score=0.05,
            anomalies=[],
            velocity_alert=False,
        ),
        "policy_matches": PolicyMatchResult(matches=[], chunk_ids=[]),
        "threat_intel": ThreatIntelResult(threat_level=0.0, sources=[]),
        "status": "processing",
        "trace": [],
    }

    print("\n[INPUTS FROM PHASE 1 AGENTS]")
    print(f"  TransactionContext: {len(state['transaction_signals'].flags)} flags")
    print(f"  BehavioralPattern: deviation_score = {state['behavioral_signals'].deviation_score:.2f}")
    print(f"  PolicyRAG: {len(state['policy_matches'].matches)} policy matches")
    print(f"  ExternalThreat: threat_level = {state['threat_intel'].threat_level:.2f}")

    print("\n[Running Evidence Aggregation Agent...]")
    result = await evidence_aggregation_agent(state)

    evidence = result["evidence"]

    print("\n" + "=" * 70)
    print("AGGREGATED EVIDENCE")
    print("=" * 70)
    print(f"\n[COMPOSITE RISK SCORE: {evidence.composite_risk_score:.2f}/100]")
    print(f"[RISK CATEGORY: {evidence.risk_category.upper()}]")

    if evidence.all_signals:
        print(f"\n[ALL SIGNALS: {len(evidence.all_signals)}]")
    else:
        print("\n[No risk signals detected]")

    if evidence.all_citations:
        print(f"\n[ALL CITATIONS: {len(evidence.all_citations)}]")
    else:
        print("[No policy or threat citations]")

    print("\n" + "=" * 70)


async def demo_graceful_degradation():
    """Demonstrate graceful degradation when some agents fail."""
    print("\n" + "=" * 70)
    print("EVIDENCE AGGREGATION - GRACEFUL DEGRADATION")
    print("=" * 70)

    state: OrchestratorState = {
        "transaction": Transaction(
            transaction_id="T-PARTIAL-001",
            customer_id="C-PARTIAL-001",
            amount=1500.0,
            currency="USD",
            country="BR",
            channel="mobile",
            device_id="D-05",
            timestamp=datetime.now(timezone.utc),
            merchant_id="M-200",
        ),
        "customer_behavior": CustomerBehavior(
            customer_id="C-PARTIAL-001",
            usual_amount_avg=800.0,
            usual_hours="08:00-22:00",
            usual_countries=["US", "BR"],
            usual_devices=["D-05"],
        ),
        "transaction_signals": TransactionSignals(
            amount_ratio=1.875,
            is_off_hours=False,
            is_foreign=False,
            is_unknown_device=False,
            channel_risk="medium",
            flags=["elevated_amount_1.9x"],
        ),
        # Simulate: BehavioralPattern agent failed (None)
        # Simulate: PolicyRAG agent failed (None)
        "threat_intel": ThreatIntelResult(
            threat_level=0.4,
            sources=[
                ThreatSource(source_name="medium_risk_country_BR", confidence=0.4)
            ],
        ),
        "status": "processing",
        "trace": [],
    }

    print("\n[INPUTS FROM PHASE 1 AGENTS]")
    print(f"  TransactionContext: ✓ Available")
    print(f"  BehavioralPattern: ✗ Failed (None)")
    print(f"  PolicyRAG: ✗ Failed (None)")
    print(f"  ExternalThreat: ✓ Available")

    print("\n[Running Evidence Aggregation Agent...]")
    print("  (Agent will use safe defaults for missing inputs)")

    result = await evidence_aggregation_agent(state)

    evidence = result["evidence"]

    print("\n" + "=" * 70)
    print("AGGREGATED EVIDENCE (DEGRADED MODE)")
    print("=" * 70)
    print(f"\n[COMPOSITE RISK SCORE: {evidence.composite_risk_score:.2f}/100]")
    print(f"[RISK CATEGORY: {evidence.risk_category.upper()}]")

    print(f"\n[ALL SIGNALS: {len(evidence.all_signals)}]")
    for signal in evidence.all_signals:
        print(f"  - {signal}")

    print("\n[OBSERVATION]")
    print("  Despite 2 agents failing, the aggregator successfully computed")
    print("  a risk score using only available inputs (graceful degradation).")

    print("\n" + "=" * 70)


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("EVIDENCE AGGREGATION AGENT DEMONSTRATIONS")
    print("=" * 70)
    print("\nThis agent consolidates outputs from Phase 1 (Parallel Collection):")
    print("  - TransactionContext → transaction_signals")
    print("  - BehavioralPattern → behavioral_signals")
    print("  - PolicyRAG → policy_matches")
    print("  - ExternalThreat → threat_intel")
    print("\nAggregation Strategy:")
    print("  - Weighted composite score (behavioral 30%, policy 25%, threat 20%, tx 25%)")
    print("  - Signal/citation consolidation")
    print("  - Risk category determination")
    print("  - Graceful degradation for missing inputs")
    print("\n" + "=" * 70)

    await demo_high_risk_aggregation()
    await demo_low_risk_aggregation()
    await demo_graceful_degradation()

    print("\n[SUMMARY]")
    print("The Evidence Aggregation agent:")
    print("  ✓ Consolidates all Phase 1 agent outputs")
    print("  ✓ Calculates weighted composite risk score (0-100)")
    print("  ✓ Aggregates signals and citations for audit trail")
    print("  ✓ Determines risk category (low/medium/high/critical)")
    print("  ✓ Handles missing inputs gracefully (degraded mode)")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
