"""Tests for ralph.harness.

Covers:
  - Stuck-sprint recovery logic
  - Lock acquisition / release
  - State persistence

Mostly we exercise the recovery + lock helpers in isolation rather than the
full main loop (which normally means real subprocess invocations). The one
exception is `TestStatusMdWrittenOnEveryExitPath`: a starved-at-launch run
breaks out of the loop before ever reaching a sprint, and the only way to
prove STATUS.md still gets written on that path is to drive `harness.main()`
for real, with agent/baseline/probe subprocess calls skipped via CLI flags
and `_run_git` faked so nothing touches the real repo.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import MagicMock, patch

import pytest

from ralph import agents, config, harness, roadmap_state, triage
from ralph.agents import Outcome, Phase, PhaseContext, PhaseResult
from ralph.harness import HarnessState, SprintState
from ralph.status import CrashInfo
from ralph.supervisor import should_restart


def _reap(pid: Optional[int]) -> None:
    """Hard-kill *pid* if it is still alive, so a probe test leaves no orphan.

    The fake CLI the agency-probe tests spawn sleeps for 300 seconds. A test
    that failed before the harness killed the tree would otherwise leave that
    tree running for the rest of the suite.
    """
    if pid is None or not harness._pid_alive(pid):
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=30)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


_ROADMAP_WITH_STUCK = """\
# Test

### SA-1 — First sprint

**Status**: in-progress (implementing)
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 14:00 — harness: implement phase starting

### SA-2 — Second sprint

**Status**: todo
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)
"""


@pytest.fixture
def isolated_roadmap(tmp_path, monkeypatch):
    """Point ROADMAP_PATH at a temp file. Reset state.json + lock file + STOP file.

    Patches harness.STOP_FILE and config.STOP_FILE to a per-test tmp path so
    should_stop() never sees a real project-root STOP file. Without this patch,
    running `pytest tests/test_ralph/` while a STOP file is present causes three
    TestExecuteSprintQualityGate tests to fail spuriously (should_stop() returns
    True after the plan phase, short-circuiting execute_sprint before the tests
    can exercise implement/review behaviour).

    harness.py imports STOP_FILE at module level (``from ralph.config import
    STOP_FILE``), so should_stop() reads the module-local binding — patching
    only config.STOP_FILE is not sufficient; both must be patched.
    """
    roadmap_file = tmp_path / "ROADMAP.md"
    roadmap_file.write_text(_ROADMAP_WITH_STUCK, encoding="utf-8")
    monkeypatch.setattr(roadmap_state, "ROADMAP_PATH", roadmap_file)

    state_file = tmp_path / "state.json"
    monkeypatch.setattr(config, "STATE_FILE", state_file)
    monkeypatch.setattr(harness, "STATE_FILE", state_file)

    lock_file = tmp_path / ".running"
    monkeypatch.setattr(config, "LOCK_FILE", lock_file)
    monkeypatch.setattr(harness, "LOCK_FILE", lock_file)

    stop_file = tmp_path / "STOP"
    monkeypatch.setattr(config, "STOP_FILE", stop_file)
    monkeypatch.setattr(harness, "STOP_FILE", stop_file)

    return tmp_path


# ---------------------------------------------------------------------------
# Stuck-sprint recovery (item D)
# ---------------------------------------------------------------------------


class TestStuckSprintRecovery:
    def test_old_in_progress_sprint_resets_to_todo(self, isolated_roadmap) -> None:
        # SA-1 is in-progress. State has it last-touched 2 hours ago (stale).
        state = HarnessState()
        old_ts = (datetime.now() - timedelta(hours=2)).isoformat()
        state.sprints["SA-1"] = SprintState(sprint_id="SA-1", last_touched_at=old_ts)
        recovered = harness._recover_stuck_sprints(state)
        assert recovered == 1
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-1"].status == "todo"

    def test_recent_in_progress_sprint_skipped(self, isolated_roadmap) -> None:
        # SA-1 is in-progress, last touched 5 minutes ago (within stale threshold).
        state = HarnessState()
        recent_ts = (datetime.now() - timedelta(minutes=5)).isoformat()
        state.sprints["SA-1"] = SprintState(sprint_id="SA-1", last_touched_at=recent_ts)
        recovered = harness._recover_stuck_sprints(state)
        assert recovered == 0
        # Still in-progress.
        sprints = roadmap_state.parse_sprints()
        assert "in-progress" in sprints["SA-1"].status

    def test_no_state_treats_as_stale(self, isolated_roadmap) -> None:
        # SA-1 is in-progress but state.json has no record (e.g., state file
        # deleted). Treat as stale and recover.
        state = HarnessState()
        recovered = harness._recover_stuck_sprints(state)
        assert recovered == 1
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-1"].status == "todo"

    def test_todo_sprint_not_recovered(self, isolated_roadmap) -> None:
        state = HarnessState()
        recovered = harness._recover_stuck_sprints(state)
        # SA-2 was already todo; recovery shouldn't touch it.
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "todo"
        # Only SA-1 should have been recovered.
        assert recovered == 1

    def test_review_sprint_is_recovered(self, isolated_roadmap) -> None:
        """M2: `review` was reclaimed by nothing at all.

        `review` is what a STOP honoured after the implement phase leaves
        behind. Recovery matched only `in-progress`, and triage counted it as
        neither todo nor eligible nor blocked -- so a sprint parked there was
        simultaneously invisible to the mechanism that would reclaim it and to
        the accounting that would report it. Forever.
        """
        roadmap = isolated_roadmap / "ROADMAP.md"
        roadmap.write_text(
            _ROADMAP_WITH_STUCK.replace(
                "**Status**: in-progress (implementing)", "**Status**: review"
            ),
            encoding="utf-8",
        )
        assert roadmap_state.parse_sprints()["SA-1"].status == "review", "test setup"

        state = HarnessState()
        recovered = harness._recover_stuck_sprints(state)

        assert recovered == 1, (
            "a sprint parked at `review` with no live run is stuck, and stuck-sprint "
            "recovery is the only thing that ever reclaims it"
        )
        assert roadmap_state.parse_sprints()["SA-1"].status == "todo"

    def test_recent_review_sprint_is_skipped_like_any_other(self, isolated_roadmap) -> None:
        """Recovering `review` must not become a way to steal a live sprint."""
        roadmap = isolated_roadmap / "ROADMAP.md"
        roadmap.write_text(
            _ROADMAP_WITH_STUCK.replace(
                "**Status**: in-progress (implementing)", "**Status**: review"
            ),
            encoding="utf-8",
        )
        state = HarnessState()
        state.sprints["SA-1"] = SprintState(
            sprint_id="SA-1", last_touched_at=datetime.now().isoformat()
        )
        assert harness._recover_stuck_sprints(state) == 0
        assert roadmap_state.parse_sprints()["SA-1"].status == "review"


# ---------------------------------------------------------------------------
# Stale-state reconciliation
# ---------------------------------------------------------------------------


class TestReconcileStaleState:
    def test_clears_error_outcome_when_roadmap_is_todo(self, isolated_roadmap) -> None:
        # SA-2 is todo in ROADMAP. State says it last errored.
        state = HarnessState()
        state.sprints["SA-2"] = SprintState(
            sprint_id="SA-2",
            last_phase="plan",
            last_outcome="error",
        )
        reconciled = harness._reconcile_stale_state(state)
        assert reconciled == 1
        assert state.sprints["SA-2"].last_outcome is None
        assert state.sprints["SA-2"].last_phase is None

    def test_preserves_iteration_counters(self, isolated_roadmap) -> None:
        # Counters are historical signal — keep them even when clearing outcome.
        state = HarnessState()
        state.sprints["SA-2"] = SprintState(
            sprint_id="SA-2",
            plan_runs=2,
            implement_runs=1,
            last_outcome="error",
        )
        harness._reconcile_stale_state(state)
        assert state.sprints["SA-2"].plan_runs == 2
        assert state.sprints["SA-2"].implement_runs == 1

    def test_does_not_touch_ok_outcomes(self, isolated_roadmap) -> None:
        state = HarnessState()
        state.sprints["SA-2"] = SprintState(sprint_id="SA-2", last_outcome="ok")
        reconciled = harness._reconcile_stale_state(state)
        assert reconciled == 0
        assert state.sprints["SA-2"].last_outcome == "ok"

    def test_does_not_touch_in_progress_sprints(self, isolated_roadmap) -> None:
        # SA-1 is in-progress in ROADMAP. Don't reconcile — it's mid-flight.
        state = HarnessState()
        state.sprints["SA-1"] = SprintState(sprint_id="SA-1", last_outcome="error")
        reconciled = harness._reconcile_stale_state(state)
        assert reconciled == 0
        assert state.sprints["SA-1"].last_outcome == "error"

    def test_no_state_entry_no_op(self, isolated_roadmap) -> None:
        # If a sprint has no state entry, nothing to reconcile.
        state = HarnessState()
        reconciled = harness._reconcile_stale_state(state)
        assert reconciled == 0


# ---------------------------------------------------------------------------
# Terminal outcome marking — INFRA_ERROR vs other non-OK outcomes
# ---------------------------------------------------------------------------


class TestMarkTerminalOutcome:
    """`_mark_terminal_outcome` resets INFRA_ERROR sprints to todo for
    re-run; all other non-OK outcomes mark the sprint blocked.
    """

    def test_infra_error_resets_to_todo(self, isolated_roadmap) -> None:
        from ralph.agents import Outcome

        # SA-2 starts as todo; mark it back as a no-op essentially, but
        # the activity log should record the infra-error reason.
        harness._mark_terminal_outcome("SA-2", "plan", Outcome.INFRA_ERROR, "auth 403 from CLI")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "todo"
        # Activity log carries the reason. Read from the patched roadmap
        # path that the isolated_roadmap fixture wired up.
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "infra_error" in content
        assert "re-runnable" in content
        assert "auth 403" in content

    def test_blocked_outcome_marks_blocked(self, isolated_roadmap) -> None:
        from ralph.agents import Outcome

        harness._mark_terminal_outcome("SA-2", "plan", Outcome.BLOCKED, "missing context doc")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"

    def test_error_outcome_marks_blocked(self, isolated_roadmap) -> None:
        from ralph.agents import Outcome

        harness._mark_terminal_outcome("SA-2", "plan", Outcome.ERROR, "no sentinel")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"

    def test_timeout_outcome_marks_blocked(self, isolated_roadmap) -> None:
        from ralph.agents import Outcome

        harness._mark_terminal_outcome("SA-2", "implement", Outcome.TIMEOUT, "phase timed out")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"


# ---------------------------------------------------------------------------
# Phase-report telemetry — item 6
# ---------------------------------------------------------------------------


class TestSafeParsePhaseReport:
    """`_safe_parse_phase_report` is best-effort. Failures don't crash."""

    def test_returns_empty_for_unknown_sprint(self, isolated_roadmap) -> None:
        result = harness._safe_parse_phase_report("NONEXISTENT")
        assert result == {}

    def test_returns_empty_for_sprint_without_report(self, isolated_roadmap) -> None:
        # SA-1 in the fixture has no Last phase report block.
        result = harness._safe_parse_phase_report("SA-1")
        assert result == {}

    def test_extracts_fields_when_report_present(self, isolated_roadmap) -> None:
        # Append a phase report to SA-2's section.

        # Patched ROADMAP_PATH from fixture.
        path = roadmap_state.ROADMAP_PATH
        content = path.read_text(encoding="utf-8")
        content += (
            "\n**Last phase report.**\n"
            "- Phase: review\n"
            "- Outcome: PHASE_OK\n"
            "- Tests_passing: 100\n"
            "- Findings_critical: 0\n"
            "- Single_tighten: Module follows established pattern.\n"
        )
        # Append to the SA-2 section by replacing its end.
        # Simpler: just write it after the existing SA-2 section.
        # The fixture's roadmap has SA-2 as the last sprint so appending
        # to the file places the report in SA-2's section.
        path.write_text(content, encoding="utf-8")

        result = harness._safe_parse_phase_report("SA-2")
        assert result.get("phase") == "review"
        assert result.get("outcome") == "PHASE_OK"
        assert result.get("findings_critical") == "0"
        assert "established pattern" in result.get("single_tighten", "")


