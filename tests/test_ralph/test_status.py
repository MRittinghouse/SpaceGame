"""Tests for STATUS.md rendering.

The bar is: can the operator tell from a beach whether it is working. Ralph
already pushes to origin, so a committed markdown file is readable on GitHub
from a phone with no app, no service, and nothing new to keep running.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph import status as status_module
from ralph.status import render_status
from ralph.triage import QueueState


class TestRenderStatus:
    def test_shows_current_sprint_and_phase(self) -> None:
        beat = {"pid": 1, "timestamp": 0.0, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=3, todo=1, eligible=1), beat, [])
        assert "SH-2" in text and "implement" in text

    def test_starvation_is_a_loud_banner(self) -> None:
        state = QueueState(
            total=16,
            todo=15,
            eligible=0,
            blocked_ids=["SA-F2"],
            stranded_by={"SA-F2": ["SA-F3", "SA-F4"]},
        )
        text = render_status(state, None, [])
        assert "STARVED" in text
        assert "SA-F2" in text and "SA-F3" in text

    def test_healthy_queue_has_no_starved_banner(self) -> None:
        text = render_status(QueueState(total=2, todo=1, eligible=1), None, [])
        assert "STARVED" not in text

    def test_missing_heartbeat_is_stated_not_omitted(self) -> None:
        """Silence must not read as health -- an absent heartbeat is a fact
        worth showing, since it is what a dead harness looks like."""
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [])
        assert "no heartbeat" in text.lower()

    def test_recent_outcomes_are_listed(self) -> None:
        text = render_status(
            QueueState(total=2, todo=0, eligible=0), None, ["SH-2 ok", "SUITE-2 ok"]
        )
        assert "SH-2 ok" in text and "SUITE-2 ok" in text


class TestHeartbeatAgeInHumanTerms:
    """A raw timestamp or a bare seconds count makes the reader do arithmetic
    on a phone. STATUS.md must do that arithmetic itself.
    """

    def test_age_rendered_in_human_terms(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - 240,  # 4 minutes before the frozen "now"
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "4 minutes ago" in text
        # The bar is human terms, not extra arithmetic -- a bare "240" (raw
        # seconds) must not be the only representation of the age.
        assert "240s ago" not in text

    def test_very_fresh_beat_reads_just_now(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {"pid": 1, "timestamp": 1_000_000.0 - 2, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "just now" in text

    def test_unparseable_timestamp_does_not_crash(self) -> None:
        beat = {"pid": 1, "timestamp": "not-a-number", "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        # Must still render the rest of the picture rather than raising.
        assert "SH-2" in text


class TestCrashLoopBanner:
    def test_crash_loop_is_a_banner(self) -> None:
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash_loop=True)
        assert "CRASH-LOOP" in text

    def test_no_crash_loop_omits_banner(self) -> None:
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash_loop=False)
        assert "CRASH-LOOP" not in text


class TestBlocksDrift:
    """`triage.blocks_disagreements()` (Task 7) had no recurring call site --
    STATUS.md is written every sprint boundary, so it is the natural home.
    This is a cross-check that reports only; it must never gate scheduling.
    """

    def test_count_and_first_lines_are_shown(self) -> None:
        disagreements = [f"SPRINT-{i}: disagreement number {i}" for i in range(7)]
        text = render_status(
            QueueState(total=1, todo=0, eligible=0), None, [], disagreements=disagreements
        )
        assert "7 disagreement" in text
        assert "SPRINT-0: disagreement number 0" in text
        assert "SPRINT-4: disagreement number 4" in text

    def test_list_is_capped_not_exhaustive(self) -> None:
        disagreements = [f"SPRINT-{i}: disagreement number {i}" for i in range(7)]
        text = render_status(
            QueueState(total=1, todo=0, eligible=0), None, [], disagreements=disagreements
        )
        # Only the first few lines -- the sixth and seventh are summarized,
        # not printed in full, or a five-second phone check becomes a scroll.
        assert "SPRINT-5: disagreement number 5" not in text
        assert "SPRINT-6: disagreement number 6" not in text
        assert "+2 more" in text

    def test_zero_disagreements_states_zero_not_silence(self) -> None:
        text = render_status(QueueState(total=1, todo=0, eligible=0), None, [], disagreements=[])
        assert "0 disagreement" in text

    def test_states_it_is_a_cross_check_not_a_gate(self) -> None:
        text = render_status(
            QueueState(total=1, todo=0, eligible=0), None, [], disagreements=["X: drift"]
        )
        assert "does not affect scheduling" in text


class TestWriteStatus:
    def test_write_status_uses_atomic_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "STATUS.md"
        monkeypatch.setattr(status_module, "STATUS_PATH", target)

        calls: list[Path] = []
        real_atomic_write = status_module.atomic_write

        def spy(path: Path, text: str) -> None:
            calls.append(path)
            real_atomic_write(path, text)

        monkeypatch.setattr(status_module, "atomic_write", spy)

        status_module.write_status(QueueState(total=2, todo=1, eligible=1), None, ["SH-1 ok"])

        assert calls == [target], "write_status must delegate to atomic_write, not write_text"
        content = target.read_text(encoding="utf-8")
        assert "SH-1 ok" in content
        assert not target.with_name(target.name + ".tmp").exists()
