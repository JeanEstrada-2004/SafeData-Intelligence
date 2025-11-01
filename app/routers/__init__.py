# app/__init__.py
"""
Sistema de Gestión de Denuncias Ciudadanas
Aplicación web desarrollada con FastAPI para la gestión de denuncias policiales.
"""

__version__ = "1.0.0"
__author__ = "Sistema de Denuncias"
__description__ = "Plataforma web para gestión de denuncias ciudadanas"

# app/routers/__init__.py
"""
Módulo de rutas para la API del sistema de denuncias.
"""

from .denuncias import router as denuncias_router

__all__ = ["denuncias_router"]