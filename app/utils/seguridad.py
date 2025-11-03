"""Security helpers: password hashing, JWT, and dependencies.

Auth por cookie: guarda un JWT HS256 en la cookie HttpOnly `access_token`.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditAccess, User

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-super-secret")
ACCESS_TOKEN_EXPIRES_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRES_MIN", "60"))


# ---------------------------
# Password helpers
# ---------------------------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # bcrypt solo admite 72 bytes; truncamos si es necesario
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        # bcrypt solo admite 72 bytes
        pw_bytes = password.encode("utf-8")
        if len(pw_bytes) > 72:
            pw_bytes = pw_bytes[:72]
        
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception:
        return False



# ---------------------------
# JWT helpers
# ---------------------------
def create_access_token(email: str, expires_minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRES_MIN
    )
    payload = {"sub": email, "exp": int(exp.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def _read_token_from_cookie(request: Request) -> Optional[str]:
    # 1) cookie
    token = request.cookies.get("access_token")
    if token:
        return token
    # 2) Authorization: Bearer ...
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    scheme, param = get_authorization_scheme_param(auth)
    if scheme.lower() != "bearer":
        return None
    return param


# ---------------------------
# Current user deps
# ---------------------------
def try_get_current_user(
    request: Request,
    db: Session = Depends(get_db),   # <-- AQUÍ estaba el problema
) -> Optional[User]:
    token = _read_token_from_cookie(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user = try_get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_roles(*roles: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _dep


# ---------------------------
# Auditar vistas
# ---------------------------
def audit_view(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(try_get_current_user),
):
    record = AuditAccess(
        user_id=getattr(user, "id", None),
        action="view",
        path=str(request.url.path),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(record)
    db.commit()
