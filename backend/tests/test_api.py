import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine
import uuid

# Recreate tables for test (using sqlite)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# We use random emails to ensure tests don't collide if DB persists
test_email = f"test_{uuid.uuid4()}@example.com"
test_password = "securepassword123"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register():
    response = client.post(
        "/api/auth/register",
        json={
            "email": test_email,
            "full_name": "Test User",
            "password": test_password,
            "role": "patient"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_email
    assert data["role"] == "patient"
    assert "password_hash" not in data
    assert "password" not in data

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

def test_login_success():
    response = client.post(
        "/api/auth/login",
        json={
            "email": test_email,
            "password": test_password
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    global access_token
    access_token = data["access_token"]

def test_login_failure():
    response = client.post(
        "/api/auth/login",
        json={
            "email": test_email,
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

def test_auth_me():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_email

def test_profile_update():
    # Get profile first
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Update profile
    response = client.put(
        "/api/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "village": "Rural Village 1",
            "blood_group": "O+"
        }
    )
    assert response.status_code == 200
    assert response.json()["village"] == "Rural Village 1"

def test_chat():
    response = client.post(
        "/api/chat",
        json={
            "query": "Hello",
            "thread_id": "test_user"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["status"] == "success"
