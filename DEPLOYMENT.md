# Rural MediBot Deployment

## Architecture

Deploy `frontend` to Vercel and `backend` to Render (or another managed Python service). Production requires PostgreSQL; local SQLite is only for testing.

## Render Backend

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

### Server-only secrets

Set these in Render. Never expose them with a `NEXT_PUBLIC_` prefix.

- `DATABASE_URL`: managed PostgreSQL connection string
- `JWT_SECRET_KEY`: random secret of at least 32 characters
- `GROQ_API_KEY`: Groq API key used by the current LLM integration
- `CORS_ALLOWED_ORIGINS`: exact Vercel origin, for example `https://your-project.vercel.app`

Optional server settings: `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `RATE_LIMIT`, `FACILITY_STALE_DAYS`, `EVIDENCE_THRESHOLD`, `RAG_TOP_K`, and `MAX_CONTEXT_MESSAGES`.

## Vercel Frontend

- Root directory: `frontend`
- Framework: Next.js
- Build command: `npm run build`

### Server-only deployment variable

- `FASTAPI_BACKEND_URL`: deployed backend origin, for example `https://your-backend.onrender.com`

`NEXT_PUBLIC_API_URL` is only needed for local development or when intentionally exposing a public API origin. The frontend fails closed during production builds when no backend origin is configured; it never silently targets localhost in production.

## Safety and data

R1-R5 must remain `PENDING_REVIEW`, inactive, and non-authoritative until a real administrator completes the existing checklist workflow. Do not seed or auto-verify them during deployment. Run document ingestion separately only after the source files and provenance have been reviewed.

## Verification

After both services are deployed:

1. Confirm `https://<backend>/health` and `/ready` return success.
2. Set `FASTAPI_BACKEND_URL` in Vercel and redeploy.
3. Verify home, registration/login, patient chat, doctor routes, admin dashboard, and `/admin/knowledge`.
4. Confirm browser requests contain no localhost or `127.0.0.1` production URLs.
5. Confirm R1-R5 remain pending and RAG rejects unverified, inactive, stale, demo, and non-authoritative documents.
