import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.guardrails import analyze_deterministic_safety
from app.schemas.triage import TriageResult
import os
import json

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["TESTING"] = "true"
    os.environ["USE_MOCK_LLM"] = "true"
    yield
    
def test_deterministic_red_english():
    result = analyze_deterministic_safety("I am having a heart attack!")
    assert result is not None
    assert result["risk_level"] == "RED"
    assert result["emergency"] is True

def test_deterministic_red_hindi():
    result = analyze_deterministic_safety("मुझे दिल का दौरा पड़ रहा है")
    assert result is not None
    assert result["risk_level"] == "RED"

def test_deterministic_red_hindi_romanized():
    result = analyze_deterministic_safety("mujhe dil ka daura pad raha hai")
    assert result is not None
    assert result["risk_level"] == "RED"

def test_deterministic_red_marathi():
    result = analyze_deterministic_safety("माझ्या छातीत दुखते")
    assert result is not None
    assert result["risk_level"] == "RED"

def test_deterministic_red_tamil():
    result = analyze_deterministic_safety("எனக்கு மாரடைப்பு")
    assert result is not None
    assert result["risk_level"] == "RED"

def test_non_emergency_safe():
    result = analyze_deterministic_safety("I have a mild headache")
    assert result is None  # Should pass to LLM

def test_api_chat_compatibility():
    response = client.post("/api/chat", json={"query": "Hello", "thread_id": "test_1"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "risk_level" in data
    assert "is_emergency" in data
    
def test_api_chat_red_bypass():
    response = client.post("/api/chat", json={"query": "I can't breathe", "thread_id": "test_2"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "RED"
    assert data["is_emergency"] is True
    assert "MEDICAL EMERGENCY DETECTED" in data["response"]
    # Bypasses RAG
    assert data["triage"]["should_bypass_rag"] is True

def test_schema_validation():
    # Test valid schema creation
    triage = TriageResult(
        risk_level="YELLOW",
        confidence="high",
        reason="Mild fever",
        reason_code="FEVER",
        emergency=False,
        requires_human_care=False,
        should_bypass_rag=False
    )
    assert triage.risk_level == "YELLOW"

def test_malformed_llm_fallback(monkeypatch):
    # Test what happens when LLM outputs garbage by forcing Mocked LLM string output
    # By default, FakeListLLM in testing might output invalid JSON for triage if we don't mock it nicely,
    # but we fixed FakeListLLM to return valid JSON in `nodes.py`.
    # Let's bypass and test the fallback directly in the node logic.
    from app.agents.nodes import triage_node
    from app.agents.state import AgentState
    
    state: AgentState = {
        "query": "malformed_trigger",
        "retrieved_docs": [],
        "sources": [],
        "is_emergency": False,
        "query_type": None,
        "final_answer": None,
        "triage": None,
        "risk_level": None
    }
    
    # We temporarily monkeypatch get_llm to return bad JSON
    from langchain_core.language_models import FakeListLLM
    import app.agents.nodes as nodes
    monkeypatch.setattr(nodes, "get_llm", lambda: FakeListLLM(responses=["Not JSON"]))
    
    new_state = triage_node(state)
    # The fallback should catch the exception and set to YELLOW safe fallback
    assert new_state["triage"]["risk_level"] == "YELLOW"
    assert new_state["triage"]["reason_code"] == "SYSTEM_FALLBACK"

def test_red_cannot_be_downgraded(monkeypatch):
    from app.agents.nodes import triage_node
    
    state = {
        "query": "I am bleeding heavily", # triggers deterministic RED
        "retrieved_docs": [],
        "sources": [],
        "is_emergency": False
    }
    
    new_state = triage_node(state)
    assert new_state["risk_level"] == "RED"
    assert new_state["triage"]["should_bypass_rag"] is True

def test_green_classification():
    response = client.post("/api/chat", json={"query": "Hello", "thread_id": "test_green"})
    # FakeListLLM is set to return GREEN JSON first
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "GREEN"

# Phase 6 & 11 logic (Facility/GPS fallback) is tested in UI integration and existing facility tests.
