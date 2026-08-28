"""Tests for the restart policy.

The supervisor is the only thing with nothing supervising it, so it stays as
dumb as possible: start a process, watch a file, apply a policy, never touch the
repo. Every feature added here is a feature that can fail unwatched.

The policy is tested as pure functions; the process loop around them is
deliberately thin.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterator, Optional

import pytest

from ralph import config as config_module
from ralph import harness, supervisor
from ralph import heartbeat as heartbeat_module
from ralph import status as status_module
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


@pytest.fixture(autouse=True)
def _isolate_supervisor_stop_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may read or write the real `ralph/supervisor_stop.json`.

    `main()` refuses to launch when that marker exists, so a test that left one
    behind would silently turn every later `main()` test into a no-op -- the
    vacuous-test failure mode this branch keeps producing. Autouse so it cannot
    be forgotten.
    """
    monkeypatch.setattr(supervisor, "SUPERVISOR_STOP_PATH", tmp_path / "supervisor_stop.json")


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
    """Lock-acquisition failure (exit code 2) is normal (another instance is
    already running) and must stay quiet. A pre-flight failure (exit code 4,
    since Task 9 fix round 1 -- previously it shared code 2 with the lock
    conflict, which was genuinely ambiguous) must be reported, including the
    exit code, or a repeating failure is silent for 7 days.

    Fix round 1, Finding 2: this used to take a `lock_holder_alive` flag
    computed by re-checking the lock file's live PID after the harness had
    already exited -- a real TOCTOU race (something else could grab or
    release the lock in that gap). The exit code the harness itself already
    chose has no such race, so that is now the sole input.
    """

    def test_lock_conflict_exit_code_is_quiet(self) -> None:
        assert silent_exit_reason(supervisor.HARNESS_RC_LOCK_CONFLICT) is None

    def test_preflight_failure_exit_code_reports_with_the_code(self) -> None:
        reason = silent_exit_reason(supervisor.HARNESS_RC_PREFLIGHT_FAILURE)
        assert reason is not None
        assert "4" in reason

    def test_reports_the_actual_exit_code_not_a_placeholder(self) -> None:
        reason = silent_exit_reason(7)
        assert reason is not None
        assert "7" in reason
        assert "code 7" in reason

    def test_the_two_cases_are_distinguishable_by_exit_code_alone(self) -> None:
        """The property Finding 2 asked for directly: given nothing but the
        two exit codes harness.main() actually uses for its silent exits,
        one must report and the other must not -- with no lock-file, no
        PID, no other input in play at all."""
        lock_conflict = silent_exit_reason(supervisor.HARNESS_RC_LOCK_CONFLICT)
        preflight_failure = silent_exit_reason(supervisor.HARNESS_RC_PREFLIGHT_FAILURE)
        assert lock_conflict is None
        assert preflight_failure is not None
        assert lock_conflict != preflight_failure


class TestCleanRunWithAFailedStatusWrite:
    """M6: rc 0 plus an unchanged STATUS.md mtime is NOT a pre-flight failure.

    `_write_status_snapshot` swallows every exception by design, so a disk
    error or a rendering bug on an otherwise-perfect run leaves exactly the
    signature `harness_exited_silently` looks for. The supervisor then
    overwrote STATUS.md with the full pre-flight explanation -- wrong in every
    particular, and pointing the operator at a subsystem that was working.
    """

    def test_a_clean_exit_does_not_get_blamed_on_pre_flight(self) -> None:
        reason = silent_exit_reason(supervisor.HARNESS_RC_OK)
        assert reason is not None, "silence is still wrong -- something did fail"
        assert "STATUS.md write failed" in reason, (
            "the operator needs the string they can actually grep the harness log "
            "for, not a tour of pre-flight"
        )
        assert "NOT a pre-flight failure" in reason

    def test_the_pre_flight_message_is_reserved_for_pre_flight(self) -> None:
        clean = silent_exit_reason(supervisor.HARNESS_RC_OK)
        preflight = silent_exit_reason(supervisor.HARNESS_RC_PREFLIGHT_FAILURE)
        assert clean != preflight
        assert preflight is not None and "pre-flight check failed" in preflight
        assert clean is not None and "pre-flight check failed" not in clean

    def test_post_try_failure_codes_are_not_blamed_on_pre_flight_either(self) -> None:
        """Baseline, infra and forced-sprint aborts all reach the finally block.

        Each of them writes STATUS.md, so an unchanged mtime on any of them
        means the write failed -- the same diagnosis as rc 0, and never
        pre-flight.
        """
        for rc in (
            supervisor.HARNESS_RC_BASELINE_FAILURE,
            supervisor.HARNESS_RC_INFRA_ERROR,
            supervisor.HARNESS_RC_FORCED_SPRINT_INVALID,
        ):
            reason = silent_exit_reason(rc)
            assert reason is not None
            assert "STATUS.md write failed" in reason, f"rc={rc} misdiagnosed: {reason!r}"


def _returned_values(node: ast.expr) -> Iterator[ast.expr]:
    """Flatten a return expression into the values it can actually yield.

    `return X if cond else Y` returns two different things; a test that only
    inspected the IfExp node itself would see neither -- and the harness's
    final line is exactly that shape.
    """
    if isinstance(node, ast.IfExp):
        yield from _returned_values(node.body)
        yield from _returned_values(node.orelse)
    else:
        yield node


