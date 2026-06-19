"""Punto de entrada principal de la aplicaciÃ³n FastAPI."""
import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, models
from .database import engine, get_db, quick_db_check
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url
import time
from .routers import denuncias as denuncias_router
from .routers import mapa_calor as mapa_calor_router
from .routers import autenticacion as auth_router
from .routers import admin_usuarios as admin_users_router
from .routers import prediccion_ia as prediccion_router
from .routers import catalogos as catalogos_router
from .routers import auditoria as auditoria_router
from .utils.seguridad import try_get_current_user, require_roles

APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
APP_DEBUG = os.getenv("APP_DEBUG", "true" if APP_ENV != "production" else "false").lower() in {"1", "true", "yes", "y"}

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Sistema de Denuncias Ciudadanas", version="1.0.0", debug=APP_DEBUG)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def on_startup():
    max_retries = int(os.getenv("DB_STARTUP_RETRIES", "8"))
    delay = float(os.getenv("DB_STARTUP_DELAY", "1"))
    attempt = 0
    while attempt < max_retries:
        try:
            # Log minimal DB info for debugging (no credentials)
            try:
                url = make_url(os.getenv("DATABASE_URL", ""))
                logging.getLogger(__name__).info(f"Connecting to DB host={url.host} db={url.database}")
            except Exception:
                logging.getLogger(__name__).info("Connecting to DB (DATABASE_URL present)")
            # Intentar conectar y crear tablas
            with engine.connect() as conn:
                models.Base.metadata.create_all(bind=engine)
            logging.getLogger(__name__).info("DB available and tables ensured")
            return
        except OperationalError as e:
            attempt += 1
            logging.getLogger(__name__).warning(
                f"DB not ready (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s..."
            )
            time.sleep(delay)
            delay = min(delay * 2, 10)
    # Si agotamos reintentos, levantamos excepción para que la plataforma lo detecte
    logging.getLogger(__name__).error("Could not connect to DB after retries; aborting startup")
    raise RuntimeError("Database unavailable after startup retries")

# API routers
app.include_router(denuncias_router.router, prefix="/api/denuncias", tags=["denuncias"])
app.include_router(mapa_calor_router.router, prefix="/api/map", tags=["mapa-calor"])
app.include_router(prediccion_router.router, prefix="/api/prediccion", tags=["prediccion-ia"])
app.include_router(auth_router.router)
app.include_router(admin_users_router.router)
app.include_router(catalogos_router.router)
app.include_router(auditoria_router.router)

# Middleware para inyectar usuario actual en request.state (para plantillas)
@app.middleware("http")
async def inject_current_user(request, call_next):
    try:
        from .database import SessionLocal

        db = SessionLocal()
        try:
            user = try_get_current_user(request, db)
            request.state.current_user = user
        finally:
            db.close()
    except Exception:
        request.state.current_user = None
    response = await call_next(request)
    return response


@app.middleware("http")
async def same_origin_guard(request: Request, call_next):
    """Basic CSRF mitigation for cookie-authenticated unsafe requests."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get("access_token"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        expected_host = request.url.netloc
        candidate = origin or referer
        if candidate:
            from urllib.parse import urlparse

            parsed = urlparse(candidate)
            if parsed.netloc and parsed.netloc != expected_host:
                from fastapi.responses import PlainTextResponse

                return PlainTextResponse("Solicitud rechazada por validación de origen.", status_code=403)
    return await call_next(request)

# ---------------------------
# Helpers (compat & serialize)
# ---------------------------


def _compat_zonas_label(m: dict) -> dict:
    """Normaliza las claves de zonas para plantillas antiguas."""

    if not isinstance(m, dict):
        return {}
    out = {}
    for k, v in m.items():
        if isinstance(k, (int, float)) and k is not None:
            out[f"Zona {int(k)}"] = v
        else:
            out[str(k)] = v
    return out


def _serialize_denuncia(d) -> dict:
    """Serializa el modelo `Denuncia` para su uso en plantillas JS."""

    return {
        "id": d.id,
        "zona_denuncia": d.zona_denuncia,
        "turno": d.turno,
        "fecha_hora_suceso": d.fecha_hora_suceso.isoformat() if d.fecha_hora_suceso else None,
        "tipo_denuncia": d.tipo_denuncia,
        "lugar_ocurrencia": d.lugar_ocurrencia,
        "resultado_ocurrencia": d.resultado_ocurrencia,
        "sexo_victima": d.sexo_victima,
        "edad_victima": d.edad_victima,
        "comentarios": d.comentarios or "",
    }


def _parse_optional_int(value) -> int | None:
    """Acepta filtros vacíos de formularios GET sin romper validación."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------
