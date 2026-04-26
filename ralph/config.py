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

# Per-phase subprocess timeout. If a phase exceeds this, the agent
# subprocess is killed and the sprint is marked blocked with reason
# "timeout in <phase>". Override via `RALPH_PHASE_TIMEOUT_SECONDS` env.
PHASE_TIMEOUT_SECONDS: int = int(os.environ.get("RALPH_PHASE_TIMEOUT_SECONDS", 60 * 60))

# Sleep between sprint pickups to give the filesystem a moment to settle
# (commits flushed, agent processes torn down). Seconds.
INTER_SPRINT_SLEEP: float = 1.0

# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

# Claude CLI invocation. The harness appends the prompt as the final
# argument. Override if your install uses a different binary or flag.
CLAUDE_CMD: list[str] = ["claude", "-p"]

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
