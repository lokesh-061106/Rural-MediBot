from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from agents.state import AgentState
from retrieval.hybrid_search import get_hybrid_retriever
import os

# Lazy initialize Groq LLM and Retriever
_llm = None
_retriever = None

def get_llm():
    global _llm
    if _llm is None:
        if os.environ.get("USE_MOCK_LLM") == "true":
            from langchain_core.language_models import FakeListLLM
            # First response is for triage, second is for QA
            _llm = FakeListLLM(responses=[
                '{"risk_level": "GREEN", "confidence": "high", "reason": "Test", "reason_code": "TEST", "emergency": false, "requires_human_care": false, "should_bypass_rag": false}',
                'Mocked AI response for testing purposes.'
            ])
        else:
            from langchain_groq import ChatGroq
            _llm = ChatGroq(model="llama3-70b-8192", temperature=0)
    return _llm

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = get_hybrid_retriever()
    return _retriever

from app.agents.guardrails import analyze_deterministic_safety
from app.schemas.triage import TriageResult
import json

def triage_node(state: AgentState) -> AgentState:
    """
    Triage Agent: Analyzes the query with deterministic safety checks first, 
    then uses LLM for structured classification if not RED.
    """
    query = state["query"]
    print(f"[Triage Agent] Analyzing query: '{query}'")
    
    # 1. Deterministic First-Pass Safety Layer (Phase 2 & 15)
    deterministic_result = analyze_deterministic_safety(query)
    if deterministic_result:
        print(f"[Triage Agent] DETERMINISTIC RED DETECTED: {deterministic_result['reason_code']}")
        state["triage"] = deterministic_result
        state["is_emergency"] = True
        state["risk_level"] = "RED"
        state["query_type"] = "emergency"
        state["final_answer"] = "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\nPlease call your local emergency services (108) immediately or go to the nearest emergency room. I am an AI and cannot provide emergency medical assistance."
        return state
        
    # 2. LLM Triage for non-RED cases (Phase 4)
    triage_prompt = PromptTemplate.from_template(
        "You are a medical triage assistant. Analyze the user's query and categorize it into exactly ONE of these risk levels: GREEN, YELLOW, ORANGE, RED.\n\n"
        "Definitions:\n"
        "- GREEN: No immediate danger. General self-care or non-medical query.\n"
        "- YELLOW: Symptoms may require routine medical attention.\n"
        "- ORANGE: Potentially serious situation requiring prompt medical evaluation.\n"
        "- RED: Potential emergency. Seek emergency care immediately.\n\n"
        "Return a valid JSON object matching this schema:\n"
        "{{\n"
        "  \"risk_level\": \"<GREEN|YELLOW|ORANGE|RED>\",\n"
        "  \"confidence\": \"<high|medium|low>\",\n"
        "  \"reason\": \"<brief explanation>\",\n"
        "  \"reason_code\": \"<e.g. ROUTINE_QUERY, POTENTIAL_INFECTION, etc>\",\n"
        "  \"emergency\": <true/false>,\n"
        "  \"requires_human_care\": <true/false>,\n"
        "  \"should_bypass_rag\": <true/false>\n"
        "}}\n\n"
        "Query: {query}\n\n"
        "Output ONLY the JSON object, nothing else."
    )
    
    try:
        chain = triage_prompt | get_llm()
        response = chain.invoke({"query": query})
        
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()
        
        # Clean up markdown if the LLM wrapped the JSON in markdown blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        # In mock LLM test environments, FakeListLLM might just return "Mocked AI response..."
        if "Mocked" in content or not content.startswith("{"):
            raise ValueError("Malformed JSON from LLM")
            
        triage_dict = json.loads(content)
        triage_obj = TriageResult(**triage_dict)
        triage_data = triage_obj.model_dump()
        
    except Exception as e:
        print(f"[Triage Agent] LLM Triage failed safely: {str(e)}")
        # Safe deterministic fallback
        triage_data = {
            "risk_level": "YELLOW",
            "confidence": "low",
            "reason": "Fallback triage due to system error. Please exercise caution.",
            "reason_code": "SYSTEM_FALLBACK",
            "emergency": False,
            "requires_human_care": True,
            "should_bypass_rag": False
        }

    # Ensure LLM cannot downgrade a missed RED if it decides it's an emergency
    if triage_data["risk_level"] == "RED" or triage_data["emergency"]:
        triage_data["risk_level"] = "RED"
        triage_data["emergency"] = True
        triage_data["should_bypass_rag"] = True

    state["triage"] = triage_data
    state["is_emergency"] = triage_data["emergency"]
    state["risk_level"] = triage_data["risk_level"]
    state["query_type"] = "emergency" if triage_data["emergency"] else "medical"
    
    if triage_data["should_bypass_rag"]:
        state["final_answer"] = "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\nPlease call your local emergency services (108) immediately or go to the nearest emergency room. I am an AI and cannot provide emergency medical assistance."
        
    print(f"[Triage Agent] Final Classification: {state['risk_level']}")
    return state

