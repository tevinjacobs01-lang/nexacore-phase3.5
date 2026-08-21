"""
Basic smoke test for the health endpoint. Full auth test suite (register/login/
protected routes with a test DB) lands alongside Phase 1 completion.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
