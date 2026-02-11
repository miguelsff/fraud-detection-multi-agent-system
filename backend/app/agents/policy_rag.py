"""Policy RAG Agent - matches transaction signals against fraud policies using LLM + RAG."""

import asyncio
import json
import re
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
    """Policy RAG agent - matches transaction signals against fraud policies.

    Uses ChromaDB for semantic search over policy documents and LLM for
    relevance scoring and interpretation.

    Args:
        state: Orchestrator state with transaction and signals

    Returns:
        Dict with policy_matches field containing PolicyMatchResult
    """
    try:
        transaction = state["transaction"]
        transaction_signals = state.get("transaction_signals")
        behavioral_signals = state.get("behavioral_signals")

        # 1. Build query from signals
        query = _build_query_from_signals(
            transaction,
            transaction_signals,
            behavioral_signals,
        )
        logger.info("rag_query_built", query=query[:100])

        # 2. Query ChromaDB for relevant policies
        rag_results = query_policies(query, n_results=5)

        if not rag_results:
            logger.warning("no_policies_retrieved", query=query[:50])
            return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}

        # 3. Call LLM for policy analysis
        llm = get_llm()
        policy_matches = await _call_llm_for_policy_analysis(
            llm,
            transaction,
            transaction_signals,
            behavioral_signals,
            rag_results,
        )

        # 4. Extract chunk IDs
        chunk_ids = [result["id"] for result in rag_results]

        result = PolicyMatchResult(
            matches=policy_matches,
            chunk_ids=chunk_ids,
        )

        logger.info(
            "policy_rag_completed",
            matches_count=len(policy_matches),
            chunks_used=len(chunk_ids),
        )

        return {"policy_matches": result}

    except Exception as e:
        logger.error("policy_rag_error", error=str(e), exc_info=True)
        # Fallback to empty result
        return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}


def _build_query_from_signals(
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
) -> str:
    """Build natural language query for ChromaDB from detected signals.

    Strategy:
    1. Start with base transaction attributes
    2. Add contextual flags from transaction_signals
    3. Add behavioral anomalies from behavioral_signals
    4. Construct Spanish query for better policy matching

    Args:
        transaction: Transaction object with base information
        transaction_signals: Optional contextual signals
        behavioral_signals: Optional behavioral deviation signals

    Returns:
        Natural language query string in Spanish
    """
    query_parts = []

    # Base transaction info
    query_parts.append(f"transacción de {transaction.amount} {transaction.currency}")

    if transaction_signals:
        # Amount ratio
        if transaction_signals.amount_ratio > 3.0:
            query_parts.append("monto muy superior al promedio")
        elif transaction_signals.amount_ratio > 2.0:
            query_parts.append("monto elevado")

        # Time-based
        if transaction_signals.is_off_hours:
            query_parts.append("fuera del horario habitual")

        # Location
        if transaction_signals.is_foreign:
            query_parts.append(f"desde país extranjero {transaction.country}")

        # Device
        if transaction_signals.is_unknown_device:
            query_parts.append("dispositivo no reconocido")

        # Channel risk
        if transaction_signals.channel_risk == "high":
            query_parts.append("canal de alto riesgo")

    if behavioral_signals:
        # Deviation score
        if behavioral_signals.deviation_score > 0.7:
            query_parts.append("comportamiento muy anómalo")
        elif behavioral_signals.deviation_score > 0.5:
            query_parts.append("comportamiento inusual")

        # Velocity
        if behavioral_signals.velocity_alert:
            query_parts.append("alerta de velocidad de transacciones")

        # Specific anomalies
        for anomaly in behavioral_signals.anomalies[:3]:  # Top 3
            query_parts.append(anomaly.replace("_", " "))

    # Fallback if no signals (use base transaction info)
    if len(query_parts) == 1:  # Only base transaction
        query_parts.append(f"canal {transaction.channel}")
        query_parts.append(f"país {transaction.country}")

    return " ".join(query_parts)


