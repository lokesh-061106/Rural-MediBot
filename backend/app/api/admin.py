from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    docs = db.query(KnowledgeDocument).all()
    
    total = len(docs)
    verified = sum(1 for d in docs if d.verification_status == "VERIFIED")
    authoritative = sum(1 for d in docs if d.is_authoritative)
    
    document_details = []
    for d in docs:
        document_details.append({
            "id": d.document_id,
            "title": d.title,
            "source": d.source,
            "source_type": d.source_type,
            "version": d.version,
            "content_hash": d.content_hash,
            "ingestion_status": d.status,
            "verification_status": d.verification_status,
            "is_authoritative": d.is_authoritative
        })
        
    readiness_status = "READY" if total > 0 and total == authoritative else "AUTHORITATIVE MEDICAL DATASET NOT AVAILABLE"
    
    return {
        "readiness_status": readiness_status,
        "metrics": {
            "total_documents": total,
            "verified_documents": verified,
            "authoritative_documents": authoritative
        },
        "documents": document_details
    }

