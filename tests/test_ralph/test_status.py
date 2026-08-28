"""Tests for STATUS.md rendering.

The bar is: can the operator tell from a beach whether it is working. Ralph
already pushes to origin, so a committed markdown file is readable on GitHub
from a phone with no app, no service, and nothing new to keep running.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ralph import status as status_module
from ralph.config import IN_PROGRESS_STALE_MINUTES
from ralph.status import CrashInfo, render_status
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


class TestStarvedBannerIsADistinctHeading:
    """`starvation_report()`'s own embedded text contains the word "STARVED",
    so a plain `assert "STARVED" in text` is satisfied even if the banner's
    own `## STARVED` heading is renamed or removed -- the embedded body text
    alone would still pass it. This asserts on the heading specifically, so a
    regression that quietly demotes the banner's prominence is caught.
    """

    def test_starved_heading_is_its_own_section(self) -> None:
        state = QueueState(total=2, todo=2, eligible=0)
        text = render_status(state, None, [])
        assert "## STARVED" in text


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


class TestStaleHeartbeat:
    """A heartbeat file can outlive the process that wrote it -- a reboot
    mid-sprint leaves it behind, and its age keeps climbing while nothing is
    running. This project has already been bitten by an indistinguishable
    stale beat once (SH-3 sat unnoticed for 19 hours), so a stale beat must
    be as visually obvious as STARVED, not identical formatting to a fresh
    one. Reuses `IN_PROGRESS_STALE_MINUTES` rather than a second threshold.
    """

    def test_stale_beat_is_flagged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        stale_seconds = IN_PROGRESS_STALE_MINUTES * 60 + 60  # just past the threshold
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - stale_seconds,
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "STALE" in text

    def test_fresh_beat_is_not_flagged_stale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - 240,  # 4 minutes -- nowhere near stale
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "STALE" not in text

    def test_stale_beat_gets_a_distinct_banner_section(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Not just inline text on the "Last beat" line -- a `##` section
        with the same prominence STARVED gets, so it survives a five-second
        phone squint rather than requiring the reader to parse a sentence.
        """
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        stale_seconds = IN_PROGRESS_STALE_MINUTES * 60 + 60
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - stale_seconds,
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "## STALE" in text

    def test_boundary_exactly_at_threshold_counts_as_stale(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - IN_PROGRESS_STALE_MINUTES * 60,
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "STALE" in text

    def test_just_under_threshold_is_not_stale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - (IN_PROGRESS_STALE_MINUTES * 60 - 1),
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "STALE" not in text

    def test_no_heartbeat_is_not_confused_with_stale(self) -> None:
        """Absent and stale are different failure modes -- absent means the
        harness (or its heartbeat thread) never wrote one this run; stale can
        mean the box rebooted mid-sprint and left the old file behind. They
        must stay visually distinguishable, not collapse into one signal.
        """
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [])
        assert "STALE" not in text


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


class TestCrashBanner:
    """Task 8 review round 2, Finding 1/2: the operator must be able to tell
    "exited cleanly with nothing to do" from "died on an unhandled
    exception" at a glance -- both would otherwise render the same calm
    queue summary. Assertions here target content unique to the crash
    (exception type, exception message, which sprint/phase was in flight),
    not just the presence of some heading that another section could also
    satisfy -- that exact mistake is what let Finding 3 (round 1) through.
    """

    def test_crash_shows_exception_type_and_message(self) -> None:
        crash = CrashInfo(
            exc_type="_SimulatedCrash",
            exc_message="boom-distinctive-crash-marker-77123",
            sprint="EXEC-1",
            phase="implement",
        )
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash=crash)
        assert "_SimulatedCrash" in text
        assert "boom-distinctive-crash-marker-77123" in text

    def test_crash_shows_which_sprint_and_phase_were_in_flight(self) -> None:
        crash = CrashInfo(
            exc_type="RuntimeError",
            exc_message="agent subprocess died",
            sprint="EXEC-1",
            phase="implement",
        )
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash=crash)
        assert "EXEC-1" in text
        assert "implement" in text

    def test_crash_is_its_own_distinct_banner_heading(self) -> None:
        crash = CrashInfo(exc_type="RuntimeError", exc_message="x", sprint=None, phase=None)
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash=crash)
        assert "## CRASHED" in text

    def test_no_crash_omits_the_banner_entirely(self) -> None:
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash=None)
        assert "## CRASHED" not in text
        assert "_SimulatedCrash" not in text

    def test_crash_with_no_sprint_in_flight_does_not_crash_the_renderer(self) -> None:
        """An exception before any sprint was picked (e.g. baseline capture)
        has no sprint/phase to report -- must still render, not raise."""
        crash = CrashInfo(exc_type="OSError", exc_message="disk full", sprint=None, phase=None)
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], crash=crash)
        assert "## CRASHED" in text
        assert "OSError" in text


