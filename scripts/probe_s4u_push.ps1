# Probe: can a logged-out scheduled task push to GitHub?
#
# Run this from an ELEVATED PowerShell (Run as Administrator). Registering an
# S4U task requires UAC consent, which an agent session cannot obtain, so this
# is the one step that has to be done by a human.
#
# What it does: registers a throwaway task named RalphS4UProbe under the same
# LogonType the real supervisor uses (S4U = runs with nobody logged on), has it
# attempt a no-op `git push --dry-run`, writes the result to a log, then
# unregisters itself.
#
# It does NOT push anything, does NOT touch the RalphSupervisor task, and does
# NOT start the harness.

$ErrorActionPreference = "Stop"
$repo    = "C:\Users\matth\PyCharmProjects\SpaceGame"
$log     = "$env:TEMP\ralph_s4u_probe.log"
$task    = "RalphS4UProbe"

if (Test-Path $log) { Remove-Item $log -Force }

# The probe body: prove identity, then prove write access, capturing everything.
$probe = @"
cd '$repo'
"=== whoami: `$(whoami) ===" | Out-File -FilePath '$log' -Encoding utf8
"=== ssh auth ===" | Out-File -FilePath '$log' -Append -Encoding utf8
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -T git@github.com *>&1 | Out-File -FilePath '$log' -Append -Encoding utf8
"=== git push --dry-run ===" | Out-File -FilePath '$log' -Append -Encoding utf8
git push --dry-run origin master *>&1 | Out-File -FilePath '$log' -Append -Encoding utf8
"=== exit code: `$LASTEXITCODE ===" | Out-File -FilePath '$log' -Append -Encoding utf8
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($probe))

$action    = New-ScheduledTaskAction -Execute "powershell.exe" `
                -Argument "-NoProfile -NonInteractive -EncodedCommand $encoded"
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" `
                -LogonType S4U -RunLevel Highest

Write-Host "Registering probe task '$task' (S4U)..." -ForegroundColor Cyan
Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Force | Out-Null

Write-Host "Running it..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $task

# Wait for it to finish rather than guessing at a sleep duration.
$deadline = (Get-Date).AddSeconds(90)
do {
    Start-Sleep -Seconds 2
    $state = (Get-ScheduledTask -TaskName $task).State
} while ($state -eq "Running" -and (Get-Date) -lt $deadline)

Write-Host "Unregistering probe task..." -ForegroundColor Cyan
Unregister-ScheduledTask -TaskName $task -Confirm:$false

Write-Host ""
Write-Host "==================== RESULT ====================" -ForegroundColor Yellow
if (Test-Path $log) {
    Get-Content $log
} else {
    Write-Host "NO LOG WRITTEN. The task did not run, or could not write." -ForegroundColor Red
    Write-Host "That itself is a failure signal for the S4U path." -ForegroundColor Red
}
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Read it this way:" -ForegroundColor Green
Write-Host "  'Hi MRittinghouse' + 'Everything up-to-date'  ->  S4U push WORKS, reboot recovery is covered."
Write-Host "  'Permission denied (publickey)'               ->  S4U cannot read the key; fall back to autologon."
Write-Host "  no log at all                                 ->  the task could not run; fall back to autologon."
Write-Host ""
Write-Host "Confirming nothing was left registered:" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "Ralph*" -ErrorAction SilentlyContinue | Select-Object TaskName, State
Write-Host "(no rows above = clean)"
