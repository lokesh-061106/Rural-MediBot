from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import sys
import os

# Ensure the app directory is in the path so we can import agents
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph import run_medibot

app = FastAPI(
    title="MediBot Backend API",
    description="FastAPI backend for the MediBot RAG Healthcare Platform",
    version="1.0.0"
)

# Allow CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    thread_id: str = "default_user_1"
    language: str = "en"
    conversation_id: Optional[int] = None

class EvidenceItem(BaseModel):
    document_id: str
    title: str
    filename: str
    source: str
    source_type: str
    chunk_index: int
    relevance_score: float
    excerpt: str

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.sync import router as sync_router
from app.api.facilities import router as facilities_router
from app.api.admin import router as admin_router
from app.api.reminders import router as reminders_router
from app.api.doctor import router as doctor_router
from app.api.conversations import router as conversations_router
from app.api.patient_context import router as patient_context_router
from app.db.database import engine, Base

# Optional: Create tables if not using Alembic (for quick testing), but we use Alembic
# Base.metadata.create_all(bind=engine)

# Include API Routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(facilities_router, prefix="/api/facilities", tags=["facilities"])
app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(reminders_router, prefix="/api/reminders", tags=["reminders"])
app.include_router(sync_router, prefix="/api/sync", tags=["sync"])
app.include_router(conversations_router, prefix="/api/conversations", tags=["conversations"])
app.include_router(patient_context_router, prefix="/api/patient-context", tags=["patient-context"])
@app.get("/")
def read_root():
    return {"status": "ok", "message": "MediBot API is running"}

@app.get("/health")
def health_check():
    try:
        # Simple DB check
        with engine.connect() as conn:
            pass
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
        
    return {"status": "healthy", "database": db_status}

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.optional_deps import get_optional_user
from app.models.user import User
from app.models.memory import Conversation, Message
from app.agents.graph import run_medibot

from app.memory.persistence import MemoryService

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    try:
        conversation_id = request.conversation_id
        
        # Verify ownership if provided
        if conversation_id and current_user:
            conv = MemoryService.get_conversation(db, conversation_id, current_user.id)
            if not conv:
                # Security: do not leak existence of other users' conversations
                conversation_id = None
        
        # Create conversation automatically if missing but authenticated
        if not conversation_id and current_user:
            conv = MemoryService.create_conversation(db, current_user.id, request.query[:50], request.language)
            conversation_id = conv.id
            
        # Persist user message
        if conversation_id and current_user:
            MemoryService.save_message(
                db, 
                conversation_id=conversation_id, 
                role="user", 
                content=request.query, 
                language=request.language
            )

        # Run the LangGraph orchestration
        user_id = current_user.id if current_user else None
        
        import time
        from app.core.logger import observability_logger, request_id_ctx_var
        import uuid
        
        req_id = str(uuid.uuid4())
        request_id_ctx_var.set(req_id)
        
        # Use conversation_id to isolate LangGraph short-lived execution state
        graph_thread_id = f"conv_{conversation_id}" if conversation_id else request.thread_id
        
        start_time = time.time()
        result = run_medibot(
            query=request.query, 
            thread_id=graph_thread_id, 
            language=request.language,
            conversation_id=conversation_id,
            user_id=user_id,
            db=db
        )
        total_latency_ms = (time.time() - start_time) * 1000
        
        # result is now a dictionary containing final_answer and sources
        if isinstance(result, dict):
            final_answer = result.get("final_answer", "")
            is_emergency = result.get("is_emergency", False)
            risk_level = result.get("risk_level", "low")
            triage_info = result.get("triage", None)
            recommended_facility = result.get("recommended_facility", None)
            evidence = result.get("evidence", [])
        else:
            # Fallback if result is just a string (old behavior)
            final_answer = result
            is_emergency = False
            risk_level = "low"
            triage_info = None
            recommended_facility = None
            evidence = []
            
        # Persist assistant response
        if conversation_id and current_user:
            reason_code = "emergency" if is_emergency else "standard"
            MemoryService.save_message(
                db,
                conversation_id=conversation_id,
                role="assistant",
                content=final_answer,
                language=request.language,
                risk_level=risk_level,
                reason_code=reason_code,
                evidence_list=evidence
            )
            
        observability_logger.info("Chat request completed", extra={"observability_data": {
            "endpoint": "/api/chat",
            "processing_time_ms": total_latency_ms,
            "risk_level": risk_level,
            "reason_code": "emergency" if is_emergency else "standard",
            "evidence_count": len(evidence),
            "language": request.language,
            "retrieval_latency_ms": result.get("retrieval_latency_ms"),
            "generation_latency_ms": result.get("generation_latency_ms"),
            "triage_latency_ms": result.get("triage_latency_ms"),
            "conversation_id": conversation_id
        }})
            
        return {
            "response": final_answer,
            "evidence": evidence,
            "is_emergency": is_emergency,
            "risk_level": risk_level,
            "triage": triage_info,
            "recommended_facility": recommended_facility,
            "language": request.language,
            "conversation_id": conversation_id,
            "status": "success"
        }
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}", "status": "error"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
