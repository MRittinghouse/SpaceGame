"""Tests for the Sprint 4 Colors → PALETTE_ROLES wrapper.

The ``Colors`` class in ``spacegame.config`` is now a metaclass-backed
wrapper: select attributes resolve through ``get_role()`` so that the
active colorblind profile remaps their values automatically. The rest of
the class's attributes remain literal tuples for legacy compatibility.

These tests verify:

  1. Migrated attributes return the expected tuple when no profile is
     active (zero visual change vs. the pre-wrapper literals)
  2. Non-migrated attributes return their class-attribute literals
  3. Setting a colorblind profile changes what Colors.* returns for
     migrated attributes whose roles are remapped in that profile
  4. Clearing the profile restores default values
  5. The wrapper is robust: missing roles, missing class attributes all
     handle gracefully

See ``requirements/ui_sprint_4_findings.md``.
"""

from __future__ import annotations

import pytest

from spacegame.config import _COLORS_ROLE_MAP, Colors
from spacegame.engine.material_palette import (
    DEUTERANOPIA,
    PROTANOPIA,
    TRITANOPIA,
    set_colorblind_profile,
)


@pytest.fixture(autouse=True)
def _reset_profile():
    """Ensure each test starts and ends with no colorblind profile active."""
    set_colorblind_profile(None)
    yield
    set_colorblind_profile(None)


class TestDefaultValues:
    """With no colorblind profile, migrated Colors.* return the expected
    literal values (unchanged from pre-Sprint-4 behavior)."""

    def test_status_colors_default_values(self) -> None:
        assert Colors.GREEN == (50, 200, 100)
        assert Colors.RED == (220, 50, 50)
        assert Colors.YELLOW == (255, 200, 50)
        assert Colors.BLUE == (80, 150, 255)

    def test_convenience_aliases_default_values(self) -> None:
        assert Colors.SUCCESS == (50, 200, 100)  # alias for GREEN
        assert Colors.ERROR == (220, 50, 50)  # alias for RED

    def test_check_colors_default_values(self) -> None:
        assert Colors.CHECK_PASS == (80, 220, 120)
        assert Colors.CHECK_MARGINAL == (220, 200, 60)
        assert Colors.CHECK_FAIL == (200, 80, 80)

    def test_quality_tier_colors_default_values(self) -> None:
        assert Colors.QUALITY_POOR == (80, 80, 80)
        assert Colors.QUALITY_NORMAL == (140, 140, 140)
        assert Colors.QUALITY_GOOD == (100, 200, 100)
        assert Colors.QUALITY_EXCELLENT == (255, 220, 80)

    def test_non_migrated_colors_return_class_literals(self) -> None:
        """Colors not in _COLORS_ROLE_MAP return their literal class attrs."""
        assert Colors.BLACK == (0, 0, 0)
        assert Colors.WHITE == (255, 255, 255)
        assert Colors.BACKGROUND == (10, 10, 20)
        assert Colors.UI_PANEL == (20, 25, 40)
        assert Colors.UI_BORDER == (60, 70, 100)
        assert Colors.GOLD == (255, 215, 0)


