"""Async OpenRouter LLM client with streaming and tool/function calling support."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_TIERS = {
    "free": [
        {"id": "google/gemma-4-26b-a4b-it", "name": "Gemma 4 26B (Free)", "cost": "$0"},
        {"id": "qwen/qwen3.6-plus:free", "name": "Qwen 3.6 Plus (Free)", "cost": "$0"},
    ],
    "balanced": [
        {"id": "qwen/qwen-2.5-coder-32b-instruct", "name": "Qwen 2.5 Coder 32B", "cost": "~$0.20/M"},
    ],
    "premium": [
        {"id": "anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "cost": "~$3/M in + $15/M out"},
        {"id": "google/gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "cost": "~$1.25/M"},
    ],
}


def get_models_for_tier(tier: str) -> list[dict[str, str]]:
    return MODEL_TIERS.get(tier, MODEL_TIERS["free"])


def get_default_model(tier: str) -> str:
    models = get_models_for_tier(tier)
    return models[0]["id"] if models else "google/gemma-4-26b-a4b-it"


async def stream_chat_completion(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream chat completion from OpenRouter, yielding parsed SSE chunks.

    Yields dicts with keys:
    - {"type": "content_delta", "content": "..."} for text chunks
    - {"type": "tool_call_delta", "index": N, "id": "...", "name": "...", "arguments_delta": "..."}
    - {"type": "done"} when stream ends
    - {"type": "error", "content": "..."} on error
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://agent-harness-platform.local",
        "X-Title": "Agent Harness Platform",
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        try:
            async with client.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    yield {"type": "error", "content": f"OpenRouter API error {response.status_code}: {body.decode()}"}
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        yield {"type": "done"}
                        return

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})

                    # Text content
                    if delta.get("content"):
                        yield {"type": "content_delta", "content": delta["content"]}

                    # Tool calls
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            yield {
                                "type": "tool_call_delta",
                                "index": tc.get("index", 0),
                                "id": tc.get("id", ""),
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments_delta": tc.get("function", {}).get("arguments", ""),
                            }

                    # Check for finish
                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason in ("stop", "tool_calls"):
                        yield {"type": "finish", "finish_reason": finish_reason}

        except httpx.ConnectError as e:
            yield {"type": "error", "content": f"Connection error: {e}"}
        except httpx.ReadTimeout:
            yield {"type": "error", "content": "OpenRouter request timed out"}


async def chat_completion(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Non-streaming chat completion. Returns full response dict."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://agent-harness-platform.local",
        "X-Title": "Agent Harness Platform",
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            return {"error": f"OpenRouter API error {response.status_code}: {response.text}"}
        return response.json()
