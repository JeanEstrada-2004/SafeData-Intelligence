-- Migration: add/ensure geospatial and heat columns and cache table
-- Safe to re-run (IF NOT EXISTS guards)

-- Extend `denuncias` with required columns if missing
ALTER TABLE IF EXISTS denuncias
  ADD COLUMN IF NOT EXISTS latitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS geocode_precision VARCHAR(20),
  ADD COLUMN IF NOT EXISTS geo_method VARCHAR(20),
  ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS peso NUMERIC(3,2) DEFAULT 1.00;

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_denuncias_latlon ON denuncias (latitud, longitud);

-- Geocoding cache table (we reuse existing name if present)
CREATE TABLE IF NOT EXISTS geocode_cache (
  direccion TEXT PRIMARY KEY,
  latitud DOUBLE PRECISION,
  longitud DOUBLE PRECISION,
  fuente VARCHAR(20),
  precision VARCHAR(20),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geocode_cache_updated ON geocode_cache (updated_at);
