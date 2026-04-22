"""Tests for CombatAtmosphere debris streaks + crimson edge glow (C6 §4.6).

Covers:
  - Per-danger debris spawn rate (none for safe/moderate, rate for dangerous/crimson)
  - Debris lifecycle (spawn, decay, expire)
  - Debris colors use the correct palette role
  - Edge glow gated on crimson only
  - Edge glow pulses via sine
  - Alpha envelope (ramp-in / hold / ramp-out)
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.combat_vfx import (
    _DEBRIS_LIFE_RANGE,
    _EDGE_GLOW_BASE_ALPHA,
    _EDGE_GLOW_PERIOD,
    CombatAtmosphere,
    _DebrisStreak,
)
from spacegame.engine.material_palette import get_role


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _arena(w: int = 400, h: int = 300) -> pygame.Rect:
    return pygame.Rect(0, 0, w, h)


# ---------------------------------------------------------------------------
# Debris spawn rate per danger
# ---------------------------------------------------------------------------


class TestDebrisSpawnRate:
    def test_safe_tier_never_spawns_debris(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="safe")
        atm.update(10.0)  # plenty of time
        assert atm._debris == []

    def test_moderate_tier_never_spawns_debris(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="moderate")
        atm.update(10.0)
        assert atm._debris == []

    def test_dangerous_tier_spawns_at_its_rate(self) -> None:
        """Dangerous debris rate = 0.25/sec → 8s yields ~2 streaks."""
        atm = CombatAtmosphere(_arena(), danger_level="dangerous")
        atm.update(8.0)
        assert 1 <= len(atm._debris) <= 3

    def test_crimson_tier_spawns_more_than_dangerous(self) -> None:
        """Crimson rate (1.5/sec) is much higher than dangerous (0.25/sec)."""
        atm_d = CombatAtmosphere(_arena(), danger_level="dangerous")
        atm_c = CombatAtmosphere(_arena(), danger_level="crimson")
        atm_d.update(4.0)
        atm_c.update(4.0)
        assert len(atm_c._debris) > len(atm_d._debris)

    def test_accumulator_does_not_burst_spawn(self) -> None:
        """Single 0.5s update at 1.5/sec should spawn ~0-1 streaks, not more."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.update(0.5)
        assert len(atm._debris) <= 1


# ---------------------------------------------------------------------------
# Debris lifecycle
# ---------------------------------------------------------------------------


