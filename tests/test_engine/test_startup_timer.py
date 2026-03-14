"""Tests for the startup phase profiler."""

import logging
import time

from spacegame.engine.startup_timer import StartupTimer


class TestStartupTimer:
    """StartupTimer records phase durations and logs them."""

    def test_begin_end_records_duration(self) -> None:
        timer = StartupTimer()
        timer.begin("test_phase")
        time.sleep(0.01)  # 10ms minimum
        timer.end("test_phase")
        assert "test_phase" in timer.phases
        assert timer.phases["test_phase"] >= 0.01

    def test_multiple_phases(self) -> None:
        timer = StartupTimer()
        timer.begin("a")
        timer.end("a")
        timer.begin("b")
        timer.end("b")
        assert "a" in timer.phases
        assert "b" in timer.phases

    def test_end_without_begin_is_ignored(self) -> None:
        timer = StartupTimer()
        timer.end("never_started")
        assert "never_started" not in timer.phases

    def test_log_summary_does_not_crash(self) -> None:
        timer = StartupTimer()
        timer.begin("fast")
        timer.end("fast")
        timer.log_summary()  # Should not raise

    def test_log_summary_includes_total(self, caplog: object) -> None:
        timer = StartupTimer()
        timer.begin("a")
        timer.end("a")
        timer.begin("b")
        timer.end("b")
        summary = timer.format_summary()
        assert "a=" in summary
        assert "b=" in summary
        assert "total=" in summary

    def test_format_summary_empty(self) -> None:
        timer = StartupTimer()
        summary = timer.format_summary()
        assert "total=" in summary

    def test_phases_ordered(self) -> None:
        timer = StartupTimer()
        timer.begin("first")
        timer.end("first")
        timer.begin("second")
        timer.end("second")
        timer.begin("third")
        timer.end("third")
        keys = list(timer.phases.keys())
        assert keys == ["first", "second", "third"]

    def test_total_time(self) -> None:
        timer = StartupTimer()
        timer.begin("phase")
        time.sleep(0.01)
        timer.end("phase")
        assert timer.total_time() >= 0.01
