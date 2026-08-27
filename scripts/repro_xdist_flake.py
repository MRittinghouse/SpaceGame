"""Repro script for the pytest -n auto worker-death flake (SUITE-1).

Runs ``pytest -n auto -q --no-header`` in a bounded loop and records how many
runs hang, fail, or pass.  Each run is supervised by the harness kill-tree
helper so a hung run is killed cleanly rather than stalling the loop itself.

Usage:
    python scripts/repro_xdist_flake.py
    python scripts/repro_xdist_flake.py --runs 10 --timeout-seconds 300

Output (last line, machine-readable):
    SUITE1_REPRO runs=<N> hangs=<h> failures=<f> passes=<p> median_seconds=<m>

Pre-fix rates and post-fix rates can be compared by recording this line before
and after applying SUITE-1 changes.  The format is intentionally stable so
automated tooling can parse it without fragility.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path so ralph.harness is importable.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from ralph.harness import _run_pytest_with_hard_timeout  # noqa: E402


def _parse_passed_count(output: str) -> int:
    """Extract the 'N passed' count from pytest -q output, or 0 if not found."""
    for line in reversed(output.splitlines()):
        m = re.search(r"(\d+) passed", line)
        if m:
            return int(m.group(1))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of pytest runs to execute (default: 20)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Per-run wall-clock timeout in seconds before declaring a hang (default: 900)",
    )
    args = parser.parse_args()

    hangs = 0
    failures = 0
    passes = 0
    durations: list[float] = []

    cmd = [sys.executable, "-m", "pytest", "-n", "auto", "-q", "--no-header"]

    print(
        f"SUITE1_REPRO: starting {args.runs} run(s) "
        f"(timeout={args.timeout_seconds}s each, cmd={' '.join(cmd)})",
        flush=True,
    )

    for i in range(1, args.runs + 1):
        start = time.monotonic()
        timed_out = False
        returncode = -1
        stdout = ""

        try:
            result = _run_pytest_with_hard_timeout(
                cmd,
                timeout_seconds=float(args.timeout_seconds),
                cwd=str(_PROJECT_ROOT),
            )
            returncode = result.returncode
            stdout = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            timed_out = True

        elapsed = time.monotonic() - start
        durations.append(elapsed)

        if timed_out:
            hangs += 1
            status = f"HANG (killed at {elapsed:.0f}s)"
        elif returncode == 0:
            passes += 1
            count = _parse_passed_count(stdout)
            status = f"PASS ({elapsed:.0f}s, {count} tests)"
        else:
            failures += 1
            status = f"FAIL (rc={returncode}, {elapsed:.0f}s)"

        print(f"  run {i:3d}/{args.runs}: {status}", flush=True)

    median = statistics.median(durations) if durations else 0.0
    summary = (
        f"SUITE1_REPRO runs={args.runs} hangs={hangs} "
        f"failures={failures} passes={passes} median_seconds={median:.1f}"
    )
    print(f"\n{summary}", flush=True)


if __name__ == "__main__":
    main()
