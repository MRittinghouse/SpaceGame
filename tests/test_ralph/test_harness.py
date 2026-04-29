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
