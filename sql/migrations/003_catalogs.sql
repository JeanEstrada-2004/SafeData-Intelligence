-- 003 Generic catalogs for validation and administration

CREATE TABLE IF NOT EXISTS catalog_items (
  id SERIAL PRIMARY KEY,
  category VARCHAR(60) NOT NULL,
  name VARCHAR(160) NOT NULL,
  description TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now() NOT NULL,
  updated_at TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_catalog_category_name ON catalog_items(category, name);
CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category);
CREATE INDEX IF NOT EXISTS idx_catalog_items_active ON catalog_items(is_active);

INSERT INTO catalog_items (category, name, description)
VALUES
  ('turno', 'Mañana', 'Turno operativo diurno inicial'),
  ('turno', 'Tarde', 'Turno operativo diurno final'),
  ('turno', 'Noche', 'Turno operativo nocturno'),
  ('estado', 'Registrada', 'Incidencia registrada en el sistema'),
  ('estado', 'Archivado', 'Incidencia archivada'),
  ('estado', 'Atendido', 'Incidencia atendida'),
  ('estado', 'Derivado', 'Incidencia derivada'),
  ('tipo_incidencia', 'Accidente de tránsito', 'Tipo base de incidencia'),
  ('tipo_incidencia', 'Hurto menor', 'Tipo base de incidencia'),
  ('tipo_incidencia', 'Robo agravado', 'Tipo base de incidencia'),
  ('tipo_incidencia', 'Violencia familiar', 'Tipo base de incidencia'),
  ('tipo_incidencia', 'Lesiones leves', 'Tipo base de incidencia'),
  ('tipo_incidencia', 'Pérdida de documento', 'Tipo base de incidencia'),
  ('fuente_datos', 'Serenazgo', 'Reporte operativo municipal'),
  ('fuente_datos', 'Central de monitoreo', 'Reporte desde central de monitoreo'),
  ('fuente_datos', 'Vecino', 'Reporte ciudadano')
ON CONFLICT (category, name) DO NOTHING;
