from tests.conftest import register


def test_register_returns_token_and_user(client):
    res = register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert "password_hash" not in body["user"]


def test_register_duplicate_email(client):
    register(client)
    res = register(client, email="ALICE@example.com")
    assert res.status_code == 409


def test_register_validation(client):
    res = register(client, password="short")
    assert res.status_code == 422


def test_login_success_and_me(client):
    register(client)
    res = client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Alice"


def test_login_wrong_password(client):
    register(client)
    res = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrongpass1"})
    assert res.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
