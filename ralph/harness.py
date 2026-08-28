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
import re
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dataclass_fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ralph import agents, heartbeat, roadmap_state, status, triage
from ralph.agents import Outcome, Phase, PhaseContext, PhaseResult
from ralph.config import (
    DEFAULT_MAX_SPRINTS_PER_RUN,
    DRY_RUN,
    HARNESS_RC_INFRA_ERROR,
    IN_PROGRESS_STALE_MINUTES,
    INTER_SPRINT_SLEEP,
    LOCK_FILE,
    LOGS_DIR,
    MAX_CONSECUTIVE_INFRA_SPRINTS,
    MAX_INFRA_ERRORS_PER_SPRINT,
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
    TEST_WORKERS,
)
from ralph.proc import ATOMIC_WRITE_TMP_SUFFIX, atomic_write, run_with_hard_timeout

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
    # One retry before a failing phase (ERROR / TIMEOUT / INFRA_ERROR) becomes
    # a permanent block. See `_should_retry`. BLOCKED never consumes this --
    # it is a judgement, not a failure.
    retry_count: int = 0
    # Consecutive INFRA_ERROR outcomes on this sprint. `retry_count` does not
    # bound INFRA_ERROR: `_mark_terminal_outcome` resets it to `todo` so the
    # next run picks it up cleanly, which makes it re-runnable without limit.
    # Reset the moment any phase actually completes, since that proves the
    # infrastructure is up. See `MAX_INFRA_ERRORS_PER_SPRINT`.
    infra_error_count: int = 0
    last_phase: Optional[str] = None
    last_outcome: Optional[str] = None
    started_at: Optional[str] = None
    last_touched_at: Optional[str] = None
    # Telemetry: structured `**Last phase report.**` fields parsed from
    # ROADMAP after each phase. Lets future runs aggregate review-quality
    # patterns (single_tighten history, findings counts, rework triggers)
    # without scraping markdown. Empty dicts mean "no report yet" or
    # "report parsing failed gracefully".
    last_plan_report: dict[str, str] = field(default_factory=dict)
    last_implement_report: dict[str, str] = field(default_factory=dict)
    last_review_report: dict[str, str] = field(default_factory=dict)


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
        # Filter unknown keys so older state.json files (missing
        # last_*_report fields, etc.) still load. New fields default
        # via the dataclass.
        valid_keys = {f.name for f in dataclass_fields(SprintState)}
        sprints: dict[str, SprintState] = {}
        for sid, sd in raw.get("sprints", {}).items():
            filtered = {k: v for k, v in sd.items() if k in valid_keys}
            sprints[sid] = SprintState(**filtered)
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
        atomic_write(STATE_FILE, json.dumps(payload, indent=2, ensure_ascii=False))

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
# Heartbeat context
# ---------------------------------------------------------------------------

# What the heartbeat thread reports each beat: (sprint_id, phase). Updated at
# each phase transition inside execute_sprint and reset to (None, None) once
# a sprint stops being actively worked (any exit path — done, blocked, error).
_current_context: tuple[Optional[str], Optional[str]] = (None, None)


def _set_context(sprint: Optional[str], phase: Optional[str]) -> None:
    """Update what the heartbeat thread reports on its next beat."""
    global _current_context
    _current_context = (sprint, phase)


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


def _safe_parse_phase_report(sprint_id: str) -> dict[str, str]:
    """Best-effort parse of the sprint's `**Last phase report.**` block.

    Returns empty dict on any failure (sprint missing, file unreadable,
    no report block). Telemetry is nice-to-have — never let parsing
    failure crash a phase transition.
    """
    try:
        return roadmap_state.parse_last_phase_report(sprint_id)
    except Exception:
        return {}


def _mark_terminal_outcome(sprint_id: str, phase: str, outcome: Outcome, reason: str) -> None:
    """Set ROADMAP status + activity log for a non-OK phase outcome.

    INFRA_ERROR is special: the agent never meaningfully executed (CLI/
    network/auth failed). Reset to `todo` so the next harness run picks
    the sprint up cleanly. All other non-OK outcomes mark the sprint
    blocked for human attention.
    """
    if outcome == Outcome.INFRA_ERROR:
        roadmap_state.update_status(sprint_id, STATUS_TODO)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: {phase} phase outcome=infra_error, resetting to todo "
            f"(re-runnable). {reason}",
        )
        return
    roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
    roadmap_state.append_activity_log(
        sprint_id,
        f"harness: {phase} phase outcome={outcome.value}, marking blocked. {reason}",
    )


# ---------------------------------------------------------------------------
# Retry grace (item: harness resilience) — one retry before a failure blocks
# ---------------------------------------------------------------------------

_RETRYABLE_OUTCOMES = frozenset({Outcome.ERROR, Outcome.TIMEOUT, Outcome.INFRA_ERROR})


def _should_retry(sprint_state: SprintState, outcome: Outcome) -> bool:
    """One retry before a failure becomes a block.

    SA-F2 failed once in April with returncode 1 and 135 bytes of output -- a
    transient bail -- and stayed blocked for four months, stranding five
    sprints. A single retry absorbs that class entirely.

    BLOCKED is never retried: an agent writing PHASE_BLOCKED made a judgement,
    and repeating the phase will not change it.
    """
    if outcome not in _RETRYABLE_OUTCOMES:
        return False
    return sprint_state.retry_count < 1


def _sprint_has_partial_commits(sprint_id: str, phase_context: PhaseContext) -> bool:
    """True if a commit referencing `sprint_id` has landed since the sprint
    started this attempt.

    Reuses `agents._commits_since` -- the same signal `agents.run_phase`
    already computes for PHASE_OK sentinel cross-validation -- rather than
    re-deriving it. Retrying a phase that already committed risks
    duplicating that work, so this gates the retry decision below.
    """
    if not phase_context.pre_phase_head:
        return False
    return bool(agents._commits_since(phase_context.pre_phase_head, sprint_id))


