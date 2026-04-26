"""Ralph loop harness — main loop entry.

Run with `python -m ralph.harness`. See `ralph/README.md` for usage.

Sequential, single-sprint-at-a-time. Three-phase per sprint
(plan → implement → review), with bounded rework cycles between
implement and review. Clean exit via `STOP` file or SIGINT.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ralph import agents, roadmap_state
from ralph.agents import Outcome, Phase, PhaseContext, PhaseResult
from ralph.config import (
    DEFAULT_MAX_SPRINTS_PER_RUN,
    DRY_RUN,
    INTER_SPRINT_SLEEP,
    IN_PROGRESS_STALE_MINUTES,
    LOCK_FILE,
    LOGS_DIR,
    MAX_REWORK_CYCLES,
    PROJECT_ROOT,
    PUSH_ON_SPRINT_COMPLETE,
    PUSH_TIMEOUT_SECONDS,
    REQUIRE_CLEAN_WORKING_TREE,
    ROADMAP_PATH,
    STATE_FILE,
    STATUS_BLOCKED,
    STATUS_DONE,
    STATUS_IMPLEMENTING,
    STATUS_PLANNING,
    STATUS_REVIEW,
    STATUS_REVIEWING,
    STATUS_TODO,
    STOP_FILE,
)


# ---------------------------------------------------------------------------
# Persistent state
# ---------------------------------------------------------------------------


@dataclass
class SprintState:
    """Per-sprint runtime state, persisted across harness runs."""

    sprint_id: str
    plan_runs: int = 0
    implement_runs: int = 0
    review_runs: int = 0
    rework_cycles: int = 0
    last_phase: Optional[str] = None
    last_outcome: Optional[str] = None
    started_at: Optional[str] = None
    last_touched_at: Optional[str] = None


@dataclass
class HarnessState:
    """Aggregate harness state."""

    sprints: dict[str, SprintState] = field(default_factory=dict)
    total_sprints_processed: int = 0
    last_run_started_at: Optional[str] = None

    @classmethod
    def load(cls) -> "HarnessState":
        if not STATE_FILE.exists():
            return cls()
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        sprints = {
            sid: SprintState(**sd) for sid, sd in raw.get("sprints", {}).items()
        }
        return cls(
            sprints=sprints,
            total_sprints_processed=raw.get("total_sprints_processed", 0),
            last_run_started_at=raw.get("last_run_started_at"),
        )

    def save(self) -> None:
        payload = {
            "sprints": {sid: asdict(s) for sid, s in self.sprints.items()},
            "total_sprints_processed": self.total_sprints_processed,
            "last_run_started_at": self.last_run_started_at,
        }
        STATE_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def for_sprint(self, sprint_id: str) -> SprintState:
        if sprint_id not in self.sprints:
            self.sprints[sprint_id] = SprintState(sprint_id=sprint_id)
        return self.sprints[sprint_id]


# ---------------------------------------------------------------------------
# Stop signaling
# ---------------------------------------------------------------------------


_stop_requested = False


def _sigint_handler(signum, frame):  # type: ignore[no-untyped-def]
    global _stop_requested
    _stop_requested = True
    log("SIGINT received. Will exit after current phase.")


def should_stop() -> bool:
    """Return True when the harness should exit cleanly."""
    if _stop_requested:
        return True
    if STOP_FILE.exists():
        log(f"STOP file present at {STOP_FILE}. Will exit after current phase.")
        return True
    return False


def consume_stop_file() -> None:
    """Delete the STOP file after acting on it, so a future run isn't immediately stopped."""
    if STOP_FILE.exists():
        try:
            STOP_FILE.unlink()
            log(f"Removed {STOP_FILE} after honoring stop signal.")
        except OSError as e:
            log(f"Could not remove {STOP_FILE}: {e}")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    """Emit a timestamped line to stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Per-sprint execution
# ---------------------------------------------------------------------------


def execute_sprint(
    sprint_id: str,
    state: HarnessState,
    test_baseline: tuple[int, int] = (0, 0),
) -> Outcome:
    """Run plan → (implement → review) cycles for one sprint.

    test_baseline: (passing, skipped) counts captured before this sprint.
    Threaded through to agents as PhaseContext so they can detect NEW
    failures (item L).

    Returns the final Outcome (OK, BLOCKED, TIMEOUT, ERROR).
    """
    sprint_state = state.for_sprint(sprint_id)
    sprint_state.started_at = sprint_state.started_at or datetime.now().isoformat()
    sprint_state.last_touched_at = datetime.now().isoformat()

    base_pass, base_skip = test_baseline
    phase_context = PhaseContext(
        test_baseline_passing=base_pass,
        test_baseline_skipped=base_skip,
    )

    # ---- Phase 1: Plan ----
    log(f"{sprint_id}: phase=plan starting")
    roadmap_state.update_status(sprint_id, STATUS_PLANNING)
    roadmap_state.append_activity_log(
        sprint_id, "harness: plan phase starting"
    )
    plan_result = agents.run_phase(Phase.PLAN, sprint_id, context=phase_context)
    sprint_state.plan_runs += 1
    sprint_state.last_phase = "plan"
    sprint_state.last_outcome = plan_result.outcome.value
    sprint_state.last_touched_at = datetime.now().isoformat()
    state.save()
    log(
        f"{sprint_id}: phase=plan outcome={plan_result.outcome.value} "
        f"reason={plan_result.reason!r} log={plan_result.log_path.name}"
    )

    if plan_result.outcome != Outcome.OK:
        roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: plan phase outcome={plan_result.outcome.value}, marking blocked. {plan_result.reason}",
        )
        return plan_result.outcome

    if should_stop():
        roadmap_state.append_activity_log(
            sprint_id, "harness: stop requested after plan phase"
        )
        return Outcome.OK  # Plan phase succeeded; stopping here is clean.

    # ---- Phase 2 + 3: Implement → Review (with bounded rework) ----
    while sprint_state.rework_cycles < MAX_REWORK_CYCLES:
        # Implement
        log(f"{sprint_id}: phase=implement starting (rework cycle {sprint_state.rework_cycles})")
        roadmap_state.update_status(sprint_id, STATUS_IMPLEMENTING)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: implement phase starting (rework cycle {sprint_state.rework_cycles})",
        )
        impl_result = agents.run_phase(Phase.IMPLEMENT, sprint_id, context=phase_context)
        sprint_state.implement_runs += 1
        sprint_state.last_phase = "implement"
        sprint_state.last_outcome = impl_result.outcome.value
        sprint_state.last_touched_at = datetime.now().isoformat()
        state.save()
        log(
            f"{sprint_id}: phase=implement outcome={impl_result.outcome.value} "
            f"reason={impl_result.reason!r} log={impl_result.log_path.name}"
        )

        if impl_result.outcome != Outcome.OK:
            roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
            roadmap_state.append_activity_log(
                sprint_id,
                f"harness: implement phase outcome={impl_result.outcome.value}, marking blocked. {impl_result.reason}",
            )
            return impl_result.outcome

        if should_stop():
            roadmap_state.update_status(sprint_id, STATUS_REVIEW)
            roadmap_state.append_activity_log(
                sprint_id, "harness: stop requested after implement phase"
            )
            return Outcome.OK

        # Review
        log(f"{sprint_id}: phase=review starting (rework cycle {sprint_state.rework_cycles})")
        roadmap_state.update_status(sprint_id, STATUS_REVIEWING)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: review phase starting (rework cycle {sprint_state.rework_cycles})",
        )
        review_result = agents.run_phase(Phase.REVIEW, sprint_id, context=phase_context)
        sprint_state.review_runs += 1
        sprint_state.last_phase = "review"
        sprint_state.last_outcome = review_result.outcome.value
        sprint_state.last_touched_at = datetime.now().isoformat()
        state.save()
        log(
            f"{sprint_id}: phase=review outcome={review_result.outcome.value} "
            f"reason={review_result.reason!r} log={review_result.log_path.name}"
        )

        if review_result.outcome == Outcome.OK:
            roadmap_state.update_status(sprint_id, STATUS_DONE)
            roadmap_state.append_activity_log(
                sprint_id, "harness: review passed, marking done"
            )
            return Outcome.OK

        if review_result.outcome == Outcome.NEEDS_REWORK:
            sprint_state.rework_cycles += 1
            state.save()
            roadmap_state.append_activity_log(
                sprint_id,
                f"harness: review demanded rework (cycle {sprint_state.rework_cycles}/{MAX_REWORK_CYCLES}). {review_result.reason}",
            )
            if sprint_state.rework_cycles >= MAX_REWORK_CYCLES:
                roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
                roadmap_state.append_activity_log(
                    sprint_id,
                    f"harness: rework cycle cap reached ({MAX_REWORK_CYCLES}), marking blocked",
                )
                return Outcome.BLOCKED
            if should_stop():
                roadmap_state.append_activity_log(
                    sprint_id, "harness: stop requested mid-rework cycle"
                )
                return Outcome.OK
            # Loop back to implement.
            continue

        # BLOCKED, TIMEOUT, ERROR
        roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: review phase outcome={review_result.outcome.value}, marking blocked. {review_result.reason}",
        )
        return review_result.outcome

    # Should be unreachable due to the cap-check above, but defend anyway.
    roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
    roadmap_state.append_activity_log(
        sprint_id, "harness: rework loop exited unexpectedly"
    )
    return Outcome.BLOCKED


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _capture_test_baseline() -> tuple[int, int]:
    """Run pytest -q to capture the current test pass/skip baseline.

    Returns (passing, skipped). On failure to run pytest, returns (0, 0)
    and the prompt addendum is suppressed (the agent runs with no
    baseline rather than a misleading one).

    This is item L: a known baseline so agents can detect NEW failures
    without freaking out about pre-existing ones.
    """
    import re as _re

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-n", "auto", "-q", "--no-header"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0, 0

    # Last "N passed, M skipped" line in pytest -q output.
    out = result.stdout + result.stderr
    pass_count = 0
    skip_count = 0
    for line in reversed(out.splitlines()):
        m = _re.search(r"(\d+) passed", line)
        if m:
            pass_count = int(m.group(1))
            m2 = _re.search(r"(\d+) skipped", line)
            if m2:
                skip_count = int(m2.group(1))
            break
    return pass_count, skip_count


def _run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a git subcommand at the project root. Returns (rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", "git not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "", f"git {args[0]} timed out after {timeout}s"


# ---------------------------------------------------------------------------
# Pre-flight checks (item F)
# ---------------------------------------------------------------------------


def _preflight_checks(allow_dirty: bool, push_enabled: bool) -> int:
    """Verify environment before starting the loop. Returns 0 on success,
    non-zero exit code on failure. Each check fails fast with a clear message.
    """
    # 1. ROADMAP.md exists.
    if not roadmap_state.roadmap_exists():
        log(f"ROADMAP.md not found at {ROADMAP_PATH}. Aborting.")
        return 2

    # 2. git is on PATH.
    rc, _stdout, _stderr = _run_git(["--version"], timeout=10)
    if rc != 0:
        log(f"git unavailable: {_stderr.strip()}. Aborting.")
        return 2

    # 3. We're in a git repository.
    rc, _stdout, _stderr = _run_git(["rev-parse", "--is-inside-work-tree"], timeout=10)
    if rc != 0 or _stdout.strip() != "true":
        log(f"Not in a git repo at {PROJECT_ROOT}. Aborting.")
        return 2

    # 4. Working tree clean (unless overridden).
    if REQUIRE_CLEAN_WORKING_TREE and not allow_dirty:
        rc, stdout, _stderr = _run_git(["status", "--porcelain"], timeout=15)
        if rc != 0:
            log("git status failed. Aborting.")
            return 2
        if stdout.strip():
            log(
                "Working tree is dirty. Agents will commit during phases; "
                "mixing in unrelated changes pollutes sprint history. "
                "Commit or stash, OR pass --allow-dirty to override."
            )
            log(f"Dirty files:\n{stdout}")
            return 2

    # 5. On a branch (not detached HEAD) — required for push.
    if push_enabled:
        rc, stdout, _stderr = _run_git(["symbolic-ref", "--short", "HEAD"], timeout=10)
        if rc != 0:
            log(
                "Detached HEAD detected. Push needs a branch. "
                "Either checkout a branch or pass --no-push."
            )
            return 2

        # 6. Origin remote configured.
        rc, _stdout, _stderr = _run_git(["remote", "get-url", "origin"], timeout=10)
        if rc != 0:
            log(
                "No 'origin' remote configured. Either add origin or pass --no-push."
            )
            return 2

    # 7. Claude CLI available (best-effort).
    from ralph.config import CLAUDE_CMD

    if not DRY_RUN:
        try:
            result = subprocess.run(
                [CLAUDE_CMD[0], "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                log(
                    f"Claude CLI '{CLAUDE_CMD[0]} --version' returned non-zero. "
                    f"The harness will still attempt invocation, but check your install."
                )
        except FileNotFoundError:
            log(
                f"Claude CLI '{CLAUDE_CMD[0]}' not found on PATH. "
                f"The first agent invocation will fail. "
                f"Check ralph/config.py CLAUDE_CMD or your install."
            )
            return 2
        except subprocess.TimeoutExpired:
            log(
                f"Claude CLI did not respond to --version within 10s. "
                f"The harness will still attempt invocation."
            )

    log("Pre-flight checks passed.")
    return 0


# ---------------------------------------------------------------------------
# Lock file (prevents concurrent harness runs)
# ---------------------------------------------------------------------------


def _acquire_lock() -> bool:
    """Try to acquire the harness lock. Returns True on success.

    If a stale lock exists (PID no longer running), remove it and acquire.
    If a fresh lock exists (PID running), refuse to start.
    """
    if LOCK_FILE.exists():
        try:
            other_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            other_pid = -1
        if other_pid > 0 and _pid_alive(other_pid):
            log(
                f"Lock file {LOCK_FILE} held by PID {other_pid} (running). "
                f"Refusing to start a concurrent harness."
            )
            return False
        log(f"Stale lock from PID {other_pid} found; removing.")
        try:
            LOCK_FILE.unlink()
        except OSError as e:
            log(f"Could not remove stale lock: {e}. Aborting.")
            return False
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError as e:
        log(f"Could not create lock file: {e}. Aborting.")
        return False
    return True


def _release_lock() -> None:
    """Remove the lock file on clean exit. Best-effort."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    """Return True if a process with the given PID is currently running."""
    if sys.platform == "win32":
        # Windows: tasklist returns the process name if it exists.
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # If we can't check, assume dead (conservative — let the new run start).
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


# ---------------------------------------------------------------------------
# Stuck-sprint recovery (item D)
# ---------------------------------------------------------------------------


def _recover_stuck_sprints(state: "HarnessState") -> int:
    """Reset sprints stuck in `in-progress (*)` Status from a prior run.

    A sprint is stale if:
      - Its Status starts with "in-progress"
      - Its state.json `last_touched_at` is older than IN_PROGRESS_STALE_MINUTES
        (or there's no state for it at all)

    Stale sprints get their Status reset to `todo` with an Activity log
    note explaining the recovery. The sprint becomes eligible for the
    next pickup.

    Returns the number of sprints recovered.
    """
    sprints = roadmap_state.parse_sprints()
    now = datetime.now()
    stale_threshold = timedelta(minutes=IN_PROGRESS_STALE_MINUTES)
    recovered = 0

    for sprint_id, sprint in sprints.items():
        if not sprint.status.lower().startswith("in-progress"):
            continue

        sprint_state = state.sprints.get(sprint_id)
        last_touched_str = sprint_state.last_touched_at if sprint_state else None
        if last_touched_str:
            try:
                last_touched = datetime.fromisoformat(last_touched_str)
            except ValueError:
                last_touched = None
        else:
            last_touched = None

        is_stale = last_touched is None or (now - last_touched) > stale_threshold
        if not is_stale:
            log(
                f"Sprint {sprint_id} is in-progress but recently touched "
                f"({last_touched_str}). Skipping recovery; another run may be active."
            )
            continue

        log(
            f"Recovering stuck sprint {sprint_id} (status={sprint.status!r}, "
            f"last_touched={last_touched_str}). Resetting to todo."
        )
        roadmap_state.update_status(sprint_id, STATUS_TODO)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: stuck-sprint recovery — was {sprint.status!r}, reset to todo",
        )
        # Don't reset the iteration counters in state.json — they're useful
        # signal for whether this sprint has been struggling.
        recovered += 1

    return recovered


# ---------------------------------------------------------------------------
# Auto-push (item A)
# ---------------------------------------------------------------------------


def _write_sprint_summary(
    sprint_id: str,
    state: "HarnessState",
    final_outcome: Outcome,
) -> None:
    """Write a per-sprint summary to ralph/logs/<SPRINT-ID>/SUMMARY.md.

    Pulls from state.json (per-phase counts, timestamps) and from git
    log (commits made during the sprint window). Provides a postmortem-
    friendly snapshot for human review of completed or blocked sprints.
    """
    sprint_state = state.sprints.get(sprint_id)
    summary_dir = LOGS_DIR / sprint_id
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "SUMMARY.md"

    started = sprint_state.started_at if sprint_state else None
    finished = datetime.now().isoformat()

    # Pull commits made since started — best-effort.
    commits_block = ""
    if started:
        try:
            since_arg = started
            rc, stdout, _stderr = _run_git(
                ["log", "--oneline", f"--since={since_arg}"], timeout=10
            )
            if rc == 0:
                # Filter for commits referencing this sprint ID.
                relevant = [
                    line
                    for line in stdout.splitlines()
                    if sprint_id in line
                ]
                if relevant:
                    commits_block = "\n".join(f"- {line}" for line in relevant)
        except Exception:
            pass

    # Latest log files per phase.
    log_links: list[str] = []
    if summary_dir.exists():
        for log_file in sorted(summary_dir.glob("*.log")):
            log_links.append(f"- [{log_file.name}]({log_file.name})")

    body = [
        f"# Sprint summary: {sprint_id}",
        "",
        f"**Final outcome**: {final_outcome.value}",
        f"**Started**: {started or 'unknown'}",
        f"**Finished**: {finished}",
        "",
        "## Phase iterations",
        "",
        f"- Plan runs: {sprint_state.plan_runs if sprint_state else 0}",
        f"- Implement runs: {sprint_state.implement_runs if sprint_state else 0}",
        f"- Review runs: {sprint_state.review_runs if sprint_state else 0}",
        f"- Rework cycles: {sprint_state.rework_cycles if sprint_state else 0}",
        f"- Last phase: {sprint_state.last_phase if sprint_state else 'n/a'}",
        f"- Last outcome: {sprint_state.last_outcome if sprint_state else 'n/a'}",
        "",
    ]
    if commits_block:
        body.extend(["## Commits", "", commits_block, ""])
    if log_links:
        body.extend(["## Phase logs", "", *log_links, ""])
    body.append(
        "Generated by the ralph harness on sprint termination. See "
        "`requirements/roadmap/ROADMAP.md` for the sprint section + "
        "Activity log."
    )
    summary_path.write_text("\n".join(body), encoding="utf-8")


def _push_after_sprint(sprint_id: str, outcome: Outcome, push_enabled: bool) -> None:
    """Push current branch to origin after sprint completion.

    Pushes on terminal outcomes (OK, BLOCKED, NEEDS_REWORK). Skips
    TIMEOUT and ERROR because state may be inconsistent. Push failures
    are logged but don't crash the harness — a network blip shouldn't
    stop the loop.
    """
    if not push_enabled:
        return
    if outcome not in (Outcome.OK, Outcome.BLOCKED, Outcome.NEEDS_REWORK):
        log(f"{sprint_id}: skipping push (outcome={outcome.value} may be inconsistent)")
        return

    rc, stdout, stderr = _run_git(["push", "origin", "HEAD"], timeout=PUSH_TIMEOUT_SECONDS)
    if rc == 0:
        log(f"{sprint_id}: pushed to origin")
    else:
        log(f"{sprint_id}: push failed (rc={rc}): {stderr.strip() or stdout.strip()}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ralph loop harness for the Aurelia roadmap")
    p.add_argument(
        "--max-sprints",
        type=int,
        default=DEFAULT_MAX_SPRINTS_PER_RUN,
        help=f"Maximum sprints to process this run (default: {DEFAULT_MAX_SPRINTS_PER_RUN})",
    )
    p.add_argument(
        "--sprint",
        type=str,
        default=None,
        help="Force a specific sprint pickup by ID (still respects dependencies)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually invoke Claude; log what would happen",
    )
    p.add_argument(
        "--no-push",
        action="store_true",
        help="Don't `git push` after sprint completion. Default is to push.",
    )
    p.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Skip the working-tree-clean pre-flight check. Use only for debugging.",
    )
    p.add_argument(
        "--skip-recovery",
        action="store_true",
        help="Don't auto-reset stuck-in-progress sprints from prior runs.",
    )
    p.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Don't capture pre-run test baseline. Faster startup; agents won't know the test count target.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        from ralph import config as _cfg

        _cfg.DRY_RUN = True

    push_enabled = not args.no_push and PUSH_ON_SPRINT_COMPLETE

    # Pre-flight checks (item F). Fail fast.
    rc = _preflight_checks(allow_dirty=args.allow_dirty, push_enabled=push_enabled)
    if rc != 0:
        return rc

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Lock — refuse concurrent runs (paranoia / safety).
    if not _acquire_lock():
        return 2

    try:
        state = HarnessState.load()
        state.last_run_started_at = datetime.now().isoformat()
        state.save()

        signal.signal(signal.SIGINT, _sigint_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _sigint_handler)

        # Stuck-sprint recovery (item D).
        if not args.skip_recovery:
            recovered = _recover_stuck_sprints(state)
            if recovered:
                log(f"Recovered {recovered} stuck sprint(s) from prior run.")

        # Test baseline (item L). Captured once at startup; refreshed
        # after every successful sprint so the baseline tracks the
        # growing test count.
        test_baseline = (0, 0)
        if not args.dry_run and not DRY_RUN and not args.skip_baseline:
            log("Capturing test-suite baseline (this can take a minute)...")
            test_baseline = _capture_test_baseline()
            log(
                f"Baseline: {test_baseline[0]} passing, {test_baseline[1]} skipped."
            )

        log(
            f"Harness starting. max_sprints={args.max_sprints} "
            f"dry_run={DRY_RUN or args.dry_run} push={push_enabled} "
            f"baseline={test_baseline[0]}p/{test_baseline[1]}s"
        )
        if args.sprint:
            log(f"Forced sprint pickup: {args.sprint}")

        sprints_processed = 0
        while sprints_processed < args.max_sprints:
            if should_stop():
                log("Stop signal honored before sprint pickup.")
                consume_stop_file()
                break

            sprints = roadmap_state.parse_sprints()

            if args.sprint:
                target = sprints.get(args.sprint)
                if target is None:
                    log(f"Forced sprint {args.sprint} not found. Aborting.")
                    return 2
                if not target.is_todo():
                    log(
                        f"Forced sprint {args.sprint} status={target.status!r}, not todo. Aborting."
                    )
                    return 2
                unmet = [
                    d
                    for d in target.depends_on
                    if not sprints.get(d) or not sprints[d].is_done()
                ]
                if unmet:
                    log(
                        f"Forced sprint {args.sprint} has unmet dependencies: {unmet}. Aborting."
                    )
                    return 2
                picked = target
                args.sprint = None
            else:
                eligible = roadmap_state.eligible_sprints(sprints)
                if not eligible:
                    log("No eligible sprints. Exiting cleanly.")
                    break
                picked = eligible[0]

            log(f"Picking up sprint {picked.sprint_id}: {picked.title}")
            outcome = execute_sprint(
                picked.sprint_id, state, test_baseline=test_baseline
            )
            sprints_processed += 1
            state.total_sprints_processed += 1
            state.save()
            log(f"Sprint {picked.sprint_id} finished with outcome={outcome.value}")

            # Refresh baseline after a successful sprint (item L).
            if (
                outcome == Outcome.OK
                and not args.dry_run
                and not DRY_RUN
                and not args.skip_baseline
            ):
                new_baseline = _capture_test_baseline()
                if new_baseline[0] > 0:
                    log(
                        f"Refreshed baseline: {new_baseline[0]} passing "
                        f"(was {test_baseline[0]}), {new_baseline[1]} skipped."
                    )
                    test_baseline = new_baseline

            # Per-sprint summary (item G).
            try:
                _write_sprint_summary(picked.sprint_id, state, outcome)
            except OSError as e:
                log(f"{picked.sprint_id}: could not write SUMMARY.md: {e}")

            # Index regen (item J). Best-effort: failure here is non-fatal.
            try:
                if roadmap_state.regenerate_index():
                    log(f"{picked.sprint_id}: regenerated SA-arc index")
            except Exception as e:
                log(f"{picked.sprint_id}: index regen failed: {e}")

            # Auto-push (item A) after sprint completion.
            _push_after_sprint(picked.sprint_id, outcome, push_enabled)

            if should_stop():
                consume_stop_file()
                break

            time.sleep(INTER_SPRINT_SLEEP)

        log(f"Harness done. Sprints processed this run: {sprints_processed}.")
        state.save()
        return 0
    finally:
        _release_lock()


if __name__ == "__main__":
    sys.exit(main())
