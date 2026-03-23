"""Refining visual effects: forge atmosphere, mastery momentum, discovery hints.

Provides visual feedback that communicates the refining progression systems —
forge intensity scaling with queue depth, mastery progress during sessions,
and recipe discovery anticipation.
"""

import math
import random as _random
from typing import Optional

import pygame

from spacegame.config import Colors, scale_x, scale_y
from spacegame.engine.fonts import FontCache, FONT_XS, FONT_SM, FONT_MD


# ==========================================================================
# Forge Atmosphere
# ==========================================================================

# Heat levels based on queue intensity
_HEAT_LEVELS = [
    {  # Cold (empty queue)
        "bg_tint": (15, 12, 10, 10),
        "particle_color": (80, 70, 60),
        "particle_rate": 2.0,
        "particle_count": 1,
        "glow_alpha": 0,
    },
    {  # Warm (1-2 jobs)
        "bg_tint": (25, 15, 8, 15),
        "particle_color": (200, 120, 40),
        "particle_rate": 0.8,
        "particle_count": 2,
        "glow_alpha": 15,
    },
    {  # Hot (3-4 jobs)
        "bg_tint": (35, 18, 5, 20),
        "particle_color": (255, 160, 30),
        "particle_rate": 0.4,
        "particle_count": 3,
        "glow_alpha": 25,
    },
    {  # Blazing (5+ jobs or tier 3)
        "bg_tint": (50, 20, 5, 30),
        "particle_color": (255, 200, 60),
        "particle_rate": 0.2,
        "particle_count": 4,
        "glow_alpha": 40,
    },
]


class ForgeAtmosphere:
    """Forge area atmosphere that scales with queue intensity.

    Empty forge is cold and dim. Full queue blazes with heat particles,
    ember glow, and warmth tinting. Recipe complexity amplifies intensity.
    """

    def __init__(self, forge_rect: pygame.Rect) -> None:
        """Initialize forge atmosphere.

        Args:
            forge_rect: The forge/queue area bounding rectangle.
        """
        self._rect = forge_rect
        self._heat_level: int = 0
        self._particles: list[dict] = []
        self._emit_timer: float = 0.0
        self._elapsed: float = 0.0
        self._rng = _random.Random(77)

    def set_intensity(self, active_jobs: int, max_tier: int = 1) -> None:
        """Update forge intensity based on queue state.

        Args:
            active_jobs: Number of jobs currently in queue.
            max_tier: Highest tier recipe in the queue (1-3).
        """
        # Tier 3 recipes add extra intensity
        effective = active_jobs + (max_tier - 1)
        if effective <= 0:
            self._heat_level = 0
        elif effective <= 2:
            self._heat_level = 1
        elif effective <= 4:
            self._heat_level = 2
        else:
            self._heat_level = 3

    def update(self, dt: float) -> None:
        self._elapsed += dt
        level = _HEAT_LEVELS[self._heat_level]

        self._emit_timer += dt
        if self._emit_timer >= level["particle_rate"]:
            self._emit_timer -= level["particle_rate"]
            r = self._rect
            for _ in range(level["particle_count"]):
                self._particles.append({
                    "x": self._rng.uniform(r.left + 10, r.right - 10),
                    "y": float(r.bottom - 5),
                    "vx": self._rng.uniform(-8, 8),
                    "vy": self._rng.uniform(-30, -10),
                    "life": self._rng.uniform(0.8, 2.0),
                    "max_life": 2.0,
                    "alpha": self._rng.randint(40, 100),
                    "size": self._rng.uniform(1.0, 3.0),
                })

        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] += self._rng.uniform(-5, 5) * dt  # Flicker
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def render(self, screen: pygame.Surface) -> None:
        r = self._rect
        level = _HEAT_LEVELS[self._heat_level]

        # Background tint
        tint = level["bg_tint"]
        tint_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        tint_surf.fill(tint)
        screen.blit(tint_surf, r.topleft)

        # Heat glow at bottom (forge hearth)
        glow_alpha = level["glow_alpha"]
        if glow_alpha > 0:
            pulse = 0.7 + 0.3 * math.sin(self._elapsed * 3.0)
            ga = int(glow_alpha * pulse)
            glow_h = min(r.height // 3, scale_y(60))
            glow_surf = pygame.Surface((r.width, glow_h), pygame.SRCALPHA)
            glow_surf.fill((255, 120, 20, ga))
            screen.blit(glow_surf, (r.left, r.bottom - glow_h))

        # Particles (embers rising)
        pc = level["particle_color"]
        for p in self._particles:
            t = p["life"] / p["max_life"]
            alpha = int(p["alpha"] * t)
            if alpha <= 0:
                continue
            size = max(1, int(p["size"] * (0.5 + 0.5 * t)))
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*pc, alpha), (size, size), size)
            screen.blit(ps, (int(p["x"]) - size, int(p["y"]) - size))


# ==========================================================================
# Mastery Momentum Bar
# ==========================================================================


