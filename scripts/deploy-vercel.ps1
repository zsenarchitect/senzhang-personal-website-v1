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
} finally {
    Write-Host "Restoring unstamped snapshot HTML in git working tree..."
    git checkout -- "snapshot/$Date/*.html" 2>$null
    if (Test-Path "snapshot/$Date/archive-version.json") {
        Remove-Item "snapshot/$Date/archive-version.json" -Force -ErrorAction SilentlyContinue
    }
    git checkout -- vercel.json 2>$null
}

exit $code
