#Requires -Version 5.1
<#
.SYNOPSIS
  Create a dated 1:1 offline mirror of https://senzhang.me
.DESCRIPTION
  Runs scripts/snapshot.py (stdlib Python crawler). Optional: install HTTrack for
  winget install XavierRoche.HTTrack and use -UseHtTrack.
#>
param(
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$Force,
    [switch]$UseHtTrack
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SnapshotDir = Join-Path (Join-Path $RepoRoot "snapshot") $Date
$PythonScript = Join-Path $RepoRoot "scripts" "snapshot.py"

if ((Test-Path $SnapshotDir) -and -not $Force) {
    throw "Snapshot already exists: $SnapshotDir`nUse -Force to overwrite."
}

if ($Force -and (Test-Path $SnapshotDir)) {
    Remove-Item -Recurse -Force $SnapshotDir
}

if ($UseHtTrack) {
    & $PSScriptRoot\snapshot-httrack.ps1 -Date $Date
    exit $LASTEXITCODE
}

Write-Host "Running Python snapshot (no extra deps required)..."
Write-Host "Date: $Date"
Write-Host ""

$py = @("py", "-3", "python", "python3") | ForEach-Object {
    Get-Command $_ -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
} | Where-Object { $_ } | Select-Object -First 1

if (-not $py) { throw "Python 3 not found on PATH." }

if ($py -match "py(\.exe)?$") {
    & py -3 $PythonScript $Date
} else {
    & $py $PythonScript $Date
}

exit $LASTEXITCODE
