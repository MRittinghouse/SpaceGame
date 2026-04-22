"""
Manufacturer profiles — the visual identity of each in-world maker.

A profile picks a material and layers on shape/detail preferences. This
is what gives a Solari ship and a Union ship distinct identities even
when they share a silhouette template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .material import MATERIALS, Material


@dataclass(frozen=True)
class ManufacturerProfile:
    id: str
    name: str
    primary_material: Material
    detail_density: float      # 0 (minimalist) -> 1 (busy)
    shape_vocabulary: Literal["angular", "rounded", "organic", "modular"]
    signature_role: str        # palette role that appears on every manufactured part
    barrel_style: Literal["clean", "fluted", "vented"]
    proportion_bias: float     # -1 slim, 0 neutral, +1 chunky


PROFILES: dict[str, ManufacturerProfile] = {
    "solari": ManufacturerProfile(
        id="solari",
        name="Solari Logistics",
        primary_material=MATERIALS["solari_chrome"],
        detail_density=0.3,      # clean, minimalist
        shape_vocabulary="rounded",
        signature_role="hud_cyan",
        barrel_style="clean",
        proportion_bias=-0.2,    # slightly slim
    ),
    "reach": ManufacturerProfile(
        id="reach",
        name="Crimson Reach",
        primary_material=MATERIALS["crimson_iron"],
        detail_density=0.85,     # busy, grimy
        shape_vocabulary="angular",
        signature_role="plasma_core",
        barrel_style="vented",
        proportion_bias=0.3,     # chunkier
    ),
    "union": ManufacturerProfile(
        id="union",
        name="Miners Union",
        primary_material=MATERIALS["union_ceramic"],
        detail_density=0.7,      # heavy industrial
        shape_vocabulary="modular",
        signature_role="hud_warning",
        barrel_style="fluted",
        proportion_bias=0.5,     # bulky
    ),
}
