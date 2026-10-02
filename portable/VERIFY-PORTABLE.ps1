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
W ""
W "=== Expected true-portable store ==="
$store = Join-Path $root "Data\ZyntaxStore"
W ("Store exists: {0}" -f (Test-Path -LiteralPath $store -PathType Container))
foreach ($p in @(
    (Join-Path $store "config\settings.json"),
    (Join-Path $store "data\history.db"),
    (Join-Path $store "data\logs"),
    (Join-Path $store "data\secrets.key"),
    (Join-Path $store "data\secrets.enc")
)) {
    W ("{0}: {1}" -f $p,(Test-Path -LiteralPath $p))
}

W ""
W "This build forces ZyntaxAI's upstream encrypted-file secret backend."
W "Windows Credential Manager should not be required for API keys in this portable fork."

Write-Host "Verification report:"
Write-Host "  $report"
