# app/routers/admin_users.py
"""Admin de usuarios (solo Gerente)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..utils.security import audit_view, require_roles  # get_current_user no se usa aquí

# usa la misma ruta que el resto del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# prefijo opcional; si no lo quieres, quítalo y deja como lo tenías
router = APIRouter(prefix="/admin", tags=["admin-users"])


@router.get("/users", response_class=HTMLResponse)
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    role: Optional[str] = None,
    active: Optional[str] = None,
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente")),
):
    query = db.query(User)
    if q:
        query = query.filter(User.email.ilike(f"%{q}%"))
    if role:
        query = query.filter(User.role == role)
    if active in {"true", "false"}:
        query = query.filter(User.is_active.is_(active == "true"))
    items = query.order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/users_list.html",
        {
            "request": request,
            "items": items,
            "q": q,
            "role": role,
            "active": active,
        },
    )


@router.get("/users/new", response_class=HTMLResponse)
def users_new(
    request: Request,
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente")),
):
    return templates.TemplateResponse(
        "admin/user_form.html",
        {"request": request, "item": None, "error": None},
    )


@router.post("/users")
def users_create(
    request: Request,
    email: str = Form(...),
    full_name: Optional[str] = Form(None),
    role: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _auth: User = Depends(require_roles("Gerente")),
):
    from ..utils.security import hash_password  # importar aquí si quieres evitar ciclos

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        return templates.TemplateResponse(
            "admin/user_form.html",
            {"request": request, "item": None, "error": "Email ya registrado"},
            status_code=400,
        )
    user = User(
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def users_edit(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return templates.TemplateResponse(
        "admin/user_form.html",
        {"request": request, "item": user, "error": None},
    )


@router.post("/users/{user_id}")
def users_update(
    request: Request,
    user_id: int,
    full_name: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(False),
    new_password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _auth: User = Depends(require_roles("Gerente")),
):
    from ..utils.security import hash_password

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.full_name = full_name
    if role:
        user.role = role
    user.is_active = bool(is_active)
    if new_password:
        user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/delete")
def users_delete(
    user_id: int,
    db: Session = Depends(get_db),
    _auth: User = Depends(require_roles("Gerente")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # baja lógica
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)
