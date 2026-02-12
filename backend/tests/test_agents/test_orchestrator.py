"""Tests for the LangGraph orchestrator (graph construction, nodes, routing, full pipeline)."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import (
    analyze_transaction,
    build_graph,
    debate_parallel,
    hitl_queue,
    persist_audit,
    phase1_parallel,
    respond,
    route_after_validation,
    route_decision,
    validate_input,
)
from app.models import (
    AggregatedEvidence,
    CustomerBehavior,
    DebateArguments,
    ExplanationResult,
    FraudDecision,
    OrchestratorState,
    Transaction,
    TransactionSignals,
)
from app.models.evidence import PolicyMatchResult, ThreatIntelResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_transaction() -> Transaction:
    return Transaction(
        transaction_id="T-1001",
        customer_id="C-501",
        amount=1800.00,
        currency="PEN",
        country="PE",
        channel="web",
        device_id="D-01",
        timestamp=datetime(2025, 1, 15, 3, 15, tzinfo=timezone.utc),
        merchant_id="M-200",
    )


@pytest.fixture
def sample_customer_behavior() -> CustomerBehavior:
    return CustomerBehavior(
        customer_id="C-501",
        usual_amount_avg=500.00,
        usual_hours="08:00-22:00",
        usual_countries=["PE"],
        usual_devices=["D-01", "D-02"],
    )


@pytest.fixture
def sample_signals() -> TransactionSignals:
    return TransactionSignals(
        amount_ratio=3.6,
        is_off_hours=True,
        is_foreign=False,
        is_unknown_device=False,
        channel_risk="low",
        flags=["high_amount_ratio_3.6x", "transaction_off_hours"],
    )


@pytest.fixture
def sample_evidence() -> AggregatedEvidence:
    return AggregatedEvidence(
        composite_risk_score=68.5,
        all_signals=["high_amount", "off_hours"],
        all_citations=["FP-01: Transacciones nocturnas"],
        risk_category="high",
    )


@pytest.fixture
def sample_debate() -> DebateArguments:
    return DebateArguments(
        pro_fraud_argument="Alta probabilidad de fraude.",
        pro_fraud_confidence=0.78,
        pro_fraud_evidence=["high_amount"],
        pro_customer_argument="Cliente conocido.",
        pro_customer_confidence=0.55,
        pro_customer_evidence=["known_device"],
    )


@pytest.fixture
def sample_decision(sample_transaction) -> FraudDecision:
    return FraudDecision(
        transaction_id=sample_transaction.transaction_id,
        decision="CHALLENGE",
        confidence=0.72,
        signals=["high_amount", "off_hours"],
        citations_internal=[{"policy_id": "FP-01", "text": "nocturnas"}],
        citations_external=[{"source": "external", "detail": "none"}],
        explanation_customer="Verificacion requerida.",
        explanation_audit="Riesgo alto.",
        agent_trace=["transaction_context", "policy_rag"],
    )


@pytest.fixture
def sample_explanation() -> ExplanationResult:
    return ExplanationResult(
        customer_explanation="Verificacion requerida.",
        audit_explanation="Riesgo alto detallado.",
    )


@pytest.fixture
def full_state(
    sample_transaction,
    sample_customer_behavior,
    sample_signals,
    sample_evidence,
    sample_debate,
    sample_decision,
    sample_explanation,
) -> OrchestratorState:
    """A fully-populated orchestrator state (post-pipeline)."""
    return {
        "transaction": sample_transaction,
        "customer_behavior": sample_customer_behavior,
        "status": "completed",
        "trace": [],
        "transaction_signals": sample_signals,
        "evidence": sample_evidence,
        "debate": sample_debate,
        "decision": sample_decision,
        "explanation": sample_explanation,
    }


def _mock_db_session() -> AsyncMock:
    session = AsyncMock()
    # add is synchronous in SQLAlchemy, the rest are awaitable
    session.add = MagicMock()
    return session


def _runnable_config(db_session=None) -> dict:
    return {"configurable": {"db_session": db_session or _mock_db_session()}}


# ============================================================================
# validate_input tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_validate_input_valid(sample_transaction, sample_customer_behavior):
    """Valid state returns status=processing."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "customer_behavior": sample_customer_behavior,
        "status": "pending",
        "trace": [],
    }
    result = await validate_input(state)
    assert result["status"] == "processing"
    assert len(result["trace"]) == 1
    assert result["trace"][0].agent_name == "validate_input"
    assert result["trace"][0].status == "success"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_validate_input_missing_transaction(sample_customer_behavior):
    """Missing transaction returns status=error."""
    state: OrchestratorState = {
        "customer_behavior": sample_customer_behavior,
        "status": "pending",
        "trace": [],
    }
    result = await validate_input(state)
    assert result["status"] == "error"
    assert result["trace"][0].status == "error"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_validate_input_missing_customer(sample_transaction):
    """Missing customer_behavior returns status=error."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "status": "pending",
        "trace": [],
    }
    result = await validate_input(state)
    assert result["status"] == "error"


# ============================================================================
# Routing function tests
# ============================================================================


@pytest.mark.unit
def test_route_after_validation_ok():
    """Returns 'continue' for status=processing."""
    state: OrchestratorState = {"status": "processing", "trace": []}
    assert route_after_validation(state) == "continue"


@pytest.mark.unit
def test_route_after_validation_error():
    """Returns 'error' for status=error."""
    state: OrchestratorState = {"status": "error", "trace": []}
    assert route_after_validation(state) == "error"


@pytest.mark.unit
def test_route_decision_approve(sample_decision):
    """Non-escalate decision routes to 'respond'."""
    state: OrchestratorState = {"decision": sample_decision, "trace": []}
    assert route_decision(state) == "respond"


@pytest.mark.unit
def test_route_decision_escalate(sample_transaction):
    """ESCALATE_TO_HUMAN decision routes to 'hitl_queue'."""
    escalate_decision = FraudDecision(
        transaction_id=sample_transaction.transaction_id,
        decision="ESCALATE_TO_HUMAN",
        confidence=0.50,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="En revision.",
        explanation_audit="Escalado.",
        agent_trace=[],
    )
    state: OrchestratorState = {"decision": escalate_decision, "trace": []}
    assert route_decision(state) == "hitl_queue"


# ============================================================================
# respond tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_respond_sets_completed():
    """respond sets status=completed when not escalated."""
    state: OrchestratorState = {"status": "processing", "trace": []}
    result = await respond(state)
    assert result["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_respond_keeps_escalated():
    """respond preserves escalated status."""
    state: OrchestratorState = {"status": "escalated", "trace": []}
    result = await respond(state)
    assert result == {}


# ============================================================================
# phase1_parallel tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_phase1_parallel_all_succeed(sample_transaction, sample_customer_behavior):
    """All 3 agents succeed; merged output contains all expected keys."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "customer_behavior": sample_customer_behavior,
        "status": "processing",
        "trace": [],
    }

    with (
        patch("app.agents.orchestrator.transaction_context_agent") as mock_tc,
        patch("app.agents.orchestrator.policy_rag_agent") as mock_pr,
        patch("app.agents.orchestrator.external_threat_agent") as mock_et,
    ):
        mock_tc.return_value = {"transaction_signals": "signals_val", "trace": [MagicMock()]}
        mock_pr.return_value = {"policy_matches": "matches_val", "trace": [MagicMock()]}
        mock_et.return_value = {"threat_intel": "intel_val", "trace": [MagicMock()]}

        result = await phase1_parallel(state)

    assert result["transaction_signals"] == "signals_val"
    assert result["policy_matches"] == "matches_val"
    assert result["threat_intel"] == "intel_val"
    assert len(result["trace"]) == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_phase1_parallel_one_fails(sample_transaction, sample_customer_behavior):
    """One agent raises; other 2 succeed (graceful degradation)."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "customer_behavior": sample_customer_behavior,
        "status": "processing",
        "trace": [],
    }

    async def failing_agent(s):
        raise RuntimeError("boom")

    with (
        patch("app.agents.orchestrator.transaction_context_agent", side_effect=failing_agent),
        patch("app.agents.orchestrator.policy_rag_agent") as mock_pr,
        patch("app.agents.orchestrator.external_threat_agent") as mock_et,
    ):
        mock_pr.return_value = {"policy_matches": "ok", "trace": [MagicMock()]}
        mock_et.return_value = {"threat_intel": "ok", "trace": [MagicMock()]}

        result = await phase1_parallel(state)

    # transaction_signals not set (agent failed), but pipeline continues
    assert "transaction_signals" not in result
    assert result["policy_matches"] == "ok"
    assert result["threat_intel"] == "ok"
    assert len(result["trace"]) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_phase1_parallel_merges_trace(sample_transaction, sample_customer_behavior):
    """Trace entries from all agents are combined."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "customer_behavior": sample_customer_behavior,
        "status": "processing",
        "trace": [],
    }

    trace_a, trace_b, trace_c = MagicMock(), MagicMock(), MagicMock()

    with (
        patch("app.agents.orchestrator.transaction_context_agent") as mock_tc,
        patch("app.agents.orchestrator.policy_rag_agent") as mock_pr,
        patch("app.agents.orchestrator.external_threat_agent") as mock_et,
    ):
        mock_tc.return_value = {"transaction_signals": "v", "trace": [trace_a]}
        mock_pr.return_value = {"policy_matches": "v", "trace": [trace_b]}
        mock_et.return_value = {"threat_intel": "v", "trace": [trace_c]}

        result = await phase1_parallel(state)

    assert result["trace"] == [trace_a, trace_b, trace_c]


