# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fraud Detection Multi-Agent System — a pipeline of 8 specialized agents orchestrated via **LangGraph** that analyze financial transactions for ambiguous fraud. Uses a **Blackboard Pattern** (shared state via `OrchestratorState` TypedDict) where agents are pure functions `(state) → state` communicating only through LangGraph's shared state.

## Architecture Reference

Detailed architecture documentation (in Spanish) lives in `.claude/docs/arquitectura-sistema.md`. Read it for agent flow diagrams, state models, and design rationale.

### Agent Pipeline (5 phases)

1. **Parallel Collection** — `TransactionContext` (deterministic), `BehavioralPattern` (deterministic), `PolicyRAG` (LLM+RAG via ChromaDB), `ExternalThreat` (LLM+web search) run concurrently
2. **Consolidation** — `EvidenceAggregation` merges all signals
3. **Adversarial Debate** — `ProFraud` and `ProCustomer` agents argue opposing positions
4. **Decision** — `DecisionArbiter` evaluates debate arguments, outputs APPROVE/CHALLENGE/BLOCK/ESCALATE_TO_HUMAN
5. **Explanation** — `Explainability` agent generates customer-facing and audit explanations

### Tech Stack

- **Backend**: FastAPI + Python 3.13 + LangGraph + Pydantic v2
- **LLM**: LangChain + LangChain-Ollama (local dev)
- **Vector DB**: ChromaDB (embedded, for fraud policy RAG)
- **Database**: PostgreSQL (via SQLAlchemy async + asyncpg + Alembic migrations)
- **Frontend**: Next.js 14 + TypeScript + Tailwind (planned)
- **Deploy**: Azure Container Apps + Terraform (planned)

### Key Backend Modules (`backend/app/`)

- `agents/` — LangGraph orchestrator + individual agent implementations
- `models/` — Pydantic models (transaction, signals, evidence, debate, decision, trace)
- `rag/` — ChromaDB vector store setup and embeddings
- `routers/` — FastAPI route handlers (transactions, HITL, analytics, websocket)
- `services/` — Business logic layer
- `hitl/` — Human-in-the-loop queue and models
- `utils/` — Structured logging (structlog), timing decorators

## Build & Development Commands

```bash
# Navigate to backend
cd backend

# Install dependencies (uses uv, Python 3.13)
python -m uv sync

# Install with dev dependencies
python -m uv sync --group dev

# Run the backend server
python -m uv run uvicorn app.main:app --reload

# Run all tests
python -m uv run pytest

# Run a single test file
python -m uv run pytest tests/test_agents/test_example.py

# Run a specific test
python -m uv run pytest tests/test_agents/test_example.py::test_function_name -v

# Start PostgreSQL (from repo root)
docker compose -f devops/docker-compose.yml up -d
```

## Key Design Decisions

- Agents use **Blackboard Pattern** (shared state), NOT message passing — for auditability in financial fraud detection
- Not all agents use LLMs: `TransactionContext` and `BehavioralPattern` are deterministic; only RAG, debate, arbiter, and explainability agents call LLMs
- Each agent reads specific state fields and writes only its own fields (see I/O contracts in architecture doc)
- Decision outcomes: APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN
- HITL (Human-in-the-Loop) queue handles ESCALATE cases via `/api/v1/hitl/` endpoints
- WebSocket at `/api/v1/ws/transactions` streams agent progress events in real-time

## API Endpoints

```
POST   /api/v1/transactions/analyze          — Full pipeline analysis
POST   /api/v1/transactions/analyze/batch    — Batch analysis
GET    /api/v1/transactions/{id}/result      — Get analysis result
GET    /api/v1/transactions/{id}/trace       — Get agent trace
GET    /api/v1/transactions                  — List analyzed transactions
GET    /api/v1/hitl/queue                    — HITL review queue
POST   /api/v1/hitl/{id}/resolve            — Resolve HITL case
GET    /api/v1/health                        — Health check
WS     /api/v1/ws/transactions              — Real-time updates
GET    /api/v1/analytics/summary             — Aggregated metrics
```
