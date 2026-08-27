# M6 Production Readiness Guide

## Architecture
Rural MediBot uses FastAPI, Next.js, and PostgreSQL, deployed natively via Docker Compose.

## Environment variables
Refer to `.env.example`. 
- **DATABASE_URL** is required to be PostgreSQL in production.
- **JWT_SECRET_KEY** must be explicitly set to a 32+ character secure string.
- **GROQ_API_KEY** must be provided for RAG generation.
- **CORS_ALLOWED_ORIGINS** comma-separated URLs (e.g. `https://yourdomain.com`).
- **RATE_LIMIT** (default 50 requests/min).
- **FACILITY_STALE_DAYS** (default 180 days).

## Database
SQLite is strictly disallowed in non-TESTING environments. 
All data runs through PostgreSQL (containerized by default). Do not expose port 5432 publicly.

## Auth & RBAC
JWT Tokens have strict expiries (default 24h). 
Invalid/expired tokens return 401. 
Admin actions (facility verification) are protected by RBAC, returning 403 for patients.
Patient contexts are protected against IDOR.

## Rate Limiting & Security Headers
In-memory rate limiter protects `/api/auth` and `/api/chat`. 
HTTP Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) are strictly injected.

## Health & Readiness
- `/health` checks application liveness and Database ping.
- `/ready` checks environment initialization, secret injection, and deep DB state.

## Docker Hardening
Containers run non-root. Development volumes have been stripped. Healthchecks use `python` and `pg_isready`.

## Authoritative Dataset
**AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED**
The system logic is secure and verified, but ships with test data. You MUST supply real MOHFW verified datasets for production.
