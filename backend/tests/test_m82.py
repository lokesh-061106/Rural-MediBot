
import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.knowledge import KnowledgeDocument
from app.models.facility import HealthcareFacility
from app.core.security import create_access_token
from app.db.database import Base, engine, get_db
from app.knowledge.ingest import ingest_document

client = TestClient(app)

@pytest.fixture(scope="module")
def m82_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    
    # Create admin
    admin = User(full_name="Admin", email="admin82@test.com", role="admin", password_hash="pw", is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    # Create Patient
    patient = User(full_name="Patient", email="patient82@test.com", role="patient", password_hash="pw", is_active=True)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    yield db
    
    db.query(KnowledgeDocument).delete()
    db.query(HealthcareFacility).delete()
    db.query(User).delete()
    db.commit()

def get_headers(db, email, role):
    user = db.query(User).filter_by(email=email).first()
    token = create_access_token(user.id, role=role)
    return {"Authorization": f"Bearer {token}"}

def test_document_defaults(m82_db, tmp_path):
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Hello World M82")
    
    res = ingest_document(str(test_file), m82_db, {"publisher": "WHO"})
    assert res["status"] == "PENDING_REVIEW"
    
    doc = m82_db.query(KnowledgeDocument).filter_by(filename="test_doc.txt").first()
    assert doc.status == "PENDING_REVIEW"
    assert doc.verification_status == "UNVERIFIED"
    assert doc.is_authoritative is False

def test_invalid_document_rejected(m82_db, tmp_path):
    # Missing publisher fails validation in M8.2
    test_file = tmp_path / "test_invalid.txt"
    test_file.write_text("Invalid because no publisher")
    
    res = ingest_document(str(test_file), m82_db, {})
    assert res["status"] == "VALIDATION_FAILED"
    
def test_empty_document_rejected(m82_db, tmp_path):
    test_file = tmp_path / "empty.txt"
    test_file.write_text("   ")
    
    res = ingest_document(str(test_file), m82_db, {"publisher": "WHO"})
    assert res["status"] == "VALIDATION_FAILED"
    assert "empty" in res["reason"].lower()

def test_hash_idempotency(m82_db, tmp_path):
    test_file = tmp_path / "test_dup.txt"
    test_file.write_text("Duplicate Content")
    
    res1 = ingest_document(str(test_file), m82_db, {"publisher": "WHO"})
    assert res1["status"] == "PENDING_REVIEW"
    
    res2 = ingest_document(str(test_file), m82_db, {"publisher": "WHO"})
    assert res2["status"] == "skipped"

def test_version_control(m82_db, tmp_path):
    # Setup v1
    f1 = tmp_path / "guide.txt"
    f1.write_text("V1 Content")
    ingest_document(str(f1), m82_db, {"publisher": "MOHFW", "version": "1.0"})
    
    doc1 = m82_db.query(KnowledgeDocument).filter_by(filename="guide.txt", version="1.0").first()
    doc1.verification_status = "VERIFIED"
    doc1.status = "ACTIVE"
    m82_db.commit()
    
    # Ingest v2 (same filename, new content)
    f2 = tmp_path / "guide.txt" # same name
    f2.write_text("V2 Content Updates")
    ingest_document(str(f2), m82_db, {"publisher": "MOHFW", "version": "2.0"})
    
    # Assert v1 is STILL ACTIVE
    m82_db.refresh(doc1)
    assert doc1.status == "ACTIVE"
    
    doc2 = m82_db.query(KnowledgeDocument).filter_by(filename="guide.txt", version="2.0").first()
    assert doc2.status == "PENDING_REVIEW"
    
    # Admin verifies and activates v2
    headers = get_headers(m82_db, "admin82@test.com", "admin")
    client.post(f"/api/admin/knowledge/documents/{doc2.document_id}/verify", headers=headers)
    client.post(f"/api/admin/knowledge/documents/{doc2.document_id}/activate", headers=headers)
    
    # Assert v1 is DEPRECATED and v2 is ACTIVE
    m82_db.refresh(doc1)
    m82_db.refresh(doc2)
    assert doc1.status == "DEPRECATED"
    assert doc2.status == "ACTIVE"

def test_rbac_patient_rejected(m82_db):
    doc = m82_db.query(KnowledgeDocument).first()
    headers = get_headers(m82_db, "patient82@test.com", "patient")
    
    res1 = client.post(f"/api/admin/knowledge/documents/{doc.document_id}/verify", headers=headers)
    assert res1.status_code == 403
    
    res2 = client.post(f"/api/admin/knowledge/documents/{doc.document_id}/activate", headers=headers)
    assert res2.status_code == 403

def test_facility_ingestion_idempotency_and_downgrade(m82_db):
    from app.knowledge.facility_ingest import ingest_json
    # Create VERIFIED facility
    data = [{
        "name": "PHC verified",
        "source": "gov",
        "source_type": "api",
        "source_record_id": "123",
        "latitude": 10.0,
        "longitude": 20.0,
        "verification_status": "VERIFIED"
    }]
    stats1 = ingest_json(m82_db, data)
    assert stats1.inserted == 1
    
    # Attempt downgrade with UNVERIFIED
    data[0]["verification_status"] = "UNVERIFIED"
    stats2 = ingest_json(m82_db, data)
    assert stats2.updated == 1
    assert stats2.skipped_verified_downgrade == 1
    
    fac = m82_db.query(HealthcareFacility).filter_by(source_record_id="123").first()
    assert fac.verification_status == "VERIFIED"

def test_readiness_blocked(m82_db):
    # Since we have active/verified docs, let's clean them to test BLOCKED
    m82_db.query(KnowledgeDocument).delete()
    m82_db.query(HealthcareFacility).delete()
    m82_db.commit()
    
    headers = get_headers(m82_db, "admin82@test.com", "admin")
    res = client.get("/api/admin/knowledge/readiness", headers=headers)
    data = res.json()
    assert data["readiness_status"] == "AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED"
    assert data["subsystems"]["medical_rag"] == "BLOCKED"
    assert data["subsystems"]["facility_network"] == "BLOCKED"

