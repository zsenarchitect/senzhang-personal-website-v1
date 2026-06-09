#Requires -Version 5.1
param([string]$Date = "2026-06-05")
$script = Join-Path $PSScriptRoot "repair-html.py"
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 $script $Date } else { python $script $Date }
