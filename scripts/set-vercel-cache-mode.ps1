#Requires -Version 5.1
<#
.SYNOPSIS
  Switch vercel.json between Phase 2 QA caching and post-sign-off immutable caching.

.EXAMPLE
  .\scripts\set-vercel-cache-mode.ps1 -Mode QA
  .\scripts\set-vercel-cache-mode.ps1 -Mode Final
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("QA", "Final")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Source = Join-Path $RepoRoot ("vercel.{0}.json" -f $Mode.ToLower())
$Target = Join-Path $RepoRoot "vercel.json"

if (-not (Test-Path $Source)) {
    throw "Missing template: $Source"
}

Copy-Item $Source $Target -Force
Write-Host ""
Write-Host "vercel.json is now $Mode cache mode." -ForegroundColor Green
if ($Mode -eq "QA") {
    Write-Host "  HTML/pages: no-cache (fresh while fixing gaps)"
    Write-Host "  _cdn/_media: immutable + deploy ?v= stamp busts assets"
} else {
    Write-Host "  HTML/pages + assets: long-lived immutable (lower CDN/bandwidth cost)"
    Write-Host "  Run one final .\scripts\deploy-vercel.ps1 -Prod -CacheMode Final after sign-off"
    Write-Host "  Commit vercel.json when switching permanently."
}
Write-Host ""
