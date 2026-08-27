# Rural MediBot — Production Data Readiness

> Last updated: M8.4 — Authoritative Data Acquisition & Controlled Production Ingestion

---

## Quick Summary

| Readiness Gate | Status |
|---|---|
| Engineering Readiness | ✅ IMPLEMENTED |
| Data Readiness (Medical) | ❌ BLOCKED — AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED |
| Data Readiness (Facility) | ❌ BLOCKED — AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED |
| Clinical Readiness | ❌ BLOCKED — Cannot serve clinical guidance without verified data |
| Deployment Readiness | ⚠️ CONDITIONAL — Software is production-hardened; data is absent |

> **The software stack is production-grade. The application is NOT clinically deployable until real authoritative data is supplied, verified, and activated by an authorized administrator.**

---

## 1. Engineering Readiness

**STATUS: ✅ FULLY IMPLEMENTED**

The Medibot software stack from M3.5 through M8.3 is implemented, tested, and hardened:

| Component | Status |
|---|---|
| Backend API (FastAPI + PostgreSQL) | ✅ Production-hardened |
| Frontend (Next.js 16) | ✅ Production build passing |
| Authentication & RBAC | ✅ JWT + role-based access control |
| Clinical Safety Triage (RED/YELLOW/ORANGE/GREEN) | ✅ Implemented (M4.2) |
| Multilingual + Voice | ✅ Implemented (M4.3) |
| Persistent Conversation Memory | ✅ Implemented (M4.4) |
| Offline Sync | ✅ Implemented (M4.4.1) |
| Evidence-Grounded RAG (Hybrid Search + Cross-Encoder) | ✅ Implemented (M4.5) |
| Clinical Safety Observability | ✅ Implemented (M4.6) |
| Facility Network + Emergency Routing | ✅ Implemented (M5.1) |
| Facility Ingestion + Verification Lifecycle | ✅ Implemented (M5.2/M5.3) |
| Production Hardening (CORS, rate limiting, security headers) | ✅ Implemented (M6) |
| CI/CD, Docker, health checks | ✅ Implemented (M7) |
| Authoritative Data Readiness Validation | ✅ Implemented (M8.1) |
| Controlled Ingestion + Verification Lifecycle | ✅ Implemented (M8.2) |
| Data Classifier + M8.3 Ingestion Framework | ✅ Implemented (M8.3) |
| Backend Tests | ✅ 89/89 passing |

---

## 2. Data Readiness — Medical Knowledge

**STATUS: ❌ BLOCKED — AUTHORITATIVE PRODUCTION DATASET: NOT VERIFIED**

### What Is in the Repository

| File | Classification | Reason |
|---|---|---|
| `backend/data/documents/test_health.txt` | **DEMO** | 50-byte placeholder ("Fever is a common sign of illness. Updated text!") – explicitly not a clinical guideline |
| `backend/data/documents/R1.pdf` | **UNVERIFIED / PENDING_REVIEW** | National Health Mission guidelines (MoHFW) ingested but pending admin verification |
| `backend/data/documents/R2.pdf` | **UNVERIFIED / PENDING_REVIEW** | Maternal health guidelines (MoHFW) ingested but pending admin verification |
| `backend/data/documents/R3.pdf` | **UNVERIFIED / PENDING_REVIEW** | Directorate General of Health Services guidelines ingested but pending admin verification |
| `backend/data/documents/R4.pdf` | **UNVERIFIED / PENDING_REVIEW** | Central TB Division guidelines ingested but pending admin verification |
| `backend/data/documents/R5.pdf` | **UNVERIFIED / PENDING_REVIEW** | National Centre for Disease Control (NCDC) guidelines ingested but pending admin verification |

Authoritative medical documents have been supplied and successfully ingested. However, they remain strictly blocked from the production RAG pipeline until an authorized administrator explicitly verifies and activates them.

### What Is Required

To unblock the medical RAG subsystem, an authorized project administrator must execute the verification lifecycle on the supplied PDFs:

| Accepted Source | Example Document Type |
|---|---|
| Ministry of Health and Family Welfare (MoHFW), Government of India | Standard Treatment Guidelines, NRHM protocols |
| World Health Organization (WHO) | Clinical protocols, Essential Medicines guidelines |
| State Directorate of Health Services (DHS) | State STGs, ASHA guidelines |
| National Health Mission (NHM) | Community health worker protocols |

### Verification Requirements

Every medical document must pass through the following lifecycle **before** it can serve clinical guidance:

```
File supplied by authorized administrator
        ↓
ingest_document() validates:
  - Non-empty content
  - publisher field present
  - SHA-256 content hash computed
        ↓
  status = PENDING_REVIEW
  verification_status = UNVERIFIED
  is_authoritative = False
        ↓
Admin reviews document via:
  POST /api/admin/knowledge/documents/{id}/verify
        ↓
  verification_status = VERIFIED
  is_authoritative = True
        ↓
Admin activates document via:
  POST /api/admin/knowledge/documents/{id}/activate
        ↓
  status = ACTIVE
  (predecessor → DEPRECATED)
        ↓
Document enters RAG pipeline ✅
```

### What Is NEVER Permitted

- ❌ Fabricating medical guidelines
- ❌ Auto-verifying any ingested document
- ❌ Treating filenames like "who_guideline.pdf" as authoritative
- ❌ Treating PDF logos or professional appearance as evidence of authority
- ❌ Allowing PENDING_REVIEW, UNVERIFIED, STALE, or REJECTED documents into the LLM pipeline
- ❌ LLM-generated verification metadata
- ❌ Client-side flag overrides for verification status

