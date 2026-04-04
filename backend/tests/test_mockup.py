"""Tests for the mockup generation endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from backend.core.encryption import encrypt_value
from backend.models.database import Setting


def _seed_gemini_key(session: Session, user_id: int = 1):
    setting = Setting(
        user_id=user_id,
        key="gemini_api_key",
        value_encrypted=encrypt_value("test-gemini-key"),
    )
    session.add(setting)
    session.commit()


def test_mockup_no_auth(client):
    resp = client.post("/api/mockup", json={"title": "Test", "description": "test"})
    assert resp.status_code == 401


def test_mockup_no_gemini_key(client, auth_headers):
    resp = client.post(
        "/api/mockup",
        json={"title": "Test", "description": "A test feature"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Gemini API key" in resp.json()["detail"]


@patch("backend.api.mockup._call_gemini", new_callable=AsyncMock)
def test_mockup_success(mock_gemini, client, auth_headers, session):
    _seed_gemini_key(session)

    mock_gemini.return_value = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"

    resp = client.post(
        "/api/mockup",
        json={"title": "Login Page", "description": "A login page with email and password fields"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "image_base64" in data
    assert data["image_base64"] == "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    assert "model_used" in data


@patch("backend.api.mockup._call_gemini", new_callable=AsyncMock)
def test_mockup_all_models_fail(mock_gemini, client, auth_headers, session):
    _seed_gemini_key(session)

    mock_gemini.side_effect = Exception("API error")

    resp = client.post(
        "/api/mockup",
        json={"title": "Test", "description": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 502
    assert "failed" in resp.json()["detail"].lower()


@patch("backend.api.mockup._call_gemini", new_callable=AsyncMock)
def test_mockup_first_model_fails_second_succeeds(mock_gemini, client, auth_headers, session):
    _seed_gemini_key(session)

    mock_gemini.side_effect = [
        Exception("Model not available"),
        "base64imagedata",
    ]

    resp = client.post(
        "/api/mockup",
        json={"title": "Dashboard", "description": "Admin dashboard with charts"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["image_base64"] == "base64imagedata"
