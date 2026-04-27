"""SA-V regression: speaker_id rename to odom_broker is complete.

Walks data/, spacegame/, tools/, and tests/ and asserts zero remaining
references to the legacy id. The rename to ``odom_broker`` was completed
in sprint SA-V. This test pins the rename closed so future authors cannot
re-introduce the old id by accident.

Exclusions (by design):
  - requirements/ -- design-archive docs carry historical context. Updating
    those would lose the paper trail. Exclusion is intentional.
  - __pycache__ directories -- compiled bytecode, not source.
  - This file itself -- the regex target string is constructed at runtime
    so the file's own bytes never contain the literal legacy id.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]

# Constructed at runtime so this source file does not contain the literal
# legacy id and does not self-match.
_LEGACY_ID: str = "delivery" + "_merchant"

# Search roots: only canonical source directories
_SEARCH_ROOTS: list[tuple[Path, list[str]]] = [
    (_REPO_ROOT / "data", ["*.json"]),
    (_REPO_ROOT / "spacegame", ["*.py"]),
    (_REPO_ROOT / "tools", ["*.py"]),
    (_REPO_ROOT / "tests", ["*.py"]),
]

# Directories and files excluded from the scan.
_EXCLUDED_DIRS: frozenset[str] = frozenset({"requirements", "__pycache__"})
# Exclude this file itself (it builds the string at runtime, but the path
# still appears in our own file listing when scanning tests/).
_THIS_FILE = Path(__file__).resolve()


def _collect_source_files() -> list[Path]:
    """Return all source files under the search roots, excluding skip dirs."""
    files: list[Path] = []
    for root, patterns in _SEARCH_ROOTS:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                if path.resolve() == _THIS_FILE:
                    continue
                if any(part in _EXCLUDED_DIRS for part in path.parts):
                    continue
                files.append(path)
    return files


class TestSpeakerIdRenameComplete:
    """Zero legacy NPC id references remain in source files after SA-V rename."""

    def test_no_legacy_id_in_source_files(self) -> None:
        """The legacy speaker id must not appear in any .py or .json source file.

        If this test fails, a file still carries the old id.
        Fix: update the file to use odom_broker everywhere.
        """
        files = _collect_source_files()
        assert files, "No source files found -- search root may be wrong"

        offenders: list[str] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if _LEGACY_ID in text:
                lines = [
                    f"  {path.relative_to(_REPO_ROOT)}:{i + 1}: {line.rstrip()}"
                    for i, line in enumerate(text.splitlines())
                    if _LEGACY_ID in line
                ]
                offenders.extend(lines)

        assert not offenders, (
            f"Found {len(offenders)} remaining reference(s) to the legacy id:\n"
            + "\n".join(offenders)
        )
