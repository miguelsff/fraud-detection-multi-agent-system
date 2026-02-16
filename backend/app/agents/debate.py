"""Adversarial Debate Agents - Pro-Fraud and Pro-Customer argumentation.

This module implements Phase 3 of the fraud detection pipeline:
- Pro-Fraud Agent: Argues WHY the transaction IS fraudulent (skeptical stance)
- Pro-Customer Agent: Argues WHY the transaction is LEGITIMATE (defender stance)

Both agents execute in parallel and provide balanced perspectives for the Decision Arbiter.
"""

from ..dependencies import get_llm
from ..models import OrchestratorState
from ..utils.logger import get_logger
from ..utils.timing import timed_agent
from .debate_utils import (
    call_debate_llm,
    generate_fallback_pro_customer,
    generate_fallback_pro_fraud,
)

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
# MAIN AGENT FUNCTIONS
# ============================================================================


@timed_agent("debate_pro_fraud")
async def debate_pro_fraud_agent(state: OrchestratorState) -> dict:
    """Pro-Fraud Debate Agent - argues WHY transaction IS fraudulent."""
    try:
        evidence = state.get("evidence")

        if not evidence:
            logger.warning("pro_fraud_no_evidence_found")
            return {
                "pro_fraud_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_fraud_confidence": 0.50,
                "pro_fraud_evidence": ["no_evidence"],
            }

        llm = get_llm()
        argument, confidence, evidence_cited = await call_debate_llm(llm, evidence, PRO_FRAUD_PROMPT)

        if argument and confidence is not None:
            logger.info("debate_pro_fraud_completed", confidence=confidence, evidence_count=len(evidence_cited))
            return {
                "pro_fraud_argument": argument,
                "pro_fraud_confidence": confidence,
                "pro_fraud_evidence": evidence_cited,
            }

        logger.warning("pro_fraud_llm_failed_using_fallback")
        return generate_fallback_pro_fraud(evidence)

    except Exception as e:
        logger.error("debate_pro_fraud_error", error=str(e), exc_info=True)
        return {
            "pro_fraud_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_fraud_confidence": 0.50,
            "pro_fraud_evidence": ["error_occurred"],
        }


@timed_agent("debate_pro_customer")
async def debate_pro_customer_agent(state: OrchestratorState) -> dict:
    """Pro-Customer Debate Agent - argues WHY transaction IS legitimate."""
    try:
        evidence = state.get("evidence")

        if not evidence:
            logger.warning("pro_customer_no_evidence_found")
            return {
                "pro_customer_argument": "No hay evidencia consolidada disponible para análisis.",
                "pro_customer_confidence": 0.50,
                "pro_customer_evidence": ["no_evidence"],
            }

        llm = get_llm()
        argument, confidence, evidence_cited = await call_debate_llm(llm, evidence, PRO_CUSTOMER_PROMPT)

        if argument and confidence is not None:
            logger.info("debate_pro_customer_completed", confidence=confidence, evidence_count=len(evidence_cited))
            return {
                "pro_customer_argument": argument,
                "pro_customer_confidence": confidence,
                "pro_customer_evidence": evidence_cited,
            }

        logger.warning("pro_customer_llm_failed_using_fallback")
        return generate_fallback_pro_customer(evidence)

    except Exception as e:
        logger.error("debate_pro_customer_error", error=str(e), exc_info=True)
        return {
            "pro_customer_argument": "Error en generación de argumento. Análisis manual requerido.",
            "pro_customer_confidence": 0.50,
            "pro_customer_evidence": ["error_occurred"],
        }
