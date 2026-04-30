"""Tests for ralph.harness.

Covers:
  - Stuck-sprint recovery logic
  - Lock acquisition / release
  - State persistence

We don't test the full main loop end-to-end (that requires real
subprocess invocations); instead we exercise the recovery + lock
helpers in isolation.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ralph import config, harness, roadmap_state
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
    """Point ROADMAP_PATH at a temp file. Reset state.json + lock file."""
    roadmap_file = tmp_path / "ROADMAP.md"
    roadmap_file.write_text(_ROADMAP_WITH_STUCK, encoding="utf-8")
    monkeypatch.setattr(roadmap_state, "ROADMAP_PATH", roadmap_file)

    state_file = tmp_path / "state.json"
    monkeypatch.setattr(config, "STATE_FILE", state_file)
    monkeypatch.setattr(harness, "STATE_FILE", state_file)

    lock_file = tmp_path / ".running"
    monkeypatch.setattr(config, "LOCK_FILE", lock_file)
    monkeypatch.setattr(harness, "LOCK_FILE", lock_file)

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
        from ralph.config import ROADMAP_PATH

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
        import json
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
        import json
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
        import os

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
