"""Prompts for Policy RAG Agent."""

POLICY_ANALYSIS_PROMPT = """INSTRUCCIÓN CRÍTICA: Debes responder COMPLETAMENTE en español. Todo el texto generado debe estar en español, sin excepciones.

Eres un experto en detección de fraude financiero. Analiza la siguiente transacción y las políticas de fraude relevantes para determinar qué políticas aplican.

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
