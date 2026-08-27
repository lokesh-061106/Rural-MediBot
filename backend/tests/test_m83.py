from datetime import datetime
"""
M8.3 — Authoritative Data Acquisition & Controlled Ingestion
Test Suite: 17 deterministic tests

Fixtures simulate metadata/state transitions.
No fixture claims to be a real government clinical guideline.
No test fabricates or automatically verifies medical content.

Auth pattern: uses create_access_token() directly (same pattern as test_m81.py)
to avoid dependency-override JWT validation issues.
"""

import os
import sys
import hashlib
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine, get_db
from app.models.user import User
from app.models.knowledge import KnowledgeDocument
from app.models.facility import HealthcareFacility
from app.core.security import create_access_token
from sqlalchemy.orm import sessionmaker

TestingSessionLocal = sessionmaker(bind=engine)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Module-level fixture — create admin + patient users once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def m83_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())

    # Admin user
    if not db.query(User).filter_by(email="admin83@test.com").first():
        admin = User(
            full_name="M83 Admin",
            email="admin83@test.com",
            role="admin",
            password_hash="irrelevant",
            is_active=True,
        )
        db.add(admin)

    # Patient user
    if not db.query(User).filter_by(email="patient83@test.com").first():
        patient = User(
            full_name="M83 Patient",
            email="patient83@test.com",
            role="patient",
            password_hash="irrelevant",
            is_active=True,
        )
        db.add(patient)

    # Doctor user
    if not db.query(User).filter_by(email="doctor83@test.com").first():
        doctor = User(
            full_name="M83 Doctor",
            email="doctor83@test.com",
            role="doctor",
            password_hash="irrelevant",
            is_active=True,
        )
        db.add(doctor)

    db.commit()
    yield db

    # Teardown — remove only M8.3 test data
    db.query(KnowledgeDocument).filter(
        KnowledgeDocument.document_id.like("m83_%")
    ).delete(synchronize_session=False)
    db.query(HealthcareFacility).filter(
        HealthcareFacility.source.in_(["m83_test", "m83_test_unverified"])
    ).delete(synchronize_session=False)
    db.commit()


def _admin_headers(db) -> dict:
    admin = db.query(User).filter_by(email="admin83@test.com").first()
    token = create_access_token(admin.id, role="admin")
    return {"Authorization": f"Bearer {token}"}


def _patient_headers(db) -> dict:
    patient = db.query(User).filter_by(email="patient83@test.com").first()
    token = create_access_token(patient.id, role="patient")
    return {"Authorization": f"Bearer {token}"}