class TestExitCodeLedger:
    """M4: `harness.py` emits the codes, `supervisor.py` interprets them, and
    nothing held the two together.

    The harness used bare integer literals and the supervisor declared its own
    constants, so every test asserted against the supervisor's copy -- the half
    that does not decide anything. Changing a literal in the harness broke no
    test at all. Worse, `2` had quietly grown a second meaning (a forced-sprint
    validation abort) alongside the one the supervisor treats as "normal, stay
    quiet".

    These tests read `ralph/harness.py`'s own source, so they fail on the
    emission side, where the drift starts.
    """

    HARNESS_SOURCE_PATH = config_module.PROJECT_ROOT / "ralph" / "harness.py"

    def _returns(self) -> tuple[list[int], set[str]]:
        """(bare int literals returned, HARNESS_RC_* names returned)."""
        tree = ast.parse(self.HARNESS_SOURCE_PATH.read_text(encoding="utf-8"))
        literals: list[int] = []
        names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            for value in _returned_values(node.value):
                if isinstance(value, ast.Constant) and type(value.value) is int:
                    literals.append(value.value)
                elif isinstance(value, ast.Name) and value.id.startswith("HARNESS_RC_"):
                    names.add(value.id)
        return literals, names

    def test_the_harness_returns_no_bare_exit_code_literals(self) -> None:
        literals, _names = self._returns()
        assert literals == [], (
            f"ralph/harness.py returns bare integer exit code(s) {sorted(set(literals))}. "
            "A literal here is invisible to every test in this file, all of which "
            "assert against the supervisor's constants -- which is exactly how the "
            "emitter and the interpreter drifted apart. Use the HARNESS_RC_* "
            "constants from ralph.config."
        )

    def test_every_code_the_harness_emits_is_in_the_ledger(self) -> None:
        _literals, names = self._returns()
        assert names, "no HARNESS_RC_* returns found -- this test has stopped looking"
        for name in sorted(names):
            code = getattr(config_module, name, None)
            assert code is not None, (
                f"harness.py returns {name}, which ralph.config does not define"
            )
            assert code in config_module.HARNESS_EXIT_CODES, (
                f"harness.py can exit with {name} ({code}), which is absent from "
                "HARNESS_EXIT_CODES -- the supervisor has not been told what it means"
            )

    def test_the_supervisor_reexports_the_config_values_unchanged(self) -> None:
        """Re-declaring instead of importing is what created the drift."""
        for name, code in (
            ("HARNESS_RC_OK", config_module.HARNESS_RC_OK),
            ("HARNESS_RC_LOCK_CONFLICT", config_module.HARNESS_RC_LOCK_CONFLICT),
            ("HARNESS_RC_BASELINE_FAILURE", config_module.HARNESS_RC_BASELINE_FAILURE),
            ("HARNESS_RC_PREFLIGHT_FAILURE", config_module.HARNESS_RC_PREFLIGHT_FAILURE),
            ("HARNESS_RC_INFRA_ERROR", config_module.HARNESS_RC_INFRA_ERROR),
            (
                "HARNESS_RC_FORCED_SPRINT_INVALID",
                config_module.HARNESS_RC_FORCED_SPRINT_INVALID,
            ),
        ):
            assert getattr(supervisor, name) == code, (
                f"supervisor.{name} disagrees with ralph.config.{name}"
            )

    def test_the_supervisor_interprets_every_code_in_the_ledger(self) -> None:
        for code in sorted(config_module.HARNESS_EXIT_CODES):
            reason = silent_exit_reason(code)
            if code == supervisor.HARNESS_RC_LOCK_CONFLICT:
                assert reason is None, "a lock conflict is normal and must stay quiet"
            else:
                assert reason is not None, (
                    f"exit code {code} produces no report at all; a silent exit on it "
                    "would be seven days of nothing"
                )
                assert str(code) in reason, f"the report for {code} does not name the code"

    def test_lock_and_forced_sprint_aborts_no_longer_share_a_code(self) -> None:
        """The unledgered second use of 2.

        A forced-sprint abort is a hard stop that must be reported. It used to
        return the one code the supervisor deliberately says nothing about, so
        a failed STATUS.md write on that path turned it into silence.
        """
        assert (
            config_module.HARNESS_RC_FORCED_SPRINT_INVALID != config_module.HARNESS_RC_LOCK_CONFLICT
        )
        assert silent_exit_reason(config_module.HARNESS_RC_FORCED_SPRINT_INVALID) is not None

    def test_only_the_pre_try_codes_are_marked_as_writing_no_status(self) -> None:
        assert config_module.HARNESS_PRE_TRY_EXIT_CODES == frozenset(
            {
                config_module.HARNESS_RC_LOCK_CONFLICT,
                config_module.HARNESS_RC_PREFLIGHT_FAILURE,
            }
        ), (
            "these are the only two exits that happen before main()'s try block; "
            "any other code reaching the supervisor with an unchanged STATUS.md "
            "mtime means the write itself failed (M6)"
        )


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


