"""Process and file primitives shared by the harness and the agent runner.

This module exists because ``harness.py`` imports ``agents.py``, so anything both
need cannot live in either without a circular import.

It deliberately holds no ralph domain knowledge -- no sprints, no roadmap, no
config beyond what is passed in. That keeps it small enough to be obviously
correct, which matters because both primitives here exist to survive failures
that are hard to reproduce.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically.

    A plain ``Path.write_text`` truncates the target and then writes. A power
    cut in between leaves a truncated file. For ``ROADMAP.md`` (~9,000 lines
    holding every sprint definition) and ``state.json`` (how the harness knows
    where it was), that is unrecoverable without git.

    Writes to a sibling temp file, flushes and fsyncs it, then ``os.replace``,
    which is atomic on both Windows and POSIX. The temp is a sibling rather than
    in the system temp dir because ``os.replace`` cannot cross volumes on
    Windows.

    If any step fails (e.g., disk full during write), the temp file is unlinked
    before the exception propagates, so no .tmp sibling is left behind.

    Args:
        path: Destination file.
        text: Full contents to write.
        encoding: Text encoding.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        # If anything fails, clean up the temp file before re-raising.
        # This prevents a single transient error from leaving a .tmp file
        # that would block harness launches on subsequent runs.
        tmp.unlink(missing_ok=True)
        raise
