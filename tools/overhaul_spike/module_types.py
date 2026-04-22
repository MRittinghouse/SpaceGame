"""
Module type catalog for Spike B.

Four module types sufficient for a meaningful ship composition test:
cockpit, engine, weapon mount (reused from Spike A shape), structural plate.
Each type declares its own shape raster; all share the material/lighting
pipeline.

A module type is a pure *shape* + *category*. Materials and manufacturer
identity are separate concerns layered on top during rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


ModuleCategory = Literal["cockpit", "engine", "weapon", "structural"]


@dataclass(frozen=True)
class ModuleType:
    """Declarative geometry of a module type.

    The shape is defined abstractly (a rasterize function that produces
    a coverage mask at the given size). The size is nominal; variants
    can scale it up or down via manufacturer proportion_bias.
    """
    id: str
    category: ModuleCategory
    nominal_width: int
    nominal_height: int
    has_emissive: bool = False  # engine thrusters, cockpit window, etc.


# ---------------------------------------------------------------------------
# The catalog.
# Each entry pairs a ModuleType with a rasterize function.
# ---------------------------------------------------------------------------


MODULE_TYPES: dict[str, ModuleType] = {
    "cockpit": ModuleType(
        id="cockpit",
        category="cockpit",
        nominal_width=48,
        nominal_height=40,
        has_emissive=True,  # glass viewport
    ),
    "engine": ModuleType(
        id="engine",
        category="engine",
        nominal_width=40,
        nominal_height=36,
        has_emissive=True,  # thruster glow
    ),
    "weapon_small": ModuleType(
        id="weapon_small",
        category="weapon",
        nominal_width=48,
        nominal_height=28,
    ),
    "structural": ModuleType(
        id="structural",
        category="structural",
        nominal_width=40,
        nominal_height=32,
    ),
}


def rasterize(
    module_type: ModuleType,
    proportion_bias: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Rasterize a module type into (coverage, emissive, metadata) arrays.

    - coverage: (H, W) float32, 1.0 inside shape, 0.0 outside
    - emissive: (H, W) float32, intensity of emissive areas (0 if not emissive)
    - metadata: dict with category-specific info (e.g., thruster exhaust origin)
    """
    w = module_type.nominal_width
    h = module_type.nominal_height
    # Apply proportion bias: chunkier manufacturers get slightly wider modules.
    w = int(w * (1.0 + proportion_bias * 0.08))
    h = int(h * (1.0 + proportion_bias * 0.05))

    coverage = np.zeros((h, w), dtype=np.float32)
    emissive = np.zeros((h, w), dtype=np.float32)
    meta: dict = {"width": w, "height": h, "category": module_type.category}

    if module_type.category == "cockpit":
        # Rounded nose + body. A trapezoidal shape with a curved front.
        for y in range(h):
            # Linear taper for trapezoid back half, curved front half
            if y < h // 2:
                # Front half: curved nose
                t = y / (h // 2 - 1) if h // 2 > 1 else 0
                # Half-ellipse frontage
                taper = 1.0 - (1.0 - t) ** 2
                half_w = int((w // 2) * taper)
            else:
                half_w = w // 2 - 2
            cx = w // 2
            coverage[y, max(0, cx - half_w):min(w, cx + half_w + 1)] = 1.0
        # Glass viewport (emissive) — center front
        vp_y0 = int(h * 0.20); vp_y1 = int(h * 0.45)
        vp_x0 = int(w * 0.28); vp_x1 = int(w * 0.72)
        mask = coverage[vp_y0:vp_y1, vp_x0:vp_x1] > 0.5
        emissive[vp_y0:vp_y1, vp_x0:vp_x1][mask] = 1.0
        meta["emissive_color"] = "hud_cyan"

    elif module_type.category == "engine":
        # Rectangular body with bell-shaped thruster at rear.
        body_w = int(w * 0.85)
        body_x0 = (w - body_w) // 2
        body_y0 = int(h * 0.15)
        body_y1 = int(h * 0.85)
        coverage[body_y0:body_y1, body_x0:body_x0 + body_w] = 1.0
        # Thruster bell (rear, right side)
        bell_x0 = body_x0 + body_w - 4
        bell_x1 = w - 2
        for y in range(body_y0 + 3, body_y1 - 3):
            # Taper outward
            t = (y - body_y0 - 3) / max(1, body_y1 - body_y0 - 7)
            flare = int(3 * np.sin(np.pi * t))
            y_in_bell = y
            coverage[y_in_bell, bell_x0:bell_x1 + 1] = 1.0
            # Emissive glow at the very tip
            emissive[y_in_bell, bell_x1 - 3:bell_x1 + 1] = 1.0 - abs(2 * t - 1) * 0.3
        meta["emissive_color"] = "plasma_core"
        meta["exhaust_origin"] = (bell_x1, h // 2)

    elif module_type.category == "weapon":
        # Reuse weapon mount shape from Spike A — simplified.
        # Base rect + barrel extending right.
        base_h = int(h * 0.70)
        base_y0 = (h - base_h) // 2
        base_w = int(w * 0.70)
        coverage[base_y0:base_y0 + base_h, 2:base_w + 2] = 1.0
        # Barrel — thin rectangle extending right
        bar_h = max(6, int(h * 0.30))
        bar_y0 = h // 2 - bar_h // 2
        coverage[bar_y0:bar_y0 + bar_h, base_w:w - 2] = 1.0

    elif module_type.category == "structural":
        # Plain hex-like plate — gives connective tissue between modules.
        cx, cy = w // 2, h // 2
        # Hexagon via y-band width variation
        for y in range(h):
            rel = abs(y - cy) / max(cy, 1)  # 0 at center, 1 at edge
            width_at_y = int(w * (0.95 - rel * 0.25))
            half = width_at_y // 2
            coverage[y, max(0, cx - half):min(w, cx + half + 1)] = 1.0

    return coverage, emissive, meta
