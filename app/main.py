"""Punto de entrada principal de la aplicación FastAPI."""
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, models
from .database import engine, get_db, quick_db_check
from .routers import denuncias as denuncias_router
from .routers import mapa_calor as mapa_calor_router
from .routers import auth as auth_router
from .routers import admin_users as admin_users_router
from .utils.security import try_get_current_user

# Crea tablas (no borra nada; si están creadas, no hace cambios)
models.Base.metadata.create_all(bind=engine)

# Modo debug para ver el traceback completo en el navegador
app = FastAPI(title="Sistema de Denuncias Ciudadanas", version="1.0.0", debug=True)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API routers
app.include_router(denuncias_router.router, prefix="/api/denuncias", tags=["denuncias"])
app.include_router(mapa_calor_router.router, prefix="/api/map", tags=["mapa-calor"])
app.include_router(auth_router.router)
app.include_router(admin_users_router.router)

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


# ---------------------------
# VISTAS HTML
# ---------------------------


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    # Si no hay usuario autenticado, redirige a /login
    if not getattr(request.state, "current_user", None):
        from fastapi.responses import RedirectResponse

        return RedirectResponse("/login", status_code=302)
    """Renderiza el panel principal con estadísticas agregadas."""

    stats = crud.get_dashboard_stats(db)

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
        {"request": request, "stats": stats_ctx, "stats_json": stats.model_dump()},
    )


@app.get("/carga-denuncias", response_class=HTMLResponse)
def carga_denuncias(request: Request):
    return templates.TemplateResponse("carga_denuncias.html", {"request": request})


@app.get("/listado-denuncias", response_class=HTMLResponse)
def listado_denuncias(request: Request, db: Session = Depends(get_db)):
    """Página de listado que delega la renderización de filas al navegador."""

    items = crud.listar_denuncias(db, limit=1000)
    tipos_unicos = sorted({x.tipo_denuncia for x in items if x.tipo_denuncia})
    turnos_unicos = sorted({x.turno for x in items if x.turno})

    return templates.TemplateResponse(
        "listado_denuncias.html",
        {
            "request": request,
            "denuncias": [],
            "denuncias_json": [_serialize_denuncia(x) for x in items],
            "tipos_unicos": tipos_unicos,
            "turnos_unicos": turnos_unicos,
        },
    )


@app.get("/prediccion-ia", response_class=HTMLResponse)
def prediccion_ia_page(request: Request):
    zonas_disponibles = [f"Zona {i}" for i in range(1, 8)]
    return templates.TemplateResponse("prediccion-ia.html", {"request": request, "zonas": zonas_disponibles})


@app.get("/zonas", response_class=HTMLResponse)
def zonas_page(request: Request, db: Session = Depends(get_db)):
    """Renderiza estadísticas resumidas por zona."""

    stats = crud.get_dashboard_stats(db)
    zonas_stats = _compat_zonas_label(getattr(stats, "denuncias_por_zona", {}))
    return templates.TemplateResponse(
        "zonas.html",
        {"request": request, "stats": stats, "zonas_stats": zonas_stats},
    )


@app.get("/horarios", response_class=HTMLResponse)
def horarios_page(request: Request):
    horarios_stats = [
        {"label": "00:00 - 06:00", "denuncias": 5},
        {"label": "06:00 - 12:00", "denuncias": 11},
        {"label": "12:00 - 18:00", "denuncias": 18},
        {"label": "18:00 - 24:00", "denuncias": 14},
    ]
    return templates.TemplateResponse("horarios.html", {"request": request, "horarios_stats": horarios_stats})


@app.get("/mapa-calor", response_class=HTMLResponse)
def mapa_calor_page(request: Request):
    return templates.TemplateResponse("mapa_calor.html", {"request": request})


# ---------------------------
# Endpoints de diagnóstico
# ---------------------------


@app.get("/health/db")
def health_db():
    """Conexión directa al motor (sin sesión) + COUNT(*)."""

    info = quick_db_check()
    return {"ok": True, **info}


@app.get("/health/stats")
def health_stats(db: Session = Depends(get_db)):
    """Verifica que el CRUD de estadísticas funciona con las columnas NUEVAS."""

    s = crud.get_dashboard_stats(db)
    return {
        "ok": True,
        "total": s.total_denuncias,
        "zonas": getattr(s, "denuncias_por_zona", {}),
        "turnos": getattr(s, "denuncias_por_turno", {}),
        "tipos": getattr(s, "tipos_denuncia", {}),
        "estados": getattr(s, "estados_denuncia", {}),
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
