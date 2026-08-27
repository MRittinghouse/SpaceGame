# Spec E — Harness Resilience

**Date**: 2026-08-27
**Status**: draft, pending review
**Arc**: HR (Harness Resilience)
**Follows**: Spec A (complete), Spec B (complete), SUITE-1, SUITE-2
**Built how**: components 1-5 by hand, not as ralph sprints. See "Why this is not a sprint arc".

---

## Why this spec exists

The harness must run unattended for seven days while its operator is away. It
currently cannot, and the evidence is from the last four days rather than from
speculation.

**Ralph completed 14 sprints and died 5 times.**

| Death | Cause |
|---|---|
| QF-6B implement | a 10-minute tool timeout imposed by the launcher |
| SH-1 implement | machine reboot |
| SH-3 | died silently between phases; unnoticed for **19 hours** |
| run 5 | starved by a concurrent full-suite run |
| run 7 | **8.5-hour hang**; `subprocess.run(timeout=600)` never fired |

Every one required a human to notice and recover. Three left a sprint stuck at
`in-progress` holding committed work and no explanation, each reconstructed by
hand. That is roughly one death per three sprints. Queue twenty sprints for a
week and expect six stalls with nobody watching.

Then, on the day this spec was written, the harness demonstrated the other half
of the problem unprompted:

```
[2026-08-27 11:09:17] No eligible sprints. Exiting cleanly.
[2026-08-27 11:09:17] Harness done. Sprints processed this run: 2.
```

At that moment: **15 sprints `todo`, 0 eligible**, five of them stranded behind
`SA-F2`, which was marked `blocked` on 2026-04-29 with
`returncode 1; commits: 0; stdout was short (135 chars) — likely an early bail`.
A transient infrastructure failure, permanently misfiled — four months before
the `INFRA_ERROR` class existed to reset exactly that case to `todo`.

The harness reported success. It has no way to tell "all work is finished" from
"everything is stranded".

## Scope

**In scope — built by hand over two days:**

1. Durability — atomic state writes
2. Liveness — kill-tree on the agent path, plus a heartbeat
3. Supervision — auto-restart, reboot survival, crash-loop backoff
4. Triage — starvation detection, cascade reporting, retry grace
5. Observability — phone-visible status

**In scope — queued as work for the week:**

6. Queue depth — enough eligible sprints to fill seven days

**Out of scope:** anything that changes what the agents build. This spec is
about the harness surviving, not about the game.

## Why this is not a sprint arc

Components 1-5 are built by hand rather than queued.

