"""
Spike C entry point — palette stress test.

Renders the Spike B ship layout (3 manufacturers x 6 modules) under
each of three candidate palettes (conservative / high_contrast / neon).
Produces per-palette atlases, a 3x3 comparison atlas, and a critique
report comparing objective metrics across palettes.

Run:
    python -m tools.overhaul_spike.spike_palettes

Output (in tools/overhaul_spike/output/):
    palette_conservative.png
    palette_high_contrast.png
    palette_neon.png
    palette_compare.png          -- 3x3 grid, palette x manufacturer
    palette_critique_report.txt
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pygame

from .critique import (
    check_alpha_discipline,
    check_detail_density,
    check_palette_compliance,
    check_palette_line_compliance,
    check_silhouette_readability,
    check_variant_distinctness,
    format_report,
    hash_surface,
)
from .manufacturer import PROFILES
from .palette_candidates import CANDIDATES, activate_palette, palette_summary
from .ship_render import compose_ship
from .spike_ship import (
    SHIP_LAYOUT,
    build_ship_atlas,
    check_ship_lighting_consistency,
    check_ship_single_connected,
)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.init()
pygame.display.set_mode((1, 1))

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)

SEED = 42
PALETTE_ORDER = ("conservative", "balanced", "high_contrast", "neon")


def render_ships_under_palette(palette_name: str) -> dict[str, pygame.Surface]:
    """Activate palette and render all three manufacturers' ships."""
    activate_palette(palette_name)
    ships: dict[str, pygame.Surface] = {}
    for manuf_id, profile in PROFILES.items():
        ships[manuf_id] = compose_ship(
            SHIP_LAYOUT, profile, seed=SEED, palette_snap=True
        )
    return ships


def build_palette_compare_atlas(
    atlases_by_palette: dict[str, pygame.Surface],
    label_height: int = 24,
    bg_rgb: tuple[int, int, int] = (6, 8, 14),
) -> pygame.Surface:
    """Stack per-palette atlases vertically with header labels."""
    atlases = [atlases_by_palette[n] for n in PALETTE_ORDER]
    w = max(a.get_width() for a in atlases)
    h = sum(a.get_height() + label_height for a in atlases) + 16
    compare = pygame.Surface((w, h))
    compare.fill(bg_rgb)
    font = pygame.font.Font(None, 22)
    y = 4
    for name, atlas in zip(PALETTE_ORDER, atlases):
        label = font.render(name.upper().replace("_", " "), True, (235, 240, 250))
        compare.blit(label, (12, y))
        y += label_height
        compare.blit(atlas, (0, y))
        y += atlas.get_height()
    return compare


def critique_one_palette(
    palette_name: str, ships: dict[str, pygame.Surface]
) -> list[str]:
    """Run the full Spike B critique suite on ships rendered under this palette.

    IMPORTANT: activate_palette MUST have been called before this — palette
    compliance checks use the currently-active PALETTE.
    """
    lines: list[str] = []
    lines.append(f"=== PALETTE: {palette_name.upper()} ===")

    summary = palette_summary(CANDIDATES[palette_name])
    lines.append(
        f"  luminance_range={summary['luminance_range']:.1f}  "
        f"warmth_skew={summary['warmth_skew']:+.1f}  "
        f"saturation_mean={summary['saturation_mean']:.1f}"
    )
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
        lines.append(format_report(f"{palette_name}/ship_{manuf_id}", results))
        lines.append("")

    # Variant distinctness within this palette
    dist = check_variant_distinctness(list(ships.values()))
    mark = "PASS" if dist.passed else "FAIL"
    lines.append(f"  [{mark}] variant_distinctness: {dist.diagnostic}")
    lines.append("")
    return lines


def main() -> None:
    t0 = time.time()

    ships_by_palette: dict[str, dict[str, pygame.Surface]] = {}
    atlases_by_palette: dict[str, pygame.Surface] = {}

    for name in PALETTE_ORDER:
        ships = render_ships_under_palette(name)
        ships_by_palette[name] = ships
        atlas = build_ship_atlas(ships)
        atlases_by_palette[name] = atlas
        pygame.image.save(atlas, str(OUT_DIR / f"palette_{name}.png"))

    # Stacked 3-palette comparison image
    compare = build_palette_compare_atlas(atlases_by_palette)
    pygame.image.save(compare, str(OUT_DIR / "palette_compare.png"))

    elapsed = time.time() - t0

    # --- Cross-palette critique ------------------------------------------
    lines: list[str] = []
    lines.append("SPIKE C: palette stress test")
    lines.append(f"Seed: {SEED}  |  Palettes tested: {', '.join(PALETTE_ORDER)}")
    lines.append(f"Render time (9 ships across 3 palettes): {elapsed*1000:.1f} ms")
    lines.append(f"Canvas: 240 x 160  |  Modules per ship: {len(SHIP_LAYOUT)}")
    lines.append("")

    # Per-palette summary header
    lines.append("PALETTE DESCRIPTIVE STATS")
    for name in PALETTE_ORDER:
        summary = palette_summary(CANDIDATES[name])
        lines.append(
            f"  {name:15s}  lum_range={summary['luminance_range']:6.1f}  "
            f"warmth={summary['warmth_skew']:+6.1f}  "
            f"saturation={summary['saturation_mean']:6.1f}"
        )
    lines.append("")

    # Per-palette full critique (each must activate its own palette)
    for name in PALETTE_ORDER:
        activate_palette(name)
        lines.extend(critique_one_palette(name, ships_by_palette[name]))

    # --- Determinism across palettes (same seed, different palette should produce
    #     deterministically different output) ----------------------------
    lines.append("CROSS-PALETTE DETERMINISM")
    for manuf_id in PROFILES:
        hashes_by_palette: dict[str, str] = {}
        for name in PALETTE_ORDER:
            activate_palette(name)
            profile = PROFILES[manuf_id]
            surf = compose_ship(SHIP_LAYOUT, profile, seed=SEED, palette_snap=True)
            hashes_by_palette[name] = hash_surface(surf)
        all_distinct = len(set(hashes_by_palette.values())) == len(PALETTE_ORDER)
        mark = "PASS" if all_distinct else "FAIL"
        lines.append(
            f"  [{mark}] {manuf_id}: "
            + "  ".join(f"{n}={h[:8]}" for n, h in hashes_by_palette.items())
        )
    lines.append("")

    # --- Per-ship variant distinctness ACROSS palettes --------------------
    # For each manufacturer, compare the three palette renderings.
    lines.append("SAME SHIP, DIFFERENT PALETTES (distinctness per manufacturer)")
    for manuf_id in PROFILES:
        # Need to re-render under each palette to capture into list.
        surfaces = []
        for name in PALETTE_ORDER:
            activate_palette(name)
            profile = PROFILES[manuf_id]
            surfaces.append(
                compose_ship(SHIP_LAYOUT, profile, seed=SEED, palette_snap=True)
            )
        dist = check_variant_distinctness(surfaces, min_mean_diff=30.0)
        mark = "PASS" if dist.passed else "FAIL"
        lines.append(f"  [{mark}] {manuf_id} across palettes: {dist.diagnostic}")
    lines.append("")

    report = "\n".join(lines)
    (OUT_DIR / "palette_critique_report.txt").write_text(report, encoding="utf-8")
    safe = report.replace("≥", ">=").replace("→", "->")
    print(safe)
    print()
    print(f"Output saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
