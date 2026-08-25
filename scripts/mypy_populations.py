"""Classify mypy errors into three populations and print counts.

Population definitions (from Spec A, Section 4 of
docs/superpowers/specs/2026-08-23-quality-foundation-design.md):

  Population A (tracked): union-attr errors, plus attr-defined errors whose
                message contains '"None" has no attribute'.
                These are Optional-type gaps -- the most mechanical to fix.
                SH-3 cleared all game.py crash-class errors, so no exclusion
                rule is needed: A=0 means the codebase is clean.

  Population B: attr-defined errors whose message contains '"object" has no attribute'
                + name-defined errors.
                These indicate missing type information (untyped third-party libs,
                forward references).  Fixing them often *raises* the total error count
                (mypy starts seeing code it was blind to) -- see Decision 7 in
                ROADMAP.md#qf-2.

  Population C: all error-severity lines not in A or B.

  TOTAL: A + B + C.
         Equals the raw mypy error count (note-severity lines are not counted).

Note-severity lines (``note:``) from mypy are not errors; they are omitted from
all populations and from TOTAL.  Mypy's own "Found N errors" summary line is also
ignored (matched by not having the error/note severity marker).

Expected output on the post-SH-3 tree:
    A=0 (no exclusion)
    B=<post-SH-3 number>
    C=<post-SH-3 number>
    TOTAL=<B+C>

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


def classify_line(line: str) -> str | None:
    """Classify a single mypy output line into a population bucket or None.

    Buckets:
        'A'  -- tracked Population A
        'B'  -- Population B
        'C'  -- Population C
        None -- note-severity lines, summary lines, blank lines (ignored)

    Args:
        line: A raw line from mypy stdout.

    Returns:
        One of 'A', 'B', 'C', or None.
    """
    m = _LINE_RE.match(line.rstrip())
    if not m:
        return None

    _path_raw, severity, message = m.group(1), m.group(2), m.group(3)

    # Note-severity lines are informational only -- not errors, not counted.
    if severity == "note":
        return None

    code_m = _ERROR_CODE_RE.search(message)
    code = code_m.group(1) if code_m else ""

    # Population A: union-attr errors
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
        Tuple of (A, B, C, TOTAL) where TOTAL = A + B + C.
    """
    a = b = c = 0
    for line in lines:
        bucket = classify_line(line)
        if bucket == "A":
            a += 1
        elif bucket == "B":
            b += 1
        elif bucket == "C":
            c += 1
    total = a + b + c
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
