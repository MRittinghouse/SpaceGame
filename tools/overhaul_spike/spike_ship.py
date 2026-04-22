"""
Spike B entry point — ship composition.

Composes a 6-module ship for each manufacturer, renders via unified-object
algorithm, saves PNGs + critique report.

Run:
    python -m tools.overhaul_spike.spike_ship

Output:
    tools/overhaul_spike/output/
        ship_solari.png
        ship_reach.png
        ship_union.png
        ship_atlas.png
        ship_critique_report.txt
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pygame

from .critique import (
    check_alpha_discipline,
    check_detail_density,
    check_determinism,
    check_palette_compliance,
    check_palette_line_compliance,
    check_silhouette_readability,
    check_variant_distinctness,
    format_report,
    CritiqueResult,
    hash_surface,
)
from .manufacturer import PROFILES
from .ship_render import PlacedModule, compose_ship

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.init()
pygame.display.set_mode((1, 1))

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Ship layout — 6 modules in a canonical small-ship arrangement.
#
# Canvas: 240 x 160. Centered roughly around (120, 80).
#
#     [weapon]
#         \
#   [struct]—[cockpit]—[engine][engine]
#         /
#     [weapon]
#
# ---------------------------------------------------------------------------

SHIP_LAYOUT = [
    # Densely overlapping layout — accepts abstract ship shape since
    # modules lack rotation support. Validates composition algorithm
    # connectivity and unified-object lighting, not ship design.
    PlacedModule("cockpit",      x=78,  y=50),   # central body, spans (78-125, 50-89)
    PlacedModule("structural",   x=100, y=62),   # nested inside cockpit back
    PlacedModule("engine",       x=122, y=52),   # overlaps cockpit right + top-engine
    PlacedModule("engine",       x=122, y=82),   # overlaps cockpit right + bottom
    PlacedModule("weapon_small", x=88,  y=36),   # overlaps cockpit top
    PlacedModule("weapon_small", x=88,  y=88),   # overlaps cockpit bottom
]


# ---------------------------------------------------------------------------
# Ship-specific critique dimensions
# ---------------------------------------------------------------------------

def check_ship_single_connected(surface: pygame.Surface) -> CritiqueResult:
    """Ship silhouette must be ONE connected component.

    A ship that breaks into disconnected fragments reads as broken, not
    as a vehicle. This is a composition-level test the per-module checks
    can't detect.
    """
    alpha = pygame.surfarray.pixels_alpha(surface)
    mask = (alpha > 16).T  # (H, W)
    if not mask.any():
        return CritiqueResult("ship_connected", False, "no opaque pixels")
    # Flood fill from the first opaque pixel via scipy would be ideal;
    # implement a simple BFS without scipy dependency.
    h, w = mask.shape
    visited = np.zeros_like(mask)
    # Find first opaque pixel
    ys, xs = np.where(mask)
    start_y, start_x = int(ys[0]), int(xs[0])
    stack = [(start_y, start_x)]
    visited[start_y, start_x] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                stack.append((ny, nx))
    # Compare visited count to total mask count
    reached = int(visited.sum())
    total = int(mask.sum())
    ok = reached == total
    return CritiqueResult(
        "ship_connected",
        ok,
        f"{reached}/{total} opaque pixels in largest connected region",
    )


def check_ship_lighting_consistency(surface: pygame.Surface) -> CritiqueResult:
    """Upper-right half of the ship should be brighter than lower-left.

    Tests the §6 'global lighting pass' — the whole ship lit as one
    object. If modules are independently lit, this check will still pass
    locally but global gradient may be noisy. A cleaner version measures
    per-module mean brightness and confirms they increase toward the light.
    """
    rgb = pygame.surfarray.pixels3d(surface).astype(np.float32)
    alpha = pygame.surfarray.pixels_alpha(surface).astype(np.float32)
    mask = (alpha > 16).T  # (H, W)
    if not mask.any():
        return CritiqueResult("lighting_consistency", False, "no opaque pixels")
    # Luminance per pixel
    rgb_hw = rgb.transpose(1, 0, 2)  # (H, W, 3)
    lum = 0.299 * rgb_hw[:, :, 0] + 0.587 * rgb_hw[:, :, 1] + 0.114 * rgb_hw[:, :, 2]
    ys, xs = np.where(mask)
    y_min, y_max = ys.min(), ys.max()
    x_min, x_max = xs.min(), xs.max()
    # Upper-right quadrant luminance
    y_mid = (y_min + y_max) // 2
    x_mid = (x_min + x_max) // 2
    upper_right = mask & (np.arange(mask.shape[0])[:, None] <= y_mid) & (np.arange(mask.shape[1])[None, :] >= x_mid)
    lower_left = mask & (np.arange(mask.shape[0])[:, None] > y_mid) & (np.arange(mask.shape[1])[None, :] < x_mid)
    if not upper_right.any() or not lower_left.any():
        return CritiqueResult("lighting_consistency", True, "insufficient ship extent")
    ur_lum = float(lum[upper_right].mean())
    ll_lum = float(lum[lower_left].mean())
    diff = ur_lum - ll_lum
    ok = diff > 5.0  # upper-right should be meaningfully brighter
    return CritiqueResult(
        "lighting_consistency",
        ok,
        f"upper-right luminance {ur_lum:.1f} vs lower-left {ll_lum:.1f} (diff {diff:+.1f})",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def render_all_ships(seed: int = 42, palette_snap: bool = True) -> dict[str, pygame.Surface]:
    ships = {}
    for manuf_id, profile in PROFILES.items():
        ships[manuf_id] = compose_ship(
            SHIP_LAYOUT, profile, seed=seed, palette_snap=palette_snap
        )
    return ships


def build_ship_atlas(
    ships: dict[str, pygame.Surface],
    background_rgb: tuple[int, int, int] = (10, 12, 20),
    padding: int = 24,
) -> pygame.Surface:
    widths = [s.get_width() for s in ships.values()]
    heights = [s.get_height() for s in ships.values()]
    w = sum(widths) + padding * (len(ships) + 1)
    h = max(heights) + padding * 2 + 16
    atlas = pygame.Surface((w, h))
    atlas.fill(background_rgb)
    font = pygame.font.Font(None, 16)
    x = padding
    for manuf_id, surf in ships.items():
        y = padding
        atlas.blit(surf, (x, y))
        label = font.render(manuf_id.upper(), True, (220, 225, 235))
        atlas.blit(label, (x, y + surf.get_height() + 4))
        x += surf.get_width() + padding
    return atlas


def main() -> None:
    seed = 42

    # Default: palette-snapped per aesthetic decision.
    t0 = time.time()
    ships = render_all_ships(seed=seed, palette_snap=True)
    elapsed = time.time() - t0

    # Also render gradient mode for comparison atlas.
    ships_grad = render_all_ships(seed=seed, palette_snap=False)

    # Save outputs.
    for manuf_id, surf in ships.items():
        pygame.image.save(surf, str(OUT_DIR / f"ship_{manuf_id}.png"))
    for manuf_id, surf in ships_grad.items():
        pygame.image.save(surf, str(OUT_DIR / f"ship_{manuf_id}_gradient.png"))

    atlas = build_ship_atlas(ships)
    pygame.image.save(atlas, str(OUT_DIR / "ship_atlas.png"))
    atlas_grad = build_ship_atlas(ships_grad)
    pygame.image.save(atlas_grad, str(OUT_DIR / "ship_atlas_gradient.png"))

    # Stacked comparison
    w = atlas.get_width()
    h = atlas.get_height() + atlas_grad.get_height() + 20
    comp = pygame.Surface((w, h))
    comp.fill((10, 12, 20))
    comp.blit(atlas, (0, 0))
    comp.blit(atlas_grad, (0, atlas.get_height() + 20))
    pygame.image.save(comp, str(OUT_DIR / "ship_atlas_compare.png"))

    # --- Critique ---------------------------------------------------------
    lines: list[str] = []
    lines.append("SPIKE B: ship composition for 3 manufacturers (palette-snapped)")
    lines.append(f"Seed: {seed}")
    lines.append(f"Render time (3 ships, snapped): {elapsed*1000:.1f} ms")
    lines.append(f"Canvas: 240 x 160  |  Modules per ship: {len(SHIP_LAYOUT)}")
    lines.append("")

    for manuf_id, surf in ships.items():
        results = [
            check_palette_compliance(surf, tolerance_rgb=12, min_pct=0.90),
            check_palette_line_compliance(surf, tolerance_rgb=10, min_pct=0.95),
            check_silhouette_readability(surf),
            check_alpha_discipline(surf),
            check_detail_density(surf),
            check_ship_single_connected(surf),
            check_ship_lighting_consistency(surf),
        ]
        lines.append(format_report(f"ship_{manuf_id}", results))
        lines.append("")

    lines.append("DETERMINISM")
    for manuf_id, profile in PROFILES.items():
        hashes = [
            hash_surface(compose_ship(SHIP_LAYOUT, profile, seed=seed, palette_snap=True))
            for _ in range(3)
        ]
        ok = len(set(hashes)) == 1
        mark = "PASS" if ok else "FAIL"
        lines.append(f"  [{mark}] {manuf_id}: {len(set(hashes))} distinct hash(es)")
    lines.append("")

    lines.append("VARIANT DISTINCTNESS")
    dist = check_variant_distinctness(list(ships.values()))
    mark = "PASS" if dist.passed else "FAIL"
    lines.append(f"  [{mark}] 3 manufacturers (snapped): {dist.diagnostic}")
    lines.append("")

    report = "\n".join(lines)
    (OUT_DIR / "ship_critique_report.txt").write_text(report, encoding="utf-8")
    safe = report.replace("≥", ">=").replace("→", "->")
    print(safe)
    print()
    print(f"Output saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