def _doctor_headers(db) -> dict:
    doctor = db.query(User).filter_by(email="doctor83@test.com").first()
    token = create_access_token(doctor.id, role="doctor")
    return {"Authorization": f"Bearer {token}"}


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _insert_doc(db, *, doc_id_suffix, content, publisher=None,
                verification_status="UNVERIFIED", is_authoritative=False,
                status="PENDING_REVIEW", filename="m83_test_doc.txt"):
    """Helper: directly insert a KnowledgeDocument test fixture into DB."""
    h = _hash(content)
    doc_id = f"m83_{doc_id_suffix}"
    existing = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.document_id == doc_id
    ).first()
    if existing:
        return existing
    doc = KnowledgeDocument(
        document_id=doc_id,
        filename=filename,
        title="M8.3 Synthetic Test Fixture (NOT a real clinical guideline)",
        source=f"/synthetic/{filename}",
        source_type="txt",
        content_hash=h,
        status=status,
        chunk_count=1,
        version="1.0",
        is_authoritative=is_authoritative,
        verification_status=verification_status,
        publisher=publisher,
        source_url="https://example.com/fixture",
        publication_date=datetime.utcnow()
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ===========================================================================
# TEST 1: Missing authoritative dataset → readiness reports 0 active verified
# ===========================================================================
def test_m83_t01_missing_authoritative_remains_blocked(m83_db):
    """
    When no ACTIVE+VERIFIED+is_authoritative document exists,
    the readiness API must report active_verified_documents == 0.
    """
    # Remove any authoritative docs that might exist from previous tests
    m83_db.query(KnowledgeDocument).filter(
        KnowledgeDocument.is_authoritative == True,
        KnowledgeDocument.verification_status == "VERIFIED",
        KnowledgeDocument.status == "ACTIVE",
    ).delete(synchronize_session=False)
    m83_db.commit()

    resp = client.get("/api/admin/knowledge/readiness", headers=_admin_headers(m83_db))
    assert resp.status_code == 200, f"readiness endpoint returned {resp.status_code}: {resp.text}"
    data = resp.json()
    km = data.get("knowledge_metrics") or data.get("metrics", {})
    active_verified = km.get("active_verified_documents", 0)
    assert active_verified == 0, f"Expected 0 active verified docs, got {active_verified}"


# ===========================================================================
# TEST 2: Supplied document enters PENDING_REVIEW (not auto-VERIFIED)
# ===========================================================================
def test_m83_t02_supplied_doc_enters_pending_review():
    """
    A freshly supplied document with a publisher must enter PENDING_REVIEW,
    never VERIFIED automatically.
    """
    import uuid
    from app.knowledge.ingest import ingest_document
    from app.db.database import SessionLocal

    # UUID suffix guarantees unique content hash per run (avoids cross-run collisions)
    unique_suffix = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    ) as f:
        # Synthetic content — explicitly not a real clinical guideline
        f.write(
            f"Synthetic test content for M8.3 ingestion pipeline test [{unique_suffix}]. " * 20
        )
        tmp_path = f.name

    db = SessionLocal()
    try:
        result = ingest_document(
            tmp_path, db,
            doc_metadata={"publisher": "Test Health Authority (Synthetic — NOT real)"}
        )
        assert result["status"] == "PENDING_REVIEW", f"Expected PENDING_REVIEW, got {result}"

        content = open(tmp_path, encoding="utf-8").read()
        h = _hash(content)
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == h).first()
        assert doc is not None
        assert doc.verification_status == "UNVERIFIED"
        assert doc.is_authoritative is False
        assert doc.status == "PENDING_REVIEW"
    finally:
        db.close()
        os.unlink(tmp_path)


# ===========================================================================
# TEST 3: Invalid document (missing publisher) → VALIDATION_FAILED
# ===========================================================================
def test_m83_t03_invalid_doc_rejected_without_publisher():
    """
    A document without a publisher must be rejected as VALIDATION_FAILED.
    """
    import uuid
    from app.knowledge.ingest import ingest_document
    from app.db.database import SessionLocal

    unique_suffix = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(f"Synthetic no-publisher content for M8.3 T03 [{unique_suffix}]. " * 10)
        tmp_path = f.name

    db = SessionLocal()
    try:
        result = ingest_document(tmp_path, db, doc_metadata={})
        assert result["status"] == "VALIDATION_FAILED"
        assert "publisher" in result["reason"].lower()
    finally:
        db.close()
        os.unlink(tmp_path)


# ===========================================================================
# TEST 4: Duplicate content hash → idempotent (skipped)
# ===========================================================================
def test_m83_t04_duplicate_hash_is_idempotent():
    """
    Re-ingesting the same file (same SHA-256) must be safely skipped.
    """
    import uuid
    from app.knowledge.ingest import ingest_document
    from app.db.database import SessionLocal

    unique_suffix = str(uuid.uuid4())
    content = f"Deterministic idempotency test content for M8.3 Phase 4 [{unique_suffix}]. " * 15
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    db = SessionLocal()
    try:
        r1 = ingest_document(tmp_path, db, doc_metadata={"publisher": "Test Org (Synthetic)"})
        assert r1["status"] == "PENDING_REVIEW", f"First ingest should be PENDING_REVIEW, got {r1}"

        r2 = ingest_document(tmp_path, db, doc_metadata={"publisher": "Test Org (Synthetic)"})
        assert r2["status"] == "skipped"
        assert "duplicate" in r2["reason"].lower()
    finally:
        db.close()
        os.unlink(tmp_path)


