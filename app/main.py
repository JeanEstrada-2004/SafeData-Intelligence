# app/main.py
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import engine, get_db, quick_db_check
from .routers import denuncias as denuncias_router
from . import models, crud

# Crea tablas (no borra nada; si están creadas, no hace cambios)
models.Base.metadata.create_all(bind=engine)

# Modo debug para ver el traceback completo en el navegador
app = FastAPI(title="Sistema de Denuncias Ciudadanas", version="1.0.0", debug=True)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API router
app.include_router(denuncias_router.router, prefix="/api/denuncias", tags=["denuncias"])

# ---------------------------
# Helpers (compat & serialize)
# ---------------------------

def _compat_zonas_label(m: dict) -> dict:
    """
    Si el CRUD devuelve {1: 12, 2: 9, ...} (clave numérica de zona),
    lo convertimos a {"Zona 1": 12, "Zona 2": 9, ...}.
    Si ya viene como {'Zona 1': 12, ...}, lo dejamos igual.
    """
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
    """
    Serializa usando los CAMPOS NUEVOS del modelo para que el JS del
    listado pinte la tabla en cliente.
    """
    return {
        "id": d.id,
        "zona_denuncia": d.zona_denuncia,  # número de zona (1..7)
        "turno": d.turno,                  # 'Mañana'/'Tarde'/'Noche'
        "fecha_hora_suceso": (
            d.fecha_hora_suceso.isoformat() if d.fecha_hora_suceso else None
        ),
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
    """
    Panel. Entregamos las claves nuevas, alias de compat y stats_json para Chart.js.
    """
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
        # Alias antiguo por compatibilidad:
        "denuncias_por_distrito": _compat_zonas_label(getattr(stats, "denuncias_por_zona", {})),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats_ctx,
            "stats_json": stats.model_dump(),  # para gráficos JS
        }
    )

@app.get("/carga-denuncias", response_class=HTMLResponse)
def carga_denuncias(request: Request):
    return templates.TemplateResponse("carga_denuncias.html", {"request": request})

@app.get("/listado-denuncias", response_class=HTMLResponse)
def listado_denuncias(request: Request, db: Session = Depends(get_db)):
    """
    Render server-side SIN filas (la tabla se llena en cliente con JS).
    Enviamos además los combos ya calculados desde BD.
    """
    items = crud.listar_denuncias(db, limit=1000)
    tipos_unicos = sorted({x.tipo_denuncia for x in items if x.tipo_denuncia})
    turnos_unicos = sorted({x.turno for x in items if x.turno})

    return templates.TemplateResponse(
        "listado_denuncias.html",
        {
            "request": request,
            "denuncias": [],  # <- no pintamos filas en servidor
            "denuncias_json": [_serialize_denuncia(x) for x in items],
            "tipos_unicos": tipos_unicos,
            "turnos_unicos": turnos_unicos,
        }
    )

@app.get("/prediccion-ia", response_class=HTMLResponse)
def prediccion_ia_page(request: Request):
    zonas_disponibles = [f"Zona {i}" for i in range(1, 8)]
    return templates.TemplateResponse("prediccion-ia.html", {"request": request, "zonas": zonas_disponibles})

@app.get("/zonas", response_class=HTMLResponse)
def zonas_page(request: Request, db: Session = Depends(get_db)):
    """
    Manda tanto 'stats' (nuevo) como 'zonas_stats' (alias tipo 'Zona N')
    para que cualquier versión de plantilla funcione.
    """
    stats = crud.get_dashboard_stats(db)
    zonas_stats = _compat_zonas_label(getattr(stats, "denuncias_por_zona", {}))
    return templates.TemplateResponse(
        "zonas.html",
        {"request": request, "stats": stats, "zonas_stats": zonas_stats}
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
    return templates.TemplateResponse("mapa-calor.html", {"request": request})

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

# Dev local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
