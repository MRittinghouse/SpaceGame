"""Salvage visual effects: derelict atmosphere, deck meter, corruption pressure.

Provides visual feedback that communicates the salvage deck descent and
corruption pressure systems — derelict-specific atmospheres, deck progression
sidebar, corruption warnings, and deck transition effects.
"""

import math
import random as _random
from typing import Optional

import pygame

from spacegame.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    Colors,
    scale_x,
    scale_y,
)
from spacegame.engine.fonts import FontCache, FONT_XS, FONT_SM, FONT_MD


# ==========================================================================
# Derelict Type Visual Profiles
# ==========================================================================

_DERELICT_PROFILES = {
    "cargo_bay": {
        "name": "Cargo Bay",
        "bg_colors": [
            (25, 22, 18),   # Deck 1: warm brown (cargo crates)
            (22, 20, 16),   # Deck 2: darker, deeper in hold
            (18, 16, 14),   # Deck 3: deep storage
            (14, 12, 12),   # Deck 4: sub-level
        ],
        "accent": (200, 170, 100),  # Cargo amber
        "particle_color": (160, 140, 100),  # Dust/debris
        "particle_style": "dust",
        "atmosphere_text": "Hull groans echo through empty cargo racks",
    },
    "lab_module": {
        "name": "Lab Module",
        "bg_colors": [
            (18, 22, 30),   # Deck 1: sterile blue-white
            (14, 18, 26),   # Deck 2: deeper, flickering lights
            (10, 14, 22),   # Deck 3: dark lab, emergency lighting
        ],
        "accent": (100, 180, 220),  # Lab cyan
        "particle_color": (80, 160, 200),  # Chemical vapor
        "particle_style": "vapor",
        "atmosphere_text": "Chemical residue floats in zero-g pockets",
    },
    "engine_room": {
        "name": "Engine Room",
        "bg_colors": [
            (28, 18, 14),   # Deck 1: warm industrial
            (24, 15, 12),   # Deck 2: heat haze
            (20, 12, 10),   # Deck 3: hot, sparks
            (16, 10, 8),    # Deck 4: reactor adjacent
            (12, 8, 8),     # Deck 5: core proximity
        ],
        "accent": (255, 140, 40),  # Engine orange
        "particle_color": (255, 120, 30),  # Sparks
        "particle_style": "sparks",
        "atmosphere_text": "Residual reactor heat makes the hull tick and pop",
    },
}

_DEFAULT_PROFILE = _DERELICT_PROFILES["cargo_bay"]


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
# Salvage Atmosphere
# ==========================================================================


