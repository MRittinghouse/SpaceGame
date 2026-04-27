"""Tests for ui_chrome badge/glyph/stamp primitives.

Covers the public API (StampType, draw_badge, draw_glyph, draw_stamp, glyph
registry), palette-role indexing, rendering behavior, and palette compliance
on produced surfaces.

See requirements/overhaul/42_ui_chrome_components.md §7 for the spec.
"""

from __future__ import annotations

import pygame
import pytest


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _make_surface(size: tuple[int, int] = (64, 32)) -> pygame.Surface:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


class TestStampTypeEnum:
    """Canonical stamps catalogued per spec §7.2."""

    def test_canonical_stamps_exist(self) -> None:
        from spacegame.engine.ui_chrome import StampType

        # Every stamp named in the Tier 2 docs is addressable.
        assert StampType.PERMIT
        assert StampType.RESTRICTED
        assert StampType.ILLEGAL
        assert StampType.APPROVED

    def test_each_stamp_has_role_mapping(self) -> None:
        from spacegame.engine.ui_chrome import StampType, get_stamp_palette

        for stamp in StampType:
            palette = get_stamp_palette(stamp)
            assert "background_role" in palette
            assert "text_role" in palette
            assert "default_label" in palette

    def test_stamp_roles_resolve_via_palette(self) -> None:
        """Stamp roles must be real PALETTE_ROLES entries, not raw RGBs."""
        from spacegame.engine.material_palette import is_valid_role
        from spacegame.engine.ui_chrome import StampType, get_stamp_palette

        for stamp in StampType:
            palette = get_stamp_palette(stamp)
            assert is_valid_role(palette["background_role"]), (
                f"{stamp.name} background_role '{palette['background_role']}' "
                f"is not a canonical palette role"
            )
            assert is_valid_role(palette["text_role"]), (
                f"{stamp.name} text_role '{palette['text_role']}' is not a canonical palette role"
            )

    def test_permit_and_approved_distinct(self) -> None:
        from spacegame.engine.ui_chrome import StampType, get_stamp_palette

        permit = get_stamp_palette(StampType.PERMIT)
        approved = get_stamp_palette(StampType.APPROVED)
        # Different intents should use different background roles.
        assert permit["background_role"] != approved["background_role"]

    def test_restricted_and_illegal_share_warning_family(self) -> None:
        """Both restricted/illegal use hud_critical — weight differs via styling."""
        from spacegame.engine.ui_chrome import StampType, get_stamp_palette

        restricted = get_stamp_palette(StampType.RESTRICTED)
        illegal = get_stamp_palette(StampType.ILLEGAL)
        assert restricted["background_role"] == illegal["background_role"] == "hud_critical"


class TestDrawBadge:
    """draw_badge renders a rounded-rect marker with palette-role colors."""

    def test_draw_badge_fills_rect(self) -> None:
        from spacegame.engine.ui_chrome import draw_badge

        surf = _make_surface((40, 16))
        draw_badge(surf, pygame.Rect(0, 0, 40, 16), background_role="hud_cyan")
        # Center pixel must have become opaque.
        px = surf.get_at((20, 8))
        assert px.a > 0

    def test_draw_badge_uses_background_role_color(self) -> None:
        from spacegame.engine.material_palette import get_role
        from spacegame.engine.ui_chrome import draw_badge

        surf = _make_surface((40, 16))
        draw_badge(surf, pygame.Rect(0, 0, 40, 16), background_role="hud_warning")
        warning = get_role("hud_warning")
        # Center pixel (inside border, no text) should be the warning role.
        px = surf.get_at((20, 8))
        assert (px.r, px.g, px.b) == warning

    def test_draw_badge_rejects_invalid_role(self) -> None:
        from spacegame.engine.ui_chrome import draw_badge

        surf = _make_surface((40, 16))
        with pytest.raises(KeyError):
            draw_badge(surf, pygame.Rect(0, 0, 40, 16), background_role="nonexistent_role")

    def test_draw_badge_label_text_rendered(self) -> None:
        """A labelled badge puts visible text pixels into the rect."""
        from spacegame.engine.ui_chrome import draw_badge

        surf_plain = _make_surface((40, 16))
        draw_badge(surf_plain, pygame.Rect(0, 0, 40, 16), background_role="hud_cyan")

        surf_labeled = _make_surface((40, 16))
        draw_badge(
            surf_labeled,
            pygame.Rect(0, 0, 40, 16),
            background_role="hud_cyan",
            label_text="NEW",
        )

        # Labelled version has at least one pixel that differs from the
        # plain version — the text glyphs.
        changed = False
        for y in range(16):
            for x in range(40):
                if surf_plain.get_at((x, y)) != surf_labeled.get_at((x, y)):
                    changed = True
                    break
            if changed:
                break
        assert changed, "draw_badge ignored label_text"

    def test_draw_badge_alpha_respected(self) -> None:
        from spacegame.engine.ui_chrome import draw_badge

        surf = _make_surface((40, 16))
        draw_badge(surf, pygame.Rect(0, 0, 40, 16), background_role="hud_cyan", alpha=128)
        px = surf.get_at((20, 8))
        assert px.a <= 200  # alpha honored (not full-opaque)


