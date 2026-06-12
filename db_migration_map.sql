-- Migración para el módulo de mapa de calor
-- Complemento a 005_geo_quality.sql para completar tabla de soporte y mejoras
-- Notas (2025-11):
--  - Asegura que existan tablas de apoyo (`geocode_cache`, `zonas`) e índices
--  - Las columnas de denuncias ya están creadas en 005_geo_quality.sql

-- Agregar columna geo_method si no existe (puede faltar en algunas versiones)
ALTER TABLE IF EXISTS denuncias
  ADD COLUMN IF NOT EXISTS geo_method VARCHAR(20);

-- Crear tablas de soporte si no existen
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

-- Crear índices necesarios para rendimiento
CREATE INDEX IF NOT EXISTS idx_denuncias_fecha ON denuncias (fecha_hora_suceso);
CREATE INDEX IF NOT EXISTS idx_denuncias_tipo  ON denuncias (tipo_denuncia);
CREATE INDEX IF NOT EXISTS idx_denuncias_turno ON denuncias (turno);
CREATE INDEX IF NOT EXISTS idx_denuncias_zona  ON denuncias (zona_denuncia);
CREATE INDEX IF NOT EXISTS idx_denuncias_latlon ON denuncias (latitud, longitud);
CREATE INDEX IF NOT EXISTS idx_denuncias_geocode_status ON denuncias (geocode_status);
