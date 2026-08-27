"""Tests for the liveness heartbeat.

A dead harness and a wedged harness look identical from the outside -- both are
"a process that is not making progress". Checking whether the PID exists cannot
tell them apart, which is why SH-3 sat unnoticed for 19 hours. The heartbeat is
what makes "alive but stuck" a detectable state.
"""

from __future__ import annotations

import time
from pathlib import Path

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

    def test_thread_beats_repeatedly_then_stops(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        stop = heartbeat.start_heartbeat_thread(lambda: ("S", "plan"), interval_seconds=0.05)
        time.sleep(0.3)
        first = heartbeat.read_heartbeat()
        assert first is not None
        stop.set()
        time.sleep(0.2)
        frozen = heartbeat.read_heartbeat()
        time.sleep(0.3)
        assert heartbeat.read_heartbeat() == frozen, "thread kept beating after stop"
