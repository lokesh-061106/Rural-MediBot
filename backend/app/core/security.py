import bcrypt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import jwt

ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if os.environ.get("TESTING", "false").lower() == "true":
    SECRET_KEY = SECRET_KEY or "test_secret_key_that_is_at_least_thirty_two_chars_long"
elif not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
    raise RuntimeError("JWT_SECRET_KEY must be a secure 32+ character secret in production")

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None, role: str = "patient") -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")))
    
    to_encode = {"exp": expire, "sub": str(subject), "role": role}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
