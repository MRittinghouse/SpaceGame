# ShipComposite API Specification

> **Status:** v1 — concrete implementation spec for the rebuilt `ShipComposite`. Written as a pre-implementation deliverable for **Framework §2 foundation work**, which blocks 5 downstream Tier 2 phases (Combat C4, Builder B1, Builder B5, Salvage S5, Station Hub H5).
>
> Inherits from `10_programmatic_generation_framework.md §2` (rebuild scope), `§4` (material system), `§6` (7-phase composition), `§15` (extensibility), `20_aesthetic_bible.md §2` (palette bands), `§6` (composition rules), `SPIKE_02_FINDINGS.md` (unified-object algorithm validation), and the prototype code in `tools/overhaul_spike/ship_render.py`.

---

## Table of Contents

1. Purpose and scope
2. Core data model
3. Public API surface
4. The 7-phase composition pipeline
5. Module state model
6. Render angles and rotation
7. Cache strategy and invalidation
8. Per-consumer integration patterns
9. Performance notes
10. Testing strategy
11. Implementation location and dependencies
12. Open questions and decisions

---

## 1. Purpose and scope

### 1.1 What ShipComposite is

A per-build renderer that produces a unified, palette-snapped, globally-lit pixel-art composite of an entire ship. One instance holds the rendered surface for one ship build at one or more angles, with caching and incremental state updates.

Replaces the existing `spacegame/engine/ship_composite.py` (484 lines, tile-stitch algorithm). The class name, per-instance pattern, and consumer-held-reference model are preserved; the internal algorithm is fundamentally new.

### 1.2 What it does not do

- **Does not own the build data.** Consumers pass a `ShipBuild` reference; the composite renders from it.
- **Does not render in world space.** It produces a `pygame.Surface`; positioning and camera transforms are consumer concerns (SceneCamera handles that).
- **Does not animate motion.** The engine-glow pulse and other emissive animations are handled internally; ship translation, rotation, and scaling in the scene are consumer territory.
- **Does not validate builds.** Physics constraints (structural integrity, center of mass) are model-layer concerns in `models/ship_build.py`.

### 1.3 Why this rebuild exists

The current implementation tiles module sprites edge-adjacent and sums them. Visible artifacts: module seams break the silhouette, lighting is per-module not global, materials don't share a coherent band. Spike 02 validated the unified-object algorithm (§6 of framework) as the fix. Implementation requires a fresh algorithm, not an extension.

### 1.4 Data model reconciliation note

**The production data model uses `PlacedPixel` (x, y, material_id) + `PlacedSlot` (slot_def_id, x, y, rotation, equipped_part_id), not `PlacedModule`.** This spec's "module" terminology maps to production concepts as follows:

- **PlacedSlot = "module" for state overrides.** When §5 says `set_module_state(module_id, DAMAGED)`, the implementation takes a stable slot identifier (e.g., `f"{slot_def_id}@{x},{y}"`) and applies the state to pixels within that slot's rotated bounding box.
- **PlacedPixel = rendering granularity.** Phases 1-7 operate on individual pixels; material_id lookups pull band + palette from each pixel's material.
- **Slot bounding box = "module region."** `get_module_rect(module_id)` returns the rotated footprint derived from the slot's `SlotDefinition`.
- **Hull pixels with no owning slot** still render (Phase 2 material fill); they contribute to the ship silhouette but can't be individually state-overridden.

This reconciliation preserves the existing `ShipBuild` / `models/ship_build.py` data model — no breaking changes to save format or build API. The composer adapts to what's there.

Five downstream phases consume this:

- **Combat C4** — player + all enemies render through this pipeline; damage states + module-targeting visualizations ride on it
- **Builder B1** — hero preview pane renders at 3 canonical angles
- **Builder B5** — test flight renders the build in motion
- **Salvage S5** — module recovery visualizes a single recovered module in isolation
- **Station Hub H5** — docked-ship corner glimpse reuses the player's composite

Shared infrastructure + shared cache = consistent identity across five systems.

---

## 2. Core data model

### 2.1 Enums

