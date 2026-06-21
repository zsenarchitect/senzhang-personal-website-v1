#Requires -Version 5.1
<#
.SYNOPSIS
  Fail fast if snapshot _cdn assets are Git LFS pointer stubs (breaks CSS/JS/images on Vercel).
#>
param(
    [string]$Date = "2026-06-05"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CdnRoot = Join-Path $RepoRoot "snapshot\$Date\_cdn"

function Test-CdnAssetProbe {
    param(
        [string]$Label,
        [string]$RelativePath,
        [int]$MinBytes = 10000
    )

    $path = Join-Path $CdnRoot $RelativePath
    if (-not (Test-Path $path)) {
        throw "Missing probe asset ($Label): $path"
    }

    $head = Get-Content $path -TotalCount 1 -ErrorAction Stop
    if ($head -match "git-lfs\.github\.com/spec") {
        throw @"
Snapshot _cdn asset is still a Git LFS pointer ($Label):
  $path
CSS/JS/images will 200 on Vercel but render as unstyled broken pages.
Run: git lfs pull
Then re-run deploy or preview.
"@
    }

    $size = (Get-Item $path).Length
    if ($size -lt $MinBytes) {
        throw "Probe asset too small for $Label (${size} bytes, need >= $MinBytes): $path"
    }

    Write-Host "CDN probe OK ($Label, $size bytes): $RelativePath"
}

# Squarespace runtime JS (lightbox, layout)
Test-CdnAssetProbe -Label "squarespace-js" -RelativePath "assets.squarespace.com\fbe4baf7c30df45ea3ff.js" -MinBytes 10000
# Main template CSS (sidebar layout, hides mobile nav on desktop)
Test-CdnAssetProbe -Label "template-css" -RelativePath "static1.squarespace.com\3f6928579d7ce4659e88.css" -MinBytes 50000
# Header logo on menu and inner pages
Test-CdnAssetProbe -Label "header-logo-gif" -RelativePath "images.squarespace-cdn.com\aed6f33c10cccaffe417.gif" -MinBytes 1000
# Custom offline video player (project embeds)
Test-CdnAssetProbe -Label "offline-video-player-js" -RelativePath "offline-video-player\offline-video-player.js" -MinBytes 1000

$MediaRoot = Join-Path $RepoRoot "snapshot\$Date\_media"
function Test-MediaAssetProbe {
    param(
        [string]$Label,
        [string]$FileName,
        [int]$MinBytes = 100000
    )

    $path = Join-Path $MediaRoot $FileName
    if (-not (Test-Path $path)) {
        throw "Missing _media probe ($Label): $path"
    }

    $head = Get-Content $path -TotalCount 1 -ErrorAction Stop
    if ($head -match "git-lfs\.github\.com/spec") {
        throw @"
Snapshot _media asset is still a Git LFS pointer ($Label):
  $path
Offline videos will 200 on Vercel but fail to play in the browser.
Run: git lfs pull
Then re-run deploy or preview.
"@
    }

    $size = (Get-Item $path).Length
    if ($size -lt $MinBytes) {
        throw "Probe _media asset too small for $Label (${size} bytes, need >= $MinBytes): $path"
    }

    Write-Host "_media probe OK ($Label, $size bytes): $FileName"
}

Test-MediaAssetProbe -Label "cover-background-video" -FileName "cover-background.mp4" -MinBytes 1000000
Test-MediaAssetProbe -Label "museum-video" -FileName "4sQc0d3HRck.mp4" -MinBytes 1000000
Test-MediaAssetProbe -Label "bank-video" -FileName "3pFCHJNHKEU.mp4" -MinBytes 100000
Test-MediaAssetProbe -Label "works-hero-video" -FileName "fAl5EJuQpUM.mp4" -MinBytes 100000

Write-Host "All CDN and _media asset probes passed."
