"""Inicialización de routers del proyecto."""

from .denuncias import router as denuncias_router
from .mapa_calor import router as mapa_calor_router
from .auth import router as auth_router
from .admin_users import router as admin_users_router

__all__ = ["denuncias_router", "mapa_calor_router", "auth_router", "admin_users_router"]
