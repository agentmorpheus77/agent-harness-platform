"""Tests for the chat API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from backend.core.encryption import encrypt_value
from backend.models.database import Repo, Setting, Workspace


def _seed_repo_and_key(session: Session, user_id: int = 1):
    """Create workspace, repo, and OpenRouter key for testing."""
    ws = Workspace(owner_id=user_id, name="Test Workspace")
    session.add(ws)
    session.commit()
    session.refresh(ws)

    repo = Repo(workspace_id=ws.id, github_full_name="testowner/testrepo")
    session.add(repo)
    session.commit()
    session.refresh(repo)

    setting = Setting(
        user_id=user_id,
        key="openrouter_api_key",
        value_encrypted=encrypt_value("sk-test-key"),
    )
    session.add(setting)
    session.commit()
    return repo


def test_chat_start_no_auth(client):
    resp = client.post("/api/chat/start", json={"repo_id": 1})
    assert resp.status_code == 401


def test_chat_start_repo_not_found(client, auth_headers):
    resp = client.post("/api/chat/start", json={"repo_id": 999}, headers=auth_headers)
    assert resp.status_code == 404


def test_chat_start_success(client, auth_headers, session):
    repo = _seed_repo_and_key(session)

    resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "message" in data
    assert "testowner/testrepo" in data["message"]


def test_chat_message_session_not_found(client, auth_headers):
    resp = client.post(
        "/api/chat/nonexistent/message",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@patch("backend.api.chat.chat_completion", new_callable=AsyncMock)
def test_chat_message_success(mock_llm, client, auth_headers, session):
    repo = _seed_repo_and_key(session)

    # Start chat
    start_resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    session_id = start_resp.json()["session_id"]

    # Mock LLM response
    mock_llm.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Got it! What kind of feature is this? A new UI component, API endpoint, or something else?"
                }
            }
        ]
    }

    resp = client.post(
        f"/api/chat/{session_id}/message",
        json={"message": "I want to add a dark mode toggle"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert data["is_draft"] is False


@patch("backend.api.chat.chat_completion", new_callable=AsyncMock)
def test_chat_message_draft_detection(mock_llm, client, auth_headers, session):
    repo = _seed_repo_and_key(session)

    start_resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    session_id = start_resp.json()["session_id"]

    # Mock LLM returning a draft
    mock_llm.return_value = {
        "choices": [
            {
                "message": {
                    "content": "**Title: Add dark mode toggle**\n\n## Description\nAdd a toggle to switch between dark and light mode.\n\n## Acceptance Criteria\n- Toggle in header\n- Persists across sessions"
                }
            }
        ]
    }

    resp = client.post(
        f"/api/chat/{session_id}/message",
        json={"message": "Yes, that's correct"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_draft"] is True
    assert data["draft_title"] == "Add dark mode toggle"


@patch("backend.api.chat.chat_completion", new_callable=AsyncMock)
def test_chat_message_ui_feature_detection(mock_llm, client, auth_headers, session):
    repo = _seed_repo_and_key(session)

    start_resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    session_id = start_resp.json()["session_id"]

    mock_llm.return_value = {
        "choices": [
            {
                "message": {
                    "content": "[UI] **Title: Redesign navigation bar**\n\n## Description\nModern sidebar nav."
                }
            }
        ]
    }

    resp = client.post(
        f"/api/chat/{session_id}/message",
        json={"message": "I want to redesign the nav"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_ui_feature"] is True


@patch("backend.api.chat.chat_completion", new_callable=AsyncMock)
def test_chat_message_no_api_key(mock_llm, client, auth_headers, session):
    # Create repo without API key
    ws = Workspace(owner_id=1, name="No Key WS")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    repo = Repo(workspace_id=ws.id, github_full_name="owner/repo")
    session.add(repo)
    session.commit()
    session.refresh(repo)

    start_resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    session_id = start_resp.json()["session_id"]

    resp = client.post(
        f"/api/chat/{session_id}/message",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "OpenRouter API key" in resp.json()["detail"]


@patch("backend.api.chat.chat_completion", new_callable=AsyncMock)
def test_chat_message_llm_error(mock_llm, client, auth_headers, session):
    repo = _seed_repo_and_key(session)

    start_resp = client.post("/api/chat/start", json={"repo_id": repo.id}, headers=auth_headers)
    session_id = start_resp.json()["session_id"]

    mock_llm.return_value = {"error": "Rate limit exceeded"}

    resp = client.post(
        f"/api/chat/{session_id}/message",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert resp.status_code == 502
