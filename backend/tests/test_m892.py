import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.knowledge import KnowledgeDocument
from app.core.security import create_access_token
import uuid

client = TestClient(app)

from app.db.database import Base, engine, get_db

@pytest.fixture
def m892_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
    Base.metadata.drop_all(bind=engine)

def get_admin_headers(db):
    u = db.query(User).filter_by(role="admin").first()
    if not u:
        u = User(full_name="Admin M892", email="admin892@test.com", role="admin", password_hash="dummy")
        db.add(u)
        db.commit()
    token = create_access_token(subject=u.id, role="admin")
    return {"Authorization": f"Bearer {token}"}

def test_m892_get_documents_endpoint(m892_db):
    headers = get_admin_headers(m892_db)
    
    doc = KnowledgeDocument(
        document_id="doc_m892",
        filename="R1.pdf",
        title="Test R1",
        content_hash="hash123",
        status="PENDING_REVIEW",
        verification_status="UNVERIFIED",
        is_authoritative=False,
        chunk_count=1,
        source_type="pdf",
        source="backend/data/documents/R1.pdf"
    )
    m892_db.add(doc)
    m892_db.commit()
    
    res = client.get("/api/admin/knowledge/documents", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(d["id"] == "doc_m892" for d in data)
    
    res_read = client.get("/api/admin/knowledge/readiness", headers=headers)
    assert res_read.status_code == 200
    readiness = res_read.json()
    assert "readiness_status" in readiness
