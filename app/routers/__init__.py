"""Inicialización de routers del proyecto."""

from .denuncias import router as denuncias_router
from .mapa_calor import router as mapa_calor_router

__all__ = ["denuncias_router", "mapa_calor_router"]
