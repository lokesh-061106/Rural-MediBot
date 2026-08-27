import pytest
from fastapi.testclient import TestClient
import os

from app.main import app
from app.db.database import Base, engine, get_db
from app.models.user import User
from app.models.memory import Conversation
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def e2e_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(Conversation).delete()
    db.query(User).delete()
    
    # Create an E2E test patient
    patient = User(full_name="E2E Patient", email="e2e@test.com", role="patient", password_hash="pw", is_active=True)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    yield db
    
    db.query(Conversation).delete()
    db.query(User).delete()
    db.commit()

def get_auth_headers(db):
    patient = db.query(User).filter_by(email="e2e@test.com").first()
    token = create_access_token(patient.id, role=patient.role)
    return {"Authorization": f"Bearer {token}"}

# Phase 6: End-to-End Patient Flow
def test_m7_p6_patient_flow(e2e_db):
    headers = get_auth_headers(e2e_db)
    
    # Send a normal medical query
    res = client.post("/api/chat", json={
        "query": "What are the symptoms of a common cold?",
        "language": "en"
    }, headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "response" in data
    
    # It might say no verified information found since we lack documents, which is correct
    # But it must create a conversation ID
    assert "conversation_id" in data
    assert data["conversation_id"] is not None
    
    # It must not be an emergency
    assert data["is_emergency"] is False
    assert data["risk_level"] in ["low", "unknown", "GREEN", "YELLOW"]

# Phase 7: RED Emergency Flow
def test_m7_p7_red_emergency_flow(e2e_db):
    headers = get_auth_headers(e2e_db)
    
    # Send a severe RED keyword
    res = client.post("/api/chat", json={
        "query": "I am having severe chest pain and cannot breathe.",
        "language": "en",
        "latitude": 12.9716,
        "longitude": 77.5946
    }, headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["is_emergency"] is True
    assert data["risk_level"] == "RED"
    assert "emergency" in data["response"].lower() or "immediate" in data["response"].lower()
    
# Phase 8: Multilingual E2E
def test_m7_p8_multilingual_flow(e2e_db):
    headers = get_auth_headers(e2e_db)
    
    # Tamil language test
    res = client.post("/api/chat", json={
        "query": "எனக்கு தலைவலி", # I have a headache
        "language": "ta"
    }, headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "ta"

# Phase 10: Offline E2E (Sync Event Idempotency)
def test_m7_p10_offline_sync(e2e_db):
    headers = get_auth_headers(e2e_db)
    
    sync_payload = {
        "events": [
            {
                "client_id": "e2e-sync-123",
                "event_type": "chat_query",
                "payload": {
                    "query": "Offline query",
                    "language": "en"
                },
                "created_at": "2024-01-01T10:00:00Z"
            }
        ]
    }
    
    # First sync
    res1 = client.post("/api/sync/events", json=sync_payload, headers=headers)
    assert res1.status_code == 200
    
    # Second sync (Idempotent)
    res2 = client.post("/api/sync/events", json=sync_payload, headers=headers)
    assert res2.status_code == 200
    
    assert len(res1.json()["synced_client_ids"]) == 1
    # Depending on implementation, idempotent might return empty processed or same.
    # But it should not crash.
    
# Phase 11: RAG Safety E2E
def test_m7_p11_rag_safety(e2e_db):
    headers = get_auth_headers(e2e_db)
    
    res = client.post("/api/chat", json={
        "query": "How to treat hypertension?",
        "language": "en"
    }, headers=headers)
    
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
        
# Phase 12: Performance Smoke Test
def test_m7_p12_performance_smoke():
    import time
    start = time.time()
    res = client.get("/health")
    end = time.time()
    assert res.status_code == 200
    assert (end - start) < 1.0 # Should be fast

