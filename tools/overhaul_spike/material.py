"""
Material system for the overhaul spike.

A material is a parametric function: given a shape region and lighting,
produce a surface fill. Materials are composed into manufacturer
profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Material:
    """Parametric material definition.

    Each material references palette roles by name; rendering is done
    via the shared render pipeline in ``render.py``.
    """

    name: str
    base_color: str              # palette role
    highlight_color: str         # lit-side color (palette role)
    shadow_color: str            # unlit-side color (palette role)
    noise_intensity: float       # 0 (clean) -> 1 (heavy surface grain)
    noise_scale: float           # lower = bigger patches
    wear_intensity: float        # baseline grime
    rivet_density: float         # approximate rivets per 1000 px^2 (0 = none)
    gloss: float                 # edge-highlight strength, 0-1
    kind: Literal["solid", "emissive"] = "solid"
    signature_stripe: str | None = None  # optional palette-role stripe accent


# ---------------------------------------------------------------------------
# Material library (v1 — spike scope)
# ---------------------------------------------------------------------------

MATERIALS: dict[str, Material] = {
    "brushed_steel": Material(
        name="brushed_steel",
        base_color="hull_cold",
        highlight_color="hull_cold_bright",
        shadow_color="hull_cold_shadow",
        noise_intensity=0.15,
        noise_scale=0.25,
        wear_intensity=0.1,
        rivet_density=0.8,
        gloss=0.3,
    ),
    "solari_chrome": Material(
        name="solari_chrome",
        base_color="solari_chrome",
        highlight_color="solari_chrome_bright",
        shadow_color="solari_chrome_shadow",
        noise_intensity=0.06,        # clean, polished
        noise_scale=0.4,
        wear_intensity=0.03,          # very little grime
        rivet_density=0.2,            # minimalist
        gloss=0.7,                    # strong highlight
        signature_stripe="hud_cyan",  # cyan accent stripe
    ),
    "crimson_iron": Material(
        name="crimson_iron",
        base_color="reach_crimson",
        highlight_color="reach_crimson_bright",
        shadow_color="reach_crimson_shadow",
        noise_intensity=0.35,         # heavy grain
        noise_scale=0.18,
        wear_intensity=0.4,           # lots of patina
        rivet_density=1.5,            # many rivets
        gloss=0.15,                   # matte
        signature_stripe="plasma_core",
    ),
    "union_ceramic": Material(
        name="union_ceramic",
        base_color="union_ceramic",
        highlight_color="union_ceramic_bright",
        shadow_color="union_ceramic_shadow",
        noise_intensity=0.22,         # some speckle (carbon scoring)
        noise_scale=0.3,
        wear_intensity=0.25,
        rivet_density=2.2,            # heavy industrial rivets
        gloss=0.1,                    # matte ceramic
        signature_stripe="hud_warning",
    ),
}
