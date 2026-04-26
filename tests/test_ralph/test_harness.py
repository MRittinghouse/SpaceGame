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
        state.sprints["SA-1"] = SprintState(
            sprint_id="SA-1", last_touched_at=old_ts
        )
        recovered = harness._recover_stuck_sprints(state)
        assert recovered == 1
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-1"].status == "todo"

    def test_recent_in_progress_sprint_skipped(self, isolated_roadmap) -> None:
        # SA-1 is in-progress, last touched 5 minutes ago (within stale threshold).
        state = HarnessState()
        recent_ts = (datetime.now() - timedelta(minutes=5)).isoformat()
        state.sprints["SA-1"] = SprintState(
            sprint_id="SA-1", last_touched_at=recent_ts
        )
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
