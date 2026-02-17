# Backend Test Structure

## Directory Layout

```
backend/
├── tests/                                # ✅ All tests organized here
│   ├── conftest.py                       # Pytest fixtures
│   ├── __init__.py
│   │
│   ├── test_agents/                      # Agent tests
│   │   ├── test_behavioral_pattern.py
│   │   ├── test_debate.py
│   │   ├── test_decision_arbiter.py
│   │   ├── test_evidence_aggregator.py
│   │   ├── test_explainability.py
│   │   ├── test_external_threat.py
│   │   ├── test_orchestrator.py
│   │   ├── test_policy_rag.py
│   │   └── test_transaction_context.py
│   │
│   ├── test_rag/                         # RAG/Vector store tests
│   │   ├── test_chromadb_server.py       # ✅ Moved from root
│   │   └── test_vector_store.py
│   │
│   ├── test_routers/                     # API endpoint tests
│   │   ├── test_health.py
│   │   ├── test_hitl.py
│   │   ├── test_transactions.py
│   │   └── test_websocket.py
│   │
│   └── test_services/                    # ✅ NEW: Service layer tests
│       ├── README.md                     # Test documentation
│       ├── test_threat_intel_country_risk.py   # ✅ Moved from root
│       ├── test_threat_intel_osint.py          # ✅ Moved from root
│       └── test_threat_intel_manager.py        # ✅ Moved from root
│
├── seed_test.py                          # ✅ Utility script (OK in root)
├── simple_seed.py                        # ✅ Utility script (OK in root)
├── explore_chromadb.py                   # ✅ Utility script (OK in root)
├── view_db.py                            # ✅ Utility script (OK in root)
└── main.py                               # ✅ Dev entry point (OK in root)
```

## Test Categories

### 🤖 Agent Tests (`test_agents/`)
Unit tests for all 8 fraud detection agents:
- Transaction Context (deterministic)
- Behavioral Pattern (deterministic)
- Policy RAG (LLM + ChromaDB)
- External Threat (LLM + threat intel providers)
- Evidence Aggregation
- Debate (Pro-Fraud vs Pro-Customer)
- Decision Arbiter
- Explainability

**Run**: `uv run pytest tests/test_agents/ -v`

### 🗄️ RAG Tests (`test_rag/`)
Tests for vector store and ChromaDB integration:
- Vector store initialization
- Policy embedding and retrieval
- ChromaDB server connectivity

**Run**: `uv run pytest tests/test_rag/ -v`

### 🌐 Router Tests (`test_routers/`)
API endpoint integration tests:
- Transaction analysis endpoints
- HITL (Human-in-the-Loop) queue
- WebSocket real-time updates
- Health checks

**Run**: `uv run pytest tests/test_routers/ -v`

### 🛡️ Service Tests (`test_services/`) ✨ NEW
Tests for service layer (threat intelligence providers):
- **Country Risk**: FATF blacklist/graylist lookup (local JSON)
- **OSINT Search**: DuckDuckGo web search for threats
- **Manager**: Parallel orchestration of all providers

**Run**: `uv run pytest tests/test_services/ -v`

## Running Tests

### Run all tests
```bash
cd backend
uv run pytest -v
```

### Run specific category
```bash
uv run pytest tests/test_agents/ -v
uv run pytest tests/test_rag/ -v
uv run pytest tests/test_routers/ -v
uv run pytest tests/test_services/ -v
```

### Run specific test file
```bash
uv run pytest tests/test_services/test_threat_intel_manager.py -v
```

### Run as standalone scripts (for debugging)
```bash
uv run python tests/test_services/test_threat_intel_country_risk.py
uv run python tests/test_services/test_threat_intel_osint.py
uv run python tests/test_services/test_threat_intel_manager.py
```

## Utility Scripts (Root Directory)

These are **not** unit tests but utility/development scripts:

- `seed_test.py` - Seed DB with synthetic data and run analysis
- `simple_seed.py` - Simple database seeding
- `explore_chromadb.py` - Explore ChromaDB vector store
- `view_db.py` - View database contents
- `main.py` - Development server entry point

**These should remain in the root directory** as they are standalone utilities.

## Test Organization Rules

✅ **DO**: Place tests in `tests/` subdirectories by layer
- `test_agents/` - Business logic (agents)
- `test_services/` - Service layer (providers, managers)
- `test_rag/` - Infrastructure (vector stores)
- `test_routers/` - API layer (endpoints)

❌ **DON'T**: Place unit tests in backend root

✅ **OK**: Utility/dev scripts in backend root if they're not unit tests

## Changes Made (2026-02-14)

1. ✅ Created `tests/test_services/` directory
2. ✅ Moved `test_country_risk.py` → `tests/test_services/test_threat_intel_country_risk.py`
3. ✅ Moved `test_osint.py` → `tests/test_services/test_threat_intel_osint.py`
4. ✅ Moved `test_manager.py` → `tests/test_services/test_threat_intel_manager.py`
5. ✅ Moved `test_chromadb_server.py` → `tests/test_rag/test_chromadb_server.py`
6. ✅ Added proper imports for standalone execution
7. ✅ Created `tests/test_services/README.md` with documentation

All tests verified working! ✅
