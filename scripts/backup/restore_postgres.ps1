param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,

    [switch]$Force,
    [string]$LogDir = "backups",
    [string]$DbHost = $env:DB_HOST,
    [string]$DbPort = $(if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }),
    [string]$DbName = $env:DB_NAME,
    [string]$DbUser = $env:DB_USER
)

if (-not (Test-Path -LiteralPath $BackupFile)) {
    throw "No existe el archivo de backup: $BackupFile"
}
if (-not $DbHost) { $DbHost = "localhost" }
if (-not $DbName) { throw "DB_NAME no esta definido." }
if (-not $DbUser) { throw "DB_USER no esta definido." }

$pgRestore = Get-Command pg_restore -ErrorAction SilentlyContinue
if (-not $pgRestore) {
    throw "pg_restore no esta disponible en PATH. Agrega la carpeta bin de PostgreSQL al PATH."
}

if (-not $Force) {
    $answer = Read-Host "Esto restaurara sobre la base '$DbName'. Escribe RESTAURAR para continuar"
    if ($answer -ne "RESTAURAR") {
        Write-Host "Operacion cancelada."
        exit 1
    }
}

$oldPassword = $env:PGPASSWORD
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$logFile = Join-Path $LogDir "restore.log"
try {
    if ($env:DB_PASS) { $env:PGPASSWORD = $env:DB_PASS }
    & pg_restore `
        --clean `
        --if-exists `
        --no-owner `
        --no-privileges `
        --host $DbHost `
        --port $DbPort `
        --username $DbUser `
        --dbname $DbName `
        $BackupFile

    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore termino con codigo $LASTEXITCODE."
    }

    Write-Host "Restauracion completada en la base: $DbName"
    Add-Content -Path $logFile -Value "$(Get-Date -Format s) OK $BackupFile db=$DbName"
}
catch {
    Add-Content -Path $logFile -Value "$(Get-Date -Format s) ERROR $($_.Exception.Message) backup=$BackupFile db=$DbName"
    throw
}
finally {
    $env:PGPASSWORD = $oldPassword
}
