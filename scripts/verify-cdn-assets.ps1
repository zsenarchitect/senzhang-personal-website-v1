#Requires -Version 5.1
<#
.SYNOPSIS
  Fail fast if snapshot _cdn assets are Git LFS pointer stubs (breaks Squarespace JS on Vercel).
#>
param(
    [string]$Date = "2026-06-05"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$probe = Join-Path $RepoRoot "snapshot\$Date\_cdn\assets.squarespace.com\fbe4baf7c30df45ea3ff.js"

if (-not (Test-Path $probe)) {
    throw "Missing probe asset: $probe"
}

$head = Get-Content $probe -TotalCount 1 -ErrorAction Stop
if ($head -match "git-lfs\.github\.com/spec") {
    throw @"
Snapshot _cdn JS is still a Git LFS pointer ($probe).
Squarespace lightbox and other interactivity will not work on deploy.
Run: git lfs pull
Then re-run deploy or preview.
"@
}

$size = (Get-Item $probe).Length
if ($size -lt 10000) {
    throw "Probe asset too small (${size} bytes): $probe"
}

Write-Host "CDN asset probe OK ($size bytes): $probe"