def _bounded_counter(max_calls: int, description: str) -> Callable[[], int]:
    """Return a zero-arg counter that raises a clear, named AssertionError
    once called more than *max_calls* times, instead of letting whatever
    resource backs a test double (an iterator, a list) run dry on its own
    and fail with an unrelated, undiagnostic error.

    Fix round 1, Finding 3: an integration test whose bounded mock ran out
    after exactly as many calls as the test happened to script would, on a
    regression that makes main() loop more than expected, fail via a raw
    `StopIteration` from deep inside `next()` rather than an assertion
    naming the real problem ("main() did not stop when it should have").
    This makes that failure explicit and diagnostic no matter which
    production code path causes the extra call.
    """
    calls = {"n": 0}

    def counter() -> int:
        calls["n"] += 1
        if calls["n"] > max_calls:
            raise AssertionError(
                f"{description} called {calls['n']} times (> {max_calls} expected) -- "
                "main() likely never stopped when it should have (should_restart / "
                "RestartPolicy.exhausted may be broken)."
            )
        return calls["n"]

    return counter


def _bounded_constant(value: int, max_calls: int, description: str) -> Callable[[object], int]:
    """A fake `_supervise` that always returns *value*, guarded by
    `_bounded_counter` so an unexpectedly-long-running `main()` fails on a
    named assertion rather than however the caller happens to notice."""
    counter = _bounded_counter(max_calls, description)

    def fake(proc: object) -> int:
        counter()
        return value

    return fake


def _bounded_scripted(values: list[int], description: str) -> Callable[[object], int]:
    """A fake `_supervise` returning *values* in order; calling it more than
    `len(values)` times raises a clear, named AssertionError (via
    `_bounded_counter`) instead of an IndexError once the script runs out."""
    counter = _bounded_counter(len(values), description)

    def fake(proc: object) -> int:
        n = counter()
        return values[n - 1]

    return fake


def _bounded_mtimes(max_calls: int, description: str = "_status_mtime") -> Callable[[], float]:
    """A fake `_status_mtime` returning a distinct, increasing value on every
    call (so `harness_exited_silently` is always False), guarded the same
    way as `_bounded_constant`."""
    counter = _bounded_counter(max_calls, description)

    def fake() -> float:
        return float(counter())

    return fake


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
        """A harness that beat and then stopped is wedged: kill it.

        The injected clock is load-bearing. A beat older than the harness has
        existed belongs to a PREVIOUS run and is deliberately not treated as
        staleness (see `TestSuperviseIgnoresAPreviousRunsHeartbeat`), so this
        must place the poll far enough past launch for a 700s-old beat to be
        genuinely this harness's own.
        """
        proc = _FakeProc(pid=4321, exit_after_polls=10_000)
        killed: list[int] = []
        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: 700.0,  # always past the 600s threshold
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=1000.0),
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

    def test_absent_heartbeat_does_not_trigger_an_immediate_kill(self) -> None:
        """`beat_age` returning None (no heartbeat file at all) must not be
        misread as "infinitely stale" -- that would kill a harness before its
        heartbeat thread has even written its first beat.

        It is bounded rather than unbounded, though: past
        FIRST_BEAT_GRACE_SECONDS an absent beat IS a kill. See
        `TestSuperviseStartupGrace`.
        """
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
    """`_report_silent_exit` is the actual call site: writes STATUS.md's
    decline_reason for a silent exit, unless the exit code IS the normal
    lock-conflict code (Finding 2: decided by exit code alone now, not by
    re-checking the lock file's live PID -- no lock file is touched here at
    all, on purpose, which is the property this class is testing).
    """

    def _isolated_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        target = tmp_path / "STATUS.md"
        monkeypatch.setattr(status_module, "STATUS_PATH", target)
        return target

    def _wire_reporting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # `_report_silent_exit` now commits and pushes what it writes (that is
        # the whole point -- see TestSupervisorPublishesWhatItWrites). Stub it
        # here so these tests keep testing the WRITE decision and never touch
        # the real repo or the network.
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=0, todo=0, eligible=0)
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

    def test_preflight_failure_code_writes_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = self._isolated_status(tmp_path, monkeypatch)
        self._wire_reporting(monkeypatch)

        supervisor._report_silent_exit(supervisor.HARNESS_RC_PREFLIGHT_FAILURE, [])

        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "code 4" in content

    def test_lock_conflict_code_stays_quiet(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = self._isolated_status(tmp_path, monkeypatch)
        self._wire_reporting(monkeypatch)

        supervisor._report_silent_exit(supervisor.HARNESS_RC_LOCK_CONFLICT, [])

        # Genuine lock conflict: no STATUS.md write at all.
        assert not target.exists()


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
        max_iterations: int = 5,
    ) -> list[dict[str, object]]:
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda _seconds: None)
        # The crash-loop path commits and pushes for real; stubbed so this
        # suite cannot mutate the repo or hit the network.
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(
            supervisor, "_supervise", _bounded_constant(supervise_rc, max_iterations, "_supervise")
        )

        # Distinct, increasing mtimes on every call so harness_exited_silently
        # is always False -- this suite isolates the crash-loop/should_restart
        # wiring from the (separately tested) silent-exit reporting path.
        # Bounded (fix round 1, Finding 3): a broken stop condition now fails
        # on `_bounded_counter`'s own assertion naming the real problem,
        # instead of degrading to a raw, undiagnostic StopIteration once an
        # unbounded-looking sequence happens to run dry.
        monkeypatch.setattr(supervisor, "_status_mtime", _bounded_mtimes(max_iterations * 2 + 2))

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
        #
        # Both fakes are bounded (fix round 1, Finding 3): if should_restart
        # or RestartPolicy were broken so main() never stopped, this now
        # fails on `_bounded_counter`'s own assertion naming the real
        # problem, instead of an incidental IndexError/StopIteration once an
        # unbounded-looking sequence happened to run dry.
        rcs = [1, 1, 0, 1, 1, 0]
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(supervisor, "_supervise", _bounded_scripted(rcs, "_supervise"))

        monkeypatch.setattr(supervisor, "_status_mtime", _bounded_mtimes(len(rcs) * 2 + 2))
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


