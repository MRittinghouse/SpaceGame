"""
Canonical 24-color palette for the overhaul spike.

Every procedural renderer in the spike references palette entries by
role name — no raw RGB in rendering code. This is the discipline that
makes palette compliance testable.

PALETTE is mutable at runtime so Spike C can swap in candidate palettes
via ``palette_candidates.activate_palette(name)``. Role names remain
constant across candidates; only the RGB values change.
"""

# role name -> (R, G, B)
# NOTE: intentionally NOT Final — Spike C swaps this dict to stress-test
# candidate palettes. See palette_candidates.py.
PALETTE: dict[str, tuple[int, int, int]] = {
    # --- Void / space background ---
    "void_deep":        (10, 12, 20),
    "void_mid":         (18, 22, 36),
    "void_light":       (30, 38, 56),

    # --- Hull cold metal (default industrial) ---
    "hull_cold":         (80, 90, 110),
    "hull_cold_bright":  (150, 170, 200),
    "hull_cold_shadow":  (40, 48, 62),

    # --- Faction signature metals ---
    "solari_chrome":         (210, 220, 230),
    "solari_chrome_bright":  (245, 248, 252),
    "solari_chrome_shadow":  (150, 160, 175),

    "reach_crimson":         (130, 40, 40),
    "reach_crimson_bright":  (185, 80, 70),
    "reach_crimson_shadow":  (70, 20, 20),

    "union_ceramic":         (200, 190, 170),
    "union_ceramic_bright":  (230, 222, 205),
    "union_ceramic_shadow":  (130, 120, 100),

    # --- Energy / emissive ---
    "plasma_core":   (255, 170, 60),
    "cryo_fractal":  (120, 220, 255),

    # --- UI (for later systems; included for palette completeness) ---
    "hud_cyan":      (80, 200, 230),
    "hud_warning":   (240, 140, 60),
    "hud_critical":  (240, 70, 70),
    "hud_muted":     (110, 120, 140),
    "hud_text":      (220, 225, 235),

    # --- Details ---
    "rivet":         (25, 28, 36),
    "glass_tint":    (40, 80, 100),
}


def rgb(role: str) -> tuple[int, int, int]:
    """Look up a palette entry. Raises KeyError if role is misspelled."""
    return PALETTE[role]


def palette_array():
    """Return the palette as an (N, 3) numpy array for vectorized operations."""
    import numpy as np
    return np.array(list(PALETTE.values()), dtype=np.int32)