async def _call_llm_for_policy_analysis(
    llm: ChatOllama,
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
    rag_results: list[dict],
) -> list[PolicyMatch]:
    """Call LLM to analyze which policies apply.

    Args:
        llm: ChatOllama instance
        transaction: Transaction object
        transaction_signals: Optional contextual signals
        behavioral_signals: Optional behavioral signals
        rag_results: Results from ChromaDB query

    Returns:
        List of PolicyMatch objects

    Note:
        - Includes 30-second timeout for LLM call
        - Handles timeout gracefully by returning empty list
    """
    # Build signals summary
    signals_parts = []
    if transaction_signals:
        signals_parts.append(
            f"- Ratio de monto: {transaction_signals.amount_ratio:.2f}x"
        )
        signals_parts.append(f"- Fuera de horario: {transaction_signals.is_off_hours}")
        signals_parts.append(f"- País extranjero: {transaction_signals.is_foreign}")
        signals_parts.append(
            f"- Dispositivo desconocido: {transaction_signals.is_unknown_device}"
        )
        signals_parts.append(
            f"- Riesgo del canal: {transaction_signals.channel_risk}"
        )
        if transaction_signals.flags:
            signals_parts.append(
                f"- Banderas: {', '.join(transaction_signals.flags[:5])}"
            )

    if behavioral_signals:
        signals_parts.append(
            f"- Puntaje de desviación: {behavioral_signals.deviation_score:.2f}"
        )
        signals_parts.append(
            f"- Alerta de velocidad: {behavioral_signals.velocity_alert}"
        )
        if behavioral_signals.anomalies:
            signals_parts.append(
                f"- Anomalías: {', '.join(behavioral_signals.anomalies[:3])}"
            )

    signals_summary = (
        "\n".join(signals_parts) if signals_parts else "No hay señales disponibles"
    )

    # Build policy chunks text
    policy_chunks_text = "\n\n---\n\n".join(
        [
            f"**Chunk ID: {r['id']} (score: {r['score']:.2f})**\n{r['text']}"
            for r in rag_results
        ]
    )

    # Format prompt
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
        # Call LLM with timeout
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=30.0)
        response_text = response.content

        # Parse response
        return _parse_llm_response(response_text)

    except asyncio.TimeoutError:
        logger.error("llm_timeout", timeout_seconds=30)
        return []
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        return []


def _parse_llm_response(response_text: str) -> list[PolicyMatch]:
    """Parse LLM response to extract PolicyMatch objects.

    Strategy:
    1. Try JSON parsing first (look for JSON in code blocks or raw)
    2. If fails, use regex fallback
    3. Validate relevance_score is 0.0-1.0

    Args:
        response_text: Raw text response from LLM

    Returns:
        List of PolicyMatch objects

    Note:
        - Clamps scores to [0.0, 1.0] range
        - Filters matches with score < 0.5
        - Logs which parsing method succeeded
    """
    matches = []

    # Try JSON parsing
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(
            r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*"matches".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        for match_data in data.get("matches", []):
            # Clamp relevance_score to 0.0-1.0
            score = max(0.0, min(1.0, float(match_data["relevance_score"])))

            # Only include matches with score >= 0.5
            if score >= 0.5:
                matches.append(
                    PolicyMatch(
                        policy_id=match_data["policy_id"],
                        description=match_data["description"],
                        relevance_score=score,
                    )
                )

        logger.info("llm_response_parsed_json", count=len(matches))

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("json_parse_failed", error=str(e), attempting_regex=True)

        # Regex fallback
        # Pattern: FP-XX ... score: 0.XX or relevance: 0.XX
        pattern = r"(FP-\d{2}).*?(?:score|relevance)[:\s]+(0\.\d+|1\.0)"
        regex_matches = re.findall(pattern, response_text, re.IGNORECASE)

        for policy_id, score_str in regex_matches:
            score = max(0.0, min(1.0, float(score_str)))
            if score >= 0.5:  # Only include relevant ones
                matches.append(
                    PolicyMatch(
                        policy_id=policy_id,
                        description=f"Política {policy_id} aplicable (extracción por regex)",
                        relevance_score=score,
                    )
                )

        logger.info("llm_response_parsed_regex", count=len(matches))

    return matches
