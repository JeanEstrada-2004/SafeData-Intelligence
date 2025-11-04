#!/usr/bin/env python3
"""Backfill geocoding and heat-weight for existing denuncias.

Usage:
  python -m scripts.backfill_denuncias_geo [--limit N] [--offset N] [--dry-run] [--only-weight] [--recompute-geo]
"""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Denuncia
from app.services.enrich import enrich_denuncia_input


def iter_targets(db: Session, limit: int | None, offset: int | None, only_weight: bool) -> Iterable[Denuncia]:
    stmt = select(Denuncia)
    if not only_weight:
        stmt = stmt.where((Denuncia.latitud.is_(None)) | (Denuncia.longitud.is_(None)))
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)
    for obj in db.scalars(stmt):
        yield obj


def run(limit: int | None, offset: int | None, dry_run: bool, only_weight: bool, recompute_geo: bool) -> int:
    db: Session = SessionLocal()
    updated = 0
    try:
        batch = 0
        for obj in iter_targets(db, limit, offset, only_weight):
            row = {
                "direccion_ocurrencia": obj.direccion_ocurrencia,
                "tipo_denuncia": obj.tipo_denuncia,
                "resultado_ocurrencia": obj.resultado_ocurrencia,
                "fecha_hora_suceso": obj.fecha_hora_suceso,
                # distrito_ocurrencia may not exist; enrich will default
            }
            enriched = enrich_denuncia_input(row, db, force_recompute_geo=recompute_geo)
            # assign
            obj.latitud = enriched.get("latitud")
            obj.longitud = enriched.get("longitud")
            obj.geocode_precision = enriched.get("geocode_precision")
            try:
                obj.geo_method = enriched.get("geo_method")
            except Exception:
                pass
            obj.geocoded_at = enriched.get("geocoded_at")
            obj.peso = enriched.get("peso")

            updated += 1
            batch += 1
            if not dry_run:
                db.add(obj)
            if batch >= 100 and not dry_run:
                db.commit()
                batch = 0
        if batch > 0 and not dry_run:
            db.commit()
        return updated
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=None)
    p.add_argument('--offset', type=int, default=None)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--only-weight', action='store_true', help='Only recompute peso, skip geocoding filter')
    p.add_argument('--recompute-geo', action='store_true', help='Ignore cache and recompute geocoding')
    args = p.parse_args()
    n = run(args.limit, args.offset, args.dry_run, args.only_weight, args.recompute_geo)
    print(f"Updated {n} rows")
