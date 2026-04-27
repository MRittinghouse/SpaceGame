"""Compliance regression guards for the ship builder view.

Sprint 2b moved every raw RGB tuple in ``spacegame/views/ship_builder_view.py``
into a ``_BUILDER_COLORS`` themed palette dict (or a ``Colors.*`` reference).
These tests make sure that discipline does not silently backslide.

Rule: zero raw ``(R, G, B)`` color-tuple literals may appear in the view
code outside the palette dict itself. If a new color is needed, add a
named entry to ``_BUILDER_COLORS``.

See ``requirements/ui_design_standards.md`` principle 4 ("Shared primitives,
always") and Sprint 4's planned Colors-wrapper migration for the broader
roadmap.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_VIEW_FILE = Path(__file__).resolve().parents[2] / "spacegame" / "views" / "ship_builder_view.py"

_RGB_PATTERN = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def _palette_span(lines: list[str]) -> tuple[int, int]:
    """Return (start, end) 1-indexed line numbers of the _BUILDER_COLORS dict."""
    start: int | None = None
    end: int | None = None
    for i, line in enumerate(lines, 1):
        if "_BUILDER_COLORS: dict" in line and start is None:
            start = i
        if start is not None and line.rstrip() == "}" and i > start:
            end = i
            break
    assert start is not None, "_BUILDER_COLORS dict definition not found"
    assert end is not None, "_BUILDER_COLORS dict closing brace not found"
    return start, end


class TestShipBuilderColorDiscipline:
    """Zero raw RGB tuples outside the themed palette dict."""

    def test_palette_dict_present(self) -> None:
        """The _BUILDER_COLORS themed palette must exist at module scope."""
        text = _VIEW_FILE.read_text(encoding="utf-8")
        assert "_BUILDER_COLORS: dict[str, tuple[int, int, int]]" in text, (
            "Ship builder must define _BUILDER_COLORS as the single source "
            "of themed colors. See Sprint 2b findings."
        )

    def test_no_raw_rgb_tuples_in_view_code(self) -> None:
        """No raw (R, G, B) literals outside the palette dict or comments."""
        lines = _VIEW_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
        palette_start, palette_end = _palette_span(lines)

        offenders: list[tuple[int, str]] = []
        for i, line in enumerate(lines, 1):
            if palette_start <= i <= palette_end:
                continue
            # Ignore fully commented lines; inline comments are still scanned.
            if line.lstrip().startswith("#"):
                continue
            for m in _RGB_PATTERN.finditer(line):
                r, g, b = (int(x) for x in m.groups())
                if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                    offenders.append((i, line.rstrip()))
                    break

        if offenders:
            report = "\n".join(f"  L{ln}: {ctx[:110]}" for ln, ctx in offenders)
            pytest.fail(
                "Raw RGB tuple(s) found in ship_builder_view outside "
                "_BUILDER_COLORS. Add a named palette entry instead:\n" + report
            )

    def test_palette_has_expected_semantic_groups(self) -> None:
        """Spot-check: the palette covers the major semantic roles."""
        text = _VIEW_FILE.read_text(encoding="utf-8")
        required_keys = [
            # Validation
            "valid_place",
            "invalid_place",
            "warn_size",
            # UI states
            "cell_selected_cool",
            "tab_active",
            "cell_alt",
            # Module categories
            "cat_cockpit",
            "cat_engine",
            "cat_weapon",
            # Tier grades
            "grade_s",
            "grade_f",
            # Stat signatures
            "stat_shield",
            "stat_armor",
            "stat_evasion",
        ]
        missing = [k for k in required_keys if f'"{k}"' not in text]
        assert not missing, f"_BUILDER_COLORS is missing required semantic keys: {missing}"
