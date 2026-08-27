from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
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

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.sync import router as sync_router
from app.api.facilities import router as facilities_router
from app.api.admin import router as admin_router
from app.api.reminders import router as reminders_router
from app.api.doctor import router as doctor_router
from app.db.database import engine, Base

# Optional: Create tables if not using Alembic (for quick testing), but we use Alembic
# Base.metadata.create_all(bind=engine)

# Include API Routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(sync_router, prefix="/api/sync", tags=["sync"])
app.include_router(facilities_router, prefix="/api/facilities", tags=["facilities"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(reminders_router, prefix="/api/reminders", tags=["reminders"])
app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])


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

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Run the LangGraph orchestration
        result = run_medibot(request.query, request.thread_id)
        
        # result is now a dictionary containing final_answer and sources
        if isinstance(result, dict):
            final_answer = result.get("final_answer", "")
            sources = result.get("sources", [])
            is_emergency = result.get("is_emergency", False)
            risk_level = result.get("risk_level", "low")
            triage_info = result.get("triage", None)
            recommended_facility = result.get("recommended_facility", None)
        else:
            # Fallback if result is just a string (old behavior)
            final_answer = result
            sources = []
            is_emergency = False
            risk_level = "low"
            triage_info = None
            recommended_facility = None
            
        return {
            "response": final_answer,
            "sources": sources,
            "is_emergency": is_emergency,
            "risk_level": risk_level,
            "triage": triage_info,
            "recommended_facility": recommended_facility,
            "status": "success"
        }
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}", "status": "error"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
