import os
os.environ["TESTING"] = "true"
os.environ["USE_MOCK_LLM"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite:///./test_medibot.db"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine
from app.models.user import UserRole
import uuid

# Recreate tables for test (using sqlite fallback for testing environment only)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

test_email = f"patient_{uuid.uuid4()}@example.com"
test_password = "securepassword123"

doctor_email = f"doctor_{uuid.uuid4()}@example.com"
admin_email = f"admin_{uuid.uuid4()}@example.com"

# Global tokens
tokens = {}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_patient():
    response = client.post(
        "/api/auth/register",
        json={
            "email": test_email,
            "full_name": "Test Patient",
            "password": test_password,
            "role": "patient"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_email
    assert data["role"] == "patient"
    assert "password_hash" not in data

def test_duplicate_register():
    response = client.post(
        "/api/auth/register",
        json={
            "email": test_email,
            "full_name": "Duplicate User",
            "password": test_password
        }
    )
    assert response.status_code == 400

def test_register_doctor_and_admin():
    res1 = client.post("/api/auth/register", json={"email": doctor_email, "full_name": "Doc", "password": test_password, "role": "doctor"})
    res2 = client.post("/api/auth/register", json={"email": admin_email, "full_name": "Admin", "password": test_password, "role": "admin"})
    assert res1.status_code == 200
    assert res2.status_code == 200

def test_login_success():
    response = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": test_password}
    )
    assert response.status_code == 200
    tokens["patient"] = response.json()["access_token"]
    
    res_doc = client.post("/api/auth/login", json={"email": doctor_email, "password": test_password})
    tokens["doctor"] = res_doc.json()["access_token"]
    
    res_admin = client.post("/api/auth/login", json={"email": admin_email, "password": test_password})
    tokens["admin"] = res_admin.json()["access_token"]

def test_login_wrong_password():
    response = client.post("/api/auth/login", json={"email": test_email, "password": "wrongpassword"})
    assert response.status_code == 401

def test_missing_token():
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_invalid_token():
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401

def test_auth_me():
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['patient']}"})
    assert response.status_code == 200
    assert response.json()["email"] == test_email

def test_profile_update():
    response = client.put(
        "/api/users/me",
        headers={"Authorization": f"Bearer {tokens['patient']}"},
        json={"village": "Test Village", "blood_group": "O+"}
    )
    assert response.status_code == 200
    assert response.json()["village"] == "Test Village"
    
    get_res = client.get("/api/users/me", headers={"Authorization": f"Bearer {tokens['patient']}"})
    assert get_res.json()["blood_group"] == "O+"

# Test RBAC
def test_rbac_doctor_endpoint():
    from fastapi import APIRouter, Depends
    from app.api.deps import require_role
    
    # We dynamically add a test endpoint to verify the role checker
    @app.get("/api/test-doctor", dependencies=[Depends(require_role("doctor"))])
    def doctor_only():
        return {"success": True}
        
    # Patient tries to access
    res = client.get("/api/test-doctor", headers={"Authorization": f"Bearer {tokens['patient']}"})
    assert res.status_code == 403
    
    # Doctor tries to access
    res = client.get("/api/test-doctor", headers={"Authorization": f"Bearer {tokens['doctor']}"})
    assert res.status_code == 200
    
    # Admin tries to access (Admin usually has all roles in our simple RBAC rule)
    res = client.get("/api/test-doctor", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res.status_code == 200

def test_chat_mocked():
    response = client.post(
        "/api/chat",
        json={"query": "What is diabetes?", "thread_id": "test_thread"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["status"] == "success"
    # Since nodes drop unverified evidence, it triggers safe fallback
    assert "verified medical information" in data["response"].lower() or "mocked" in data["response"].lower()
