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


@dataclass
class PhaseContext:
    """Optional pre-phase context the harness passes through to agents.

    test_baseline_passing: pre-sprint pass count from the test suite.
      Agents use this to detect whether they introduced new failures
      (their pass count must be >= baseline).
    test_baseline_skipped: skipped count for the same reason.
    pre_phase_head: git HEAD SHA before the phase invocation. Used by
      cross-validation to detect whether the agent committed.
    """

    test_baseline_passing: int = 0
    test_baseline_skipped: int = 0
    pre_phase_head: str = ""


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def _load_prompt_template(phase: Phase) -> str:
    template_path = PROMPTS_DIR / f"{phase.value}.md"
    return template_path.read_text(encoding="utf-8")


def _build_prompt(
    phase: Phase, sprint_id: str, context: Optional[PhaseContext] = None
) -> str:
    """Build the full prompt for a phase by substituting sprint context
    into the template. If `context` is provided, append a baseline
    addendum so the agent knows what the pre-sprint test state was.
    """
    template = _load_prompt_template(phase)
    rendered = (
        template.replace("{SPRINT_ID}", sprint_id)
        .replace("{ROADMAP_PATH}", str(ROADMAP_PATH.relative_to(PROJECT_ROOT)))
        .replace("{CONVENTIONS_PATH}", str(CONVENTIONS_PATH.relative_to(PROJECT_ROOT)))
        .replace("{AGENT_GUIDE_PATH}", str(AGENT_GUIDE_PATH.relative_to(PROJECT_ROOT)))
    )
    if context is not None and context.test_baseline_passing > 0:
        addendum = (
            "\n\n---\n\n"
            "## Pre-phase test baseline (item L)\n\n"
            f"- Tests passing: **{context.test_baseline_passing}**\n"
            f"- Tests skipped: **{context.test_baseline_skipped}**\n\n"
            "Your acceptance bar for the test suite is: pass count must be "
            "**>=** the baseline above. New failures vs. this baseline are a "
            "blocker. Pre-existing skips are fine. If you discover a "
            "pre-existing FAILURE that's already in the baseline, that's "
            "noteworthy but not your sprint's problem to fix unless your work "
            "made it worse.\n"
        )
        rendered += addendum
    return rendered


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


_PERMISSION_DENIAL_PATTERNS = (
    "permission denied",
    "sandbox",
    "not allowed",
    "i don't have permission",
    "i do not have permission",
    "tool use was rejected",
    "blocked by sandbox",
    "operation not permitted",
)


def _scan_for_sentinels(text: str) -> list[tuple[Outcome, str]]:
    """Scan an arbitrary text for sentinel lines, in document order.

    Returns a list of (Outcome, reason) tuples for each sentinel found.
    Caller decides which to honor (typically the last).
    """
    matches: list[tuple[Outcome, str]] = []
    for line in text.splitlines():
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
    return matches


def _diagnose_no_sentinel(
    sprint_id: str,
    returncode: int,
    stdout: str,
    pre_phase_head: str,
) -> str:
    """Build a specific failure reason when the agent wrote no sentinel.

    Looks at: returncode, commit count vs. pre_phase_head, presence of
    permission-denial keywords in stdout, stdout length. Returns a
    one-line reason suitable for surfacing to the operator.
    """
    bits: list[str] = []
    if returncode != 0:
        bits.append(f"agent exited with returncode {returncode}")
    else:
        bits.append("agent exited cleanly")

    # Count commits referencing this sprint since pre-phase HEAD.
    if pre_phase_head:
        commits = _commits_since(pre_phase_head, sprint_id)
        bits.append(f"commits referencing {sprint_id}: {len(commits)}")

    # Check stdout for telltale permission failures.
    lowered = (stdout or "").lower()
    hit = next((p for p in _PERMISSION_DENIAL_PATTERNS if p in lowered), None)
    if hit:
        bits.append(
            f"stdout contains permission-denial signal ({hit!r}); "
            f"check CLAUDE_CMD has `--dangerously-skip-permissions` "
            f"and the write-permission probe at startup"
        )

    if not stdout:
        bits.append("agent stdout was empty (subprocess may have failed early)")
    elif len(stdout) < 200:
        bits.append(f"agent stdout was short ({len(stdout)} chars) — likely an early bail")

    bits.append("no sentinel in ROADMAP.md or in agent stdout")
    return "; ".join(bits)