class SalvageAtmosphere:
    """Derelict-specific atmosphere for the salvage mini-game.

    Renders background tinting, ambient particles, and corruption
    pressure visualization behind the salvage grid.
    """

    def __init__(self, grid_rect: pygame.Rect, derelict_type: str = "cargo_bay") -> None:
        self._grid_rect = grid_rect
        self._profile = _DERELICT_PROFILES.get(derelict_type, _DEFAULT_PROFILE)
        self._deck: int = 1
        self._corruption_ratio: float = 1.0  # 1.0 = full time, 0.0 = corrupted
        self._particles: list[dict] = []
        self._emit_timer: float = 0.0
        self._elapsed: float = 0.0
        self._rng = _random.Random(hash(derelict_type) + 99)

        # Transition state
        self._transitioning: bool = False
        self._transition_timer: float = 0.0
        self._transition_duration: float = 0.7

    def set_deck(self, deck: int) -> None:
        """Update the current deck and trigger transition."""
        if deck != self._deck:
            self._transitioning = True
            self._transition_timer = self._transition_duration
        self._deck = deck

    def set_corruption(self, ratio: float) -> None:
        """Update corruption pressure (1.0 = safe, 0.0 = fully corrupted)."""
        self._corruption_ratio = max(0.0, min(1.0, ratio))

    def update(self, dt: float) -> None:
        self._elapsed += dt

        if self._transitioning:
            self._transition_timer -= dt
            if self._transition_timer <= 0:
                self._transitioning = False

        # Particle emission (style depends on derelict type)
        self._emit_timer += dt
        rate = 0.5 if self._corruption_ratio > 0.3 else 0.25  # Faster when corrupting
        if self._emit_timer >= rate:
            self._emit_timer -= rate
            gr = self._grid_rect
            style = self._profile["particle_style"]

            if style == "dust":
                self._particles.append({
                    "x": self._rng.uniform(gr.left, gr.right),
                    "y": float(gr.bottom),
                    "vx": self._rng.uniform(-5, 5),
                    "vy": self._rng.uniform(-12, -4),
                    "life": self._rng.uniform(2.0, 4.0), "max_life": 4.0,
                    "alpha": self._rng.randint(15, 35), "size": 1.5,
                })
            elif style == "vapor":
                self._particles.append({
                    "x": self._rng.uniform(gr.left, gr.right),
                    "y": self._rng.uniform(gr.top, gr.bottom),
                    "vx": self._rng.uniform(-10, 10),
                    "vy": self._rng.uniform(-8, 8),
                    "life": self._rng.uniform(1.5, 3.0), "max_life": 3.0,
                    "alpha": self._rng.randint(15, 30), "size": 2.0,
                })
            elif style == "sparks":
                self._particles.append({
                    "x": self._rng.uniform(gr.left, gr.right),
                    "y": self._rng.uniform(gr.top, gr.top + gr.height * 0.3),
                    "vx": self._rng.uniform(-15, 15),
                    "vy": self._rng.uniform(20, 50),
                    "life": self._rng.uniform(0.3, 0.8), "max_life": 0.8,
                    "alpha": self._rng.randint(80, 160), "size": 1.0,
                })

        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if self._profile["particle_style"] == "sparks":
                p["vy"] += 60 * dt  # Gravity for sparks
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def render(self, screen: pygame.Surface) -> None:
        gr = self._grid_rect
        margin = scale_x(12)
        area = pygame.Rect(
            gr.left - margin, gr.top - margin,
            gr.width + margin * 2, gr.height + margin * 2,
        )

        # Background tint (deck-specific)
        bg_colors = self._profile["bg_colors"]
        idx = min(self._deck - 1, len(bg_colors) - 1)
        bg = bg_colors[idx]

        if self._transitioning:
            prev_idx = max(0, idx - 1)
            t = 1.0 - self._transition_timer / self._transition_duration
            bg = _lerp_color(bg_colors[prev_idx], bg, t)

        bg_surf = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
        bg_surf.fill((*bg, 150))
        screen.blit(bg_surf, area.topleft)

        # Corruption pressure overlay — red tint that intensifies as time runs out
        if self._corruption_ratio < 0.5:
            corruption_intensity = (0.5 - self._corruption_ratio) / 0.5
            pulse = 0.5 + 0.5 * math.sin(self._elapsed * 4.0)
            red_alpha = int(30 * corruption_intensity * pulse)
            red_surf = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
            red_surf.fill((200, 30, 20, red_alpha))
            screen.blit(red_surf, area.topleft)

        # Border (accent colored, brightens under corruption pressure)
        accent = self._profile["accent"]
        if self._corruption_ratio < 0.3:
            # Warning: border pulses red
            pulse = 0.5 + 0.5 * math.sin(self._elapsed * 6.0)
            border_color = _lerp_color(accent, (220, 40, 30), pulse)
        else:
            border_color = accent
        pygame.draw.rect(screen, (*border_color, 50), area, 1)

        # Particles
        pc = self._profile["particle_color"]
        for p in self._particles:
            t = p["life"] / p["max_life"]
            alpha = int(p["alpha"] * t)
            if alpha <= 0:
                continue
            size = max(1, int(p["size"]))
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*pc, alpha), (size, size), size)
            screen.blit(ps, (int(p["x"]) - size, int(p["y"]) - size))


# ==========================================================================
# Deck Meter
# ==========================================================================


