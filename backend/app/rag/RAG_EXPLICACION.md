# RAG en el Sistema de Detección de Fraude

## 1. Visión General

**RAG** (Retrieval-Augmented Generation) combina búsqueda vectorial con generación LLM. En lugar de que el modelo "memorice" las políticas de fraude, las **recuperamos dinámicamente** desde una base de datos vectorial (ChromaDB) y las inyectamos en el prompt. Esto permite actualizar políticas sin reentrenar el modelo.

### Flujo completo

```
Políticas (.md)           ← 6 archivos en backend/policies/
       │
       ▼
  Chunking por sección    ← _split_markdown_sections()
       │
       ▼
  Vectorización            ← ChromaDB embebe automáticamente con all-MiniLM-L6-v2
       │
       ▼
  ChromaDB persistente     ← backend/data/chroma/
       │
       │  ── En tiempo de análisis ──
       │
       ▼
  Construcción del query   ← build_rag_query() en policy_utils.py
       │
       ▼
  Búsqueda por similitud   ← query_policies() → top-5 chunks
       │
       ▼
  Inyección en prompt LLM  ← POLICY_ANALYSIS_PROMPT + chunks + señales
       │
       ▼
  Parseo de respuesta       ← JSON → regex fallback → PolicyMatchResult
       │
       ▼
  PolicyMatchResult         ← matches[] + chunk_ids[] → al orquestador
```

---

## 2. Fase 1: Ingesta de Políticas

### Fuente de datos

6 archivos markdown individuales en `backend/policies/`:

| Archivo | Política |
|---|---|
| `FP-01.md` | Política de Montos Inusuales |
| `FP-02.md` | Política de Transacciones Internacionales |
| `FP-03.md` | Política de Dispositivos No Reconocidos |
| `FP-04.md` | Política de Horario de Operaciones |
| `FP-05.md` | Política de Velocidad de Transacciones |
| `FP-06.md` | Política de Combinación de Factores de Riesgo |

### Cómo ejecutar la ingesta

```bash
cd backend
python -m app.rag.ingest
```

El script CLI (`backend/app/rag/ingest.py`) llama a `ingest_policies()` de `vector_store.py`, que:
1. Lee todos los archivos `.md` del directorio `backend/policies/`
2. Divide cada archivo en chunks por sección `## FP-XX:`
3. Hace upsert en ChromaDB (idempotente, se puede ejecutar múltiples veces)

### Chunking: cómo se dividen las políticas

La función `_split_markdown_sections()` en `vector_store.py` usa el patrón regex:

```python
pattern = r"^## (FP-\d{2}):\s*(.+)$"
```

Cada sección `## FP-XX: Título` se convierte en un chunk independiente. Como cada archivo `.md` contiene una sola política, **cada archivo produce exactamente un chunk**.

### Ejemplo concreto: chunk generado desde FP-01.md

```python
{
    "id": "fp-01-section-0",
    "document": "## FP-01: Política de Montos Inusuales\n\n**Descripción:**\n"
                "Esta política detecta transacciones con montos significativamente "
                "superiores al comportamiento histórico del cliente...\n"
                "...\n"
                "**Acción Recomendada:**\n"
                "CHALLENGE - Solicitar verificación adicional...\n",
    "metadata": {
        "policy_id": "FP-01",
        "section_name": "Política de Montos Inusuales",
        "file_name": "FP-01.md",
        "section_index": 0,
        "action_recommended": "CHALLENGE"
    }
}
```

### Extracción de `action_recommended`

Después de crear los chunks, el código escanea el texto buscando las keywords `BLOCK`, `CHALLENGE`, `APPROVE` o `ESCALATE`. La primera que encuentre se asigna como metadata:

```python
if "BLOCK" in doc:
    chunk["metadata"]["action_recommended"] = "BLOCK"
elif "CHALLENGE" in doc:
    chunk["metadata"]["action_recommended"] = "CHALLENGE"
# ...
```

Esto permite filtrar resultados por acción recomendada sin necesidad de leer el texto completo.

---

## 3. Fase 2: Vectorización (Embeddings)

### Modelo de embeddings

ChromaDB usa por defecto **`sentence-transformers/all-MiniLM-L6-v2`**, que genera vectores de **384 dimensiones**. Este modelo se descarga automáticamente la primera vez que se ejecuta la ingesta.

### Cómo funciona

Cuando se llama a `collection.upsert()`, ChromaDB **internamente**:
1. Toma cada string del campo `documents`
2. Lo pasa por el modelo de embeddings
3. Obtiene un vector de 384 números flotantes
4. Almacena el vector junto con el documento original y su metadata

```python
# En ingest_policies(), esta línea hace todo:
collection.upsert(
    ids=[chunk["id"] for chunk in all_chunks],
    documents=[chunk["document"] for chunk in all_chunks],    # ChromaDB vectoriza esto
    metadatas=[chunk["metadata"] for chunk in all_chunks],
)
```

### Ejemplo conceptual de vectorización

El texto:
> "Política de Montos Inusuales - transacciones con montos significativamente superiores al promedio"

