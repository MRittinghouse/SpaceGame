# Palette & Material Band Infrastructure Specification

> **Status:** v1 — concrete implementation spec for the canonical palette + material band infrastructure per Aesthetic Bible §2 + §3. Written as a pre-implementation deliverable for the **third major foundation piece**, following SceneCamera (Combat C1) and ShipComposite (Framework §2).
>
> **Breaking-change session.** This spec commits to replacing `HullMaterial`'s `color_primary` / `color_accent` / `color_highlight` fields with `shade_band: str` + material parameters (rivet_density, wear_intensity, etc.). All 35 production materials migrate in this session. Per the alpha "be bold" stance, breaking changes are welcomed and no backward-compatibility scaffolding is added.
>
> Inherits from `20_aesthetic_bible.md §2` (palette canon), `§2.4` (colorblind modes), `§2.5` (compliance tests), `§3` (material library), `10_programmatic_generation_framework.md §4` (material schema), `94_ship_composite_api.md §1.4` (data-model reconciliation). Referenced by the ShipComposite implementation for band-aware snap.

---

## Table of Contents

1. Purpose and scope
2. Core data model
3. Public API surface
4. Material schema migration (breaking)
5. Colorblind remap architecture
6. Material reconciliation roadmap (35 → 10)
7. Per-consumer integration patterns
8. Performance notes
9. Testing strategy
10. Implementation location and dependencies
11. Open questions and decisions

---

## 1. Purpose and scope

### 1.1 What the palette infrastructure is

A **canonical data layer** providing every rendering system with authoritative access to Aurelia's 58 palette entries (29 material-band entries + 29 role entries), consumed by role name rather than raw RGB. Includes:

- Palette constants (the 58 entries themselves as Python data)
- Lookup APIs — `get_band(name)`, `get_role(name)`, `snap_to_band(color, band, tolerance)`
- Compliance test helpers — `assert_band_compliance()`, `assert_role_compliance()`
- Colorblind remap infrastructure — profiles + active-profile hook
- Material reconciliation discipline — canonical band assignments

### 1.2 What it replaces

- **`HullMaterial.color_primary` / `color_accent` / `color_highlight`** — replaced with `shade_band: str` naming a canonical band
- **`ship_composite.py::_derive_material_band` synthesis fallback** — superseded by direct band lookup; fallback removed once all materials are migrated
- **`engine/palettes.py`'s generic loader** — stays as a utility; a new module provides the canonical Aurelia palette

### 1.3 What it does not do

- **Does not redesign existing materials.** The reconciliation from 35 production materials to Bible §3's 10 canonical materials is a **separate follow-up phase** (§6 of this spec). This spec assigns each of the 35 materials to one of the 7 existing bands without collapsing them.
- **Does not ship colorblind content profiles.** The remap *API* lands in v1; actual `Protanopia`, `Deuteranopia`, `Tritanopia` profile content is deferred (requires playtest calibration with colorblind users).
- **Does not change rendering algorithms.** ShipComposite's pipeline stays as-is; it just swaps the band source from synthesis to canonical lookup.
- **Does not touch UI rendering.** UI chrome already uses palette roles per `42_ui_chrome_components.md`; the role table here just formalizes what UI consumes.

### 1.4 Why this rebuild exists

Three reasons the current state doesn't serve:

1. **Band synthesis drifts from intent.** `_derive_material_band(material)` synthesizes a 5-stop band via darken/lighten from `color_primary` + `color_highlight`. The resulting bands are approximations of Bible §2.2's hand-tuned canonical bands. Spike 03 validated that the canonical bands (especially Solari's widened luminance range) solve lighting issues that synthesis can't.

2. **No compliance enforcement.** Nothing currently asserts that rendered pixels actually land on palette entries. This is how palette drift creeps in silently.

3. **Colorblind modes impossible.** Remapping requires role-indexed lookups. With raw RGBs scattered in material data, a colorblind mode would need per-site changes everywhere. Band-indexed lookups mean one remap function updates the whole pipeline.

---

## 2. Core data model

### 2.1 The canonical palette constants

Defined in `spacegame/engine/material_palette.py` (new file). Values taken verbatim from Aesthetic Bible §2.2 + §2.3.

