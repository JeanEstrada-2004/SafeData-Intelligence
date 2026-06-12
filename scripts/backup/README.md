# Backup PostgreSQL

Scripts operativos:

- `backup_postgres.ps1`: genera backup con `pg_dump`.
- `restore_postgres.ps1`: restaura backup con `pg_restore`.

Ejemplo de backup:

```powershell
.\scripts\backup\backup_postgres.ps1 -OutputDir backups -RetentionDays 14
```

Ejemplo de restauracion:

```powershell
.\scripts\backup\restore_postgres.ps1 -BackupFile backups\safedata_YYYYMMDD_HHMM.dump
```

Los scripts usan `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASS`.

Los logs se generan en:

- `backups\backup.log`
- `backups\restore.log`

No guardes respaldos dentro de Git.
