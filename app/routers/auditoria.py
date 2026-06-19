"""Consulta de auditoria del sistema."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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

ACTION_LABELS = {
    "view": "Consultó una pantalla",
    "login_success": "Inició sesión",
    "login_fail": "Intento de acceso fallido",
    "logout": "Cerró sesión",
    "reset_request": "Solicitó recuperar contraseña",
    "reset_ok": "Cambió su contraseña",
    "user_create": "Creó un usuario",
    "user_update": "Actualizó un usuario",
    "user_deactivate": "Desactivó un usuario",
    "catalog_create": "Creó un catálogo",
    "catalog_update": "Actualizó un catálogo",
    "catalog_toggle": "Activó o desactivó un catálogo",
    "upload_processed": "Procesó una carga de datos",
    "upload_error": "Error al cargar archivo",
    "export_denuncias_csv": "Exportó incidencias a CSV",
    "export_denuncias_excel": "Exportó incidencias a Excel",
    "export_map_points_csv": "Exportó puntos del mapa",
    "prediction_query": "Consultó predicción de riesgo",
}

STATUS_LABELS = {
    "ok": "Correcto",
    "error": "Con error",
    "warning": "Con observaciones",
}


def _parse_date(value: Optional[str], end: bool = False) -> datetime | None:
    if not value:
        return None


def _module_label(path: str) -> str:
    path = path or ""
    if path.startswith("/api/denuncias/upload"):
        return "Carga de datos"
    if path.startswith("/api/denuncias/export") or path.startswith("/listado-denuncias"):
        return "Denuncias"
    if path.startswith("/api/prediccion") or path.startswith("/prediccion-ia"):
        return "Predicción IA"
    if path.startswith("/api/map") or path.startswith("/mapa-calor"):
        return "Mapa de calor"
    if path.startswith("/admin/catalogos"):
        return "Catálogos"
    if path.startswith("/admin/auditoria"):
        return "Auditoría"
    if path.startswith("/admin/users"):
        return "Usuarios"
    if path.startswith("/login") or path.startswith("/logout") or "password" in path:
        return "Acceso"
    if path == "/":
        return "Panel analítico"
    return "Sistema"


def _status_label(status: str | None) -> str:
    return STATUS_LABELS.get(status or "", status or "Sin estado")


def _action_label(action: str | None) -> str:
    return ACTION_LABELS.get(action or "", action or "Acción no identificada")


def _detail_summary(detail: Any) -> str:
    if not isinstance(detail, dict) or not detail:
        return "-"
    if "accepted_rows" in detail or "rejected_rows" in detail:
        parts = []
        if detail.get("batch_id"):
            parts.append(f"Lote #{detail.get('batch_id')}")
        if "accepted_rows" in detail:
            parts.append(f"{detail.get('accepted_rows')} filas aceptadas")
        if "rejected_rows" in detail:
            parts.append(f"{detail.get('rejected_rows')} filas rechazadas")
        if detail.get("status"):
            parts.append(str(detail.get("status")).replace("_", " "))
        return ". ".join(parts) + "."
    if "rows" in detail:
        return f"Exportó {detail.get('rows')} registros."
    if "risk_level" in detail:
        model = {"ml": "modelo predictivo", "heuristica": "reglas históricas", "sin_datos": "sin datos"}.get(detail.get("model_type"), detail.get("model_type"))
        return f"Resultado: riesgo {detail.get('risk_level')}. Método: {model}."
    if "error" in detail:
        return f"Error: {detail.get('error')}"
    if "target_user_id" in detail:
        return f"Usuario afectado: #{detail.get('target_user_id')}."
    if "catalog_id" in detail:
        return f"Catálogo afectado: #{detail.get('catalog_id')}."
    if "count" in detail:
        return f"{detail.get('count')} registros incluidos."
    return "; ".join(f"{str(k).replace('_', ' ')}: {v}" for k, v in detail.items())


def _audit_view_model(record: AuditAccess, users: dict[int, User]) -> dict:
    user = users.get(record.user_id) if record.user_id else None
    return {
        "created_at": record.created_at,
        "usuario": (user.full_name or user.email) if user else "Sistema / anónimo",
        "accion": _action_label(record.action),
        "modulo": _module_label(record.path),
        "resultado": _status_label(record.status),
        "status_raw": record.status or "",
        "ip": record.ip or "-",
        "detalle": _detail_summary(record.detail_json),
    }
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
    records_view = [_audit_view_model(record, users) for record in records]
    action_options = [{"value": item, "label": _action_label(item)} for item in actions]
    status_options = [{"value": item, "label": _status_label(item)} for item in statuses]

    return templates.TemplateResponse(
        "admin/auditoria.html",
        {
            "request": request,
            "records": records,
            "records_view": records_view,
            "users": users,
            "actions": action_options,
            "statuses": status_options,
            "filters": {"action": action or "", "status": status or "", "q": q or "", "desde": desde or "", "hasta": hasta or ""},
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    )