class MasteryMomentumBar:
    """Shows mastery progress for the currently processing recipe.

    Displayed during active forging to make mastery progression
    visible and tangible — the player sees themselves getting closer
    to the next mastery level with each completed job.
    """

    def __init__(self, x: int, y: int, width: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = scale_y(28)
        self._recipe_name: str = ""
        self._current_crafts: int = 0
        self._next_threshold: int = 3
        self._mastery_level: int = 0
        self._visible: bool = False
        self._label_font = FontCache.get(FONT_XS)
        self._name_font = FontCache.get(FONT_SM)

    def set_recipe(
        self,
        recipe_name: str,
        current_crafts: int,
        mastery_level: int,
    ) -> None:
        """Update the displayed recipe mastery state.

        Args:
            recipe_name: Name of the recipe being forged.
            current_crafts: Total times this recipe has been crafted.
            mastery_level: Current mastery level (0-3).
        """
        self._recipe_name = recipe_name
        self._current_crafts = current_crafts
        self._mastery_level = mastery_level
        self._visible = mastery_level < 3  # Don't show if already maxed

        # Thresholds: 3, 8, 15
        thresholds = [3, 8, 15]
        if mastery_level < len(thresholds):
            self._next_threshold = thresholds[mastery_level]
        else:
            self._next_threshold = 999
            self._visible = False

    def clear(self) -> None:
        """Hide the bar (no active recipe)."""
        self._visible = False

    def render(self, screen: pygame.Surface) -> None:
        if not self._visible:
            return

        # Background
        bar_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        bg.fill((15, 12, 10, 180))
        screen.blit(bg, (self.x, self.y))
        pygame.draw.rect(screen, Colors.UI_BORDER, bar_rect, 1)

        # Mastery label
        star_labels = ["", "Bronze", "Silver", "Gold"]
        next_level = self._mastery_level + 1
        next_name = star_labels[next_level] if next_level < len(star_labels) else "Max"
        label = f"{self._recipe_name}: {self._current_crafts}/{self._next_threshold} to {next_name}"
        label_surf = self._label_font.render(label, True, Colors.TEXT_SECONDARY)
        screen.blit(label_surf, (self.x + 4, self.y + 2))

        # Progress bar
        bar_y = self.y + scale_y(14)
        bar_h = scale_y(10)
        bar_w = self.width - 8
        pygame.draw.rect(screen, Colors.BAR_BG, (self.x + 4, bar_y, bar_w, bar_h))

        ratio = min(1.0, self._current_crafts / max(1, self._next_threshold))
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            # Color: bronze → silver → gold based on target level
            colors = [(180, 120, 50), (180, 180, 200), (255, 200, 50)]
            fill_color = colors[min(self._mastery_level, len(colors) - 1)]
            pygame.draw.rect(screen, fill_color, (self.x + 4, bar_y, fill_w, bar_h))

        pygame.draw.rect(screen, Colors.UI_BORDER, (self.x + 4, bar_y, bar_w, bar_h), 1)


# ==========================================================================
# Discovery Hint
# ==========================================================================


class BufferPressure:
    """Visual warning when forge buffer approaches capacity.

    Creates escalating visual urgency as the buffer fills:
    - Under 70%: no warning
    - 70-90%: amber pulse on buffer bar area
    - 90%+: red pulse with "BUFFER CRITICAL" warning
    - 100%: solid red flash with "BUFFER FULL" alert
    """

    def __init__(self, bar_x: int, bar_y: int, bar_w: int) -> None:
        self.bar_x = bar_x
        self.bar_y = bar_y
        self.bar_w = bar_w
        self.bar_h = scale_y(12)
        self._ratio: float = 0.0
        self._elapsed: float = 0.0
        self._label_font = FontCache.get(FONT_XS)

    def set_ratio(self, ratio: float) -> None:
        """Update buffer fill ratio (0.0 = empty, 1.0 = full)."""
        self._ratio = max(0.0, min(1.0, ratio))

    def update(self, dt: float) -> None:
        self._elapsed += dt

    def render(self, screen: pygame.Surface) -> None:
        # Buffer bar background
        bg_rect = pygame.Rect(self.bar_x, self.bar_y, self.bar_w, self.bar_h)
        pygame.draw.rect(screen, Colors.BAR_BG, bg_rect)

        # Fill bar with color gradient
        fill_w = int(self.bar_w * self._ratio)
        if fill_w > 0:
            if self._ratio < 0.7:
                fill_color = (200, 160, 40)  # Amber
            elif self._ratio < 0.9:
                pulse = 0.7 + 0.3 * math.sin(self._elapsed * 4.0)
                fill_color = (
                    int(220 * pulse + 30),
                    int(140 * pulse),
                    20,
                )
            else:
                pulse = 0.5 + 0.5 * math.sin(self._elapsed * 8.0)
                fill_color = (
                    int(200 + 55 * pulse),
                    int(30 * (1 - pulse)),
                    int(20 * (1 - pulse)),
                )
            pygame.draw.rect(screen, fill_color, (self.bar_x, self.bar_y, fill_w, self.bar_h))

        pygame.draw.rect(screen, Colors.UI_BORDER, bg_rect, 1)

        # Warning text
        if self._ratio >= 1.0:
            label = self._label_font.render("BUFFER FULL", True, Colors.RED)
        elif self._ratio >= 0.9:
            label = self._label_font.render("BUFFER CRITICAL", True, (255, 120, 40))
        elif self._ratio >= 0.7:
            label = self._label_font.render("BUFFER FILLING", True, (220, 180, 60))
        else:
            pct = f"{int(self._ratio * 100)}%"
            label = self._label_font.render(f"FORGE BUFFER {pct}", True, Colors.TEXT_SECONDARY)

        screen.blit(label, (self.bar_x, self.bar_y - label.get_height() - 2))


class MasteryLevelUp:
    """Celebration effect when a recipe reaches a new mastery level.

    Golden particle burst + brief banner with the mastery tier name.
    Creates a satisfying "achievement" moment mid-session.
    """

    def __init__(self) -> None:
        self._active: bool = False
        self._timer: float = 0.0
        self._duration: float = 1.2
        self._recipe_name: str = ""
        self._level: int = 0
        self._particles: list[dict] = []
        self._rng = _random.Random()

    @property
    def active(self) -> bool:
        return self._active

    def trigger(self, recipe_name: str, level: int, cx: int, cy: int) -> None:
        """Trigger a mastery level-up celebration.

        Args:
            recipe_name: Name of the mastered recipe.
            level: New mastery level (1=Bronze, 2=Silver, 3=Gold).
            cx: Center X for particle burst.
            cy: Center Y for particle burst.
        """
        self._active = True
        self._timer = self._duration
        self._recipe_name = recipe_name
        self._level = level

        # Particle burst
        colors = [(180, 120, 50), (200, 200, 220), (255, 215, 50)]
        color = colors[min(level - 1, len(colors) - 1)]
        self._particles = []
        count = 12 + level * 5
        for i in range(count):
            angle = (2 * math.pi * i / count) + self._rng.uniform(-0.3, 0.3)
            speed = self._rng.uniform(40, 120)
            self._particles.append({
                "x": 0.0, "y": 0.0,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": self._rng.uniform(0.5, 1.0),
                "max_life": 1.0,
                "size": self._rng.uniform(1.5, 3.5),
                "color": color,
            })
        self._cx = cx
        self._cy = cy

    def update(self, dt: float) -> None:
        if not self._active:
            return
        self._timer -= dt
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 30 * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]
        if self._timer <= 0:
            self._active = False

    def render(self, screen: pygame.Surface) -> None:
        if not self._active:
            return

        t = self._timer / self._duration

        # Particles
        for p in self._particles:
            pt = p["life"] / p["max_life"]
            alpha = int(220 * pt)
            size = max(1, int(p["size"] * pt))
            color = p["color"]
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*color, alpha), (size, size), size)
            screen.blit(ps, (self._cx + int(p["x"]) - size, self._cy + int(p["y"]) - size))

        # Banner text
        if t > 0.3:
            banner_alpha = int(220 * min(1.0, (t - 0.3) / 0.3))
            tier_names = {1: "BRONZE", 2: "SILVER", 3: "GOLD"}
            tier_colors = {1: (180, 120, 50), 2: (200, 200, 220), 3: (255, 215, 50)}
            tier = tier_names.get(self._level, "")
            color = tier_colors.get(self._level, Colors.TEXT_HIGHLIGHT)

            font = FontCache.get(FONT_MD)
            text = f"MASTERY {tier}: {self._recipe_name}"
            surf = font.render(text, True, color)
            surf.set_alpha(banner_alpha)
            rect = surf.get_rect(center=(self._cx, self._cy - scale_y(40)))
            screen.blit(surf, rect)


