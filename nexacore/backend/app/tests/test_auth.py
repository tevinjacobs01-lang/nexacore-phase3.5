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


def test_malformed_password_hash_is_invalid_credentials():
    from app.core.security import verify_password

    assert verify_password("probe", "not-a-bcrypt-hash") is False
