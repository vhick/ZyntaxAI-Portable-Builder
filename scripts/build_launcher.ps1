# Build the real Windows x64 GUI launcher with the MSVC version installed on this runner.
# Uses official vswhere and CMake generators; no GUI automation or interactive installers.
# Copyright (c) 2026 ZyntaxAI Native Portable Builder contributors. MIT license.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$icon = Join-Path $root 'upstream/src-tauri/icons/icon.ico'
$launcherDir = Join-Path $root 'launcher'
$buildDir = Join-Path $launcherDir 'build'
$target = Join-Path $buildDir 'Release/ZyntaxAIPortable.exe'

if (!(Test-Path -LiteralPath $icon -PathType Leaf)) {
    throw "Upstream official ZyntaxAI icon not found: $icon"
}
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (!(Test-Path -LiteralPath $vswhere -PathType Leaf)) {
    $detected = Get-Command 'vswhere.exe' -ErrorAction SilentlyContinue
    if ($null -eq $detected) { throw 'vswhere.exe missing; cannot safely identify the installed MSVC toolchain.' }
    $vswhere = $detected.Source
}
$query = @('-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64')
$versionLines = @(& $vswhere @query '-property' 'installationVersion')
if ($LASTEXITCODE -ne 0 -or $versionLines.Count -ne 1 -or [string]::IsNullOrWhiteSpace($versionLines[0])) {
    throw 'vswhere did not find exactly one latest Visual Studio installation with C++ x64 tools.'
}
$locationLines = @(& $vswhere @query '-property' 'installationPath')
if ($LASTEXITCODE -ne 0 -or $locationLines.Count -ne 1 -or !(Test-Path -LiteralPath $locationLines[0] -PathType Container)) {
    throw 'vswhere did not provide a valid Visual Studio installation path.'
}
$vsVersion = [version]$versionLines[0].Trim()
$vsPath = $locationLines[0].Trim()
$generator = switch ($vsVersion.Major) {
    17 { 'Visual Studio 17 2022' }
    18 { 'Visual Studio 18 2026' }
    default { throw "Unsupported Visual Studio major version $($vsVersion.Major). Inspect the runner and update this mapping." }
}

$cmakeVersionOutput = @(& cmake --version)
if ($LASTEXITCODE -ne 0 -or $cmakeVersionOutput.Count -eq 0) {
    throw 'Cannot run cmake --version.'
}
$cmakeInfo = $cmakeVersionOutput[0]
if ($cmakeInfo -match '^cmake version ([0-9]+\.[0-9]+\.[0-9]+)') {
    $cmakeVersion = [version]$Matches[1]
} else {
    throw "Cannot determine the installed CMake version: $cmakeInfo"
}
if ($vsVersion.Major -eq 18 -and $cmakeVersion -lt [version]'4.2.0') {
    throw "Visual Studio 2026 requires CMake >= 4.2 for its generator; found $cmakeVersion."
}
Write-Host "Detected Visual Studio $vsVersion at: $vsPath"
Write-Host "Detected CMake $cmakeVersion; selecting generator: $generator"

# This fresh CI checkout should not contain a previous CMake cache or packaged binaries.
# Fail instead of reusing a stale cache that targets a different compiler.
if (Test-Path -LiteralPath $buildDir) {
    throw "Unexpected existing launcher build directory: $buildDir. Start from a clean checkout."
}
Copy-Item -LiteralPath $icon -Destination (Join-Path $launcherDir 'icon.ico') -Force
& cmake -S $launcherDir -B $buildDir -G $generator -A x64 "-DCMAKE_GENERATOR_INSTANCE=$vsPath"
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed using $generator" }
& cmake --build $buildDir --config Release --parallel
if ($LASTEXITCODE -ne 0) { throw "ZyntaxAI native launcher compilation failed using $generator" }
if (!(Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "Compiled root launcher missing: $target"
}
Write-Host "Launcher compiled: $target"
