# Clear the leaked pytest processes and resume the run.
#
# Run from an ELEVATED PowerShell (Win, type "powershell", Ctrl+Shift+Enter).
#
# Why elevation is needed: the Scheduled Task runs as S4U, so the processes it
# leaked belong to that token. A non-elevated shell gets Access Denied from
# both Stop-Process and taskkill, and cannot even read their CommandLine.
#
# What happened: gate runs whose parallel pytest hung left their worker trees
# behind. 66 python processes accumulated overnight, holding 2.1 GB, and each
# leaked worker made the next run likelier to hang. The run stopped after three
# consecutive failures. `harness._sweep_stray_pytest` now clears these at
# pre-flight, so this should be a one-off cleanup of the existing backlog.

$ErrorActionPreference = "Continue"
$repo = "C:\Users\matth\PyCharmProjects\SpaceGame"

Write-Host "=== 1. Leaked python processes ===" -ForegroundColor Cyan
$before = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
$mem = [math]::Round(((Get-Process python -ErrorAction SilentlyContinue | Measure-Object WS -Sum).Sum / 1GB), 2)
Write-Host "  before: $before processes, ${mem} GB"

# Kill trees older than 30 minutes. Anything the harness starts after this runs
# is far younger, so a live run is never touched.
$cut = (Get-Date).AddMinutes(-30)
$stale = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" |
    Where-Object { $_.CreationDate -lt $cut }
Write-Host "  older than 30 min: $($stale.Count)"
foreach ($p in $stale) { cmd /c "taskkill /F /T /PID $($p.ProcessId)" 2>&1 | Out-Null }
Start-Sleep -Seconds 5
$after = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "  after: $after processes" -ForegroundColor $(if ($after -lt $before) {"Green"} else {"Red"})

Write-Host ""
Write-Host "=== 2. Clear the supervisor's stop marker ===" -ForegroundColor Cyan
# The supervisor stopped deliberately after 3 consecutive failures and has been
# correctly refusing to relaunch since. Clearing the marker is what says
# "the cause is fixed, go again".
$marker = Join-Path $repo "ralph\supervisor_stop.json"
if (Test-Path $marker) {
    Get-Content $marker | Write-Host
    Remove-Item $marker -Force
    Write-Host "  marker cleared" -ForegroundColor Green
} else {
    Write-Host "  no marker present"
}

Write-Host ""
Write-Host "=== 3. Restart the supervisor ===" -ForegroundColor Cyan
Start-ScheduledTask -TaskName "RalphSupervisor"
Start-Sleep -Seconds 20
$t = Get-ScheduledTask -TaskName "RalphSupervisor"
Write-Host "  task state: $($t.State)"
Write-Host ""
Write-Host "--- harness log (last 8 lines) ---" -ForegroundColor Cyan
$log = Join-Path $repo "ralph\logs\harness.log"
if (Test-Path $log) { Get-Content $log -Tail 8 } else { Write-Host "  (no log yet)" }

Write-Host ""
Write-Host "Expect the pre-flight to report 'Killed N stray pytest process tree(s)'" -ForegroundColor Green
Write-Host "on future launches if any leak again. Watch STATUS.md on GitHub." -ForegroundColor Green
