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

def ingest_document(file_path: str, db: Session, doc_metadata: dict = None) -> dict:
    """
    Ingests a single document into PostgreSQL (metadata) and ChromaDB (chunks).
    Returns a result dict for logging.
    """
    if doc_metadata is None:
        doc_metadata = {}
        
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    result = {
        "file": filename,
        "status": "VALIDATION_FAILED",
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
    document_id = f"doc_{content_hash}"
    
    # 1. Idempotency Check in PostgreSQL
    existing_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == content_hash).first()
    if existing_doc:
        result["status"] = "skipped"
        result["reason"] = "Duplicate content hash"
        return result
        
    # Check for older versions of the same file
    old_versions = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.filename == filename,
        KnowledgeDocument.source == file_path
    ).order_by(KnowledgeDocument.id.desc()).all()
    
    version_num = doc_metadata.get("version", "1.0")
    if old_versions:
        # M8.2: Do NOT delete old active versions. 
        # Calculate new version if not explicitly provided
        if "version" not in doc_metadata:
            old_v_str = old_versions[0].version
            try:
                old_v = float(old_v_str) if old_v_str else 1.0
                version_num = str(old_v + 1.0)
            except ValueError:
                version_num = old_v_str + "-new"

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
        
    # 3. Validation Rules (M8.2 Phase 4)
    title = doc_metadata.get("title") or os.path.splitext(filename)[0].replace("_", " ").title()
    publisher = doc_metadata.get("publisher")
    
    # In M8.2, we enforce deterministic validation. We'll allow CLI ingestion to pass basic validation 
    # if publisher isn't strictly provided in CLI yet, or we can mark it VALIDATION_FAILED.
    # The requirement says "Validate: title, publisher/issuing organization..." 
    # Let's require publisher to enter PENDING_REVIEW, else VALIDATION_FAILED.
    initial_status = "PENDING_REVIEW"
    if not publisher:
        initial_status = "VALIDATION_FAILED"
        result["reason"] = "Missing required metadata: publisher"
    
    pub_date_str = doc_metadata.get("publication_date")
    pub_date = None
    if pub_date_str:
        if isinstance(pub_date_str, str):
            try:
                from datetime import datetime
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            pub_date = pub_date_str

    # Create Document DB Entry
    new_doc = KnowledgeDocument(
        document_id=document_id,
        filename=filename,
        title=title,
        source=file_path,
        source_type=ext.replace(".", ""),
        content_hash=content_hash,
        status=initial_status,
        chunk_count=len(chunks),
        version=version_num,
        is_authoritative=False,
        verification_status="UNVERIFIED",
        publisher=publisher,
        source_url=doc_metadata.get("source_url"),
        publication_date=pub_date
    )
    db.add(new_doc)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        result["status"] = "failed"
        result["reason"] = f"DB Insert failed: {str(e)}"
        return result
        
    if initial_status == "VALIDATION_FAILED":
        return result

    # 4. Ingest into ChromaDB
    documents_to_add = []
    ids_to_add = []
    
    for i, chunk in enumerate(chunks):
        # Deterministic Chunk ID
        chunk_id = f"{document_id}_chunk_{i}"
        
        # Source Traceability Metadata (M4.1 E & M8.1)
        chunk_metadata = {
            "document_id": document_id,
            "filename": filename,
            "source": file_path,
            "chunk_index": i,
            "content_hash": content_hash,
            "title": title,
            "is_authoritative": False, # Defaults to false for unverified docs
            "verification_status": "UNVERIFIED",
            "status": initial_status
        }
        
        documents_to_add.append(Document(page_content=chunk, metadata=chunk_metadata))
        ids_to_add.append(chunk_id)
        
    vector_store_manager = get_vector_db_manager()
    
    try:
        # ChromaDB allows passing ids explicitly
        vector_store_manager.vector_store.add_documents(documents=documents_to_add, ids=ids_to_add)
        
        # M8.2: We no longer set 'success'. It remains 'PENDING_REVIEW'
        db.commit()
        
        result["status"] = "PENDING_REVIEW"
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
    Documents ingested without explicit metadata are always VALIDATION_FAILED
    (publisher is required). Use run_ingest_with_metadata() for controlled ingestion.
    """
    run_ingest_with_metadata(target_path, publisher=None)


def run_ingest_with_metadata(
    target_path: str,
    publisher: str = None,
    source_url: str = None,
    publication_date: str = None,
    title: str = None,
    version: str = None,
) -> dict:
    """
    Controlled ingestion entry-point for M8.3.

    Accepts authoritative provenance metadata alongside the file path.
    Every successfully accepted document enters PENDING_REVIEW (never auto-VERIFIED).
    Documents without a publisher are rejected as VALIDATION_FAILED.

    Args:
        target_path:      Path to a single file or a directory.
        publisher:        Required. Name of the issuing organization/publisher.
        source_url:       Optional. Canonical URL for the document.
        publication_date: Optional. ISO date string (YYYY-MM-DD) of publication.
        title:            Optional. Override the document title.
        version:          Optional. Explicit version string (e.g. "2.1").

    Returns:
        Summary dict with counts.
    """
    db = SessionLocal()

    doc_metadata = {}
    if publisher:
        doc_metadata["publisher"] = publisher
    if source_url:
        doc_metadata["source_url"] = source_url
    if publication_date:
        doc_metadata["publication_date"] = publication_date
    if title:
        doc_metadata["title"] = title
    if version:
        doc_metadata["version"] = version

    stats = {
        "discovered": 0,
        "pending_review": 0,
        "skipped": 0,
        "validation_failed": 0,
        "failed": 0,
        "chunks_created": 0,
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
        return stats

    stats["discovered"] = len(files_to_process)
    print(f"Discovered {stats['discovered']} supported document(s).")

    try:
        for file_path in files_to_process:
            res = ingest_document(file_path, db, doc_metadata=doc_metadata.copy())

            if res["status"] == "PENDING_REVIEW":
                stats["pending_review"] += 1
                stats["chunks_created"] += res.get("chunks", 0)
                print(f"[PENDING_REVIEW] {res['file']} → {res.get('chunks', 0)} chunks")
            elif res["status"] == "skipped":
                stats["skipped"] += 1
                print(f"[SKIPPED]        {res['file']} → {res['reason']}")
            elif res["status"] == "VALIDATION_FAILED":
                stats["validation_failed"] += 1
                print(f"[VALIDATION_FAILED] {res['file']} → {res['reason']}")
            else:
                stats["failed"] += 1
                print(f"[FAILED]         {res['file']} → {res['reason']}")

    finally:
        db.close()

    print("\n--- M8.3 Ingestion Summary ---")
    print(f"  Documents Discovered:  {stats['discovered']}")
    print(f"  Pending Review:        {stats['pending_review']}")
    print(f"  Skipped (Duplicates):  {stats['skipped']}")
    print(f"  Validation Failed:     {stats['validation_failed']}")
    print(f"  Failed (errors):       {stats['failed']}")
    print(f"  Total Chunks Created:  {stats['chunks_created']}")
    if stats["pending_review"] > 0:
        print(
            "\n  ⚠️  Documents are in PENDING_REVIEW. An administrator must verify and "
            "activate them via the admin API before they enter the clinical RAG pipeline."
        )
    return stats


def discover_and_report(data_dir: str = None) -> dict:
    """
    M8.3 data audit helper. Classifies all files in the data directory
    without ingesting them. Returns a structured audit report.

    Args:
        data_dir: Path to scan. Defaults to backend/data/documents/.

    Returns:
        Audit report dict.
    """
    from app.knowledge.data_classifier import classify_directory, summarize_classifications

    if data_dir is None:
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "documents"
        )

    results = classify_directory(data_dir)
    summary = summarize_classifications(results)

    report = {
        "data_directory": data_dir,
        "files": [
            {
                "path": r.path,
                "filename": os.path.basename(r.path),
                "classification": r.classification,
                "reason": r.reason,
                "file_size_bytes": r.file_size_bytes,
                "content_hash": r.content_hash,
            }
            for r in results
        ],
        "summary": summary,
        "authoritative_available": summary.get("VERIFIED", 0) > 0,
        "data_blocked": summary.get("VERIFIED", 0) == 0,
    }

    return report


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "discover":
            path = sys.argv[2] if len(sys.argv) > 2 else None
            report = discover_and_report(path)
            print(json.dumps(report, indent=2))

        elif cmd == "ingest":
            if len(sys.argv) < 3:
                print("Usage: python -m app.knowledge.ingest ingest <path> [--publisher <pub>] [--source-url <url>]")
                sys.exit(1)
            target = sys.argv[2]
            pub = None
            url = None
            pub_date = None
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] == "--publisher" and i + 1 < len(args):
                    pub = args[i + 1]; i += 2
                elif args[i] == "--source-url" and i + 1 < len(args):
                    url = args[i + 1]; i += 2
                elif args[i] == "--publication-date" and i + 1 < len(args):
                    pub_date = args[i + 1]; i += 2
                else:
                    i += 1
            run_ingest_with_metadata(target, publisher=pub, source_url=url, publication_date=pub_date)

        else:
            # Legacy: treat as file/dir path
            run_ingest_with_metadata(sys.argv[1])
    else:
        print("Usage:")
        print("  python -m app.knowledge.ingest discover [path]")
        print("  python -m app.knowledge.ingest ingest <path> --publisher <name> [--source-url <url>]")
        sys.exit(1)