```python
# ---------------------------------------------------------------------------
# MATERIAL BANDS — 7 bands, 29 total entries
# Each band: darkest → brightest. Phase 3 lighting lerps within band.
# Phase 7 palette snap constrains material-pixel output to band entries only.
# ---------------------------------------------------------------------------

MATERIAL_BANDS: dict[str, tuple[tuple[int, int, int], ...]] = {
    # Default hull metal — cool industrial steel
    "steel": (
        (24, 30, 42),       # steel_shadow_deep
        (52, 62, 82),       # steel_shadow
        (88, 100, 122),     # steel_base
        (140, 156, 188),    # steel_bright
        (190, 210, 238),    # steel_specular
    ),

    # Solari Chrome — polished mirror; forced-wide band per Spike 01/02/03 findings
    "solari_chrome": (
        (82, 92, 108),      # solari_pewter
        (140, 152, 172),    # solari_dim
        (200, 212, 226),    # solari_base
        (232, 240, 248),    # solari_bright
        (252, 253, 255),    # solari_mirror
    ),

    # Crimson Iron — Reach hull, patinated red-brown, matte
    "reach_crimson": (
        (40, 10, 12),       # reach_shadow_deep
        (78, 22, 24),       # reach_shadow
        (138, 42, 40),      # reach_base
        (186, 78, 62),      # reach_bright
        (224, 128, 92),     # reach_specular (hue-shift warm for rim glow)
    ),

    # Union Ceramic — matte heat-tile, warm undertone
    "union_ceramic": (
        (78, 68, 58),       # union_shadow_deep
        (132, 118, 98),     # union_shadow
        (202, 192, 170),    # union_base
        (232, 222, 202),    # union_bright
        (248, 240, 222),    # union_specular
    ),

    # Frontier Canvas — welded patchwork, cooler/grittier
    "frontier_canvas": (
        (32, 26, 22),       # frontier_shadow_deep
        (62, 52, 44),       # frontier_shadow
        (108, 92, 72),      # frontier_base (oxidized brown)
        (160, 142, 112),    # frontier_bright
        (208, 192, 158),    # frontier_specular (fresh weld tan)
    ),

    # Collective Composite — science-clean blue-white
    "collective_composite": (
        (40, 52, 68),       # collective_shadow_deep
        (90, 108, 128),     # collective_shadow
        (168, 192, 212),    # collective_base
        (210, 228, 242),    # collective_bright
        (240, 248, 254),    # collective_specular
    ),

    # Glass Viewport — narrow 4-entry band by nature
    "glass_viewport": (
        (14, 28, 42),       # glass_shadow
        (30, 58, 80),       # glass_base_dim
        (52, 96, 126),      # glass_base
        (96, 146, 176),     # glass_bright
    ),
}


# ---------------------------------------------------------------------------
# PALETTE ROLES — 29 entries for non-material rendering
# Void/sky, emissive cores, UI chrome, details. Disjoint from MATERIAL_BANDS.
# ---------------------------------------------------------------------------

PALETTE_ROLES: dict[str, tuple[int, int, int]] = {
    # Void / sky (3 entries)
    "void_deep":        (8, 10, 17),
    "void_mid":         (17, 20, 33),
    "void_light":       (29, 36, 53),

    # Emissive cores (7 entries) — bypass snap; additive blend
    "plasma_core":      (255, 175, 58),
    "plasma_hot":       (255, 225, 180),
    "cryo_fractal":     (127, 225, 255),
    "ion_arc":          (198, 110, 255),
    "voltaic_strike":   (255, 232, 108),
    "glow_warm":        (255, 200, 120),
    "glow_cool":        (108, 185, 255),

    # UI chrome (7 entries) — HUD layer; disjoint from material bands
    "hud_cyan":         (85, 207, 236),
    "hud_warning":      (245, 145, 55),
    "hud_critical":     (245, 65, 65),
    "hud_muted":        (108, 119, 142),
    "hud_text":         (225, 230, 240),
    "hud_text_dim":     (160, 168, 185),
    "hud_accent_warm":  (232, 180, 110),

    # Detail colors (4 entries)
    "rivet":            (20, 23, 30),
    "rivet_gloss":      (110, 128, 155),
    "seam":             (14, 16, 22),
    "weld":             (178, 148, 92),

    # Fixtures, mood-overlay tinting (remaining 8 entries — reserved for
    # future expansion; currently empty slots per Bible §9.1)
    # "sensor_glass":     ...       # Future: radar dome material base
    # "electronics_emissive": ...   # Future: targeting-computer window glow
    # etc.
}
```

**Disjoint invariant:** A tuple that appears in any band entry never appears in the role table, and vice versa. Enforced by compliance test (§9.1).

