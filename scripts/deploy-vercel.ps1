#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy the dated snapshot to the linked Vercel project (legacy-personal-website).

.NOTES
  Cost policy: do NOT run this automatically after every fix. git push alone does not
  update production. Run -Prod only when the user explicitly asks to publish (sign-off).
  For QA, use .\scripts\serve.ps1 locally instead (~1.7 GB upload per prod deploy).

  Before upload: stamp-cache-version.py appends ?v=<git-sha> to _cdn/_media URLs so
  browsers/CDN fetch fresh assets. Working-tree HTML is restored after deploy.
#>
param(
    [switch]$Prod,
    [string]$Date = "2026-06-05"
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
    git checkout -- "snapshot/$Date/*.html" "snapshot/$Date/archive-version.json" 2>$null
}

exit $code
