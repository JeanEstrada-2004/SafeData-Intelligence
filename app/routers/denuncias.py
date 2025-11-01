# app/routers/denuncias.py
from __future__ import annotations
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import math
import pandas as pd

from .. import crud, schemas
from ..database import get_db

router = APIRouter()


# =========================
#  Utilidades de parseo
# =========================
def _parse_dt(v) -> datetime:
    """
    Convierte valores de fecha/hora (str, numpy, pandas, datetime) a datetime.
    Espera formatos tipo 'YYYY-MM-DD HH:MM[:SS]'.
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise ValueError("Campo de fecha/hora requerido")
    try:
        if isinstance(v, datetime):
            return v
        return pd.to_datetime(v)  # pandas se encarga de strings y timestamps
    except Exception:
        raise ValueError(f"Fecha/hora inválida: {v}")

def _opt_str(v) -> Optional[str]:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip()
    return s if s else None

def _req_str(v, field: str) -> str:
    s = _opt_str(v)
    if not s:
        raise ValueError(f"{field} es requerido")
    return s

def _req_int(v, field: str) -> int:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise ValueError(f"{field} es requerido")
    try:
        return int(v)
    except Exception:
        raise ValueError(f"{field} inválido: {v}")


# =========================
#  Carga desde Excel/CSV
# (opcional: si decides cargar desde la app además de DBeaver)
# =========================
@router.post("/upload-excel/", response_model=dict)
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    name = file.filename.lower()
    if not (name.endswith(".xlsx") or name.endswith(".xls") or name.endswith(".csv")):
        raise HTTPException(400, "Formato no soportado. Sube .xlsx/.xls/.csv")

    # Guardar temporalmente
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    tmp_path = os.path.join(upload_dir, file.filename)

    with open(tmp_path, "wb") as fh:
        fh.write(await file.read())

    try:
        if name.endswith(".csv"):
            # Detecta automáticamente separador , o ;
            # (Si sabes que siempre será ; cambia sep=';')
            df = pd.read_csv(tmp_path, sep=None, engine="python")
        else:
            df = pd.read_excel(tmp_path)

        # Columnas requeridas del nuevo layout
        required = [
            "numero_parte", "estado_denuncia", "zona_denuncia",
            "origen_denuncia", "naturaleza_personal", "forma_patrullaje",
            "turno", "fecha_hora_suceso", "fecha_hora_alerta",
            "fecha_hora_llegada", "edad_victima", "sexo_victima",
            "distrito_victima"
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise HTTPException(400, f"Columnas faltantes: {', '.join(missing)}")

        items: List[schemas.DenunciaCreate] = []
        for i, row in df.iterrows():
            try:
                zona = _req_int(row["zona_denuncia"], "zona_denuncia")
                if not (1 <= zona <= 7):
                    raise ValueError("zona_denuncia fuera de rango (1..7)")

                item = schemas.DenunciaCreate(
                    numero_parte=_req_str(row["numero_parte"], "numero_parte"),
                    estado_denuncia=_req_str(row["estado_denuncia"], "estado_denuncia"),
                    zona_denuncia=zona,
                    origen_denuncia=_req_str(row["origen_denuncia"], "origen_denuncia"),
                    naturaleza_personal=_req_str(row["naturaleza_personal"], "naturaleza_personal"),
                    forma_patrullaje=_req_str(row["forma_patrullaje"], "forma_patrullaje"),
                    turno=_req_str(row["turno"], "turno"),
                    fecha_hora_suceso=_parse_dt(row["fecha_hora_suceso"]),
                    fecha_hora_alerta=_parse_dt(row["fecha_hora_alerta"]),
                    fecha_hora_llegada=_parse_dt(row["fecha_hora_llegada"]),
                    edad_victima=_req_int(row["edad_victima"], "edad_victima"),
                    sexo_victima=_req_str(row["sexo_victima"], "sexo_victima"),
                    distrito_victima=_req_str(row["distrito_victima"], "distrito_victima"),
                    sexo_victimario=_opt_str(row.get("sexo_victimario")),
                    relacion_victima_victimario=_opt_str(row.get("relacion_victima_victimario")),
                    tipo_denuncia=_opt_str(row.get("tipo_denuncia")),
                    arma_instrumento=_opt_str(row.get("arma_instrumento")),
                    resultado_ocurrencia=_opt_str(row.get("resultado_ocurrencia")),
                    lugar_ocurrencia=_opt_str(row.get("lugar_ocurrencia")),
                    direccion_ocurrencia=_opt_str(row.get("direccion_ocurrencia")),
                    comentarios=_opt_str(row.get("comentarios")),
                )
                items.append(item)
            except Exception as e:
                raise HTTPException(400, f"Error en fila {i+2}: {e}")  # +2 por encabezado base 1

        inserted = crud.create_denuncias_bulk(db, items)

        return {"message": f"Se cargaron {inserted} denuncias exitosamente", "denuncias_procesadas": inserted}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error procesando archivo: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# =========================
#  Endpoints de lectura
# =========================
@router.get("/", response_model=List[schemas.DenunciaResponse])
def listar(
    zona: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    turno: Optional[str] = Query(None),
    desde: Optional[str] = Query(None, description="YYYY-MM-DD o YYYY-MM-DD HH:MM:SS"),
    hasta: Optional[str] = Query(None, description="YYYY-MM-DD o YYYY-MM-DD HH:MM:SS"),
    q: Optional[str] = Query(None, description="Búsqueda libre en texto"),
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    return crud.listar_denuncias(
        db,
        zona=zona, tipo=tipo, turno=turno,
        desde=desde, hasta=hasta, q=q,
        limit=limit,
    )

@router.get("/stats/", response_model=schemas.DashboardStats)
def stats(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)
