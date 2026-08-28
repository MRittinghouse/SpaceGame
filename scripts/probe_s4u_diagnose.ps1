# Diagnose why Register-ScheduledTask returned Access Denied.
#
# Separates the two causes, which point to opposite conclusions:
#   1. The shell is not actually elevated        -> retry properly, nothing learned yet
#   2. S4U specifically is denied on this account -> real finding, use the fallback
#
# Registers nothing permanent. Any task it creates is removed immediately.

$ErrorActionPreference = "Continue"

Write-Host "=== 1. Is this shell actually elevated? ===" -ForegroundColor Cyan
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$elevated = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "  User:     $($id.Name)"
Write-Host "  Elevated: $elevated" -ForegroundColor $(if ($elevated) {"Green"} else {"Red"})
if (-not $elevated) {
    Write-Host ""
    Write-Host "  STOP. This shell is NOT elevated, so nothing below is conclusive." -ForegroundColor Red
    Write-Host "  Close it. Press Win, type 'powershell', then Ctrl+Shift+Enter to" -ForegroundColor Yellow
    Write-Host "  launch as Administrator, and re-run this script there." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "=== 2. Account type (S4U behaves differently for MSA/AzureAD) ===" -ForegroundColor Cyan
try {
    $acct = Get-CimInstance Win32_UserAccount -Filter "Name='$env:USERNAME'" -ErrorAction Stop |
            Select-Object -First 1 Name, Domain, LocalAccount, SID
    if ($acct) {
        Write-Host "  Name=$($acct.Name)  Domain=$($acct.Domain)  LocalAccount=$($acct.LocalAccount)"
    } else {
        Write-Host "  No local Win32_UserAccount row. Likely a Microsoft or AzureAD account," -ForegroundColor Yellow
        Write-Host "  which commonly cannot use S4U." -ForegroundColor Yellow
    }
} catch { Write-Host "  Could not query: $_" }

Write-Host ""
Write-Host "=== 3. Can this shell register a PLAIN task (no S4U)? ===" -ForegroundColor Cyan
$plainOk = $false
try {
    $a = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c exit"
    Register-ScheduledTask -TaskName "RalphDiagPlain" -Action $a -Force -ErrorAction Stop | Out-Null
    $plainOk = $true
    Write-Host "  PLAIN task registration: SUCCEEDED" -ForegroundColor Green
    Unregister-ScheduledTask -TaskName "RalphDiagPlain" -Confirm:$false
} catch {
    Write-Host "  PLAIN task registration: FAILED -- $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 4. Can this shell register an S4U task? ===" -ForegroundColor Cyan
$s4uOk = $false
try {
    $a = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c exit"
    $p = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" `
            -LogonType S4U -RunLevel Highest
    Register-ScheduledTask -TaskName "RalphDiagS4U" -Action $a -Principal $p -Force -ErrorAction Stop | Out-Null
    $s4uOk = $true
    Write-Host "  S4U task registration: SUCCEEDED" -ForegroundColor Green
    Unregister-ScheduledTask -TaskName "RalphDiagS4U" -Confirm:$false
} catch {
    Write-Host "  S4U task registration: FAILED -- $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=================== VERDICT ===================" -ForegroundColor Yellow
if (-not $elevated) {
    Write-Host "  Not elevated. Re-run as Administrator; no conclusion yet." -ForegroundColor Red
} elseif ($plainOk -and $s4uOk) {
    Write-Host "  Both work. The earlier failure was the non-elevated shell." -ForegroundColor Green
    Write-Host "  Re-run probe_s4u_push.ps1 here to get the real push answer."
} elseif ($plainOk -and -not $s4uOk) {
    Write-Host "  S4U specifically is denied on this account. REAL FINDING." -ForegroundColor Red
    Write-Host "  Reboot recovery cannot use S4U. Fall back to autologon, or accept"
    Write-Host "  that a power cut pauses the run until someone logs in."
} else {
    Write-Host "  Task registration is blocked outright (policy or rights)." -ForegroundColor Red
    Write-Host "  Scheduled-task reboot recovery is not available on this machine."
}
Write-Host "=============================================="

Write-Host ""
Write-Host "Leftover check (expect no rows):" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "Ralph*" -ErrorAction SilentlyContinue | Select-Object TaskName, State
