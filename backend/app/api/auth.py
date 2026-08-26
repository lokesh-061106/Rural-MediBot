from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.database import get_db
from app.models.user import User, UserProfile, AuditLog
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.core import security
from app.api import deps

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        phone=user_in.phone,
        role=user_in.role,
        preferred_language=user_in.preferred_language,
        password_hash=security.get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create empty profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    
    # Audit log
    log = AuditLog(user_id=user.id, action="REGISTER", resource="User", resource_id=str(user.id))
    db.add(log)
    
    db.commit()
    
    return user

@router.post("/login")
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.password_hash):
        if user:
            log = AuditLog(user_id=user.id, action="LOGIN_FAILED", resource="User", resource_id=str(user.id), success=False)
            db.add(log)
            db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = security.create_access_token(user.id, role=user.role)
    
    log = AuditLog(user_id=user.id, action="LOGIN_SUCCESS", resource="User", resource_id=str(user.id))
    db.add(log)
    db.commit()
    
    # Format according to what Next.js expects from its proxy route, or standard OAuth2
    # Next.js expects { user, token } in its old route, but we return standard token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(deps.get_current_active_user)):
    return current_user
