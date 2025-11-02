-- Migración para el módulo de mapa de calor
-- Notas (2025-11):
--  - Extiende la tabla existente `denuncias` con columnas de geocodificación.
--  - Crea tablas de apoyo (`geocode_cache`, `zonas`) y sus índices.

ALTER TABLE denuncias
  ADD COLUMN IF NOT EXISTS latitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS geocode_status VARCHAR(20) DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS geocode_precision VARCHAR(20),
  ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS peso NUMERIC(3,2) DEFAULT 1.00;

CREATE TABLE IF NOT EXISTS geocode_cache (
  direccion TEXT PRIMARY KEY,
  latitud DOUBLE PRECISION,
  longitud DOUBLE PRECISION,
  fuente VARCHAR(20),
  precision VARCHAR(20),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zonas (
  id_zona INT PRIMARY KEY,
  nombre  TEXT NOT NULL,
  geojson JSONB NOT NULL,
  centroid_lat DOUBLE PRECISION NOT NULL,
  centroid_lon DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_denuncias_fecha ON denuncias (fecha_hora_suceso);
CREATE INDEX IF NOT EXISTS idx_denuncias_tipo  ON denuncias (tipo_denuncia);
CREATE INDEX IF NOT EXISTS idx_denuncias_turno ON denuncias (turno);
CREATE INDEX IF NOT EXISTS idx_denuncias_zona  ON denuncias (zona_denuncia);
CREATE INDEX IF NOT EXISTS idx_denuncias_latlon ON denuncias (latitud, longitud);
