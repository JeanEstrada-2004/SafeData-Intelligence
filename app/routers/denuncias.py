# app/routers/denuncias.py
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import crud, models
from ..database import get_db
from ..models import CatalogItem, Denuncia, UploadBatch, UploadError, User
from ..utils.seguridad import audit_event, require_roles

router = APIRouter()

UPLOAD_ROLES = ("Gerente", "EncargadoSipCop")
READ_ROLES = ("Gerente", "JefeOperaciones", "EncargadoSipCop", "Analista")

REQUIRED_COLUMNS = [
    "numero_parte",
    "estado_denuncia",
    "zona_denuncia",
    "origen_denuncia",
    "naturaleza_personal",
    "forma_patrullaje",
    "turno",
    "fecha_hora_suceso",
    "fecha_hora_alerta",
    "fecha_hora_llegada",
    "edad_victima",
    "sexo_victima",
    "distrito_victima",
    "sexo_victimario",
    "relacion_victima_victimario",
    "tipo_denuncia",
    "arma_instrumento",
    "resultado_ocurrencia",
    "lugar_ocurrencia",
    "direccion_ocurrencia",
    "comentarios",
]

TEXT_COLUMNS = [
    "numero_parte",
    "estado_denuncia",
    "origen_denuncia",
    "naturaleza_personal",
    "forma_patrullaje",
    "turno",
    "sexo_victima",
    "distrito_victima",
    "sexo_victimario",
    "relacion_victima_victimario",
    "tipo_denuncia",
    "arma_instrumento",
    "resultado_ocurrencia",
    "lugar_ocurrencia",
    "direccion_ocurrencia",
    "comentarios",
]


def _safe_filename(filename: str) -> str:
    stem = Path(filename or "archivo").name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", stem)[:140]


def _source_type(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".csv"):
        return "CSV"
    if name.endswith((".xlsx", ".xls")):
        return "Excel"
    raise HTTPException(400, "Formato no soportado. Sube .xlsx/.xls/.csv")


def _parse_dt(v) -> datetime:
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
    except Exception as exc:
        raise ValueError(f"Fecha/hora inválida: {v}") from exc


def _parse_optional_dt(v):
    if _is_empty(v):
        return None
    return _parse_dt(v)


