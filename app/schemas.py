# app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List

# Campos que mostramos/filtramos en las plantillas
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
    # Para el endpoint de carga cuando lo modernicemos
    pass

class DenunciaResponse(DenunciaBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # pydantic v2

class DashboardStats(BaseModel):
    total_denuncias: int
    # Bloques actuales del dashboard
    denuncias_por_zona: Dict[int, int]           # {1:12, 2:9, ...}
    denuncias_por_turno: Dict[str, int]          # {"Mañana": 20, ...}
    tipos_denuncia: Dict[str, int]               # {"Robo agravado": 7, ...}

    # Nuevos bloques
    estados_denuncia: Dict[str, int]             # {"Derivado": 30, "Atendido": 60, "Detenido": 30}
    mes_actual_labels: List[str]                 # ["01","02",...]
    mes_actual_counts: List[int]                 # [3,0,5,...]
    ult_3_meses_labels: List[str]                # ["Ago 2025","Sep 2025","Oct 2025"]
    ult_3_meses_counts: List[int]                # [20,38,62]
