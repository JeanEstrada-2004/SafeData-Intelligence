"""Enrichment service for Denuncia rows (geocode + heat weight).

- Enriches incoming Excel-parsed rows on the fly
- Also used by backfill script

Fields populated (keeping compatibility with existing model):
  - latitud, longitud
  - geocode_precision (precision)
  - geo_method (new)
  - geocoded_at
  - peso (heat weight)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..utils.geocoder import normalize_address, geocode_address
from ..utils.heat import compute_heat_weight


def _get_distrito_ocurrencia(row: Dict[str, Any]) -> Optional[str]:
    # We must NEVER use `distrito_victima` for place of occurrence.
    # If dataset provides an explicit field (e.g., distrito_ocurrencia), prefer it.
    for key in ("distrito_ocurrencia", "distrito_hecho", "distrito"):  # last one only as a fallback if dataset uses generic name
        if key in row and row[key]:
            return str(row[key]).strip()
    return None


def enrich_denuncia_input(row: Dict[str, Any], db: Session, *, force_recompute_geo: bool = False) -> Dict[str, Any]:
    direccion = str(row.get("direccion_ocurrencia") or "").strip()
    distrito = _get_distrito_ocurrencia(row)
    tipo = row.get("tipo_denuncia")
    resultado = row.get("resultado_ocurrencia")

    fecha_suceso = row.get("fecha_hora_suceso")
    # Allow datetime strings (already parsed upstream in router)

    full_addr = normalize_address(direccion, distrito)
    lat, lon, precision, method = geocode_address(full_addr, db, force_recompute=force_recompute_geo)

    weight = compute_heat_weight(tipo, resultado, fecha_suceso)

    out = dict(row)
    out.update(
        {
            "latitud": lat,
            "longitud": lon,
            "geocode_precision": precision,
            "geo_method": method,
            "geocoded_at": datetime.utcnow(),
            "peso": weight,
        }
    )
    return out
