# Arquitectura del Sistema Multi-Agente de Detección de Fraude

## 1. Visión General

El sistema implementa un pipeline de **8 agentes especializados** orquestados mediante **LangGraph** que analizan transacciones financieras en busca de fraude ambiguo. La arquitectura sigue un patrón **DAG (Directed Acyclic Graph)** con fases paralelas y secuenciales, permitiendo máxima eficiencia sin sacrificar trazabilidad.

### Stack Tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| **Orquestación** | LangGraph | Grafos de estado tipados, checkpointing nativo, soporte async, visualización de flujos |
| **Backend** | FastAPI + Python 3.11 | Async nativo, Pydantic v2 integrado, OpenAPI auto-generado, WebSockets |
| **Frontend** | Next.js 14 + TypeScript + Tailwind | SSR/SSG, App Router, React Server Components, excelente DX |
| **Vector DB** | ChromaDB | Lightweight, embebible, ideal para el volumen de políticas internas |
| **LLM** | Azure OpenAI (GPT-4o) | Requerimiento del desafío (ecosistema Azure), function calling robusto |
| **Base de datos** | SQLite (local) / PostgreSQL (cloud) | Audit trail persistente, sin overhead para desarrollo local |
| **Cache** | Redis (opcional) | Cache de embeddings y rate limiting |
| **Deploy** | Azure Container Apps + Terraform | Serverless containers, escalado automático, integración nativa Azure |

---

## 2. Diagrama de Arquitectura General

```mermaid
graph TB
    subgraph "Frontend — Next.js"
        UI[Dashboard UI]
        TL[Transaction List]
        AT[Agent Trace Viewer]
        HQ[HITL Queue]
        EP[Explanation Panel]
    end

    subgraph "API Gateway — FastAPI"
        API[FastAPI Server]
        WS[WebSocket Handler]
        MW[Middleware<br/>Auth · CORS · Rate Limit]
    end

    subgraph "Orchestration Layer — LangGraph"
        ORC[Orchestrator<br/>State Machine]
    end

    subgraph "Agent Layer"
        direction TB
        subgraph "Fase 1 — Recolección Paralela"
            TCA[Transaction Context<br/>Agent]
            BPA[Behavioral Pattern<br/>Agent]
            PRA[Policy RAG<br/>Agent]
            ETA[External Threat<br/>Agent]
        end
        subgraph "Fase 2 — Consolidación"
            EAA[Evidence Aggregation<br/>Agent]
        end
        subgraph "Fase 3 — Deliberación"
            DPF[Debate Agent<br/>Pro-Fraud]
            DPC[Debate Agent<br/>Pro-Customer]
        end
        subgraph "Fase 4 — Decisión"
            DAR[Decision Arbiter<br/>Agent]
        end
        subgraph "Fase 5 — Explicación"
            EXP[Explainability<br/>Agent]
        end
    end

    subgraph "Data Layer"
        CDB[(ChromaDB<br/>Políticas)]
        SQL[(SQLite/PostgreSQL<br/>Audit Trail)]
        SYN[(Datos Sintéticos<br/>JSON)]
    end

    UI --> API
    API --> ORC
    ORC --> TCA & BPA & PRA & ETA
    TCA & BPA & PRA & ETA --> EAA
    EAA --> DPF & DPC
    DPF & DPC --> DAR
    DAR --> EXP
    EXP --> API
    API --> WS --> UI

    PRA -.-> CDB
    ETA -.->|Web Search| EXT[Fuentes Externas<br/>Whitelisted]
    ORC -.-> SQL
    API -.-> SYN
```

---

## 3. Flujo de Orquestación Detallado (LangGraph)

