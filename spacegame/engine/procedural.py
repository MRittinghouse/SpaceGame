"""
Procedural art generation for backgrounds, planets, and nebulae.

All methods return cached pygame.Surface objects, seeded for determinism.
"""

import random
from typing import Optional

import pygame

_cache: dict = {}
_CACHE_MAX_ENTRIES = 50


def _cache_key(func_name: str, *args) -> tuple:
    return (func_name, *args)


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


def _render_gas_blob(
    surface: pygame.Surface,
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
    peak_alpha: int,
) -> None:
    """Render a single gas blob with Gaussian-style radial falloff.

    The blob fades smoothly from peak_alpha at center to 0 at the edge,
    producing soft, cloud-like shapes instead of flat discs.
    """
    # Only render the region that overlaps the surface
    sw, sh = surface.get_size()
    x0 = max(0, cx - radius)
    y0 = max(0, cy - radius)
    x1 = min(sw, cx + radius + 1)
    y1 = min(sh, cy + radius + 1)
    if x0 >= x1 or y0 >= y1:
        return

    # Pre-render blob into a small SRCALPHA surface, then blit additively
    blob_w = x1 - x0
    blob_h = y1 - y0
    blob = pygame.Surface((blob_w, blob_h), pygame.SRCALPHA)

    r, g, b = color
    # Draw concentric rings instead of per-pixel for performance
    # Rings from outside in so inner (brighter) overwrites outer
    ring_count = min(radius, 40)
    for ring_i in range(ring_count, -1, -1):
        ring_r = int(radius * ring_i / ring_count)
        if ring_r < 1:
            continue
        # Gaussian-ish falloff: alpha = peak * (1 - (d/R)^2)^2
        t = ring_i / ring_count  # 0 at center, 1 at edge
        falloff = (1.0 - t * t) ** 2
        a = int(peak_alpha * falloff)
        if a < 1:
            continue
        # Draw filled circle on blob surface, offset by blob origin
        local_cx = cx - x0
        local_cy = cy - y0
        pygame.draw.circle(blob, (r, g, b, a), (local_cx, local_cy), ring_r)

    surface.blit(blob, (x0, y0), special_flags=pygame.BLEND_ALPHA_SDL2)


def generate_nebula(
    w: int, h: int, color_base: tuple = (60, 20, 80), seed: int = 0
) -> pygame.Surface:
    """Generate a nebula overlay with soft Gaussian gas blobs.

    Uses radial falloff blobs instead of flat circles for a natural,
    cloud-like appearance. Multiple overlapping blobs at low alpha
    create wispy, volumetric-looking gas structures.
    """
    key = _cache_key("nebula", w, h, color_base, seed)
    cached = _get_cached(key)
    if cached:
        return cached

    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    rng = random.Random(seed)

    # Large diffuse blobs form the base structure
    for _ in range(rng.randint(8, 14)):
        cx = rng.randint(-w // 6, w + w // 6)
        cy = rng.randint(-h // 6, h + h // 6)
        radius = rng.randint(120, 280)
        peak_alpha = rng.randint(8, 18)
        r = min(255, max(0, color_base[0] + rng.randint(-15, 15)))
        g = min(255, max(0, color_base[1] + rng.randint(-15, 15)))
        b = min(255, max(0, color_base[2] + rng.randint(-15, 15)))
        _render_gas_blob(surface, cx, cy, radius, (r, g, b), peak_alpha)

    # Medium detail blobs add texture and color variation
    for _ in range(rng.randint(15, 25)):
        cx = rng.randint(-w // 8, w + w // 8)
        cy = rng.randint(-h // 8, h + h // 8)
        radius = rng.randint(50, 140)
        peak_alpha = rng.randint(6, 14)
        r = min(255, max(0, color_base[0] + rng.randint(-25, 25)))
        g = min(255, max(0, color_base[1] + rng.randint(-25, 25)))
        b = min(255, max(0, color_base[2] + rng.randint(-25, 25)))
        _render_gas_blob(surface, cx, cy, radius, (r, g, b), peak_alpha)

    # Small bright cores where gas is densest
    for _ in range(rng.randint(5, 10)):
        cx = rng.randint(w // 6, w * 5 // 6)
        cy = rng.randint(h // 6, h * 5 // 6)
        radius = rng.randint(20, 60)
        peak_alpha = rng.randint(10, 22)
        # Brighter, slightly shifted color for the cores
        r = min(255, max(0, color_base[0] + rng.randint(10, 40)))
        g = min(255, max(0, color_base[1] + rng.randint(10, 40)))
        b = min(255, max(0, color_base[2] + rng.randint(10, 40)))
        _render_gas_blob(surface, cx, cy, radius, (r, g, b), peak_alpha)

    _set_cached(key, surface)
    return surface


def generate_planet(radius: int, planet_type: str = "terran", seed: int = 0) -> pygame.Surface:
    """Generate a procedural planet surface.

    Uses clipped horizontal bands with varied widths and colors for a
    natural look. Bands are drawn as filled rectangles clipped to a
    circular mask for performance (no per-pixel iteration).

    Types: terran, trade_hub, gas, ice, volcanic, desert, industrial,
           agricultural, mining, research, frontier
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

    # Base colors per type (primary, secondary, accent)
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

    # Build on a work surface, then mask to a circle at the end
    work = pygame.Surface((diameter, diameter), pygame.SRCALPHA)

    # Fill base color
    work.fill((*colors[0], 255))

    # Draw varied horizontal bands using rectangles (fast, no per-pixel)
    band_y = 0
    while band_y < diameter:
        band_h = rng.randint(1, max(1, radius // 3))
        if rng.random() > 0.45:  # 55% chance of a band
            color_idx = rng.randint(0, len(colors) - 1)
            bc = colors[color_idx]
            # Vary color slightly for natural feel
            r = min(255, max(0, bc[0] + rng.randint(-12, 12)))
            g = min(255, max(0, bc[1] + rng.randint(-12, 12)))
            b = min(255, max(0, bc[2] + rng.randint(-12, 12)))
            band_alpha = rng.randint(60, 160)
            band_surf = pygame.Surface((diameter, band_h), pygame.SRCALPHA)
            band_surf.fill((r, g, b, band_alpha))
            work.blit(band_surf, (0, band_y))
        band_y += band_h

    # Circular mask: copy only the planet circle to the output
    mask = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (center, center), radius)
    # Apply mask by blitting work through it
    work.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(work, (0, 0))

    # Light crescent (sunlight from upper-left) for depth
    crescent = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    highlight_offset = max(1, radius // 4)
    pygame.draw.circle(
        crescent,
        (255, 255, 255, 30),
        (center - highlight_offset, center - highlight_offset),
        radius,
    )
    # Cut away the shadow side
    pygame.draw.circle(
        crescent,
        (0, 0, 0, 0),
        (center + highlight_offset // 2, center + highlight_offset // 2),
        radius,
        0,
    )
    # Clip to planet circle
    crescent.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(crescent, (0, 0))

    # Atmosphere glow rings
    for ring in range(3):
        glow_radius = radius + ring + 1
        glow_alpha = max(10, 60 - ring * 20)
        pygame.draw.circle(
            surface,
            (*colors[1][:3], glow_alpha),
            (center, center),
            glow_radius,
            1,
        )

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
