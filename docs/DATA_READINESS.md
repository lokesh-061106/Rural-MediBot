# Production Data Readiness (M8.2)

## Medical Knowledge Documents (RAG)
**STATUS: AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED**

Currently, there are no authoritative medical protocols or guidelines ingested into the system. The `backend/data/documents` directory only contains test placeholders.

### Authoritative Medical Source Requirements
To safely deploy this AI in a clinical setting, all RAG documents MUST strictly adhere to the following rules:

1. **Accepted Authoritative Sources**:
   - Official Ministry of Health and Family Welfare (MOHFW) guidelines.
   - World Health Organization (WHO) clinical protocols.
   - State-level Directorate of Health Services (DHS) standard treatment guidelines.

2. **Verification Requirements (Controlled Lifecycle)**:
   - New ingestions default to `PENDING_REVIEW` with `is_authoritative = False` and `verification_status = UNVERIFIED`.
   - An administrator MUST verify the document using the backend API. 
   - A document must be both `VERIFIED` and activated (`ACTIVE`) to be served to the AI.
   - Demo/test fixtures are NEVER automatically verified.

3. **Document Provenance Requirements**:
   - `publisher` / issuing organization MUST be explicitly provided to pass validation.
   - `source_url` and `publication_date` must be stored if available.
   - The ingestion pipeline calculates a deterministic `content_hash` guaranteeing exact file integrity and idempotency.

4. **Version / Freshness Requirements**:
   - A new version of an existing file safely enters `PENDING_REVIEW` without disabling the current `ACTIVE` protocol.
   - Only when the new version is verified and activated does the old version become `DEPRECATED`.
   - This ensures safe fallback and zero downtime of medical guidance.

5. **Rejection Rules for Untrusted Documents (RAG Safety)**:
   - ANY document lacking `is_authoritative = True`, `verification_status = VERIFIED`, and `status = ACTIVE` is STRICTLY DROPPED by the Hybrid Retrieval engine.
   - The LLM safely falls back to disclaimers instead of using unverified sources.

### Blockers for Deployment:
- The MOHFW or an equivalent authoritative medical body must provide official clinical guidelines.
- These documents must be verified for accuracy and ingested through the M8.2 pipeline.
- Do NOT fabricate medical protocols.

## Healthcare Facility Network
**STATUS: AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED**

There is no verified dataset of real rural healthcare facilities integrated.

### Blockers for Deployment:
- A verified, government-backed dataset of PHCs/CHCs must be provided.
- Facility ingestion requires deterministic `name` and `source` and rejects invalid coordinates.
- Unverified ingestions correctly protect previously `VERIFIED` facilities from downgrade.
- Do NOT fabricate government facilities or coordinates.

## Conclusion
The system architecture and integration pipelines are production-ready (IMPLEMENTED and VERIFIED). However, the actual application is **BLOCKED — EXTERNAL DATA REQUIRED** before real-world clinical usage.

