"""Tests for ralph.proc — the process/file primitives shared by harness and agents."""

from __future__ import annotations

from pathlib import Path

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

    def test_temp_file_is_same_directory(self, tmp_path: Path, monkeypatch) -> None:
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
