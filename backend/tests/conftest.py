"""Shared pytest fixtures for fraud detection test suite.

Provides:
- Synthetic data fixtures (6 transaction scenarios from synthetic_data.json)
- Mock database sessions (unit tests)
- In-memory SQLite database (integration tests)
- Mock LLM fixtures
- Mock ChromaDB fixtures
- State dictionary fixtures
- FastAPI test client
"""

import json
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    CustomerBehavior,
    OrchestratorState,
    Transaction,
)

# ============================================================================
# Synthetic Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def synthetic_data() -> list[dict]:
    """Load synthetic test data from JSON file.

    Returns list of 6 transaction scenarios:
    - T-1001: CHALLENGE (high amount + off-hours)
    - T-1002: BLOCK (very high amount + unusual country + unknown device)
    - T-1003: APPROVE (normal transaction profile)
    - T-1004: ESCALATE_TO_HUMAN (ambiguous signals)
    - T-1005: CHALLENGE (high amount + new device)
    - T-1006: BLOCK (all risk factors present)
    """
    data_path = Path(__file__).parent.parent / "data" / "synthetic_data.json"
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def transaction_t1001(synthetic_data) -> Transaction:
    """T-1001: High amount (3.6x) + off-hours → CHALLENGE expected.

    - Amount: 1800 PEN (3.6x avg 500)
    - Country: PE (usual)
    - Time: 03:15 (off-hours)
    - Device: D-01 (known)
    """
    data = synthetic_data[0]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c501(synthetic_data) -> CustomerBehavior:
    """C-501 behavior for T-1001."""
    data = synthetic_data[0]["customer_behavior"]
    return CustomerBehavior(**data)


@pytest.fixture
def transaction_t1002(synthetic_data) -> Transaction:
    """T-1002: Very high amount (17x) + unusual country + unknown device → BLOCK expected.

    - Amount: 8500 USD (17x avg 500)
    - Country: NG (Nigeria, not usual)
    - Time: 02:00 (off-hours)
    - Device: D-99 (unknown)
    """
    data = synthetic_data[1]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c502(synthetic_data) -> CustomerBehavior:
    """C-502 behavior for T-1002."""
    data = synthetic_data[1]["customer_behavior"]
    return CustomerBehavior(**data)


@pytest.fixture
def transaction_t1003(synthetic_data) -> Transaction:
    """T-1003: Normal transaction (0.5x) + usual country + known device → APPROVE expected.

    - Amount: 250 PEN (0.5x avg 500)
    - Country: PE (usual)
    - Time: 14:30 (normal hours)
    - Device: D-03 (known)
    """
    data = synthetic_data[2]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c503(synthetic_data) -> CustomerBehavior:
    """C-503 behavior for T-1003."""
    data = synthetic_data[2]["customer_behavior"]
    return CustomerBehavior(**data)


@pytest.fixture
def transaction_t1004(synthetic_data) -> Transaction:
    """T-1004: Ambiguous (4x amount, new country but low-risk) → ESCALATE_TO_HUMAN expected.

    - Amount: 2000 USD (4x avg 500)
    - Country: CO (Colombia, new but nearby and low-risk)
    - Time: 16:00 (normal hours)
    - Device: D-01 (known)
    """
    data = synthetic_data[3]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c504(synthetic_data) -> CustomerBehavior:
    """C-504 behavior for T-1004."""
    data = synthetic_data[3]["customer_behavior"]
    return CustomerBehavior(**data)


@pytest.fixture
def transaction_t1005(synthetic_data) -> Transaction:
    """T-1005: High amount (6x) + new device, usual country → CHALLENGE expected.

    - Amount: 3000 PEN (6x avg 500)
    - Country: PE (usual)
    - Time: 10:00 (normal hours)
    - Device: D-05 (new)
    """
    data = synthetic_data[4]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c505(synthetic_data) -> CustomerBehavior:
    """C-505 behavior for T-1005."""
    data = synthetic_data[4]["customer_behavior"]
    return CustomerBehavior(**data)


@pytest.fixture
def transaction_t1006(synthetic_data) -> Transaction:
    """T-1006: Extremely high amount (30x) + high-risk country + unknown device → BLOCK expected.

    - Amount: 15000 USD (30x avg 500)
    - Country: RU (Russia, high-risk)
    - Time: 01:00 (off-hours)
    - Device: D-88 (unknown)
    """
    data = synthetic_data[5]["transaction"]
    return Transaction(
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        amount=data["amount"],
        currency=data["currency"],
        country=data["country"],
        channel=data["channel"],
        device_id=data["device_id"],
        timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
        merchant_id=data["merchant_id"],
    )


@pytest.fixture
def customer_behavior_c506(synthetic_data) -> CustomerBehavior:
    """C-506 behavior for T-1006."""
    data = synthetic_data[5]["customer_behavior"]
    return CustomerBehavior(**data)


