import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.language import (
    detect_language, 
    normalize_text, 
    prepare_for_triage, 
    prepare_for_generation, 
    format_response,
    SUPPORTED_LANGUAGES
)
import os

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["TESTING"] = "true"
    os.environ["USE_MOCK_LLM"] = "true"
    yield

def test_language_detection():
    # Deterministic fallback is to 'en'
    assert detect_language("Hello") == "en"
    
def test_language_normalization():
    assert normalize_text("  hello  ", "en") == "hello"
    assert normalize_text("", "hi") == ""
    assert normalize_text(None, "ta") == ""

def test_language_preparation():
    assert prepare_for_triage("test", "mr") == "test"
    assert prepare_for_generation("test", "en") == "test"

def test_format_response():
    assert format_response("response", "en") == "response"
    assert format_response("", "ta") == ""

def test_api_chat_language_metadata_propagation():
    response = client.post("/api/chat", json={
        "query": "Hello", 
        "thread_id": "test_lang_1",
        "language": "ta"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "ta"

def test_unsupported_language_fallback():
    # If client passes 'fr', it should just pass it through the state, 
    # the QA prompt handles fallback instructions. 
    response = client.post("/api/chat", json={
        "query": "Bonjour",
        "thread_id": "test_lang_2",
        "language": "fr"
    })
    assert response.status_code == 200
    assert response.json()["language"] == "fr"

def test_deterministic_emergency_detection_after_language():
    # Pass Tamil emergency text
    response = client.post("/api/chat", json={
        "query": "எனக்கு மாரடைப்பு", # "I am having a heart attack"
        "thread_id": "test_lang_3",
        "language": "ta"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "RED"
    assert data["is_emergency"] is True
    assert data["triage"]["reason_code"] == "EMERGENCY_CHEST_PAIN"

def test_malformed_language_input():
    # Just white space
    response = client.post("/api/chat", json={
        "query": "   ",
        "thread_id": "test_lang_4",
        "language": "hi"
    })
    assert response.status_code == 200
    assert response.json()["language"] == "hi"

def test_existing_chat_compatibility():
    # Missing language should default to 'en' in Pydantic schema
    response = client.post("/api/chat", json={
        "query": "Hello",
        "thread_id": "test_lang_5"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"

def test_red_bypasses_qa_node_with_language():
    # "moochu vida siramam" is a romanized Tamil string for breathing difficulty
    response = client.post("/api/chat", json={
        "query": "moochu vida siramam",
        "thread_id": "test_lang_6",
        "language": "ta"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "RED"
    assert data["is_emergency"] is True
    assert data["triage"]["should_bypass_rag"] is True
    assert data["language"] == "ta"
