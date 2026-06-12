-- 004 Prediction logs and model metadata

CREATE TABLE IF NOT EXISTS prediction_logs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  requested_at TIMESTAMP DEFAULT now() NOT NULL,
  input_json JSONB NOT NULL,
  output_json JSONB NOT NULL,
  model_type VARCHAR(40) NOT NULL,
  model_version VARCHAR(80),
  risk_level VARCHAR(30)
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_user ON prediction_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_requested ON prediction_logs(requested_at);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_risk ON prediction_logs(risk_level);

CREATE TABLE IF NOT EXISTS model_metadata (
  id SERIAL PRIMARY KEY,
  version VARCHAR(80) NOT NULL UNIQUE,
  trained_at TIMESTAMP,
  dataset_summary JSONB,
  accuracy DOUBLE PRECISION,
  f1_score DOUBLE PRECISION,
  confusion_matrix JSONB,
  model_path VARCHAR(260),
  created_at TIMESTAMP DEFAULT now() NOT NULL
);
