"""Tests for the liveness heartbeat.

A dead harness and a wedged harness look identical from the outside -- both are
"a process that is not making progress". Checking whether the PID exists cannot
tell them apart, which is why SH-3 sat unnoticed for 19 hours. The heartbeat is
what makes "alive but stuck" a detectable state.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pytest

from ralph import heartbeat


class TestHeartbeat:
    def test_write_then_read_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        heartbeat.write_heartbeat("SH-2", "implement")
        data = heartbeat.read_heartbeat()
        assert data is not None
        assert data["sprint"] == "SH-2"
        assert data["phase"] == "implement"
        assert isinstance(data["pid"], int)

    def test_seconds_since_beat_is_small_right_after_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        heartbeat.write_heartbeat("SH-2", "implement")
        age = heartbeat.seconds_since_beat()
        assert age is not None and age < 5

    def test_missing_heartbeat_reads_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "absent.json")
        assert heartbeat.read_heartbeat() is None
        assert heartbeat.seconds_since_beat() is None

    def test_corrupt_heartbeat_reads_as_none_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A truncated heartbeat must not take down the supervisor.

        The supervisor is the thing that restarts everything else; it has to be
        the most defensive code in the system.
        """
        hb = tmp_path / "hb.json"
        hb.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", hb)
        assert heartbeat.read_heartbeat() is None

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows file-sharing semantics")
    def test_a_read_during_a_replace_still_returns_the_beat(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A read that lands while `os.replace` swaps in a new beat returns a beat.

        On Windows the replace holds the destination open with DELETE access
        while it swaps. `open()` never grants FILE_SHARE_DELETE, so a read in
        that window failed with PermissionError, and `read_heartbeat` reported
        None: "no heartbeat" for a file that was there all along. Measured
        2026-10-12, about 1 read in 80 failed against a writer looping
        `atomic_write`. That made `test_thread_beats_repeatedly_then_stops`
        fail "thread never wrote a beat" 0.13s after its first beat landed, and
        the supervisor kills a harness whose beat reads None past the
        first-beat grace.

        The DELETE-access handle below is the state the replace creates, held
        open so the collision is certain rather than lucky.
        """
        import _winapi

        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        heartbeat.write_heartbeat("SH-2", "implement")
        delete_access = 0x00010000
        share_all = 0x1 | 0x2 | 0x4  # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
        swap = _winapi.CreateFile(
            str(heartbeat.HEARTBEAT_PATH),
            delete_access,
            share_all,
            _winapi.NULL,
            _winapi.OPEN_EXISTING,
            0,
            _winapi.NULL,
        )
        try:
            data = heartbeat.read_heartbeat()
        finally:
            _winapi.CloseHandle(swap)
        assert data is not None, "a beat being replaced read back as no heartbeat at all"
        assert data["sprint"] == "SH-2"

    def test_thread_beats_repeatedly_then_stops(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Beats until stopped, and stops once it is -- waited on, not slept at.

        The first version slept a fixed 0.2s after the stop before sampling the
        value it expected to stay frozen, and failed under the Scheduled Task
        (2026-08-31). The second waited for two equal reads 0.2s apart and took
        that as proof the thread was done. It was not proof: a beat already in
        flight lands after both reads whenever its fsync is slow. `stop` joins
        the thread, so once it returns nothing is left to write.

        The first beat is kept from the read that saw it. Reading again for the
        assertion gave a read a second chance to collide with the next beat's
        replace, which is how a beat already seen was reported as "thread never
        wrote a beat". Between them, these two failed 2 of 3 full `-n 8` runs
        on 2026-10-12.

        The thread is stopped even when an assertion fails, so a failure here
        cannot leave a 0.05s writer beating into later tests' patched paths.
        """
        interval = 0.05
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        beat = heartbeat.start_heartbeat_thread(lambda: ("S", "plan"), interval_seconds=interval)
        try:
            first = heartbeat.read_heartbeat()
            deadline = time.monotonic() + 10.0
            while first is None and time.monotonic() < deadline:
                time.sleep(interval)
                first = heartbeat.read_heartbeat()
            assert first is not None, "thread never wrote a beat"
        finally:
            stopped = beat.stop(timeout=10.0)

        assert stopped, "the heartbeat thread did not exit"
        frozen = heartbeat.read_heartbeat()
        time.sleep(interval * 6)
        assert heartbeat.read_heartbeat() == frozen, "thread kept beating after stop"

    def test_stop_returns_only_after_the_beat_in_flight_has_landed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A beat already past the stop check lands before `stop` returns.

        The loop checks its event before each beat, so a beat past the check
        carries on after the event is set. Setting the event cannot wait for
        that beat; joining the thread can. Measured 2026-10-12 under load:
        fsync alone took up to 0.21s, so the beat in flight landed after the
        old settle check and failed it "thread kept beating after stop". In
        every reproduction the late beat came from the test's own thread. The
        beat stamps its time after the check, so a timestamp later than the
        stop does not mean a second writer.

        The second beat is held in `get_context` until 0.2s after the stop is
        requested, so the race is certain rather than lucky.
        """
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        in_flight = threading.Event()
        release = threading.Event()
        calls = 0

        def context() -> tuple[Optional[str], Optional[str]]:
            nonlocal calls
            calls += 1
            if calls == 2:
                in_flight.set()
                release.wait(10.0)
            return ("S", f"beat-{calls}")

        beat = heartbeat.start_heartbeat_thread(context, interval_seconds=0.01)
        releaser = threading.Timer(0.2, release.set)
        try:
            assert in_flight.wait(10.0), "the second beat never started"
            releaser.start()
            stopped = beat.stop(timeout=10.0)
            landed = heartbeat.read_heartbeat()
        finally:
            releaser.cancel()
            release.set()
            beat.stop(timeout=10.0)

        assert stopped, "the heartbeat thread did not exit"
        assert landed is not None and landed["phase"] == "beat-2", (
            f"stop returned before the beat in flight landed; the file held {landed!r}"
        )
