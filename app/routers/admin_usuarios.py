# app/routers/admin_users.py
"""Admin de usuarios (solo Gerente)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditAccess, User
from ..utils.seguridad import audit_event, audit_view, require_roles, validate_password_policy

# usa la misma ruta que el resto del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# prefijo opcional; si no lo quieres, quítalo y deja como lo tenÃ­as
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
    user_ids = [u.id for u in items]
    last_access = {}
    if user_ids:
        last_access = {
            row.user_id: row.last_login
            for row in (
                db.query(AuditAccess.user_id, func.max(AuditAccess.created_at).label("last_login"))
                .filter(AuditAccess.action == "login_success", AuditAccess.user_id.in_(user_ids))
                .group_by(AuditAccess.user_id)
                .all()
            )
        }
    return templates.TemplateResponse(
        "admin/usuarios_lista.html",
        {
            "request": request,
            "items": items,
            "last_access": last_access,
            "q": q,
            "role": role,
            "active": active,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/users/new", response_class=HTMLResponse)
def users_new(
    request: Request,
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente")),
):
    return templates.TemplateResponse(
        "admin/usuario_form.html",
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
    from ..utils.seguridad import hash_password

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        return templates.TemplateResponse(
            "admin/usuario_form.html",
            {"request": request, "item": None, "error": "Email ya registrado"},
            status_code=400,
        )
    try:
        validate_password_policy(password)
    except ValueError as exc:
        return templates.TemplateResponse(
            "admin/usuario_form.html",
            {"request": request, "item": None, "error": str(exc)},
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
    audit_event(db, request, "user_create", user=_auth, detail={"target_user_id": user.id, "role": role})
    return RedirectResponse("/admin/users?message=Usuario%20creado", status_code=302)


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
        "admin/usuario_form.html",
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
    from ..utils.seguridad import hash_password

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    old_role = user.role
    old_active = bool(user.is_active)
    next_active = bool(is_active)
    if user.id == _auth.id and not next_active:
        active_managers = db.query(User).filter(User.role == "Gerente", User.is_active.is_(True)).count()
        if active_managers <= 1:
            return templates.TemplateResponse(
                "admin/usuario_form.html",
                {"request": request, "item": user, "error": "No puedes desactivar el único usuario Gerente activo."},
                status_code=400,
            )
    if old_role == "Gerente" and role and role != "Gerente":
        active_managers = db.query(User).filter(User.role == "Gerente", User.is_active.is_(True), User.id != user.id).count()
        if active_managers < 1:
            return templates.TemplateResponse(
                "admin/usuario_form.html",
                {"request": request, "item": user, "error": "Debe quedar al menos un usuario Gerente activo."},
                status_code=400,
            )
    if new_password:
        try:
            validate_password_policy(new_password)
        except ValueError as exc:
            return templates.TemplateResponse(
                "admin/usuario_form.html",
                {"request": request, "item": user, "error": str(exc)},
                status_code=400,
            )

    user.full_name = full_name
    if role:
        user.role = role
    user.is_active = next_active
    if new_password:
        user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    audit_event(
        db,
        request,
        "user_update",
        user=_auth,
        detail={
            "target_user_id": user.id,
            "old_role": old_role,
            "new_role": user.role,
            "old_active": old_active,
            "new_active": user.is_active,
            "password_changed": bool(new_password),
        },
    )
    return RedirectResponse("/admin/users?message=Usuario%20actualizado", status_code=302)


@router.post("/users/{user_id}/delete")
def users_delete(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _auth: User = Depends(require_roles("Gerente")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == _auth.id:
        active_managers = db.query(User).filter(User.role == "Gerente", User.is_active.is_(True)).count()
        if active_managers <= 1:
            return RedirectResponse("/admin/users?error=No%20puedes%20desactivar%20el%20único%20Gerente%20activo", status_code=302)
    # baja lÃ³gica
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    audit_event(db, request, "user_deactivate", user=_auth, detail={"target_user_id": user.id})
    return RedirectResponse("/admin/users?message=Usuario%20desactivado", status_code=302)

