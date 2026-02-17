"""Tests for health check endpoint."""
import pytest
from app.main import app


def test_health_check(test_client):
    """Test health check endpoint returns OK status."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"


def test_health_check_format(test_client):
    """Test health check response format."""
    response = test_client.get("/api/v1/health")
    data = response.json()

    # Verify timestamp is ISO format
    from datetime import datetime
    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    # Verify required fields
    assert set(data.keys()) == {"status", "timestamp", "version"}
