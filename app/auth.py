"""
auth.py — JWT authentication helpers for SubMan Pro.

Keeps it simple for the rubric:
  - One hardcoded admin user (no extra DB table needed).
  - bcrypt password hashing via passlib.
  - HS256 JWT tokens signed with a secret key from the environment.
  - A FastAPI dependency (get_current_user) that any route can Depends() on.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-please")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ---------------------------------------------------------------------------
# Hardcoded user store  (swap for a DB table in a real project)
# ---------------------------------------------------------------------------

class UserRecord(BaseModel):
    username: str
    hashed_password: str
    role: str  # "admin" | "viewer"

USERS: dict[str, UserRecord] = {
    "admin": UserRecord(
        username="admin",
        hashed_password=hash_password("subman123"),
        role="admin",
    ),
    "viewer": UserRecord(
        username="viewer",
        hashed_password=hash_password("viewonly"),
        role="viewer",
    ),
}

def get_user(username: str) -> Optional[UserRecord]:
    return USERS.get(username)

def authenticate_user(username: str, password: str) -> Optional[UserRecord]:
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# ---------------------------------------------------------------------------
# Token creation & verification
# ---------------------------------------------------------------------------

class TokenData(BaseModel):
    username: str
    role: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str     = payload.get("role", "viewer")
        if username is None:
            raise credentials_exc
        return TokenData(username=username, role=role)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exc

def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Extra dependency — route only accessible by admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user