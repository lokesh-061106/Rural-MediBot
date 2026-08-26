# Rural MediBot - SIH26133

## PROJECT
Rural MediBot

## SIH PROBLEM STATEMENT
SIH26133 - Accessibility and quality of public healthcare services, particularly in rural and underserved areas.

## CURRENT ARCHITECTURE
The application features a Next.js (App Router) frontend and a FastAPI backend using a shared PostgreSQL database.
- **Frontend**: Next.js 16.2.10, React 19, Tailwind CSS 4
- **Backend**: FastAPI, Python 3, SQLAlchemy, Alembic
- **AI Engine**: LangChain, LangGraph, Groq, ChromaDB, Sentence Transformers

## DATABASE
PostgreSQL is the primary application database for user data, profiles, and audit logs.
SQLite is used for LangGraph state checkpointing (memory).
ChromaDB is used for vector search.

## AUTHENTICATION & USER ROLES
- JWT-based authentication
- Secure password hashing using bcrypt
- Roles: `patient`, `doctor`, `admin`

## LOCAL DEVELOPMENT

### ENVIRONMENT SETUP
1. Copy `.env.example` to `.env`
2. Update the `GROQ_API_KEY` and other credentials.

### DOCKER SETUP (Recommended)
You can run the entire stack using Docker Compose:
```bash
docker compose up -d --build
```

### MANUAL SETUP

#### POSTGRESQL SETUP
Ensure PostgreSQL is running locally and update `DATABASE_URL` in `.env`.
For local testing without PostgreSQL, you can use SQLite by setting:
`DATABASE_URL=sqlite:///./medibot.db`

#### ALEMBIC MIGRATIONS
Initialize the database schema:
```bash
cd backend
alembic upgrade head
```

#### RUNNING BACKEND
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### RUNNING FRONTEND
```bash
cd frontend
npm install
npm run dev
```

#### RUNNING TESTS
```bash
cd backend
pytest tests/
```

## API DOCUMENTATION
When the backend is running, visit `http://localhost:8000/docs` to view the interactive OpenAPI documentation.

## CURRENT MILESTONE (M1.1)
- Hardened foundation with mockable AI dependency.
- Fixed global LLM initialization to prevent `pytest` collection failures.
- Implemented robust `pytest` suite for Authentication, JWT, and RBAC tests without requiring real `GROQ_API_KEY`.
- Refactored `database.py` to prevent silent SQLite fallback in production, ensuring PostgreSQL is explicitly required.

## TESTING & VERIFICATION STATUS
### PostgreSQL Verification
- **Status**: Limited local testing due to agent environment restrictions (No Docker/PostgreSQL available natively on test environment).
- **Implementation**: The application enforces PostgreSQL via `DATABASE_URL` in production, rejecting SQLite to prevent silent fallback. For automated testing, `TESTING=true` explicitly permits a sandboxed SQLite instance.

### AI / RAG Testing
- **Status**: Tested with mocked LLM.
- **Implementation**: `USE_MOCK_LLM=true` injects `FakeListLLM` and `FakeEmbeddings` to allow complete API orchestration testing without real API keys, internet, or Groq requests.
- **Real Groq Smoke-test**: Not executed during CI due to unavailable keys.

### Jitsi Verification
- **Status**: Manually verified page structure. No modifications were made to the telemedicine React integration during M1 refactoring. Live video call not automatically tested.

## OFFLINE-FIRST ARCHITECTURE (M2)

Rural MediBot is designed to function gracefully without internet connectivity, ensuring rural users are never stranded.

### Online Architecture
When connected, the PWA functions as a Next.js client communicating with a FastAPI PostgreSQL backend, routing medical queries through a Groq/LangGraph RAG pipeline.

### Offline Architecture
When disconnected, the PWA immediately degrades to an offline-safe mode using:
- **Service Worker (`sw.js`)**: Caches the App Shell, static assets, and Next.js routes.
- **IndexedDB (`idb`)**: Local storage for `local_profile`, `emergency_contacts`, `saved_hospitals`, `chat_queue`, and `reminders`.
- **Connectivity Detection**: A custom React hook (`useConnectivity`) actively monitors network state and drives the `ConnectivityBadge` UI.

### Emergency Fallback
The offline Chat intercepts messages client-side. If a critical keyword (e.g., "heart attack", "chest pain", "सांस लेने में दिक्कत") is detected across English, Hindi, Marathi, or Tamil, the local Safety Engine immediately routes the user to an Emergency warning. Non-emergencies are queued.

### Sync Engine
Messages queued while offline are stored in IndexedDB with a `PENDING_SYNC` status. Upon reconnection, the Sync Engine automatically flushes them to the backend via `POST /api/sync/events` in an idempotent batch.

### Features
**OFFLINE FEATURES (What Works):**
- App loading and UI navigation
- Accessing saved Emergency Contacts and Hospitals
- Queuing chat queries
- Offline safety triage (Emergency keyword detection)
- Local Medication Reminders

**ONLINE FEATURES (Requires Connectivity):**
- AI/LLM conversational responses
- Telemedicine (Jitsi video calls)
- Real-time profile synchronization

**NOT YET IMPLEMENTED:**
- Advanced Offline Maps/Directions
- Pharmacy API Integration
- Multilingual Speech-to-Text / Text-to-Speech
- ABDM / Government API Integrations

## FUTURE MILESTONES
- Offline-first PWA and IndexedDB sync engine
- ASHA/ANM module and advanced EHR
- Voice assistant (Marathi/Hindi/Odia)
- Advanced telemedicine and ABDM integration
- Emergency ambulance integration and GPS routing
- Pharmacy price comparison and medicine delivery
