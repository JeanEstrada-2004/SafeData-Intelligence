"""Consulta de auditoria del sistema."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditAccess, User
from ..utils.seguridad import audit_view, require_roles

BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/admin/auditoria", tags=["auditoria"])


def _parse_date(value: Optional[str], end: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        if end:
            return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def auditoria_page(
    request: Request,
    db: Session = Depends(get_db),
    action: str | None = None,
    status: str | None = None,
    q: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    page: int = 1,
    _view: None = Depends(audit_view),
    _auth: User = Depends(require_roles("Gerente", "AdministradorTecnico", "OTICS")),
):
    page = max(1, int(page or 1))
    per_page = 30
    query = db.query(AuditAccess)

    if action:
        query = query.filter(AuditAccess.action == action)
    if status:
        query = query.filter(AuditAccess.status == status)
    start = _parse_date(desde)
    end = _parse_date(hasta, end=True)
    if start:
        query = query.filter(AuditAccess.created_at >= start)
    if end:
        query = query.filter(AuditAccess.created_at <= end)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                AuditAccess.action.ilike(like),
                AuditAccess.path.ilike(like),
                AuditAccess.ip.ilike(like),
                AuditAccess.user_agent.ilike(like),
                cast(AuditAccess.detail_json, String).ilike(like),
            )
        )

    total = int(query.count() or 0)
    records = (
        query.order_by(AuditAccess.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    user_ids = {r.user_id for r in records if r.user_id}
    users = {}
    if user_ids:
        users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    actions = [x[0] for x in db.query(AuditAccess.action).distinct().order_by(AuditAccess.action.asc()).all() if x[0]]
    statuses = [x[0] for x in db.query(AuditAccess.status).distinct().order_by(AuditAccess.status.asc()).all() if x[0]]

    return templates.TemplateResponse(
        "admin/auditoria.html",
        {
            "request": request,
            "records": records,
            "users": users,
            "actions": actions,
            "statuses": statuses,
            "filters": {"action": action or "", "status": status or "", "q": q or "", "desde": desde or "", "hasta": hasta or ""},
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    )