class TestDrawStamp:
    """draw_stamp renders a canonical stamp with type-driven color + label."""

    def test_draw_stamp_fills_rect(self) -> None:
        from spacegame.engine.ui_chrome import StampType, draw_stamp

        surf = _make_surface((80, 20))
        draw_stamp(surf, pygame.Rect(0, 0, 80, 20), stamp_type=StampType.PERMIT)
        # Interior must contain at least some opaque pixels.
        any_opaque = any(surf.get_at((x, y)).a > 0 for x in range(80) for y in range(20))
        assert any_opaque

    def test_draw_stamp_uses_type_background(self) -> None:
        from spacegame.engine.material_palette import get_role
        from spacegame.engine.ui_chrome import StampType, draw_stamp, get_stamp_palette

        for stamp in StampType:
            surf = _make_surface((80, 20))
            draw_stamp(surf, pygame.Rect(0, 0, 80, 20), stamp_type=stamp)
            expected = get_role(get_stamp_palette(stamp)["background_role"])
            # Check a pixel that's interior, not on text: corner-offset-center.
            px = surf.get_at((4, 4))
            if px.a == 0:
                continue
            # We're within the background; RGB should be the role.
            assert (px.r, px.g, px.b) == expected, (
                f"{stamp.name} interior pixel {px} != background role {expected}"
            )

    def test_draw_stamp_default_label(self) -> None:
        """Default labels come from StampType. Passing None uses the default."""
        from spacegame.engine.ui_chrome import StampType, draw_stamp

        for stamp in StampType:
            surf = _make_surface((80, 20))
            # Should not raise even when text=None (uses default_label).
            draw_stamp(surf, pygame.Rect(0, 0, 80, 20), stamp_type=stamp, text=None)

    def test_draw_stamp_custom_label_overrides_default(self) -> None:
        from spacegame.engine.ui_chrome import StampType, draw_stamp

        surf_default = _make_surface((80, 20))
        draw_stamp(surf_default, pygame.Rect(0, 0, 80, 20), stamp_type=StampType.PERMIT)

        surf_custom = _make_surface((80, 20))
        draw_stamp(
            surf_custom,
            pygame.Rect(0, 0, 80, 20),
            stamp_type=StampType.PERMIT,
            text="HAULER-7",
        )

        # Different text → different glyph pattern → at least one pixel differs.
        differ = any(
            surf_default.get_at((x, y)) != surf_custom.get_at((x, y))
            for x in range(80)
            for y in range(20)
        )
        assert differ


class TestGlyphRegistry:
    """The glyph library exposes named pixel-art icons."""

    def test_registry_has_core_tier_glyphs(self) -> None:
        """Spec §7.2 commodity tier glyphs: bulk/standard/premium/luxury/restricted/illegal."""
        from spacegame.engine.ui_chrome import glyph_names

        names = glyph_names()
        expected_tiers = {
            "tier_bulk",
            "tier_standard",
            "tier_premium",
            "tier_luxury",
            "tier_restricted",
            "tier_illegal",
        }
        missing = expected_tiers - set(names)
        assert not missing, f"Missing tier glyphs: {missing}"

    def test_registry_has_faction_insignia(self) -> None:
        """Spec §7.2 faction affinity glyphs — 5 factions."""
        from spacegame.engine.ui_chrome import glyph_names

        names = glyph_names()
        expected_factions = {
            "faction_commerce_guild",
            "faction_miners_union",
            "faction_frontier_alliance",
            "faction_science_collective",
            "faction_crimson_reach",
        }
        missing = expected_factions - set(names)
        assert not missing, f"Missing faction glyphs: {missing}"

    def test_glyph_lookup_returns_mask(self) -> None:
        from spacegame.engine.ui_chrome import get_glyph_mask

        mask = get_glyph_mask("tier_standard")
        assert len(mask) > 0
        assert len(mask[0]) > 0
        # Every row same width.
        w = len(mask[0])
        for row in mask:
            assert len(row) == w

    def test_unknown_glyph_raises(self) -> None:
        from spacegame.engine.ui_chrome import get_glyph_mask

        with pytest.raises(KeyError):
            get_glyph_mask("nonexistent_glyph")

    def test_is_valid_glyph_helper(self) -> None:
        from spacegame.engine.ui_chrome import is_valid_glyph

        assert is_valid_glyph("tier_standard")
        assert not is_valid_glyph("nonsense")


