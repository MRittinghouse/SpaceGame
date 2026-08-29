# Ralph run handoff — 2026-08-29

Written for whoever picks this up next, including a fresh Claude Code session
with no memory of the conversation that produced it.

## What this is

`ralph` is an autonomous sprint harness working through
`requirements/roadmap/ROADMAP.md`. It is armed as a Windows Scheduled Task
(`RalphSupervisor`, LogonType **S4U**, ExecutionTimeLimit **PT0S**, at-startup
plus a 15-minute repetition trigger) and is meant to run unattended for seven
days while the operator is away. It commits and pushes to `master` over SSH.

## Current state

- **Done:** A2-1 (lens registry), A2-2 (authoring guide), A2-3 (capstone
  format), A2-4 (investment tracking).
- **Blocked:** none in the A2 arc. `SA-F2` and `UI-BOUNDS-1` are blocked from
  April and are deliberately left that way.
- **Queue:** 33 todo. Not starved.
- **The run is STOPPED.** The supervisor recorded a deliberate stop at
  `2026-08-29 03:09:57` after three consecutive failures and has been correctly
  refusing to relaunch every 15 minutes since. `ralph/supervisor_stop.json`
  holds that marker; deleting it is what says "the cause is fixed, go again".

## What went wrong, and why it mattered

The post-review test gate's parallel `pytest` run hung on every sprint that
reached it. Each hang leaked its xdist worker tree. By morning there were **66
python processes** alive from a six-minute window overnight, holding 2.1 GB.

The leak is **self-amplifying**, which is what made it fatal rather than
untidy: every leaked worker competes with the next run, so the next run is
likelier to hang, which leaks more workers. Direct measurement: the
`tests/test_ralph/` suite alone runs in ~9s clean and took **117s** with the
strays present. The machine read 8% CPU throughout, because the leaked
processes were stalled rather than busy, which makes "load looks fine"
misleading here.

Two sprints (A2-1, A2-4) were marked **blocked** by this despite their work
being complete, correct, and committed. A2-1 blocked strands 18 downstream
sprints. Both have been reset to `done` with the reasoning in their activity
logs.

## Fixes already in (all pushed)

| Commit | What |
|---|---|
| `2492f26` | A hung parallel pytest retries **serially** instead of failing. Also pins pytest's temp root outside the repo. |
| `97f7497` | Gate budgets sized against observed speed: 2700s parallel, 7200s serial. The old 2400s serial budget could not finish ~11k tests even in principle. |
| `d61a23e` | A gate **timeout** now returns `INFRA_ERROR`, not `BLOCKED`. A suite that ran and was red is evidence about the code; one that never finished is evidence about the machine. |
| `fa49b6f` | `harness._sweep_stray_pytest` kills leftover pytest trees at pre-flight. |
| `76e8154` | `scripts/resume_run.ps1` — one elevated command to clear the backlog and resume. |

## What to do next

1. **From an ELEVATED PowerShell** (the leaked processes belong to the task's
   S4U token; a normal shell gets Access Denied from both `Stop-Process` and
   `taskkill`, and cannot even read their `CommandLine`):

       powershell -ExecutionPolicy Bypass -File C:\Users\matth\PyCharmProjects\SpaceGame\scripts\resume_run.ps1

   It kills stale python trees, clears the stop marker, restarts the task, and
   prints the log.

2. **Watch one full sprint through its gate.** That is the open question: does
   the new sweep break the amplification loop, or does the S4U token itself
   cause the hang? The suite runs in ~116s interactively and hung repeatedly
   under the task, so S4U is implicated but not proven.

3. **If the gate still hangs with a clean process table**, S4U is the cause.
   Options, in order of preference:
   - Switch the task to `InteractiveToken` (processes become killable and
     inspectable, and the hang likely disappears). Cost: only runs while
     logged on, so a reboot needs autologon.
   - Drop the gate to `-n 4`.
   - Disable the gate and rely on the startup baseline. This is the weakest
     option: the gate is what stops agents pushing a red tree for days.

## Operating notes

- **Never run `pytest -n auto`** — it hangs 6 runs in 10 on this host. Use `-n 8`.
- **Do not push to `master` from anywhere else** while the run is live. Every
  remote channel ends in one `git push origin HEAD` and nothing rebases, so a
  diverged remote freezes `STATUS.md` while the harness keeps working. Auto
  rebase was considered and deliberately rejected: a conflicted rebase leaves a
  detached HEAD that fails pre-flight repeatedly, and `ROADMAP.md` is the
  hottest file, so conflict would be the default outcome rather than the tail.
- **`STATUS.md` on GitHub is the operator's window.** Banners: `STARVED`,
  `CRASHED`, `STALE HEARTBEAT`, `NO LIVE HARNESS`, `TEST SUITE FAILING`,
  `INFRASTRUCTURE FAILING`, `PUSH FAILING`, `STRANDED`.
- **To pause without unregistering**, from any shell:
  `python -c "from ralph import supervisor; supervisor.record_terminal_stop('paused')"`
  and resume with `supervisor.clear_terminal_stop()`.
- **To stop entirely**, elevated:
  `Unregister-ScheduledTask -TaskName 'RalphSupervisor' -Confirm:$false`
- S4U processes and files are **opaque to a non-elevated session**: command
  lines read empty and the harness's pytest temp root is Access Denied. A
  running harness can therefore look like nothing at all. Check with an
  elevated shell before concluding it is dead.

## Design decisions worth not re-litigating

- Investment is **fully oblique** (no meter, no panel); a dilemma **cannot be
  declined**; capstones are capped **diegetically** by the dilemma graph. Because
  the first two remove every warning channel but one, the telegraph is an
  enforced invariant: A2-9 must fail the build when
  `telegraph_threshold >= collision_threshold`.
- **Act I's cast and worlds stay in Act I.** Only the player's crew and the
  perpetrators survive the galaxy's destruction. Systems travel; cast and place
  do not.
