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
PHASE_TIMEOUT_SECONDS: int = max(
    PHASE_TIMEOUT_PLAN, PHASE_TIMEOUT_IMPLEMENT, PHASE_TIMEOUT_REVIEW
)

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
MODEL_IMPLEMENT_DEFAULT: str = os.environ.get(
    "RALPH_MODEL_IMPLEMENT_DEFAULT", "claude-sonnet-4-6"
)
MODEL_IMPLEMENT_HEAVY: str = os.environ.get(
    "RALPH_MODEL_IMPLEMENT_HEAVY", "claude-opus-4-7"
)
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
    return list(CLAUDE_CMD) + ["--model", model_for_phase(phase, sprint_size)]


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

# An "in-progress" sprint older than this many minutes (no recent
# Activity log entry, no recent state-file touch) is considered
# abandoned by a previously-killed run. The startup recovery resets it
# to `todo` so the next run can re-pick it up cleanly.
IN_PROGRESS_STALE_MINUTES: int = 60

# ---------------------------------------------------------------------------
# Pre-flight checks (item F)
# ---------------------------------------------------------------------------

# Refuse to start if the working tree has uncommitted changes. Agents
# commit during phases; mixing in unrelated dirty changes pollutes the
# sprint history. Override with `--allow-dirty` if you know what you're
# doing (e.g., debugging in a fresh worktree).
REQUIRE_CLEAN_WORKING_TREE: bool = True
