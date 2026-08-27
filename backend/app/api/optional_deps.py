from typing import Optional
from fastapi import Depends
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core import security
from app.models.user import User
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_optional_user(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme_optional)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
        
    return db.query(User).filter(User.id == int(user_id)).first()
