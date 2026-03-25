"""Mining visual effects: depth atmosphere, depth meter, and layer transitions.

Provides visual feedback that communicates the mining depth system —
background palette shifts, ambient particles, depth sidebar, and
dramatic layer transition effects when drilling deeper.
"""

import math
import random as _random
from typing import Optional

import pygame

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    scale_x,
    scale_y,
)
from spacegame.engine.fonts import FONT_MD, FONT_XS, get_font

# ==========================================================================
# Depth Layer Definitions
# ==========================================================================

# Depth ranges define visual treatment
_DEPTH_LAYERS = [
    {
        "name": "Surface",
        "min_depth": 1,
        "max_depth": 3,
        "bg_color": (35, 30, 22),  # Warm rocky brown
        "accent": (160, 140, 100),  # Sandy
        "particle_color": (120, 110, 90),  # Dust
        "particle_rate": 0.8,
        "description": "Loose regolith and surface deposits",
    },
    {
        "name": "Shallow Rock",
        "min_depth": 4,
        "max_depth": 6,
        "bg_color": (28, 25, 20),  # Darker brown
        "accent": (180, 120, 60),  # Iron tones
        "particle_color": (180, 130, 60),  # Iron dust
        "particle_rate": 0.6,
        "description": "Iron-rich sedimentary layers",
    },
    {
        "name": "Mid Strata",
        "min_depth": 7,
        "max_depth": 9,
        "bg_color": (22, 22, 28),  # Cool gray
        "accent": (100, 160, 200),  # Crystal blue hints
        "particle_color": (80, 140, 180),  # Crystal glint
        "particle_rate": 0.5,
        "description": "Crystalline veins and compressed ore",
    },
    {
        "name": "Deep Core",
        "min_depth": 10,
        "max_depth": 14,
        "bg_color": (18, 15, 22),  # Deep purple-dark
        "accent": (160, 80, 200),  # Rare purple glow
        "particle_color": (140, 60, 180),  # Energy wisps
        "particle_rate": 0.4,
        "description": "Pressurized rare mineral deposits",
    },
    {
        "name": "Abyssal Vein",
        "min_depth": 15,
        "max_depth": 999,
        "bg_color": (15, 10, 10),  # Near black with red tint
        "accent": (200, 60, 40),  # Magma orange-red
        "particle_color": (220, 80, 30),  # Magma embers
        "particle_rate": 0.3,
        "description": "Unstable core — extreme pressure and heat",
    },
]


def _get_layer_for_depth(depth: int) -> dict:
    """Get the visual layer config for a given depth."""
    for layer in _DEPTH_LAYERS:
        if layer["min_depth"] <= depth <= layer["max_depth"]:
            return layer
    return _DEPTH_LAYERS[-1]