# ===========================================================================
# TEST 5: Versioning — new version of same filename doesn't remove active predecessor
# ===========================================================================
def test_m83_t05_versioning_preserves_active_predecessor(m83_db):
    """
    When a new version of a document is ingested, the previously ACTIVE version
    must not be automatically deprecated or removed.
    """
    import uuid
    from app.knowledge.ingest import ingest_document
    from app.db.database import SessionLocal

    unique_suffix = str(uuid.uuid4())

    # Create an "active" predecessor directly in DB (each run uses unique content hash)
    v1_content = f"Version 1 content for M8.3 versioning test [{unique_suffix}]. " * 15
    doc_v1 = _insert_doc(
        m83_db,
        doc_id_suffix=f"version_v1_{unique_suffix[:8]}",
        content=v1_content,
        publisher="Test Publisher (Synthetic)",
        status="ACTIVE",
        verification_status="VERIFIED",
        is_authoritative=True,
        filename="m83_version_test.txt",
    )

    # Ingest v2 (different content, same filename)
    content_v2 = f"Version 2 content for M8.3 versioning test — updated [{unique_suffix}]. " * 15
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(content_v2)
        tmp_path = f.name

    db = SessionLocal()
    try:
        r2 = ingest_document(tmp_path, db, doc_metadata={"publisher": "Test Publisher (Synthetic)"})
        assert r2["status"] == "PENDING_REVIEW", f"V2 should be PENDING_REVIEW, got {r2}"

        # Predecessor must still be ACTIVE
        m83_db.refresh(doc_v1)
        assert doc_v1.status == "ACTIVE", (
            f"Predecessor should remain ACTIVE after new version ingested, got {doc_v1.status}"
        )
    finally:
        db.close()
        os.unlink(tmp_path)



# ===========================================================================
# TEST 6: Unverified document cannot reach RAG
# ===========================================================================
def test_m83_t06_unverified_document_blocked_from_rag():
    """
    A PENDING_REVIEW document must be excluded from hybrid search results.
    """
    from app.retrieval.hybrid_search import get_hybrid_retriever
    from langchain_core.documents import Document
    import app.retrieval.hybrid_search as hs

    retriever = get_hybrid_retriever()

    class PendingRetriever:
        def invoke(self, query):
            return [Document(
                page_content="Unverified pending clinical content",
                metadata={
                    "document_id": "m83_pending_rag_test",
                    "is_authoritative": False,
                    "verification_status": "UNVERIFIED",
                    "status": "PENDING_REVIEW",
                }
            )]

    class FakeEncoder:
        def predict(self, pairs): return [5.0] * len(pairs)

    retriever.semantic_retriever = PendingRetriever()
    retriever.bm25_retriever = PendingRetriever()
    hs._cross_encoder = FakeEncoder()

    results = retriever.retrieve_and_rerank("clinical test")
    assert len(results) == 0, "PENDING_REVIEW doc must not reach RAG"


# ===========================================================================
# TEST 7: Verified authoritative ACTIVE document CAN reach RAG
# ===========================================================================
def test_m83_t07_verified_active_doc_reaches_rag():
    """
    A document with is_authoritative=True, VERIFIED, ACTIVE metadata
    (not in DB — metadata fallback path) must pass through hybrid search.
    """
    from app.retrieval.hybrid_search import get_hybrid_retriever
    from langchain_core.documents import Document
    import app.retrieval.hybrid_search as hs

    retriever = get_hybrid_retriever()

    class VerifiedRetriever:
        def invoke(self, query):
            return [Document(
                page_content="Verified authoritative clinical content for RAG",
                metadata={
                    "document_id": "m83_verified_rag_test",
                    "is_authoritative": True,
                    "verification_status": "VERIFIED",
                    "status": "ACTIVE",
                }
            )]

    class FakeEncoder:
        def predict(self, pairs): return [5.0] * len(pairs)

    retriever.semantic_retriever = VerifiedRetriever()
    retriever.bm25_retriever = VerifiedRetriever()
    hs._cross_encoder = FakeEncoder()

    results = retriever.retrieve_and_rerank("clinical test")
    assert len(results) == 1, "ACTIVE+VERIFIED+authoritative doc must reach RAG"