Se convierte en un vector como:
```
[0.0231, -0.0892, 0.1547, ..., 0.0034]   ← 384 dimensiones
```

Textos semánticamente similares producen vectores cercanos en el espacio vectorial, lo que permite encontrar políticas relevantes sin necesidad de coincidencias exactas de palabras.

### Almacenamiento persistente

Los vectores se persisten en disco en `backend/data/chroma/` (configurado via `settings.chroma_persist_dir` en `config.py`). No se pierden al reiniciar el servidor.

---

## 4. Fase 3: Construcción del Query

### Función: `build_rag_query()`

Ubicada en `backend/app/utils/policy_utils.py`, esta función construye un query en **lenguaje natural en español** a partir de las señales detectadas por los agentes de la Fase 1 (TransactionContext y BehavioralPattern).

### Lógica de construcción

```python
def build_rag_query(transaction, transaction_signals, behavioral_signals) -> str:
    query_parts = [f"transacción de {transaction.amount} {transaction.currency}"]

    # Señales de TransactionContext
    if transaction_signals.amount_ratio > 3.0:
        query_parts.append("monto muy superior al promedio")
    elif transaction_signals.amount_ratio > 2.0:
        query_parts.append("monto elevado")

    if transaction_signals.is_foreign:
        query_parts.append(f"desde país extranjero {transaction.country}")
    if transaction_signals.is_unknown_device:
        query_parts.append("dispositivo no reconocido")
    if transaction_signals.channel_risk == "high":
        query_parts.append("canal de alto riesgo")

    # Señales de BehavioralPattern
    if "off_hours_transaction" in behavioral_signals.anomalies:
        query_parts.append("fuera del horario habitual del cliente")

    if behavioral_signals.deviation_score > 0.7:
        query_parts.append("comportamiento muy anómalo")
    if behavioral_signals.velocity_alert:
        query_parts.append("alerta de velocidad de transacciones")

    # Anomalías individuales
    for anomaly in behavioral_signals.anomalies[:3]:
        query_parts.append(anomaly.replace("_", " "))

    return " ".join(query_parts)
```

Los umbrales `3.0` y `2.0` vienen de `AMOUNT_THRESHOLDS` en `backend/app/constants.py`.

### Ejemplo: query para transacción T-1001

Supongamos T-1001 con monto alto y fuera de horario:
- `amount_ratio = 3.6` (> 3.0)
- `is_foreign = False`
- `is_unknown_device = False`
- `anomalies = ["off_hours_transaction", "amount_3x_above_average"]`
- `deviation_score = 0.45`

Query resultante:
```
"transacción de 4500.00 PEN monto muy superior al promedio fuera del horario habitual del cliente off hours transaction amount 3x above average"
```

Este texto en español permite que ChromaDB lo vectorice y encuentre las políticas más relevantes semánticamente.

---

## 5. Fase 4: Búsqueda por Similitud

### Función: `query_policies()`

Ubicada en `backend/app/rag/vector_store.py`, recibe el query y devuelve los top-N chunks más relevantes.

### Proceso interno

```python
def query_policies(query: str, n_results: int = 5) -> list[dict]:
    collection = initialize_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    # ...
```

Cuando ChromaDB recibe el query:
1. **Vectoriza** el query con el mismo modelo (all-MiniLM-L6-v2)
2. **Calcula distancia L2** (euclidiana) entre el vector del query y cada vector almacenado
3. **Retorna** los `n_results` chunks con menor distancia

### Conversión de distancia a score

ChromaDB retorna **distancia** (menor = mejor). El código la convierte a **score** (mayor = mejor) usando decaimiento exponencial:

```python
score = math.exp(-distance)
```

| Distancia L2 | Score resultante | Interpretación |
|---|---|---|
| 0.0 | 1.0000 | Coincidencia perfecta |
| 0.5 | 0.6065 | Muy relevante |
| 1.0 | 0.3679 | Moderadamente relevante |
| 2.0 | 0.1353 | Poco relevante |

### Ejemplo de resultados para T-1001

```python
[
    {
        "id": "fp-01-section-0",
        "text": "## FP-01: Política de Montos Inusuales\n...",
        "metadata": {"policy_id": "FP-01", "action_recommended": "CHALLENGE", ...},
        "score": 0.6823
    },
    {
        "id": "fp-04-section-0",
        "text": "## FP-04: Política de Horario de Operaciones\n...",
        "metadata": {"policy_id": "FP-04", "action_recommended": "CHALLENGE", ...},
        "score": 0.5912
    },
    {
        "id": "fp-06-section-0",
        "text": "## FP-06: Política de Combinación de Factores de Riesgo\n...",
        "metadata": {"policy_id": "FP-06", "action_recommended": "BLOCK", ...},
        "score": 0.4201
    },
    # ... hasta 5 resultados
]
```

---

## 6. Fase 5: Análisis LLM

### Inyección en el prompt

Los chunks recuperados se inyectan en `POLICY_ANALYSIS_PROMPT` (definido en `backend/app/prompts/policy.py`). El prompt incluye:

