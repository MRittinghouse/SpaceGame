"""Benchmark: ShipComposite full-rebuild cost (Combat §11.4 gate).

Measures the wall-clock cost of a full pipeline rebuild (InvalidationScope.ALL)
on a representative enemy build. The result determines which destruction-pipeline
strategy we ship:

  <  15 ms/rebuild: direct bucketed destruction progression (5 rebuilds per kill)
  15-30 ms/rebuild: lazy precompute on encounter start (one-time spike)
  >  30 ms/rebuild: Option C — composite + particle hybrid, no destruction state

Usage:
    python tools/benchmark_composite_rebuild.py

Prints: min / median / p95 / max rebuild times in ms across N samples on
three reference builds (small, medium, large enemy).
"""

from __future__ import annotations

import os
import statistics
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

from spacegame.data_loader import get_data_loader  # noqa: E402
from spacegame.engine.enemy_build_generator import generate_enemy_build  # noqa: E402
from spacegame.engine.ship_composite import InvalidationScope, ShipComposite  # noqa: E402

SAMPLES_PER_BUILD = 40
WARMUP_ITERATIONS = 2


def _benchmark_build(template_id: str, label: str) -> None:
    loader = get_data_loader()
    loader.load_all()
    template = loader.enemy_templates.get(template_id)
    if template is None:
        print(f"  [skip] {label} — template '{template_id}' not found")
        return
    build = generate_enemy_build(template)
    composite = ShipComposite(build)

    # Warmup (first rebuild incurs import/JIT warmup + numpy cache paths)
    for _ in range(WARMUP_ITERATIONS):
        composite.invalidate(InvalidationScope.ALL)
        composite.get_surface()

    samples_ms: list[float] = []
    for _ in range(SAMPLES_PER_BUILD):
        composite.invalidate(InvalidationScope.ALL)
        t0 = time.perf_counter()
        composite.get_surface()
        samples_ms.append((time.perf_counter() - t0) * 1000.0)

    samples_ms.sort()
    p95 = samples_ms[int(len(samples_ms) * 0.95)]
    median = statistics.median(samples_ms)
    pixel_count = len(build.pixels)
    canvas = f"{build.canvas_w}x{build.canvas_h}"
    print(
        f"  {label:20s} canvas={canvas:<7} pixels={pixel_count:>4}  "
        f"min={samples_ms[0]:6.2f}  med={median:6.2f}  p95={p95:6.2f}  max={samples_ms[-1]:6.2f}  ms"
    )


def main() -> None:
    print("ShipComposite rebuild cost (InvalidationScope.ALL, N=%d samples each)" % SAMPLES_PER_BUILD)
    print("Gate thresholds: <15ms direct · 15-30ms lazy precompute · >30ms Option C")
    print()
    targets = [
        ("pirate_scout", "small regular"),
        ("pirate_heavy", "mid regular"),
        ("void_leviathan", "legendary"),
        ("union_behemoth", "big boss"),
        ("reach_dreadnought", "big boss"),
    ]
    for template_id, label in targets:
        _benchmark_build(template_id, label)


if __name__ == "__main__":
    main()