class SalvageDeckMeter:
    """Vertical deck meter showing current deck depth in the derelict."""

    def __init__(self, x: int, y: int, height: int, max_decks: int = 5) -> None:
        self.x = x
        self.y = y
        self.height = height
        self.width = scale_x(35)
        self.max_decks = max_decks
        self._deck: int = 1
        self._derelict_type: str = "cargo_bay"
        self._label_font = FontCache.get(FONT_XS)
        self._value_font = FontCache.get(FONT_MD)

    def set_state(self, deck: int, derelict_type: str = "cargo_bay") -> None:
        self._deck = deck
        self._derelict_type = derelict_type

    def render(self, screen: pygame.Surface) -> None:
        profile = _DERELICT_PROFILES.get(self._derelict_type, _DEFAULT_PROFILE)

        # Background track
        track = pygame.Rect(self.x, self.y, self.width, self.height)
        track_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        track_surf.fill((15, 12, 10, 180))
        screen.blit(track_surf, (self.x, self.y))
        pygame.draw.rect(screen, Colors.UI_BORDER, track, 1)

        # Deck segments
        segment_h = self.height // self.max_decks
        bg_colors = profile["bg_colors"]
        for i in range(self.max_decks):
            seg_y = self.y + i * segment_h
            color_idx = min(i, len(bg_colors) - 1)
            seg_surf = pygame.Surface((self.width - 2, segment_h - 1), pygame.SRCALPHA)
            seg_surf.fill((*bg_colors[color_idx], 80))
            screen.blit(seg_surf, (self.x + 1, seg_y))

            # Deck label
            label = self._label_font.render(f"D{i + 1}", True, Colors.TEXT_SECONDARY)
            screen.blit(label, (self.x + 3, seg_y + 2))

        # Current deck marker
        marker_y = self.y + (self._deck - 1) * segment_h
        pygame.draw.rect(
            screen, profile["accent"],
            (self.x + 1, marker_y, self.width - 2, segment_h - 1),
        )
        deck_text = f"D{self._deck}"
        deck_surf = self._value_font.render(deck_text, True, profile["accent"])
        screen.blit(deck_surf, (self.x + self.width + 4, marker_y + 2))

        # Title
        title = self._label_font.render("DECK", True, Colors.TEXT_SECONDARY)
        screen.blit(title, (self.x + (self.width - title.get_width()) // 2, self.y - title.get_height() - 2))


# ==========================================================================
# Corruption Timer Visual
# ==========================================================================


class CorruptionOverlay:
    """Visual corruption pressure indicator.

    Shows the corruption countdown as a creeping visual effect —
    screen edges darken, warning pulses intensify, and a timer bar
    shows remaining time.
    """

    def __init__(self, bar_x: int, bar_y: int, bar_w: int) -> None:
        self._bar_x = bar_x
        self._bar_y = bar_y
        self._bar_w = bar_w
        self._bar_h = scale_y(8)
        self._ratio: float = 1.0
        self._elapsed: float = 0.0
        self._label_font = FontCache.get(FONT_XS)

    def set_ratio(self, ratio: float) -> None:
        """Update corruption ratio (1.0 = safe, 0.0 = corrupted)."""
        self._ratio = max(0.0, min(1.0, ratio))

    def update(self, dt: float) -> None:
        self._elapsed += dt

    def render(self, screen: pygame.Surface) -> None:
        # Corruption timer bar
        bg_rect = pygame.Rect(self._bar_x, self._bar_y, self._bar_w, self._bar_h)
        pygame.draw.rect(screen, Colors.BAR_BG, bg_rect)

        fill_w = int(self._bar_w * self._ratio)
        if fill_w > 0:
            # Color transitions: green → yellow → red
            if self._ratio > 0.5:
                fill_color = Colors.GREEN
            elif self._ratio > 0.25:
                fill_color = Colors.YELLOW
            else:
                # Pulsing red
                pulse = 0.5 + 0.5 * math.sin(self._elapsed * 8.0)
                fill_color = (
                    int(220 + 35 * pulse),
                    int(40 * (1 - pulse)),
                    int(30 * (1 - pulse)),
                )
            pygame.draw.rect(screen, fill_color, (self._bar_x, self._bar_y, fill_w, self._bar_h))

        pygame.draw.rect(screen, Colors.UI_BORDER, bg_rect, 1)

        # Label
        label_text = "STRUCTURAL INTEGRITY"
        if self._ratio <= 0:
            label_text = "CORRUPTED"
        elif self._ratio < 0.25:
            label_text = "CRITICAL — EVACUATE"
        label = self._label_font.render(label_text, True, Colors.TEXT_SECONDARY)
        screen.blit(label, (self._bar_x, self._bar_y - label.get_height() - 2))


# ==========================================================================
# Deck Transition Effect
# ==========================================================================


# ==========================================================================
# Scan Pulse Effect
# ==========================================================================


class ScanPulse:
    """Sonar-like ripple that radiates from a scanned cell.

    Creates a ring that expands outward from the scan point,
    fading as it grows. Reinforces the "active scanning" feel.
    """

    def __init__(self) -> None:
        self._pulses: list[dict] = []

    def trigger(self, cx: int, cy: int) -> None:
        """Start a scan pulse from a grid position.

        Args:
            cx: Center X pixel coordinate.
            cy: Center Y pixel coordinate.
        """
        self._pulses.append({
            "x": cx, "y": cy,
            "radius": 0.0,
            "max_radius": float(scale_x(120)),
            "life": 0.4,
            "max_life": 0.4,
        })

    def update(self, dt: float) -> None:
        for p in self._pulses:
            p["life"] -= dt
            t = 1.0 - p["life"] / p["max_life"]
            p["radius"] = p["max_radius"] * t
        self._pulses = [p for p in self._pulses if p["life"] > 0]

    @property
    def has_active(self) -> bool:
        return len(self._pulses) > 0

    def render(self, screen: pygame.Surface) -> None:
        for p in self._pulses:
            t = p["life"] / p["max_life"]
            alpha = int(80 * t)
            radius = int(p["radius"])
            if radius <= 0:
                continue
            pulse_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                pulse_surf, (80, 180, 255, alpha), (radius, radius), radius, 2
            )
            # Inner ring (fainter, smaller)
            inner_r = max(1, radius - scale_x(15))
            pygame.draw.circle(
                pulse_surf, (60, 140, 220, alpha // 2), (radius, radius), inner_r, 1
            )
            screen.blit(pulse_surf, (p["x"] - radius, p["y"] - radius))


# ==========================================================================
# Quality Discovery Burst
# ==========================================================================


class QualityBurst:
    """Particle burst effect when scanning reveals a valuable item.

    Good items get a moderate glow. Excellent items get a dramatic
    golden sparkle burst.
    """

    def __init__(self) -> None:
        self._bursts: list[dict] = []
        self._rng = _random.Random()

    def trigger(self, cx: int, cy: int, quality: str) -> None:
        """Trigger a quality discovery burst.

        Args:
            cx: Cell center X.
            cy: Cell center Y.
            quality: Quality tier string ("poor", "normal", "good", "excellent").
        """
        if quality == "good":
            color = (80, 160, 255)
            count = 8
            speed = 60
        elif quality == "excellent":
            color = (255, 215, 60)
            count = 15
            speed = 100
        else:
            return  # No burst for poor/normal

        particles = []
        for i in range(count):
            angle = (2 * math.pi * i / count) + self._rng.uniform(-0.3, 0.3)
            spd = self._rng.uniform(speed * 0.5, speed)
            particles.append({
                "x": 0.0, "y": 0.0,
                "vx": math.cos(angle) * spd,
                "vy": math.sin(angle) * spd,
                "life": self._rng.uniform(0.3, 0.6),
                "max_life": 0.6,
                "size": self._rng.uniform(1.5, 3.0),
            })

        self._bursts.append({
            "cx": cx, "cy": cy, "color": color,
            "particles": particles,
            "glow_timer": 0.3,
        })

    def update(self, dt: float) -> None:
        for burst in self._bursts:
            burst["glow_timer"] -= dt
            for p in burst["particles"]:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt
            burst["particles"] = [p for p in burst["particles"] if p["life"] > 0]
        self._bursts = [b for b in self._bursts if b["particles"] or b["glow_timer"] > 0]

    @property
    def has_active(self) -> bool:
        return len(self._bursts) > 0

    def render(self, screen: pygame.Surface) -> None:
        for burst in self._bursts:
            cx, cy = burst["cx"], burst["cy"]
            color = burst["color"]

            # Glow flash at center
            if burst["glow_timer"] > 0:
                gt = burst["glow_timer"] / 0.3
                glow_r = int(scale_x(25) * gt)
                glow_alpha = int(100 * gt)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color, glow_alpha), (glow_r, glow_r), glow_r)
                screen.blit(glow_surf, (cx - glow_r, cy - glow_r))

            # Particles
            for p in burst["particles"]:
                t = p["life"] / p["max_life"]
                alpha = int(200 * t)
                size = max(1, int(p["size"] * t))
                ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*color, alpha), (size, size), size)
                screen.blit(ps, (cx + int(p["x"]) - size, cy + int(p["y"]) - size))


