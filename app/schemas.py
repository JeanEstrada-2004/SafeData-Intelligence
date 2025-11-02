"""Esquemas Pydantic utilizados por la aplicación."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class DenunciaBase(BaseModel):
    zona_denuncia: Optional[int] = None
    turno: Optional[str] = None
    fecha_hora_suceso: Optional[datetime] = None
    tipo_denuncia: Optional[str] = None
    lugar_ocurrencia: Optional[str] = None
    resultado_ocurrencia: Optional[str] = None
    sexo_victima: Optional[str] = None
    edad_victima: Optional[int] = None
    comentarios: Optional[str] = None


class DenunciaCreate(DenunciaBase):
    """Placeholder para futuras operaciones de creación."""


class DenunciaResponse(DenunciaBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_denuncias: int
    denuncias_por_zona: Dict[int, int]
    denuncias_por_turno: Dict[str, int]
    tipos_denuncia: Dict[str, int]
    estados_denuncia: Dict[str, int]
    mes_actual_labels: List[str]
    mes_actual_counts: List[int]
    ult_3_meses_labels: List[str]
    ult_3_meses_counts: List[int]


class MapDateRange(BaseModel):
    """Rango mínimo y máximo de fechas disponibles."""

    min: Optional[str] = None
    max: Optional[str] = None


class MapFilters(BaseModel):
    """Opciones disponibles para el módulo de mapa."""

    tipos: List[str]
    turnos: List[str]
    zonas: List[int]
    fecha: MapDateRange


class MapPoint(BaseModel):
    """Representa un incidente proyectado en el mapa."""

    id: int
    lat: float
    lon: float
    peso: float
    tipo: Optional[str] = None
    turno: Optional[str] = None
    fecha: datetime
    zona: Optional[int] = None
    direccion: Optional[str] = None

    class Config:
        from_attributes = True


class ZoneFeature(BaseModel):
    """Elemento GeoJSON simplificado para las zonas operativas."""

    id_zona: int
    nombre: str
    geojson: Dict[str, object]
    centroid: List[float]

    class Config:
        from_attributes = True


# -------------------
# Auth module schemas
# -------------------

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool = True


class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    email: str
    exp: int


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