# ============================================================================
# Database Session Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock AsyncSession for unit tests that don't need real DB.

    Returns a mock with common SQLAlchemy async session methods:
    - add() - synchronous (MagicMock)
    - commit() - async
    - flush() - async
    - execute() - async with chained result methods
    """
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(
        return_value=AsyncMock(
            scalar_one_or_none=Mock(return_value=None),
            scalars=Mock(return_value=Mock(all=Mock(return_value=[]))),
        )
    )
    return session


@pytest.fixture
async def in_memory_db() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory database for integration tests.

    Creates a fresh database with all tables for each test.
    Uses aiosqlite for async support.

    Yields:
        AsyncSession: Database session for testing
    """
    # Create async engine with SQLite in-memory
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Import Base and create all tables
    from app.database.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session
    async with async_session_maker() as session:
        yield session

    # Cleanup
    await engine.dispose()


# ============================================================================
# LLM Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_llm():
    """Factory fixture for creating mock LLM responses.

    Usage:
        def test_my_agent(mock_llm):
            llm = mock_llm('{"key": "value"}')
            result = await agent_with_llm(llm)
    """

    def _mock_llm(content: str):
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=Mock(content=content))
        return mock

    return _mock_llm


@pytest.fixture
def mock_llm_policy_rag(mock_llm):
    """Mock LLM for policy RAG agent with structured JSON response.

    Returns a mock that produces a PolicyMatchResult-compatible JSON.
    """
    return mock_llm(
        json.dumps(
            {
                "matches": [
                    {
                        "policy_id": "FP-01",
                        "description": "High Amount Transactions",
                        "relevance_score": 0.9,
                    }
                ]
            }
        )
    )


@pytest.fixture
def mock_llm_threat_intel(mock_llm):
    """Mock LLM for threat intel agent with structured JSON response.

    Returns a mock that produces a ThreatIntelResult-compatible JSON.
    """
    return mock_llm(
        json.dumps(
            {
                "threats": [
                    {
                        "source": "OSINT",
                        "description": "Country flagged in recent fraud reports",
                        "severity": "medium",
                        "confidence": 0.7,
                    }
                ]
            }
        )
    )


@pytest.fixture
def mock_llm_pro_fraud(mock_llm):
    """Mock LLM for ProFraud debate agent."""
    return mock_llm(
        "This transaction exhibits multiple fraud indicators: high amount ratio, unusual timing, and unknown device. Risk score is elevated."
    )


@pytest.fixture
def mock_llm_pro_customer(mock_llm):
    """Mock LLM for ProCustomer debate agent."""
    return mock_llm(
        "Customer has a clean history with no previous fraud flags. The amount, while elevated, is within reasonable bounds for this customer segment."
    )


@pytest.fixture
def mock_llm_arbiter(mock_llm):
    """Mock LLM for Decision Arbiter agent."""
    return mock_llm(
        json.dumps(
            {
                "decision": "CHALLENGE",
                "confidence": 0.75,
                "reasoning": "Moderate risk indicators warrant additional verification",
            }
        )
    )


@pytest.fixture
def mock_llm_explainability(mock_llm):
    """Mock LLM for Explainability agent."""
    return mock_llm(
        json.dumps(
            {
                "explanation_customer": "Verificación adicional requerida por monto elevado",
                "explanation_audit": "Transaction flagged for high amount ratio (3.6x) and off-hours timing",
            }
        )
    )


# ============================================================================
# ChromaDB Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_chroma_query_policies():
    """Mock ChromaDB query_policies() function.

    Returns a list of policy document chunks with metadata and scores.
    """
    return [
        {
            "id": "fp-01-section-0",
            "text": "## FP-01: High Amount Transactions\n\nTransactions exceeding 3x the customer's average require additional verification.",
            "metadata": {"policy_id": "FP-01", "section": "0"},
            "score": 0.95,
        },
        {
            "id": "fp-02-section-0",
            "text": "## FP-02: Foreign Country Transactions\n\nTransactions from countries not in the customer's usual_countries list are flagged.",
            "metadata": {"policy_id": "FP-02", "section": "0"},
            "score": 0.88,
        },
    ]


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection object.

    Provides a mock collection with query() method.
    """
    mock_collection = Mock()
    mock_collection.query = Mock(
        return_value={
            "ids": [["fp-01-section-0", "fp-02-section-0"]],
            "documents": [
                [
                    "## FP-01: High Amount Transactions\n\nTransactions exceeding 3x average.",
                    "## FP-02: Foreign Country Transactions\n\nForeign countries flagged.",
                ]
            ],
            "metadatas": [
                [
                    {"policy_id": "FP-01", "section": "0"},
                    {"policy_id": "FP-02", "section": "0"},
                ]
            ],
            "distances": [[0.05, 0.12]],
        }
    )
    return mock_collection


# ============================================================================
# State Dictionary Fixtures
# ============================================================================


@pytest.fixture
def minimal_state(transaction_t1001, customer_behavior_c501) -> OrchestratorState:
    """Minimal valid orchestrator state (required fields only).

    Uses T-1001 transaction and C-501 behavior by default.
    For other scenarios, use the specific transaction/behavior fixtures.
    """
    return {
        "transaction": transaction_t1001,
        "customer_behavior": customer_behavior_c501,
        "status": "processing",
        "trace": [],
    }


# ============================================================================
# FastAPI Test Client
# ============================================================================


@pytest.fixture
def test_client():
    """Synchronous TestClient for FastAPI router tests.

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    from app.main import app

    return TestClient(app)
