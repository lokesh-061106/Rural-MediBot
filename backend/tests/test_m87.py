import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.knowledge import KnowledgeDocument
from app.core.security import create_access_token
from app.db.database import Base, engine, get_db
from datetime import datetime

client = TestClient(app)

@pytest.fixture(scope="module")
def m87_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    db.query(KnowledgeDocument).delete()
    db.commit()
    admin = User(full_name="Admin", email="admin87@test.com", role="admin", password_hash="pw", is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    yield db
    db.query(KnowledgeDocument).delete()
    db.query(User).delete()
    db.commit()

def get_headers(db):
    admin = db.query(User).filter_by(email="admin87@test.com").first()
    token = create_access_token(admin.id, role="admin")
    return {"Authorization": f"Bearer {token}"}

def test_m87_rag_blocks_demo(m87_db):
    doc = KnowledgeDocument(
        document_id="demo1", filename="guide.pdf", source_type="pdf", content_hash="h1",
        status="DEMO", verification_status="UNVERIFIED", is_authoritative=False, chunk_count=1,
        source_url="http", publication_date=datetime.utcnow(), version="1.0"
    )
    m87_db.add(doc)
    m87_db.commit()
    res = client.post(f"/api/admin/knowledge/documents/demo1/activate", headers=get_headers(m87_db))
    assert res.status_code == 400

def test_m87_rag_blocks_stale(m87_db):
    doc = KnowledgeDocument(
        document_id="stale1", filename="stale.pdf", source_type="pdf", content_hash="h2",
        status="STALE", verification_status="UNVERIFIED", is_authoritative=False, chunk_count=1,
        source_url="http", publication_date=datetime.utcnow(), version="1.0"
    )
    m87_db.add(doc)
    m87_db.commit()
    res = client.post(f"/api/admin/knowledge/documents/stale1/activate", headers=get_headers(m87_db))
    assert res.status_code == 400