---

## 3. Data Readiness — Facility Network

**STATUS: ❌ BLOCKED — AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED**

### What Is in the Repository

No real healthcare facility records are present. The facility database is empty of verified production data.

### What Is Required

A real, government-backed dataset of rural healthcare facilities (PHCs, CHCs, District Hospitals, Sub-Centres) must be provided. Accepted sources:

| Accepted Source | Format |
|---|---|
| NHM Facility Registry / HFR (Health Facility Registry) | JSON / CSV |
| State Health Department GIS datasets | JSON / CSV |
| HMIS (Health Management Information System) extracts | CSV |

### Validation Rules

Every facility record must pass:

```
- name: non-empty string
- source: non-empty (identifies the dataset)
- source_type: non-empty
- source_record_id: unique identifier from source
- latitude: valid float, -90 ≤ lat ≤ 90
- longitude: valid float, -180 ≤ lon ≤ 180
- facility_type: one of PHC / CHC / DISTRICT_HOSPITAL / SUB_CENTRE / etc.
```

### Facility Verification Lifecycle

```
Ingested from authoritative dataset
        ↓
  verification_status = UNVERIFIED
        ↓
Admin verifies:
  POST /api/admin/facilities/{id}/verify
        ↓
  verification_status = VERIFIED
        ↓
Appears in emergency routing and facility search ✅
```

### What Is NEVER Permitted

- ❌ Fabricating facility coordinates
- ❌ Auto-verifying newly ingested facilities
- ❌ DEMO facilities appearing in emergency routing when verified alternatives exist
- ❌ Downgrading a VERIFIED facility to UNVERIFIED via a re-ingestion
- ❌ Client-controlled verification status

---

## 4. Clinical Readiness

**STATUS: ❌ NOT READY — BLOCKED BY DATA**

Medibot passes all software tests. However, **passing software tests does not establish clinical readiness**.

Clinical readiness requires ALL of the following:

| Gate | Status |
|---|---|
| Authoritative medical documents ingested | ❌ Not done |
| Medical documents verified by qualified reviewer | ❌ Not done |
| Medical documents activated in RAG pipeline | ❌ Not done |
| Clinical accuracy review of RAG outputs | ❌ Not done |
| Real facility dataset ingested | ❌ Not done |
| Facility data verified by health authority | ❌ Not done |
| Emergency routing validated against real facility locations | ❌ Not done |
| Regulatory/ethics approval (if applicable) | ❌ Not assessed |
| ASHA/ANM workflow review | ❌ Not done |
| Adverse event response procedure defined | ❌ Not done |

> **Software tests verify engineering correctness only. They cannot verify clinical accuracy, clinical safety, or regulatory compliance.**

---

## 5. Deployment Readiness

**STATUS: ⚠️ CONDITIONAL**

The software infrastructure is production-ready for deployment:

- Docker Compose with non-root users ✅
- PostgreSQL not exposed on host port ✅
- JWT authentication + RBAC ✅
- HTTPS-ready (reverse proxy expected) ✅
- Health check endpoints (`/health`, `/ready`) ✅
- CI/CD workflow defined ✅
- Secrets via environment variables (no hardcoded credentials) ✅

**However, the application cannot be deployed into a real clinical setting until:**

1. Medical Data Readiness gate is cleared (authoritative documents ingested, verified, activated)
2. Facility Data Readiness gate is cleared (real facility dataset ingested and verified)
3. Clinical accuracy review is completed by qualified medical professionals
4. Any applicable regulatory approvals are obtained

---

## 6. Data Classifier

M8.3 introduces `backend/app/knowledge/data_classifier.py`. It classifies every discovered file as:

| Classification | Meaning |
|---|---|
| `VERIFIED` | In DB, `is_authoritative=True`, `verification_status=VERIFIED`, `status=ACTIVE` |
| `UNVERIFIED` | Exists + ingested, but not yet verified through admin workflow |
| `DEMO` | Known test fixture or file too small to be a real clinical document |
| `INVALID` | File exists but cannot be processed (empty, unsupported, corrupted) |
| `NOT_PRESENT` | File or directory does not exist |

**Classification is never based on:**
- Filename patterns (e.g. "who", "gov", "guideline")
- PDF logos or document styling
- File extension alone
- Source URL domain names

---

## 7. Controlled Ingestion Reference

To ingest a real authoritative document after M8.3:

```bash
# Discover what is currently in the data directory
python -m app.knowledge.ingest discover

# Ingest a document with required publisher metadata
python -m app.knowledge.ingest ingest path/to/document.pdf \
  --publisher "Ministry of Health and Family Welfare, Government of India" \
  --source-url "https://mohfw.gov.in/..." \
  --publication-date "2023-01-01"

# Document enters PENDING_REVIEW — admin must then verify and activate via API
# POST /api/admin/knowledge/documents/{id}/verify
# POST /api/admin/knowledge/documents/{id}/activate
```

---

## 8. Known Limitations

1. **No authoritative data:** The RAG system correctly reports BLOCKED. It will not serve clinical guidance until real data is supplied and verified.
2. **Offline RAG:** When offline, the LLM uses local ChromaDB. Only documents that were in the vector store at the time of offline caching are available — and only if they were ACTIVE+VERIFIED at cache time.
3. **Multilingual accuracy:** Clinical guidance is served in multiple languages, but translation accuracy for medical terminology has not been independently verified for all supported languages.
4. **Voice recognition:** Voice input accuracy in rural/noisy environments has not been field-tested.
5. **Emergency routing:** Emergency routing is functional but depends on real facility data being present and verified.