class TestSupervisorPublishesWhatItWrites:
    """Every remote signal in this system is emitted by the harness.

    That is the whole defect: when the harness cannot start (a repeating
    pre-flight failure) or will not be restarted again (crash-loop), the two
    states that mean "the week is over", the supervisor is the only component
    that knows -- and it wrote what it knew to local disk only. GitHub kept
    serving the last STATUS.md the harness pushed, whose beat age is
    re-rendered at read time and therefore reads as recent: a calm, green,
    permanently-final page describing a dead run.
    """

    def _wire(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        """Fake the roadmap/queue edges and capture publish labels."""
        monkeypatch.setattr(status_module, "STATUS_PATH", tmp_path / "STATUS.md")
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=0, todo=0, eligible=0)
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

        published: list[str] = []
        monkeypatch.setattr(
            supervisor, "_publish_status", lambda label: published.append(label) or True
        )
        return published

    def test_a_preflight_failure_report_is_pushed_not_just_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        published = self._wire(tmp_path, monkeypatch)

        supervisor._report_silent_exit(supervisor.HARNESS_RC_PREFLIGHT_FAILURE, [])

        assert published, (
            "the silent-exit report was written to local disk and never "
            "committed or pushed, so the operator's GitHub view keeps showing "
            "the last healthy STATUS.md and never changes again"
        )

    def test_a_normal_lock_conflict_publishes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        published = self._wire(tmp_path, monkeypatch)

        supervisor._report_silent_exit(supervisor.HARNESS_RC_LOCK_CONFLICT, [])

        assert published == [], "a lock conflict is normal and must stay quiet"

    def test_crash_loop_is_pushed_not_just_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        published = self._wire(tmp_path, monkeypatch)

        supervisor._write_crash_loop_status([])

        assert published, (
            "CRASH-LOOP -- the supervisor will not restart the harness again -- "
            "reached local disk only; from GitHub 'stopped for good' and "
            "'between sprints' remain indistinguishable"
        )

    def test_a_failed_status_write_publishes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing was written, so there is nothing to commit."""
        published = self._wire(tmp_path, monkeypatch)

        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(supervisor.status, "write_status", boom)

        supervisor._write_crash_loop_status([])
        supervisor._report_silent_exit(supervisor.HARNESS_RC_PREFLIGHT_FAILURE, [])

        assert published == []


class TestPublishStatusIsResilient:
    """A push that cannot run must never crash the supervisor.

    The supervisor is the one thing keeping the run alive; trading a reporting
    gap for the end of the week is the wrong trade in every case.
    """

    def test_reuses_the_harness_commit_and_push_helpers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Not a second mechanism: the same commit/push path the harness uses."""
        from ralph import harness

        committed: list[tuple[str, str]] = []
        pushed: list[str] = []
        monkeypatch.setattr(
            harness,
            "_commit_harness_bookkeeping",
            lambda sprint_id, summary: bool(committed.append((sprint_id, summary))) or True,
        )
        monkeypatch.setattr(
            harness,
            "_push_after_sprint",
            lambda sprint_id, outcome, enabled: pushed.append(sprint_id),
        )
        monkeypatch.setattr(
            supervisor.status,
            "read_push_state",
            lambda: status_module.PushState(ok=True, timestamp=1.0),
        )

        assert supervisor._publish_status("supervisor-crash-loop") is True
        assert committed and committed[0][0] == "supervisor-crash-loop"
        assert pushed == ["supervisor-crash-loop"]

    def test_a_raising_commit_helper_does_not_propagate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ralph import harness

        def boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("git exploded")

        monkeypatch.setattr(harness, "_commit_harness_bookkeeping", boom)

        assert supervisor._publish_status("supervisor-crash-loop") is False

    def test_a_failed_push_is_reported_as_unpublished(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A rejected push must be recorded, not mistaken for a delivery."""
        from ralph import harness

        monkeypatch.setattr(harness, "_commit_harness_bookkeeping", lambda *a: True)
        monkeypatch.setattr(harness, "_push_after_sprint", lambda *a: None)
        monkeypatch.setattr(
            supervisor.status,
            "read_push_state",
            lambda: status_module.PushState(
                ok=False, timestamp=1.0, detail="! [rejected] non-fast-forward"
            ),
        )

        assert supervisor._publish_status("supervisor-crash-loop") is False, (
            "a rejected push was reported as a successful publish, which is "
            "exactly the false confidence this whole finding is about"
        )


class TestSupervisorLogFile:
    """`silent_exit_reason` used to send the operator to `ralph/logs`, which
    structurally could not contain the pre-flight message: both components
    logged only via `print`, and the Scheduled Task redirects nothing."""

    def test_log_lines_reach_a_file_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "supervisor.log"
        monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path)
        monkeypatch.setattr(supervisor, "SUPERVISOR_LOG_PATH", target)

        supervisor._log("supervisor: harness exited rc=4")

        assert target.exists(), (
            "the supervisor logged to stdout only; under a Scheduled Task that "
            "stream is discarded, so nothing about the run exists on disk"
        )
        assert "rc=4" in target.read_text(encoding="utf-8")

    def test_logging_survives_an_unwritable_log_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A supervisor that cannot write its log must still supervise."""
        monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path / "missing")
        monkeypatch.setattr(supervisor, "SUPERVISOR_LOG_PATH", tmp_path / "nope" / "x" / "s.log")
        monkeypatch.setattr(
            supervisor.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("read-only"))
        )

        supervisor._log("still alive")

    def test_the_guidance_points_at_files_that_hold_the_message(self) -> None:
        reason = supervisor.silent_exit_reason(supervisor.HARNESS_RC_PREFLIGHT_FAILURE)

        assert reason is not None
        assert "ralph/logs/harness.log" in reason, (
            "the operator is told where to look for the pre-flight message; the "
            "place named must be the place that actually holds it"
        )
        assert "ralph/logs/supervisor.log" in reason

    def test_the_harness_subprocess_gets_a_real_log_handle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`Popen` with no stdout makes the harness inherit the supervisor's
        handles, which a Scheduled Task discards."""
        monkeypatch.setattr(supervisor, "LOGS_DIR", tmp_path)
        monkeypatch.setattr(supervisor, "HARNESS_LOG_PATH", tmp_path / "harness.log")

        handle = supervisor._open_harness_log()

        assert handle is not None
        handle.write(b"pre-flight message\n")
        handle.close()
        assert "pre-flight message" in (tmp_path / "harness.log").read_text(encoding="utf-8")

    def test_main_hands_the_harness_a_log_handle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: list[dict[str, object]] = []

        def fake_popen(*_args: object, **kwargs: object) -> object:
            captured.append(kwargs)
            return object()

        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(supervisor.time, "sleep", lambda _s: None)
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: 0)
        mtimes = iter([1.0, 2.0])
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: next(mtimes))
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=0, todo=0, eligible=0)
        )

        supervisor.main()

        assert captured, "main() never launched the harness"
        assert captured[0].get("stdout") is not None, (
            "the harness was launched with no stdout handle, so it inherits the "
            "supervisor's -- which a Scheduled Task discards, leaving no record "
            "of the pre-flight failure the operator is told to go read"
        )

    def test_rotation_bounds_the_log_over_a_seven_day_run(self, tmp_path: Path) -> None:
        target = tmp_path / "supervisor.log"
        target.write_text("x" * 200, encoding="utf-8")

        supervisor._rotate_if_large(target, max_bytes=100)

        assert not target.exists()
        assert (tmp_path / "supervisor.log.1").exists()


class TestTerminalStopMarker:
    """A repeating Scheduled Task trigger must heal a KILLED supervisor
    without resurrecting one that deliberately gave up.

    The 3-consecutive-failure cap and the exponential backoff live in an
    in-process counter, so a relaunched supervisor starts from zero. Without
    this marker the new repeating trigger would grant three fresh harness
    attempts every repetition, forever -- turning the bounded restart policy
    into exactly the unbounded spend it exists to prevent.
    """

    def _wire(
        self, monkeypatch: pytest.MonkeyPatch, *, rc: int, eligible: int, todo: int = 5
    ) -> list[object]:
        launches: list[object] = []
        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(
            supervisor.subprocess,
            "Popen",
            lambda *a, **k: launches.append(a) or object(),
        )
        monkeypatch.setattr(supervisor.time, "sleep", lambda _s: None)
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(supervisor, "_supervise", lambda proc: rc)
        mtimes = iter([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        monkeypatch.setattr(supervisor, "_status_mtime", lambda: next(mtimes))
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage,
            "analyse",
            lambda sprints: QueueState(total=5, todo=todo, eligible=eligible),
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)
        return launches

    def test_a_deliberate_stop_is_recorded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._wire(monkeypatch, rc=0, eligible=0, todo=0)

        supervisor.main()

        stopped = supervisor.read_terminal_stop()
        assert stopped is not None, (
            "the supervisor stopped on purpose and left no record, so the "
            "repeating Scheduled Task trigger will relaunch it every "
            "repetition and the bounded restart policy is gone"
        )
        assert "all work complete" in str(stopped.get("reason", ""))

    def test_a_recorded_stop_prevents_a_relaunch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        launches = self._wire(monkeypatch, rc=0, eligible=5)
        supervisor.record_terminal_stop("stopping: 3 consecutive failures")

        rc = supervisor.main()

        assert rc == 0
        assert launches == [], (
            "a supervisor that had already given up launched the harness "
            "again; every trigger firing would grant three more attempts"
        )

    def test_no_marker_means_a_killed_supervisor_relaunches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The whole point of the repeating trigger: a supervisor terminated
        by the 72-hour execution limit leaves no record and must resume."""
        launches = self._wire(monkeypatch, rc=0, eligible=0, todo=0)
        supervisor.clear_terminal_stop()

        supervisor.main()

        assert launches, (
            "with no recorded stop the supervisor refused to launch, so a "
            "killed supervisor would never resume and the run ends silently"
        )

    def test_a_corrupt_marker_fails_open(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A parse bug must not be able to permanently prevent a launch."""
        supervisor.SUPERVISOR_STOP_PATH.write_text("{not json", encoding="utf-8")
        launches = self._wire(monkeypatch, rc=0, eligible=0, todo=0)

        supervisor.main()

        assert supervisor.read_terminal_stop() is not None or launches
        assert launches, "an unreadable marker stopped the supervisor forever"

    def test_clear_removes_the_marker(self) -> None:
        supervisor.record_terminal_stop("stopping: all work complete")
        assert supervisor.read_terminal_stop() is not None

        supervisor.clear_terminal_stop()

        assert supervisor.read_terminal_stop() is None


class TestInstallSupervisorTaskScript:
    """The Scheduled Task's own settings, which no runtime test can reach.

    `New-ScheduledTaskSettingsSet` defaults `ExecutionTimeLimit` to PT72H with
    `AllowHardTerminate` True (measured). Seven days is 168 hours, so on the
    middle of day 3 Windows hard-terminated the supervisor -- and since the
    only trigger was At-startup, nothing ever resumed it. Neither the smoke
    drill (minutes) nor any Python test can see a property of a default nobody
    set, so it is asserted against the script text.
    """

    def _script(self) -> str:
        """The script's EXECUTABLE lines only.

        The comment block above each setting repeats the arguments verbatim, so
        asserting against the raw file text passes even when the real call has
        been stripped -- verified: deleting `-ExecutionTimeLimit` from the
        settings left every assertion here green. Same self-confirming failure
        class as the .tmp-orphan test; fixed the same way.
        """
        path = Path(supervisor.PROJECT_ROOT) / "scripts" / "install_supervisor_task.ps1"
        raw = path.read_text(encoding="utf-8")
        # Drop the <# ... #> comment-based help block.
        if "<#" in raw and "#>" in raw:
            raw = raw[raw.index("#>") + 2 :]
        lines = [line for line in raw.splitlines() if not line.lstrip().startswith("#")]
        return "\n".join(lines)

    def test_the_helper_reads_real_code_not_comments(self) -> None:
        """Guard on the guard: if the stripper ate everything, or ate nothing,
        every assertion in this class would be meaningless."""
        code = self._script()
        assert "New-ScheduledTaskSettingsSet" in code, "the settings call was stripped away"
        assert "load-bearing" not in code, (
            "explanatory comments survived the strip, so these assertions can "
            "again be satisfied by prose rather than by the actual arguments"
        )

    def test_execution_time_limit_is_unlimited(self) -> None:
        text = self._script()
        assert "-ExecutionTimeLimit" in text, (
            "no -ExecutionTimeLimit argument: the cmdlet default is PT72H with "
            "AllowHardTerminate, so Windows kills the supervisor on day 3 of a "
            "seven-day run and the At-startup trigger never brings it back"
        )
        assert "[TimeSpan]::Zero" in text, (
            "ExecutionTimeLimit must be PT0S (unlimited); any finite value is a "
            "hard deadline on an unattended run"
        )

    def test_there_is_a_recurring_trigger_not_only_at_startup(self) -> None:
        text = self._script()
        assert "-RepetitionInterval" in text, (
            "the only trigger is At-startup, so a supervisor that stops for any "
            "reason short of a reboot never resumes and the week ends silently"
        )
        assert "-RepetitionDuration" in text

    def test_the_task_still_refuses_concurrent_instances(self) -> None:
        """A repeating trigger plus a running supervisor must not double-launch."""
        assert "IgnoreNew" in self._script()

    def test_battery_defaults_do_not_block_the_task(self) -> None:
        """Both battery settings default True; a UPS presenting as a battery
        would stop the task starting at boot."""
        text = self._script()
        assert "-AllowStartIfOnBatteries" in text
        assert "-DontStopIfGoingOnBatteries" in text

    def test_the_script_does_not_arm_itself_on_import(self) -> None:
        """Registering a Scheduled Task is a system-level change and must stay
        a deliberate human action -- reading this file must never arm it."""
        text = self._script()
        assert text.count("Register-ScheduledTask ") == 1, (
            "exactly one registration call is expected, at the end of the script"
        )


def _stepping_clock(step: float, start: float = 0.0) -> Callable[[], float]:
    """A monotonic clock that advances *step* seconds on every read.

    `_supervise` reads it once at launch and once per poll, so the Nth poll
    sees ``elapsed == N * step``. Injecting it is what makes the startup
    grace and the leftover-beat rule testable without real 15-minute waits.
    """
    state = {"t": start - step}

    def _now() -> float:
        state["t"] += step
        return state["t"]

    return _now


class TestSuperviseStartupGrace:
    """H2(b): "no heartbeat" must not mean "wait forever".

    `_supervise` treated an absent beat as "no information, keep waiting" with
    no upper bound. There is a real window in which that applies: the harness's
    heartbeat thread starts only after pre-flight passes and the lock is held,
    and pre-flight ends with a real claude invocation. A hang there, on a run
    with no heartbeat.json on disk, meant: harness blocked forever, supervisor
    polling a condition that could never become true, no STATUS.md ever
    written, nothing pushed, no log entry. Total silence, indefinitely -- and
    the 15-minute repeating Scheduled Task trigger does not rescue it, because
    the supervisor process is alive so `MultipleInstances = IgnoreNew` discards
    the firing.
    """

    def test_a_harness_that_never_beats_is_killed_once_the_grace_expires(self) -> None:
        proc = _FakeProc(pid=4321, exit_after_polls=10_000)
        killed: list[int] = []

        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            first_beat_grace_seconds=900.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: None,  # the harness never wrote a first beat
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=100.0),
        )

        assert killed == [4321], (
            "a harness that produced no heartbeat at all was never killed, so a "
            "pre-flight hang blocks the supervisor forever with nothing written "
            "anywhere -- the purest 'dead run indistinguishable from a working "
            "one' path in the system"
        )

    def test_no_kill_before_the_grace_expires(self) -> None:
        """The rule the grace must not break: a harness in a legitimately slow
        pre-flight (the agency probe alone is allowed 240s) must be left
        alone."""
        proc = _FakeProc(pid=4321, exit_after_polls=5)
        killed: list[int] = []

        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            first_beat_grace_seconds=900.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: None,
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=30.0),  # 5 polls == 150s elapsed
        )

        assert killed == []

    def test_a_first_beat_disarms_the_grace(self) -> None:
        """Once the harness beats, the grace is irrelevant and only staleness
        matters -- a 90-minute implement phase must not be killed at 15."""
        proc = _FakeProc(pid=4321, exit_after_polls=40)
        killed: list[int] = []

        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            first_beat_grace_seconds=900.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: 20.0,  # beating happily
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=30.0),  # 40 polls == 1200s, past the grace
        )

        assert killed == [], (
            "a harness that IS beating was killed once the startup grace elapsed; "
            "the grace must apply only while no beat of this harness's own exists"
        )

    def test_the_grace_is_wider_than_the_slowest_legitimate_preflight(self) -> None:
        """The bound is only correct if it clears the real pre-flight cost.

        Derived from the harness's own probe timeout rather than restated, so
        raising the probe timeout cannot silently make the grace too tight.
        """
        assert supervisor.FIRST_BEAT_GRACE_SECONDS > harness.PROBE_TIMEOUT_SECONDS * 2, (
            f"the startup grace ({supervisor.FIRST_BEAT_GRACE_SECONDS}s) leaves too "
            f"little room over the agency probe alone "
            f"({harness.PROBE_TIMEOUT_SECONDS}s); a slow but healthy pre-flight "
            "would be hard-killed, and each kill costs a strike off the 3-failure "
            "budget"
        )


class TestSuperviseIgnoresAPreviousRunsHeartbeat:
    """A leftover beat is not this harness's beat.

    heartbeat.json survives the process that wrote it. After two failures the
    supervisor sleeps 480s before relaunching, so by the time the new harness
    starts, the previous run's file is already ~8 minutes old. Judged as if it
    belonged to the new harness, it crosses the 600s stale threshold about two
    minutes into a pre-flight that is working perfectly -- and the supervisor
    hard-kills a healthy run, records another failure, and moves one step
    closer to ending the week.
    """

    def test_a_stale_leftover_beat_does_not_kill_a_healthy_new_harness(self) -> None:
        proc = _FakeProc(pid=4321, exit_after_polls=5)
        killed: list[int] = []

        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            first_beat_grace_seconds=900.0,
            sleep=lambda _seconds: None,
            # 700s old at the first poll: older than this harness has existed,
            # so it cannot be this harness's beat.
            beat_age=lambda: 700.0,
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=30.0),
        )

        assert killed == [], (
            "the supervisor hard-killed a harness that had been running for 30 "
            "seconds because of a heartbeat left behind by the PREVIOUS run -- "
            "after an 8-minute backoff that happens on every relaunch"
        )

    def test_a_leftover_beat_still_leaves_the_startup_grace_armed(self) -> None:
        """Ignoring the leftover must not reintroduce the unbounded wait: a
        harness that never beats is still killed, leftover file or not."""
        proc = _FakeProc(pid=4321, exit_after_polls=10_000)
        killed: list[int] = []

        supervisor._supervise(
            proc,  # type: ignore[arg-type]
            poll_interval=0.0,
            stale_seconds=600.0,
            first_beat_grace_seconds=900.0,
            sleep=lambda _seconds: None,
            beat_age=lambda: 700.0,
            kill=lambda pid: killed.append(pid),
            monotonic=_stepping_clock(step=100.0),
        )

        assert killed == [4321]


class TestInfrastructureFailuresAreAFailureMode:
    """H4: the harness used to exit 0 after processing ten sprints that all
    failed with infra_error and accomplishing nothing.

    `should_restart` saw rc 0, `record_success()` reset the counter, and the
    3-strike cap and the exponential backoff -- named in the spec as "the
    difference between a quiet week and an expensive one" -- never engaged,
    because both are keyed to non-zero exits and this failure mode never
    produced one. An expired token or a multi-hour outage on day 2 therefore
    yielded a full pre-flight (one claude call) plus a full baseline capture
    (~100s of pytest) plus ten sprints, on a 30-second loop, for five days.
    """

    def test_an_infra_exit_is_not_a_success(self) -> None:
        policy = RestartPolicy()
        policy.record_failure()
        policy.record_failure()
        policy.record_infra_failure()

        assert policy.consecutive_failures == 2, (
            "an infrastructure failure reset the ordinary failure counter, so a "
            "harness alternating between crashing and hitting an outage never trips "
            "the crash-loop cap"
        )
        assert policy.consecutive_infra_failures == 1

    def test_repeated_infra_failures_eventually_exhaust_the_policy(self) -> None:
        policy = RestartPolicy()
        for _ in range(supervisor.MAX_CONSECUTIVE_INFRA_FAILURES):
            policy.record_infra_failure()
            assert policy.consecutive_failures == 0, (
                "infra failures must not be counted as ordinary failures too, or a "
                "three-minute blip would retire the week"
            )
        assert policy.exhausted, (
            "the supervisor never gives up on an infrastructure failure, so a "
            "permanently expired auth token spins for the whole trip"
        )

    def test_a_successful_run_clears_the_infra_counter(self) -> None:
        policy = RestartPolicy()
        policy.record_infra_failure()
        policy.record_infra_failure()
        policy.record_success()

        assert policy.consecutive_infra_failures == 0
        assert not policy.exhausted

    def test_should_restart_stops_on_repeated_infra_failures(self) -> None:
        restart, reason = should_restart(0, 5, False, supervisor.MAX_CONSECUTIVE_INFRA_FAILURES)
        assert restart is False
        assert "infrastructure" in reason

    def test_should_restart_keeps_going_below_the_infra_cap(self) -> None:
        restart, _reason = should_restart(
            0, 5, False, supervisor.MAX_CONSECUTIVE_INFRA_FAILURES - 1
        )
        assert restart is True

    def test_the_infra_backoff_is_an_order_of_magnitude_slower(self) -> None:
        """Nothing the harness does shortens an API outage, so a fast retry
        only spends money. The ladder must also give a transient outage room
        to end: the ordinary ladder retires a run in ~10 minutes, which would
        make a three-hour outage on day 2 end a seven-day trip."""
        for n in range(supervisor.MAX_CONSECUTIVE_INFRA_FAILURES):
            assert supervisor.infra_backoff_seconds(n) >= supervisor.backoff_seconds(n) * 3

        total = sum(
            supervisor.infra_backoff_seconds(n)
            for n in range(supervisor.MAX_CONSECUTIVE_INFRA_FAILURES)
        )
        assert total >= 3 * 3600, (
            f"the supervisor gives up on infrastructure after only {total / 3600:.1f} "
            "hours of backoff; a transient outage would end the week"
        )


class TestInfraExitDrivesTheSupervisorLoop:
    """The policy is right in isolation; this proves `main()` consults it."""

    def test_repeated_infra_exits_stop_the_supervisor_with_an_infra_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_calls: list[dict[str, object]] = []
        slept: list[float] = []

        monkeypatch.setattr(supervisor, "heartbeat_pid_alive", lambda: None)
        monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *a, **k: object())
        monkeypatch.setattr(supervisor.time, "sleep", lambda seconds: slept.append(seconds))
        monkeypatch.setattr(supervisor, "_publish_status", lambda label: True)
        monkeypatch.setattr(
            supervisor,
            "_supervise",
            _bounded_constant(supervisor.HARNESS_RC_INFRA_ERROR, 10, "_supervise"),
        )
        monkeypatch.setattr(supervisor, "_status_mtime", _bounded_mtimes(30))
        monkeypatch.setattr(supervisor, "parse_sprints", dict)
        monkeypatch.setattr(
            supervisor.triage, "analyse", lambda sprints: QueueState(total=5, todo=5, eligible=5)
        )
        monkeypatch.setattr(supervisor.triage, "blocks_disagreements", lambda sprints: [])
        monkeypatch.setattr(supervisor.heartbeat, "read_heartbeat", lambda: None)

        def spy_write_status(queue: object, beat: object, recent: object, **kwargs: object) -> None:
            write_calls.append(kwargs)

        monkeypatch.setattr(supervisor.status, "write_status", spy_write_status)

        rc = supervisor.main()

        assert rc == 0
        assert len(write_calls) == 1, (
            f"expected exactly one crash-loop STATUS.md write, got {write_calls} -- "
            "a harness exiting on an infrastructure failure must eventually stop the "
            "supervisor rather than being relaunched forever"
        )
        assert write_calls[0].get("crash_loop") is True
        reason = str(write_calls[0].get("crash_loop_reason"))
        assert "infrastructure" in reason, (
            f"the CRASH-LOOP banner does not distinguish an outage from a crashing "
            f"harness: {reason!r}. The operator's response to the two is different"
        )
        assert slept and min(slept) >= supervisor.infra_backoff_seconds(0), (
            f"the supervisor used the fast ladder after an infrastructure failure "
            f"({slept}), which is the 30-second spin this finding is about"
        )
