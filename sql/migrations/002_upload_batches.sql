-- 002 Upload batches and row-level validation errors

CREATE TABLE IF NOT EXISTS upload_batches (
  id SERIAL PRIMARY KEY,
  filename VARCHAR(180) NOT NULL,
  original_filename VARCHAR(220) NOT NULL,
  uploaded_by_user_id INTEGER REFERENCES users(id),
  uploaded_at TIMESTAMP DEFAULT now() NOT NULL,
  total_rows INTEGER NOT NULL DEFAULT 0,
  accepted_rows INTEGER NOT NULL DEFAULT 0,
  rejected_rows INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(40) NOT NULL DEFAULT 'procesado',
  source_type VARCHAR(20) NOT NULL,
  file_hash VARCHAR(64) NOT NULL,
  message TEXT,
  processing_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_upload_batches_uploaded_at ON upload_batches(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_upload_batches_user ON upload_batches(uploaded_by_user_id);
CREATE INDEX IF NOT EXISTS idx_upload_batches_hash ON upload_batches(file_hash);

CREATE TABLE IF NOT EXISTS upload_errors (
  id SERIAL PRIMARY KEY,
  batch_id INTEGER NOT NULL REFERENCES upload_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  column_name VARCHAR(120),
  raw_value TEXT,
  error_type VARCHAR(80) NOT NULL,
  error_message TEXT NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'error',
  created_at TIMESTAMP DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_upload_errors_batch ON upload_errors(batch_id);
CREATE INDEX IF NOT EXISTS idx_upload_errors_severity ON upload_errors(severity);

ALTER TABLE IF EXISTS denuncias
  ADD COLUMN IF NOT EXISTS source_file VARCHAR(160),
  ADD COLUMN IF NOT EXISTS raw_row_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS upload_batch_id INTEGER REFERENCES upload_batches(id);

CREATE INDEX IF NOT EXISTS idx_denuncias_upload_batch ON denuncias(upload_batch_id);
CREATE INDEX IF NOT EXISTS idx_denuncias_raw_row_hash ON denuncias(raw_row_hash);
CREATE INDEX IF NOT EXISTS idx_denuncias_numero_parte ON denuncias(numero_parte);
