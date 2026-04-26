"""Agent invocation for the ralph harness.

Three agents per sprint: planner, implementer, reviewer. Each is a
separate Claude CLI subprocess invocation with a role-specific prompt.

The agent's outcome (PHASE_OK / PHASE_BLOCKED / PHASE_NEEDS_REWORK) is
read from the sprint's Activity log after the subprocess returns. The
harness greps the most recently appended log entries for the sentinel.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from ralph.config import (
    AGENT_GUIDE_PATH,
    AGENT_OUTCOME_BLOCKED,
    AGENT_OUTCOME_NEEDS_REWORK,
    AGENT_OUTCOME_OK,
    CLAUDE_CMD,
    CONVENTIONS_PATH,
    DRY_RUN,
    LOGS_DIR,
    PHASE_TIMEOUT_SECONDS,
    PROJECT_ROOT,
    PROMPTS_DIR,
    ROADMAP_PATH,
    VALIDATE_ROADMAP_AFTER_AGENT,
)
from ralph import roadmap_state
from ralph.roadmap_state import RoadmapValidationError


class Phase(Enum):
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"


# Phases where it's legitimate for the agent to add new sprint sections
# to the roadmap. Plan and Review can author new sprints (planner
# proposes scope additions; reviewer files follow-ups). Implement should
# only modify the claimed sprint.
_PHASE_ALLOWS_NEW_SPRINTS: frozenset[Phase] = frozenset({Phase.PLAN, Phase.REVIEW})


class Outcome(Enum):
    OK = "ok"
    BLOCKED = "blocked"
    NEEDS_REWORK = "needs_rework"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class PhaseResult:
    outcome: Outcome
    phase: Phase
    sprint_id: str
    log_path: Path
    reason: str = ""


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def _load_prompt_template(phase: Phase) -> str:
    template_path = PROMPTS_DIR / f"{phase.value}.md"
    return template_path.read_text(encoding="utf-8")


def _build_prompt(phase: Phase, sprint_id: str) -> str:
    """Build the full prompt for a phase by substituting sprint context
    into the template.
    """
    template = _load_prompt_template(phase)
    return template.replace("{SPRINT_ID}", sprint_id).replace(
        "{ROADMAP_PATH}", str(ROADMAP_PATH.relative_to(PROJECT_ROOT))
    ).replace(
        "{CONVENTIONS_PATH}", str(CONVENTIONS_PATH.relative_to(PROJECT_ROOT))
    ).replace(
        "{AGENT_GUIDE_PATH}", str(AGENT_GUIDE_PATH.relative_to(PROJECT_ROOT))
    )


# ---------------------------------------------------------------------------
# Subprocess invocation
# ---------------------------------------------------------------------------


def _log_path_for(sprint_id: str, phase: Phase) -> Path:
    sprint_dir = LOGS_DIR / sprint_id
    sprint_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return sprint_dir / f"{phase.value}-{timestamp}.log"


def _invoke_claude(prompt: str, log_path: Path) -> tuple[int, str, str]:
    """Run the claude CLI with the prompt, capturing stdout+stderr to
    the log file. Returns (returncode, stdout, stderr).

    Raises subprocess.TimeoutExpired on phase timeout.
    """
    cmd = list(CLAUDE_CMD) + [prompt]

    if DRY_RUN:
        with log_path.open("w", encoding="utf-8") as f:
            f.write(f"[DRY-RUN] Would have invoked: {cmd[0]} ...\n")
            f.write(f"\n--- PROMPT ---\n{prompt}\n--- END PROMPT ---\n")
        return 0, "[dry-run no-op]", ""

    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"# Phase invocation\n")
        f.write(f"# Started: {datetime.now().isoformat()}\n")
        f.write(f"# Command: {cmd[0]} {' '.join(cmd[1:-1])} <prompt>\n")
        f.write(f"# Prompt length: {len(prompt)} chars\n")
        f.write(f"# Timeout: {PHASE_TIMEOUT_SECONDS}s\n\n")
        f.write(f"--- PROMPT ---\n{prompt}\n--- END PROMPT ---\n\n")
        f.write(f"--- AGENT OUTPUT ---\n")
        f.flush()

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=PHASE_TIMEOUT_SECONDS,
                encoding="utf-8",
                errors="replace",
            )
            f.write(result.stdout)
            if result.stderr:
                f.write(f"\n--- STDERR ---\n{result.stderr}\n")
            f.write(f"\n--- END (returncode {result.returncode}) ---\n")
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            f.write(f"\n--- TIMEOUT after {PHASE_TIMEOUT_SECONDS}s ---\n")
            raise


# ---------------------------------------------------------------------------
# Outcome detection
# ---------------------------------------------------------------------------


def _read_recent_activity_log(sprint_id: str) -> str:
    """Return the trailing portion of the sprint's Activity log so the
    harness can detect the sentinel the agent wrote.
    """
    sprint = roadmap_state.get_sprint(sprint_id)
    content = ROADMAP_PATH.read_text(encoding="utf-8")
    section = content[sprint.section_start : sprint.section_end]
    log_match = re.search(r"\*\*Activity log\.\*\*\s*\n((?:- .*\n)*)", section)
    if log_match is None:
        return ""
    return log_match.group(1)


def _detect_outcome(sprint_id: str, returncode: int) -> tuple[Outcome, str]:
    """Determine the phase outcome from the agent's Activity-log update.

    Sentinels (the agent is told to write one of these in its final log
    entry):
      - PHASE_OK
      - PHASE_BLOCKED: <reason>
      - PHASE_NEEDS_REWORK: <reason>

    If the agent crashed (returncode != 0) and didn't write a sentinel,
    treat as ERROR. If the subprocess succeeded but no sentinel appears,
    treat as ERROR (agent didn't follow protocol).
    """
    log = _read_recent_activity_log(sprint_id)
    # Look at the most recent sentinel — the LAST occurrence in the log
    # block. Agents are instructed to put one final sentinel line.
    matches: list[tuple[Outcome, str]] = []
    for line in log.strip().splitlines():
        if AGENT_OUTCOME_OK in line:
            matches.append((Outcome.OK, ""))
        elif AGENT_OUTCOME_BLOCKED in line:
            reason = line.split(AGENT_OUTCOME_BLOCKED, 1)[-1].lstrip(": -").strip()
            matches.append((Outcome.BLOCKED, reason or "agent reported blocked"))
        elif AGENT_OUTCOME_NEEDS_REWORK in line:
            reason = line.split(AGENT_OUTCOME_NEEDS_REWORK, 1)[-1].lstrip(": -").strip()
            matches.append(
                (Outcome.NEEDS_REWORK, reason or "agent reported rework needed")
            )

    if matches:
        # Agent's last sentinel wins.
        return matches[-1]

    if returncode != 0:
        return Outcome.ERROR, f"agent exited with returncode {returncode}, no sentinel"
    return Outcome.ERROR, "agent completed but wrote no sentinel"


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_phase(phase: Phase, sprint_id: str) -> PhaseResult:
    """Invoke the agent for the given phase against the given sprint.

    Wraps subprocess invocation with:
      - Pre-phase ROADMAP.md snapshot (item B + C).
      - Post-phase validation: roadmap parses cleanly, claimed sprint
        still exists, no out-of-claim modifications, no deletions, new
        sprints only in phases that allow it.
      - On validation failure: restore the snapshot, return ERROR with
        the validation reason.

    Returns a PhaseResult with the detected outcome. The harness uses
    this to decide whether to advance, retry, or block the sprint.
    """
    log_path = _log_path_for(sprint_id, phase)
    prompt = _build_prompt(phase, sprint_id)

    # Snapshot ROADMAP.md before the agent runs (item B + C).
    pre_snapshot = roadmap_state.snapshot_roadmap()

    try:
        returncode, _stdout, _stderr = _invoke_claude(prompt, log_path)
    except subprocess.TimeoutExpired:
        # Best-effort snapshot restore — the agent may have done partial
        # writes before the timeout.
        if VALIDATE_ROADMAP_AFTER_AGENT:
            try:
                roadmap_state.restore_roadmap(pre_snapshot)
            except OSError:
                pass
        return PhaseResult(
            outcome=Outcome.TIMEOUT,
            phase=phase,
            sprint_id=sprint_id,
            log_path=log_path,
            reason=f"phase timed out after {PHASE_TIMEOUT_SECONDS}s",
        )
    except FileNotFoundError as e:
        return PhaseResult(
            outcome=Outcome.ERROR,
            phase=phase,
            sprint_id=sprint_id,
            log_path=log_path,
            reason=f"claude CLI not found: {e}. Check ralph/config.py CLAUDE_CMD.",
        )

    # Validate the roadmap state after the agent's writes (item B + C).
    if VALIDATE_ROADMAP_AFTER_AGENT and not DRY_RUN:
        try:
            roadmap_state.validate_post_agent(
                snapshot=pre_snapshot,
                claimed_sprint_id=sprint_id,
                phase_allows_new_sprints=phase in _PHASE_ALLOWS_NEW_SPRINTS,
            )
        except RoadmapValidationError as e:
            # Restore the pre-phase snapshot to undo whatever the agent
            # did. The sprint is reported as ERROR with the validation
            # reason; the harness will mark the sprint blocked.
            try:
                roadmap_state.restore_roadmap(pre_snapshot)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        f"\n--- ROADMAP VALIDATION FAILURE — RESTORED SNAPSHOT ---\n{e}\n"
                    )
            except OSError as restore_err:
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        f"\n--- ROADMAP VALIDATION FAILURE + RESTORE FAILED ---\n"
                        f"validation: {e}\nrestore: {restore_err}\n"
                    )
            return PhaseResult(
                outcome=Outcome.ERROR,
                phase=phase,
                sprint_id=sprint_id,
                log_path=log_path,
                reason=f"roadmap validation failed: {e}",
            )

    outcome, reason = _detect_outcome(sprint_id, returncode)
    return PhaseResult(
        outcome=outcome,
        phase=phase,
        sprint_id=sprint_id,
        log_path=log_path,
        reason=reason,
    )
