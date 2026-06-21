#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy the dated snapshot to the linked Vercel project (legacy-personal-website).

.NOTES
  Cost policy: do NOT run this automatically after every fix. git push alone does not
  update production. Run -Prod only when the user explicitly asks to publish (sign-off).
  For QA, use .\scripts\serve.ps1 locally instead (~1.7 GB upload per prod deploy).
#>
param(
    [switch]$Prod
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    throw "Vercel CLI not found. Install: npm i -g vercel"
}

if ($Prod) {
    Write-Host "PROD deploy — uploads full snapshot (~1.7 GB). User must have requested this." -ForegroundColor Yellow
}

$args = @("deploy", "--yes")
if ($Prod) { $args += "--prod" }

Write-Host "Deploying from $RepoRoot (output: snapshot/2026-06-05 per vercel.json)..."
& vercel @args
exit $LASTEXITCODE
