"""Async OpenRouter LLM client with streaming and tool/function calling support."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MODEL_TIERS = {
    # All models verified to support tool/function calling via OpenRouter API (2026-04)
    "free": [
        {
            "id": "qwen/qwen3-coder:free",
            "name": "Qwen3 Coder 480B (Free)",
            "cost": "$0",
            "context": 262000,
            "note": "Best free coding model, 480B MoE",
        },
        {
            "id": "meta-llama/llama-3.3-70b-instruct:free",
            "name": "Llama 3.3 70B (Free)",
            "cost": "$0",
            "context": 65536,
            "note": "Reliable, widely supported",
        },
        {
            "id": "openai/gpt-oss-120b:free",
            "name": "OpenAI OSS 120B (Free)",
            "cost": "$0",
            "context": 131072,
            "note": "OpenAI open-source 120B",
        },
    ],
    "balanced": [
        {
            "id": "deepseek/deepseek-v3.2",
            "name": "DeepSeek V3.2",
            "cost": "~$0.26/M in + $0.38/M out",
            "context": 163840,
            "note": "Best value coding model",
        },
        {
            "id": "meta-llama/llama-4-maverick",
            "name": "Llama 4 Maverick",
            "cost": "~$0.15/M in + $0.60/M out",
            "context": 1048576,
            "note": "1M context, great price/performance",
        },
        {
            "id": "mistralai/devstral-2512",
            "name": "Devstral (Mistral)",
            "cost": "~$0.40/M in + $2.00/M out",
            "context": 262144,
            "note": "Coding-specialist model by Mistral",
        },
        {
            "id": "google/gemini-3.1-flash-lite-preview",
            "name": "Gemini 3.1 Flash Lite",
            "cost": "~$0.25/M in + $1.50/M out",
            "context": 1048576,
            "note": "Fast, cheap, 1M context",
        },
    ],
    "premium": [
        {
            "id": "anthropic/claude-sonnet-4-6",
            "name": "Claude Sonnet 4.6",
            "cost": "~$3/M in + $15/M out",
            "context": 1000000,
            "note": "Best overall coding quality",
        },
        {
            "id": "google/gemini-3.1-pro-preview",
            "name": "Gemini 3.1 Pro",
            "cost": "~$2/M in + $12/M out",
            "context": 1048576,
            "note": "Strong reasoning, 1M context",
        },
        {
            "id": "openai/gpt-4.1",
            "name": "GPT-4.1",
            "cost": "~$2/M in + $8/M out",
            "context": 1047576,
            "note": "OpenAI flagship, excellent tools support",
        },
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
        # Tell OpenRouter to only route to providers that support tool use
        payload["provider"] = {"require_parameters": True}

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
        payload["provider"] = {"require_parameters": True}

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            return {"error": f"OpenRouter API error {response.status_code}: {response.text}"}
        return response.json()
