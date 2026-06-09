#Requires -Version 5.1
<#
.SYNOPSIS
  Start a local HTTP server for the archived senzhang.me snapshot.
.EXAMPLE
  .\scripts\serve.ps1
  .\scripts\serve.ps1 -Date 2026-06-05 -Port 8765
#>
param(
    [string]$Date,
    [int]$Port = 8765,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$PythonScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "serve.py"

$pyArgs = @($PythonScript, "--port", $Port)
if ($Date) { $pyArgs += @("--date", $Date) }
if ($NoOpen) { $pyArgs += "--no-open" }

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 @pyArgs
} else {
    & python @pyArgs
}