class TestSprintStatePhaseReports:
    """SprintState carries per-phase report dicts; HarnessState load
    handles missing fields in older state.json files."""

    def test_default_reports_are_empty_dicts(self) -> None:
        s = SprintState(sprint_id="SA-1")
        assert s.last_plan_report == {}
        assert s.last_implement_report == {}
        assert s.last_review_report == {}

    def test_load_tolerates_missing_report_fields(self, isolated_roadmap, tmp_path) -> None:
        # Old-format state.json without the new fields.
        from ralph import config

        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "sprints": {
                        "SA-1": {
                            "sprint_id": "SA-1",
                            "plan_runs": 1,
                            "last_outcome": "ok",
                        }
                    },
                    "total_sprints_processed": 1,
                }
            ),
            encoding="utf-8",
        )
        with patch.object(harness, "STATE_FILE", state_file):
            with patch.object(config, "STATE_FILE", state_file):
                state = harness.HarnessState.load()
        assert "SA-1" in state.sprints
        assert state.sprints["SA-1"].plan_runs == 1
        # New fields default cleanly.
        assert state.sprints["SA-1"].last_plan_report == {}

    def test_load_tolerates_unknown_keys(self, isolated_roadmap, tmp_path) -> None:
        # Future-format state.json with unknown extra fields.
        from ralph import config

        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "sprints": {
                        "SA-1": {
                            "sprint_id": "SA-1",
                            "plan_runs": 1,
                            "future_field_we_dont_know": "value",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        with patch.object(harness, "STATE_FILE", state_file):
            with patch.object(config, "STATE_FILE", state_file):
                state = harness.HarnessState.load()
        assert "SA-1" in state.sprints
        assert state.sprints["SA-1"].plan_runs == 1
        # Unknown field is silently dropped, not raised.


# ---------------------------------------------------------------------------
# Harness bookkeeping commits
# ---------------------------------------------------------------------------


class TestCommitHarnessBookkeeping:
    """The helper commits ROADMAP.md drift the harness writes after the
    agent's last commit (terminal status, post-sprint index regen, etc).
    """

    def test_no_op_when_roadmap_clean(self, isolated_roadmap) -> None:
        # status --porcelain returns empty string -> nothing to commit.
        with patch.object(harness, "_run_git") as mock_git:
            mock_git.return_value = (0, "", "")
            committed = harness._commit_harness_bookkeeping("SA-1", "test no-op")
            assert committed is False
            # Only `git status` should have been invoked.
            assert mock_git.call_count == 1
            assert mock_git.call_args.args[0][0] == "status"

    def test_commits_when_roadmap_dirty(self, isolated_roadmap) -> None:
        # status --porcelain shows ROADMAP modified -> add + commit.
        responses = [
            (0, " M requirements/roadmap/ROADMAP.md\n", ""),  # status
            (0, "", ""),  # add
            (0, "", ""),  # commit
        ]
        with patch.object(harness, "_run_git", side_effect=responses) as mock_git:
            committed = harness._commit_harness_bookkeeping("SA-1", "finalize sprint")
            assert committed is True
            assert mock_git.call_count == 3
            # Final call: git commit -m with our prefixed message.
            commit_args = mock_git.call_args_list[2].args[0]
            assert commit_args[0] == "commit"
            assert commit_args[1] == "-m"
            assert "ralph(harness)" in commit_args[2]
            assert "SA-1" in commit_args[2]
            assert "finalize sprint" in commit_args[2]

    def test_returns_false_on_status_failure(self, isolated_roadmap) -> None:
        with patch.object(harness, "_run_git") as mock_git:
            mock_git.return_value = (1, "", "git error")
            committed = harness._commit_harness_bookkeeping("SA-1", "test")
            assert committed is False

    def test_returns_false_on_add_failure(self, isolated_roadmap) -> None:
        responses = [
            (0, " M requirements/roadmap/ROADMAP.md\n", ""),  # status
            (1, "", "add failed"),  # add
        ]
        with patch.object(harness, "_run_git", side_effect=responses):
            committed = harness._commit_harness_bookkeeping("SA-1", "test")
            assert committed is False

    def test_returns_false_on_commit_failure(self, isolated_roadmap) -> None:
        responses = [
            (0, " M requirements/roadmap/ROADMAP.md\n", ""),  # status
            (0, "", ""),  # add
            (1, "", "commit failed"),  # commit
        ]
        with patch.object(harness, "_run_git", side_effect=responses):
            committed = harness._commit_harness_bookkeeping("SA-1", "test")
            assert committed is False

    def test_stages_status_md_when_present_on_disk(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """STATUS.md is invisible from a phone unless it rides along with the
        bookkeeping commit that already gets pushed. Task 8's ruling: extend
        the existing commit helper rather than invent a second mechanism.

        `relative_to(PROJECT_ROOT)` requires a real subpath of the project,
        so the scratch file lives under the gitignored `ralph/logs/` rather
        than an unrelated tmp_path.
        """
        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_scratch.md"
        status_file.write_text("# Ralph Status\n", encoding="utf-8")
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)
        try:
            responses = [
                (0, " M requirements/roadmap/ROADMAP.md\n?? STATUS.md\n", ""),  # status
                (0, "", ""),  # add
                (0, "", ""),  # commit
            ]
            with patch.object(harness, "_run_git", side_effect=responses) as mock_git:
                committed = harness._commit_harness_bookkeeping("SA-1", "finalize sprint")
            assert committed is True
            status_call_paths = mock_git.call_args_list[0].args[0]
            add_call_paths = mock_git.call_args_list[1].args[0]
            assert "ralph/logs/_test_status_scratch.md" in status_call_paths
            assert "ralph/logs/_test_status_scratch.md" in add_call_paths
        finally:
            status_file.unlink(missing_ok=True)

    def test_skips_status_md_when_not_yet_written(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Before the first successful write_status() -- e.g. the very first
        harness run ever -- STATUS.md does not exist on disk yet. `git add`
        on a pathspec matching nothing is fatal (exit 128), which would
        otherwise sink the ROADMAP.md commit it rides along with.
        """
        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_scratch_absent.md"
        assert not status_file.exists()  # precondition: nothing was left behind
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)
        responses = [
            (0, " M requirements/roadmap/ROADMAP.md\n", ""),  # status
            (0, "", ""),  # add
            (0, "", ""),  # commit
        ]
        with patch.object(harness, "_run_git", side_effect=responses) as mock_git:
            committed = harness._commit_harness_bookkeeping("SA-1", "finalize sprint")
        assert committed is True
        status_call_paths = mock_git.call_args_list[0].args[0]
        assert "ralph/logs/_test_status_scratch_absent.md" not in status_call_paths


# ---------------------------------------------------------------------------
# STATUS.md sprint-boundary snapshot
# ---------------------------------------------------------------------------


class TestWriteStatusSnapshot:
    """STATUS.md is the operator's only window into a week-long unattended
    run. A bug producing it must degrade to a logged warning, never take
    down the run it is trying to report on.
    """

    def test_writes_using_live_queue_heartbeat_and_recent_outcomes(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict] = []

        def fake_write_status(
            queue: triage.QueueState,
            beat: Optional[dict[str, object]],
            recent: list[str],
            crash_loop: bool = False,
            disagreements: Optional[list[str]] = None,
            crash: Optional[CrashInfo] = None,
            decline_reason: Optional[str] = None,
            gate_failure: Optional[str] = None,
            infra_failure: Optional[str] = None,
        ) -> None:
            calls.append(
                {
                    "queue": queue,
                    "beat": beat,
                    "recent": recent,
                    "disagreements": disagreements,
                    "crash": crash,
                    "decline_reason": decline_reason,
                }
            )

        monkeypatch.setattr(harness.status, "write_status", fake_write_status)
        monkeypatch.setattr(harness.heartbeat, "read_heartbeat", lambda: {"sprint": "SA-1"})

        harness._write_status_snapshot("SA-1", ["SA-0 ok", "SA-1 ok"])

        assert len(calls) == 1
        call = calls[0]
        # isolated_roadmap's fixture roadmap has SA-1 (in-progress) and SA-2
        # (todo, no deps) -- SA-2 is eligible, so this is a healthy queue.
        assert isinstance(call["queue"], triage.QueueState)
        assert call["queue"].total == 2
        assert call["beat"] == {"sprint": "SA-1"}
        assert call["recent"] == ["SA-0 ok", "SA-1 ok"]
        # blocks_disagreements() was actually computed against the live
        # roadmap, not skipped or hardcoded.
        assert call["disagreements"] == []

    def test_only_the_last_five_recent_outcomes_are_kept(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_write_status(
            queue: triage.QueueState,
            beat: Optional[dict[str, object]],
            recent: list[str],
            crash_loop: bool = False,
            disagreements: Optional[list[str]] = None,
            crash: Optional[CrashInfo] = None,
            decline_reason: Optional[str] = None,
            gate_failure: Optional[str] = None,
            infra_failure: Optional[str] = None,
        ) -> None:
            calls.append(recent)

        monkeypatch.setattr(harness.status, "write_status", fake_write_status)
        monkeypatch.setattr(harness.heartbeat, "read_heartbeat", lambda: None)

        long_history = [f"S-{i} ok" for i in range(8)]
        harness._write_status_snapshot("SA-1", long_history)

        assert calls == [long_history[-5:]]

    def test_a_rendering_failure_is_logged_not_raised(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("rendering exploded")

        monkeypatch.setattr(harness.status, "write_status", boom)
        monkeypatch.setattr(harness.heartbeat, "read_heartbeat", lambda: None)

        with patch.object(harness, "log") as mock_log:
            harness._write_status_snapshot("SA-1", [])  # must not raise

        messages = [call.args[0] for call in mock_log.call_args_list]
        assert any("STATUS.md write failed" in m and "rendering exploded" in m for m in messages), (
            f"expected a logged warning naming the failure, got: {messages}"
        )


_STARVED_ROADMAP = """\
# Test Starved Roadmap

### BLOCK-1 — Blocker sprint

**Status**: blocked
**Depends on**: none

**Activity log.**
- 2026-01-01 — todo (created)

### WAIT-1 — Waiting sprint

**Status**: todo
**Depends on**: BLOCK-1

**Activity log.**
- 2026-01-01 — todo (created)
"""


class TestStatusMdWrittenOnEveryExitPath:
    """Finding 1 (Task 8 review round 1): the main loop `break`s out on a
    starved-at-launch (or already-complete) queue BEFORE it ever reaches a
    sprint, and `_write_status_snapshot` was only ever called after a sprint
    finished. That is exactly the vacation scenario STATUS.md exists for:
    the operator leaves, the harness finds nothing eligible, exits, and the
    one file that would have told them so was never created.

    This drives `harness.main()` for real (not just `_write_status_snapshot`
    in isolation) because a mock proves the function was *called*; the
    operator needs the file *written*, and only an end-to-end run proves
    that every break site reaches it, not just the one this test thinks of.
    """

    def test_status_md_exists_and_shows_starved_after_a_starved_at_launch_run(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (isolated_roadmap / "ROADMAP.md").write_text(_STARVED_ROADMAP, encoding="utf-8")

        # The heartbeat thread beats immediately on start; keep it off the
        # real project file rather than writing ralph/heartbeat.json.
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")

        # DRY_RUN short-circuits the real `claude --version` check and the
        # agency probe inside _preflight_checks -- neither is relevant to
        # whether STATUS.md gets written on a starved queue, and both would
        # otherwise spawn real subprocesses.
        monkeypatch.setattr(harness, "DRY_RUN", True)

        # STATUS.md must be a real subpath of PROJECT_ROOT:
        # _commit_harness_bookkeeping does STATUS_PATH.relative_to(PROJECT_ROOT),
        # which raises for an unrelated tmp_path. ralph/logs/ is gitignored
        # scratch space, cleaned up in the finally block below.
        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_e2e_starved.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args and args[0] == "status":
                return (0, " M requirements/roadmap/ROADMAP.md\n?? STATUS.md\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
            ],
        )

        try:
            rc = harness.main()
            assert rc == 0

            assert status_file.exists(), (
                "STATUS.md must exist after a starved-at-launch run -- this is "
                "the exact vacation scenario it exists to report on"
            )
            content = status_file.read_text(encoding="utf-8")
            assert "## STARVED" in content
            # Names the real blocker from the crafted roadmap, not a generic
            # placeholder -- proves this came from a live analyse(), not a
            # stub.
            assert "BLOCK-1" in content
        finally:
            status_file.unlink(missing_ok=True)


class _SimulatedCrash(RuntimeError):
    """A deliberately distinctive exception type/name for crash-banner tests.

    Distinctive on purpose: assertions on its type name and message must not
    accidentally pass because some OTHER section of STATUS.md happens to
    contain the same text (the exact mistake that let round 1's Finding 3
    through for the STARVED heading).
    """


_ONE_ELIGIBLE_SPRINT_ROADMAP = """\
# Test One Eligible Sprint

### EXEC-1 — Sprint that will crash

**Status**: todo
**Depends on**: none

**Activity log.**
- 2026-01-01 — todo (created)
"""


class TestUncaughtExceptionDuringLoop:
    """Task 8 review round 2, Finding 1 -- the critical gap: an uncaught
    exception escaping the loop body previously produced total silence, no
    STATUS.md, no explanation. An agent crash on day 4 of a week-long
    unattended run is otherwise indistinguishable, from a phone, from a
    quiet success.
    """

    def test_exception_propagates_unchanged_and_status_md_shows_crash_banner(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (isolated_roadmap / "ROADMAP.md").write_text(_ONE_ELIGIBLE_SPRINT_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", True)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_e2e_crash.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_execute_sprint(
            sprint_id: str, state: HarnessState, test_baseline: tuple[int, int] = (0, 0)
        ) -> Outcome:
            raise _SimulatedCrash("boom-distinctive-crash-marker-77123")

        monkeypatch.setattr(harness, "execute_sprint", fake_execute_sprint)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args and args[0] == "status":
                return (0, " M requirements/roadmap/ROADMAP.md\n?? STATUS.md\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
            ],
        )

        try:
            # The status write must never swallow or mask a propagating
            # exception -- the original error and exit code are what the
            # operator (or a process supervisor) needs, and STATUS.md is a
            # supplement, never a replacement.
            with pytest.raises(_SimulatedCrash, match="boom-distinctive-crash-marker-77123"):
                harness.main()

            assert status_file.exists(), (
                "STATUS.md must exist even when the harness dies on an "
                "unhandled exception -- this is the single most important "
                "case in the whole task"
            )
            content = status_file.read_text(encoding="utf-8")
            # Distinguishing content, not merely a heading another section
            # could also satisfy (the Finding 3 mistake).
            assert "## CRASHED" in content
            assert "_SimulatedCrash" in content
            assert "boom-distinctive-crash-marker-77123" in content
            assert "EXEC-1" in content  # which sprint was in flight
        finally:
            status_file.unlink(missing_ok=True)

    def test_a_failure_inside_status_write_does_not_replace_the_real_crash(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The write must stay internally guarded: if status rendering
        itself has a bug while a real crash is already in flight (a
        `finally` running during unwinding of an already-failing run), the
        operator needs the ORIGINAL error, not a confusing secondary one
        from the reporting mechanism replacing it.
        """
        (isolated_roadmap / "ROADMAP.md").write_text(_ONE_ELIGIBLE_SPRINT_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", True)

        def fake_execute_sprint(
            sprint_id: str, state: HarnessState, test_baseline: tuple[int, int] = (0, 0)
        ) -> Outcome:
            raise _SimulatedCrash("original-crash-marker")

        monkeypatch.setattr(harness, "execute_sprint", fake_execute_sprint)

        def broken_write_status(*args: object, **kwargs: object) -> None:
            raise RuntimeError("status-write-itself-is-also-broken")

        monkeypatch.setattr(harness.status, "write_status", broken_write_status)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
            ],
        )

        # The ORIGINAL crash must win -- not the secondary bug in the
        # status-writing path that fired while it was already unwinding.
        with pytest.raises(_SimulatedCrash, match="original-crash-marker"):
            harness.main()


class TestDeclinedToRunLeavesStatus:
    """`return 2` (forced-sprint validation) / `return 3` (baseline capture
    failure) are clean, intentional declines -- not crashes -- but the
    operator still needs to know the harness didn't run, and why, rather
    than finding no STATUS.md at all.
    """

    def test_baseline_capture_failure_leaves_a_status_with_the_reason(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (isolated_roadmap / "ROADMAP.md").write_text(_ONE_ELIGIBLE_SPRINT_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")

        # This path specifically needs baseline capture to actually run
        # (not short-circuited by DRY_RUN), so preflight's real `claude
        # --version` subprocess check is neutralized directly instead.
        def fake_subprocess_run(*args: object, **kwargs: object) -> MagicMock:
            return MagicMock(returncode=0)

        monkeypatch.setattr(harness.subprocess, "run", fake_subprocess_run)

        def fake_capture_baseline() -> tuple[int, int]:
            raise harness.BaselineCaptureError("simulated-baseline-marker-42")

        monkeypatch.setattr(harness, "_capture_test_baseline", fake_capture_baseline)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_e2e_baseline.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args and args[0] == "status":
                return (0, " M requirements/roadmap/ROADMAP.md\n?? STATUS.md\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-agency-probe",
            ],
        )

        try:
            rc = harness.main()
            assert rc == 3

            assert status_file.exists(), (
                "a declined run must still leave STATUS.md -- total silence "
                "here is what the operator cannot tell from a quiet success"
            )
            content = status_file.read_text(encoding="utf-8")
            assert "simulated-baseline-marker-42" in content
            assert "## CRASHED" not in content, "a clean decline is not a crash"
        finally:
            status_file.unlink(missing_ok=True)

    def test_forced_sprint_not_found_leaves_a_status_with_the_reason(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (isolated_roadmap / "ROADMAP.md").write_text(_ONE_ELIGIBLE_SPRINT_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", True)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_e2e_forced.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            if args and args[0] == "status":
                return (0, " M requirements/roadmap/ROADMAP.md\n?? STATUS.md\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
                "--sprint",
                "DOES-NOT-EXIST",
            ],
        )

        try:
            rc = harness.main()
            # Its own code (M4), no longer shared with HARNESS_RC_LOCK_CONFLICT:
            # a hard abort must never be readable as "another instance is
            # running, stay quiet", which is exactly what the supervisor does
            # with code 2.
            assert rc == config.HARNESS_RC_FORCED_SPRINT_INVALID
            assert rc != config.HARNESS_RC_LOCK_CONFLICT

            assert status_file.exists()
            content = status_file.read_text(encoding="utf-8")
            assert "DOES-NOT-EXIST" in content
            assert "not found" in content
        finally:
            status_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Harness-managed dirty filter
# ---------------------------------------------------------------------------


class TestFilterHarnessManagedDirty:
    """The pre-flight clean-tree check filters lifecycle artifacts the
    harness owns. Without this, an accidentally-tracked lock file or a
    leaked state.json bricks the harness for everyone in the project.
    """

    def test_empty_porcelain_passes_through(self) -> None:
        filtered, removed = harness._filter_harness_managed_dirty("")
        assert filtered == ""
        assert removed == []

    def test_filters_running_lock_file(self) -> None:
        # The exact case the operator hit: ralph/.running deleted.
        filtered, removed = harness._filter_harness_managed_dirty("D  ralph/.running\n")
        assert filtered == ""
        assert removed == ["ralph/.running"]

    def test_filters_state_json(self) -> None:
        filtered, removed = harness._filter_harness_managed_dirty(" M ralph/state.json\n")
        assert filtered == ""
        assert "ralph/state.json" in removed

    def test_filters_logs_subdirectory(self) -> None:
        porcelain = "?? ralph/logs/SA-1/plan-20260429-100000.log\n"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert filtered == ""
        assert removed == ["ralph/logs/SA-1/plan-20260429-100000.log"]

    def test_filters_probe_artifacts(self) -> None:
        porcelain = "?? ralph/.agency_probe\n?? ralph/.write_probe\n"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert filtered == ""
        assert "ralph/.agency_probe" in removed
        assert "ralph/.write_probe" in removed

    def test_filters_stop_file(self) -> None:
        filtered, removed = harness._filter_harness_managed_dirty("?? STOP\n")
        assert filtered == ""
        assert removed == ["STOP"]

    def test_keeps_real_dirty_changes(self) -> None:
        porcelain = " M spacegame/models/foo.py\n?? new_test.py\n"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert "spacegame/models/foo.py" in filtered
        assert "new_test.py" in filtered
        assert removed == []

    def test_mixed_dirty_keeps_only_real(self) -> None:
        # The realistic mid-development case: harness artifacts + real changes.
        porcelain = "D  ralph/.running\n M spacegame/models/foo.py\n?? ralph/logs/SA-1/run.log\n"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert "spacegame/models/foo.py" in filtered
        assert "ralph/" not in filtered
        assert "ralph/.running" in removed
        assert "ralph/logs/SA-1/run.log" in removed

    def test_does_not_filter_ralph_source_files(self) -> None:
        # ralph/harness.py is real source — must NOT be filtered out even
        # though it lives under ralph/.
        porcelain = " M ralph/harness.py\n M ralph/agents.py\n"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert "ralph/harness.py" in filtered
        assert "ralph/agents.py" in filtered
        assert removed == []


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------


class TestLock:
    def test_acquire_when_no_lock(self, isolated_roadmap) -> None:
        result = harness._acquire_lock()
        assert result is True
        assert config.LOCK_FILE.exists()

    def test_release_removes_lock(self, isolated_roadmap) -> None:
        harness._acquire_lock()
        assert config.LOCK_FILE.exists()
        harness._release_lock()
        assert not config.LOCK_FILE.exists()

    def test_stale_lock_replaced(self, isolated_roadmap) -> None:
        # Write a stale lock with a PID that's almost certainly dead.
        config.LOCK_FILE.write_text("999999", encoding="utf-8")
        with patch.object(harness, "_pid_alive", return_value=False):
            result = harness._acquire_lock()
        assert result is True
        # The lock file now holds OUR pid.
        assert config.LOCK_FILE.read_text(encoding="utf-8").strip() == str(os.getpid())

    def test_fresh_lock_blocks_acquisition(self, isolated_roadmap) -> None:
        config.LOCK_FILE.write_text("12345", encoding="utf-8")
        with patch.object(harness, "_lock_holder_is_live_harness", return_value=True):
            result = harness._acquire_lock()
        assert result is False

    @pytest.mark.timeout(120)
    def test_a_live_but_unrelated_pid_does_not_hold_the_lock(self, isolated_roadmap) -> None:
        """A recycled PID must not brick every launch for the rest of the week.

        The lock check asked `_pid_alive` -- existence, not identity. PIDs are
        recycled, so a lock file left behind by a hard-killed harness whose PID
        now belongs to something else read as "held by a running harness", and
        the harness refused to start. Forever: nothing ages a lock file out.

        The process below is real and genuinely alive, so existence alone says
        "held". It is `python -c "sleep"`, not a harness, so identity says
        "stale" -- which is the correct answer.
        """
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            config.LOCK_FILE.write_text(str(proc.pid), encoding="utf-8")
            assert harness._pid_alive(proc.pid), (
                "test setup is broken: the stand-in process must genuinely be "
                "alive, or this proves nothing about identity vs. existence"
            )

            acquired = harness._acquire_lock()

            assert acquired is True, (
                f"PID {proc.pid} is alive but is NOT the ralph harness -- it is a "
                f"sleeping python -c. Treating it as the lock holder is the "
                f"recycled-PID failure: one dead harness's PID, reused by anything "
                f"on the machine, refuses every launch for the rest of the run"
            )
            assert config.LOCK_FILE.read_text(encoding="utf-8").strip() == str(os.getpid())
        finally:
            proc.kill()
            proc.wait(timeout=30)

    def test_release_idempotent(self, isolated_roadmap) -> None:
        # Releasing without holding is a no-op (no exception).
        harness._release_lock()
        harness._release_lock()


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


class TestHarnessState:
    def test_round_trip(self, isolated_roadmap) -> None:
        state = HarnessState()
        state.sprints["SA-1"] = SprintState(
            sprint_id="SA-1",
            plan_runs=2,
            implement_runs=3,
            rework_cycles=1,
            last_phase="review",
            last_outcome="needs_rework",
        )
        state.total_sprints_processed = 5
        state.save()

        loaded = HarnessState.load()
        assert loaded.total_sprints_processed == 5
        assert "SA-1" in loaded.sprints
        assert loaded.sprints["SA-1"].plan_runs == 2
        assert loaded.sprints["SA-1"].rework_cycles == 1
        assert loaded.sprints["SA-1"].last_phase == "review"

    def test_load_returns_default_when_missing(self, isolated_roadmap) -> None:
        # State file doesn't exist.
        state = HarnessState.load()
        assert state.sprints == {}
        assert state.total_sprints_processed == 0

    def test_for_sprint_creates_on_demand(self, isolated_roadmap) -> None:
        state = HarnessState()
        sprint_state = state.for_sprint("SA-NEW")
        assert sprint_state.sprint_id == "SA-NEW"
        assert "SA-NEW" in state.sprints


# ---------------------------------------------------------------------------
# Quality gates — _run_quality_gates() unit tests
# ---------------------------------------------------------------------------


class TestRunQualityGates:
    """Unit tests for _run_quality_gates() in isolation.

    All subprocess calls are monkeypatched so no real ruff/mypy runs.
    """

    def _cp(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_all_pass_returns_none(self) -> None:
        """When all four gates pass, returns None (no regression)."""
        with patch(
            "ralph.harness.subprocess.run",
            side_effect=[
                self._cp(0),  # ruff check spacegame/
                self._cp(0),  # ruff format --check spacegame/ tests/
                self._cp(
                    1, stdout="spacegame/foo.py:12: error: old error"
                ),  # mypy (existing errors OK)
                self._cp(0),  # mypy_baseline filter: all in baseline → clean
                self._cp(0),  # mypy tools/crawler --follow-imports=silent
            ],
        ):
            result = harness._run_quality_gates()
        assert result is None

    def test_crawler_mypy_fails_returns_mypy_crawler_tuple(self) -> None:
        """tools/crawler is gated at zero tolerance, with no baseline escape.

        spacegame/ may carry baselined errors; the crawler may not. A new error
        there must block the sprint rather than be absorbed.
        """
        with patch(
            "ralph.harness.subprocess.run",
            side_effect=[
                self._cp(0),  # ruff check passes
                self._cp(0),  # ruff format passes
                self._cp(1, stdout="spacegame/foo.py:12: error: old error"),  # mypy
                self._cp(0),  # baseline filter: clean
                self._cp(
                    1, stdout="tools/crawler/crawler.py:9: error: new error"
                ),  # crawler gate fails
            ],
        ):
            result = harness._run_quality_gates()
        assert result is not None
        gate, err = result
        assert gate == "mypy-crawler"
        assert "tools/crawler" in err

    def test_ruff_check_fails_returns_ruff_tuple(self) -> None:
        """ruff check non-zero exit → ('ruff', error_text)."""
        with patch("ralph.harness.subprocess.run", return_value=self._cp(1, stdout="lint error")):
            result = harness._run_quality_gates()
        assert result is not None
        gate, err = result
        assert gate == "ruff"
        assert "lint error" in err

    def test_ruff_format_fails_returns_ruff_format_tuple(self) -> None:
        """ruff format --check non-zero exit → ('ruff-format', error_text)."""
        with patch(
            "ralph.harness.subprocess.run",
            side_effect=[
                self._cp(0),  # ruff check passes
                self._cp(1, stdout="format violation"),  # ruff format fails
            ],
        ):
            result = harness._run_quality_gates()
        assert result is not None
        gate, err = result
        assert gate == "ruff-format"
        assert "format violation" in err

    def test_mypy_baseline_filter_fails_returns_mypy_tuple(self) -> None:
        """mypy_baseline filter non-zero exit → ('mypy', error_text)."""
        with patch(
            "ralph.harness.subprocess.run",
            side_effect=[
                self._cp(0),  # ruff check passes
                self._cp(0),  # ruff format passes
                self._cp(1, stdout="spacegame/foo.py:12: error: incompatible type"),  # mypy
                self._cp(1, stdout="Your changes introduced new violations."),  # filter fails
            ],
        ):
            result = harness._run_quality_gates()
        assert result is not None
        gate, err = result
        assert gate == "mypy"
        assert "violations" in err

    def test_long_output_truncated_to_gate_error_max(self) -> None:
        """Error text longer than _GATE_ERROR_MAX_CHARS is truncated."""
        long_output = "x" * 800
        with patch("ralph.harness.subprocess.run", return_value=self._cp(1, stdout=long_output)):
            result = harness._run_quality_gates()
        assert result is not None
        _, err = result
        assert len(err) == harness._GATE_ERROR_MAX_CHARS

    def test_mypy_file_not_found_returns_gate_tuple_no_crash(self) -> None:
        """FileNotFoundError on mypy → ('mypy', 'FileNotFoundError: ...'), no crash."""
        with patch(
            "ralph.harness.subprocess.run",
            side_effect=[
                self._cp(0),  # ruff check passes
                self._cp(0),  # ruff format passes
                FileNotFoundError("mypy not found"),  # mypy invocation fails
            ],
        ):
            result = harness._run_quality_gates()
        assert result is not None
        gate, err = result
        assert gate == "mypy"
        assert "FileNotFoundError" in err


# ---------------------------------------------------------------------------
# Quality gates — execute_sprint integration tests
# ---------------------------------------------------------------------------


class TestExecuteSprintQualityGate:
    """Integration tests verifying quality-gate wiring inside execute_sprint.

    agents.run_phase and _run_quality_gates are both mocked so no real
    subprocess calls occur. Uses isolated_roadmap fixture for ROADMAP + state
    file isolation.
    """

    def _ok_result(self, phase: Phase, tmp_path: Path) -> PhaseResult:
        return PhaseResult(
            outcome=Outcome.OK,
            phase=phase,
            sprint_id="SA-2",
            log_path=tmp_path / "test.log",
            reason="",
        )

    def test_plan_gate_failure_blocks_sprint(self, isolated_roadmap) -> None:
        """When plan phase is OK but gate fails, sprint ends blocked."""
        tmp = isolated_roadmap
        gate_error = ("mypy", "spacegame/foo.py:12: error: incompatible type")

        with patch.object(agents, "run_phase", return_value=self._ok_result(Phase.PLAN, tmp)):
            with patch.object(harness, "_run_quality_gates", return_value=gate_error):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.BLOCKED
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "blocked" in content
        assert "plan" in content
        assert "mypy" in content

    def test_implement_gate_failure_blocks_sprint(self, isolated_roadmap) -> None:
        """When plan is clean but implement gate fails, sprint ends blocked."""
        tmp = isolated_roadmap
        gate_error = ("ruff", "lint error in spacegame/models/foo.py")

        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
        ]
        gate_results = [None, gate_error]  # plan clean, implement fails

        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", side_effect=gate_results):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.BLOCKED
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "blocked" in content
        assert "implement" in content
        assert "ruff" in content

    def test_review_gate_failure_blocks_sprint_not_done(self, isolated_roadmap) -> None:
        """When review is OK but gate fails, sprint is blocked; STATUS_DONE not written."""
        tmp = isolated_roadmap
        gate_error = ("ruff-format", "format violation in spacegame/views/foo.py")

        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
            self._ok_result(Phase.REVIEW, tmp),
        ]
        gate_results = [None, None, gate_error]  # plan+implement clean, review gate fails

        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", side_effect=gate_results):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.BLOCKED
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "**Status**: done" not in content
        assert "blocked" in content
        assert "review" in content

    def test_all_clean_happy_path_gate_called_three_times(self, isolated_roadmap) -> None:
        """When all phases and gates are clean, sprint ends done; gate called exactly 3 times."""
        tmp = isolated_roadmap

        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
            self._ok_result(Phase.REVIEW, tmp),
        ]
        mock_gate = MagicMock(return_value=None)

        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", mock_gate):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.OK
        assert mock_gate.call_count == 3
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "**Status**: done" in content

    def test_non_ok_plan_phase_skips_gate(self, isolated_roadmap) -> None:
        """When plan phase returns non-OK, quality gate is not invoked."""
        tmp = isolated_roadmap
        blocked_result = PhaseResult(
            outcome=Outcome.BLOCKED,
            phase=Phase.PLAN,
            sprint_id="SA-2",
            log_path=tmp / "test.log",
            reason="missing context doc",
        )
        gate_spy = MagicMock(return_value=None)

        with patch.object(agents, "run_phase", return_value=blocked_result):
            with patch.object(harness, "_run_quality_gates", gate_spy):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.BLOCKED
        gate_spy.assert_not_called()

    def test_dry_run_skips_gate(self, isolated_roadmap, monkeypatch) -> None:
        """When DRY_RUN is True in harness module, quality gates are not invoked."""
        tmp = isolated_roadmap
        monkeypatch.setattr(harness, "DRY_RUN", True)

        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
            self._ok_result(Phase.REVIEW, tmp),
        ]
        gate_spy = MagicMock(return_value=None)

        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", gate_spy):
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.OK
        gate_spy.assert_not_called()


# ---------------------------------------------------------------------------
# STOP-file isolation — regression guard
# ---------------------------------------------------------------------------


class TestExecuteSprintStopFileIsolation:
    """Regression guard: tests/test_ralph/ must pass with a real project-root STOP file.

    Before SUITE-2: isolated_roadmap did not patch STOP_FILE. With a STOP file at
    PROJECT_ROOT, should_stop() returned True after the plan phase, causing
    execute_sprint to short-circuit and leaving gate call counts / outcome
    assertions wrong in three TestExecuteSprintQualityGate tests.

    After SUITE-2: isolated_roadmap patches harness.STOP_FILE + config.STOP_FILE
    to a per-test tmp_path, so should_stop() reads from a path that does not
    exist by default — isolating every test that uses the fixture.
    """

    def _ok_result(self, phase: Phase, tmp_path: Path) -> PhaseResult:
        return PhaseResult(
            outcome=Outcome.OK,
            phase=phase,
            sprint_id="SA-2",
            log_path=tmp_path / "test.log",
            reason="",
        )

    def test_happy_path_unaffected_by_real_stop_file(self, isolated_roadmap, monkeypatch) -> None:
        """Happy path completes all 3 phases even when PROJECT_ROOT/STOP exists.

        Creates the real project-root STOP file, verifies execute_sprint still
        runs plan + implement + review to completion because the fixture has
        redirected harness.STOP_FILE away from the project root.
        """
        tmp = isolated_roadmap

        # A prior SIGINT in this pytest process could set _stop_requested=True
        # and leak into should_stop(). Reset it explicitly.
        monkeypatch.setattr(harness, "_stop_requested", False)

        real_stop = config.PROJECT_ROOT / "STOP"
        real_stop.touch()
        try:
            phase_results = [
                self._ok_result(Phase.PLAN, tmp),
                self._ok_result(Phase.IMPLEMENT, tmp),
                self._ok_result(Phase.REVIEW, tmp),
            ]
            mock_gate = MagicMock(return_value=None)

            with patch.object(agents, "run_phase", side_effect=phase_results):
                with patch.object(harness, "_run_quality_gates", mock_gate):
                    result = harness.execute_sprint("SA-2", HarnessState())

            assert result == Outcome.OK
            assert mock_gate.call_count == 3, (
                f"Gate should be called 3 times (plan+implement+review); "
                f"got {mock_gate.call_count} — real STOP file must not reach "
                f"should_stop() inside isolated tests"
            )
            content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
            assert "**Status**: done" in content
        finally:
            # Always clean up so the next harness run is not immediately stopped.
            if real_stop.exists():
                real_stop.unlink()


# ---------------------------------------------------------------------------
# BaselineCaptureError — _capture_test_baseline error semantics
# ---------------------------------------------------------------------------


class TestCaptureTestBaseline:
    """_capture_test_baseline raises BaselineCaptureError on all three failure modes.

    AC #4: timeout, subprocess error, and unparseable output all surface
    as named exceptions; the caller (main loop) converts them to abort signals.
    """

    def _make_cp(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_timeout_raises_baseline_capture_error(self) -> None:
        """TimeoutExpired from the helper → BaselineCaptureError."""
        with patch.object(
            harness,
            "run_with_hard_timeout",
            side_effect=subprocess.TimeoutExpired(cmd=[], timeout=600),
        ):
            with pytest.raises(harness.BaselineCaptureError, match="timeout"):
                harness._capture_test_baseline()

    def test_nonzero_exit_raises_baseline_capture_error(self) -> None:
        """Non-zero subprocess exit → BaselineCaptureError with stderr tail."""
        with patch.object(
            harness,
            "run_with_hard_timeout",
            return_value=self._make_cp(returncode=2, stderr="worker crashed"),
        ):
            with pytest.raises(harness.BaselineCaptureError, match="worker crashed"):
                harness._capture_test_baseline()

    def test_file_not_found_raises_baseline_capture_error(self) -> None:
        """FileNotFoundError (pytest missing) → BaselineCaptureError."""
        with patch.object(
            harness,
            "run_with_hard_timeout",
            side_effect=FileNotFoundError("pytest not found"),
        ):
            with pytest.raises(harness.BaselineCaptureError, match="FileNotFoundError"):
                harness._capture_test_baseline()

    def test_unparseable_output_raises_baseline_capture_error(self) -> None:
        """Zero exit but no 'N passed' line → BaselineCaptureError('unparseable')."""
        with patch.object(
            harness,
            "run_with_hard_timeout",
            return_value=self._make_cp(returncode=0, stdout="no test results here"),
        ):
            with pytest.raises(harness.BaselineCaptureError, match="unparseable"):
                harness._capture_test_baseline()

    def test_parseable_output_returns_counts(self) -> None:
        """Zero exit with 'N passed' line → (passing, skipped) tuple."""
        output = "10 passed, 3 skipped in 5.00s"
        with patch.object(
            harness,
            "run_with_hard_timeout",
            return_value=self._make_cp(returncode=0, stdout=output),
        ):
            result = harness._capture_test_baseline()
        assert result == (10, 3)


class TestStateWritesAreAtomic:
    def test_state_save_uses_atomic_write(self, tmp_path: Path) -> None:
        """A truncated state.json means the harness cannot start."""
        target = tmp_path / "state.json"
        state = harness.HarnessState()
        with patch.object(harness, "STATE_FILE", target):
            with patch("ralph.harness.atomic_write") as mock_atomic:
                state.save()
        mock_atomic.assert_called_once()
        call_args = mock_atomic.call_args[0]
        assert call_args[0] == target
        # Verify the content is valid JSON with expected structure.
        content = json.loads(call_args[1])
        assert "sprints" in content
        assert "total_sprints_processed" in content
        assert "last_run_started_at" in content

    def test_write_sprint_summary_uses_atomic_write(self, tmp_path: Path) -> None:
        """Per-sprint SUMMARY.md must survive a power cut."""
        summary_dir = tmp_path / "logs" / "SA-1"
        summary_path = summary_dir / "SUMMARY.md"
        state = harness.HarnessState()
        state.sprints["SA-1"] = harness.SprintState(sprint_id="SA-1")

        with patch.object(harness, "LOGS_DIR", tmp_path / "logs"):
            with patch("ralph.harness.atomic_write") as mock_atomic:
                harness._write_sprint_summary("SA-1", state, Outcome.OK)
        mock_atomic.assert_called_once()
        call_args = mock_atomic.call_args[0]
        assert call_args[0] == summary_path
        assert "SA-1" in call_args[1]
        assert "ok" in call_args[1]

    def test_sync_roadmap_index_uses_atomic_write(self) -> None:
        """Index sync must survive a power cut."""
        mock_sync = MagicMock(return_value=("new content", ["SA-1"]))
        mock_rm_path = MagicMock()
        mock_rm_path.read_text.return_value = "original"

        with patch("ralph.harness.atomic_write") as mock_atomic:
            with patch.dict(
                "sys.modules", {"scripts.sync_roadmap_index": MagicMock()}
            ) as mocked_modules:
                mock_module = mocked_modules["scripts.sync_roadmap_index"]
                mock_module.ROADMAP_PATH = mock_rm_path
                mock_module.sync = mock_sync

                harness._sync_roadmap_index("SA-1")

        mock_atomic.assert_called_once()
        call_args = mock_atomic.call_args[0]
        assert call_args[0] == mock_rm_path
        assert call_args[1] == "new content"


# ---------------------------------------------------------------------------
# Retry grace — one retry before a failure becomes a permanent block
# ---------------------------------------------------------------------------


class TestRetryGrace:
    def test_first_failure_retries_rather_than_blocking(self) -> None:
        """SA-F2 died on returncode 1 with 135 bytes of output and stayed
        blocked for four months. One retry absorbs that entire class."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.ERROR) is True

    def test_second_failure_blocks(self) -> None:
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        sprint_state.retry_count = 1
        assert harness._should_retry(sprint_state, Outcome.ERROR) is False

    def test_blocked_outcome_is_never_retried(self) -> None:
        """A deliberate PHASE_BLOCKED is a judgement, not a failure."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.BLOCKED) is False

    def test_timeout_and_infra_error_are_retryable(self) -> None:
        """TIMEOUT and INFRA_ERROR are transient-failure classes too."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.TIMEOUT) is True
        assert harness._should_retry(sprint_state, Outcome.INFRA_ERROR) is True

    def test_needs_rework_is_not_retried_by_this_mechanism(self) -> None:
        """NEEDS_REWORK has its own bounded rework-cycle loop; it is not
        one of the outcomes this grace period governs."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.NEEDS_REWORK) is False


# ---------------------------------------------------------------------------
# Retry grace — execute_sprint integration (safety against partial work)
# ---------------------------------------------------------------------------


class TestExecuteSprintRetryGrace:
    """A retryable failure resets the sprint to `todo` instead of `blocked`,
    UNLESS the failed phase already produced a commit referencing the
    sprint -- retrying that would risk duplicating partial work.
    """

    def _err_run_phase(
        self, tmp_path: Path, reason: str = "no sentinel"
    ) -> Callable[..., PhaseResult]:
        """Build a `run_phase` replacement that mimics the real function's
        one relevant side effect: populating `context.pre_phase_head`.

        `agents.run_phase` is mocked wholesale in these tests (no real
        subprocess), so nothing else sets `pre_phase_head`. Without this,
        `_sprint_has_partial_commits` would short-circuit on an empty SHA
        and the mocked `_commits_since` below would never actually run --
        the exact "test that verifies nothing" failure mode.
        """

        def _run(
            phase: Phase, sprint_id: str, context: Optional[PhaseContext] = None
        ) -> PhaseResult:
            if context is not None and not context.pre_phase_head:
                context.pre_phase_head = "deadbeef"
            return PhaseResult(
                outcome=Outcome.ERROR,
                phase=phase,
                sprint_id=sprint_id,
                log_path=tmp_path / "test.log",
                reason=reason,
            )

        return _run

    def test_first_error_resets_to_todo_not_blocked(self, isolated_roadmap) -> None:
        tmp = isolated_roadmap
        with patch.object(agents, "run_phase", side_effect=self._err_run_phase(tmp)):
            with patch.object(agents, "_commits_since", return_value=[]) as mock_commits:
                result = harness.execute_sprint("SA-2", HarnessState())

        assert mock_commits.called, "the commit-safety check must actually run"
        assert result == Outcome.ERROR
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "todo"
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "retrying" in content

    def test_retry_count_increments_on_first_failure(self, isolated_roadmap) -> None:
        tmp = isolated_roadmap
        state = HarnessState()
        with patch.object(agents, "run_phase", side_effect=self._err_run_phase(tmp)):
            with patch.object(agents, "_commits_since", return_value=[]):
                harness.execute_sprint("SA-2", state)

        assert state.sprints["SA-2"].retry_count == 1

    def test_second_error_blocks(self, isolated_roadmap) -> None:
        tmp = isolated_roadmap
        state = HarnessState()
        state.sprints["SA-2"] = SprintState(sprint_id="SA-2", retry_count=1)
        with patch.object(agents, "run_phase", side_effect=self._err_run_phase(tmp)):
            with patch.object(agents, "_commits_since", return_value=[]):
                result = harness.execute_sprint("SA-2", state)

        assert result == Outcome.ERROR
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"

    def test_commits_already_present_blocks_instead_of_retrying(self, isolated_roadmap) -> None:
        """Partial completion signal: a commit already references the sprint.

        Retrying would risk duplicating that work, so this must block on
        the FIRST failure even though a retry would otherwise be available.
        """
        tmp = isolated_roadmap
        state = HarnessState()
        with patch.object(agents, "run_phase", side_effect=self._err_run_phase(tmp)):
            with patch.object(
                agents, "_commits_since", return_value=["abc123 SA-2 partial work"]
            ) as mock_commits:
                result = harness.execute_sprint("SA-2", state)

        assert mock_commits.called, "the commit-safety check must actually run"
        assert result == Outcome.ERROR
        assert state.sprints["SA-2"].retry_count == 0, (
            "a commit-guarded block is not a consumed retry -- retry_count must stay 0"
        )
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "not retrying" in content or "commit" in content.lower()

    def test_infra_error_with_commits_blocks_not_silently_resets(self, isolated_roadmap) -> None:
        """INFRA_ERROR normally auto-resets to `todo` unconditionally via
        `_mark_terminal_outcome` (the agent never meaningfully ran, so it is
        always safe to re-run). But if a commit already landed this attempt,
        that premise is false -- the commit-guard must win and actually
        block, not fall through to the INFRA_ERROR auto-reset.
        """

        def _infra_run_phase(
            phase: Phase, sprint_id: str, context: Optional[PhaseContext] = None
        ) -> PhaseResult:
            if context is not None and not context.pre_phase_head:
                context.pre_phase_head = "deadbeef"
            return PhaseResult(
                outcome=Outcome.INFRA_ERROR,
                phase=phase,
                sprint_id=sprint_id,
                log_path=isolated_roadmap / "test.log",
                reason="auth 403 from CLI",
            )

        state = HarnessState()
        with patch.object(agents, "run_phase", side_effect=_infra_run_phase):
            with patch.object(agents, "_commits_since", return_value=["abc123 SA-2 partial work"]):
                result = harness.execute_sprint("SA-2", state)

        assert result == Outcome.INFRA_ERROR
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked", (
            "a commit already landed -- INFRA_ERROR's usual auto-reset-to-todo "
            "must be overridden, not silently applied"
        )

    def test_blocked_outcome_never_retries_even_on_first_failure(self, isolated_roadmap) -> None:
        tmp = isolated_roadmap
        blocked_result = PhaseResult(
            outcome=Outcome.BLOCKED,
            phase=Phase.PLAN,
            sprint_id="SA-2",
            log_path=tmp / "test.log",
            reason="missing context doc",
        )
        with patch.object(agents, "run_phase", return_value=blocked_result):
            with patch.object(agents, "_commits_since", return_value=[]) as mock_commits:
                result = harness.execute_sprint("SA-2", HarnessState())

        assert result == Outcome.BLOCKED
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-2"].status == "blocked"
        assert not mock_commits.called, (
            "BLOCKED is a judgement; the retry path (and its commit check) must not even run"
        )


class TestAtomicWriteTmpOrphansDoNotBrickTheHarness:
    """A hard kill mid-`atomic_write` leaves a `.tmp` sibling behind.

    `atomic_write` writes `<path>.tmp` then `os.replace`. Its `finally`
    removes the sibling on exception, but a SIGKILL / `taskkill /F` / power
    cut skips `finally` entirely. The orphan then shows up as an untracked
    file, preflight's clean-tree check fails, and EVERY later launch returns
    the preflight code -- the harness is bricked until a human deletes a file
    they do not know exists.

    Found by the pre-deployment smoke drill, which killed the process
    mid-write rather than reasoning about it. The trigger is routine, not
    hypothetical: the supervisor's own stale-heartbeat recovery IS a
    `taskkill /F /T`.

    The first version of this class iterated a hardcoded three-element subset
    of `_HARNESS_MANAGED_RUNTIME_BASE` and asserted that the derivation
    produced `.tmp` entries for it -- i.e. it asserted over the same set that
    produced the answer, so it could not notice that `ROADMAP.md` (the
    largest and most frequently written atomic-write destination of all) was
    missing from the list entirely. That is why the defect survived review.
    The expectations below are therefore derived from the real write sites:
    the AST of every module is walked for `atomic_write(...)` calls, and a
    call site naming a destination this file does not know about fails.
    """

    # Destination expression (as it appears in the source) -> repo-relative
    # path it resolves to. Written out by hand ON PURPOSE: these strings are
    # an independent statement of where `atomic_write` actually writes, so
    # checking them against `_filter_harness_managed_dirty` cannot be
    # satisfied by the registry agreeing with itself.
    EXPECTED_DESTINATIONS: dict[str, str] = {
        "STATE_FILE": "ralph/state.json",
        "HEARTBEAT_PATH": "ralph/heartbeat.json",
        "PUSH_STATE_PATH": "ralph/push_state.json",
        "SUPERVISOR_STOP_PATH": "ralph/supervisor_stop.json",
        "STATUS_PATH": "STATUS.md",
        "ROADMAP_PATH": "requirements/roadmap/ROADMAP.md",
        "_RM": "requirements/roadmap/ROADMAP.md",
        "summary_path": "ralph/logs/SA-1/SUMMARY.md",
    }

    @staticmethod
    def _scan_source(source: str, rel: str) -> list[tuple[str, int, str]]:
        """Every `atomic_write(dest, ...)` call in one module's source.

        Resolves ALIASES. Matching only the literal name `atomic_write` meant
        `from ralph.proc import atomic_write as _aw; _aw(Path('x'), '{}')`
        registered nothing and the whole class stayed green -- a scan that
        claimed a property it did not have, which is the eighth vacuous test
        this plan produced. The local names bound to `atomic_write` are
        collected first (import aliases, plus plain `name = atomic_write`
        rebindings), then calls are matched against that set. Attribute calls
        (`proc.atomic_write(...)`) are matched on the attribute name, which
        covers `import ralph.proc as p` without needing to resolve the module.

        Returns (module path, line number, source of the first argument).
        """
        tree = ast.parse(source)
        local_names = {"atomic_write"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "atomic_write":
                        local_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.Assign):
                value = node.value
                bound = (isinstance(value, ast.Name) and value.id in local_names) or (
                    isinstance(value, ast.Attribute) and value.attr == "atomic_write"
                )
                if bound:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            local_names.add(target.id)

        sites: list[tuple[str, int, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if isinstance(func, ast.Name):
                matched = func.id in local_names
            elif isinstance(func, ast.Attribute):
                matched = func.attr == "atomic_write"
            else:
                matched = False
            if matched:
                sites.append((rel, node.lineno, ast.unparse(node.args[0])))
        return sites

    def _atomic_write_call_sites(self) -> list[tuple[str, int, str]]:
        """Every `atomic_write(dest, ...)` call in ralph/ and scripts/."""
        root = Path(harness.PROJECT_ROOT)
        sites: list[tuple[str, int, str]] = []
        for source_dir in ("ralph", "scripts"):
            for module in sorted((root / source_dir).rglob("*.py")):
                if "__pycache__" in module.parts:
                    continue
                sites.extend(
                    self._scan_source(
                        module.read_text(encoding="utf-8"),
                        module.relative_to(root).as_posix(),
                    )
                )
        return sites

    def test_the_ast_scan_finds_the_known_write_sites(self) -> None:
        """Guard on the guard: a scan that silently matched nothing would make
        every assertion below vacuous, which is exactly the failure class this
        rewrite exists to close."""
        sites = self._atomic_write_call_sites()
        assert len(sites) >= 5, (
            f"the atomic_write AST scan found only {len(sites)} call site(s); "
            "every test in this class would then be asserting over an empty "
            "set and proving nothing"
        )
        modules = {module for module, _line, _dest in sites}
        assert "ralph/roadmap_state.py" in modules, (
            "the scan missed ralph/roadmap_state.py, the ROADMAP.md write site "
            f"whose orphan bricks preflight; found: {sorted(modules)}"
        )

    def test_the_ast_scan_resolves_an_aliased_import(self) -> None:
        """The scan was defeated by one `as` clause.

        Fed a synthetic module rather than editing a real one, so the property
        is asserted permanently instead of by a probe someone has to remember
        to re-run.
        """
        aliased = (
            "from pathlib import Path\n"
            "from ralph.proc import atomic_write as _aw\n"
            "_aw(Path('data/unregistered.json'), '{}')\n"
        )
        sites = self._scan_source(aliased, "fake/aliased.py")
        assert [dest for _m, _line, dest in sites] == ["Path('data/unregistered.json')"], (
            "an aliased `atomic_write` import evades the scan, so a new write "
            "site can be added without registering its destination and the "
            "registry test silently proves nothing; sites found: {}".format(sites)
        )

    def test_the_ast_scan_still_finds_the_plain_and_attribute_forms(self) -> None:
        """Controls for the alias resolution: it must not have narrowed the
        scan to aliases only."""
        plain = (
            "from ralph.proc import atomic_write\n"
            "from ralph import proc\n"
            "atomic_write(A, '')\n"
            "proc.atomic_write(B, '')\n"
        )
        dests = [dest for _m, _line, dest in self._scan_source(plain, "fake/plain.py")]
        assert dests == ["A", "B"], f"the unaliased forms stopped matching; got {dests}"

    def test_every_atomic_write_destination_is_registered(self) -> None:
        """A new `atomic_write` call site must declare where it writes.

        This is the check that would have caught the ROADMAP.md gap: the
        registry is compared against the code, not against itself.
        """
        for module, line, dest in self._atomic_write_call_sites():
            assert dest in self.EXPECTED_DESTINATIONS, (
                f"{module}:{line} writes via atomic_write to `{dest}`, a "
                "destination this test does not know about. A hard kill "
                f"mid-write strands `{dest}.tmp`; if that path is not covered "
                "by harness._ATOMIC_WRITE_TARGETS (or the ralph/logs/ prefix) "
                "the orphan fails preflight's clean-tree check and bricks "
                "EVERY subsequent launch. Add the destination to "
                "harness._ATOMIC_WRITE_TARGETS, to .gitignore, and to "
                "EXPECTED_DESTINATIONS here."
            )

    def test_tmp_sibling_of_every_atomic_write_destination_is_filtered(self) -> None:
        """The orphan of every real write site must read as harness noise."""
        for dest in sorted(set(self.EXPECTED_DESTINATIONS.values())):
            porcelain = f"?? {dest}.tmp"
            filtered, removed = harness._filter_harness_managed_dirty(porcelain)
            assert filtered == "", (
                f"a leftover '{dest}.tmp' from a hard kill is treated as real "
                "working-tree dirt, so preflight returns 4 and every future "
                f"launch is bricked; filtered={filtered!r}"
            )
            assert removed == [f"{dest}.tmp"]

    def test_tmp_sibling_of_every_managed_runtime_file_is_filtered(self) -> None:
        """Iterates the whole tuple, not a literal subset of it."""
        assert harness._HARNESS_MANAGED_RUNTIME_BASE, "the managed-file tuple is empty"
        for managed in harness._HARNESS_MANAGED_RUNTIME_BASE:
            porcelain = f"?? {managed}.tmp"
            filtered, removed = harness._filter_harness_managed_dirty(porcelain)
            assert filtered == "", (
                f"a leftover '{managed}.tmp' from a hard kill is treated as real "
                "working-tree dirt, so preflight fails and every future launch "
                f"is bricked; filtered={filtered!r}"
            )
            assert f"{managed}.tmp" in removed

    def test_roadmap_md_itself_is_still_real_dirt(self) -> None:
        """Only the `.tmp` sibling is harness noise.

        ROADMAP.md is deliberately absent from `_HARNESS_MANAGED_RUNTIME_BASE`:
        blanket-filtering it would hide a genuinely modified roadmap from the
        clean-tree check, which is a real signal.
        """
        porcelain = " M requirements/roadmap/ROADMAP.md"
        filtered, removed = harness._filter_harness_managed_dirty(porcelain)
        assert filtered == porcelain, (
            "a modified ROADMAP.md is a real working-tree change and must still "
            f"fail the clean-tree check; filtered={filtered!r}"
        )
        assert removed == []


class TestTmpOrphanSweep:
    """`_sweep_tmp_orphans` is the second layer: it deletes the stranded file.

    The filter above makes a registered orphan invisible; the sweep removes it
    outright, including for destinations nobody registered -- the case that
    cannot be fixed by adding one more entry to a tuple.
    """

    def _aged(self, path: Path, age_seconds: float) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("half-written", encoding="utf-8")
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))
        return path

    def test_stranded_orphan_of_a_registered_target_is_deleted(self, tmp_path: Path) -> None:
        orphan = self._aged(tmp_path / "requirements" / "roadmap" / "ROADMAP.md.tmp", 600)

        _porcelain, swept = harness._sweep_tmp_orphans(root=tmp_path)

        assert not orphan.exists(), (
            "a ROADMAP.md.tmp stranded by a hard kill survived the startup "
            "sweep; it stays untracked dirt and preflight returns 4 forever"
        )
        assert "requirements/roadmap/ROADMAP.md.tmp" in swept

    def test_untracked_tmp_of_an_unregistered_target_is_deleted(self, tmp_path: Path) -> None:
        """The property the registry alone cannot give: a FUTURE write site."""
        orphan = self._aged(tmp_path / "some" / "future" / "target.json.tmp", 600)

        porcelain, swept = harness._sweep_tmp_orphans(
            "?? some/future/target.json.tmp", root=tmp_path
        )

        assert not orphan.exists(), (
            "an untracked .tmp for an atomic_write destination nobody "
            "registered survived the sweep, so a future write site can still "
            "brick every launch"
        )
        assert swept == ["some/future/target.json.tmp"]
        assert porcelain == "", (
            "the swept file is gone from disk, so its porcelain line must not "
            f"still be counted as dirt; porcelain={porcelain!r}"
        )

    def test_a_fresh_tmp_is_left_alone(self, tmp_path: Path) -> None:
        """Preflight runs before the lock, so a young .tmp may be in flight.

        Deleting it would break a concurrent instance's `os.replace`.
        """
        live = self._aged(tmp_path / "STATUS.md.tmp", 1)

        _porcelain, swept = harness._sweep_tmp_orphans(root=tmp_path)

        assert live.exists(), (
            "a .tmp written one second ago may belong to a write happening "
            "right now; deleting it breaks that write's os.replace"
        )
        assert swept == []

    def test_non_tmp_untracked_files_are_never_deleted(self, tmp_path: Path) -> None:
        real = self._aged(tmp_path / "spacegame" / "new_module.py", 600)

        porcelain, swept = harness._sweep_tmp_orphans("?? spacegame/new_module.py", root=tmp_path)

        assert real.exists(), "the sweep deleted an untracked file that is not a .tmp orphan"
        assert swept == []
        assert porcelain == "?? spacegame/new_module.py"

    def test_tracked_modifications_are_never_deleted(self, tmp_path: Path) -> None:
        """Only `??` (untracked) porcelain entries are sweep candidates."""
        tracked = self._aged(tmp_path / "notes.tmp", 600)

        _porcelain, swept = harness._sweep_tmp_orphans(" M notes.tmp", root=tmp_path)

        assert tracked.exists(), (
            "a tracked file ending in .tmp was deleted; the sweep must only "
            "consider untracked orphans and registered destinations"
        )
        assert swept == []


class TestPushOutcomeIsRecorded:
    """`_push_after_sprint` must leave a trace outside stdout.

    Under the Scheduled Task the harness's stdout is discarded, so a push
    failure logged with `log()` reached no channel at all: the harness kept
    working, the GitHub copy of STATUS.md froze, and nothing anywhere said so.
    """

    def _isolate_push_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        target = tmp_path / "push_state.json"
        monkeypatch.setattr(harness.status, "PUSH_STATE_PATH", target)
        return target

    def test_successful_push_is_recorded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._isolate_push_state(tmp_path, monkeypatch)
        monkeypatch.setattr(harness, "_run_git", lambda args, timeout=30: (0, "", ""))

        harness._push_after_sprint("SA-1", harness.Outcome.OK, True)

        state = harness.status.read_push_state()
        assert state is not None and state.ok
        assert state.last_success_timestamp is not None

    def test_failed_push_records_the_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._isolate_push_state(tmp_path, monkeypatch)
        monkeypatch.setattr(
            harness,
            "_run_git",
            lambda args, timeout=30: (1, "", "! [rejected] master -> master (non-fast-forward)"),
        )

        harness._push_after_sprint("SA-1", harness.Outcome.OK, True)

        state = harness.status.read_push_state()
        assert state is not None, (
            "a failed push left no record, so STATUS.md cannot tell the "
            "operator the board they are reading is frozen"
        )
        assert not state.ok
        assert "non-fast-forward" in state.detail

    def test_a_push_state_write_failure_does_not_crash_the_harness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recording is a reporting nicety; it must never end the run."""
        monkeypatch.setattr(harness, "_run_git", lambda args, timeout=30: (0, "", ""))

        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(harness.status, "record_push", boom)

        harness._push_after_sprint("SA-1", harness.Outcome.OK, True)


class TestAgencyProbeCannotHangIndefinitely:
    """H2(a): the pre-flight agency probe must be bounded by a process-tree kill.

    This is the worst failure shape in the system, and it is a *call-site*
    property, not a `proc.run_with_hard_timeout` property (which
    `tests/test_ralph/test_proc.py` already covers in isolation). The probe
    runs an agentic CLI whose own prompt asks it to spawn a Task subagent and
    a WebFetch -- grandchildren, holding the stdout pipe. With
    `subprocess.run(timeout=...)` the timeout kills the direct child and then
    `communicate()` blocks for as long as any grandchild holds that pipe: the
    measured 8.5-hour hang.

    And it happens BEFORE the heartbeat thread starts, so the supervisor has
    no beat age to judge and (before H2(b)) would wait forever. A hang here is
    total, indefinite silence: no STATUS.md, nothing pushed, no banner.

    So this drives the real `_probe_claude_write_permission` against a real
    process tree with a real pipe-holding grandchild.
    """

    def _run_probe_bounded(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        *,
        probe_timeout: float,
        wait_seconds: float,
    ) -> tuple[bool, Optional[tuple[bool, str]], Optional[int]]:
        """Drive the probe against a hanging process tree, in a daemon thread.

        Returning rather than asserting keeps the assertions in the test
        bodies. The thread is a daemon so a genuine hang fails this test on
        its own assertion instead of wedging the whole suite.

        Returns (finished, probe_result, grandchild_pid).
        """
        pid_file = tmp_path / "grandchild.pid"
        script = tmp_path / "fake_claude.py"
        # argv[1] is the prompt the harness appends; ignored on purpose.
        script.write_text(
            "import subprocess, sys, time\n"
            "gc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
            f"open({str(pid_file)!r}, 'w').write(str(gc.pid))\n"
            "sys.stdout.flush()\n"
            "time.sleep(300)\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "CLAUDE_CMD", (sys.executable, str(script)))
        monkeypatch.setattr(harness, "PROBE_TIMEOUT_SECONDS", probe_timeout)

        box: dict[str, tuple[bool, str]] = {}

        def _call() -> None:
            box["result"] = harness._probe_claude_write_permission()

        thread = threading.Thread(target=_call, name="agency-probe-under-test", daemon=True)
        started = time.monotonic()
        thread.start()
        thread.join(timeout=wait_seconds)
        elapsed = time.monotonic() - started
        finished = not thread.is_alive()

        grandchild_pid: Optional[int] = None
        if pid_file.exists():
            try:
                grandchild_pid = int(pid_file.read_text(encoding="utf-8").strip())
            except ValueError:
                grandchild_pid = None
        assert elapsed <= wait_seconds + 5, "join() overran its own bound"
        return finished, box.get("result"), grandchild_pid

    @pytest.mark.timeout(180)
    def test_probe_returns_bounded_when_a_grandchild_holds_the_pipe(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        finished, result, grandchild_pid = self._run_probe_bounded(
            monkeypatch, tmp_path, probe_timeout=3.0, wait_seconds=45.0
        )
        _reap(grandchild_pid)

        assert finished, (
            "the agency probe did not return within 45s of its own 3s timeout. "
            "A grandchild is holding the stdout pipe open, so this call site is "
            "still using subprocess.run(timeout=...) -- which kills the direct "
            "child and then blocks in communicate() until the grandchild exits "
            "(the measured 8.5-hour hang). Pre-flight runs before the heartbeat "
            "thread starts, so this hang is indefinite silence with no rescue: "
            "route it through ralph.proc.run_with_hard_timeout."
        )
        assert result is not None
        ok, reason = result
        assert not ok, f"a hung CLI must fail the probe, got {reason!r}"
        assert "timed out" in reason, (
            f"the probe returned but did not report a timeout: {reason!r} -- "
            "the operator must be told which pre-flight check failed and why"
        )

    @pytest.mark.timeout(180)
    def test_the_pipe_holding_grandchild_is_actually_killed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Returning on time is not the same as having killed the tree.

        A probe that returned while leaving a live agent tree behind would
        leak one such tree per launch for seven days, each holding an API
        session open. Wall clock alone cannot see that; the PID can.
        """
        finished, _result, grandchild_pid = self._run_probe_bounded(
            monkeypatch, tmp_path, probe_timeout=3.0, wait_seconds=45.0
        )
        assert finished, "probe hung; see the sibling test for the diagnosis"
        assert grandchild_pid is not None, "grandchild never started -- test setup is broken"
        time.sleep(0.5)  # let the OS reap it
        still_alive = harness._pid_alive(grandchild_pid)
        _reap(grandchild_pid)
        assert not still_alive, (
            f"grandchild PID {grandchild_pid} survived the probe's timeout -- the "
            f"process-tree kill did not reach it, so every launch leaks a live "
            f"agent tree"
        )


class TestNoBareSubprocessRunTimeoutOnCommandsThatSpawnGrandchildren:
    """H2/N2 audit: `subprocess.run(timeout=...)` may not run anything that can
    leave a grandchild holding the captured pipe.

    The distinction that matters is not "does it have a timeout" but "can it
    spawn grandchildren that hold the stdout pipe". On Windows, `run()` handles
    `TimeoutExpired` by killing the DIRECT child and then calling
    `communicate()` with no timeout at all -- so a surviving grandchild turns a
    60-second bound into an unbounded wait. That is the measured 8.5-hour hang.

    Two command families qualify:

    * an agentic CLI, which spawns subagents by design;
    * **git**, which the original H2 audit cleared on the reasoning that
      "capture_output means no tty, so no pager, so no grandchild". True of
      `git status`. False of `git push`: origin is
      `git@github.com:MRittinghouse/SpaceGame.git`, so git execs `ssh.exe`,
      which inherits the captured stderr. Killing `git.exe` does not kill
      `ssh.exe`, and an ssh writing to a black-holed socket has no
      `ServerAliveInterval` by default. The supervisor reaches `git push`
      through `_publish_status`, and nothing supervises the supervisor:
      `MultipleInstances = IgnoreNew` discards every trigger firing while the
      wedged process lives, and `_publish_status` catches exceptions, not
      hangs. So a hang there is permanent.

    Still cleared, deliberately: `tasklist`, `taskkill` and
    `powershell -Command Get-CimInstance` are leaf queries that spawn nothing,
    and `python -m ruff|mypy|mypy_baseline` (the quality gates) spawn no
    children either -- and unlike the supervisor, the harness running them is
    itself watched by the supervisor's stale-heartbeat kill.

    Walks the AST rather than grepping so a reformatted call site cannot slip
    past, and so it keeps holding for call sites that do not exist yet.
    """

    _AGENTIC_MARKERS = ("claude_cmd", "harness_cmd")

    def _subprocess_run_calls(self, path: Path) -> list[tuple[int, str, bool]]:
        """(lineno, unparsed positional args, has a `timeout=` keyword)."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: list[tuple[int, str, bool]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "run"
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
            ):
                continue
            args_src = " ".join(ast.unparse(a) for a in node.args)
            has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
            found.append((node.lineno, args_src, has_timeout))
        return found

    def _ralph_modules(self) -> list[Path]:
        return sorted(Path(harness.__file__).parent.glob("*.py"))

    def test_the_ast_scan_finds_the_known_call_sites(self) -> None:
        """Guards the guard: if the scan matched nothing, both assertions
        below would be vacuously green."""
        total = sum(len(self._subprocess_run_calls(p)) for p in self._ralph_modules())
        assert total >= 5, (
            f"the AST scan found only {total} subprocess.run call sites in ralph/; "
            "it has stopped matching real code, which would make the assertions "
            "below prove nothing"
        )

    def test_no_subprocess_run_invokes_an_agentic_cli(self) -> None:
        offenders: list[str] = []
        for module in self._ralph_modules():
            for lineno, args_src, _bounded in self._subprocess_run_calls(module):
                lowered = args_src.lower()
                if any(marker in lowered for marker in self._AGENTIC_MARKERS):
                    offenders.append(f"{module.name}:{lineno} -> {args_src}")
        assert not offenders, (
            "these subprocess.run call sites launch an agentic CLI: "
            f"{offenders}. subprocess.run(timeout=...) kills only the direct "
            "child and then blocks in communicate() while a grandchild holds "
            "the stdout pipe -- the 8.5-hour hang. Use "
            "ralph.proc.run_with_hard_timeout instead."
        )

    def test_no_subprocess_run_invokes_git(self) -> None:
        """N2: `git push` against an SSH origin execs `ssh.exe`, which holds
        the captured stderr after `git.exe` is killed.

        Enforced against git as a whole rather than against a push/fetch
        allowlist: deciding which subcommands reach the network is precisely
        the judgement the first audit got wrong, and an allowlist would have to
        be re-derived every time a call site is added. `harness._run_git` is
        the single choke point and it goes through `run_with_hard_timeout`.
        """
        offenders: list[str] = []
        for module in self._ralph_modules():
            for lineno, args_src, _bounded in self._subprocess_run_calls(module):
                if re.search(r"""['"]git['"]""", args_src):
                    offenders.append(f"{module.name}:{lineno} -> {args_src}")
        assert not offenders, (
            f"these subprocess.run call sites invoke git: {offenders}. origin "
            "is git@github.com:..., so git execs ssh.exe, which inherits the "
            "captured pipe; subprocess.run's timeout kills git.exe and then "
            "blocks in communicate() with NO timeout while ssh holds the "
            "handle -- the 8.5-hour hang. In the supervisor that hang is "
            "permanent: nothing supervises it and IgnoreNew discards every "
            "trigger firing. Route it through harness._run_git, which uses "
            "ralph.proc.run_with_hard_timeout."
        )

    def test_every_subprocess_run_in_ralph_is_bounded(self) -> None:
        """A `subprocess.run` with no timeout at all can block forever even
        without a grandchild -- and both such calls were on kill paths: the
        supervisor's only recovery action, and the hard timeout's own kill."""
        unbounded: list[str] = []
        for module in self._ralph_modules():
            for lineno, _args_src, has_timeout in self._subprocess_run_calls(module):
                if not has_timeout:
                    unbounded.append(f"{module.name}:{lineno}")
        assert not unbounded, (
            f"subprocess.run without a timeout in ralph/: {unbounded}. "
            "Nothing supervises the supervisor; an unbounded call there is an "
            "unbounded wait with nobody left to break it."
        )


class TestGitCannotHangTheProcessThatRunsIt:
    """N2, behaviourally: `_run_git` is the one choke point for git, and it
    must not be `subprocess.run`.

    The AST test above states the rule; this states the wiring, so a call site
    that stopped using `_run_git` (or a `_run_git` that quietly went back to
    `subprocess.run`) fails here as well as there.
    """

    def _capture(
        self, monkeypatch: pytest.MonkeyPatch, result: object
    ) -> list[tuple[list[str], float]]:
        seen: list[tuple[list[str], float]] = []

        def _run(cmd: list[str], timeout_seconds: float, cwd: Optional[str] = None) -> object:
            seen.append((list(cmd), timeout_seconds))
            if isinstance(result, BaseException):
                raise result
            return result

        monkeypatch.setattr(harness, "run_with_hard_timeout", _run)

        def _forbidden(*_args: object, **_kwargs: object) -> object:
            raise AssertionError(
                "_run_git fell back to subprocess.run: on Windows its timeout "
                "kills git.exe and then blocks in communicate() with no bound "
                "while ssh.exe holds the pipe"
            )

        monkeypatch.setattr(harness.subprocess, "run", _forbidden)
        return seen

    def test_a_push_goes_through_the_hard_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen = self._capture(monkeypatch, _FakeCompleted(0, "Everything up-to-date\r\n"))

        rc, stdout, _stderr = harness._run_git(["push", "origin", "HEAD"], timeout=60)

        assert seen == [(["git", "push", "origin", "HEAD"], 60)], (
            "the push did not reach run_with_hard_timeout, so a wedged ssh.exe "
            f"can block it indefinitely; calls seen: {seen}"
        )
        assert rc == 0
        assert stdout == "Everything up-to-date\n", (
            "run_with_hard_timeout decodes raw bytes, so CRLF must be "
            "normalised here or every caller that compares git output against "
            f"a plain string silently changes behaviour; got {stdout!r}"
        )

    def test_a_wedged_push_is_reported_as_a_timeout_not_raised(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hard timeout must still look to callers exactly like the old
        `subprocess.run` timeout: rc 124 and a reason, never an exception that
        would escape `_push_after_sprint` and end the run."""
        self._capture(
            monkeypatch,
            subprocess.TimeoutExpired(cmd=["git", "push"], timeout=60),
        )

        rc, _stdout, stderr = harness._run_git(["push", "origin", "HEAD"], timeout=60)

        assert rc == 124, f"a timed-out push reported rc={rc} instead of 124"
        assert "timed out" in stderr


class TestHeartbeatIsWrittenOnlyByTheLockHolder:
    """M3: an instance that loses the lock race must not stamp the heartbeat.

    `heartbeat._loop` beats immediately, before its first `stop.wait()`. The
    thread used to be started before `_acquire_lock()`, so a second harness
    that correctly LOST the race wrote heartbeat.json with its OWN pid -- a pid
    that was dead moments later, since it then returned rc 2.

    For up to 30 seconds (until the real harness's next beat)
    `supervisor.heartbeat_pid_alive()` therefore read "no live run" while a
    healthy harness was working in the repo. A supervisor sampling in that
    window double-launches; the new instance loses the lock and exits rc 2;
    and `main()` counts rc 2 as a failure. Three of those consume the entire
    3-strike budget and stop the supervisor for the week while a perfectly
    healthy harness is running.
    """

    def _drive_main(
        self,
        isolated_roadmap: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        lock_granted: bool,
    ) -> tuple[int, Path]:
        beat_path = isolated_roadmap / "hb.json"
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", beat_path)
        (isolated_roadmap / "ROADMAP.md").write_text(_STARVED_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness, "DRY_RUN", True)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_m3.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        if not lock_granted:
            monkeypatch.setattr(harness, "_acquire_lock", lambda: False)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
            ],
        )
        try:
            rc = harness.main()
        finally:
            status_file.unlink(missing_ok=True)
        # A heartbeat thread started at the wrong moment beats immediately;
        # give it more than enough time to land on disk before asserting.
        time.sleep(0.3)
        return rc, beat_path

    def test_losing_the_lock_writes_no_heartbeat(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc, beat_path = self._drive_main(isolated_roadmap, monkeypatch, lock_granted=False)

        assert rc == 2, f"expected the lock-conflict exit code, got {rc}"
        assert not beat_path.exists(), (
            "an instance that lost the lock race still stamped heartbeat.json with "
            "its own (about-to-be-dead) pid. For up to 30s the supervisor then reads "
            "'no live run' while a healthy harness is working, double-launches, and "
            "burns a strike off its 3-failure budget on every such collision. Start "
            "the heartbeat thread only after _acquire_lock() succeeds."
        )

    def test_holding_the_lock_does_write_a_heartbeat(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: without this, the assertion above would pass just
        as happily if the heartbeat never worked at all."""
        rc, beat_path = self._drive_main(isolated_roadmap, monkeypatch, lock_granted=True)

        assert rc == 0
        assert beat_path.exists(), (
            "the lock holder wrote no heartbeat, so the harness is invisible to the "
            "supervisor's liveness check for its entire run"
        )
        payload = json.loads(beat_path.read_text(encoding="utf-8"))
        assert payload["pid"] == os.getpid(), (
            "the heartbeat must carry the pid of the process that holds the lock"
        )


_TWO_TODO_ROADMAP = """\
# Test Two Sprints

### RED-1 — First sprint

**Status**: todo
**Depends on**: none

**Activity log.**
- 2026-01-01 — todo (created)

### RED-2 — Second sprint

**Status**: todo
**Depends on**: none

**Activity log.**
- 2026-01-01 — todo (created)
"""


class _FakeCompleted:
    """Stand-in for `subprocess.CompletedProcess` from `run_with_hard_timeout`."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestTestSuiteGate:
    """H3: the test suite is a harness-enforced gate, not a prompt paragraph.

    `_run_quality_gates` runs ruff, ruff-format and mypy. It does not run
    pytest. So the full sequence "implement breaks the suite -> agent writes
    PHASE_OK -> lint/format/type gates pass because they never run tests ->
    review agent may or may not notice -> sprint marked done -> harness commits
    and PUSHES -> next sprint picked up, up to 10 per invocation" was
    available, and the only machine backstop was the *next* launch's baseline
    capture -- several sprints and one supervisor shutdown later.
    """

    def _fake_runner(
        self,
        monkeypatch: pytest.MonkeyPatch,
        results: list[object],
    ) -> list[list[str]]:
        """Replace `run_with_hard_timeout`; return the list of argvs it saw."""
        seen: list[list[str]] = []
        queue = list(results)

        def _run(cmd: list[str], timeout_seconds: float, cwd: Optional[str] = None) -> object:
            seen.append(list(cmd))
            assert queue, f"the gate ran more pytest invocations than the test expected: {seen}"
            outcome = queue.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        monkeypatch.setattr(harness, "run_with_hard_timeout", _run)
        return seen

    def test_a_green_suite_passes_the_gate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._fake_runner(monkeypatch, [_FakeCompleted(0, "10774 passed, 98 skipped in 100s")])
        assert harness._run_test_gate((10_774, 98)) is None

    def test_a_red_suite_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        failure = _FakeCompleted(1, "FAILED tests/test_models/test_market.py::test_price\n1 failed")
        self._fake_runner(monkeypatch, [failure, failure])

        gate = harness._run_test_gate((10_774, 98))

        assert gate is not None, (
            "a red test suite passed the gate. The harness will now mark the sprint "
            "done, commit it, push it, and author the next sprint on top of the break"
        )
        name, detail = gate
        assert name == "pytest"
        assert "test_market" in detail, (
            f"the block reason does not name what failed: {detail!r} -- the operator "
            "reads this from STATUS.md, not from a log the Scheduled Task discards"
        )

    def test_a_failure_that_does_not_reproduce_is_treated_as_a_flake(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single flaky test must not strand a week of unattended work.

        The retry is cheap because it only happens on failure and only re-runs
        what failed.
        """
        seen = self._fake_runner(
            monkeypatch,
            [_FakeCompleted(1, "1 failed, 10773 passed"), _FakeCompleted(0, "1 passed")],
        )

        assert harness._run_test_gate((10_774, 98)) is None
        assert len(seen) == 2, "the gate blocked without re-running the failure"
        assert "--last-failed" in seen[1], (
            f"the retry re-ran the whole suite instead of the failures: {seen[1]}"
        )

    def test_a_dropped_passing_count_blocks_even_though_the_suite_is_green(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deleting the failing test is how a red suite is made green when
        nobody is watching."""
        self._fake_runner(monkeypatch, [_FakeCompleted(0, "10500 passed, 98 skipped")])

        gate = harness._run_test_gate((10_774, 98))

        assert gate is not None, (
            "274 tests disappeared and the gate passed, so a sprint that deletes "
            "tests instead of fixing them is indistinguishable from one that works"
        )
        assert "10500" in gate[1] and "10774" in gate[1]

    def test_a_hung_suite_is_a_failure_not_a_hang(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._fake_runner(monkeypatch, [subprocess.TimeoutExpired(cmd=["pytest"], timeout=900)])

        gate = harness._run_test_gate((10_774, 98))

        assert gate is not None
        assert "did not finish" in gate[1]

    def test_the_gate_declines_when_no_baseline_anchors_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--skip-baseline` / `--dry-run` means the tree was never proven
        green at startup, so "absolute green" would be asserting against an
        anchor that does not exist. Declining is honest; blocking on a
        pre-existing failure would strand the whole week."""
        seen = self._fake_runner(monkeypatch, [])
        assert harness._run_test_gate((0, 0)) is None
        assert seen == [], "the gate ran pytest with no known-good baseline to compare against"

    def test_the_gate_never_uses_dash_n_auto(self) -> None:
        """`-n auto` hung 6 runs in 10 on this host (see config.TEST_WORKERS).
        A gate that hangs is worse than no gate: it wedges the harness inside
        a sprint, where a hang is hardest to attribute."""
        cmd = harness._pytest_gate_cmd()
        assert "auto" not in cmd, f"the test gate uses -n auto: {cmd}"
        assert "-n" in cmd and cmd[cmd.index("-n") + 1] == config.TEST_WORKERS


class TestTestGateIsWiredIntoTheSprint:
    """Unit-testing `_run_test_gate` proves the rule; this proves it is
    consulted at the one moment that matters -- before `done`, before the
    bookkeeping commit, before the push."""

    def _ok_result(self, phase: Phase, tmp_path: Path) -> PhaseResult:
        return PhaseResult(
            outcome=Outcome.OK,
            phase=phase,
            sprint_id="SA-2",
            log_path=tmp_path / "test.log",
            reason="",
        )

    def test_a_red_tree_blocks_the_sprint_and_it_is_not_marked_done(
        self, isolated_roadmap: Path
    ) -> None:
        tmp = isolated_roadmap
        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
            self._ok_result(Phase.REVIEW, tmp),
        ]

        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", return_value=None):
                with patch.object(
                    harness,
                    "_run_test_gate",
                    return_value=("pytest", "3 failed in tests/test_models/test_market.py"),
                ):
                    result = harness.execute_sprint(
                        "SA-2", HarnessState(), test_baseline=(10_774, 98)
                    )

        assert result == Outcome.BLOCKED
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "**Status**: done" not in content, (
            "a sprint that broke the test suite was marked done -- the harness will "
            "commit and push it and then build the next sprint on top of it"
        )
        assert "test-suite gate FAILED" in content
        assert "test_market" in content

    def test_the_gate_is_given_the_real_baseline(self, isolated_roadmap: Path) -> None:
        """The gate's whole safety argument rests on the startup baseline
        having proven the tree green. Handing it (0, 0) would make it decline
        silently on every sprint."""
        tmp = isolated_roadmap
        seen: list[tuple[int, int]] = []

        def _spy(baseline: tuple[int, int]) -> None:
            seen.append(baseline)
            return None

        phase_results = [
            self._ok_result(Phase.PLAN, tmp),
            self._ok_result(Phase.IMPLEMENT, tmp),
            self._ok_result(Phase.REVIEW, tmp),
        ]
        with patch.object(agents, "run_phase", side_effect=phase_results):
            with patch.object(harness, "_run_quality_gates", return_value=None):
                with patch.object(harness, "_run_test_gate", _spy):
                    harness.execute_sprint("SA-2", HarnessState(), test_baseline=(10_774, 98))

        assert seen == [(10_774, 98)], f"the gate was called with {seen}"


class TestARedTreeStopsTheRunAndReachesStatusMd:
    """The gate must end the run, not merely block one sprint.

    Blocking one sprint and continuing would spend the remaining nine sprint
    slots authoring work on top of a tree already known to be broken -- and
    each one would fail its own gate, burning an implement phase apiece. And a
    gate whose failure is only logged is not a gate: `log()` writes to a stdout
    the Scheduled Task discards.
    """

    def _drive(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[int, str, list[str]]:
        (isolated_roadmap / "ROADMAP.md").write_text(_TWO_TODO_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", False)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_gate.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)

        picked: list[str] = []

        def fake_execute(
            sprint_id: str, state: object, test_baseline: tuple[int, int] = (0, 0)
        ) -> Outcome:
            picked.append(sprint_id)
            harness._set_red_tree(f"{sprint_id}: test-suite gate FAILED: 3 failed")
            return Outcome.BLOCKED

        monkeypatch.setattr(harness, "execute_sprint", fake_execute)
        monkeypatch.setattr(harness, "_capture_test_baseline", lambda: (10_774, 98))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "3",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-agency-probe",
            ],
        )
        try:
            rc = harness.main()
            content = status_file.read_text(encoding="utf-8") if status_file.exists() else ""
        finally:
            status_file.unlink(missing_ok=True)
        return rc, content, picked

    def test_the_run_stops_after_the_first_red_sprint(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _rc, _content, picked = self._drive(isolated_roadmap, monkeypatch)

        assert picked == ["RED-1"], (
            f"the harness picked up {picked} -- it kept authoring sprints on a tree "
            "it already knew was red, and each one burns a full implement phase"
        )

    def test_the_gate_failure_reaches_status_md(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _rc, content, _picked = self._drive(isolated_roadmap, monkeypatch)

        assert "## TEST SUITE FAILING" in content, (
            "the run stopped on a red tree and STATUS.md says nothing about it. "
            "STATUS.md is the only channel that reaches the operator's phone; a "
            "gate failure reported only to stdout is reported nowhere"
        )
        assert "RED-1" in content, "STATUS.md does not name the sprint whose gate failed"
        assert "TEST-GATE FAILED" in content, (
            "the outcome list does not distinguish a gate failure from any other block"
        )


class TestMidRunBaselineRefreshFailureIsVisible:
    """The mid-run baseline refresh failure was caught and downgraded to a log
    line ("Keeping previous baseline") -- and `log()` writes to a stdout the
    Scheduled Task discards.

    Keeping the run going on the last known-good count is right; making the
    failure invisible is not. `## Recent` in STATUS.md is pushed, so that is
    where it goes.
    """

    def test_a_failed_refresh_appears_in_status_md(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (isolated_roadmap / "ROADMAP.md").write_text(_TWO_TODO_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", False)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_refresh.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)
        monkeypatch.setattr(
            harness,
            "_run_git",
            lambda args, timeout=30: (0, "true\n", "")
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]
            else (0, "", ""),
        )
        monkeypatch.setattr(
            harness,
            "execute_sprint",
            lambda sprint_id, state, test_baseline=(0, 0): Outcome.OK,
        )

        calls = {"n": 0}

        def flaky_baseline() -> tuple[int, int]:
            calls["n"] += 1
            if calls["n"] == 1:
                return (10_774, 98)
            raise harness.BaselineCaptureError("pytest exited 2; tail: INTERNALERROR")

        monkeypatch.setattr(harness, "_capture_test_baseline", flaky_baseline)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-agency-probe",
            ],
        )
        try:
            rc = harness.main()
            content = status_file.read_text(encoding="utf-8") if status_file.exists() else ""
        finally:
            status_file.unlink(missing_ok=True)

        assert rc == 0
        assert "baseline-refresh FAILED" in content, (
            "the mid-run baseline refresh failed and STATUS.md does not mention it. "
            "The only other record is a log line on a stdout the Scheduled Task "
            "discards, so the operator sees a green board while the harness has "
            "stopped being able to measure the suite at all"
        )
        assert "INTERNALERROR" in content, "STATUS.md does not carry the reason"


class TestInfraErrorIsBoundedPerSprint:
    """`_mark_terminal_outcome` resets INFRA_ERROR to `todo` so the next run
    picks the sprint up cleanly -- which makes it re-runnable without limit.
    `retry_count` bounds every other outcome class; it bounds nothing here,
    because the reset happens whether or not the retry was allowed.
    """

    def _infra_result(self, tmp_path: Path) -> PhaseResult:
        return PhaseResult(
            outcome=Outcome.INFRA_ERROR,
            phase=Phase.PLAN,
            sprint_id="SA-2",
            log_path=tmp_path / "test.log",
            reason="claude CLI exited 1 with 0 bytes of output",
        )

    def _drive(self, isolated_roadmap: Path, attempts: int) -> HarnessState:
        state = HarnessState()
        for _ in range(attempts):
            roadmap_state.update_status("SA-2", config.STATUS_TODO)
            with patch.object(
                agents, "run_phase", return_value=self._infra_result(isolated_roadmap)
            ):
                harness.execute_sprint("SA-2", state)
        return state

    def test_below_the_cap_the_sprint_is_reset_to_todo(self, isolated_roadmap: Path) -> None:
        """Control: the existing, correct behaviour must survive the bound.

        A transient CLI blip is exactly what the todo-reset is for, and the
        bound must not turn the first one into a block."""
        self._drive(isolated_roadmap, attempts=1)
        sprint = roadmap_state.parse_sprints()["SA-2"]
        assert sprint.is_todo(), (
            f"a single infrastructure blip left SA-2 at {sprint.status!r} instead of "
            "todo; the bound has swallowed the transient-failure grace"
        )

    def test_at_the_cap_the_sprint_is_blocked_instead(self, isolated_roadmap: Path) -> None:
        state = self._drive(isolated_roadmap, attempts=config.MAX_INFRA_ERRORS_PER_SPRINT)

        assert state.for_sprint("SA-2").infra_error_count >= config.MAX_INFRA_ERRORS_PER_SPRINT
        content = roadmap_state.ROADMAP_PATH.read_text(encoding="utf-8")
        assert "**Status**: blocked" in content, (
            f"after {config.MAX_INFRA_ERRORS_PER_SPRINT} consecutive infrastructure "
            "failures the sprint was still reset to todo, so it is re-picked forever "
            "and the rest of the queue waits behind it"
        )
        assert "consecutive infrastructure failures" in content

    def test_a_completed_phase_clears_the_count(self, isolated_roadmap: Path) -> None:
        """The counter means "consecutive", so a phase that actually ran --
        which proves the CLI, network and token are all up -- must reset it."""
        state = self._drive(isolated_roadmap, attempts=config.MAX_INFRA_ERRORS_PER_SPRINT - 1)
        assert state.for_sprint("SA-2").infra_error_count > 0

        roadmap_state.update_status("SA-2", config.STATUS_TODO)
        ok = PhaseResult(
            outcome=Outcome.OK,
            phase=Phase.PLAN,
            sprint_id="SA-2",
            log_path=isolated_roadmap / "t.log",
            reason="",
        )
        needs_rework = PhaseResult(
            outcome=Outcome.NEEDS_REWORK,
            phase=Phase.REVIEW,
            sprint_id="SA-2",
            log_path=isolated_roadmap / "t.log",
            reason="not yet",
        )
        with patch.object(agents, "run_phase", side_effect=[ok, ok, needs_rework] * 4):
            with patch.object(harness, "_run_quality_gates", return_value=None):
                harness.execute_sprint("SA-2", state)

        assert state.for_sprint("SA-2").infra_error_count == 0, (
            "a phase that actually completed did not clear the infrastructure counter, "
            "so unrelated blips accumulate across a seven-day run and eventually block "
            "a sprint that has nothing wrong with it"
        )


class TestAnInfrastructureOutageStopsTheRunAndIsReported:
    """The composed failure: ten sprints, every one infra_error, nothing
    accomplished -- and `main()` still returned 0, so the supervisor recorded
    a success, reset its counter, and relaunched 30 seconds later."""

    def _drive(
        self,
        isolated_roadmap: Path,
        monkeypatch: pytest.MonkeyPatch,
        outcomes: list[Outcome],
    ) -> tuple[int, str, list[str]]:
        (isolated_roadmap / "ROADMAP.md").write_text(_TWO_TODO_ROADMAP, encoding="utf-8")
        monkeypatch.setattr(harness.heartbeat, "HEARTBEAT_PATH", isolated_roadmap / "hb.json")
        monkeypatch.setattr(harness, "DRY_RUN", False)

        status_file = config.PROJECT_ROOT / "ralph" / "logs" / "_test_status_infra.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)
        monkeypatch.setattr(
            harness,
            "_run_git",
            lambda args, timeout=30: (0, "true\n", "")
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]
            else (0, "", ""),
        )
        monkeypatch.setattr(harness, "_capture_test_baseline", lambda: (10_774, 98))

        picked: list[str] = []
        queue = list(outcomes)

        def fake_execute(
            sprint_id: str, state: object, test_baseline: tuple[int, int] = (0, 0)
        ) -> Outcome:
            picked.append(sprint_id)
            assert queue, f"main() ran more sprints than scripted: {picked}"
            return queue.pop(0)

        monkeypatch.setattr(harness, "execute_sprint", fake_execute)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                str(len(outcomes)),
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-agency-probe",
            ],
        )
        try:
            rc = harness.main()
            content = status_file.read_text(encoding="utf-8") if status_file.exists() else ""
        finally:
            status_file.unlink(missing_ok=True)
        return rc, content, picked

    def test_consecutive_infra_errors_stop_the_run_with_a_nonzero_exit(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc, _content, picked = self._drive(isolated_roadmap, monkeypatch, [Outcome.INFRA_ERROR] * 4)

        assert rc == config.HARNESS_RC_INFRA_ERROR, (
            f"the harness exited {rc} after accomplishing nothing. On rc 0 the "
            "supervisor calls record_success(), resets its failure counter, and "
            "relaunches in 30 seconds -- for as long as the outage lasts"
        )
        assert len(picked) == config.MAX_CONSECUTIVE_INFRA_SPRINTS, (
            f"the harness kept picking up sprints during an outage: {picked}. Each one "
            "costs up to three agent invocations that cannot possibly succeed"
        )

    def test_the_outage_is_named_in_status_md(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _rc, content, _picked = self._drive(
            isolated_roadmap, monkeypatch, [Outcome.INFRA_ERROR] * 4
        )

        assert "## INFRASTRUCTURE FAILING" in content, (
            "STATUS.md carried the individual `infra_error` outcomes but never said "
            "the run had given up, or why -- the operator sees a queue that is not "
            "moving and no statement of the cause"
        )
        assert "INFRA-STOP" in content

    def test_an_isolated_infra_error_does_not_stop_the_run(
        self, isolated_roadmap: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control: a single blip between working sprints must not end a run.
        The counter is consecutive, so a success in between clears it."""
        rc, content, picked = self._drive(
            isolated_roadmap,
            monkeypatch,
            [Outcome.INFRA_ERROR, Outcome.OK, Outcome.INFRA_ERROR, Outcome.OK],
        )

        assert rc == 0
        assert len(picked) == 4, f"the run stopped early on an isolated blip: {picked}"
        assert "INFRASTRUCTURE FAILING" not in content


_ROADMAP_ONLY_WORK_IS_IN_FLIGHT = """\
# Test

### SA-1 — Finished sprint

**Status**: done
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)

### SA-2 — The sprint nobody finished

**Status**: in-progress (implementing)
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)
"""


class TestStrandedSprintIsNotCompletion:
    """M2, end to end: a sprint stranded in flight must not read as success.

    Everything the old code counted reads zero in this roadmap -- todo 0,
    eligible 0, blocked none -- so the harness logged "No eligible sprints; all
    work complete. Exiting cleanly", `should_restart` returned
    "stopping: all work complete", the supervisor recorded a DELIBERATE stop
    (which the repeating Scheduled Task trigger refuses to override), and
    STATUS.md rendered a calm, green, permanently-final page describing an
    abandoned sprint.
    """

    @pytest.mark.timeout(120)
    def test_the_harness_does_not_call_it_complete_and_says_so_in_status(
        self, isolated_roadmap, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        roadmap = isolated_roadmap / "ROADMAP.md"
        roadmap.write_text(_ROADMAP_ONLY_WORK_IS_IN_FLIGHT, encoding="utf-8")
        status_file = isolated_roadmap / "STATUS.md"
        monkeypatch.setattr(harness.status, "STATUS_PATH", status_file)
        # A real heartbeat read would probe a live PID over PowerShell; this
        # test is about the queue, not about liveness.
        monkeypatch.setattr(harness.heartbeat, "read_heartbeat", lambda: None)

        def fake_run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
            if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
                return (0, "true\n", "")
            return (0, "", "")

        monkeypatch.setattr(harness, "_run_git", fake_run_git)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ralph.harness",
                "--max-sprints",
                "1",
                "--dry-run",
                "--no-push",
                "--allow-dirty",
                "--skip-recovery",
                "--skip-baseline",
                "--skip-agency-probe",
            ],
        )

        rc = harness.main()

        assert rc == config.HARNESS_RC_OK
        logged = capsys.readouterr().out
        assert "all work complete" not in logged, (
            "SA-2 is marked in-progress and nobody is working on it. Reporting that "
            "as completion is the exact false statement Spec E was written to "
            f"eliminate, reached through a different door. Log was:\n{logged}"
        )
        assert "STRANDED" in logged
        assert "SA-2" in logged

        # And the operator, who only ever sees STATUS.md, must be told.
        assert status_file.exists(), "STATUS.md is the only window into an unattended run"
        content = status_file.read_text(encoding="utf-8")
        assert "## STRANDED" in content, (
            "a stranded sprint has to be VISIBLE, not silently end the run"
        )
        assert "SA-2" in content
        assert "in-progress (implementing)" in content

    def test_the_supervisor_relaunches_rather_than_stopping_for_good(
        self, isolated_roadmap
    ) -> None:
        """The same roadmap, through the supervisor's own decision function.

        Driven from `parse_sprints` -> `triage.analyse` -> `should_restart`
        rather than from a hand-built QueueState, so the three components have
        to agree with each other and not merely with the test.
        """
        (isolated_roadmap / "ROADMAP.md").write_text(
            _ROADMAP_ONLY_WORK_IS_IN_FLIGHT, encoding="utf-8"
        )
        queue = triage.analyse(roadmap_state.parse_sprints())

        assert queue.eligible == 0 and queue.todo == 0 and queue.blocked_ids == [], (
            "test setup: this must be the state that used to look like completion"
        )
        assert queue.in_flight == {"SA-2": "in-progress (implementing)"}
        assert queue.is_complete is False

        restart, reason = should_restart(
            consecutive_failures=0,
            eligible=queue.eligible,
            starved=queue.is_starved,
            consecutive_infra_failures=0,
            in_flight=queue.in_flight_count,
        )
        assert restart is True, (
            "stopping here records a deliberate stop, and a deliberate stop is what "
            "keeps the repeating Scheduled Task trigger from ever bringing the "
            "supervisor back -- the run is over, for a sprint nobody finished"
        )
        assert "complete" not in reason.lower()
