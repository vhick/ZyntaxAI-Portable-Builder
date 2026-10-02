param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,

    [Parameter(Mandatory=$true)]
    [string]$OutputRoot
)

$ErrorActionPreference = "Stop"

$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)

if (Test-Path -LiteralPath $OutputRoot) {
    Remove-Item -LiteralPath $OutputRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$revision = (git -C $SourceRoot rev-parse HEAD).Trim()
$report = Join-Path $OutputRoot "Storage-Path-Inventory.txt"
$sourceOut = Join-Path $OutputRoot "RelevantSource"
New-Item -ItemType Directory -Path $sourceOut -Force | Out-Null

$terms = @(
    "ProjectDirs",
    "BaseDirs",
    "UserDirs",
    "directories::",
    "directories_next",
    "dirs::",
    "app_data_dir",
    "app_config_dir",
    "app_local_data_dir",
    "app_log_dir",
    "config_dir",
    "data_dir",
    "data_local_dir",
    "cache_dir",
    "log_dir",
    "project_path",
    "TheHolyOneZ",
    "ZyntaxAI",
    "APPDATA",
    "LOCALAPPDATA",
    "settings.json",
    "settings.toml",
    "history.db",
    "sqlite",
    "rusqlite",
    "logs"
)

Set-Content -LiteralPath $report -Encoding UTF8 -Value @(
    "ZYNTAXAI STORAGE-PATH SOURCE INVENTORY",
    "Revision: $revision",
    "Generated: $(Get-Date)",
    "",
    "SOURCE CODE ONLY. No user settings, database, logs, API keys or Credential Manager values are read.",
    ""
)

$extensions = @(".rs",".toml",".json",".ts",".tsx",".js",".mjs")
$roots = @(
    (Join-Path $SourceRoot "crates"),
    (Join-Path $SourceRoot "src-tauri"),
    (Join-Path $SourceRoot "apps")
)

$candidateMap = @{}

foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }

    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in $extensions } |
        ForEach-Object {
            $file = $_
            $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
            if ($null -eq $content) { return }

            foreach ($term in $terms) {
                if ($content.IndexOf($term,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    $candidateMap[$file.FullName] = $true
                    break
                }
            }
        }
}

foreach ($filePath in ($candidateMap.Keys | Sort-Object)) {
    $rel = $filePath.Substring($SourceRoot.Length).TrimStart('\')
    $dest = Join-Path $sourceOut $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath $filePath -Destination $dest -Force

    Add-Content -LiteralPath $report -Encoding UTF8 -Value @(
        "========================================================================",
        "FILE: $rel",
        "========================================================================"
    )

    $lines = Get-Content -LiteralPath $filePath
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

        $from = [Math]::Max(0,$i-6)
        $to = [Math]::Min($lines.Count-1,$i+12)

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
    "crates\zyntax-store\Cargo.toml",
    "package.json",
    "pnpm-lock.yaml"
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

Write-Host ""
Write-Host "Storage-path source inspection prepared at:" -ForegroundColor Green
Write-Host "  $OutputRoot"
Write-Host ""
Write-Host "This artifact contains upstream source only." -ForegroundColor Green
