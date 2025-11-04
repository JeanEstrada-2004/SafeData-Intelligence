"""Heat weight computation utilities for map weighting.

Maps crime types to base weights, adjusts by result, and applies
exponential time decay. Returns a value in [0.0, 1.0] rounded to 2 decimals.
"""
from __future__ import annotations

from datetime import datetime
import math
from typing import Optional


_BASE_TABLE = {
    # High severity
    "Homicidio": 1.00,
    "Violación sexual": 0.95,
    "Robo agravado": 0.90,
    # Medium-high
    "Lesiones graves": 0.75,
    "Amenazas": 0.70,
    "Extorsión": 0.70,
    "Secuestro": 0.70,
    # Medium
    "Lesiones leves": 0.60,
    "Acoso sexual": 0.60,
    # Lower
    "Hurto menor": 0.40,
    "Estafa": 0.40,
    "Daño a la propiedad": 0.40,
    # Other common categories
    "Pérdida de documento": 0.30,
    "Daño ambiental": 0.30,
    "Persona desaparecida": 0.30,
    "Emergencia médica": 0.30,
}


def _normalize_text(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def base_weight(tipo: Optional[str]) -> float:
    t = (tipo or "").strip()
    if not t:
        return 0.40
    # direct match
    if t in _BASE_TABLE:
        return float(_BASE_TABLE[t])
    # case-insensitive contains
    low = t.lower()
    for key, val in _BASE_TABLE.items():
        if key.lower() in low or low in key.lower():
            return float(val)
    return 0.40


def result_adj(resultado: Optional[str]) -> float:
    r = _normalize_text(resultado)
    if not r:
        return 0.0
    if "consum" in r:      # consumado, consumada
        return 0.10
    if "frustr" in r:      # frustrado
        return -0.10
    if "intent" in r:      # intentado
        return -0.05
    if "disuas" in r:      # disuasivo/disuadido
        return -0.05
    return 0.0


def decay(fecha_suceso: Optional[datetime]) -> float:
    if not fecha_suceso:
        return 1.0
    delta_days = max(0.0, (datetime.utcnow() - fecha_suceso).days)
    # half-life around ~124 days (since ln(2)*180 ≈ 124.7)
    return math.exp(- delta_days / 180.0)


def compute_heat_weight(tipo: Optional[str], resultado: Optional[str], fecha_suceso: Optional[datetime]) -> float:
    w = (base_weight(tipo) + result_adj(resultado)) * decay(fecha_suceso)
    w = max(0.0, min(1.0, w))
    return round(w, 2)
