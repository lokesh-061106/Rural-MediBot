import re

with open("backend/app/api/admin.py", "r", encoding="utf-8") as f:
    content = f.read()

# find the @router.get("/knowledge/readiness") and everything after it
pattern = r"@router\.get\(\"/knowledge/readiness\"\).*$"
new_code = """@router.get("/knowledge/readiness")
def get_knowledge_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    # Medical Knowledge Metrics
    docs = db.query(KnowledgeDocument).all()
    
    k_total = len(docs)
    k_verified = sum(1 for d in docs if d.verification_status == "VERIFIED")
    k_pending = sum(1 for d in docs if d.status == "PENDING_REVIEW")
    k_rejected = sum(1 for d in docs if d.status in ("REJECTED", "VALIDATION_FAILED"))
    k_active = sum(1 for d in docs if d.status == "ACTIVE")
    k_deprecated = sum(1 for d in docs if d.status == "DEPRECATED")
    k_authoritative = sum(1 for d in docs if d.is_authoritative)
    
    # Facilities Metrics
    facs = db.query(HealthcareFacility).all()
    
    f_total = len(facs)
    f_verified = sum(1 for f in facs if f.verification_status == "VERIFIED")
    f_unverified = sum(1 for f in facs if f.verification_status == "UNVERIFIED")
    f_stale = sum(1 for f in facs if f.verification_status == "STALE")
    f_active = sum(1 for f in facs if f.status == "active")
    
    # State Logic
    medical_rag = "READY" if (k_authoritative > 0 and k_verified > 0 and k_active > 0) else "BLOCKED"
    facility_network = "READY" if f_verified > 0 else "BLOCKED"
    
    overall_state = "READY" if (medical_rag == "READY" and facility_network == "READY") else "BLOCKED"
    
    if overall_state == "BLOCKED":
        overall_state = "AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED"
    
    return {
        "readiness_status": overall_state,
        "subsystems": {
            "medical_rag": medical_rag,
            "facility_network": facility_network
        },
        "knowledge_metrics": {
            "total_documents": k_total,
            "verified_documents": k_verified,
            "pending_documents": k_pending,
            "rejected_documents": k_rejected,
            "active_documents": k_active,
            "stale_documents": k_deprecated,
            "authoritative_documents": k_authoritative
        },
        "facility_metrics": {
            "total_facilities": f_total,
            "verified_facilities": f_verified,
            "unverified_facilities": f_unverified,
            "stale_facilities": f_stale,
            "active_facilities": f_active
        },
        "documents": [{"id": d.document_id, "title": d.title, "content_hash": d.content_hash, "verification_status": d.verification_status, "is_authoritative": d.is_authoritative, "status": d.status} for d in docs]
    }

from datetime import datetime

@router.post("/knowledge/documents/{document_id}/verify")
def verify_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status == "VALIDATION_FAILED":
        raise HTTPException(status_code=400, detail="Cannot verify a failed document")
        
    doc.verification_status = "VERIFIED"
    doc.is_authoritative = True
    doc.verified_at = datetime.utcnow()
    doc.status = "VERIFIED"
    
    db.commit()
    return {"message": "Document marked as verified", "document_id": document_id}

@router.post("/knowledge/documents/{document_id}/activate")
def activate_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.verification_status != "VERIFIED":
        raise HTTPException(status_code=400, detail="Document must be VERIFIED before it can be ACTIVE")
        
    old_docs = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.filename == doc.filename,
        KnowledgeDocument.document_id != document_id,
        KnowledgeDocument.status == "ACTIVE"
    ).all()
    
    for old_doc in old_docs:
        old_doc.status = "DEPRECATED"
        
    doc.status = "ACTIVE"
    db.commit()
    return {"message": "Document activated", "deprecated_count": len(old_docs)}
"""

content = re.sub(pattern, new_code, content, flags=re.DOTALL)

with open("backend/app/api/admin.py", "w", encoding="utf-8") as f:
    f.write(content)

