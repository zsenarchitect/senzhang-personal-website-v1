#Requires -Version 5.1
<#
.SYNOPSIS
  Verify the latest snapshot against the live senzhang.me sitemap.
#>
param(
    [string]$SnapshotDate
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SnapshotRoot = Join-Path $RepoRoot "snapshot"

if (-not $SnapshotDate) {
    $dates = Get-ChildItem $SnapshotRoot -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending
    if ($dates.Count -eq 0) { throw "No snapshots found under $SnapshotRoot" }
    $SnapshotDate = $dates[0].Name
}

$SnapshotDir = Join-Path $SnapshotRoot $SnapshotDate
if (-not (Test-Path $SnapshotDir)) {
    throw "Snapshot not found: $SnapshotDir"
}

Write-Host "Verifying snapshot: $SnapshotDate"
Write-Host ""

$sitemapXml = curl.exe -sL "https://senzhang.me/sitemap.xml"
$pageUrls = [regex]::Matches($sitemapXml, '<loc>(https://senzhang\.me[^<]+)</loc>') |
    ForEach-Object { $_.Groups[1].Value } |
    Sort-Object -Unique

$missing = @()
$found = @()

foreach ($url in $pageUrls) {
    $path = ([uri]$url).AbsolutePath.Trim("/")
    if ([string]::IsNullOrEmpty($path)) { $path = "index.html" }
    else {
        $candidate = Join-Path $SnapshotDir ($path + ".html")
        $candidateDir = Join-Path $SnapshotDir ($path + "/index.html")
        if (Test-Path $candidate) { $path = $path + ".html" }
        elseif (Test-Path $candidateDir) { $path = Join-Path $path "index.html" }
        else { $path = $path + ".html" }
    }

    $localPath = Join-Path $SnapshotDir $path
    if (Test-Path $localPath) { $found += $url }
    else { $missing += $url }
}

Write-Host "Sitemap pages: $($pageUrls.Count)"
Write-Host "Found locally: $($found.Count)"
Write-Host "Missing:       $($missing.Count)"
Write-Host ""

if ($missing.Count -gt 0) {
    Write-Host "Missing pages:"
    $missing | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

Write-Host "All sitemap pages present in snapshot."
exit 0
