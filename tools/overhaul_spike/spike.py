"""
Spike entry point.

Renders a weapon-mount module for three manufacturers (Solari, Reach,
Union), saves PNGs, runs the critique harness, and writes a report.

Run:
    python -m tools.overhaul_spike.spike

Output:
    tools/overhaul_spike/output/
        module_solari.png
        module_reach.png
        module_union.png
        module_atlas.png      (all three side-by-side on a void bg)
        critique_report.txt
"""

from __future__ import annotations

import os
import time
from pathlib import Path

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
)
from .manufacturer import PROFILES
from .palette import rgb
from .render import render_module

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # headless
pygame.init()
pygame.display.set_mode((1, 1))  # minimal display for convert_alpha calls

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)


def render_all(seed: int = 42, palette_snap: bool = False) -> dict[str, pygame.Surface]:
    surfaces = {}
    for manuf_id, profile in PROFILES.items():
        surfaces[manuf_id] = render_module(profile, seed=seed, palette_snap=palette_snap)
    return surfaces


def build_atlas(
    surfaces: dict[str, pygame.Surface],
    background_rgb: tuple[int, int, int] = (10, 12, 20),
    padding: int = 24,
) -> pygame.Surface:
    """Compose all variants side-by-side on the void background."""
    # Assume all same size.
    widths = [s.get_width() for s in surfaces.values()]
    heights = [s.get_height() for s in surfaces.values()]
    w = sum(widths) + padding * (len(surfaces) + 1)
    h = max(heights) + padding * 2 + 16  # extra for labels
    atlas = pygame.Surface((w, h))
    atlas.fill(background_rgb)
    font = pygame.font.Font(None, 16)
    x = padding
    for manuf_id, surf in surfaces.items():
        y = padding
        atlas.blit(surf, (x, y))
        label = font.render(manuf_id.upper(), True, (220, 225, 235))
        atlas.blit(label, (x, y + surf.get_height() + 4))
        x += surf.get_width() + padding
    return atlas


def save_png(surface: pygame.Surface, path: Path) -> None:
    pygame.image.save(surface, str(path))


def main() -> None:
    seed = 42

    # --- Pass 1: gradient rendering (the default) -----------------------------
    t0 = time.time()
    surfaces_grad = render_all(seed=seed, palette_snap=False)
    grad_elapsed = time.time() - t0

    # --- Pass 2: palette-snapped rendering (comparison) -----------------------
    t0 = time.time()
    surfaces_snap = render_all(seed=seed, palette_snap=True)
    snap_elapsed = time.time() - t0

    # --- Save outputs ---------------------------------------------------------
    for manuf_id, surf in surfaces_grad.items():
        save_png(surf, OUT_DIR / f"module_{manuf_id}.png")
    for manuf_id, surf in surfaces_snap.items():
        save_png(surf, OUT_DIR / f"module_{manuf_id}_snap.png")

    atlas_grad = build_atlas(surfaces_grad)
    save_png(atlas_grad, OUT_DIR / "module_atlas_gradient.png")
    atlas_snap = build_atlas(surfaces_snap)
    save_png(atlas_snap, OUT_DIR / "module_atlas_snapped.png")

    # Stacked comparison: gradient over snapped.
    w = atlas_grad.get_width()
    h = atlas_grad.get_height() + atlas_snap.get_height() + 20
    comp = pygame.Surface((w, h))
    comp.fill((10, 12, 20))
    comp.blit(atlas_grad, (0, 0))
    comp.blit(atlas_snap, (0, atlas_grad.get_height() + 20))
    save_png(comp, OUT_DIR / "module_atlas_compare.png")

    # ---- Critique ---------------------------------------------------------
    report_sections: list[str] = []
    report_sections.append("SPIKE: module render for 3 manufacturers")
    report_sections.append(f"Seed: {seed}")
    report_sections.append(
        f"Render time: gradient {grad_elapsed*1000:.1f} ms, "
        f"snapped {snap_elapsed*1000:.1f} ms (both for 3 modules)"
    )
    report_sections.append("")

    report_sections.append("=" * 72)
    report_sections.append("PASS 1: GRADIENT RENDERING (smooth intermediates)")
    report_sections.append("=" * 72)
    for manuf_id, surf in surfaces_grad.items():
        results = [
            check_palette_compliance(surf, tolerance_rgb=12, min_pct=0.90),
            check_palette_line_compliance(surf, tolerance_rgb=10, min_pct=0.95),
            check_silhouette_readability(surf),
            check_alpha_discipline(surf),
            check_detail_density(surf),
        ]
        report_sections.append(format_report(f"module_{manuf_id} (gradient)", results))
        report_sections.append("")

    report_sections.append("=" * 72)
    report_sections.append("PASS 2: PALETTE-SNAPPED (flat pixel-art look)")
    report_sections.append("=" * 72)
    for manuf_id, surf in surfaces_snap.items():
        results = [
            check_palette_compliance(surf, tolerance_rgb=12, min_pct=0.90),
            check_palette_line_compliance(surf, tolerance_rgb=10, min_pct=0.95),
            check_silhouette_readability(surf),
            check_alpha_discipline(surf),
            check_detail_density(surf),
        ]
        report_sections.append(format_report(f"module_{manuf_id} (snapped)", results))
        report_sections.append("")

    # Determinism
    report_sections.append("DETERMINISM (gradient)")
    for manuf_id, profile in PROFILES.items():
        det = check_determinism(render_module, profile, seed=seed)
        mark = "PASS" if det.passed else "FAIL"
        report_sections.append(f"  [{mark}] {manuf_id}: {det.diagnostic}")
    report_sections.append("")

    # Variant distinctness
    report_sections.append("VARIANT DISTINCTNESS")
    dist_grad = check_variant_distinctness(list(surfaces_grad.values()))
    mark = "PASS" if dist_grad.passed else "FAIL"
    report_sections.append(f"  [{mark}] gradient: {dist_grad.diagnostic}")
    dist_snap = check_variant_distinctness(list(surfaces_snap.values()))
    mark = "PASS" if dist_snap.passed else "FAIL"
    report_sections.append(f"  [{mark}] snapped:  {dist_snap.diagnostic}")
    report_sections.append("")

    report = "\n".join(report_sections)
    (OUT_DIR / "critique_report.txt").write_text(report, encoding="utf-8")
    safe = report.replace("≥", ">=").replace("→", "->")
    print(safe)
    print()
    print(f"Output saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