```mermaid
stateDiagram-v2
    [*] --> ReceiveTransaction: POST /api/v1/transactions/analyze

    ReceiveTransaction --> ValidateInput: Validar schema Pydantic
    ValidateInput --> ParallelCollection: Input válido

    state ParallelCollection {
        [*] --> TransactionContext
        [*] --> BehavioralPattern
        [*] --> PolicyRAG
        [*] --> ExternalThreat

        TransactionContext --> [*]: Señales contextuales
        BehavioralPattern --> [*]: Desviaciones comportamiento
        PolicyRAG --> [*]: Políticas aplicables + chunks
        ExternalThreat --> [*]: Amenazas externas relevantes
    }

    ParallelCollection --> EvidenceAggregation: Consolidar señales

    EvidenceAggregation --> DebatePhase: Evidencia consolidada

    state DebatePhase {
        [*] --> ProFraudArgument: Argumentar sospecha
        [*] --> ProCustomerArgument: Argumentar legitimidad
        ProFraudArgument --> [*]: Caso de fraude
        ProCustomerArgument --> [*]: Caso legítimo
    }

    DebatePhase --> DecisionArbiter: Evaluar argumentos

    DecisionArbiter --> Explainability: Decisión + confidence

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

---

## 5. Modelo de Estado Compartido (Shared State)

El estado es el contrato central entre todos los agentes. LangGraph lo gestiona de forma inmutable con `TypedDict`:

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
        +bool is_off_hours
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

| Agente | Lee del Estado | Escribe al Estado |
|--------|---------------|-------------------|
| **Transaction Context** | `transaction` | `transaction_signals` |
| **Behavioral Pattern** | `transaction`, `customer_behavior` | `behavioral_signals` |
| **Policy RAG** | `transaction`, `transaction_signals`, `behavioral_signals` | `policy_matches` |
| **External Threat** | `transaction`, `transaction_signals` | `threat_intel` |
| **Evidence Aggregation** | `transaction_signals`, `behavioral_signals`, `policy_matches`, `threat_intel` | `evidence` |
| **Debate Pro-Fraud** | `evidence` | `debate.pro_fraud_*` |
| **Debate Pro-Customer** | `evidence` | `debate.pro_customer_*` |
| **Decision Arbiter** | `evidence`, `debate` | `decision` |
| **Explainability** | `decision`, `evidence`, `policy_matches`, `debate` | `explanation` |

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

---

## 7. Justificación de Decisiones de Diseño

### 7.1 ¿Por qué LangGraph sobre otras opciones?

| Criterio | LangGraph | Azure AI Agent | AWS Bedrock Agents | CrewAI |
|----------|-----------|---------------|-------------------|--------|
| **Grafos tipados** | ✅ Nativo | ❌ | ❌ | ❌ |
| **Paralelismo** | ✅ Fan-out/in | ⚠️ Manual | ⚠️ Manual | ✅ |
| **Checkpointing** | ✅ Built-in | ❌ | ❌ | ❌ |
| **Debugging** | ✅ LangSmith | ⚠️ | ⚠️ | ⚠️ |
| **Estado tipado** | ✅ TypedDict | ❌ | ❌ | ❌ |
| **Vendor lock-in** | ❌ Agnóstico | ✅ Azure | ✅ AWS | ❌ |
| **Madurez** | ✅ Producción | ⚠️ Preview | ✅ | ⚠️ |

**Decisión**: LangGraph ofrece el mejor balance entre control granular del flujo, tipado fuerte del estado, paralelismo nativo y trazabilidad. Su integración con LangSmith permite debugging visual del grafo completo, lo cual es crítico para un sistema de detección de fraude donde cada decisión debe ser auditable.

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

```mermaid
graph TB
    subgraph "Azure Cloud"
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

    subgraph "Local Dev"
        DC[docker-compose]
        LITE[(SQLite)]
        CHR[(ChromaDB<br/>Embedded)]
    end

    GH -->|build & push| ACR
    ACR -->|deploy| BE & FE
    TF -->|provision| AOAI & KV & PG
    BE --> AOAI
    BE --> KV
    BE --> PG
    BE --> FE
    AI -.-> BE & FE

    DC -->|local| LITE & CHR
