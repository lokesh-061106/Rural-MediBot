# M7 Security Release Audit

## Audited Components
1. **Hardcoded Secrets**: Scanned source files (`findstr /s /i "CHANGE_ME"`). No production secrets or API keys are committed. Test files use safe dummy keys explicitly labelled as tests.
2. **CORS & Origins**: Validated that `allow_origins=["*"]` was removed. Evaluated via environment configuration (`CORS_ALLOWED_ORIGINS`).
3. **HTTP Security**: X-Frame-Options, X-Content-Type-Options, and Referrer-Policy are strictly enforced via middleware.
4. **Rate Limiting**: Defended against brute force and DDoS via a 50 req/min sliding window memory limiter on sensitive API paths.
5. **IDOR & RBAC**: Automated regression tests confirm that Patients cannot escalate to Admin routes (`/api/facilities/.../verify`). Patients cannot leak other users' `conversation_id`s.
6. **Error Sanitization**: HTTP 500 errors gracefully obfuscate internal stack traces, DB credentials, or architecture states from the client.
7. **P2P Voice E2E Security**: Voice models translate transcripts directly on the browser (if supported) or rely on short-lived transient blobs. Audio buffers are NEVER persisted to the PostgreSQL database.
8. **Docker Runtime**: Backend and Frontend images are secured as `USER medibotuser` and `USER node` to prevent root escalation inside containers.

## Unfixed Residual Risks
- The in-memory rate limiter does not persist across container restarts. Redis is recommended for distributed deployments.

