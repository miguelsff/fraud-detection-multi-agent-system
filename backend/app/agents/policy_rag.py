"""Policy RAG Agent - matches transaction signals against fraud policies using LLM + RAG."""

import asyncio
from typing import Optional

from langchain_ollama import ChatOllama

from ..constants import AGENT_TIMEOUTS
from ..dependencies import get_llm
from ..models import (
    BehavioralSignals,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    Transaction,
    TransactionSignals,
)
from ..prompts.policy import POLICY_ANALYSIS_PROMPT
from ..rag.vector_store import query_policies
from ..utils.logger import get_logger
from ..utils.policy_utils import build_rag_query, build_signals_summary, parse_policy_matches
from ..utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("policy_rag")
async def policy_rag_agent(state: OrchestratorState) -> dict:
    """Policy RAG agent - matches transaction signals against fraud policies."""
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")

        query = build_rag_query(transaction, transaction_signals, behavioral_signals)
        logger.info("rag_query_built", query=query[:100])

        rag_results = query_policies(query, n_results=5)

        # Capture RAG query details
        rag_trace = {
            "rag_query": query,
            "rag_scores": {result["id"]: result["score"] for result in rag_results}
            if rag_results
            else {},
        }

        if not rag_results:
            logger.warning("no_policies_retrieved", query=query[:50])
            return {
                "policy_matches": PolicyMatchResult(matches=[], chunk_ids=[]),
                "_rag_trace": rag_trace,
            }

        llm = get_llm()
        policy_matches, llm_trace = await _call_llm_for_policy_analysis(
            llm,
            transaction,
            transaction_signals,
            behavioral_signals,
            rag_results,
        )

        chunk_ids = [result["id"] for result in rag_results]
        result = PolicyMatchResult(matches=policy_matches, chunk_ids=chunk_ids)

        logger.info(
            "policy_rag_completed", matches_count=len(policy_matches), chunks_used=len(chunk_ids)
        )
        return {"policy_matches": result, "_llm_trace": llm_trace, "_rag_trace": rag_trace}

    except Exception as e:
        logger.error("policy_rag_error", error=str(e), exc_info=True)
        return {
            "policy_matches": PolicyMatchResult(matches=[], chunk_ids=[]),
            "_error_trace": {"error_details": str(e)},
        }


async def _call_llm_for_policy_analysis(
    llm: ChatOllama,
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
    rag_results: list[dict],
) -> tuple[list[PolicyMatch], dict]:
    """Call LLM to analyze which policies apply.

    Returns:
        Tuple of (policy_matches, llm_trace_metadata)
    """
    signals_summary = build_signals_summary(transaction_signals, behavioral_signals)

    policy_chunks_text = "\n\n---\n\n".join(
        [f"**Chunk ID: {r['id']} (score: {r['score']:.2f})**\n{r['text']}" for r in rag_results]
    )

    prompt = POLICY_ANALYSIS_PROMPT.format(
        transaction_id=transaction.transaction_id,
        amount=transaction.amount,
        currency=transaction.currency,
        country=transaction.country,
        channel=transaction.channel,
        device_id=transaction.device_id,
        timestamp=transaction.timestamp.isoformat(),
        signals_summary=signals_summary,
        policy_chunks=policy_chunks_text,
    )

    # Initialize LLM trace metadata
    llm_trace = {
        "llm_prompt": prompt,
        "llm_model": llm.model,
        "llm_temperature": 0.0,
    }

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=AGENT_TIMEOUTS.llm_call)

        # Capture raw response
        llm_trace["llm_response_raw"] = response.content

        # Capture token usage if available
        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("usage", {})
            llm_trace["llm_tokens_used"] = usage.get("total_tokens")

        matches = parse_policy_matches(response.content)
        return matches, llm_trace

    except asyncio.TimeoutError:
        logger.error("llm_timeout", timeout_seconds=AGENT_TIMEOUTS.llm_call)
        llm_trace["llm_response_raw"] = f"TIMEOUT after {AGENT_TIMEOUTS.llm_call}s"
        return [], llm_trace
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        llm_trace["llm_response_raw"] = f"ERROR: {str(e)}"
        return [], llm_trace
