$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackupDir = Join-Path $Root "backups"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Stage = Join-Path $env:TEMP "forgemind-backup-$Stamp"
$Archive = Join-Path $BackupDir "ForgeMind-Local-Data-$Stamp.zip"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

$Database = Join-Path $Root "backend\forgemind.db"
$Storage = Join-Path $Root "backend\storage"
$Models = Join-Path $Root "backend\ml\models"
$BackendEnv = Join-Path $Root "backend\.env"
$FrontendEnv = Join-Path $Root "frontend\.env.local"

if (Test-Path $Database) { Copy-Item $Database $Stage }
if (Test-Path $Storage) { Copy-Item $Storage (Join-Path $Stage "storage") -Recurse }
if (Test-Path $Models) { Copy-Item $Models (Join-Path $Stage "models") -Recurse }
if (Test-Path $BackendEnv) { Copy-Item $BackendEnv (Join-Path $Stage "backend.env") }
if (Test-Path $FrontendEnv) { Copy-Item $FrontendEnv (Join-Path $Stage "frontend.env.local") }

if ((Get-ChildItem $Stage -Force | Measure-Object).Count -eq 0) {
    Remove-Item $Stage -Recurse -Force
    throw "No ForgeMind runtime data exists yet. Start the application first."
}

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Archive -Force
Remove-Item $Stage -Recurse -Force
Write-Host "Backup created:" -ForegroundColor Green
Write-Host $Archive
