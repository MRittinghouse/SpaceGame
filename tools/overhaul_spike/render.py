"""
Procedural module renderer — the heart of the spike.

Renders a "weapon mount" module from a manufacturer profile + seed into
a pygame Surface. Exercises the full pipeline described in
``10_programmatic_generation_framework.md``:

    1. Shape raster (polygon + ellipse)
    2. Material base fill
    3. Global directional lighting (top-right, 45 deg)
    4. Procedural surface grain (noise)
    5. Procedural wear (lower-frequency noise)
    6. Rivet placement (Poisson-disc approximation)
    7. Gloss rim highlight
    8. Signature stripe accent

All rendering is numpy-accelerated via pygame.surfarray. Output is a
SRCALPHA pygame.Surface ready for blit.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
import pygame
from pygame import gfxdraw

from .manufacturer import ManufacturerProfile
from .material import Material
from .palette import rgb


# Global light direction (top-right, normalized). Matches the framework
# doc's "sacrosanct, globally" decision.
LIGHT_DIR = np.array([0.707, -0.707], dtype=np.float32)  # (x_right, y_up-ish)


@dataclass(frozen=True)
class ModuleShape:
    """Declarative shape of a weapon mount.

    Bounding box is (width, height) in pixels. Base is the rectangular
    housing; barrel is an ellipse extending to the right.
    """
    width: int = 96
    height: int = 48
    base_rect: tuple[int, int, int, int] = (4, 10, 64, 28)   # x, y, w, h
    barrel_rect: tuple[int, int, int, int] = (60, 18, 32, 12)
    mount_pad_rect: tuple[int, int, int, int] = (8, 38, 40, 6)  # under-mount pad


def make_shape(profile: ManufacturerProfile) -> ModuleShape:
    """Slightly vary shape by manufacturer proportion bias."""
    w, h = 96, 48
    bias = profile.proportion_bias
    # Chunkier manufacturers get a taller base.
    base_h = int(28 + bias * 6)
    base_w = int(64 - bias * 4)  # counter-bias width slightly
    base_y = (h - base_h - 4) // 2
    return ModuleShape(
        width=w,
        height=h,
        base_rect=(4, base_y, base_w, base_h),
        barrel_rect=(base_w + 4, base_y + base_h // 2 - 6, 32, 12),
        mount_pad_rect=(8, base_y + base_h, 40, 6),
    )


# ---------------------------------------------------------------------------
# Shape raster — produces a coverage mask + lighting gradient
# ---------------------------------------------------------------------------

def rasterize_shape(shape: ModuleShape) -> tuple[np.ndarray, np.ndarray]:
    """Return (coverage_mask, lighting_field) as numpy arrays of shape (H, W).

    - coverage_mask: 1.0 inside the shape, 0.0 outside
    - lighting_field: per-pixel diffuse contribution in [0, 1]
    """
    w, h = shape.width, shape.height

    coverage = np.zeros((h, w), dtype=np.float32)
    # Rectangular base
    bx, by, bw, bh = shape.base_rect
    coverage[by:by + bh, bx:bx + bw] = 1.0
    # Mount pad (underneath)
    mx, my, mw, mh = shape.mount_pad_rect
    coverage[my:my + mh, mx:mx + mw] = 1.0

    # Elliptical barrel (filled via analytic test for smooth edge)
    cx, cy, bw_, bh_ = shape.barrel_rect
    ex = cx + bw_ / 2.0
    ey = cy + bh_ / 2.0
    rx = bw_ / 2.0
    ry = bh_ / 2.0
    ys, xs = np.mgrid[0:h, 0:w]
    ellipse_mask = ((xs - ex) ** 2) / (rx ** 2) + ((ys - ey) ** 2) / (ry ** 2) <= 1.0
    coverage[ellipse_mask] = 1.0

    # Lighting: dot product of (approximate surface normal) with LIGHT_DIR.
    # For a 2D flat-shaded panel we use a cheap trick: the gradient of the
    # coverage mask gives us "how flat" versus "edge", but that's not quite
    # right. A better approximation for a 2D card: treat the module as a
    # slightly convex surface and bake a linear gradient along LIGHT_DIR.
    # That's what produces the "upper-right bright, lower-left dim" feel.
    light_x, light_y_raw = LIGHT_DIR
    # light_y_raw is negative (toward top); flip sign because screen-y is down.
    light_y = -light_y_raw
    # Diffuse gradient: center at 0.5, ramping toward 1.0 in light direction.
    # Normalize coords to [-1, 1] across the bounding box.
    nx = (xs / max(w - 1, 1)) * 2.0 - 1.0
    ny = (ys / max(h - 1, 1)) * 2.0 - 1.0
    diffuse = 0.5 + 0.5 * (nx * light_x + ny * light_y)
    diffuse = np.clip(diffuse, 0.0, 1.0) * coverage
    return coverage, diffuse.astype(np.float32)


# ---------------------------------------------------------------------------
# Noise — simple value-noise with smoothing. Not true Perlin, but deterministic
# and fast enough for a 96x48 spike.
# ---------------------------------------------------------------------------

def value_noise(width: int, height: int, scale: float, seed: int) -> np.ndarray:
    """Return a noise field of shape (H, W) in [0, 1]."""
    # Low-res random grid, then upsample with bilinear-like smoothing.
    grid_w = max(2, int(width * scale))
    grid_h = max(2, int(height * scale))
    rng = np.random.default_rng(seed)
    low = rng.random((grid_h, grid_w), dtype=np.float32)

    # Simple bilinear upsample.
    ys = np.linspace(0, grid_h - 1, height)
    xs = np.linspace(0, grid_w - 1, width)
    y0 = np.floor(ys).astype(int); y1 = np.clip(y0 + 1, 0, grid_h - 1)
    x0 = np.floor(xs).astype(int); x1 = np.clip(x0 + 1, 0, grid_w - 1)
    dy = (ys - y0).reshape(-1, 1); dx = (xs - x0).reshape(1, -1)

    top = low[y0][:, x0] * (1 - dx) + low[y0][:, x1] * dx
    bot = low[y1][:, x0] * (1 - dx) + low[y1][:, x1] * dx
    return (top * (1 - dy) + bot * dy).astype(np.float32)


# ---------------------------------------------------------------------------
# Rivet placement — Poisson-disc-lite via rejection sampling
# ---------------------------------------------------------------------------

def place_rivets(
    coverage: np.ndarray,
    density_per_kpx2: float,
    seed: int,
    min_spacing_px: int = 6,
) -> list[tuple[int, int]]:
    """Return a list of rivet center (x, y) positions inside the shape.

    density_per_kpx2: target rivets per 1000 px² of covered area.
    min_spacing_px: enforce approximate spacing so rivets don't clump.
    """
    h, w = coverage.shape
    covered_px = int(coverage.sum())
    if covered_px == 0 or density_per_kpx2 <= 0:
        return []
    target_count = int(covered_px * density_per_kpx2 / 1000.0)
    if target_count == 0:
        return []

    rng = np.random.default_rng(seed + 9001)
    placed: list[tuple[int, int]] = []
    attempts = 0
    max_attempts = target_count * 40
    while len(placed) < target_count and attempts < max_attempts:
        attempts += 1
        x = int(rng.integers(2, w - 2))
        y = int(rng.integers(2, h - 2))
        if coverage[y, x] < 0.5:
            continue
        too_close = False
        for px, py in placed:
            if (px - x) ** 2 + (py - y) ** 2 < min_spacing_px ** 2:
                too_close = True
                break
        if not too_close:
            placed.append((x, y))
    return placed


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def snap_to_palette(surface: pygame.Surface) -> pygame.Surface:
    """Snap every opaque pixel to its nearest palette color.

    Produces a flat, pixel-art aesthetic (strict palette compliance)
    at the cost of gradient smoothness. An alternative to the
    gradient-line compliance model. Operates in place and returns
    the input surface for chaining.
    """
    from .palette import palette_array
    palette = palette_array()  # (N, 3)
    rgb = pygame.surfarray.pixels3d(surface)  # (W, H, 3) uint8
    orig_shape = rgb.shape
    flat = rgb.reshape(-1, 3).astype(np.int32)  # (P, 3)
    # Nearest neighbor
    diff = flat[:, None, :] - palette[None, :, :]
    d2 = np.sum(diff * diff, axis=-1)
    idx = np.argmin(d2, axis=-1)
    flat[:] = palette[idx]
    rgb[:] = flat.reshape(orig_shape).astype(np.uint8)
    del rgb
    return surface


def render_module(
    profile: ManufacturerProfile,
    seed: int,
    debug: bool = False,
    palette_snap: bool = False,
) -> pygame.Surface:
    """Render a weapon-mount module for the given manufacturer.

    Returns a SRCALPHA pygame.Surface sized to the module's bounding box.
    If ``palette_snap`` is True, final output is snapped to the nearest
    palette colors (flat pixel-art look); otherwise smooth gradient.
    """
    shape = make_shape(profile)
    mat = profile.primary_material
    w, h = shape.width, shape.height

    coverage, diffuse = rasterize_shape(shape)

    # --- Build the color array -----------------------------------------------
    base = np.array(rgb(mat.base_color), dtype=np.float32)
    hi = np.array(rgb(mat.highlight_color), dtype=np.float32)
    lo = np.array(rgb(mat.shadow_color), dtype=np.float32)

    # Lerp per-pixel by diffuse: 0 -> shadow, 0.5 -> base, 1 -> highlight.
    # We use a piecewise blend to keep base color the anchor mid-tone.
    t = diffuse[..., None]  # (H, W, 1)
    # Low half: blend shadow -> base. High half: blend base -> highlight.
    low_mix = lo + (base - lo) * (t * 2.0)          # for t in [0, 0.5]
    high_mix = base + (hi - base) * ((t - 0.5) * 2.0)  # for t in [0.5, 1]
    lit = np.where(t < 0.5, low_mix, high_mix)
    # lit shape: (H, W, 3). Mask to coverage.
    cov = coverage[..., None]
    pixels = lit * cov  # transparent outside

    # --- Procedural surface grain --------------------------------------------
    if mat.noise_intensity > 0:
        grain = value_noise(w, h, mat.noise_scale, seed)
        # Bipolar: [-1, 1], scaled by intensity, modulates brightness.
        grain_signed = (grain - 0.5) * 2.0
        grain_mod = 1.0 + grain_signed * mat.noise_intensity * 0.25
        pixels = pixels * grain_mod[..., None]

    # --- Wear (lower-frequency noise, darkens) -------------------------------
    if mat.wear_intensity > 0:
        wear = value_noise(w, h, mat.noise_scale * 0.4, seed + 1337)
        # Only the darker 40% of the wear field actually wears — simulates patches.
        wear_mask = np.clip((0.4 - wear) / 0.4, 0, 1) * mat.wear_intensity
        darken = 1.0 - wear_mask * 0.35
        pixels = pixels * darken[..., None]

    # --- Gloss edge highlight ------------------------------------------------
    if mat.gloss > 0:
        # Highlight a thin band on the lit side: where diffuse is near 1.
        gloss_mask = np.clip((diffuse - 0.82) / 0.18, 0, 1) * mat.gloss
        # Blend toward highlight color.
        pixels = pixels + (hi - pixels) * gloss_mask[..., None] * 0.5

    # --- Clamp + snap back to uint8 ------------------------------------------
    pixels = np.clip(pixels, 0, 255).astype(np.uint8)

    # --- Build surface with alpha --------------------------------------------
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    alpha = (coverage * 255).astype(np.uint8)
    # surfarray.pixels3d expects (W, H, 3); we have (H, W, 3) - transpose.
    rgb_arr = pygame.surfarray.pixels3d(surface)
    rgb_arr[:, :, :] = pixels.transpose(1, 0, 2)
    del rgb_arr
    alpha_arr = pygame.surfarray.pixels_alpha(surface)
    alpha_arr[:, :] = alpha.T
    del alpha_arr

    # --- Rivets (drawn on top of the pixel pass) -----------------------------
    rivets = place_rivets(coverage, mat.rivet_density, seed)
    rivet_color = rgb("rivet")
    for rx, ry in rivets:
        gfxdraw.filled_circle(surface, rx, ry, 1, rivet_color)

    # --- Signature stripe (manufacturer accent) ------------------------------
    if mat.signature_stripe is not None:
        stripe_color = rgb(mat.signature_stripe)
        # A thin horizontal accent band across the base rect, middle.
        bx, by, bw, bh = shape.base_rect
        stripe_y = by + bh // 2
        stripe_rect = pygame.Rect(bx + 4, stripe_y - 1, bw - 8, 2)
        pygame.draw.rect(surface, (*stripe_color, 200), stripe_rect)

    if palette_snap:
        surface = snap_to_palette(surface)

    if debug:
        _draw_debug_overlay(surface, shape, len(rivets))

    return surface


def _draw_debug_overlay(
    surface: pygame.Surface, shape: ModuleShape, rivet_count: int
) -> None:
    """Small debug text showing rivet count — useful during spike iteration."""
    font = pygame.font.Font(None, 10)
    txt = font.render(f"r={rivet_count}", True, (255, 255, 255))
    surface.blit(txt, (1, 1))
