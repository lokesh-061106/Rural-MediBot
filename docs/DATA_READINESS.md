# Production Data Readiness

## Medical Knowledge Documents (RAG)
**STATUS: AUTHORITATIVE MEDICAL DATASET NOT AVAILABLE**

Currently, there are no authoritative medical protocols or guidelines ingested into the system. The `backend/data/documents` directory only contains test placeholders.

### Authoritative Medical Source Requirements
To safely deploy this AI in a clinical setting, all RAG documents MUST strictly adhere to the following rules:

1. **Accepted Authoritative Sources**:
   - Official Ministry of Health and Family Welfare (MOHFW) guidelines.
   - World Health Organization (WHO) clinical protocols.
   - State-level Directorate of Health Services (DHS) standard treatment guidelines.

2. **Verification Requirements**:
   - Documents must be signed or officially published by the authoritative body.
   - A Chief Medical Officer (CMO) or equivalent medical administrator must digitally verify the document prior to ingestion (`verification_status = VERIFIED`).
   - The document MUST be explicitly flagged as `is_authoritative = True`.

3. **Document Provenance Requirements**:
   - Source URL or official registry ID must be provided.
   - The ingestion pipeline intrinsically generates a cryptographic `content_hash` (SHA-256 equivalent) to guarantee file integrity.

4. **Version / Freshness Requirements**:
   - The document `version` must explicitly match the officially published version.
   - Medical guidelines older than 3 years must be flagged for review to prevent medical staleness.

5. **Rejection Rules for Untrusted Documents**:
   - ANY document lacking `is_authoritative = True` and `verification_status = VERIFIED` is STRICTLY DROPPED by the Hybrid Retrieval engine.
   - Synthetic fixtures, textbooks without explicit state approval, and generic internet articles are permanently rejected.
   - The LLM will fall back to safe disclaimers ("I do not have verified information") rather than citing unverified sources.

### Blockers for Deployment:
- The MOHFW or an equivalent authoritative medical body must provide official clinical guidelines.
- These documents must be verified for accuracy and ingested through the M8.1 pipeline.
- Do NOT fabricate medical protocols.

## Healthcare Facility Network
**STATUS: NOT VERIFIED / REQUIRES EXTERNAL DATA**

There is no verified dataset of real rural healthcare facilities integrated.

### Blockers for Deployment:
- A verified, government-backed dataset of PHCs/CHCs must be provided.
- Do NOT fabricate government facilities or coordinates.

## Conclusion
The system architecture and integration pipelines are production-ready (IMPLEMENTED and VERIFIED). However, the actual application is **BLOCKED — EXTERNAL DATA REQUIRED** before real-world clinical usage.

