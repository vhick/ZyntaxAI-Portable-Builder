param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot
)

$ErrorActionPreference = "Stop"

$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)
$lock = Join-Path $SourceRoot "Cargo.lock"
$schema = Join-Path $SourceRoot "node_modules\@tauri-apps\cli\config.schema.json"

if (-not (Test-Path -LiteralPath $lock -PathType Leaf)) {
    throw "Cargo.lock not found at $lock"
}

if (-not (Test-Path -LiteralPath $schema -PathType Leaf)) {
    throw "@tauri-apps/cli config schema not found at $schema"
}

$schemaText = Get-Content -LiteralPath $schema -Raw
if ($schemaText.IndexOf('"appDirectoriesOverride"',[StringComparison]::Ordinal) -lt 0) {
    throw "Installed Tauri CLI schema does not contain appDirectoriesOverride."
}

Write-Host "Tauri CLI schema contains appDirectoriesOverride." -ForegroundColor Green

$lockText = Get-Content -LiteralPath $lock -Raw

function Get-PackageVersion {
    param([string]$Name)

    $escaped = [regex]::Escape($Name)
    $m = [regex]::Match(
        $lockText,
        "(?ms)\[\[package\]\]\s*name = `"$escaped`"\s*version = `"([^`"]+)`""
    )

    if (-not $m.Success) {
        return $null
    }

    try {
        return [version]$m.Groups[1].Value
    }
    catch {
        return $null
    }
}

$tauri = Get-PackageVersion "tauri"
$utils = Get-PackageVersion "tauri-utils"
$build = Get-PackageVersion "tauri-build"

Write-Host "Rust tauri:       $tauri"
Write-Host "Rust tauri-utils: $utils"
Write-Host "Rust tauri-build: $build"

if (-not $tauri -or $tauri -lt [version]"2.12.0") {
    throw "Rust tauri is too old for this portable build."
}

if (-not $utils -or $utils -lt [version]"2.10.0") {
    throw "Rust tauri-utils is too old; appDirectoriesOverride is unavailable."
}

if (-not $build -or $build -lt [version]"2.7.0") {
    throw "Rust tauri-build is too old for the updated Tauri config stack."
}

Write-Host ""
Write-Host "Portable-directory support is ready." -ForegroundColor Green
