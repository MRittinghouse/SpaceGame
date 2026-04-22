"""Cached ShipComposite provider for enemy rendering (Combat C4 §4.1).

Bridges the enemy template data model to the :class:`ShipComposite`
pipeline. Combat view asks for a template id (and optionally an enemy
instance); the provider lazily generates a build via
:func:`enemy_build_generator.generate_enemy_build`, constructs a
ShipComposite around it, and caches the result for the life of the
combat encounter.

**Caching model (updated QA Pass 5 Tier 3.A — 2026-04-21):**

Builds are cached per-template — they're immutable geometry, safe to share.
Composites are cached per-INSTANCE when an ``instance_key`` is provided,
because ShipComposite carries mutable destruction/wear/state that must not
be shared across multiple living enemies of the same template. When no
instance_key is given (most tests, a few portrait-only call sites), the
cache falls back to a template-scoped key for backward compatibility.

Two render paths coexist right now:
  - **New path** — this provider, returning palette-compliant ShipComposite
    surfaces. Used for static portrait-style rendering.
  - **Legacy path** — :class:`engine.sprites.AnimatedSprite` sprite-sheet
    animations. Retained for frame-animated sequences (ship destruction
    playback) that the procedural composite doesn't cover yet.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.1`` and §11.4.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from spacegame.engine.enemy_build_generator import generate_enemy_build
from spacegame.engine.ship_composite import ShipComposite, ShipCompositeConfig
from spacegame.models.combat import EnemyShipTemplate
from spacegame.models.ship_build import ShipBuild

# Template lookup signature — takes a template id, returns the template
# or None. Accepts any callable so tests can inject fakes without pulling
# in the DataLoader singleton.
TemplateLookup = Callable[[str], Optional[EnemyShipTemplate]]

# Composite cache key. ``instance_id`` is ``id(enemy_ship)`` when caller
# provides an instance, else None for template-scoped caching.
_CompositeKey = tuple[str, Optional[int]]


class EnemyCompositeProvider:
    """Lazy, cached ShipComposite source for enemy templates.

    Construct one per combat session. The provider caches builds *and*
    composites, so repeated ``get_surface(...)`` calls for the same
    template/instance reuse the same rendered surface. :meth:`clear`
    drops the cache (e.g., on combat exit or a faction overhaul hot
    reload).
    """

    def __init__(
        self,
        lookup: TemplateLookup,
        config: Optional[ShipCompositeConfig] = None,
    ) -> None:
        """Construct a provider.

        Args:
            lookup: Callable that maps template id → EnemyShipTemplate.
                Typically ``lambda tid: get_data_loader().enemy_templates.get(tid)``.
                Injected so tests can supply stub templates.
            config: Optional :class:`ShipCompositeConfig` override. None
                uses a portrait-sensible default (no wear, no rivets,
                no engine glow — keeps UI-sized portraits clean).
        """
        self._lookup = lookup
        self._config = config if config is not None else self._portrait_config()
        self._build_cache: dict[str, ShipBuild] = {}
        self._composite_cache: dict[_CompositeKey, ShipComposite] = {}

    @staticmethod
    def _portrait_config() -> ShipCompositeConfig:
        """Portrait-friendly ShipComposite config.

        Rivets + wear + engine glow add a lot of visual texture that
        doesn't read at small portrait sizes. Palette snap stays on so
        the output remains band-compliant.
        """
        return ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_engine_glow=False,
            enable_connection_detail=False,
            enable_palette_snap=True,
        )

    # ---- cache operations -------------------------------------------------

    def clear(self) -> None:
        """Drop every cached build + composite."""
        self._build_cache.clear()
        self._composite_cache.clear()

    def reset_destruction(self) -> None:
        """Reset destruction progress on every cached composite to 0.0.

        Cheap per-encounter reset: composites stay cached (no rebuild cost
        on first render) but destruction state from a prior encounter
        cannot leak into the new one.
        """
        for composite in self._composite_cache.values():
            composite.set_destruction_progress(0.0)

    def prune_dead_instances(self, living_enemies: list) -> None:
        """Drop cached composites for enemy instances no longer in combat.

        Per-instance caching keyed on object id means stale entries can
        accumulate across encounters. Call this on combat exit OR at the
        start of a new encounter with the fresh enemy list to evict any
        composites whose enemies are gone. Template-scoped entries
        (``instance_id is None``) are preserved.
        """
        living_ids = {id(e) for e in living_enemies}
        stale = [
            key
            for key in self._composite_cache
            if key[1] is not None and key[1] not in living_ids
        ]
        for key in stale:
            del self._composite_cache[key]

    def cached_keys(self) -> tuple[_CompositeKey, ...]:
        return tuple(self._composite_cache.keys())

    def cached_template_ids(self) -> tuple[str, ...]:
        """Backward-compat alias — returns just the template_id component
        of every cached key. Preserved because existing tests use it."""
        return tuple(key[0] for key in self._composite_cache.keys())

    # ---- resolution -------------------------------------------------------

    def get_build(self, template_id: str) -> Optional[ShipBuild]:
        """Return the cached build for a template.

        Resolution order (Combat C4 §11.3):
          1. Hand-authored ``template.composite_build`` (marquee bosses)
          2. Procedural fallback via :func:`generate_enemy_build`

        Result is cached per template id. Builds are immutable geometry
        so template-scoped caching is safe.
        """
        if template_id in self._build_cache:
            return self._build_cache[template_id]
        template = self._lookup(template_id)
        if template is None:
            return None
        # Hand-authored override takes precedence when present.
        override = getattr(template, "composite_build", None)
        if override is not None:
            build = ShipBuild.from_dict(override)
        else:
            build = generate_enemy_build(template)
        self._build_cache[template_id] = build
        return build

    def get_composite(
        self,
        template_id: str,
        instance_key: Optional[object] = None,
    ) -> Optional[ShipComposite]:
        """Return a cached composite, constructing on first ask.

        When ``instance_key`` is provided (typically the ``EnemyShip``
        instance), the cache is keyed per-instance so each living enemy
        gets its own composite — critical for destruction progress and
        per-enemy visual state.

        When ``instance_key`` is None, falls back to template-scoped
        caching. Safe for portrait-only or test call sites that never
        mutate the returned composite.

        Returns ``None`` when the template is unknown — combat view falls
        back to the legacy sprite path in that case.
        """
        cache_key: _CompositeKey = (
            template_id,
            id(instance_key) if instance_key is not None else None,
        )
        if cache_key in self._composite_cache:
            return self._composite_cache[cache_key]
        build = self.get_build(template_id)
        if build is None:
            return None
        composite = ShipComposite(build, self._config)
        self._composite_cache[cache_key] = composite
        return composite

    def get_surface(
        self,
        template_id: str,
        instance_key: Optional[object] = None,
    ) -> Optional[pygame.Surface]:
        """Return the rendered ShipComposite surface for an enemy.

        Convenience wrapper over :meth:`get_composite` + ``get_surface()``.
        Combat view calls this from render paths; ``None`` means "no
        composite available, use the legacy sprite fallback".

        Pass ``instance_key`` (the EnemyShip instance) when per-enemy
        state matters (destruction progress, active module overlays).
        """
        composite = self.get_composite(template_id, instance_key=instance_key)
        if composite is None:
            return None
        return composite.get_surface()
