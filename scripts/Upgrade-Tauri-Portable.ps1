param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot
)

$ErrorActionPreference = "Stop"

function Run {
    param(
        [string]$File,
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "> $File $($Arguments -join ' ')" -ForegroundColor Cyan

    & $File @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code $LASTEXITCODE."
    }
}

$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)

if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot "package.json"))) {
    throw "package.json was not found in $SourceRoot"
}

if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot "Cargo.lock"))) {
    throw "Cargo.lock was not found in $SourceRoot"
}

Push-Location $SourceRoot
try {
    Write-Host ""
    Write-Host "The upstream checkout predates Tauri's portable-directory config." -ForegroundColor Yellow
    Write-Host "This step upgrades ONLY the temporary GitHub Actions checkout." -ForegroundColor Yellow
    Write-Host "Your clean ZyntaxAI fork is not modified." -ForegroundColor Yellow

    # appDirectoriesOverride was added to the newer Tauri configuration stack.
    # The upstream checkout used @tauri-apps/cli 2.11.4 in the failed build,
    # which predates that config field. Use the first Tauri line that ships it
    # consistently across CLI/core/config crates.
    Run "pnpm" @(
        "add",
        "--save-dev",
        "--workspace-root",
        "@tauri-apps/cli@2.12.0"
    )

    # Upgrade the Rust side too. The configuration is consumed by both the CLI
    # and generated Rust context, so updating only the JavaScript CLI is not enough.
    Run "cargo" @(
        "update",
        "-p","tauri",
        "--precise","2.12.0"
    )

    Run "cargo" @(
        "update",
        "-p","tauri-build",
        "--precise","2.7.0"
    )

    # Usually this is updated transitively by tauri 2.12.0. If Cargo still has
    # an older compatible lock entry, move tauri-utils to the release that
    # introduced appDirectoriesOverride.
    $lockText = Get-Content -LiteralPath "Cargo.lock" -Raw
    $utils = [regex]::Match(
        $lockText,
        '(?ms)\[\[package\]\]\s*name = "tauri-utils"\s*version = "([^"]+)"'
    )

    if ($utils.Success) {
        $utilsVersion = [version]$utils.Groups[1].Value
        Write-Host "tauri-utils after core update: $utilsVersion"

        if ($utilsVersion -lt [version]"2.10.0") {
            Run "cargo" @(
                "update",
                "-p","tauri-utils",
                "--precise","2.10.0"
            )
        }
    }

    Write-Host ""
    Write-Host "Temporary Tauri portable-support upgrade finished." -ForegroundColor Green
}
finally {
    Pop-Location
}