class TestDrawGlyph:
    """draw_glyph paints a registered glyph at a position with a role color."""

    def test_draw_glyph_lights_pixels(self) -> None:
        from spacegame.engine.ui_chrome import draw_glyph

        surf = _make_surface((24, 24))
        draw_glyph(surf, (4, 4), glyph_id="tier_standard", color_role="hud_cyan", size=8)

        # At least one pixel within the glyph footprint must be opaque.
        opaque_in_region = any(
            surf.get_at((x, y)).a > 0 for x in range(4, 14) for y in range(4, 14)
        )
        assert opaque_in_region

    def test_draw_glyph_uses_role_color(self) -> None:
        from spacegame.engine.material_palette import get_role
        from spacegame.engine.ui_chrome import draw_glyph

        surf = _make_surface((32, 32))
        draw_glyph(surf, (0, 0), glyph_id="tier_standard", color_role="hud_warning", size=16)
        warning = get_role("hud_warning")

        # Scan for the first opaque pixel in the glyph footprint.
        opaque_rgbs = []
        for y in range(16):
            for x in range(16):
                px = surf.get_at((x, y))
                if px.a > 0:
                    opaque_rgbs.append((px.r, px.g, px.b))
        assert opaque_rgbs
        # Every opaque pixel must be the warning RGB — no off-palette tints.
        for rgb in opaque_rgbs:
            assert rgb == warning, f"Glyph pixel {rgb} != {warning}"

    def test_draw_glyph_rejects_unknown_role(self) -> None:
        from spacegame.engine.ui_chrome import draw_glyph

        surf = _make_surface((24, 24))
        with pytest.raises(KeyError):
            draw_glyph(surf, (0, 0), glyph_id="tier_standard", color_role="nope", size=8)

    def test_draw_glyph_rejects_unknown_glyph(self) -> None:
        from spacegame.engine.ui_chrome import draw_glyph

        surf = _make_surface((24, 24))
        with pytest.raises(KeyError):
            draw_glyph(surf, (0, 0), glyph_id="nope", color_role="hud_cyan", size=8)


class TestChromePaletteCompliance:
    """Every opaque pixel rendered by a chrome primitive maps to a PALETTE_ROLES entry.

    Wires the Session 4 compliance helper into the chrome layer — regression
    alarm if a future change sneaks a raw RGB into any primitive.
    """

    def test_badge_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance
        from spacegame.engine.ui_chrome import draw_badge

        surf = _make_surface((40, 16))
        draw_badge(surf, pygame.Rect(0, 0, 40, 16), background_role="hud_cyan")
        # Label-less badge: every opaque pixel is either the bg role or
        # (if we added border) a palette-role border. tolerance accounts
        # for SDF/AA'd text edges if any.
        assert_role_compliance(surf, tolerance=4.0)

    def test_stamp_is_role_compliant_across_all_types(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance
        from spacegame.engine.ui_chrome import StampType, draw_stamp

        for stamp in StampType:
            surf = _make_surface((96, 24))
            draw_stamp(surf, pygame.Rect(0, 0, 96, 24), stamp_type=stamp)
            assert_role_compliance(surf, tolerance=4.0)

    def test_glyph_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance
        from spacegame.engine.ui_chrome import draw_glyph

        surf = _make_surface((24, 24))
        draw_glyph(
            surf, (4, 4), glyph_id="faction_miners_union", color_role="hud_accent_warm", size=12
        )
        assert_role_compliance(surf, tolerance=2.0)
