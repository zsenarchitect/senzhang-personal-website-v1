# Monitor job-hunt staging download every 15 minutes; exit when complete.
$Repo = "C:\Users\szhang\github\Personal\senzhang-personal-website-v1"
$Staging = Join-Path $Repo "dev\job-hunt-staging"
$Log = Join-Path $Staging "monitor.log"
$DownloadLog = Join-Path $Staging "download.log"
$Target = 2224

function Get-StagingStats {
    $files = Get-ChildItem $Staging -Recurse -File -ErrorAction SilentlyContinue
    $n = ($files | Measure-Object).Count
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    $gb = if ($bytes) { [math]::Round($bytes / 1GB, 2) } else { 0 }
    return @{ Count = $n; GB = $gb }
}

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $s = Get-StagingStats
    $pct = if ($Target -gt 0) { [math]::Round(100 * $s.Count / $Target, 1) } else { 0 }
    $tail = ""
    if (Test-Path $DownloadLog) {
        $tail = (Get-Content $DownloadLog -Tail 1 -ErrorAction SilentlyContinue) -join ""
    }
    $line = "{0} | files={1}/{2} ({3}%) | {4} GB | last: {5}" -f $stamp, $s.Count, $Target, $pct, $s.GB, $tail
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Output $line

    $done = $false
    if (Test-Path $DownloadLog) {
        $done = Select-String -Path $DownloadLog -Pattern "Done in" -Quiet -ErrorAction SilentlyContinue
    }
    if ($done) {
        $final = "STAGING_DOWNLOAD_COMPLETE | files={0} | {1} GB" -f $s.Count, $s.GB
        Add-Content -Path $Log -Value $final -Encoding UTF8
        Write-Output $final
        exit 0
    }

    Start-Sleep -Seconds 900
}
