$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$target = Join-Path $root "Data\ZyntaxStore"
$source = Join-Path $env:APPDATA "TheHolyOneZ\ZyntaxAI"
$backupRoot = Join-Path $root "MigrationBackups"

Write-Host ""
Write-Host "ZyntaxAI official-data migration" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source:"
Write-Host "  $source"
Write-Host "Target:"
Write-Host "  $target"
Write-Host ""

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    Write-Host "No official AppData folder was found. Nothing to migrate." -ForegroundColor Yellow
    exit 0
}

New-Item -ItemType Directory -Path $target,$backupRoot -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $backupRoot "TheHolyOneZ-ZyntaxAI-$stamp"

Write-Host "First making a safety backup..."
& robocopy.exe "$source" "$backup" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Backup copy failed. Robocopy exit code: $LASTEXITCODE"
}

Write-Host "Backup created:"
Write-Host "  $backup" -ForegroundColor Green
Write-Host ""
Write-Host "Copying existing settings/history/logs into portable Data..."

& robocopy.exe "$source" "$target" /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Migration copy failed. Robocopy exit code: $LASTEXITCODE"
}

Write-Host ""
Write-Host "Migration completed." -ForegroundColor Green
Write-Host ""
Write-Host "The old AppData folder was NOT deleted."
Write-Host "Start the portable build, verify your settings/history, then optionally run:"
Write-Host "  CLEAN-OLD-HOST-DATA.ps1"
Write-Host ""
Read-Host "Press Enter to close" | Out-Null
