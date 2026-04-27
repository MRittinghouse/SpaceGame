"""Tests for EnemyCompositeProvider (Combat C4 Session 3).

Covers:
  - Build + composite caching (one per template id)
  - Lazy construction (no work until requested)
  - Unknown-template fallback (returns None)
  - Explicit lookup injection for test isolation
  - Coverage of every live enemy template
  - Portrait-config defaults match intent (snap on, rivets off, etc.)
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.enemy_composite_provider import EnemyCompositeProvider
from spacegame.engine.ship_composite import ShipComposite, ShipCompositeConfig
from spacegame.models.combat import EnemyBehavior, EnemyShipTemplate
from spacegame.models.ship_build import ShipBuild


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _template(
    template_id: str,
    *,
    faction: str = "",
    danger_tier: str = "moderate",
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id=template_id,
        name=f"Test {template_id}",
        description="",
        behavior=behavior,
        hull=50,
        shields=10,
        energy=5,
        energy_regen=1,
        speed=10,
        evasion=0,
        accuracy=50,
        moves=[],
        loot_table=[],
        faction_id=faction,
        danger_tier=danger_tier,
    )


def _lookup_from(templates: list[EnemyShipTemplate]):  # type: ignore[no-untyped-def]
    by_id = {t.id: t for t in templates}
    return lambda tid: by_id.get(tid)


# ---------------------------------------------------------------------------
# Lookup + caching
# ---------------------------------------------------------------------------


class TestLookupAndCaching:
    def test_unknown_template_returns_none(self) -> None:
        provider = EnemyCompositeProvider(lookup=lambda _tid: None)
        assert provider.get_build("nope") is None
        assert provider.get_composite("nope") is None
        assert provider.get_surface("nope") is None

    def test_known_template_returns_build(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        build = provider.get_build("alpha")
        assert build is not None
        assert isinstance(build, ShipBuild)

    def test_build_caching_reuses_same_instance(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        b1 = provider.get_build("alpha")
        b2 = provider.get_build("alpha")
        assert b1 is b2

    def test_composite_caching_reuses_same_instance(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        c1 = provider.get_composite("alpha")
        c2 = provider.get_composite("alpha")
        assert c1 is c2

    def test_cached_ids_report_correctly(self) -> None:
        templates = [_template("a"), _template("b")]
        provider = EnemyCompositeProvider(lookup=_lookup_from(templates))
        # Fresh provider — no cache.
        assert provider.cached_template_ids() == ()
        provider.get_composite("a")
        assert provider.cached_template_ids() == ("a",)
        provider.get_composite("b")
        assert set(provider.cached_template_ids()) == {"a", "b"}

    def test_clear_drops_cache(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        c1 = provider.get_composite("alpha")
        provider.clear()
        assert provider.cached_template_ids() == ()
        c2 = provider.get_composite("alpha")
        assert c1 is not c2  # New instance after clear


# ---------------------------------------------------------------------------
# Surface rendering
# ---------------------------------------------------------------------------


class TestSurfaceRendering:
    def test_get_surface_returns_pygame_surface(self) -> None:
        t = _template("alpha", faction="commerce_guild", danger_tier="moderate")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        surface = provider.get_surface("alpha")
        assert isinstance(surface, pygame.Surface)

    def test_surface_has_opaque_pixels(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        surface = provider.get_surface("alpha")
        assert surface is not None
        any_opaque = any(
            surface.get_at((x, y)).a > 0
            for y in range(surface.get_height())
            for x in range(surface.get_width())
        )
        assert any_opaque

    def test_surface_dimensions_scale_with_weight_class(self) -> None:
        """Dangerous tier → medium canvas (40x28) should be larger than low tier → tiny (16x16)."""
        small_t = _template("a", danger_tier="low")
        big_t = _template("b", danger_tier="dangerous")
        provider = EnemyCompositeProvider(lookup=_lookup_from([small_t, big_t]))
        small_surface = provider.get_surface("a")
        big_surface = provider.get_surface("b")
        assert small_surface is not None and big_surface is not None
        assert big_surface.get_width() > small_surface.get_width()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_portrait_config_disables_rivets(self) -> None:
        """Portrait default disables decorative noise so small renders read clean."""
        provider = EnemyCompositeProvider(lookup=lambda _tid: None)
        assert provider._config.enable_rivets is False
        assert provider._config.enable_wear_overlay is False
        assert provider._config.enable_engine_glow is False

    def test_default_portrait_config_enables_palette_snap(self) -> None:
        provider = EnemyCompositeProvider(lookup=lambda _tid: None)
        assert provider._config.enable_palette_snap is True

    def test_custom_config_is_respected(self) -> None:
        custom = ShipCompositeConfig(enable_rivets=True)
        provider = EnemyCompositeProvider(lookup=lambda _tid: None, config=custom)
        assert provider._config.enable_rivets is True


# ---------------------------------------------------------------------------
# Full live-template coverage
# ---------------------------------------------------------------------------


class TestLiveTemplateCoverage:
    def test_every_live_template_produces_a_surface(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()
        provider = EnemyCompositeProvider(lookup=lambda tid: dl.enemy_templates.get(tid))
        for template_id in dl.enemy_templates.keys():
            surface = provider.get_surface(template_id)
            assert surface is not None, f"{template_id} failed to produce a surface"
            assert surface.get_width() > 0

    def test_live_template_surface_is_cached(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()
        first_id = next(iter(dl.enemy_templates.keys()))
        provider = EnemyCompositeProvider(lookup=lambda tid: dl.enemy_templates.get(tid))
        c1 = provider.get_composite(first_id)
        c2 = provider.get_composite(first_id)
        assert c1 is c2


# ---------------------------------------------------------------------------
# ShipComposite contract
# ---------------------------------------------------------------------------


class TestShipCompositeIntegration:
    def test_returned_composite_is_shipcomposite(self) -> None:
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        composite = provider.get_composite("alpha")
        assert isinstance(composite, ShipComposite)

    def test_repeated_get_surface_stable(self) -> None:
        """Same template id always produces the same surface dimensions
        on repeated calls (caching + determinism)."""
        t = _template("alpha")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        s1 = provider.get_surface("alpha")
        s2 = provider.get_surface("alpha")
        assert s1 is not None and s2 is not None
        assert s1.get_size() == s2.get_size()


# ---------------------------------------------------------------------------
# Hand-authored composite_build override (Combat C4 §11.3)
# ---------------------------------------------------------------------------


class TestCompositeBuildOverride:
    def _template_with_override(self, build_dict: dict) -> EnemyShipTemplate:
        """Create a template with a hand-authored build override."""
        t = _template("overridden")
        # Mutation-friendly: swap in a new template instance with override.
        return EnemyShipTemplate(
            id=t.id,
            name=t.name,
            description=t.description,
            behavior=t.behavior,
            hull=t.hull,
            shields=t.shields,
            energy=t.energy,
            energy_regen=t.energy_regen,
            speed=t.speed,
            evasion=t.evasion,
            accuracy=t.accuracy,
            moves=t.moves,
            loot_table=t.loot_table,
            faction_id=t.faction_id,
            danger_tier=t.danger_tier,
            composite_build=build_dict,
        )

    def test_override_takes_precedence_over_procedural(self) -> None:
        """When composite_build is set, provider skips the generator."""
        from spacegame.models.ship_build import PlacedPixel, ShipBuild

        # Hand-authored: a specific 2-pixel build (different from any
        # procedural output the generator would produce).
        hand_build = ShipBuild(
            weight_class="tiny",
            pixels=[
                PlacedPixel(x=0, y=0, material_id="module_hull_rk"),
                PlacedPixel(x=1, y=0, material_id="module_hull_rk"),
            ],
            preset_name="Hand-Authored Boss",
        )
        t = self._template_with_override(hand_build.to_dict())
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        build = provider.get_build("overridden")
        assert build is not None
        # Must match the hand-authored build, not the generator's output.
        assert len(build.pixels) == 2
        assert build.preset_name == "Hand-Authored Boss"

    def test_no_override_falls_back_to_generator(self) -> None:
        """Templates without composite_build use the procedural generator."""
        t = _template("proc")  # composite_build is None by default
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        build = provider.get_build("proc")
        assert build is not None
        # Generator output preserves template.id as ship_type_id.
        assert build.ship_type_id == "proc"
        # Generator produces >2 pixels (elliptical silhouette).
        assert len(build.pixels) > 2

    def test_override_build_is_cached(self) -> None:
        from spacegame.models.ship_build import PlacedPixel, ShipBuild

        hand_build = ShipBuild(
            weight_class="tiny",
            pixels=[PlacedPixel(x=0, y=0, material_id="module_hull_rk")],
        )
        t = self._template_with_override(hand_build.to_dict())
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        b1 = provider.get_build("overridden")
        b2 = provider.get_build("overridden")
        assert b1 is b2  # Cached — same instance returned


class TestPerInstanceCaching:
    """Tier 3.A: composites cache per-enemy-instance so multiple living
    enemies of the same template don't share mutable state (destruction
    progress, per-module overlays, etc.).
    """

    def test_same_template_different_instances_get_different_composites(self) -> None:
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))

        # Two distinct enemy instances of the same template
        instance_a = object()
        instance_b = object()

        comp_a = provider.get_composite("scout", instance_key=instance_a)
        comp_b = provider.get_composite("scout", instance_key=instance_b)

        assert comp_a is not None
        assert comp_b is not None
        assert comp_a is not comp_b, (
            "Two enemy instances must not share a composite — destruction "
            "progress on one would otherwise thrash the other."
        )

    def test_same_instance_reuses_composite(self) -> None:
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        instance = object()

        c1 = provider.get_composite("scout", instance_key=instance)
        c2 = provider.get_composite("scout", instance_key=instance)
        assert c1 is c2

    def test_destruction_progress_isolated_per_instance(self) -> None:
        """The whole point of per-instance caching — verify directly."""
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        enemy_a = object()
        enemy_b = object()

        comp_a = provider.get_composite("scout", instance_key=enemy_a)
        comp_b = provider.get_composite("scout", instance_key=enemy_b)

        comp_a.set_destruction_progress(0.75)  # heavy damage on A
        comp_b.set_destruction_progress(0.0)  # full health on B

        assert comp_a.destruction_bucket == 0.75
        assert comp_b.destruction_bucket == 0.0, (
            "Instance B's state must not follow Instance A's mutations"
        )

    def test_no_instance_key_uses_template_scoped_cache(self) -> None:
        """Backward compat: callers passing no instance_key share one
        composite per template (test-friendly, portrait-only paths)."""
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))

        c1 = provider.get_composite("scout")
        c2 = provider.get_composite("scout")
        assert c1 is c2

    def test_prune_dead_instances_evicts_gone_enemies(self) -> None:
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))

        dead = object()
        alive = object()
        provider.get_composite("scout", instance_key=dead)
        provider.get_composite("scout", instance_key=alive)
        assert len(provider.cached_keys()) == 2

        provider.prune_dead_instances(living_enemies=[alive])

        keys = provider.cached_keys()
        assert len(keys) == 1
        assert keys[0][1] == id(alive)

    def test_prune_preserves_template_scoped_entries(self) -> None:
        """Template-scoped entries (instance_id=None) must survive prune —
        they're not per-instance and flushing them would cost us portrait
        cache on every encounter start."""
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))
        instance = object()
        provider.get_composite("scout")
        provider.get_composite("scout", instance_key=instance)
        assert len(provider.cached_keys()) == 2

        provider.prune_dead_instances(living_enemies=[])

        keys = provider.cached_keys()
        assert len(keys) == 1
        assert keys[0][1] is None, "Template-scoped entry should survive"

    def test_reset_destruction_applies_across_all_instances(self) -> None:
        """reset_destruction clears progress on EVERY cached composite."""
        t = _template("scout")
        provider = EnemyCompositeProvider(lookup=_lookup_from([t]))

        a = object()
        b = object()
        comp_a = provider.get_composite("scout", instance_key=a)
        comp_b = provider.get_composite("scout", instance_key=b)
        comp_a.set_destruction_progress(0.5)
        comp_b.set_destruction_progress(1.0)

        provider.reset_destruction()

        assert comp_a.destruction_bucket == 0.0
        assert comp_b.destruction_bucket == 0.0
