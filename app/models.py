# app/models.py
from sqlalchemy import Column, Integer, String, SmallInteger, Text, TIMESTAMP, func
from .database import Base

class Denuncia(Base):
    __tablename__ = "denuncias"

    id = Column(Integer, primary_key=True, index=True)

    # Nuevos campos (según tu diseño en DBeaver)
    numero_parte = Column(String(30), nullable=True)
    estado_denuncia = Column(String(40), nullable=True)

    zona_denuncia = Column(SmallInteger, nullable=False)  # 1..7

    origen_denuncia = Column(String(60), nullable=True)
    naturaleza_personal = Column(String(80), nullable=True)
    forma_patrullaje = Column(String(60), nullable=True)

    turno = Column(String(20), nullable=True)  # Mañana/Tarde/Noche

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

    # Metadatos/ETL
    source_file = Column(String(160), nullable=True)
    raw_row_hash = Column(String(64), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
