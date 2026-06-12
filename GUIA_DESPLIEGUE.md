# Guia de despliegue local/controlado

Esta guia describe una instalacion limpia de SafeData Intelligence en entorno local o servidor institucional.

## 1. Requisitos

- Python 3.11 o compatible.
- PostgreSQL 14 o superior.
- Node.js solo para validar JavaScript con `node --check`.
- Acceso a `pg_dump` y `pg_restore` si se usaran backups.
- Token publico de Mapbox restringido por dominio para produccion.

## 2. Entorno Python

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Variables de entorno

```powershell
Copy-Item .env.example .env
```

Configura al menos:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASS`
- `SECRET_KEY`
- `MAPBOX_ACCESS_TOKEN`

En produccion usa:

```env
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=<valor-largo-y-aleatorio>
```

## 4. Base de datos

Crea la base en PostgreSQL y ejecuta migraciones:

```powershell
python scripts\ejecutar_sql.py sql\migrations\001_auth_audit_hardening.sql
python scripts\ejecutar_sql.py sql\migrations\002_upload_batches.sql
python scripts\ejecutar_sql.py sql\migrations\003_catalogs.sql
python scripts\ejecutar_sql.py sql\migrations\004_prediction_logs.sql
python scripts\ejecutar_sql.py sql\migrations\005_geo_quality.sql
```

Luego crea o valida el usuario inicial:

```powershell
python scripts\semilla_admin.py
```

## 5. Ejecutar aplicacion

```powershell
python run_server.py
```

Acceso local:

- Aplicacion: `http://localhost:8000`
- Documentacion API: `http://localhost:8000/docs`

## 6. Verificaciones

Sin iniciar el servidor:

```powershell
python -m compileall -q app scripts run_server.py
node --check static\js\mapa_calor.js
```

Con servidor iniciado y sesion autorizada:

- `/health`
- `/health/db`
- `/health/stats`

`/health` es publico y no expone datos sensibles. Los endpoints con detalles de base requieren rol tecnico/gerencial.

## 7. Recomendaciones de produccion

- Restringir el token Mapbox por dominio.
- Usar HTTPS.
- Configurar backups programados.
- No publicar `.env`.
- No activar `APP_DEBUG=true` fuera de desarrollo.
- Mantener al menos un usuario `Gerente` activo.

## 8. Monitoreo externo opcional

UptimeRobot:

- Crear monitor HTTP hacia `/health`.
- Frecuencia sugerida: 5 minutos.
- No usar `/health/db` como monitor publico porque requiere autenticacion y contiene datos operativos.

Netdata:

- Puede instalarse en el servidor para observar CPU, memoria, disco, red y proceso Python/Uvicorn.
- Configurar alertas de espacio libre en disco, especialmente si los backups se guardan localmente.
- Mantener logs de aplicacion y logs de backup fuera de carpetas publicas.
