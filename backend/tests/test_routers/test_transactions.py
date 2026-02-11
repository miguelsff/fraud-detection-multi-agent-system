"""Tests for transaction analysis endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models import FraudDecision

client = TestClient(app)


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
async def test_analyze_endpoint_requires_auth_in_future():
    """Placeholder test - will add authentication tests later."""
    # TODO: Add authentication tests when auth is implemented
    pass


def test_analyze_missing_fields():
    """Test analyze endpoint with missing required fields."""
    response = client.post("/api/v1/transactions/analyze", json={})
    assert response.status_code == 422  # Validation error


def test_batch_analyze_empty_list():
    """Test batch analyze with empty list."""
    response = client.post("/api/v1/transactions/analyze/batch", json=[])
    assert response.status_code == 200
    assert response.json() == []


def test_get_result_not_found():
    """Test getting result for non-existent transaction."""
    response = client.get("/api/v1/transactions/NONEXISTENT-ID/result")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_trace_not_found():
    """Test getting trace for non-existent transaction."""
    response = client.get("/api/v1/transactions/NONEXISTENT-ID/trace")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_transactions_default_params():
    """Test listing transactions with default pagination."""
    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_transactions_custom_pagination():
    """Test listing transactions with custom pagination."""
    response = client.get("/api/v1/transactions?limit=10&offset=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