```python
from enum import Enum


class RenderAngle(Enum):
    """Canonical orthographic angles. Three supported in v1; arbitrary
    angles deferred to a future composer extension if needed.
    """
    FRONT = "front"            # Nose-on; narrow silhouette
    PROFILE = "profile"        # Side-on; full silhouette, landscape layout
    THREE_QUARTER = "three_quarter"  # Default; combat + preview default angle


class ModuleState(Enum):
    """Per-module visual state. Consumers override defaults per-module
    via set_module_state. Unset modules render as NORMAL.
    """
    NORMAL = "normal"
    HIGHLIGHTED = "highlighted"    # Targeting outline (combat, placement)
    DAMAGED = "damaged"            # <50% module HP — scorch overlay + subdued emissive
    CRITICAL = "critical"          # <25% module HP — heavy damage + smoke anchor
    DISABLED = "disabled"          # Offline but intact — tint only, no emissive
    DESTROYED = "destroyed"        # Severed — hole in silhouette, persistent marker
    RECOVERED = "recovered"        # Salvage preview mode — success tint + extraction flourish
    CORRUPTED = "corrupted"        # Salvage grid corruption — red-shift tint + static noise


class InvalidationScope(Enum):
    """Granularity of cache invalidation."""
    ALL = "all"                    # Full rebuild — build geometry changed
    STATE_ONLY = "state_only"      # Module states changed; base silhouette preserved
    WEAR_ONLY = "wear_only"        # Wear level changed; base + states preserved
    SCALE_CACHE = "scale_cache"    # Only the per-scale cache is discarded
```

### 2.2 Request types (standalone rendering)

For catalog previews, placement ghosts, and module-recovery cinematics, consumers need to render **individual modules** without a full ShipBuild context. These go through a free function, not the class.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleRenderRequest:
    """Standalone render request for a single module.

    Used by:
      - Ship builder catalog preview pane (§4.3 of builder doc)
      - Placement ghost during drag (§4.4 of builder doc)
      - Salvage module recovery cinematic (§4.7 of salvage doc)
    """
    module_id: str
    category: str                     # "cockpit", "engine", "weapon", "structural", ...
    manufacturer: str                 # Manufacturer ID (drives material + shape vocab)
    material_override: str | None = None  # Optional explicit material ID; otherwise derived from manufacturer
    faction_overlay: str | None = None
    state: ModuleState = ModuleState.NORMAL
    wear: float = 0.0                 # 0.0 (factory fresh) to 1.0 (battle-wrecked)
    rotation: int = 0                 # 0, 90, 180, 270 degrees
    flipped: bool = False             # Mirror-flip horizontally
    seed: int = 0                     # Deterministic variation seed
    scale: int = 1                    # Integer scale factor
```

### 2.3 Configuration type

Optional configuration when constructing a `ShipComposite`:

```python
@dataclass(frozen=True)
class ShipCompositeConfig:
    """Configuration tunables for ShipComposite rendering.

    Defaults produce the canonical Aurelia look; overrides support
    specific scene contexts.
    """
    angles_to_cache: tuple[RenderAngle, ...] = (RenderAngle.THREE_QUARTER,)
    emissive_pulse_hz: float = 0.83   # ~1.2s period; matches material §3.5 discipline
    enable_engine_glow: bool = True
    enable_wear_overlay: bool = True
    enable_rivets: bool = True
    enable_connection_detail: bool = True
    faction_overlay: str | None = None  # Applied ship-wide; individual modules override
    max_scale: int = 8                  # Upper bound on scale cache entries
```

---

## 3. Public API surface

### 3.1 Construction

```python
class ShipComposite:
    def __init__(
        self,
        build: "ShipBuild",
        config: ShipCompositeConfig | None = None,
    ) -> None:
        """Create a composite renderer bound to a build.

        The composite does not copy the build; consumers should call
        invalidate() when the build mutates (e.g., module placement).
        """
```

### 3.2 State management

```python
def set_module_state(self, module_id: str, state: ModuleState) -> None:
    """Override a single module's visual state. Triggers STATE_ONLY
    invalidation, which preserves the base silhouette and recomputes
    only the affected module region."""

def set_wear(self, wear: float) -> None:
    """Set ship-wide wear level (0.0-1.0). Triggers WEAR_ONLY invalidation."""

def set_faction_overlay(self, faction_id: str | None) -> None:
    """Apply or clear a faction color overlay. Triggers ALL invalidation
    because accent stripes and insignia re-route."""

def invalidate(
    self,
    scope: InvalidationScope = InvalidationScope.ALL,
    module_id: str | None = None,
) -> None:
    """Explicit cache invalidation. Pass module_id with STATE_ONLY to
    target a single module; otherwise the full state-overlay is rebuilt."""