class TestDeclineReason:
    """`return 2` / `return 3` paths (forced-sprint validation, baseline
    capture failure) are clean, intentional declines, not crashes -- but
    STATUS.md must still say why the harness didn't run, not just exist
    with a generic queue snapshot.
    """

    def test_decline_reason_is_shown(self) -> None:
        text = render_status(
            QueueState(total=1, todo=1, eligible=1),
            None,
            [],
            decline_reason="Forced sprint XYZ-9 not found. Aborting.",
        )
        assert "Forced sprint XYZ-9 not found. Aborting." in text

    def test_no_decline_reason_omits_the_section(self) -> None:
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [], decline_reason=None)
        assert "Did Not Run" not in text

    def test_decline_reason_and_crash_are_visually_distinct(self) -> None:
        """A decline is an intentional, clean abort; a crash is a bug. They
        must not collapse into the same banner wording."""
        text = render_status(
            QueueState(total=1, todo=1, eligible=1),
            None,
            [],
            decline_reason="Baseline capture FAILED: pytest exited 1. Aborting run.",
        )
        assert "## CRASHED" not in text


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


class TestPushStatusIsVisible:
    """A `git push` that starts failing freezes the board, silently.

    Push failure was handled correctly as non-fatal and then reported to a
    stream that, under the Scheduled Task, goes nowhere: STATUS.md carried no
    push field at all. The harness keeps working perfectly -- committing
    locally, rendering STATUS.md locally -- while the GitHub copy the operator
    reads from a beach is frozen at the moment of divergence. A frozen board
    and a dead machine look identical from GitHub, so the file itself has to
    say which one it is.
    """

    def _isolate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        target = tmp_path / "push_state.json"
        monkeypatch.setattr(status_module, "PUSH_STATE_PATH", target)
        return target

    def test_successful_push_is_stated_not_assumed(self) -> None:
        text = render_status(
            QueueState(total=2, todo=1, eligible=1),
            None,
            [],
            push=status_module.PushState(ok=True, timestamp=time.time()),
        )
        assert "## Push" in text
        assert "**OK**" in text
        assert "PUSH FAILING" not in text

    def test_failing_push_is_a_loud_banner(self) -> None:
        now = time.time()
        text = render_status(
            QueueState(total=2, todo=1, eligible=1),
            None,
            [],
            push=status_module.PushState(
                ok=False,
                timestamp=now,
                detail="! [rejected] master -> master (non-fast-forward)",
                last_success_timestamp=now - 7200,
                consecutive_failures=3,
            ),
        )
        assert "## PUSH FAILING" in text, (
            "a failing push freezes the GitHub copy of this file; without a "
            "banner the operator reads a stale board as a healthy one"
        )
        assert "non-fast-forward" in text, (
            "the failure reason must be in the file, not only in a log"
        )
        assert "2 hours ago" in text, (
            "the file must say when anything last actually reached GitHub, not "
            "merely that the last attempt failed"
        )

    def test_never_pushed_says_so_rather_than_implying_success(self) -> None:
        text = render_status(
            QueueState(total=2, todo=1, eligible=1),
            None,
            [],
            push=status_module.PushState(ok=False, timestamp=time.time(), consecutive_failures=1),
        )
        assert "**never**" in text

    def test_absent_push_state_is_stated_not_omitted(self) -> None:
        text = render_status(QueueState(total=2, todo=1, eligible=1), None, [])
        assert "no push recorded yet" in text

    def test_record_and_read_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._isolate(tmp_path, monkeypatch)

        status_module.record_push(True, now=100.0)
        state = status_module.read_push_state()

        assert state is not None
        assert state.ok and state.timestamp == 100.0
        assert state.last_success_timestamp == 100.0

    def test_failure_carries_the_last_success_forward(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The question that matters is 'when did anything last reach GitHub'."""
        self._isolate(tmp_path, monkeypatch)

        status_module.record_push(True, now=100.0)
        status_module.record_push(False, detail="rejected", now=200.0)
        status_module.record_push(False, detail="rejected", now=300.0)
        state = status_module.read_push_state()

        assert state is not None
        assert not state.ok
        assert state.last_success_timestamp == 100.0, (
            "a run of failures erased the last-successful-push timestamp, so "
            "STATUS.md can no longer say how stale the GitHub copy is"
        )
        assert state.consecutive_failures == 2

    def test_success_after_failures_resets_the_streak(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._isolate(tmp_path, monkeypatch)

        status_module.record_push(False, detail="rejected", now=100.0)
        status_module.record_push(True, now=200.0)
        state = status_module.read_push_state()

        assert state is not None
        assert state.ok and state.consecutive_failures == 0 and state.detail == ""

    def test_corrupt_push_state_reads_as_none_not_a_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = self._isolate(tmp_path, monkeypatch)
        target.write_text("{not json", encoding="utf-8")

        assert status_module.read_push_state() is None

    def test_write_status_picks_up_the_recorded_push_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No call site is in a position to pass it: the harness writes
        STATUS.md before it pushes, and the supervisor pushes after."""
        self._isolate(tmp_path, monkeypatch)
        monkeypatch.setattr(status_module, "STATUS_PATH", tmp_path / "STATUS.md")

        status_module.record_push(False, detail="! [rejected] non-fast-forward")
        status_module.write_status(QueueState(total=2, todo=1, eligible=1), None, [])

        content = (tmp_path / "STATUS.md").read_text(encoding="utf-8")
        assert "## PUSH FAILING" in content, (
            "write_status ignored the recorded push state, so the one file the "
            "operator reads cannot tell them the board is frozen"
        )
