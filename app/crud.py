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


























# ======== DASHBOARD AVANZADO ========
from sqlalchemy import case
from sqlalchemy.sql import label
from datetime import date, datetime
from collections import defaultdict

def _month_floor(d: date) -> date:
    return d.replace(day=1)

def _last_n_months(n: int, ref: date | None = None):
    ref = ref or date.today()
    base = _month_floor(ref)
    months = []
    y, m = base.year, base.month
    for i in range(n-1, -1, -1):
        yy = y if m - i > 0 else y - ((i - m) // 12 + 1)
        mm = (m - i - 1) % 12 + 1
        months.append(date(yy, mm, 1))
    return months  # [date(YYYY,MM,01), ...]

def _seconds(expr):
    return func.extract("epoch", expr)  # timedelta -> seconds

def _percentile(p: float, expr):
    # percentile_cont(p) WITHIN GROUP (ORDER BY expr)
    return func.percentile_cont(p).within_group(expr)  # PostgreSQL

def get_mes_labels_counts_12m(db: Session):
    meses = _last_n_months(12)
    ini = meses[0]
    prox = date(meses[-1].year + (1 if meses[-1].month == 12 else 0),
                1 if meses[-1].month == 12 else meses[-1].month + 1,
                1)

    rows = (
        db.query(func.date_trunc("month", models.Denuncia.fecha_hora_suceso).label("m"),
                 func.count(models.Denuncia.id))
        .filter(models.Denuncia.fecha_hora_suceso >= ini)
        .filter(models.Denuncia.fecha_hora_suceso < prox)
        .group_by("m").order_by("m")
        .all()
    )
    mapa = {m.date().replace(day=1): int(c) for m, c in rows}
    labels = [d.strftime("%b %Y") for d in meses]
    counts = [mapa.get(d, 0) for d in meses]
    return labels, counts

def get_estados_por_mes_6m(db: Session):
    meses = _last_n_months(6)
    ini = meses[0]
    prox = date(meses[-1].year + (1 if meses[-1].month == 12 else 0),
                1 if meses[-1].month == 12 else meses[-1].month + 1,
                1)
    rows = (
        db.query(
            func.date_trunc("month", models.Denuncia.fecha_hora_suceso).label("m"),
            models.Denuncia.estado_denuncia,
            func.count(models.Denuncia.id)
        )
        .filter(models.Denuncia.fecha_hora_suceso >= ini)
        .filter(models.Denuncia.fecha_hora_suceso < prox)
        .group_by("m", models.Denuncia.estado_denuncia)
        .order_by("m")
        .all()
    )
    # estados dinámicos
    estados = sorted({(e or "Sin dato") for _, e, _ in rows})
    # llenar matriz meses x estados
    matriz = {d: {e: 0 for e in estados} for d in meses}
    for m, e, c in rows:
        key = m.date().replace(day=1)
        matriz[key][e or "Sin dato"] = int(c)
    labels = [d.strftime("%b %Y") for d in meses]
    datasets = []
    for e in estados:
        datasets.append({
            "label": e,
            "data": [matriz[d][e] for d in meses]
        })
    return labels, datasets

def get_top_dict(db: Session, column, limit=10):
    rows = (
        db.query(column, func.count(models.Denuncia.id))
        .group_by(column).order_by(func.count(models.Denuncia.id).desc())
        .limit(limit).all()
    )
    return [(k or "Sin dato", int(c)) for k, c in rows]

def get_age_buckets(db: Session):
    # buckets: 0-20, 21-30, 31-45, 46-60, 61+
    expr = models.Denuncia.edad_victima
    rows = (
        db.query(
            func.sum(case((expr.between(0,20),1), else_=0)).label("b1"),
            func.sum(case((expr.between(21,30),1), else_=0)).label("b2"),
            func.sum(case((expr.between(31,45),1), else_=0)).label("b3"),
            func.sum(case((expr.between(46,60),1), else_=0)).label("b4"),
            func.sum(case((expr >= 61,1), else_=0)).label("b5"),
            func.count(expr).label("n")
        )
    ).one()

    buckets = {
        "0-20": int(rows.b1 or 0),
        "21-30": int(rows.b2 or 0),
        "31-45": int(rows.b3 or 0),
        "46-60": int(rows.b4 or 0),
        "61+": int(rows.b5 or 0),
    }
    n = int(rows.n or 0)
    return buckets, n

def get_sexo_counts(db: Session):
    rows = (
        db.query(models.Denuncia.sexo_victima, func.count(models.Denuncia.id))
        .group_by(models.Denuncia.sexo_victima).all()
    )
    return {(s or "Sin dato"): int(c) for s, c in rows}

def get_reaccion_stats(db: Session, sla_minutes: int = 20):
    # Diferencias en segundos
    suceso = models.Denuncia.fecha_hora_suceso
    alerta = models.Denuncia.fecha_hora_alerta
    llegada = models.Denuncia.fecha_hora_llegada

    # suceso->alerta
    s_a_q = (
        db.query(
            _percentile(0.5, _seconds(alerta - suceso)).label("p50"),
            _percentile(0.9, _seconds(alerta - suceso)).label("p90")
        )
        .filter(suceso.isnot(None), alerta.isnot(None))
    ).one()

    # alerta->llegada
    a_l_q = (
        db.query(
            _percentile(0.5, _seconds(llegada - alerta)).label("p50"),
            _percentile(0.9, _seconds(llegada - alerta)).label("p90")
        )
        .filter(alerta.isnot(None), llegada.isnot(None))
    ).one()

    # suceso->llegada
    s_l_q = (
        db.query(
            _percentile(0.5, _seconds(llegada - suceso)).label("p50"),
            _percentile(0.9, _seconds(llegada - suceso)).label("p90")
        )
        .filter(suceso.isnot(None), llegada.isnot(None))
    ).one()

    # SLA %
    sla_secs = sla_minutes * 60
    sla_rows = (
        db.query(func.count(models.Denuncia.id))
        .filter(suceso.isnot(None), llegada.isnot(None))
        .all()
    )
    total_valid = int(sla_rows[0][0]) if sla_rows else 0

    sla_ok_rows = (
        db.query(func.count(models.Denuncia.id))
        .filter(suceso.isnot(None), llegada.isnot(None))
        .filter(_seconds(llegada - suceso) <= sla_secs)
        .all()
    )
    sla_ok = int(sla_ok_rows[0][0]) if sla_ok_rows else 0
    sla_pct = round(100.0 * sla_ok / total_valid, 1) if total_valid else 0.0

    def _sec(x): return int(x or 0)

    return {
        "suceso_alerta": {"p50": _sec(s_a_q.p50), "p90": _sec(s_a_q.p90)},
        "alerta_llegada": {"p50": _sec(a_l_q.p50), "p90": _sec(a_l_q.p90)},
        "suceso_llegada": {"p50": _sec(s_l_q.p50), "p90": _sec(s_l_q.p90)},
        "sla_pct": sla_pct,
        "total_valid": total_valid
    }

def get_advanced_dashboard_stats(db: Session) -> dict:
    total = get_denuncia_count(db)
    estados = get_estados_denuncia(db)
    por_turno = get_denuncias_por_turno(db)
    por_zona = get_denuncias_por_zona(db)
    tipos = get_tipos_denuncia(db)

    # series
    m12_labels, m12_counts = get_mes_labels_counts_12m(db)
    est6_labels, est6_datasets = get_estados_por_mes_6m(db)

    # operación
    origen = dict(get_top_dict(db, models.Denuncia.origen_denuncia, 10))
    naturaleza = dict(get_top_dict(db, models.Denuncia.naturaleza_personal, 10))
    forma = dict(get_top_dict(db, models.Denuncia.forma_patrullaje, 10))
    lugar = dict(get_top_dict(db, models.Denuncia.lugar_ocurrencia, 10))
    distritos = dict(get_top_dict(db, models.Denuncia.distrito_victima, 10))

    sexo = get_sexo_counts(db)
    edad_buckets, edad_n = get_age_buckets(db)
    edad_promedio_row = db.query(func.avg(models.Denuncia.edad_victima)).filter(models.Denuncia.edad_victima.isnot(None)).one()
    edad_prom = float(edad_promedio_row[0] or 0.0)

    reaccion = get_reaccion_stats(db, sla_minutes=20)

    return {
        "kpis": {
            "total": total,
            "sla_pct": reaccion["sla_pct"],
            "reaccion_mediana": reaccion["suceso_llegada"]["p50"],
            "reaccion_p90": reaccion["suceso_llegada"]["p90"]
        },
        "estados": estados,
        "por_turno": por_turno,
        "por_zona": por_zona,
        "tipos": tipos,
        "series_12m": {"labels": m12_labels, "counts": m12_counts},
        "estados_por_mes_6m": {"labels": est6_labels, "datasets": est6_datasets},
        "origen": origen,
        "naturaleza": naturaleza,
        "forma": forma,
        "lugar": lugar,
        "distritos_top": distritos,
        "sexo": sexo,
        "edad": {
            "promedio": round(edad_prom, 1),
            "buckets": edad_buckets,
            "n": edad_n
        },
        "reaccion": reaccion
    }




# ======== FIN DASHBOARD AVANZADO ========