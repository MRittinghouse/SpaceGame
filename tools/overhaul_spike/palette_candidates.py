"""
Spike C — candidate palettes for the stress test.

Three palette philosophies, all using the same role names so materials
and renderers need zero changes. Role names are contractual; RGB values
are the degree of freedom.

- CONSERVATIVE  — muted industrial sci-fi. The baseline. Grounded. Think
                  The Expanse, early Starfield. Safe and legible.
- HIGH_CONTRAST — darker darks, brighter brights, more saturated mids.
                  Graphic-novel punch. Same hue families as conservative
                  but with more chroma and dynamic range.
- NEON          — glow-forward cyberpunk. Cool-purple void, electric
                  highlights, hot-pink plasma, magenta-leaning reach.
                  Hyper Light Drifter / Signalis energy.

The three palettes share all role names. Only RGB values differ. This
tests whether palette philosophy meaningfully changes the "feel" of
identical ship compositions under identical lighting.
"""

from __future__ import annotations

from .palette import PALETTE


# ---------------------------------------------------------------------------
# CONSERVATIVE — muted industrial. Baseline.
# ---------------------------------------------------------------------------

PALETTE_CONSERVATIVE: dict[str, tuple[int, int, int]] = {
    # Void
    "void_deep":        (10, 12, 20),
    "void_mid":         (18, 22, 36),
    "void_light":       (30, 38, 56),

    # Hull cold metal
    "hull_cold":         (80, 90, 110),
    "hull_cold_bright":  (150, 170, 200),
    "hull_cold_shadow":  (40, 48, 62),

    # Faction signatures
    "solari_chrome":         (210, 220, 230),
    "solari_chrome_bright":  (245, 248, 252),
    "solari_chrome_shadow":  (150, 160, 175),

    "reach_crimson":         (130, 40, 40),
    "reach_crimson_bright":  (185, 80, 70),
    "reach_crimson_shadow":  (70, 20, 20),

    "union_ceramic":         (200, 190, 170),
    "union_ceramic_bright":  (230, 222, 205),
    "union_ceramic_shadow":  (130, 120, 100),

    # Energy / emissive
    "plasma_core":   (255, 170, 60),
    "cryo_fractal":  (120, 220, 255),

    # UI
    "hud_cyan":      (80, 200, 230),
    "hud_warning":   (240, 140, 60),
    "hud_critical":  (240, 70, 70),
    "hud_muted":     (110, 120, 140),
    "hud_text":      (220, 225, 235),

    # Details
    "rivet":         (25, 28, 36),
    "glass_tint":    (40, 80, 100),
}


# ---------------------------------------------------------------------------
# HIGH_CONTRAST — same hues, more chroma + dynamic range.
# ---------------------------------------------------------------------------

PALETTE_HIGH_CONTRAST: dict[str, tuple[int, int, int]] = {
    # Void — darker, deeper
    "void_deep":        (4, 5, 10),
    "void_mid":         (14, 17, 28),
    "void_light":       (26, 32, 48),

    # Hull cold metal — wider range, more saturated base
    "hull_cold":         (88, 100, 128),
    "hull_cold_bright":  (180, 205, 240),
    "hull_cold_shadow":  (26, 32, 46),

    # Solari — more luminous, darker shadow
    "solari_chrome":         (228, 236, 248),
    "solari_chrome_bright":  (252, 253, 255),
    "solari_chrome_shadow":  (135, 152, 178),

    # Reach — hotter crimson, deeper shadow
    "reach_crimson":         (160, 32, 32),
    "reach_crimson_bright":  (220, 85, 60),
    "reach_crimson_shadow":  (55, 10, 10),

    # Union — warmer, brighter, deeper
    "union_ceramic":         (215, 198, 165),
    "union_ceramic_bright":  (245, 230, 200),
    "union_ceramic_shadow":  (115, 100, 78),

    # Energy — more vivid
    "plasma_core":   (255, 185, 55),
    "cryo_fractal":  (140, 235, 255),

    # UI — more chromatic
    "hud_cyan":      (95, 220, 248),
    "hud_warning":   (255, 155, 45),
    "hud_critical":  (255, 55, 55),
    "hud_muted":     (105, 118, 145),
    "hud_text":      (235, 240, 250),

    # Details
    "rivet":         (12, 14, 20),
    "glass_tint":    (25, 65, 95),
}


# ---------------------------------------------------------------------------
# NEON — glow-forward cyberpunk. Purple-tinted void, hot-pink plasma.
# ---------------------------------------------------------------------------

