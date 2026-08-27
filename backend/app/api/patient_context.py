from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.memory import PatientContext
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.memory import PatientContextOut, PatientContextUpdate
from app.memory.persistence import MemoryService

router = APIRouter()

@router.get("/", response_model=PatientContextOut)
def get_patient_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return MemoryService.get_patient_context(db, current_user.id)

@router.put("/", response_model=PatientContextOut)
def update_patient_context(
    ctx_in: PatientContextUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return MemoryService.update_patient_context(db, current_user.id, ctx_in)