```

### 3.3 Per-frame update

```python
def update(self, dt: float) -> None:
    """Advance emissive pulse phase by dt seconds. Call once per frame.

    Does not rebuild cached surfaces; emissive animation is applied at
    render time as a cheap overlay pass.
    """
```

### 3.4 Render access (the primary API)

```python
def get_surface(
    self,
    angle: RenderAngle = RenderAngle.THREE_QUARTER,
    scale: int = 1,
) -> pygame.Surface:
    """Return the composited ship surface for the requested angle + scale.

    If the (angle, scale, state_hash, wear, faction_overlay) combination
    is cached, returns the cached surface. Otherwise rebuilds synchronously.

    The returned surface includes the current emissive phase; successive
    calls within the same frame return byte-identical surfaces, but
    successive frames reflect emissive pulse advancement.
    """

def get_module_surface(self, module_id: str) -> pygame.Surface:
    """Return the surface for a single module in isolation, at its
    current state + wear.

    Used by Salvage S5 for module recovery cinematic (single module
    rendered at extraction cell). Uses the same 7-phase pipeline
    minus the silhouette-union step.
    """

def get_module_rect(
    self,
    module_id: str,
    angle: RenderAngle = RenderAngle.THREE_QUARTER,
) -> pygame.Rect:
    """Return the bounding rect of a module within the ship composite
    at the given angle. Used by Combat C4 module-targeting overlay
    (highlight, hit flash, damage tint, destruction marker).
    """
```

### 3.5 Batch / precompute operations

```python
def preload_angles(self) -> None:
    """Pre-render all angles configured in config.angles_to_cache.

    Builder B1 calls this after build confirmation so subsequent orbit
    cycling is instantaneous. Combat does not preload (uses only default
    angle).
    """

def preload_scales(self, scales: tuple[int, ...]) -> None:
    """Pre-render at the given integer scales. Station hub H5 calls this
    with (1, 2) to have both the tiny corner-glimpse scale and the
    normal-combat scale ready."""
```

### 3.6 State queries

```python
@property
def is_dirty(self) -> bool:
    """True if any pending invalidation has not yet been resolved."""

@property
def wear(self) -> float:
    """Current ship-wide wear level."""

@property
def cached_angles(self) -> tuple[RenderAngle, ...]:
    """Angles currently present in cache."""

def get_module_state(self, module_id: str) -> ModuleState:
    """Current state override for a module, or NORMAL if unset."""
```

### 3.7 Standalone module rendering (free function)

```python
def compose_standalone_module(
    request: ModuleRenderRequest,
) -> pygame.Surface:
    """Render a single module in isolation, outside any ShipComposite.

    Used by:
      - Builder catalog preview (hovering a module in the shop)
      - Placement ghost (drag preview before commit)
      - Salvage cell preview (showing a recoverable module in the grid)

    Does not cache. Each call renders from scratch. For repeated
    rendering of the same module (e.g., orbit animation in catalog
    preview), consumers should cache the result themselves.
    """
```

---

## 4. The 7-phase composition pipeline

Per Framework §6.2, composition is a strict ordered pipeline. Each phase has a distinct role; phases do not interleave.

### Phase 1 — Silhouette

Iterate over all `PlacedModule` entries. For each:
- Retrieve the module's shape mask (from `ModuleType.rasterize()` per Framework §15)
- Apply rotation (via numpy rot90 for 90° increments; scipy.ndimage.rotate for arbitrary, deferred)
- Translate to the module's build-grid position
- OR-union into the ship silhouette mask

**Output:** `silhouette_mask: np.ndarray[bool]` at ship-composite resolution.

Phase 1 is entirely deterministic. Result is cached per (build_geometry_hash, angle).

### Phase 2 — Per-module base fill

For each module:
- Look up material from manufacturer (`Bible §4.7 default pairings`) or explicit `material_override`
- Fill module cells with the material's band midpoint entry (index `len(band)//2`)
- Mask the fill to the silhouette (prevents overhangs)

**Output:** `base_surface: pygame.Surface` with palette-midpoint fills.

Deterministic; cached per (build_geometry_hash, materials_hash, angle).

### Phase 3 — Global lighting

The single canonical feature of the rebuild. One upper-right 45° directional light applied across the whole silhouette:

- Compute per-pixel lighting factor from the silhouette mask + light direction (dot product approximation; simple 2D lighting)
- For each lit pixel: lerp within its module's material band (index 0 = darkest shadow, index len-1 = brightest specular) based on the lighting factor
- Write the interpolated color back to the base surface

