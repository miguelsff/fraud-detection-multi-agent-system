"""Policy RAG Agent - matches transaction signals against fraud policies using LLM + RAG."""

from langchain_core.runnables import RunnableConfig

from app.domain.models import (
    BehavioralSignals,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    Transaction,
    TransactionSignals,
)
from app.application.ports.llm import LLMPort
from app.application.ports.vector_store import VectorStorePort
from app.application.prompts.policy import POLICY_ANALYSIS_PROMPT
from app.utils.logger import get_logger
from app.utils.policy_utils import build_rag_query, build_signals_summary, parse_policy_matches
from app.utils.timing import timed_agent

logger = get_logger(__name__)


@timed_agent("policy_rag")
async def policy_rag_agent(state: OrchestratorState, config: RunnableConfig = None) -> dict:
    """Policy RAG agent - matches transaction signals against fraud policies.

    Uses llm_port and vector_store from config["configurable"] instead of direct imports.
    """
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")

        # Get ports from config
        configurable = (config or {}).get("configurable", {})
        llm_port: LLMPort = configurable.get("llm_port")
        vector_store: VectorStorePort = configurable.get("vector_store")

        query = build_rag_query(transaction, transaction_signals, behavioral_signals)
        logger.info("rag_query_built", query=query[:100])

        if not vector_store:
            logger.warning("policy_rag_no_vector_store_in_config")
            return {
                "policy_matches": PolicyMatchResult(matches=[], chunk_ids=[]),
                "_error_trace": {"fallback_reason": "no_vector_store_in_config"},
            }

        rag_results = vector_store.query(query, n_results=5)

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

        policy_matches, llm_trace = await _call_llm_for_policy_analysis(
            llm_port,
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
    llm_port: LLMPort | None,
    transaction: Transaction,
    transaction_signals: TransactionSignals | None,
    behavioral_signals: BehavioralSignals | None,
    rag_results: list[dict],
) -> tuple[list[PolicyMatch], dict]:
    """Call LLM to analyze which policies apply."""
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

    if not llm_port:
        logger.warning("policy_rag_no_llm_port_in_config")
        return [], {"fallback_reason": "no_llm_port_in_config"}

    content, llm_trace = await llm_port.invoke(prompt, agent_name="policy_rag")

    matches = parse_policy_matches(content) if content else []
    return matches, llm_trace
