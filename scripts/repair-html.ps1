#Requires -Version 5.1
param(
    [string]$Date = "2026-06-05",
    [ValidateSet("safe", "normal", "fast")]
    [string]$Profile = "",
    [string]$Config = ""
)
$script = Join-Path $PSScriptRoot "repair-html.py"
$args = @($script, $Date)
if ($Profile) { $args += @("--profile", $Profile) }
if ($Config) { $args += @("--config", $Config) }
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 @args } else { python @args }