### 2.2 Lookup helpers

```python
def get_band(name: str) -> tuple[tuple[int, int, int], ...]:
    """Return the band stops for a named band. Respects active colorblind
    profile (§5). Raises KeyError if name is not a valid band."""

def get_role(name: str) -> tuple[int, int, int]:
    """Return the RGB for a named palette role. Respects active colorblind
    profile. Raises KeyError if name is not a valid role."""

def band_names() -> tuple[str, ...]:
    """Return all canonical band names (in defined order)."""

def role_names() -> tuple[str, ...]:
    """Return all canonical role names (in defined order)."""

def is_valid_band(name: str) -> bool:
    """Check if a name is a valid band (without raising)."""

def is_valid_role(name: str) -> bool:
    """Check if a name is a valid role (without raising)."""
```

### 2.3 Snap helpers

```python
def snap_to_band(
    color: tuple[int, int, int],
    band: tuple[tuple[int, int, int], ...],
) -> tuple[int, int, int]:
    """Snap an RGB color to the nearest entry in the given band.

    Uses sum-of-squared-RGB distance. Replaces the nearest-entry lookup
    currently duplicated in ship_composite._phase7_palette_snap.
    """

def snap_to_role(
    color: tuple[int, int, int],
    tolerance: float = 4.0,
) -> Optional[tuple[int, int, int]]:
    """Snap a UI color to the nearest PALETTE_ROLES entry within tolerance.

    Returns None if no role is within tolerance (diagnostic signal — useful
    for palette audit tooling)."""

def lerp_in_band(
    band: tuple[tuple[int, int, int], ...],
    factor: float,
) -> tuple[int, int, int]:
    """Interpolate a color within a band based on a 0..1 factor.

    Replaces ship_composite._lerp_band_color (which stays as a thin wrapper).
    """
```

### 2.4 Offset helpers

```python
def apply_category_offset(
    band: tuple[tuple[int, int, int], ...],
    offset: int,
) -> tuple[tuple[int, int, int], ...]:
    """Return a rotated view of the band shifted by offset indices.

    Per Framework §4.1 Spike 02 Finding 4 — per-category variation uses
    band-index shift, not RGB multiplication. Positive offset = brighter
    bias (e.g., structurals). Negative = darker (e.g., weapons).

    Out-of-range shifts clamp to endpoints rather than wrapping.
    """
```

---

## 3. Public API surface

### 3.1 Module interface

```python
# spacegame/engine/material_palette.py

# Constants (see §2.1)
MATERIAL_BANDS: dict[str, tuple[tuple[int, int, int], ...]]
PALETTE_ROLES: dict[str, tuple[int, int, int]]

# Lookups (see §2.2)
def get_band(name: str) -> tuple[tuple[int, int, int], ...]: ...
def get_role(name: str) -> tuple[int, int, int]: ...
def band_names() -> tuple[str, ...]: ...
def role_names() -> tuple[str, ...]: ...
def is_valid_band(name: str) -> bool: ...
def is_valid_role(name: str) -> bool: ...

# Snap / lerp (see §2.3)
def snap_to_band(color, band) -> tuple[int, int, int]: ...
def snap_to_role(color, tolerance) -> Optional[tuple[int, int, int]]: ...
def lerp_in_band(band, factor) -> tuple[int, int, int]: ...

# Category offset (see §2.4)
def apply_category_offset(band, offset) -> tuple[tuple[int, int, int], ...]: ...

# Colorblind (see §5)
@dataclass(frozen=True)
class ColorblindProfile: ...
def set_colorblind_profile(profile: Optional[ColorblindProfile]) -> None: ...
def get_active_profile() -> Optional[ColorblindProfile]: ...

# Compliance (see §9)
def assert_band_compliance(surface, band, tolerance=2.0) -> None: ...
def assert_role_compliance(surface, tolerance=4.0) -> None: ...
```

### 3.2 Consumer usage pattern

```python
from spacegame.engine.material_palette import get_band, snap_to_band

# ShipComposite Phase 3:
band = get_band(material.shade_band)
color = lerp_in_band(band, lighting_factor)

# ShipComposite Phase 7:
snapped = snap_to_band(current_color, band)

# Trading UI:
text_color = get_role("hud_text")
warning_tint = get_role("hud_warning")
```

No raw RGB tuples appear in consumer code post-migration. Every color goes through a named lookup.

---

## 4. Material schema migration (breaking)

### 4.1 HullMaterial — before vs after

