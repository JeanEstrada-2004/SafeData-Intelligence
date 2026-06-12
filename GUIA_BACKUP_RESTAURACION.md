# Guia de backup y restauracion

Los scripts estan en `scripts/backup` y usan las variables del `.env` cargadas en la sesion PowerShell.

## Preparar variables

Activa el entorno y carga las variables necesarias:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="safedata_intelligence"
$env:DB_USER="postgres"
$env:DB_PASS="<password>"
```

## Crear backup

```powershell
.\scripts\backup\backup_postgres.ps1 -OutputDir backups -RetentionDays 14
```

Genera un archivo `.dump` en formato custom de PostgreSQL:

```text
backups\safedata_YYYYMMDD_HHMM.dump
```

El resultado queda registrado en `backups\backup.log`.

## Restaurar backup

La restauracion limpia objetos existentes antes de recrearlos. Usala solo contra una base preparada para restauracion.

```powershell
.\scripts\backup\restore_postgres.ps1 -BackupFile backups\safedata_YYYYMMDD_HHMM.dump
```

Para automatizacion controlada:

```powershell
.\scripts\backup\restore_postgres.ps1 -BackupFile backups\safedata_YYYYMMDD_HHMM.dump -Force
```

El resultado queda registrado en `backups\restore.log`.

## Politica recomendada

- Un backup antes de cada migracion.
- Un backup diario mientras el sistema este en uso.
- Conservar al menos 7 copias diarias y 4 semanales.
- Probar una restauracion en una base separada antes de confiar en el respaldo.
- No guardar backups en repositorios Git.

## RPO/RTO sugeridos

- RPO: 24 horas como maximo para operacion normal; menor si la municipalidad carga datos varias veces al dia.
- RTO: 2 a 4 horas para restaurar servicio en un servidor equivalente con PostgreSQL instalado.
