"""Geocoding utilities using Nominatim (geopy) with DB + in-memory cache.

Behavior:
- Builds addresses scoped to José Luis Bustamante y Rivero, Arequipa, Perú (defaults from env).
- Uses Nominatim with country_codes='pe'.
- Falls back (configurable) to district centroid when geocoding fails, to keep points within the expected area.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

from sqlalchemy.orm import Session

try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
except Exception:  # pragma: no cover
    Nominatim = None  # type: ignore
    RateLimiter = None  # type: ignore

from ..models import GeocodeCache

_MEM_CACHE: Dict[str, Tuple[Optional[float], Optional[float], str, str]] = {}

# Defaults (can be overridden by .env)
DEFAULT_DISTRITO = os.getenv("DEFAULT_DISTRITO", "José Luis Bustamante y Rivero").strip()
DEFAULT_PROVINCIA = os.getenv("DEFAULT_PROVINCIA", "Arequipa").strip()
DEFAULT_PAIS = os.getenv("DEFAULT_PAIS", "Perú").strip()
GEOCODER_PROVIDER = os.getenv("GEOCODER_PROVIDER", "nominatim").strip().lower()
GEOCODER_EMAIL = os.getenv("GEOCODER_EMAIL", "contacto@demo.local").strip()
GEOCODER_RATE = float(os.getenv("GEOCODER_RATE", "1.0"))
CACHE_TTL_DAYS = int(os.getenv("GEOCODER_CACHE_TTL_DAYS", "180"))

# Optional centroid fallback if geocoding fails
GEO_FALLBACK_TO_CENTROID = os.getenv("GEO_FALLBACK_TO_CENTROID", "true").lower() in ("1","true","yes","y")
DEFAULT_CENTROID_LAT = float(os.getenv("DEFAULT_CENTROID_LAT", "-16.4225"))
DEFAULT_CENTROID_LON = float(os.getenv("DEFAULT_CENTROID_LON", "-71.5230"))


_ABBREVS = {
    " av. ": " avenida ",
    " jr. ": " jirón ",
    " jr ": " jirón ",
    " psje ": " pasaje ",
    " psj ": " pasaje ",
    " cll ": " calle ",
}


def _fix_common_variants(text: str) -> str:
    s = text.lower()
    # Normalize common variants for the district name
    s = s.replace("jose ", "josé ")
    s = s.replace("riveros", "rivero")
    return s


def normalize_address(direccion: Optional[str], distrito: Optional[str]) -> str:
    d = (direccion or "").strip()
    repl = f" {d.lower()} "
    for k, v in _ABBREVS.items():
        repl = repl.replace(k, v)
    d_norm = repl.strip().title() if d else ""

    dist_raw = (distrito or DEFAULT_DISTRITO).strip()
    dist = _fix_common_variants(dist_raw).title()

    # Build full address. For Nominatim, using plain 'Peru' helps sometimes.
    country = "Peru" if DEFAULT_PAIS.lower().startswith("per") else DEFAULT_PAIS
    parts = [p for p in [d_norm, dist, DEFAULT_PROVINCIA, country] if p]
    return ", ".join(parts)


def _precision_from_raw(raw: dict) -> str:
    t = str(raw.get("type") or raw.get("addresstype") or "").lower()
    if t in ("house", "building"):
        return "rooftop"
    if t in ("street_number", "address") or "interpolation" in t:
        return "interpolated"
    if t in ("neighbourhood", "suburb", "city_district"):
        return "centroid"
    return "approx"


def _nominatim_geocode(full_address: str) -> Tuple[Optional[float], Optional[float], str, str]:
    if Nominatim is None or RateLimiter is None:
        return None, None, "none", "n/a"
    user_agent = f"safedata-intelligence/{GEOCODER_EMAIL}" if GEOCODER_EMAIL else "safedata-intelligence"
    geolocator = Nominatim(user_agent=user_agent)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=max(GEOCODER_RATE, 1.0))

    # Nominatim works better with 'Peru' sometimes, so try a variant
    query = full_address.replace("Perú", "Peru")

    try:
        loc = geocode(query, addressdetails=True, timeout=10, country_codes="pe", limit=1)
        if not loc:
            return None, None, "none", "n/a"
        lat, lon = float(loc.latitude), float(loc.longitude)
        precision = _precision_from_raw(getattr(loc, "raw", {}) or {})
        return lat, lon, precision, "nominatim"
    except Exception:
        return None, None, "none", "n/a"


def geocode_address(full_address: str, db: Session, *, force_recompute: bool = False) -> Tuple[Optional[float], Optional[float], str, str]:
    """Geocode with in-memory + DB cache and optional centroid fallback."""
    key = (full_address or "").strip()
    if not key:
        return None, None, "none", "n/a"

    # in-memory cache first
    if not force_recompute and key in _MEM_CACHE:
        return _MEM_CACHE[key]

    # DB cache
    cached: Optional[GeocodeCache] = db.get(GeocodeCache, key)
    if cached and not force_recompute:
        if cached.updated_at and cached.updated_at >= datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS):
            res = (cached.latitud, cached.longitud, cached.precision or "approx", cached.fuente or "nominatim")
            _MEM_CACHE[key] = res
            return res

    lat, lon, precision, method = _nominatim_geocode(key) if GEOCODER_PROVIDER == "nominatim" else (None, None, "none", "n/a")

    # Optional centroid fallback to keep points within the intended district
    if (lat is None or lon is None) and GEO_FALLBACK_TO_CENTROID:
        lat, lon = DEFAULT_CENTROID_LAT, DEFAULT_CENTROID_LON
        precision, method = "centroid", "manual"

    # upsert cache (defer commit to caller)
    if cached is None:
        cached = GeocodeCache(
            direccion=key,
            latitud=lat,
            longitud=lon,
            fuente=method,
            precision=precision,
        )
    else:
        cached.latitud = lat
        cached.longitud = lon
        cached.fuente = method
        cached.precision = precision
    db.add(cached)

    res = (lat, lon, precision, method)
    _MEM_CACHE[key] = res
    return res
