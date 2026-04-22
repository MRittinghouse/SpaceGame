"""Dual tech cinematic orchestrator (Combat overhaul §4.3).

Bridges the three C5 primitives — :class:`DualTechCinematic` timeline,
:func:`render_portraits`, :func:`render_element_trail` — into one
cohesive lifecycle object that combat view consumes per-cinematic.

Lifecycle:
  1. Combat view detects a dual tech trigger (move dispatch, ultimate
     activation, scripted cutscene).
  2. Combat view calls :meth:`DualTechController.from_inputs(...)` with
     tech name, element pair, crew portraits, and impact source/target.
     Optionally supplies an ``on_impact`` callback for damage resolution.
  3. Combat view stores the controller and, each frame:
     - Calls ``update(dt)`` to advance the timeline (fires on_impact
       exactly once at the IMPACT phase boundary).
     - Reads ``camera_zoom_factor`` to interpolate SceneCamera zoom
       and ``impact_shake_factor`` to drive camera shake.
     - Calls ``render(screen)`` last so the cinematic paints over all
       normal combat + UI rendering.
     - Checks ``is_complete`` to clear the slot and resume normal turn
       flow.

Keeping every rendering decision in one controller means combat view
doesn't need to reason about which overlay is active at which phase —
the controller handles phase gating internally.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.3``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pygame

from spacegame.engine.damage_text import DamageTier, get_tier_config
from spacegame.engine.dual_tech_cinematic import DualTechCinematic, DualTechPhase
from spacegame.engine.dual_tech_element_trail import TrailConfig, render_element_trail
from spacegame.engine.dual_tech_portraits import PortraitConfig, render_portraits
from spacegame.engine.material_palette import get_role

# Tech-name text uses the Tier 4 cinematic treatment from damage_text.py
# so the stroke + font size match the damage-number weight tier. This
# reinforces the visual language: "big things happening."
_STROKE_ROLE = "void_deep"


@dataclass
class DualTechController:
    """Live dual tech cinematic — owns timeline, renderers, and callback.

    Use :meth:`from_inputs` to construct from primitive inputs; the
    dataclass constructor is exposed for tests that want to inject
    custom timeline or renderer configs directly.
    """

    timeline: DualTechCinematic
    left_portrait: PortraitConfig
    right_portrait: PortraitConfig
    trail_config: TrailConfig
    on_impact: Optional[Callable[[], None]] = None

    # ---- factory ---------------------------------------------------------

    @classmethod
    def from_inputs(
        cls,
        tech_name: str,
        dominant_element: str,
        secondary_element: str,
        left_portrait: PortraitConfig,
        right_portrait: PortraitConfig,
        trail_start: tuple[float, float],
        trail_end: tuple[float, float],
        is_ultimate: bool = False,
        on_impact: Optional[Callable[[], None]] = None,
    ) -> "DualTechController":
        """Build a controller from primitive inputs.

        Combat view uses this at dual tech dispatch time. The timeline
        auto-resolves element palette roles, which the trail config
        picks up for its head + trail colors.
        """
        timeline = DualTechCinematic(
            tech_name=tech_name,
            dominant_element=dominant_element,
            secondary_element=secondary_element,
            is_ultimate=is_ultimate,
        )
        trail_config = TrailConfig(
            start=trail_start,
            end=trail_end,
            dominant_role=timeline.dominant_role,
            trail_role=timeline.trail_role,
        )
        return cls(
            timeline=timeline,
            left_portrait=left_portrait,
            right_portrait=right_portrait,
            trail_config=trail_config,
            on_impact=on_impact,
        )

    # ---- lifecycle -------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the timeline. Fires ``on_impact`` once at IMPACT start."""
        self.timeline.update(dt)
        if self.timeline.consume_impact_trigger() and self.on_impact is not None:
            self.on_impact()

    @property
    def is_complete(self) -> bool:
        return self.timeline.is_complete

    # ---- factor passthroughs for camera + shake --------------------------

    @property
    def camera_zoom_factor(self) -> float:
        """0.0 → 1.0 over the CAMERA_ZOOM phase; 1.0 thereafter."""
        return self.timeline.camera_zoom_factor

    @property
    def impact_shake_factor(self) -> float:
        """Shake amplitude multiplier during IMPACT phase; 0 otherwise."""
        return self.timeline.impact_shake_factor

    @property
    def phase(self) -> DualTechPhase:
        return self.timeline.phase

    # ---- rendering -------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        """Paint the full cinematic over ``screen``.

        Render order (back to front):
          1. Screen darken overlay (peaks at 70% black during central phases)
          2. Element trail (during COMBINED_RESOLVE / CHARGE)
          3. Portraits (slide in from edges; bottom-left + bottom-right)
          4. Tech name text (centered during NAME_HOLD, fades on next phase)
        """
        self._render_darken(screen)
        self._render_trail(screen)
        self._render_portraits(screen)
        self._render_tech_name(screen)

    # ---- internals -------------------------------------------------------

    def _render_darken(self, screen: pygame.Surface) -> None:
        alpha = self.timeline.darken_alpha
        if alpha <= 0:
            return
        sw, sh = screen.get_size()
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

    def _render_trail(self, screen: pygame.Surface) -> None:
        progress = self.timeline.combined_resolve_progress
        # Only render trail during/after NAME_HOLD's end; skip when the
        # cinematic is complete to avoid a stale frame during the
        # controller-clear transition.
        if progress <= 0 or self.timeline.is_complete:
            return
        render_element_trail(screen, self.trail_config, progress)

    def _render_portraits(self, screen: pygame.Surface) -> None:
        alpha = self.timeline.portrait_alpha
        if alpha <= 0:
            return
        render_portraits(
            screen,
            self.left_portrait,
            self.right_portrait,
            slide_factor=self.timeline.portrait_slide_factor,
            alpha=alpha,
        )

    def _render_tech_name(self, screen: pygame.Surface) -> None:
        alpha = self.timeline.tech_name_alpha
        if alpha <= 0:
            return

        tier = get_tier_config(DamageTier.CINEMATIC)
        font = pygame.font.Font(None, tier.font_size)
        font.set_bold(tier.bold)

        dominant_color = get_role(self.timeline.dominant_role)
        stroke_color = get_role(_STROKE_ROLE)

        text_surf = font.render(self.timeline.tech_name, False, dominant_color)
        stroke_surf = font.render(self.timeline.tech_name, False, stroke_color)
        text_surf.set_alpha(alpha)
        stroke_surf.set_alpha(alpha)

        sw, sh = screen.get_size()
        tx = sw // 2 - text_surf.get_width() // 2
        ty = sh // 2 - text_surf.get_height() // 2

        # 4-direction stroke first, then the colored text on top.
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            screen.blit(stroke_surf, (tx + dx, ty + dy))
        screen.blit(text_surf, (tx, ty))
