"""Ralph loop harness — main loop entry.

Run with `python -m ralph.harness`. See `ralph/README.md` for usage.

Sequential, single-sprint-at-a-time. Three-phase per sprint
(plan → implement → review), with bounded rework cycles between
implement and review. Clean exit via `STOP` file or SIGINT.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ralph import agents, roadmap_state
from ralph.agents import Outcome, Phase, PhaseResult
from ralph.config import (
    DEFAULT_MAX_SPRINTS_PER_RUN,
    DRY_RUN,
    INTER_SPRINT_SLEEP,
    LOGS_DIR,
    MAX_REWORK_CYCLES,
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


def execute_sprint(sprint_id: str, state: HarnessState) -> Outcome:
    """Run plan → (implement → review) cycles for one sprint.

    Returns the final Outcome (OK, BLOCKED, TIMEOUT, ERROR).
    """
    sprint_state = state.for_sprint(sprint_id)
    sprint_state.started_at = sprint_state.started_at or datetime.now().isoformat()
    sprint_state.last_touched_at = datetime.now().isoformat()

    # ---- Phase 1: Plan ----
    log(f"{sprint_id}: phase=plan starting")
    roadmap_state.update_status(sprint_id, STATUS_PLANNING)
    roadmap_state.append_activity_log(
        sprint_id, "harness: plan phase starting"
    )
    plan_result = agents.run_phase(Phase.PLAN, sprint_id)
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
        impl_result = agents.run_phase(Phase.IMPLEMENT, sprint_id)
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
        review_result = agents.run_phase(Phase.REVIEW, sprint_id)
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
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        # Override config; agents will respect this via env or config import.
        # Easiest path: set the config value directly.
        from ralph import config as _cfg

        _cfg.DRY_RUN = True

    if not roadmap_state.roadmap_exists():
        log(f"ROADMAP.md not found at {ROADMAP_PATH}. Aborting.")
        return 2

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    state = HarnessState.load()
    state.last_run_started_at = datetime.now().isoformat()
    state.save()

    signal.signal(signal.SIGINT, _sigint_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sigint_handler)

    log(f"Harness starting. max_sprints={args.max_sprints} dry_run={DRY_RUN or args.dry_run}")
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
                log(f"Forced sprint {args.sprint} status={target.status!r}, not todo. Aborting.")
                return 2
            # Verify deps.
            unmet = [d for d in target.depends_on if not sprints.get(d) or not sprints[d].is_done()]
            if unmet:
                log(
                    f"Forced sprint {args.sprint} has unmet dependencies: {unmet}. Aborting."
                )
                return 2
            picked = target
            args.sprint = None  # Don't loop on the same sprint forever.
        else:
            eligible = roadmap_state.eligible_sprints(sprints)
            if not eligible:
                log("No eligible sprints. Exiting cleanly.")
                break
            picked = eligible[0]

        log(f"Picking up sprint {picked.sprint_id}: {picked.title}")
        outcome = execute_sprint(picked.sprint_id, state)
        sprints_processed += 1
        state.total_sprints_processed += 1
        state.save()
        log(f"Sprint {picked.sprint_id} finished with outcome={outcome.value}")

        if should_stop():
            consume_stop_file()
            break

        time.sleep(INTER_SPRINT_SLEEP)

    log(f"Harness done. Sprints processed this run: {sprints_processed}.")
    state.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
