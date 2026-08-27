from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Any

from app.db.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, AuditLog
from app.models.facility import HealthcareFacility
from app.models.consultation import Consultation

router = APIRouter()

@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    total_users = db.query(User).count()
    active_doctors = db.query(User).filter(User.role == "doctor", User.is_active == True).count()
    total_consultations = db.query(Consultation).count() 
    total_facilities = db.query(HealthcareFacility).count()
    
    return {
        "stats": {
            "total_users": total_users,
            "active_doctors": active_doctors,
            "ai_consultations": total_consultations,
            "total_facilities": total_facilities
        },
        "system_status": [
            {"name": "Gemini AI API", "status": "Operational", "color": "text-emerald-400"},
            {"name": "PostgreSQL Database", "status": "Operational", "color": "text-emerald-400"},
            {"name": "Jitsi Telemedicine", "status": "Operational", "color": "text-emerald-400"}
        ]
    }

@router.get("/facilities/stats")
def get_facilities_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    active = db.query(HealthcareFacility).filter(HealthcareFacility.status == "active").count()
    inactive = db.query(HealthcareFacility).filter(HealthcareFacility.status == "inactive").count()
    
    # Group by facility_type
    types = db.query(HealthcareFacility.facility_type, func.count(HealthcareFacility.id))\
              .group_by(HealthcareFacility.facility_type).all()
              
    return {
        "active_facilities": active,
        "inactive_facilities": inactive,
        "by_type": {t[0]: t[1] for t in types}
    }

@router.get("/users/stats")
def get_users_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    roles = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    return {
        "by_role": {t[0]: t[1] for t in roles}
    }

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    logs = db.query(AuditLog, User.email).outerjoin(User, AuditLog.user_id == User.id)\
             .order_by(AuditLog.timestamp.desc()).limit(limit).all()
             
    result = []
    for log, email in logs:
        result.append({
            "id": log.id,
            "user_email": email or "Unknown",
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "timestamp": log.timestamp.isoformat(),
            "success": log.success
        })
    return result

from app.models.knowledge import KnowledgeDocument

@router.get("/knowledge/readiness")
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
    medical_rag = "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
    if k_authoritative > 0 and k_verified > 0 and k_active > 0:
        medical_rag = "CLINICALLY_DATA_READY"
    elif k_verified > 0 and k_active == 0:
        medical_rag = "AUTHORITATIVE PRODUCTION DATASET: VERIFIED BUT NOT ACTIVATED"
    elif k_pending > 0:
        medical_rag = "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
        
    facility_network = "READY" if f_verified > 0 else "BLOCKED"
    
    overall_state = "CLINICALLY_DATA_READY" if (medical_rag == "CLINICALLY_DATA_READY" and facility_network == "READY") else medical_rag
    

    
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
        "documents": [{
            "id": d.document_id, 
            "title": d.title, 
            "filename": d.filename,
            "publisher": d.publisher,
            "source_url": d.source_url,
            "publication_date": d.publication_date.isoformat() if d.publication_date else None,
            "content_hash": d.content_hash, 
            "verification_status": d.verification_status, 
            "is_authoritative": d.is_authoritative, 
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None
        } for d in docs]
    }

from datetime import datetime

class VerifyRequest(BaseModel):
    checklist_confirmed: bool = False

@router.post("/knowledge/documents/{document_id}/verify")
def verify_knowledge_document(
    document_id: str,
    req: VerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not req.checklist_confirmed:
        raise HTTPException(status_code=400, detail="Administrator must explicitly confirm the review checklist")
        
    if doc.status not in ["PENDING_REVIEW", "UNVERIFIED"]:
        raise HTTPException(status_code=400, detail="Document must be in PENDING_REVIEW or eligible state to be verified")
        
    if doc.status in ["DEMO", "INVALID", "STALE"]:
        raise HTTPException(status_code=400, detail="Cannot verify a DEMO, STALE or INVALID document")
        
    # Provenance guard
    if not doc.publisher:
        raise HTTPException(status_code=400, detail="Missing required provenance metadata: publisher")
    if not doc.source_url:
        raise HTTPException(status_code=400, detail="Missing required provenance metadata: source_url")
    if not doc.publication_date:
        raise HTTPException(status_code=400, detail="Missing required provenance metadata: publication_date")
    if not doc.content_hash:
        raise HTTPException(status_code=400, detail="Missing required content hash")
    if not doc.filename or not doc.chunk_count or doc.chunk_count == 0:
        raise HTTPException(status_code=400, detail="Missing filename or content is empty")
        
    old_status = doc.status
    doc.verification_status = "VERIFIED"
    doc.is_authoritative = True
    doc.verified_at = datetime.utcnow()
    doc.status = "VERIFIED"
    
    # Audit logging
    log = AuditLog(
        user_id=current_user.id,
        action="VERIFY_DOCUMENT",
        resource="KnowledgeDocument",
        resource_id=document_id,
        success=True,
        details={
            "previous_status": old_status,
            "new_status": "VERIFIED",
            "content_hash": doc.content_hash,
            "review_decision": "APPROVE"
        }
    )
    db.add(log)
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
        
    if doc.verification_status != "VERIFIED" or not doc.is_authoritative:
        raise HTTPException(status_code=400, detail="Document must be VERIFIED and authoritative before it can be ACTIVE")
        
    if doc.status in ["ACTIVE", "DEPRECATED", "STALE", "DEMO", "PENDING_REVIEW"]:
        raise HTTPException(status_code=400, detail=f"Document is in state {doc.status} which cannot be activated")
        
    if not doc.publisher or not doc.source_url or not doc.content_hash:
        raise HTTPException(status_code=400, detail="Missing required provenance or content hash")
        
    old_docs = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.filename == doc.filename,
        KnowledgeDocument.document_id != document_id,
        KnowledgeDocument.status == "ACTIVE"
    ).all()
    
    for old_doc in old_docs:
        old_doc.status = "DEPRECATED"
        db.add(AuditLog(
            user_id=current_user.id,
            action="DEPRECATE_DOCUMENT",
            resource="KnowledgeDocument",
            resource_id=old_doc.document_id,
            success=True
        ))
        
    old_status = doc.status
    doc.status = "ACTIVE"
    
    log = AuditLog(
        user_id=current_user.id,
        action="ACTIVATE_DOCUMENT",
        resource="KnowledgeDocument",
        resource_id=document_id,
        success=True,
        details={
            "previous_status": old_status,
            "new_status": "ACTIVE",
            "content_hash": doc.content_hash,
            "review_decision": "ACTIVATE"
        }
    )
    db.add(log)
    db.commit()
    return {"message": "Document activated", "deprecated_count": len(old_docs)}


@router.post("/knowledge/documents/{document_id}/reject")
def reject_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    old_status = doc.status
    doc.status = "REJECTED"
    
    log = AuditLog(
        user_id=current_user.id,
        action="REJECT_DOCUMENT",
        resource="KnowledgeDocument",
        resource_id=document_id,
        success=True,
        details={
            "previous_status": old_status,
            "new_status": "REJECTED",
            "content_hash": doc.content_hash,
            "review_decision": "REJECT"
        }
    )
    db.add(log)
    db.commit()
    return {"message": "Document rejected", "document_id": document_id}
