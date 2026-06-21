#Requires -Version 5.1
<#
.SYNOPSIS
  Start a local HTTP server for the archived senzhang.me snapshot.
.EXAMPLE
  .\scripts\serve.ps1
  .\scripts\serve.ps1 -Date 2026-06-05 -Port 8765
  .\scripts\serve.ps1 -NoCleanStale   # keep existing serve.py on this port
#>
param(
    [string]$Date,
    [int]$Port = 8765,
    [switch]$NoOpen,
    [switch]$NoCleanStale
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "serve.py"

function Get-ServePyPidsOnPort {
    param([int]$TargetPort)
    $pids = @()
    $connections = Get-NetTCPConnection -LocalPort $TargetPort -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
        if ($proc -and $proc.CommandLine -match 'serve\.py') {
            $pids += $conn.OwningProcess
        }
    }
    return $pids | Select-Object -Unique
}

function Stop-StaleServeOnPort {
    param([int]$TargetPort)
    $pids = Get-ServePyPidsOnPort -TargetPort $TargetPort
    foreach ($pid in $pids) {
        Write-Host "Stopping stale serve.py on port $TargetPort (PID $pid)..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    if ($pids.Count -gt 0) {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $NoCleanStale) {
    Stop-StaleServeOnPort -TargetPort $Port
}

$pyArgs = @($PythonScript, "--port", $Port)
if ($Date) { $pyArgs += @("--date", $Date) }
if ($NoOpen) { $pyArgs += "--no-open" }

Write-Host ""
Write-Host "Local QA server (edits to snapshot/ show on browser refresh — no restart needed)" -ForegroundColor Green
Write-Host "  Compare against:"
Write-Host "    Live:   https://senzhang.me/"
Write-Host "    Vercel: https://legacy-personal-website.vercel.app/index.html"
Write-Host ""
& (Join-Path $ScriptDir "qa-urls.ps1") -Port $Port

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 @pyArgs
} else {
    & python @pyArgs
}
