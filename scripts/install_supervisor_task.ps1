<#
.SYNOPSIS
    Registers the ralph supervisor to start at boot, so a power cut resumes
    unattended work without anyone logging in.

.DESCRIPTION
    This script is DISARMED by design: it only DEFINES the scheduled task
    below and does nothing until you deliberately run it yourself. Nothing
    in the harness-resilience work runs this automatically, and it is not
    wired into any CI, pre-commit, or agent workflow. Registering a
    Scheduled Task is a system-level change outside the repo -- it must be
    a deliberate, human decision, made after a smoke drill has validated
    the supervisor + harness pair (see ARMING below).

    Once armed, `RalphSupervisor` runs `python -m ralph.supervisor` at
    startup. The supervisor itself relaunches `python -m ralph.harness`
    under a bounded restart policy (ralph/supervisor.py) -- this task only
    has to survive a reboot, not a crash loop; that part is the
    supervisor's job.

    LOGON TYPE (fix round 1, Finding 1): registered with an explicit
    `-Principal` using `-LogonType S4U`, NOT the default. `Register-
    ScheduledTask` with no `-Principal`/`-User`/`-Password` defaults to
    `InteractiveToken`, which only runs while the registering user is
    logged on -- exactly backwards for a task whose entire purpose is
    resuming work after a reboot nobody is present for. S4U runs whether
    or not the user is logged on, and does so WITHOUT storing the user's
    password (unlike `-LogonType Password`, which needs `-User`/`-Password`
    at registration and would store a real credential for the task to use).

    KNOWN OPEN RISK, must be settled by the smoke drill before relying on
    this: the harness does `git push` after each sprint so STATUS.md is
    readable from a phone. This repo authenticates to `origin`
    (https://github.com/MRittinghouse/SpaceGame.git) via Git Credential
    Manager (`credential.helper=manager`), which stores its token in the
    Windows Credential Manager -- a per-user store protected by DPAPI,
    which in turn is normally unprotected using material tied to an
    interactive logon session. An S4U token is explicitly documented by
    Microsoft as having "restricted access to network resources" and does
    NOT carry the user's password, so whether it can load enough of the
    user's profile/DPAPI context to read that stored token -- specifically
    in the "nobody is logged on" case this task exists for -- is NOT
    confirmed. If it cannot, `git push` silently fails, STATUS.md is never
    updated, and the operator sees nothing for seven days -- the exact
    failure this whole task exists to prevent. The smoke drill (step 2
    below) MUST include triggering this task (`Start-ScheduledTask`) while
    genuinely logged off (or via `psexec -u <user>` / a second remote
    session, not just an unlocked desktop) and confirming a real `git push`
    succeeds, not just that the harness launches. If it fails, the fallback
    is `-LogonType Password` (stores the password, but gets a full
    interactive-equivalent token) or switching the credential store to one
    that isn't DPAPI/session-bound (e.g. GCM's plaintext store, or a
    machine-scoped rather than per-user secret) -- both are a deliberate,
    separate decision, not made here.

.NOTES
    Run once, elevated (Run as Administrator), after you have:
      1. Read ralph/supervisor.py's module docstring.
      2. Run a smoke drill: `python -m ralph.supervisor` in a foreground
         terminal, confirm it launches the harness, watch a full sprint
         cycle (or a deliberate --dry-run / --max-sprints 1 pass) complete,
         confirm STATUS.md updates as expected, AND -- separately, after
         arming -- confirm `git push` succeeds when the task runs under S4U
         with nobody logged on (see the DESCRIPTION's KNOWN OPEN RISK).
      3. Confirmed `claude` (the CLI) and `git` are on PATH for the SAME
         account this task will run under -- a Scheduled Task's PATH can
         differ from an interactive shell's.

.ARMING
    To actually register the task (NOT done by loading/reading this file):

        powershell -ExecutionPolicy Bypass -File scripts\install_supervisor_task.ps1

    Run that from an elevated ("Run as Administrator") PowerShell prompt.

.VERIFYING
    After arming:

        Get-ScheduledTask -TaskName "RalphSupervisor"
        Start-ScheduledTask -TaskName "RalphSupervisor"   # to test without rebooting
        Get-ScheduledTaskInfo -TaskName "RalphSupervisor"  # LastRunTime / LastTaskResult

.DISARMING
    To remove it later:

        Unregister-ScheduledTask -TaskName "RalphSupervisor" -Confirm:$false
#>

$ProjectRoot = "C:\Users\matth\PyCharmProjects\SpaceGame"

$action = New-ScheduledTaskAction -Execute "python" `
    -Argument "-m ralph.supervisor" `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger -AtStartup

# RestartCount/RestartInterval cover the supervisor itself dying (its own
# crash-loop backoff, in ralph/supervisor.py, covers the harness dying
# underneath it). Three restarts five minutes apart is deliberately modest --
# a supervisor that keeps dying needs a human, not an ever-longer leash.
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)

# S4U: runs whether or not the user is logged on, without storing a
# password -- see the DESCRIPTION's LOGON TYPE note above for why the
# cmdlet's own default (InteractiveToken) is wrong here, and the KNOWN
# OPEN RISK note for what the smoke drill must still verify (git push
# reading a DPAPI-protected credential with nobody logged on).
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" `
    -LogonType S4U -RunLevel Highest

Register-ScheduledTask -TaskName "RalphSupervisor" -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description "Ralph harness supervisor (Spec E)"
