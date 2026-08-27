# Rural MediBot System Architecture

## Overview
The Rural MediBot is an intelligent, offline-capable, evidence-grounded medical triage assistant.

## Components
1. **Frontend (Next.js + Tailwind + Leaflet)**
   - PWA compliant for offline usage.
   - Syncs IndexedDB queues to backend upon reconnection.
   - Browser-based STT (Speech-to-Text) capabilities.
2. **Backend (FastAPI + LangGraph)**
   - **Triage Node**: Deterministic rule-based keyword matching (e.g., severe bleeding) bypassing LLMs to guarantee response safety.
   - **Retrieval Node**: Hybrid Search (ChromaDB + BM25) with cross-encoder reranking.
   - **QA Node**: Groq API powered Llama3 LLM providing grounded answers referencing exact Document IDs.
3. **Database (PostgreSQL + Alembic)**
   - Manages Users, Conversations, Messages, Facilities, and Sync Events.
4. **Data Science Pipelines**
   - Facility Verification Engine tracking `verified_at` and `STALE` status.

## Data Flow (Normal Query)
Client -> `POST /api/chat` -> JWT Auth -> Triage Engine -> ChromaDB Vector Search -> Langchain QA -> Client.

## Data Flow (Emergency RED Query)
Client -> `POST /api/chat` -> JWT Auth -> Triage Engine (Triggers RED) -> Haversine Facility Lookup -> Immediate Client Response (Bypasses LLM generation entirely).

