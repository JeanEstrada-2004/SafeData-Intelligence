"""Inicialización de routers del proyecto."""

from .denuncias import router as denuncias_router
from .mapa_calor import router as mapa_calor_router
from .autenticacion import router as auth_router
from .admin_usuarios import router as admin_users_router
from .catalogos import router as catalogos_router
from .auditoria import router as auditoria_router

__all__ = [
    "denuncias_router",
    "mapa_calor_router",
    "auth_router",
    "admin_users_router",
    "catalogos_router",
    "auditoria_router",
]
