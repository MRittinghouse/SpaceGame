"""Tests for the restart policy.

The supervisor is the only thing with nothing supervising it, so it stays as
dumb as possible: start a process, watch a file, apply a policy, never touch the
repo. Every feature added here is a feature that can fail unwatched.

The policy is tested as pure functions; the process loop around them is
deliberately thin.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

from ralph import heartbeat as heartbeat_module
from ralph import status as status_module
from ralph import supervisor
from ralph.supervisor import (
    RestartPolicy,
    backoff_seconds,
    harness_exited_silently,
    is_harness_alive,
    looks_like_ralph_process,
    should_restart,
    silent_exit_reason,
)
from ralph.triage import QueueState


class TestBackoff:
    def test_escalates(self) -> None:
        assert backoff_seconds(0) == 30
        assert backoff_seconds(1) == 120
        assert backoff_seconds(2) == 480

    def test_caps_at_final_step(self) -> None:
        assert backoff_seconds(99) == 480


class TestShouldRestart:
    def test_restarts_when_work_remains(self) -> None:
        ok, _ = should_restart(consecutive_failures=0, eligible=3, starved=False)
        assert ok is True

    def test_stops_after_three_consecutive_failures(self) -> None:
        ok, reason = should_restart(consecutive_failures=3, eligible=3, starved=False)
        assert ok is False
        assert "consecutive" in reason.lower()

    def test_stops_when_starved(self) -> None:
        """Restarting into starvation burns a week of API budget achieving
        nothing -- the harness would pick up no sprint and exit, forever."""
        ok, reason = should_restart(consecutive_failures=0, eligible=0, starved=True)
        assert ok is False
        assert "starved" in reason.lower()

    def test_stops_when_all_work_complete(self) -> None:
        ok, reason = should_restart(consecutive_failures=0, eligible=0, starved=False)
        assert ok is False
        assert "complete" in reason.lower()


class TestRestartPolicy:
    """A dumb counter, deliberately: consecutive failures reset on success
    rather than decaying on a wall-clock timer, so a policy object's state is
    fully determined by the sequence of record_* calls -- easy to reason
    about after a week of unattended restarts.
    """

    def test_starts_at_zero_and_not_exhausted(self) -> None:
        policy = RestartPolicy()
        assert policy.consecutive_failures == 0
        assert policy.exhausted is False

    def test_record_failure_increments(self) -> None:
        policy = RestartPolicy()
        policy.record_failure()
        policy.record_failure()
        assert policy.consecutive_failures == 2

    def test_record_success_resets_to_zero(self) -> None:
        policy = RestartPolicy()
        policy.record_failure()
        policy.record_failure()
        policy.record_success()
        assert policy.consecutive_failures == 0

    def test_exhausted_matches_max_consecutive_failures(self) -> None:
        policy = RestartPolicy()
        for _ in range(supervisor.MAX_CONSECUTIVE_FAILURES - 1):
            policy.record_failure()
        assert policy.exhausted is False
        policy.record_failure()
        assert policy.exhausted is True

    def test_one_success_after_two_failures_avoids_the_cap(self) -> None:
        """The scenario the reset exists for: two bad runs, then one good
        one, then two more bad runs should NOT trip the cap -- only three
        bad runs in a row with no success between them should."""
        policy = RestartPolicy()
        policy.record_failure()
        policy.record_failure()
        policy.record_success()
        policy.record_failure()
        policy.record_failure()
        assert policy.exhausted is False


class TestLooksLikeRalphProcess:
    """Pure identity rule, tested without spawning anything: does a command
    line identify the ralph harness. This is the rule that stands between
    "PID exists" and "PID is provably ralph" -- the recycled-PID guard.
    """

    def test_matches_realistic_harness_command_line(self) -> None:
        assert looks_like_ralph_process(
            r"C:\Python313\python.exe -m ralph.harness --max-sprints 10"
        )

    def test_matches_case_insensitively(self) -> None:
        assert looks_like_ralph_process(r"C:\Python313\PYTHON.EXE -M RALPH.HARNESS")

    def test_unrelated_process_does_not_match(self) -> None:
        """The exact scenario a recycled PID produces: some other process
        (here, explorer.exe) now owns the PID a stale heartbeat once named."""
        assert not looks_like_ralph_process(r"C:\Windows\explorer.exe")

    def test_unrelated_python_process_does_not_match(self) -> None:
        """Being Python is not enough -- must be *this* Python invocation."""
        assert not looks_like_ralph_process(r"C:\Python313\python.exe -m pytest")

    def test_none_command_line_does_not_match(self) -> None:
        assert not looks_like_ralph_process(None)

    def test_empty_command_line_does_not_match(self) -> None:
        assert not looks_like_ralph_process("")


@pytest.mark.timeout(30)
class TestIsHarnessAliveRealProcesses:
    """Real, unmocked Windows processes -- pid existence alone must never be
    sufficient; identity (the process's own command line) must also match.

    Both directions are exercised on a process this test itself spawns and
    controls, so "the pid happens not to exist on this machine" cannot be
    the reason either assertion passes.
    """

    def test_live_pid_running_ralph_marker_reads_alive(self) -> None:
        # The extra positional arg becomes part of the real Windows command
        # line (visible via WMI) without needing to actually import ralph.
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)", "ralph.harness"]
        )
        try:
            assert is_harness_alive(proc.pid) is True
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    def test_dead_pid_reads_as_not_alive(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)", "ralph.harness"]
        )
        proc.terminate()
        proc.wait(timeout=10)
        # Same identity marker, same pid -- only liveness changed. If this
        # read True, a genuinely dead run would be mistaken for alive and
        # the supervisor would refuse to ever restart it.
        assert is_harness_alive(proc.pid) is False

    def test_live_pid_not_running_ralph_reads_as_not_alive(self) -> None:
        """The recycled-pid scenario, made real: a live process exists at
        this pid, but it is not ralph. Existence must not be read as
        liveness of the harness."""
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
        try:
            assert is_harness_alive(proc.pid) is False
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    def test_pid_zero_or_negative_is_never_alive(self) -> None:
        assert is_harness_alive(0) is False
        assert is_harness_alive(-1) is False


class TestHarnessExitedSilently:
    """`harness.main()` writes STATUS.md in its outer `finally` -- but two
    exits (pre-flight failure, lock conflict) happen before that `try` even
    starts. An unchanged STATUS.md mtime is that signature.
    """

    def test_unchanged_mtime_is_silent(self) -> None:
        assert harness_exited_silently(123.0, 123.0) is True

    def test_advanced_mtime_is_not_silent(self) -> None:
        assert harness_exited_silently(123.0, 456.0) is False

    def test_never_existed_before_or_after_is_silent(self) -> None:
        assert harness_exited_silently(None, None) is True

    def test_newly_created_is_not_silent(self) -> None:
        """STATUS.md did not exist before this run and does after -- the
        harness reached its finally block for the first time ever."""
        assert harness_exited_silently(None, 999.0) is False


class TestSilentExitReason:
    """Lock-acquisition failure is normal (another instance is already
    running) and must stay quiet. A pre-flight failure must be reported,
    including the exit code, or a repeating failure is silent for 7 days.
    """

    def test_lock_held_by_live_instance_is_quiet(self) -> None:
        assert silent_exit_reason(2, lock_holder_alive=True) is None

    def test_no_live_lock_holder_reports_with_exit_code(self) -> None:
        reason = silent_exit_reason(2, lock_holder_alive=False)
        assert reason is not None
        assert "2" in reason

    def test_reports_the_actual_exit_code_not_a_placeholder(self) -> None:
        reason = silent_exit_reason(7, lock_holder_alive=False)
        assert reason is not None
        assert "7" in reason
        assert "code 7" in reason


class TestKillTree:
    """The real OS-level kill this supervisor relies on to recover from a
    hung harness. Uses `proc.wait(timeout=...)` rather than a bare wall-clock
    assertion, so a no-op kill fails on the wait() timeout, not silently.
    """

    @pytest.mark.timeout(30)
    def test_kills_a_real_process_tree(self) -> None:
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        supervisor._kill_tree(proc.pid)
        # If _kill_tree did nothing, this raises TimeoutExpired rather than
        # silently passing -- the failure names the real problem.
        returncode = proc.wait(timeout=10)
        assert returncode is not None


class _FakeProc:
    """Minimal stand-in for subprocess.Popen, for testing `_supervise`'s
    decision logic (when to poll, when to kill) without a real subprocess."""

    def __init__(self, pid: int, exit_after_polls: int) -> None:
        self.pid = pid
        self._polls = 0
        self._exit_after = exit_after_polls
        self.wait_called = False

    def poll(self) -> Optional[int]:
        self._polls += 1
        return 0 if self._polls > self._exit_after else None

    def wait(self) -> int:
        self.wait_called = True
        return 0


class TestSupervise:
    def test_kills_on_stale_heartbeat(self) -> None:
        proc = _FakeProc(pid=4321, exit_after_polls=10_000)
        killed: list[int] = []
        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: 700.0,  # always past the 600s threshold
            kill=lambda pid: killed.append(pid),
        )
        assert killed == [4321]
        assert proc.wait_called is True

    def test_no_kill_when_heartbeat_stays_fresh(self) -> None:
        proc = _FakeProc(pid=4321, exit_after_polls=3)
        killed: list[int] = []
        rc = supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: 5.0,  # nowhere near stale
            kill=lambda pid: killed.append(pid),
        )
        assert killed == []
        assert rc == 0

    def test_absent_heartbeat_never_triggers_kill(self) -> None:
        """`beat_age` returning None (no heartbeat file at all) must not be
        misread as "infinitely stale" -- that would kill a harness before
        its heartbeat thread has even written its first beat."""
        proc = _FakeProc(pid=4321, exit_after_polls=3)
        killed: list[int] = []
        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: None,
            kill=lambda pid: killed.append(pid),
        )
        assert killed == []

    @pytest.mark.timeout(15)
    def test_real_fast_exiting_process_returns_its_own_code(self) -> None:
        """No fakes: a real, quick subprocess with no heartbeat at all.
        `_supervise` must return its actual exit code and never touch kill,
        since a missing heartbeat is not the same as a stale one."""
        proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(7)"])
        killed: list[int] = []
        rc = supervisor._supervise(
            proc,
            poll_interval=0.02,
            stale_seconds=600.0,
            sleep=time.sleep,
            beat_age=lambda: None,
            kill=lambda pid: killed.append(pid),
        )
        assert rc == 7
        assert killed == []


class TestWaitForForeignHarness:
    """`main()`'s startup path adopts an already-alive harness rather than
    double-launching one; this is the poll loop that watches it. Same
    dependency-injection pattern as `_supervise`, tested without real
    600-second waits.
    """

    def test_returns_when_the_process_dies_on_its_own(self) -> None:
        alive_sequence = iter([True, True, False])
        killed: list[int] = []
        supervisor._wait_for_foreign_harness(
            9999,
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _s: None,
            alive=lambda pid: next(alive_sequence),
            beat_age=lambda: 5.0,  # fresh -- never stale
            kill=lambda pid: killed.append(pid),
        )
        assert killed == [], "a process that exits on its own must not be killed"

    def test_kills_when_heartbeat_goes_stale(self) -> None:
        killed: list[int] = []
        supervisor._wait_for_foreign_harness(
            9999,
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _s: None,
            alive=lambda pid: True,  # still running the whole time
            beat_age=lambda: 700.0,  # always past the threshold
            kill=lambda pid: killed.append(pid),
        )
        assert killed == [9999]

    def test_absent_heartbeat_never_triggers_kill(self) -> None:
        calls = {"n": 0}

        def alive(pid: int) -> bool:
            calls["n"] += 1
            return calls["n"] <= 3

        killed: list[int] = []
        supervisor._wait_for_foreign_harness(
            9999,
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _s: None,
            alive=alive,
            beat_age=lambda: None,
            kill=lambda pid: killed.append(pid),
        )
        assert killed == []


class TestReadLockPid:
    def test_reads_pid_from_lock_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        lock = tmp_path / ".running"
        lock.write_text("54321", encoding="utf-8")
        monkeypatch.setattr(supervisor, "LOCK_FILE", lock)
        assert supervisor._read_lock_pid() == 54321

    def test_missing_lock_file_reads_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(supervisor, "LOCK_FILE", tmp_path / "absent")
        assert supervisor._read_lock_pid() is None

    def test_corrupt_lock_file_reads_as_none_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        lock = tmp_path / ".running"
        lock.write_text("not-a-pid", encoding="utf-8")
        monkeypatch.setattr(supervisor, "LOCK_FILE", lock)
        assert supervisor._read_lock_pid() is None


class TestHeartbeatPidAlive:
    """Composes heartbeat.read_heartbeat() with is_harness_alive() -- the
    check the main loop uses to decide whether to adopt an already-running
    harness instead of double-launching one."""

    def test_no_heartbeat_reads_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat_module, "HEARTBEAT_PATH", tmp_path / "absent.json")
        assert supervisor.heartbeat_pid_alive() is None

    def test_heartbeat_naming_a_dead_pid_reads_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat_module, "HEARTBEAT_PATH", tmp_path / "hb.json")
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)", "ralph.harness"]
        )
        proc.terminate()
        proc.wait(timeout=10)
        heartbeat_module.write_heartbeat(sprint="SH-2", phase="implement")
        # Overwrite with the now-dead pid to simulate a beat left behind by
        # a process that has since died (e.g. a power cut).
        import json

        payload = json.loads(heartbeat_module.HEARTBEAT_PATH.read_text(encoding="utf-8"))
        payload["pid"] = proc.pid
        heartbeat_module.HEARTBEAT_PATH.write_text(json.dumps(payload), encoding="utf-8")
        assert supervisor.heartbeat_pid_alive() is None

    def test_heartbeat_naming_a_live_ralph_pid_reads_as_alive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat_module, "HEARTBEAT_PATH", tmp_path / "hb.json")
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)", "ralph.harness"]
        )
        try:
            heartbeat_module.write_heartbeat(sprint="SH-2", phase="implement")
            import json

            payload = json.loads(heartbeat_module.HEARTBEAT_PATH.read_text(encoding="utf-8"))
            payload["pid"] = proc.pid
            heartbeat_module.HEARTBEAT_PATH.write_text(json.dumps(payload), encoding="utf-8")
            assert supervisor.heartbeat_pid_alive() == proc.pid
        finally:
            proc.terminate()
            proc.wait(timeout=10)


class TestReportSilentExit:
    """`_report_silent_exit` is the actual call site: reads the lock file,
    checks liveness, and only writes STATUS.md's decline_reason when the
    silence is NOT a normal lock conflict.
    """

    def _isolated_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        target = tmp_path / "STATUS.md"
        monkeypatch.setattr(status_module, "STATUS_PATH", target)
        return target

    def test_no_lock_file_reports_pre_flight_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = self._isolated_status(tmp_path, monkeypatch)
        monkeypatch.setattr(supervisor, "LOCK_FILE", tmp_path / "absent-lock")
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=0, todo=0, eligible=0)
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

        supervisor._report_silent_exit(2, [])

        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "code 2" in content

    def test_live_lock_holder_stays_quiet(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = self._isolated_status(tmp_path, monkeypatch)
        lock = tmp_path / ".running"
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)", "ralph.harness"]
        )
        try:
            lock.write_text(str(proc.pid), encoding="utf-8")
            monkeypatch.setattr(supervisor, "LOCK_FILE", lock)

            supervisor._report_silent_exit(2, [])

            # Genuine lock conflict: no STATUS.md write at all.
            assert not target.exists()
        finally:
            proc.terminate()
            proc.wait(timeout=10)


class TestMainProcessLoop:
    """Thin integration tests of `main()`'s wiring: real subprocesses and
    real backoff sleeps are replaced so these run instantly, but the actual
    should_restart / RestartPolicy / status.write_status call sites are
    exercised for real -- only their I/O edges (Popen, _supervise, parsed
    sprints, the clock) are faked.
    """

    def _wire_common(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        supervise_rc: int,
        eligible: int,
        starved: bool = False,
    ) -> list[dict[str, object]]:
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: supervise_rc)

        # Distinct, increasing mtimes on every call so harness_exited_silently
        # is always False -- this suite isolates the crash-loop/should_restart
        # wiring from the (separately tested) silent-exit reporting path.
        mtimes = iter(range(1, 10_000))
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: next(mtimes))

        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage,
            "analyse",
            lambda sprints: QueueState(total=5, todo=5, eligible=eligible)
            if not starved
            else QueueState(total=5, todo=5, eligible=0),
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

        write_calls: list[dict[str, object]] = []

        def spy_write_status(queue: object, beat: object, recent: object, **kwargs: object) -> None:
            write_calls.append(kwargs)

        monkeypatch.setattr(supervisor.status, "write_status", spy_write_status)
        return write_calls

    def test_stops_and_writes_crash_loop_after_three_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_calls = self._wire_common(monkeypatch, supervise_rc=1, eligible=5)

        rc = supervisor.main()

        assert rc == 0
        assert len(write_calls) == 1, f"expected exactly one STATUS.md write, got {write_calls}"
        assert write_calls[0].get("crash_loop") is True

    def test_stops_cleanly_when_work_completes_no_crash_loop_write(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single successful run with nothing left eligible must stop
        without ever touching the crash-loop STATUS.md path -- a clean,
        expected exit must not look like a crash to the operator."""
        write_calls = self._wire_common(monkeypatch, supervise_rc=0, eligible=0)

        rc = supervisor.main()

        assert rc == 0
        assert write_calls == [], "a clean stop must not write a crash_loop status"

    def test_one_success_between_failures_prevents_the_cap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mirrors TestRestartPolicy's pure test, but through the real main()
        loop: alternating fail/succeed must never trip the 3-in-a-row cap,
        so the loop only stops via should_restart's own "starved" branch,
        not via crash_loop."""
        # fail, fail, SUCCEED (resets the counter), fail, fail, SUCCEED (resets
        # it again right as starvation hits) -- consecutive_failures never
        # reaches 3, so if the loop stops it cannot be the failure cap.
        rcs = iter([1, 1, 0, 1, 1, 0])
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: next(rcs))

        mtimes = iter(range(1, 10_000))
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: next(mtimes))
        monkeypatch.setattr(supervisor, "parse_sprints", dict)

        # Starved only once the 5 scripted runs are exhausted, so the loop
        # runs exactly 5 times then stops for a reason OTHER than the
        # 3-consecutive-failure cap.
        calls = {"n": 0}

        def analyse(sprints: object) -> QueueState:
            calls["n"] += 1
            if calls["n"] <= 5:
                return QueueState(total=5, todo=5, eligible=5)
            return QueueState(total=5, todo=5, eligible=0)  # starved thereafter

        monkeypatch.setattr(supervisor.triage, "analyse", analyse)
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

        write_calls: list[dict[str, object]] = []
        monkeypatch.setattr(
            supervisor.status,
            "write_status",
            lambda queue, beat, recent, **kwargs: write_calls.append(kwargs),
        )

        rc = supervisor.main()

        assert rc == 0
        assert calls["n"] == 6, "expected exactly 5 restarts then the starved stop"
        assert write_calls == [], "starved stop is not a crash-loop stop"

    def test_silent_exit_triggers_the_reporter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Call-site wiring for the two harness exits that happen before its
        own finally block (pre-flight failure, lock conflict): when
        STATUS.md's mtime does not move across a run, main() must hand off
        to the silent-exit reporter with the real exit code."""
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: 2)
        # Same mtime before and after -- STATUS.md was never touched, the
        # exact signature harness_exited_silently exists to detect.
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: 42.0)
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage,
            "analyse",
            lambda sprints: QueueState(total=0, todo=0, eligible=0),
        )

        reported: list[tuple[int, list[str]]] = []
        monkeypatch.setattr(
            supervisor,
            "_report_silent_exit",
            lambda rc, recent: reported.append((rc, list(recent))),
        )

        rc = supervisor.main()

        assert rc == 0
        assert reported == [(2, [])], f"expected the reporter called once with rc=2, got {reported}"

    def test_does_not_double_launch_when_a_live_harness_is_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If heartbeat_pid_alive() finds a live, identity-confirmed harness
        at startup (e.g. this supervisor instance was restarted by Scheduled
        Tasks while its child kept running), main() must adopt it instead of
        launching a second one -- launching a duplicate would let two
        harnesses run concurrently against one repo, which Task 9's brief
        calls out as the worst outcome available here."""
        pids = iter([4242, None])  # alive once, then gone
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: next(pids))
        waited: list[int] = []
        monkeypatch.setattr(supervisor, "_wait_for_foreign_harness", lambda pid: waited.append(pid))

        launches: list[object] = []

        def fake_popen(*args: object, **kwargs: object) -> object:
            launches.append(args)
            return object()

        monkeypatch.setattr(supervisor.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(supervisor.time, "sleep", lambda _s: None)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: 0)
        mtimes = iter([1.0, 2.0])
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: next(mtimes))
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=0, todo=0, eligible=0)
        )

        rc = supervisor.main()

        assert rc == 0
        assert waited == [4242], "must adopt the live pid rather than ignore it"
        assert len(launches) == 1, "must launch exactly once, only after adopting finished"
