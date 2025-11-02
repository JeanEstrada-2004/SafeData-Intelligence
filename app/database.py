# app/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

# 1) Si hay DATABASE_URL completa en el entorno, úsala tal cual.
DATABASE_URL_ENV = os.getenv("DATABASE_URL", "").strip()

DB_HOST = os.getenv("DB_HOST", "dpg-d42p5np5pdvs73da3i2g-a.oregon-postgres.render.com").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "denuncias_db").strip()
DB_USER = os.getenv("DB_USER", "denuncias_db_user").strip()
DB_PASS = os.getenv("DB_PASS", "U25F3n8UmYoghcKe6cR7La3AEh55OaZf").strip()

def _is_local(host: str) -> bool:
    h = (host or "").lower()
    return h in ("localhost", "127.0.0.1", "::1") or h.endswith(".local")

def _build_url() -> str:
    # Si viene DATABASE_URL (completa), úsala sin tocar.
    if DATABASE_URL_ENV:
        return DATABASE_URL_ENV

    # Construye a partir de partes. Agrega sslmode=require SOLO si no es local.
    base = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if _is_local(DB_HOST):
        return base  # sin SSL
    return base + "?sslmode=require"  # Render u otros remotos

DATABASE_URL = _build_url()

# Motor y sesiones
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # evita conexiones muertas
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- Diagnóstico ----
def quick_db_check():
    """
    Devuelve versión de Postgres y conteo de filas en public.denuncias.
    Útil para /health/db.
    """
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        total = None
        try:
            total = conn.execute(text("SELECT COUNT(*) FROM public.denuncias")).scalar()
        except Exception as e:
            # La tabla puede no existir aún: lo reportamos como warning en la versión
            version = f"{version} (warn: {e})"
        return {"version": version, "denuncias": 0 if total is None else int(total)}

