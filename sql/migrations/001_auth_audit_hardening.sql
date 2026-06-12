-- 001 Auth/audit hardening
-- Adds optional audit metadata columns without removing existing data.

ALTER TABLE IF EXISTS audit_access
  ADD COLUMN IF NOT EXISTS method VARCHAR(12),
  ADD COLUMN IF NOT EXISTS status VARCHAR(30),
  ADD COLUMN IF NOT EXISTS detail_json JSONB;

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_access(action);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_access(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_path ON audit_access(path);
