"""Rellena coordenadas faltantes en `denuncias` usando centroides de `zonas`.

Uso:
    python -m app.services.backfill_centroids --limit 20000

Asigna latitud/longitud desde el centroide de la zona cuando están nulos y
calcula `peso` según el tipo de denuncia. Marca `geocode_status='approx'` y
`geocode_precision='centroid'`.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Denuncia, Zona


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


WEIGHT_RULES = {
    "robo": 1.00,
    "robo agravado": 1.00,
    "hurto": 0.80,
    "lesiones": 0.90,
    "violencia": 0.90,
}


def compute_weight(tipo: str | None) -> float:
    if not tipo:
        return 0.60
    key = tipo.lower()
    for label, weight in WEIGHT_RULES.items():
        if label in key:
            return clamp(weight, 0.30, 1.20)
    return 0.60


def backfill(session: Session, limit: int) -> int:
    zonas: Dict[int, tuple[float, float]] = {
        z.id_zona: (z.centroid_lat, z.centroid_lon)
        for z in session.scalars(select(Zona)).all()
        if z.centroid_lat is not None and z.centroid_lon is not None
    }
    if not zonas:
        return 0

    q = (
        select(Denuncia)
        .where((Denuncia.latitud.is_(None)) | (Denuncia.longitud.is_(None)))
        .order_by(Denuncia.id)
        .limit(limit)
    )
    rows = session.scalars(q).all()
    updated = 0
    for d in rows:
        if d.zona_denuncia in zonas:
            lat, lon = zonas[d.zona_denuncia]
            d.latitud = lat
            d.longitud = lon
            d.geocode_status = "approx"
            d.geocode_precision = "centroid"
            d.geocoded_at = datetime.utcnow()
            d.peso = compute_weight(d.tipo_denuncia)
            session.add(d)
            updated += 1
    session.commit()
    return updated


def main(limit: int) -> None:
    session = SessionLocal()
    try:
        n = backfill(session, limit)
        print(f"Registros actualizados con centroides: {n}")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill de coordenadas desde centroides de zonas")
    parser.add_argument("--limit", type=int, default=20000)
    args = parser.parse_args()
    main(args.limit)

