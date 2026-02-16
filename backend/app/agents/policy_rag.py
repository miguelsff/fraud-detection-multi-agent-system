"""Policy RAG Agent - matches transaction signals against fraud policies using LLM + RAG."""

import asyncio
from typing import Optional

from langchain_ollama import ChatOllama

from ..dependencies import get_llm
from ..models import (
    BehavioralSignals,
    OrchestratorState,
    PolicyMatch,
    PolicyMatchResult,
    Transaction,
    TransactionSignals,
)
from ..rag.vector_store import query_policies
from ..utils.logger import get_logger
from ..utils.timing import timed_agent
from .constants import AGENT_TIMEOUTS
from .policy_utils import build_rag_query, build_signals_summary, parse_policy_matches

logger = get_logger(__name__)

POLICY_ANALYSIS_PROMPT = """Eres un experto en detección de fraude financiero. Analiza la siguiente transacción y las políticas de fraude relevantes para determinar qué políticas aplican.

**TRANSACCIÓN:**
- ID: {transaction_id}
- Monto: {amount} {currency}
- País: {country}
- Canal: {channel}
- Dispositivo: {device_id}
- Timestamp: {timestamp}

**SEÑALES DETECTADAS:**
{signals_summary}

**POLÍTICAS RELEVANTES (recuperadas de la base de conocimiento):**
{policy_chunks}

**INSTRUCCIONES:**
1. Evalúa qué políticas aplican a esta transacción específica
2. Para cada política aplicable, asigna un puntaje de relevancia de 0.0 a 1.0
3. Proporciona una breve descripción de por qué aplica

**FORMATO DE SALIDA (JSON estricto):**
{{
  "matches": [
    {{
      "policy_id": "FP-01",
      "description": "Transacción nocturna con monto 3.6x superior al promedio",
      "relevance_score": 0.92
    }}
  ]
}}

**IMPORTANTE:**
- Solo incluye políticas con relevance_score >= 0.5
- El relevance_score debe estar entre 0.0 y 1.0
- Responde SOLO con el JSON, sin texto adicional
"""


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

        if not rag_results:
            logger.warning("no_policies_retrieved", query=query[:50])
            return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}

        llm = get_llm()
        policy_matches = await _call_llm_for_policy_analysis(
            llm, transaction, transaction_signals, behavioral_signals, rag_results,
        )

        chunk_ids = [result["id"] for result in rag_results]
        result = PolicyMatchResult(matches=policy_matches, chunk_ids=chunk_ids)

        logger.info("policy_rag_completed", matches_count=len(policy_matches), chunks_used=len(chunk_ids))
        return {"policy_matches": result}

    except Exception as e:
        logger.error("policy_rag_error", error=str(e), exc_info=True)
        return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}


async def _call_llm_for_policy_analysis(
    llm: ChatOllama,
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
    rag_results: list[dict],
) -> list[PolicyMatch]:
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

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=AGENT_TIMEOUTS.llm_call)
        return parse_policy_matches(response.content)
    except asyncio.TimeoutError:
        logger.error("llm_timeout", timeout_seconds=AGENT_TIMEOUTS.llm_call)
        return []
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        return []
