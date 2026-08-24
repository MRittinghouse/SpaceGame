"""Classify mypy errors into three populations and print counts.

Population definitions (from Spec A, Section 4 of
docs/superpowers/specs/2026-08-23-quality-foundation-design.md):

  Population A (tracked): union-attr errors NOT in engine/game.py, plus
                attr-defined errors whose message contains '"None" has no attribute'
                and are NOT in engine/game.py.
                These are Optional-type gaps -- the most mechanical to fix.
                Reported count EXCLUDES all engine/game.py errors of these shapes
                (see exclusion rule below).

  Population B: attr-defined errors whose message contains '"object" has no attribute'
                + name-defined errors.
                These indicate missing type information (untyped third-party libs,
                forward references).  Fixing them often *raises* the total error count
                (mypy starts seeing code it was blind to) -- see Decision 7 in
                ROADMAP.md#qf-2.

  Population C: all error-severity lines not in A or B, excluding the game.py
                exclusion bucket.

  TOTAL: A (tracked) + A (excluded game.py A-shaped errors) + B + C.
         Equals the raw mypy error count (note-severity lines are not counted).

Exclusion rule for game.py (Spec A Section 4; extended by QF-8 Plan Task 2):
  BOTH union-attr AND attr-defined-with-message-``"None" has no attribute`` errors
  whose path ends in ``engine/game.py`` or ``engine\\game.py`` are EXCLUDED from
  the tracked Population A count.  They are still counted in TOTAL.  Rationale:
  Spec A Section 4 states "all 106 game.py errors excluded from the Population A
  metric" -- Spec B's non-Optional Player accessor property will erase these
  errors wholesale rather than by individual code-level fixes.  The original
  script excluded only the 72 union-attr errors; QF-8 extends the exclusion to
  cover the 31 attr-defined-None errors in game.py per Spec A's unambiguous
  "excluded from the Population A metric" language.

Note-severity lines (``note:``) from mypy are not errors; they are omitted from
all populations and from TOTAL.  Mypy's own "Found N errors" summary line is also
ignored (matched by not having the error/note severity marker).

Expected output on the post-QF-8 tree:
    A=0
    B=234
    C=338
    TOTAL=675 (excluding baselined; equals raw mypy count minus the fixes)

Usage::

    # Run mypy internally (default):
    python scripts/mypy_populations.py

    # Read pre-captured mypy output from stdin:
    python -m mypy spacegame/ | python scripts/mypy_populations.py --stdin
"""

from __future__ import annotations

import re
import subprocess
import sys

_ERROR_CODE_RE = re.compile(r"\[([a-z-]+)\]\s*$")

# Mypy error-line pattern:  path:line: severity: message  [code]
# The baseline normalises line numbers to 0; live output uses real numbers.
_LINE_RE = re.compile(r"^(.+?):\d+: (error|note): (.+)$")


def _normalise_path(path: str) -> str:
    """Return the path with backslashes converted to forward slashes."""
    return path.replace("\\", "/")


def classify_line(line: str) -> str | None:
    """Classify a single mypy output line into a population bucket or None.

    Buckets:
        'A'          -- tracked Population A
        'excluded_a' -- game.py A-shaped errors (union-attr and attr-defined-None)
                        excluded from tracked A (still counted toward TOTAL)
        'B'          -- Population B
        'C'          -- Population C
        None         -- note-severity lines, summary lines, blank lines (ignored)

    Args:
        line: A raw line from mypy stdout.

    Returns:
        One of 'A', 'excluded_a', 'B', 'C', or None.
    """
    m = _LINE_RE.match(line.rstrip())
    if not m:
        return None

    path_raw, severity, message = m.group(1), m.group(2), m.group(3)

    # Note-severity lines are informational only -- not errors, not counted.
    if severity == "note":
        return None

    norm_path = _normalise_path(path_raw)

    code_m = _ERROR_CODE_RE.search(message)
    code = code_m.group(1) if code_m else ""

    is_game_py = norm_path.endswith("engine/game.py") or path_raw.endswith("engine\\game.py")

    # Exclusion: game.py A-shaped errors -> counted in TOTAL but not tracked in A.
    # Covers both union-attr and attr-defined-None per Spec A S4 (QF-8 extension).
    if is_game_py and code == "union-attr":
        return "excluded_a"
    if is_game_py and code == "attr-defined" and '"None" has no attribute' in message:
        return "excluded_a"

    # Population A: union-attr errors (except game.py, handled above)
    if code == "union-attr":
        return "A"

    # Population A: attr-defined where message contains '"None" has no attribute'
    if code == "attr-defined" and '"None" has no attribute' in message:
        return "A"

    # Population B: attr-defined where message contains '"object" has no attribute'
    if code == "attr-defined" and '"object" has no attribute' in message:
        return "B"

    # Population B: name-defined
    if code == "name-defined":
        return "B"

    # Population C: everything else (error severity, not note)
    return "C"


def count_populations(lines: list[str]) -> tuple[int, int, int, int]:
    """Count errors per population across a list of mypy output lines.

    Args:
        lines: Raw lines from mypy stdout (may include summary and blank lines).

    Returns:
        Tuple of (A_tracked, B, C, TOTAL) where TOTAL = A_tracked + excluded_a + B + C.
    """
    a = excluded_a = b = c = 0
    for line in lines:
        bucket = classify_line(line)
        if bucket == "A":
            a += 1
        elif bucket == "excluded_a":
            excluded_a += 1
        elif bucket == "B":
            b += 1
        elif bucket == "C":
            c += 1
    total = a + excluded_a + b + c
    return a, b, c, total


def _run_mypy() -> list[str]:
    """Run ``python -m mypy spacegame/`` and return stdout lines."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "spacegame/"],
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main(argv: list[str] | None = None) -> None:
    """Entry point: classify mypy output and print A/B/C/TOTAL counts."""
    if argv is None:
        argv = sys.argv[1:]

    if "--stdin" in argv:
        lines = sys.stdin.read().splitlines()
    else:
        lines = _run_mypy()

    a, b, c, total = count_populations(lines)
    print(f"A={a}")
    print(f"B={b}")
    print(f"C={c}")
    print(f"TOTAL={total}")


if __name__ == "__main__":
    main()
