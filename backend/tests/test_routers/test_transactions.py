"""Tests for transaction analysis endpoints."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.application.models import FraudDecision
from app.presentation.routers.transactions import MAX_BATCH_SIZE


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
async def test_analyze_transaction_success(sample_transaction_request, test_client):
    """Test POST /api/v1/transactions/analyze with mocked orchestrator."""
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

    with patch("app.presentation.routers.transactions.analyze_transaction") as mock_analyze:
        mock_analyze.return_value = mock_decision

        response = test_client.post(
            "/api/v1/transactions/analyze", json=sample_transaction_request
        )

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "T-TEST-001"
    assert data["decision"] == "CHALLENGE"
    assert data["confidence"] == 0.75
    assert len(data["signals"]) == 2
    assert len(data["agent_trace"]) == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_result_success(mock_container, test_client):
    """Test GET /api/v1/transactions/{id}/result with existing transaction."""
    mock_container.persistence.get_transaction.return_value = {
        "transaction_id": "T-001",
        "transaction": {"transaction_id": "T-001", "amount": 1500.0, "currency": "PEN"},
        "decision": "APPROVE",
        "confidence": 0.95,
        "hitl": None,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    response = test_client.get("/api/v1/transactions/T-001/result")

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "T-001"
    assert data["decision"] == "APPROVE"
    assert data["confidence"] == 0.95
    assert data["hitl"] is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_trace_success(mock_container, test_client):
    """Test GET /api/v1/transactions/{id}/trace with existing traces."""
    mock_container.persistence.get_transaction_trace.return_value = [
        {
            "agent_name": "transaction_context",
            "duration_ms": 15.5,
            "input_summary": "Transaction T-001",
            "output_summary": "6 signals generated",
            "status": "success",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "llm_prompt": None,
            "llm_response_raw": None,
            "llm_model": None,
            "llm_temperature": None,
            "llm_tokens_used": None,
            "rag_query": None,
            "rag_scores": None,
            "fallback_reason": None,
            "error_details": None,
        },
        {
            "agent_name": "evidence_aggregation",
            "duration_ms": 8.2,
            "input_summary": "Signals from 3 sources",
            "output_summary": "Composite score: 45.0",
            "status": "success",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "llm_prompt": None,
            "llm_response_raw": None,
            "llm_model": None,
            "llm_temperature": None,
            "llm_tokens_used": None,
            "rag_query": None,
            "rag_scores": None,
            "fallback_reason": None,
            "error_details": None,
        },
    ]

    response = test_client.get("/api/v1/transactions/T-001/trace")

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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_batch_parallel_success(sample_transaction_request, test_client):
    """Test batch endpoint processes multiple requests in parallel."""
    mock_decision = FraudDecision(
        transaction_id="T-TEST-001",
        decision="APPROVE",
        confidence=0.85,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="Aprobada.",
        explanation_audit="Audit.",
        agent_trace=[],
    )

    with patch("app.presentation.routers.transactions.analyze_transaction") as mock_analyze:
        mock_analyze.return_value = mock_decision

        response = test_client.post(
            "/api/v1/transactions/analyze/batch",
            json=[sample_transaction_request, sample_transaction_request],
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["status"] == "ok" for item in data)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_analyze_batch_partial_failure(sample_transaction_request, test_client):
    """Test batch endpoint handles partial failures gracefully."""
    mock_decision = FraudDecision(
        transaction_id="T-TEST-001",
        decision="APPROVE",
        confidence=0.85,
        signals=[],
        citations_internal=[],
        citations_external=[],
        explanation_customer="Aprobada.",
        explanation_audit="Audit.",
        agent_trace=[],
    )

    call_count = 0

    async def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Pipeline error")
        return mock_decision

    with patch("app.presentation.routers.transactions.analyze_transaction", side_effect=_side_effect):
        response = test_client.post(
            "/api/v1/transactions/analyze/batch",
            json=[sample_transaction_request, sample_transaction_request, sample_transaction_request],
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    ok_count = sum(1 for item in data if item["status"] == "ok")
    error_count = sum(1 for item in data if item["status"] == "error")
    assert ok_count == 2
    assert error_count == 1


@pytest.mark.unit
def test_analyze_batch_max_size_exceeded(sample_transaction_request, test_client):
    """Test batch endpoint rejects oversized batches."""
    too_many = [sample_transaction_request] * (MAX_BATCH_SIZE + 1)
    response = test_client.post("/api/v1/transactions/analyze/batch", json=too_many)
    assert response.status_code == 400
    assert "exceeds maximum" in response.json()["detail"].lower()
