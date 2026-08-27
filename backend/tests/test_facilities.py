import os
os.environ["TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite:///./test_medibot.db"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine
import uuid

# Recreate tables for test
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

admin_email = f"admin_fac_{uuid.uuid4()}@example.com"
test_password = "securepassword123"
tokens = {}

def test_setup_admin():
    res = client.post("/api/auth/register", json={"email": admin_email, "full_name": "Admin Fac", "password": test_password, "role": "admin"})
    assert res.status_code == 200
    res_login = client.post("/api/auth/login", json={"email": admin_email, "password": test_password})
    tokens["admin"] = res_login.json()["access_token"]

def test_get_facilities_empty():
    response = client.get("/api/facilities/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_facility():
    facility_data = {
        "name": "Test PHC",
        "facility_type": "PHC",
        "district": "Pune",
        "state": "Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "emergency_available": True
    }
    response = client.post(
        "/api/facilities/",
        json=facility_data,
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test PHC"
    assert data["emergency_available"] == True
    assert "id" in data

def test_create_facility_unauthorized():
    facility_data = {
        "name": "Hacker Clinic",
        "facility_type": "Clinic"
    }
    response = client.post("/api/facilities/", json=facility_data)
    # Should require admin token
    assert response.status_code == 401

def test_get_nearby_facilities():
    # First create one
    client.post(
        "/api/facilities/",
        json={
            "name": "Nearby Hospital",
            "facility_type": "District Hospital",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "emergency_available": True
        },
        headers={"Authorization": f"Bearer {tokens['admin']}"}
    )
    
    # Search nearby
    response = client.get("/api/facilities/nearby?latitude=19.0760&longitude=72.8777&radius_km=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(f["name"] == "Nearby Hospital" for f in data)
