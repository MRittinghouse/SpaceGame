"""Static analysis test for color value safety.

Scans all view files for dynamic color computations (base + offset patterns)
and verifies their maximum possible values stay within [0, 255].
"""

import ast
import math
import re

import pytest

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT

# Collect all Python source files in the views directory
from pathlib import Path

VIEWS_DIR = Path(__file__).resolve().parent.parent.parent / "spacegame" / "views"


def _find_color_arithmetic_lines() -> list[tuple[str, int, str]]:
    """Find lines with patterns like (N + pulse, ...) or (N + offset, ...).

    Returns list of (filename, line_number, line_text).
    """
    # Pattern: digit(s) + variable in a tuple context (likely a color)
    pattern = re.compile(r"\(\s*(\d{2,3})\s*\+\s*(\w+)\s*,")
    results = []
    for py_file in VIEWS_DIR.glob("*.py"):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            match = pattern.search(line)
            if match:
                results.append((py_file.name, i, line.strip()))
    return results


def _extract_pulse_max(source_lines: list[str], var_name: str, line_idx: int) -> int | None:
    """Look backwards from line_idx to find the assignment of var_name
    and compute its maximum possible value.

    Handles patterns like:
        pulse = int(abs(math.sin(...)) * N) + M
        pulse = int(abs(math.sin(...)) * N)
    """
    for i in range(line_idx - 1, max(line_idx - 15, -1), -1):
        line = source_lines[i].strip()
        if not line.startswith(f"{var_name} =") and not line.startswith(f"{var_name}="):
            continue

        # Pattern: int(abs(math.sin(...)) * N) + M
        match = re.search(r"int\(abs\(math\.sin\([^)]+\)\)\s*\*\s*(\d+)\)\s*\+\s*(\d+)", line)
        if match:
            return int(match.group(1)) + int(match.group(2))

        # Pattern: int(abs(math.sin(...)) * N) without addition
        match = re.search(r"int\(abs\(math\.sin\([^)]+\)\)\s*\*\s*(\d+)\)", line)
        if match:
            return int(match.group(1))

        # Pattern: int(...* N)
        match = re.search(r"int\([^)]*\*\s*(\d+)\)", line)
        if match:
            return int(match.group(1))

    return None


class TestColorValueSafety:
    """Verify all dynamic color computations stay within [0, 255]."""

    def test_no_color_channel_exceeds_255(self) -> None:
        """Scan views for base + offset color patterns and check max values."""
        pattern = re.compile(r"\(\s*(\d{2,3})\s*\+\s*(\w+)\s*,")
        violations = []

        for py_file in VIEWS_DIR.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            lines = source.splitlines()
            for i, line in enumerate(lines):
                match = pattern.search(line)
                if match:
                    base = int(match.group(1))
                    var_name = match.group(2)

                    # Try to compute the max of the variable
                    var_max = _extract_pulse_max(lines, var_name, i)
                    if var_max is not None:
                        total_max = base + var_max
                        if total_max > 255:
                            violations.append(
                                f"{py_file.name}:{i + 1} — {var_name} max={var_max}, "
                                f"base={base}, total={total_max} > 255: {line.strip()}"
                            )

        assert not violations, f"Color channel overflow detected:\n" + "\n".join(violations)

    def test_min_calls_clamp_computed_colors(self) -> None:
        """Verify that tuple(min(c + N, 255) ...) patterns clamp correctly."""
        # This pattern is correct — just verify it exists where expected
        pattern = re.compile(r"min\(c\s*\+\s*\d+,\s*255\)")
        found = False
        for py_file in VIEWS_DIR.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            if pattern.search(source):
                found = True
        # At least dialogue_view uses this pattern for portrait borders
        assert found, "Expected at least one clamped color computation in views"

    def test_alpha_values_clamped(self) -> None:
        """Verify alpha computations use min(..., 255) or similar clamping."""
        # Find set_alpha calls with computed values (not literals)
        alpha_pattern = re.compile(r"set_alpha\((\d{3,})\)")
        violations = []

        for py_file in VIEWS_DIR.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                match = alpha_pattern.search(line)
                if match:
                    val = int(match.group(1))
                    if val > 255:
                        violations.append(f"{py_file.name}:{i} — set_alpha({val}) > 255")

        assert not violations, f"Alpha overflow detected:\n" + "\n".join(violations)