PALETTE_NEON: dict[str, tuple[int, int, int]] = {
    # Void — purple-tinted
    "void_deep":        (14, 10, 26),
    "void_mid":         (28, 22, 46),
    "void_light":       (48, 40, 78),

    # Hull cold metal — cool blue-purple shift
    "hull_cold":         (78, 84, 118),
    "hull_cold_bright":  (165, 180, 225),
    "hull_cold_shadow":  (30, 30, 58),

    # Solari — cool electric white
    "solari_chrome":         (218, 228, 248),
    "solari_chrome_bright":  (250, 252, 255),
    "solari_chrome_shadow":  (140, 155, 195),

    # Reach — pushed toward hot-pink/magenta
    "reach_crimson":         (158, 48, 92),
    "reach_crimson_bright":  (232, 102, 158),
    "reach_crimson_shadow":  (72, 18, 46),

    # Union — warm cream with slight magenta undertone
    "union_ceramic":         (198, 180, 168),
    "union_ceramic_bright":  (232, 218, 205),
    "union_ceramic_shadow":  (122, 108, 102),

    # Energy — hot pink plasma, electric cyan
    "plasma_core":   (255, 130, 180),
    "cryo_fractal":  (150, 235, 255),

    # UI — hot-pink/cyan cyberpunk
    "hud_cyan":      (100, 240, 255),
    "hud_warning":   (255, 105, 180),
    "hud_critical":  (255, 55, 125),
    "hud_muted":     (115, 108, 150),
    "hud_text":      (230, 232, 250),

    # Details
    "rivet":         (18, 14, 32),
    "glass_tint":    (60, 35, 105),
}


# ---------------------------------------------------------------------------
# BALANCED — 65% conservative + 35% high_contrast.
# Leans conservative but with slightly deeper shadows and slightly brighter
# highlights for better lighting legibility. Minimal saturation/warmth drift.
# ---------------------------------------------------------------------------

PALETTE_BALANCED: dict[str, tuple[int, int, int]] = {
    # Void — slightly darker than conservative
    "void_deep":        (8, 10, 17),
    "void_mid":         (17, 20, 33),
    "void_light":       (29, 36, 53),

    # Hull cold metal — wider lighting band, base largely unchanged
    "hull_cold":         (83, 94, 116),
    "hull_cold_bright":  (161, 182, 214),
    "hull_cold_shadow":  (35, 42, 56),

    # Solari — slightly lifted, shadow a touch deeper
    "solari_chrome":         (216, 226, 236),
    "solari_chrome_bright":  (247, 250, 253),
    "solari_chrome_shadow":  (145, 157, 176),

    # Reach — slightly richer crimson, shadow a touch deeper
    "reach_crimson":         (141, 37, 37),
    "reach_crimson_bright":  (197, 82, 67),
    "reach_crimson_shadow":  (65, 17, 17),

    # Union — slightly warmer base, slightly deeper shadow
    "union_ceramic":         (205, 193, 168),
    "union_ceramic_bright":  (235, 225, 203),
    "union_ceramic_shadow":  (125, 113, 92),

    # Energy — marginal lift
    "plasma_core":   (255, 175, 58),
    "cryo_fractal":  (127, 225, 255),

    # UI
    "hud_cyan":      (85, 207, 236),
    "hud_warning":   (245, 145, 55),
    "hud_critical":  (245, 65, 65),
    "hud_muted":     (108, 119, 142),
    "hud_text":      (225, 230, 240),

    # Details
    "rivet":         (20, 23, 30),
    "glass_tint":    (35, 75, 98),
}


CANDIDATES: dict[str, dict[str, tuple[int, int, int]]] = {
    "conservative":  PALETTE_CONSERVATIVE,
    "balanced":      PALETTE_BALANCED,
    "high_contrast": PALETTE_HIGH_CONTRAST,
    "neon":          PALETTE_NEON,
}


def activate_palette(name: str) -> None:
    """Replace the active PALETTE with the named candidate.

    All role names must match; mismatched roles will silently remain as
    the previous palette's values, which would corrupt compliance tests.
    This function validates role parity before swapping.
    """
    if name not in CANDIDATES:
        raise KeyError(f"Unknown palette candidate: {name}. Available: {list(CANDIDATES)}")
    candidate = CANDIDATES[name]
    missing = set(PALETTE) - set(candidate)
    extra = set(candidate) - set(PALETTE)
    if missing or extra:
        raise ValueError(
            f"Palette '{name}' role mismatch. "
            f"Missing: {sorted(missing)}. Extra: {sorted(extra)}."
        )
    PALETTE.clear()
    PALETTE.update(candidate)


def palette_summary(palette: dict[str, tuple[int, int, int]]) -> dict[str, float]:
    """Compute descriptive statistics for a palette (informational, not pass/fail).

    - luminance_range: max - min luminance across all entries
    - warmth_skew: mean(R-B) across all entries (positive = warm)
    - saturation_mean: mean perceptual chroma
    """
    import numpy as np

    arr = np.array(list(palette.values()), dtype=np.float32)
    r, g, b = arr[:, 0], arr[:, 1], arr[:, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    max_channel = arr.max(axis=1)
    min_channel = arr.min(axis=1)
    chroma = max_channel - min_channel
    return {
        "luminance_min":   float(lum.min()),
        "luminance_max":   float(lum.max()),
        "luminance_range": float(lum.max() - lum.min()),
        "warmth_skew":     float((r - b).mean()),
        "saturation_mean": float(chroma.mean()),
    }
