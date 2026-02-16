# Backend — Fraud Detection Multi-Agent System

FastAPI backend that orchestrates 8 specialized AI agents via LangGraph to detect ambiguous financial fraud.

## Tech Stack

- **Python 3.13** + **FastAPI** — async API server
- **LangGraph** — agent orchestration (DAG with parallel phases)
- **LangChain + Ollama** — local LLM inference (llama3.2)
- **ChromaDB** — vector store for fraud policy RAG
- **PostgreSQL** — audit trail persistence (SQLAlchemy async + Alembic)
- **Pydantic v2** — typed models and validation
- **structlog** — structured logging

## Project Structure

```
backend/
├── app/
│   ├── agents/          # LangGraph orchestrator + 8 agent implementations
│   ├── models/          # Pydantic models (transaction, signals, evidence, debate, decision)
│   ├── prompts/         # LLM prompt templates (separated from agent logic)
│   ├── rag/             # ChromaDB vector store setup and policy ingestion
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # Business logic layer
│   ├── db/              # SQLAlchemy models and database session
│   ├── utils/           # Structured logging, timing decorators
│   ├── config.py        # Pydantic Settings (env-based config)
│   ├── constants.py     # Centralized constants
│   ├── dependencies.py  # FastAPI dependency injection
│   ├── exceptions.py    # Custom exception hierarchy
│   └── main.py          # FastAPI app factory
├── data/                # Synthetic test data (6 scenarios) + fraud policies
├── tests/               # Unit + integration tests (pytest)
├── Dockerfile           # Multi-stage, non-root, healthcheck
└── pyproject.toml       # Dependencies (managed by uv)
```

## Setup

**Prerequisites**: Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker (for PostgreSQL), [Ollama](https://ollama.com/)

```bash
# Install dependencies
uv sync --group dev

# Start PostgreSQL
docker compose -f ../devops/docker-compose.yml up -d

# Run database migrations
uv run alembic upgrade head

# Ingest fraud policies into ChromaDB
uv run python -m app.rag.ingest

# Start development server
uv run uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000 with interactive docs at http://localhost:8000/docs.

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_agents/test_orchestrator.py

# Run E2E with synthetic data (6 scenarios)
uv run python seed_test.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/transactions/analyze` | Full pipeline analysis |
| `POST` | `/api/v1/transactions/analyze/batch` | Batch analysis |
| `GET` | `/api/v1/transactions/{id}/result` | Get analysis result |
| `GET` | `/api/v1/transactions/{id}/trace` | Get agent execution trace |
| `GET` | `/api/v1/transactions` | List analyzed transactions |
| `GET` | `/api/v1/hitl/queue` | HITL review queue |
| `POST` | `/api/v1/hitl/{id}/resolve` | Resolve HITL case |
| `GET` | `/api/v1/health` | Health check |
| `WS` | `/api/v1/ws/transactions` | Real-time agent progress |

## Agent Pipeline

The orchestrator runs 5 phases as a LangGraph `StateGraph`:

1. **Parallel Collection** — `TransactionContext`, `BehavioralPattern`, `PolicyRAG`, `ExternalThreat` run concurrently via `asyncio.gather`
2. **Consolidation** — `EvidenceAggregation` merges all signals into a unified evidence package
3. **Adversarial Debate** — `ProFraud` and `ProCustomer` agents argue opposing positions
4. **Decision** — `DecisionArbiter` evaluates debate → outputs `APPROVE | CHALLENGE | BLOCK | ESCALATE_TO_HUMAN`
5. **Explanation** — `Explainability` agent generates customer-facing and audit explanations

## Environment Variables

Configure via `.env` file or environment:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./fraud.db` | Database connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | LLM model name |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB storage path |
| `LOG_LEVEL` | `INFO` | Logging level |
