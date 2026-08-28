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
    startup, under the current user context, with the highest available
    run level. The supervisor itself relaunches `python -m ralph.harness`
    under a bounded restart policy (ralph/supervisor.py) -- this task only
    has to survive a reboot, not a crash loop; that part is the
    supervisor's job.

.NOTES
    Run once, elevated (Run as Administrator), after you have:
      1. Read ralph/supervisor.py's module docstring.
      2. Run a smoke drill: `python -m ralph.supervisor` in a foreground
         terminal, confirm it launches the harness, watch a full sprint
         cycle (or a deliberate --dry-run / --max-sprints 1 pass) complete,
         and confirm STATUS.md updates as expected.
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

Register-ScheduledTask -TaskName "RalphSupervisor" -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Highest -Description "Ralph harness supervisor (Spec E)"
