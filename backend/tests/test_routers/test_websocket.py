"""Tests for WebSocket and analytics endpoints."""
import pytest
from app.main import app


def test_analytics_summary(test_client):
    """Test analytics summary endpoint."""
    response = test_client.get("/api/v1/analytics/summary")
    assert response.status_code == 200

    data = response.json()
    assert "total_analyzed" in data
    assert "decisions_breakdown" in data
    assert "avg_confidence" in data
    assert "avg_processing_time_ms" in data
    assert "escalation_rate" in data

    # Verify types
    assert isinstance(data["total_analyzed"], int)
    assert isinstance(data["decisions_breakdown"], dict)
    assert isinstance(data["avg_confidence"], (int, float))
    assert isinstance(data["avg_processing_time_ms"], (int, float))
    assert isinstance(data["escalation_rate"], (int, float))


def test_analytics_summary_format(test_client):
    """Test analytics summary response format."""
    response = test_client.get("/api/v1/analytics/summary")
    data = response.json()

    # Escalation rate should be between 0 and 1
    assert 0 <= data["escalation_rate"] <= 1

    # Confidence should be between 0 and 1 (if not 0)
    if data["avg_confidence"] > 0:
        assert 0 <= data["avg_confidence"] <= 1


@pytest.mark.skip(reason="WebSocket testing requires async client setup")
def test_websocket_connection():
    """Test WebSocket connection establishment.

    Note: This is a basic test. More comprehensive WebSocket tests
    would require async test client or manual connection testing.
    """
    pass


@pytest.mark.skip(reason="WebSocket testing requires async client setup")
def test_websocket_receive_events():
    """Test receiving events from WebSocket.

    TODO: Implement with async test client when needed.
    """
    pass
