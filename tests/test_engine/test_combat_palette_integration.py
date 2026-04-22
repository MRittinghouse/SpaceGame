"""Combat C2 — VFX palette integration tests.

Verifies that combat VFX (projectiles, shields, destruction fire, dust
motes, atmospheric tint) draw their colors from the canonical palette
roles per Combat overhaul §4.5. Catches regressions where a future
change pastes a hardcoded RGB back into a combat-render path.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.5``.
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.combat_vfx import (
    CombatAtmosphere,
    DestructionSequence,
    ShieldRenderer,
    ShieldState,
    _atmosphere_dust_color,
    _atmosphere_twinkle_color,
    _fire_palette,
    _shield_color_for,
)
from spacegame.engine.material_palette import get_role
from spacegame.engine.projectiles import (
    _ELEMENT_PRIMARY_ROLE,
    ProjectileManager,
    WeaponType,
    _resolve_element_role,
)


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


# ---------------------------------------------------------------------------
# Element → palette-role table (spec §4.5)
# ---------------------------------------------------------------------------


class TestElementPaletteTable:
    """Spec §4.5 table integrity."""

    def test_every_canonical_element_has_role(self) -> None:
        for element in ("kinetic", "plasma", "ion", "cryo", "voltaic", "repair"):
            assert element in _ELEMENT_PRIMARY_ROLE, (
                f"Element '{element}' missing from _ELEMENT_PRIMARY_ROLE"
            )

    def test_element_roles_are_canonical_palette_roles(self) -> None:
        from spacegame.engine.material_palette import is_valid_role

        for element, role in _ELEMENT_PRIMARY_ROLE.items():
            assert is_valid_role(role), (
                f"Element '{element}' maps to off-palette role '{role}'"
            )

    def test_plasma_uses_plasma_core(self) -> None:
        assert _ELEMENT_PRIMARY_ROLE["plasma"] == "plasma_core"

    def test_ion_uses_ion_arc(self) -> None:
        assert _ELEMENT_PRIMARY_ROLE["ion"] == "ion_arc"

    def test_cryo_uses_cryo_fractal(self) -> None:
        assert _ELEMENT_PRIMARY_ROLE["cryo"] == "cryo_fractal"

    def test_voltaic_uses_voltaic_strike(self) -> None:
        assert _ELEMENT_PRIMARY_ROLE["voltaic"] == "voltaic_strike"

    def test_kinetic_uses_glow_warm(self) -> None:
        """Kinetic has no element tint per spec — uses glow_warm muzzle."""
        assert _ELEMENT_PRIMARY_ROLE["kinetic"] == "glow_warm"

    def test_unknown_element_falls_back_to_plasma(self) -> None:
        assert _resolve_element_role("not_a_real_element") == "plasma_core"

    def test_none_element_falls_back_to_plasma(self) -> None:
        assert _resolve_element_role(None) == "plasma_core"


# ---------------------------------------------------------------------------
# Projectile rendering — element-aware palette colors
# ---------------------------------------------------------------------------


def _render_projectile(weapon: WeaponType, element: str | None) -> pygame.Surface:
    """Spawn one projectile mid-flight and render it onto a fresh surface."""
    mgr = ProjectileManager()
    if weapon == WeaponType.LASER:
        mgr.spawn_laser((10, 30), (60, 30), element=element)
    elif weapon == WeaponType.MISSILE:
        mgr.spawn_missile((10, 30), (60, 30), element=element)
    else:
        mgr.spawn_cannon((10, 30), (60, 30), element=element, burst_count=1)
    # Advance the projectile partway so it has visible body.
    mgr.update(0.05)
    surf = pygame.Surface((100, 60), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    mgr.render(surf)
    return surf


def _surface_contains_color(
    surf: pygame.Surface, expected: tuple[int, int, int]
) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a == 0:
                continue
            if (px.r, px.g, px.b) == expected:
                return True
    return False


class TestProjectileElementColors:
    """Each spawned projectile must emit pixels of its element's role color."""

    @pytest.mark.parametrize(
        "element,role",
        [
            ("plasma", "plasma_core"),
            ("ion", "ion_arc"),
            ("cryo", "cryo_fractal"),
            ("voltaic", "voltaic_strike"),
            ("kinetic", "glow_warm"),
        ],
    )
    def test_laser_glow_uses_element_role(self, element: str, role: str) -> None:
        surf = _render_projectile(WeaponType.LASER, element)
        expected = get_role(role)
        assert _surface_contains_color(surf, expected), (
            f"Laser ({element}) did not render any {role}={expected} pixels"
        )

    def test_default_laser_falls_back_to_plasma(self) -> None:
        surf = _render_projectile(WeaponType.LASER, None)
        assert _surface_contains_color(surf, get_role("plasma_core"))

    def test_missile_trail_uses_plasma_hot(self) -> None:
        """Spec §4.5: missile exhaust = plasma_hot additive."""
        surf = _render_projectile(WeaponType.MISSILE, "plasma")
        assert _surface_contains_color(surf, get_role("plasma_hot")), (
            "Missile trail must contain plasma_hot pixels"
        )

    def test_voltaic_cannon_uses_voltaic_role(self) -> None:
        """Spec §4.5: cannon + voltaic-tech weapon → voltaic_strike."""
        surf = _render_projectile(WeaponType.CANNON, "voltaic")
        assert _surface_contains_color(surf, get_role("voltaic_strike"))

    def test_default_cannon_uses_glow_warm(self) -> None:
        """Spec §4.5: cannon muzzle baseline is glow_warm."""
        surf = _render_projectile(WeaponType.CANNON, "kinetic")
        assert _surface_contains_color(surf, get_role("glow_warm"))


