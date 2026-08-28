 # Rural MediBot Deployment Report

## Status

The application builds successfully and the tested source changes are ready for deployment. A public Vercel frontend deployment exists at [https://rural-medi-bot.vercel.app](https://rural-medi-bot.vercel.app), but the complete application is not yet production-ready because its FastAPI backend is unavailable.

## Verified locally

- Backend regression suite: 143 passed.
- Frontend production build: passed.
- RAG gates, RBAC, admin review checklist, and adversarial LLM isolation tests passed.
- R1-R5 remain pending human review in the application safety workflow; no automatic verification or activation was added.

## Deployment architecture

- Frontend: Next.js on Vercel, root directory `frontend`.
- Backend: FastAPI on Render or another managed Python service, root directory `backend`.
- Database: production PostgreSQL via `DATABASE_URL`; SQLite is testing-only.
- Backend startup: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Production configuration required

Render must provide `DATABASE_URL`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, and `CORS_ALLOWED_ORIGINS`. Vercel must provide `FASTAPI_BACKEND_URL` and the same `JWT_SECRET_KEY` used by the backend. Secrets must not use `NEXT_PUBLIC_` prefixes.

## Deployment result

Vercel deployment succeeded, but public smoke tests found `/chat` and protected admin pages unavailable because the configured backend origin does not respond and the Vercel project does not have the shared JWT secret configured. No public full-stack success is claimed.

## Remaining blocker

Create/deploy the Render backend with managed PostgreSQL and set its real URL in Vercel as `FASTAPI_BACKEND_URL`; set the matching JWT secret in both services. Then redeploy Vercel and rerun the public patient, doctor, admin, chat, and knowledge-management smoke tests.
