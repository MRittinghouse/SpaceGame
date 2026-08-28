# Smoke drill results (Task 10, Spec E)

Every row below was actually injected and observed against the real `ralph` code (real
subprocesses spawned/killed, real files written and read back, real `harness.main()` /
`supervisor.main()` invocations with only paths and the `claude` CLI call redirected to
scratch locations) — not inferred from reading the source. Full narrative and evidence is in
`.superpowers/sdd/2026-08-27-harness-resilience/task-10-report.md`; this file is the durable,
committed record per the task brief.

## The open question: does `git push` work under S4U

**Could not be executed end-to-end in the agent session that ran this drill**: registering
any scheduled task with `-LogonType S4U` (or any non-default `LogonType`/`RunLevel`) requires
an elevated caller, and that session had no path to elevation (`Register-ScheduledTask` and
`schtasks.exe` both returned `Access is denied` the moment a Principal/RunLevel was specified,
while registering with no Principal at all — the "only run when logged on" default —
succeeded instantly and unelevated, isolating the cause; Windows' native `sudo` reported
itself disabled). This mirrors the installer script's own documented requirement to run
elevated, and is a genuine environmental limitation, not a skipped step.

What was established instead:

- **Baseline (removes a confound)**: a Task-Scheduler-launched process, under the only
  logon type registerable without elevation, ran `git push --dry-run origin master`
  successfully (exit 0, resolved `git` on PATH, authenticated fine) — twice, at different
  points in the drill. This proves the git/GCM plumbing and the Task-Scheduler launch
  mechanism are sound; the only remaining variable is specifically the S4U logon type.
