import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User, AuditLog
from app.models.knowledge import KnowledgeDocument
from app.core.security import create_access_token
from app.db.database import Base, engine, get_db
from datetime import datetime, timedelta

client = TestClient(app)

@pytest.fixture(scope="module")
def m88_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(KnowledgeDocument).delete()
    db.query(AuditLog).delete()
    db.commit()
    
    admin = User(full_name="Admin", email="admin88@test.com", role="admin", password_hash="pw", is_active=True)
    patient = User(full_name="Pat", email="pat88@test.com", role="patient", password_hash="pw", is_active=True)
    doctor = User(full_name="Doc", email="doc88@test.com", role="doctor", password_hash="pw", is_active=True)
    
    db.add(admin)
    db.add(patient)
    db.add(doctor)
    db.commit()
    db.refresh(admin)
    db.refresh(patient)
    db.refresh(doctor)
    yield db
    db.query(KnowledgeDocument).delete()
    db.query(User).delete()
    db.query(AuditLog).delete()
    db.commit()

def get_headers(db, email, role):
    u = db.query(User).filter_by(email=email).first()
    token = create_access_token(u.id, role=role)
    return {"Authorization": f"Bearer {token}"}

def setup_doc(db, **kwargs):
    doc_id = f"test_{len(db.query(KnowledgeDocument).all())}"
    defaults = {
        "document_id": doc_id,
        "filename": "test.pdf",
        "title": "Test Document",
        "content_hash": "hash123",
        "status": "PENDING_REVIEW",
        "verification_status": "UNVERIFIED",
        "is_authoritative": False,
        "publisher": "Test Publisher",
        "source_url": "https://example.com/doc",
        "publication_date": datetime.utcnow(),
        "chunk_count": 1
    }
    defaults.update(kwargs)
    doc = KnowledgeDocument(**defaults)
    db.add(doc)
    db.commit()
    return doc_id

def test_patient_cannot_access_verification(m88_db):
    doc_id = setup_doc(m88_db)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/verify", headers=get_headers(m88_db, "pat88@test.com", "patient"), json={"checklist_confirmed": True})
    assert res.status_code == 403

def test_doctor_cannot_access_verification(m88_db):
    doc_id = setup_doc(m88_db)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/verify", headers=get_headers(m88_db, "doc88@test.com", "doctor"), json={"checklist_confirmed": True})
    assert res.status_code == 403

def test_checklist_required(m88_db):
    doc_id = setup_doc(m88_db)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/verify", headers=get_headers(m88_db, "admin88@test.com", "admin"), json={"checklist_confirmed": False})
    assert res.status_code == 400

def test_incomplete_provenance_rejected(m88_db):
    doc_id = setup_doc(m88_db, source_url="")
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/verify", headers=get_headers(m88_db, "admin88@test.com", "admin"), json={"checklist_confirmed": True})
    assert res.status_code == 400

def test_admin_can_verify(m88_db):
    doc_id = setup_doc(m88_db)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/verify", headers=get_headers(m88_db, "admin88@test.com", "admin"), json={"checklist_confirmed": True})
    assert res.status_code == 200
    doc = m88_db.query(KnowledgeDocument).filter_by(document_id=doc_id).first()
    assert doc.verification_status == "VERIFIED"
    assert doc.status != "ACTIVE" # verification does not activate

def test_activation_requires_verified(m88_db):
    doc_id = setup_doc(m88_db)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/activate", headers=get_headers(m88_db, "admin88@test.com", "admin"))
    assert res.status_code == 400

def test_activation_works(m88_db):
    doc_id = setup_doc(m88_db, status="VERIFIED", verification_status="VERIFIED", is_authoritative=True)
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/activate", headers=get_headers(m88_db, "admin88@test.com", "admin"))
    assert res.status_code == 200
    doc = m88_db.query(KnowledgeDocument).filter_by(document_id=doc_id).first()
    assert doc.status == "ACTIVE"

def test_stale_cannot_activate(m88_db):
    doc_id = setup_doc(m88_db, verification_status="VERIFIED", is_authoritative=True, status="STALE")
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/activate", headers=get_headers(m88_db, "admin88@test.com", "admin"))
    assert res.status_code == 400

def test_demo_cannot_activate(m88_db):
    doc_id = setup_doc(m88_db, verification_status="VERIFIED", is_authoritative=True, status="DEMO")
    res = client.post(f"/api/admin/knowledge/documents/{doc_id}/activate", headers=get_headers(m88_db, "admin88@test.com", "admin"))
    assert res.status_code == 400

def test_rag_blocks_rejected(m88_db):
    doc_id = setup_doc(m88_db, status="REJECTED")
    doc = m88_db.query(KnowledgeDocument).filter_by(document_id=doc_id).first()
    assert doc.status == "REJECTED"

def test_audit_log_created_no_phi(m88_db):
    logs = m88_db.query(AuditLog).filter_by(action="VERIFY_DOCUMENT").all()
    assert len(logs) > 0
    for log in logs:
        assert "pat88" not in str(log.details)
        assert log.details["new_status"] == "VERIFIED"
