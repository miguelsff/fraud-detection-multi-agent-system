"""Adversarial Debate Agents - Pro-Fraud and Pro-Customer argumentation.

This module implements Phase 3 of the fraud detection pipeline:
- Pro-Fraud Agent: Argues WHY the transaction IS fraudulent (skeptical stance)
- Pro-Customer Agent: Argues WHY the transaction is LEGITIMATE (defender stance)

Both agents execute in parallel and provide balanced perspectives for the Decision Arbiter.
"""

import asyncio
import json
import re
from typing import Optional

from langchain_ollama import ChatOllama

from ..dependencies import get_llm
from ..models import AggregatedEvidence, OrchestratorState
from ..utils.logger import get_logger
from ..utils.timing import timed_agent

logger = get_logger(__name__)

# ============================================================================
# PROMPT TEMPLATES (Spanish)
# ============================================================================

PRO_FRAUD_PROMPT = """Eres un especialista en detección de fraude financiero con postura ESCÉPTICA. Tu rol es argumentar POR QUÉ esta transacción PODRÍA SER FRAUDULENTA.

**EVIDENCIA CONSOLIDADA:**
- Puntaje de riesgo compuesto: {composite_risk_score}/100
- Categoría de riesgo: {risk_category}
- Señales detectadas: {all_signals}
- Citaciones: {all_citations}

**TU TAREA:**
Asume una postura adversarial ESCÉPTICA y argumenta por qué esta transacción podría ser fraude.

**INSTRUCCIONES:**
1. Enfócate en las señales de riesgo más preocupantes
2. Conecta múltiples señales para construir un caso coherente
3. Asigna un nivel de confianza (0.0-1.0) a tu argumento
4. Cita las evidencias específicas que respaldan tu posición

**GUÍA DE CONFIANZA:**
- 0.8-1.0: Evidencia muy fuerte de fraude (múltiples señales críticas)
- 0.6-0.8: Evidencia considerable (señales de alto riesgo combinadas)
- 0.4-0.6: Evidencia moderada (algunas banderas rojas)
- 0.2-0.4: Evidencia débil (señales menores)
- 0.0-0.2: Evidencia mínima (muy bajo riesgo)

**FORMATO DE SALIDA (JSON estricto):**
{{
  "argument": "La transacción presenta múltiples señales de fraude: monto 3.6x superior al promedio del cliente, ejecutada a las 03:15 AM (horario de alto riesgo según política FP-01), desde dispositivo no reconocido. Esta combinación es consistente con patrones de fraude de account takeover.",
  "confidence": 0.78,
  "evidence_cited": ["amount_ratio_3.6x", "off_hours_03:15", "unknown_device", "policy_FP-01"]
}}

**IMPORTANTE:**
- Responde SOLO con el JSON, sin texto adicional
- El argumento debe ser 2-4 oraciones
- La confianza debe estar entre 0.0 y 1.0
- Cita 2-5 evidencias específicas
"""

PRO_CUSTOMER_PROMPT = """Eres un especialista en protección al consumidor financiero con postura DEFENSORA. Tu rol es argumentar POR QUÉ esta transacción PODRÍA SER LEGÍTIMA.

**EVIDENCIA CONSOLIDADA:**
- Puntaje de riesgo compuesto: {composite_risk_score}/100
- Categoría de riesgo: {risk_category}
- Señales detectadas: {all_signals}
- Citaciones: {all_citations}

**TU TAREA:**
Asume una postura adversarial DEFENSORA y argumenta por qué esta transacción podría ser legítima.

**INSTRUCCIONES:**
1. Busca explicaciones legítimas para las señales de riesgo
2. Considera contextos válidos que justifiquen el comportamiento
3. Asigna un nivel de confianza (0.0-1.0) a tu argumento de legitimidad
4. Cita las evidencias que respaldan la interpretación legítima

**GUÍA DE CONFIANZA (perspectiva de legitimidad):**
- 0.8-1.0: Alta probabilidad de ser legítimo (bajo riesgo real)
- 0.6-0.8: Probabilidad considerable de legitimidad
- 0.4-0.6: Legitimidad moderada (riesgo balanceado)
- 0.2-0.4: Legitimidad cuestionable
- 0.0-0.2: Baja probabilidad de legitimidad (alto riesgo real)

**FORMATO DE SALIDA (JSON estricto):**
{{
  "argument": "Aunque el monto es elevado, el cliente tiene historial de compras similares en este merchant. El dispositivo es conocido (D-01) y el país coincide con su perfil habitual (PE). El horario nocturno podría explicarse por el huso horario del cliente o trabajo de turno tarde.",
  "confidence": 0.55,
  "evidence_cited": ["known_device_D-01", "same_country_PE", "merchant_history", "possible_shift_work"]
}}

**IMPORTANTE:**
- Responde SOLO con el JSON, sin texto adicional
- El argumento debe ser 2-4 oraciones
- La confianza debe estar entre 0.0 y 1.0
- Cita 2-5 evidencias específicas
- Busca interpretaciones legítimas incluso en transacciones de alto riesgo
"""

