#Requires -Version 5.1
param(
    [string]$Date = "2026-06-05",
    [ValidateSet("safe", "normal", "fast")]
    [string]$Profile = "safe"
)
$script = Join-Path $PSScriptRoot "fix-offline-fonts.py"
$args = @($script, $Date, "--profile", $Profile)
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 @args } else { python @args }
