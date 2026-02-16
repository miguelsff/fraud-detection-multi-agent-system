"""Tests for transaction analysis endpoints."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from app.main import app
from app.models import FraudDecision, AgentTraceEntry
from app.dependencies import get_db


@pytest.fixture
def sample_transaction_request():
    """Sample transaction analysis request."""
    return {
        "transaction": {
            "transaction_id": "T-TEST-001",
            "customer_id": "C-TEST-001",
            "amount": 1500.0,
            "currency": "PEN",
            "country": "PE",
            "channel": "web",
            "device_id": "D-TEST-001",
            "timestamp": "2025-01-15T10:30:00Z",
            "merchant_id": "M-TEST-001",
        },
        "customer_behavior": {
            "customer_id": "C-TEST-001",
            "usual_amount_avg": 500.0,
            "usual_hours": "08:00-22:00",
            "usual_countries": ["PE"],
            "usual_devices": ["D-TEST-001"],
        },
    }


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_transaction_success(sample_transaction_request, mock_db_session, test_client):
    """Test POST /api/v1/transactions/analyze with mocked orchestrator.

    Validates that the endpoint correctly:
    - Parses request body
    - Calls analyze_transaction orchestrator
    - Returns FraudDecision response
    """
    # Mock the analyze_transaction function
    mock_decision = FraudDecision(
        transaction_id="T-TEST-001",
        decision="CHALLENGE",
        confidence=0.75,
        signals=["high_amount_ratio_3.0x", "transaction_off_hours"],
        citations_internal=[
            {"policy_id": "FP-01", "text": "High amount transactions"}
        ],
        citations_external=[{"source": "OSINT", "detail": "Country flagged"}],
        explanation_customer="Verificación adicional requerida por monto elevado",
        explanation_audit="Transaction flagged for high amount ratio (3.0x) and off-hours timing",
        agent_trace=["transaction_context", "policy_rag", "evidence_aggregation"],
    )

    with patch("app.routers.transactions.analyze_transaction") as mock_analyze:
        mock_analyze.return_value = mock_decision

        # Override DB dependency
        app.dependency_overrides[get_db] = lambda: mock_db_session

        response = test_client.post(
            "/api/v1/transactions/analyze", json=sample_transaction_request
        )

        # Cleanup
        app.dependency_overrides.clear()

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "T-TEST-001"
    assert data["decision"] == "CHALLENGE"
    assert data["confidence"] == 0.75
    assert len(data["signals"]) == 2
    assert len(data["agent_trace"]) == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_result_success(mock_db_session, test_client):
    """Test GET /api/v1/transactions/{id}/result with existing transaction.

    Validates that the endpoint correctly:
    - Queries database for TransactionRecord
    - Returns transaction result with decision
    """
    # Mock DB query to return a TransactionRecord
    mock_record = Mock()
    mock_record.transaction_id = "T-001"
    mock_record.raw_data = {
        "transaction_id": "T-001",
        "amount": 1500.0,
        "currency": "PEN",
    }
    mock_record.decision = "APPROVE"
    mock_record.confidence = 0.95
    mock_record.signals = ["low_risk"]
    mock_record.analysis_state = {}  # Important: prevent Mock recursion during serialization
    mock_record.created_at = datetime.now(timezone.utc)

    # scalar_one_or_none is a synchronous method on the Result object.
    # We must return a MagicMock (synchronous) from the awaited execute call.
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_record
    
    # mock_db_session.execute is an AsyncMock, checking return_value.
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    response = test_client.get("/api/v1/transactions/T-001/result")

    app.dependency_overrides.clear()

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "T-001"
    assert data["decision"] == "APPROVE"
    assert data["confidence"] == 0.95


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_trace_success(mock_db_session, test_client):
    """Test GET /api/v1/transactions/{id}/trace with existing traces.

    Validates that the endpoint correctly:
    - Queries database for AgentTrace records
    - Returns list of agent execution traces
    """
    # Mock DB query to return list of AgentTrace
    mock_trace1 = Mock()
    mock_trace1.agent_name = "transaction_context"
    mock_trace1.duration_ms = 15.5
    mock_trace1.status = "success"
    mock_trace1.input_summary = "Transaction T-001"
    mock_trace1.output_summary = "6 signals generated"
    mock_trace1.created_at = datetime.now(timezone.utc)

    mock_trace2 = Mock()
    mock_trace2.agent_name = "evidence_aggregation"
    mock_trace2.duration_ms = 8.2
    mock_trace2.status = "success"
    mock_trace2.input_summary = "Signals from 3 sources"
    mock_trace2.output_summary = "Composite score: 45.0"
    mock_trace2.created_at = datetime.now(timezone.utc)

    # Result.scalars() is synchronous, returns ScalarResult.
    # ScalarResult.all() is synchronous.
    mock_scalars = Mock()
    mock_scalars.all.return_value = [mock_trace1, mock_trace2]

    mock_result = Mock()
    mock_result.scalars.return_value = mock_scalars

    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    response = test_client.get("/api/v1/transactions/T-001/trace")

    app.dependency_overrides.clear()

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["agent_name"] == "transaction_context"
    assert data[0]["duration_ms"] == 15.5
    assert data[1]["agent_name"] == "evidence_aggregation"
    assert data[1]["duration_ms"] == 8.2


@pytest.mark.asyncio
async def test_analyze_endpoint_requires_auth_in_future():
    """Placeholder test - will add authentication tests later."""
    # TODO: Add authentication tests when auth is implemented
    pass


@pytest.mark.unit
def test_analyze_missing_fields(test_client):
    """Test analyze endpoint with missing required fields."""
    response = test_client.post("/api/v1/transactions/analyze", json={})
    assert response.status_code == 422  # Validation error


@pytest.mark.unit
def test_batch_analyze_empty_list(test_client):
    """Test batch analyze with empty list."""
    response = test_client.post("/api/v1/transactions/analyze/batch", json=[])
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_get_result_not_found(test_client):
    """Test getting result for non-existent transaction."""
    response = test_client.get("/api/v1/transactions/NONEXISTENT-ID/result")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
def test_get_trace_not_found(test_client):
    """Test getting trace for non-existent transaction."""
    response = test_client.get("/api/v1/transactions/NONEXISTENT-ID/trace")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit
def test_list_transactions_default_params(test_client):
    """Test listing transactions with default pagination."""
    response = test_client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.unit
def test_list_transactions_custom_pagination(test_client):
    """Test listing transactions with custom pagination."""
    response = test_client.get("/api/v1/transactions?limit=10&offset=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
