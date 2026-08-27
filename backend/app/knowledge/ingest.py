import os
import hashlib
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.knowledge import KnowledgeDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.vector_db.chroma_store import get_vector_db_manager
from langchain_core.documents import Document

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

def get_content_hash(content: str) -> str:
    """Calculate deterministic SHA-256 hash of the content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_text_from_pdf(file_path: str) -> str:
    """Safely extract text from a PDF file."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")
    
    if not text.strip():
        raise ValueError("PDF extraction resulted in empty text.")
    return text

def extract_text_from_text_file(file_path: str) -> str:
    """Safely extract text from TXT or MD files."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        raise ValueError(f"Failed to read text file: {str(e)}")
    
    if not text.strip():
        raise ValueError("Text file is empty.")
    return text

def process_file(file_path: str) -> str:
    """Extract text based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")
        
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        # .txt and .md
        return extract_text_from_text_file(file_path)

def ingest_document(file_path: str, db: Session) -> dict:
    """
    Ingests a single document into PostgreSQL (metadata) and ChromaDB (chunks).
    Returns a result dict for logging.
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    result = {
        "file": filename,
        "status": "failed",
        "reason": "",
        "chunks": 0
    }
    
    if ext not in SUPPORTED_EXTENSIONS:
        result["reason"] = f"Unsupported extension {ext}"
        return result
        
    try:
        content = process_file(file_path)
    except Exception as e:
        result["reason"] = f"Extraction error: {str(e)}"
        return result
        
    content_hash = get_content_hash(content)
    
    # Deterministic document_id (we use the content hash to ensure uniqueness)
    # Using content hash means if a document is updated, its hash changes, 
    # making it a new ingestion automatically (with a new ID), fulfilling M4.1 D.
    document_id = f"doc_{content_hash}"
    
    # 1. Idempotency Check in PostgreSQL
    existing_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == content_hash).first()
    if existing_doc:
        result["status"] = "skipped"
        result["reason"] = "Duplicate content hash"
        return result
        
    # Check for older versions of the same file
    old_version = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.filename == filename,
        KnowledgeDocument.source == file_path
    ).first()
    
    version_num = "1.0"
    if old_version:
        # It's an update. We'll delete the old one from DB.
        # Note: ChromaDB doesn't have a simple cascading delete, but we can delete by where metadata matches
        try:
            vector_store_manager = get_vector_db_manager()
            # Delete old chunks
            # chroma vector store delete requires ids or where
            # Since we generated deterministic chunk IDs, we could just delete them or use where clause
            # Langchain chroma delete takes ids
            old_chunk_ids = [f"{old_version.document_id}_chunk_{i}" for i in range(old_version.chunk_count)]
            vector_store_manager.vector_store.delete(ids=old_chunk_ids)
        except Exception as e:
            print(f"Warning: Failed to clean up old vector chunks for {filename}: {e}")
            
        old_v = float(old_version.version) if old_version.version else 1.0
        version_num = str(old_v + 1.0)
        db.delete(old_version)
        db.commit()

    # 2. Split Document into Chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    
    chunks = text_splitter.split_text(content)
    if not chunks:
        result["reason"] = "Document resulted in 0 chunks."
        return result
        
    # 3. Create Document DB Entry
    title = os.path.splitext(filename)[0].replace("_", " ").title()
    new_doc = KnowledgeDocument(
        document_id=document_id,
        filename=filename,
        title=title,
        source=file_path,
        source_type=ext.replace(".", ""),
        content_hash=content_hash,
        status="processing",
        chunk_count=len(chunks),
        version=version_num
    )
    db.add(new_doc)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        result["reason"] = f"DB Insert failed: {str(e)}"
        return result

    # 4. Ingest into ChromaDB
    documents_to_add = []
    ids_to_add = []
    
    for i, chunk in enumerate(chunks):
        # Deterministic Chunk ID
        chunk_id = f"{document_id}_chunk_{i}"
        
        # Source Traceability Metadata (M4.1 E)
        chunk_metadata = {
            "document_id": document_id,
            "filename": filename,
            "source": file_path,
            "chunk_index": i,
            "content_hash": content_hash,
            "title": title
        }
        
        documents_to_add.append(Document(page_content=chunk, metadata=chunk_metadata))
        ids_to_add.append(chunk_id)
        
    vector_store_manager = get_vector_db_manager()
    
    try:
        # ChromaDB allows passing ids explicitly
        vector_store_manager.vector_store.add_documents(documents=documents_to_add, ids=ids_to_add)
        
        # Mark as success
        new_doc.status = "success"
        db.commit()
        
        result["status"] = "success"
        result["chunks"] = len(chunks)
        
    except Exception as e:
        # If vector DB fails, mark DB entry as failed
        new_doc.status = "failed"
        db.commit()
        result["reason"] = f"Vector DB Error: {str(e)}"
        
    return result

def run_ingest(target_path: str):
    """
    CLI runner for ingestion. Target path can be a file or a directory.
    """
    db = SessionLocal()
    
    stats = {
        "discovered": 0,
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "chunks_created": 0
    }
    
    files_to_process = []
    
    if os.path.isfile(target_path):
        files_to_process.append(target_path)
    elif os.path.isdir(target_path):
        for root, _, files in os.walk(target_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    files_to_process.append(os.path.join(root, file))
    else:
        print(f"Error: Target path '{target_path}' does not exist.")
        return
        
    stats["discovered"] = len(files_to_process)
    print(f"Discovered {stats['discovered']} supported documents.")
    
    try:
        for file_path in files_to_process:
            res = ingest_document(file_path, db)
            
            if res["status"] == "success":
                stats["success"] += 1
                stats["chunks_created"] += res["chunks"]
                print(f"[SUCCESS] {res['file']} -> {res['chunks']} chunks")
            elif res["status"] == "skipped":
                stats["skipped"] += 1
                print(f"[SKIPPED] {res['file']} -> {res['reason']}")
            else:
                stats["failed"] += 1
                print(f"[FAILED] {res['file']} -> {res['reason']}")
                
    finally:
        db.close()
        
    print("\n--- Ingestion Summary ---")
    print(f"Documents Discovered: {stats['discovered']}")
    print(f"Successfully Ingested: {stats['success']}")
    print(f"Skipped (Duplicates): {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total Chunks Created: {stats['chunks_created']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        run_ingest(target)
    else:
        print("Usage: python -m app.knowledge.ingest <path_to_file_or_directory>")
        sys.exit(1)
