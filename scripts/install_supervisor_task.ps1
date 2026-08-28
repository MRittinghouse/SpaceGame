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

    UNATTENDED PUSH: SETTLED, and how. This used to be recorded here as an
    open risk, on the reasoning that `origin` was
    https://github.com/MRittinghouse/SpaceGame.git, authenticated by Git
    Credential Manager out of the Windows Credential Manager -- a per-user
    store protected by DPAPI, which is normally unprotected using material
    tied to an interactive logon session. S4U is documented by Microsoft as
    having "restricted access to network resources" and carries no password,
    so whether it could reach that token with nobody logged on was genuinely
    unknown, and the fallback on the table was `-LogonType Password`.

    Commit 81a6af8 settled it by removing the dependency rather than
    testing it: `origin` is now git@github.com:MRittinghouse/SpaceGame.git.
    SSH reads a key file, not a DPAPI-protected credential. The operator
    then ran `scripts\probe_s4u_push.ps1` from an elevated prompt -- it
    registers a throwaway task under this same LogonType, attempts a real
    push, and unregisters itself -- with nobody logged on. It authenticated
    and pushed: exit code 0.

    So: no DPAPI question, no `-LogonType Password`, and the smoke drill
    below does not need to settle this. Re-run `probe_s4u_push.ps1` if
    `origin` ever moves back to HTTPS, if the SSH key is moved or
    passphrase-protected, or if the account this task runs under changes --
    those are the conditions under which the answer would change.

.NOTES
    Run once, elevated (Run as Administrator), after you have:
      1. Read ralph/supervisor.py's module docstring.
      2. Run a smoke drill: `python -m ralph.supervisor` in a foreground
         terminal, confirm it launches the harness, watch a full sprint
         cycle (or a deliberate --dry-run / --max-sprints 1 pass) complete,
         and confirm STATUS.md updates as expected. Unattended `git push`
         is already settled and is NOT part of this drill -- see the
         DESCRIPTION's UNATTENDED PUSH note.
      3. Confirmed `claude` (the CLI) and `git` are on PATH for the SAME
         account this task will run under -- a Scheduled Task's PATH can
         differ from an interactive shell's.

.ARMING
    To actually register the task (NOT done by loading/reading this file):

        powershell -ExecutionPolicy Bypass -File scripts\install_supervisor_task.ps1

    Run that from an elevated ("Run as Administrator") PowerShell prompt.

.LOGGING
    The task redirects nothing, and it does not need to: both components write
    their own files under ralph/logs/ (each rotated once at 5 MB).

        ralph\logs\supervisor.log  -- the supervisor's own account: every
                                       launch, every exit code, every restart
                                       decision, every STATUS.md publish.
        ralph\logs\harness.log     -- the harness's stdout and stderr,
                                       captured by the supervisor's Popen.
                                       This is where a PRE-FLIGHT FAILURE
                                       message lands, and a pre-flight failure
                                       is the most likely way an unattended
                                       run dies.

    Before this, both logged only via `print` and the task discarded that
    stream, so nothing at all was written to disk.

.VERIFYING
    After arming:

        Get-ScheduledTask -TaskName "RalphSupervisor"
        Start-ScheduledTask -TaskName "RalphSupervisor"   # to test without rebooting
        Get-ScheduledTaskInfo -TaskName "RalphSupervisor"  # LastRunTime / LastTaskResult

    Confirm the two settings that killed the previous design:

        (Get-ScheduledTask -TaskName "RalphSupervisor").Settings.ExecutionTimeLimit
            # must be PT0S -- anything else is a deadline on the run
        (Get-ScheduledTask -TaskName "RalphSupervisor").Triggers
            # must include a repetition, not only the boot trigger

.DISARMING
    To remove it later:

        Unregister-ScheduledTask -TaskName "RalphSupervisor" -Confirm:$false
#>

$ProjectRoot = "C:\Users\matth\PyCharmProjects\SpaceGame"

$action = New-ScheduledTaskAction -Execute "python" `
    -Argument "-m ralph.supervisor" `
    -WorkingDirectory $ProjectRoot

# TWO triggers, both load-bearing.
#
# At-startup resumes work after a power cut. On its own, though, it is the only
# way this task can ever start again -- and a task that stops for any other
# reason then waits for a reboot that may never come. Measured: the seven-day
# run this exists for would have ended at hour 72 (see ExecutionTimeLimit
# below) with nothing to restart it.
#
# So a second trigger repeats every 15 minutes, indefinitely, from midnight.
# MultipleInstances = IgnoreNew (set explicitly below) means a firing while the
# supervisor is already running is discarded, so the repetition costs nothing
# in the normal case and heals a KILLED supervisor within a bounded window.
#
# It does NOT resurrect a supervisor that stopped on purpose: the 3-consecutive-
# failure cap lives in an in-process counter, so relaunching a supervisor that
# gave up would grant three fresh harness attempts every 15 minutes forever --
# the unbounded spend the cap exists to prevent. `ralph/supervisor.py` records a
# deliberate stop in `ralph/supervisor_stop.json` and a new instance that finds
# it exits immediately. Delete that file to resume.
$triggerAtBoot = New-ScheduledTaskTrigger -AtStartup
$triggerRepeating = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

# RestartCount/RestartInterval cover the supervisor itself dying (its own
# crash-loop backoff, in ralph/supervisor.py, covers the harness dying
# underneath it). Three restarts five minutes apart is deliberately modest --
# a supervisor that keeps dying needs a human, not an ever-longer leash.
#
# -ExecutionTimeLimit ([TimeSpan]::Zero) => PT0S => run indefinitely. This is
# the single most important argument here. The cmdlet's DEFAULT is PT72H, with
# AllowHardTerminate True (both measured on this host), so without it the Task
# Scheduler service hard-terminates the supervisor after exactly 72 hours --
# the middle of day 3 of a seven-day trip -- and, with an At-startup-only
# trigger, nothing ever brought it back. -RestartCount does not help: it
# governs restart-on-failure, and a scheduler-imposed termination is not a
# failure. The hard termination is also a `.tmp`-orphan trigger (see
# harness._sweep_tmp_orphans), so it took the next launch with it.
#
# Battery settings: DisallowStartIfOnBatteries and StopIfGoingOnBatteries both
# default True, so a UPS that presents itself as a battery would prevent the
# task starting at boot -- the one moment it matters most. Overridden here
# rather than left to a pre-arming check nobody will remember to run.
#
# -StartWhenAvailable so a repetition missed while the machine was asleep fires
# on wake instead of being dropped.
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# S4U: runs whether or not the user is logged on, without storing a
# password -- see the DESCRIPTION's LOGON TYPE note above for why the
# cmdlet's own default (InteractiveToken) is wrong here. The question of
# whether an S4U token can push was settled by probe_s4u_push.ps1 (exit
# code 0 with nobody logged on, against an SSH origin); see UNATTENDED
# PUSH above.
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\$env:USERNAME" `
    -LogonType S4U -RunLevel Highest

Register-ScheduledTask -TaskName "RalphSupervisor" -Action $action `
    -Trigger $triggerAtBoot, $triggerRepeating `
    -Settings $settings -Principal $principal -Description "Ralph harness supervisor (Spec E)"
