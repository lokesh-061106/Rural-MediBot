from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, AuditLog
from app.models.consultation import Consultation

router = APIRouter()

class ConsultationOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: Optional[int]
    status: str
    risk_level: str
    symptoms: str
    ai_assessment: Optional[str]
    doctor_notes: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

class ConsultationUpdate(BaseModel):
    status: Optional[str] = None
    doctor_notes: Optional[str] = None

@router.get("/consultations", response_model=List[ConsultationOut])
def get_consultations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor"))
):
    # Get unassigned consultations or ones assigned to this doctor
    consultations = db.query(Consultation).filter(
        (Consultation.doctor_id == None) | (Consultation.doctor_id == current_user.id)
    ).order_by(Consultation.created_at.desc()).all()
    
    result = []
    for c in consultations:
        result.append({
            "id": c.id,
            "patient_id": c.patient_id,
            "doctor_id": c.doctor_id,
            "status": c.status,
            "risk_level": c.risk_level,
            "symptoms": c.symptoms,
            "ai_assessment": c.ai_assessment,
            "doctor_notes": c.doctor_notes,
            "created_at": c.created_at.isoformat()
        })
    return result

@router.put("/consultations/{consultation_id}", response_model=ConsultationOut)
def update_consultation(
    consultation_id: int,
    update_data: ConsultationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor"))
):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
        
    if consultation.doctor_id and consultation.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Consultation assigned to another doctor")
        
    if not consultation.doctor_id and update_data.status == "ACCEPTED":
        consultation.doctor_id = current_user.id
        
    if update_data.status:
        consultation.status = update_data.status
    if update_data.doctor_notes is not None:
        consultation.doctor_notes = update_data.doctor_notes
        
    db.commit()
    db.refresh(consultation)
    
    log = AuditLog(user_id=current_user.id, action="CONSULTATION_UPDATED", resource="Consultation", resource_id=str(consultation.id))
    db.add(log)
    db.commit()
    
    return {
        "id": consultation.id,
        "patient_id": consultation.patient_id,
        "doctor_id": consultation.doctor_id,
        "status": consultation.status,
        "risk_level": consultation.risk_level,
        "symptoms": consultation.symptoms,
        "ai_assessment": consultation.ai_assessment,
        "doctor_notes": consultation.doctor_notes,
        "created_at": consultation.created_at.isoformat()
    }
