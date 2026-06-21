#Requires -Version 5.1
<#
.SYNOPSIS
  Print side-by-side URLs for A/B QA: live Squarespace, deployed Vercel, local serve.
.EXAMPLE
  .\scripts\qa-urls.ps1
  .\scripts\qa-urls.ps1 -Page museum-of-verbs
  .\scripts\qa-urls.ps1 -Port 8780
#>
param(
    [string]$Page = "index",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

function Normalize-PagePath {
    param([string]$Name)
    $n = $Name.Trim().TrimStart("/")
    if ($n -eq "" -or $n -eq "index" -or $n -eq "index.html") {
        return @{ Live = "/"; Local = "index.html"; Label = "Home / cover" }
    }
    if ($n -match '\.html$') {
        $stem = $n -replace '\.html$', ''
    } else {
        $stem = $n
    }
    return @{
        Live  = "/{0}" -f $stem
        Local = "{0}.html" -f $stem
        Label = $stem
    }
}

$p = Normalize-PagePath $Page
$liveBase = "https://senzhang.me"
$vercelBase = "https://legacy-personal-website.vercel.app"
$localBase = "http://127.0.0.1:{0}" -f $Port

Write-Host ""
Write-Host ("QA triple - {0}" -f $p.Label) -ForegroundColor Cyan
Write-Host ("  Live Squarespace (source):     {0}{1}" -f $liveBase, $p.Live)
Write-Host ("  Deployed Vercel (archive):   {0}/{1}" -f $vercelBase, $p.Local)
Write-Host ("  Local (your fixes; refresh): {0}/{1}" -f $localBase, $p.Local)
Write-Host ""
Write-Host "Workflow: compare Live vs Vercel for archive gaps; fix locally; hard-refresh Local to verify."
Write-Host "git push = backup only. Vercel prod updates only when you run deploy-vercel.ps1 -Prod"
Write-Host ""
