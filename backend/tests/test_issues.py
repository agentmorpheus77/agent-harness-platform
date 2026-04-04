from fastapi.testclient import TestClient


def test_list_issues_empty(client: TestClient, auth_headers: dict):
    resp = client.get("/api/issues", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_issues_with_repo_filter(client: TestClient, auth_headers: dict):
    resp = client.get("/api/issues?repo_id=999", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_issues_unauthorized(client: TestClient):
    resp = client.get("/api/issues")
    assert resp.status_code == 401