**Before** (current `models/ship_build.py`):

```python
@dataclass
class HullMaterial:
    id: str
    name: str
    description: str
    color_primary: tuple[int, int, int]
    color_accent: tuple[int, int, int] = (0, 0, 0)
    color_highlight: tuple[int, int, int] = (0, 0, 0)
    hull_per_pixel: float = 0.0
    armor_per_pixel: float = 0.0
    # ... (stats fields unchanged)
```

**After** (new `models/ship_build.py`):

```python
@dataclass
class HullMaterial:
    id: str
    name: str
    description: str
    shade_band: str                      # REQUIRED — palette band name (§2.1)
    category_offset: int = 0             # Band-index shift per Framework §4.1
    noise_intensity: float = 0.15        # Surface grain 0-1
    rivet_density: float = 40.0          # Rivets per 1000 px²
    wear_intensity: float = 0.10         # Baseline wear 0-1
    gloss: float = 0.30                  # Specular highlight strength 0-1
    emissive_role: Optional[str] = None  # PALETTE_ROLES key if emissive
    signature_stripe_role: Optional[str] = None  # Optional accent role
    hull_per_pixel: float = 0.0          # Unchanged (gameplay stats)
    armor_per_pixel: float = 0.0
    # ... (all other stats fields unchanged)
```

**What changes:**
- `color_primary` / `color_accent` / `color_highlight` → **removed**
- `shade_band` is a new **required** field (data migration assigns one per material)
- New optional fields for material rendering parameters that were previously heuristic substring matches in `ship_composite.py`
- `emissive_role` replaces the substring-match emissive identification
- Stats fields (`hull_per_pixel`, etc.) unchanged

**What stays:** Material `id`, `name`, `description`, all gameplay stats, all unlock metadata. Only the visual-rendering fields change.

### 4.2 JSON data migration

