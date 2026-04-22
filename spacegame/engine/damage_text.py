"""Damage text tier primitive (Combat overhaul §4.7).

Canonical weight tiers for floating combat feedback. Each tier has a
distinct font size, timing envelope, rise curve, and optional stroke —
so the player reads graze / standard / threshold / cinematic events at
a glance instead of by color alone.

    Tier 1 (MINOR)      — graze, shield chip, armor absorb
    Tier 2 (STANDARD)   — normal damage
    Tier 3 (THRESHOLD)  — crit, momentum threshold, elemental trigger
    Tier 4 (CINEMATIC)  — dual tech impact, ultimate, boss-critical

All colors route through ``engine.material_palette.get_role`` so
combat text participates in colorblind remapping like the rest of the
palette-compliant chrome.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.7``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pygame

from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Tier enum + config
# ---------------------------------------------------------------------------


class DamageTier(Enum):
    """Canonical damage-text weight tiers."""

    MINOR = 1  # Graze, shield chip, armor absorb
    STANDARD = 2  # Normal damage
    THRESHOLD = 3  # Crit, momentum, elemental trigger
    CINEMATIC = 4  # Dual tech, ultimate, boss-critical


@dataclass(frozen=True)
class DamageTierConfig:
    """Timing + sizing envelope for one tier.

    Attributes:
        font_size: Font pixel height used when rendering.
        hold: Seconds the text stays at full alpha + scale (0 for MINOR/STANDARD).
        fade: Seconds to fade out after hold.
        rise: Total upward drift in pixels across the life of the text.
        scale_start: Initial scale factor (used for "pop" animation).
        scale_end: Final scale factor after the pop settles.
        stroke: Whether to draw a 1-pixel stroke outline for legibility.
        bold: Whether to render with pygame's bold flag.
    """

    font_size: int
    hold: float
    fade: float
    rise: float
    scale_start: float
    scale_end: float
    stroke: bool
    bold: bool

    @property
    def total_duration(self) -> float:
        return self.hold + self.fade


# Per-spec §4.7 table. Font sizes are the exact pt values the spec calls out
# (rendered 1:1 in pixels for the 1080p chrome tier).
_TIER_CONFIGS: dict[DamageTier, DamageTierConfig] = {
    DamageTier.MINOR: DamageTierConfig(
        font_size=12,
        hold=0.0,
        fade=0.6,
        rise=18.0,
        scale_start=1.0,
        scale_end=1.0,
        stroke=False,
        bold=False,
    ),
    DamageTier.STANDARD: DamageTierConfig(
        font_size=16,
        hold=0.0,
        fade=0.9,
        rise=32.0,
        scale_start=1.0,
        scale_end=1.0,
        stroke=False,
        bold=False,
    ),
    DamageTier.THRESHOLD: DamageTierConfig(
        font_size=22,
        hold=0.15,
        fade=1.2,
        rise=40.0,
        scale_start=1.25,
        scale_end=1.0,
        stroke=False,
        bold=True,
    ),
    DamageTier.CINEMATIC: DamageTierConfig(
        font_size=32,
        hold=0.4,
        fade=2.0,
        rise=24.0,
        scale_start=1.45,
        scale_end=1.0,
        stroke=True,
        bold=True,
    ),
}


def get_tier_config(tier: DamageTier) -> DamageTierConfig:
    """Return the canonical config for a tier."""
    return _TIER_CONFIGS[tier]


def classify_damage_text(effect_text: str) -> DamageTier:
    """Classify a raw combat-log effect line into a damage tier.

    Heuristic classifier for wire-up at combat-view emit sites. Callers
    who already know the semantic tier (e.g. VOID RELEASE) should pass
    :class:`DamageTier.CINEMATIC` directly rather than rely on matching.
    """
    text = effect_text.upper()
    # Cinematic-weight moments first — loudest wins.
    if any(k in text for k in ("VOID RELEASE", "OVERDRIVE", "ULTIMATE", "LEGENDARY")):
        return DamageTier.CINEMATIC
    # Threshold — critical/elemental/momentum beats.
    if any(
        k in text
        for k in (
            "CRITICAL",
            "MOMENTUM",
            "FROZEN",
            "SHIELDS BROKEN",
            "COUNTERSTRIKE",
            "SUPPRESSED",
        )
    ):
        return DamageTier.THRESHOLD
    # Minor — absorbed / grazed / regen events.
    if any(k in text for k in ("GRAZE", "ARMOR ABSORBED", "SHIELD REGEN", "CHIP")):
        return DamageTier.MINOR
    return DamageTier.STANDARD


# ---------------------------------------------------------------------------
# Item + manager
# ---------------------------------------------------------------------------


@dataclass
class DamageTextItem:
    """One floating damage text instance with tier-aware animation."""

    text: str
    x: float
    y: float
    color_role: str
    tier: DamageTier
    stroke_role: str = "void_deep"
    _elapsed: float = 0.0
    _origin_y: float = field(init=False)

    def __post_init__(self) -> None:
        self._origin_y = self.y

    @property
    def config(self) -> DamageTierConfig:
        return _TIER_CONFIGS[self.tier]

    @property
    def finished(self) -> bool:
        return self._elapsed >= self.config.total_duration

    def update(self, dt: float) -> None:
        """Advance the animation by ``dt`` seconds."""
        if dt <= 0:
            return
        self._elapsed = min(self._elapsed + dt, self.config.total_duration)
        cfg = self.config
        # Rise applies over the full lifetime, starting slow during hold,
        # accelerating through fade. Simple linear rise is sufficient here —
        # the "pop" comes from scale, not motion.
        progress = self._elapsed / max(cfg.total_duration, 1e-6)
        self.y = self._origin_y - cfg.rise * progress

    @property
    def alpha(self) -> int:
        """Current opacity 0-255. Full during hold, linear ramp during fade."""
        cfg = self.config
        if self._elapsed <= cfg.hold or cfg.fade <= 0:
            return 255 if self._elapsed < cfg.total_duration else 0
        fade_progress = (self._elapsed - cfg.hold) / cfg.fade
        return max(0, min(255, round(255 * (1.0 - fade_progress))))

    @property
    def scale(self) -> float:
        """Current scale factor. Pops from scale_start to scale_end over the
        first 150ms (or the full hold if shorter)."""
        cfg = self.config
        pop_window = min(0.15, cfg.total_duration)
        if pop_window <= 0:
            return cfg.scale_end
        t = min(self._elapsed / pop_window, 1.0)
        return cfg.scale_start + (cfg.scale_end - cfg.scale_start) * t


class DamageTextManager:
    """Owns active damage text items + renders them.

    Views construct once per combat, call ``add`` when the combat engine
    emits an event, ``update(dt)`` each frame, and ``render(screen)`` to
    paint. Items self-expire; the manager prunes on each update.
    """

    def __init__(self) -> None:
        self._items: list[DamageTextItem] = []
        self._font_cache: dict[tuple[int, bool], pygame.font.Font] = {}

    @property
    def items(self) -> tuple[DamageTextItem, ...]:
        return tuple(self._items)

    def add(
        self,
        text: str,
        x: float,
        y: float,
        color_role: str,
        tier: DamageTier = DamageTier.STANDARD,
        stroke_role: str = "void_deep",
    ) -> DamageTextItem:
        """Queue a damage text item. Returns the item for inspection."""
        item = DamageTextItem(
            text=text,
            x=x,
            y=y,
            color_role=color_role,
            tier=tier,
            stroke_role=stroke_role,
        )
        self._items.append(item)
        return item

    def add_auto_tier(
        self,
        effect_text: str,
        x: float,
        y: float,
        color_role: str,
        stroke_role: str = "void_deep",
    ) -> DamageTextItem:
        """Add an item, classifying tier automatically from the text."""
        return self.add(
            text=effect_text,
            x=x,
            y=y,
            color_role=color_role,
            tier=classify_damage_text(effect_text),
            stroke_role=stroke_role,
        )

    def clear(self) -> None:
        self._items.clear()

    def update(self, dt: float) -> None:
        for item in self._items:
            item.update(dt)
        self._items = [item for item in self._items if not item.finished]

    def render(self, screen: pygame.Surface) -> None:
        for item in self._items:
            self._render_item(screen, item)

    # ---- internals --------------------------------------------------------

    def _render_item(self, screen: pygame.Surface, item: DamageTextItem) -> None:
        cfg = item.config
        alpha = item.alpha
        if alpha == 0:
            return
        font = self._get_font(cfg.font_size, cfg.bold)
        # No AA: keeps palette-role pixels exact so compliance holds
        # (consistent with the rest of Aurelia's pixel-precise chrome).
        color = get_role(item.color_role)
        text_surf = font.render(item.text, False, color)

        # Apply scale by transforming to a larger/smaller surface.
        scale = item.scale
        if abs(scale - 1.0) > 1e-3:
            w = max(1, int(text_surf.get_width() * scale))
            h = max(1, int(text_surf.get_height() * scale))
            text_surf = pygame.transform.scale(text_surf, (w, h))

        text_surf.set_alpha(alpha)
        draw_x = int(item.x) - text_surf.get_width() // 2
        draw_y = int(item.y)

        if cfg.stroke:
            stroke_color = get_role(item.stroke_role)
            stroke_surf = font.render(item.text, False, stroke_color)
            if abs(scale - 1.0) > 1e-3:
                stroke_surf = pygame.transform.scale(
                    stroke_surf, (text_surf.get_width(), text_surf.get_height())
                )
            stroke_surf.set_alpha(alpha)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                screen.blit(stroke_surf, (draw_x + dx, draw_y + dy))

        screen.blit(text_surf, (draw_x, draw_y))

    def _get_font(self, size: int, bold: bool) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
            self._font_cache[key] = font
        return self._font_cache[key]
