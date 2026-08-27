from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.db.database import Base

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True, unique=True, nullable=False) # Deterministic ID
    filename = Column(String, nullable=False)
    title = Column(String, index=True)
    source = Column(String)
    source_type = Column(String) # e.g. pdf, txt, md
    content_hash = Column(String, index=True, nullable=False)
    version = Column(String, nullable=True)
    status = Column(String, default="processing") # e.g. success, failed, skipped
    chunk_count = Column(Integer, default=0)
    ingestion_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # M8.1 Authoritative Verification
    is_authoritative = Column(Boolean, default=False, nullable=False)
    verification_status = Column(String, default="UNVERIFIED", nullable=False)
    
    # M8.2 Provenance & Version Lifecycle
    publisher = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Extra fields for flexibility
    organization = Column(String, nullable=True)
    disease_topic = Column(String, index=True, nullable=True)
    metadata_json = Column(JSON, nullable=True)
