"""Tests for agent API endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_estimate_complexity(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/agent/estimate-complexity",
        json={"title": "Fix typo in README"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "free"
    assert "reason" in data
    assert "estimated_files" in data


def test_estimate_complexity_complex(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/agent/estimate-complexity",
        json={
            "title": "Add auth with database migration",
            "body": "Implement authentication, authorization, encryption, API endpoint, frontend component, security review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] in ("balanced", "premium")
    assert data["score"] > 3.0


def test_list_models(client: TestClient, auth_headers: dict):
    resp = client.get("/api/agent/models", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "free" in data
    assert "balanced" in data
    assert "premium" in data
    assert len(data["free"]) > 0


def test_start_agent_issue_not_found(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/agent/start",
        json={"issue_id": 9999, "model_tier": "free"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_get_job_status_not_found(client: TestClient, auth_headers: dict):
    resp = client.get("/api/agent/nonexistent-job/status", headers=auth_headers)
    assert resp.status_code == 404


def test_stream_job_not_found(client: TestClient, auth_headers: dict):
    resp = client.get("/api/agent/nonexistent-job/stream", headers=auth_headers)
    assert resp.status_code == 404
