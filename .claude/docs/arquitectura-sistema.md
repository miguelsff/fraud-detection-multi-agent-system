# Arquitectura del Sistema Multi-Agente de Detección de Fraude

**Última actualización**: 2026-02-16
**Refleja commit**: fa32866 (HITL resolution visibility, LLM/RAG trace fields, componentes trace UI, traducción español)
**Actualizar este documento cuando**: Se cambien versiones de tech stack, se agreguen nuevos agentes, o se modifique arquitectura core

## 1. Visión General

El sistema implementa un pipeline de **8 agentes especializados** orquestados mediante **LangGraph** que analizan transacciones financieras en busca de fraude ambiguo. La arquitectura sigue un patrón **DAG (Directed Acyclic Graph)** con fases paralelas y secuenciales, permitiendo máxima eficiencia sin sacrificar trazabilidad.

**Estado de Implementación**: Sistema completamente funcional con las siguientes características implementadas:
- ✅ Pipeline completo de 8 agentes con LangGraph
- ✅ HITL (Human-in-the-Loop) queue con resolución manual
- ✅ Analytics dashboard con métricas en tiempo real
- ✅ WebSocket para actualizaciones en vivo
- ✅ Frontend completo con 54 componentes React y 6 páginas
- ✅ PostgreSQL async con Alembic migrations
- ✅ ChromaDB para RAG de políticas internas
- ✅ Policy CRUD (gestión de políticas con sincronización ChromaDB)
- ✅ Threat Intelligence real (FATF + OSINT + Sanctions providers)
- ✅ Prompts extraídos a módulo dedicado (`app/prompts/`)
- ✅ Constantes centralizadas en modelos Pydantic (`constants.py`)
- ✅ Jerarquía de excepciones custom (`exceptions.py`)
- ✅ Estructured logging con structlog
- ✅ Datos sintéticos para testing (6 transacciones)
- ✅ Scripts de demostración end-to-end
- ✅ Resolución HITL visible en detalle de transacción (`GET /result` incluye campo `hitl`)
- ✅ Trace de interacciones LLM y queries RAG en UI (`LLMInteractionViewer`, `RAGQueryViewer`)

### Stack Tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| **Orquestación** | LangGraph 1.0+ | Grafos de estado tipados, checkpointing nativo, soporte async, visualización de flujos |
| **Backend** | FastAPI + Python 3.13 + uv | Async nativo, Pydantic v2 integrado, OpenAPI auto-generado, WebSockets, package manager ultrarrápido |
| **Frontend** | Next.js 16 + TypeScript + Tailwind + shadcn/ui | SSR/SSG, App Router, React Server Components, componentes copiables sin vendor lock-in |
| **Vector DB** | ChromaDB (embedded) | Lightweight, embebible, ideal para el volumen de políticas internas, persistencia automática |
| **LLM** | Ollama (qwen3:30b local) / Azure OpenAI (prod) | Desarrollo local sin costos, Azure OpenAI planeado para despliegue en cloud |
| **Base de datos** | PostgreSQL 16 (async via asyncpg) | Audit trail persistente, SQLAlchemy async, Alembic migrations, soporte tanto local como cloud |
| **Logging** | structlog | Logs estructurados JSON, contexto automático, ideal para observabilidad |
| **Deploy** | Docker Compose (local) / Azure Container Apps (planeado) | Containerización con 3 servicios (postgres, backend, frontend), Azure planeado para producción |

---

## 2. Diagrama de Arquitectura General

**Nota**: Este diagrama refleja el sistema completamente implementado y funcional en desarrollo local.

```mermaid
graph TB
    subgraph "Frontend — Next.js 16 (✅ Implementado)"
        UI[Dashboard UI<br/>Stats + Charts]
        TL[Transaction List<br/>+ Detail View]
        AT[Agent Trace Viewer<br/>Timeline + Debate]
        HQ[HITL Queue<br/>Human Review]
        EP[Explanation Panel<br/>Customer + Audit]
        AN[Analytics Dashboard<br/>Metrics + Trends]
        PL[Policy Management<br/>CRUD + Reingest]
    end

    subgraph "API Gateway — FastAPI"
        API[FastAPI Server<br/>Python 3.13]
        WS[WebSocket Handler<br/>Real-time Events]
        MW[Middleware<br/>CORS · Logging]
    end

    subgraph "Orchestration Layer — LangGraph"
        ORC[Orchestrator<br/>State Machine<br/>~4-6s pipeline]
    end

    subgraph "Agent Layer (8 agentes)"
        direction TB
        subgraph "Fase 1 — Recolección Paralela (~2-4s)"
            TCA[Transaction Context<br/>Determinístico]
            BPA[Behavioral Pattern<br/>Determinístico]
            PRA[Policy RAG<br/>LLM + ChromaDB]
            ETA[External Threat<br/>LLM + Web Search]
        end
        subgraph "Fase 2 — Consolidación"
            EAA[Evidence Aggregation<br/>Determinístico]
        end
        subgraph "Fase 3 — Deliberación (~1-2s)"
            DPF[Debate Agent<br/>Pro-Fraud · LLM]
            DPC[Debate Agent<br/>Pro-Customer · LLM]
        end
        subgraph "Fase 4 — Decisión"
            DAR[Decision Arbiter<br/>LLM]
        end
        subgraph "Fase 5 — Explicación"
            EXP[Explainability<br/>LLM]
        end
    end

    subgraph "Data Layer"
        CDB[(ChromaDB<br/>Políticas Embedded)]
        SQL[(PostgreSQL 16<br/>Async + Alembic)]
        SYN[(Synthetic Data<br/>6 transacciones)]
    end

    UI & AN & PL --> API
    TL & AT & HQ & EP --> API
    API --> ORC
    ORC --> TCA & BPA & PRA & ETA
    TCA & BPA & PRA & ETA --> EAA
    EAA --> DPF & DPC
    DPF & DPC --> DAR
    DAR --> EXP
    EXP --> API
    API --> WS --> UI

    PRA -.-> CDB
    ETA -.->|FATF · OSINT · Sanctions| EXT[Threat Intel<br/>Multi-Provider]
    ORC -.->|structlog| SQL
    API -.-> SYN
```

---

## 3. Flujo de Orquestación Detallado (LangGraph)

**Tiempos Reales de Ejecución**:
- Pipeline completo: ~4-6 segundos
- Fase paralela: ~2-4 segundos (el agente más lento determina el tiempo)
- Debate adversarial: ~1-2 segundos
- Timeout global: 60 segundos
- Timeout por agente: 30 segundos

**Manejo de Errores**:
- Si un agente falla, se registra en trace con `status: "error"`
- El pipeline **continúa** con resultados parciales (graceful degradation)
- Decision Arbiter favorece `ESCALATE_TO_HUMAN` ante evidencia incompleta

```mermaid
stateDiagram-v2
    [*] --> ReceiveTransaction: POST /api/v1/transactions/analyze

    ReceiveTransaction --> ValidateInput: Validar schema Pydantic
    ValidateInput --> ParallelCollection: Input válido
    ValidateInput --> ErrorResponse: Input inválido

    state ParallelCollection {
        [*] --> TransactionContext
        [*] --> BehavioralPattern
        [*] --> PolicyRAG
        [*] --> ExternalThreat

        TransactionContext --> [*]: Señales contextuales (instantáneo)
        BehavioralPattern --> [*]: Desviaciones comportamiento (instantáneo)
        PolicyRAG --> [*]: Políticas + chunks (1-2s LLM)
        ExternalThreat --> [*]: Amenazas externas (1-3s Web+LLM)

        note right of PolicyRAG
            Circuit breaker:
            Si falla → matches: []
        end note

        note right of ExternalThreat
            Circuit breaker:
            Si falla → threat_level: 0.0
        end note
    }

    ParallelCollection --> EvidenceAggregation: Consolidar señales (~50ms)

    EvidenceAggregation --> DebatePhase: Evidencia consolidada

    state DebatePhase {
        [*] --> ProFraudArgument: Argumentar sospecha (LLM)
        [*] --> ProCustomerArgument: Argumentar legitimidad (LLM)
        ProFraudArgument --> [*]: Caso de fraude
        ProCustomerArgument --> [*]: Caso legítimo
    }

    DebatePhase --> DecisionArbiter: Evaluar argumentos (~800ms LLM)

    DecisionArbiter --> Explainability: Decisión + confidence (~600ms LLM)

    state DecisionRouting <<choice>>
    Explainability --> DecisionRouting

    DecisionRouting --> ResponseAPPROVE: APPROVE
    DecisionRouting --> ResponseCHALLENGE: CHALLENGE
    DecisionRouting --> ResponseBLOCK: BLOCK
    DecisionRouting --> HITLQueue: ESCALATE_TO_HUMAN

    ResponseAPPROVE --> PersistAudit
    ResponseCHALLENGE --> PersistAudit
    ResponseBLOCK --> PersistAudit
    HITLQueue --> PersistAudit

    PersistAudit --> [*]: Retornar FraudDecision JSON
    ErrorResponse --> [*]: Retornar error 422/500
```

---

## 4. Grafo LangGraph — Definición del State Machine

```mermaid
graph LR
    subgraph "LangGraph StateGraph"
        START((START)) --> validate[validate_input]
        validate --> fork{Fan-Out<br/>Paralelo}

        fork --> tca[transaction_context]
        fork --> bpa[behavioral_pattern]
        fork --> pra[policy_rag]
        fork --> eta[external_threat]

        tca --> join{Fan-In<br/>Barrier}
        bpa --> join
        pra --> join
        eta --> join

        join --> agg[evidence_aggregation]
        agg --> debate_fork{Fan-Out<br/>Debate}

        debate_fork --> pro_fraud[debate_pro_fraud]
        debate_fork --> pro_customer[debate_pro_customer]

        pro_fraud --> debate_join{Fan-In}
        pro_customer --> debate_join

        debate_join --> arbiter[decision_arbiter]
        arbiter --> explain[explainability]
        explain --> persist[persist_audit]
        persist --> route{Route by<br/>Decision}

        route -->|APPROVE| response[respond]
        route -->|CHALLENGE| response
        route -->|BLOCK| response
        route -->|ESCALATE| hitl[hitl_queue]
        hitl --> response
        response --> END((END))
    end

    style START fill:#22c55e,color:#fff
    style END fill:#ef4444,color:#fff
    style fork fill:#3b82f6,color:#fff
    style join fill:#3b82f6,color:#fff
    style debate_fork fill:#8b5cf6,color:#fff
    style debate_join fill:#8b5cf6,color:#fff
    style route fill:#f59e0b,color:#fff
```

### 4.1 Implementación LangGraph Real

**Archivo**: `backend/app/agents/orchestrator.py`

El grafo se define como un `StateGraph[OrchestratorState]` con nodos que son funciones async:

```python
from langgraph.graph import END, START, StateGraph
from ..models import OrchestratorState

# Crear grafo con estado tipado
builder = StateGraph(OrchestratorState)

# Agregar nodos (cada nodo es una función async)
builder.add_node("validate_input", validate_input)
builder.add_node("phase1_parallel", phase1_parallel)  # 4 agentes en paralelo
builder.add_node("evidence_aggregation", evidence_aggregation_node)
builder.add_node("debate_parallel", debate_parallel)  # Pro-Fraud + Pro-Customer
builder.add_node("decision_arbiter", decision_arbiter_node)
builder.add_node("explainability", explainability_node)
builder.add_node("persist_audit", persist_audit)
builder.add_node("hitl_queue", hitl_queue)
builder.add_node("respond", respond)

# Definir edges
builder.add_edge(START, "validate_input")
builder.add_conditional_edges(
    "validate_input",
    route_after_validation,
    {"continue": "phase1_parallel", "error": "respond"},
)
builder.add_edge("phase1_parallel", "evidence_aggregation")
builder.add_edge("evidence_aggregation", "debate_parallel")
builder.add_edge("debate_parallel", "decision_arbiter")
builder.add_edge("decision_arbiter", "explainability")
builder.add_edge("explainability", "persist_audit")

# Routing condicional basado en decisión
builder.add_conditional_edges(
    "persist_audit",
    route_decision,
    {"hitl_queue": "hitl_queue", "respond": "respond"},
)

builder.add_edge("hitl_queue", "respond")
builder.add_edge("respond", END)

# Compilar grafo
graph = builder.compile()
```

**Paralelismo con `asyncio.gather()`**:

```python
async def phase1_parallel(state: OrchestratorState) -> dict:
    """Ejecutar 4 agentes en paralelo con manejo de errores."""
    results = await asyncio.gather(
        transaction_context_agent(state),
        behavioral_pattern_agent(state),
        policy_rag_agent(state),
        external_threat_agent(state),
        return_exceptions=True,  # No detener si uno falla
    )

    # Mergear resultados al estado compartido
    merged = {}
    for result in results:
        if isinstance(result, dict):
            merged.update(result)
    return merged
```

**Beneficios de esta implementación**:
- ✅ Tipado fuerte con TypedDict (OrchestratorState)
- ✅ Paralelismo real con asyncio (no secuencial)
- ✅ Graceful degradation (return_exceptions=True)
- ✅ Trace automático de cada nodo
- ✅ Visualización del grafo con LangSmith

---

## 5. Modelo de Estado Compartido (Shared State)

El estado es el contrato central entre todos los agentes. LangGraph lo gestiona de forma inmutable con `TypedDict`.

**Archivo de definición**: `backend/app/models/trace.py`

**Persistencia**: El estado completo se serializa a PostgreSQL para auditoría, usando:
- **Tabla `transaction_records`**: Almacena Transaction + FraudDecision + timestamps
- **Tabla `agent_traces`**: Almacena cada AgentTraceEntry individual
- **Tabla `hitl_cases`**: Almacena casos escalados a humanos

```mermaid
classDiagram
    class OrchestratorState {
        +Transaction transaction
        +CustomerBehavior customer_behavior
        +TransactionSignals? transaction_signals
        +BehavioralSignals? behavioral_signals
        +PolicyMatchResult? policy_matches
        +ThreatIntelResult? threat_intel
        +AggregatedEvidence? evidence
        +DebateArguments? debate
        +FraudDecision? decision
        +ExplanationResult? explanation
        +List~AgentTraceEntry~ trace
        +str status
    }

    class HITLCase {
        +int id
        +str transaction_id
        +str status
        +FraudDecision original_decision
        +str? reviewer_id
        +str? human_decision
        +str? human_rationale
        +datetime created_at
        +datetime? resolved_at
    }

    class Transaction {
        +str transaction_id
        +str customer_id
        +float amount
        +str currency
        +str country
        +str channel
        +str device_id
        +datetime timestamp
        +str merchant_id
    }

    class CustomerBehavior {
        +str customer_id
        +float usual_amount_avg
        +str usual_hours
        +List~str~ usual_countries
        +List~str~ usual_devices
    }

    class TransactionSignals {
        +float amount_ratio
        +bool is_foreign
        +bool is_unknown_device
        +str channel_risk
        +List~str~ flags
    }

    class BehavioralSignals {
        +float deviation_score
        +List~str~ anomalies
        +bool velocity_alert
    }

    class PolicyMatchResult {
        +List~PolicyMatch~ matches
        +List~str~ chunk_ids
    }

    class ThreatIntelResult {
        +float threat_level
        +List~ThreatSource~ sources
    }

    class AggregatedEvidence {
        +float composite_risk_score
        +List~str~ all_signals
        +List~str~ all_citations
        +str risk_category
    }

    class DebateArguments {
        +str pro_fraud_argument
        +float pro_fraud_confidence
        +List~str~ pro_fraud_evidence
        +str pro_customer_argument
        +float pro_customer_confidence
        +List~str~ pro_customer_evidence
    }

    class FraudDecision {
        +str transaction_id
        +str decision
        +float confidence
        +List~str~ signals
        +List~dict~ citations_internal
        +List~dict~ citations_external
        +str explanation_customer
        +str explanation_audit
        +List~str~ agent_trace
    }

    class AgentTraceEntry {
        +str agent_name
        +datetime timestamp
        +float duration_ms
        +str input_summary
        +str output_summary
        +str status
    }

    class ExplanationResult {
        +str customer_explanation
        +str audit_explanation
    }

    class PolicyResponse {
        +str policy_id
        +str title
        +str description
        +list~str~ criteria
        +list~str~ thresholds
        +PolicyAction action_recommended
        +PolicySeverity severity
        +str file_path
    }

    class HITLResolution {
        +int case_id
        +str status
        +str? resolution
        +datetime? resolved_at
    }

    class TransactionAnalysisDetail {
        +FraudDecision decision
        +HITLResolution? hitl
    }

    TransactionAnalysisDetail --> FraudDecision
    TransactionAnalysisDetail --> HITLResolution

    OrchestratorState --> Transaction
    OrchestratorState --> CustomerBehavior
    OrchestratorState --> TransactionSignals
    OrchestratorState --> BehavioralSignals
    OrchestratorState --> PolicyMatchResult
    OrchestratorState --> ThreatIntelResult
    OrchestratorState --> AggregatedEvidence
    OrchestratorState --> DebateArguments
    OrchestratorState --> FraudDecision
    OrchestratorState --> AgentTraceEntry
```

---

## 6. Patrón de Comunicación entre Agentes

### 6.1 Principio: Shared State (Blackboard Pattern)

Los agentes **NO se comunican directamente entre sí**. Toda comunicación fluye a través del **estado compartido** gestionado por LangGraph. Esto garantiza:

- **Trazabilidad total**: cada modificación al estado queda registrada
- **Desacoplamiento**: los agentes son funciones puras `(state) → state`
- **Testabilidad**: cada agente se puede probar en aislamiento con un estado mock
- **Reproducibilidad**: dado el mismo estado de entrada, un agente siempre produce el mismo resultado

```mermaid
graph LR
    subgraph "Blackboard Pattern"
        STATE[(Shared State<br/>OrchestratorState)]

        A1[Agent 1<br/>Lee estado] -->|read| STATE
        STATE -->|write| A1R[Agent 1<br/>Actualiza estado]

        A2[Agent 2<br/>Lee estado] -->|read| STATE
        STATE -->|write| A2R[Agent 2<br/>Actualiza estado]

        A3[Agent N<br/>Lee estado] -->|read| STATE
        STATE -->|write| A3R[Agent N<br/>Actualiza estado]
    end

    note["Cada agente:<br/>1. Lee campos relevantes del estado<br/>2. Ejecuta su lógica<br/>3. Retorna SOLO sus campos actualizados<br/>4. LangGraph mergea al estado global"]

    style STATE fill:#f59e0b,color:#000,stroke:#000,stroke-width:2px
```

### 6.2 Contratos de Entrada/Salida por Agente

| Agente | Lee del Estado | Escribe al Estado | Tipo | Timeout |
|--------|---------------|-------------------|------|---------|
| **Transaction Context** | `transaction`, `customer_behavior` | `transaction_signals` | Determinístico | Instantáneo |
| **Behavioral Pattern** | `transaction`, `customer_behavior` | `behavioral_signals` | Determinístico | Instantáneo |
| **Policy RAG** | `transaction`, `transaction_signals`, `behavioral_signals` | `policy_matches` | LLM + RAG | 30s |
| **External Threat** | `transaction`, `transaction_signals`, `behavioral_signals` | `threat_intel` | LLM + Multi-Provider (FATF, OSINT, Sanctions) | 30s |
| **Evidence Aggregation** | `transaction_signals`, `behavioral_signals`, `policy_matches`, `threat_intel` | `evidence` | Determinístico | <100ms |
| **Debate Pro-Fraud** | `evidence` | `debate.pro_fraud_*` | LLM | 30s |
| **Debate Pro-Customer** | `evidence` | `debate.pro_customer_*` | LLM | 30s |
| **Decision Arbiter** | `evidence`, `debate` | `decision` | LLM | 30s |
| **Explainability** | `decision`, `evidence`, `policy_matches`, `debate` | `explanation` | LLM | 30s |

> **Nota sobre `off_hours`**: `BehavioralPattern` es el dueño exclusivo de la detección de transacciones fuera de horario. Lo reporta como `"off_hours_transaction"` en `behavioral_signals.anomalies[]`. Los agentes `PolicyRAG` y `ExternalThreat` leen este dato desde `behavioral_signals.anomalies`, no desde `transaction_signals`.

### 6.3 Fan-Out / Fan-In para Paralelismo

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant TCA as Transaction Context
    participant BPA as Behavioral Pattern
    participant PRA as Policy RAG
    participant ETA as External Threat
    participant EAA as Evidence Aggregator

    O->>+TCA: state (async)
    O->>+BPA: state (async)
    O->>+PRA: state (async)
    O->>+ETA: state (async)

    Note over TCA,ETA: Ejecución Paralela (asyncio.gather)

    TCA-->>-O: transaction_signals
    BPA-->>-O: behavioral_signals
    PRA-->>-O: policy_matches
    ETA-->>-O: threat_intel

    Note over O: Merge all results into state

    O->>+EAA: merged state
    EAA-->>-O: aggregated evidence
```

### 6.4 Arquitectura de Threat Intelligence (Multi-Provider)

El agente `ExternalThreat` delega la recolección de inteligencia a un sistema de providers intercambiables, orquestados por `ThreatIntelManager`.

#### Interfaz Base

**Archivo**: `backend/app/services/threat_intel/base.py`

```python
class ThreatProvider(ABC):
    """Abstract base class for all threat intelligence providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique name for this provider (used in logs and traces)."""

    @abstractmethod
    async def lookup(
        self,
        transaction: Transaction,
        signals: TransactionSignals | None = None,
    ) -> list[ThreatSource]:
        """Lookup threats. Returns empty list on failure (never raises)."""