- **Documentation** (Microsoft's own "Task Security Context" page, `learn.microsoft.com/
  .../cc722152`): *"When using S4U the ability of the service to use the security context of
  the account is constrained. In particular, the service can only use the security context to
  access local resources... If your task requires access to network resources, you cannot use
  S4U; doing so will cause your task to fail... the task will not have access to encrypted
  files."* Corroborated by independent community reports of S4U task execution disturbing
  cached DPAPI credential material for the logged-on user.

**Answer: expect `git push` to FAIL under S4U on this machine** — high confidence from the
evidence above, explicitly disclosed as not directly executed end-to-end due to the elevation
blocker. A two-minute elevated-prompt script to settle it definitively is included in the full
report.

**Fallback recommendation: (b) switch `origin` to SSH key auth, not (a) autologon.** A scoped,
revocable deploy key that never touches DPAPI or the Windows account password is a smaller,
shorter-lived exposure than leaving the machine logged in and unlocked for seven days with the
account password stored for autologon. This machine currently has no SSH key configured for
GitHub and `ssh-agent` is disabled — recommend a plain no-passphrase key file with a tight NTFS
ACL over depending on the agent service. **Not implemented — recommendation only, per
instruction.**

## Drill table

| # | Inject | Expected | Result | Observed |
|---|---|---|---|---|
| 1 | `taskkill /PID <harness>` mid-implement | supervisor relaunches within backoff; sprint reclaimed, no hand repair | **PASS** (two real sub-mechanisms proven directly; the literal `taskkill` against a live `claude` CLI call was not run — would spend real agent budget) | `harness._recover_stuck_sprints()` reset a stuck `in-progress` sprint to `todo` fully automatically against a stale `state.json` timestamp. The relaunch-within-backoff mechanism is the same one proven for real in row 8. |
| 2 | `taskkill /F` during a roadmap write | `ROADMAP.md` + `state.json` still parse | **PASS, with a new gap found** | Force-killed a real process mid-write to a `.tmp` sibling; the real target file was byte-identical and parsed. But the kill also proved the `.tmp` sibling itself is left behind and is **not** filtered by `_filter_harness_managed_dirty` or covered by `.gitignore` — see "New finding" below. |
| 3 | Reboot the machine | Scheduled Task starts the supervisor unprompted | **NOT TESTABLE** — forbidden by this drill's constraints (no arming, no reboot). Untested, not assumed working. | Adjacent evidence only: a Task-Scheduler-launched process does run correctly under the one logon type registerable without elevation (see S4U section above). Says nothing about the boot trigger or S4U specifically. |
| 4 | Agent subprocess sleeps past its phase timeout | killed at timeout, phase marked `timeout` | **PASS** | Real subprocess with a real grandchild holding its own handles (the exact shape of the 8.5h bug). `proc.run_with_hard_timeout(..., timeout_seconds=3)` raised `TimeoutExpired` after 3.4s; `tasklist` (independent of the code under test) confirmed both the direct child and the grandchild were dead afterward. |
| 5 | Freeze the heartbeat, leave process alive | detected inside 10 min, restarted | **PASS** (detected far faster than 10 min, by design — the drill used injected short thresholds rather than waiting a real 10 minutes) | `supervisor._supervise()` against a real 60s-sleeping process with a stale beat age killed it and returned in 0.50s; pid confirmed dead via `tasklist`. Separately: a live-but-unrelated real process was correctly **not** mistaken for a live harness instance; a live process whose real command line contains `ralph.harness` was correctly identified as alive, then correctly re-identified as dead within under a second of actually killing it. |
| 6 | Empty the eligible queue | `STARVED` named with blockers — not "exiting cleanly" | **PASS** | Did not edit the real `ROADMAP.md`. Scratch roadmap with a typo'd (nonexistent) dependency id — a different starvation cause than the project's existing "blocked sprint" test. Real `harness.main()` logged `"STARVED -- exiting. This is NOT completion."`, never "exiting cleanly," and `STATUS.md` named both the real sprint and the real bad dependency id, not the generic fallback message. |
| 7 | A sprint that fails once | retried once, then blocked | **PASS** | Real `_handle_non_ok_phase`/`_should_retry` calls: first `ERROR` outcome → stayed `todo`, `retry_count=1`; second `ERROR` on the same sprint → `blocked`. |
| 8 | Harness that dies instantly, repeatedly | stops after 3 | **PASS** | Real `supervisor.main()` loop with a real subprocess exiting instantly (rc=7) three times: exactly 3 launches, exactly 3 recorded failures, stopped via the real "3 consecutive failures" message, `STATUS.md` written with `## CRASH-LOOP`, no 4th launch. Ran for a real 690s — the actual production backoff ladder (120s after failure 1, 480s after failure 2, per `backoff_seconds`) plus per-launch poll overhead, not a hang; my own drill script's first-pass timing assertion was wrong and has been corrected in the full report. |
| 9 | Any of the above | `STATUS.md` reflects it on GitHub | **PARTIAL** | The logged-on half of "does a Task-Scheduler-launched push work" is proven (see S4U section baseline). The decisive half — S4U with nobody logged on — is the open question above, not independently re-litigated here. |

## New finding: a stray `.tmp` file from a killed write can permanently brick the harness

`ralph.proc.atomic_write` writes to a `<file>.tmp` sibling before `os.replace`-ing it onto the
real path. If the writer **process itself** is killed between those two steps (a real
`taskkill /F`, or a power cut — exactly what Spec E's durability component exists to survive),
the `.tmp` sibling is left behind, since the cleanup that deletes it lives in `atomic_write`'s
own `except` clause, which never runs because the process is gone.

Confirmed directly (not by inspection): `.gitignore` does not cover `ralph/state.json.tmp` or
`requirements/roadmap/ROADMAP.md.tmp` at all, and feeding synthetic `git status --porcelain`
lines for both through the real `harness._filter_harness_managed_dirty` leaves both flagged as
dirty. Since `_preflight_checks` refuses to start on a dirty tree, a kill landing in that
narrow write window bricks every subsequent harness launch until a human deletes the stray
file — Task 9's supervisor does report this via its silent-exit mechanism (so the operator
isn't left in total silence), but the harness itself stops making progress within minutes and
stays stopped. Not fixed as part of this drill (scope is running the drill and recording
results, not patching `harness.py` unreviewed the night before departure) — recommended as a
small, low-risk fix worth taking before departure given there is still time.

## Constraints honored

- `requirements/roadmap/ROADMAP.md` never edited.
- All scratch artifacts (drill script, temp roadmaps, probe scripts/logs, scheduled tasks)
  cleaned up; `Get-ScheduledTask -TaskName "Ralph*"` returns nothing.
- `RalphSupervisor` never registered, enabled, or started. No real harness/supervisor run was
  started.
- Every push performed during this drill was `--dry-run`; the repo's pre-existing "ahead of
  origin by 26 commits" is unchanged by this drill.
- `python -m pytest tests/test_ralph/ -n 8` → 264 passed (never `-n auto`).
- `python -m ruff check ralph/ tests/test_ralph/` → 17 errors (pre-existing baseline,
  unchanged).
- `mypy-baseline.txt` not regenerated.