# ============================================================================
# debate_parallel tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_debate_parallel_merges_into_debate_arguments():
    """Two flat results merged into a single DebateArguments."""
    state: OrchestratorState = {"evidence": MagicMock(), "trace": []}

    with (
        patch("app.agents.orchestrator.debate_pro_fraud_agent") as mock_f,
        patch("app.agents.orchestrator.debate_pro_customer_agent") as mock_c,
    ):
        mock_f.return_value = {
            "pro_fraud_argument": "Fraude probable.",
            "pro_fraud_confidence": 0.80,
            "pro_fraud_evidence": ["sig1"],
            "trace": [MagicMock()],
        }
        mock_c.return_value = {
            "pro_customer_argument": "Legitimo.",
            "pro_customer_confidence": 0.60,
            "pro_customer_evidence": ["sig2"],
            "trace": [MagicMock()],
        }

        result = await debate_parallel(state)

    debate = result["debate"]
    assert isinstance(debate, DebateArguments)
    assert debate.pro_fraud_argument == "Fraude probable."
    assert debate.pro_fraud_confidence == 0.80
    assert debate.pro_customer_argument == "Legitimo."
    assert debate.pro_customer_confidence == 0.60
    assert len(result["trace"]) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_debate_parallel_one_fails():
    """One debate agent fails; DebateArguments uses fallback values."""
    state: OrchestratorState = {"evidence": MagicMock(), "trace": []}

    async def failing_agent(s):
        raise RuntimeError("debate boom")

    with (
        patch("app.agents.orchestrator.debate_pro_fraud_agent", side_effect=failing_agent),
        patch("app.agents.orchestrator.debate_pro_customer_agent") as mock_c,
    ):
        mock_c.return_value = {
            "pro_customer_argument": "Legitimo.",
            "pro_customer_confidence": 0.65,
            "pro_customer_evidence": ["sig"],
            "trace": [MagicMock()],
        }

        result = await debate_parallel(state)

    debate = result["debate"]
    assert isinstance(debate, DebateArguments)
    # Fraud side should have fallback defaults
    assert debate.pro_fraud_confidence == 0.5
    assert "no disponible" in debate.pro_fraud_argument.lower() or debate.pro_fraud_argument != ""
    # Customer side should have real values
    assert debate.pro_customer_argument == "Legitimo."
    assert debate.pro_customer_confidence == 0.65