```

#### Providers Implementados

| Provider | Clase | Fuente de Datos | Señal Principal |
|----------|-------|-----------------|-----------------|
| **Country Risk** | `CountryRiskProvider` | Lista FATF de jurisdicciones de alto riesgo | Riesgo geográfico del país de la transacción |
| **OSINT Search** | `OSINTSearchProvider` | DuckDuckGo search (merchant + fraud patterns) | Reportes públicos de fraude asociados al merchant |
| **Sanctions** | `SanctionsProvider` | OpenSanctions API | Coincidencia con listas de sanciones internacionales |

#### Orquestación con Fan-Out Paralelo

**Archivo**: `backend/app/services/threat_intel/manager.py`

```mermaid
graph LR
    EA[ExternalThreat Agent] --> TIM[ThreatIntelManager]

    TIM --> CR[CountryRiskProvider<br/>FATF Lists]
    TIM --> OS[OSINTSearchProvider<br/>DuckDuckGo]
    TIM --> SC[SanctionsProvider<br/>OpenSanctions]

    CR --> AGG[Aggregator]
    OS --> AGG
    SC --> AGG

    AGG --> TIR[ThreatIntelResult<br/>threat_level + sources]

    style TIM fill:#8b5cf6,color:#fff
    style AGG fill:#f59e0b,color:#000
```

**Ejecución paralela**:
```python
class ThreatIntelManager:
    def __init__(self):
        self._providers: list[ThreatProvider] = [
            CountryRiskProvider(),
            OSINTSearchProvider(),
            SanctionsProvider(),
        ]

    async def analyze(self, transaction, signals) -> ThreatIntelResult:
        tasks = [p.lookup(transaction, signals) for p in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Combine sources, handle exceptions per-provider
        all_sources = [...]
        threat_level = self._calculate_threat_level(all_sources)
        return ThreatIntelResult(threat_level=threat_level, sources=all_sources)
```

#### Estrategia de Agregación

```python
def _calculate_threat_level(self, sources: list[ThreatSource]) -> float:
    """
    - Primary signal: max confidence across all sources
    - Multi-source bonus: +0.1 per additional source
    - Clamped to 1.0
    """
    max_confidence = max(s.confidence for s in sources)
    multi_source_bonus = 0.1 * (len(sources) - 1)
    return min(1.0, max_confidence + multi_source_bonus)
```

**Resiliencia**: Cada provider maneja sus propios errores internamente y retorna `[]` en caso de fallo. El manager continúa con los providers que sí respondieron.

### 6.5 Mecanismos de Resiliencia Implementados

El sistema implementa múltiples estrategias de resiliencia para garantizar que el pipeline completo continúe funcionando incluso cuando agentes individuales fallan.

#### Two-Stage Parsing (Parsing de Dos Etapas)

Todos los agentes LLM implementan una estrategia de parsing resiliente en caso de que el modelo no genere JSON válido:

**Estrategia de 3 niveles**:
1. **Intento primario**: Parsear respuesta completa como JSON puro
2. **Fallback con regex**: Extraer bloque JSON del texto si falla paso 1 (maneja markdown ```json)
3. **Fallback a valores por defecto**: Si ambos fallan, retornar estructura válida vacía

**Implementación real** (`backend/app/agents/policy_rag.py:296`):

```python
def _parse_llm_response(response_text: str) -> list[PolicyMatch]:
    """Two-stage parsing with graceful fallback."""
    matches = []

    try:
        # Stage 1: Try extracting JSON from markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Stage 2: Try finding raw JSON in text
            json_match = re.search(r'\{.*"matches".*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found")

        data = json.loads(json_str)
        # Process matches...

    except Exception as e:
        logger.warning("json_parse_failed", error=str(e))
        # Stage 3: Return empty but valid structure
        return []  # Graceful degradation
```

**Beneficios**:
- ✅ Maneja modelos que agregan texto antes/después del JSON
- ✅ Maneja markdown code blocks (```json)
- ✅ Nunca crashea por respuesta malformada
- ✅ Permite que el pipeline continúe con datos parciales

#### Graceful Degradation (Degradación Elegante)

**Principio**: Un agente individual que falle no debe detener el pipeline completo.

**Implementación**:
```python
async def phase1_parallel(state: OrchestratorState) -> dict:
    """Run Phase 1 agents in parallel with error handling."""
    results = await asyncio.gather(
        transaction_context_agent(state),
        policy_rag_agent(state),
        external_threat_agent(state),
        return_exceptions=True  # ← No detiene si uno falla
    )

    # Merge successful results
    merged = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"agent_{i}_failed", error=str(result))
            # Continue with other results
        else:
            merged.update(result)
    return merged
```

**Comportamiento**:
- Si `policy_rag_agent` falla → `policy_matches` queda vacío, pipeline continúa
- Si `external_threat_agent` falla → `threat_intel.threat_level = 0.0`, pipeline continúa
- `Decision Arbiter` detecta evidencia incompleta y favorece `ESCALATE_TO_HUMAN`

#### Circuit Breaker Pattern

Los agentes que dependen de servicios externos implementan circuit breakers:

**External Threat Agent**:
```python
try:
    search_results = await web_search(query)  # Puede fallar
    threat_analysis = await llm.ainvoke(...)
    return {"threat_intel": threat_analysis}
except Exception as e:
    logger.error("external_threat_circuit_breaker", error=str(e))
    # Return safe default instead of crashing
    return {"threat_intel": ThreatIntelResult(threat_level=0.0, sources=[])}
```

**Policy RAG Agent**:
```python
try:
    rag_results = query_policies(query)  # ChromaDB puede estar down
    if not rag_results:
        return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}
    # Continue processing...
except Exception as e:
    logger.error("policy_rag_circuit_breaker", error=str(e))
    return {"policy_matches": PolicyMatchResult(matches=[], chunk_ids=[])}
```

#### Safety Overrides (Decision Arbiter)

**Archivo**: `backend/app/utils/decision_utils.py`

El Decision Arbiter aplica overrides de seguridad automáticos que anulan la decisión del LLM en casos extremos:

| Condición | Override | Justificación |
|-----------|----------|---------------|
| `composite_score > 85.0` | Forzar **BLOCK** | Riesgo crítico requiere bloqueo inmediato |
| `confidence < 0.55` | Forzar **ESCALATE_TO_HUMAN** | Baja confianza requiere revisión humana |

```python
from ..constants import SAFETY_OVERRIDES

def apply_safety_overrides(decision, confidence, reasoning, composite_score):
    if composite_score > SAFETY_OVERRIDES.critical_risk_threshold:  # 85.0
        decision = "BLOCK"
        confidence = max(confidence, 0.85)
    if confidence < SAFETY_OVERRIDES.low_confidence_threshold:  # 0.55
        decision = "ESCALATE_TO_HUMAN"
    return decision, confidence, reasoning
```

Los umbrales están centralizados en `constants.py` (clase `SafetyOverrides`), no hardcodeados.

#### Timeouts Configurables

Cada agente LLM tiene timeouts configurables, centralizados en `constants.py` (clase `AgentTimeouts`):

- `llm_call`: 30s (timeout por llamada LLM individual)
- `pipeline`: 60s (timeout global del pipeline)
- `provider_lookup`: 15s (timeout por provider de threat intel)

Implementado con el decorador `@timed_agent`:

**Archivo**: `backend/app/utils/timing.py`

```python
def timed_agent(agent_name: str):
    """Decorator to add timing and timeout to agent functions."""
    def decorator(func):
        async def wrapper(state: OrchestratorState) -> dict:
            start = time.perf_counter()
            try:
                # Execute with timeout
                result = await asyncio.wait_for(func(state), timeout=30.0)
                duration_ms = (time.perf_counter() - start) * 1000

                # Add trace entry
                trace_entry = AgentTraceEntry(
                    agent_name=agent_name,
                    timestamp=datetime.now(UTC),
                    duration_ms=duration_ms,
                    status="success"
                )
                result["trace"] = result.get("trace", []) + [trace_entry]
                return result

            except asyncio.TimeoutError:
                logger.error(f"{agent_name}_timeout", timeout_seconds=30)
                # Return empty but valid result
                return {agent_name: None, "trace": [...]}

        return wrapper
    return decorator
```

**Uso**:
```python
@timed_agent("policy_rag")
async def policy_rag_agent(state: OrchestratorState) -> dict:
    # Si la ejecución toma >30s, timeout automático
    ...
```

#### Logging Estructurado (structlog)

Todos los errores y eventos se registran con contexto estructurado para debugging:

```python
logger.error(
    "agent_failed",
    agent="policy_rag",
    transaction_id=transaction.transaction_id,
    error=str(e),
    duration_ms=duration,
    exc_info=True  # Incluye stack trace
)
```

**Beneficios**:
- ✅ Logs en formato JSON para agregación
- ✅ Contexto automático (transaction_id, agent_name)
- ✅ Facilita debugging en producción
- ✅ Compatible con herramientas de observabilidad (ELK, Datadog, etc.)

---

## 7. Justificación de Decisiones de Diseño

### 7.1 ¿Por qué LangGraph sobre otras opciones?

| Criterio | LangGraph | Azure AI Agent | AWS Bedrock Agents | CrewAI | Estado Actual |
|----------|-----------|---------------|-------------------|--------|---------------|
| **Grafos tipados** | ✅ Nativo | ❌ | ❌ | ❌ | ✅ Implementado con TypedDict |
| **Paralelismo** | ✅ Fan-out/in | ⚠️ Manual | ⚠️ Manual | ✅ | ✅ asyncio.gather en 2 fases |
| **Checkpointing** | ✅ Built-in | ❌ | ❌ | ❌ | ⚠️ No usado (audit trail en PostgreSQL) |
| **Debugging** | ✅ LangSmith | ⚠️ | ⚠️ | ⚠️ | ✅ Trace logs + structlog |
| **Estado tipado** | ✅ TypedDict | ❌ | ❌ | ❌ | ✅ OrchestratorState tipado |
| **Vendor lock-in** | ❌ Agnóstico | ✅ Azure | ✅ AWS | ❌ | ✅ Agnóstico de LLM (Ollama local) |
| **Madurez** | ✅ Producción | ⚠️ Preview | ✅ | ⚠️ | ✅ LangGraph 1.0+ estable |

**Decisión**: LangGraph ofrece el mejor balance entre control granular del flujo, tipado fuerte del estado, paralelismo nativo y trazabilidad. Su integración con LangSmith permite debugging visual del grafo completo, lo cual es crítico para un sistema de detección de fraude donde cada decisión debe ser auditable.

**Implementación actual**: El sistema usa LangGraph 1.0+ con estado tipado `OrchestratorState`, paralelismo en 2 fases (recolección + debate), y trace logging completo en PostgreSQL.

### 7.2 ¿Por qué Blackboard Pattern sobre Message Passing?

- **Message Passing** (ej. pub/sub entre agentes): más flexible pero dificulta la trazabilidad y el debugging. Los mensajes pueden perderse o procesarse fuera de orden.
- **Blackboard Pattern** (estado compartido): cada agente lee/escribe a un estado central. Garantiza consistencia, reproducibilidad y facilita auditoría.

Para un sistema de **detección de fraude financiero**, la **auditabilidad** es más importante que la flexibilidad, por lo que el Blackboard Pattern es la elección correcta.

### 7.3 ¿Por qué ChromaDB sobre FAISS o Azure AI Search?

- **FAISS**: excelente rendimiento pero no persiste datos nativamente, requiere gestión manual de índices.
- **Azure AI Search**: potente pero over-engineered para ~6 políticas de fraude, alto costo.
- **ChromaDB**: persiste automáticamente, API Pythonic, embebible en el container, ideal para el volumen de datos del desafío (~6-20 políticas).

En producción real se migraría a **Azure AI Search** para beneficios de escalado y gestión empresarial.

### 7.4 ¿Por qué Next.js sobre React SPA?

- **Server-Side Rendering**: mejor performance percibida en el dashboard
- **App Router**: layouts anidados ideales para un dashboard con sidebar + panels
- **API Routes**: puede actuar como BFF (Backend for Frontend) para transformar respuestas
- **Built-in optimizations**: Image, Font, Bundle splitting automáticos
- **TypeScript first**: tipado end-to-end con los schemas del backend

### 7.5 ¿Por qué patrón de Debate (adversarial)?

El patrón de debate entre dos agentes con posiciones opuestas:
- Reduce el sesgo de confirmación inherente en un solo agente decisor
- Genera evidencia explícita a favor y en contra
- Permite al Arbiter hacer una evaluación balanceada
- Produce explicaciones más ricas para auditoría (se documentan ambos lados)
- Es un patrón reconocido en la literatura de AI Safety ("debate" de Irving et al., 2018)

### 7.6 ¿Por qué uv sobre pip/poetry/conda?

**uv** es un package manager ultrarrápido escrito en Rust que reemplaza pip, poetry, y virtualenv.

**Ventajas clave**:
- **Velocidad**: 10-100x más rápido en resolución de dependencias que pip
- **Python version management**: Descarga automática de Python 3.13 si no está instalado
- **Zero-config**: Compatible con `pyproject.toml`, `requirements.txt`, y `setup.py`
- **Single binary**: Sin dependencias de Python, instalación trivial
- **Drop-in replacement**: Comandos compatibles con pip (`uv pip install`, `uv sync`)
- **Determinismo**: Lock files automáticos para builds reproducibles

**Uso en el proyecto** (`backend/`):

```bash
# Instalar dependencias del proyecto
uv sync

