#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy the dated snapshot to the linked Vercel project (senzhang-personal-website-v1).

.NOTES
  Default scope: zsen-idea-house (personal). NOT ennead-projects.

  PRODUCTION (-Prod): milestone-only. Pass -Milestone with a short label (e.g. S2.5, P2, DNS).
  Day-to-day QA: py -3 scripts\serve.py (local). Do NOT prod-deploy every commit.

  Phase 2 (default -CacheMode QA): HTML no-cache; assets immutable with ?v=<git-sha> stamp.
  After sign-off: set-vercel-cache-mode.ps1 -Mode Final, commit vercel.json, then
  .\scripts\deploy-vercel.ps1 -Prod -Milestone DNS -CacheMode Final
#>
param(
    [switch]$Prod,
    [string]$Milestone = "",
    [string]$Date = "2026-06-05",
    [ValidateSet("QA", "Final")]
    [string]$CacheMode = "QA",
    [string]$VercelScope = "zsen-idea-house"
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
    if (-not $Milestone.Trim()) {
        throw @"
Prod deploy is milestone-only. Pass -Milestone <label> (e.g. S2.5, P2, DNS).
For day-to-day work use: py -3 scripts\serve.py
Preview (non-prod): .\scripts\deploy-vercel.ps1
"@
    }
    Write-Host "PROD deploy [milestone: $($Milestone.Trim())] - uploads full snapshot (~1.7 GB)." -ForegroundColor Yellow
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

Write-Host "Patching offline folder nav (dropdown toggle + root-relative hrefs)..."
& py -3 (Join-Path $PSScriptRoot "fix-offline-nav.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Ensuring code/ and speaking/ index pages..."
& py -3 (Join-Path $PSScriptRoot "add-section-index-pages.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py -3 (Join-Path $PSScriptRoot "fix-offline-nav.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Stamping cache-bust build id on snapshot HTML..."
& py -3 (Join-Path $PSScriptRoot "stamp-cache-version.py") $Date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Vercel scope: $VercelScope"
$scopeFlag = @("--scope", $VercelScope)

Write-Host "Deploying via local build + --prebuilt (remote git lfs pull fails on Vercel)..."
$code = 1
try {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    vercel pull --yes --environment=production @scopeFlag
    if ($LASTEXITCODE -ne 0) { $code = $LASTEXITCODE; throw "vercel pull failed" }
    $buildArgs = @("build") + $scopeFlag
    if ($Prod) { $buildArgs += "--prod" }
    vercel @buildArgs
    if ($LASTEXITCODE -ne 0) { $code = $LASTEXITCODE; throw "vercel build failed" }
    $deployArgs = @("deploy", "--prebuilt", "--yes") + $scopeFlag
    if ($Prod) { $deployArgs += "--prod" }
    vercel @deployArgs
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($code -eq 0) {
        Write-Host "Verifying production CDN assets (not LFS pointers)..."
        & py -3 (Join-Path $PSScriptRoot "verify-prod-assets.py") --base "https://senzhang-personal-website-v1.vercel.app"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Production asset probe failed. Enable Git LFS in Vercel Settings -> Git and redeploy." -ForegroundColor Red
        }
    }
} finally {
    Write-Host "Restoring unstamped snapshot HTML in git working tree..."
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    git checkout -- "snapshot/$Date/" 2>$null
    if (Test-Path "snapshot/$Date/archive-version.json") {
        Remove-Item "snapshot/$Date/archive-version.json" -Force -ErrorAction SilentlyContinue
    }
    git checkout -- vercel.json 2>$null
    $ErrorActionPreference = $prevEap
}

exit $code
