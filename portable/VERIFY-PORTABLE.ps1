$root = $PSScriptRoot
$reportDir = Join-Path $root "Verification"
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$report = Join-Path $reportDir ("Verify-{0}.txt" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

function W([string]$Text="") {
    Add-Content -LiteralPath $report -Value $Text -Encoding UTF8
}

W "ZYNTAXAI PORTABLE VERIFICATION"
W ("Generated: {0}" -f (Get-Date))
W ("Portable folder: {0}" -f $root)
W ""

W ("EXE exists: {0}" -f (Test-Path -LiteralPath (Join-Path $root "ZyntaxAI-Portable.exe")))
W ("Data exists: {0}" -f (Test-Path -LiteralPath (Join-Path $root "Data")))

W ""
W "=== Data contents ==="
Get-ChildItem -LiteralPath (Join-Path $root "Data") -Force -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 300 |
    ForEach-Object { W $_.FullName }

W ""
W "=== Known host AppData residue ==="
foreach ($p in @(
    (Join-Path $env:APPDATA "dev.theholyonez.zyntaxai"),
    (Join-Path $env:APPDATA "TheHolyOneZ"),
    (Join-Path $env:LOCALAPPDATA "dev.theholyonez.zyntaxai")
)) {
    W ("{0}: {1}" -f $p,(Test-Path -LiteralPath $p))
}

W ""
W "Cloud portable-data build still uses upstream Windows Credential Manager for provider API keys."
W "Run the builder manually in inspect-secrets mode and upload that artifact for the strict portable-key patch."

Write-Host "Verification report:"
Write-Host "  $report"
