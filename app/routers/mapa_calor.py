"""Router del modulo Mapa de Calor.

Notas (2025-11):
- Protegido por roles (Gerente/JefeOperaciones/Analista) via require_roles.
- Usa la tabla existente `denuncias` (no requiere `incidentes`).
- Endpoints: /filters, /points, /zones, /points.csv
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, extract
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Denuncia, Zona
from ..schemas import MapDateRange, MapFilters, MapPoint, ZoneFeature

LOGGER = logging.getLogger("app.routers.mapa_calor")
# Permiten acceder al módulo de Mapa de Calor
ALLOWED_ROLES = ("Gerente", "JefeOperaciones", "Analista", "EncargadoSipCop")


@dataclass
class User:
    """Representación mínima del usuario autenticado."""

    id: int
    username: str
    role: str


def get_current_user() -> User:
    """Stub de autenticación para entornos sin módulo de seguridad."""

    return User(id=1, username="demo", role="Analista")


def require_roles(*roles: str):
    """Valida que el usuario posea alguno de los roles permitidos.

    En produccion, reemplazar get_current_user por la dependencia real.
    """

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes para acceder al mapa")
        return user

    return _dependency


def _parse_csv_param(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int_list(value: Optional[str]) -> List[int]:
    items = []
    for raw in _parse_csv_param(value):
        try:
            items.append(int(raw))
        except ValueError as exc:  # pragma: no cover - validación defensiva
            raise HTTPException(status_code=400, detail=f"Zona inválida: {raw}") from exc
    return items


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Fecha inválida: {value}") from exc


def _build_filters_summary(params: Dict[str, object]) -> Dict[str, object]:
    return {key: val for key, val in params.items() if val not in (None, [], "")}


def _to_datetime_end_of_day(value: datetime) -> datetime:
    return value + timedelta(days=1) - timedelta(microseconds=1)


def _fetch_denuncias(
    db: Session,
    desde: Optional[str],
    hasta: Optional[str],
    tipos: Optional[str],
    turnos: Optional[str],
    zonas: Optional[str],
    anio: Optional[int] = None
) -> List[Denuncia]:
    desde_dt = _parse_date(desde)
    hasta_dt = _parse_date(hasta)
    tipos_list = _parse_csv_param(tipos)
    turnos_list = _parse_csv_param(turnos)
    zonas_list = _parse_int_list(zonas)

    # Year filter (optional)
    year_val = anio if isinstance(anio, int) else None

    stmt = (
        select(Denuncia)
        .where(Denuncia.latitud.is_not(None), Denuncia.longitud.is_not(None))
        .order_by(Denuncia.fecha_hora_suceso.desc().nullslast(), Denuncia.id.desc())
    )

    if year_val:
        stmt = stmt.where(extract('year', Denuncia.fecha_hora_suceso) == year_val)
    if desde_dt:
        stmt = stmt.where(Denuncia.fecha_hora_suceso >= desde_dt)
    if hasta_dt:
        stmt = stmt.where(Denuncia.fecha_hora_suceso <= _to_datetime_end_of_day(hasta_dt))
    if tipos_list:
        stmt = stmt.where(Denuncia.tipo_denuncia.in_(tipos_list))
    if turnos_list:
        stmt = stmt.where(Denuncia.turno.in_(turnos_list))
    if zonas_list:
        stmt = stmt.where(Denuncia.zona_denuncia.in_(zonas_list))

    return db.scalars(stmt).all()


def _denuncia_to_point(denuncia: Denuncia) -> MapPoint:
    peso_value = denuncia.peso
    if isinstance(peso_value, Decimal):
        peso_value = float(peso_value)
    elif peso_value is None:
        peso_value = 1.0

    fecha_value = denuncia.fecha_hora_suceso or denuncia.created_at or datetime.utcnow()

    return MapPoint(
        id=denuncia.id,
        lat=float(denuncia.latitud),
        lon=float(denuncia.longitud),
        peso=float(peso_value),
        tipo=denuncia.tipo_denuncia,
        turno=denuncia.turno,
        fecha=fecha_value,
        zona=denuncia.zona_denuncia,
        direccion=denuncia.direccion_ocurrencia,
    )


# Nota: el prefijo se aplica en app/main.py al incluir este router.
router = APIRouter(tags=["mapa-calor"])


@router.get("/filters", response_model=MapFilters)
def get_filters(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ALLOWED_ROLES)),
) -> MapFilters:
    tipos = [
        value
        for value in db.scalars(
            select(Denuncia.tipo_denuncia)
            .where(Denuncia.tipo_denuncia.is_not(None))
            .distinct()
            .order_by(Denuncia.tipo_denuncia)
        )
        if value
    ]

    # Fallbacks si la BD aún no tiene datos
    if not tipos:
        tipos = ["Robo", "Hurto", "Lesiones", "Violencia familiar", "Otros"]

    turnos = [
        value
        for value in db.scalars(
            select(Denuncia.turno)
            .where(Denuncia.turno.is_not(None))
            .distinct()
            .order_by(Denuncia.turno)
        )
        if value
    ]

    if not turnos:
        turnos = ["Mañana", "Tarde", "Noche"]

    zonas = db.scalars(select(Zona.id_zona).order_by(Zona.id_zona)).all()
    if not zonas:
        zonas = list(range(1, 8))

    min_fecha, max_fecha = db.execute(
        select(func.min(Denuncia.fecha_hora_suceso), func.max(Denuncia.fecha_hora_suceso))
    ).one()

    fecha_range = MapDateRange(
        min=min_fecha.date().isoformat() if min_fecha else None,
        max=max_fecha.date().isoformat() if max_fecha else None,
    )

    years_rows = db.execute(select(func.date_part('year', Denuncia.fecha_hora_suceso).label('y')).distinct().order_by(func.date_part('year', Denuncia.fecha_hora_suceso))).all()
    years = [int(row[0]) for row in years_rows if row and row[0] is not None]

    filters_summary = _build_filters_summary({"tipos": tipos, "turnos": turnos, "zonas": zonas})
    LOGGER.info(
        "user=%s role=%s endpoint=/filters filters=%s",
        user.username,
        user.role,
        filters_summary,
    )

    return MapFilters(tipos=tipos, turnos=turnos, zonas=list(zonas), fecha=fecha_range, anios=years)


@router.get("/points", response_model=List[MapPoint])
def get_points(
    desde: Optional[str] = Query(None, description="Fecha inicial YYYY-MM-DD"),
    hasta: Optional[str] = Query(None, description="Fecha final YYYY-MM-DD"),
    tipo: Optional[str] = Query(None, description="Tipos de denuncia separados por coma"),
    turno: Optional[str] = Query(None, description="Turnos separados por coma"),
    zona: Optional[str] = Query(None, description="Zonas separadas por coma"),
    anio: Optional[int] = Query(None, description="Año (e.g., 2025); vacío=Todos"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ALLOWED_ROLES)),
) -> List[MapPoint]:
    denuncias = _fetch_denuncias(db, desde, hasta, tipo, turno, zona, anio)
    puntos = [_denuncia_to_point(x) for x in denuncias]

    filters_summary = _build_filters_summary(
        {"desde": desde, "hasta": hasta, "tipo": tipo, "turno": turno, "zona": zona}
    )
    LOGGER.info(
        "user=%s role=%s endpoint=/points filters=%s count=%s",
        user.username,
        user.role,
        filters_summary,
        len(puntos),
    )

    return puntos


@router.get("/zones", response_model=List[ZoneFeature])
def get_zones(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ALLOWED_ROLES)),
) -> List[ZoneFeature]:
    zonas = db.scalars(select(Zona).order_by(Zona.id_zona)).all()

    payload = [
        ZoneFeature(
            id_zona=zona.id_zona,
            nombre=zona.nombre,
            geojson=zona.geojson,
            centroid=[zona.centroid_lat, zona.centroid_lon],
        )
        for zona in zonas
    ]

    LOGGER.info(
        "user=%s role=%s endpoint=/zones count=%s",
        user.username,
        user.role,
        len(payload),
    )

    return payload


@router.get("/points.csv", response_class=StreamingResponse)
def download_points_csv(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    turno: Optional[str] = Query(None),
    zona: Optional[str] = Query(None),
    anio: Optional[int] = Query(None, description="Año (e.g., 2025); vacío=Todos"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ALLOWED_ROLES)),
) -> StreamingResponse:
    denuncias = _fetch_denuncias(db, desde, hasta, tipo, turno, zona, anio)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "fecha", "tipo", "turno", "zona", "lat", "lon", "direccion"])

    for denuncia in denuncias:
        fecha = (denuncia.fecha_hora_suceso or denuncia.created_at or datetime.utcnow()).isoformat()
        lat = denuncia.latitud if denuncia.latitud is not None else ""
        lon = denuncia.longitud if denuncia.longitud is not None else ""
        writer.writerow(
            [
                denuncia.id,
                fecha,
                denuncia.tipo_denuncia or "",
                denuncia.turno or "",
                denuncia.zona_denuncia or "",
                lat,
                lon,
                denuncia.direccion_ocurrencia or "",
            ]
        )

    output.seek(0)

    filters_summary = _build_filters_summary(
        {"desde": desde, "hasta": hasta, "tipo": tipo, "turno": turno, "zona": zona}
    )
    LOGGER.info(
        "user=%s role=%s endpoint=/points.csv filters=%s count=%s",
        user.username,
        user.role,
        filters_summary,
        len(denuncias),
    )

    headers = {"Content-Disposition": "attachment; filename=incidentes_filtrados.csv"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)
