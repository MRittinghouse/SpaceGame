"""
Procedural art generation for backgrounds, planets, and nebulae.

All methods return cached pygame.Surface objects, seeded for determinism.
"""

import pygame
import math
import random
from typing import Optional

_cache: dict = {}
_CACHE_MAX_ENTRIES = 50


def _cache_key(func_name: str, *args) -> tuple:
    return (func_name,) + args


def _get_cached(key: tuple) -> Optional[pygame.Surface]:
    return _cache.get(key)


def _set_cached(key: tuple, surface: pygame.Surface) -> None:
    if len(_cache) >= _CACHE_MAX_ENTRIES:
        # Evict oldest entry
        oldest = next(iter(_cache))
        del _cache[oldest]
    _cache[key] = surface


def generate_starfield(w: int, h: int, star_count: int = 300, seed: int = 42) -> pygame.Surface:
    """Generate a starfield with 3 depth layers."""
    key = _cache_key("starfield", w, h, star_count, seed)
    cached = _get_cached(key)
    if cached:
        return cached

    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    rng = random.Random(seed)

    # Layer 1: dim distant stars (1px)
    for _ in range(star_count // 2):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        brightness = rng.randint(40, 80)
        surface.set_at((x, y), (brightness, brightness, brightness + 10, brightness))

    # Layer 2: medium stars (1-2px)
    for _ in range(star_count // 3):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        brightness = rng.randint(100, 170)
        sz = rng.choice([1, 1, 2])
        color = (brightness, brightness, brightness + rng.randint(0, 20), brightness)
        if sz == 1:
            surface.set_at((x, y), color)
        else:
            pygame.draw.circle(surface, color, (x, y), 1)

    # Layer 3: bright close stars (2-3px)
    for _ in range(star_count // 6):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        brightness = rng.randint(180, 255)
        sz = rng.choice([1, 2, 2])
        # Slight color tint
        tint = rng.choice([(0, 0, 20), (20, 10, 0), (0, 15, 15)])
        r = min(255, brightness + tint[0])
        g = min(255, brightness + tint[1])
        b = min(255, brightness + tint[2])
        pygame.draw.circle(surface, (r, g, b, brightness), (x, y), sz)

    _set_cached(key, surface)
    return surface


def generate_nebula(
    w: int, h: int, color_base: tuple = (60, 20, 80), seed: int = 0
) -> pygame.Surface:
    """Generate a nebula overlay with transparent overlapping circles."""
    key = _cache_key("nebula", w, h, color_base, seed)
    cached = _get_cached(key)
    if cached:
        return cached

    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    rng = random.Random(seed)

    count = rng.randint(40, 80)
    for _ in range(count):
        cx = rng.randint(-w // 4, w + w // 4)
        cy = rng.randint(-h // 4, h + h // 4)
        radius = rng.randint(60, 200)
        alpha = rng.randint(3, 12)

        r = min(255, max(0, color_base[0] + rng.randint(-20, 20)))
        g = min(255, max(0, color_base[1] + rng.randint(-20, 20)))
        b = min(255, max(0, color_base[2] + rng.randint(-20, 20)))

        pygame.draw.circle(surface, (r, g, b, alpha), (cx, cy), radius)

    _set_cached(key, surface)
    return surface


def generate_planet(radius: int, planet_type: str = "terran", seed: int = 0) -> pygame.Surface:
    """Generate a procedural planet surface.

    Types: terran, gas, ice, volcanic, desert, industrial
    """
    key = _cache_key("planet", radius, planet_type, seed)
    cached = _get_cached(key)
    if cached:
        return cached

    diameter = radius * 2 + 4
    surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    center = diameter // 2
    rng = random.Random(seed)

    # Base colors per type
    type_colors = {
        "terran": ((40, 120, 60), (30, 80, 140), (60, 140, 70)),
        "trade_hub": ((40, 100, 180), (60, 140, 200), (30, 80, 160)),
        "gas": ((180, 140, 80), (200, 160, 100), (160, 120, 60)),
        "ice": ((160, 200, 220), (180, 220, 240), (140, 180, 200)),
        "volcanic": ((180, 60, 30), (200, 80, 20), (160, 40, 40)),
        "desert": ((180, 150, 80), (200, 170, 100), (160, 130, 60)),
        "industrial": ((100, 100, 120), (120, 120, 140), (80, 80, 100)),
        "agricultural": ((50, 140, 50), (40, 120, 70), (60, 160, 40)),
        "mining": ((160, 140, 100), (140, 120, 80), (180, 160, 120)),
        "research": ((80, 60, 160), (100, 80, 180), (60, 40, 140)),
        "frontier": ((140, 80, 60), (160, 100, 80), (120, 60, 40)),
    }
    colors = type_colors.get(planet_type, type_colors["terran"])

    # Fill circle with base color
    pygame.draw.circle(surface, colors[0], (center, center), radius)

    # Horizontal band noise
    for band_y in range(-radius, radius + 1):
        band_width = int(math.sqrt(max(0, radius * radius - band_y * band_y)))
        if band_width <= 0:
            continue
        noise_val = rng.random()
        if noise_val > 0.6:
            color_idx = rng.randint(0, len(colors) - 1)
            band_color = colors[color_idx]
            band_alpha = rng.randint(40, 120)
            for bx in range(-band_width, band_width + 1):
                px = center + bx
                py = center + band_y
                if 0 <= px < diameter and 0 <= py < diameter:
                    # Check if inside circle
                    dist = math.sqrt(bx * bx + band_y * band_y)
                    if dist <= radius:
                        existing = surface.get_at((px, py))
                        # Simple alpha blend
                        t = band_alpha / 255.0
                        nr = int(existing[0] * (1 - t) + band_color[0] * t)
                        ng = int(existing[1] * (1 - t) + band_color[1] * t)
                        nb = int(existing[2] * (1 - t) + band_color[2] * t)
                        surface.set_at((px, py), (nr, ng, nb, 255))

    # Atmosphere glow rings
    for ring in range(3):
        glow_radius = radius + ring + 1
        glow_alpha = max(10, 60 - ring * 20)
        glow_color = (*colors[1][:3], glow_alpha) if len(colors[1]) == 3 else colors[1]
        pygame.draw.circle(surface, (*glow_color[:3], glow_alpha), (center, center), glow_radius, 1)

    _set_cached(key, surface)
    return surface


# Theme -> nebula color mapping
THEME_NEBULA_COLORS = {
    "deep_space": None,
    "nebula": (60, 20, 80),
    "frontier": (80, 30, 20),
    "trade_routes": (20, 40, 80),
    "industrial": (80, 60, 20),
    "asteroid_field": (40, 30, 20),
    "debris": (30, 30, 50),
}


def generate_background(
    w: int, h: int, theme: str = "deep_space", seed: int = 42
) -> pygame.Surface:
    """Generate a composite background: starfield + optional nebula overlays.

    Themes: deep_space, nebula, frontier, trade_routes, industrial, asteroid_field, debris
    """
    key = _cache_key("background", w, h, theme, seed)
    cached = _get_cached(key)
    if cached:
        return cached

    surface = pygame.Surface((w, h))
    surface.fill((8, 10, 18))

    # Starfield layer
    star_count = 300 if theme != "industrial" else 150
    starfield = generate_starfield(w, h, star_count, seed)
    surface.blit(starfield, (0, 0))

    # Nebula overlays based on theme
    nebula_color = THEME_NEBULA_COLORS.get(theme)
    if nebula_color:
        rng = random.Random(seed + 1000)
        nebula_count = rng.randint(1, 2)
        for i in range(nebula_count):
            nebula = generate_nebula(w, h, nebula_color, seed + i + 100)
            surface.blit(nebula, (0, 0))

    _set_cached(key, surface)
    return surface


def clear_cache() -> None:
    """Clear the procedural art cache."""
    _cache.clear()
