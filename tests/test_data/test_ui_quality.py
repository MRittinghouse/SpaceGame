"""UI quality enforcement tests.

Validates that the UI codebase follows established standards from the
UI overhaul (U1-U7): faction colors use canonical sources, station layouts
reference Colors class constants, and layout.py is the shared source
for list-detail pattern dimensions.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Faction color consistency
# ---------------------------------------------------------------------------


class TestFactionColorConsistency:
    """Station layout accent colors must reference Colors class, not hardcoded RGB."""

    def test_station_layout_accents_use_colors_class(self) -> None:
        """Station layout accent_color fields should reference Colors.*."""
        layout_path = Path("spacegame/views/station_layouts.py")
        content = layout_path.read_text(encoding="utf-8")

        # Find class-level accent_color = ... definitions (indented 4 spaces)
        errors = []
        for match in re.finditer(r"^    accent_color\s*=\s*(.+)$", content, re.MULTILINE):
            value = match.group(1).strip()
            # Allow Colors.* references and the Crimson Reach unique color
            if value.startswith("Colors.") or "180, 50, 40" in value:
                continue
            errors.append(f"accent_color = {value} should use Colors.FACTION_ACCENT_*")
        assert not errors, "\n".join(errors)

    def test_cockpit_hud_accents_use_colors_class(self) -> None:
        """Cockpit HUD faction accents should reference Colors.*."""
        hud_path = Path("spacegame/views/cockpit_hud.py")
        content = hud_path.read_text(encoding="utf-8")

        # The FACTION_ACCENTS dict should use Colors.FACTION_ACCENT_* values
        assert "Colors.FACTION_ACCENT_COMMERCE" in content, (
            "HUD FACTION_ACCENTS should reference Colors.FACTION_ACCENT_COMMERCE"
        )
        assert "Colors.FACTION_ACCENT_MINERS" in content
        assert "Colors.FACTION_ACCENT_SCIENCE" in content
        assert "Colors.FACTION_ACCENT_FRONTIER" in content


# ---------------------------------------------------------------------------
# Layout.py adoption
# ---------------------------------------------------------------------------


class TestLayoutAdoption:
    """Views using the list-detail pattern should import from layout.py."""

    def test_crew_roster_imports_layout(self) -> None:
        """Crew roster view imports layout constants from layout.py."""
        content = Path("spacegame/views/crew_roster_view.py").read_text(encoding="utf-8")
        assert "from spacegame.views.layout import" in content

    def test_mission_log_imports_layout(self) -> None:
        """Mission log view imports layout constants from layout.py."""
        content = Path("spacegame/views/mission_log_view.py").read_text(encoding="utf-8")
        assert "from spacegame.views.layout import" in content

    def test_journal_imports_layout(self) -> None:
        """Journal view imports shared margins from layout.py."""
        content = Path("spacegame/views/journal_view.py").read_text(encoding="utf-8")
        assert "from spacegame.views.layout import" in content

    def test_layout_py_defines_faction_helpers(self) -> None:
        """Layout.py provides faction color accessor functions."""
        from spacegame.views.layout import get_faction_accent, get_faction_color, get_faction_tint

        # Verify they return valid RGB tuples for known factions
        for faction_id in [
            "commerce_guild",
            "miners_union",
            "science_collective",
            "frontier_alliance",
        ]:
            color = get_faction_color(faction_id)
            accent = get_faction_accent(faction_id)
            tint = get_faction_tint(faction_id)
            for c in [color, accent, tint]:
                assert len(c) == 3, f"Expected RGB tuple for {faction_id}"
                assert all(0 <= v <= 255 for v in c)

    def test_layout_py_defines_standard_spacing(self) -> None:
        """Layout.py provides the standard spacing vocabulary."""
        from spacegame.views.layout import (
            BUTTON_H_LG,
            BUTTON_H_MD,
            BUTTON_H_SM,
            CARD_H_STANDARD,
            CARD_W_STANDARD,
            CONTENT_BOTTOM,
            GAP_CARD,
            GAP_ITEM,
            MARGIN_EDGE,
            PAD_LG,
            PAD_MD,
            PAD_SM,
            PAD_XS,
        )

        # Verify hierarchy: XS < SM < MD < LG
        assert PAD_XS < PAD_SM < PAD_MD < PAD_LG
        assert BUTTON_H_SM < BUTTON_H_MD < BUTTON_H_LG
        assert CARD_W_STANDARD > 0
        assert CARD_H_STANDARD > 0
        assert GAP_ITEM < GAP_CARD
        assert MARGIN_EDGE > 0
        assert CONTENT_BOTTOM > 0


# ---------------------------------------------------------------------------
# Draw utils availability
# ---------------------------------------------------------------------------


class TestDrawUtilsAvailability:
    """Draw utilities added in U1 are importable and functional."""

    def test_truncate_text_importable(self) -> None:
        """truncate_text utility is importable."""
        from spacegame.engine.draw_utils import truncate_text

        assert callable(truncate_text)

    def test_brighten_and_dim_importable(self) -> None:
        """brighten and dim color helpers are importable."""
        from spacegame.engine.draw_utils import brighten, dim

        assert brighten((100, 100, 100), 50) == (150, 150, 150)
        assert dim((100, 100, 100), 50) == (50, 50, 50)
        # Clamping
        assert brighten((250, 250, 250), 50) == (255, 255, 255)
        assert dim((10, 10, 10), 50) == (0, 0, 0)

    def test_draw_bar_accepts_label_color(self) -> None:
        """draw_bar accepts label_color keyword argument."""
        import inspect

        from spacegame.engine.draw_utils import draw_bar

        sig = inspect.signature(draw_bar)
        assert "label_color" in sig.parameters
