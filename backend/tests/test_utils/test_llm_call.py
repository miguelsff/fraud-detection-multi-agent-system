"""Tests for the shared LLM invocation helper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.llm_call import invoke_llm_with_timeout


@pytest.mark.asyncio
async def test_invoke_llm_success():
    """Test successful LLM invocation returns content and trace."""
    mock_llm = AsyncMock()
    mock_llm.model = "test-model"
    mock_llm.temperature = 0.1

    mock_response = MagicMock()
    mock_response.content = "LLM response text"
    del mock_response.response_metadata
    mock_llm.ainvoke.return_value = mock_response

    content, trace = await invoke_llm_with_timeout(
        mock_llm, "test prompt", agent_name="test"
    )

    assert content == "LLM response text"
    assert trace["llm_prompt"] == "test prompt"
    assert trace["llm_model"] == "test-model"
    assert trace["llm_response_raw"] == "LLM response text"
    mock_llm.ainvoke.assert_called_once_with("test prompt")


@pytest.mark.asyncio
async def test_invoke_llm_timeout():
    """Test timeout returns None content and records in trace."""
    mock_llm = AsyncMock()
    mock_llm.model = "test-model"

    with patch("app.utils.llm_call.asyncio.wait_for", side_effect=TimeoutError):
        content, trace = await invoke_llm_with_timeout(
            mock_llm, "test prompt", timeout=5.0, agent_name="test"
        )

    assert content is None
    assert "TIMEOUT" in trace["llm_response_raw"]


@pytest.mark.asyncio
async def test_invoke_llm_exception():
    """Test generic exception returns None content and records error."""
    mock_llm = AsyncMock()
    mock_llm.model = "test-model"
    mock_llm.ainvoke.side_effect = RuntimeError("connection refused")

    content, trace = await invoke_llm_with_timeout(
        mock_llm, "test prompt", agent_name="test"
    )

    assert content is None
    assert "ERROR" in trace["llm_response_raw"]
    assert "connection refused" in trace["llm_response_raw"]


@pytest.mark.asyncio
async def test_invoke_llm_captures_token_usage():
    """Test that token usage is captured from response metadata."""
    mock_llm = AsyncMock()
    mock_llm.model = "test-model"

    mock_response = MagicMock()
    mock_response.content = "response"
    mock_response.response_metadata = {"usage": {"total_tokens": 150}}
    mock_llm.ainvoke.return_value = mock_response

    content, trace = await invoke_llm_with_timeout(
        mock_llm, "prompt", agent_name="test"
    )

    assert content == "response"
    assert trace["llm_tokens_used"] == 150
