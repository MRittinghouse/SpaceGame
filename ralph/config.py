"""Ralph harness configuration.

Tunables for the multi-agent execution loop. Override at runtime via env
vars (see RALPH_* below) or edit this file for one-time changes.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
RALPH_DIR: Path = PROJECT_ROOT / "ralph"
ROADMAP_PATH: Path = PROJECT_ROOT / "requirements" / "roadmap" / "ROADMAP.md"
CONVENTIONS_PATH: Path = PROJECT_ROOT / "requirements" / "roadmap" / "CONVENTIONS.md"
AGENT_GUIDE_PATH: Path = PROJECT_ROOT / "requirements" / "roadmap" / "AGENT_GUIDE.md"

PROMPTS_DIR: Path = RALPH_DIR / "prompts"
LOGS_DIR: Path = RALPH_DIR / "logs"
STATE_FILE: Path = RALPH_DIR / "state.json"
LOCK_FILE: Path = RALPH_DIR / ".running"
STOP_FILE: Path = PROJECT_ROOT / "STOP"

# ---------------------------------------------------------------------------
# Loop control
# ---------------------------------------------------------------------------

# Maximum number of times Implement → Review can cycle for one sprint
# before the sprint is marked blocked for human attention. Prevents a
# confused reviewer from looping forever.
MAX_REWORK_CYCLES: int = 3

# Maximum number of sprints the harness will process in one invocation
# before exiting. Override per-run with `--max-sprints N`.
DEFAULT_MAX_SPRINTS_PER_RUN: int = 10

# xdist worker count for the harness's own test runs.
#
# NOT "auto". SUITE-1 measured `-n auto` (32 workers here) hanging roughly 1 run
# in 3: workers die during concurrent SDL init and the controller is left
# spinning. SUITE-1 made that failure loud and bounded (pytest-timeout, a
# taskkill /T kill-tree, and a 30-minute CI job cap) but did NOT eliminate it --
# forcing SDL_VIDEODRIVER=dummy narrowed the race without closing it.
#
# SUITE-2 (2026-08-27) identified the root cause and confirmed it is not
# fixable in-project without significant test-infrastructure changes:
#
#   Pre-fix: SUITE1_REPRO runs=10 hangs=6 failures=2 passes=2 median_seconds=300.5
#   (see SUITE-2 phase report in requirements/roadmap/ROADMAP.md for full run log)
#
#   Root cause: tests/test_engine/ and tests/test_crawler/ contain many test
#   files that call pygame.init() or display.set_mode() at module or test level.
#   With 32 workers, 32 simultaneous pygame.init() calls contend on Windows
#   native resources (GDI handles, Window Station objects) even with
#   SDL_VIDEODRIVER=dummy and SDL_AUDIODRIVER=dummy. The dummy video driver
#   bypasses the SDL display chain but does not fully bypass the Windows
#   subsystem initialisation path. Worker processes die ("node down: Not
#   properly terminated") rather than raising Python-level exceptions.
#
#   Diagnostic: excluding test_engine and test_crawler with
#   `-k "not test_engine and not test_crawler"` produced
#   SUITE1_REPRO runs=3 hangs=0 failures=0 passes=3 median_seconds=129.4 —
#   confirming that the remaining ~9100 tests are stable at -n auto and the
#   deaths are isolated to the SDL-init tests in those two directories.
#
#   No in-project fix was attempted: serialising pygame.init() across 32 worker
#   processes would require session-scoped per-worker init fixtures, a cross-
#   process lock file, or migrating the affected tests to --forked isolation.
#   All options are outside SUITE-2's scope and would require significant
#   restructuring of tests/test_engine/ and tests/test_crawler/.
#
# A bounded failure at -n auto is still a failed launch, and the baseline-
# capture path runs BEFORE any sprint is picked up, so it blocks the whole
# harness. -n 4 and -n 8 never reproduced the flake across many runs. Trading
# ~100s for ~180s of wall clock to make unattended operation reliable is the
# right side of that trade.
#
# This is a mitigation layered ON TOP of the loud-failure work, never a
# replacement for it: a future variant still fails visibly rather than stalling.
# Removing the cap requires re-running scripts/repro_xdist_flake.py and showing
# the hang rate is zero (which requires resolving the concurrent pygame.init
# contention first).
TEST_WORKERS: str = os.environ.get("RALPH_TEST_WORKERS", "8")

# Per-phase subprocess timeouts. If a phase exceeds these, the agent
# subprocess is killed and the sprint is marked blocked with reason
# "timeout in <phase>".
#
# Plan and review are mostly synthesis + verification (under an hour
# even for L sprints). Implement is the heavy lifter — bumping it to
# 90 min keeps L/XL sprints from getting cut off mid-edit. Override via
# RALPH_TIMEOUT_PLAN / RALPH_TIMEOUT_IMPLEMENT / RALPH_TIMEOUT_REVIEW.
PHASE_TIMEOUT_PLAN: int = int(os.environ.get("RALPH_TIMEOUT_PLAN", 60 * 60))
PHASE_TIMEOUT_IMPLEMENT: int = int(os.environ.get("RALPH_TIMEOUT_IMPLEMENT", 90 * 60))
PHASE_TIMEOUT_REVIEW: int = int(os.environ.get("RALPH_TIMEOUT_REVIEW", 60 * 60))

# Backward-compatible alias used by snapshot/restore error paths and
# probe defaults — set to the largest of the three so anything keyed off
# this value won't under-allocate.
PHASE_TIMEOUT_SECONDS: int = max(PHASE_TIMEOUT_PLAN, PHASE_TIMEOUT_IMPLEMENT, PHASE_TIMEOUT_REVIEW)

# Sleep between sprint pickups to give the filesystem a moment to settle
# (commits flushed, agent processes torn down). Seconds.
INTER_SPRINT_SLEEP: float = 1.0

# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

# Claude CLI invocation. The harness appends the prompt as the final
# argument. Override if your install uses a different binary or flag.
#
# `--dangerously-skip-permissions`: required for the harness's unattended
# pattern. In `claude -p` non-interactive mode, tool calls (Edit, Write,
# Bash) are otherwise sandbox-restricted, even for paths inside the
# project root. Without this flag, agents read context successfully but
# silently fail on writes — producing "no sentinel" outcomes that look
# like agent disobedience but are actually permission denials. The flag
# is documented as "dangerous" because the agent can do anything; that's
# exactly the contract we want for autonomous sprint execution against
# our own roadmap.
CLAUDE_CMD: list[str] = ["claude", "-p", "--dangerously-skip-permissions"]

# Per-phase model selection. Mapping rationale:
#   - Plan: Opus 4.7 (1M context). Planning is highest-leverage — a bad
#     plan wastes the entire sprint. Worth the spend.
#   - Implement (S/M sprints): Sonnet 4.6. Workhorse for routine
#     implementation. Most sprints fall here.
#   - Implement (L/XL sprints): Opus 4.7. Multi-system content-arc
#     sprints (SA-1 Wreckers Hall, SA-2 Deep Shafts, etc.) need the
#     larger context window and stronger synthesis.
#   - Review: Sonnet 4.6. Verification is easier than synthesis. If
#     review misses something subtle, the rework cycle catches it.
#
# Override per-phase via env vars (e.g., for a cost-saving run on a
# small sprint backlog: RALPH_MODEL_PLAN=claude-sonnet-4-6).
MODEL_PLAN: str = os.environ.get("RALPH_MODEL_PLAN", "claude-opus-4-7")
MODEL_IMPLEMENT_DEFAULT: str = os.environ.get("RALPH_MODEL_IMPLEMENT_DEFAULT", "claude-sonnet-4-6")
MODEL_IMPLEMENT_HEAVY: str = os.environ.get("RALPH_MODEL_IMPLEMENT_HEAVY", "claude-opus-4-7")
MODEL_REVIEW: str = os.environ.get("RALPH_MODEL_REVIEW", "claude-sonnet-4-6")

# Sprint sizes that bump the implement phase to the heavy model.
HEAVY_SIZES: frozenset[str] = frozenset({"L", "XL"})


def model_for_phase(phase: str, sprint_size: str = "") -> str:
    """Return the claude `--model` value to use for the given phase.

    For implement, sprint_size determines whether to use the heavy
    model. Sizes follow CONVENTIONS.md: S, M, L, XL.
    """
    phase_l = phase.lower()
    if phase_l == "plan":
        return MODEL_PLAN
    if phase_l == "review":
        return MODEL_REVIEW
    if phase_l == "implement":
        if (sprint_size or "").upper() in HEAVY_SIZES:
            return MODEL_IMPLEMENT_HEAVY
        return MODEL_IMPLEMENT_DEFAULT
    return MODEL_IMPLEMENT_DEFAULT


def timeout_for_phase(phase: str) -> int:
    """Return the subprocess timeout (seconds) for the given phase."""
    return {
        "plan": PHASE_TIMEOUT_PLAN,
        "implement": PHASE_TIMEOUT_IMPLEMENT,
        "review": PHASE_TIMEOUT_REVIEW,
    }.get(phase.lower(), PHASE_TIMEOUT_SECONDS)


def build_claude_cmd(phase: str, sprint_size: str = "") -> list[str]:
    """Build the full claude CLI argv for a given phase + sprint size.

    Returns CLAUDE_CMD with `--model <id>` appended. The harness adds
    the prompt as the final positional argument.
    """
    return [*CLAUDE_CMD, "--model", model_for_phase(phase, sprint_size)]


# Dry-run mode: log what would happen, don't actually invoke Claude.
# Useful for testing the loop logic. Override via `RALPH_DRY_RUN=1`.
DRY_RUN: bool = os.environ.get("RALPH_DRY_RUN", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Status markers used in ROADMAP.md
# ---------------------------------------------------------------------------

# These are the exact strings the harness writes to the Status field at
# phase transitions. Agents update Activity log; harness updates Status.
STATUS_TODO: str = "todo"
STATUS_PLANNING: str = "in-progress (planning)"
STATUS_IMPLEMENTING: str = "in-progress (implementing)"
STATUS_REVIEWING: str = "in-progress (reviewing)"
STATUS_REVIEW: str = "review"
STATUS_DONE: str = "done"
STATUS_BLOCKED: str = "blocked"

# Sentinel strings the agents are instructed to write into the Activity
# log at the end of their phase. The harness greps for these to
# determine the phase's outcome.
AGENT_OUTCOME_OK: str = "PHASE_OK"
AGENT_OUTCOME_BLOCKED: str = "PHASE_BLOCKED"
AGENT_OUTCOME_NEEDS_REWORK: str = "PHASE_NEEDS_REWORK"

# ---------------------------------------------------------------------------
# Auto-push (item A)
# ---------------------------------------------------------------------------

# When a sprint reaches a terminal outcome (done / blocked / needs-rework),
# automatically `git push origin HEAD`. Disable with `--no-push` to keep
# work local. Push failures are logged but don't crash the harness.
PUSH_ON_SPRINT_COMPLETE: bool = True

# Push subprocess timeout (a slow network shouldn't hang the harness).
PUSH_TIMEOUT_SECONDS: int = 60

# ---------------------------------------------------------------------------
# Validation + recovery (items B, C, D)
# ---------------------------------------------------------------------------

# Validate ROADMAP.md after each agent phase. If parsing fails or the
# agent corrupted unrelated sprint sections, restore the pre-phase
# snapshot and mark the sprint blocked. Disable as an escape hatch in
# case validation has false positives — but we should fix the false
# positive rather than disable, normally.
VALIDATE_ROADMAP_AFTER_AGENT: bool = True

# ---------------------------------------------------------------------------
# Infrastructure failures (H4)
# ---------------------------------------------------------------------------

# Exit code meaning "this run accomplished nothing because the infrastructure
# the agents depend on was down" -- an expired auth token, an API outage, a
# sustained rate limit.
#
# It exists because INFRA_ERROR used to leave `main()` returning 0. The
# supervisor's `record_success()` then reset its consecutive-failure counter,
# so the 3-strike crash-loop cap and the exponential backoff -- the two
# mechanisms that separate a quiet week from an expensive one -- never engaged
# for the one failure class that can persist for hours. A harness that
# processed ten sprints, every one of them infra_error, and produced nothing,
# still reported success, and the supervisor relaunched it 30 seconds later,
# for as long as the outage lasted.
HARNESS_RC_INFRA_ERROR: int = 5

# Consecutive INFRA_ERROR sprint outcomes before the harness stops the run and
# exits with HARNESS_RC_INFRA_ERROR. Two is enough to tell "the API is down"
# from "one phase hit a blip": the first one already consumed its retry.
MAX_CONSECUTIVE_INFRA_SPRINTS: int = 2

# Consecutive INFRA_ERROR outcomes on ONE sprint before it is blocked instead
# of reset to `todo`. `_mark_terminal_outcome` resets INFRA_ERROR to todo so
# the next run can pick it up cleanly, which makes it infinitely re-runnable
# -- `retry_count` gates every other outcome class but not this one. A sprint
# whose prompt reliably kills the CLI would otherwise be re-picked forever
# while the rest of the queue waited behind it.
MAX_INFRA_ERRORS_PER_SPRINT: int = 3

# ---------------------------------------------------------------------------
# Liveness thresholds (M1) -- three questions, three numbers
# ---------------------------------------------------------------------------

# "This heartbeat is too old for the process that wrote it to still be
# working": the supervisor's kill threshold, and the same number STATUS.md
# uses to decide whether to flag a beat as STALE.
#
# These used to disagree. The supervisor killed at 600s while STATUS.md
# reused IN_PROGRESS_STALE_MINUTES (3600s), so for fifty minutes a run the
# supervisor already considered dead rendered on the operator's phone with no
# STALE banner at all -- and `status.py`'s own docstring cites "a reboot
# mid-sprint leaves it behind" as its motivating case, which is exactly when
# the leftover beat's age is small.
HEARTBEAT_STALE_SECONDS: float = 600.0

# A different question from HEARTBEAT_STALE_SECONDS, deliberately left at a
# different (much larger) number: "this ROADMAP entry has said in-progress for
# so long that no live run can plausibly still own it". It is compared against
# Activity-log and state-file timestamps, not against the heartbeat, and it
# gates a destructive action (resetting someone else's sprint to todo), so it
# is the one threshold that should stay conservative.
IN_PROGRESS_STALE_MINUTES: int = 60

# ---------------------------------------------------------------------------
# Pre-flight checks (item F)
# ---------------------------------------------------------------------------

# Refuse to start if the working tree has uncommitted changes. Agents
# commit during phases; mixing in unrelated dirty changes pollutes the
# sprint history. Override with `--allow-dirty` if you know what you're
# doing (e.g., debugging in a fresh worktree).
REQUIRE_CLEAN_WORKING_TREE: bool = True