All 35 materials in `data/progression/*.json` (or wherever they're loaded from) need rewriting. Each gets:

- `shade_band` assigned to one of the 7 canonical bands (see §6 for assignment)
- `category_offset` set (default 0; specific values for weapons/structurals per Bible §3.3)
- `rivet_density`, `wear_intensity`, `noise_intensity`, `gloss` — migrated from `ship_composite.py`'s heuristic tables into explicit data

### 4.3 Consumer impact

Code touching HullMaterial that needs updating:

| Consumer | Current behavior | Post-migration |
|---|---|---|
| `ship_composite.py::_derive_material_band` | Synthesizes band from color_primary + color_highlight | Returns `get_band(material.shade_band)` with optional `apply_category_offset` |
| `ship_composite.py::_phase2_base_fill` | Uses `material.color_primary` | Uses `get_band(material.shade_band)[midpoint_index]` |
| `ship_composite.py::_emissive_color_for` | Substring match on material_id | Checks `material.emissive_role` |
| `ship_composite.py::_rivet_density_for` | Substring match on material_id | Reads `material.rivet_density` directly |
| Anywhere reading `material.color_primary` | Raw RGB | Resolve through `get_band(...)[midpoint]` or via new helper `material.primary_color` computed property |

Legacy ShipType material rendering (in `combat.py` per combat_balance_design.md §12) — already scheduled for deprecation; no new work needed here.

---

## 5. Colorblind remap architecture

Per Aesthetic Bible §2.4, colorblind modes remap bands and roles via a single profile rather than per-renderer changes.

### 5.1 ColorblindProfile dataclass

```python
@dataclass(frozen=True)
class ColorblindProfile:
    """A remap from canonical palette names to alternate names.

    Profiles change WHICH band/role the lookup resolves to, not the
    underlying RGB data. If a profile omits a mapping, the canonical
    entry is returned unchanged.
    """
    id: str                       # "protanopia", "deuteranopia", etc.
    name: str                     # Display name
    description: str
    band_remap: dict[str, str] = field(default_factory=dict)
    role_remap: dict[str, str] = field(default_factory=dict)
```

### 5.2 Active-profile API

```python
_active_profile: Optional[ColorblindProfile] = None


def set_colorblind_profile(profile: Optional[ColorblindProfile]) -> None:
    """Set (or clear) the active colorblind profile.

    When set, subsequent get_band / get_role lookups apply the profile's
    remapping. When None (default), canonical entries are returned.
    Should be called only at settings-change time; not per-frame.
    """

def get_active_profile() -> Optional[ColorblindProfile]:
    """Current active profile, or None if not set."""
```

### 5.3 Lookup implementation

```python
def get_band(name: str) -> tuple[tuple[int, int, int], ...]:
    if _active_profile is not None:
        name = _active_profile.band_remap.get(name, name)
    return MATERIAL_BANDS[name]

def get_role(name: str) -> tuple[int, int, int]:
    if _active_profile is not None:
        name = _active_profile.role_remap.get(name, name)
    return PALETTE_ROLES[name]
```

Remaps chain through the same constant data — no alternate RGB tables required. Profile defines which name maps to which.

### 5.4 v1 profile content (deferred)

Three empty profile stubs ship with the infrastructure:

```python
PROTANOPIA = ColorblindProfile(
    id="protanopia",
    name="Protanopia (red-blind)",
    description="Remaps red-family bands to higher-contrast alternatives.",
    band_remap={},   # TODO: populate per playtest calibration
    role_remap={},   # TODO: populate per playtest calibration
)

DEUTERANOPIA = ColorblindProfile(
    id="deuteranopia",
    name="Deuteranopia (green-blind)",
    description="Remaps green-family bands to higher-contrast alternatives.",
    band_remap={},
    role_remap={},
)

TRITANOPIA = ColorblindProfile(
    id="tritanopia",
    name="Tritanopia (blue-blind)",
    description="Remaps blue-family bands to higher-contrast alternatives.",
    band_remap={},
    role_remap={},
)
```

Populating the remap dicts is a **content pass** requiring:
- Playtesting with colorblind users
- Perceptual testing with simulated vision profiles
- Consideration of remaps that alter game-critical state reads (danger tier, faction rep)

Deferred to a future "Accessibility Content Pass." The infrastructure here ensures the remap works once the content lands.

### 5.5 UI settings hook

A settings toggle in the player options (deferred UI work — part of `42_ui_chrome_components.md` accessibility §10) calls `set_colorblind_profile` on change. The renderers below it require no changes; the lookup redirects automatically.

---

## 6. Material reconciliation roadmap

### 6.1 Context

Bible §3 commits to **10 canonical materials**:
`brushed_steel`, `solari_chrome`, `crimson_iron`, `union_ceramic`, `frontier_canvas`, `collective_composite`, `glass_viewport`, `plasma_energy`, `cryo_fractal`, `ion_field`.

Production currently has **35 materials** — a historical accumulation across phases. Each renders fine; together they're more diverse than Bible intends.

### 6.2 What this spec does NOT do

It does not collapse 35 → 10. That reconciliation is a **dedicated content phase** covering:

- Playtest the current 35 to identify which are gameplay-essential vs. visual-redundant
- Design a migration table: which production materials map to which Bible canonical
- Update all save data (in alpha, just wipe per the feedback memory) and module data references
- Visual regression against representative builds
- Player-communication if any named materials get renamed

Estimated scope: ~1-2 weeks of content work + playtest + migration.

### 6.3 What this spec DOES do

Assigns each of the 35 production materials to one of the 7 **existing bands** (per §2.1). This is a partial migration — materials keep their names + gameplay stats, but share a canonical band with siblings. The result:

- All rendering goes through canonical bands (discipline enforced)
- Materials with the same band render visually similar (which may be desired or undesired depending on the material)
- Playtest data from the fully-banded ship renders informs the 35→10 reconciliation scope

### 6.4 Migration table (assignments)

Proposed shade_band assignment for production's 35 materials:

| Production material (examples) | Canonical band |
|---|---|
| `hull_cold`, `light_alloy`, `standard_plate`, `module_hull_rk` | `steel` |
| `heavy_armor`, `reinforced_plate`, `module_hull_foundry` | `union_ceramic` |
| `module_hull_talon`, `module_hull_meridian` | `solari_chrome` |
| `module_hull_sable` | `collective_composite` |
| `crimson_steel`, `module_hull_crimson` | `reach_crimson` |
| `salvage_scrap`, `module_hull_salvage` | `frontier_canvas` |
| `cockpit_glass` | `glass_viewport` |
| `exhaust_port`, `plasma_core`, `reactor_core` | *emissive_role* set, no band (emissive materials) |
| `shield_crystal`, `quantum_lattice`, `shield_emitter` | `collective_composite` + emissive_role cryo_fractal or ion_arc |
| `bio_hull` | `frontier_canvas` (organic, matching patchwork voice) |
| `legendary_hull`, `legendary_core` | `solari_chrome` + emissive_role (ion_arc or voltaic_strike) |
| `void_material`, `phantom_material` | `collective_composite` + custom treatment (future work) |
| `weapon_barrel`, `sensor_dish`, `console_panel` | `steel` with category_offset |
| `cargo_interior`, `crew_quarters_interior` | `steel` (neutral interior) |

Final assignments confirmed during implementation via per-material review. Expect ~5 edge cases requiring discussion.

### 6.5 Future reconciliation phase — placeholder

When the 35 → 10 reconciliation phase runs, the work is:

1. **Audit current 35 for actual gameplay distinctness.** Many materials have identical stats; those are visual-only variants safe to collapse.
2. **Design the canonical 10 instances** from Bible §3.2 (material library table with specific parameter values).
3. **Map each of the 35 to one of the 10.** Breaking rename for some; merge for others.
4. **Data migration** in `data/progression/ship_materials.json` (or wherever loaded).
5. **Module data updates** — any `material_map` in `data/ships/modules.json` pointing to collapsed names gets rewritten.
6. **Playtest pass** — does the 10-material world feel impoverished? If so, revisit canonical count.

Tracked in `requirements/overhaul/93_risk_register.md` as a known future phase.

---

## 7. Per-consumer integration patterns

### 7.1 ShipComposite (primary consumer)

**Phase 3 (lighting):**
```python
band = get_band(material.shade_band)
if material.category_offset:
    band = apply_category_offset(band, material.category_offset)
color = lerp_in_band(band, lighting_factor)
```

**Phase 7 (snap):**
```python
band = get_band(material.shade_band)
snapped = snap_to_band(current_color, band)
```

**Phase 6 (emissive):**
```python
if material.emissive_role:
    emissive_color = get_role(material.emissive_role)
    # Apply per-pixel additive blend with pulse
```

`ship_composite._derive_material_band` becomes a thin wrapper (for the current fallback path) and is deprecated. `_EMISSIVE_MATERIAL_RULES` and `_RIVET_DENSITY_RULES` substring tables get **removed** — all data now on the material itself.

### 7.2 UI chrome (`engine/draw_utils.py`, views)

Any view or chrome function that takes a color should accept a role name or call `get_role(...)`. Example:

```python
from spacegame.engine.material_palette import get_role

# Old
text_color = (255, 230, 100)  # hand-tuned

# New
text_color = get_role("hud_warning")
```

No mass rewrite of existing views in this spec — ongoing migration via audit. New UI code uses roles from day one.

### 7.3 Particles (`engine/particles.py` + `*_vfx.py`)

Particle configs currently hold raw RGB color tuples. Migration is additive — particle presets can optionally declare roles:

```python
SPARK_BURST = ParticleConfig(
    start_color=get_role("plasma_core"),
    end_color=get_role("glow_warm"),
    ...
)
```

Similar pattern: particle configs updated opportunistically; new ones use roles.

### 7.4 Backgrounds and scene overlays

Star colors, nebula tints, vignette colors, mood overlays — all should resolve through `get_role`. Per Bible §8, scene mood overlays are themselves role-referenced.

### 7.5 Audit task

A grep-and-migrate audit (per `92_code_touch_map.md` §6.5):

```
rg '\([0-9]+,\s*[0-9]+,\s*[0-9]+\)' spacegame/ --type py
```

Identifies raw RGB tuples in code. Each hit is either:
- Legitimate (test data, default values in helpers)
- Migration candidate (should use `get_role`)

Audit runs during palette-infrastructure implementation. Not all hits migrate this session; the audit produces a backlog.

---

## 8. Performance notes

### 8.1 Lookup cost

- `get_band(name)` — dict lookup, O(1). With active profile, additional dict lookup, still O(1).
- `get_role(name)` — same O(1) pattern.
- `snap_to_band(color, band)` — O(band_size). Bands are 4-5 entries, so 4-5 comparisons per call.
- `lerp_in_band(band, factor)` — O(1) constant math.

### 8.2 Caching

None required. The data is small, lookups are trivially fast, and the hot path (Phase 7 snap) already iterates every pixel. Adding a lookup per pixel is cheap.

### 8.3 Memory

The 58-entry palette is ~0.5KB of Python data. Colorblind profiles are dict-of-strings, negligible. No performance consideration.

---

## 9. Testing strategy

### 9.1 Unit tests

`tests/test_engine/test_material_palette.py`:

```python
class TestPaletteConstants:
    def test_material_bands_count(self): ...        # 7 bands
    def test_material_bands_total_entries(self): ...  # 29 entries
    def test_palette_roles_count(self): ...          # 29 entries  
    def test_disjoint_tiers(self):                    # No RGB in both band and role
    def test_all_bands_monotonic_brightness(self): ...
    def test_all_bands_5_stops_except_glass(self): ...

class TestLookups:
    def test_get_band_returns_tuple(self): ...
    def test_get_band_unknown_raises(self): ...
    def test_get_role_returns_rgb(self): ...
    def test_is_valid_band_true_for_known(self): ...
    def test_is_valid_band_false_for_unknown(self): ...

class TestSnap:
    def test_snap_to_band_nearest(self): ...
    def test_snap_to_band_exact(self): ...
    def test_snap_to_role_within_tolerance(self): ...
    def test_snap_to_role_returns_none_if_outside(self): ...

class TestLerp:
    def test_lerp_factor_zero(self): ...
    def test_lerp_factor_one(self): ...
    def test_lerp_midpoint_hits_middle_stop(self): ...
    def test_lerp_clamps_below_zero(self): ...
    def test_lerp_clamps_above_one(self): ...

class TestCategoryOffset:
    def test_offset_zero_returns_band_unchanged(self): ...
    def test_offset_positive_shifts_brighter(self): ...
    def test_offset_negative_shifts_darker(self): ...
    def test_offset_clamps_at_endpoints(self): ...

class TestColorblind:
    def test_no_profile_returns_canonical(self): ...
    def test_profile_band_remap_applied(self): ...
    def test_profile_role_remap_applied(self): ...
    def test_profile_missing_mapping_falls_through(self): ...
    def test_set_profile_none_clears(self): ...

class TestCompliance:
    def test_assert_band_compliance_passes_on_exact(self): ...
    def test_assert_band_compliance_fails_on_mismatch(self): ...
    def test_assert_band_compliance_tolerance_respected(self): ...
    def test_assert_role_compliance_passes_on_roles(self): ...
```

Target: 30-40 tests.

### 9.2 Integration tests

Two integration test types:

**1. HullMaterial migration integrity** — `tests/test_models/test_ship_build_material.py` extended:

```python
class TestHullMaterialMigration:
    def test_shade_band_is_required(self): ...
    def test_shade_band_must_be_valid_band_name(self): ...
    def test_color_fields_removed(self): ...
```

**2. ShipComposite band-aware rendering** — `tests/test_engine/test_ship_composite.py` extended:

```python
class TestShipCompositeBandIntegration:
    def test_phase_3_uses_canonical_band(self): ...  # verify lit colors land on band
    def test_phase_7_snaps_to_shade_band(self): ...
    def test_different_bands_produce_different_output(self): ...
    def test_emissive_role_drives_phase_6(self): ...
```

### 9.3 Compliance test harness

`assert_band_compliance` and `assert_role_compliance` become part of the CI toolkit — used by ShipComposite tests and (later) visual regression tests.

```python
def assert_band_compliance(surface, band, tolerance=2.0):
    """Every opaque pixel within `tolerance` of a band entry."""

def assert_role_compliance(surface, tolerance=4.0):
    """Every opaque pixel within `tolerance` of any role entry."""
```

### 9.4 Data migration tests

Every existing material's JSON gets a test that it has a valid `shade_band`. Automated via data-loader tests.

---

## 10. Implementation location and dependencies

### 10.1 New files

```
spacegame/engine/material_palette.py        # ~400 lines (this spec's implementation)
tests/test_engine/test_material_palette.py  # ~400 lines (tests)
```

### 10.2 Modified files

```
spacegame/models/ship_build.py              # HullMaterial breaking change
spacegame/engine/ship_composite.py          # Consume canonical bands; remove synthesis
data/progression/ship_materials.json        # Add shade_band to all 35 materials
                                            # (filename assumed; verify during implementation)
```

### 10.3 Dependencies

- **Depends on:** existing `models/ship_build.py` structure, `engine/ship_composite.py`, Bible §2 palette canon
- **Blocks:** UI Chrome foundation (§4.4 of `92_code_touch_map.md`), Audio orchestration (indirectly, via audit patterns)
- **Parallelizable with:** any non-rendering Tier 2 phase (Mining M3+, Salvage S3+ content authoring)

### 10.4 No new external dependencies

Uses only stdlib. `numpy` for vectorized snap operations if needed; already present.

### 10.5 Python module layout

```python
# material_palette.py structure
"""Canonical palette + material band infrastructure."""

# Imports
from dataclasses import dataclass, field
from typing import Optional

# Constants (§2.1)
MATERIAL_BANDS = {...}
PALETTE_ROLES = {...}

# ColorblindProfile dataclass (§5)
@dataclass(frozen=True)
class ColorblindProfile: ...

# Canonical profiles (§5.4) — empty stubs
PROTANOPIA = ColorblindProfile(...)
DEUTERANOPIA = ColorblindProfile(...)
TRITANOPIA = ColorblindProfile(...)
CANONICAL_PROFILES: dict[str, ColorblindProfile] = {...}

# Module-level active profile state
_active_profile: Optional[ColorblindProfile] = None

# Lookups (§2.2)
def get_band(name): ...
def get_role(name): ...
def band_names(): ...
def role_names(): ...
def is_valid_band(name): ...
def is_valid_role(name): ...

# Snap / lerp (§2.3)
def snap_to_band(color, band): ...
def snap_to_role(color, tolerance=4.0): ...
def lerp_in_band(band, factor): ...

# Category offset (§2.4)
def apply_category_offset(band, offset): ...

# Colorblind control (§5)
def set_colorblind_profile(profile): ...
def get_active_profile(): ...

# Compliance (§9.3)
def assert_band_compliance(surface, band, tolerance=2.0): ...
def assert_role_compliance(surface, tolerance=4.0): ...
```

---

## 11. Open questions and decisions

### 11.1 Resolved during authoring

- **Breaking change (Option A)** — confirmed per user direction; no backward-compat scaffolding.
- **Colorblind hooks in v1** — confirmed; content profiles deferred.
- **Material reconciliation** — separate phase, scoped in §6.5; this spec doesn't collapse 35 → 10.
- **Band-index shift (not RGB multiplication) for category_offset** — aligns with Spike 02 Finding 4.
- **Compliance test tolerance** — 2.0 RGB for bands (tight, post-snap should be exact), 4.0 RGB for roles (allows antialiasing).

### 11.2 Deferred to implementation

- **Exact shade_band assignment for 5-8 edge-case materials** (void_material, phantom_material, legendary variants) — worked out during JSON migration.
- **Whether `emissive_role` materials need a `shade_band` at all** — for pure emissive (plasma_core, exhaust_port), the band may be unused. v1: band is still required, but the composite never queries it for emissive pixels (Phase 7 skips them).
- **Category offset defaults** — weapons = -1, structurals = +1 per Bible §3.3. Whether these are applied automatically based on a material's category association or explicitly set per material: v1 goes explicit (simpler).

### 11.3 Future considerations (post-v1)

- **Band expansion** — adding a new band (e.g., `voltaic_plate` per Bible §9.1 reserved naming space) is additive; no breaking change.
- **Role expansion** — same.
- **Per-scene palette variants** — Bible §8 scene mood overlays. Could eventually be their own remap layer on top of colorblind. Out of scope now.
- **Runtime palette edits** — for debugging or player customization. Not currently supported; bands/roles are constants.

---

## 12. Estimated effort

| Work item | Estimate |
|---|---|
| Spec authoring (this doc) | 1 session ✓ |
| `material_palette.py` implementation + tests | 1-2 sessions |
| HullMaterial breaking change + data migration | 1 session |
| ShipComposite integration update | 1 session |
| 35-material JSON migration | 1 session |
| Compliance test integration into CI | ~2 hours |
| **Total for v1 (infrastructure + band assignments):** | **~5-6 sessions** |

After v1 ships:
- Colorblind profile content pass: 1-2 weeks (playtesting dependency)
- 35 → 10 material reconciliation: 1-2 weeks (content + playtest)

---

*Revision history:*
- *v1 — initial spec. Breaking change (Option A) per user direction. Colorblind hooks included in v1 API; content deferred. Material reconciliation from 35 to Bible's 10 canonical called out as separate future phase (§6.5). Palette values taken verbatim from Aesthetic Bible §2.2 + §2.3.*
- *v1.1 — post-implementation correction. Bible summary arithmetic claimed "29 band entries + 29 role entries = 58 total" but actual band definitions sum to 34 (6 bands × 5 stops + glass_viewport × 4). Canonical counts are now **34 band entries + 21 live role entries = 55 total**, plus 7 reserved future-band names (§9.1) kept as a separate `RESERVED_BAND_NAMES` tuple. Reserved names raise KeyError on lookup — intended guardrail to force content-phase arrival before consumer code depends on them.*
