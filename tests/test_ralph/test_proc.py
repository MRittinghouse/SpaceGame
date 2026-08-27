"""Tests for ralph.proc — the process/file primitives shared by harness and agents."""

from __future__ import annotations

from pathlib import Path

import pytest

from ralph.proc import atomic_write


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