# Instalar con dev dependencies
uv sync --group dev

# Ejecutar comando en el entorno virtual
uv run pytest

# Ejecutar servidor
uv run uvicorn app.main:app --reload
```

**Comparación**:

| Característica | uv | pip | poetry | conda |
|---------------|-----|-----|--------|-------|
| **Velocidad de instalación** | ⚡⚡⚡ | ⚡ | ⚡⚡ | ⚡ |
| **Gestión de Python versions** | ✅ | ❌ | ❌ | ✅ |
| **Lock files** | ✅ | ❌ | ✅ | ✅ |
| **Dependencias del sistema** | Cero (Rust binary) | Python | Python | Conda runtime |
| **Compatibilidad PyPI** | 100% | 100% | 100% | ~80% |

**Decisión**: uv es ideal para CI/CD (instalación rápida, reproducible) y desarrollo local (gestión automática de Python versions, experiencia de usuario excelente).

### 7.7 ¿Por qué shadcn/ui sobre MUI/Chakra/Ant Design?

**shadcn/ui** NO es una librería de componentes tradicional. Es un **sistema de componentes copiables** basado en Radix UI.

**Filosofía única**:
- **No es un npm package**: Los componentes se copian a tu proyecto (carpeta `components/ui/`)
- **Ownership total**: El código fuente es tuyo, modificable sin restricciones
- **No vendor lock-in**: Puedes usar shadcn/ui para el 80% y crear componentes custom para el resto
- **Tailwind-native**: Usa Tailwind CSS directamente, sin abstracciones de CSS-in-JS
- **TypeScript-first**: Tipos completos incluidos, excelente DX
- **Accesibilidad**: Basado en Radix UI primitives (cumple WAI-ARIA)

**Comparación con alternativas**:

| Característica | shadcn/ui | MUI | Chakra UI | Ant Design |
|---------------|-----------|-----|-----------|------------|
| **Instalación** | Copy/paste components | npm install | npm install | npm install |
| **Customización** | Modificar código directamente | Override theme | Override theme | Override theme + LESS |
| **Bundle size** | Solo lo que usas | ~300KB base | ~200KB base | ~500KB base |
| **Estilos** | Tailwind CSS | Emotion (CSS-in-JS) | Emotion | LESS |
| **Vendor lock-in** | ❌ Cero | ✅ Alto | ⚠️ Medio | ✅ Alto |
| **Accesibilidad** | ✅ Radix UI | ✅ | ✅ | ⚠️ |

**Implementación en el proyecto** (`frontend/src/components/`):

```
components/
├── ui/                           # 24 componentes base (shadcn/ui + JsonViewer)
│   ├── button.tsx
│   ├── card.tsx
│   ├── badge.tsx
│   ├── select.tsx
│   ├── dialog.tsx
│   ├── JsonViewer.tsx
│   └── ... (18 más)
├── dashboard/                    # Componentes de dominio (custom)
│   ├── StatsCards.tsx
│   ├── RecentDecisions.tsx
│   └── RiskDistribution.tsx
├── transactions/
│   ├── TransactionTable.tsx
│   └── TransactionDetailClient.tsx
├── policies/                     # NUEVO: Gestión CRUD de políticas
│   ├── PoliciesClient.tsx
│   ├── PolicyList.tsx
│   ├── PolicyCard.tsx
│   ├── PolicyForm.tsx
│   └── PolicyDeleteDialog.tsx
├── common/                       # NUEVO: Componentes compartidos
│   └── WebSocketStatus.tsx
└── ... (10 directorios, 54 componentes totales)
```

**Dependencias reales** (solo primitives de Radix UI):
```json
{
  "@radix-ui/react-avatar": "^1.1.11",
  "@radix-ui/react-dialog": "^1.1.15",
  "@radix-ui/react-select": "^2.2.6",
  "@radix-ui/react-tabs": "^1.1.13"
  // ... (solo lo que se usa)
}
```

**Decisión**: shadcn/ui permite **máxima flexibilidad** sin sacrificar velocidad de desarrollo. Para un proyecto de detección de fraude con requisitos de UI específicos (colores de decisión, gráficos custom, tablas complejas), tener control total del código frontend es más importante que la conveniencia de una librería empaquetada.

### 7.8 ¿Por qué constantes centralizadas (`constants.py`)?

**Archivo**: `backend/app/constants.py`

Todos los "magic numbers" del pipeline están centralizados en **6 modelos Pydantic** que actúan como single source of truth:

| Modelo | Propósito | Ejemplo |
|--------|-----------|---------|
| `BehavioralWeights` | Pesos de desviación conductual | `off_hours: 0.04`, `foreign_country: 0.20` |
| `AmountThresholds` | Umbrales de ratio de monto | `high_ratio: 3.0`, `velocity_ratio: 5.0` |
| `EvidenceWeights` | Pesos del score compuesto | `behavioral: 0.30`, `policy: 0.25` |
| `RiskThresholds` | Categorías de riesgo (0-100) | `low_max: 30.0`, `high_max: 80.0` |
| `SafetyOverrides` | Overrides del Decision Arbiter | `critical_risk_threshold: 85.0` |
| `AgentTimeouts` | Timeouts en segundos | `llm_call: 30.0`, `pipeline: 60.0` |

**Beneficios**:
- ✅ Validación automática por Pydantic (tipos, rangos)
- ✅ Un solo lugar para ajustar parámetros del pipeline
- ✅ Documentación inline (docstrings en cada modelo)
- ✅ Evita magic numbers dispersos en el código

### 7.9 ¿Por qué patrón "Thin Agent"?

Los agentes siguen el patrón de **orquestadores delgados**: cada agente es una función pequeña que coordina llamadas a utilidades y prompts, sin contener lógica pesada internamente.

**Separación de responsabilidades**:

| Capa | Directorio | Responsabilidad |
|------|-----------|-----------------|
| **Prompts** | `app/prompts/` | Templates de prompts LLM (5 módulos: policy, threat, debate, decision, explainability) |
| **Utils** | `app/utils/` | Helpers de dominio (debate_utils, decision_utils, policy_utils, threat_utils, llm_utils) |
| **Agents** | `app/agents/` | Orquestación: leer estado → llamar utils/prompts → escribir estado |

**Ejemplo** — El agente `decision_arbiter.py`:
1. Lee `evidence` y `debate` del estado
2. Construye el prompt usando `prompts/decision.py`
3. Invoca el LLM con `utils/llm_utils.py`
4. Aplica safety overrides con `utils/decision_utils.py`
5. Retorna `decision` al estado

**Beneficio**: Cada componente es testeable en aislamiento. Los prompts pueden iterarse sin tocar la lógica del agente.

### 7.10 ¿Por qué jerarquía de excepciones custom (`exceptions.py`)?

**Archivo**: `backend/app/exceptions.py`

El sistema define una jerarquía de excepciones que mapea a categorías específicas de error:

```
FraudDetectionError (base)
├── PolicyNotFoundError      → 404
├── PolicyExistsError        → 409
├── InvalidPolicyFormatError → 422
├── LLMParsingError          → 500 (JSON parse failure)
└── LLMTimeoutError          → 504 (timeout)
```

**Beneficios**:
- ✅ Routers mapean excepciones a HTTP status codes específicos
- ✅ Cada excepción incluye `details: dict` para debugging
- ✅ Los agentes capturan errores tipados en lugar de `Exception` genérico
- ✅ Logging estructurado incluye detalles de la excepción automáticamente

---

## 8. Flujo por Tipo de Decisión (Ejemplos con Datos Sintéticos)

```mermaid
graph TD
    subgraph "T-1003: APPROVE"
        T3[Monto: S/250<br/>País: PE<br/>Horario: 14:30<br/>Dispositivo: D-03]
        T3 --> T3D[✅ Dentro de parámetros<br/>FP-04 match<br/>Confidence: 0.95]
    end

    subgraph "T-1001: CHALLENGE"
        T1[Monto: S/1800<br/>3.6x promedio<br/>Horario: 03:15<br/>Dispositivo: D-01]
        T1 --> T1D[⚠️ Monto alto + fuera horario<br/>FP-01 match<br/>Confidence: 0.72]
    end

    subgraph "T-1004: BLOCK"
        T4[Monto: $15,000 USD<br/>7.5x promedio<br/>País: CO ≠ PE<br/>Dispositivo: D-99 ≠ D-04]
        T4 --> T4D[🚫 País + dispositivo + monto<br/>FP-03 + FP-06 match<br/>Confidence: 0.94]
    end

    subgraph "T-1004 alt: ESCALATE_TO_HUMAN"
        T4E[Monto: $15,000 USD<br/>País: CO ≠ PE<br/>Dispositivo: D-99 nuevo]
        T4E --> T4ED[👤 Internacional + dispositivo nuevo<br/>FP-02 match<br/>Confidence: 0.55]
    end

    style T3D fill:#22c55e,color:#fff
    style T1D fill:#f59e0b,color:#000
    style T4D fill:#ef4444,color:#fff
    style T4ED fill:#8b5cf6,color:#fff
