from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.state import AgentState
from agents.nodes import triage_node, retrieval_node, qa_node
import sqlite3
import os

# Create Memory Database Path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory", "checkpoints.sqlite")

def route_triage(state: AgentState):
    """
    Routing logic after the Triage node.
    """
    # M4.2 Deterministic Safety bypass
    triage_info = state.get("triage", {})
    if state.get("is_emergency") or triage_info.get("should_bypass_rag"):
        return "end"
    elif state.get("query_type") == "general":
        return "qa_node"
    else:
        return "retrieval_node"

# 1. Initialize StateGraph
graph_builder = StateGraph(AgentState)

# 2. Add Nodes
graph_builder.add_node("triage_node", triage_node)
graph_builder.add_node("retrieval_node", retrieval_node)
graph_builder.add_node("qa_node", qa_node)

# 3. Define Edges
# The graph always starts at the Triage Agent
graph_builder.set_entry_point("triage_node")

# From Triage, route dynamically
graph_builder.add_conditional_edges(
    "triage_node",
    route_triage,
    {
        "end": END,
        "qa_node": "qa_node",
        "retrieval_node": "retrieval_node"
    }
)

# After Retrieval, always go to QA
graph_builder.add_edge("retrieval_node", "qa_node")

# After QA, end the flow
graph_builder.add_edge("qa_node", END)

# 4. Initialize Memory Saver (SQLite)
# This enables long-term conversation memory and human-in-the-loop capabilities
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
memory_saver = SqliteSaver(conn)

# 5. Compile the Graph
medibot_graph = graph_builder.compile(checkpointer=memory_saver)

from sqlalchemy.orm import Session
from app.models.memory import Message, PatientContext, Conversation

def run_medibot(
    query: str, 
    thread_id: str = "default_user_1", 
    language: str = "en",
    conversation_id: int = None,
    user_id: int = None,
    db: Session = None
):
    """
    Entry point to run the LangGraph workflow.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    chat_history = []
    patient_context_text = ""
    
    if db and user_id:
        # Load Patient Context
        ctx = db.query(PatientContext).filter(PatientContext.user_id == user_id).first()
        if ctx:
            context_parts = []
            if ctx.known_conditions:
                context_parts.append(f"Known conditions: {', '.join(ctx.known_conditions)}")
            if ctx.allergies:
                context_parts.append(f"Allergies: {', '.join(ctx.allergies)}")
            if ctx.current_medications:
                context_parts.append(f"Medications: {', '.join(ctx.current_medications)}")
            if ctx.relevant_notes:
                context_parts.append(f"Notes: {ctx.relevant_notes}")
            patient_context_text = " | ".join(context_parts)
            
        # Load Recent Messages (Bounded Context Strategy)
        if conversation_id:
            max_msgs = int(os.environ.get("MAX_CONTEXT_MESSAGES", "10"))
            recent_msgs = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(max_msgs).all()
            
            # Reverse to chronological
            for m in reversed(recent_msgs):
                chat_history.append({"role": m.role, "content": m.content})

    
    # Run the graph
    result = medibot_graph.invoke({
        "query": query, 
        "language": language,
        "chat_history": chat_history,
        "patient_context": patient_context_text
    }, config=config)
    
    triage_info = result.get("triage", {})
    return {
        "final_answer": result.get("final_answer", ""),
        "sources": result.get("sources", []),
        "is_emergency": result.get("is_emergency", False),
        "risk_level": result.get("risk_level", "GREEN"),
        "triage": triage_info,
        "recommended_facility": result.get("recommended_facility_type", None)
    }

if __name__ == "__main__":
    # Test the workflow
    print("\n--- Test 1: Medical Query ---")
    print(run_medibot("What happens when blood sugar goes up?"))
    
    print("\n--- Test 2: Emergency Query ---")
    print(run_medibot("I am having severe chest pain right now!"))
    
    print("\n--- Test 3: General Query ---")
    print(run_medibot("Hello, who are you?"))
