# SafeData Intelligence

Sistema web para gestion, analisis, prediccion y visualizacion geoespacial de denuncias ciudadanas.

## Componentes principales

- FastAPI + Jinja2 para vistas y API.
- PostgreSQL como base de datos principal.
- Carga de archivos Excel/CSV con validacion, trazabilidad por lote y errores descargables.
- Dashboard analitico, listado filtrable, prediccion de riesgo y mapa de calor con Mapbox.
- Autenticacion por cookie JWT, roles, auditoria y administracion de usuarios.

## Preparacion local

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` con tu base PostgreSQL y token Mapbox si usaras el mapa.

## Migraciones

Ejecuta las migraciones en orden despues de configurar `.env`:

```powershell
python scripts\ejecutar_sql.py sql\migrations\001_auth_audit_hardening.sql
python scripts\ejecutar_sql.py sql\migrations\002_upload_batches.sql
python scripts\ejecutar_sql.py sql\migrations\003_catalogs.sql
python scripts\ejecutar_sql.py sql\migrations\004_prediction_logs.sql
python scripts\ejecutar_sql.py sql\migrations\005_geo_quality.sql
```

Si necesitas crear usuarios demo:

```powershell
python scripts\semilla_admin.py
```

## Ejecutar

```powershell
python run_server.py
```

URL local: `http://localhost:8000`

## Verificacion rapida

```powershell
python -m compileall -q app scripts run_server.py
node --check static\js\mapa_calor.js
```

## Documentacion adicional

- `sql/migrations/README.md`: orden y proposito de migraciones.
- `GUIA_DESPLIEGUE.md`: despliegue local/controlado.
- `GUIA_BACKUP_RESTAURACION.md`: respaldo y restauracion de PostgreSQL.
- `CHANGELOG_MVP.md`: cambios implementados en la mejora MVP.
- `DIAGNOSTICO_TECNICO_SAFEDATA.md`: diagnostico tecnico del proyecto.

## Archivos auxiliares

- `crear_excel.py`, `create_sample_data.py`, `ejemplo_denuncias.xlsx` e `informe_denuncias.xlsx` son recursos de prueba o apoyo local.
- No se ejecutan automaticamente.
- Para datos reales, usa la pantalla `Carga de datos` y conserva la trazabilidad por lote.
