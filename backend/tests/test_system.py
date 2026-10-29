from fastapi.testclient import TestClient

def test_root_index(client: TestClient):
    """Verify welcome root endpoint provides documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert data["documentation"] == "/docs"

def test_health_probe(client: TestClient):
    """Verify liveness probe returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
