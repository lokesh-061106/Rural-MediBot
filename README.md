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

## CURRENT MILESTONE (M1)
- Initializing the core foundation.
- PostgreSQL database integrated with SQLAlchemy and Alembic.
- Real user registration, login, and JWT-based authentication.
- Role-based Access Control (RBAC).
- AI/RAG system preserved.
- Jitsi telemedicine preserved.

## FUTURE MILESTONES
- Offline-first PWA and IndexedDB sync engine
- ASHA/ANM module and advanced EHR
- Voice assistant (Marathi/Hindi/Odia)
- Advanced telemedicine and ABDM integration
- Emergency ambulance integration and GPS routing
- Pharmacy price comparison and medicine delivery