# VISTAS HTML
# ---------------------------


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    zona: str | None = None,
    tipo: str | None = None,
    turno: str | None = None,
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    q: str | None = None,
):
    # Si no hay usuario autenticado, redirige a /login
    if not getattr(request.state, "current_user", None):
        from fastapi.responses import RedirectResponse

        return RedirectResponse("/login", status_code=302)
    """Renderiza el panel principal con estadÃ­sticas agregadas."""

    zona_id = _parse_optional_int(zona)
    stats = crud.get_dashboard_stats(db)
    tipos_all = sorted({x[0] for x in db.query(models.Denuncia.tipo_denuncia).distinct().all() if x[0]})
    turnos_all = sorted({x[0] for x in db.query(models.Denuncia.turno).distinct().all() if x[0]})
    estados_all = sorted({x[0] for x in db.query(models.Denuncia.estado_denuncia).distinct().all() if x[0]})

    stats_ctx = {
        "total_denuncias": stats.total_denuncias,
        "denuncias_por_zona": getattr(stats, "denuncias_por_zona", {}),
        "denuncias_por_turno": getattr(stats, "denuncias_por_turno", {}),
        "tipos_denuncia": getattr(stats, "tipos_denuncia", {}),
        "estados_denuncia": getattr(stats, "estados_denuncia", {}),
        "mes_actual_labels": getattr(stats, "mes_actual_labels", []),
        "mes_actual_counts": getattr(stats, "mes_actual_counts", []),
        "ult_3_meses_labels": getattr(stats, "ult_3_meses_labels", []),
        "ult_3_meses_counts": getattr(stats, "ult_3_meses_counts", []),
        "denuncias_por_distrito": _compat_zonas_label(getattr(stats, "denuncias_por_zona", {})),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats_ctx,
            "stats_json": stats.model_dump(),
            "filters": {"zona": zona_id, "tipo": tipo or "", "turno": turno or "", "estado": estado or "", "desde": desde or "", "hasta": hasta or "", "q": q or ""},
            "tipos_unicos": tipos_all,
            "turnos_unicos": turnos_all,
            "estados_unicos": estados_all,
        },
    )


@app.get("/carga-denuncias", response_class=HTMLResponse)
def carga_denuncias(request: Request, _auth=Depends(require_roles("Gerente", "EncargadoSipCop"))):
    return templates.TemplateResponse("carga_denuncias.html", {"request": request})


