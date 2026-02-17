"""LangGraph orchestrator — wires all 8 agents into a StateGraph pipeline.

Graph topology:
    START -> validate_input -> phase1_parallel -> evidence_aggregation
          -> debate_parallel -> decision_arbiter -> explainability
          -> persist_audit -> [hitl_queue] -> respond -> END

Parallel phases use asyncio.gather with return_exceptions=True for graceful
degradation when individual agents fail.
"""

import asyncio
import time
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants import AGENT_TIMEOUTS
from ..db.models import AgentTrace as AgentTraceDB
from ..db.models import HITLCase, TransactionRecord
from ..models import (
    CustomerBehavior,
    DebateArguments,
    FraudDecision,
    OrchestratorState,
    Transaction,
)
from ..models.trace import AgentTraceEntry
from ..utils.logger import get_logger
from .behavioral_pattern import behavioral_pattern_agent
from .debate import debate_pro_customer_agent, debate_pro_fraud_agent
from .decision_arbiter import decision_arbiter_agent
from .evidence_aggregator import evidence_aggregation_agent
from .explainability import explainability_agent
from .external_threat import external_threat_agent
from .policy_rag import policy_rag_agent
from .transaction_context import transaction_context_agent

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# WebSocket broadcast helper
# ---------------------------------------------------------------------------


async def _broadcast(
    config: RunnableConfig, event: str, agent: str | None = None, data: dict | None = None
):
    """Send a WebSocket event if a broadcast function was provided via config."""
    fn = config.get("configurable", {}).get("broadcast_fn")
    transaction_id = config.get("configurable", {}).get("transaction_id", "")
    if fn:
        try:
            await fn(transaction_id, event, agent, data)
        except Exception:
            pass  # Never crash the pipeline because of WS


