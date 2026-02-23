"""Tests for WebSocket connection manager buffer cleanup."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.services.ws_manager import MAX_BUFFER_AGE_SECONDS, MAX_BUFFER_SIZE, ConnectionManager


@pytest.fixture
def ws_manager():
    return ConnectionManager()


@pytest.mark.asyncio
async def test_buffer_cleanup_after_max_size(ws_manager):
    """Test that stale buffers are cleaned when buffer count exceeds MAX_BUFFER_SIZE."""
    # Fill buffers beyond limit with completed analyses (pending_cleanup)
    for i in range(MAX_BUFFER_SIZE + 10):
        tid = f"T-{i:04d}"
        ws_manager._event_buffers[tid] = [
            {
                "transaction_id": tid,
                "event": "decision_ready",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ]
        ws_manager._pending_cleanup.add(tid)

    # Trigger cleanup by broadcasting a new event
    await ws_manager.broadcast_agent_event("T-NEW", "agent_started", "test")

    # Completed buffers should have been cleaned
    assert len(ws_manager._event_buffers) <= MAX_BUFFER_SIZE + 1


@pytest.mark.asyncio
async def test_buffer_cleanup_after_replay(ws_manager):
    """Test that buffer is removed after replay for completed analysis."""
    # Buffer an event
    await ws_manager.broadcast_agent_event("T-001", "agent_started", "test")
    await ws_manager.broadcast_agent_event("T-001", "decision_ready", data={"decision": "APPROVE"})

    assert "T-001" in ws_manager._event_buffers
    assert "T-001" in ws_manager._pending_cleanup

    # Replay to a mock websocket
    mock_ws = AsyncMock()
    await ws_manager.replay_events(mock_ws, "T-001")

    # Buffer should be cleaned after replay
    assert "T-001" not in ws_manager._event_buffers
    assert "T-001" not in ws_manager._pending_cleanup


@pytest.mark.asyncio
async def test_buffer_cleanup_stale_by_age(ws_manager):
    """Test that old buffers are cleaned based on timestamp age."""
    old_ts = (datetime.now(UTC) - timedelta(seconds=MAX_BUFFER_AGE_SECONDS + 100)).isoformat()

    # Manually insert a stale buffer
    ws_manager._event_buffers["T-OLD"] = [
        {"transaction_id": "T-OLD", "event": "agent_started", "timestamp": old_ts}
    ]

    # Fill to trigger cleanup
    for i in range(MAX_BUFFER_SIZE + 1):
        ws_manager._event_buffers[f"T-FILL-{i}"] = [
            {"transaction_id": f"T-FILL-{i}", "event": "agent_started", "timestamp": old_ts}
        ]

    ws_manager._cleanup_stale_buffers()

    # Old buffer should have been removed
    assert "T-OLD" not in ws_manager._event_buffers


@pytest.mark.asyncio
async def test_buffer_normal_operation_no_cleanup(ws_manager):
    """Test that buffers are not cleaned during normal operation (under limit)."""
    await ws_manager.broadcast_agent_event("T-001", "agent_started", "test")
    await ws_manager.broadcast_agent_event("T-002", "agent_started", "test")

    assert len(ws_manager._event_buffers) == 2
    assert "T-001" in ws_manager._event_buffers
    assert "T-002" in ws_manager._event_buffers