class TestProtanopiaRemaps:
    """Protanopia (red-blind) remaps critical reds to info blue."""

    def test_critical_red_remaps_to_info_blue(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        # status_critical → status_info, so Colors.RED == (80, 150, 255)
        assert Colors.RED == (80, 150, 255)
        assert Colors.ERROR == (80, 150, 255)  # Alias remaps too

    def test_check_fail_remaps_to_info_blue(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        assert Colors.CHECK_FAIL == (80, 150, 255)

    def test_unrelated_colors_unchanged_under_protanopia(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        assert Colors.GREEN == (50, 200, 100)  # status_success: not remapped
        assert Colors.BLUE == (80, 150, 255)  # status_info: not remapped
        assert Colors.CHECK_PASS == (80, 220, 120)  # not remapped
        assert Colors.BACKGROUND == (10, 10, 20)  # not in map at all


class TestDeuteranopiaRemaps:
    """Deuteranopia (green-blind) remaps both reds and greens."""

    def test_critical_red_and_success_green_remap(self) -> None:
        set_colorblind_profile(DEUTERANOPIA)
        # status_critical → status_info (blue)
        assert Colors.RED == (80, 150, 255)
        # status_success → hud_cyan
        from spacegame.engine.material_palette import PALETTE_ROLES

        expected_cyan = PALETTE_ROLES["hud_cyan"]
        assert Colors.GREEN == expected_cyan
        assert Colors.SUCCESS == expected_cyan

    def test_check_and_quality_greens_remap(self) -> None:
        set_colorblind_profile(DEUTERANOPIA)
        from spacegame.engine.material_palette import PALETTE_ROLES

        expected_cyan = PALETTE_ROLES["hud_cyan"]
        assert Colors.CHECK_PASS == expected_cyan
        assert Colors.QUALITY_GOOD == expected_cyan


class TestTritanopiaRemaps:
    """Tritanopia (blue-blind) remaps info-blue to success-green."""

    def test_info_blue_remaps_to_success_green(self) -> None:
        set_colorblind_profile(TRITANOPIA)
        # status_info → status_success
        assert Colors.BLUE == (50, 200, 100)

    def test_critical_red_unchanged_under_tritanopia(self) -> None:
        set_colorblind_profile(TRITANOPIA)
        # Tritanopia does not remap reds; RED is still (220, 50, 50)
        assert Colors.RED == (220, 50, 50)


class TestProfileRestoreCycle:
    """Setting and clearing a profile must round-trip cleanly."""

    def test_set_then_clear_restores_defaults(self) -> None:
        original_red = Colors.RED
        set_colorblind_profile(PROTANOPIA)
        assert Colors.RED != original_red
        set_colorblind_profile(None)
        assert Colors.RED == original_red

    def test_multiple_profile_switches(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        red_proto = Colors.RED
        set_colorblind_profile(DEUTERANOPIA)
        red_deuter = Colors.RED
        set_colorblind_profile(TRITANOPIA)
        red_trit = Colors.RED
        set_colorblind_profile(None)
        red_default = Colors.RED

        # Protanopia and Deuteranopia both remap RED to info blue
        assert red_proto == red_deuter == (80, 150, 255)
        # Tritanopia does not remap RED
        assert red_trit == (220, 50, 50) == red_default


class TestRoleMapIntegrity:
    """The role-map itself is well-formed."""

    def test_every_mapped_role_exists_in_palette(self) -> None:
        """Every role name in _COLORS_ROLE_MAP must exist in PALETTE_ROLES."""
        from spacegame.engine.material_palette import PALETTE_ROLES

        for color_name, role in _COLORS_ROLE_MAP.items():
            assert role in PALETTE_ROLES, (
                f"Colors.{color_name} maps to role {role!r} which is not "
                f"defined in PALETTE_ROLES."
            )

    def test_aliases_point_to_same_role_as_primary(self) -> None:
        """SUCCESS/ERROR aliases point at the same roles as GREEN/RED."""
        assert _COLORS_ROLE_MAP["SUCCESS"] == _COLORS_ROLE_MAP["GREEN"]
        assert _COLORS_ROLE_MAP["ERROR"] == _COLORS_ROLE_MAP["RED"]


class TestWrapperRobustness:
    """The wrapper handles edge cases without crashing."""

    def test_dunder_access_bypasses_palette(self) -> None:
        """Dunder attribute access (e.g., __class__) works normally."""
        assert Colors.__name__ == "Colors"
        # isinstance check works on the class object itself
        assert isinstance(Colors, type)

    def test_access_of_undefined_attr_raises(self) -> None:
        """Accessing a truly undefined attribute raises AttributeError."""
        with pytest.raises(AttributeError):
            _ = Colors.THIS_IS_NOT_A_COLOR


# ============================================================================
# Sprint 4b: Text + Faction migration tests
# ============================================================================


class TestSprint4bTextDefaults:
    """Text color migration preserves literal values by default."""

    def test_text_primary_default(self) -> None:
        assert Colors.TEXT_PRIMARY == (220, 220, 230)

    def test_text_secondary_default(self) -> None:
        assert Colors.TEXT_SECONDARY == (150, 160, 180)

    def test_text_highlight_default(self) -> None:
        assert Colors.TEXT_HIGHLIGHT == (100, 200, 255)

    def test_text_alias_routes_through_primary(self) -> None:
        """Colors.TEXT is an alias of TEXT_PRIMARY and routes through the palette."""
        assert Colors.TEXT == Colors.TEXT_PRIMARY


class TestSprint4bFactionDefaults:
    """Faction color migration preserves literal values by default."""

    def test_faction_primary_defaults(self) -> None:
        assert Colors.FACTION_COMMERCE == (100, 150, 255)
        assert Colors.FACTION_MINERS == (200, 150, 50)
        assert Colors.FACTION_SCIENCE == (150, 100, 200)
        assert Colors.FACTION_FRONTIER == (100, 200, 100)

    def test_faction_accent_defaults(self) -> None:
        assert Colors.FACTION_ACCENT_COMMERCE == (80, 140, 220)
        assert Colors.FACTION_ACCENT_MINERS == (220, 170, 60)
        assert Colors.FACTION_ACCENT_SCIENCE == (140, 170, 220)
        assert Colors.FACTION_ACCENT_FRONTIER == (80, 200, 120)

    def test_faction_tint_defaults(self) -> None:
        assert Colors.FACTION_TINT_COMMERCE == (40, 60, 100)
        assert Colors.FACTION_TINT_MINERS == (90, 70, 30)
        assert Colors.FACTION_TINT_SCIENCE == (60, 50, 90)
        assert Colors.FACTION_TINT_FRONTIER == (40, 80, 50)


class TestSprint4bProtanopiaFactionRemap:
    """Protanopia swaps miners orange to science purple for red-blind."""

    def test_miners_primary_remaps(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        # faction_miners → faction_science: (150, 100, 200)
        assert Colors.FACTION_MINERS == (150, 100, 200)

    def test_other_factions_unchanged_under_protanopia(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        assert Colors.FACTION_COMMERCE == (100, 150, 255)
        assert Colors.FACTION_SCIENCE == (150, 100, 200)
        assert Colors.FACTION_FRONTIER == (100, 200, 100)

    def test_accent_and_tint_not_remapped_under_protanopia(self) -> None:
        """Sprint 4b scope: only primary faction colors remap; accent and
        tint variants stay at canonical. Documented in findings."""
        set_colorblind_profile(PROTANOPIA)
        assert Colors.FACTION_ACCENT_MINERS == (220, 170, 60)
        assert Colors.FACTION_TINT_MINERS == (90, 70, 30)


class TestSprint4bDeuteranopiaFactionRemap:
    """Deuteranopia remaps both miners (orange) and frontier (green)."""

    def test_miners_and_frontier_remap(self) -> None:
        set_colorblind_profile(DEUTERANOPIA)
        # faction_miners → faction_science
        assert Colors.FACTION_MINERS == (150, 100, 200)
        # faction_frontier → faction_commerce
        assert Colors.FACTION_FRONTIER == (100, 150, 255)


class TestSprint4bTritanopiaFactionRemap:
    """Tritanopia swaps commerce blue to frontier green for blue-blind."""

    def test_commerce_primary_remaps(self) -> None:
        set_colorblind_profile(TRITANOPIA)
        # faction_commerce → faction_frontier
        assert Colors.FACTION_COMMERCE == (100, 200, 100)

    def test_other_factions_unchanged_under_tritanopia(self) -> None:
        set_colorblind_profile(TRITANOPIA)
        assert Colors.FACTION_MINERS == (200, 150, 50)
        assert Colors.FACTION_SCIENCE == (150, 100, 200)
        assert Colors.FACTION_FRONTIER == (100, 200, 100)