async def _run_agent(config: RunnableConfig, name: str, agent_fn, state: OrchestratorState) -> dict:
    """Wrap an agent call with independent start/complete broadcasts."""
    await _broadcast(config, "agent_started", name)
    try:
        result = await agent_fn(state)
        await _broadcast(config, "agent_completed", name, {"status": "success"})
        return result
    except BaseException:
        await _broadcast(config, "agent_completed", name, {"status": "error"})
        raise


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def validate_input(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Check that required input fields are present."""
    await _broadcast(config, "agent_started", "validate_input")
    start = time.perf_counter()
    transaction = state.get("transaction")
    customer_behavior = state.get("customer_behavior")

    if not transaction or not customer_behavior:
        missing = []
        if not transaction:
            missing.append("transaction")
        if not customer_behavior:
            missing.append("customer_behavior")
        logger.error("validate_input_missing_fields", missing=missing)
        duration_ms = (time.perf_counter() - start) * 1000
        await _broadcast(config, "agent_completed", "validate_input", {"status": "error"})
        return {
            "status": "error",
            "trace": [
                AgentTraceEntry(
                    agent_name="validate_input",
                    timestamp=datetime.now(UTC),
                    duration_ms=duration_ms,
                    input_summary=f"missing={missing}",
                    output_summary="status=error",
                    status="error",
                )
            ],
        }

    logger.info(
        "validate_input_ok",
        transaction_id=transaction.transaction_id,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    await _broadcast(config, "agent_completed", "validate_input", {"status": "success"})
    return {
        "status": "processing",
        "trace": [
            AgentTraceEntry(
                agent_name="validate_input",
                timestamp=datetime.now(UTC),
                duration_ms=duration_ms,
                input_summary=f"transaction={transaction.transaction_id}",
                output_summary="status=processing",
                status="success",
            )
        ],
    }


async def phase1_parallel(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Run Phase 1 collection agents in parallel (4 agents)."""
    results = await asyncio.gather(
        _run_agent(config, "transaction_context", transaction_context_agent, state),
        _run_agent(config, "behavioral_pattern", behavioral_pattern_agent, state),
        _run_agent(config, "policy_rag", policy_rag_agent, state),
        _run_agent(config, "external_threat", external_threat_agent, state),
        return_exceptions=True,
    )

    merged: dict = {}
    trace_entries: list[AgentTraceEntry] = []

    for result in results:
        if isinstance(result, BaseException):
            logger.error("phase1_agent_failed", error=str(result))
            continue
        trace_entries.extend(result.pop("trace", []))
        merged.update(result)

    merged["trace"] = trace_entries
    return merged


async def evidence_aggregation_node(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Phase 2 — consolidate all signals."""
    await _broadcast(config, "agent_started", "evidence_aggregation")
    result = await evidence_aggregation_agent(state)
    await _broadcast(config, "agent_completed", "evidence_aggregation", {"status": "success"})
    return result


async def debate_parallel(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Run Phase 3 debate agents in parallel, then merge into DebateArguments."""
    results = await asyncio.gather(
        _run_agent(config, "debate_pro_fraud", debate_pro_fraud_agent, state),
        _run_agent(config, "debate_pro_customer", debate_pro_customer_agent, state),
        return_exceptions=True,
    )

    fraud_result: dict = {}
    customer_result: dict = {}
    trace_entries: list[AgentTraceEntry] = []

    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.error("debate_agent_failed", index=i, error=str(result))
            continue
        trace_entries.extend(result.pop("trace", []))
        if i == 0:
            fraud_result = result
        else:
            customer_result = result

    debate = DebateArguments(
        pro_fraud_argument=fraud_result.get(
            "pro_fraud_argument",
            "Argumento no disponible por error en agente.",
        ),
        pro_fraud_confidence=fraud_result.get("pro_fraud_confidence", 0.5),
        pro_fraud_evidence=fraud_result.get("pro_fraud_evidence", []),
        pro_customer_argument=customer_result.get(
            "pro_customer_argument",
            "Argumento no disponible por error en agente.",
        ),
        pro_customer_confidence=customer_result.get("pro_customer_confidence", 0.5),
        pro_customer_evidence=customer_result.get("pro_customer_evidence", []),
    )

    return {"debate": debate, "trace": trace_entries}


async def decision_arbiter_node(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Phase 4 — make final decision."""
    await _broadcast(config, "agent_started", "decision_arbiter")
    result = await decision_arbiter_agent(state)
    await _broadcast(config, "agent_completed", "decision_arbiter", {"status": "success"})
    return result


async def explainability_node(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Phase 5 — generate explanations."""
    await _broadcast(config, "agent_started", "explainability")
    result = await explainability_agent(state)
    await _broadcast(config, "agent_completed", "explainability", {"status": "success"})
    return result


async def persist_audit(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Persist transaction record and agent traces to the database.

    Non-fatal: DB errors are logged but do NOT crash the pipeline.
    """
    try:
        db_session: AsyncSession = config["configurable"]["db_session"]
        transaction = state["transaction"]
        decision: FraudDecision = state["decision"]

        # Build analysis_state from OrchestratorState
        analysis_state = {
            "customer_behavior": (
                state["customer_behavior"].model_dump(mode="json")
                if state.get("customer_behavior")
                else None
            ),
            "transaction_signals": (
                state["transaction_signals"].model_dump(mode="json")
                if state.get("transaction_signals")
                else None
            ),
            "behavioral_signals": (
                state["behavioral_signals"].model_dump(mode="json")
                if state.get("behavioral_signals")
                else None
            ),
            "policy_matches": (
                state["policy_matches"].model_dump(mode="json")
                if state.get("policy_matches")
                else None
            ),
            "threat_intel": (
                state["threat_intel"].model_dump(mode="json") if state.get("threat_intel") else None
            ),
            "evidence": (
                state["evidence"].model_dump(mode="json") if state.get("evidence") else None
            ),
            "debate": (state["debate"].model_dump(mode="json") if state.get("debate") else None),
            "explanation": (
                state["explanation"].model_dump(mode="json") if state.get("explanation") else None
            ),
        }

        # Create TransactionRecord with analysis_state
        record = TransactionRecord(
            transaction_id=transaction.transaction_id,
            raw_data=transaction.model_dump(mode="json"),
            decision=decision.decision,
            confidence=float(decision.confidence),
            analysis_state=analysis_state,
        )
        db_session.add(record)
        await db_session.flush()

        # Create AgentTrace rows
        for entry in state.get("trace", []):
            trace_row = AgentTraceDB(
                transaction_id=transaction.transaction_id,
                agent_name=entry.agent_name,
                duration_ms=int(entry.duration_ms),
                input_summary=entry.input_summary,
                output_summary=entry.output_summary,
                status=entry.status,
            )
            db_session.add(trace_row)

        await db_session.commit()
        logger.info(
            "persist_audit_ok",
            transaction_id=transaction.transaction_id,
        )
    except Exception as e:
        logger.error("persist_audit_failed", error=str(e), exc_info=True)

    return {}


async def hitl_queue(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Create HITL case for ESCALATE_TO_HUMAN decisions."""
    try:
        db_session: AsyncSession = config["configurable"]["db_session"]
        transaction = state["transaction"]

        case = HITLCase(
            transaction_id=transaction.transaction_id,
            status="pending",
        )
        db_session.add(case)
        await db_session.commit()
        logger.info(
            "hitl_case_created",
            transaction_id=transaction.transaction_id,
        )
    except Exception as e:
        logger.error("hitl_queue_failed", error=str(e), exc_info=True)

    return {"status": "escalated"}


async def respond(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Terminal node — set final status and broadcast decision."""
    decision = state.get("decision")
    if decision:
        await _broadcast(
            config,
            "decision_ready",
            data={
                "decision": decision.decision,
                "confidence": float(decision.confidence),
            },
        )

    if state.get("status") == "escalated":
        return {}
    return {"status": "completed"}


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------


def route_after_validation(state: OrchestratorState) -> str:
    """Route after validate_input: continue pipeline or short-circuit on error."""
    if state.get("status") == "error":
        return "error"
    return "continue"


def route_decision(state: OrchestratorState) -> str:
    """Route after persist_audit: HITL queue or straight to respond."""
    decision = state.get("decision")
    if decision and decision.decision == "ESCALATE_TO_HUMAN":
        return "hitl_queue"
    return "respond"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Build and compile the fraud-detection LangGraph pipeline."""
    builder = StateGraph(OrchestratorState)

    # Nodes
    builder.add_node("validate_input", validate_input)
    builder.add_node("phase1_parallel", phase1_parallel)
    builder.add_node("evidence_aggregation", evidence_aggregation_node)
    builder.add_node("debate_parallel", debate_parallel)
    builder.add_node("decision_arbiter", decision_arbiter_node)
    builder.add_node("explainability", explainability_node)
    builder.add_node("persist_audit", persist_audit)
    builder.add_node("hitl_queue", hitl_queue)
    builder.add_node("respond", respond)

    # Edges
    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"continue": "phase1_parallel", "error": "respond"},
    )
    builder.add_edge("phase1_parallel", "evidence_aggregation")
    builder.add_edge("evidence_aggregation", "debate_parallel")
    builder.add_edge("debate_parallel", "decision_arbiter")
    builder.add_edge("decision_arbiter", "explainability")
    builder.add_edge("explainability", "persist_audit")
    builder.add_conditional_edges(
        "persist_audit",
        route_decision,
        {"hitl_queue": "hitl_queue", "respond": "respond"},
    )
    builder.add_edge("hitl_queue", "respond")
    builder.add_edge("respond", END)

    return builder.compile()


# Module-level compiled graph singleton
graph = build_graph()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_transaction(
    transaction: Transaction,
    customer_behavior: CustomerBehavior,
    db_session: AsyncSession,
    broadcast_fn=None,
) -> FraudDecision:
    """Run the full fraud-detection pipeline and return the final decision.

    Args:
        transaction: The financial transaction to analyze.
        customer_behavior: Historical behavior profile for the customer.
        db_session: Async SQLAlchemy session for persistence.
        broadcast_fn: Optional async callable(transaction_id, event, agent, data)
                      for real-time WebSocket broadcasts. When None, no broadcasts
                      are emitted (backward compatible).

    Returns:
        FraudDecision with decision, confidence, signals, and explanations.

    Raises:
        asyncio.TimeoutError: If the pipeline exceeds the configured timeout (see AGENT_TIMEOUTS.pipeline).
        KeyError: If the pipeline finishes without producing a decision
                  (should not happen with proper fallbacks in agents).
    """
    initial_state: OrchestratorState = {
        "transaction": transaction,
        "customer_behavior": customer_behavior,
        "status": "pending",
        "trace": [],
    }
    config: RunnableConfig = {
        "configurable": {
            "db_session": db_session,
            "broadcast_fn": broadcast_fn,
            "transaction_id": transaction.transaction_id,
        }
    }

    final_state = await asyncio.wait_for(
        graph.ainvoke(initial_state, config=config),
        timeout=AGENT_TIMEOUTS.pipeline,
    )

    return final_state["decision"]