A sprint that rewrites the timeout logic, executed by the harness whose timeout
logic is broken, is a bad bet: the failure mode under repair is the one that
would interrupt the repair. The same applies to atomic writes (a power cut
mid-sprint corrupts the file the sprint is editing) and to supervision (nothing
supervises the supervisor's own sprint).

Content sprints have no such circularity, so the week's work is queued normally.

---

## 1. Durability

`ROADMAP.md` and `state.json` are written with a plain `write_text`:

```python
ROADMAP_PATH.write_text(content, encoding="utf-8")   # roadmap_state.py:83
STATE_FILE.write_text(json.dumps(payload), ...)      # harness.py:113
```

Neither is atomic. A power cut mid-write truncates the file. `ROADMAP.md` is
~9,000 lines and holds every sprint definition; `state.json` is what the harness
loads to know where it was. Git versions the roadmap between commits, but the
harness writes it far more often than it commits.

**Change:** an `_atomic_write(path, text)` helper — write `path.tmp` in the same
directory, `flush` + `fsync`, then `os.replace(tmp, path)`, which is atomic on
Windows and POSIX. Same-directory temp keeps it on one volume, which
`os.replace` requires on Windows.

Applied to: `ROADMAP.md`, `state.json`, `SUMMARY.md`, the lock file, `STATUS.md`.

## 2. Liveness

**The kill-tree gap.** SUITE-1 built a hard-timeout helper that kills the whole
process tree with `taskkill /F /T`, and wired it into baseline capture only. The
agent invocation still uses plain `subprocess.run(timeout=...)`:

```python
result = subprocess.run(cmd, ..., timeout=timeout, ...)   # agents.py:202
```

That is the construct that failed during the 8.5-hour hang: on Windows the
timeout kills the direct child, but `communicate()` keeps blocking while
grandchildren hold the stdout pipe. Phases are where the harness spends hours,
so this is where a days-long stall actually comes from.

**Change:** generalise SUITE-1's helper to `_run_with_hard_timeout` and use it
for agent invocation as well. `RALPH_TIMEOUT_*` becomes a guarantee rather than
an intention.

**The heartbeat.** A timeout only helps if the harness is waiting on something.
SH-3 died between phases; run 7 sat alive at 0.5s CPU blocked on a child. Both
are indistinguishable from healthy work if you only check whether the process
exists — which is exactly the mistake that cost 19 hours.

**Change:** a background thread writes `{pid, timestamp, sprint, phase}` to
`ralph/heartbeat.json` every 30s. Alive plus stale heartbeat means wedged. This
is what the supervisor watches; `threading` is already imported.

## 3. Supervision

A `ralph/supervisor.py` that:

- launches the harness and waits
- relaunches while eligible work remains
- kills and restarts when the heartbeat is more than 10 minutes stale
  (comfortably longer than any legitimate gap between 30s writes, short
  enough that a wedge costs minutes rather than the 19 hours SH-3 cost)
- backs off exponentially on rapid repeated failure (30s, 2m, 8m)
- **hard-stops after 3 consecutive failures** rather than spinning for a week

Reboot survival is a Windows Scheduled Task triggered **At startup**, running
the supervisor. Not ralph directly — the supervisor is what carries the restart
policy, and a bare relaunch of a crash-looping harness is worse than stopping.

The supervisor never edits the roadmap or the repo. It starts processes and
watches a heartbeat. Keeping it that dumb is what makes it trustworthy.

## 4. Triage

**Starvation is not completion.** When `todo > 0` and `eligible == 0`, that is a
distinct outcome from "everything is done", and must be reported as such: name
the blocking sprints and the transitive set they strand.

```
STARVED: 15 todo, 0 eligible.
  SA-F2 (blocked) strands SA-F3, SA-F4, SA-F5, SA-F6, SA-F7
```

That line, in April, would have saved four months.

**Cascade report on block.** When a sprint is marked blocked, compute and log
what just became unreachable, so the cost is visible when incurred rather than
discovered later.

**One retry grace.** A sprint gets one retry before being marked blocked.
`SA-F2` is the case in point: returncode 1, 135 bytes of output, a transient
bail that became a four-month block. A single retry absorbs that class entirely.
The retry count lives in `state.json`, so it survives a restart.

**`Blocks:` becomes a consistency check.** Every sprint declares a `**Blocks**:`
field and **nothing has ever parsed it.** It reads as structural but is a
comment, free to drift out of agreement with the real `depends_on` edges. Wire
it as a cross-check that fails loudly on disagreement — not as a second source
of truth, which would just create two things to keep in sync.

## 5. Observability

`STATUS.md`, committed and pushed periodically: current sprint and phase,
elapsed time, queue depth, recent outcomes, and prominent banners for
`STARVED` or `CRASH-LOOP`.

Ralph already pushes to origin, so this is readable on GitHub from a phone with
no new infrastructure, no app, and no service to keep running. The bar is "can
the operator tell from a beach whether it is working", and a committed markdown
file clears it.

## 6. Queue depth

Reset `SA-F2` from `blocked` to `todo`. Its failure was transient and predates
`INFRA_ERROR`. That alone makes five Phase V sprints eligible.

**That is necessary but not sufficient, and the reason matters.** `SA-F2` is
**XL, estimated 1-2 weeks, against a 90-minute implement phase.** Unblocking it
only changes how it fails. It must be split into phase-sized pieces first.

This generalises: **sprint size and phase timeout are in tension, and nothing
currently enforces the relationship.** A sprint whose implement phase cannot
finish inside `RALPH_TIMEOUT_IMPLEMENT` is structurally guaranteed to time out
or to be completed badly. Auditing the 15 `todo` sprints for XL sizing is part
of filling the week.

---

## Pre-deployment smoke test

None of this ships to a seven-day run on the strength of the code reading
correctly. Every failure mode in this spec is cheap to inject deliberately, so
each one gets injected and observed before the operator leaves.

The drill, run end to end against a live harness on a throwaway sprint:

| # | Injected fault | Expected observable |
|---|---|---|
| 1 | `taskkill` the harness mid-implement | supervisor relaunches within backoff; sprint reclaimed or resumed with no hand repair |
| 2 | Hard-kill the machine mid-write (or `taskkill /F` during a roadmap write) | `ROADMAP.md` and `state.json` still parse; no truncation |
| 3 | Reboot | Scheduled Task starts the supervisor unprompted |
| 4 | An agent subprocess that sleeps past its phase timeout | killed at the timeout by the kill-tree, phase marked `timeout` |
| 5 | Freeze the heartbeat while leaving the process alive | supervisor detects staleness inside 10 minutes and restarts |
| 6 | Empty the eligible queue | `STARVED` reported with blockers and stranded sprints named -- NOT "exiting cleanly" |
| 7 | A sprint that fails once | retried once, then blocked -- not blocked on first failure |
| 8 | A harness that dies instantly, repeatedly | stops after 3 consecutive failures rather than spinning |
| 9 | Any of the above | `STATUS.md` reflects it, committed and visible on GitHub |

Drill 4 is the one most worth doing properly. The 8.5-hour hang happened because
a timeout that *looked* correct did not fire, and no amount of reading
`subprocess.run(timeout=...)` reveals that -- only hanging something does.

Drills 2 and 3 need a real power interruption to be fully honest. A `taskkill /F`
mid-write approximates the write case well; the boot case genuinely requires a
restart, so do one.

**A drill that cannot be run is a criterion that will not hold.** If any fault
above proves impractical to inject, say so and treat that component as unproven
rather than quietly assuming it works.

## Success criteria

1. Killing the harness process mid-phase results in the supervisor relaunching
   it, and the interrupted sprint resuming or being cleanly reclaimed, with no
   hand reconstruction.
2. A hard reboot mid-sprint leaves `ROADMAP.md` and `state.json` parseable, and
   the Scheduled Task restarts the supervisor on boot.
3. An agent subprocess that hangs is killed at its phase timeout, verified by
   deliberately hanging one — not by reasoning about the code.
4. A wedged harness (alive, no progress) is detected within 10 minutes via a
   stale heartbeat and restarted.
5. Starvation is reported distinctly from completion, naming blockers and
   stranded sprints. Verified against the current real state: 15 todo, 0
   eligible, SA-F2 stranding five.
6. A sprint that fails once is retried once before being blocked.
7. `Blocks:` disagreeing with `depends_on` fails loudly.
8. `STATUS.md` is committed and pushed, and readable on GitHub.
9. A crash-looping harness stops after 3 consecutive failures instead of
   restarting for seven days.
10. Full suite green throughout; no regression from 10,586 passing.

## Risks

- **The supervisor is new code with no supervisor of its own.** Keep it small
  and dumb: start a process, watch a file, apply a restart policy. Every feature
  added to it is a feature that can fail unwatched.
- **Restart storms.** A harness that dies instantly and is relaunched instantly
  burns a week of API budget in hours. The backoff and the hard stop are not
  optional niceties; they are the difference between a quiet week and an
  expensive one.
- **Heartbeat false positives.** A legitimately long operation (a 90-minute
  implement phase) must not look wedged. The heartbeat is written on a timer by
  a separate thread, not on phase transitions, precisely so long phases stay
  visibly alive.
- **A retry that repeats a destructive action.** The retry grace re-runs a phase
  that may have already committed work. Retry must be safe against partial
  completion — check for commits referencing the sprint before re-running, the
  same signal the harness already uses for sentinel cross-validation.

## Open question

What fills the seven days. Resetting `SA-F2` and splitting it unlocks the Phase
V arc, but whether that is the right use of a week — versus Spec C's legibility
work, which addresses the findings a real playtester actually reported — is a
decision for the operator, not a consequence of this spec.
