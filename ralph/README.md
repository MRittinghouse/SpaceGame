# Ralph Loop Harness

Multi-agent execution harness for `requirements/roadmap/ROADMAP.md`. Runs sprints sequentially through a three-agent cycle (Plan → Implement → Review), with bounded rework cycles and clean-exit safeguards.

---

## Quick start

```bash
# From project root
python -m ralph.harness                    # run with defaults
python -m ralph.harness --max-sprints 1    # process exactly one sprint
python -m ralph.harness --dry-run          # log what would happen, don't invoke Claude
python -m ralph.harness --sprint SA-PREP-1 # force a specific sprint pickup
```

To stop cleanly:
- Create a file named `STOP` in the project root. The harness exits after the current phase completes.
- Or send SIGINT (Ctrl-C). The harness catches it, finishes the current phase, then exits.

---

## What it does

For each eligible sprint in `ROADMAP.md`:

1. **Plan phase** (once per sprint): a Claude agent reads the sprint, the strategic vision docs, and any context links. It assesses scope, identifies polish items, decides whether to expand this sprint or propose new ones, locks open decisions, and fills in the sprint's Plan section.

2. **Implement phase**: another Claude agent reads the planner's output and implements the sprint TDD-style. Writes failing tests, implements to green, runs lint + format + full suite, commits with sprint ID in the message.

3. **Review phase**: a third Claude agent reviews the implementer's work. Verifies acceptance criteria, runs tests, checks for flow regressions, validates narrative voice. Can fix small issues directly, OR demand a rework cycle (returns to Implement), OR add follow-up items to the sprint plan, OR mark the sprint blocked if structural rework is needed.

4. **Implement ↔ Review** cycles up to `MAX_REWORK_CYCLES` times (default 3). If the reviewer keeps demanding rework past the cap, the sprint is marked blocked for human attention.

When the loop runs out of eligible sprints OR hits `MAX_SPRINTS_PER_RUN` (default 10), the harness exits cleanly.

---

## Files

```
ralph/
  README.md                  # this file
  harness.py                 # main loop entry: python -m ralph.harness
  config.py                  # tunable constants (timeouts, caps, paths)
  roadmap_state.py           # parse + update ROADMAP.md
  agents.py                  # agent invocation logic (subprocess, prompts)
  prompts/
    planner.md               # planner agent system prompt template
    implementer.md           # implementer system prompt template
    reviewer.md              # reviewer system prompt template
  logs/                      # per-sprint, per-phase logs (gitignored)
  state.json                 # persistent state (iteration counters, phase) — gitignored
```

Top-level `STOP` file — presence signals the harness to exit cleanly. Gitignored.

---

## Eligibility

A sprint is eligible for pickup when:
1. Its `Status` is `todo`.
2. All listed dependencies have `Status: done`.
3. (Future) No touch-zone conflicts with currently `in-progress` sprints. The current single-sprint-at-a-time harness doesn't need this; a parallel harness would.

The harness scans the index table at the top of `ROADMAP.md` and selects the first eligible sprint in document order. Override with `--sprint <ID>` to force a specific pickup (the harness still verifies dependencies).

---

## Safeguards

| Safeguard | Default | Override |
|---|---|---|
| Per-phase timeout | 60 min | `RALPH_PHASE_TIMEOUT_SECONDS` env var or `config.py` |
| Rework cycles per sprint | 3 | `MAX_REWORK_CYCLES` in `config.py` |
| Sprints per harness run | 10 | `--max-sprints N` |
| Total runtime | unbounded | (use `--max-sprints` or external scheduler) |
| Clean exit | `STOP` file or SIGINT | — |

If a phase exceeds its timeout, the subprocess is killed and the sprint is marked `blocked` with reason `timeout in <phase>`.

If `MAX_REWORK_CYCLES` is exhausted, the sprint is marked `blocked` with reason `exceeded rework cycles`. Human attention required.

If the harness encounters a parsing error on `ROADMAP.md` (malformed sprint section, missing required field), it aborts with a clear error message. The roadmap is the source of truth; the harness refuses to guess.

---

## State

`ralph/state.json` tracks:
- Per-sprint iteration counts (plan, implement, review, rework cycles)
- Current phase per sprint
- Started/last-touched timestamps
- Global counters (total sprints processed)

This file is read on harness startup so a Ctrl-C and restart resumes correctly. Delete to reset.

---

## Logs

`ralph/logs/<SPRINT-ID>/<phase>-<timestamp>.log` captures the prompt + agent output for each phase invocation. Useful for postmortem on blocked sprints or to understand why a reviewer demanded rework.

---

## Configuration

Edit `ralph/config.py` for one-time changes (timeouts, paths). Use environment variables for run-specific overrides (`RALPH_PHASE_TIMEOUT_SECONDS`, `RALPH_DRY_RUN`).

The Claude CLI invocation is configurable in `config.py` via `CLAUDE_CMD`. Default is `claude -p`. Override if your install uses a different binary or non-interactive flag.

---

## Limitations

- Sequential only. The CONVENTIONS.md format supports parallel work via touch-zone conflict detection, but this harness processes one sprint at a time. A parallel dispatcher is future work.
- Single-host. No distributed coordination.
- The harness does not push to remote. All commits are local. A human reviews and pushes after the queue drains or at convenient checkpoints.
- The harness does not modify other sprints' sections. Agents are told not to either, but the harness doesn't enforce this — it trusts agent obedience and detects violations by comparing pre/post diffs. (Future: hard enforcement.)

---

## Stopping

Three ways:
1. **`STOP` file**: `touch STOP` in the project root. Harness exits cleanly after the current phase. Recommended.
2. **SIGINT**: Ctrl-C. Caught by the harness; current phase completes, then exit.
3. **Hard kill**: SIGKILL. State may be inconsistent. Manually inspect `ROADMAP.md` and `ralph/state.json` before resuming.
