param(
    [string]$OutputDir = "backups",
    [string]$Prefix = "safedata",
    [int]$RetentionDays = 0,
    [string]$DbHost = $env:DB_HOST,
    [string]$DbPort = $(if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }),
    [string]$DbName = $env:DB_NAME,
    [string]$DbUser = $env:DB_USER
)

if (-not $DbHost) { $DbHost = "localhost" }
if (-not $DbName) { throw "DB_NAME no esta definido." }
if (-not $DbUser) { throw "DB_USER no esta definido." }

$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
    throw "pg_dump no esta disponible en PATH. Agrega la carpeta bin de PostgreSQL al PATH."
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$backupFile = Join-Path $OutputDir "$Prefix`_$timestamp.dump"
$logFile = Join-Path $OutputDir "backup.log"

$oldPassword = $env:PGPASSWORD
try {
    if ($env:DB_PASS) { $env:PGPASSWORD = $env:DB_PASS }
    & pg_dump `
        --format=custom `
        --no-owner `
        --no-privileges `
        --host $DbHost `
        --port $DbPort `
        --username $DbUser `
        --file $backupFile `
        $DbName

    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump termino con codigo $LASTEXITCODE."
    }

    Write-Host "Backup generado: $backupFile"
    Add-Content -Path $logFile -Value "$(Get-Date -Format s) OK $backupFile db=$DbName"

    if ($RetentionDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-$RetentionDays)
        Get-ChildItem -LiteralPath $OutputDir -Filter "$Prefix`_*.dump" |
            Where-Object { $_.LastWriteTime -lt $cutoff } |
            ForEach-Object {
                Remove-Item -LiteralPath $_.FullName -Force
                Add-Content -Path $logFile -Value "$(Get-Date -Format s) RETENTION_DELETE $($_.FullName)"
            }
    }
}
catch {
    Add-Content -Path $logFile -Value "$(Get-Date -Format s) ERROR $($_.Exception.Message) db=$DbName"
    throw
}
finally {
    $env:PGPASSWORD = $oldPassword
}