def _is_empty(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == ""


def _normalize_text(v) -> Optional[str]:
    if _is_empty(v):
        return None
    s = re.sub(r"\s+", " ", str(v).strip())
    return s or None


def _normalize_title(v) -> Optional[str]:
    s = _normalize_text(v)
    if not s:
        return None
    lowered = s.lower()
    if lowered in {"mañana", "manana"}:
        return "Mañana"
    return lowered[:1].upper() + lowered[1:]


def _parse_int(v, field: str) -> int:
    if _is_empty(v):
        raise ValueError(f"{field} es requerido")
    try:
        return int(v)
    except Exception as exc:
        raise ValueError(f"{field} inválido: {v}") from exc


def _catalog_map(db: Session, category: str, fallback: List[str]) -> Dict[str, str]:
    rows = (
        db.query(CatalogItem)
        .filter(CatalogItem.category == category, CatalogItem.is_active.is_(True))
        .order_by(CatalogItem.name)
        .all()
    )
    values = [r.name for r in rows] or fallback
    return {v.strip().lower(): v for v in values if v}


def _add_issue(issues: List[dict], row_number: int, column: Optional[str], raw_value, error_type: str, message: str, severity: str = "error"):
    issues.append(
        {
            "row_number": row_number,
            "column_name": column,
            "raw_value": "" if raw_value is None else str(raw_value)[:500],
            "error_type": error_type,
            "error_message": message,
            "severity": severity,
        }
    )


def _row_hash(row: Dict[str, Any]) -> str:
    material = {k: ("" if row.get(k) is None else str(row.get(k)).strip()) for k in REQUIRED_COLUMNS}
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _serialize_denuncia(d: Denuncia) -> dict:
    return {
        "id": d.id,
        "numero_parte": d.numero_parte,
        "estado_denuncia": d.estado_denuncia,
        "zona_denuncia": d.zona_denuncia,
        "turno": d.turno,
        "fecha_hora_suceso": d.fecha_hora_suceso.isoformat() if d.fecha_hora_suceso else None,
        "tipo_denuncia": d.tipo_denuncia,
        "lugar_ocurrencia": d.lugar_ocurrencia,
        "resultado_ocurrencia": d.resultado_ocurrencia,
        "sexo_victima": d.sexo_victima,
        "edad_victima": d.edad_victima,
        "direccion_ocurrencia": d.direccion_ocurrencia,
        "comentarios": d.comentarios or "",
        "source_file": d.source_file,
        "upload_batch_id": d.upload_batch_id,
        "latitud": d.latitud,
        "longitud": d.longitud,
        "geocode_status": d.geocode_status,
        "geocode_precision": d.geocode_precision,
    }


def _validate_and_build(row: Dict[str, Any], row_number: int, db: Session, batch: UploadBatch) -> tuple[Optional[Denuncia], List[dict]]:
    issues: List[dict] = []
    normalized = dict(row)
    for col in TEXT_COLUMNS:
        normalized[col] = _normalize_text(row.get(col))

    turno_map = _catalog_map(db, "turno", ["Mañana", "Tarde", "Noche"])
    estado_map = _catalog_map(db, "estado", ["Registrada", "Atendido", "Archivado", "Derivado"])
    tipo_map = _catalog_map(db, "tipo_incidencia", [])

    try:
        zona = _parse_int(row.get("zona_denuncia"), "zona_denuncia")
        if not db.get(models.Zona, zona):
            _add_issue(issues, row_number, "zona_denuncia", row.get("zona_denuncia"), "zona_invalida", "La zona no existe en el catálogo de zonas.")
    except ValueError as exc:
        zona = None
        _add_issue(issues, row_number, "zona_denuncia", row.get("zona_denuncia"), "zona_invalida", str(exc))

    try:
        fecha_suceso = _parse_dt(row.get("fecha_hora_suceso"))
    except ValueError as exc:
        fecha_suceso = None
        _add_issue(issues, row_number, "fecha_hora_suceso", row.get("fecha_hora_suceso"), "fecha_invalida", str(exc))

    fecha_alerta = None
    fecha_llegada = None
    for col in ("fecha_hora_alerta", "fecha_hora_llegada"):
        try:
            parsed = _parse_optional_dt(row.get(col))
            if col == "fecha_hora_alerta":
                fecha_alerta = parsed
            else:
                fecha_llegada = parsed
        except ValueError as exc:
            _add_issue(issues, row_number, col, row.get(col), "fecha_invalida", str(exc))

    turno_raw = normalized.get("turno")
    turno = turno_map.get((turno_raw or "").lower())
    if not turno:
        _add_issue(issues, row_number, "turno", row.get("turno"), "turno_invalido", "Turno inválido. Usa Mañana, Tarde o Noche.")

    estado_raw = normalized.get("estado_denuncia") or "Registrada"
    estado = estado_map.get(estado_raw.lower(), _normalize_title(estado_raw))
    if estado_raw.lower() not in estado_map:
        _add_issue(issues, row_number, "estado_denuncia", row.get("estado_denuncia"), "estado_no_catalogado", "Estado no encontrado en catálogo; se guardará normalizado.", "warning")

    tipo_raw = normalized.get("tipo_denuncia")
    tipo = tipo_map.get((tipo_raw or "").lower(), _normalize_title(tipo_raw))
    if not tipo:
        _add_issue(issues, row_number, "tipo_denuncia", row.get("tipo_denuncia"), "tipo_requerido", "Tipo de incidencia requerido.")
    elif tipo_map and (tipo_raw or "").lower() not in tipo_map:
        _add_issue(issues, row_number, "tipo_denuncia", row.get("tipo_denuncia"), "tipo_no_catalogado", "Tipo no encontrado en catálogo; se guardará normalizado.", "warning")

    edad = None
    if not _is_empty(row.get("edad_victima")):
        try:
            edad = _parse_int(row.get("edad_victima"), "edad_victima")
            max_age = int(os.getenv("MAX_EDAD_VICTIMA", "110"))
            if edad < 0 or edad > max_age:
                _add_issue(issues, row_number, "edad_victima", row.get("edad_victima"), "edad_fuera_rango", f"Edad fuera de rango permitido 0-{max_age}.")
        except ValueError as exc:
            _add_issue(issues, row_number, "edad_victima", row.get("edad_victima"), "edad_invalida", str(exc))

    raw_hash = _row_hash(normalized)
    if db.query(Denuncia.id).filter(Denuncia.raw_row_hash == raw_hash).first():
        _add_issue(issues, row_number, None, raw_hash, "duplicado_hash", "La fila ya existe en el sistema por hash.")

    numero_parte = normalized.get("numero_parte")
    if fecha_suceso and tipo:
        dup_q = db.query(Denuncia.id).filter(Denuncia.fecha_hora_suceso == fecha_suceso, Denuncia.tipo_denuncia == tipo)
        if numero_parte:
            dup_q = dup_q.filter(Denuncia.numero_parte == numero_parte)
        if dup_q.first():
            _add_issue(issues, row_number, "numero_parte", numero_parte, "duplicado_operativo", "Registro duplicado por número de parte, fecha/hora y tipo.")

    if not normalized.get("lugar_ocurrencia") and not normalized.get("direccion_ocurrencia"):
        _add_issue(issues, row_number, "lugar_ocurrencia", "", "ubicacion_incompleta", "Debe existir lugar o dirección de ocurrencia.")

    has_error = any(issue["severity"] == "error" for issue in issues)
    if has_error or zona is None or fecha_suceso is None:
        return None, issues

    if not numero_parte:
        numero_parte = f"PAR-{fecha_suceso.strftime('%Y%m%d')}-{row_number:04d}"[:30]

    denuncia = Denuncia(
        numero_parte=numero_parte,
        estado_denuncia=estado,
        zona_denuncia=zona,
        origen_denuncia=_normalize_title(normalized.get("origen_denuncia")),
        naturaleza_personal=_normalize_title(normalized.get("naturaleza_personal")),
        forma_patrullaje=_normalize_title(normalized.get("forma_patrullaje")),
        turno=turno,
        fecha_hora_suceso=fecha_suceso,
        fecha_hora_alerta=fecha_alerta,
        fecha_hora_llegada=fecha_llegada,
        edad_victima=edad,
        sexo_victima=_normalize_title(normalized.get("sexo_victima")),
        distrito_victima=_normalize_title(normalized.get("distrito_victima")),
        sexo_victimario=_normalize_title(normalized.get("sexo_victimario")),
        relacion_victima_victimario=_normalize_title(normalized.get("relacion_victima_victimario")),
        tipo_denuncia=tipo,
        arma_instrumento=_normalize_title(normalized.get("arma_instrumento")),
        resultado_ocurrencia=_normalize_title(normalized.get("resultado_ocurrencia")),
        lugar_ocurrencia=_normalize_title(normalized.get("lugar_ocurrencia")),
        direccion_ocurrencia=normalized.get("direccion_ocurrencia"),
        comentarios=normalized.get("comentarios"),
        source_file=batch.original_filename,
        raw_row_hash=raw_hash,
        upload_batch_id=batch.id,
    )

    try:
        from ..services.enrich import enrich_denuncia_input

        enriched = enrich_denuncia_input(
            {
                "direccion_ocurrencia": denuncia.direccion_ocurrencia,
                "tipo_denuncia": denuncia.tipo_denuncia,
                "resultado_ocurrencia": denuncia.resultado_ocurrencia,
                "fecha_hora_suceso": denuncia.fecha_hora_suceso,
            },
            db,
        )
        denuncia.latitud = enriched.get("latitud")
        denuncia.longitud = enriched.get("longitud")
        denuncia.geocode_precision = enriched.get("geocode_precision")
        denuncia.geo_method = enriched.get("geo_method")
        denuncia.geocoded_at = enriched.get("geocoded_at")
        denuncia.peso = enriched.get("peso")
        if denuncia.latitud is not None and denuncia.longitud is not None:
            denuncia.geocode_status = "approx" if denuncia.geocode_precision == "centroid" else "ok"
    except Exception as exc:
        _add_issue(issues, row_number, "direccion_ocurrencia", denuncia.direccion_ocurrencia, "geocoding_warning", f"No se pudo geocodificar: {exc}", "warning")

    return denuncia, issues


def _persist_issues(db: Session, batch_id: int, issues: List[dict]) -> None:
    for issue in issues:
        db.add(UploadError(batch_id=batch_id, **issue))


@router.post("/upload-excel/", response_model=dict)
async def upload_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*UPLOAD_ROLES)),
):
    started = time.perf_counter()
    source_type = _source_type(file.filename or "")
    content = await file.read()
    if not content:
        raise HTTPException(400, "El archivo está vacío.")

    file_hash = hashlib.sha256(content).hexdigest()
    safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{_safe_filename(file.filename or 'archivo')}"
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / safe_name
    tmp_path.write_bytes(content)

    batch = UploadBatch(
        filename=safe_name,
        original_filename=file.filename or safe_name,
        uploaded_by_user_id=user.id,
        total_rows=0,
        accepted_rows=0,
        rejected_rows=0,
        status="error",
        source_type=source_type,
        file_hash=file_hash,
        message="Procesando archivo",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    try:
        if source_type == "CSV":
            df = pd.read_csv(tmp_path, sep=None, engine="python")
        else:
            df = pd.read_excel(tmp_path)
        df.columns = [str(c).strip() for c in df.columns]

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            issues = [
                {
                    "row_number": 1,
                    "column_name": col,
                    "raw_value": "",
                    "error_type": "columna_faltante",
                    "error_message": f"Columna obligatoria faltante: {col}",
                    "severity": "error",
                }
                for col in missing
            ]
            _persist_issues(db, batch.id, issues)
            batch.total_rows = int(len(df))
            batch.rejected_rows = int(len(df))
            batch.status = "rechazado"
            batch.message = "El archivo no cumple con el formato requerido."
            batch.processing_time_ms = int((time.perf_counter() - started) * 1000)
            db.add(batch)
            db.commit()
            audit_event(db, request, "upload_rejected", user=user, detail={"batch_id": batch.id, "missing": missing})
            return {
                "message": batch.message,
                "batch_id": batch.id,
                "total_rows": batch.total_rows,
                "accepted_rows": 0,
                "rejected_rows": batch.rejected_rows,
                "errors_url": f"/api/denuncias/uploads/{batch.id}/errors",
            }

        accepted: List[Denuncia] = []
        issues_all: List[dict] = []
        rejected_rows = 0
        for i, row in df.iterrows():
            row_number = int(i) + 2
            row_dict = row.to_dict()
            obj, issues = _validate_and_build(row_dict, row_number, db, batch)
            issues_all.extend(issues)
            if obj is None:
                rejected_rows += 1
            else:
                accepted.append(obj)

        if accepted:
            db.add_all(accepted)
        _persist_issues(db, batch.id, issues_all)
        batch.total_rows = int(len(df))
        batch.accepted_rows = len(accepted)
        batch.rejected_rows = rejected_rows
        if rejected_rows and accepted:
            batch.status = "procesado_con_observaciones"
        elif rejected_rows and not accepted:
            batch.status = "rechazado"
        else:
            batch.status = "procesado"
        warning_count = sum(1 for issue in issues_all if issue["severity"] == "warning")
        batch.message = f"Carga finalizada: {len(accepted)} aceptadas, {rejected_rows} rechazadas, {warning_count} advertencias."
        batch.processing_time_ms = int((time.perf_counter() - started) * 1000)
        db.add(batch)
        db.commit()

        audit_event(
            db,
            request,
            "upload_processed",
            user=user,
            detail={
                "batch_id": batch.id,
                "status": batch.status,
                "accepted_rows": batch.accepted_rows,
                "rejected_rows": batch.rejected_rows,
            },
        )
        return {
            "message": batch.message,
            "batch_id": batch.id,
            "total_rows": batch.total_rows,
            "accepted_rows": batch.accepted_rows,
            "rejected_rows": batch.rejected_rows,
            "status": batch.status,
            "errors_url": f"/api/denuncias/uploads/{batch.id}/errors",
            "errors_csv_url": f"/api/denuncias/uploads/{batch.id}/errors.csv",
            "errors_excel_url": f"/api/denuncias/uploads/{batch.id}/errors.xlsx",
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        batch = db.get(UploadBatch, batch.id)
        if batch:
            batch.status = "error"
            batch.message = f"Error procesando archivo: {exc}"
            batch.processing_time_ms = int((time.perf_counter() - started) * 1000)
            db.add(batch)
            db.commit()
        audit_event(db, request, "upload_error", user=user, status="error", detail={"batch_id": getattr(batch, "id", None), "error": str(exc)})
        raise HTTPException(500, f"Error procesando archivo: {exc}") from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/", response_model=List[dict])
def listar(
    zona: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    turno: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    items = crud.listar_denuncias(db, zona=zona, tipo=tipo, turno=turno, estado=estado, desde=desde, hasta=hasta, q=q, limit=limit, offset=offset)
    return [_serialize_denuncia(x) for x in items]


@router.get("/count", response_model=dict)
def count_denuncias(
    zona: Optional[int] = None,
    tipo: Optional[str] = None,
    turno: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    return {"total": crud.contar_denuncias(db, zona=zona, tipo=tipo, turno=turno, estado=estado, desde=desde, hasta=hasta, q=q)}


@router.get("/stats/", response_model=dict)
def stats(db: Session = Depends(get_db), user: User = Depends(require_roles(*READ_ROLES))):
    return crud.get_dashboard_stats(db)


def _month_add(base: date, months: int) -> date:
    month = base.month - 1 + months
    year = base.year + month // 12
    return date(year, month % 12 + 1, 1)


def _last_months(n: int, ref: date) -> list[date]:
    first = ref.replace(day=1)
    return [_month_add(first, -i) for i in range(n - 1, -1, -1)]


def _percentile_value(values: list[float], p: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    idx = max(0, min(len(values) - 1, math.ceil(p * len(values)) - 1))
    return int(values[idx])


def _filtered_dashboard_stats(rows: list[Denuncia]) -> dict:
    total = len(rows)
    ref_date = max((x.fecha_hora_suceso.date() for x in rows if x.fecha_hora_suceso), default=date.today())
    months12 = _last_months(12, ref_date)
    months6 = _last_months(6, ref_date)

    month_counts = Counter()
    estados_month = {m: Counter() for m in months6}
    for row in rows:
        if not row.fecha_hora_suceso:
            continue
        month = row.fecha_hora_suceso.date().replace(day=1)
        month_counts[month] += 1
        if month in estados_month:
            estados_month[month][row.estado_denuncia or "Sin dato"] += 1

    estados = Counter(row.estado_denuncia or "Sin dato" for row in rows)
    por_turno = Counter(row.turno or "Sin dato" for row in rows)
    por_zona = Counter(row.zona_denuncia for row in rows if row.zona_denuncia is not None)
    tipos = Counter(row.tipo_denuncia or "Sin dato" for row in rows)
    origen = Counter(row.origen_denuncia or "Sin dato" for row in rows)
    lugar = Counter(row.lugar_ocurrencia or "Sin dato" for row in rows)
    sexo = Counter(row.sexo_victima or "Sin dato" for row in rows)
    distritos = Counter(row.distrito_victima or "Sin dato" for row in rows)

    edad_values = [int(row.edad_victima) for row in rows if row.edad_victima is not None]
    edad_buckets = {
        "0-20": sum(1 for x in edad_values if 0 <= x <= 20),
        "21-30": sum(1 for x in edad_values if 21 <= x <= 30),
        "31-45": sum(1 for x in edad_values if 31 <= x <= 45),
        "46-60": sum(1 for x in edad_values if 46 <= x <= 60),
        "61+": sum(1 for x in edad_values if x >= 61),
    }

    reaction_seconds = []
    for row in rows:
        if row.fecha_hora_suceso and row.fecha_hora_llegada:
            seconds = (row.fecha_hora_llegada - row.fecha_hora_suceso).total_seconds()
            if seconds >= 0:
                reaction_seconds.append(seconds)
    sla_ok = sum(1 for x in reaction_seconds if x <= 20 * 60)
    sla_pct = round((sla_ok / len(reaction_seconds)) * 100, 1) if reaction_seconds else 0

    estados_labels = sorted({status for counter in estados_month.values() for status in counter.keys()})
    estados_datasets = [
        {"label": status, "data": [estados_month[m].get(status, 0) for m in months6]}
        for status in estados_labels
    ]

    return {
        "kpis": {
            "total": total,
            "sla_pct": sla_pct,
            "reaccion_mediana": _percentile_value(reaction_seconds, 0.5),
            "reaccion_p90": _percentile_value(reaction_seconds, 0.9),
        },
        "estados": dict(estados),
        "por_turno": dict(por_turno),
        "por_zona": {str(k): v for k, v in por_zona.items()},
        "tipos": dict(tipos.most_common(20)),
        "series_12m": {
            "labels": [m.strftime("%b %Y") for m in months12],
            "counts": [month_counts.get(m, 0) for m in months12],
        },
        "estados_por_mes_6m": {
            "labels": [m.strftime("%b %Y") for m in months6],
            "datasets": estados_datasets,
        },
        "origen": dict(origen.most_common(10)),
        "naturaleza": {},
        "forma": {},
        "lugar": dict(lugar.most_common(10)),
        "distritos_top": dict(distritos.most_common(10)),
        "sexo": dict(sexo),
        "edad": {
            "promedio": round(sum(edad_values) / len(edad_values), 1) if edad_values else 0,
            "buckets": edad_buckets,
            "n": len(edad_values),
        },
        "reaccion": {"suceso_llegada": {"p50": _percentile_value(reaction_seconds, 0.5), "p90": _percentile_value(reaction_seconds, 0.9)}},
    }


@router.get("/stats-advanced", response_model=dict)
def stats_advanced(
    zona: Optional[int] = None,
    tipo: Optional[str] = None,
    turno: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente", "JefeOperaciones", "Analista", "EncargadoSipCop")),
):
    filters = {"zona": zona, "tipo": tipo, "turno": turno, "estado": estado, "desde": desde, "hasta": hasta, "q": q}
    has_filters = any(value not in (None, "") for value in filters.values())
    if has_filters:
        rows = crud.listar_denuncias(db, limit=50000, offset=0, **filters)
        data = _filtered_dashboard_stats(rows)
    else:
        data = crud.get_advanced_dashboard_stats(db)
    total = data.get("kpis", {}).get("total", 0) or 0
    geo_query = crud.denuncias_query(db, **filters) if has_filters else db.query(Denuncia)
    geocoded = geo_query.filter(Denuncia.latitud.is_not(None), Denuncia.longitud.is_not(None)).count()
    missing_geo = max(0, int(total) - int(geocoded))
    batches = db.query(func.count(UploadBatch.id)).scalar() or 0
    rejected = db.query(func.coalesce(func.sum(UploadBatch.rejected_rows), 0)).scalar() or 0
    loaded = db.query(func.coalesce(func.sum(UploadBatch.total_rows), 0)).scalar() or 0
    duplicates = db.query(func.count(UploadError.id)).filter(UploadError.error_type.like("duplicado%")).scalar() or 0
    data["calidad"] = {
        "geocodificados_pct": round((int(geocoded) / total) * 100, 1) if total else 0,
        "sin_coordenadas": missing_geo,
        "cargas_procesadas": int(batches),
        "filas_rechazadas_pct": round((int(rejected) / int(loaded)) * 100, 1) if loaded else 0,
        "duplicados_detectados": int(duplicates),
    }
    return data


def _filtered_for_export(db: Session, **filters):
    return crud.listar_denuncias(db, limit=50000, offset=0, **filters)


@router.get("/export.csv", response_class=StreamingResponse)
def export_csv(
    request: Request,
    zona: Optional[int] = None,
    tipo: Optional[str] = None,
    turno: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    rows = _filtered_for_export(db, zona=zona, tipo=tipo, turno=turno, estado=estado, desde=desde, hasta=hasta, q=q)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "numero_parte", "fecha_hora_suceso", "zona", "turno", "tipo", "estado", "lugar", "direccion", "source_file", "upload_batch_id"])
    for d in rows:
        writer.writerow([d.id, d.numero_parte or "", d.fecha_hora_suceso or "", d.zona_denuncia, d.turno or "", d.tipo_denuncia or "", d.estado_denuncia or "", d.lugar_ocurrencia or "", d.direccion_ocurrencia or "", d.source_file or "", d.upload_batch_id or ""])
    out.seek(0)
    audit_event(db, request, "export_denuncias_csv", user=user, detail={"rows": len(rows)})
    return StreamingResponse(out, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=incidencias_filtradas.csv"})


@router.get("/export.xlsx", response_class=StreamingResponse)
def export_xlsx(
    request: Request,
    zona: Optional[int] = None,
    tipo: Optional[str] = None,
    turno: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
):
    rows = _filtered_for_export(db, zona=zona, tipo=tipo, turno=turno, estado=estado, desde=desde, hasta=hasta, q=q)
    df = pd.DataFrame([_serialize_denuncia(d) for d in rows])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Incidencias")
    buffer.seek(0)
    audit_event(db, request, "export_denuncias_excel", user=user, detail={"rows": len(rows)})
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=incidencias_filtradas.xlsx"})


@router.get("/uploads", response_model=List[dict])
def upload_batches(db: Session = Depends(get_db), user: User = Depends(require_roles(*UPLOAD_ROLES))):
    batches = db.query(UploadBatch).order_by(UploadBatch.uploaded_at.desc()).limit(100).all()
    return [
        {
            "id": b.id,
            "filename": b.original_filename,
            "uploaded_at": b.uploaded_at,
            "total_rows": b.total_rows,
            "accepted_rows": b.accepted_rows,
            "rejected_rows": b.rejected_rows,
            "status": b.status,
            "message": b.message,
        }
        for b in batches
    ]


@router.get("/uploads/{batch_id}/errors", response_model=List[dict])
def upload_errors(batch_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*UPLOAD_ROLES))):
    errors = db.query(UploadError).filter(UploadError.batch_id == batch_id).order_by(UploadError.row_number, UploadError.id).all()
    return [
        {
            "id": e.id,
            "batch_id": e.batch_id,
            "row_number": e.row_number,
            "column_name": e.column_name,
            "raw_value": e.raw_value,
            "error_type": e.error_type,
            "error_message": e.error_message,
            "severity": e.severity,
            "created_at": e.created_at,
        }
        for e in errors
    ]


def _errors_dataframe(db: Session, batch_id: int) -> pd.DataFrame:
    rows = db.query(UploadError).filter(UploadError.batch_id == batch_id).order_by(UploadError.row_number, UploadError.id).all()
    return pd.DataFrame(
        [
            {
                "fila": e.row_number,
                "columna": e.column_name,
                "valor": e.raw_value,
                "tipo": e.error_type,
                "mensaje": e.error_message,
                "severidad": e.severity,
            }
            for e in rows
        ]
    )


@router.get("/uploads/{batch_id}/errors.csv", response_class=StreamingResponse)
def upload_errors_csv(request: Request, batch_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*UPLOAD_ROLES))):
    df = _errors_dataframe(db, batch_id)
    out = io.StringIO()
    df.to_csv(out, index=False)
    out.seek(0)
    audit_event(db, request, "export_upload_errors_csv", user=user, detail={"batch_id": batch_id, "rows": len(df)})
    return StreamingResponse(out, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=errores_carga_{batch_id}.csv"})


@router.get("/uploads/{batch_id}/errors.xlsx", response_class=StreamingResponse)
def upload_errors_xlsx(request: Request, batch_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*UPLOAD_ROLES))):
    df = _errors_dataframe(db, batch_id)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Errores")
    buffer.seek(0)
    audit_event(db, request, "export_upload_errors_excel", user=user, detail={"batch_id": batch_id, "rows": len(df)})
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=errores_carga_{batch_id}.xlsx"})


@router.get("/{denuncia_id}", response_model=dict)
def detalle_denuncia(denuncia_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*READ_ROLES))):
    item = db.get(Denuncia, denuncia_id)
    if not item:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return _serialize_denuncia(item)
