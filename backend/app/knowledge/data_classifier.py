"""
M8.3 — Data Classifier

Classifies discovered datasets as:
  VERIFIED    — Exists, has known verified provenance in DB, ACTIVE+VERIFIED+is_authoritative
  UNVERIFIED  — Exists, ingested, but not yet verified via admin workflow
  DEMO        — Exists but is a test placeholder / synthetic fixture; NOT authoritative
  INVALID     — Exists but cannot be processed (corrupted, empty, unsupported format)
  NOT_PRESENT — Does not exist at the expected path

Classification is based on:
  1. File existence + readability
  2. Non-empty, non-trivial content (minimum meaningful length)
  3. Presence of publisher metadata in DB record
  4. Actual verification_status / is_authoritative / status from the PostgreSQL DB

IMPORTANT:
  - Authority is NEVER inferred from filename patterns (e.g. "guideline", "who", "gov").
  - Authority is NEVER inferred from PDF logos or professional appearance.
  - This module does NOT ingest documents — it only classifies what exists.
  - Classification is deterministic and auditable.
"""

import os
import hashlib
from typing import Literal, Optional
from dataclasses import dataclass, field

# Minimum byte size to avoid classifying near-empty files as real documents
_DEMO_SIZE_THRESHOLD_BYTES = 500

# Known demo/test filenames (lowercase) — these are always classified DEMO
_KNOWN_DEMO_FILENAMES = {
    "test_health.txt",
    "sample.txt",
    "sample.pdf",
    "dummy.txt",
    "placeholder.txt",
    "test_fixture.txt",
    "test.txt",
    "test.md",
    "hello.txt",
}

DatasetClassification = Literal["VERIFIED", "UNVERIFIED", "DEMO", "INVALID", "NOT_PRESENT"]


@dataclass
class ClassificationResult:
    path: str
    classification: DatasetClassification
    reason: str
    file_size_bytes: int = 0
    content_hash: Optional[str] = None
    db_document_id: Optional[str] = None
    db_status: Optional[str] = None
    db_verification_status: Optional[str] = None
    db_is_authoritative: bool = False
    db_publisher: Optional[str] = None


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _read_file_content(path: str) -> Optional[str]:
    """Read text content from TXT or MD files. Returns None on error."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".txt", ".md"):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                text = ""
                for page in reader.pages:
                    pt = page.extract_text()
                    if pt:
                        text += pt + "\n"
                return text if text.strip() else None
            except Exception:
                return None
    except Exception:
        return None
    return None


def classify_file(path: str, db=None) -> ClassificationResult:
    """
    Classify a single file path.

    Args:
        path: Absolute or relative path to the file.
        db:   Optional SQLAlchemy session. If provided, the DB record is checked
              for verification lifecycle status.

    Returns:
        ClassificationResult with classification and reasoning.
    """
    result = ClassificationResult(path=path, classification="NOT_PRESENT", reason="")

    # 1. Existence check
    if not os.path.exists(path):
        result.reason = "File does not exist."
        return result

    if not os.path.isfile(path):
        result.classification = "INVALID"
        result.reason = "Path exists but is not a regular file."
        return result

    # 2. Size check
    size = os.path.getsize(path)
    result.file_size_bytes = size

    ext = os.path.splitext(path)[1].lower()
    supported = {".txt", ".md", ".pdf"}
    if ext not in supported:
        result.classification = "INVALID"
        result.reason = f"Unsupported file extension: {ext}"
        return result

    # 3. Read content
    content = _read_file_content(path)
    if not content or not content.strip():
        result.classification = "INVALID"
        result.reason = "File is empty or produced no extractable text."
        return result

    content_hash = _compute_hash(content)
    result.content_hash = content_hash

    # 4. Known demo filename check (highest priority — no filename can override this)
    filename_lower = os.path.basename(path).lower()
    if filename_lower in _KNOWN_DEMO_FILENAMES:
        result.classification = "DEMO"
        result.reason = (
            f"Filename '{os.path.basename(path)}' is a known test/demo fixture. "
            "Not treated as authoritative regardless of content."
        )
        return result

    # 5. Size-based demo detection (very small files cannot be authoritative clinical docs)
    if size < _DEMO_SIZE_THRESHOLD_BYTES:
        result.classification = "DEMO"
        result.reason = (
            f"File size ({size} bytes) is below the minimum threshold "
            f"({_DEMO_SIZE_THRESHOLD_BYTES} bytes) for an authoritative clinical document. "
            "Classified as DEMO/placeholder."
        )
        return result

    # 6. DB check — look up by content_hash
    if db is not None:
        try:
            from app.models.knowledge import KnowledgeDocument
            db_doc = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.content_hash == content_hash
            ).first()

            if db_doc:
                result.db_document_id = db_doc.document_id
                result.db_status = db_doc.status
                result.db_verification_status = db_doc.verification_status
                result.db_is_authoritative = db_doc.is_authoritative
                result.db_publisher = db_doc.publisher

                if (
                    db_doc.is_authoritative
                    and db_doc.verification_status == "VERIFIED"
                    and db_doc.status == "ACTIVE"
                ):
                    result.classification = "VERIFIED"
                    result.reason = (
                        "Document is in DB with is_authoritative=True, "
                        "verification_status=VERIFIED, status=ACTIVE."
                    )
                else:
                    result.classification = "UNVERIFIED"
                    result.reason = (
                        f"Document found in DB but not fully verified. "
                        f"status={db_doc.status}, "
                        f"verification_status={db_doc.verification_status}, "
                        f"is_authoritative={db_doc.is_authoritative}."
                    )
                return result
        except Exception:
            pass  # DB unavailable — fall through to filesystem-only classification

    # 7. Not in DB — file exists but has never been ingested
    result.classification = "UNVERIFIED"
    result.reason = (
        "File exists and appears non-trivial, but has not been ingested and verified "
        "through the M8.2 admin workflow. Cannot be treated as authoritative."
    )
    return result


def classify_directory(directory: str, db=None) -> list:
    """
    Walk a directory and classify all supported files.

    Returns:
        List of ClassificationResult objects.
    """
    results = []
    supported = {".txt", ".md", ".pdf"}

    if not os.path.isdir(directory):
        return [ClassificationResult(
            path=directory,
            classification="NOT_PRESENT",
            reason="Directory does not exist."
        )]

    for root, _, files in os.walk(directory):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in supported:
                full_path = os.path.join(root, fname)
                results.append(classify_file(full_path, db=db))

    return results


def summarize_classifications(results: list) -> dict:
    """
    Summarize a list of ClassificationResult objects into counts by classification.
    """
    summary = {
        "VERIFIED": 0,
        "UNVERIFIED": 0,
        "DEMO": 0,
        "INVALID": 0,
        "NOT_PRESENT": 0,
        "total": len(results),
    }
    for r in results:
        summary[r.classification] = summary.get(r.classification, 0) + 1
    return summary
