"""Seeder para la tabla `zonas` (7 zonas con GeoJSON simplificado).

Uso:
    python -m app.services.seed_zonas

Inserta 7 polígonos rectangulares aproximados centrados en JLByR.
No son límites oficiales; sirven para pruebas y tooltips del mapa.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Zona


# Centro aproximado: José Luis Bustamante y Rivero, Arequipa
CENTER_LAT = -16.409
CENTER_LON = -71.535


def _rect(lon0: float, lat0: float, lon1: float, lat1: float) -> dict:
    """Construye un polígono rectangular en GeoJSON (ccw)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon0, lat0],
                [lon1, lat0],
                [lon1, lat1],
                [lon0, lat1],
                [lon0, lat0],
            ]
        ],
    }


def build_test_zones() -> List[Zona]:
    """Genera 7 zonas con rectángulos alrededor del centro.

    Cada zona tiene un pequeño desplazamiento para que no se superpongan completamente.
    """
    # Offsets en grados (~1e-3 ≈ 100m aprox en lat; en lon varía con latitud)
    offs = [
        (0.00, 0.00),
        (0.01, 0.00),
        (-0.01, 0.00),
        (0.00, 0.01),
        (0.00, -0.01),
        (0.008, 0.008),
        (-0.008, -0.008),
    ]

    zones = []
    for i, (dx, dy) in enumerate(offs, start=1):
        lat = CENTER_LAT + dy
        lon = CENTER_LON + dx
        # Rectángulo de ~400m x ~400m aprox
        lat_span = 0.004
        lon_span = 0.004
        geom = _rect(lon - lon_span, lat - lat_span, lon + lon_span, lat + lat_span)

        zones.append(
            Zona(
                id_zona=i,
                nombre=f"Z{i}",
                geojson={"type": "Feature", "geometry": geom, "properties": {"id": i, "name": f"Z{i}"}},
                centroid_lat=lat,
                centroid_lon=lon,
            )
        )
    return zones


def upsert_zones(session: Session) -> int:
    existing_ids = set(session.scalars(select(Zona.id_zona)).all())
    items = build_test_zones()
    inserted = 0
    for item in items:
        if item.id_zona in existing_ids:
            # update simple (nombre/geojson/centroides)
            db_item = session.get(Zona, item.id_zona)
            db_item.nombre = item.nombre
            db_item.geojson = item.geojson
            db_item.centroid_lat = item.centroid_lat
            db_item.centroid_lon = item.centroid_lon
        else:
            session.add(item)
            inserted += 1
    session.commit()
    return inserted


def main() -> None:
    session = SessionLocal()
    try:
        n = upsert_zones(session)
        print(f"Zonas listas. Insertadas: {n} (otras fueron actualizadas si existían).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
