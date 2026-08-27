import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db, engine, Base
from app.core import security
from app.models.user import User
from app.models.memory import Conversation, Message, PatientContext
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def setup_users(db_session):
    user_a = User(full_name="Patient A", email="patient.a@example.com", password_hash="hash", role="patient")
    user_b = User(full_name="Patient B", email="patient.b@example.com", password_hash="hash", role="patient")
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)
    
    token_a = security.create_access_token(user_a.id)
    token_b = security.create_access_token(user_b.id)
    
    return {"a": {"id": user_a.id, "token": token_a}, "b": {"id": user_b.id, "token": token_b}}

def test_patient_context_update(setup_users):
    client = TestClient(app)
    token = setup_users["a"]["token"]
    
    # Update context
    res = client.put(
        "/api/patient-context/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sex": "male",
            "known_conditions": ["hypertension"],
            "allergies": ["penicillin"]
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sex"] == "male"
    assert "hypertension" in data["known_conditions"]

    # Retrieve context
    res2 = client.get(
        "/api/patient-context/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res2.status_code == 200
    assert res2.json()["known_conditions"] == ["hypertension"]

def test_chat_creates_conversation(setup_users):
    client = TestClient(app)
    token = setup_users["a"]["token"]
    
    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Hello, MediBot", "language": "en"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["conversation_id"] is not None
    assert data["language"] == "en"
    
    # Store ID for next test
    return data["conversation_id"]

def test_offline_sync_chat_query(setup_users):
    """Verify that offline chat messages sync correctly and persist to a conversation."""
    client = TestClient(app)
    token = setup_users["a"]["token"]
    
    # 1. Create a conversation
    res_conv = client.post(
        "/api/conversations/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Sync Test", "language": "en"}
    )
    assert res_conv.status_code == 200
    conv_id = res_conv.json()["id"]

    # 2. Sync an offline event with this conversation_id
    sync_payload = {
        "events": [
            {
                "client_id": "test_offline_msg_1",
                "event_type": "chat_query",
                "payload": {
                    "query": "I had a chest pain offline",
                    "conversation_id": conv_id,
                    "language": "en",
                    "is_emergency": True
                },
                "created_at": "2026-08-27T12:00:00Z"
            }
        ]
    }
    
    res_sync = client.post(
        "/api/sync/events",
        headers={"Authorization": f"Bearer {token}"},
        json=sync_payload
    )
    assert res_sync.status_code == 200
    assert "test_offline_msg_1" in res_sync.json()["synced_client_ids"]
    
    # 3. Check if the message is in the conversation
    res_msgs = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_msgs.status_code == 200
    msgs = res_msgs.json()
    
    # There should be 2 messages (1 user, 1 assistant)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "I had a chest pain offline"
    
    assert msgs[1]["role"] == "assistant"
    assert "MEDICAL EMERGENCY DETECTED" in msgs[1]["content"]
    assert msgs[1]["risk_level"] == "RED"
    
    # 4. Idempotency test (sync same message again)
    res_sync_2 = client.post(
        "/api/sync/events",
        headers={"Authorization": f"Bearer {token}"},
        json=sync_payload
    )
    assert res_sync_2.status_code == 200
    
    # Messages should still be 2 (no duplicates)
    res_msgs_2 = client.get(
        f"/api/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert len(res_msgs_2.json()) == 2

def test_chat_continues_conversation(setup_users):
    client = TestClient(app)
    token = setup_users["a"]["token"]
    
    # First message
    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "My stomach hurts.", "language": "en"}
    )
    conv_id = res.json()["conversation_id"]
    
    # Second message
    res2 = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Can I take antacids?", "language": "en", "conversation_id": conv_id}
    )
    assert res2.json()["conversation_id"] == conv_id

def test_conversation_ownership(setup_users):
    client = TestClient(app)
    token_a = setup_users["a"]["token"]
    token_b = setup_users["b"]["token"]
    
    # A creates conv
    res = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"query": "Private message"}
    )
    conv_id = res.json()["conversation_id"]
    
    # B tries to read
    res_b = client.get(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 404  # Explicit 404 for IDOR protection
    
    # B tries to chat on A's conv (should create new or drop ID, but let's check chat endpoint logic)
    res_b2 = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"query": "Hack", "conversation_id": conv_id}
    )
    # The API is designed to drop the unauthorized conversation_id and create a new one
    assert res_b2.json()["conversation_id"] != conv_id

def test_emergency_override_memory(setup_users):
    client = TestClient(app)
    token = setup_users["a"]["token"]
    
    # First message is safe
    res1 = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "I am feeling fine.", "language": "en"}
    )
    conv_id = res1.json()["conversation_id"]
    assert res1.json()["is_emergency"] == False
    
    # Second message is deterministic emergency (should override safe context)
    res2 = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "I have severe chest pain and cannot breathe.", "language": "en", "conversation_id": conv_id}
    )
    data = res2.json()
    assert data["is_emergency"] == True
    assert data["risk_level"] == "RED"
    assert data["triage"]["should_bypass_rag"] == True
