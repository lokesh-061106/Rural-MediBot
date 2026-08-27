from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.reminder import Reminder

router = APIRouter()

class ReminderCreate(BaseModel):
    medicine_name: str
    dose: Optional[str] = None
    time: str
    frequency: str
    notes: Optional[str] = None

class ReminderUpdate(BaseModel):
    medicine_name: Optional[str] = None
    dose: Optional[str] = None
    time: Optional[str] = None
    frequency: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None

class ReminderOut(BaseModel):
    id: int
    medicine_name: str
    dose: Optional[str]
    time: str
    frequency: str
    notes: Optional[str]
    active: bool
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ReminderOut])
def get_reminders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Reminder).filter(Reminder.user_id == current_user.id).all()

@router.post("/", response_model=ReminderOut)
def create_reminder(
    reminder_in: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_reminder = Reminder(**reminder_in.model_dump(), user_id=current_user.id)
    db.add(new_reminder)
    db.commit()
    db.refresh(new_reminder)
    return new_reminder

@router.put("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    reminder_in: ReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
        
    update_data = reminder_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reminder, key, value)
        
    db.commit()
    db.refresh(reminder)
    return reminder

@router.delete("/{reminder_id}", response_model=dict)
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
        
    db.delete(reminder)
    db.commit()
    return {"status": "success", "message": "Reminder deleted"}
