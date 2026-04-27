"""Canonical palette + material band infrastructure.

Implements the 58-entry Aurelia palette per Aesthetic Bible §2 (29
material-band entries across 7 bands + 29 role entries). Provides:

  - Palette constants (MATERIAL_BANDS, PALETTE_ROLES)
  - Lookups (get_band, get_role, name listings, validity checks)
  - Snap helpers (snap_to_band, snap_to_role, lerp_in_band)
  - Category offset (band-index shift per Bible §3.3)
  - Colorblind remap infrastructure (ColorblindProfile + active-profile hook)
  - Compliance test helpers (assert_band_compliance, assert_role_compliance)

Consumer pattern: renderers reference bands and roles by name, never raw
RGB. This enables colorblind remapping via a single profile rather than
per-site changes.

See requirements/overhaul/95_palette_infrastructure.md for the full spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pygame


# ---------------------------------------------------------------------------
# MATERIAL BANDS — 7 bands, 29 entries total
# ---------------------------------------------------------------------------
#
# Each band: darkest → brightest. Phase 3 lighting lerps within a band;
# Phase 7 palette snap constrains material-pixel output to band entries.
# Values per Aesthetic Bible §2.2 — hand-tuned by the design team to
# produce legible banded lighting under the palette-snap pipeline.

MATERIAL_BANDS: dict[str, tuple[tuple[int, int, int], ...]] = {
    # Default hull metal — cool industrial steel
    "steel": (
        (24, 30, 42),  # steel_shadow_deep — ambient floor
        (52, 62, 82),  # steel_shadow
        (88, 100, 122),  # steel_base
        (140, 156, 188),  # steel_bright
        (190, 210, 238),  # steel_specular
    ),
    # Solari Chrome — polished mirror; forced-wide band per Spike 01/02/03
    # findings (naive narrow chrome collapses under palette-snap).
    "solari_chrome": (
        (82, 92, 108),  # solari_pewter — darker than "real" chrome for legibility
        (140, 152, 172),  # solari_dim
        (200, 212, 226),  # solari_base
        (232, 240, 248),  # solari_bright
        (252, 253, 255),  # solari_mirror
    ),
    # Crimson Iron — Reach hull, patinated red-brown, matte
    "reach_crimson": (
        (40, 10, 12),  # reach_shadow_deep
        (78, 22, 24),  # reach_shadow
        (138, 42, 40),  # reach_base
        (186, 78, 62),  # reach_bright
        (224, 128, 92),  # reach_specular — hue-shifts warm for rim glow
    ),
    # Union Ceramic — matte heat-tile, warm undertone
    "union_ceramic": (
        (78, 68, 58),  # union_shadow_deep
        (132, 118, 98),  # union_shadow
        (202, 192, 170),  # union_base
        (232, 222, 202),  # union_bright
        (248, 240, 222),  # union_specular
    ),
    # Frontier Canvas — welded patchwork, cooler / grittier
    "frontier_canvas": (
        (32, 26, 22),  # frontier_shadow_deep
        (62, 52, 44),  # frontier_shadow
        (108, 92, 72),  # frontier_base — oxidized brown
        (160, 142, 112),  # frontier_bright
        (208, 192, 158),  # frontier_specular — fresh weld tan
    ),
    # Collective Composite — science-clean blue-white
    "collective_composite": (
        (40, 52, 68),  # collective_shadow_deep
        (90, 108, 128),  # collective_shadow
        (168, 192, 212),  # collective_base
        (210, 228, 242),  # collective_bright
        (240, 248, 254),  # collective_specular
    ),
    # Glass Viewport — narrow 4-entry band by nature
    "glass_viewport": (
        (14, 28, 42),  # glass_shadow
        (30, 58, 80),  # glass_base_dim
        (52, 96, 126),  # glass_base
        (96, 146, 176),  # glass_bright
    ),
}


# ---------------------------------------------------------------------------
# PALETTE ROLES — 29 entries for non-material rendering
# ---------------------------------------------------------------------------
#
# Void/sky, emissive cores, UI chrome, detail colors. Disjoint from
# MATERIAL_BANDS: no RGB value appears in both. This invariant is
# enforced by test_tiers_are_disjoint.

PALETTE_ROLES: dict[str, tuple[int, int, int]] = {
    # Void / sky (3 entries)
    "void_deep": (8, 10, 17),
    "void_mid": (17, 20, 33),
    "void_light": (29, 36, 53),
    # Emissive cores (7 entries) — bypass snap; additive blend
    "plasma_core": (255, 175, 58),
    "plasma_hot": (255, 225, 180),
    "cryo_fractal": (127, 225, 255),
    "ion_arc": (198, 110, 255),
    "voltaic_strike": (255, 232, 108),
    "glow_warm": (255, 200, 120),
    "glow_cool": (108, 185, 255),
    # UI chrome (7 entries) — HUD layer
    "hud_cyan": (85, 207, 236),
    "hud_warning": (245, 145, 55),
    "hud_critical": (245, 65, 65),
    "hud_muted": (108, 119, 142),
    "hud_text": (225, 230, 240),
    "hud_text_dim": (160, 168, 185),
    "hud_accent_warm": (232, 180, 110),
    # Detail colors (4 entries)
    "rivet": (20, 23, 30),
    "rivet_gloss": (110, 128, 155),
    "seam": (14, 16, 22),
    "weld": (178, 148, 92),
    # Status roles (4 entries) — used by Colors.GREEN/RED/YELLOW/BLUE
    # wrappers. Values preserve the original Colors class literals exactly
    # so the Sprint 4 migration causes zero visual change.
    "status_success": (50, 200, 100),  # Colors.GREEN
    "status_critical": (220, 50, 50),  # Colors.RED
    "status_warning": (255, 200, 50),  # Colors.YELLOW
    "status_info": (80, 150, 255),  # Colors.BLUE
    # Skill check roles (3 entries) — gameplay feedback on social and
    # skill outcomes. Distinct from status roles so their remaps can be
    # tuned separately.
    "check_pass": (80, 220, 120),  # Colors.CHECK_PASS
    "check_marginal": (220, 200, 60),  # Colors.CHECK_MARGINAL
    "check_fail": (200, 80, 80),  # Colors.CHECK_FAIL
    # Quality tier roles (4 entries) — item quality grades.
    "quality_poor": (80, 80, 80),  # Colors.QUALITY_POOR
    "quality_normal": (140, 140, 140),  # Colors.QUALITY_NORMAL
    "quality_good": (100, 200, 100),  # Colors.QUALITY_GOOD
    "quality_excellent": (255, 220, 80),  # Colors.QUALITY_EXCELLENT
    # Text roles (3 entries) — ubiquitous foreground text colors used
    # across every view. Distinct from hud_text* (which targets the
    # persistent HUD overlay layer specifically).
    "text_primary": (220, 220, 230),  # Colors.TEXT_PRIMARY
    "text_secondary": (150, 160, 180),  # Colors.TEXT_SECONDARY
    "text_highlight": (100, 200, 255),  # Colors.TEXT_HIGHLIGHT
    # Faction primary roles (4 entries) — labels, emblems, indicators.
    "faction_commerce": (100, 150, 255),  # Colors.FACTION_COMMERCE
    "faction_miners": (200, 150, 50),  # Colors.FACTION_MINERS
    "faction_science": (150, 100, 200),  # Colors.FACTION_SCIENCE
    "faction_frontier": (100, 200, 100),  # Colors.FACTION_FRONTIER
    # Faction accent roles (4 entries) — brighter variants for active
    # borders and HUD highlights.
    "faction_accent_commerce": (80, 140, 220),
    "faction_accent_miners": (220, 170, 60),
    "faction_accent_science": (140, 170, 220),
    "faction_accent_frontier": (80, 200, 120),
    # Faction tint roles (4 entries) — dimmed variants for subtle panel
    # edge tints.
    "faction_tint_commerce": (40, 60, 100),
    "faction_tint_miners": (90, 70, 30),
    "faction_tint_science": (60, 50, 90),
    "faction_tint_frontier": (40, 80, 50),
}


# ---------------------------------------------------------------------------
# RESERVED_BAND_NAMES — future material-class names (Bible §9.1)
# ---------------------------------------------------------------------------
#
# These names are reserved for future band content. Not in MATERIAL_BANDS
# yet — they become real bands when their associated category expansion
# lands (radar, sensor, cooling, shield, voltaic-tech, cryo-tech).
#
# Consumer code should NOT reference these names via get_band yet; doing
# so raises KeyError, which is the intended guardrail. When the content
# phase adds them to MATERIAL_BANDS, consumers can start referencing
# them and this tuple becomes empty.

RESERVED_BAND_NAMES: tuple[str, ...] = (
    "sensor_glass",  # Translucent green-tint for radar/sensor domes
    "electronics_emissive",  # Targeting-computer window glow, sensor panels
    "cooling_vent",  # Textured metal with heat-gradient emissive
    "radar_mesh",  # Latticed reflective antenna surface
    "shield_field",  # Emissive shield lattice, cool blue-cyan family
    "voltaic_plate",  # Lightning-etched metal for voltaic-tech weapons
    "cryo_frost",  # Frost accumulation on cryo weapons and hulls
)


# ---------------------------------------------------------------------------
# ColorblindProfile — remap infrastructure (Bible §2.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ColorblindProfile:
    """A remap from canonical palette names to alternate names.

    Profiles change WHICH band or role the lookup resolves to; they do
    not change the underlying RGB data. An empty remap dict means every
    lookup falls through to canonical.

    v1 profiles ship as stubs with empty remaps. Populating them is a
    content pass requiring playtest calibration with colorblind users.
    See 95_palette_infrastructure.md §5.4.
    """

    id: str
    name: str
    description: str
    band_remap: dict[str, str] = field(default_factory=dict)
    role_remap: dict[str, str] = field(default_factory=dict)


# Starter profiles — pending playtest calibration (see §95 palette infra).
#
# These remaps apply the MINIMUM set of band/role substitutions that
# address the most common conflicts for each deficiency class. Values are
# directionally correct (swap the problem family for a luminance-distinct
# alternative from the same visual-weight tier) but are NOT playtest-
# calibrated with real colorblind users.
#
# A full accessibility pass is post-v1 per corpus coherence review §42.
# Until then, these give the colorblind settings real behavior — toggling
# the profile visibly changes the render — rather than shipping as no-op
# stubs that would mislead players into thinking a setting was active.

PROTANOPIA = ColorblindProfile(
    id="protanopia",
    name="Protanopia (red-blind)",
    description="Swaps red-family bands to warm-neutral alternatives. Red-blind players see reach_crimson as brown-gray; remapping to union_ceramic restores hue contrast against surrounding hull.",
    band_remap={
        # Crimson red-brown → warm ceramic (reads as distinct even without red cone)
        "reach_crimson": "union_ceramic",
    },
    role_remap={
        # Warning orange is dangerously close to plasma red for red-blind —
        # swap warning to HUD cyan which is unambiguous for them.
        "hud_warning": "hud_cyan",
        # Status/check reds read as brown-gray; swap to info blue so
        # failure/critical feedback stays unambiguous.
        "status_critical": "status_info",
        "check_fail": "status_info",
        # Miners Union orange reads too close to Frontier Alliance green's
        # warm component. Remap miners to Science Collective purple which
        # has a distinct luminance profile for red-blind viewers.
        "faction_miners": "faction_science",
    },
)

DEUTERANOPIA = ColorblindProfile(
    id="deuteranopia",
    name="Deuteranopia (green-blind)",
    description="Green-blind deficiency overlaps heavily with protanopia for red/green-family conflicts. Same remap shape, calibrated for the slightly different green-cone profile.",
    band_remap={
        "reach_crimson": "union_ceramic",
    },
    role_remap={
        "hud_warning": "hud_cyan",
        "status_critical": "status_info",
        "check_fail": "status_info",
        # Green-blind also loses green/green contrast. Remap success/pass
        # to cyan so positive feedback does not collide with chrome greens.
        "status_success": "hud_cyan",
        "check_pass": "hud_cyan",
        "quality_good": "hud_cyan",
        # Same faction concern as protanopia; orange miners → purple science.
        "faction_miners": "faction_science",
        # Frontier's green also loses contrast; remap to commerce blue so
        # factions stay visually separable (commerce already blue, but
        # luminance-distinct from frontier original).
        "faction_frontier": "faction_commerce",
    },
)

TRITANOPIA = ColorblindProfile(
    id="tritanopia",
    name="Tritanopia (blue-blind)",
    description="Blue-blind deficiency confuses blue/yellow channels. Remaps collective (blue-white) to solari_chrome so clean-tech materials stay distinct from warm hulls.",
    band_remap={
        # Blue-white composite → chrome (still cool but hue-neutral)
        "collective_composite": "solari_chrome",
        # Blue glass → steel band (both cool, but steel has richer luminance)
        "glass_viewport": "steel",
    },
    role_remap={
        # Cool glow becomes warm — blue-blind players see cool glows as desaturated
        "glow_cool": "glow_warm",
        # Blue-blind confuses yellow/blue channels. Swap info-blue to
        # success-green so informational highlights stay readable.
        "status_info": "status_success",
        # Commerce Guild blue reads as desaturated for blue-blind. Remap
        # to frontier green which holds hue for them.
        "faction_commerce": "faction_frontier",
    },
)

CANONICAL_PROFILES: dict[str, ColorblindProfile] = {
    PROTANOPIA.id: PROTANOPIA,
    DEUTERANOPIA.id: DEUTERANOPIA,
    TRITANOPIA.id: TRITANOPIA,
}


# Module-level active profile. Accessed only via set_colorblind_profile
# and get_active_profile — never mutated directly.
_active_profile: Optional[ColorblindProfile] = None


def set_colorblind_profile(profile: Optional[ColorblindProfile]) -> None:
    """Set (or clear) the active colorblind profile.

    When set, subsequent get_band and get_role calls apply the profile's
    remap tables. When None (default), canonical data is returned.

    Intended to be called from settings changes, not per-frame.
    """
    global _active_profile
    _active_profile = profile


def get_active_profile() -> Optional[ColorblindProfile]:
    """Return the currently active colorblind profile, or None."""
    return _active_profile


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def get_band(name: str) -> tuple[tuple[int, int, int], ...]:
    """Return the band stops for a named band.

    Respects the active colorblind profile: if the profile remaps this
    name, the remapped band is returned instead.

    Raises KeyError if the name (or its remapped alias) is not a valid
    band.
    """
    if _active_profile is not None:
        name = _active_profile.band_remap.get(name, name)
    return MATERIAL_BANDS[name]


def get_role(name: str) -> tuple[int, int, int]:
    """Return the RGB for a named palette role.

    Respects the active colorblind profile: if the profile remaps this
    name, the remapped role's RGB is returned.

    Raises KeyError if the name (or its remapped alias) is not valid.
    """
    if _active_profile is not None:
        name = _active_profile.role_remap.get(name, name)
    return PALETTE_ROLES[name]


def band_names() -> tuple[str, ...]:
    """Return all canonical band names in defined order."""
    return tuple(MATERIAL_BANDS.keys())


def role_names() -> tuple[str, ...]:
    """Return all canonical role names in defined order."""
    return tuple(PALETTE_ROLES.keys())


def is_valid_band(name: str) -> bool:
    """Return True if the name is a valid canonical band."""
    return name in MATERIAL_BANDS


def is_valid_role(name: str) -> bool:
    """Return True if the name is a valid canonical role."""
    return name in PALETTE_ROLES


# ---------------------------------------------------------------------------
# Snap / lerp helpers
# ---------------------------------------------------------------------------


def snap_to_band(
    color: tuple[int, int, int],
    band: tuple[tuple[int, int, int], ...],
) -> tuple[int, int, int]:
    """Snap an RGB color to the nearest entry in the given band.

    Uses sum-of-squared-RGB distance. When multiple entries are
    equidistant, the first in band order wins (stable selection).
    """
    best_entry = band[0]
    best_dist = _distance_sq(color, band[0])
    for entry in band[1:]:
        dist = _distance_sq(color, entry)
        if dist < best_dist:
            best_dist = dist
            best_entry = entry
    return best_entry


def snap_to_role(
    color: tuple[int, int, int],
    tolerance: float = 4.0,
) -> Optional[tuple[int, int, int]]:
    """Snap a UI color to the nearest PALETTE_ROLES entry within tolerance.

    Returns None if no role is within `tolerance` RGB units (Euclidean).
    Diagnostic signal — useful for palette audit tooling that wants to
    surface colors drifting off the role table.
    """
    best_entry: Optional[tuple[int, int, int]] = None
    best_dist_sq = float("inf")
    tolerance_sq = tolerance * tolerance
    for entry in PALETTE_ROLES.values():
        dist = _distance_sq(color, entry)
        if dist < best_dist_sq:
            best_dist_sq = dist
            best_entry = entry
    if best_entry is None:
        return None
    if best_dist_sq > tolerance_sq:
        return None
    return best_entry


def lerp_in_band(
    band: tuple[tuple[int, int, int], ...],
    factor: float,
) -> tuple[int, int, int]:
    """Interpolate a color within a band based on a 0..1 factor.

    Factor 0.0 returns band[0]; factor 1.0 returns band[-1]. Intermediate
    factors interpolate linearly between adjacent stops. Factor values
    outside [0, 1] clamp to the endpoints.
    """
    if len(band) == 0:
        return (0, 0, 0)
    if len(band) == 1:
        return band[0]
    f = max(0.0, min(1.0, factor))
    scaled = f * (len(band) - 1)
    lo = int(scaled)
    hi = min(lo + 1, len(band) - 1)
    blend = scaled - lo
    lo_c = band[lo]
    hi_c = band[hi]
    return (
        int(lo_c[0] + (hi_c[0] - lo_c[0]) * blend),
        int(lo_c[1] + (hi_c[1] - lo_c[1]) * blend),
        int(lo_c[2] + (hi_c[2] - lo_c[2]) * blend),
    )


# ---------------------------------------------------------------------------
# Category offset — band-index shift (Bible §3.3, Spike 02 Finding 4)
# ---------------------------------------------------------------------------


def apply_category_offset(
    band: tuple[tuple[int, int, int], ...],
    offset: int,
) -> tuple[tuple[int, int, int], ...]:
    """Return a band with entries shifted by `offset` indices.

    Positive offset = brighter bias (each index takes the entry `offset`
    stops brighter, clamping at band[-1]). Negative = darker bias
    (clamps at band[0]). Zero returns the band unchanged.

    Used for per-category variation: weapons offset=-1, structurals
    offset=+1. Band-index shift preserves palette discipline that RGB
    multiplication would break (Spike 02 Finding 4).
    """
    if offset == 0:
        return band
    max_idx = len(band) - 1
    return tuple(band[max(0, min(max_idx, i + offset))] for i in range(len(band)))


# ---------------------------------------------------------------------------
# Compliance test helpers (Bible §2.5)
# ---------------------------------------------------------------------------


def assert_band_compliance(
    surface: "pygame.Surface",
    band: tuple[tuple[int, int, int], ...],
    tolerance: float = 2.0,
) -> None:
    """Assert every opaque pixel in the surface is within `tolerance` of a band entry.

    Transparent pixels (alpha == 0) are ignored — they're not part of the
    rendered content.

    Tolerance defaults tight (2.0 RGB) because post-Phase-7 pixels should
    be exact band entries modulo rounding.

    Raises AssertionError with a diagnostic listing offending pixels.
    """
    tolerance_sq = tolerance * tolerance
    violations: list[tuple[int, int, tuple[int, int, int]]] = []
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            px = surface.get_at((x, y))
            if px.a == 0:
                continue
            rgb = (px.r, px.g, px.b)
            min_dist_sq = min(_distance_sq(rgb, entry) for entry in band)
            if min_dist_sq > tolerance_sq:
                violations.append((x, y, rgb))
    if violations:
        sample = violations[:5]
        raise AssertionError(
            f"{len(violations)} pixels not within {tolerance} of band. "
            f"Sample: {sample}. Band: {band}"
        )


def assert_role_compliance(
    surface: "pygame.Surface",
    tolerance: float = 4.0,
) -> None:
    """Assert every opaque pixel is within `tolerance` of any PALETTE_ROLES entry.

    Default tolerance is looser than band compliance to allow for
    antialiased UI edges.
    """
    tolerance_sq = tolerance * tolerance
    role_values = list(PALETTE_ROLES.values())
    violations: list[tuple[int, int, tuple[int, int, int]]] = []
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            px = surface.get_at((x, y))
            if px.a == 0:
                continue
            rgb = (px.r, px.g, px.b)
            min_dist_sq = min(_distance_sq(rgb, entry) for entry in role_values)
            if min_dist_sq > tolerance_sq:
                violations.append((x, y, rgb))
    if violations:
        sample = violations[:5]
        raise AssertionError(
            f"{len(violations)} pixels not within {tolerance} of any role. Sample: {sample}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _distance_sq(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
) -> int:
    """Euclidean distance squared between two RGB colors."""
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return dr * dr + dg * dg + db * db