```

---

## 10. Endpoints API (FastAPI)

```
POST   /api/v1/transactions/analyze          → Analizar transacción (flujo completo)
POST   /api/v1/transactions/analyze/batch     → Analizar múltiples transacciones
GET    /api/v1/transactions/{id}/result       → Obtener resultado de análisis
GET    /api/v1/transactions/{id}/trace        → Obtener traza completa de agentes
GET    /api/v1/transactions                   → Listar transacciones analizadas
GET    /api/v1/hitl/queue                     → Cola de revisión humana
POST   /api/v1/hitl/{id}/resolve             → Resolver caso HITL (humano decide)
GET    /api/v1/health                         → Health check
WS     /api/v1/ws/transactions               → WebSocket para actualizaciones en tiempo real
GET    /api/v1/analytics/summary              → Métricas agregadas de decisiones
```

---

## 11. Estructura Final del Proyecto

```
fraud-detection-multiagent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app + routers
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── dependencies.py            # Dependency injection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py         # Transaction, CustomerBehavior
│   │   │   ├── signals.py             # TransactionSignals, BehavioralSignals
│   │   │   ├── evidence.py            # PolicyMatch, ThreatIntel, AggregatedEvidence
│   │   │   ├── debate.py              # DebateArguments
│   │   │   ├── decision.py            # FraudDecision, ExplanationResult
│   │   │   └── trace.py               # AgentTraceEntry, OrchestratorState
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # LangGraph StateGraph definition
│   │   │   ├── transaction_context.py # Señales de la transacción
│   │   │   ├── behavioral_pattern.py  # Análisis de comportamiento
│   │   │   ├── policy_rag.py          # RAG sobre políticas internas
│   │   │   ├── external_threat.py     # Web search gobernada
│   │   │   ├── evidence_aggregator.py # Consolidación de evidencias
│   │   │   ├── debate.py              # Pro-Fraud + Pro-Customer
│   │   │   ├── decision_arbiter.py    # Decisión final
│   │   │   └── explainability.py      # Generación de explicaciones
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py        # ChromaDB setup + ingestion
│   │   │   └── embeddings.py          # Embedding model config
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── transaction_service.py # Business logic
│   │   │   └── analytics_service.py   # Métricas y estadísticas
│   │   ├── hitl/
│   │   │   ├── __init__.py
│   │   │   ├── queue.py               # Cola HITL
│   │   │   └── models.py              # HITLCase schema
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── transactions.py        # /api/v1/transactions/*
│   │   │   ├── hitl.py                # /api/v1/hitl/*
│   │   │   ├── analytics.py           # /api/v1/analytics/*
│   │   │   └── websocket.py           # /api/v1/ws/*
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py              # Structured logging
│   │       └── timing.py              # Decorador de timing para agentes
│   ├── data/
│   │   └── synthetic_data.json        # Datos sintéticos
│   ├── policies/
│   │   └── fraud_policies.md          # Políticas para ingestar en ChromaDB
│   ├── tests/
│   │   ├── test_agents/
│   │   ├── test_routers/
│   │   └── test_orchestrator.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout (sidebar + header)
│   │   │   ├── page.tsx               # Dashboard principal
│   │   │   ├── transactions/
│   │   │   │   ├── page.tsx           # Lista de transacciones
│   │   │   │   └── [id]/page.tsx      # Detalle de transacción
│   │   │   ├── hitl/
│   │   │   │   └── page.tsx           # Cola HITL
│   │   │   └── analytics/
│   │   │       └── page.tsx           # Métricas
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   │   ├── StatsCards.tsx
│   │   │   │   ├── RecentDecisions.tsx
│   │   │   │   └── RiskDistribution.tsx
│   │   │   ├── transactions/
│   │   │   │   ├── TransactionTable.tsx
│   │   │   │   ├── TransactionDetail.tsx
│   │   │   │   └── AnalyzeButton.tsx
│   │   │   ├── agents/
│   │   │   │   ├── AgentTraceTimeline.tsx
│   │   │   │   ├── AgentFlowDiagram.tsx
│   │   │   │   └── DebateView.tsx
│   │   │   ├── hitl/
│   │   │   │   ├── HITLQueue.tsx
│   │   │   │   └── HITLReviewForm.tsx
│   │   │   ├── explanation/
│   │   │   │   ├── CustomerExplanation.tsx
│   │   │   │   └── AuditExplanation.tsx
│   │   │   └── ui/
│   │   │       ├── Badge.tsx
│   │   │       ├── Card.tsx
│   │   │       └── ...
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client (fetch wrapper)
│   │   │   ├── types.ts               # TypeScript interfaces (mirror Pydantic)
│   │   │   └── websocket.ts           # WebSocket hook
│   │   └── hooks/
│   │       ├── useTransactions.ts
│   │       └── useWebSocket.ts
│   ├── Dockerfile
│   ├── package.json
│   └── tailwind.config.ts
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── container_apps/
│   │       ├── database/
│   │       └── openai/
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint + Test
│       └── deploy.yml                 # Build + Push + Deploy
├── .env.example
├── Makefile                           # Comandos útiles
└── README.md
```

---

## 12. Decisiones Clave para la Implementación

### 12.1 Agentes con LLM vs Agentes Determinísticos

No todos los agentes necesitan un LLM. Diseño híbrido:

| Agente | Tipo | Justificación |
|--------|------|---------------|
| Transaction Context | **Determinístico** | Reglas de negocio claras (ratios, horarios, país) |
| Behavioral Pattern | **Determinístico** | Comparación directa contra historial |
| Policy RAG | **LLM + RAG** | Necesita entender semántica de políticas |
| External Threat | **LLM + Tool** | Web search requiere interpretación |
| Evidence Aggregation | **Determinístico + LLM** | Agregación matemática + resumen narrativo |
| Debate Pro-Fraud | **LLM** | Argumentación requiere razonamiento |
| Debate Pro-Customer | **LLM** | Argumentación requiere razonamiento |
| Decision Arbiter | **LLM** | Evaluación balanceada de argumentos |
| Explainability | **LLM** | Generación de lenguaje natural |

Esto optimiza costos (menos llamadas LLM) y latencia (agentes determinísticos son instantáneos).

### 12.2 Manejo de Errores y Resiliencia

- **Timeout por agente**: 30s máximo, con fallback a resultado parcial
- **Retry con backoff**: para llamadas a LLM y web search
- **Circuit breaker**: si External Threat falla, el flujo continúa sin esa señal
- **Graceful degradation**: si un agente falla, se marca en la traza y el resto del pipeline continúa

### 12.3 WebSocket para Actualizaciones en Tiempo Real

El análisis completo toma ~5-15 segundos. El frontend recibe actualizaciones por WebSocket:

```
ws://backend/api/v1/ws/transactions
→ {"event": "agent_started", "agent": "transaction_context", "timestamp": "..."}
→ {"event": "agent_completed", "agent": "transaction_context", "duration_ms": 12}
→ {"event": "agent_started", "agent": "behavioral_pattern", ...}
→ ...
→ {"event": "decision_ready", "transaction_id": "T-1001", "decision": "CHALLENGE"}
```

Esto permite animar el flujo de agentes en tiempo real en el frontend.
