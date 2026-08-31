# Ralph run handoff — 2026-08-30

Written for whoever picks this up next, including a fresh Claude Code session
with no memory of the conversation that produced it.

## What this is

`ralph` is an autonomous sprint harness working through
`requirements/roadmap/ROADMAP.md`. It is armed as a Windows Scheduled Task
(`RalphSupervisor`, LogonType **S4U**, ExecutionTimeLimit **PT0S**, at-startup
plus a 15-minute repetition trigger) and is meant to run unattended for days
while the operator is away. It commits and pushes to `master` over SSH.

## Current state

- **The run is LIVE.** A2-5 completed end to end at 2026-08-30 22:08 — the first
  sprint to pass plan → implement → review → gate → done since the arc stalled.
  A2-6 picked up at 22:14.
- **Done:** A2-1, A2-2, A2-3, A2-4, A2-5.
- **Blocked:** none in the A2 arc. `SA-F2` and `UI-BOUNDS-1` are blocked from
  April and are deliberately left that way.
- Suite green at **11063 passing / 100 skipped**, ~60s at `-n 8`.

## The one thing to understand first

The previous handoff blamed leaked pytest workers and suspected the S4U token.
Both were wrong, or at least secondary. **One fault caused most of it:**

`pygame.mixer.music.unpause()` deadlocks intermittently and never returns.
py-spy caught it on three separate wedged processes, always the same stack:

    resume_music (spacegame/engine/audio_manager.py)
    _close_pause_menu (spacegame/engine/game.py)
    _handle_pause_menu (spacegame/engine/game.py)
    step (spacegame/engine/game.py)
    step_once (tools/crawler/crawler.py)
    test_crawler_determinism_across_two_runs (tests/test_crawler/test_integration.py)

It wore two masks. Under `-n 8` it wedges a worker and the controller waits
forever, which read as "xdist cannot start workers". Under `-n 0` it wedges the
main process, which read as "serial hangs too". It is **not** session-specific;
it took down an interactive full-suite run after 927 CPU-seconds.

**pytest-timeout cannot catch it.** `timeout = 120` is set in `pyproject.toml`,
and the timer thread was armed for that exact test — but the block is inside a C
call holding the GIL, so the timer never runs. Only an out-of-process kill
bounds this class of hang. Do not trust the per-test timeout to protect the
suite from a C-level block.

Fixed in `51ebcf3` by having the crawler disable audio on its own `Game`
instance (`AudioManager.disable()`). Per-instance, deliberately **not** via the
`get_audio_manager()` singleton — that is process-global, and under `-n 0` the
crawler shares a process with tests asserting real mixer behaviour. The
underlying SDL_mixer deadlock is untouched; only the path into it is removed.

## Everything else that was fixed

| Commit | What |
|---|---|
| `12c25b6` | The suite was **rewriting the real `ROADMAP.md`**. `_sync_roadmap_index` resolved the file through a second binding no fixture could redirect, so the harness's own gate dirtied the tree the next launch then refused. |
| `8fdeba8` | `update_status` wrote a sprint's section but left its index row stale. Stuck-sprint recovery runs **before** baseline capture, so the harness committed drift and then failed a suite on drift it had created one second earlier. Index now syncs inside the write. |
| `5f95cda` | Baseline capture retries once **on a hang only**. A suite that ran and was red is evidence about the code and must stop the run; one that never finished is evidence about the machine. |
| `dfffb98`, `2af03d7` | Gate parallel probe 2700s → 1500s, sized from session-0 data. |
| `aaefc18` | A dirty tree left by a **dead** harness is stashed and the run continues, instead of bricking every future launch. |

## Read this before trusting a measurement

**An interactive timing is not evidence about what the harness does.** The same
`pytest -n 8` command takes 60–77s in an interactive session (session 1) and
322s under the Scheduled Task (session 0). Check `Win32_Process.SessionId` — the
harness runs in **session 0**, your shell in session 1. A 5x gap on identical
work sent several of this project's earlier conclusions the wrong way, including
two of mine.

`py-spy` is installed (`pip install py-spy`). For any future hang, this is the
first move, not the last:

    C:\Python314\Scripts\py-spy.exe dump --pid <pid>

It turned three days of guessing into a named line of code in one command.

## Open questions

1. **Something killed a supervisor+harness pair outright** on 2026-08-29 at
   13:15:01, mid-gate, with no exit logged by either. Not the stray sweep (it
   logs its kills), not heartbeat staleness (the beat is timer-based precisely
   so a long phase stays alive), not the 15-minute trigger (that harness
   survived five boundaries first). Task Scheduler's operational log was
   **disabled**, so the evidence was gone. It is **now enabled**, so the next
   occurrence is diagnosable. If instances die roughly every 80 minutes, no
   sprint whose gate falls back to the serial run can finish.
2. **An unidentified flaky test.** A2-5's gate failed once, then passed on
   re-run and was correctly treated as a flake. The gate logs only a summary,
   not the failing test names, so it is unnamed. If flakes start costing gates,
   make the gate record the failing test IDs before its re-run.
3. `test_dialogue_response_tooltip.py::TestTooltipGeometry::test_right_side_clipping_flips_to_left`
   failed once in session 0 and has passed everywhere since. `_tooltip_rect_for_button`
   compares against the `WINDOW_WIDTH` constant and nothing patches it, so there
   is no explanation yet. Possibly the same flake as (2).

## Operating notes

- **Never run `pytest -n auto`** — it hangs on this host. Use `-n 8`.
- **Do not push to `master` from another clone** while the run is live. Every
  remote channel ends in one `git push origin HEAD` and nothing rebases. Working
  in *this* clone is fine — the harness picks up local commits.
- **A dirty tree still blocks a launch** unless a stale lock proves a harness
  died. If you leave edits uncommitted while no harness holds the lock, the run
  stops. Commit before you walk away.
- **`STATUS.md` on GitHub is the operator's window.** Banners: `STARVED`,
  `CRASHED`, `STALE HEARTBEAT`, `NO LIVE HARNESS`, `TEST SUITE FAILING`,
  `INFRASTRUCTURE FAILING`, `PUSH FAILING`, `STRANDED`.
- **To pause without unregistering:**
  `python -c "from ralph import supervisor; supervisor.record_terminal_stop('paused')"`
  and resume with `supervisor.clear_terminal_stop()`. Note the marker is checked
  at supervisor **startup**, so an already-running supervisor finishes its
  current cycle.
- **To stop entirely**, elevated:
  `Unregister-ScheduledTask -TaskName 'RalphSupervisor' -Confirm:$false`
- `harness._sweep_stray_pytest()` clears leaked pytest trees and works from an
  elevated interactive shell too — it tree-kills the xdist controllers, which
  takes every worker with them.
- **A missing `PHASE_OK` sentinel is not missing work.** Both A2-5 and A2-6 had
  complete, committed implementations that the harness treated as unfinished
  because the agent died before writing its sentinel. The planner now detects
  this and reports `PHASE_BLOCKED: already implemented`. Check `git log` before
  assuming a recovered sprint needs redoing.

## Design decisions worth not re-litigating

- Investment is **fully oblique** (no meter, no panel); a dilemma **cannot be
  declined**; capstones are capped **diegetically** by the dilemma graph. Because
  the first two remove every warning channel but one, the telegraph is an
  enforced invariant: A2-9 must fail the build when
  `telegraph_threshold >= collision_threshold`.
- **Act I's cast and worlds stay in Act I.** Only the player's crew and the
  perpetrators survive the galaxy's destruction. Systems travel; cast and place
  do not.
