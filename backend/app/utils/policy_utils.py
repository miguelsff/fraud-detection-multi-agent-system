"""Helper functions extracted from policy_rag.py.

Provides query building, signals summary construction,
and policy match response parsing.
"""

import re
from typing import Optional

from app.models import BehavioralSignals, PolicyMatch, Transaction, TransactionSignals
from app.utils.llm_utils import clamp_float, parse_json_response
from app.utils.logger import get_logger

from ..constants import AMOUNT_THRESHOLDS

logger = get_logger(__name__)


def build_rag_query(
    transaction: Transaction,
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
) -> str:
    """Build natural language query for ChromaDB from detected signals.

    Constructs Spanish query for better policy matching.
    """
    query_parts = [f"transacción de {transaction.amount} {transaction.currency}"]

    if transaction_signals:
        if transaction_signals.amount_ratio > AMOUNT_THRESHOLDS.high_ratio:
            query_parts.append("monto muy superior al promedio")
        elif transaction_signals.amount_ratio > AMOUNT_THRESHOLDS.elevated_ratio:
            query_parts.append("monto elevado")

        if transaction_signals.is_foreign:
            query_parts.append(f"desde país extranjero {transaction.country}")
        if transaction_signals.is_unknown_device:
            query_parts.append("dispositivo no reconocido")
        if transaction_signals.channel_risk == "high":
            query_parts.append("canal de alto riesgo")

    if behavioral_signals and "off_hours_transaction" in behavioral_signals.anomalies:
        query_parts.append("fuera del horario habitual del cliente")

    if behavioral_signals:
        if behavioral_signals.deviation_score > 0.7:
            query_parts.append("comportamiento muy anómalo")
        elif behavioral_signals.deviation_score > 0.5:
            query_parts.append("comportamiento inusual")

        if behavioral_signals.velocity_alert:
            query_parts.append("alerta de velocidad de transacciones")

        for anomaly in behavioral_signals.anomalies[:3]:
            query_parts.append(anomaly.replace("_", " "))

    if len(query_parts) == 1:
        query_parts.append(f"canal {transaction.channel}")
        query_parts.append(f"país {transaction.country}")

    return " ".join(query_parts)


def build_signals_summary(
    transaction_signals: Optional[TransactionSignals],
    behavioral_signals: Optional[BehavioralSignals],
) -> str:
    """Build signals summary text for LLM prompt."""
    signals_parts = []

    if transaction_signals:
        signals_parts.append(f"- Ratio de monto: {transaction_signals.amount_ratio:.2f}x")
        signals_parts.append(f"- País extranjero: {transaction_signals.is_foreign}")
        signals_parts.append(f"- Dispositivo desconocido: {transaction_signals.is_unknown_device}")
        signals_parts.append(f"- Riesgo del canal: {transaction_signals.channel_risk}")
        if transaction_signals.flags:
            signals_parts.append(f"- Banderas: {', '.join(transaction_signals.flags[:5])}")

    if behavioral_signals:
        is_off_hours = "off_hours_transaction" in behavioral_signals.anomalies
        signals_parts.append(f"- Fuera de horario: {is_off_hours}")
        signals_parts.append(f"- Puntaje de desviación: {behavioral_signals.deviation_score:.2f}")
        signals_parts.append(f"- Alerta de velocidad: {behavioral_signals.velocity_alert}")
        if behavioral_signals.anomalies:
            signals_parts.append(f"- Anomalías: {', '.join(behavioral_signals.anomalies[:3])}")

    return "\n".join(signals_parts) if signals_parts else "No hay señales disponibles"


def parse_policy_matches(response_text: str) -> list[PolicyMatch]:
    """Parse LLM response to extract PolicyMatch objects.

    Two-stage parsing: JSON first, regex fallback.
    Filters matches with score < 0.5.
    """
    matches = []

    # Stage 1: JSON parsing
    data = parse_json_response(response_text, "matches", "policy_rag")
    if data:
        try:
            for match_data in data.get("matches", []):
                score = clamp_float(float(match_data["relevance_score"]))
                if score >= 0.5:
                    matches.append(
                        PolicyMatch(
                            policy_id=match_data["policy_id"],
                            description=match_data["description"],
                            relevance_score=score,
                        )
                    )
            logger.info("llm_response_parsed_json", count=len(matches))
            return matches
        except (KeyError, ValueError):
            pass

    # Stage 2: Regex fallback
    pattern = r"(FP-\d{2}).*?(?:score|relevance)[:\s]+(0\.\d+|1\.0)"
    regex_matches = re.findall(pattern, response_text, re.IGNORECASE)

    for policy_id, score_str in regex_matches:
        score = clamp_float(float(score_str))
        if score >= 0.5:
            matches.append(
                PolicyMatch(
                    policy_id=policy_id,
                    description=f"Política {policy_id} aplicable (extracción por regex)",
                    relevance_score=score,
                )
            )

    logger.info("llm_response_parsed_regex", count=len(matches))
    return matches