Light direction is a constant: `(+1, -1)` normalized (upper-right). Not parameterized.

**Output:** `lit_surface: pygame.Surface` with continuous RGB values (not yet palette-snapped).

Deterministic; cached per (silhouette_hash, materials_hash, angle).

### Phase 4 — Connection detail

For every pair of adjacent modules (sharing at least one edge pixel in the silhouette):
- Look up the connection kind from their shared connection points (Framework §15.3 `ConnectionKind`)
- Draw the seam treatment per the compatibility matrix:
  - `structural / structural` — thin dark line in `seam` palette role
  - `mount / mount` — bolted detail, visible bolts in `rivet` role
  - `power / power` — glowing line in `plasma_core` emissive role with animated pulse
  - `data / data` — thin cable in `hud_muted`
  - `coolant / coolant` — pipe in `glow_cool`
- Cross-manufacturer seams use the `weld` role rather than the owner's default

Connection detection uses the pre-computed pixel adjacency from Phase 1. Seam rendering is procedural.

**Output:** `lit_surface` with seams drawn in.

### Phase 5 — Decoration

Per-module decorations:
- **Rivets** via Poisson-disc sampling at `material.rivet_density`; rivets use band entry 0 (dark) for core + band entry len-1 (bright) for single-pixel gloss
- **Wear overlay** — larger-scale Simplex noise at `material.wear_intensity + instance_wear`, darkening toward band-entry-0 where noise peaks
- **Signature stripes** — per-manufacturer accent stripe in the manufacturer's accent role (Bible §4)
- **Faction insignia** — hand-authored sprite overlaid at a designated module if faction_overlay is set (Bible §4.8)

Seeded per module_id; deterministic given the seed.

**Output:** `detailed_surface` with Phases 1-5 composited.

### Phase 6 — Emissive

Emissive elements render as an **overlay** (additive blend) on top of the detailed surface:
- Engine module cores (glow_warm → plasma_core radial gradient)
- Cockpit windows (glass_viewport emissive if night / interior lighting)
- Weapon tech overlays (element-specific; plasma_core / ion_arc / cryo_fractal / voltaic_strike)
- Power coupling lines from Phase 4

Each emissive source pulses at `config.emissive_pulse_hz` with amplitude 15% of its peak intensity. Pulse phase is shared ship-wide (synchronized).

**Output:** `emissive_surface` — this is a separate Surface composited at render time (not baked in).

Emissive is the ONE phase that's not fully cached; it's applied at `get_surface()` call time so animation progresses.

### Phase 7 — Palette snap (material-band-constrained)

Non-emissive pixels snap to their material's band. Critical discipline from Spike 02 Finding 3: snap is **material-band-constrained**, not against the full palette.

For each opaque non-emissive pixel:
- Look up which module owns it (from Phase 1 module map)
- Find the nearest band entry within that module's material's `shade_band`
- Replace the pixel with the band entry

Emissive pixels bypass snap (Bible §3.5).

**Output:** `final_surface` — palette-compliant, ready for render.

### Pipeline caching (summary)

| Phase | Cached? | Cache key |
|---|---|---|
| 1 Silhouette | Yes | (build_geometry_hash, angle) |
| 2 Base fill | Yes | (geometry_hash, materials_hash, angle) |
| 3 Lighting | Yes | (silhouette_hash, materials_hash, angle) |
| 4 Connection | Yes | (adjacency_hash, connection_kinds_hash, angle) |
| 5 Decoration | Yes | (seed, wear, faction_overlay, angle) |
| 6 Emissive | **No** | (regenerated per frame at current pulse phase) |
| 7 Snap | Yes | (all prior + materials_hash) |

The final composite = Phases 1-5 + Phase 7 (all cached) + Phase 6 (per-frame overlay).

---

## 5. Module state model

### 5.1 State application in the pipeline

State overrides affect phases differently:

