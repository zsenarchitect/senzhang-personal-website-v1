#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Date = if ($args[0]) { $args[0] } else { "2026-06-05" }
Set-Location $RepoRoot
py -3 scripts\fix-offline-videos.py $Date @args[1..($args.Length)]
exit $LASTEXITCODE
