$ErrorActionPreference = "Stop"

$source = Join-Path $env:APPDATA "TheHolyOneZ\ZyntaxAI"

Write-Host ""
Write-Host "Remove old ZyntaxAI host AppData" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will delete:"
Write-Host "  $source" -ForegroundColor Yellow
Write-Host ""
Write-Host "Use this ONLY after:"
Write-Host "  1. MIGRATE-OFFICIAL-DATA.ps1 succeeded"
Write-Host "  2. the portable build shows your settings/history correctly"
Write-Host ""

$answer = Read-Host "Type DELETE to continue"
if ($answer -cne "DELETE") {
    Write-Host "Cancelled."
    exit 0
}

if (Test-Path -LiteralPath $source -PathType Container) {
    Remove-Item -LiteralPath $source -Recurse -Force
    Write-Host "Removed old host AppData folder." -ForegroundColor Green
} else {
    Write-Host "Old host AppData folder is already absent." -ForegroundColor DarkGray
}

Read-Host "Press Enter to close" | Out-Null
