from fastapi.testclient import TestClient

def test_register_success(client: TestClient):
    payload = {
        "email": "fresh_user@finpilot.in",
        "password": "SecurePassword123!",
        "full_name": "Fresh User",
        "currency": "INR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "fresh_user@finpilot.in"
    assert data["user"]["full_name"] == "Fresh User"

def test_register_duplicate_email(client: TestClient, auth_user: dict):
    payload = {
        "email": auth_user["user"]["email"],
        "password": "AnotherPassword123!",
        "full_name": "Duplicate User",
        "currency": "INR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error_code"] == "RESOURCE_CONFLICT"

def test_register_short_password(client: TestClient):
    payload = {
        "email": "shortpass@finpilot.in",
        "password": "123",  # < 8 chars
        "full_name": "Short Pass",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

def test_login_success(client: TestClient):
    email = "login_test@finpilot.in"
    password = "MyPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Login Tester"
    })

    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

def test_login_wrong_password(client: TestClient, auth_user: dict):
    res = client.post("/api/v1/auth/login", json={
        "email": auth_user["user"]["email"],
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401
    assert res.json()["error_code"] == "UNAUTHORIZED"

def test_demo_login(client: TestClient):
    res = client.post("/api/v1/auth/demo-login")
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "demo@finpilot.in"
    assert data["user"]["full_name"] == "Rahul Sharma"
    assert data["user"]["is_demo"] is True
    assert "access_token" in data

def test_me_endpoint(client: TestClient, auth_user: dict):
    # Authenticated
    res = client.get("/api/v1/auth/me", headers=auth_user["headers"])
    assert res.status_code == 200
    assert res.json()["email"] == auth_user["user"]["email"]

    # Unauthenticated
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
