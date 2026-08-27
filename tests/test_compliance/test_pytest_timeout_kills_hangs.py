"""Compliance: pytest-timeout must kill a hanging test within a bounded wall clock.

This demonstrates AC #3 of SUITE-1: a deliberately hung test causes a FAILURE
within a bounded time, not an open-ended wait.

The test subprocess-invokes pytest against an inline test file whose single test
does time.sleep(60).  With --timeout=5 configured, pytest must exit non-zero
within 30 seconds (generous ceiling around a 5-second timeout) and the output
must mention the timeout.

The outer pytest call is supervised by run_with_hard_timeout so a broken
pytest-timeout installation cannot itself hang the parent suite.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

# The kill-tree helper shared by the harness and the agent runner is reused
# here so a broken pytest-timeout does not hang *this* test indefinitely.
from ralph.proc import run_with_hard_timeout

# Wall-clock ceiling for the outer subprocess call (seconds).
# 5s timeout + 5s pytest startup + 20s CI headroom = 30s.
# Raise this if the test is flaky on slow CI runners, but keep it documented.
_OUTER_CEILING_SECONDS = 30


_HANGING_TEST_SOURCE = """\
import time

def test_hangs():
    time.sleep(60)
"""


class TestPytestTimeoutKillsHangs:
    """pytest-timeout is installed and terminates a sleeping test promptly."""

    def test_hung_test_fails_within_bounded_time(self, tmp_path: Path) -> None:
        """A test sleeping 60s fails within 30s wall clock when --timeout=5 is active."""
        test_file = tmp_path / "test_deliberate_hang.py"
        test_file.write_text(_HANGING_TEST_SOURCE, encoding="utf-8")

        start = time.monotonic()
        try:
            result = run_with_hard_timeout(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--timeout=5",
                    "--timeout-method=thread",
                    "-q",
                    "--no-header",
                    str(test_file),
                ],
                timeout_seconds=_OUTER_CEILING_SECONDS,
                cwd=str(tmp_path),
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            pytest.fail(
                f"pytest itself hung for {elapsed:.1f}s — pytest-timeout is not working. "
                "Ensure pytest-timeout>=2.3 is installed and the test-file path is correct."
            )

        elapsed = time.monotonic() - start
        assert elapsed < _OUTER_CEILING_SECONDS, (
            f"Outer ceiling breached: took {elapsed:.1f}s (ceiling={_OUTER_CEILING_SECONDS}s). "
            "pytest-timeout may not be killing the hung test promptly."
        )
        assert result.returncode != 0, (
            "Expected pytest to exit non-zero (hung test timed out), but it exited 0. "
            "pytest-timeout may not be active or configured correctly."
        )
        combined = result.stdout + result.stderr
        assert any(kw in combined.lower() for kw in ("timeout", "timed out")), (
            f"Expected 'timeout' in pytest output, got:\n{combined[:500]}"
        )

    def test_pytest_timeout_is_installed(self) -> None:
        """pytest-timeout must be importable (installed as a dev dependency)."""
        try:
            import pytest_timeout  # noqa: F401
        except ImportError:
            pytest.fail(
                "pytest-timeout is not installed.  "
                "Run: uv sync --extra dev  (or pip install pytest-timeout>=2.3)"
            )