```

---

## 9. Arquitectura de Despliegue

### 9.1 Entorno de Desarrollo Local (✅ COMPLETAMENTE IMPLEMENTADO)

**Descripción**: Sistema totalmente funcional que corre en localhost con Docker Compose.

```mermaid
graph TB
    subgraph "Host Machine - localhost"
        subgraph "Docker Compose (devops/docker-compose.yml)"
            PG[(PostgreSQL 16<br/>:5432<br/>fraud_detection DB)]
        end

        subgraph "Servicios Locales (no containerizados)"
            OL[Ollama<br/>:11434<br/>qwen3:30b]
            CHR[(ChromaDB<br/>Embedded<br/>./data/chroma)]
        end

        subgraph "Backend (uv run)"
            BE[FastAPI Server<br/>:8000<br/>Python 3.13]
        end

        subgraph "Frontend (npm run dev)"
            FE[Next.js 16<br/>:3000<br/>React 18]
        end
    end

    subgraph "Usuario"
        BROWSER[Browser<br/>http://localhost:3000]
    end

    BROWSER --> FE
    FE -->|API calls| BE
    FE -->|WebSocket| BE
    BE --> PG
    BE --> OL
    BE --> CHR

    style PG fill:#3b82f6,color:#fff
    style OL fill:#22c55e,color:#fff
    style CHR fill:#f59e0b,color:#000
    style BE fill:#8b5cf6,color:#fff
    style FE fill:#06b6d4,color:#fff
```

**Comandos de inicio**:

```bash
# 1. Iniciar PostgreSQL con Docker Compose
cd devops
docker compose up -d

# 2. Verificar Ollama está corriendo (host)
ollama serve  # Si no está ya corriendo
ollama pull qwen3:30b

# 3. Iniciar backend (desde backend/)
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 4. Iniciar frontend (desde frontend/)
cd frontend
npm install
npm run dev

# 5. Acceder a http://localhost:3000
```

**Configuración** (archivo `backend/.env`):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://fraud_user:fraud_pass_dev@localhost:5432/fraud_detection

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:30b

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# App
APP_ENV=development
LOG_LEVEL=DEBUG
```

**Ventajas del setup local**:
- ✅ Cero costos de LLM (Ollama es gratis)
- ✅ Desarrollo offline (no requiere internet después de descargar modelos)
- ✅ Hot reload en backend y frontend
- ✅ Debugging fácil con breakpoints
- ✅ ChromaDB embebido (sin servicios adicionales)

---

### 9.2 Entorno de Producción con Docker Compose (✅ IMPLEMENTADO)

**Descripción**: Setup containerizado completo para despliegue en servidor.

**Archivo**: `docker-compose.prod.yml` (raíz del repo)

```mermaid
graph TB
    subgraph "Docker Network - fraud-network"
        PG[(PostgreSQL 16<br/>Container<br/>fraud-db)]
        BE[Backend Container<br/>fraud-backend<br/>:8000]
        FE[Frontend Container<br/>fraud-frontend<br/>:3000]
    end

    subgraph "Host Machine"
        OL[Ollama<br/>:11434<br/>host.docker.internal]
    end

    BE --> PG
    BE --> OL
    FE --> BE

    style PG fill:#3b82f6,color:#fff
    style BE fill:#8b5cf6,color:#fff
    style FE fill:#06b6d4,color:#fff
```

**Servicios** (3 containers):
1. **postgres**: PostgreSQL 16 Alpine con healthcheck
2. **backend**: FastAPI + LangGraph con dependencies on postgres
3. **frontend**: Next.js production build

**Comandos**:
```bash
# Build y start de todos los servicios
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Detener
docker compose -f docker-compose.prod.yml down

# Rebuild después de cambios
docker compose -f docker-compose.prod.yml up --build
```

**Healthchecks implementados**:
- PostgreSQL: `pg_isready` cada 5s
- Backend: `curl /api/v1/health` cada 30s
- Frontend: HTTP check en :3000 cada 30s

---

### 9.3 Despliegue en Azure Cloud (⚠️ PLANIFICADO, NO IMPLEMENTADO)

**Nota**: Este despliegue está planificado pero no implementado. El sistema actual funciona completamente en desarrollo local y Docker Compose producción.

```mermaid
graph TB
    subgraph "Azure Cloud (PLANIFICADO)"
        subgraph "Azure Container Apps"
            BE[Backend Container<br/>FastAPI + LangGraph]
            FE[Frontend Container<br/>Next.js]
        end

        subgraph "Azure Managed Services"
            AOAI[Azure OpenAI<br/>GPT-4o]
            KV[Azure Key Vault<br/>Secrets]
            PG[(Azure PostgreSQL<br/>Flexible Server)]
            ACR[Azure Container<br/>Registry]
        end

        subgraph "Monitoring"
            AI[Application Insights]
            LA[Log Analytics]
        end
    end

    subgraph "CI/CD"
        GH[GitHub Actions]
        TF[Terraform]
    end

    GH -->|build & push| ACR
    ACR -->|deploy| BE & FE
    TF -->|provision| AOAI & KV & PG
    BE --> AOAI
    BE --> KV
    BE --> PG
    BE --> FE
    AI -.-> BE & FE

    style BE fill:#8b5cf6,color:#fff,stroke-dasharray: 5 5
    style FE fill:#06b6d4,color:#fff,stroke-dasharray: 5 5
    style AOAI fill:#22c55e,color:#fff,stroke-dasharray: 5 5
    style PG fill:#3b82f6,color:#fff,stroke-dasharray: 5 5
```

**Componentes planeados**:
- **Azure Container Apps**: Despliegue serverless de containers
- **Azure OpenAI**: Reemplazo de Ollama para GPT-4o
- **Azure PostgreSQL Flexible Server**: Base de datos gestionada
- **Azure Key Vault**: Gestión segura de secrets
- **Application Insights**: Telemetría y métricas
- **Terraform**: IaC para provisión de infraestructura

**Migración requerida**:
1. Cambiar `OLLAMA_BASE_URL` → `AZURE_OPENAI_ENDPOINT`
2. Cambiar modelo `qwen3:30b` → `gpt-4o`
3. Actualizar `DATABASE_URL` a Azure PostgreSQL connection string
4. Configurar managed identities para Key Vault
5. Agregar Application Insights SDK

---

## 10. Endpoints API (FastAPI)

**Documentación interactiva**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Endpoints Implementados

#### Transacciones (`/api/v1/transactions`)

| Método | Endpoint | Descripción | Estado | Request Body | Response |
|--------|----------|-------------|--------|--------------|----------|
| POST | `/analyze` | Analizar transacción individual (pipeline completo) | ✅ | `Transaction` + `CustomerBehavior` | `FraudDecision` |
| POST | `/analyze/batch` | Analizar múltiples transacciones en paralelo | ✅ | `List[Transaction + Behavior]` | `List[FraudDecision]` |
| GET | `/` | Listar todas las transacciones analizadas | ✅ | - | `List[TransactionRecord]` |
| GET | `/{transaction_id}/result` | Obtener decisión de una transacción (incluye `hitl` si hay caso asociado) | ✅ | - | `FraudDecision` + `hitl?` |
| GET | `/{transaction_id}/trace` | Obtener traza completa de agentes | ✅ | - | `List[AgentTraceEntry]` |

**Ejemplo de uso**:
```bash
# Analizar transacción
curl -X POST http://localhost:8000/api/v1/transactions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {...},
    "customer_behavior": {...}
  }'

# Ver resultado
curl http://localhost:8000/api/v1/transactions/T-1001/result
```

**Campo `hitl` en respuesta de `GET /{transaction_id}/result`**:

Si la transacción tiene un caso HITL asociado, el campo `hitl` contendrá los datos de resolución:

```json
{
  "decision": "ESCALATE_TO_HUMAN",
  "confidence": 0.55,
  "...": "...",
  "hitl": {
    "case_id": 1,
    "status": "resolved",
    "resolution": "APPROVE: Cliente confirmó la transacción por teléfono",
    "resolved_at": "2026-02-16T10:30:00Z"
  }
}
```

- Si no hay caso HITL asociado, `hitl` será `null`
- El campo `resolution` sigue el formato `"DECISION: razón"` (ej. `"APPROVE: razón"` o `"BLOCK: razón"`)
- El frontend parsea este formato para mostrar la decisión humana con badge de color y la justificación por separado

#### HITL - Human-in-the-Loop (`/api/v1/hitl`)

| Método | Endpoint | Descripción | Estado | Request Body | Response |
|--------|----------|-------------|--------|--------------|----------|
| GET | `/queue` | Obtener cola de casos escalados a humanos | ✅ | `?status=pending` (opcional) | `List[HITLCase]` |
| POST | `/{case_id}/resolve` | Resolver caso con decisión humana | ✅ | `reviewer_id`, `decision`, `rationale` | `HITLCase` |
| GET | `/{case_id}` | Obtener detalle de caso HITL | ✅ | - | `HITLCase` |

**Ejemplo de uso**:
```bash
# Ver cola HITL
curl http://localhost:8000/api/v1/hitl/queue?status=pending

# Resolver caso
curl -X POST http://localhost:8000/api/v1/hitl/1/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "analyst_01",
    "human_decision": "BLOCK",
    "human_rationale": "Confirmado fraude después de contactar cliente"
  }'
```

#### Políticas (`/api/v1/policies`)

| Método | Endpoint | Descripción | Estado | Request Body | Response |
|--------|----------|-------------|--------|--------------|----------|
| GET | `/` | Listar todas las políticas de fraude | ✅ | - | `List[PolicyResponse]` |
| GET | `/{policy_id}` | Obtener política por ID (ej. FP-01) | ✅ | - | `PolicyResponse` |
| POST | `/` | Crear nueva política (genera .md + reingest ChromaDB) | ✅ | `PolicyCreate` | `PolicyResponse` (201) |
| PUT | `/{policy_id}` | Actualizar política existente (parcial) | ✅ | `PolicyUpdate` | `PolicyResponse` |
| DELETE | `/{policy_id}` | Eliminar política (.md + ChromaDB) | ✅ | - | 204 No Content |
| POST | `/reingest` | Re-ingestar manualmente todas las políticas en ChromaDB | ✅ | - | 202 Accepted |

**Ejemplo de uso**:
```bash
# Listar políticas
curl http://localhost:8000/api/v1/policies

# Crear nueva política
curl -X POST http://localhost:8000/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "FP-07",
    "title": "Nueva Política",
    "description": "Descripción detallada...",
    "criteria": ["criterio 1"],
    "thresholds": ["umbral 1"],
    "action_recommended": "CHALLENGE",
    "severity": "MEDIUM"
  }'
```

#### Analytics (`/api/v1/analytics`)

| Método | Endpoint | Descripción | Estado | Query Params | Response |
|--------|----------|-------------|--------|--------------|----------|
| GET | `/summary` | Métricas agregadas del sistema | ✅ | - | `AnalyticsSummary` |
| GET | `/decisions` | Distribución de decisiones por tipo | ✅ | `?period=7d` | `DecisionDistribution` |
| GET | `/agents/performance` | Performance de agentes individuales | ✅ | - | `AgentPerformanceMetrics` |

**Métricas incluidas**:
- Total de transacciones analizadas
- Distribución de decisiones (APPROVE/CHALLENGE/BLOCK/ESCALATE)
- Tiempo promedio de análisis
- Tasa de escalación a HITL
- Precisión de agentes (cuando hay ground truth)
- Confidence scores promedio por tipo de decisión

#### WebSocket (`/api/v1/ws`)

| Protocolo | Endpoint | Descripción | Estado | Eventos |
|-----------|----------|-------------|--------|---------|
| WS | `/transactions` | Stream de eventos de agentes en tiempo real | ✅ | `agent_started`, `agent_completed`, `agent_error`, `decision_ready` |

**Uso del WebSocket**:
```javascript
// Frontend (lib/websocket.ts)
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/transactions');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  // { event: "agent_completed", agent: "policy_rag", duration_ms: 1234 }
};
```

**Eventos emitidos**:
- `agent_started`: Un agente comenzó su ejecución
- `agent_completed`: Un agente terminó exitosamente
- `agent_error`: Un agente falló
- `decision_ready`: Decisión final disponible
- `hitl_escalated`: Transacción escalada a cola HITL

#### Sistema (`/api/v1`)

| Método | Endpoint | Descripción | Estado | Response |
|--------|----------|-------------|--------|----------|
| GET | `/health` | Health check del sistema | ✅ | `{"status": "ok", "timestamp": "..."}` |
| GET | `/docs` | Documentación interactiva Swagger UI | ✅ | HTML |
| GET | `/redoc` | Documentación interactiva ReDoc | ✅ | HTML |
| GET | `/openapi.json` | Especificación OpenAPI 3.1 | ✅ | JSON |

---

## 11. Estructura Final del Proyecto

**Nota**: Esta estructura refleja el estado actual del repositorio (commit fa32866).

```
fraud-detection-multi-agent-system/
├── backend/                           # Backend FastAPI + LangGraph
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app + routers + CORS
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── constants.py               # Constantes centralizadas (6 modelos Pydantic)
│   │   ├── dependencies.py            # Dependency injection (LLM, DB session)
│   │   ├── exceptions.py              # Jerarquía de excepciones custom
│   │   ├── models/                    # Pydantic models (9 archivos)
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py         # Transaction, CustomerBehavior
│   │   │   ├── signals.py             # TransactionSignals, BehavioralSignals
│   │   │   ├── evidence.py            # PolicyMatch, ThreatIntel, AggregatedEvidence
│   │   │   ├── debate.py              # DebateArguments
│   │   │   ├── decision.py            # FraudDecision, ExplanationResult
│   │   │   ├── trace.py               # AgentTraceEntry, OrchestratorState
│   │   │   ├── policy.py              # PolicyBase, PolicyCreate, PolicyUpdate, PolicyResponse
│   │   │   └── analyze_request.py     # AnalyzeRequest (transaction + behavior)
│   │   ├── agents/                    # 8 agentes + orchestrator (10 archivos)
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # LangGraph StateGraph + asyncio.gather
│   │   │   ├── transaction_context.py # Señales determinísticas
│   │   │   ├── behavioral_pattern.py  # Análisis de desviación comportamental
│   │   │   ├── policy_rag.py          # ChromaDB + LLM para políticas
│   │   │   ├── external_threat.py     # Multi-provider threat intel + LLM synthesis
│   │   │   ├── evidence_aggregator.py # Consolidación matemática + narrativa
│   │   │   ├── debate.py              # Pro-Fraud + Pro-Customer (adversarial)
│   │   │   ├── decision_arbiter.py    # Evaluación final LLM + safety overrides
│   │   │   └── explainability.py      # Generación de explicaciones duales
│   │   ├── prompts/                   # Templates de prompts LLM (5 módulos)
│   │   │   ├── __init__.py
│   │   │   ├── policy.py              # Prompts del PolicyRAG agent
│   │   │   ├── threat.py              # Prompts del ExternalThreat agent
│   │   │   ├── debate.py              # Prompts Pro-Fraud + Pro-Customer
│   │   │   ├── decision.py            # Prompts del Decision Arbiter
│   │   │   └── explainability.py      # Prompts del Explainability agent
│   │   ├── db/                        # Capa de base de datos PostgreSQL
│   │   │   ├── __init__.py
│   │   │   ├── engine.py              # AsyncEngine + init_db
│   │   │   └── models.py              # SQLAlchemy models (TransactionRecord, AgentTrace, HITLCase)
│   │   ├── rag/                       # ChromaDB vector store
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py        # Query functions
│   │   │   └── ingest.py              # Ingestion de políticas
│   │   ├── services/                  # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── seed_service.py        # Ingesta de datos sintéticos
│   │   │   ├── policy_service.py      # Policy CRUD orchestration
│   │   │   ├── policy_parser.py       # Markdown ↔ PolicyResponse parser
│   │   │   ├── policy_repository.py   # Filesystem I/O para policies .md
│   │   │   └── threat_intel/          # Threat Intelligence providers
│   │   │       ├── __init__.py
│   │   │       ├── base.py            # ThreatProvider ABC interface
│   │   │       ├── manager.py         # ThreatIntelManager (fan-out paralelo)
│   │   │       ├── country_risk.py    # CountryRiskProvider (FATF lists)
│   │   │       ├── osint_search.py    # OSINTSearchProvider (DuckDuckGo)
│   │   │       └── sanctions_screening.py # SanctionsProvider (OpenSanctions)
│   │   ├── routers/                   # FastAPI route handlers (5 archivos)
│   │   │   ├── __init__.py
│   │   │   ├── health.py              # GET /health
│   │   │   ├── transactions.py        # POST /analyze, GET /{id}/trace
│   │   │   ├── hitl.py                # GET /queue, POST /{id}/resolve
│   │   │   ├── policies.py            # CRUD /policies + POST /reingest
│   │   │   └── websocket.py           # WS /transactions (real-time events)
│   │   └── utils/                     # Utilities (9 módulos)
│   │       ├── __init__.py
│   │       ├── logger.py              # structlog configuration
│   │       ├── timing.py              # @timed_agent decorator
│   │       ├── shared_utils.py        # parse_usual_hours, is_time_in_range
│   │       ├── llm_utils.py           # JSON parsing, LLM call helpers
│   │       ├── debate_utils.py        # Debate argument formatting
│   │       ├── decision_utils.py      # Safety overrides, citations, fallback
│   │       ├── policy_utils.py        # Policy matching helpers
│   │       └── threat_utils.py        # Threat analysis helpers
│   ├── alembic/                       # Database migrations
│   │   ├── versions/
│   │   │   ├── ac4fa394c551_add_analysis_state_to_transaction_.py
│   │   │   └── 685da8fe2597_add_llm_and_rag_trace_fields.py
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── data/
│   │   ├── synthetic_data.json        # 6 transacciones sintéticas (T-1001 a T-1006)
│   │   ├── README.md                  # Descripción de datos sintéticos
│   │   └── chroma/                    # ChromaDB persistent directory (gitignored)
│   ├── policies/                      # Políticas individuales (1 archivo .md por política)
│   │   ├── FP-01.md                   # Montos significativamente superiores
│   │   ├── FP-02.md                   # Transacciones desde países no habituales
│   │   ├── FP-03.md                   # Dispositivos no reconocidos
│   │   ├── FP-04.md                   # Horarios inusuales
│   │   ├── FP-05.md                   # Patrones de velocidad sospechosos
│   │   └── FP-06.md                   # Combinación de múltiples señales
│   ├── scripts/                       # Scripts de utilidad
│   │   ├── demo.py                    # Demo end-to-end con Rich CLI
│   │   ├── verify_api.py              # Verificación de endpoints
│   │   └── seed_test.py               # Ingesta de datos sintéticos
│   ├── tests/                         # Test suite (pytest, 21+ archivos)
│   │   ├── conftest.py                # Fixtures compartidos
│   │   ├── test_agents/               # Tests de agentes (10 archivos)
│   │   │   ├── test_transaction_context.py
│   │   │   ├── test_behavioral_pattern.py
│   │   │   ├── test_policy_rag.py
│   │   │   ├── test_external_threat_providers.py
│   │   │   ├── test_external_threat_refactored.py
│   │   │   ├── test_evidence_aggregator.py
│   │   │   ├── test_debate.py
│   │   │   ├── test_decision_arbiter.py
│   │   │   ├── test_explainability.py
│   │   │   └── test_orchestrator.py
│   │   ├── test_routers/              # Tests de endpoints (5 archivos)
│   │   │   ├── test_health.py
│   │   │   ├── test_transactions.py
│   │   │   ├── test_hitl.py
│   │   │   ├── test_policies.py
│   │   │   └── test_websocket.py
│   │   ├── test_services/             # Tests de servicios (4 archivos)
│   │   │   ├── test_policy_service.py
│   │   │   ├── test_threat_intel_osint.py
│   │   │   ├── test_threat_intel_country_risk.py
│   │   │   └── test_threat_intel_manager.py
│   │   └── test_rag/                  # Tests de RAG
│   │       └── test_vector_store.py
│   ├── Dockerfile                     # Multi-stage build (uv + Python 3.13)
│   ├── .env.example                   # Environment variables template
│   ├── pyproject.toml                 # uv project definition (Python >=3.13)
│   └── README.md                      # Backend documentation
│
├── frontend/                          # Frontend Next.js 16
│   ├── src/
│   │   ├── app/                       # Next.js App Router (6 páginas)
│   │   │   ├── layout.tsx             # Root layout con sidebar + header
│   │   │   ├── page.tsx               # Dashboard principal (stats + charts)
│   │   │   ├── error.tsx              # Error boundary
│   │   │   ├── loading.tsx            # Loading state
│   │   │   ├── not-found.tsx          # 404 page
│   │   │   ├── transactions/
│   │   │   │   ├── page.tsx           # Lista de transacciones + tabla
│   │   │   │   └── [id]/page.tsx      # Detalle + trace + debate
│   │   │   ├── hitl/
│   │   │   │   └── page.tsx           # Cola HITL + form de resolución
│   │   │   ├── analytics/
│   │   │   │   └── page.tsx           # Métricas + distribución + trends
│   │   │   └── policies/
│   │   │       └── page.tsx           # Gestión CRUD de políticas
│   │   ├── components/                # 54 componentes React (10 subdirectorios)
│   │   │   ├── layout/                # Header, Sidebar, MobileSidebar
│   │   │   ├── dashboard/             # StatsCards, RecentDecisions, RiskDistribution
│   │   │   ├── transactions/          # TransactionTable, TransactionsClient, TransactionDetailClient,
│   │   │   │                          #   TransactionDetailCard, DecisionCard, AnalyzeButton
│   │   │   ├── agents/                # AgentTraceTimeline, DebateView, LLMInteractionViewer, RAGQueryViewer
│   │   │   ├── hitl/                  # HITLQueue, HITLReviewForm
│   │   │   ├── analytics/             # DecisionBreakdownChart, ProcessingTimeChart,
│   │   │   │                          #   ConfidenceDistribution, RiskByCountry
│   │   │   ├── explanation/           # CustomerExplanation, AuditExplanation
│   │   │   ├── policies/              # PoliciesClient, PolicyList, PolicyCard,
│   │   │   │                          #   PolicyForm, PolicyDeleteDialog
│   │   │   ├── common/                # WebSocketStatus
│   │   │   └── ui/                    # 24 shadcn/ui + custom components (button, card, badge, dialog, JsonViewer, etc.)
│   │   ├── lib/
│   │   │   ├── api.ts                 # Fetch wrapper con error handling
│   │   │   ├── types.ts               # TypeScript interfaces (mirror Pydantic models)
│   │   │   ├── utils.ts               # Helper functions (cn, formatters)
│   │   │   └── constants.ts           # Constantes frontend
│   │   └── hooks/                     # 4 custom hooks
│   │       ├── useTransactions.ts     # Hook para transacciones
│   │       ├── useWebSocket.ts        # WebSocket con reconnect + circuit breaker
│   │       ├── useSystemHealth.ts     # Hook de health check
│   │       └── use-toast.ts           # Hook de notificaciones toast
│   ├── public/                        # Static assets
│   ├── Dockerfile                     # Next.js production build
│   ├── package.json                   # Dependencies (Next.js ^16.1.6, React ^18)
│   ├── tailwind.config.ts             # Tailwind + shadcn/ui config
│   ├── next.config.ts                 # Next.js config
│   └── tsconfig.json                  # TypeScript config (strict mode)
│
├── devops/                            # Docker Compose configs
│   ├── docker-compose.yml             # PostgreSQL 16 para desarrollo local
│   └── README.md                      # Instrucciones de Docker
│
├── docker-compose.prod.yml            # Producción: 3 servicios (postgres, backend, frontend)
│
├── docs/                              # Documentación
│   ├── images/                        # Screenshots del sistema
│   │   ├── dashboard.png
│   │   ├── transaction-detail.png
│   │   └── agent-timeline.png
│   └── README.md                      # Índice de documentación
│
├── .claude/                           # Claude Code memory + docs
│   ├── docs/
│   │   └── arquitectura-sistema.md    # Este archivo (arquitectura completa)
│   └── memory/
│       └── MEMORY.md                  # Patrones aprendidos
│
├── .env.example                       # Environment variables template
├── .gitignore                         # Python, Node, ChromaDB, .env
├── Makefile                           # Comandos útiles (install, dev, test, docker-up)
├── README.md                          # README principal del proyecto
└── CLAUDE.md                          # Instrucciones para Claude Code
```

**Conteo de archivos**:
- **Backend**: ~65 archivos Python (.py)
- **Frontend**: 54 componentes React (.tsx) + 4 custom hooks
- **Total componentes frontend**:
  - 24 componentes UI base (shadcn/ui + JsonViewer)
  - 30 componentes de dominio (dashboard, transactions, agents, hitl, analytics, policies, common)
  - 3 componentes de layout
- **Tests**: 21 archivos de test (pytest) en 4 subdirectorios
- **Migrations**: 2 Alembic migrations (initial schema + LLM/RAG trace fields)
- **Docker**: 3 Dockerfiles + 2 docker-compose configs
- **Docs**: 3 archivos de documentación + 3 screenshots
- **Páginas frontend**: 6 (dashboard, transactions, transaction detail, hitl, analytics, policies)

---

## 12. Decisiones Clave para la Implementación

### 12.1 Agentes con LLM vs Agentes Determinísticos

No todos los agentes necesitan un LLM. Diseño híbrido optimizado para costo y latencia:

| Agente | Tipo | Justificación | Implementación | Archivo |
|--------|------|---------------|----------------|---------|
| Transaction Context | **Determinístico** | Reglas de negocio claras (ratios, horarios, país) | Cálculos matemáticos + comparaciones | `transaction_context.py` |
| Behavioral Pattern | **Determinístico** | Comparación directa contra historial | Desviación estándar + anomaly detection | `behavioral_pattern.py` |
| Policy RAG | **LLM + RAG** | Necesita entender semántica de políticas | ChromaDB query + LLM relevance scoring | `policy_rag.py` |
| External Threat | **LLM + Multi-Provider** | Múltiples fuentes requieren agregación e interpretación | FATF + OSINT + Sanctions → LLM synthesis | `external_threat.py` |
| Evidence Aggregation | **Determinístico** | Agregación matemática pura | Weighted average + categorization | `evidence_aggregator.py` |
| Debate Pro-Fraud | **LLM** | Argumentación requiere razonamiento | LLM prompt engineering | `debate.py:debate_pro_fraud_agent` |
| Debate Pro-Customer | **LLM** | Argumentación requiere razonamiento | LLM prompt engineering | `debate.py:debate_pro_customer_agent` |
| Decision Arbiter | **LLM** | Evaluación balanceada de argumentos | LLM con context window de evidencia completa | `decision_arbiter.py` |
| Explainability | **LLM** | Generación de lenguaje natural dual | LLM con templates customer/audit | `explainability.py` |

**Impacto en costos** (estimado con Ollama local = $0, Azure OpenAI futuro):
- 2 agentes determinísticos (0 llamadas LLM) → $0
- 6 agentes con LLM (1 llamada cada uno) → ~6 llamadas por transacción
- Con GPT-4o en Azure: ~$0.015/transacción (6 llamadas × $0.0025/llamada promedio)
- Con Ollama local: $0/transacción

**Impacto en latencia**:
- Agentes determinísticos: <50ms cada uno
- Agentes LLM: 800-2000ms cada uno (según modelo y complejidad)
- Total pipeline: ~4-6 segundos (paralelismo reduce impacto)

### 12.2 Manejo de Errores y Resiliencia (Implementación Real)

**Archivo**: `backend/app/utils/timing.py` + cada agente individual

#### Timeouts Configurables con Decorador

```python
def timed_agent(agent_name: str):
    """Decorator to add timing, timeout, and trace logging to agents."""
    def decorator(func):
        async def wrapper(state: OrchestratorState) -> dict:
            start = time.perf_counter()
            try:
                # Execute with 30s timeout
                result = await asyncio.wait_for(func(state), timeout=30.0)
                duration_ms = (time.perf_counter() - start) * 1000

                # Add successful trace entry
                trace_entry = AgentTraceEntry(
                    agent_name=agent_name,
                    timestamp=datetime.now(UTC),
                    duration_ms=duration_ms,
                    status="success"
                )
                result["trace"] = result.get("trace", []) + [trace_entry]
                return result

            except asyncio.TimeoutError:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(f"{agent_name}_timeout", timeout_seconds=30)

                # Return safe default with error trace
                trace_entry = AgentTraceEntry(
                    agent_name=agent_name,
                    timestamp=datetime.now(UTC),
                    duration_ms=duration_ms,
                    status="timeout"
                )
                return {"trace": [trace_entry]}  # Pipeline continues

            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(f"{agent_name}_error", error=str(e), exc_info=True)

                trace_entry = AgentTraceEntry(
                    agent_name=agent_name,
                    timestamp=datetime.now(UTC),
                    duration_ms=duration_ms,
                    status="error"
                )
                return {"trace": [trace_entry]}  # Graceful degradation

        return wrapper
    return decorator
```

**Uso en agentes**:
```python
@timed_agent("policy_rag")
async def policy_rag_agent(state: OrchestratorState) -> dict:
    # Si toma >30s → timeout automático
    # Si falla → error trace, pipeline continúa
    ...
```

#### Retry con Exponential Backoff (External Threat)

**Archivo**: `backend/app/agents/external_threat.py`

```python
async def _call_llm_with_retry(llm: ChatOllama, prompt: str, max_retries: int = 3) -> str:
    """Call LLM with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=25.0)
            return response.content
        except asyncio.TimeoutError:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"llm_retry", attempt=attempt, wait_seconds=wait_time)
            await asyncio.sleep(wait_time)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded")
```

#### Circuit Breaker en Agentes Externos

**Ejemplo**: `external_threat_agent`

```python
@timed_agent("external_threat")
async def external_threat_agent(state: OrchestratorState) -> dict:
    try:
        # Intento de web search
        search_results = await ddg_search(query)

        # Análisis con LLM
        threat_intel = await _analyze_threats(llm, search_results)
        return {"threat_intel": threat_intel}

    except Exception as e:
        logger.error("external_threat_circuit_breaker", error=str(e))
        # Circuit breaker: retornar resultado seguro en lugar de crashear
        return {
            "threat_intel": ThreatIntelResult(
                threat_level=0.0,  # Sin amenazas detectadas
                sources=[]
            )
        }
```

**Resultado**: Pipeline continúa sin `threat_intel`, otros agentes compensan.

### 12.3 WebSocket para Actualizaciones en Tiempo Real (Implementación Real)

**Archivo**: `backend/app/routers/websocket.py`

El análisis completo toma ~4-6 segundos. El frontend recibe eventos en tiempo real vía WebSocket.

#### Backend - Emisión de Eventos

```python
from fastapi import WebSocket
from typing import Dict, Set

# Store de conexiones activas
active_connections: Set[WebSocket] = set()

@router.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_event(event: dict):
    """Broadcast event to all connected clients."""
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except Exception:
            disconnected.add(connection)

    # Cleanup disconnected clients
    active_connections.difference_update(disconnected)
```

**Eventos emitidos durante el pipeline**:

```python
# Cuando un agente comienza
await broadcast_event({
    "event": "agent_started",
    "agent": "transaction_context",
    "timestamp": "2026-02-14T10:30:00Z"
})

# Cuando un agente termina
await broadcast_event({
    "event": "agent_completed",
    "agent": "transaction_context",
    "duration_ms": 45,
    "status": "success"
})

# Cuando hay decisión final
await broadcast_event({
    "event": "decision_ready",
    "transaction_id": "T-1001",
    "decision": "CHALLENGE",
    "confidence": 0.72
})
```

#### Frontend - Conexión WebSocket con Circuit Breaker

**Archivo**: `frontend/src/hooks/use-websocket.ts`

```typescript
export function useWebSocket() {
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/transactions');

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      reconnectAttempts.current = 0;  // Reset counter
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      // Exponential backoff reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
        reconnectAttempts.current++;
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
        setTimeout(connect, delay);
      } else {
        console.error('Max reconnect attempts reached. Circuit breaker open.');
      }
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { events, isConnected };
}
```

**Uso en componentes**:

```typescript
function TransactionDetail({ id }: Props) {
  const { events } = useWebSocket();

  // Filtrar eventos de esta transacción
  const transactionEvents = events.filter(e => e.transaction_id === id);

  return (
    <div>
      {transactionEvents.map(event => (
        <AgentTimelineItem key={event.timestamp} event={event} />
      ))}
    </div>
  );
}
```

**Flujo de eventos real**:

```
[00:00.000] {"event": "agent_started", "agent": "validate_input"}
[00:00.012] {"event": "agent_completed", "agent": "validate_input", "duration_ms": 12}
[00:00.015] {"event": "agent_started", "agent": "transaction_context"}
[00:00.015] {"event": "agent_started", "agent": "policy_rag"}
[00:00.015] {"event": "agent_started", "agent": "external_threat"}
[00:00.058] {"event": "agent_completed", "agent": "transaction_context", "duration_ms": 43}
[00:02.341] {"event": "agent_completed", "agent": "policy_rag", "duration_ms": 2326}
[00:03.712] {"event": "agent_completed", "agent": "external_threat", "duration_ms": 3697}
[00:03.756] {"event": "agent_started", "agent": "evidence_aggregation"}
[00:03.801] {"event": "agent_completed", "agent": "evidence_aggregation", "duration_ms": 45}
... (debate, arbiter, explainability)
[00:05.234] {"event": "decision_ready", "transaction_id": "T-1001", "decision": "CHALLENGE"}
```

**Beneficios**:
- ✅ UI reactiva (usuario ve progreso en vivo)
- ✅ Debugging facilitado (trace visual del pipeline)
- ✅ Reconexión automática con exponential backoff
- ✅ Circuit breaker evita loops infinitos de reconexión

---

## 13. Scripts y Utilidades

El proyecto incluye scripts de utilidad para demostración, testing y verificación del sistema.

### 13.1 Demo End-to-End (`backend/scripts/demo.py`)

**Propósito**: Demostración completa del pipeline con interfaz Rich CLI.

**Funcionalidad**:
1. Ingesta de políticas de fraude en ChromaDB (6 políticas)
2. Carga de datos sintéticos (6 transacciones)
3. Análisis secuencial con progreso visual
4. Tabla resumen con métricas de performance
5. Vista detallada de debate adversarial
6. Cálculo de accuracy vs ground truth

**Uso**:
```bash
cd backend
uv run python scripts/demo.py
```

**Output esperado**:

```
╔════════════════════════════════════════════════════════════╗
║     Fraud Detection Multi-Agent System                     ║
║     End-to-End Pipeline Demo                               ║
╚════════════════════════════════════════════════════════════╝

Step 1: Ingesting fraud policies into ChromaDB
✓ Ingested 6 policies with 24 chunks

Step 2: Loading synthetic data
✓ Loaded 6 transactions

Step 3: Analyzing transactions
⠋ Analyzing T-1001... 4.2s
⠋ Analyzing T-1002... 5.1s
...

╔═══════════════════════════════════════════════════════════════════════════╗
║                           RESULTS SUMMARY                                  ║
╠═══════════════╦═══════════╦════════════╦══════════╦═══════════════════════╣
║ Transaction   ║ Decision  ║ Confidence ║ Duration ║ Expected              ║
╠═══════════════╬═══════════╬════════════╬══════════╬═══════════════════════╣
║ T-1001        ║ CHALLENGE ║ 0.72       ║ 4.2s     ║ ✓ CHALLENGE           ║
║ T-1002        ║ BLOCK     ║ 0.94       ║ 5.1s     ║ ✓ BLOCK               ║
║ T-1003        ║ APPROVE   ║ 0.95       ║ 3.8s     ║ ✓ APPROVE             ║
║ T-1004        ║ ESCALATE  ║ 0.55       ║ 4.5s     ║ ✓ ESCALATE_TO_HUMAN   ║
║ T-1005        ║ CHALLENGE ║ 0.78       ║ 4.0s     ║ ✓ CHALLENGE           ║
║ T-1006        ║ BLOCK     ║ 0.96       ║ 5.3s     ║ ✓ BLOCK               ║
╠═══════════════╩═══════════╩════════════╩══════════╩═══════════════════════╣
║ Accuracy: 100% (6/6)                                                       ║
║ Avg Confidence: 0.82                                                       ║
║ Avg Duration: 4.5s                                                         ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Implementación destacada**:
- Usa Rich para UI en terminal (tablas, spinners, panels)
- Procesa transacciones secuencialmente para visualización clara
- Calcula métricas de performance automáticamente
- Muestra debate completo de una transacción como ejemplo

### 13.2 Verificación de API (`backend/scripts/verify_api.py`)

**Propósito**: Verificar que todos los endpoints de la API estén funcionando correctamente.

**Funcionalidad**:
- Verifica health check (`/api/v1/health`)
- Analiza una transacción de prueba (`POST /api/v1/transactions/analyze`)
- Verifica trace endpoint (`GET /api/v1/transactions/{id}/trace`)
- Verifica lista de transacciones (`GET /api/v1/transactions`)
- Verifica analytics (`GET /api/v1/analytics/summary`)
- Verifica HITL queue (`GET /api/v1/hitl/queue`)

**Uso**:
```bash
cd backend
uv run python scripts/verify_api.py
```

**Output**:
```
✓ Health check: OK
✓ Analyze transaction: OK (decision=CHALLENGE, confidence=0.72)
✓ Get trace: OK (9 agent traces)
✓ List transactions: OK (1 transactions)
✓ Analytics summary: OK
✓ HITL queue: OK (0 pending cases)

All endpoints verified successfully!
```

### 13.3 Datos Sintéticos (`backend/data/`)

**Archivo principal**: `backend/data/synthetic_data.json`

**Contenido**: 6 transacciones de prueba diseñadas para cubrir todos los outcomes posibles.

| Transaction ID | Características | Expected Decision | Confidence |
|---------------|----------------|-------------------|------------|
| **T-1001** | Monto 3.6x promedio, horario nocturno (03:15) | CHALLENGE | ~0.72 |
| **T-1002** | Monto muy alto (7.5x), país extranjero (CO≠PE), dispositivo desconocido | BLOCK | ~0.94 |
| **T-1003** | Monto normal (S/250), horario normal (14:30), dispositivo conocido | APPROVE | ~0.95 |
| **T-1004** | Monto moderado-alto, país OK, señales ambiguas | ESCALATE_TO_HUMAN | ~0.55 |
| **T-1005** | Monto alto (S/2500), dispositivo nuevo, país OK | CHALLENGE | ~0.78 |
| **T-1006** | Todos los factores de riesgo presentes | BLOCK | ~0.96 |

**Políticas asociadas** (`backend/policies/fraud_policies.md`):
- **FP-01**: Montos significativamente superiores al promedio
- **FP-02**: Transacciones desde países no habituales
- **FP-03**: Uso de dispositivos no reconocidos
- **FP-04**: Transacciones en horarios inusuales
- **FP-05**: Patrones de velocidad sospechosos
- **FP-06**: Combinación de múltiples señales de riesgo

**Documentación**: Ver `backend/data/README.md` para detalles completos.

### 13.4 Makefile (`Makefile` en raíz del repo)

**Comandos útiles** para desarrollo:

```makefile
# Ver todos los comandos disponibles
make help

# Instalación
make install              # Instalar dependencias backend + frontend
make install-backend      # Solo backend (uv sync)
make install-frontend     # Solo frontend (npm install)

# Desarrollo
make dev                  # Iniciar todos los servicios (PostgreSQL, backend, frontend)
make backend              # Solo backend (uvicorn --reload)
make frontend             # Solo frontend (npm run dev)

# Docker
make docker-up            # Iniciar PostgreSQL con Docker Compose
make docker-down          # Detener PostgreSQL
make docker-logs          # Ver logs de PostgreSQL

# Testing
make test                 # Ejecutar todos los tests (pytest)
make test-coverage        # Tests con coverage report

# Limpieza
make clean                # Limpiar cache de Python (__pycache__, .pyc)
make clean-all            # Limpiar todo (cache, ChromaDB, node_modules)

# Demo
make demo                 # Ejecutar demo end-to-end
```

**Ejemplo de uso**:
```bash
# Setup inicial
git clone <repo>
cd fraud-detection-multi-agent-system
make install

# Desarrollo
make docker-up    # Iniciar PostgreSQL
make dev          # En terminal 1: backend + frontend

# Testing
make test         # Ejecutar test suite

# Demo
make demo         # Ver demostración completa
```

---

## 14. Documentación Visual

El proyecto incluye documentación visual para facilitar el onboarding y presentaciones.

### 14.1 Screenshots del Sistema

**Ubicación**: `docs/images/`

**Imágenes disponibles**:

1. **dashboard.png**: Vista principal del dashboard
   - Cards de estadísticas (Total, Approve, Challenge, Block, HITL)
   - Gráfico de distribución de decisiones (pie chart)
   - Lista de decisiones recientes

2. **transaction-detail.png**: Vista detallada de una transacción
   - Header con ID, monto, decisión, confidence
   - Timeline de agentes con duración individual
   - Panel de debate adversarial (Pro-Fraud vs Pro-Customer)
   - Explicaciones duales (customer-facing + audit)

3. **agent-timeline.png**: Visualización del flujo de agentes
   - Orden secuencial/paralelo de ejecución
   - Tiempos de cada agente
   - Estados (success/error/timeout)
   - Conexiones entre fases

4. **hitl-queue.png**: Cola de revisión humana
   - Lista de casos escalados
   - Formulario de resolución
   - Historial de decisiones humanas

5. **analytics.png**: Dashboard de analytics
   - Métricas agregadas (total, promedio, distribución)
   - Gráficos de tendencias temporales
   - Performance de agentes individuales

### 14.2 Diagramas Mermaid Exportables

Todos los diagramas de este documento están en formato **Mermaid**, que puede ser:

1. **Renderizado en GitHub/GitLab**: Automáticamente en archivos `.md`
2. **Exportado como imagen**: Usando [Mermaid Live Editor](https://mermaid.live/)
3. **Incluido en documentación**: Compatible con MkDocs, Docusaurus, etc.

**Diagramas disponibles**:
- Arquitectura general (Sección 2)
- Flujo de orquestación (Sección 3)
- Grafo LangGraph (Sección 4)
- Modelo de estado (Sección 5)
- Blackboard pattern (Sección 6)
- Desarrollo local (Sección 9.1)
- Docker Compose producción (Sección 9.2)
- Azure cloud (Sección 9.3)

**Exportación a PNG/SVG**:
```bash
# Opción 1: Mermaid CLI (requiere npx/npm)
npx -p @mermaid-js/mermaid-cli mmdc -i diagrama.mmd -o diagrama.png

# Opción 2: Usar Mermaid Live Editor
# 1. Abrir https://mermaid.live/
# 2. Copiar código Mermaid del documento
# 3. Click en "Actions" → "Download PNG/SVG"
```

### 14.3 Uso de la Documentación

**Para onboarding de nuevos desarrolladores**:
1. Leer `README.md` (overview y quickstart)
2. Leer `CLAUDE.md` (reglas de desarrollo)
3. Revisar este archivo (`arquitectura-sistema.md`) para entender arquitectura completa
4. Ejecutar `make demo` para ver el sistema en acción

**Para presentaciones técnicas**:
1. Usar diagramas Mermaid exportados como PNG/SVG
2. Mostrar screenshots del dashboard y transaction detail
3. Ejecutar demo en vivo (`make demo`)
4. Mostrar WebSocket en acción (abrir DevTools en frontend)

**Para auditorías de seguridad/compliance**:
1. Sección 5: Modelo de estado (qué datos se almacenan)
2. Sección 6.4: Arquitectura de Threat Intelligence (providers externos)
3. Sección 6.5: Mecanismos de resiliencia (safety overrides, timeouts, circuit breakers)
4. Sección 10: Endpoints API (superficie de ataque)
5. Sección 12.2: Timeouts y circuit breakers (protección)
6. Logs estructurados con structlog (auditabilidad)