| Phase | NORMAL | HIGHLIGHTED | DAMAGED | CRITICAL | DISABLED | DESTROYED | RECOVERED | CORRUPTED |
|---|---|---|---|---|---|---|---|---|
| 1 Silhouette | include | include | include | include | include | **exclude** | include | include |
| 2 Base fill | normal | normal | scorched tint | heavy scorch | cool-tint | n/a | success tint | red-shift |
| 3 Lighting | normal | normal | normal | normal | reduced | n/a | normal | normal |
| 4 Connection | normal | normal | normal | normal | no-power-pulse | broken-stub | normal | static-distort |
| 5 Decoration | normal | **+ outline** | + smoke anchor | + heavy smoke | normal | + debris-ring | + particle-flourish | + noise |
| 6 Emissive | normal | normal | dim | very dim | **off** | **off** | brightened | flicker |
| 7 Snap | normal | normal | normal | normal | normal | n/a | normal | normal |

**Key behaviors:**

- **DESTROYED** excludes the module from Phase 1; the silhouette has a hole. Phase 4's seam rendering produces "broken stubs" at the severed connection points. Debris-ring particles are an overlay.
- **HIGHLIGHTED** adds a 2-pixel inset outline in `hud_warning` (pre-fire) or `hud_cyan` (selected); drawn in Phase 5 as a targeted decoration.
- **DISABLED** cuts emissive; a disabled reactor does not glow. The ship looks powered-down without looking destroyed.
- **RECOVERED** and **CORRUPTED** are salvage-specific; they tint and flourish but don't affect silhouette.

### 5.2 State-scoped invalidation

`STATE_ONLY` invalidation recomputes only the per-module state overlay layer. Phases 1-4 stay cached; phases 5-7 rerun for affected modules only (not the whole ship).

This matters for combat performance: damage events fire frequently (per hit). Full rebuilds per hit would stall the frame. State-only invalidation targets only the damaged module's region.

---

## 6. Render angles and rotation

### 6.1 The three canonical angles

| Angle | Usage | Silhouette character |
|---|---|---|
| `FRONT` | Rarely default; used for head-on beauty shots | Narrow, compact, symmetric |
| `PROFILE` | Default for combat and builder preview | Wide, landscape; primary "ship" read |
| `THREE_QUARTER` | Cinematic / hero moments | Moderate width with depth hint |

**The "three-quarter" interpretation is orthographic-with-rotation**, not perspective-3D. Modules are rasterized with their local 3/4 orientation; there's no perspective depth or actual 3D transform.

Most systems default to `THREE_QUARTER`. Combat Phase C4 may switch to `PROFILE` for some combat poses; this is deferred.

### 6.2 Per-module rotation (Framework §15)

Separate from render angle. Per-module rotation is the 90° increment a module can be placed in (e.g., a thruster facing right vs. left). Rotation is a `PlacedModule` data field; the composer applies it during Phase 1:

- 0° — default orientation
- 90°, 180°, 270° — rotated via numpy rot90 (cheap, deterministic, lossless)
- Arbitrary rotations (non-90° increments) — deferred; would require scipy.ndimage.rotate with aliasing

Connection-point metadata rotates with the module (per Framework §15.3). The connection compatibility matrix (Phase 4) still works because kinds are rotation-invariant.

### 6.3 Precomputing multiple angles

Builder B1 preview cycles three angles. The `preload_angles()` call renders and caches all three upfront (after build confirm), so the orbit animation is instantaneous.

Cost: ~3x the single-angle render cost, done once per build-state. Memory: 3 cached surfaces per build at each required scale.

---

## 7. Cache strategy and invalidation

### 7.1 Cache hierarchy

ShipComposite maintains a layered cache:

```
_phase_cache: dict[CacheKey, CachedSurface]  # Per-phase intermediate results
_final_cache: dict[FinalKey, pygame.Surface]  # Final composited (post-Phase-7)
_scale_cache: dict[ScaleKey, pygame.Surface]  # Scaled versions of final
```

Cache key includes:
- `build_geometry_hash` — hash of (module positions + rotations + flips)
- `materials_hash` — hash of (per-module material overrides)
- `states_hash` — hash of (per-module state overrides)
- `wear` — float rounded to 2 decimals
- `faction_overlay` — string or None
- `angle` — RenderAngle enum value

Cache size caps are per-scope:
- `_phase_cache`: up to 30 entries (LRU)
- `_final_cache`: up to 10 entries (LRU; typically just the current + recent)
- `_scale_cache`: up to `config.max_scale` entries

### 7.2 Invalidation scopes

| Scope | What's cleared | Use when |
|---|---|---|
| `ALL` | All caches | Build geometry changed (module added/removed/repositioned) |
| `STATE_ONLY` | Final cache + scale cache; per-module phase cache preserved | Module state changed (damage, highlight) |
| `WEAR_ONLY` | Final + scale; phases 1-4 preserved; phase 5 invalidated | Wear level changed |
| `SCALE_CACHE` | Only the scale cache | Rarely used; primarily internal |

