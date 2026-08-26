# M0 BASELINE REPORT - SIH26133
**Status:** Verified & Copied
**Date:** 2026-08-26

This report documents the exact state of the manually copied `MediBot` codebase before any SIH26133-specific transformation or fixes are applied.

## A. Current Architecture
The application currently features a disconnected hybrid architecture:
1. **Frontend:** A Next.js (App Router) application that serves the UI and proxies chat requests.
2. **Backend:** A Python FastAPI server located at `backend/main.py`. However, the backend heavily relies on root-level modules (`agents/`, `rag/`, `retrieval/`, `vector_db/`) making it essentially a Python monolith overlapping with a Next.js workspace.
3. **Communication:** The Next.js frontend calls the FastAPI backend via a proxied HTTP POST request (`/api/chat`).

## B. Technology Stack
- **Frontend:** Next.js 16.2.10, React 19, Tailwind CSS 4.
- **Backend:** FastAPI, Python, LangChain, LangGraph.
- **AI/Vector DB:** ChromaDB (local), Sentence-Transformers (local embeddings), Groq (llama3-70b-8192).
- **Authentication:** `jose` (JWT) implemented purely in Next.js memory.
- **Telemedicine:** Jitsi Meet React SDK (`@jitsi/react-sdk`).

## C. Existing Features
- **AI Triage & Chat:** LangGraph orchestrated agents (Triage -> Retrieval -> QA) using Groq.
- **Telemedicine:** Basic Jitsi Meet integration in the frontend.
- **Medication Reminders:** Frontend-only implementation using `localStorage`.
- **Role-based Dashboards:** Static UI for Patient, Doctor, and Admin roles.

## D. Database Structure
- **PostgreSQL / SQLAlchemy:** Listed in `requirements.txt` and `docker-compose.yml`, but **NOT USED** in any Python code.
- **SQLite (Memory):** LangGraph uses a local `memory/checkpoints.sqlite` file for session state.
- **SQLite (medibot.db):** A leftover file in the root containing tables like `users`, `appointments`, but it is completely disconnected from the actual application code.
- **Vector DB:** ChromaDB is used locally (`vector_db/chroma_data/chroma.sqlite3`).

## E. API Structure
**Next.js API:**
- `POST /api/auth/login`: Mocked authentication
- `POST /api/auth/register`: Mocked user registration
- `GET /api/auth/me`: Decodes JWT
- `POST /api/chat`: Proxies to FastAPI

**FastAPI Backend:**
- `GET /`: Health check
- `GET /health`: Health check
- `POST /api/chat`: Orchestrates LangGraph agent workflow

## F. Authentication Status
- **Static/Mocked.** Authentication is managed by `frontend/lib/auth.js`.
- It uses a hardcoded `DEFAULT_USERS` array containing an admin, a doctor, and a patient.
- Changes are held in-memory and lost upon Next.js server restart.

## G. AI Integration Status
- **Working.** LangChain/LangGraph is implemented in `agents/`.
- Uses Groq API (`llama3-70b-8192`) instead of Gemini (despite instructions suggesting Gemini might be used, Groq is the actual implementation).
- Implements a basic Triage system, classifying queries as `emergency`, `medical`, or `general`.

## H. Existing User Roles
- `admin` (e.g., admin@medibot.com)
- `doctor` (e.g., doctor@medibot.com)
- `patient` (e.g., patient@medibot.com)

## I. Existing Pages/Routes
- `/` - Landing page
- `/login`, `/register` - Authentication UI
- `/chat` - AI Chat Interface
- `/dashboard` - Patient Dashboard
- `/doctor` - Doctor Dashboard
- `/admin` - Admin Dashboard
- `/reminders` - Medication Reminders
- `/reports` - Patient Reports / Analytics
- `/telemedicine` - Jitsi Video Consultation

## J. Working Features
- **Telemedicine:** The Jitsi integration works natively on the client side.
- **Chat/Triage:** The FastAPI backend correctly processes queries and retrieves documents from the local ChromaDB.

## K. Partial Features
- **Medication Reminders:** UI works, but state is tied exclusively to the browser's `localStorage` (offline-only, device-specific).

## L. Static/Mock Features
- **Authentication:** In-memory only.
- **Reports/Dashboards:** UI is present but data is static or hardcoded.

## M. Broken Features
- **Docker Compose:** The provided `docker-compose.yml` is severely broken. It attempts to build a `./backend` context, but the necessary Python modules (`agents`, `rag`, etc.) exist in the root directory. It also provides environment variables for a Vite app (`VITE_API_BASE_URL`), but the frontend is actually Next.js.
- **Database Connection:** PostgreSQL is spun up via Docker but completely ignored by the code.

## N. Security Issues
- **Hardcoded Secrets:** `JWT_SECRET` and `GROQ_API_KEY` are hardcoded or tracked in `.env.local` and `docker-compose.yml`.
- **Plaintext Passwords:** Mock user passwords are in plain text inside `lib/auth.js`.
- **AI Safety:** While triage exists, the system relies heavily on the LLM prompt to prevent dangerous prescriptions.

## O. Environment Variables
- `GROQ_API_KEY`: Required for LLM inference.
- `FASTAPI_BACKEND_URL`: Used by Next.js to locate the backend (defaults to `http://localhost:8000`).
*(Note: A sanitized `.env.example` has been created during this M0 step).*

## P. Deployment Status
- **Broken.** The current repository structure prevents successful containerized deployment due to mismatched contexts and hardcoded local paths.

## Q. Recommended Migration Priorities for SIH26133
1. **P0 - Codebase Restructuring:** Move root Python modules into the `backend/` folder to allow proper Docker builds and separation of concerns.
2. **P0 - Real Database Integration:** Connect FastAPI (or Next.js) to the PostgreSQL database for persistent Authentication, Users, and EHR functionality.
3. **P0 - Docker Configuration:** Rewrite `docker-compose.yml` to correctly build Next.js and FastAPI with accurate environment variables.
4. **P1 - Offline-First Foundation:** Implement a Service Worker and IndexedDB in the Next.js frontend to meet the core SIH requirement.