@app.get("/listado-denuncias", response_class=HTMLResponse)
def listado_denuncias(
    request: Request,
    db: Session = Depends(get_db),
    zona: str | None = None,
    tipo: str | None = None,
    turno: str | None = None,
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    q: str | None = None,
    page: int = 1,
    _auth=Depends(require_roles("Gerente", "JefeOperaciones", "EncargadoSipCop")),
):
    """Listado server-side con filtros y paginación."""

    per_page = 15
    page = max(1, int(page or 1))
    zona_id = _parse_optional_int(zona)
    filters = {"zona": zona_id, "tipo": tipo or None, "turno": turno or None, "estado": estado or None, "desde": desde or None, "hasta": hasta or None, "q": q or None}
    total = crud.contar_denuncias(db, **filters)
    items = crud.listar_denuncias(db, limit=per_page, offset=(page - 1) * per_page, **filters)
    tipos_unicos = sorted({x.tipo_denuncia for x in items if x.tipo_denuncia})
    turnos_unicos = sorted({x.turno for x in items if x.turno})
    estados_unicos = sorted({x.estado_denuncia for x in db.query(models.Denuncia.estado_denuncia).distinct().all() if x.estado_denuncia})
    tipos_all = sorted({x.tipo_denuncia for x in db.query(models.Denuncia.tipo_denuncia).distinct().all() if x.tipo_denuncia})
    turnos_all = sorted({x.turno for x in db.query(models.Denuncia.turno).distinct().all() if x.turno})

    return templates.TemplateResponse(
        "listado_denuncias.html",
        {
            "request": request,
            "denuncias": items,
            "denuncias_json": [_serialize_denuncia(x) for x in items],
            "tipos_unicos": tipos_all or tipos_unicos,
            "turnos_unicos": turnos_all or turnos_unicos,
            "estados_unicos": estados_unicos,
            "filters": filters,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    )


@app.get("/prediccion-ia", response_class=HTMLResponse)
def prediccion_ia_page(request: Request, _auth=Depends(require_roles("Gerente", "JefeOperaciones", "Analista"))):
    zonas_disponibles = list(range(1, 8))  # Zonas del 1 al 7
    return templates.TemplateResponse("prediccion-ia.html", {"request": request, "zonas": zonas_disponibles})


@app.get("/zonas", response_class=HTMLResponse)
def zonas_page(request: Request, db: Session = Depends(get_db), _auth=Depends(require_roles("Gerente", "JefeOperaciones", "Analista"))):
    """Renderiza estadÃ­sticas resumidas por zona."""

    stats = crud.get_dashboard_stats(db)
    zonas_stats = _compat_zonas_label(getattr(stats, "denuncias_por_zona", {}))
    return templates.TemplateResponse(
        "zonas.html",
        {"request": request, "stats": stats, "zonas_stats": zonas_stats},
    )


@app.get("/horarios", response_class=HTMLResponse)
def horarios_page(request: Request, _auth=Depends(require_roles("Gerente", "JefeOperaciones", "Analista"))):
    horarios_stats = [
        {"label": "00:00 - 06:00", "denuncias": 5},
        {"label": "06:00 - 12:00", "denuncias": 11},
        {"label": "12:00 - 18:00", "denuncias": 18},
        {"label": "18:00 - 24:00", "denuncias": 14},
    ]
    return templates.TemplateResponse("horarios.html", {"request": request, "horarios_stats": horarios_stats})


@app.get("/mapa-calor", response_class=HTMLResponse)
def mapa_calor_page(request: Request, _auth=Depends(require_roles("Gerente", "JefeOperaciones", "Analista", "EncargadoSipCop"))):
    return templates.TemplateResponse(
        "mapa_calor.html",
        {
            "request": request,
            "mapbox_token": os.getenv("MAPBOX_ACCESS_TOKEN", "").strip(),
        },
    )


# ---------------------------
# Endpoints de diagnÃ³stico
# ---------------------------


@app.get("/health")
def health():
    """Healthcheck público mínimo, sin detalles sensibles."""

    return {"ok": True, "app": "SafeData Intelligence", "version": app.version}


@app.get("/health/db")
def health_db(_auth=Depends(require_roles("Gerente", "AdministradorTecnico", "OTICS"))):
    """ConexiÃ³n directa al motor (sin sesión) + COUNT(*)."""

    info = quick_db_check()
    return {"ok": True, **info}


@app.get("/health/stats")
def health_stats(db: Session = Depends(get_db), _auth=Depends(require_roles("Gerente", "AdministradorTecnico", "OTICS"))):
    """Verifica que el CRUD de estadÃ­sticas funciona con las columnas NUEVAS."""

    s = crud.get_dashboard_stats(db)
    last_upload = db.query(models.UploadBatch).order_by(models.UploadBatch.uploaded_at.desc()).first()
    backup_dir = Path(os.getenv("BACKUP_DIR", "backups"))
    latest_backup = None
    if backup_dir.exists():
        backups = sorted(backup_dir.glob("safedata_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            latest_backup = {"file": backups[0].name, "updated_at": backups[0].stat().st_mtime}
    return {
        "ok": True,
        "version": app.version,
        "total": s.total_denuncias,
        "zonas": getattr(s, "denuncias_por_zona", {}),
        "turnos": getattr(s, "denuncias_por_turno", {}),
        "tipos": getattr(s, "tipos_denuncia", {}),
        "estados": getattr(s, "estados_denuncia", {}),
        "ultima_carga": {
            "id": last_upload.id,
            "uploaded_at": last_upload.uploaded_at.isoformat() if last_upload.uploaded_at else None,
            "status": last_upload.status,
            "accepted_rows": last_upload.accepted_rows,
            "rejected_rows": last_upload.rejected_rows,
        } if last_upload else None,
        "ultimo_backup": latest_backup,
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