`set_module_state(module_id, state)` calls `invalidate(STATE_ONLY, module_id)` internally. Explicit `invalidate()` is for consumer-initiated scenarios (e.g., "build was heavily modified externally, rebuild everything").

### 7.3 Emissive is not cached

Phase 6 emissive is a per-frame overlay. Cache only stores the Phase-1-through-5-plus-7 base; emissive is composited fresh in `get_surface()` using the current pulse phase from `update(dt)`.

---

## 8. Per-consumer integration patterns

How each of the 5 downstream phases consumes ShipComposite. Each references its Tier 2 phase doc for narrative context.

### 8.1 Combat C4 — unified runtime pipeline

- **Per-ship composite:** one `ShipComposite` instance per ship in combat (player + enemies)
- **State updates:** on damage events, call `set_module_state(module_id, DAMAGED)` or `CRITICAL`; on destruction, `DESTROYED`
- **Highlight:** on targeting, `set_module_state(module_id, HIGHLIGHTED)`; clear on target-change
- **Rendering:** `get_surface(angle=THREE_QUARTER, scale=combat_scale)` per frame
- **Module region overlays (for hit flash, damage tint):** query `get_module_rect(module_id, angle)` and composite overlays at those positions
- **Update cadence:** call `update(dt)` per frame for emissive pulse

### 8.2 Builder B1 — preview pane

