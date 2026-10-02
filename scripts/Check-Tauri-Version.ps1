param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot
)

$ErrorActionPreference = "Stop"

$lock = Join-Path $SourceRoot "Cargo.lock"
if (-not (Test-Path -LiteralPath $lock -PathType Leaf)) {
    throw "Cargo.lock not found at $lock"
}

$text = Get-Content -LiteralPath $lock -Raw
$m = [regex]::Match(
    $text,
    '(?ms)\[\[package\]\]\s*name = "tauri"\s*version = "([^"]+)"'
)

if (-not $m.Success) {
    throw "Could not determine Tauri version from Cargo.lock."
}

$version = [version]$m.Groups[1].Value
Write-Host "Upstream Tauri version: $version"

if ($version -lt [version]"2.10.0") {
    throw "Tauri $version is older than 2.10.0. appDirectoriesOverride is not available."
}

Write-Host "Tauri portable-directory override is supported."