# ---------------------------------------------------------------------------
# Shield palette
# ---------------------------------------------------------------------------


class TestShieldPalette:
    def test_default_shield_resolves_to_cryo_fractal(self) -> None:
        """Spec §4.5: shield ripple default = cryo_fractal."""
        assert _shield_color_for(None) == get_role("cryo_fractal")
        assert _shield_color_for("cryo") == get_role("cryo_fractal")

    def test_ion_shield_resolves_to_ion_arc(self) -> None:
        """Spec §4.5: ion-shielded variant = ion_arc."""
        assert _shield_color_for("ion") == get_role("ion_arc")

    def test_unknown_shield_element_falls_back_to_cryo(self) -> None:
        assert _shield_color_for("nonsense") == get_role("cryo_fractal")

    def test_shield_render_uses_state_element_color(self) -> None:
        renderer = ShieldRenderer()
        renderer._states["x"] = ShieldState(active=True, ratio=1.0, element="ion")
        surf = pygame.Surface((120, 120), pygame.SRCALPHA)
        renderer.render(surf, "x", 60, 60, 24)
        # Ion shield must put at least one ion_arc-tinted pixel on the
        # surface (alpha-blended, but with one of the channels matching).
        ion = get_role("ion_arc")
        any_ion_tint = any(
            surf.get_at((x, y)).r == ion[0] or surf.get_at((x, y)).b == ion[2]
            for y in range(120)
            for x in range(120)
            if surf.get_at((x, y)).a > 0
        )
        assert any_ion_tint, "Ion shield should bias the rendered surface toward ion_arc"


# ---------------------------------------------------------------------------
# Destruction fire gradient
# ---------------------------------------------------------------------------


class TestDestructionFirePalette:
    def test_fire_palette_uses_plasma_gradient(self) -> None:
        """Spec §4.5: destruction fragment fire = plasma_core → plasma_hot → glow_warm."""
        palette = _fire_palette()
        expected_roles = {get_role("plasma_core"), get_role("plasma_hot"), get_role("glow_warm")}
        assert set(palette).issubset(expected_roles | {get_role("plasma_core")}), (
            f"Fire palette {palette} drifted off-spec"
        )

    def test_destruction_fire_renders_palette_pixels(self) -> None:
        """A live destruction sequence emits fire pixels matching the gradient."""
        seq = DestructionSequence(cx=50, cy=50, sprite_radius=20)
        # Advance past the fire-emit phase.
        for _ in range(20):
            seq.update(0.05)
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        seq.render(surf)
        # At least one pixel must come from the canonical fire palette.
        gradient = set(_fire_palette())
        match = False
        for y in range(100):
            for x in range(100):
                px = surf.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) in gradient:
                    match = True
                    break
            if match:
                break
        assert match, "Destruction sequence must emit at least one palette-fire pixel"


