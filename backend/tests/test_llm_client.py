"""Tests for LLM client (mocked OpenRouter responses)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.llm_client import (
    MODEL_TIERS,
    get_default_model,
    get_models_for_tier,
    stream_chat_completion,
)


def test_get_models_for_tier_free():
    models = get_models_for_tier("free")
    assert len(models) > 0
    assert all("id" in m for m in models)


def test_get_models_for_tier_unknown():
    models = get_models_for_tier("nonexistent")
    assert models == MODEL_TIERS["free"]


def test_get_default_model():
    model = get_default_model("free")
    assert model == MODEL_TIERS["free"][0]["id"]


def test_get_default_model_balanced():
    model = get_default_model("balanced")
    assert model == MODEL_TIERS["balanced"][0]["id"]


class AsyncLineIterator:
    """Helper to simulate async line iteration."""
    def __init__(self, lines):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


def _make_mock_client(status_code, lines=None, body=None):
    """Create a mock httpx.AsyncClient with stream support."""
    mock_response = MagicMock()
    mock_response.status_code = status_code

    if lines is not None:
        mock_response.aiter_lines = lambda: AsyncLineIterator(lines)

    if body is not None:
        mock_response.aread = AsyncMock(return_value=body)

    # Context manager for response
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return mock_client


@pytest.mark.asyncio
async def test_stream_content_delta():
    """Test streaming with mocked content response."""
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        'data: {"choices":[{"finish_reason":"stop","delta":{}}]}',
        "data: [DONE]",
    ]

    mock_client = _make_mock_client(200, lines=lines)

    with patch("backend.core.llm_client.httpx.AsyncClient", return_value=mock_client):
        events = []
        async for chunk in stream_chat_completion("fake-key", "test-model", [{"role": "user", "content": "hi"}]):
            events.append(chunk)

    content_events = [e for e in events if e["type"] == "content_delta"]
    assert len(content_events) == 2
    assert content_events[0]["content"] == "Hello"
    assert content_events[1]["content"] == " world"


@pytest.mark.asyncio
async def test_stream_tool_call():
    """Test streaming with tool call response."""
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"read_file","arguments":"{\\"path\\":"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"test.txt\\"}"}}]}}]}',
        'data: {"choices":[{"finish_reason":"tool_calls","delta":{}}]}',
        "data: [DONE]",
    ]

    mock_client = _make_mock_client(200, lines=lines)

    with patch("backend.core.llm_client.httpx.AsyncClient", return_value=mock_client):
        events = []
        async for chunk in stream_chat_completion("fake-key", "test-model", [{"role": "user", "content": "hi"}]):
            events.append(chunk)

    tool_events = [e for e in events if e["type"] == "tool_call_delta"]
    assert len(tool_events) == 2
    assert tool_events[0]["name"] == "read_file"


@pytest.mark.asyncio
async def test_stream_error_status():
    """Test handling of non-200 status."""
    mock_client = _make_mock_client(429, body=b"Rate limited")

    with patch("backend.core.llm_client.httpx.AsyncClient", return_value=mock_client):
        events = []
        async for chunk in stream_chat_completion("fake-key", "test-model", [{"role": "user", "content": "hi"}]):
            events.append(chunk)

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "429" in events[0]["content"]
