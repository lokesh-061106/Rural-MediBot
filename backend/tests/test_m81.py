import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.knowledge import KnowledgeDocument
from app.core.security import create_access_token
from app.db.database import Base, engine, get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def m81_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    
    db.query(KnowledgeDocument).delete()
    db.commit()
    
    # Create admin
    admin = User(full_name="Admin", email="admin81@test.com", role="admin", password_hash="pw", is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    yield db
    
    db.query(KnowledgeDocument).delete()
    db.query(User).delete()
    db.commit()

def get_admin_headers(db):
    admin = db.query(User).filter_by(email="admin81@test.com").first()
    token = create_access_token(admin.id, role="admin")
    return {"Authorization": f"Bearer {token}"}

def test_missing_authoritative_dataset(m81_db):
    headers = get_admin_headers(m81_db)
    res = client.get("/api/admin/knowledge/readiness", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["readiness_status"] == "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
    assert data["knowledge_metrics"]["total_documents"] == 0

def test_unverified_document_rejection_and_metadata(m81_db):
    # Add an unverified document
    doc1 = KnowledgeDocument(
        document_id="doc_unverified",
        filename="test.pdf",
        title="Test",
        source="/path/test.pdf",
        source_type="pdf",
        content_hash="hash123",
        version="1.0",
        status="success",
        is_authoritative=False,
        verification_status="UNVERIFIED"
    )
    m81_db.add(doc1)
    m81_db.commit()
    
    headers = get_admin_headers(m81_db)
    res = client.get("/api/admin/knowledge/readiness", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["readiness_status"] == "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
    
    # Valid metadata handling
    assert data["knowledge_metrics"]["total_documents"] == 1
    assert data["knowledge_metrics"]["authoritative_documents"] == 0
    assert data["documents"][0]["content_hash"] == "hash123"

def test_content_hash_integrity_and_provenance(m81_db):
    doc2 = KnowledgeDocument(
        document_id="doc_verified",
        filename="verified.pdf",
        title="Verified Protocol",
        source="/path/verified.pdf",
        source_type="pdf",
        content_hash="hash456",
        version="1.0",
        status="success",
        is_authoritative=True,
        verification_status="VERIFIED"
    )
    m81_db.add(doc2)
    m81_db.commit()
    
    headers = get_admin_headers(m81_db)
    res = client.get("/api/admin/knowledge/readiness", headers=headers)
    assert res.status_code == 200
    data = res.json()
    
    docs = data["documents"]
    verified_doc = next(d for d in docs if d["id"] == "doc_verified")
    
    assert verified_doc["content_hash"] == "hash456"
    assert verified_doc["verification_status"] == "VERIFIED"
    assert verified_doc["is_authoritative"] is True
    
    assert data["readiness_status"] == "AUTHORITATIVE PRODUCTION DATASET: VERIFIED BUT NOT ACTIVATED"

def test_hybrid_search_rejects_unverified_docs():
    from app.retrieval.hybrid_search import get_hybrid_retriever
    from langchain_core.documents import Document
    
    # Create dummy retrieved documents directly testing the retrieval rerank loop
    retriever = get_hybrid_retriever()
    
    class FakeRetriever:
        def invoke(self, query):
            return [
                Document(page_content="Unverified info", metadata={"document_id": "d1", "is_authoritative": False, "verification_status": "UNVERIFIED"}),
                Document(page_content="Verified info", metadata={"document_id": "d2", "is_authoritative": True, "verification_status": "VERIFIED", "status": "ACTIVE"})
            ]
            
    class FakeEncoder:
        def predict(self, pairs):
            return [5.0, 5.0]
            
    retriever.semantic_retriever = FakeRetriever()
    retriever.bm25_retriever = FakeRetriever()
    
    import app.retrieval.hybrid_search as hs
    hs._cross_encoder = FakeEncoder()
    
    results = retriever.retrieve_and_rerank("Test")
    assert len(results) == 1
    assert results[0].metadata["document_id"] == "d2"
    assert results[0].metadata["is_authoritative"] is True