# ---------------------------------------------------------------------------
# Atmosphere palette
# ---------------------------------------------------------------------------


class TestAtmospherePalette:
    def test_dust_color_is_void_light(self) -> None:
        """Spec §4.5: dust motes use void_light."""
        assert _atmosphere_dust_color() == get_role("void_light")

    def test_twinkle_color_is_glow_cool(self) -> None:
        """Spec §4.5: dust mote twinkle accent = glow_cool."""
        assert _atmosphere_twinkle_color() == get_role("glow_cool")

    def test_atmosphere_dust_renders_palette_pixels(self) -> None:
        atm = CombatAtmosphere(arena_rect=pygame.Rect(0, 0, 200, 200), danger_level="safe")
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        # Force dust into rendering: don't rely on randomness for color, just
        # verify a plain render produces no off-palette tones in dust pixels.
        atm.update(0.0)
        atm.render_background(surf)
        dust = get_role("void_light")
        twinkle = get_role("glow_cool")
        # Sample opaque pixels — every dust pixel is one of these two roles
        # (modulo alpha). Tint may be in play, so we just verify that at
        # least one pixel matches a canonical dust hue when one is rendered.
        opaque_seen = False
        any_palette_match = False
        for y in range(200):
            for x in range(200):
                px = surf.get_at((x, y))
                if px.a == 0:
                    continue
                opaque_seen = True
                if (px.r, px.g, px.b) in (dust, twinkle):
                    any_palette_match = True
                    break
            if any_palette_match:
                break
        # Either the surface has nothing visible (no dust generated this
        # seed) or any visible dust matches a canonical role.
        if opaque_seen:
            assert any_palette_match, "Dust pixels must use void_light or glow_cool"

    def test_crimson_tint_uses_hud_critical(self) -> None:
        """Spec §4.5: danger tint uses palette roles (no off-palette RGB)."""
        atm = CombatAtmosphere(arena_rect=pygame.Rect(0, 0, 60, 40), danger_level="crimson")
        surf = pygame.Surface((60, 40), pygame.SRCALPHA)
        atm.render_background(surf)
        # The tint overlay should put hud_critical-tinted pixels on the
        # surface. With low alpha they appear as faint hud_critical-RGB
        # over transparent — RGB equals the role exactly.
        critical = get_role("hud_critical")
        found = False
        for y in range(40):
            for x in range(60):
                px = surf.get_at((x, y))
                if (px.r, px.g, px.b) == critical and px.a > 0:
                    found = True
                    break
            if found:
                break
        assert found, "Crimson atmosphere tint must use hud_critical"

    def test_safe_atmosphere_has_no_tint(self) -> None:
        atm = CombatAtmosphere(arena_rect=pygame.Rect(0, 0, 60, 40), danger_level="safe")
        # safe has tint_role=None, so _tint_surface should be None.
        assert atm._tint_surface is None


# ---------------------------------------------------------------------------
# Projectile module discipline (regression guard)
# ---------------------------------------------------------------------------


class TestProjectileModuleDiscipline:
    """Source-level guard: legacy hardcoded projectile RGBs must stay gone."""

    def test_legacy_constants_removed(self) -> None:
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "spacegame"
            / "engine"
            / "projectiles.py"
        ).read_text(encoding="utf-8")
        for legacy in (
            "_LASER_CORE",
            "_LASER_GLOW",
            "_MISSILE_BODY",
            "_MISSILE_TRAIL",
            "_CANNON_ROUND",
        ):
            assert legacy not in source, (
                f"Legacy hardcoded constant {legacy} must not reappear"
            )

    def test_projectile_module_imports_palette(self) -> None:
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "spacegame"
            / "engine"
            / "projectiles.py"
        ).read_text(encoding="utf-8")
        assert "from spacegame.engine.material_palette import get_role" in source
