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
from app.db.database import engine, Base

# Optional: Create tables if not using Alembic (for quick testing), but we use Alembic
# Base.metadata.create_all(bind=engine)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])

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
        else:
            # Fallback if result is just a string (old behavior)
            final_answer = result
            sources = []
            
        return {
            "response": final_answer,
            "sources": sources,
            "status": "success"
        }
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}", "status": "error"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
