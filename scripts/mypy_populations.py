"""Classify mypy errors into three populations and print counts.

Population definitions (from Spec A, Section 4 of
docs/superpowers/specs/2026-08-23-quality-foundation-design.md):

  Population A (tracked): union-attr errors NOT in engine/game.py, plus
                attr-defined errors whose message contains '"None" has no attribute'.
                These are Optional-type gaps -- the most mechanical to fix.
                Reported count EXCLUDES engine/game.py union-attr errors (see below).

  Population B: attr-defined errors whose message contains '"object" has no attribute'
                + name-defined errors.
                These indicate missing type information (untyped third-party libs,
                forward references).  Fixing them often *raises* the total error count
                (mypy starts seeing code it was blind to) -- see Decision 7 in
                ROADMAP.md#qf-2.

  Population C: all error-severity lines not in A or B, excluding the game.py
                union-attr exclusion bucket.

  TOTAL: A (tracked) + A (excluded game.py union-attr) + B + C.
         Equals the raw mypy error count (note-severity lines are not counted).

Exclusion rule for game.py (Decision 1 in ROADMAP.md#qf-2):
  union-attr errors whose path ends in ``engine/game.py`` or ``engine\\game.py``
  are EXCLUDED from the tracked Population A count.  They are still counted in
  TOTAL.  Rationale: Spec B's non-Optional Player accessor property will erase ~64
  of these 72 errors in a single edit; they are deferred rather than fixed here.
  The 31 ``"None" has no attribute`` [attr-defined] errors in game.py remain in
  tracked Population A -- they need individual code-level fixes.

Note-severity lines (``note:``) from mypy are not errors; they are omitted from
all populations and from TOTAL.  Mypy's own "Found N errors" summary line is also
ignored (matched by not having the error/note severity marker).

Expected output on the 2026-08-23 tree:
    A=124
    B=234
    C=338
    TOTAL=768

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
        'excluded_a' -- game.py union-attr errors excluded from tracked A
                        (still counted toward TOTAL)
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

    # Exclusion: union-attr in game.py -> counted in TOTAL but not tracked in A.
    if code == "union-attr" and (
        norm_path.endswith("engine/game.py") or path_raw.endswith("engine\\game.py")
    ):
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
