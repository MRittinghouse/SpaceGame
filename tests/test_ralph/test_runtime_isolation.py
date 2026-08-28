"""The suite must not write ralph's live runtime files.

These are the covering tests for ``conftest.isolate_ralph_runtime_paths``. They
are deliberately behavioural rather than structural: they call the real writer
and then look at the real file, so removing the fixture makes them fail on their
own assertions rather than on an incidental error.

Why this matters more than ordinary test hygiene: the harness runs this entire
suite from the repo root once per sprint (the H3 gate) and once per launch (the
baseline capture). Anything the suite writes to a live runtime file is written
*during* the unattended week, with a live timestamp, into the exact files the
operator is told to go read.
"""

from __future__ import annotations

from pathlib import Path

from ralph import config as config_module
from ralph import harness as harness_module
from ralph import heartbeat as heartbeat_module
from ralph import status as status_module
from ralph import supervisor as supervisor_module

_REAL_ROOT = Path(config_module.PROJECT_ROOT)


def _bytes_of(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


class TestTheSuiteCannotWriteRalphsLiveRuntimeFiles:
    def test_a_supervisor_log_line_never_reaches_the_real_log(self) -> None:
        """N1: the H3 gate wrote ~88 fabricated lines per run into
        ``ralph/logs/supervisor.log`` -- ``stopping: 3 consecutive failures``,
        ``all work complete``, ``heartbeat is 700s stale ... killing`` -- with
        live timestamps and in exactly the shape of real output.
        ``silent_exit_reason`` names that file to the operator, so the one
        on-disk channel the run has was being filled with fiction."""
        real_log = _REAL_ROOT / "ralph" / "logs" / "supervisor.log"
        before = _bytes_of(real_log)

        supervisor_module._log("supervisor: stopping: 3 consecutive failures")

        assert _bytes_of(real_log) == before, (
            "a test wrote a fabricated supervisor event into the REAL "
            f"{real_log}. That file is what `silent_exit_reason` tells the "
            "operator to grep when a run dies, and a fabricated "
            "'stopping: 3 consecutive failures' there is indistinguishable "
            "from a real one -- the operator would be diagnosing a week-long "
            "unattended run from events that never happened"
        )

    def test_a_heartbeat_write_never_stamps_the_real_beat_file(self) -> None:
        """N6: tests that drive ``harness.main()`` start a real heartbeat
        thread. It stamped ``ralph/heartbeat.json`` with an xdist worker's PID,
        so for up to 30s afterwards ``status.beat_pid_liveness`` probed a dead
        process and ``render_status`` emitted ``## NO LIVE HARNESS`` -- a false
        "the harness is not running" banner, committed and pushed."""
        real_beat = _REAL_ROOT / "ralph" / "heartbeat.json"
        before = _bytes_of(real_beat)

        heartbeat_module.write_heartbeat("ISOLATION-1", "implement")

        assert _bytes_of(real_beat) == before, (
            f"a test stamped the REAL {real_beat} with its own PID. That PID "
            "is dead moments later, so STATUS.md renders `## NO LIVE HARNESS` "
            "for a perfectly healthy run and pushes it to the operator's phone"
        )

    def test_every_redirected_runtime_path_points_outside_the_repo(self) -> None:
        """Structural backstop for the paths with no cheap behavioural probe.

        Guards the guard too: an empty list here would make this vacuous, so
        the count is asserted.
        """
        redirected: list[tuple[str, Path]] = [
            ("config.LOGS_DIR", config_module.LOGS_DIR),
            ("harness.LOGS_DIR", harness_module.LOGS_DIR),
            ("supervisor.LOGS_DIR", supervisor_module.LOGS_DIR),
            ("supervisor.SUPERVISOR_LOG_PATH", supervisor_module.SUPERVISOR_LOG_PATH),
            ("supervisor.HARNESS_LOG_PATH", supervisor_module.HARNESS_LOG_PATH),
            ("supervisor.SUPERVISOR_STOP_PATH", supervisor_module.SUPERVISOR_STOP_PATH),
            ("heartbeat.HEARTBEAT_PATH", heartbeat_module.HEARTBEAT_PATH),
            ("status.STATUS_PATH", status_module.STATUS_PATH),
            ("status.PUSH_STATE_PATH", status_module.PUSH_STATE_PATH),
            ("harness.STATE_FILE", harness_module.STATE_FILE),
            ("harness.LOCK_FILE", harness_module.LOCK_FILE),
            ("harness.STOP_FILE", harness_module.STOP_FILE),
        ]
        assert len(redirected) >= 12, "the redirection list has been emptied"

        leaking = [
            f"{name} -> {path}"
            for name, path in redirected
            if path == _REAL_ROOT or _REAL_ROOT in Path(path).resolve().parents
        ]
        assert not leaking, (
            "these ralph runtime paths still point inside the live repository "
            f"during a test run: {leaking}. Every write through them lands in "
            "a file the operator reads as the record of a real unattended run"
        )
