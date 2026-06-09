#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy the dated snapshot to the linked Vercel project (legacy-personal-website).
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

$args = @("deploy", "--yes")
if ($Prod) { $args += "--prod" }

Write-Host "Deploying from $RepoRoot (output: snapshot/2026-06-05 per vercel.json)..."
& vercel @args
exit $LASTEXITCODE