1. **Datos de la transacción**: ID, monto, país, canal, dispositivo, timestamp
2. **Señales detectadas**: resumen construido por `build_signals_summary()`
3. **Políticas recuperadas**: los chunks de ChromaDB con sus scores

```
**POLÍTICAS RELEVANTES (recuperadas de la base de conocimiento):**

**Chunk ID: fp-01-section-0 (score: 0.68)**
## FP-01: Política de Montos Inusuales
...

---

**Chunk ID: fp-04-section-0 (score: 0.59)**
## FP-04: Política de Horario de Operaciones
...
```

### El LLM evalúa

El modelo (Ollama, configurado como `qwen3:30b` por defecto en `config.py`) recibe el prompt completo y debe responder con un JSON indicando qué políticas aplican y con qué relevancia.

### Parseo de la respuesta: dos etapas

La función `parse_policy_matches()` en `policy_utils.py` usa una estrategia de dos etapas:

**Etapa 1 - JSON**: intenta parsear la respuesta como JSON estructurado:
```json
{
  "matches": [
    {
      "policy_id": "FP-01",
      "description": "Transacción nocturna con monto 3.6x superior al promedio",
      "relevance_score": 0.92
    }
  ]
}
```

**Etapa 2 - Regex fallback**: si el JSON falla, busca patrones con regex:
```python
pattern = r"(FP-\d{2}).*?(?:score|relevance)[:\s]+(0\.\d+|1\.0)"
```

### Filtro de calidad

Solo se retienen matches con `relevance_score >= 0.5`. Los scores se clampean al rango [0.0, 1.0] con `clamp_float()`.

---

## 7. Fase 6: Valor Entregado al Orquestador

### Modelo: `PolicyMatchResult`

Definido en `backend/app/models/evidence.py`:

```python
class PolicyMatchResult(BaseModel):
    matches: list[PolicyMatch]   # Políticas que aplican
    chunk_ids: list[str]         # IDs de chunks consultados (trazabilidad)

class PolicyMatch(BaseModel):
    policy_id: str               # "FP-01"
    description: str             # Por qué aplica
    relevance_score: float       # 0.0 - 1.0
```

### Ejemplo completo de output para T-1001

```python
PolicyMatchResult(
    matches=[
        PolicyMatch(
            policy_id="FP-01",
            description="Transacción con monto 3.6x superior al promedio del cliente, activando umbral crítico de montos inusuales",
            relevance_score=0.92
        ),
        PolicyMatch(
            policy_id="FP-04",
            description="Transacción realizada a las 02:30 AM, fuera del horario habitual del cliente (08:00-22:00)",
            relevance_score=0.85
        ),
    ],
    chunk_ids=[
        "fp-01-section-0",
        "fp-04-section-0",
        "fp-06-section-0",
        "fp-02-section-0",
        "fp-05-section-0",
    ]
)
```

### Cómo se usa en las fases posteriores

El `PolicyMatchResult` se escribe en el campo `policy_matches` del `OrchestratorState` y es consumido por:

1. **EvidenceAggregation** (Fase 2): incorpora los matches en el cálculo del `composite_risk_score`, con un peso de 25% (`EVIDENCE_WEIGHTS.policy = 0.25`)
2. **ProFraud / ProCustomer** (Fase 3): los agentes de debate usan las políticas como evidencia para argumentar a favor o en contra del fraude
3. **DecisionArbiter** (Fase 4): considera las políticas activadas para emitir la decisión final
4. **Explainability** (Fase 5): genera explicaciones citando las políticas específicas que se activaron

### Trazabilidad

El agente también retorna metadata de traza (`_rag_trace` y `_llm_trace`) que incluye:
- El query exacto enviado a ChromaDB
- Los scores de cada chunk recuperado
- El prompt completo enviado al LLM
- La respuesta raw del LLM
- Tokens consumidos (si disponible)

Esto permite auditar completamente cada decisión del sistema.

---

## Archivos fuente referenciados

| Archivo | Contenido clave |
|---|---|
| `backend/app/rag/vector_store.py` | `ingest_policies()`, `_split_markdown_sections()`, `query_policies()` |
| `backend/app/rag/ingest.py` | CLI de ingesta |
| `backend/app/agents/policy_rag.py` | Agente PolicyRAG completo |
| `backend/app/utils/policy_utils.py` | `build_rag_query()`, `build_signals_summary()`, `parse_policy_matches()` |
| `backend/app/prompts/policy.py` | `POLICY_ANALYSIS_PROMPT` |
| `backend/app/models/evidence.py` | `PolicyMatch`, `PolicyMatchResult` |
| `backend/app/dependencies.py` | `get_chroma()` → `PersistentClient` |
| `backend/app/config.py` | `settings.chroma_persist_dir`, `settings.ollama_model` |
| `backend/app/constants.py` | `AMOUNT_THRESHOLDS`, `EVIDENCE_WEIGHTS` |
| `backend/policies/FP-01.md` a `FP-06.md` | Políticas fuente |