# ===========================================================================
# TEST 8: STALE document cannot reach current RAG
# ===========================================================================
def test_m83_t08_stale_document_blocked_from_rag():
    """
    A document marked STALE must be excluded from the RAG pipeline.
    """
    from app.retrieval.hybrid_search import get_hybrid_retriever
    from langchain_core.documents import Document
    import app.retrieval.hybrid_search as hs

    retriever = get_hybrid_retriever()

    class StaleRetriever:
        def invoke(self, query):
            return [Document(
                page_content="Stale clinical guideline content",
                metadata={
                    "document_id": "m83_stale_rag_test",
                    "is_authoritative": True,
                    "verification_status": "VERIFIED",
                    "status": "STALE",
                }
            )]

    class FakeEncoder:
        def predict(self, pairs): return [5.0] * len(pairs)

    retriever.semantic_retriever = StaleRetriever()
    retriever.bm25_retriever = StaleRetriever()
    hs._cross_encoder = FakeEncoder()

    results = retriever.retrieve_and_rerank("clinical test")
    assert len(results) == 0, "STALE doc must not reach RAG"


# ===========================================================================
# TEST 9: DEMO document cannot reach RAG
# ===========================================================================
def test_m83_t09_demo_document_blocked_from_rag():
    """
    A document that is not authoritative must be blocked from RAG
    regardless of its status field.
    """
    from app.retrieval.hybrid_search import get_hybrid_retriever
    from langchain_core.documents import Document
    import app.retrieval.hybrid_search as hs

    retriever = get_hybrid_retriever()

    class DemoRetriever:
        def invoke(self, query):
            return [Document(
                page_content="Demo test health content — not authoritative",
                metadata={
                    "document_id": "m83_demo_rag_test",
                    "is_authoritative": False,
                    "verification_status": "UNVERIFIED",
                    "status": "ACTIVE",
                }
            )]

    class FakeEncoder:
        def predict(self, pairs): return [5.0] * len(pairs)

    retriever.semantic_retriever = DemoRetriever()
    retriever.bm25_retriever = DemoRetriever()
    hs._cross_encoder = FakeEncoder()

    results = retriever.retrieve_and_rerank("clinical test")
    assert len(results) == 0, "DEMO (not authoritative) doc must not reach RAG"


# ===========================================================================
# TEST 10: Patient cannot verify documents
# ===========================================================================
def test_m83_t10_patient_cannot_verify_documents(m83_db):
    """
    A patient-role user must receive 403 when attempting to verify a document.
    """
    doc = _insert_doc(
        m83_db,
        doc_id_suffix="patient_verify",
        content="Patient verify test content for M8.3. " * 15,
        publisher="Test Org (Synthetic)",
        filename="m83_patient_verify.txt",
    )
    resp = client.post(
        f"/api/admin/knowledge/documents/{doc.document_id}/verify",
        headers=_patient_headers(m83_db),
    )
    assert resp.status_code in (403, 401), (
        f"Patient should not be able to verify docs. Got {resp.status_code}: {resp.text}"
    )


# ===========================================================================
# TEST 11: Non-admin (doctor role) cannot verify documents
# ===========================================================================
def test_m83_t11_non_admin_cannot_verify_documents(m83_db):
    """
    A doctor-role user must receive 403 when attempting to verify a document.
    """
    doc = _insert_doc(
        m83_db,
        doc_id_suffix="doctor_verify",
        content="Doctor verify test content for M8.3 non-admin. " * 15,
        publisher="Test Org (Synthetic)",
        filename="m83_doctor_verify.txt",
    )
    resp = client.post(
        f"/api/admin/knowledge/documents/{doc.document_id}/verify",
        headers=_doctor_headers(m83_db),
    )
    assert resp.status_code in (403, 401), (
        f"Doctor should not be able to verify docs. Got {resp.status_code}: {resp.text}"
    )


