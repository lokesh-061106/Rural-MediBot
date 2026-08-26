from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User, UserProfile, AuditLog
from app.schemas.user import UserProfileUpdate, UserProfileResponse
from app.api import deps

router = APIRouter()

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(deps.get_current_active_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(profile_in: UserProfileUpdate, current_user: User = Depends(deps.get_current_active_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    update_data = profile_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    log = AuditLog(user_id=current_user.id, action="PROFILE_UPDATE", resource="UserProfile", resource_id=str(profile.id))
    db.add(log)
    
    db.commit()
    db.refresh(profile)
    return profile