def _detect_outcome(
    sprint_id: str,
    returncode: int,
    stdout: str = "",
    pre_phase_head: str = "",
) -> tuple[Outcome, str]:
    """Determine the phase outcome from the agent's Activity-log update.

    Sentinels (the agent is told to write one of these in its final log
    entry):
      - PHASE_OK
      - PHASE_BLOCKED: <reason>
      - PHASE_NEEDS_REWORK: <reason>

    Detection order:
      1. Activity log of the sprint section in ROADMAP.md (canonical).
      2. Agent stdout — fallback for the case where the agent decided
         BLOCKED/NEEDS_REWORK but couldn't persist the write (sandbox,
         filesystem failure). PHASE_OK from stdout is NOT honored —
         claiming success without persisting is treated as ERROR.

    If the agent crashed (returncode != 0) and didn't write a sentinel,
    treat as ERROR. If the subprocess succeeded but no sentinel appears
    in either place, treat as ERROR with a specific diagnostic.
    """
    activity_log = _read_recent_activity_log(sprint_id)
    matches = _scan_for_sentinels(activity_log)

    if matches:
        # Agent's last sentinel in the canonical log wins.
        return matches[-1]

    # Fallback: scan stdout. Agents writing PHASE_BLOCKED to stdout when
    # they couldn't write to ROADMAP.md should still be detectable.
    if stdout:
        stdout_matches = _scan_for_sentinels(stdout)
        # Filter out OK — never trust a success claim that didn't persist.
        non_ok = [m for m in stdout_matches if m[0] != Outcome.OK]
        if non_ok:
            outcome, reason = non_ok[-1]
            qualifier = "(detected in stdout fallback — agent did not write to ROADMAP.md)"
            return outcome, f"{reason} {qualifier}".strip()

    reason = _diagnose_no_sentinel(sprint_id, returncode, stdout, pre_phase_head)
    return Outcome.ERROR, reason


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def _git_head_sha() -> str:
    """Return current HEAD SHA. Empty string on error."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _commits_since(sha: str, sprint_id: str) -> list[str]:
    """Return the oneline commits since `sha` whose subject contains
    `sprint_id`. Used by sentinel cross-validation (item E).
    """
    import subprocess

    if not sha:
        return []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{sha}..HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        return [line for line in result.stdout.splitlines() if sprint_id in line]
    except Exception:
        return []


def run_phase(
    phase: Phase, sprint_id: str, context: Optional[PhaseContext] = None
) -> PhaseResult:
    """Invoke the agent for the given phase against the given sprint.

    Wraps subprocess invocation with:
      - Pre-phase ROADMAP.md snapshot (item B + C).
      - Pre-phase git HEAD capture for sentinel cross-validation (item E).
      - Optional pre-phase test baseline included in the prompt (item L).
      - Post-phase validation: roadmap parses cleanly, claimed sprint
        still exists, no out-of-claim modifications, no deletions, new
        sprints only in phases that allow it.
      - Post-PHASE_OK cross-check: was a commit made referencing the
        sprint ID? If not, override outcome (item E).
      - On validation failure: restore the snapshot, return ERROR with
        the validation reason.

    Returns a PhaseResult with the detected outcome. The harness uses
    this to decide whether to advance, retry, or block the sprint.
    """
    log_path = _log_path_for(sprint_id, phase)
    prompt = _build_prompt(phase, sprint_id, context=context)

    # Capture pre-phase HEAD for sentinel cross-validation (item E).
    if context is None:
        context = PhaseContext()
    if not context.pre_phase_head:
        context.pre_phase_head = _git_head_sha()

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

    outcome, reason = _detect_outcome(
        sprint_id,
        returncode,
        stdout=_stdout,
        pre_phase_head=context.pre_phase_head if context else "",
    )

    # Sentinel cross-validation (item E): a PHASE_OK on a phase that
    # should have produced commits must show at least one. If no commit
    # references the sprint ID, override the OK to ERROR.
    if (
        outcome == Outcome.OK
        and not DRY_RUN
        and context is not None
        and context.pre_phase_head
    ):
        commits = _commits_since(context.pre_phase_head, sprint_id)
        if not commits:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(
                    f"\n--- SENTINEL CROSS-VALIDATION: PHASE_OK but no commits "
                    f"reference {sprint_id} since {context.pre_phase_head[:8]} ---\n"
                )
            return PhaseResult(
                outcome=Outcome.ERROR,
                phase=phase,
                sprint_id=sprint_id,
                log_path=log_path,
                reason=(
                    f"sentinel says PHASE_OK but no commits reference {sprint_id}. "
                    "Agent claimed completion without committing — protocol violation."
                ),
            )

    return PhaseResult(
        outcome=outcome,
        phase=phase,
        sprint_id=sprint_id,
        log_path=log_path,
        reason=reason,
    )