# ==========================================================================
# Mode Overlay
# ==========================================================================


class ModeOverlay:
    """Subtle tint overlay indicating the current salvage mode.

    Scan mode: blue sonar tint. Extract mode: warm amber work-light tint.
    """

    def __init__(self, grid_rect: pygame.Rect) -> None:
        self._grid_rect = grid_rect
        self._mode: str = "scan"
        self._transition: float = 0.0  # 0=scan, 1=extract

    def set_mode(self, mode: str) -> None:
        self._mode = mode

    def update(self, dt: float) -> None:
        target = 1.0 if self._mode == "extract" else 0.0
        diff = target - self._transition
        self._transition += diff * dt * 5.0  # Smooth lerp

    def render(self, screen: pygame.Surface) -> None:
        gr = self._grid_rect
        t = self._transition

        # Blend between scan (blue) and extract (amber)
        r = int(10 * (1 - t) + 20 * t)
        g = int(15 * (1 - t) + 15 * t)
        b = int(25 * (1 - t) + 8 * t)
        alpha = 20

        overlay = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
        overlay.fill((r, g, b, alpha))
        screen.blit(overlay, gr.topleft)

        # Mode label in corner
        label_color = (80, 160, 255) if self._mode == "scan" else (220, 170, 60)
        label_text = "SCAN MODE" if self._mode == "scan" else "EXTRACT MODE"
        font = FontCache.get(FONT_XS)
        label = font.render(label_text, True, label_color)
        screen.blit(label, (gr.right - label.get_width() - 4, gr.top + 3))