def _lerp_color(
    c1: tuple[int, int, int], c2: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    """Linear interpolation between two colors."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ==========================================================================
# Mining Atmosphere
# ==========================================================================


class MiningAtmosphere:
    """Depth-responsive atmosphere for the mining mini-game.

    Renders background tinting, ambient particles, and depth-appropriate
    visual effects behind the mining grid. Intensity increases with depth.
    """

    def __init__(self, grid_rect: pygame.Rect) -> None:
        """Initialize mining atmosphere.

        Args:
            grid_rect: The mining grid's bounding rectangle.
        """
        self._grid_rect = grid_rect
        self._depth: int = 1
        self._layer = _get_layer_for_depth(1)
        self._particles: list[dict] = []
        self._emit_timer: float = 0.0
        self._elapsed: float = 0.0
        self._rng = _random.Random(42)

        # Transition animation state
        self._transitioning: bool = False
        self._transition_timer: float = 0.0
        self._transition_duration: float = 0.8
        self._old_layer: Optional[dict] = None

    def set_depth(self, depth: int) -> None:
        """Update the current depth and trigger transition if layer changed.

        Args:
            depth: Current mining depth.
        """
        new_layer = _get_layer_for_depth(depth)
        if new_layer != self._layer:
            self._old_layer = self._layer
            self._layer = new_layer
            self._transitioning = True
            self._transition_timer = self._transition_duration
        self._depth = depth

    def update(self, dt: float) -> None:
        """Advance atmosphere animations and particle emission.

        Args:
            dt: Delta time in seconds.
        """
        self._elapsed += dt

        # Transition fade
        if self._transitioning:
            self._transition_timer -= dt
            if self._transition_timer <= 0:
                self._transitioning = False
                self._old_layer = None

        # Ambient particle emission
        rate = self._layer["particle_rate"]
        self._emit_timer += dt
        if self._emit_timer >= rate:
            self._emit_timer -= rate
            gr = self._grid_rect
            self._particles.append(
                {
                    "x": self._rng.uniform(gr.left - 20, gr.right + 20),
                    "y": self._rng.uniform(gr.top, gr.bottom),
                    "vx": self._rng.uniform(-8, 8),
                    "vy": self._rng.uniform(-15, -3),
                    "life": self._rng.uniform(1.5, 3.0),
                    "max_life": 3.0,
                    "alpha": self._rng.randint(20, 50),
                    "size": self._rng.uniform(1, 2.5),
                }
            )

        # Update particles
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def render(self, screen: pygame.Surface) -> None:
        """Render the depth atmosphere behind the mining grid.

        Args:
            screen: Surface to draw on.
        """
        gr = self._grid_rect
        margin = scale_x(15)
        area = pygame.Rect(
            gr.left - margin,
            gr.top - margin,
            gr.width + margin * 2,
            gr.height + margin * 2,
        )

        # Background tint (with transition blend)
        if self._transitioning and self._old_layer:
            t = 1.0 - self._transition_timer / self._transition_duration
            bg = _lerp_color(self._old_layer["bg_color"], self._layer["bg_color"], t)
        else:
            bg = self._layer["bg_color"]

        bg_surf = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
        bg_surf.fill((*bg, 140))
        screen.blit(bg_surf, area.topleft)

        # Subtle border in accent color
        accent = self._layer["accent"]
        pygame.draw.rect(screen, (*accent, 40), area, 1)

        # Ambient particles
        pc = self._layer["particle_color"]
        for p in self._particles:
            t = p["life"] / p["max_life"]
            alpha = int(p["alpha"] * t)
            if alpha <= 0:
                continue
            size = max(1, int(p["size"]))
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*pc, alpha), (size, size), size)
            screen.blit(ps, (int(p["x"]) - size, int(p["y"]) - size))

        # Depth intensity effect: subtle pulsing glow at edges for deep layers
        if self._depth >= 10:
            pulse = 0.5 + 0.5 * math.sin(self._elapsed * 2.0)
            glow_alpha = int(15 * pulse * min(1.0, (self._depth - 9) / 5))
            glow_surf = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
            glow_surf.fill((*accent, glow_alpha))
            screen.blit(glow_surf, area.topleft)


# ==========================================================================
# Depth Meter Sidebar
# ==========================================================================


class DepthMeter:
    """Vertical depth meter sidebar showing current depth with layer zones.

    Rendered as a narrow vertical bar alongside the mining grid with
    labeled depth layer markers and the current position highlighted.
    """

    def __init__(self, x: int, y: int, height: int, max_display_depth: int = 20) -> None:
        """Initialize the depth meter.

        Args:
            x: Left edge X position.
            y: Top edge Y position.
            height: Total height in pixels.
            max_display_depth: Maximum depth shown on the meter.
        """
        self.x = x
        self.y = y
        self.height = height
        self.width = scale_x(35)
        self.max_display_depth = max_display_depth
        self._depth: int = 1
        self._label_font = get_font("label", FONT_XS)
        self._value_font = get_font("stats", FONT_MD)

    def set_depth(self, depth: int) -> None:
        """Update the current depth display."""
        self._depth = depth

    def render(self, screen: pygame.Surface) -> None:
        """Render the depth meter sidebar.

        Args:
            screen: Surface to draw on.
        """
        # Background track
        track_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        track_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        track_surf.fill((15, 12, 10, 180))
        screen.blit(track_surf, (self.x, self.y))
        pygame.draw.rect(screen, Colors.UI_BORDER, track_rect, 1)

        # Layer zones (colored segments)
        for layer in _DEPTH_LAYERS:
            y_start = self._depth_to_y(layer["min_depth"])
            y_end = self._depth_to_y(min(layer["max_depth"], self.max_display_depth))
            if y_end <= y_start:
                continue
            zone_h = y_end - y_start
            zone_surf = pygame.Surface((self.width - 2, zone_h), pygame.SRCALPHA)
            zone_surf.fill((*layer["accent"], 30))
            screen.blit(zone_surf, (self.x + 1, y_start))

            # Layer name label (rotated text would be ideal, but just use small text)
            if zone_h > scale_y(25):
                label = self._label_font.render(layer["name"], True, (*layer["accent"],))
                label.set_alpha(80)
                lx = self.x + (self.width - label.get_width()) // 2
                ly = y_start + 3
                screen.blit(label, (lx, ly))

        # Current depth marker
        marker_y = self._depth_to_y(self._depth)
        marker_h = max(4, self._depth_to_y(self._depth + 1) - marker_y)
        current_layer = _get_layer_for_depth(self._depth)
        marker_color = current_layer["accent"]

        # Bright marker bar
        pygame.draw.rect(
            screen,
            marker_color,
            (self.x + 1, marker_y, self.width - 2, marker_h),
        )

        # Depth number (right of the meter)
        depth_text = str(self._depth)
        depth_surf = self._value_font.render(depth_text, True, marker_color)
        screen.blit(depth_surf, (self.x + self.width + 4, marker_y - 2))

        # "DEPTH" label at top
        title = self._label_font.render("DEPTH", True, Colors.TEXT_SECONDARY)
        screen.blit(
            title, (self.x + (self.width - title.get_width()) // 2, self.y - title.get_height() - 2)
        )

    def _depth_to_y(self, depth: int) -> int:
        """Convert a depth value to a Y pixel position on the meter."""
        clamped = max(1, min(depth, self.max_display_depth))
        t = (clamped - 1) / max(1, self.max_display_depth - 1)
        return self.y + int(t * (self.height - 4))


# ==========================================================================
# Layer Transition Effect
# ==========================================================================


class LayerTransition:
    """Dramatic visual effect when drilling deeper (field regeneration).

    Shows a brief "drilling down" animation: screen shake, dust burst,
    rock fragments sliding away, new layer color bleeding in.
    """

    def __init__(self) -> None:
        self.active: bool = False
        self._timer: float = 0.0
        self._duration: float = 0.6
        self._fragments: list[dict] = []
        self._rng = _random.Random()
        self._new_depth: int = 1

    def trigger(self, new_depth: int, grid_rect: pygame.Rect) -> None:
        """Start the layer transition effect.

        Args:
            new_depth: The depth being transitioned TO.
            grid_rect: Grid bounds for fragment generation.
        """
        self.active = True
        self._timer = self._duration
        self._new_depth = new_depth

        # Generate rock fragments that slide downward
        self._fragments = []
        for _ in range(12):
            self._fragments.append(
                {
                    "x": self._rng.uniform(grid_rect.left, grid_rect.right),
                    "y": self._rng.uniform(grid_rect.top, grid_rect.bottom),
                    "vy": self._rng.uniform(80, 200),
                    "size": self._rng.randint(3, 8),
                    "alpha": 200,
                    "color": _get_layer_for_depth(max(1, new_depth - 1))["bg_color"],
                }
            )

    def update(self, dt: float) -> None:
        """Advance the transition animation."""
        if not self.active:
            return

        self._timer -= dt
        for frag in self._fragments:
            frag["y"] += frag["vy"] * dt
            frag["alpha"] = max(0, frag["alpha"] - dt * 300)

        if self._timer <= 0:
            self.active = False
            self._fragments.clear()

    def render(self, screen: pygame.Surface) -> None:
        """Render the transition effect overlay."""
        if not self.active:
            return

        t = self._timer / self._duration

        # Screen-wide dust flash (brief bright overlay)
        if t > 0.7:
            flash_alpha = int(60 * (t - 0.7) / 0.3)
            flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            layer = _get_layer_for_depth(self._new_depth)
            flash.fill((*layer["accent"], flash_alpha))
            screen.blit(flash, (0, 0))

        # Falling fragments
        for frag in self._fragments:
            if frag["alpha"] <= 0:
                continue
            size = frag["size"]
            alpha = int(frag["alpha"])
            color = frag["color"]
            fs = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            pygame.draw.rect(fs, (*color, alpha), (0, 0, size * 2, size))
            screen.blit(fs, (int(frag["x"]) - size, int(frag["y"])))

        # "DEPTH X" banner (fading in during transition)
        if t < 0.5:
            banner_alpha = int(200 * (1.0 - t / 0.5))
            layer = _get_layer_for_depth(self._new_depth)
            font = get_font("machine", FONT_MD)
            text = f"DEPTH {self._new_depth} — {layer['name']}"
            surf = font.render(text, True, layer["accent"])
            surf.set_alpha(banner_alpha)
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
            screen.blit(surf, rect)
