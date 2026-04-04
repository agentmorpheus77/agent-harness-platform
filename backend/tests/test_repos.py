from fastapi.testclient import TestClient


def test_list_repos_empty(client: TestClient, auth_headers: dict):
    resp = client.get("/api/repos", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_repo(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/repos",
        headers=auth_headers,
        json={"github_full_name": "owner/repo", "deploy_provider": "railway"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["github_full_name"] == "owner/repo"
    assert data["deploy_provider"] == "railway"


def test_list_repos_after_create(client: TestClient, auth_headers: dict):
    client.post("/api/repos", headers=auth_headers, json={"github_full_name": "owner/repo"})
    resp = client.get("/api/repos", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_repos_unauthorized(client: TestClient):
    resp = client.get("/api/repos")
    assert resp.status_code == 401