def retrieval_node(state: AgentState) -> AgentState:
    """
    Retrieval Agent: Fetches relevant documents from the Hybrid Retriever.
    """
    query = state["query"]
    print("[Retrieval Agent] Fetching relevant medical context...")
    
    # Fetch top 3 documents using our hybrid search + reranking
    docs = get_retriever().retrieve_and_rerank(query, top_k=3)
    
    # Convert Document objects to dicts for the state
    formatted_docs = []
    for d in docs:
        formatted_docs.append({
            "content": d.page_content,
            "metadata": d.metadata
        })
        
    state["retrieved_docs"] = formatted_docs
    print(f"[Retrieval Agent] Retrieved {len(formatted_docs)} relevant chunks.")
    
    return state

def qa_node(state: AgentState) -> AgentState:
    """
    QA Agent: Generates a medically accurate response based ONLY on the retrieved documents.
    """
    query = state["query"]
    docs = state.get("retrieved_docs", [])
    
    if state.get("query_type") == "general":
        print("[QA Agent] Handling general query...")
        state["final_answer"] = "I am MediBot, an AI-powered healthcare assistant. How can I help you with medical information today?"
        return state
        
    print("[QA Agent] Generating medical response...")
    
    if not docs:
        state["final_answer"] = "I'm sorry, I couldn't find any relevant medical information in my knowledge base to answer your question. Please consult a healthcare professional."
        return state
        
    context_str = ""
    for idx, doc in enumerate(docs):
        score = doc['metadata'].get('relevance_score', 0)
        context_str += f"--- Source {idx+1} (Relevance: {score:.2f}) ---\n{doc['content']}\n\n"
        
    qa_prompt = PromptTemplate.from_template(
        "You are an expert medical AI assistant (MediBot). Your task is to answer the user's question based strictly on the provided medical context.\n\n"
        "Rules:\n"
        "1. Do not use outside knowledge. If the context does not contain the answer, say 'I do not have enough information to answer this.'\n"
        "2. Do not prescribe medication or provide definitive diagnoses.\n"
        "3. Always include a disclaimer at the end stating 'Disclaimer: This information is for educational purposes and is not a substitute for professional medical advice.'\n"
        "4. Be compassionate and professional.\n"
        "5. CRITICAL: You must answer in the user's requested language ({language}). If you cannot, fallback to English safely.\n\n"
        "Context:\n{context}\n\n"
        "User Question: {query}\n\n"
        "Answer:"
    )
    
    chain = qa_prompt | get_llm()
    response = chain.invoke({
        "context": context_str, 
        "query": query,
        "language": state.get("language", "en")
    })
    if hasattr(response, "content"):
        content = response.content.strip()
    else:
        content = str(response).strip()
    
    # Extract sources for Explainability
    sources_list = []
    sources_text = "\n\n**Sources used:**\n"
    for idx, doc in enumerate(docs):
        source_name = doc['metadata'].get('source', 'Unknown File').split('\\')[-1]
        score = doc['metadata'].get('relevance_score', 0)
        
        sources_list.append({
            "source": source_name,
            "relevance_score": score,
            "content": doc['content']
        })
        sources_text += f"- {source_name} (Confidence: {score:.2f})\n"
        
    state["final_answer"] = content + sources_text
    state["sources"] = sources_list
    
    return state
