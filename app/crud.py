# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List, Dict
from datetime import date, timedelta
from . import models, schemas

# ---------------------------
# Helpers fechas
# ---------------------------

def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)

def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)

# ---------------------------
# CRUD básico
# ---------------------------

def create_denuncia(db: Session, denuncia: schemas.DenunciaCreate):
    obj = models.Denuncia(**denuncia.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def create_denuncias_bulk(db: Session, rows: List[schemas.DenunciaCreate]):
    objs = [models.Denuncia(**r.model_dump(exclude_unset=True)) for r in rows]
    db.add_all(objs)
    db.commit()
    return len(objs)

def listar_denuncias(db: Session, limit: int = 1000):
    return (
        db.query(models.Denuncia)
        .order_by(models.Denuncia.id.desc())
        .limit(limit)
        .all()
    )

# ---------------------------
# Agregaciones
# ---------------------------

def get_denuncia_count(db: Session) -> int:
    return int(db.query(func.count(models.Denuncia.id)).scalar() or 0)

def get_denuncias_por_zona(db: Session) -> Dict[int, int]:
    rows = (
        db.query(models.Denuncia.zona_denuncia, func.count(models.Denuncia.id))
        .group_by(models.Denuncia.zona_denuncia)
        .all()
    )
    return {int(z): int(c) for z, c in rows if z is not None}

def get_denuncias_por_turno(db: Session) -> Dict[str, int]:
    rows = (
        db.query(models.Denuncia.turno, func.count(models.Denuncia.id))
        .group_by(models.Denuncia.turno)
        .all()
    )
    return {(t or "Sin dato"): int(c) for t, c in rows}

def get_tipos_denuncia(db: Session) -> Dict[str, int]:
    rows = (
        db.query(models.Denuncia.tipo_denuncia, func.count(models.Denuncia.id))
        .group_by(models.Denuncia.tipo_denuncia)
        .order_by(func.count(models.Denuncia.id).desc())
        .all()
    )
    return {(t or "Sin dato"): int(c) for t, c in rows}

def get_estados_denuncia(db: Session) -> Dict[str, int]:
    rows = (
        db.query(models.Denuncia.estado_denuncia, func.count(models.Denuncia.id))
        .group_by(models.Denuncia.estado_denuncia)
        .all()
    )
    return {(e or "Sin dato"): int(c) for e, c in rows}

def _evolucion_mes_actual(db: Session):
    hoy = date.today()
    ini_mes = _first_day_of_month(hoy)
    prox_mes = _add_months(ini_mes, 1)

    rows = (
        db.query(cast(models.Denuncia.fecha_hora_suceso, Date), func.count(models.Denuncia.id))
        .filter(models.Denuncia.fecha_hora_suceso >= ini_mes)
        .filter(models.Denuncia.fecha_hora_suceso < prox_mes)
        .group_by(cast(models.Denuncia.fecha_hora_suceso, Date))
        .order_by(cast(models.Denuncia.fecha_hora_suceso, Date))
        .all()
    )
    mapa = {d.isoformat(): int(c) for d, c in rows}

    labels, counts = [], []
    d = ini_mes
    while d < prox_mes:
        labels.append(f"{d.day:02d}")
        counts.append(mapa.get(d.isoformat(), 0))
        d += timedelta(days=1)
    return labels, counts

def _comparativo_ult_3_meses(db: Session):
    hoy = date.today()
    ini_mes = _first_day_of_month(hoy)
    prox_mes = _add_months(ini_mes, 1)
    ini_3m = _add_months(ini_mes, -2)  # mes-2, mes-1, mes actual

    rows = (
        db.query(func.date_trunc("month", models.Denuncia.fecha_hora_suceso).label("m"),
                 func.count(models.Denuncia.id))
        .filter(models.Denuncia.fecha_hora_suceso >= ini_3m)
        .filter(models.Denuncia.fecha_hora_suceso < prox_mes)
        .group_by("m")
        .order_by("m")
        .all()
    )

    labels, counts = [], []
    cursor = ini_3m
    while cursor < prox_mes:
        label = cursor.strftime("%b %Y")  # Ej: Nov 2025
        labels.append(label)
        c = 0
        for m, n in rows:
            if m.date().replace(day=1) == cursor:
                c = int(n)
                break
        counts.append(c)
        cursor = _add_months(cursor, 1)
    return labels, counts

def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    mes_labels, mes_counts = _evolucion_mes_actual(db)
    ult3_labels, ult3_counts = _comparativo_ult_3_meses(db)

    return schemas.DashboardStats(
        total_denuncias=get_denuncia_count(db),
        denuncias_por_zona=get_denuncias_por_zona(db),
        denuncias_por_turno=get_denuncias_por_turno(db),
        tipos_denuncia=get_tipos_denuncia(db),
        estados_denuncia=get_estados_denuncia(db),
        mes_actual_labels=mes_labels,
        mes_actual_counts=mes_counts,
        ult_3_meses_labels=ult3_labels,
        ult_3_meses_counts=ult3_counts,
    )
