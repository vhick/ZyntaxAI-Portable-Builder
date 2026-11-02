# Run on a real Windows user session BEFORE and AFTER testing the portable app.
# Report-only. Never alters, deletes or rehomes host files or registry keys.
param(
    [ValidateSet('Before','After')][string]$Phase = 'Before',
    [string]$PortableRoot = (Join-Path $PSScriptRoot '..')
)
$ErrorActionPreference = 'Stop'
$PortableRoot = [IO.Path]::GetFullPath($PortableRoot)
$reports = Join-Path $PortableRoot 'Data\TraceGuard'
New-Item -ItemType Directory -Path $reports -Force | Out-Null
$locations = @()
foreach ($root in @('APPDATA','LOCALAPPDATA','PROGRAMDATA')) {
    $value = [Environment]::GetEnvironmentVariable($root)
    if (-not $value) { continue }
    foreach ($relative in @('dev.theholyonez.zyntaxai', 'TheHolyOneZ\ZyntaxAI')) {
        $locations += [pscustomobject]@{ Root = $root; Target = (Join-Path $value $relative) }
    }
}
$results = @()
foreach ($location in $locations) {
    $isPresent = Test-Path -LiteralPath $location.Target
    $entries = @()
    if ($isPresent) {
        $item = Get-Item -LiteralPath $location.Target -Force
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            # Bounded to the exact target root, no recursion through reparse points.
            $entries = @(Get-ChildItem -LiteralPath $location.Target -Force -ErrorAction Stop |
                ForEach-Object { [pscustomobject]@{
                    Name = $_.Name; Type = if ($_.PSIsContainer) {'Directory'} else {'File'};
                    Bytes = if ($_.PSIsContainer) {$null} else {$_.Length};
                    ReparsePoint = [bool]($_.Attributes -band [IO.FileAttributes]::ReparsePoint)
                } })
        }
    }
    $results += [pscustomobject]@{ Root=$location.Root; Path=$location.Target; Exists=$isPresent; DirectChildren=$entries }
}
$path = Join-Path $reports "Host-$Phase.json"
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Wrote report-only $Phase snapshot: $path"
if ($Phase -eq 'After') {
    $before = Join-Path $reports 'Host-Before.json'
    if (Test-Path -LiteralPath $before) {
        $prior = Get-Content -LiteralPath $before -Raw
        $after = Get-Content -LiteralPath $path -Raw
        if ($prior -ceq $after) { Write-Host 'No change in bounded candidate snapshot (not proof of zero host traces).' }
        else { Write-Warning 'Candidate root differences found. Inspect both JSON files. Do NOT auto-delete.' }
    }
}
Write-Host 'A before/after difference alone DOES NOT prove ZyntaxAI created it.'
