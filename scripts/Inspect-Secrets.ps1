param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,

    [Parameter(Mandatory=$true)]
    [string]$OutputRoot
)

$ErrorActionPreference = "Stop"

$storeRoot = Join-Path $SourceRoot "crates\zyntax-store"
if (-not (Test-Path -LiteralPath $storeRoot -PathType Container)) {
    throw "Expected crates\zyntax-store was not found."
}

if (Test-Path -LiteralPath $OutputRoot) {
    Remove-Item -LiteralPath $OutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$sourceOut = Join-Path $OutputRoot "RelevantSource"
New-Item -ItemType Directory -Path $sourceOut -Force | Out-Null

$terms = @(
    "keyring",
    "keychain",
    "credential",
    "secret",
    "aes",
    "gcm",
    "fallback",
    "password",
    "api_key",
    "api key"
)

$report = Join-Path $OutputRoot "Secret-Backend-Inventory.txt"
$revision = (git -C $SourceRoot rev-parse HEAD).Trim()

Set-Content -LiteralPath $report -Encoding UTF8 -Value @(
    "ZYNTAXAI SECRET BACKEND SOURCE INVENTORY",
    "Revision: $revision",
    "Generated: $(Get-Date)",
    "",
    "SOURCE CODE ONLY. No Credential Manager values or user API keys are read.",
    ""
)

$candidates = New-Object System.Collections.Generic.List[object]

Get-ChildItem -LiteralPath $storeRoot -Recurse -File |
    Where-Object { $_.Extension -in @(".rs",".toml") } |
    ForEach-Object {
        $content = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
        if ($null -eq $content) { return }

        foreach ($term in $terms) {
            if ($content.IndexOf($term,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $candidates.Add($_)
                break
            }
        }
    }

foreach ($file in $candidates | Sort-Object FullName -Unique) {
    $rel = $file.FullName.Substring($storeRoot.Length).TrimStart('\')
    $dest = Join-Path $sourceOut $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $dest -Force

    Add-Content -LiteralPath $report -Encoding UTF8 -Value @(
        "========================================================================",
        "FILE: crates\zyntax-store\$rel",
        "========================================================================"
    )

    $lines = Get-Content -LiteralPath $file.FullName
    for ($i=0; $i -lt $lines.Count; $i++) {
        $line = [string]$lines[$i]
        $matched = $false

        foreach ($term in $terms) {
            if ($line.IndexOf($term,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $matched = $true
                break
            }
        }

        if (-not $matched) { continue }

        $from = [Math]::Max(0,$i-4)
        $to = [Math]::Min($lines.Count-1,$i+8)

        for ($j=$from; $j -le $to; $j++) {
            Add-Content -LiteralPath $report -Encoding UTF8 `
                -Value ("{0,5}: {1}" -f ($j+1),$lines[$j])
        }

        Add-Content -LiteralPath $report -Encoding UTF8 -Value ""
    }
}

$manifestOut = Join-Path $OutputRoot "Manifests"
New-Item -ItemType Directory -Path $manifestOut -Force | Out-Null

foreach ($relative in @(
    "Cargo.toml",
    "Cargo.lock",
    "src-tauri\Cargo.toml",
    "src-tauri\tauri.conf.json",
    "crates\zyntax-store\Cargo.toml"
)) {
    $src = Join-Path $SourceRoot $relative
    if (Test-Path -LiteralPath $src -PathType Leaf) {
        $name = $relative -replace '[\\/:*?"<>|]','_'
        Copy-Item -LiteralPath $src -Destination (Join-Path $manifestOut $name) -Force
    }
}

Set-Content -LiteralPath (Join-Path $OutputRoot "UPSTREAM-REVISION.txt") `
    -Encoding UTF8 `
    -Value $revision

Write-Host "Secret source inspection prepared at $OutputRoot"
