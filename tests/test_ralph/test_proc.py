"""Tests for ralph.proc — the process/file primitives shared by harness and agents."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ralph.proc import atomic_write, run_with_hard_timeout


def _pid_alive(pid: int) -> bool:
    """Return True if a process with the given PID is currently running.

    Mirrors ``ralph.harness._pid_alive``, duplicated here rather than imported
    so this test file's only production dependency stays on the module under
    test (``ralph.proc``).
    """
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


class TestAtomicWrite:
    def test_writes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert target.read_text(encoding="utf-8") == "hello"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        target.write_text("old", encoding="utf-8")
        atomic_write(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_leaves_no_temp_file_behind(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert list(tmp_path.iterdir()) == [target], (
            "atomic_write must clean up its temp file; a leftover .tmp means a "
            "future write could collide or a reader could pick up a partial file"
        )

    def test_temp_file_is_same_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """os.replace is only atomic within a volume; the temp must be a sibling.

        On Windows a cross-volume replace raises OSError, so writing the temp to
        the system temp dir would break on any machine where the repo is not on
        C:.
        """
        seen: list[Path] = []
        real_replace = __import__("os").replace

        def spy(src, dst):  # type: ignore[no-untyped-def]
            seen.append(Path(src))
            return real_replace(src, dst)

        monkeypatch.setattr("ralph.proc.os.replace", spy)
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert seen and seen[0].parent == target.parent

    def test_cleans_up_temp_on_write_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If a write fails, the temp file must be unlinked before re-raising.

        If the temp is left behind, a single transient error (disk full, etc.)
        during an unattended run would leave a .tmp sibling, making the working
        tree dirty and blocking subsequent harness launches that refuse to start
        with uncommitted changes.
        """
        target = tmp_path / "out.txt"

        def failing_fsync(fd: int) -> None:  # type: ignore[no-untyped-def]
            raise IOError("Simulated disk full")

        monkeypatch.setattr("ralph.proc.os.fsync", failing_fsync)
        with pytest.raises(IOError, match="Simulated disk full"):
            atomic_write(target, "hello")
        # Verify the target was never created (failed before replace)
        assert not target.exists()
        # Verify no temp file was left behind
        assert list(tmp_path.iterdir()) == []

    def test_fsync_before_replace(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that os.fsync is called before os.replace.

        This matters for power-loss recovery: fsync-before-replace is what
        ensures the file is durable on disk when the rename happens.
        """
        call_order: list[str] = []
        real_fsync = __import__("os").fsync
        real_replace = __import__("os").replace

        def spy_fsync(fd: int):  # type: ignore[no-untyped-def]
            call_order.append("fsync")
            return real_fsync(fd)

        def spy_replace(src: str, dst: str):  # type: ignore[no-untyped-def]
            call_order.append("replace")
            return real_replace(src, dst)

        monkeypatch.setattr("ralph.proc.os.fsync", spy_fsync)
        monkeypatch.setattr("ralph.proc.os.replace", spy_replace)
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        # Verify fsync was called before replace
        assert "fsync" in call_order
        assert "replace" in call_order
        assert call_order.index("fsync") < call_order.index("replace")


class TestRunWithHardTimeout:
    def test_returns_completed_process_on_success(self) -> None:
        result = run_with_hard_timeout([sys.executable, "-c", "print(1)"], timeout_seconds=30)
        assert result.returncode == 0
        assert "1" in result.stdout

    def test_captures_stderr(self) -> None:
        code = "import sys; sys.stderr.write('boom')"
        result = run_with_hard_timeout([sys.executable, "-c", code], timeout_seconds=30)
        assert "boom" in result.stderr

    def test_raises_timeout_and_returns_promptly(self) -> None:
        """The whole point: a hung child must not hold us past the timeout.

        subprocess.run(timeout=...) kills the direct child but keeps blocking in
        communicate() while grandchildren hold the pipe. That produced an
        8.5-hour stall on 2026-08-26. This asserts WALL CLOCK, not just that the
        exception is raised -- the exception was never the missing part.
        """
        started = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_hard_timeout(
                [sys.executable, "-c", "import time; time.sleep(60)"], timeout_seconds=3
            )
        elapsed = time.monotonic() - started
        assert elapsed < 20, f"returned after {elapsed:.1f}s; the kill did not take effect"

    def test_kills_grandchildren_not_just_the_child(self) -> None:
        """A child that spawns a sleeping grandchild holding the pipe open.

        This is the exact shape of the real failure. Without a process-tree kill
        the grandchild keeps stdout open and the read never ends.
        """
        script = (
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
            "time.sleep(60)"
        )
        started = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_hard_timeout([sys.executable, "-c", script], timeout_seconds=3)
        elapsed = time.monotonic() - started
        assert elapsed < 20, f"returned after {elapsed:.1f}s; grandchild held the pipe"

    def test_grandchild_process_is_actually_killed(self, tmp_path: Path) -> None:
        """Wall clock alone cannot prove the tree died -- check the PID.

        After ``proc.wait()`` raises ``TimeoutExpired``, the kill's own result is
        never checked: ``taskkill``'s exit code is discarded, and the POSIX
        branch swallows ``ProcessLookupError``/``OSError``. The drain-thread
        joins that follow run on a fixed 2s schedule regardless of whether the
        kill actually worked, so a wall-clock-only assertion (as in
        ``test_kills_grandchildren_not_just_the_child`` above) would still pass
        even if the kill silently no-op'd. This spawns a child that spawns a
        grandchild, records the grandchild's PID to a file, lets the timeout
        fire, and asserts the grandchild is verifiably dead -- not merely that
        the call returned on schedule.
        """
        pid_file = tmp_path / "grandchild.pid"
        script = tmp_path / "hung.py"
        script.write_text(
            "import subprocess, sys, time\n"
            f"gc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
            f"open({str(pid_file)!r}, 'w').write(str(gc.pid))\n"
            "sys.stdout.flush()\n"
            "time.sleep(300)\n"
        )
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_hard_timeout([sys.executable, str(script)], timeout_seconds=3)

        assert pid_file.exists(), "grandchild never started -- test setup is broken"
        grandchild_pid = int(pid_file.read_text().strip())
        time.sleep(0.5)  # give the OS a moment to reap the killed process
        assert not _pid_alive(grandchild_pid), (
            f"grandchild PID {grandchild_pid} is still alive after the timeout fired -- "
            f"the process-tree kill silently failed"
        )
