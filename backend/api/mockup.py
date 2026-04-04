"""Mockup generator using Gemini API image generation."""

from __future__ import annotations

import base64
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value
from backend.models.database import Setting, User

router = APIRouter(prefix="/api", tags=["mockup"])

GEMINI_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
]


class MockupRequest(BaseModel):
    title: str
    description: str


class MockupResponse(BaseModel):
    image_base64: str
    model_used: str


@router.post("/mockup", response_model=MockupResponse)
async def generate_mockup(
    req: MockupRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Get Gemini API key
    setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "gemini_api_key")
    ).first()
    if not setting:
        raise HTTPException(status_code=400, detail="Gemini API key not configured")

    api_key = decrypt_value(setting.value_encrypted)

    prompt = (
        f"Create a clean wireframe mockup for: {req.title}\n\n"
        f"{req.description}\n\n"
        "Simple black and white UI wireframe sketch style. "
        "Show the layout, buttons, text areas, and navigation elements. "
        "Clean, minimal, professional wireframe only."
    )

    # Try models in order
    last_error = None
    for model in GEMINI_MODELS:
        try:
            result = await _call_gemini(api_key, model, prompt)
            if result:
                return MockupResponse(image_base64=result, model_used=model)
        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(
        status_code=502,
        detail=f"Mockup generation failed with all models. Last error: {last_error}",
    )


async def _call_gemini(api_key: str, model: str, prompt: str) -> str | None:
    """Call Gemini API to generate an image. Returns base64 string or None."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = await client.post(
            url,
            params={"key": api_key},
            json=payload,
        )

        if response.status_code != 200:
            raise Exception(f"Gemini API error {response.status_code}: {response.text[:200]}")

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                return part["inlineData"]["data"]

        return None