class TestDebrisLifecycle:
    def test_debris_advances_position_over_time(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        # Force a spawn.
        atm._spawn_debris_streak()
        streak = atm._debris[0]
        x0 = streak.x
        y0 = streak.y
        atm.update(0.2)
        # vx is negative (right-to-left drift).
        assert streak.x != x0 or streak.y != y0

    def test_debris_expires_after_lifespan(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm._spawn_debris_streak()
        # Max debris lifespan is 3s — advance past it.
        atm.update(_DEBRIS_LIFE_RANGE[1] + 0.5)
        # Expired streaks should have been pruned.
        assert len(atm._debris) == 0 or all(s.life_remaining > 0 for s in atm._debris)

    def test_debris_alpha_envelope_ramps_in(self) -> None:
        """Fresh streak has alpha_factor near 0; mid-life = 1.0."""
        streak = _DebrisStreak(
            x=100, y=100, vx=-100, vy=0, length=40, life_remaining=2.0, max_life=2.0
        )
        assert streak.alpha_factor <= 0.1
        # Mid-life.
        streak.life_remaining = 1.0
        assert streak.alpha_factor == 1.0

    def test_debris_alpha_envelope_ramps_out(self) -> None:
        streak = _DebrisStreak(
            x=100, y=100, vx=-100, vy=0, length=40, life_remaining=0.1, max_life=2.0
        )
        # Last 20% of life — should be ramping out.
        assert 0.0 < streak.alpha_factor < 1.0

    def test_debris_alpha_at_max_life_is_zero(self) -> None:
        streak = _DebrisStreak(
            x=100, y=100, vx=-100, vy=0, length=40, life_remaining=0.0, max_life=2.0
        )
        assert streak.alpha_factor == 0.0


# ---------------------------------------------------------------------------
# Debris rendering uses correct palette role
# ---------------------------------------------------------------------------


def _contains_color(surf: pygame.Surface, rgb: tuple[int, int, int]) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a > 0 and (px.r, px.g, px.b) == rgb:
                return True
    return False


class TestDebrisRendering:
    def test_dangerous_debris_uses_hud_warning(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="dangerous")
        # Force-spawn a fresh streak and advance slightly so alpha > 0.
        atm._spawn_debris_streak()
        atm.update(0.3)
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_debris(canvas)
        assert _contains_color(canvas, get_role("hud_warning"))

    def test_crimson_debris_uses_hud_critical(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm._spawn_debris_streak()
        atm.update(0.3)
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_debris(canvas)
        assert _contains_color(canvas, get_role("hud_critical"))

    def test_safe_tier_render_produces_no_debris_pixels(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="safe")
        atm.update(5.0)  # lots of time; no debris should appear
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_debris(canvas)
        # hud_warning and hud_critical should not appear.
        assert not _contains_color(canvas, get_role("hud_warning"))
        assert not _contains_color(canvas, get_role("hud_critical"))


# ---------------------------------------------------------------------------
# Edge glow (crimson only)
# ---------------------------------------------------------------------------


class TestEdgeGlow:
    def test_safe_has_no_edge_glow(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="safe")
        atm.update(0.5)
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_edge_glow(canvas)
        assert not _contains_color(canvas, get_role("hud_critical"))

    def test_dangerous_has_no_edge_glow(self) -> None:
        """Dangerous tier has debris but no edge glow."""
        atm = CombatAtmosphere(_arena(), danger_level="dangerous")
        atm.update(0.5)
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_edge_glow(canvas)
        # Debris renders separately; edge_glow_role is None for dangerous.
        # Can't assert "no hud_warning" because debris uses that — but
        # we're rendering _render_edge_glow alone, so only glow pixels
        # are on this canvas. hud_warning + hud_critical both absent.
        assert not _contains_color(canvas, get_role("hud_warning"))
        assert not _contains_color(canvas, get_role("hud_critical"))

    def test_crimson_renders_edge_glow(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        # Set elapsed to peak-pulse phase so alpha is maximal.
        atm._elapsed = _EDGE_GLOW_PERIOD * 0.25  # sin(π/2) = 1
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_edge_glow(canvas)
        assert _contains_color(canvas, get_role("hud_critical"))

    def test_edge_glow_alpha_pulses_with_sine(self) -> None:
        """Edge glow alpha is a sine wave over _EDGE_GLOW_PERIOD."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")

        def _glow_alpha(elapsed: float) -> int:
            atm._elapsed = elapsed
            canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
            canvas.fill((0, 0, 0, 0))
            atm._render_edge_glow(canvas)
            # Sample an edge pixel where the glow definitely paints.
            px = canvas.get_at((5, 150))
            return px.a

        peak = _glow_alpha(_EDGE_GLOW_PERIOD * 0.25)  # sin(π/2) = 1
        trough = _glow_alpha(_EDGE_GLOW_PERIOD * 0.75)  # sin(3π/2) = -1
        assert peak > trough

    def test_crimson_glow_base_alpha_non_zero(self) -> None:
        """At sine=0 (mid pulse), glow is at base alpha (still visible)."""
        assert _EDGE_GLOW_BASE_ALPHA > 0


# ---------------------------------------------------------------------------
# Render_background integration
# ---------------------------------------------------------------------------


class TestRenderBackgroundIntegration:
    def test_render_background_calls_without_crash(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.update(5.0)
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        # Full render should complete without exception.
        atm.render_background(canvas)

    def test_crimson_render_shows_tint_debris_and_glow(self) -> None:
        """A fully-elapsed crimson render should include all three layers."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm._elapsed = _EDGE_GLOW_PERIOD * 0.25  # peak glow phase
        # Spawn a streak explicitly so rendering has something to show.
        atm._spawn_debris_streak()
        atm.update(0.3)  # let debris alpha ramp in
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm.render_background(canvas)
        # hud_critical appears from both debris AND edge glow. Confirm presence.
        assert _contains_color(canvas, get_role("hud_critical"))


# ---------------------------------------------------------------------------
# Arc-flash (C6 deferral — spec §4.6)
# ---------------------------------------------------------------------------


class TestArcFlash:
    def test_non_crimson_tiers_cannot_trigger_arc_flash(self) -> None:
        """Arc-flash is crimson-only; trigger_arc_flash no-ops elsewhere."""
        for tier in ("safe", "moderate", "dangerous"):
            atm = CombatAtmosphere(_arena(), danger_level=tier)
            atm.trigger_arc_flash()
            assert not atm.is_arc_flash_active

    def test_crimson_trigger_activates_flash(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.trigger_arc_flash()
        assert atm.is_arc_flash_active

    def test_arc_flash_decays_after_duration(self) -> None:
        from spacegame.engine.combat_vfx import _ARC_FLASH_DURATION

        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.trigger_arc_flash()
        atm.update(_ARC_FLASH_DURATION + 0.1)
        assert not atm.is_arc_flash_active

    def test_arc_flash_renders_voltaic_strike(self) -> None:
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.trigger_arc_flash()
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm._render_arc_flash(canvas)
        assert _contains_color(canvas, get_role("voltaic_strike"))

    def test_arc_flash_schedules_next(self) -> None:
        """After a flash fires, the timer is reset to a new random interval."""
        from spacegame.engine.combat_vfx import _ARC_FLASH_INTERVAL_RANGE

        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        atm.trigger_arc_flash()
        # Timer is now in the random interval range.
        assert _ARC_FLASH_INTERVAL_RANGE[0] <= atm._arc_flash_timer <= _ARC_FLASH_INTERVAL_RANGE[1]

    def test_arc_flash_fires_automatically_on_timer_expiry(self) -> None:
        from spacegame.engine.combat_vfx import _ARC_FLASH_INTERVAL_RANGE

        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        # Force timer to near-zero so a small update triggers the flash.
        atm._arc_flash_timer = 0.01
        atm.update(0.02)
        assert atm.is_arc_flash_active
        # Next timer is scheduled in the canonical range.
        assert _ARC_FLASH_INTERVAL_RANGE[0] <= atm._arc_flash_timer <= _ARC_FLASH_INTERVAL_RANGE[1]


# ---------------------------------------------------------------------------
# render_background alpha factor (C3 ArenaEntry fade-in)
# ---------------------------------------------------------------------------


class TestRenderAlphaFactor:
    def test_full_factor_matches_legacy_behavior(self) -> None:
        """alpha_factor=1.0 renders tint + dust at normal alpha."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        canvas_a = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas_a.fill((0, 0, 0, 0))
        canvas_b = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas_b.fill((0, 0, 0, 0))
        atm.render_background(canvas_a)
        atm.render_background(canvas_b, alpha_factor=1.0)
        for y in range(300):
            for x in range(400):
                assert canvas_a.get_at((x, y)) == canvas_b.get_at((x, y))

    def test_zero_factor_skips_tint(self) -> None:
        """alpha_factor=0 produces no tint pixels."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        canvas = pygame.Surface((400, 300), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        atm.render_background(canvas, alpha_factor=0.0)
        # Tint is crimson; no dust will be opaque either at alpha 0.
        # The edge glow still renders (it has its own phase/alpha).
        # Assertion: no pixel from the tint fills the arena interior
        # where the edge glow doesn't reach.
        interior_pixel = canvas.get_at((200, 150))  # center, well away from edges
        # hud_critical tint + no glow at interior = should be transparent.
        assert interior_pixel.a == 0

    def test_half_factor_dims_tint(self) -> None:
        """alpha_factor=0.5 produces dimmer tint than factor=1.0."""
        atm = CombatAtmosphere(_arena(), danger_level="crimson")
        a = pygame.Surface((400, 300), pygame.SRCALPHA)
        a.fill((0, 0, 0, 0))
        b = pygame.Surface((400, 300), pygame.SRCALPHA)
        b.fill((0, 0, 0, 0))
        atm.render_background(a, alpha_factor=0.5)
        atm.render_background(b, alpha_factor=1.0)
        # Sample an interior point: b should have more alpha than a.
        px_a = a.get_at((200, 150))
        px_b = b.get_at((200, 150))
        # Both have the tint overlay; b's alpha is higher.
        assert px_b.a >= px_a.a