# ===========================================================================
# TEST 12: Admin verification workflow works correctly
# ===========================================================================
def test_m83_t12_admin_verification_lifecycle(m83_db):
    """
    An admin can verify a PENDING_REVIEW document.
    Verification must set verification_status=VERIFIED and is_authoritative=True.
    """
    doc = _insert_doc(
        m83_db,
        doc_id_suffix="admin_lifecycle",
        content="Admin lifecycle test content for M8.3 verification. " * 15,
        publisher="Test Health Authority (Synthetic)",
        status="PENDING_REVIEW",
        verification_status="UNVERIFIED",
        is_authoritative=False,
        filename="m83_admin_lifecycle.txt",
    )
    doc_id = doc.document_id

    resp = client.post(
        f"/api/admin/knowledge/documents/{doc_id}/verify",
        headers=_admin_headers(m83_db), json={"checklist_confirmed": True}
    )
    assert resp.status_code == 200, f"Admin verify failed: {resp.text}"

    m83_db.refresh(doc)
    assert doc.verification_status == "VERIFIED"
    assert doc.is_authoritative is True


# ===========================================================================
# TEST 13: Evidence metadata originates from backend records (not LLM)
# ===========================================================================
def test_m83_t13_evidence_metadata_from_backend(monkeypatch):
    """
    The retrieval_node must populate evidence dicts from document metadata
    stored in backend records, not from LLM output.
    """
    monkeypatch.setenv("EVIDENCE_THRESHOLD", "0.5")
    monkeypatch.setenv("USE_MOCK_LLM", "true")

    from app.retrieval import hybrid_search as hs_module
    from langchain_core.documents import Document
    from app.agents.nodes import retrieval_node
    import app.agents.nodes as nodes_module

    # Reset only the retrieval singleton so our mocks take fresh effect.
    # Do NOT reset nodes_module._retriever independently — they must share the same object.
    hs_module.hybrid_retriever = None
    nodes_module._retriever = None  # will be lazily re-set to hs_module.hybrid_retriever

    retriever = hs_module.get_hybrid_retriever()
    # Sync nodes_module so get_retriever() returns the same patched object
    nodes_module._retriever = retriever

    class BackendRetriever:
        def invoke(self, query):
            return [Document(
                page_content="Evidence metadata traceability test content for M8.3",
                metadata={
                    "document_id": "m83_backend_meta",
                    "title": "M8.3 Traceability Test",
                    "chunk_index": 0,
                    "is_authoritative": True,
                    "verification_status": "VERIFIED",
                    "status": "ACTIVE",
                }
            )]

    class FakeEncoder:
        def predict(self, pairs): return [5.0] * len(pairs)

    retriever.semantic_retriever = BackendRetriever()
    retriever.bm25_retriever = BackendRetriever()
    hs_module._cross_encoder = FakeEncoder()

    state = {
        "query": "traceability",
        "query_type": "medical",
        "triage": {"should_bypass_rag": False},
    }
    state = retrieval_node(state)

    evidence = state.get("evidence", [])
    assert len(evidence) >= 1, f"retrieval_node must produce evidence items, got {len(evidence)}"
    ev = evidence[0]

    # Evidence fields must come from document metadata, not LLM
    assert ev.get("document_id") == "m83_backend_meta"
    assert ev.get("title") == "M8.3 Traceability Test"
    assert ev.get("chunk_index") == 0
    assert "relevance_score" in ev
    assert "traceability" in ev.get("excerpt", "").lower()

    # Restore singletons so subsequent tests get clean retrievers
    hs_module.hybrid_retriever = None
    nodes_module._retriever = None


# ===========================================================================
# TEST 14: Facility dataset rejects invalid coordinates
# ===========================================================================
def test_m83_t14_facility_rejects_invalid_coordinates():
    """
    The facility ingestion pipeline must reject records with malformed
    or out-of-range coordinates without crashing.
    """
    from app.knowledge.facility_ingest import process_facility_record, IngestStats
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        invalid_records = [
            {"name": "Bad Facility A", "source": "m83_test", "source_type": "m83",
             "source_record_id": "m83_bad_001", "latitude": 999.0, "longitude": 180.1,
             "facility_type": "PHC"},
            {"name": "Bad Facility B", "source": "m83_test", "source_type": "m83",
             "source_record_id": "m83_bad_002", "latitude": "not_a_number", "longitude": 80.0,
             "facility_type": "CHC"},
            {"name": "Bad Facility C", "source": "m83_test", "source_type": "m83",
             "source_record_id": "m83_bad_003", "latitude": None, "longitude": None,
             "facility_type": "PHC"},
        ]
        for record in invalid_records:
            stats = IngestStats()
            process_facility_record(db, record, stats)
            assert stats.invalid_coordinates >= 1 or stats.rejected >= 1, (
                f"Expected rejection for record {record['source_record_id']}"
            )
    finally:
        db.close()


