"""Tests for STATUS.md rendering.

The bar is: can the operator tell from a beach whether it is working. Ralph
already pushes to origin, so a committed markdown file is readable on GitHub
from a phone with no app, no service, and nothing new to keep running.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from ralph import status as status_module
from ralph import supervisor as supervisor_module
from ralph.config import HEARTBEAT_STALE_SECONDS, IN_PROGRESS_STALE_MINUTES
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
    one.

    The threshold is `HEARTBEAT_STALE_SECONDS` -- the SAME number the
    supervisor kills at. It used to be `IN_PROGRESS_STALE_MINUTES` (3600s, six
    times larger), so for fifty minutes a run the supervisor already considered
    dead rendered here with no STALE banner at all (M1).
    """

    def test_stale_beat_is_flagged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        stale_seconds = HEARTBEAT_STALE_SECONDS + 60  # just past the threshold
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
        stale_seconds = HEARTBEAT_STALE_SECONDS + 60
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
            "timestamp": 1_000_000.0 - HEARTBEAT_STALE_SECONDS,
            "sprint": "SH-2",
            "phase": "implement",
        }
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "STALE" in text

    def test_just_under_threshold_is_not_stale(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {
            "pid": 1,
            "timestamp": 1_000_000.0 - (HEARTBEAT_STALE_SECONDS - 1),
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


class TestGateFailureBanner:
    """H3: a red tree is the one state where the correct response is to stop
    authoring, so it must be as loud as STARVED and it must reach GitHub.

    Without this the harness stops on a red tree and STATUS.md renders the same
    calm queue summary a clean exit produces -- and the only other channel,
    `log()`, writes to a stdout the Scheduled Task discards.
    """

    def test_a_gate_failure_is_a_loud_banner_naming_what_broke(self) -> None:
        text = render_status(
            QueueState(total=5, todo=3, eligible=3),
            None,
            [],
            gate_failure="SA-7: test-suite gate FAILED: 3 failed in tests/test_models/test_market.py",
        )
        assert "## TEST SUITE FAILING" in text
        assert "SA-7" in text, "the banner does not name the sprint whose gate failed"
        assert "test_market" in text, "the banner does not say which tests broke"

    def test_no_banner_when_the_suite_is_green(self) -> None:
        """Control: this banner must mean something. If it rendered
        unconditionally the operator would learn to ignore it."""
        text = render_status(QueueState(total=5, todo=3, eligible=3), None, [])
        assert "TEST SUITE FAILING" not in text

    def test_write_status_carries_the_gate_failure_through(self, tmp_path: Path) -> None:
        """`render_status` is the pure function; `write_status` is what the
        harness actually calls, and a parameter dropped in between would make
        the banner unreachable in production while every render test passed."""
        target = tmp_path / "STATUS.md"
        status_module.STATUS_PATH = target
        try:
            status_module.write_status(
                QueueState(total=1, todo=1, eligible=1),
                None,
                [],
                gate_failure="SA-9: test-suite gate FAILED: 1 failed",
                push=None,
            )
        finally:
            status_module.STATUS_PATH = status_module.PROJECT_ROOT / "STATUS.md"
        assert "## TEST SUITE FAILING" in target.read_text(encoding="utf-8")


class TestInfrastructureBanner:
    """H4: `## Recent` already rendered the individual `infra_error` outcomes,
    so the failure was not silent -- but nothing said the run had GIVEN UP, or
    why, or that the supervisor is now backing off rather than retrying. The
    operator saw a queue that had stopped moving with no statement of cause.
    """

    def test_an_infrastructure_stop_is_a_loud_banner(self) -> None:
        text = render_status(
            QueueState(total=5, todo=5, eligible=5),
            None,
            [],
            infra_failure="2 consecutive sprints failed with infra_error (most recently SA-4).",
        )
        assert "## INFRASTRUCTURE FAILING" in text
        assert "SA-4" in text
        assert "not because of anything in the repo" in text, (
            "the banner does not tell the operator this is an outage rather than a "
            "code problem, which is the whole diagnostic value of separating it"
        )

    def test_no_banner_on_a_healthy_run(self) -> None:
        text = render_status(QueueState(total=5, todo=5, eligible=5), None, [])
        assert "INFRASTRUCTURE FAILING" not in text

    def test_the_crash_loop_banner_carries_the_supervisors_reason(self) -> None:
        """ "3 consecutive failures" and "6 consecutive infrastructure failures"
        call for entirely different responses; the banner said neither."""
        text = render_status(
            QueueState(total=5, todo=5, eligible=5),
            None,
            [],
            crash_loop=True,
            crash_loop_reason="stopping: 6 consecutive infrastructure failures",
        )
        assert "## CRASH-LOOP" in text
        assert "6 consecutive infrastructure failures" in text
        assert "Nothing will resume until a human intervenes." in text

    def test_the_crash_loop_banner_still_renders_without_a_reason(self) -> None:
        text = render_status(QueueState(total=5, todo=5, eligible=5), None, [], crash_loop=True)
        assert "## CRASH-LOOP" in text


class TestTheStaleThresholdIsTheSupervisorsThreshold:
    """M1: one constant, three meanings.

    `supervisor.HEARTBEAT_STALE_SECONDS` (600s, kill a wedged harness),
    `status.py`'s STALE banner (was IN_PROGRESS_STALE_MINUTES * 60 = 3600s) and
    `_recover_stuck_sprints` (60 minutes) all read as "how long is too long",
    and the first two are the SAME question asked by two components. They now
    share one constant; the third is a different question (how long may a
    ROADMAP entry claim to be in-progress) and keeps its own.
    """

    def test_status_and_supervisor_agree(self) -> None:
        assert status_module.HEARTBEAT_STALE_SECONDS == supervisor_module.HEARTBEAT_STALE_SECONDS, (
            "STATUS.md flags a stale beat at a different age than the supervisor kills "
            "at, so there is a window in which a run the supervisor has already given "
            "up on renders on the operator's phone as healthy"
        )

    def test_a_beat_the_supervisor_would_kill_is_flagged_here(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The property, stated end to end rather than as a constant
        comparison: any beat old enough to be killed must be flagged."""
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        age = supervisor_module.HEARTBEAT_STALE_SECONDS + 1
        beat = {"pid": 1, "timestamp": 1_000_000.0 - age, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [])
        assert "## STALE HEARTBEAT" in text

    def test_the_recovery_threshold_is_deliberately_separate(self) -> None:
        """Not merged: `_recover_stuck_sprints` gates a destructive action
        (resetting a sprint another run may own) against Activity-log
        timestamps, not against the heartbeat. Pinned so a future tidy-up
        collapses them only on purpose."""
        assert IN_PROGRESS_STALE_MINUTES * 60 > HEARTBEAT_STALE_SECONDS


class TestPidLivenessInStatus:
    """M1: `status.py` checked beat age but never beat PID.

    Ruling 16 established PID liveness as the correct discriminator and
    `supervisor.heartbeat_pid_alive()` already implements it, but the one
    module whose job is "tell the operator whether a run is live" used the
    signal the ledger ruled insufficient. `status.py`'s own docstring cites "a
    reboot mid-sprint leaves it behind" -- and a reboot is exactly when the
    leftover beat's age is SMALL, so the age guard never fires for it.
    """

    def test_a_dead_pid_is_a_banner_even_when_the_beat_is_fresh(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {"pid": 4321, "timestamp": 999_990.0, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [], pid_alive=False)
        assert "## NO LIVE HARNESS" in text, (
            "a 10-second-old heartbeat naming a dead process rendered as a healthy run "
            "-- which is precisely the post-reboot case this file claims to cover"
        )
        assert "NOT RUNNING" in text

    def test_a_live_pid_is_stated_not_banner(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {"pid": 4321, "timestamp": 999_990.0, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [], pid_alive=True)
        assert "NO LIVE HARNESS" not in text
        assert "alive" in text

    def test_an_undetermined_pid_says_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A probe that could not run must never read as "dead" -- that would
        put a false CRASHED-grade banner on a perfectly healthy run."""
        monkeypatch.setattr(status_module.time, "time", lambda: 1_000_000.0)
        beat = {"pid": 4321, "timestamp": 999_990.0, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=1, todo=1, eligible=1), beat, [], pid_alive=None)
        assert "NO LIVE HARNESS" not in text
        assert "Beat PID" not in text

    def test_our_own_pid_needs_no_probe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The harness writes STATUS.md from inside the process the beat names,
        many times per run. Probing it would spawn a PowerShell per write for
        an answer that is knowable for free."""
        spawned: list[int] = []

        def _boom(pid: int) -> bool:
            spawned.append(pid)
            raise AssertionError("should not have probed our own pid")

        monkeypatch.setattr(supervisor_module, "is_harness_alive", _boom)
        assert status_module.beat_pid_liveness({"pid": os.getpid()}) is True, (
            "the render probed the process it is running inside, which spawns a "
            "PowerShell per STATUS.md write for an answer that is knowable for free"
        )
        assert spawned == []

    def test_an_unusable_pid_field_is_unknown(self) -> None:
        assert status_module.beat_pid_liveness({}) is None
        assert status_module.beat_pid_liveness({"pid": "nope"}) is None
        assert status_module.beat_pid_liveness({"pid": 0}) is None

    def test_a_probe_that_raises_is_unknown_not_dead(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(pid: int) -> bool:
            raise OSError("WMI unavailable")

        monkeypatch.setattr(supervisor_module, "is_harness_alive", _raise)
        assert status_module.beat_pid_liveness({"pid": os.getpid() + 100_000}) is None, (
            "a liveness probe that could not run reported the harness as DEAD, which "
            "puts a NO LIVE HARNESS banner on a perfectly healthy run"
        )

    def test_write_status_fills_in_liveness_for_the_caller(self, tmp_path: Path) -> None:
        """No call site is placed to know, so `write_status` must probe. If it
        did not, the banner would be unreachable in production while every
        render test above stayed green."""
        target = tmp_path / "STATUS.md"
        original = status_module.STATUS_PATH
        status_module.STATUS_PATH = target
        try:
            status_module.write_status(
                QueueState(total=1, todo=1, eligible=1),
                {"pid": os.getpid(), "timestamp": time.time(), "sprint": "X", "phase": "plan"},
                [],
                push=None,
            )
        finally:
            status_module.STATUS_PATH = original
        assert "Beat PID" in target.read_text(encoding="utf-8")
