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
    "VERIFY-PORTABLE.ps1"
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
    mode = "portable-data-os-keychain"
    upstream_revision = $revision
    portable_data_root = "./Data"
    app_directories_override = $true
    api_keys_portable = $false
    note = "API keys still use the upstream Windows Credential Manager backend."
} |
    ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $OutputRoot "PORTABLE-BUILD.json") -Encoding UTF8

$license = Join-Path $SourceRoot "LICENSE"
if (Test-Path -LiteralPath $license -PathType Leaf) {
    Copy-Item -LiteralPath $license `
        -Destination (Join-Path $OutputRoot "LICENSE-UPSTREAM.txt") `
        -Force
}

Write-Host "Portable package assembled at $OutputRoot"
