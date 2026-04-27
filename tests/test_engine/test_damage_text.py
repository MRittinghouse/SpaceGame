"""Tests for the damage_text tier primitive (Combat C3).

Covers the canonical tier config table, item animation (hold + fade +
rise + scale), tier classification heuristic, manager lifecycle, and
palette compliance on rendered surfaces.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.7``.
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.damage_text import (
    DamageTextItem,
    DamageTextManager,
    DamageTier,
    classify_damage_text,
    get_tier_config,
)


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


# ---------------------------------------------------------------------------
# Tier config
# ---------------------------------------------------------------------------


class TestDamageTierConfig:
    def test_every_tier_has_config(self) -> None:
        for tier in DamageTier:
            cfg = get_tier_config(tier)
            assert cfg.font_size > 0
            assert cfg.total_duration > 0

    def test_font_sizes_match_spec(self) -> None:
        """Spec §4.7: 12/16/22/32 pt across tiers."""
        assert get_tier_config(DamageTier.MINOR).font_size == 12
        assert get_tier_config(DamageTier.STANDARD).font_size == 16
        assert get_tier_config(DamageTier.THRESHOLD).font_size == 22
        assert get_tier_config(DamageTier.CINEMATIC).font_size == 32

    def test_minor_has_no_hold(self) -> None:
        assert get_tier_config(DamageTier.MINOR).hold == 0.0

    def test_standard_has_no_hold(self) -> None:
        assert get_tier_config(DamageTier.STANDARD).hold == 0.0

    def test_threshold_has_hold(self) -> None:
        assert get_tier_config(DamageTier.THRESHOLD).hold == 0.15

    def test_cinematic_has_longest_hold_and_fade(self) -> None:
        cfg = get_tier_config(DamageTier.CINEMATIC)
        assert cfg.hold == 0.4
        assert cfg.fade == 2.0

    def test_stroke_reserved_for_cinematic(self) -> None:
        """Only Tier 4 gets a stroke outline per spec."""
        for tier in (DamageTier.MINOR, DamageTier.STANDARD, DamageTier.THRESHOLD):
            assert get_tier_config(tier).stroke is False
        assert get_tier_config(DamageTier.CINEMATIC).stroke is True

    def test_threshold_and_cinematic_are_bold(self) -> None:
        assert get_tier_config(DamageTier.THRESHOLD).bold is True
        assert get_tier_config(DamageTier.CINEMATIC).bold is True

    def test_threshold_pops_before_settling(self) -> None:
        cfg = get_tier_config(DamageTier.THRESHOLD)
        assert cfg.scale_start > cfg.scale_end

    def test_cinematic_total_duration_is_2_4_seconds(self) -> None:
        """0.4s hold + 2.0s fade = 2.4s total, per spec."""
        assert get_tier_config(DamageTier.CINEMATIC).total_duration == pytest.approx(2.4)


# ---------------------------------------------------------------------------
# Tier classifier
# ---------------------------------------------------------------------------


class TestClassifyDamageText:
    def test_standard_damage_defaults_to_standard(self) -> None:
        assert classify_damage_text("12 damage") == DamageTier.STANDARD

    def test_graze_classified_minor(self) -> None:
        assert classify_damage_text("GRAZE 3") == DamageTier.MINOR

    def test_armor_absorbed_classified_minor(self) -> None:
        assert classify_damage_text("Armor absorbed 4 damage") == DamageTier.MINOR

    def test_shield_regen_classified_minor(self) -> None:
        assert classify_damage_text("Shield regen +2") == DamageTier.MINOR

    def test_frozen_classified_threshold(self) -> None:
        assert classify_damage_text("FROZEN for 2 turns") == DamageTier.THRESHOLD

    def test_shields_broken_classified_threshold(self) -> None:
        assert classify_damage_text("SHIELDS BROKEN") == DamageTier.THRESHOLD

    def test_momentum_classified_threshold(self) -> None:
        assert classify_damage_text("Momentum threshold reached") == DamageTier.THRESHOLD

    def test_critical_classified_threshold(self) -> None:
        assert classify_damage_text("CRITICAL 34 damage") == DamageTier.THRESHOLD

    def test_void_release_classified_cinematic(self) -> None:
        assert classify_damage_text("VOID RELEASE: 240") == DamageTier.CINEMATIC

    def test_overdrive_classified_cinematic(self) -> None:
        assert classify_damage_text("OVERDRIVE activated") == DamageTier.CINEMATIC

    def test_cinematic_beats_threshold_when_both_match(self) -> None:
        """A cinematic-tagged line should NOT downgrade even if threshold
        keywords also appear in it."""
        assert classify_damage_text("VOID RELEASE CRITICAL HIT") == DamageTier.CINEMATIC


# ---------------------------------------------------------------------------
# Item animation
# ---------------------------------------------------------------------------


def _item(tier: DamageTier = DamageTier.STANDARD) -> DamageTextItem:
    return DamageTextItem(text="12", x=50.0, y=100.0, color_role="hud_text", tier=tier)


class TestDamageTextItemTiming:
    def test_fresh_item_is_full_alpha(self) -> None:
        item = _item()
        assert item.alpha == 255
        assert not item.finished

    def test_negative_dt_ignored(self) -> None:
        item = _item()
        item.update(-0.5)
        assert item.alpha == 255
        assert item.y == 100.0

    def test_standard_fully_fades_by_total_duration(self) -> None:
        item = _item(DamageTier.STANDARD)
        item.update(item.config.total_duration + 0.1)
        assert item.finished
        assert item.alpha == 0

    def test_threshold_holds_before_fading(self) -> None:
        item = _item(DamageTier.THRESHOLD)
        # Just before fade starts
        item.update(item.config.hold - 0.01)
        assert item.alpha == 255
        # Mid-fade
        item.update(item.config.fade * 0.5)
        alpha_mid = item.alpha
        assert 0 < alpha_mid < 255

    def test_cinematic_alpha_monotonic_non_increasing(self) -> None:
        item = _item(DamageTier.CINEMATIC)
        last = 256
        steps = int((item.config.total_duration + 0.3) / 0.05)
        for _ in range(steps):
            item.update(0.05)
            assert item.alpha <= last, f"alpha increased: {item.alpha} > {last}"
            last = item.alpha

    def test_rise_accumulates_over_lifetime(self) -> None:
        item = _item(DamageTier.STANDARD)
        origin_y = item.y
        item.update(item.config.total_duration)
        assert item.y < origin_y
        assert origin_y - item.y == pytest.approx(item.config.rise, rel=0.01)

    def test_threshold_pops_from_larger_to_settled_scale(self) -> None:
        item = _item(DamageTier.THRESHOLD)
        cfg = item.config
        assert item.scale == pytest.approx(cfg.scale_start)
        # After the pop window settles
        item.update(0.16)
        assert item.scale == pytest.approx(cfg.scale_end, abs=1e-3)

    def test_minor_stays_at_unit_scale(self) -> None:
        item = _item(DamageTier.MINOR)
        item.update(0.3)
        assert item.scale == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Manager lifecycle
# ---------------------------------------------------------------------------


class TestDamageTextManager:
    def test_empty_manager(self) -> None:
        mgr = DamageTextManager()
        assert mgr.items == ()

    def test_add_queues_item(self) -> None:
        mgr = DamageTextManager()
        item = mgr.add("12", 50.0, 100.0, color_role="hud_text")
        assert item in mgr.items

    def test_add_auto_tier_classifies_by_text(self) -> None:
        mgr = DamageTextManager()
        a = mgr.add_auto_tier("12 damage", 0, 0, "hud_text")
        b = mgr.add_auto_tier("CRITICAL 34", 0, 0, "hud_critical")
        c = mgr.add_auto_tier("VOID RELEASE: 99", 0, 0, "ion_arc")
        assert a.tier == DamageTier.STANDARD
        assert b.tier == DamageTier.THRESHOLD
        assert c.tier == DamageTier.CINEMATIC

    def test_update_prunes_finished_items(self) -> None:
        mgr = DamageTextManager()
        mgr.add("12", 0, 0, "hud_text", tier=DamageTier.STANDARD)
        mgr.add("34", 0, 0, "hud_text", tier=DamageTier.STANDARD)
        mgr.update(10.0)  # well past total_duration
        assert mgr.items == ()

    def test_clear_empties_manager(self) -> None:
        mgr = DamageTextManager()
        mgr.add("12", 0, 0, "hud_text")
        mgr.clear()
        assert mgr.items == ()


# ---------------------------------------------------------------------------
# Rendering + palette compliance
# ---------------------------------------------------------------------------


def _render_text(tier: DamageTier, color_role: str = "hud_text") -> pygame.Surface:
    mgr = DamageTextManager()
    mgr.add("42", x=50.0, y=30.0, color_role=color_role, tier=tier)
    surf = pygame.Surface((200, 80), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    mgr.render(surf)
    return surf


class TestDamageTextRendering:
    def test_rendering_produces_opaque_pixels(self) -> None:
        surf = _render_text(DamageTier.STANDARD)
        any_opaque = any(surf.get_at((x, y)).a > 0 for y in range(80) for x in range(200))
        assert any_opaque

    def test_rendering_uses_requested_role_color(self) -> None:
        from spacegame.engine.material_palette import get_role

        surf = _render_text(DamageTier.STANDARD, color_role="hud_critical")
        expected = get_role("hud_critical")
        found = any(
            (surf.get_at((x, y)).r, surf.get_at((x, y)).g, surf.get_at((x, y)).b) == expected
            and surf.get_at((x, y)).a > 0
            for y in range(80)
            for x in range(200)
        )
        assert found

    def test_cinematic_tier_includes_stroke_pixels(self) -> None:
        from spacegame.engine.material_palette import get_role

        surf = _render_text(DamageTier.CINEMATIC, color_role="plasma_core")
        stroke = get_role("void_deep")
        found_stroke = any(
            (surf.get_at((x, y)).r, surf.get_at((x, y)).g, surf.get_at((x, y)).b) == stroke
            and surf.get_at((x, y)).a > 0
            for y in range(80)
            for x in range(200)
        )
        assert found_stroke

    def test_non_cinematic_tier_has_no_stroke(self) -> None:
        """Minor/standard/threshold never render void_deep stroke pixels."""
        from spacegame.engine.material_palette import get_role

        stroke = get_role("void_deep")
        for tier in (DamageTier.MINOR, DamageTier.STANDARD, DamageTier.THRESHOLD):
            surf = _render_text(tier, color_role="hud_text")
            has_stroke = any(
                (surf.get_at((x, y)).r, surf.get_at((x, y)).g, surf.get_at((x, y)).b) == stroke
                and surf.get_at((x, y)).a > 0
                for y in range(80)
                for x in range(200)
            )
            assert not has_stroke, f"{tier.name} should not render a stroke"

    def test_faded_item_skips_render(self) -> None:
        mgr = DamageTextManager()
        item = mgr.add("42", 50.0, 30.0, color_role="hud_text", tier=DamageTier.STANDARD)
        # Fast-forward to end — alpha hits 0, item marked finished.
        item.update(item.config.total_duration + 0.1)
        # Force-remove prune step (manager.update would have done it)
        surf = pygame.Surface((200, 80), pygame.SRCALPHA)
        mgr.render(surf)
        # No pixels drawn (item is at alpha 0).
        assert not any(surf.get_at((x, y)).a > 0 for y in range(80) for x in range(200))


class TestDamageTextPaletteCompliance:
    """Rendered damage text uses canonical palette roles only."""

    def test_standard_tier_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        surf = _render_text(DamageTier.STANDARD, color_role="hud_text")
        assert_role_compliance(surf, tolerance=4.0)

    def test_cinematic_tier_with_stroke_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        surf = _render_text(DamageTier.CINEMATIC, color_role="plasma_core")
        assert_role_compliance(surf, tolerance=4.0)
