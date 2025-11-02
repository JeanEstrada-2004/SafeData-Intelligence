"""Job de geocodificación offline para la tabla `denuncias`.

Notas (2025-11):
- Usa Nominatim (1 req/seg) con caché local (`geocode_cache`).
- Actualiza columnas añadidas al modelo `Denuncia` (lat/lon, status, peso).
- Se mantiene independiente del API para ejecutarse desde consola.

Ejemplo:
    python -m app.services.geocode_job --batch 500
"""
from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import datetime
from typing import Optional, Tuple

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import GeocodeCache, Denuncia, Zona

LOGGER = logging.getLogger("app.services.geocode")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SafeData-Intelligence/1.0 (contact: soporte@safedata.local)"
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
_LAST_REQUEST_TS = 0.0

_ABBREVIATIONS = (
    (r"\bAv\.?\b", "Avenida"),
    (r"\bJr\.?\b", "Jiron"),
    (r"\bJr\.?\b", "Jiron"),
    (r"\bC\.?\s*\b", "Calle "),
    (r"\bMz\.?\b", "Manzana"),
    (r"\bLt\.?\b", "Lote"),
    (r"\bPje\.?\b", "Pasaje"),
    (r"\bUrb\.?\b", "Urbanizacion"),
    (r"\bPsje\.?\b", "Pasaje"),
    (r"\bFracc\.?\b", "Fraccionamiento"),
)

_WEIGHT_RULES = {
    "robo": 1.00,
    "robo agravado": 1.00,
    "hurto": 0.80,
    "lesiones": 0.90,
    "violencia": 0.90,
}


def normalize_address(raw: Optional[str]) -> str:
    """Normaliza la direcciÃ³n y agrega la localidad completa."""

    text = (raw or "").strip()
    if not text:
        return ""

    text = re.sub(r"[\n\r]+", " ", text)
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"[^0-9A-Za-zÃÃ‰ÃÃ“ÃšÃœÃ‘Ã¡Ã©Ã­Ã³ÃºÃ¼Ã±#\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    return f"{text}, JosÃ© Luis Bustamante y Rivero, Arequipa, PerÃº"


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def compute_weight(tipo: Optional[str]) -> float:
    """Calcula la ponderaciÃ³n del heatmap segÃºn el tipo de denuncia."""

    if not tipo:
        return 0.60

    key = tipo.lower()
    for label, weight in _WEIGHT_RULES.items():
        if label in key:
            return clamp(weight, 0.30, 1.20)
    return 0.60


def _respect_rate_limit() -> None:
    global _LAST_REQUEST_TS
    elapsed = time.time() - _LAST_REQUEST_TS
    if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
        time.sleep(MIN_SECONDS_BETWEEN_REQUESTS - elapsed)


def _map_precision(result: dict) -> str:
    place_type = (result.get("type") or "").lower()
    place_class = (result.get("class") or "").lower()
    if place_type in {"building", "house", "yes"} or place_class == "building":
        return "rooftop"
    if place_type in {"residential", "tertiary", "primary", "secondary", "street"} or place_class == "highway":
        return "street"
    return "approx"


def geocode_with_nominatim(query: str) -> Optional[Tuple[float, float, str]]:
    """Consulta a Nominatim aplicando el rate limit definido."""

    if not query:
        return None

    _respect_rate_limit()
    params = {"format": "json", "limit": 1, "q": query}
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=30)

    global _LAST_REQUEST_TS
    _LAST_REQUEST_TS = time.time()

    if response.status_code != 200:
        LOGGER.warning("Nominatim devolviÃ³ %s para '%s'", response.status_code, query)
        return None

    payload = response.json()
    if not payload:
        return None

    item = payload[0]
    lat = float(item["lat"])
    lon = float(item["lon"])
    precision = _map_precision(item)
    return lat, lon, precision


def geocode_denuncia(session: Session, denuncia: Denuncia) -> Tuple[Optional[float], Optional[float], str, Optional[str]]:
    """Obtiene latitud/longitud usando cachÃ© y Nominatim."""

    query = normalize_address(denuncia.direccion_ocurrencia or denuncia.lugar_ocurrencia)
    if not query:
        return None, None, "fail", None

    cache = session.get(GeocodeCache, query)
    if cache and cache.latitud is not None and cache.longitud is not None:
        LOGGER.debug("Cache hit para '%s'", query)
        return cache.latitud, cache.longitud, "ok", cache.precision or "approx"

    result = geocode_with_nominatim(query)
    if result is None:
        return None, None, "fail", None

    lat, lon, precision = result
    cache_entry = GeocodeCache(
        direccion=query,
        latitud=lat,
        longitud=lon,
        fuente="nominatim",
        precision=precision,
    )
    session.merge(cache_entry)
    session.flush()
    return lat, lon, "ok", precision


def fallback_to_zone_centroid(session: Session, denuncia: Denuncia) -> Tuple[Optional[float], Optional[float]]:
    if denuncia.zona_denuncia is None:
        return None, None
    zone = session.get(Zona, denuncia.zona_denuncia)
    if not zone:
        return None, None
    return zone.centroid_lat, zone.centroid_lon


def process_batch(session: Session, batch_size: int) -> int:
    stmt = (
        select(Denuncia)
        .where(
            (Denuncia.latitud.is_(None))
            | (Denuncia.longitud.is_(None))
            | Denuncia.geocode_status.in_(["pending", "fail"])
        )
        .order_by(Denuncia.id)
        .limit(batch_size)
    )
    denuncias = session.scalars(stmt).all()
    if not denuncias:
        LOGGER.info("No hay incidentes pendientes de geocodificar.")
        return 0

    procesados = 0
    for denuncia in denuncias:
        peso = compute_weight(denuncia.tipo_denuncia)
        lat, lon, status, precision = geocode_denuncia(session, denuncia)

        if lat is None or lon is None:
            lat, lon = fallback_to_zone_centroid(session, denuncia)
            if lat is not None and lon is not None:
                status = "approx"
                precision = "centroid"
            else:
                status = "fail"
                precision = None

        denuncia.latitud = lat
        denuncia.longitud = lon
        denuncia.geocode_status = status
        denuncia.geocode_precision = precision
        denuncia.geocoded_at = datetime.utcnow()
        denuncia.peso = peso
        session.add(denuncia)
        procesados += 1
        LOGGER.info(
            "Denuncia %s geocodificada (%s) -> lat=%s lon=%s",
            denuncia.id,
            status,
            lat,
            lon,
        )

    session.commit()
    return procesados


def main(batch: int) -> None:
    LOGGER.info("Iniciando geocodificaciÃ³n para lote de hasta %s incidentes", batch)
    session = SessionLocal()
    try:
        processed = process_batch(session, batch)
        LOGGER.info("Proceso finalizado. Incidentes actualizados: %s", processed)
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geocodificador offline de incidentes")
    parser.add_argument("--batch", type=int, default=200, help="Cantidad mÃ¡xima de incidentes a procesar")
    args = parser.parse_args()
    main(args.batch)



