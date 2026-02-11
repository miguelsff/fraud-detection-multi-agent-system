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
from .debate import debate_pro_customer_agent, debate_pro_fraud_agent
from .decision_arbiter import decision_arbiter_agent
from .evidence_aggregator import evidence_aggregation_agent
from .explainability import explainability_agent
from .external_threat import external_threat_agent
from .policy_rag import policy_rag_agent
from .transaction_context import transaction_context_agent

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def validate_input(state: OrchestratorState) -> dict:
    """Check that required input fields are present."""
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


async def phase1_parallel(state: OrchestratorState) -> dict:
    """Run Phase 1 collection agents in parallel (3 agents)."""
    results = await asyncio.gather(
        transaction_context_agent(state),
        policy_rag_agent(state),
        external_threat_agent(state),
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


async def evidence_aggregation_node(state: OrchestratorState) -> dict:
    """Phase 2 — consolidate all signals."""
    return await evidence_aggregation_agent(state)


async def debate_parallel(state: OrchestratorState) -> dict:
    """Run Phase 3 debate agents in parallel, then merge into DebateArguments."""
    results = await asyncio.gather(
        debate_pro_fraud_agent(state),
        debate_pro_customer_agent(state),
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


async def decision_arbiter_node(state: OrchestratorState) -> dict:
    """Phase 4 — make final decision."""
    return await decision_arbiter_agent(state)


async def explainability_node(state: OrchestratorState) -> dict:
    """Phase 5 — generate explanations."""
    return await explainability_agent(state)


async def persist_audit(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Persist transaction record and agent traces to the database.

    Non-fatal: DB errors are logged but do NOT crash the pipeline.
    """
    try:
        db_session: AsyncSession = config["configurable"]["db_session"]
        transaction = state["transaction"]
        decision: FraudDecision = state["decision"]

        # Create TransactionRecord
        record = TransactionRecord(
            transaction_id=transaction.transaction_id,
            raw_data=transaction.model_dump(mode="json"),
            decision=decision.decision,
            confidence=float(decision.confidence),
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


async def respond(state: OrchestratorState) -> dict:
    """Terminal node — set final status."""
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
) -> FraudDecision:
    """Run the full fraud-detection pipeline and return the final decision.

    Args:
        transaction: The financial transaction to analyze.
        customer_behavior: Historical behavior profile for the customer.
        db_session: Async SQLAlchemy session for persistence.

    Returns:
        FraudDecision with decision, confidence, signals, and explanations.

    Raises:
        asyncio.TimeoutError: If the pipeline exceeds 60 seconds.
        KeyError: If the pipeline finishes without producing a decision
                  (should not happen with proper fallbacks in agents).
    """
    initial_state: OrchestratorState = {
        "transaction": transaction,
        "customer_behavior": customer_behavior,
        "status": "pending",
        "trace": [],
    }
    config: RunnableConfig = {"configurable": {"db_session": db_session}}

    final_state = await asyncio.wait_for(
        graph.ainvoke(initial_state, config=config),
        timeout=60.0,
    )

    return final_state["decision"]
