"""Timing decorator for agent functions."""

import asyncio
import functools
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
    """Build a short summary of the keys returned by an agent."""
    keys = [k for k in result if k != "trace"]
    return f"keys={keys}" if keys else "no output"


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
    input_keys = [k for k in state if state[k] is not None]

    entry = AgentTraceEntry(
        agent_name=agent_name,
        timestamp=ts,
        duration_ms=duration_ms,
        input_summary=f"keys={input_keys}",
        output_summary=output_summary,
        status=status,
    )

    result.setdefault("trace", [])
    result["trace"].append(entry)
    return result
