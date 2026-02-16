"""Timing decorator for agent functions."""

import asyncio
import functools
import json
import time
from datetime import UTC, datetime
from typing import Any, Callable

from ..models.trace import AgentTraceEntry


def timed_agent(agent_name: str) -> Callable:
    """Decorator that wraps an agent function with timing and trace entry creation.

    Works with both sync and async functions. The decorated function must accept
    a ``state`` dict as its first argument and return a dict of state updates.

    The decorator appends an ``AgentTraceEntry`` to the returned dict under the
    ``"trace"`` key (as a single-element list for the LangGraph ``operator.add``
    reducer).

    Usage::

        @timed_agent("transaction_context")
        def transaction_context_agent(state: OrchestratorState) -> dict:
            ...
            return {"transaction_signals": signals}
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def async_wrapper(state: dict, *args: Any, **kwargs: Any) -> dict:
            start = time.perf_counter()
            ts = datetime.now(UTC)
            status = "success"
            output_summary = ""

            try:
                result = await fn(state, *args, **kwargs)
            except Exception as exc:
                status = "error"
                output_summary = str(exc)
                raise
            else:
                output_summary = _summarise_result(result)
                return _attach_trace(result, agent_name, ts, start, status, state, output_summary)

        @functools.wraps(fn)
        def sync_wrapper(state: dict, *args: Any, **kwargs: Any) -> dict:
            start = time.perf_counter()
            ts = datetime.now(UTC)
            status = "success"
            output_summary = ""

            try:
                result = fn(state, *args, **kwargs)
            except Exception as exc:
                status = "error"
                output_summary = str(exc)
                raise
            else:
                output_summary = _summarise_result(result)
                return _attach_trace(result, agent_name, ts, start, status, state, output_summary)

        return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper

    return decorator


def _summarise_result(result: dict) -> str:
    try:
        # Excluimos la clave 'trace' para no incluir metadatos
        result_clean = {k: v for k, v in result.items() if k != "trace"}
        serializable = _to_serializable(result_clean)
        # Opcional: limitar longitud para evitar logs excesivos
        json_str = json.dumps(serializable, ensure_ascii=False)
        # Si quieres truncar, puedes hacer: json_str[:1000] + "..." si es muy largo
        return json_str
    except Exception:
        # Fallback seguro: representación string simple
        return str(result)


def _build_input_summary(state: dict, agent_name: str) -> str:
    """Extract key input values based on agent type.

    Instead of just listing keys, this captures specific values that are
    critical for audit trails and debugging.
    """
    summary = {}

    # Always include transaction ID and key attributes if available
    if tx := state.get("transaction"):
        if hasattr(tx, "transaction_id"):
            summary["transaction_id"] = tx.transaction_id
        if hasattr(tx, "amount"):
            summary["amount"] = float(tx.amount)
        if hasattr(tx, "country"):
            summary["country"] = tx.country
        if hasattr(tx, "timestamp"):
            summary["timestamp"] = str(tx.timestamp)

    # Agent-specific inputs
    if agent_name in ("behavioral_pattern", "policy_rag", "external_threat"):
        if tx_signals := state.get("transaction_signals"):
            if hasattr(tx_signals, "amount_ratio"):
                summary["amount_ratio"] = float(tx_signals.amount_ratio)
            if hasattr(tx_signals, "is_foreign"):
                summary["is_foreign"] = tx_signals.is_foreign

    if agent_name == "decision_arbiter":
        if debate := state.get("debate"):
            if hasattr(debate, "pro_fraud_confidence"):
                summary["pro_fraud_confidence"] = float(debate.pro_fraud_confidence)
            if hasattr(debate, "pro_customer_confidence"):
                summary["pro_customer_confidence"] = float(debate.pro_customer_confidence)

    if agent_name == "evidence_aggregation":
        # Include counts from each phase
        if state.get("transaction_signals"):
            summary["has_transaction_signals"] = True
        if state.get("behavioral_signals"):
            summary["has_behavioral_signals"] = True
        if state.get("policy_matches"):
            summary["has_policy_matches"] = True
        if state.get("threat_intel"):
            summary["has_threat_intel"] = True

    return json.dumps(summary, ensure_ascii=False)


def _attach_trace(
    result: dict,
    agent_name: str,
    ts: datetime,
    start: float,
    status: str,
    state: dict,
    output_summary: str,
) -> dict:
    duration_ms = (time.perf_counter() - start) * 1000
    input_summary = _build_input_summary(state, agent_name)

    # Extract optional LLM and RAG metadata from result
    llm_trace = result.pop("_llm_trace", {})
    rag_trace = result.pop("_rag_trace", {})
    error_trace = result.pop("_error_trace", {})

    entry = AgentTraceEntry(
        agent_name=agent_name,
        timestamp=ts,
        duration_ms=duration_ms,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
        # LLM fields
        llm_prompt=llm_trace.get("llm_prompt"),
        llm_response_raw=llm_trace.get("llm_response_raw"),
        llm_model=llm_trace.get("llm_model"),
        llm_temperature=llm_trace.get("llm_temperature"),
        llm_tokens_used=llm_trace.get("llm_tokens_used"),
        # RAG fields
        rag_query=rag_trace.get("rag_query"),
        rag_scores=rag_trace.get("rag_scores"),
        # Error handling fields
        fallback_reason=error_trace.get("fallback_reason"),
        error_details=error_trace.get("error_details"),
    )

    result.setdefault("trace", [])
    result["trace"].append(entry)
    return result


def _to_serializable(obj: Any) -> Any:
    """Convierte objetos complejos a tipos serializables por JSON."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_serializable(value) for key, value in obj.items()}

    # Para objetos personalizados, intentamos obtener un dict
    if hasattr(obj, "dict") and callable(obj.dict):  # Pydantic v1
        return _to_serializable(obj.dict())
    if hasattr(obj, "model_dump") and callable(obj.model_dump):  # Pydantic v2
        return _to_serializable(obj.model_dump())
    if hasattr(obj, "__dict__"):  # Objetos con __dict__
        return _to_serializable(obj.__dict__)
    # Último recurso: convertir a string
    return str(obj)
