"""Tests for EnemyModuleOverlayProvider (Tier 3.C, 2026-04-21).

Covers:
  - Canonical region layout per subsystem tag
  - Per-instance caching (mirror of composite provider)
  - Stale instance eviction
  - State sync from enemy runtime fields (destroyed, focused)
"""

from __future__ import annotations

import pygame

from spacegame.engine.enemy_overlay_provider import (
    EnemyModuleOverlayProvider,
    canonical_subsystem_regions,
)
from spacegame.engine.ship_module_overlay import ModuleOverlayState
from spacegame.models.ship_build import ShipBuild


def _build(weight_class: str = "tiny") -> ShipBuild:
    return ShipBuild(weight_class=weight_class, pixels=[])


class _FakeEnemy:
    """Minimal stand-in for EnemyShip to isolate overlay-provider tests
    from the combat model. Has just what sync_state_from_enemy reads."""

    def __init__(
        self,
        *,
        destroyed: set[str] | None = None,
        focused: str | None = None,
    ) -> None:
        self.subsystems_destroyed = destroyed or set()
        self.focused_subsystem = focused


class TestCanonicalSubsystemRegions:
    def test_six_known_tags_all_produce_regions(self) -> None:
        build = _build("small")
        tags = [
            "cockpit",
            "weapon_array",
            "sensor_array",
            "shield_generator",
            "reactor",
            "engine",
        ]
        regions = canonical_subsystem_regions(build, tags)
        assert len(regions) == 6
        assert {r.module_id for r in regions} == set(tags)

    def test_unknown_tag_silently_dropped(self) -> None:
        build = _build("tiny")
        regions = canonical_subsystem_regions(build, ["engine", "warp_core"])
        assert len(regions) == 1
        assert regions[0].module_id == "engine"

    def test_regions_fit_inside_canvas(self) -> None:
        build = _build("small")
        regions = canonical_subsystem_regions(
            build,
            ["cockpit", "engine", "weapon_array"],
        )
        w = build.canvas_w
        h = build.canvas_h
        for region in regions:
            assert 0 <= region.x < w
            assert 0 <= region.y < h
            assert region.x + region.w <= w
            assert region.y + region.h <= h
            assert region.w >= 1 and region.h >= 1

    def test_front_is_right_side_cockpit_at_right(self) -> None:
        """The silhouette generator points ships right, so cockpit
        regions should live in the right half of the canvas."""
        build = _build("small")
        regions = canonical_subsystem_regions(build, ["cockpit"])
        cockpit = regions[0]
        assert cockpit.x >= build.canvas_w // 2, (
            f"Cockpit should be in the front (right) half, got x={cockpit.x}"
        )

    def test_engine_is_left_side(self) -> None:
        build = _build("small")
        regions = canonical_subsystem_regions(build, ["engine"])
        engine = regions[0]
        # Engine lives in the back quarter
        assert engine.x < build.canvas_w // 2

    def test_empty_tag_list_produces_no_regions(self) -> None:
        build = _build("tiny")
        assert canonical_subsystem_regions(build, []) == []