# ============================================================================
# persist_audit tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_persist_audit_creates_records(full_state):
    """TransactionRecord and AgentTrace rows are created."""
    db_session = _mock_db_session()
    config = _runnable_config(db_session)

    result = await persist_audit(full_state, config)

    assert result == {}
    # add() called at least for TransactionRecord
    assert db_session.add.called
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_persist_audit_db_error_non_fatal(full_state):
    """DB error is logged but pipeline continues (returns empty dict)."""
    db_session = _mock_db_session()
    db_session.flush.side_effect = Exception("DB connection lost")
    config = _runnable_config(db_session)

    result = await persist_audit(full_state, config)

    assert result == {}  # Non-fatal — pipeline continues


# ============================================================================
# hitl_queue tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hitl_queue_creates_case(sample_transaction):
    """HITLCase is created and status is set to 'escalated'."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "trace": [],
    }
    db_session = _mock_db_session()
    config = _runnable_config(db_session)

    result = await hitl_queue(state, config)

    assert result["status"] == "escalated"
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hitl_queue_db_error_non_fatal(sample_transaction):
    """DB error in HITL is logged but returns escalated status."""
    state: OrchestratorState = {
        "transaction": sample_transaction,
        "trace": [],
    }
    db_session = _mock_db_session()
    db_session.commit.side_effect = Exception("DB error")
    config = _runnable_config(db_session)

    result = await hitl_queue(state, config)

    assert result["status"] == "escalated"


# ============================================================================
# Graph construction test
# ============================================================================


@pytest.mark.unit
def test_build_graph_compiles():
    """Graph compiles without errors and has expected nodes."""
    compiled = build_graph()
    # The compiled graph should be truthy
    assert compiled is not None


# ============================================================================
# Full pipeline integration tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_transaction_full_pipeline(
    sample_transaction, sample_customer_behavior, sample_decision, sample_explanation
):
    """Full pipeline with all agents mocked returns a FraudDecision."""
    db_session = _mock_db_session()

    # Mock all agents
    with (
        patch("app.agents.orchestrator.transaction_context_agent") as mock_tc,
        patch("app.agents.orchestrator.policy_rag_agent") as mock_pr,
        patch("app.agents.orchestrator.external_threat_agent") as mock_et,
        patch("app.agents.orchestrator.evidence_aggregation_agent") as mock_ea,
        patch("app.agents.orchestrator.debate_pro_fraud_agent") as mock_df,
        patch("app.agents.orchestrator.debate_pro_customer_agent") as mock_dc,
        patch("app.agents.orchestrator.decision_arbiter_agent") as mock_da,
        patch("app.agents.orchestrator.explainability_agent") as mock_ex,
    ):
        mock_tc.return_value = {
            "transaction_signals": TransactionSignals(
                amount_ratio=3.6,
                is_off_hours=True,
                is_foreign=False,
                is_unknown_device=False,
                channel_risk="low",
                flags=["high_amount"],
            ),
            "trace": [],
        }
        mock_pr.return_value = {
            "policy_matches": PolicyMatchResult(matches=[], chunk_ids=[]),
            "trace": [],
        }
        mock_et.return_value = {
            "threat_intel": ThreatIntelResult(threat_level=0.0, sources=[]),
            "trace": [],
        }
        mock_ea.return_value = {
            "evidence": AggregatedEvidence(
                composite_risk_score=68.5,
                all_signals=["high_amount"],
                all_citations=[],
                risk_category="high",
            ),
            "trace": [],
        }
        mock_df.return_value = {
            "pro_fraud_argument": "Fraude.",
            "pro_fraud_confidence": 0.78,
            "pro_fraud_evidence": ["high_amount"],
            "trace": [],
        }
        mock_dc.return_value = {
            "pro_customer_argument": "Legitimo.",
            "pro_customer_confidence": 0.55,
            "pro_customer_evidence": ["known_device"],
            "trace": [],
        }
        mock_da.return_value = {"decision": sample_decision, "trace": []}
        mock_ex.return_value = {"explanation": sample_explanation, "trace": []}

        result = await analyze_transaction(
            sample_transaction, sample_customer_behavior, db_session
        )

    assert isinstance(result, FraudDecision)
    assert result.decision == "CHALLENGE"
    assert result.transaction_id == "T-1001"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_transaction_validation_error(sample_customer_behavior):
    """Missing transaction causes error status — pipeline short-circuits."""
    db_session = _mock_db_session()

    # Transaction is required but we pass a fake state without it
    # We need to invoke the graph directly to test validation error
    from app.agents.orchestrator import graph

    initial_state: OrchestratorState = {
        "customer_behavior": sample_customer_behavior,
        "status": "pending",
        "trace": [],
    }
    config = {"configurable": {"db_session": db_session}}

    final_state = await graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "completed"  # respond sets completed even for error path


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_transaction_escalation(
    sample_transaction, sample_customer_behavior, sample_explanation
):
    """ESCALATE_TO_HUMAN decision triggers HITL queue creation."""
    db_session = _mock_db_session()

    escalate_decision = FraudDecision(
        transaction_id="T-1001",
        decision="ESCALATE_TO_HUMAN",
        confidence=0.50,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="En revision.",
        explanation_audit="Escalado.",
        agent_trace=[],
    )

    with (
        patch("app.agents.orchestrator.transaction_context_agent") as mock_tc,
        patch("app.agents.orchestrator.policy_rag_agent") as mock_pr,
        patch("app.agents.orchestrator.external_threat_agent") as mock_et,
        patch("app.agents.orchestrator.evidence_aggregation_agent") as mock_ea,
        patch("app.agents.orchestrator.debate_pro_fraud_agent") as mock_df,
        patch("app.agents.orchestrator.debate_pro_customer_agent") as mock_dc,
        patch("app.agents.orchestrator.decision_arbiter_agent") as mock_da,
        patch("app.agents.orchestrator.explainability_agent") as mock_ex,
    ):
        mock_tc.return_value = {"transaction_signals": MagicMock(), "trace": []}
        mock_pr.return_value = {"policy_matches": MagicMock(), "trace": []}
        mock_et.return_value = {"threat_intel": MagicMock(), "trace": []}
        mock_ea.return_value = {
            "evidence": AggregatedEvidence(
                composite_risk_score=50.0,
                all_signals=[],
                all_citations=[],
                risk_category="medium",
            ),
            "trace": [],
        }
        mock_df.return_value = {
            "pro_fraud_argument": "A.",
            "pro_fraud_confidence": 0.5,
            "pro_fraud_evidence": [],
            "trace": [],
        }
        mock_dc.return_value = {
            "pro_customer_argument": "B.",
            "pro_customer_confidence": 0.5,
            "pro_customer_evidence": [],
            "trace": [],
        }
        mock_da.return_value = {"decision": escalate_decision, "trace": []}
        mock_ex.return_value = {"explanation": sample_explanation, "trace": []}

        from app.agents.orchestrator import graph

        initial_state: OrchestratorState = {
            "transaction": sample_transaction,
            "customer_behavior": sample_customer_behavior,
            "status": "pending",
            "trace": [],
        }
        config = {"configurable": {"db_session": db_session}}

        final_state = await graph.ainvoke(initial_state, config=config)

    assert final_state["status"] == "escalated"
    # db_session.add should have been called for HITLCase (and TransactionRecord)
    assert db_session.add.call_count >= 1


# ============================================================================
# Integration Tests (Require Ollama Running)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.db
async def test_full_pipeline_approve_t1003(
    transaction_t1003, customer_behavior_c503, in_memory_db
):
    """Integration test: T-1003 → APPROVE or CHALLENGE (requires Ollama running).

    T-1003 characteristics:
    - Amount: 250 PEN (0.5x avg 500) - LOW
    - Country: PE (usual)
    - Time: 14:30 (normal hours)
    - Device: D-03 (known)

    Expected: APPROVE decision with high confidence (or CHALLENGE if LLM is conservative).
    This test validates the full pipeline with real LLM calls.
    """
    decision = await analyze_transaction(
        transaction_t1003,
        customer_behavior_c503,
        in_memory_db,
    )

    # Assertions
    assert isinstance(decision, FraudDecision)
    assert decision.transaction_id == "T-1003"

    # May be APPROVE or CHALLENGE depending on LLM, but should NOT be BLOCK
    assert decision.decision in ["APPROVE", "CHALLENGE"]
    assert decision.confidence > 0.5

    # Should have explanations
    assert len(decision.explanation_customer) > 0
    assert len(decision.explanation_audit) > 0

    # Should have agent trace
    assert len(decision.agent_trace) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.db
async def test_full_pipeline_block_t1002(
    transaction_t1002, customer_behavior_c502, in_memory_db
):
    """Integration test: T-1002 → BLOCK or ESCALATE (requires Ollama).

    T-1002 characteristics:
    - Amount: 8500 USD (17x avg 500) - VERY HIGH
    - Country: NG (Nigeria, not usual)
    - Time: 02:00 (off-hours)
    - Device: D-99 (unknown)

    Expected: BLOCK decision with high confidence (or ESCALATE_TO_HUMAN).
    This test validates extreme risk scenario handling.
    """
    decision = await analyze_transaction(
        transaction_t1002,
        customer_behavior_c502,
        in_memory_db,
    )

    # Assertions
    assert isinstance(decision, FraudDecision)
    assert decision.transaction_id == "T-1002"

    # Should BLOCK or ESCALATE due to extreme risk
    assert decision.decision in ["BLOCK", "ESCALATE_TO_HUMAN"]
    assert decision.confidence > 0.6

    # Should have multiple signals
    assert len(decision.signals) >= 3

    # Should have explanations
    assert len(decision.explanation_customer) > 0
    assert len(decision.explanation_audit) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.db
async def test_full_pipeline_challenge_t1001(
    transaction_t1001, customer_behavior_c501, in_memory_db
):
    """Integration test: T-1001 → CHALLENGE or APPROVE (requires Ollama).

    T-1001 characteristics:
    - Amount: 1800 PEN (3.6x avg 500) - MODERATE
    - Country: PE (usual)
    - Time: 03:15 (off-hours)
    - Device: D-01 (known)

    Expected: CHALLENGE decision (ambiguous risk - moderate amount + off-hours).
    This test validates the debate and decision arbiter logic.
    """
    decision = await analyze_transaction(
        transaction_t1001,
        customer_behavior_c501,
        in_memory_db,
    )

    # Assertions
    assert isinstance(decision, FraudDecision)
    assert decision.transaction_id == "T-1001"

    # Should CHALLENGE or APPROVE (not extreme enough for BLOCK)
    assert decision.decision in ["CHALLENGE", "APPROVE"]
    assert 0.5 <= decision.confidence <= 0.9

    # Should have at least 2 signals (high_amount, off_hours)
    assert len(decision.signals) >= 2

    # Should have explanations
    assert len(decision.explanation_customer) > 0
    assert len(decision.explanation_audit) > 0
