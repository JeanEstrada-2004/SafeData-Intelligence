"""Auth router: login/logout/forgot/reset + templates.

Stores JWT (HS256) in HttpOnly cookie `access_token`.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditAccess, PasswordResetToken, User
from ..utils.mail import send_password_reset_email
from ..utils.security import create_access_token, get_current_user, hash_password, try_get_current_user, verify_password


APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
ACCESS_TOKEN_EXPIRES_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRES_MIN", "60"))

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["auth"])


def _audit(db: Session, request: Request, action: str, user: Optional[User] = None):
    rec = AuditAccess(
        user_id=user.id if user else None,
        action=action,
        path=str(request.url.path),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(rec)
    db.commit()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password) or not user.is_active:
        _audit(db, request, "login_fail")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Credenciales inválidas o usuario inactivo"}, status_code=400
        )

    token = create_access_token(user.email, ACCESS_TOKEN_EXPIRES_MIN)
    resp = RedirectResponse(url="/", status_code=302)
    # Cookie segura
    secure = APP_BASE_URL.startswith("https://")
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=ACCESS_TOKEN_EXPIRES_MIN * 60,
    )
    _audit(db, request, "login_success", user)
    return resp


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token")
    _audit(db, request, "logout", user)
    return resp


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "sent": False, "error": None})


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_post(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        _audit(db, request, "reset_request")
        return templates.TemplateResponse(
            "forgot_password.html", {"request": request, "sent": True, "error": None}
        )

    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
    db.commit()
    reset_url = f"{APP_BASE_URL}/reset-password?token={token}"
    try:
        send_password_reset_email(user.email, reset_url)
    except Exception:
        # No detenemos el flujo por error de SMTP en entornos locales
        pass

    _audit(db, request, "reset_request", user)
    return templates.TemplateResponse("forgot_password.html", {"request": request, "sent": True, "error": None})


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token, "error": None})


@router.post("/reset-password")
def reset_password_post(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "reset_password.html", {"request": request, "token": token, "error": "Las contraseñas no coinciden"}, status_code=400
        )

    prt = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == token, PasswordResetToken.used_at.is_(None))
        .first()
    )
    if not prt or prt.expires_at < datetime.now(timezone.utc):
        return templates.TemplateResponse(
            "reset_password.html", {"request": request, "token": token, "error": "Token inválido o expirado"}, status_code=400
        )

    user = db.get(User, prt.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    user.hashed_password = hash_password(new_password)
    prt.used_at = datetime.now(timezone.utc)
    db.add(user)
    db.add(prt)
    db.commit()
    _audit(db, request, "reset_ok", user)
    return RedirectResponse(url="/login", status_code=302)