# ===========================================================================
# TEST 15: Facility duplicates are idempotent
# ===========================================================================
def test_m83_t15_facility_duplicates_are_idempotent():
    """
    Re-ingesting the same facility record must produce only one DB row.
    """
    from app.knowledge.facility_ingest import process_facility_record, IngestStats
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        record = {
            "name": "M8.3 Idempotency Test PHC",
            "source": "m83_test",
            "source_type": "test_fixture",
            "source_record_id": "m83_idempotent_001",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "facility_type": "PHC",
            "verification_status": "UNVERIFIED",
        }
        stats1 = IngestStats()
        process_facility_record(db, record, stats1)
        db.commit()  # process_facility_record does not auto-commit

        stats2 = IngestStats()
        process_facility_record(db, record, stats2)
        db.commit()

        count = db.query(HealthcareFacility).filter(
            HealthcareFacility.source == "m83_test",
            HealthcareFacility.source_record_id == "m83_idempotent_001",
        ).count()
        assert count == 1, f"Expected 1 facility record after idempotent upsert, found {count}"
    finally:
        db.close()


# ===========================================================================
# TEST 16: Unverified facilities cannot be treated as VERIFIED
# ===========================================================================
def test_m83_t16_unverified_facility_cannot_be_verified_automatically():
    """
    A newly ingested facility must start as UNVERIFIED and must not be
    automatically promoted to VERIFIED by the ingestion pipeline.
    """
    from app.knowledge.facility_ingest import process_facility_record, IngestStats
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        record = {
            "name": "M8.3 Unverified Test CHC",
            "source": "m83_test_unverified",
            "source_type": "test_fixture",
            "source_record_id": "m83_unverified_001",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "facility_type": "CHC",
        }
        stats = IngestStats()
        process_facility_record(db, record, stats)
        db.commit()  # process_facility_record does not auto-commit

        facility = db.query(HealthcareFacility).filter(
            HealthcareFacility.source_record_id == "m83_unverified_001"
        ).first()
        assert facility is not None
        assert facility.verification_status != "VERIFIED", (
            "Newly ingested facility must not be auto-VERIFIED"
        )
    finally:
        db.close()



# ===========================================================================
# TEST 17: Readiness correctly reports 0 active verified docs when data absent
# ===========================================================================
def test_m83_t17_readiness_blocked_without_authoritative_data(m83_db):
    """
    The /readiness endpoint must accurately report active_verified_documents == 0
    when no authoritative verified active documents are present.
    """
    # Remove all authoritative docs
    m83_db.query(KnowledgeDocument).filter(
        KnowledgeDocument.is_authoritative == True,
        KnowledgeDocument.verification_status == "VERIFIED",
        KnowledgeDocument.status == "ACTIVE",
    ).delete(synchronize_session=False)
    m83_db.commit()

    resp = client.get("/api/admin/knowledge/readiness", headers=_admin_headers(m83_db))
    assert resp.status_code == 200, f"readiness returned {resp.status_code}: {resp.text}"
    data = resp.json()

    km = data.get("knowledge_metrics") or data.get("metrics", {})
    active_verified = km.get("active_verified_documents", 0)
    assert active_verified == 0, (
        f"active_verified_documents should be 0 when no real data present, got {active_verified}"
    )

    # Verify data_classifier classifies test_health.txt as DEMO
    from app.knowledge.data_classifier import classify_file
    demo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "documents", "test_health.txt",
    )
    if os.path.exists(demo_path):
        result = classify_file(demo_path)
        assert result.classification == "DEMO", (
            f"test_health.txt must be classified DEMO, got {result.classification}: {result.reason}"
        )
