"""Tests for HITL (Human-in-the-Loop) endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_queue_default_status():
    """Test getting HITL queue with default status (pending)."""
    response = client.get("/api/v1/hitl/queue")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_queue_pending_status():
    """Test getting HITL queue with pending status."""
    response = client.get("/api/v1/hitl/queue?status=pending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_queue_resolved_status():
    """Test getting HITL queue with resolved status."""
    response = client.get("/api/v1/hitl/queue?status=resolved")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_queue_invalid_status():
    """Test getting HITL queue with invalid status."""
    response = client.get("/api/v1/hitl/queue?status=invalid")
    assert response.status_code == 422  # Validation error


def test_resolve_case_not_found():
    """Test resolving non-existent HITL case."""
    response = client.post(
        "/api/v1/hitl/999999/resolve",
        json={"resolution": "APPROVE", "reason": "Test reason"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_resolve_case_missing_fields():
    """Test resolving case with missing fields."""
    response = client.post("/api/v1/hitl/1/resolve", json={})
    assert response.status_code == 422  # Validation error
