#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy the dated snapshot to the linked Vercel project (legacy-personal-website).

.NOTES
  Phase 2 (default -CacheMode QA): HTML no-cache; assets immutable with ?v=<git-sha> stamp.
  After sign-off: set-vercel-cache-mode.ps1 -Mode Final, commit vercel.json, then
  .\scripts\deploy-vercel.ps1 -Prod -CacheMode Final for lowest ongoing CDN cost.
#>
param(
    [switch]$Prod,
    [string]$Date = "2026-06-05",
    [ValidateSet("QA", "Final")]
    [string]$CacheMode = "QA"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    throw "Vercel CLI not found. Install: npm i -g vercel"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' not found."
}

if ($Prod) {
    Write-Host "PROD deploy - uploads full snapshot (~1.7 GB). User must have requested this." -ForegroundColor Yellow
}

$vercelJson = Join-Path $RepoRoot "vercel.json"
$modeTemplate = Join-Path $RepoRoot ("vercel.{0}.json" -f $CacheMode.ToLower())
if (-not (Test-Path $modeTemplate)) {
    throw "Missing cache template: $modeTemplate"
}
Copy-Item $modeTemplate $vercelJson -Force
Write-Host "Cache mode: $CacheMode"

# CLI deploy uploads the local working tree (already smudged via `git lfs pull`).
# buildCommand/installCommand are for Git-triggered builds only; they fail with exit 128
# when Vercel has no .git checkout during `vercel deploy`.
& py -3 -c @"
import json
from pathlib import Path
path = Path(r'$vercelJson')
cfg = json.loads(path.read_text(encoding='utf-8'))
cfg.pop('buildCommand', None)
cfg.pop('installCommand', None)
path.write_text(json.dumps(cfg, indent=2) + '\n', encoding='utf-8')
"@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "CLI deploy: stripped git lfs build/install commands from vercel.json"

Write-Host "Verifying snapshot _cdn assets are not Git LFS pointers..."
& (Join-Path $PSScriptRoot "verify-cdn-assets.ps1") -Date $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Relocalizing snapshot asset URLs from manifest..."
& py -3 (Join-Path $PSScriptRoot "fix-offline-urls.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Patching offline lightbox (base href + stuck-overlay recovery)..."
& py -3 (Join-Path $PSScriptRoot "fix-offline-lightbox.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Patching offline video player (seek bar + custom controls)..."
& py -3 (Join-Path $PSScriptRoot "fix-offline-video-player.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Stamping cache-bust build id on snapshot HTML..."
& py -3 (Join-Path $PSScriptRoot "stamp-cache-version.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$vercelArgs = @("deploy", "--yes")
if ($Prod) { $vercelArgs += "--prod" }

Write-Host "Deploying from $RepoRoot (output: snapshot/$Date per vercel.json)..."
$code = 1
try {
    & vercel @vercelArgs
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "Verifying production CDN assets (not LFS pointers)..."
        & py -3 (Join-Path $PSScriptRoot "verify-prod-assets.py")
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Production asset probe failed. Enable Git LFS in Vercel Settings -> Git and redeploy." -ForegroundColor Red
        }
    }
} finally {
    Write-Host "Restoring unstamped snapshot HTML in git working tree..."
    git checkout -- "snapshot/$Date/*.html" 2>$null
    if (Test-Path "snapshot/$Date/archive-version.json") {
        Remove-Item "snapshot/$Date/archive-version.json" -Force -ErrorAction SilentlyContinue
    }
    git checkout -- vercel.json 2>$null
}

exit $code
