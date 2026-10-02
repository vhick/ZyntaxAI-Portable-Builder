param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,

    [Parameter(Mandatory=$true)]
    [string]$OutputRoot,

    [Parameter(Mandatory=$true)]
    [string]$KitRoot
)

$ErrorActionPreference = "Stop"

if (Test-Path -LiteralPath $OutputRoot) {
    Remove-Item -LiteralPath $OutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $OutputRoot "Data") -Force | Out-Null

$exeCandidates = @(
    Get-ChildItem -LiteralPath $SourceRoot -Recurse -Filter "*.exe" -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -match '\\target\\release\\' -and
        $_.Name -match '(?i)zyntax' -and
        $_.FullName -notmatch '\\bundle\\'
    } |
    Sort-Object LastWriteTime -Descending
)

if ($exeCandidates.Count -eq 0) {
    throw "Could not locate a ZyntaxAI release EXE under target\release."
}

$exe = $exeCandidates[0]
Write-Host "Using built EXE: $($exe.FullName)"

Copy-Item -LiteralPath $exe.FullName `
    -Destination (Join-Path $OutputRoot "ZyntaxAI-Portable.exe") `
    -Force

foreach ($name in @(
    "LAUNCH-ZYNTAXAI-PORTABLE.cmd",
    "INSTALL-PORTABLE-STARTUP.cmd",
    "REMOVE-PORTABLE-STARTUP.cmd",
    "VERIFY-PORTABLE.ps1",
    "MIGRATE-OFFICIAL-DATA.ps1",
    "CLEAN-OLD-HOST-DATA.ps1"
)) {
    Copy-Item -LiteralPath (Join-Path $KitRoot "portable\$name") `
        -Destination (Join-Path $OutputRoot $name) `
        -Force
}

$revision = (git -C $SourceRoot rev-parse HEAD).Trim()

Set-Content -LiteralPath (Join-Path $OutputRoot "SOURCE-REVISION.txt") `
    -Encoding UTF8 `
    -Value @(
        "Source: synced ZyntaxAI fork supplied by build workflow",
        "Revision: $revision",
        "Built: $(Get-Date)",
        "Build environment: GitHub Actions windows-2022"
    )

@{
    mode = "true-portable-encrypted-file-secrets"
    upstream_revision = $revision
    portable_data_root = "./Data"
    app_directories_override = $true
    api_keys_portable = $true
    note = "Application-owned state and API keys are stored below ./Data. API keys use upstream AES-256-GCM encrypted-file storage."
} |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $OutputRoot "PORTABLE-BUILD.json") -Encoding UTF8


$patchMarker = Join-Path $SourceRoot ".zyntax-true-portable-patch.json"
if (-not (Test-Path -LiteralPath $patchMarker -PathType Leaf)) {
    throw "True-portable patch marker was not found. Refusing to package a build as portable."
}
Copy-Item -LiteralPath $patchMarker `
    -Destination (Join-Path $OutputRoot "TRUE-PORTABLE-PATCH.json") `
    -Force

$license = Join-Path $SourceRoot "LICENSE"
if (Test-Path -LiteralPath $license -PathType Leaf) {
    Copy-Item -LiteralPath $license `
        -Destination (Join-Path $OutputRoot "LICENSE-UPSTREAM.txt") `
        -Force
}

Write-Host "Portable package assembled at $OutputRoot"
