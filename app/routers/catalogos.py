"""Administracion de catalogos operativos."""
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
from ..models import CatalogItem, User
from ..utils.seguridad import audit_event, audit_view, require_roles

BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/admin/catalogos", tags=["catalogos"])

CATEGORIES = {
    "tipo_incidencia": "Tipos de denuncia",
    "turno": "Turnos",
    "estado": "Estados",
    "fuente_datos": "Fuentes de datos",
}


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _redirect(message: str | None = None, error: str | None = None) -> RedirectResponse:
    if error:
        return RedirectResponse(f"/admin/catalogos?error={error}", status_code=302)
    return RedirectResponse(f"/admin/catalogos?message={message or 'Operacion%20realizada'}", status_code=302)


def _duplicate_exists(db: Session, category: str, name: str, exclude_id: int | None = None) -> bool:
    query = db.query(CatalogItem).filter(
        CatalogItem.category == category,
        func.lower(CatalogItem.name) == name.lower(),
    )
    if exclude_id:
        query = query.filter(CatalogItem.id != exclude_id)
    return db.query(query.exists()).scalar()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def catalogos_page(
    request: Request,
    db: Session = Depends(get_db),
    category: str | None = None,
    active: str | None = None,
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente")),
):
    query = db.query(CatalogItem)
    if category in CATEGORIES:
        query = query.filter(CatalogItem.category == category)
    if active in {"true", "false"}:
        query = query.filter(CatalogItem.is_active.is_(active == "true"))
    items = query.order_by(CatalogItem.category.asc(), CatalogItem.name.asc()).all()
    return templates.TemplateResponse(
        "admin/catalogos.html",
        {
            "request": request,
            "items": items,
            "categories": CATEGORIES,
            "category": category or "",
            "active": active or "",
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("")
@router.post("/")
def catalogos_create(
    request: Request,
    category: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente")),
):
    category = _clean(category)
    name = _clean(name)
    if category not in CATEGORIES:
        return _redirect(error="Categoria%20invalida")
    if not name:
        return _redirect(error="El%20nombre%20es%20obligatorio")
    if _duplicate_exists(db, category, name):
        return _redirect(error="Ya%20existe%20un%20catalogo%20con%20ese%20nombre")

    item = CatalogItem(category=category, name=name, description=_clean(description), is_active=True)
    db.add(item)
    db.commit()
    audit_event(db, request, "catalog_create", user=user, detail={"catalog_id": item.id, "category": category, "name": name})
    return _redirect(message="Catalogo%20creado")


@router.post("/{item_id}")
def catalogos_update(
    request: Request,
    item_id: int,
    category: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente")),
):
    item = db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalogo no encontrado")

    category = _clean(category)
    name = _clean(name)
    if category not in CATEGORIES:
        return _redirect(error="Categoria%20invalida")
    if not name:
        return _redirect(error="El%20nombre%20es%20obligatorio")
    if _duplicate_exists(db, category, name, exclude_id=item.id):
        return _redirect(error="Ya%20existe%20un%20catalogo%20con%20ese%20nombre")

    before = {"category": item.category, "name": item.name, "is_active": bool(item.is_active)}
    item.category = category
    item.name = name
    item.description = _clean(description)
    item.is_active = bool(is_active)
    item.updated_at = datetime.utcnow()
    db.add(item)
    db.commit()
    audit_event(
        db,
        request,
        "catalog_update",
        user=user,
        detail={"catalog_id": item.id, "before": before, "after": {"category": item.category, "name": item.name, "is_active": item.is_active}},
    )
    return _redirect(message="Catalogo%20actualizado")


@router.post("/{item_id}/toggle")
def catalogos_toggle(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente")),
):
    item = db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalogo no encontrado")
    item.is_active = not bool(item.is_active)
    item.updated_at = datetime.utcnow()
    db.add(item)
    db.commit()
    audit_event(db, request, "catalog_toggle", user=user, detail={"catalog_id": item.id, "is_active": item.is_active})
    return _redirect(message="Catalogo%20actualizado")