# ==========================================================================
# Deck Transition Effect
# ==========================================================================


class DeckTransition:
    """Visual effect when descending to the next deck."""

    def __init__(self) -> None:
        self.active: bool = False
        self._timer: float = 0.0
        self._duration: float = 0.5
        self._new_deck: int = 1
        self._derelict_type: str = "cargo_bay"

    def trigger(self, new_deck: int, derelict_type: str = "cargo_bay") -> None:
        self.active = True
        self._timer = self._duration
        self._new_deck = new_deck
        self._derelict_type = derelict_type

    def update(self, dt: float) -> None:
        if self.active:
            self._timer -= dt
            if self._timer <= 0:
                self.active = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.active:
            return

        t = self._timer / self._duration
        profile = _DERELICT_PROFILES.get(self._derelict_type, _DEFAULT_PROFILE)

        # Scan-line wipe effect
        if t > 0.5:
            line_y = int(WINDOW_HEIGHT * (1.0 - (t - 0.5) / 0.5))
            pygame.draw.line(screen, profile["accent"], (0, line_y), (WINDOW_WIDTH, line_y), 2)

        # "DECK X" banner
        if t < 0.6:
            alpha = int(220 * min(1.0, (0.6 - t) / 0.4))
            font = FontCache.get(FONT_MD)
            text = f"DESCENDING TO DECK {self._new_deck}"
            surf = font.render(text, True, profile["accent"])
            surf.set_alpha(alpha)
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
            screen.blit(surf, rect)
