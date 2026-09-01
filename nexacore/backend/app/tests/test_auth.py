"""
Basic smoke test for the health endpoint. Full auth test suite (register/login/
protected routes with a test DB) lands alongside Phase 1 completion.
"""
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.deps import get_current_user, get_db
from app.db.base import Base
from app.models.user import User
from app.models.discovery_event import DiscoveryEvent
from app.core.security import hash_password

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_malformed_password_hash_is_invalid_credentials():
    from app.core.security import verify_password

    assert verify_password("probe", "not-a-bcrypt-hash") is False


def test_registration_verification_and_owner_approval_gate():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    app.dependency_overrides[get_db] = lambda: (yield db)
    try:
        client = TestClient(app)
        owner_response = client.post("/api/v1/auth/register", json={"email": "owner@workspace.example.com", "password": "password123"})
        assert owner_response.status_code == 201
        assert owner_response.json()["user"]["role"] == "owner"
        successful_login = client.post("/api/v1/auth/login", json={"email": "owner@workspace.example.com", "password": "password123"})
        assert successful_login.status_code == 200
        access_token = successful_login.json()["access_token"]
        protected_properties = client.get("/api/v1/properties/", headers={"Authorization": f"Bearer {access_token}"})
        assert protected_properties.status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": "owner@workspace.example.com", "password": "wrong-password"}).status_code == 401
        malformed_login = client.post("/api/v1/auth/login", json={"email": "owner@workspace.example.com"})
        assert malformed_login.status_code == 422
        assert malformed_login.json()["detail"][0]["loc"] == ["body", "password"]

        pending_response = client.post("/api/v1/auth/register", json={"email": "agent@workspace.example.com", "password": "password123"})
        assert pending_response.status_code == 201
        pending = pending_response.json()
        assert pending["user"]["approval_status"] == "pending"
        assert pending["user"]["email_verified"] is False
        assert client.post("/api/v1/auth/login", json={"email": "agent@workspace.example.com", "password": "password123"}).status_code == 403

        verify_response = client.post("/api/v1/auth/verify-email", json={"token": pending["verification_token"]})
        assert verify_response.status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": "agent@workspace.example.com", "password": "password123"}).status_code == 403

        owner = db.query(User).filter(User.email == "owner@workspace.example.com").one()
        agent = db.query(User).filter(User.email == "agent@workspace.example.com").one()
        app.dependency_overrides[get_current_user] = lambda: owner
        approval = client.patch(f"/api/v1/users/{agent.id}/approve", json={"role": "agent"})
        assert approval.status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": "agent@workspace.example.com", "password": "password123"}).status_code == 200
        assert {event.event_type for event in db.query(DiscoveryEvent).all()} >= {"user_registered", "user_email_verified", "user_approved"}
    finally:
        app.dependency_overrides.clear()
        db.close()