class TestPerInstanceOverlays:
    def test_same_template_different_instances_get_separate_overlays(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("small")
        tags = ["engine", "weapon_array"]

        a = object()
        b = object()
        overlay_a = provider.get_overlay("pirate_scout", build, tags, instance_key=a)
        overlay_b = provider.get_overlay("pirate_scout", build, tags, instance_key=b)

        assert overlay_a is not overlay_b

    def test_same_instance_reuses_overlay(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("small")
        enemy = object()
        o1 = provider.get_overlay("scout", build, ["engine"], instance_key=enemy)
        o2 = provider.get_overlay("scout", build, ["engine"], instance_key=enemy)
        assert o1 is o2

    def test_regions_registered_on_first_fetch(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("small")
        overlay = provider.get_overlay(
            "scout", build, ["engine", "reactor"], instance_key=object()
        )
        assert set(overlay.module_ids()) == {"engine", "reactor"}


class TestPruneDeadInstances:
    def test_stale_instances_evicted(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        alive = object()
        dead = object()
        provider.get_overlay("scout", build, ["engine"], instance_key=alive)
        provider.get_overlay("scout", build, ["engine"], instance_key=dead)
        assert len(provider.cached_keys()) == 2

        provider.prune_dead_instances([alive])
        keys = provider.cached_keys()
        assert len(keys) == 1
        assert keys[0][1] == id(alive)


class TestSyncStateFromEnemy:
    def test_destroyed_sets_destroyed_state(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        overlay = provider.get_overlay(
            "scout", build, ["engine", "reactor"], instance_key=object()
        )
        enemy = _FakeEnemy(destroyed={"engine"})

        provider.sync_state_from_enemy(overlay, enemy)

        assert overlay.get_region("engine").state == ModuleOverlayState.DESTROYED
        assert overlay.get_region("reactor").state == ModuleOverlayState.NORMAL

    def test_focused_sets_highlighted_state(self) -> None:
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        overlay = provider.get_overlay(
            "scout", build, ["engine", "reactor"], instance_key=object()
        )
        enemy = _FakeEnemy(focused="engine")

        provider.sync_state_from_enemy(overlay, enemy)

        assert overlay.get_region("engine").state == ModuleOverlayState.HIGHLIGHTED
        assert overlay.get_region("reactor").state == ModuleOverlayState.NORMAL

    def test_destroyed_precedence_over_focused(self) -> None:
        """If a subsystem is both destroyed AND focused (stale UI), DESTROYED wins."""
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        overlay = provider.get_overlay(
            "scout", build, ["engine"], instance_key=object()
        )
        enemy = _FakeEnemy(destroyed={"engine"}, focused="engine")

        provider.sync_state_from_enemy(overlay, enemy)

        assert overlay.get_region("engine").state == ModuleOverlayState.DESTROYED

    def test_unfocused_and_alive_resets_to_normal(self) -> None:
        """If state was previously HIGHLIGHTED and now unfocused, revert to NORMAL."""
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        overlay = provider.get_overlay(
            "scout", build, ["engine"], instance_key=object()
        )
        # First sync: focused
        provider.sync_state_from_enemy(overlay, _FakeEnemy(focused="engine"))
        assert overlay.get_region("engine").state == ModuleOverlayState.HIGHLIGHTED

        # Second sync: no focus
        provider.sync_state_from_enemy(overlay, _FakeEnemy())
        assert overlay.get_region("engine").state == ModuleOverlayState.NORMAL

    def test_enemy_without_overlay_fields_does_not_crash(self) -> None:
        """Defensive: a minimal enemy missing the runtime fields must not blow up."""
        provider = EnemyModuleOverlayProvider()
        build = _build("tiny")
        overlay = provider.get_overlay(
            "scout", build, ["engine"], instance_key=object()
        )

        class MinimalEnemy:
            pass  # No subsystems_destroyed, no focused_subsystem

        provider.sync_state_from_enemy(overlay, MinimalEnemy())
        assert overlay.get_region("engine").state == ModuleOverlayState.NORMAL


class TestOverlayRenderDoesNotCrash:
    """The whole integration must be paintable on a pygame Surface."""

    def test_render_onto_surface(self) -> None:
        pygame.init()
        provider = EnemyModuleOverlayProvider()
        build = _build("small")
        enemy = object()
        overlay = provider.get_overlay(
            "scout", build, ["engine", "weapon_array"], instance_key=enemy
        )

        # Simulate a focused + destroyed state
        overlay.set_state("engine", ModuleOverlayState.HIGHLIGHTED)
        overlay.set_state("weapon_array", ModuleOverlayState.DESTROYED)

        surface = pygame.Surface((build.canvas_w, build.canvas_h), pygame.SRCALPHA)
        overlay.render(surface, origin_x=0, origin_y=0, cell_size=1)

        # Verify the surface has non-transparent pixels (overlay painted something)
        has_overlay_pixel = False
        for y in range(surface.get_height()):
            for x in range(surface.get_width()):
                if surface.get_at((x, y)).a > 0:
                    has_overlay_pixel = True
                    break
            if has_overlay_pixel:
                break
        assert has_overlay_pixel, "Overlay render produced no visible pixels"