class DiscoveryHint:
    """Shows a teaser when the player is close to unlocking a new recipe.

    Appears as a subtle banner: "Master [Recipe] to unlock a new blueprint"
    Creates anticipation and gives the player a goal to work toward.
    """

    def __init__(self, x: int, y: int, width: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self._text: str = ""
        self._visible: bool = False
        self._pulse_timer: float = 0.0
        self._font = FontCache.get(FONT_XS)

    def set_hint(self, prerequisite_name: str, target_name: str) -> None:
        """Set the discovery hint text.

        Args:
            prerequisite_name: Recipe that needs mastery.
            target_name: Recipe that will be unlocked.
        """
        self._text = f"Master {prerequisite_name} to unlock: {target_name}"
        self._visible = True

    def clear(self) -> None:
        self._visible = False

    def update(self, dt: float) -> None:
        self._pulse_timer += dt

    def render(self, screen: pygame.Surface) -> None:
        if not self._visible or not self._text:
            return

        pulse = 0.6 + 0.4 * math.sin(self._pulse_timer * 2.0)
        alpha = int(140 * pulse)

        surf = self._font.render(self._text, True, (255, 200, 80))
        surf.set_alpha(alpha)

        # Center within width
        tx = self.x + (self.width - surf.get_width()) // 2
        screen.blit(surf, (tx, self.y))