def _handle_non_ok_phase(
    sprint_id: str,
    phase: str,
    result: PhaseResult,
    sprint_state: SprintState,
    phase_context: PhaseContext,
    state: HarnessState,
) -> None:
    """Decide retry vs. terminal block for a non-OK phase outcome.

    If `_should_retry` allows it AND the phase left no commits behind, reset
    the sprint to `todo` so the main loop picks it back up rather than
    blocking on a single transient failure. If commits already exist, the
    work is partially done -- retrying risks duplicating it, so this always
    marks blocked instead, even on what would otherwise be the free retry.
    """
    outcome = result.outcome
    if outcome == Outcome.INFRA_ERROR:
        sprint_state.infra_error_count += 1
        state.save()
        if sprint_state.infra_error_count >= MAX_INFRA_ERRORS_PER_SPRINT:
            _mark_terminal_outcome(
                sprint_id,
                phase,
                Outcome.BLOCKED,
                f"{result.reason} (blocking rather than resetting to todo: "
                f"{sprint_state.infra_error_count} consecutive infrastructure failures on "
                f"this sprint. INFRA_ERROR normally resets to todo and is therefore "
                f"re-runnable without limit; this bound stops one sprint holding the "
                f"whole queue behind it.)",
            )
            return
    if _should_retry(sprint_state, outcome):
        if _sprint_has_partial_commits(sprint_id, phase_context):
            _mark_terminal_outcome(
                sprint_id,
                phase,
                Outcome.BLOCKED,
                f"{result.reason} (not retrying -- a commit referencing {sprint_id} "
                "already landed this attempt; re-running risks duplicating partial work)",
            )
            return
        sprint_state.retry_count += 1
        state.save()
        roadmap_state.update_status(sprint_id, STATUS_TODO)
        roadmap_state.append_activity_log(
            sprint_id,
            f"harness: {phase} phase outcome={outcome.value}, retrying "
            f"(retry {sprint_state.retry_count}/1) rather than blocking. {result.reason}",
        )
        return
    _mark_terminal_outcome(sprint_id, phase, outcome, result.reason)


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

    Wrapped in try/finally so the heartbeat context (`_current_context`) is
    reset to (None, None) no matter which of the many exit paths below is
    taken -- otherwise the heartbeat would keep reporting a stale phase for
    a sprint that has already finished.
    """
    try:
        return _run_sprint_phases(sprint_id, state, test_baseline)
    finally:
        _set_context(None, None)


def _run_sprint_phases(
    sprint_id: str,
    state: HarnessState,
    test_baseline: tuple[int, int],
) -> Outcome:
    """The actual plan → (implement → review) logic. See `execute_sprint`."""
    sprint_state = state.for_sprint(sprint_id)
    sprint_state.started_at = sprint_state.started_at or datetime.now().isoformat()
    sprint_state.last_touched_at = datetime.now().isoformat()

    base_pass, base_skip = test_baseline
    phase_context = PhaseContext(
        test_baseline_passing=base_pass,
        test_baseline_skipped=base_skip,
    )

    # ---- Phase 1: Plan ----
    _set_context(sprint_id, "plan")
    log(f"{sprint_id}: phase=plan starting")
    roadmap_state.update_status(sprint_id, STATUS_PLANNING)
    roadmap_state.append_activity_log(sprint_id, "harness: plan phase starting")
    plan_result = agents.run_phase(Phase.PLAN, sprint_id, context=phase_context)
    sprint_state.plan_runs += 1
    sprint_state.last_phase = "plan"
    sprint_state.last_outcome = plan_result.outcome.value
    sprint_state.last_touched_at = datetime.now().isoformat()
    sprint_state.last_plan_report = _safe_parse_phase_report(sprint_id)
    state.save()
    log(
        f"{sprint_id}: phase=plan outcome={plan_result.outcome.value} "
        f"reason={plan_result.reason!r} log={plan_result.log_path.name}"
    )

    if plan_result.outcome != Outcome.OK:
        _handle_non_ok_phase(sprint_id, "plan", plan_result, sprint_state, phase_context, state)
        return plan_result.outcome

    # A phase that actually completed proves the CLI, the network and the auth
    # token are all working, so any earlier infrastructure failures on this
    # sprint were transient.
    sprint_state.infra_error_count = 0
    state.save()

    if not DRY_RUN:
        gate = _run_quality_gates()
        if gate is not None:
            gate_name, err = gate
            reason = f"quality-gate regression ({gate_name}): {err}"
            _mark_terminal_outcome(sprint_id, "plan", Outcome.BLOCKED, reason)
            return Outcome.BLOCKED

    if should_stop():
        roadmap_state.append_activity_log(sprint_id, "harness: stop requested after plan phase")
        return Outcome.OK  # Plan phase succeeded; stopping here is clean.

    # ---- Phase 2 + 3: Implement → Review (with bounded rework) ----
    while sprint_state.rework_cycles < MAX_REWORK_CYCLES:
        # Implement
        _set_context(sprint_id, "implement")
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
        sprint_state.last_implement_report = _safe_parse_phase_report(sprint_id)
        state.save()
        log(
            f"{sprint_id}: phase=implement outcome={impl_result.outcome.value} "
            f"reason={impl_result.reason!r} log={impl_result.log_path.name}"
        )

        if impl_result.outcome != Outcome.OK:
            _handle_non_ok_phase(
                sprint_id, "implement", impl_result, sprint_state, phase_context, state
            )
            return impl_result.outcome

        if not DRY_RUN:
            gate = _run_quality_gates()
            if gate is not None:
                gate_name, err = gate
                reason = f"quality-gate regression ({gate_name}): {err}"
                _mark_terminal_outcome(sprint_id, "implement", Outcome.BLOCKED, reason)
                return Outcome.BLOCKED

        if should_stop():
            roadmap_state.update_status(sprint_id, STATUS_REVIEW)
            roadmap_state.append_activity_log(
                sprint_id, "harness: stop requested after implement phase"
            )
            return Outcome.OK

        # Review
        _set_context(sprint_id, "review")
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
        sprint_state.last_review_report = _safe_parse_phase_report(sprint_id)
        state.save()
        log(
            f"{sprint_id}: phase=review outcome={review_result.outcome.value} "
            f"reason={review_result.reason!r} log={review_result.log_path.name}"
        )

        if review_result.outcome == Outcome.OK:
            if not DRY_RUN:
                gate = _run_quality_gates()
                if gate is not None:
                    gate_name, err = gate
                    reason = f"quality-gate regression ({gate_name}): {err}"
                    _mark_terminal_outcome(sprint_id, "review", Outcome.BLOCKED, reason)
                    return Outcome.BLOCKED

                # The test gate runs here and nowhere else: the last moment
                # before the sprint is marked done, the bookkeeping is
                # committed, and the work is PUSHED. Gating here is what stops
                # a break being authored, pushed, and then built on for days.
                # Once per sprint rather than once per phase -- a sprint runs
                # up to seven agent phases, so per-phase would cost seven
                # full-suite runs to protect against intermediate red trees the
                # review agent exists to resolve.
                log("Running test-suite gate before marking the sprint done...")
                test_gate = _run_test_gate(test_baseline)
                if test_gate is not None:
                    _gate_name, err = test_gate
                    reason = f"test-suite gate FAILED: {err}"
                    _mark_terminal_outcome(sprint_id, "review", Outcome.BLOCKED, reason)
                    _set_red_tree(f"{sprint_id}: {reason}")
                    return Outcome.BLOCKED
            roadmap_state.update_status(sprint_id, STATUS_DONE)
            roadmap_state.append_activity_log(sprint_id, "harness: review passed, marking done")
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

        # BLOCKED, TIMEOUT, ERROR, INFRA_ERROR
        _handle_non_ok_phase(sprint_id, "review", review_result, sprint_state, phase_context, state)
        return review_result.outcome

    # Should be unreachable due to the cap-check above, but defend anyway.
    roadmap_state.update_status(sprint_id, STATUS_BLOCKED)
    roadmap_state.append_activity_log(sprint_id, "harness: rework loop exited unexpectedly")
    return Outcome.BLOCKED


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


class BaselineCaptureError(RuntimeError):
    """Raised when test-baseline capture fails in a way that prevents a safe run.

    The three failure modes that surface this:
    1. Timeout (subprocess killed but communicate() would have hung indefinitely).
    2. Non-zero subprocess exit (pytest crashed or suite is broken).
    3. Unparseable output (zero exit but no 'N passed' line found).

    On startup, the harness must abort when it sees this; proceeding with a
    zero baseline means agents cannot detect new regressions.
    """


def _parse_pytest_counts(output: str) -> Optional[tuple[int, int]]:
    """(passed, skipped) from a pytest summary line, or None if absent.

    Shared by the startup baseline capture and the per-sprint test gate so the
    two can never disagree about what pytest said.
    """
    for line in reversed(output.splitlines()):
        m = re.search(r"(\d+) passed", line)
        if m:
            skipped = re.search(r"(\d+) skipped", line)
            return int(m.group(1)), int(skipped.group(1)) if skipped else 0
    return None


# The full suite is ~100s at -n 8. 15 minutes is a wide margin for a loaded
# machine while still being a bound: a pytest run that never finishes must not
# become the harness's new way of hanging.
TEST_GATE_TIMEOUT_SECONDS: int = 900

# Characters of pytest output carried into the block reason / STATUS.md.
_TEST_GATE_TAIL_CHARS: int = 1200


def _pytest_gate_cmd(*extra: str) -> list[str]:
    """The gate's pytest argv.

    `-n TEST_WORKERS` (8), never `-n auto`: auto hung 6 runs in 10 on this
    host, and a gate that hangs is worse than no gate. See config.TEST_WORKERS
    for the measurement.
    """
    return [sys.executable, "-m", "pytest", "-n", TEST_WORKERS, "-q", "--no-header", *extra]


def _run_test_gate(test_baseline: tuple[int, int]) -> Optional[tuple[str, str]]:
    """Run the test suite as a quality gate. None means pass.

    `_run_quality_gates` runs ruff, ruff-format and mypy -- not pytest. So
    "tests still pass" was enforced only by a paragraph in the agent's prompt
    and by whatever the review agent chose to check, and the sequence
    "implement breaks the suite -> PHASE_OK -> lint/format/types pass because
    they do not run tests -> sprint marked done -> pushed to origin -> repeat,
    up to 10 sprints per invocation" was fully available. During an unattended
    week authoring game content, later sprints would be built on the break for
    days before the next launch's baseline capture aborted with rc 3.

    Called once per sprint, at the last moment before the sprint is marked
    done and the harness commits and pushes -- see `_run_sprint_phases`.

    Absolute green, not a delta, and that is safe *because* of the baseline:
    `_capture_test_baseline` hard-aborts the whole run (rc 3) when the suite is
    red at startup, so a run only exists if the tree was green when it began.
    Any red seen here therefore belongs to this run. Where that guarantee is
    absent -- `--skip-baseline`, `--dry-run` -- the gate declines rather than
    inventing an anchor it does not have.

    A first failure is re-run with `--last-failed` before it counts. A single
    flaky test must not block a sprint, and the retry is cheap because it only
    happens on failure and only re-runs what failed.

    Returns:
        None when the suite passes (or the gate legitimately declines to run),
        or ``(gate_name, error_text)`` describing the failure.
    """
    if test_baseline == (0, 0):
        # No known-good anchor was captured (--skip-baseline / --dry-run).
        return None

    try:
        result = run_with_hard_timeout(
            _pytest_gate_cmd(),
            timeout_seconds=TEST_GATE_TIMEOUT_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return (
            "pytest",
            f"the test suite did not finish within {TEST_GATE_TIMEOUT_SECONDS}s. "
            "Treated as a failure: an unbounded suite is indistinguishable from a "
            "hung one, and neither may be built on.",
        )
    except FileNotFoundError as exc:
        return ("pytest", f"could not run pytest: {exc}")

    combined = result.stdout + result.stderr

    if result.returncode != 0:
        log("Test gate: suite FAILED; re-running the failures once before blocking.")
        try:
            retry = run_with_hard_timeout(
                _pytest_gate_cmd("--last-failed"),
                timeout_seconds=TEST_GATE_TIMEOUT_SECONDS,
                cwd=str(PROJECT_ROOT),
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return ("pytest", f"{combined[-_TEST_GATE_TAIL_CHARS:]}\n(retry failed: {exc})")
        if retry.returncode != 0:
            return ("pytest", combined[-_TEST_GATE_TAIL_CHARS:].strip())
        log("Test gate: the failure did not reproduce on re-run; treating it as a flake.")
        return None

    counts = _parse_pytest_counts(combined)
    if counts is None:
        return (
            "pytest",
            "pytest exited 0 but printed no 'N passed' summary line, so the gate "
            "cannot tell whether the suite actually ran.",
        )
    passed, _skipped = counts
    if passed < test_baseline[0]:
        return (
            "pytest",
            f"the suite passes but the passing count fell from {test_baseline[0]} to "
            f"{passed}. Tests were deleted or skipped rather than fixed -- which is "
            "exactly how a red suite is made green when nobody is watching.",
        )
    return None


def _capture_test_baseline() -> tuple[int, int]:
    """Run pytest -q to capture the current test pass/skip baseline.

    Returns:
        ``(passing, skipped)`` counts extracted from pytest output.

    Raises:
        BaselineCaptureError: On timeout, subprocess error, or unparseable output.
            The harness main loop catches this and aborts before picking up any sprint.
    """
    try:
        result = run_with_hard_timeout(
            [sys.executable, "-m", "pytest", "-n", TEST_WORKERS, "-q", "--no-header"],
            timeout_seconds=600,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired as exc:
        raise BaselineCaptureError("timeout after 600s — pytest run never finished") from exc
    except FileNotFoundError as exc:
        raise BaselineCaptureError(f"FileNotFoundError: {exc}") from exc

    if result.returncode != 0:
        tail = (result.stderr or result.stdout)[-500:].strip()
        raise BaselineCaptureError(
            f"pytest exited {result.returncode}; tail: {tail or '(no output)'}"
        )

    counts = _parse_pytest_counts(result.stdout + result.stderr)
    if counts is None:
        raise BaselineCaptureError("unparseable output — no 'N passed' line in pytest output")
    return counts


_HARNESS_MANAGED_RUNTIME_BASE: tuple[str, ...] = (
    "ralph/.running",
    "ralph/state.json",
    "ralph/heartbeat.json",
    "ralph/push_state.json",
    "ralph/supervisor_stop.json",
    "ralph/.write_probe",
    "ralph/.agency_probe",
    "STOP",
    "STATUS.md",
)

# Every destination written through `ralph.proc.atomic_write`, repo-relative.
#
# This is the registry, not a convenience list: `atomic_write` writes
# "<path>.tmp" then `os.replace`s it into place, and its `finally` only deletes
# that sibling when an *exception* unwinds. A hard kill -- `taskkill /F`
# (which is exactly what the supervisor's own stale-heartbeat recovery does),
# SIGKILL, Task Scheduler's AllowHardTerminate, a power cut -- skips `finally`
# entirely and strands the .tmp.
#
# A stranded .tmp is untracked, so preflight's clean-tree check fails and EVERY
# later launch returns HARNESS_RC_PREFLIGHT_FAILURE. The harness stays bricked
# until a human deletes a file they have no reason to know exists -- and the
# preflight exit is the one that writes no STATUS.md of its own, so the bricked
# state is also the invisible one.
#
# ROADMAP.md is the load-bearing entry: it is the largest file written (~9,000
# lines, the widest write window), it is written a dozen times per sprint, and
# unlike the runtime files below it is NOT gitignored -- an orphan there is
# real, visible working-tree dirt. It appears here and not in
# `_HARNESS_MANAGED_RUNTIME_BASE` on purpose: only its `.tmp` sibling is
# harness noise, while a genuinely modified ROADMAP.md must still fail the
# clean-tree check.
#
# `tests/test_ralph/test_harness.py::TestAtomicWriteTmpOrphansDoNotBrickTheHarness`
# walks the AST of every module for `atomic_write(...)` call sites and fails if
# one names a destination that is not covered here, so a future write site
# cannot be added silently.
_ATOMIC_WRITE_TARGETS: tuple[str, ...] = (
    "ralph/state.json",  # HarnessState.save
    "ralph/heartbeat.json",  # heartbeat.write_heartbeat
    "ralph/push_state.json",  # status.record_push
    "ralph/supervisor_stop.json",  # supervisor.record_terminal_stop
    "STATUS.md",  # status.write_status
    "requirements/roadmap/ROADMAP.md",  # roadmap_state._write_roadmap, _sync_roadmap_index
    # ralph/logs/<sprint>/SUMMARY.md (_write_sprint_summary) is covered by
    # _HARNESS_MANAGED_RUNTIME_PREFIXES below, which already swallows the
    # whole gitignored log tree.
)

# Derived rather than hand-listed so neither a new managed runtime file nor a
# new atomic-write destination can be added without its .tmp sibling coming
# along. `dict.fromkeys` de-duplicates while preserving order.
_HARNESS_MANAGED_RUNTIME_FILES: tuple[str, ...] = _HARNESS_MANAGED_RUNTIME_BASE + tuple(
    f"{name}{ATOMIC_WRITE_TMP_SUFFIX}"
    for name in dict.fromkeys(_HARNESS_MANAGED_RUNTIME_BASE + _ATOMIC_WRITE_TARGETS)
)
_HARNESS_MANAGED_RUNTIME_PREFIXES: tuple[str, ...] = ("ralph/logs/",)

# A .tmp sibling younger than this may belong to a write happening right now
# (preflight runs before the lock is acquired, so a second instance can be
# mid-write), so the sweep leaves it alone and the managed-dirty filter above
# covers it instead. An `atomic_write` takes milliseconds; a minute is a very
# wide margin.
TMP_ORPHAN_MIN_AGE_SECONDS: float = 60.0

# Maximum characters of gate output captured in the activity-log entry.
# Full output lives in the phase log; this keeps the ROADMAP readable.
_GATE_ERROR_MAX_CHARS: int = 500

# Set when the per-sprint test gate fails. Module-level for the same reason as
# `_current_context`: it is produced deep inside `_run_sprint_phases` and
# consumed by `main()`, which must stop the run rather than author further
# sprints on top of a red tree, and must say so in STATUS.md.
_red_tree_reason: Optional[str] = None


def _set_red_tree(reason: str) -> None:
    """Record that the test suite is failing, for `main()` to act on."""
    global _red_tree_reason
    _red_tree_reason = reason


def _consume_red_tree() -> Optional[str]:
    """Read and clear the red-tree reason."""
    global _red_tree_reason
    reason, _red_tree_reason = _red_tree_reason, None
    return reason


def _run_quality_gates() -> Optional[tuple[str, str]]:
    """Run ruff, ruff-format, and mypy quality gates against the project.

    Runs three gates in order, short-circuiting on first failure:
    1. ``ruff check spacegame/``
    2. ``ruff format --check spacegame/ tests/``
    3. ``mypy spacegame/`` piped through a Python note-filter into
       ``mypy_baseline filter`` (Windows-safe; no shell=True).

    Returns:
        None when all gates pass, or ``(gate_name, error_text)`` on the
        first regression. On subprocess exception (FileNotFoundError,
        TimeoutExpired) the exception class and message are returned as
        the error text so a broken tool install surfaces as a gate
        failure rather than crashing the harness.
    """

    def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
            **kwargs,  # type: ignore[arg-type]
        )

    # Gate 1: ruff check spacegame/
    gate_name = "ruff"
    try:
        result = _run([sys.executable, "-m", "ruff", "check", "spacegame/"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (gate_name, f"{type(exc).__name__}: {exc}"[:_GATE_ERROR_MAX_CHARS])
    if result.returncode != 0:
        return (gate_name, (result.stdout + result.stderr)[:_GATE_ERROR_MAX_CHARS])

    # Gate 2: ruff format --check spacegame/ tests/
    gate_name = "ruff-format"
    try:
        result = _run([sys.executable, "-m", "ruff", "format", "--check", "spacegame/", "tests/"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (gate_name, f"{type(exc).__name__}: {exc}"[:_GATE_ERROR_MAX_CHARS])
    if result.returncode != 0:
        return (gate_name, (result.stdout + result.stderr)[:_GATE_ERROR_MAX_CHARS])

    # Gate 3: mypy spacegame/ | filter ": note:" lines | mypy_baseline filter
    # Chained in Python (no shell=True) for Windows portability — grep isn't
    # native on Windows and shell syntax differs from bash.
    gate_name = "mypy"
    try:
        mypy_result = _run([sys.executable, "-m", "mypy", "spacegame/"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (gate_name, f"{type(exc).__name__}: {exc}"[:_GATE_ERROR_MAX_CHARS])

    filtered_output = "\n".join(
        line for line in mypy_result.stdout.splitlines() if ": note:" not in line
    )

    try:
        filter_result = _run(
            [sys.executable, "-m", "mypy_baseline", "filter"],
            input=filtered_output,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (gate_name, f"{type(exc).__name__}: {exc}"[:_GATE_ERROR_MAX_CHARS])
    if filter_result.returncode != 0:
        return (gate_name, (filter_result.stdout + filter_result.stderr)[:_GATE_ERROR_MAX_CHARS])

    # Gate 4: mypy tools/crawler/ at zero tolerance (no baseline).
    # The play harness was born with 0 errors under the QF arc; gate it from
    # day one so it cannot accumulate debt the way spacegame/ did.
    # --follow-imports=silent stops spacegame/'s 768 baselined errors from
    # leaking in through the crawler's imports. Legacy tools/ scripts stay out
    # of scope: build-time utilities, not shipped code.
    gate_name = "mypy-crawler"
    try:
        crawler_result = _run(
            [sys.executable, "-m", "mypy", "tools/crawler/", "--follow-imports=silent"]
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (gate_name, f"{type(exc).__name__}: {exc}"[:_GATE_ERROR_MAX_CHARS])
    if crawler_result.returncode != 0:
        return (gate_name, (crawler_result.stdout + crawler_result.stderr)[:_GATE_ERROR_MAX_CHARS])

    return None


def _filter_harness_managed_dirty(porcelain_text: str) -> tuple[str, list[str]]:
    """Strip git-status-porcelain lines whose paths are harness-managed.

    The harness creates and removes runtime artifacts (lock file, state,
    logs, probe files, STOP) as part of its normal lifecycle. Their
    presence or absence in git status should never block a sprint. This
    helper separates them from real working-tree changes.

    Returns (filtered_porcelain, removed_paths). Empty filtered_porcelain
    means the only dirty entries were harness-internal — the working tree
    is effectively clean from the operator's perspective.
    """
    kept_lines: list[str] = []
    removed_paths: list[str] = []
    for line in porcelain_text.splitlines():
        if not line:
            continue
        if len(line) < 4:
            kept_lines.append(line)
            continue
        # Porcelain format: "XY <path>" or "XY <old> -> <new>" for renames.
        path_part = line[3:]
        first_path = path_part.split(" -> ", 1)[0].strip().strip('"')
        is_managed = first_path in _HARNESS_MANAGED_RUNTIME_FILES or any(
            first_path.startswith(p) for p in _HARNESS_MANAGED_RUNTIME_PREFIXES
        )
        if is_managed:
            removed_paths.append(first_path)
        else:
            kept_lines.append(line)
    return "\n".join(kept_lines), removed_paths


def _sweep_tmp_orphans(
    porcelain_text: str = "",
    *,
    root: Path = PROJECT_ROOT,
    min_age_seconds: float = TMP_ORPHAN_MIN_AGE_SECONDS,
) -> tuple[str, list[str]]:
    """Delete `.tmp` siblings stranded by a hard kill mid-`atomic_write`.

    The second layer of the orphan defence. `_filter_harness_managed_dirty`
    makes a stranded `.tmp` invisible to the clean-tree check for every
    destination in `_ATOMIC_WRITE_TARGETS`; this one deletes the file so the
    orphan cannot accumulate, cannot brick anything, and -- crucially -- so
    that a *future* `atomic_write` destination nobody registered still cannot
    fail a launch. Anything git reports as untracked with a `.tmp` suffix is
    swept, registered or not.

    Only orphans older than *min_age_seconds* are removed: preflight runs
    before the lock is acquired, so a concurrent instance could be mid-write,
    and deleting its temp file would break its `os.replace`. A fresh orphan is
    left to the filter layer and swept by the next launch.

    Args:
        porcelain_text: `git status --porcelain` output, when available. Its
            untracked `.tmp` entries are swept in addition to the registered
            destinations, and the lines for files actually deleted are
            stripped from the returned text.
        root: Repository root (injectable for tests).
        min_age_seconds: Minimum age before an orphan is considered stranded
            rather than in flight.

    Returns:
        (porcelain_text with swept lines removed, repo-relative paths swept).
    """
    candidates: dict[str, str] = {}  # relative path -> porcelain line ("" if none)
    for target in _ATOMIC_WRITE_TARGETS:
        candidates.setdefault(f"{target}{ATOMIC_WRITE_TMP_SUFFIX}", "")

    for line in porcelain_text.splitlines():
        if not line.startswith("??") or len(line) < 4:
            continue
        rel = line[3:].split(" -> ", 1)[0].strip().strip('"')
        if rel.endswith(ATOMIC_WRITE_TMP_SUFFIX):
            candidates[rel] = line

    now = time.time()
    swept: list[str] = []
    swept_lines: set[str] = set()
    for rel, line in candidates.items():
        path = root / rel
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue  # absent, or unreadable -- nothing to sweep
        if age < min_age_seconds:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        swept.append(rel)
        if line:
            swept_lines.add(line)

    if swept_lines:
        remaining = [ln for ln in porcelain_text.splitlines() if ln not in swept_lines]
        porcelain_text = "\n".join(remaining)
    return porcelain_text, swept


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


def _preflight_checks(allow_dirty: bool, push_enabled: bool, probe_writes: bool) -> int:
    """Verify environment before starting the loop. Returns 0 on success,
    non-zero exit code on failure. Each check fails fast with a clear message.
    """
    # 0. Sweep `.tmp` orphans stranded by a hard kill mid-`atomic_write`
    # (see `_sweep_tmp_orphans`). Runs first, because an orphan of a
    # non-gitignored destination -- ROADMAP.md above all -- is what fails
    # check 4 below and bricks every subsequent launch.
    _, swept = _sweep_tmp_orphans()
    if swept:
        log(f"Swept stranded atomic-write .tmp orphan(s) from a hard kill: {swept}")

    # 1. ROADMAP.md exists.
    if not roadmap_state.roadmap_exists():
        log(f"ROADMAP.md not found at {ROADMAP_PATH}. Aborting.")
        return 4

    # 2. git is on PATH.
    rc, _stdout, _stderr = _run_git(["--version"], timeout=10)
    if rc != 0:
        log(f"git unavailable: {_stderr.strip()}. Aborting.")
        return 4

    # 3. We're in a git repository.
    rc, _stdout, _stderr = _run_git(["rev-parse", "--is-inside-work-tree"], timeout=10)
    if rc != 0 or _stdout.strip() != "true":
        log(f"Not in a git repo at {PROJECT_ROOT}. Aborting.")
        return 4

    # 4. Working tree clean (unless overridden).
    if REQUIRE_CLEAN_WORKING_TREE and not allow_dirty:
        rc, stdout, _stderr = _run_git(["status", "--porcelain"], timeout=15)
        if rc != 0:
            log("git status failed. Aborting.")
            return 4
        # Sweep again with git's own view: this catches a stranded `.tmp`
        # for an `atomic_write` destination that is not in the registry --
        # the failure mode that cannot be fixed by adding one more entry.
        stdout, swept = _sweep_tmp_orphans(stdout)
        if swept:
            log(f"Swept stranded .tmp orphan(s) reported as untracked: {swept}")

        # Filter out harness-managed runtime artifacts (lock file, state,
        # logs, probe files, STOP) and the `.tmp` siblings of every
        # atomic-write destination. The harness owns those paths and their
        # presence/absence is normal lifecycle, not a project-state concern.
        # Without this, a leaked-tracked-artifact (e.g., .running once got
        # accidentally committed) bricks the pre-flight permanently.
        filtered, removed = _filter_harness_managed_dirty(stdout)
        if removed:
            log(f"Note: ignoring harness-managed dirty entries: {removed}")
        if filtered.strip():
            log(
                "Working tree is dirty. Agents will commit during phases; "
                "mixing in unrelated changes pollutes sprint history. "
                "Commit or stash, OR pass --allow-dirty to override."
            )
            log(f"Dirty files:\n{filtered}")
            return 4

    # 5. On a branch (not detached HEAD) — required for push.
    if push_enabled:
        rc, stdout, _stderr = _run_git(["symbolic-ref", "--short", "HEAD"], timeout=10)
        if rc != 0:
            log(
                "Detached HEAD detected. Push needs a branch. "
                "Either checkout a branch or pass --no-push."
            )
            return 4

        # 6. Origin remote configured.
        rc, _stdout, _stderr = _run_git(["remote", "get-url", "origin"], timeout=10)
        if rc != 0:
            log("No 'origin' remote configured. Either add origin or pass --no-push.")
            return 4

    # 7. Claude CLI available (best-effort).
    from ralph.config import CLAUDE_CMD

    if not DRY_RUN:
        try:
            # Same reasoning as the agency probe below: the claude CLI is the
            # one pre-flight subprocess that can leave grandchildren holding
            # the stdout pipe, and pre-flight runs before the heartbeat exists.
            result = run_with_hard_timeout(
                [CLAUDE_CMD[0], "--version"],
                timeout_seconds=10,
                cwd=str(PROJECT_ROOT),
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
            return 4
        except subprocess.TimeoutExpired:
            log(
                "Claude CLI did not respond to --version within 10s. "
                "The harness will still attempt invocation."
            )

    # 8. Claude has agency (item 2 + agency upgrade): WRITE is required,
    # TASK + WEBFETCH are tracked as warnings. Catches sandbox/permission
    # failures and missing tools before any sprint time is wasted.
    if probe_writes and not DRY_RUN:
        ok, reason = _probe_claude_write_permission()
        if not ok:
            log(f"Agency probe FAILED: {reason}")
            log(
                "Aborting. The harness cannot drive agents that can't persist "
                "files. To skip this check (e.g., known-good environment), "
                "pass --skip-agency-probe."
            )
            return 4
        log(f"Agency probe passed: {reason}")

    log("Pre-flight checks passed.")
    return 0


# ---------------------------------------------------------------------------
# Claude agency probe (item 2 + agency upgrade)
# ---------------------------------------------------------------------------
#
# Verifies the agent has the three capabilities the harness depends on:
#   1. WRITE — can persist file edits inside PROJECT_ROOT (in `claude -p`
#      mode, this fails silently without `--dangerously-skip-permissions`).
#   2. TASK — can spawn subagents for parallel research / delegation.
#   3. WEBFETCH — can pull external docs (pygame, library APIs).
#
# Single combined probe to keep the startup cost to one claude invocation.
# WRITE failure is a hard abort; TASK/WEBFETCH failures are warnings (the
# harness can still drive work without them, but quality drops).

PROBE_FILENAME = ".agency_probe"
PROBE_TIMEOUT_SECONDS = 240
PROBE_WRITE_TOKEN = "WRITE_OK"
PROBE_TASK_TOKEN = "TASK_OK"
PROBE_WEBFETCH_TOKEN = "WEBFETCH_OK"
# A safe, stable URL for WebFetch verification. example.com is maintained
# by IANA specifically for this kind of programmatic check.
PROBE_WEBFETCH_URL = "https://example.com/"


def _probe_claude_write_permission() -> tuple[bool, str]:
    """Spawn a minimal claude subprocess to verify it has write, Task,
    and WebFetch capabilities.

    Returns (success, reason). Success requires WRITE; missing TASK or
    WEBFETCH downgrades to a warning (logged) but does not fail the probe.

    One real claude invocation. Bounded by PROBE_TIMEOUT_SECONDS.
    """
    from ralph.config import CLAUDE_CMD

    probe_dir = LOGS_DIR.parent  # ralph/
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe_path = probe_dir / PROBE_FILENAME
    log_path = LOGS_DIR / "_agency_probe.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Clean any stale probe file from a prior run.
    try:
        if probe_path.exists():
            probe_path.unlink()
    except OSError as e:
        return False, f"could not remove stale probe file at {probe_path}: {e}"

    rel_probe_path = probe_path.relative_to(PROJECT_ROOT).as_posix()
    prompt = (
        f"This is a startup smoke test for the ralph harness. Verify three "
        f"agent capabilities and write the result to `{rel_probe_path}`.\n\n"
        f"Step 1 (WRITE): Use the Write tool to create the file "
        f"`{rel_probe_path}` containing the single line `{PROBE_WRITE_TOKEN}`.\n\n"
        f"Step 2 (TASK): Use the Task tool to spawn one Explore subagent "
        f"with prompt 'glob *.md in this directory and report the count'. "
        f"If the Task tool succeeds (whatever the subagent returns), use the "
        f"Edit tool to append a new line `{PROBE_TASK_TOKEN}` to "
        f"`{rel_probe_path}`. If the Task tool errors or is unavailable, "
        f"append a line `TASK_FAIL: <error>` instead.\n\n"
        f"Step 3 (WEBFETCH): Use the WebFetch tool on the URL "
        f"`{PROBE_WEBFETCH_URL}` with the prompt 'is this page reachable'. "
        f"If WebFetch returns content, append `{PROBE_WEBFETCH_TOKEN}` to "
        f"`{rel_probe_path}`. If WebFetch errors or is unavailable, append "
        f"`WEBFETCH_FAIL: <error>` instead.\n\n"
        f"Reply with 'done' when all three steps are attempted."
    )
    cmd = [*list(CLAUDE_CMD), prompt]

    log(f"Running agency probe (writes {rel_probe_path}, ~60-240s)...")
    try:
        with log_path.open("w", encoding="utf-8") as f:
            f.write(f"# Agency probe\n# Started: {datetime.now().isoformat()}\n")
            f.write(f"# Command: {cmd[0]} {' '.join(cmd[1:-1])} <prompt>\n")
            f.write(f"# Probe file: {rel_probe_path}\n")
            f.write(f"# Timeout: {PROBE_TIMEOUT_SECONDS}s\n\n")
            f.write(f"--- PROMPT ---\n{prompt}\n--- END PROMPT ---\n\n")
            f.write("--- AGENT OUTPUT ---\n")
            f.flush()

            try:
                # `run_with_hard_timeout`, NOT `subprocess.run(timeout=...)`.
                # This is the one pre-flight call that runs an agentic CLI, and
                # the prompt explicitly asks it to spawn a Task subagent and a
                # WebFetch -- i.e. grandchildren. `subprocess.run(timeout=)`
                # kills only the direct child and then blocks in
                # `communicate()` for as long as any grandchild holds the
                # stdout pipe: the measured 8.5-hour hang this whole module
                # exists because of. Worse, this call happens BEFORE the
                # heartbeat thread starts, so a hang here produces a harness
                # the supervisor has no beat to judge -- total silence, with
                # no rescue. `run_with_hard_timeout` kills the whole tree with
                # `taskkill /F /T` and never re-reads the pipe afterwards.
                result = run_with_hard_timeout(
                    cmd,
                    timeout_seconds=PROBE_TIMEOUT_SECONDS,
                    cwd=str(PROJECT_ROOT),
                )
            except FileNotFoundError as e:
                f.write(f"\n--- claude CLI not found: {e} ---\n")
                return False, f"claude CLI not found on PATH: {e}"
            except subprocess.TimeoutExpired:
                f.write(f"\n--- TIMEOUT after {PROBE_TIMEOUT_SECONDS}s ---\n")
                return False, (
                    f"probe timed out after {PROBE_TIMEOUT_SECONDS}s. "
                    f"The agent did not respond — check {log_path}."
                )

            f.write(result.stdout)
            if result.stderr:
                f.write(f"\n--- STDERR ---\n{result.stderr}\n")
            f.write(f"\n--- END (returncode {result.returncode}) ---\n")

        # Verify WRITE happened. Hard requirement.
        if not probe_path.exists():
            return False, (
                f"probe file {rel_probe_path} was not created. The agent "
                f"likely hit a sandbox/permission denial. Check {log_path} "
                f"for the agent's response. Common cause: missing "
                f"`--dangerously-skip-permissions` in CLAUDE_CMD (config.py)."
            )
        try:
            content = probe_path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"probe file at {rel_probe_path} unreadable: {e}"
        # Normalize for token detection.
        content_stripped = content.strip()
        has_write = PROBE_WRITE_TOKEN in content_stripped
        has_task = PROBE_TASK_TOKEN in content_stripped
        has_webfetch = PROBE_WEBFETCH_TOKEN in content_stripped

        if not has_write:
            return False, (
                f"probe file at {rel_probe_path} exists but missing "
                f"{PROBE_WRITE_TOKEN!r} marker. Agent wrote a file but "
                f"didn't follow the prompt — check {log_path}."
            )

        # WRITE is good. TASK / WEBFETCH are non-fatal; warn if missing.
        warnings: list[str] = []
        if not has_task:
            warnings.append(
                "Task tool unavailable or failed — agents won't be able to "
                "spawn research subagents. Check claude CLI install."
            )
        if not has_webfetch:
            warnings.append(
                "WebFetch unavailable or failed — agents can't pull external "
                "docs. Sandboxed/offline environments make this expected; "
                "otherwise check claude CLI install or network access."
            )

        # Clean up the probe file. Best-effort.
        try:
            probe_path.unlink()
        except OSError:
            pass

        for w in warnings:
            log(f"Agency probe WARNING: {w}")

        if warnings:
            return True, "WRITE ok; degraded agency: " + " | ".join(warnings)
        return True, "WRITE + TASK + WEBFETCH all ok"
    except OSError as e:
        return False, f"could not run agency probe: {e}"


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


def _commit_harness_bookkeeping(sprint_id: str, summary: str) -> bool:
    """Commit any pending harness-authored ROADMAP.md (and STATUS.md) changes.

    The harness writes to ROADMAP.md at phase transitions (status updates,
    activity-log entries, index regeneration). When those writes happen
    AFTER the last agent commit of a sprint, they otherwise sit
    uncommitted and pollute the working tree of the next sprint. This
    commits them with a `ralph(harness)` prefix so they're distinguishable
    from agent commits.

    STATUS.md rides along here too, on purpose: it is only visible from a
    phone once it is committed and pushed, and this is the commit/push path
    the harness already uses -- Task 8 deliberately does not invent a
    second mechanism. STATUS.md is staged only if it already exists on disk
    (i.e. `status.write_status` has succeeded at least once): `git add` on a
    pathspec matching nothing exits non-zero, which would otherwise sink an
    unrelated, legitimate ROADMAP.md commit on the very first run before
    STATUS.md has ever been written.

    Best-effort: returns True if a commit was made, False if there was
    nothing to commit or the operation failed (logged on failure, never
    raised).
    """
    paths = [ROADMAP_PATH.relative_to(PROJECT_ROOT).as_posix()]
    if status.STATUS_PATH.exists():
        paths.append(status.STATUS_PATH.relative_to(PROJECT_ROOT).as_posix())

    rc, porcelain, _stderr = _run_git(["status", "--porcelain", "--", *paths], timeout=10)
    if rc != 0:
        log(f"{sprint_id}: harness bookkeeping git status failed; skipping commit")
        return False
    if not porcelain.strip():
        return False  # nothing to commit

    rc, _stdout, stderr = _run_git(["add", "--", *paths], timeout=10)
    if rc != 0:
        log(f"{sprint_id}: harness bookkeeping git add failed: {stderr.strip()}")
        return False

    full_msg = f"ralph(harness): {sprint_id} -- {summary}"
    rc, _stdout, stderr = _run_git(["commit", "-m", full_msg], timeout=30)
    if rc != 0:
        log(f"{sprint_id}: harness bookkeeping commit failed: {stderr.strip()}")
        return False

    log(f"{sprint_id}: committed harness bookkeeping ({summary})")
    return True


def _write_status_snapshot(
    sprint_id: str,
    recent_outcomes: list[str],
    exit_reason: Optional[str] = None,
    crash_info: Optional[status.CrashInfo] = None,
    gate_failure: Optional[str] = None,
    infra_failure: Optional[str] = None,
) -> None:
    """Write STATUS.md so progress is visible from a phone.

    Best-effort: any failure here -- a roadmap-parsing bug, a rendering bug,
    a disk error -- is logged and swallowed. STATUS.md is the operator's only
    window into a week-long unattended run; a bug in producing it must never
    be allowed to end the run it is trying to report on, and must never
    replace a real error already propagating with a confusing secondary one.

    `blocks_disagreements` is a cross-check on the `Blocks:` field, reported
    here so it resurfaces without a human remembering to run a command. It
    never influences `sprints_now` or which sprint gets picked -- reporting
    only.

    Args:
        sprint_id: Used only in the log line if this write fails.
        recent_outcomes: Trimmed to the last 5 here, at write time.
        exit_reason: Set when the harness declined to run at all (a forced-
            sprint validation failure, a baseline-capture failure).
        crash_info: Set when an unhandled exception escaped the main loop.
        gate_failure: Set when the per-sprint test gate found a red tree. The
            operator must be able to see that from GitHub -- a gate whose
            failure only reaches a discarded stdout is not a gate.
        infra_failure: Set when consecutive sprints failed with INFRA_ERROR and
            the run stopped. Partially visible before (`recent_outcomes`
            rendered "SA-2 infra_error") but nothing said the run had given
            up, or why.
    """
    try:
        sprints_now = roadmap_state.parse_sprints()
        status.write_status(
            triage.analyse(sprints_now),
            heartbeat.read_heartbeat(),
            recent_outcomes[-5:],
            disagreements=triage.blocks_disagreements(sprints_now),
            crash=crash_info,
            decline_reason=exit_reason,
            gate_failure=gate_failure,
            infra_failure=infra_failure,
        )
    except Exception as e:
        log(f"{sprint_id}: STATUS.md write failed: {e}")


def _reconcile_stale_state(state: "HarnessState") -> int:
    """Clear stale `last_outcome` entries from state.json.

    When a sprint failed in a prior run (state recorded `last_outcome=error`
    or similar), but the operator has since reset its ROADMAP status back
    to `todo` (e.g., via a recovery commit, or by hand), the state entry
    becomes misleading: it suggests the sprint is in trouble when it's
    actually fresh.

    For each sprint whose ROADMAP status is `todo` but whose state shows
    a non-OK last_outcome, clear the outcome and last_phase fields. The
    iteration counters (plan_runs, implement_runs, review_runs) are
    preserved as historical signal.

    Returns the number of entries reconciled.
    """
    sprints = roadmap_state.parse_sprints()
    reconciled = 0
    for sprint_id, sprint in sprints.items():
        if not sprint.is_todo():
            continue
        sprint_state = state.sprints.get(sprint_id)
        if sprint_state is None:
            continue
        if sprint_state.last_outcome in (None, "ok", ""):
            continue
        log(
            f"Reconciling stale state for {sprint_id}: ROADMAP shows todo but "
            f"state.last_outcome={sprint_state.last_outcome!r}. Clearing outcome."
        )
        sprint_state.last_outcome = None
        sprint_state.last_phase = None
        reconciled += 1
    if reconciled:
        state.save()
    return reconciled


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
            rc, stdout, _stderr = _run_git(["log", "--oneline", f"--since={since_arg}"], timeout=10)
            if rc == 0:
                # Filter for commits referencing this sprint ID.
                relevant = [line for line in stdout.splitlines() if sprint_id in line]
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
    atomic_write(summary_path, "\n".join(body))


def _sync_roadmap_index(sprint_id: str) -> None:
    """Sync Status cells in non-auto-generated ROADMAP.md index tables.

    regenerate_index() only rebuilds the SA-arc table (it works between the
    AUTO_GENERATED_SA_INDEX markers). The Followups and QF tables are
    hand-maintained and drift the moment a status changes. This helper syncs
    the Status cells of every other table too, writing atomically.

    Failure here is non-fatal and logged; the harness continues.
    """
    try:
        from scripts.sync_roadmap_index import ROADMAP_PATH as _RM
        from scripts.sync_roadmap_index import sync as _sync_index

        _text = _RM.read_text(encoding="utf-8")
        _new, _drift = _sync_index(_text)
        if _drift:
            atomic_write(_RM, _new)
            log(f"{sprint_id}: synced {len(_drift)} index row(s)")
    except Exception as e:
        log(f"{sprint_id}: index sync failed: {e}")


def _push_after_sprint(sprint_id: str, outcome: Outcome, push_enabled: bool) -> None:
    """Push current branch to origin after sprint completion.

    Pushes on terminal outcomes (OK, BLOCKED, NEEDS_REWORK). Skips
    TIMEOUT and ERROR because state may be inconsistent. Push failures
    are logged but don't crash the harness — a network blip shouldn't
    stop the loop — and are recorded via `status.record_push` so the next
    STATUS.md render can say the board is frozen.
    """
    if not push_enabled:
        return
    if outcome not in (Outcome.OK, Outcome.BLOCKED, Outcome.NEEDS_REWORK):
        log(f"{sprint_id}: skipping push (outcome={outcome.value} may be inconsistent)")
        return

    rc, stdout, stderr = _run_git(["push", "origin", "HEAD"], timeout=PUSH_TIMEOUT_SECONDS)
    detail = stderr.strip() or stdout.strip()
    if rc == 0:
        log(f"{sprint_id}: pushed to origin")
    else:
        log(f"{sprint_id}: push failed (rc={rc}): {detail}")

    # Record the outcome where the operator can see it. `log()` goes to a
    # stdout the Scheduled Task discards, so without this a push that starts
    # failing -- one push to `master` from anywhere else makes every later
    # `git push origin HEAD` a non-fast-forward, and the harness never pulls --
    # freezes the GitHub copy of STATUS.md while the harness looks healthy, and
    # says so in no channel at all.
    try:
        status.record_push(rc == 0, detail=f"rc={rc}: {detail}" if rc != 0 else "")
    except OSError as exc:
        log(f"{sprint_id}: could not record push state: {exc}")


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
    p.add_argument(
        "--skip-agency-probe",
        "--skip-write-probe",
        action="store_true",
        dest="skip_agency_probe",
        help=(
            "Don't run the Claude agency probe at startup. The probe is a "
            "tiny smoke-test that verifies WRITE / Task / WebFetch are "
            "available before sprint time is wasted. Skip only when you're "
            "sure the environment is good (e.g., immediately after a "
            "successful probe, or in dry-run). The legacy "
            "--skip-write-probe alias is preserved."
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        from ralph import config as _cfg

        _cfg.DRY_RUN = True

    push_enabled = not args.no_push and PUSH_ON_SPRINT_COMPLETE

    # Pre-flight checks (item F). Fail fast.
    rc = _preflight_checks(
        allow_dirty=args.allow_dirty,
        push_enabled=push_enabled,
        probe_writes=not args.skip_agency_probe,
    )
    if rc != 0:
        return rc

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Lock — refuse concurrent runs (paranoia / safety).
    if not _acquire_lock():
        return 2

    # Heartbeat (Task 5): started only once pre-flight has passed AND the lock
    # is held, and stopped on every exit path below. A stale or absent
    # heartbeat then always means "something is wrong" -- never "the harness
    # hasn't decided whether to run yet."
    #
    # AFTER the lock, not before (M3): `heartbeat._loop` beats immediately,
    # before its first `stop.wait()`, so starting it first meant an instance
    # that correctly LOST the lock race stamped heartbeat.json with its own
    # PID -- dead moments later -- and then exited rc 2. For up to 30s (until
    # the real harness's next beat) `supervisor.heartbeat_pid_alive()` then
    # read "no live run" while a healthy harness was working, so the
    # supervisor would double-launch, the new instance would lose the lock,
    # and each such rc 2 burns a strike off the 3-failure budget.
    heartbeat_stop = heartbeat.start_heartbeat_thread(lambda: _current_context)

    # Declared before `try` (not at first use inside it) so `finally` can
    # always reference them, no matter how early an exception strikes --
    # otherwise a crash before, say, `recent_outcomes` was normally assigned
    # would raise NameError out of `finally` itself, which would replace the
    # real error rather than report it (Task 8 review round 2, Finding 1).
    recent_outcomes: list[str] = []
    crashed_sprint_id: Optional[str] = None
    exit_reason: Optional[str] = None
    crash_info: Optional[status.CrashInfo] = None
    gate_failure: Optional[str] = None
    infra_failure: Optional[str] = None
    infra_streak = 0
    _consume_red_tree()  # a previous in-process run must not leak into this one

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
                # Commit the recovery edits so they don't drift into
                # the first agent's working tree.
                try:
                    _commit_harness_bookkeeping(
                        "recovery",
                        f"reset {recovered} stuck sprint(s) to todo",
                    )
                except Exception as e:
                    log(f"recovery: harness bookkeeping commit failed: {e}")
            reconciled = _reconcile_stale_state(state)
            if reconciled:
                log(
                    f"Reconciled {reconciled} stale state entry/entries (todo in ROADMAP, error in state)."
                )

        # Test baseline (item L). Captured once at startup; refreshed
        # after every successful sprint so the baseline tracks the
        # growing test count.
        test_baseline = (0, 0)
        if not args.dry_run and not DRY_RUN and not args.skip_baseline:
            log("Capturing test-suite baseline (this can take a minute)...")
            try:
                test_baseline = _capture_test_baseline()
            except BaselineCaptureError as exc:
                exit_reason = (
                    f"Baseline capture FAILED: {exc}. "
                    "Aborting run to avoid running agents with no baseline."
                )
                log(exit_reason)
                return 3
            log(f"Baseline: {test_baseline[0]} passing, {test_baseline[1]} skipped.")

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
                    exit_reason = f"Forced sprint {args.sprint} not found. Aborting."
                    log(exit_reason)
                    return 2
                if not target.is_todo():
                    exit_reason = (
                        f"Forced sprint {args.sprint} status={target.status!r}, not todo. Aborting."
                    )
                    log(exit_reason)
                    return 2
                unmet = [
                    d for d in target.depends_on if not sprints.get(d) or not sprints[d].is_done()
                ]
                if unmet:
                    exit_reason = (
                        f"Forced sprint {args.sprint} has unmet dependencies: {unmet}. Aborting."
                    )
                    log(exit_reason)
                    return 2
                picked = target
                args.sprint = None
            else:
                eligible = roadmap_state.eligible_sprints(sprints)
                if not eligible:
                    queue = triage.analyse(sprints)
                    if queue.is_starved:
                        log(triage.starvation_report(queue))
                        log("STARVED -- exiting. This is NOT completion.")
                    else:
                        log("No eligible sprints; all work complete. Exiting cleanly.")
                    break
                picked = eligible[0]

            log(f"Picking up sprint {picked.sprint_id}: {picked.title}")
            # Set right before, cleared right after: if execute_sprint raises,
            # this stays pointed at the sprint that was in flight when it
            # died, for the CRASHED banner (Task 8 review round 2).
            crashed_sprint_id = picked.sprint_id
            outcome = execute_sprint(picked.sprint_id, state, test_baseline=test_baseline)
            crashed_sprint_id = None
            sprints_processed += 1
            state.total_sprints_processed += 1
            state.save()
            log(f"Sprint {picked.sprint_id} finished with outcome={outcome.value}")
            recent_outcomes.append(f"{picked.sprint_id} {outcome.value}")

            # A red tree ends the run. Continuing would author the next sprint
            # on top of a broken one, and the loop allows up to 10 per
            # invocation. Recorded before the STATUS.md write below so the
            # reason reaches GitHub with the same commit.
            gate_failure = _consume_red_tree()
            if gate_failure is not None:
                recent_outcomes.append(f"{picked.sprint_id} TEST-GATE FAILED")
                log(f"Stopping the run: {gate_failure}")

            # Infrastructure down (H4). INFRA_ERROR means the agent never
            # meaningfully executed -- expired token, API outage, sustained
            # rate limit -- and `_mark_terminal_outcome` resets the sprint to
            # `todo`, so the loop would otherwise re-pick it immediately and
            # keep doing so for every one of `--max-sprints` sprints, then
            # exit 0. Exiting 0 is what let the supervisor call it a success,
            # reset its failure counter, and relaunch 30 seconds later for as
            # long as the outage lasted.
            infra_streak = infra_streak + 1 if outcome == Outcome.INFRA_ERROR else 0
            if infra_streak >= MAX_CONSECUTIVE_INFRA_SPRINTS:
                infra_failure = (
                    f"{infra_streak} consecutive sprints failed with infra_error "
                    f"(most recently {picked.sprint_id}). The agent CLI, the network "
                    "or the auth token is down; no sprint can succeed until it is "
                    "back. Stopping this run and reporting failure so the supervisor "
                    "backs off instead of relaunching every 30 seconds."
                )
                log(infra_failure)
                recent_outcomes.append(f"{picked.sprint_id} INFRA-STOP")

            # Refresh baseline after a successful sprint (item L).
            # Mid-run failure keeps the previous baseline rather than aborting —
            # agents already running can still compare against the last-known-good count.
            if (
                outcome == Outcome.OK
                and not args.dry_run
                and not DRY_RUN
                and not args.skip_baseline
            ):
                try:
                    new_baseline = _capture_test_baseline()
                    log(
                        f"Refreshed baseline: {new_baseline[0]} passing "
                        f"(was {test_baseline[0]}), {new_baseline[1]} skipped."
                    )
                    test_baseline = new_baseline
                except BaselineCaptureError as exc:
                    # Keep going (agents can still compare against the last
                    # known-good count) but do not let it be swallowed: this
                    # used to be a log line to a stdout the Scheduled Task
                    # discards. `## Recent` in STATUS.md is pushed.
                    log(
                        f"Mid-run baseline refresh FAILED: {exc}. "
                        f"Keeping previous baseline ({test_baseline[0]}p/{test_baseline[1]}s)."
                    )
                    recent_outcomes.append(f"{picked.sprint_id} baseline-refresh FAILED ({exc})")

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

            # Sync Status cells in hand-maintained index tables (item J).
            _sync_roadmap_index(picked.sprint_id)

            # STATUS.md (Task 8) -- the operator's only window into the run
            # while away. Written before the bookkeeping commit below so it
            # rides along with it.
            _write_status_snapshot(
                picked.sprint_id,
                recent_outcomes,
                gate_failure=gate_failure,
                infra_failure=infra_failure,
            )

            # Commit harness bookkeeping (terminal status + index regen).
            # Captures the post-agent ROADMAP edits the harness writes
            # inline. Without this, those edits drift into the next
            # sprint's working tree and trip the dirty-tree pre-flight.
            try:
                _commit_harness_bookkeeping(
                    picked.sprint_id,
                    f"finalize sprint (outcome={outcome.value})",
                )
            except Exception as e:
                log(f"{picked.sprint_id}: harness bookkeeping commit failed: {e}")

            # Auto-push (item A) after sprint completion.
            _push_after_sprint(picked.sprint_id, outcome, push_enabled)

            if gate_failure is not None or infra_failure is not None:
                break

            if should_stop():
                consume_stop_file()
                break

            time.sleep(INTER_SPRINT_SLEEP)

        log(f"Harness done. Sprints processed this run: {sprints_processed}.")
        state.save()
        # Non-zero when the run accomplished nothing because the infrastructure
        # was down, so the supervisor records a failure rather than a success.
        return HARNESS_RC_INFRA_ERROR if infra_failure is not None else 0
    except Exception as exc:
        # A crash must be legible as a crash: right now, without this, the
        # operator cannot tell "exited cleanly with nothing to do" from
        # "died on an unhandled exception" -- both would otherwise render
        # the same calm queue summary in STATUS.md. Captured here (not in
        # `finally`) because heartbeat.read_heartbeat() must be read while
        # the heartbeat thread is still running, and because
        # execute_sprint's own try/finally already reset _current_context
        # to (None, None) by the time control reaches this frame -- the
        # heartbeat FILE (written on its own timer) still holds the last
        # live sprint/phase, unlike that synchronous in-process variable.
        beat = heartbeat.read_heartbeat()
        phase = None
        if beat is not None and beat.get("sprint") == crashed_sprint_id:
            beat_phase = beat.get("phase")
            phase = beat_phase if isinstance(beat_phase, str) else None
        crash_info = status.CrashInfo(
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            sprint=crashed_sprint_id,
            phase=phase,
        )
        log(f"harness: UNHANDLED {crash_info.exc_type}: {crash_info.exc_message}")
        raise  # the operator needs the real traceback; STATUS.md is a supplement, not a replacement
    finally:
        # STATUS.md must be written on EVERY exit from this function --
        # clean break, early return (baseline/forced-sprint validation
        # failures), or a propagating exception -- not just after a sprint
        # completes inside the loop. `finally` is the one path Python
        # guarantees runs regardless of how `try` was left, so it belongs
        # here rather than duplicated at each exit site (Task 8 review
        # round 2, Finding 1). `_write_status_snapshot` is internally
        # guarded (see its docstring) and only ever logs on failure, so it
        # cannot itself raise and mask a real error already in flight; the
        # two calls below are wrapped for the same reason.
        _write_status_snapshot(
            "harness-exit",
            recent_outcomes,
            exit_reason=exit_reason,
            crash_info=crash_info,
            gate_failure=gate_failure,
            infra_failure=infra_failure,
        )
        try:
            _commit_harness_bookkeeping("harness-exit", "final status snapshot")
        except Exception as e:
            log(f"harness-exit: harness bookkeeping commit failed: {e}")
        try:
            _push_after_sprint("harness-exit", Outcome.OK, push_enabled)
        except Exception as e:
            log(f"harness-exit: push failed: {e}")
        heartbeat_stop.set()
        _release_lock()


if __name__ == "__main__":
    sys.exit(main())
