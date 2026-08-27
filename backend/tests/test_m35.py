import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_m35_new_endpoints():
    test_email = f"user_{uuid.uuid4()}@example.com"
    doctor_email = f"doc_{uuid.uuid4()}@example.com"
    admin_email = f"admin_{uuid.uuid4()}@example.com"
    test_password = "securepassword123"

    # Register
    client.post("/api/auth/register", json={"email": test_email, "full_name": "Test User", "password": test_password, "role": "patient"})
    client.post("/api/auth/register", json={"email": doctor_email, "full_name": "Test Doc", "password": test_password, "role": "doctor"})
    client.post("/api/auth/register", json={"email": admin_email, "full_name": "Test Admin", "password": test_password, "role": "admin"})

    # Login
    user_token = client.post("/api/auth/login", json={"email": test_email, "password": test_password}).json()["access_token"]
    doc_token = client.post("/api/auth/login", json={"email": doctor_email, "password": test_password}).json()["access_token"]
    admin_token = client.post("/api/auth/login", json={"email": admin_email, "password": test_password}).json()["access_token"]

    # Reminders CRUD
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.post("/api/reminders/", json={"medicine_name": "Aspirin", "time": "10:00", "frequency": "Daily"}, headers=headers)
    assert res.status_code == 200
    reminder_id = res.json()["id"]

    res = client.get("/api/reminders/", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.put(f"/api/reminders/{reminder_id}", json={"active": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["active"] == False
    
    res = client.delete(f"/api/reminders/{reminder_id}", headers=headers)
    assert res.status_code == 200

    # Admin endpoints
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/admin/overview", headers=admin_headers)
    assert res.status_code == 200
    assert "stats" in res.json()

    res = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert res.status_code == 200

    # Facility deactivation
    res = client.post("/api/facilities/", json={
        "name": "Test Fac",
        "facility_type": "PHC",
        "address": "123",
        "latitude": 0,
        "longitude": 0
    }, headers=admin_headers)
    assert res.status_code == 200
    fac_id = res.json()["id"]

    res = client.delete(f"/api/facilities/{fac_id}", headers=admin_headers)
    assert res.status_code == 200
    
    res = client.post(f"/api/facilities/{fac_id}/reactivate", headers=admin_headers)
    assert res.status_code == 200

    # Offline sync
    res = client.post("/api/sync/events", json={
        "events": [
            {
                "client_id": "test_event_1",
                "event_type": "test",
                "payload": {"data": "test"},
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    }, headers=headers)
    assert res.status_code == 200
    assert "test_event_1" in res.json()["synced_client_ids"]
    
    # Idempotent sync check
    res = client.post("/api/sync/events", json={
        "events": [
            {
                "client_id": "test_event_1",
                "event_type": "test",
                "payload": {"data": "test"},
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    }, headers=headers)
    assert res.status_code == 200

    # Doctor endpoint
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    res = client.get("/api/doctor/consultations", headers=doc_headers)
    assert res.status_code == 200
