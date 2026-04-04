"""Tests for the issue submission endpoint."""

from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest
from sqlmodel import Session

from backend.core.encryption import encrypt_value
from backend.models.database import Repo, Setting, Workspace


def _seed_repo_and_token(session: Session, user_id: int = 1):
    """Create workspace, repo, and GitHub token for testing."""
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
        key="github_token",
        value_encrypted=encrypt_value("ghp_testtoken123"),
    )
    session.add(setting)
    session.commit()
    return repo


def test_submit_issue_no_auth(client):
    resp = client.post("/api/issues/submit", json={"repo_id": 1, "title": "Test", "body": "test"})
    assert resp.status_code == 401


def test_submit_issue_repo_not_found(client, auth_headers):
    resp = client.post(
        "/api/issues/submit",
        json={"repo_id": 999, "title": "Test", "body": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_submit_issue_no_github_token(client, auth_headers, session):
    ws = Workspace(owner_id=1, name="Test")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    repo = Repo(workspace_id=ws.id, github_full_name="owner/repo")
    session.add(repo)
    session.commit()
    session.refresh(repo)

    resp = client.post(
        "/api/issues/submit",
        json={"repo_id": repo.id, "title": "Test", "body": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "GitHub token" in resp.json()["detail"]


@patch("backend.api.issues.httpx.AsyncClient")
def test_submit_issue_success(mock_client_class, client, auth_headers, session):
    repo = _seed_repo_and_token(session)

    # Mock GitHub API response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "number": 42,
        "html_url": "https://github.com/testowner/testrepo/issues/42",
        "title": "Add export feature",
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    resp = client.post(
        "/api/issues/submit",
        json={
            "repo_id": repo.id,
            "title": "Add export feature",
            "body": "## Description\nAdd PDF export button",
            "labels": ["enhancement"],
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["github_issue_number"] == 42
    assert data["github_url"] == "https://github.com/testowner/testrepo/issues/42"
    assert data["title"] == "Add export feature"


@patch("backend.api.issues.httpx.AsyncClient")
def test_submit_issue_github_api_error(mock_client_class, client, auth_headers, session):
    repo = _seed_repo_and_token(session)

    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.text = "Validation failed"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_class.return_value = mock_client

    resp = client.post(
        "/api/issues/submit",
        json={"repo_id": repo.id, "title": "Test", "body": "test"},
        headers=auth_headers,
    )

    assert resp.status_code == 502
    assert "GitHub API error" in resp.json()["detail"]
