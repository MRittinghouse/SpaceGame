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

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import MagicMock, patch

import pytest

from ralph import agents, config, harness, roadmap_state, triage
from ralph.agents import Outcome, Phase, PhaseContext, PhaseResult
from ralph.harness import HarnessState, SprintState

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
        ) -> None:
            calls.append(
                {
                    "queue": queue,
                    "beat": beat,
                    "recent": recent,
                    "disagreements": disagreements,
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
        with patch.object(harness, "_pid_alive", return_value=True):
            result = harness._acquire_lock()
        assert result is False

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
