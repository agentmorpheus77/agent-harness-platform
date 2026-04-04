from fastapi.testclient import TestClient


def test_register(client: TestClient):
    resp = client.post("/api/auth/register", json={"email": "new@example.com", "password": "pass123"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate(client: TestClient):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    resp = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    assert resp.status_code == 400


def test_login(client: TestClient):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client: TestClient):
    client.post("/api/auth/register", json={"email": "wrong@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_me(client: TestClient, auth_headers: dict):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "admin"  # First user is admin


def test_me_unauthorized(client: TestClient):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
