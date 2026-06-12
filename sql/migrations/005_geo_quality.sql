-- 005 Geocoding quality cleanup
-- Existing coordinates should not remain pending.

ALTER TABLE IF EXISTS denuncias
  ADD COLUMN IF NOT EXISTS latitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitud DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS geocode_status VARCHAR(20) DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS geocode_precision VARCHAR(20),
  ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS geo_method VARCHAR(20),
  ADD COLUMN IF NOT EXISTS peso NUMERIC(3,2) DEFAULT 1.00;

UPDATE denuncias
SET geocode_status = CASE
  WHEN geocode_precision = 'centroid' THEN 'approx'
  WHEN geocode_precision IS NOT NULL THEN 'ok'
  ELSE 'ok'
END
WHERE latitud IS NOT NULL
  AND longitud IS NOT NULL
  AND (geocode_status IS NULL OR geocode_status = 'pending');

CREATE INDEX IF NOT EXISTS idx_denuncias_geocode_status ON denuncias(geocode_status);
CREATE INDEX IF NOT EXISTS idx_denuncias_latlon ON denuncias(latitud, longitud);
