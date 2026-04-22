"""
Unified-object ship renderer — Spike B.

Implements the algorithm from 10_programmatic_generation_framework.md §6:

    1. Silhouette pass — union of all module coverage
    2. Per-module base pass — material fill for each module region
    3. Global lighting pass — ONE light direction across whole silhouette
    4. Connection detail pass — seams where modules abut
    5. Decoration pass — rivets, wear via noise on silhouette
    6. Emissive pass — windows, thrusters
    7. Palette snap — final output in palette

Key design: the ship is lit AS ONE OBJECT, not as a collage of independently-lit
modules. That's the architectural move that makes a ship "read as one vehicle."
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pygame
from pygame import gfxdraw

from .manufacturer import ManufacturerProfile
from .module_types import MODULE_TYPES, ModuleType, rasterize
from .palette import palette_array, rgb


# Same LIGHT_DIR as render.py — consistency is sacrosanct.
LIGHT_DIR = np.array([0.707, -0.707], dtype=np.float32)


@dataclass(frozen=True)
class PlacedModule:
    """A module placed at (x, y) in ship canvas coordinates."""
    module_type_id: str
    x: int
    y: int


def compose_ship(
    placed_modules: list[PlacedModule],
    profile: ManufacturerProfile,
    seed: int,
    canvas_size: tuple[int, int] = (240, 160),
    palette_snap: bool = True,  # default per Spike 01 decision
    debug: bool = False,
) -> pygame.Surface:
    """Render a ship from a list of placed modules + manufacturer profile.

    Returns a SRCALPHA pygame.Surface of canvas_size with the composed ship
    centered within it (or anchored per placed module positions).
    """
    cw, ch = canvas_size
    rng = np.random.default_rng(seed)

    # --- Phase 1: Silhouette pass ---------------------------------------------
    # Build the full-ship coverage mask by OR-ing each module's coverage into
    # a canvas-sized target. Also collect emissive mask the same way.
    silhouette = np.zeros((ch, cw), dtype=np.float32)
    emissive_mask = np.zeros((ch, cw), dtype=np.float32)
    emissive_color_roles: dict[tuple[int, int], str] = {}
    module_regions: list[dict] = []  # {slice_y, slice_x, coverage_local, meta, placed}

    for placed in placed_modules:
        mt = MODULE_TYPES[placed.module_type_id]
        coverage_local, emissive_local, meta = rasterize(
            mt, proportion_bias=profile.proportion_bias
        )
        h, w = coverage_local.shape
        # Clip the module into the canvas bounds.
        y0 = max(0, placed.y); y1 = min(ch, placed.y + h)
        x0 = max(0, placed.x); x1 = min(cw, placed.x + w)
        if y1 <= y0 or x1 <= x0:
            continue
        # Corresponding slice into the local arrays
        ly0 = y0 - placed.y; ly1 = ly0 + (y1 - y0)
        lx0 = x0 - placed.x; lx1 = lx0 + (x1 - x0)

        silhouette[y0:y1, x0:x1] = np.maximum(
            silhouette[y0:y1, x0:x1], coverage_local[ly0:ly1, lx0:lx1]
        )
        emissive_mask[y0:y1, x0:x1] = np.maximum(
            emissive_mask[y0:y1, x0:x1], emissive_local[ly0:ly1, lx0:lx1]
        )
        emissive_color_roles[(y0, x0)] = meta.get("emissive_color", "plasma_core")

        module_regions.append({
            "placed": placed,
            "meta": meta,
            "coverage_slice": (slice(y0, y1), slice(x0, x1)),
            "coverage_local": coverage_local[ly0:ly1, lx0:lx1],
        })

    # --- Phase 2: Per-module base pass ----------------------------------------
    # Fill each module region with the material's base color. Differentiate
    # subtly by module category: weapons slightly darker, structurals slightly
    # lighter, engines/cockpits use base + edge-gradient hint.
    mat = profile.primary_material
    base_color = np.array(rgb(mat.base_color), dtype=np.float32)
    hi_color = np.array(rgb(mat.highlight_color), dtype=np.float32)
    lo_color = np.array(rgb(mat.shadow_color), dtype=np.float32)

    pixels = np.zeros((ch, cw, 3), dtype=np.float32)
    silhouette_mask = silhouette > 0.5
    pixels[silhouette_mask] = base_color

    # Per-category tint map — applied AFTER lighting so it doesn't dilute
    # the lighting gradient. Stored as a multiplier array.
    category_tint = np.ones((ch, cw), dtype=np.float32)
    for region in module_regions:
        ys, xs = region["coverage_slice"]
        cat = region["meta"]["category"]
        cov = region["coverage_local"] > 0.5
        if cat == "structural":
            tint_sub = category_tint[ys, xs]
            tint_sub[cov] = 1.05
            category_tint[ys, xs] = tint_sub
        elif cat == "weapon":
            tint_sub = category_tint[ys, xs]
            tint_sub[cov] = 0.92
            category_tint[ys, xs] = tint_sub

    # --- Phase 3: Global lighting pass ----------------------------------------
    # ONE light direction across the WHOLE silhouette. Not per-module.
    # This is the key algorithmic move.
    ys, xs = np.mgrid[0:ch, 0:cw]
    # Normalize canvas coordinates to [-1, 1] over the silhouette's bounding box.
    if silhouette_mask.any():
        y_idx, x_idx = np.where(silhouette_mask)
        bbox_y0, bbox_y1 = y_idx.min(), y_idx.max()
        bbox_x0, bbox_x1 = x_idx.min(), x_idx.max()
        bbox_h = max(1, bbox_y1 - bbox_y0)
        bbox_w = max(1, bbox_x1 - bbox_x0)
        nx = ((xs - bbox_x0) / bbox_w) * 2.0 - 1.0
        ny = ((ys - bbox_y0) / bbox_h) * 2.0 - 1.0
        light_x, light_y_raw = LIGHT_DIR
        light_y = -light_y_raw  # screen-y is down
        diffuse = 0.5 + 0.5 * (nx * light_x + ny * light_y)
        # Steepen contrast so gradient extremes are more visible after
        # palette-snap. S-curve around 0.5 amplifies extreme values
        # (pushes pixels further toward shadow or highlight).
        diffuse = 0.5 + (diffuse - 0.5) * 1.6
        diffuse = np.clip(diffuse, 0.0, 1.0)
        diffuse = diffuse * silhouette  # mask to ship

        # Blend base -> highlight/shadow by diffuse.
        t = diffuse[..., None]
        lo_mix = lo_color + (base_color - lo_color) * (t * 2.0)
        hi_mix = base_color + (hi_color - base_color) * ((t - 0.5) * 2.0)
        lit = np.where(t < 0.5, lo_mix, hi_mix)
        # Apply lighting at full strength (no dilution).
        pixels = np.where(silhouette_mask[..., None], lit, pixels)
        # Apply per-category tint AFTER lighting so it doesn't wash the gradient.
        pixels = pixels * category_tint[..., None]
    else:
        diffuse = np.zeros((ch, cw), dtype=np.float32)

    # --- Phase 4: Connection detail pass --------------------------------------
    # For each pair of modules with shared edges, draw a seam line.
    # Cheap approach: find boundary pixels between two module regions and
    # darken them slightly to suggest a welded seam.
    module_id_map = np.full((ch, cw), -1, dtype=np.int32)
    for i, region in enumerate(module_regions):
        ys, xs = region["coverage_slice"]
        cov = region["coverage_local"] > 0.5
        sub = module_id_map[ys, xs]
        sub[cov] = i
        module_id_map[ys, xs] = sub

    # Find pixels where id differs from any neighbor (within silhouette).
    seam_mask = np.zeros((ch, cw), dtype=bool)
    pad = np.pad(module_id_map, 1, constant_values=-1)
    me = module_id_map
    neighbors_differ = (
        ((pad[:-2, 1:-1] != me) & (pad[:-2, 1:-1] != -1))
        | ((pad[2:, 1:-1] != me) & (pad[2:, 1:-1] != -1))
        | ((pad[1:-1, :-2] != me) & (pad[1:-1, :-2] != -1))
        | ((pad[1:-1, 2:] != me) & (pad[1:-1, 2:] != -1))
    )
    seam_mask = neighbors_differ & silhouette_mask
    # Darken seam pixels.
    pixels[seam_mask] = pixels[seam_mask] * 0.72

    # --- Phase 5: Decoration pass (wear noise + rivets) -----------------------
    # Apply a low-frequency wear noise across the silhouette.
    if mat.wear_intensity > 0:
        wear_field = _value_noise(cw, ch, scale=0.08, seed=seed + 17)
        wear_mask = np.clip((0.42 - wear_field) / 0.42, 0, 1) * mat.wear_intensity
        darken = 1.0 - wear_mask * 0.35
        pixels = np.where(
            silhouette_mask[..., None],
            pixels * darken[..., None],
            pixels,
        )

    # High-frequency surface grain for material feel.
    if mat.noise_intensity > 0:
        grain = _value_noise(cw, ch, scale=0.3, seed=seed)
        grain_signed = (grain - 0.5) * 2.0
        grain_mod = 1.0 + grain_signed * mat.noise_intensity * 0.22
        pixels = np.where(
            silhouette_mask[..., None],
            pixels * grain_mod[..., None],
            pixels,
        )

    pixels = np.clip(pixels, 0, 255).astype(np.uint8)

    # --- Phase 6: Emissive pass -----------------------------------------------
    # Emissive pixels bypass lighting and get the emissive color.
    if emissive_mask.any():
        # Pick one emissive color — in a more mature system, per-module would vary.
        # For the spike, default to plasma_core; cockpit gets hud_cyan.
        for region in module_regions:
            cat = region["meta"]["category"]
            if not region["meta"].get("emissive_color"):
                continue
            ecolor = np.array(rgb(region["meta"]["emissive_color"]), dtype=np.float32)
            ys, xs = region["coverage_slice"]
            # Local emissive mask
            mt = MODULE_TYPES[region["placed"].module_type_id]
            _, emissive_local, _ = rasterize(mt, proportion_bias=profile.proportion_bias)
            lh, lw = emissive_local.shape
            # Match slices
            y0 = max(0, region["placed"].y); y1 = min(ch, region["placed"].y + lh)
            x0 = max(0, region["placed"].x); x1 = min(cw, region["placed"].x + lw)
            ly0 = y0 - region["placed"].y; ly1 = ly0 + (y1 - y0)
            lx0 = x0 - region["placed"].x; lx1 = lx0 + (x1 - x0)
            em_slice = emissive_local[ly0:ly1, lx0:lx1]
            e_mask = em_slice > 0.3
            # Write emissive color directly.
            target = pixels[y0:y1, x0:x1]
            if target.shape[:2] == e_mask.shape:
                target[e_mask] = ecolor.astype(np.uint8)
                pixels[y0:y1, x0:x1] = target

    # --- Phase 7: Palette snap (default for Aurelia) --------------------------
    if palette_snap:
        pixels = _snap_to_palette(pixels, silhouette_mask)

    # --- Build surface with alpha ---------------------------------------------
    surface = pygame.Surface((cw, ch), pygame.SRCALPHA)
    alpha = (silhouette * 255).astype(np.uint8)
    rgb_arr = pygame.surfarray.pixels3d(surface)
    rgb_arr[:, :, :] = pixels.transpose(1, 0, 2)
    del rgb_arr
    alpha_arr = pygame.surfarray.pixels_alpha(surface)
    alpha_arr[:, :] = alpha.T
    del alpha_arr

    # --- Rivets on silhouette -------------------------------------------------
    rivets = _place_rivets_silhouette(
        silhouette, mat.rivet_density, seed=seed + 9001
    )
    rivet_color = rgb("rivet")
    for rx, ry in rivets:
        # Skip rivets on emissive pixels.
        if emissive_mask[ry, rx] > 0.3:
            continue
        gfxdraw.filled_circle(surface, rx, ry, 1, rivet_color)

    if debug:
        font = pygame.font.Font(None, 12)
        info = f"{profile.id} | {len(placed_modules)}m {len(rivets)}r"
        txt = font.render(info, True, (255, 255, 255))
        surface.blit(txt, (2, 2))

    return surface


def _value_noise(width: int, height: int, scale: float, seed: int) -> np.ndarray:
    """Copy of render._value_noise for standalone ship module."""
    grid_w = max(2, int(width * scale))
    grid_h = max(2, int(height * scale))
    rng = np.random.default_rng(seed)
    low = rng.random((grid_h, grid_w), dtype=np.float32)
    ys = np.linspace(0, grid_h - 1, height)
    xs = np.linspace(0, grid_w - 1, width)
    y0 = np.floor(ys).astype(int); y1 = np.clip(y0 + 1, 0, grid_h - 1)
    x0 = np.floor(xs).astype(int); x1 = np.clip(x0 + 1, 0, grid_w - 1)
    dy = (ys - y0).reshape(-1, 1); dx = (xs - x0).reshape(1, -1)
    top = low[y0][:, x0] * (1 - dx) + low[y0][:, x1] * dx
    bot = low[y1][:, x0] * (1 - dx) + low[y1][:, x1] * dx
    return (top * (1 - dy) + bot * dy).astype(np.float32)


def _snap_to_palette(pixels: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Snap pixels within mask to nearest palette color. In-place semantics."""
    palette = palette_array()  # (N, 3)
    flat = pixels.reshape(-1, 3).astype(np.int32)
    mask_flat = mask.reshape(-1)
    # Only compute for masked pixels — the rest stay 0
    if mask_flat.any():
        opaque = flat[mask_flat]
        diff = opaque[:, None, :] - palette[None, :, :]
        d2 = np.sum(diff * diff, axis=-1)
        idx = np.argmin(d2, axis=-1)
        opaque[:] = palette[idx]
        flat[mask_flat] = opaque
    return flat.reshape(pixels.shape).astype(np.uint8)


def _place_rivets_silhouette(
    silhouette: np.ndarray,
    density_per_kpx2: float,
    seed: int,
    min_spacing_px: int = 7,
) -> list[tuple[int, int]]:
    """Distribute rivets across the whole ship silhouette."""
    h, w = silhouette.shape
    covered_px = int(silhouette.sum())
    if covered_px == 0 or density_per_kpx2 <= 0:
        return []
    target = int(covered_px * density_per_kpx2 / 1000.0)
    if target == 0:
        return []
    rng = np.random.default_rng(seed)
    placed: list[tuple[int, int]] = []
    max_attempts = target * 30
    attempts = 0
    while len(placed) < target and attempts < max_attempts:
        attempts += 1
        x = int(rng.integers(2, w - 2))
        y = int(rng.integers(2, h - 2))
        if silhouette[y, x] < 0.5:
            continue
        close = any(
            (px - x) ** 2 + (py - y) ** 2 < min_spacing_px ** 2
            for px, py in placed
        )
        if not close:
            placed.append((x, y))
    return placed
