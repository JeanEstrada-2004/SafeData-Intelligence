# app/routers/denuncias.py
from __future__ import annotations
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import math
import pandas as pd

from .. import models  # <- usamos el modelo directamente
from ..database import get_db

router = APIRouter()

# =========================
#  Utilidades de parseo
# =========================
def _parse_dt(v) -> datetime:
    """
    Convierte valores de fecha/hora (str, numpy, pandas, datetime) a datetime.
    Acepta formatos comunes: 'DD/MM/YYYY HH:MM', ISO, etc. (dayfirst=True).
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise ValueError("Campo de fecha/hora requerido")
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="raise")
        return dt.to_pydatetime() if hasattr(dt, "to_pydatetime") else dt
    except Exception:
        pass
    try:
        dt = pd.to_datetime(s, errors="raise")
        return dt.to_pydatetime() if hasattr(dt, "to_pydatetime") else dt
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

def _gen_numero_parte(prefix: str, fecha: datetime, sec: int) -> str:
    # PAR-YYYYMMDD-#### (máx 30 chars)
    return f"{prefix}-{fecha.strftime('%Y%m%d')}-{sec:04d}"[:30]

# =========================
#  Carga desde Excel/CSV
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
            df = pd.read_csv(tmp_path, sep=None, engine="python")
        else:
            df = pd.read_excel(tmp_path)

        # Normaliza encabezados (trim)
        df.columns = [str(c).strip() for c in df.columns]

        # Columnas del layout ACTUAL (21)
        required = [
            "numero_parte", "estado_denuncia", "zona_denuncia",
            "origen_denuncia", "naturaleza_personal", "forma_patrullaje",
            "turno", "fecha_hora_suceso", "fecha_hora_alerta",
            "fecha_hora_llegada", "edad_victima", "sexo_victima",
            "distrito_victima", "sexo_victimario", "relacion_victima_victimario",
            "tipo_denuncia", "arma_instrumento", "resultado_ocurrencia",
            "lugar_ocurrencia", "direccion_ocurrencia", "comentarios"
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise HTTPException(400, f"Columnas faltantes: {', '.join(missing)}")

        # Construimos modelos directamente
        objetos: List[models.Denuncia] = []
        hoy = datetime.now()
        for i, row in df.iterrows():
            try:
                # zona_denuncia: entero 1..7
                zona = _req_int(row["zona_denuncia"], "zona_denuncia")
                if not (1 <= zona <= 7):
                    raise ValueError("zona_denuncia fuera de rango (1..7)")

                # fecha para componer numero_parte si falta
                fecha_suceso = _parse_dt(row["fecha_hora_suceso"])

                # numero_parte (si falta, se genera)
                numero_parte = _opt_str(row["numero_parte"])
                if not numero_parte:
                    numero_parte = _gen_numero_parte("PAR", fecha_suceso or hoy, i + 1)

                # estado_denuncia (default si falta)
                estado_denuncia = _opt_str(row["estado_denuncia"]) or "Registrada"

                obj = models.Denuncia(
                    numero_parte=numero_parte,
                    estado_denuncia=estado_denuncia,
                    zona_denuncia=zona,
                    origen_denuncia=_opt_str(row["origen_denuncia"]),
                    naturaleza_personal=_opt_str(row["naturaleza_personal"]),
                    forma_patrullaje=_opt_str(row["forma_patrullaje"]),
                    turno=_opt_str(row["turno"]),
                    fecha_hora_suceso=fecha_suceso,
                    fecha_hora_alerta=_opt_str(row["fecha_hora_alerta"]) and _parse_dt(row["fecha_hora_alerta"]),
                    fecha_hora_llegada=_opt_str(row["fecha_hora_llegada"]) and _parse_dt(row["fecha_hora_llegada"]),
                    edad_victima=_opt_str(row["edad_victima"]) and _req_int(row["edad_victima"], "edad_victima"),
                    sexo_victima=_opt_str(row["sexo_victima"]),
                    distrito_victima=_opt_str(row["distrito_victima"]),
                    sexo_victimario=_opt_str(row["sexo_victimario"]),
                    relacion_victima_victimario=_opt_str(row["relacion_victima_victimario"]),
                    tipo_denuncia=_opt_str(row["tipo_denuncia"]),
                    arma_instrumento=_opt_str(row["arma_instrumento"]),
                    resultado_ocurrencia=_opt_str(row["resultado_ocurrencia"]),
                    lugar_ocurrencia=_opt_str(row["lugar_ocurrencia"]),
                    direccion_ocurrencia=_opt_str(row["direccion_ocurrencia"]),
                    comentarios=_opt_str(row["comentarios"]),
                    # Campos de geocodificación quedan en None (los completa el job de geocoding)
                )
                objetos.append(obj)
            except Exception as e:
                # +2 por encabezado y base 1 de Excel
                raise HTTPException(400, f"Error en fila {i+2}: {e}")

        # Inserción directa
        if objetos:
            db.bulk_save_objects(objetos)
            db.commit()

        return {"message": f"Se cargaron {len(objetos)} denuncias exitosamente", "denuncias_procesadas": len(objetos)}

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
#  Endpoints de lectura (sin cambios)
# =========================
@router.get("/", response_model=List[dict])
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
    # si ya tenías schemas.DenunciaResponse, puedes dejar tu versión original
    from .. import crud, schemas
    return crud.listar_denuncias(
        db,
        zona=zona, tipo=tipo, turno=turno,
        desde=desde, hasta=hasta, q=q,
        limit=limit,
    )

@router.get("/stats/", response_model=dict)
def stats(db: Session = Depends(get_db)):
    from .. import crud, schemas
    return crud.get_dashboard_stats(db)










# ======== DASHBOARD AVANZADO ========
@router.get("/stats-advanced", response_model=dict)
def stats_advanced(db: Session = Depends(get_db)):
    from ..crud import get_advanced_dashboard_stats
    return get_advanced_dashboard_stats(db)


# ======== FIN DASHBOARD AVANZADO ========