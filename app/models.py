"""SQLAlchemy models for SafeData Intelligence.

Map module notes (2025-11): this file was extended so the existing
`denuncias` table supports georeferencing without creating a new table.
Added columns: latitud, longitud, geocode_status, geocode_precision,
geocoded_at, peso. Used by `/api/map/*` endpoints and the geocode job.
"""

from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Text,
    TIMESTAMP,
    Float,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Boolean, ForeignKey
from datetime import datetime, timedelta

from .database import Base


class Denuncia(Base):
    """Main model (table `denuncias`). Extended for the heatmap module."""

    __tablename__ = "denuncias"

    id = Column(Integer, primary_key=True, index=True)
    numero_parte = Column(String(30), nullable=True)
    estado_denuncia = Column(String(40), nullable=True)
    zona_denuncia = Column(SmallInteger, nullable=False)
    origen_denuncia = Column(String(60), nullable=True)
    naturaleza_personal = Column(String(80), nullable=True)
    forma_patrullaje = Column(String(60), nullable=True)
    turno = Column(String(20), nullable=True)
    fecha_hora_suceso = Column(TIMESTAMP, nullable=False)
    fecha_hora_alerta = Column(TIMESTAMP, nullable=True)
    fecha_hora_llegada = Column(TIMESTAMP, nullable=True)
    edad_victima = Column(SmallInteger, nullable=True)
    sexo_victima = Column(String(20), nullable=True)
    distrito_victima = Column(String(120), nullable=True)
    sexo_victimario = Column(String(20), nullable=True)
    relacion_victima_victimario = Column(String(120), nullable=True)
    tipo_denuncia = Column(String(120), nullable=True)
    arma_instrumento = Column(String(120), nullable=True)
    resultado_ocurrencia = Column(String(160), nullable=True)
    lugar_ocurrencia = Column(String(160), nullable=True)
    direccion_ocurrencia = Column(String(220), nullable=True)
    comentarios = Column(Text, nullable=True)
    source_file = Column(String(160), nullable=True)
    raw_row_hash = Column(String(64), nullable=True)

    # Heatmap/geocoding fields
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    geocode_status = Column(String(20), nullable=False, server_default="pending")
    geocode_precision = Column(String(20), nullable=True)  # LÍNEA 61 CORREGIDA
    geocoded_at = Column(TIMESTAMP, nullable=True)
    geo_method = Column(String(20), nullable=True)
    peso = Column(Numeric(3, 2), nullable=False, server_default="1.00")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class Incidente(Base):
    """Not used anymore. Kept for compatibility only."""

    __tablename__ = "incidentes"
    id = Column(Integer, primary_key=True, index=True)


class GeocodeCache(Base):
    """Local cache for geocoding results."""

    __tablename__ = "geocode_cache"

    direccion = Column(Text, primary_key=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    fuente = Column(String(20), nullable=True)
    precision = Column(String(20), nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Zona(Base):
    """Zones polygons and centroids."""

    __tablename__ = "zonas"

    id_zona = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    geojson = Column(JSONB, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)


# -------------------
# Auth module models
# -------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(160), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(40), nullable=False)  # Gerente|JefeOperaciones|Analista|EncargadoSipCop
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(120), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=False)
    used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class AuditAccess(Base):
    __tablename__ = "audit_access"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(40), nullable=False)  # login_success, login_fail, view, logout, reset_request, reset_ok
    path = Column(String(300), nullable=False)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)



