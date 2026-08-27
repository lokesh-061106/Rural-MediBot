import pytest
from fastapi.testclient import TestClient
import os
import time

from app.main import app
from app.db.database import Base, engine, get_db
from app.models.user import User
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(User).delete()
    
    # Create test users
    admin = User(full_name="Admin", email="admin@test.com", role="admin", password_hash="pw", is_active=True)
    patient1 = User(full_name="Patient 1", email="patient1@test.com", role="patient", password_hash="pw", is_active=True)
    patient2 = User(full_name="Patient 2", email="patient2@test.com", role="patient", password_hash="pw", is_active=True)
    
    db.add(admin)
    db.add(patient1)
    db.add(patient2)
    db.commit()
    
    yield db
    
    db.query(User).delete()
    db.commit()

def test_m6_health_and_ready():
    # Test health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["database"] == "connected"

    # Test readiness check
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"

def test_m6_auth_invalid_token():
    res = client.get("/api/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert res.status_code == 401

def test_m6_auth_expired_token():
    from datetime import timedelta
    # Create an expired token
    expired_token = create_access_token("1", expires_delta=timedelta(minutes=-10))
    res = client.get("/api/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

def test_m6_rbac_admin_protection(setup_db):
    patient = setup_db.query(User).filter_by(email="patient1@test.com").first()
    token = create_access_token(patient.id, role=patient.role)
    
    # Patient trying to access admin verify endpoint
    res = client.post("/api/facilities/999/verify", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_m6_rate_limiting():
    # Clear rate limits first by overriding
    from app.main import request_counts
    request_counts.clear()
    
    responses = []
    for _ in range(55):
        # /api/auth/login is rate limited
        res = client.post("/api/auth/login", data={"username": "test", "password": "pw"})
        responses.append(res.status_code)
    
    assert 429 in responses

def test_m6_cors_headers():
    from app.main import request_counts
    request_counts.clear()
    
    # Preflight request to check CORS
    res = client.options("/api/chat", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers

def test_m6_http_security_headers():
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