# ============================================================================
# PARSING HELPERS
# ============================================================================


def _parse_debate_response(response_text: str) -> tuple[Optional[str], Optional[float], list[str]]:
    """Parse LLM response to extract argument, confidence, and evidence.

    Two-stage parsing strategy:
    1. JSON parsing: Look for JSON in markdown code blocks or raw JSON
    2. Regex fallback: Extract fields via regex if JSON parsing fails

    Args:
        response_text: Raw text response from LLM

    Returns:
        Tuple of (argument, confidence, evidence_cited)
        Returns (None, None, []) if parsing fails completely

    Note:
        - Clamps confidence to [0.0, 1.0]
        - Logs which parsing method succeeded
    """
    # ========== STAGE 1: JSON PARSING ==========
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*"argument".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        # Extract fields
        argument = data.get("argument")
        confidence = data.get("confidence")
        evidence_cited = data.get("evidence_cited", [])

        # Validate and normalize
        if argument and confidence is not None:
            confidence = max(0.0, min(1.0, float(confidence)))  # Clamp to [0.0, 1.0]
            if not isinstance(evidence_cited, list):
                evidence_cited = []

            logger.info("debate_response_parsed_json")
            return argument, confidence, evidence_cited

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("json_parse_failed_debate", error=str(e), attempting_regex=True)

    # ========== STAGE 2: REGEX FALLBACK ==========
    try:
        # Extract confidence: "confidence": 0.XX or "confidence": 1.0
        confidence_match = re.search(
            r'"?confidence"?\s*:\s*(0\.\d+|1\.0|0|1)',
            response_text,
            re.IGNORECASE,
        )
        confidence = None
        if confidence_match:
            confidence = float(confidence_match.group(1))
            confidence = max(0.0, min(1.0, confidence))

        # Extract argument: "argument": "..."
        argument_match = re.search(
            r'"?argument"?\s*:\s*"([^"]+)"',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        argument = argument_match.group(1) if argument_match else None

        # Extract evidence_cited: ["item1", "item2", ...]
        evidence_match = re.search(
            r'"?evidence_cited"?\s*:\s*\[(.*?)\]',
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        evidence_cited = []
        if evidence_match:
            # Extract quoted strings from the list
            evidence_items = re.findall(r'"([^"]+)"', evidence_match.group(1))
            evidence_cited = evidence_items

        if argument and confidence is not None:
            logger.info("debate_response_parsed_regex", confidence=confidence)
            return argument, confidence, evidence_cited

    except Exception as e:
        logger.error("regex_parse_failed_debate", error=str(e))

    # ========== PARSING FAILED ==========
    logger.error("debate_response_parse_failed_completely")
    return None, None, []


# ============================================================================
# LLM CALL HELPER
# ============================================================================


async def _call_llm_for_debate(
    llm: ChatOllama,
    evidence: AggregatedEvidence,
    prompt_template: str,
) -> tuple[Optional[str], Optional[float], list[str]]:
    """Call LLM for debate argument generation.

    Args:
        llm: ChatOllama instance
        evidence: AggregatedEvidence from Phase 2
        prompt_template: Prompt template (PRO_FRAUD_PROMPT or PRO_CUSTOMER_PROMPT)

    Returns:
        Tuple of (argument, confidence, evidence_cited)
        Returns (None, None, []) if LLM call fails

    Note:
        - Includes 30-second timeout
        - Delegates parsing to _parse_debate_response()
    """
    # Format prompt with evidence data
    prompt = prompt_template.format(
        composite_risk_score=evidence.composite_risk_score,
        risk_category=evidence.risk_category,
        all_signals=", ".join(evidence.all_signals) if evidence.all_signals else "ninguna",
        all_citations="\n- ".join(evidence.all_citations) if evidence.all_citations else "ninguna",
    )

    try:
        # Call LLM with timeout
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=30.0)
        response_text = response.content

        # Parse response
        return _parse_debate_response(response_text)

    except asyncio.TimeoutError:
        logger.error("llm_timeout_debate", timeout_seconds=30)
        return None, None, []
    except Exception as e:
        logger.error("llm_call_failed_debate", error=str(e))
        return None, None, []


# ============================================================================
# DETERMINISTIC FALLBACKS
# ============================================================================


def _generate_fallback_pro_fraud(evidence: AggregatedEvidence) -> dict:
    """Generate deterministic pro-fraud argument when LLM fails.

    Maps risk_category to confidence and argument template.
    Higher risk → higher fraud confidence.

    Args:
        evidence: AggregatedEvidence from Phase 2

    Returns:
        Dict with pro_fraud_argument, pro_fraud_confidence, pro_fraud_evidence
    """
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    # Risk category → (confidence, argument template)
    risk_mappings = {
        "critical": (
            0.90,
            f"La transacción presenta riesgo CRÍTICO (puntaje {composite_score}/100). "
            "Múltiples señales de alto riesgo sugieren alta probabilidad de fraude. "
            "Se recomienda bloqueo inmediato.",
        ),
        "high": (
            0.75,
            f"La transacción presenta riesgo ALTO (puntaje {composite_score}/100). "
            "Señales combinadas indican probabilidad considerable de fraude. "
            "Verificación adicional requerida.",
        ),
        "medium": (
            0.55,
            f"La transacción presenta riesgo MEDIO (puntaje {composite_score}/100). "
            "Algunas señales de riesgo presentes. "
            "Monitoreo recomendado.",
        ),
        "low": (
            0.30,
            f"La transacción presenta riesgo BAJO (puntaje {composite_score}/100). "
            "Señales de riesgo mínimas. "
            "Probabilidad de fraude reducida.",
        ),
    }

    confidence, argument = risk_mappings.get(
        risk_category,
        (0.50, "Nivel de riesgo no clasificado. Análisis adicional requerido."),
    )

    # Use top 3 signals as evidence
    evidence_cited = evidence.all_signals[:3] if evidence.all_signals else ["risk_score_elevated"]

    logger.info(
        "pro_fraud_fallback_generated",
        risk_category=risk_category,
        confidence=confidence,
    )

    return {
        "pro_fraud_argument": argument,
        "pro_fraud_confidence": confidence,
        "pro_fraud_evidence": evidence_cited,
    }


def _generate_fallback_pro_customer(evidence: AggregatedEvidence) -> dict:
    """Generate deterministic pro-customer argument when LLM fails.

    Maps risk_category to confidence and argument template.
    Lower risk → higher legitimacy confidence (inverse of pro-fraud).

    Args:
        evidence: AggregatedEvidence from Phase 2

    Returns:
        Dict with pro_customer_argument, pro_customer_confidence, pro_customer_evidence
    """
    risk_category = evidence.risk_category
    composite_score = evidence.composite_risk_score

    # Risk category → (legitimacy confidence, argument template)
    # NOTE: Inverse mapping - lower risk = higher legitimacy confidence
    risk_mappings = {
        "critical": (
            0.20,
            f"Aunque el puntaje de riesgo es crítico ({composite_score}/100), "
            "podría existir un contexto legítimo no capturado por las señales automáticas. "
            "Se requiere revisión humana para confirmar.",
        ),
        "high": (
            0.35,
            f"El puntaje de riesgo es alto ({composite_score}/100), "
            "pero las señales podrían tener explicaciones legítimas. "
            "El contexto del cliente debe considerarse antes de bloquear.",
        ),
        "medium": (
            0.60,
            f"El puntaje de riesgo es medio ({composite_score}/100). "
            "Las señales detectadas podrían corresponder a comportamiento legítimo atípico. "
            "Probabilidad razonable de transacción válida.",
        ),
        "low": (
            0.85,
            f"El puntaje de riesgo es bajo ({composite_score}/100). "
            "Las señales de fraude son mínimas. "
            "Alta probabilidad de transacción legítima.",
        ),
    }

    confidence, argument = risk_mappings.get(
        risk_category,
        (0.50, "Nivel de riesgo no clasificado. Revisión recomendada."),
    )

    # Use generic legitimate context evidence
    evidence_cited = ["possible_legitimate_context", "customer_history_unknown"]
    if evidence.all_signals:
        # Add first signal as something to potentially explain
        evidence_cited.append(f"review_needed_{evidence.all_signals[0]}")

    logger.info(
        "pro_customer_fallback_generated",
        risk_category=risk_category,
        confidence=confidence,
    )

    return {
        "pro_customer_argument": argument,
        "pro_customer_confidence": confidence,
        "pro_customer_evidence": evidence_cited,
    }


# ============================================================================
# MAIN AGENT FUNCTIONS
# ============================================================================


@timed_agent("debate_pro_fraud")
async def debate_pro_fraud_agent(state: OrchestratorState) -> dict:
    """Pro-Fraud Debate Agent - argues WHY transaction IS fraudulent.

    Reads AggregatedEvidence and generates skeptical argument emphasizing
    fraud risk signals. Executes in parallel with pro_customer agent.

    Args:
        state: Orchestrator state with evidence field

    Returns:
        Dict with partial state update:
        - pro_fraud_argument: str
        - pro_fraud_confidence: float
        - pro_fraud_evidence: list[str]

    Note:
        - Uses LLM for nuanced argumentation
        - Falls back to deterministic argument on LLM failure
        - Never crashes - always returns valid output
    """
    try:
        # Extract evidence from state
        evidence = state.get("evidence")

        # Validate evidence exists
        if not evidence:
            logger.warning("pro_fraud_no_evidence_found")
            return {
                "pro_fraud_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_fraud_confidence": 0.50,
                "pro_fraud_evidence": ["no_evidence"],
            }

        # Get LLM instance
        llm = get_llm()

        # Call LLM for debate argument
        argument, confidence, evidence_cited = await _call_llm_for_debate(
            llm,
            evidence,
            PRO_FRAUD_PROMPT,
        )

        # If LLM succeeded, return LLM-generated argument
        if argument and confidence is not None:
            logger.info(
                "debate_pro_fraud_completed",
                confidence=confidence,
                evidence_count=len(evidence_cited),
            )
            return {
                "pro_fraud_argument": argument,
                "pro_fraud_confidence": confidence,
                "pro_fraud_evidence": evidence_cited,
            }

        # LLM failed - use deterministic fallback
        logger.warning("pro_fraud_llm_failed_using_fallback")
        return _generate_fallback_pro_fraud(evidence)

    except Exception as e:
        logger.error("debate_pro_fraud_error", error=str(e), exc_info=True)

        # Exception fallback - return minimal safe values
        return {
            "pro_fraud_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_fraud_confidence": 0.50,
            "pro_fraud_evidence": ["error_occurred"],
        }


@timed_agent("debate_pro_customer")
async def debate_pro_customer_agent(state: OrchestratorState) -> dict:
    """Pro-Customer Debate Agent - argues WHY transaction IS legitimate.

    Reads AggregatedEvidence and generates defensive argument emphasizing
    legitimate explanations. Executes in parallel with pro_fraud agent.

    Args:
        state: Orchestrator state with evidence field

    Returns:
        Dict with partial state update:
        - pro_customer_argument: str
        - pro_customer_confidence: float
        - pro_customer_evidence: list[str]

    Note:
        - Uses LLM for nuanced argumentation
        - Falls back to deterministic argument on LLM failure
        - Never crashes - always returns valid output
    """
    try:
        # Extract evidence from state
        evidence = state.get("evidence")

        # Validate evidence exists
        if not evidence:
            logger.warning("pro_customer_no_evidence_found")
            return {
                "pro_customer_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_customer_confidence": 0.50,
                "pro_customer_evidence": ["no_evidence"],
            }

        # Get LLM instance
        llm = get_llm()

        # Call LLM for debate argument
        argument, confidence, evidence_cited = await _call_llm_for_debate(
            llm,
            evidence,
            PRO_CUSTOMER_PROMPT,
        )

        # If LLM succeeded, return LLM-generated argument
        if argument and confidence is not None:
            logger.info(
                "debate_pro_customer_completed",
                confidence=confidence,
                evidence_count=len(evidence_cited),
            )
            return {
                "pro_customer_argument": argument,
                "pro_customer_confidence": confidence,
                "pro_customer_evidence": evidence_cited,
            }

        # LLM failed - use deterministic fallback
        logger.warning("pro_customer_llm_failed_using_fallback")
        return _generate_fallback_pro_customer(evidence)

    except Exception as e:
        logger.error("debate_pro_customer_error", error=str(e), exc_info=True)

        # Exception fallback - return minimal safe values
        return {
            "pro_customer_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_customer_confidence": 0.50,
            "pro_customer_evidence": ["error_occurred"],
        }
