# Migraciones SQL SafeData Intelligence

Estas migraciones son idempotentes y están pensadas para PostgreSQL. Ejecutarlas en orden desde la raíz del proyecto:

```powershell
python scripts\ejecutar_sql.py sql\migrations\001_auth_audit_hardening.sql
python scripts\ejecutar_sql.py sql\migrations\002_upload_batches.sql
python scripts\ejecutar_sql.py sql\migrations\003_catalogs.sql
python scripts\ejecutar_sql.py sql\migrations\004_prediction_logs.sql
python scripts\ejecutar_sql.py sql\migrations\005_geo_quality.sql
```

No eliminan tablas ni columnas existentes.