- **Single composite:** the build-in-progress's composite
- **Preload 3 angles:** after each build modification, call `invalidate(ALL)` and then `preload_angles()` in a deferred task (don't block frame)
- **Angle cycling:** SceneCamera cycles through FRONT / PROFILE / THREE_QUARTER; renderer calls `get_surface(current_angle, preview_scale)`
- **Invalidation on placement:** every module placement calls `invalidate(ALL)`

### 8.3 Builder B5 — test flight

- **Reuses B1 composite:** no new instance; uses the builder's existing composite
- **Animation layer:** the test-flight view applies camera motion via SceneCamera; ShipComposite contributes only the composited surface
- **Emissive pulse:** `update(dt)` continues during test flight so engine cores pulse

### 8.4 Salvage S5 — module recovery cinematic

- **Standalone module rendering:** uses `compose_standalone_module(request)` for the cell-level preview (what the player sees in the salvage grid before extraction)
- **Post-recovery preview:** when the module is recovered, `compose_standalone_module` is called with `state=RECOVERED` for the cinematic "module lifts out of wreck" visual
- **No ShipComposite instance needed** for salvage grid cells; salvage renders individual modules

### 8.5 Station Hub H5 — docked-ship corner glimpse

- **Reuses player's existing composite:** accesses `player.ship.composite` directly
- **Small scale:** renders at scale=1 or scale=2 depending on resolution setting
- **Three-quarter angle:** uses the default cached angle
- **Low update cadence:** doesn't need per-frame update since the corner panel isn't animated; only updates if the ship's state changes (hull damage persisting from combat)

### 8.6 Common ownership pattern

```python
# In models/ship.py (simplified)
class Ship:
    def __init__(self, build: ShipBuild, ...):
        self.build = build
        self.composite: ShipComposite | None = None  # Lazy init
    
    def get_composite(self) -> ShipComposite:
        if self.composite is None or self.composite.is_dirty:
            self.composite = ShipComposite(self.build)
        return self.composite

# Consumer side
surface = player.ship.get_composite().get_surface()
```

This matches the existing pattern in `models/ship.py`; the rebuild preserves the ownership model.

---

## 9. Performance notes

### 9.1 Target frame budgets

Per Tier 2 doc success criteria:

| Context | Composite budget per frame | Notes |
|---|---|---|
| Combat (cached) | <0.5ms per ship | 6 ships × <0.5ms = 3ms; well within combat's 8ms total budget |
| Builder preview (cached) | <1ms | Single ship, ample budget |
| Builder preload (cold) | <80ms per angle | One-time cost after build confirm; acceptable |
| Station hub glimpse | <0.5ms | Cached |
| Salvage standalone | <20ms per module | Fire-and-forget during cinematic |

### 9.2 Cold-render cost

First render of a new build (no cache hit) runs all 7 phases:

- Phase 1 Silhouette: ~5-10ms for 6-module ship
- Phase 2 Base fill: ~3-5ms
- Phase 3 Lighting: ~10-15ms (numpy vectorized)
- Phase 4 Connection: ~2-4ms
- Phase 5 Decoration: ~5-10ms (Poisson-disc is the long pole)
- Phase 7 Snap: ~8-12ms

**Total cold render: ~33-56ms per ship-angle.** Acceptable for one-shot renders (after build confirm); never executed per-frame.

Phase 6 (emissive) at render time: ~0.3-0.8ms. This is the per-frame cost.

### 9.3 Memory per composite

- One cached final surface at default angle + scale: ~10-40KB depending on build size
- Three angles pre-loaded: ~30-120KB
- Phase cache intermediates: ~50-150KB

**Typical memory footprint: ~200KB per build.** For combat with 6 ships: ~1.2MB. Negligible.

### 9.4 Optimization levers if needed

If performance regressions surface (per risk register RT-1):

1. **Aggressive phase caching** — cache intermediate phases across builds with shared module subsets
2. **Lower-resolution internal render** — render at native, scale up; currently assumed
3. **Defer decoration to render time** — cheaper but breaks determinism
4. **Batch numpy operations** — already the default; profile to confirm

---

## 10. Testing strategy

### 10.1 Unit tests

In `tests/test_engine/test_ship_composite.py`:

```python
class TestShipCompositeConstruction:
    def test_empty_build_renders_transparent_surface(self): ...
    def test_single_module_build_renders_module(self): ...
    def test_is_dirty_true_before_first_render(self): ...

class TestPhasePipeline:
    def test_phase1_silhouette_union_matches_expected(self): ...
    def test_phase3_lighting_is_brighter_on_upper_right(self): ...
    def test_phase7_snap_produces_band_compliant_pixels(self): ...
    def test_destroyed_module_excluded_from_silhouette(self): ...

class TestStateOverrides:
    def test_set_module_state_triggers_state_only_invalidation(self): ...
    def test_highlighted_module_has_outline(self): ...
    def test_disabled_module_has_no_emissive(self): ...
    def test_destroyed_module_has_hole(self): ...

class TestRenderAngles:
    def test_preload_angles_caches_all_configured(self): ...
    def test_rotation_90_applied_before_lighting(self): ...
    def test_three_quarter_differs_from_profile(self): ...

class TestCaching:
    def test_repeated_get_surface_hits_cache(self): ...
    def test_build_change_invalidates_all(self): ...
    def test_state_change_invalidates_state_only(self): ...
    def test_cache_size_respects_max(self): ...

class TestStandaloneModule:
    def test_compose_standalone_module_renders_in_isolation(self): ...
    def test_standalone_respects_rotation(self): ...
    def test_standalone_respects_flip(self): ...

class TestDeterminism:
    def test_same_inputs_produce_byte_identical_output(self): ...
    def test_seed_controls_decoration_variation(self): ...

class TestPaletteCompliance:
    def test_all_non_emissive_pixels_in_material_band(self): ...
    def test_emissive_pixels_bypass_band_constraint(self): ...
```

### 10.2 Visual regression tests

Reference surfaces stored in `tests/visual_refs/ship_composite/`:

- `single_module_*.png` — each category rendered in isolation
- `six_module_ship_*.png` — representative full ship at each angle
- `damaged_state_*.png` — each state override
- `cross_manufacturer_*.png` — multi-manufacturer builds

CI test compares fresh renders to references at <2% pixel diff tolerance. Updates require explicit reference commit.

### 10.3 Integration tests

Against the actual consumer integrations:

```python
class TestCombatIntegration:
    def test_combat_sets_module_damaged_state_on_hit(self): ...
    def test_destruction_removes_module_from_silhouette(self): ...

class TestBuilderIntegration:
    def test_preload_angles_populates_cache(self): ...
    def test_placement_ghost_renders_standalone(self): ...
```

### 10.4 Spike evidence reuse

Spike 02 validated the unified-object algorithm. The prototype code at `tools/overhaul_spike/ship_render.py` serves as a reference implementation; production is not a direct port but inherits the algorithm.

Spike 03 validated palette band structure. The band-constrained snap in Phase 7 inherits Spike 03's findings.

---

## 11. Implementation location and dependencies

### 11.1 File layout

```
spacegame/engine/
  ship_composite.py               # REBUILD — this spec
  ship_composite_pipeline.py      # NEW — the 7-phase pipeline (internal)
  ship_composite_cache.py         # NEW — LRU cache implementation
  material_lookup.py              # NEW — band + role palette lookups

spacegame/data/ui/
  faction_insignia/*.png          # NEW — 5 hand-authored insignia
```

### 11.2 Python dependencies

- numpy (existing) for vectorized pixel operations
- pygame-ce (existing) for Surface management

No new external dependencies.

### 11.3 Existing modules consumed

- `models/ship_build.py` — `ShipBuild`, `PlacedModule` (used as-is; minor extensions for rotation + connection-point metadata per Framework §15)
- `engine/palettes.py` — palette band + role lookup (rebuilt per Bible §2)
- `engine/particles.py` — for destruction debris rings (STATE_ONLY state overlay)
- `data/ships/modules.json` — module catalog; needs rotation + connection-point metadata additions

### 11.4 Consumer-facing breaking changes

Per the alpha "be bold" stance (`feedback_alpha_no_backcompat.md`), the API changes freely without backward-compat scaffolding.

Changes from existing API:
- `get_surface(scale)` → `get_surface(angle, scale)` — angle parameter added
- New method: `set_module_state`, `set_wear`, `set_faction_overlay`
- New method: `get_module_surface`, `get_module_rect`, `preload_angles`
- New function: `compose_standalone_module` (module-level, not class method)
- Constructor: no longer takes `materials` dict (uses canonical palette lookup instead)

Consumer updates needed:
- Every `composite.get_surface(scale)` call adds the angle parameter (default works for most)
- Combat C4 adds state-override calls on damage events
- Builder B1 adds `preload_angles()` call on build change
- Salvage S5 uses new `compose_standalone_module()` function

### 11.5 Estimated effort

- Core rebuild (`ship_composite.py` + `ship_composite_pipeline.py` + `ship_composite_cache.py`): ~800-1000 lines
- `material_lookup.py`: ~100 lines
- Tests: ~600-800 lines
- Consumer integration updates (5 consumer phases): ~200 lines total

**Total for Framework §2 foundation work: ~2-3 weeks focused effort.** Longer than Combat C1 because the algorithm is more complex and 5 consumers need integration verification.

---

## 12. Open questions and decisions

### 12.1 Resolved during authoring

- **Class-based per-build instance pattern preserved**, not replaced with a module-level function. Caching and per-ship state are load-bearing; class is the right abstraction.
- **Standalone module rendering is a free function**, not a class method. Matches the "one-shot catalog preview" use case cleanly; no class overhead for non-persistent renders.
- **State overrides are per-module**, not per-pixel or per-cell. Spike 02 confirmed per-module granularity is sufficient for the visual effects required.
- **Emissive is not cached**. Per-frame overlay is cheap and the pulse animation demands it.
- **Phase 7 snap is material-band-constrained**, not against the full palette. Spike 02 Finding 3 validated this.

### 12.2 Deferred to implementation

- **Arbitrary-angle rotation** (non-90° increments). Deferred unless a specific production need surfaces. Current spec supports 0/90/180/270 only.
- **Runtime angle transitions.** Does the composite animate smoothly between angles, or does consumer handle angle interpolation via SceneCamera? v1 spec: **discrete angles** (consumer cross-fades externally via SceneCamera orbit). Confirm during Builder B1 integration.
- **Module-state transitions.** When a module goes from NORMAL to DAMAGED, should the visual transition be animated? v1: **instantaneous** (state-only invalidation, immediate re-render). Can add animation later if needed.
- **Cold-render on main thread vs. background.** First render of a new build takes ~50ms. Is this acceptable during gameplay? For combat, builds are pre-cached before combat starts. For builder, it happens after placement (frame-jitter acceptable). Deferred; will profile during C4 integration.

### 12.3 Future considerations (post-v1)

- **Procedural module templates** — currently shapes come from rasterize functions; a future expansion could load shape templates from JSON for content-team authoring
- **Damage heat maps** — visualize cumulative module damage history across a combat session
- **Wireframe / schematic view** — non-photoreal render mode for builder debugging

---

*Revision history:*
- *v1 — initial API specification for the Framework §2 foundation rebuild. Complete data model, public API, 7-phase pipeline detail, state model, cache strategy, per-consumer patterns, test strategy. Informed by Spike 02 (unified-object algorithm validation) and Spike 03 (palette bands).*
