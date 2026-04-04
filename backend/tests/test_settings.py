from fastapi.testclient import TestClient


def test_get_settings_empty(client: TestClient, auth_headers: dict):
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"settings": {}}


def test_put_settings(client: TestClient, auth_headers: dict):
    resp = client.put(
        "/api/settings",
        headers=auth_headers,
        json=[
            {"key": "openrouter_api_key", "value": "sk-test-123"},
            {"key": "github_token", "value": "ghp_test456"},
        ],
    )
    assert resp.status_code == 200
    data = resp.json()["settings"]
    assert data["openrouter_api_key"] == "sk-test-123"
    assert data["github_token"] == "ghp_test456"


def test_update_existing_setting(client: TestClient, auth_headers: dict):
    client.put("/api/settings", headers=auth_headers, json=[{"key": "key1", "value": "v1"}])
    client.put("/api/settings", headers=auth_headers, json=[{"key": "key1", "value": "v2"}])
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.json()["settings"]["key1"] == "v2"


def test_settings_unauthorized(client: TestClient):
    resp = client.get("/api/settings")
    assert resp.status_code == 401
