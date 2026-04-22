# Programmatic Generation Framework

> **Status:** DESIGN — v1 (post Spike 01 + Spike 02 revisions). Prototype-phase spikes continue to validate and revise.
>
> Defines the creative discipline of generating visual assets from code. Establishes primitive vocabulary, material system, lighting model, composition rules, and variation strategies. Sits under `00_master_plan.md`; every downstream Tier 2 overhaul doc inherits from here.
>
> **Revision history:**
> - v0 — initial draft, pre-prototype.
> - v0.1 — Spike 01 findings: palette-snap declared default rendering mode (§5.1.1).
> - v1 — Spike 02 findings: material sub-palettes (§4, §8), rotation in `ship_composite.py` rebuild scope (§2), directional-lighting test split (§10), connection validation flagged as gameplay-layer concern.
> - v1.1 — Extensibility section added (§15): registry-based `ModuleCategory`, `CategoryProfile`, silhouette-role, typed `ConnectionKind`. Forward-looking; no implementation impact on current spikes.

---

## 1. Purpose

The game's look must be **producible at scale by a solo developer + AI coding agent**, with the production ceiling high enough to credibly read as modern and intentional. We cannot rely on AI image generation (audience rejection), and hand-authoring every asset is not compatible with the scope we've committed to. The answer is programmatic generation elevated from a fallback to a primary creative medium — with its own maturity model, tooling, and quality standards.

This framework is the set of constraints and capabilities that make that possible.

### The governing aesthetic position

**Programmatic generation done well reads as a stylistic choice, not a technical compromise.** Hyper Light Drifter (hand-pixel-art-disciplined), Mini Metro (geometric primitives with obsessive polish), Thomas Was Alone (pure rectangles carrying narrative), and Downwell (palette-constrained procedural rooms) all demonstrate the ceiling. The player never thinks "this game couldn't afford art" — they think "this game has a visual signature."

Our target is that signature.

---

## 2. Existing Code Triage

Before designing new systems, an honest audit of what exists. The master plan asked us to be critical about refactor-vs-rebuild without unnecessary deference to legacy.

| File | Purpose | Lines | Triage Decision | Rationale |
|------|---------|-------|-----------------|-----------|
| `engine/procedural.py` | Procedural surface generator with caching | 335 | **EXPAND** | Solid foundation. Adding material system + lighting model will more than double its size but preserves the cache architecture. |
| `engine/ship_composite.py` | Composes placed modules into a ship image | 484 | **REBUILD** | Core to the most-visible visual offender (ship builder). Current impl stitches sprite tiles; we need a renderer that treats the ship as a *unified lit object*. Migration cost bounded — single file, well-contained. |
| `engine/particles.py` | Particle pool with preset configurations | 610 | **EXPAND** | Architecture is sound (object pooling, config presets). Needs richer vocabulary (see `41_vfx_particle_vocabulary.md` — Tier 3). |
| `engine/backgrounds.py` | Animated starfield backgrounds | 122 | **EXPAND** | Underbuilt for the scale reverence we want. Needs parallax depth, nebula fields, atmospheric fog. |
| `engine/screen_effects.py` | Full-screen effects (dim/flash/shake) | 90 | **REBUILD AS `post_processing.py`** | Only 90 lines. Small footprint. Better to rebuild with a proper pipeline (pre-composite → shader chain → composite) than to bolt onto the current `screen_effects` primitives. |
| `engine/sprites.py` | Sprite loading/caching | - | **KEEP** | Orthogonal to procedural generation. Coexists. |
| `engine/draw_utils.py` | Small drawing helpers | - | **EXPAND** | Additions as new primitives land. No structural change. |
| `engine/combat_vfx.py`, `mining_vfx.py`, `salvage_vfx.py`, `refining_vfx.py` | Per-system effects | - | **EXPAND** | Each per-system overhaul doc will extend these as needed. |
| `engine/palettes.py` | Color palettes incl. colorblind modes | - | **REBUILD** | Current palette system predates the aesthetic direction. New palette definition drives the entire pipeline; worth a clean rebuild informed by the Aesthetic Bible. |
| `engine/projectiles.py` | Projectile rendering | - | **EXPAND** | Gains elemental signature effects. |
| `engine/easing.py` | Ease curves | - | **KEEP** | Well-scoped utility. |

**Total rebuild footprint: ~2 files, ~575 lines.** Everything else is expansion of what exists. This is a meaningful but bounded rebuild.

**Justification for the rebuilds:**

1. **`ship_composite.py` → rebuild:** the current composite treats modules as tiles and stitches them. We need a renderer that (a) renders each module with baked lighting and material, (b) computes the ship's silhouette as a union, (c) re-lights the unified ship for consistent illumination, (d) adds composition-level detail (seams, glow lines), (e) **supports per-module rotation** (90° increments minimum; arbitrary for radial modules) with connection-point metadata that rotates with the module. This is a fundamentally different algorithm, not an extension. Rebuilding produces ~600-800 lines of code tightly scoped to the new design (rotation adds ~200 lines over the base estimate per Spike 02 finding); refactoring would fight the existing structure at every step.

   *Spike 02 surfaced rotation as non-negotiable for production:* modules with fixed intrinsic orientations (engine-thruster-right, cockpit-nose-up, weapon-barrel-right) don't compose coherently at orthography level. Rotation is easy to defer and painful to retrofit — ship it in the first rebuild iteration.

   **Known consumers** (enumerated post-Tier-2; the rebuild's API must serve all five):
   - **Combat runtime** (`30_overhaul_space_combat.md §4.1`) — player + enemies render through the unified pipeline; damage states, module destruction, wear all render consistently
   - **Ship builder preview** (`31_overhaul_ship_builder.md §4.2`) — large central preview pane renders at three canonical angles (front / profile / three-quarter) with orbit animation
   - **Ship builder test flight** (`31_overhaul_ship_builder.md §4.7`) — 20-second sim renders the ship in motion, weapons firing, in a test arena
   - **Salvage module recovery** (`36_overhaul_salvage.md §4.7`) — recovered module animates lifting out of wreckage into the player's inventory with module composite rendering at the cell
   - **Station hub docked-ship glimpse** (`35_overhaul_station_hub.md §4.6`) — 120×80 persistent corner panel shows the player's ship as it's visible from the station perspective

   **API implications:** the rebuilt `ShipComposite` must accept a `render_angle` parameter (minimum 3 canonical angles), support per-module state overrides (damaged / destroyed / highlighted), and expose a cache key that includes rotation + angle + state. This is beyond what a single-consumer combat-only rebuild would require.

2. **`screen_effects.py` → rebuild as `post_processing.py`:** 90 lines of ad-hoc effects. A proper post-processing pipeline (with explicit stages: bloom extract → blur → composite, chromatic aberration sampler, grain overlay, vignette) is ~200-300 lines with a different architecture (surface-chain pipeline rather than direct blit effects). The rebuild cost is ~1 day; the refactor cost would be higher and produce worse code.

3. **`palettes.py` → rebuild:** The aesthetic bible will define a canonical 24-color palette. Every procedural function will reference this palette by role name ("hull-cold-metal," "reach-warning-red"). The current palette module isn't structured for that indexing. Small file, clean rebuild.

**Everything else stays.** We don't redesign for the sake of it.

---

## 3. Primitive Vocabulary

The set of mathematical primitives every procedural asset is composed of. We commit to a deliberately small vocabulary so that consistency emerges from constraint.

### 3.1 Committed primitives

- **Rectangles, rounded rectangles** — the base of most modules, panels, UI chrome
- **Circles, ellipses** — portholes, thrusters, sensor domes, buttons
- **Polygons** (convex + concave) — ship frames, hull plates, angular structures
- **Bézier curves** (quadratic + cubic) — smooth decorative lines, cable runs, atmospheric wisps
- **Line segments** with configurable width and caps — panel seams, weld lines, wiring

### 3.2 Secondary primitives (committed but used sparingly)

- **Voronoi cells** — deterministic hull paneling (prevents "tiled" look). Each module gets a Voronoi decomposition of its surface into 4–12 panels with individually weathered fills.
- **Perlin/Simplex noise** (scalar fields) — wear patterns, grain, cloud fields, sensor distortion. Commit to `opensimplex` library for consistency.
- **FBM (Fractal Brownian Motion)** — composited noise for atmospheric depth (nebulae, engine exhaust plumes, fog).
- **Poisson-disc sampling** — deterministic rivet/bolt placement avoiding clustering.

### 3.3 Optional / research-required

- **Signed Distance Fields (SDFs)** — smooth shape blending. *Research question: is the complexity cost worth the visual smoothness?* Prototype spike required before committing. Verdict candidates:
  - **Adopt universally** — all shape rendering via SDF. Highest quality, highest complexity.
  - **Adopt for silhouette only** — SDF defines ship outline + connection blending; internals use polygon/raster. Compromise.
  - **Skip** — polygon rendering is good enough with careful antialiasing.
- **Wave Function Collapse (WFC)** — for generating module-interior patterns (panel grids, conduit runs). High-power, high-complexity. *Defer decision until a Tier 2 doc surfaces a specific need.*

### 3.4 Explicitly not used

- **Raytraced lighting** — overkill for 2D.
- **Per-pixel handwork after procedural pass** — this violates the "programmatic is the medium" discipline. If procedural can't produce it, we either accept the result or change the algorithm.
- **3D mesh rendering in pygame** — out of scope. Blender renders baked into 2D sprites is the approved handoff (see `12_agentic_graphics_workflow.md`).

---

## 4. Material System

A material is a parametric function: given a shape and lighting, produce a surface rendering. Materials are the primary unit of "what this thing is made of."

### 4.1 Material schema

*Revised per Spike 02 Finding 3 — a flat shadow/base/highlight triple collapses under palette-snap when the luminance range is narrow. Materials now declare a **shade band** of 4–5 palette entries spanning their lighting range, and palette-snap operates against the material's own band rather than the whole 24-color palette.*

```python
@dataclass(frozen=True)
class Material:
    name: str                                # "brushed_steel", "crimson_iron", "plasma_glass"
    shade_band: tuple[str, ...]              # 4-5 palette-role keys, DARKEST → BRIGHTEST
                                             # e.g., ("steel_shadow", "steel_dim", "steel_base",
                                             #        "steel_bright", "steel_specular")
                                             # Lighting lerps across the band; snap is constrained
                                             # to band entries only (prevents UI colors snapping
                                             # into material surfaces accidentally).
    category_offset: int = 0                 # per-category shift within band (-1, 0, +1)
                                             # weapons default -1 (darker), structurals default +1
                                             # (brighter). Expressed as band-entry shift, NOT RGB
                                             # multiply — multiplicative tints erase under snap
                                             # (Spike 02 Finding 4).
    noise_scale: float                       # Perlin frequency for surface grain
    noise_intensity: float                   # how visible the grain is (0-1)
    rivet_density: float                     # rivets per 1000 px² (0 = no rivets)
    wear_noise_scale: float                  # larger-scale noise for weathering
    wear_intensity: float                    # baseline grime before per-instance wear
    gloss: float                             # specular highlight strength (0-1)
    emissive: bool = False                   # renders through lighting (engines, windows)
    emissive_color: str | None = None        # required if emissive (single palette entry;
                                             # emissive passes bypass the snap stage)
```

**Key change from the v0 schema:** `base_color` / `highlight_color` / `shadow_color` are replaced by a single `shade_band` tuple. The band is the material's entire permitted output range; snap constrains pixels to that range only. Category differentiation happens via `category_offset` — a band-index shift — not via RGB multiplication, because multiplicative tints snap to the same palette entries as un-tinted pixels and lose their signal.

### 4.2 Committed material library (v1)

Defined in `engine/materials.py` (new file). Each material references a shade band (§8.1); values calibrated against the Aesthetic Bible once written.

| Material | Purpose | Shade band |
|----------|---------|-----------|
| `brushed_steel` | Default ship hull metal — cold, industrial | `steel` |
| `crimson_iron` | Crimson Reach faction hull — patinated red-brown | `reach_crimson` |
| `solari_chrome` | Commerce Guild flagship — polished mirror | `solari_chrome` |
| `union_ceramic` | Miners Union heat-tile — matte off-white with carbon scoring | `union_ceramic` |
| `frontier_canvas` | Frontier Alliance welded patchwork — visible seams | `frontier_canvas` |
| `collective_composite` | Science Collective lab equipment — sterile white-blue | `collective_composite` |
| `glass_viewport` | Window material — low gloss, emissive at night | `glass_viewport` (narrow band + emissive override) |
| `plasma_energy` | Fully emissive, animated, for engine cores | (bypasses band — uses `PALETTE_ROLES.plasma_core` family) |
| `cryo_fractal` | Emissive blue-white with crystalline pattern | (bypasses band — uses `PALETTE_ROLES.cryo_fractal` family) |
| `ion_field` | Emissive purple with arc-line detail | (bypasses band — uses `PALETTE_ROLES.ion_arc` family) |

**Discipline:** NEW materials get added only when an existing one genuinely can't carry the aesthetic. Default is reuse. Adding a material means adding a shade band to §8.1 — both co-evolve.

### 4.3 Manufacturer profiles

A manufacturer profile references a palette subset + material dictionary + detail parameters:

```python
@dataclass(frozen=True)
class ManufacturerProfile:
    id: str
    name: str
    primary_material: Material
    accent_material: Material
    detail_density: float        # 0 (minimalist) to 1 (busy with rivets/panels)
    shape_vocabulary: Literal["angular", "rounded", "organic", "modular"]
    signature_color: str         # palette-role, appears on every manufactured part
```

This formalizes what "a Reach ship vs. a Solari ship" looks like, so procedural output maintains the intuition the player develops.

### 4.4 Rendering a material

Given a shape (polygon, rectangle, etc.) and a light direction, the material renderer:

1. Fills the shape with the band's **midpoint entry** (`shade_band[len(band)//2]`)
2. Applies the lighting gradient across the shape: pixels on the light-facing side interpolate toward the band's bright end, pixels away toward the dark end. Output is still continuous RGB at this stage.
3. Overlays a per-instance noise field (seeded) at `noise_intensity`, perturbing toward brighter/darker band entries (not arbitrary RGB)
4. Applies wear: a second, larger-scale noise at `wear_intensity`, biasing toward the dark end of the band
5. Places rivets via Poisson-disc sampling at `rivet_density` (rivets are band-entries themselves, typically the dark + bright ends to read as shaded metal bumps)
6. Applies a subtle `gloss` highlight on edges parallel to the light direction (uses the band's brightest entry)
7. If emissive: skip lighting, apply pulse modulation for animated glow — emissive passes **bypass palette-snap**
8. **Palette-snap pass (band-constrained):** every non-emissive pixel is snapped to the nearest entry **within the material's own shade_band**, not the full 24-color palette. This prevents UI colors from being accidentally pulled into material surfaces and guarantees lighting produces the intended banded appearance.

Output is a `pygame.Surface` with per-pixel alpha. Cached in `procedural.py` keyed on `(material.name, shape_hash, seed, lighting_direction, wear_level, category_offset)`.

---

## 5. Lighting Model

One global directional light. No exceptions. Consistency is the whole point.

### 5.1 Direction

**Top-right, 45° down from horizontal** (convention: light from upper-right, shadows fall lower-left). This matches Starfield, Hades, Factorio, and most 2D games with baked lighting. Players won't consciously notice consistency — they WILL notice inconsistency.

### 5.1.1 Rendering discipline: palette-snapped by default

*Informed by Spike 01 findings.* Gradient lerping between shadow/base/highlight produces an infinite color continuum, but Aurelia's aesthetic direction calls for **flat palette bands**, not smooth gradients. After the lighting pass, pixels snap to the nearest palette color. This yields:

- **Chunky, material-honest lighting** — discrete bands read as *metal under light* rather than *computer gradient*
- **Strict palette compliance** — every output pixel is a palette entry
- **Heavier load on detail passes** — rivets, wear, stripes, and noise must carry more of the visual richness; lighting alone is too flat without them
- **"Lived-in" feel** — the combination of banded lighting + rich surface detail reads as weathered industrial object, not sterile render

Gradient mode remains implemented as a non-default option for cases where smooth interpolation is specifically desired (likely: atmospheric backgrounds, emissive glows, VFX). Per-asset-class declaration determines which mode applies.

### 5.2 Components

- **Ambient:** 0.35 of base color. The "what things look like in shadow" floor.
- **Diffuse:** scales 0 → 1 with the dot product of surface normal and light direction. For 2D polygons, the "normal" is approximated by edge direction + a hemisphere blend; for circles, radial gradient outward from the lit-side edge.
- **Specular:** gloss-weighted highlight along edges perpendicular to the light. Small, intense, applied to rims and metallic surfaces.
- **Emissive:** contributes independently of lighting. Plasma cores, windows at night, warning lights. Additive blend on top of the lit base.

### 5.3 Per-scene overrides

The global light is sacrosanct for individual assets. **Scene-level tinting** is a post-processing concern (a cold-blue tint over the whole combat view, a warm tint during a station docking sequence) — applied in the post-processing pipeline, not per-asset.

### 5.4 Rim lighting (hero assets only)

Used sparingly for narrative emphasis: the player's ship during combat, the boss at phase transition, the legendary drop moment. Adds a faint inverse-direction rim to read the silhouette against dark backgrounds. Flag on `ManufacturerProfile` or per-render call; never default.

---

## 6. Composition & Connection System

How modules come together into ships (or analogously, how UI panels come together into screens). The most-visible weakness of the current shipbuilder.

### 6.1 The problem

Current `ship_composite.py` stitches module sprites tile-adjacent. Players see "modules next to each other," not "a ship." This is the clunkiness the user called out.

### 6.2 The solution: unified-object rendering

Treat the ship as a single shape to light and detail, not a grid of independently-lit tiles.

**Algorithm:**

1. **Silhouette pass.** Compute the union of all placed-module bounding shapes. Rasterize to a ship-silhouette mask.
2. **Per-module base pass.** Render each module's material fill at its placed position into a shared render target. Alpha-masked to the silhouette.
3. **Global lighting pass.** Apply the ONE global light direction across the whole silhouette. The ship receives light as a single object. This is the key move: light isn't per-module, it's per-ship.
4. **Connection detail pass.** Where two modules share an edge, render a seam (line or gradient) appropriate to their materials. Weld seams between metal modules; panel gaps between different-manufacturer modules; glowing coupling lines where power modules connect to weapon modules.
5. **Decoration pass.** Rivets, wear, and small details placed deterministically via Poisson on the silhouette mask.
6. **Emissive pass.** Plasma cores, engine glow, window lights — additive, animated.
7. **Cache.** Result cached keyed on the ship build hash. Re-rendered only when the build changes.

This produces a ship that reads as **one vehicle** with consistent lighting and material transitions, rather than a collage.

### 6.3 Connection vocabulary

Three connection types, chosen by module-adjacency rules:

- **Weld seam:** same-manufacturer + same-material modules adjacent. Thin dark line.
- **Panel gap:** same-manufacturer, different-material modules. Slight dark gradient with subtle reflective highlight.
- **Power coupling:** between a reactor-category module and a weapon/utility module. Glowing line in the coupling color (default plasma; matches weapon element if weapon).

### 6.4 Failure modes to guard against

- **Over-busy composition.** Rule: any given pixel receives at most 3 passes of detail (base + lighting + one decoration). Enforce via render-order discipline.
- **Silhouette breakage.** Rule: every module must render within its declared bounding box; no overhangs. Enforce via test harness.
- **Lighting inconsistency.** Rule: all per-module rendering at this layer ignores lighting; global lighting happens only at the silhouette pass. Violations = test harness failure.

---

## 7. Variation Without Chaos

Programmatic generation's classic failure: either everything looks the same (boring) or every variant looks different (chaos). Path between:

### 7.1 Seeded parametric families

Each module category has 3–6 hand-designed **parametric templates**. A small weapon mount has templates like "barrel-forward," "turret-dome," "lateral-array." Each template accepts manufacturer + seed, producing deterministic variants within its shape family.

- Templates = hand-designed shape language. Small, reviewable, authored with intent.
- Parameters = where the procedural magic lives (sizing, detail placement, wear, color).
- Seed = provides within-family variation.

This gives you thousands of valid outputs from a few dozen templates — without the grey-goo sameness of pure procgen and without the hand-authoring cost of every sprite.

### 7.2 Per-instance memory

A ship's appearance is deterministic from its build state. Save the build, load it tomorrow, it looks the same. No drift. The seed is `hash(build.id + module.position)` so moving a module to a new position re-seeds it (feature, not bug — different positions imply different placements).

### 7.3 Aging and wear

Wear level is a numeric parameter (0 = fresh, 1 = decrepit). Stored per ship, persisted, advanced slightly by combat/damage events. Renderers accept wear as input and modulate the wear-noise pass accordingly. Aging is **visible progression** without requiring new art.

---

## 8. Palette System

A palette organized into **material-specific shade bands + global role entries** is the single strongest discipline lever. Every rendering function references palette entries by role; raw RGB hex values do not appear in procedural code.

*Revised structurally per Spike 02 Finding 3.* The v0 schema was a flat dict of ~24 entries. The v1 schema is **two-tier**: a set of material shade bands (4–5 entries each, used by material renders) plus a shared role table (used by UI, emissive, and scene-level pixels). Materials snap only into their band; UI pixels snap to the role table. This prevents cross-contamination observed in Spike 02 (UI `hud_text` appearing as an "accidental" material shade on Solari hulls).

Total palette grows from 24 → approximately **40 entries** organized as bands. This is a meaningful addition that the Aesthetic Bible finalizes; the structural decision is made here.

### 8.1 Palette structure (to be finalized in Aesthetic Bible)

```python
# --- MATERIAL SHADE BANDS ---
# Each band: DARKEST → BRIGHTEST. Materials lerp lighting across their band
# and snap output to band entries only.

MATERIAL_BANDS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "steel": (
        (28, 34, 46),    # steel_shadow
        (58, 68, 84),    # steel_dim
        (92, 104, 124),  # steel_base
        (140, 156, 182), # steel_bright
        (190, 205, 225), # steel_specular
    ),
    "solari_chrome": (
        (90, 100, 115),
        (150, 160, 175),
        (200, 210, 222),
        (225, 232, 242),
        (248, 250, 254),  # near-mirror bright
    ),
    "reach_crimson": (
        (55, 18, 22),
        (95, 30, 32),
        (135, 45, 42),
        (175, 70, 58),
        (215, 110, 82),
    ),
    "union_ceramic": (
        (90, 82, 72),
        (135, 125, 108),
        (180, 170, 150),
        (215, 205, 185),
        (238, 230, 215),
    ),
    # frontier_canvas, collective_composite, glass_viewport, plasma_energy,
    # cryo_fractal, ion_field — each their own band, defined in Aesthetic Bible.
}

# --- GLOBAL ROLE TABLE ---
# For pixels that are NOT material surfaces: scene background, UI chrome,
# emissive cores, particles. Rendered separately; NOT a fallback for material snap.

PALETTE_ROLES: dict[str, tuple[int, int, int]] = {
    # Base space
    "void_deep":     (10, 12, 20),
    "void_mid":      (18, 22, 36),
    "void_light":    (30, 38, 56),

    # Energy (emissive cores — bypass snap)
    "plasma_core":    (255, 170, 60),
    "cryo_fractal":   (120, 220, 255),
    "ion_arc":        (200, 100, 255),
    "voltaic_strike": (255, 230, 100),
    "glow_warm":      (255, 200, 120),
    "glow_cool":      (100, 180, 255),

    # UI chrome
    "hud_cyan":     (80, 200, 230),
    "hud_warning":  (240, 140, 60),
    "hud_critical": (240, 70, 70),
    "hud_muted":    (110, 120, 140),
    "hud_text":     (220, 225, 235),

    # Misc
    "glass_tint":   (40, 80, 100),
}
```

**Rules:**

- A material pixel may only contain a color from its own `shade_band`. Post-snap compliance test asserts this strictly.
- A UI or role pixel may only contain a `PALETTE_ROLES` color.
- Emissive pixels bypass snap entirely and may use `PALETTE_ROLES` emissive entries as seeds for bloom/particle gradients.
- The two tiers are disjoint. A band entry never appears in the role table and vice versa — this is what makes material/UI separation enforceable.

### 8.2 Palette compliance

A test harness asserts, per pixel, that it belongs to the correct tier:

```python
def assert_band_compliance(surface, material_band: tuple[tuple[int,int,int],...],
                           tolerance: float = 2.0) -> None:
    """Opaque pixels of a material render must be within `tolerance` RGB of a
    band entry. Tighter than v0's whole-palette check because the band is small."""

def assert_role_compliance(surface, tolerance: float = 4.0) -> None:
    """Opaque pixels of UI/scene content must be within `tolerance` of a role entry."""
```

With band-constrained snap, tolerance on material compliance can be very tight (≤2 RGB) because post-snap pixels are supposed to be exact band entries. This is a stronger discipline than the v0 ~8-RGB tolerance.

### 8.3 Colorblind modes

Handled via band remapping + role remapping, not per-renderer code. A colorblind profile defines a function `band → band'` for each material and an analogous map for roles; every renderer works unchanged.

---

## 9. Render Pipeline Architecture

How all this fits together in the rendering frame.

### 9.1 Per-frame order

```
  1. Clear to palette['void_deep']
  2. Render animated background (parallax starfield, nebulae)
  3. Render scene (ships, UI, effects) to SCENE_SURFACE
     - Each renderable resolves to a cached Surface from procedural.py
     - Ships rendered as unified-object (see section 6)
     - UI rendered via ui_chrome components
  4. Apply post-processing pipeline to SCENE_SURFACE:
     a. Bloom extract → blur → additive composite
     b. Chromatic aberration (edge-weighted)
     c. Vignette
     d. Noise/grain overlay
     e. Per-scene color tint (optional)
  5. Render particles (PARTICLE_SURFACE, additive composite)
  6. Render UI overlay (NOT subject to post-processing)
  7. Present frame
```

### 9.2 Post-processing pipeline

Rebuilt from scratch (see §2 triage). Implemented as an ordered chain of `PostProcessStage` objects:

```python
class PostProcessStage:
    def apply(self, src: pygame.Surface) -> pygame.Surface: ...

class BloomStage(PostProcessStage): ...
class ChromaticAberrationStage(PostProcessStage): ...
class VignetteStage(PostProcessStage): ...
class GrainStage(PostProcessStage): ...
```

Stages are either pygame-native (`surfarray` / `BLEND_*` mode manipulation) or shader-based (pygame-ce shader or moderngl). Decision tree for each stage is in `11_pygame_capability_audit.md`.

### 9.3 Caching discipline

- **Procedural asset Surfaces** cached in `procedural.py`, keyed on all inputs.
- **Ship composites** cached per build-hash, invalidated on build change.
- **Post-processing results** not cached (applies to full-frame, changes per-frame).
- **Font renderings** cached at FONT_CACHE level.

**Rule:** procedural generation at the per-frame level is forbidden. Anything that generates a Surface must check cache first; anything new goes into cache. Violations flagged by profiling.

---

## 10. Testing Discipline

Programmatic generation is disciplined code — tested like any other.

### 10.1 Automated tests

- **Band compliance** (§8.2) — material renders fed through `assert_band_compliance` with tight tolerance (≤2 RGB post-snap).
- **Role compliance** (§8.2) — UI/scene renders fed through `assert_role_compliance`.
- **Determinism** — same inputs → byte-identical output. Hashed.
- **Silhouette bounds** — module renders don't overflow declared bounding boxes.
- **Silhouette connectivity** — ship composites render as ONE connected component (per Spike 02 `check_ship_single_connected`). A disconnected ship reads as broken and fails.
- **Cache correctness** — cache keys disambiguate all relevant inputs (seed, wear, manufacturer, rotation, category_offset).
- **Directional lighting** — test harness splits into two assertions per Spike 02 Finding 5:
  - **`test_lighting_direction_correct` (required):** `sign(UR_luminance - LL_luminance) > 0`. Any non-zero positive gradient proves the light direction is respected. Narrow-band materials can pass this even when the magnitude is small.
  - **`test_lighting_magnitude_sufficient` (advisory):** `UR_luminance - LL_luminance > 5`. Legacy test; promoted to warning rather than failure. Flags materials whose bands are too narrow to express legible gradient.
- **Module rotation** — a module rendered at 0° / 90° / 180° / 270° produces silhouettes that are rotations of each other (pixel-wise after rotation-inverse), and lighting on each reads consistently from the global upper-right (ie. a module rotated 180° has its bright side facing the rotated light direction, NOT its original one — global lighting is applied AFTER rotation).

### 10.2 Visual regression suite

Reference renders saved per-commit. Any procedural change that alters output triggers visual review. Tools: store reference PNGs in `tests/visual_refs/`, compare on CI via pixel-diff. See `12_agentic_graphics_workflow.md` for details.

### 10.3 Acceptance bars

Each procedural asset type has acceptance criteria in its implementation doc. A module render is "acceptable" when:
- Palette compliance > 95%
- Silhouette readable against `void_deep` background (edge contrast > 30 perceptual units)
- Manufacturer identity visible (test: side-by-side three variants, ask "which is Solari?" — answerable)

---

## 11. Research Questions (to resolve before full implementation)

The master plan named these; this doc elaborates with specific experiments:

### 11.1 Which noise library?

Options: `noise` (C extension, fast), `opensimplex` (pure Python but good), `fastnoise` (C extension, very fast, fewer functions).

**Experiment:** benchmark full-screen Perlin at 60 FPS with each. Winner commits as project standard.

### 11.2 SDFs: in, partial, or out?

**Experiment (module render spike):** render one module three ways — polygon-only, SDF-only, hybrid. Compare visual quality, code complexity, render time. Decide.

### 11.3 Voronoi paneling: yes or no?

**Experiment:** render one ship with Voronoi-based hull paneling, one without. A/B subjective judgment against the aesthetic bible's "feels space-like" target.

### 11.4 How many material entries is enough?

The v1 list (§4.2) has 10. **Prediction:** covers 80% of needs. **Experiment:** attempt to render a diverse ship variety using only v1 materials. Note what it can't produce. Iterate.

### 11.5 Is pure programmatic enough for portraits/characters?

Portraits currently use `sprites.py` pixel-art assets. **Experiment:** try to procedurally generate an Elena portrait. Likely fails — portraits need authored detail. Honest answer: portraits stay hand-authored pixel art. Commit to this boundary in `12_agentic_graphics_workflow.md`.

### 11.6 Cache size discipline

Current `procedural.py` caches 50 entries. **Experiment:** profile the cache hit rate across a representative gameplay session. Tune the cap if needed.

### 11.7 Performance ceiling

**Experiment:** render a scene with 6 ships, full post-processing, 500 particles. Target: 60 FPS with headroom. If we can't hit it, pipeline redesign is needed before committing.

---

## 12. Prototype Spikes (deliverables before this doc finalizes)

From master plan §3.1, with refinement:

### Spike A — Module Render

Deliverable: `tools/spike_module_render.py` — a standalone script that renders one module type in three manufacturer variants. Saves PNG output to `tools/output/`. Passes palette compliance test harness (if built).

**Success criteria:** three variants recognizably distinct; lit consistently; respect the material system schema above.

**Expected finding:** probably reveals that material parameters need tuning; that a manufacturer profile needs one more parameter we didn't think of; that Poisson rivet placement looks bad without manual constraints. All good — these are the exact questions the spike is buying answers for.

### Spike B — Ship Composition

Deliverable: `tools/spike_ship_composition.py` — composes a 6-module ship using spike A's module renderer + a stub `render_ship` function implementing §6's algorithm. Produces a PNG.

**Success criteria:** ship reads as one vehicle; connection seams visible; silhouette clean.

### Spike C — Palette Stress Test

Deliverable: render Spike B's ship with three candidate palettes (conservative, high-contrast, neon). Side-by-side PNG. Used to inform Aesthetic Bible palette finalization.

---

## 13. Dependencies

**This doc depends on:**
- `00_master_plan.md` — umbrella philosophy and sequencing

**Docs that depend on this one:**
- `11_pygame_capability_audit.md` — implementation substrate decisions
- `12_agentic_graphics_workflow.md` — what we produce via agent iteration
- `20_aesthetic_bible.md` — palette and material catalog finalize here
- All Tier 2 per-system overhaul docs
- Tier 3 `41_vfx_particle_vocabulary.md` and `42_ui_chrome_components.md`

**External dependencies:**
- `opensimplex` or `noise` library (see §11.1)
- Potentially `moderngl` (see pygame audit)
- No new heavyweight deps beyond these

---

## 14. Open Questions

1. Do we commit to one material renderer with per-material parameters, or per-material classes? (Performance vs. flexibility trade-off.)
2. Does the Aesthetic Bible drive palette, or does palette exploration in prototypes drive the Bible? Current plan: bidirectional — prototypes generate candidates, Bible picks the winner, framework freezes it.
3. How do we visualize materials in a test harness (a "materials sampler" screen for QA)?
4. Should module templates be defined in Python or data (YAML/JSON)? Python gives parametric power; data gives content-team ease. Probably Python for v1 pending someone who's not a programmer needing to add them.

---

## 15. Extensibility: Module Category Expansion (forward-looking)

*Planted to prevent expensive retrofit. The framework assumes the current 4-category ship module vocabulary (cockpit / engine / weapon / structural) may expand to include new functional classes — radar, targeting computers, sensor arrays, cooling vents, shield emitters, electronic warfare, comms, repair drones, cargo externals. We are NOT planning or implementing expansion here; we are making three small structural decisions so that expansion, if and when it happens, costs additive code rather than rework.*

### 15.1 Decision 1: `ModuleCategory` is a registry, not a closed enum

**Current state (Spike 02):** `ModuleCategory = Literal["cockpit", "engine", "weapon", "structural"]`. The `rasterize()` function in `module_types.py` dispatches on category via if/elif. Production `data/ships/*.json` uses the same closed set.

**Decision:** categories are **registered**, not enumerated. The production rebuild of `ship_composite.py` (see §2) introduces a `ModuleCategoryRegistry` with:

```python
@dataclass(frozen=True)
class CategoryProfile:
    id: str                                  # "radar", "targeting", "structural", ...
    rasterize_fn: Callable[..., tuple[np.ndarray, np.ndarray, dict]]
    default_shape_vocabulary: Literal["angular", "rounded", "organic", "modular", "radial", "appendage"]
    default_material_tag: str                # hint — materials pick from this tag when not overridden
    default_emissive: bool
    silhouette_role: Literal["hull", "appendage", "internal"]
    detail_density_range: tuple[float, float]  # per-category critique override (see §15.5)

def register_category(profile: CategoryProfile) -> None: ...
def get_category(id: str) -> CategoryProfile: ...
```

New categories register themselves at import time. No core file changes when a category is added. The only test that needs updating is the per-category critique override table (§15.5), which is itself registry-driven.

**Discipline:** `if category == "weapon"` style dispatch is banned in rendering code after the rebuild. All category-specific behavior lives on `CategoryProfile` or on the module's own declared metadata.

### 15.2 Decision 2: Silhouette-role is a first-class concept

Three silhouette-roles, chosen by category:

- **`hull`** — part of the ship's main body. Composed into the unified silhouette via bbox-overlap union (current algorithm). Examples: cockpit, engine body, structural plate, heavy weapon mount.
- **`appendage`** — attached externally via a connection point, protruding from the hull. Contributes to the silhouette but rendered with a single-point connection (the seam is a welded joint, not a blended gradient). Examples: radar dish, antenna mast, sensor boom, comms array.
- **`internal`** — occupies build grid space but does NOT appear in the external silhouette. Lit interior glimpsed through windows only, or entirely invisible. Examples: targeting computer, reactor core, shield emitter, cooling vent (internals — external vents are appendages).

This classification matters at composition time: §6's algorithm unifies hull modules into a silhouette; appendage modules are composited on top with explicit connection treatment; internal modules skip silhouette contribution entirely but may produce emissive bleed through windows.

**Why it matters now:** the `ship_composite.py` rebuild must understand these three cases or it will produce broken output for radar/sensor-style categories. Easy to build in; painful to retrofit into a hull-only composer.

### 15.3 Decision 3: Typed connection points with `ConnectionKind`

Spike 02 Finding 1 already flagged connection-point metadata for the rebuild. Strengthen: each connection point declares a **kind**, enabling declarative placement rules.

```python
@dataclass(frozen=True)
class ConnectionPoint:
    position: tuple[float, float]            # relative to module's local origin, 0..1 normalized
    kind: Literal["structural", "data", "power", "mount", "coolant"]
    facing: Literal["up", "down", "left", "right", "any"]
```

**Compatibility matrix** (maintained in a small data table, extensible):
- `structural` ↔ `structural` — weld seam (thruster mounts, hull joints)
- `mount` ↔ `mount` — bolted attachment (radar on a mast, weapon on a hardpoint)
- `power` ↔ `power` — plasma coupling with visible glow
- `data` ↔ `data` — thin cable run, minor visible detail
- `coolant` ↔ `coolant` — pipe connection, vent glow if hot

The composer enforces connection compatibility at placement time. Ship builder UI surfaces violations. New category = add connection points in its shape authoring; new connection kind = one row in the matrix. No rendering code changes.

### 15.4 What the Aesthetic Bible should carry forward

When the Bible is written (after Spike C), these TODOs need to land:

- **Reserve palette-band naming space** for anticipated future material classes: `sensor_glass`, `electronics_emissive`, `cooling_vent`, `radar_mesh`, `shield_field`. The Bible doesn't need to finalize values yet — it just names the slots so future palette work doesn't conflict.
- **Per-category critique thresholds.** The current global `check_detail_density` range of `(0.04, 0.35)` will underfit busy categories (radar arrays) and overfit spare ones (structural plates). The Bible captures each category's expected density range as a CategoryProfile default (§15.5).
- **Category-level visual signatures.** The Bible defines not just manufacturer voice but per-category shape language: what does a Solari radar LOOK like vs a Reach radar? Manufacturer × category is the identity grid.

### 15.5 Critique harness: per-category overrides

Small addition to `critique.py` — thresholds default-to-global but can be overridden per category profile:

```python
def check_detail_density(
    surface, category: str | None = None,
    target_range: tuple[float, float] | None = None,
) -> CritiqueResult:
    if target_range is None:
        target_range = (
            get_category(category).detail_density_range
            if category else (0.04, 0.35)
        )
    ...
```

This stays as a one-liner override today; extension to a full per-category tuning table is trivial when Tier-2 overhaul docs for sensor/radar modules land.

### 15.6 What this section explicitly does NOT do

- **No new modules implemented.** Radar, targeting, etc. remain outside current scope.
- **No production data changes.** `data/ships/*.json` retains its current 4-category vocabulary until a concrete expansion roadmap is written.
- **No impact on Spike C.** Palette stress test runs on the same 3 manufacturers × 6 modules as Spike B.
- **No scope on the `ship_composite.py` rebuild beyond what was already estimated.** Items 15.1-15.3 are structural decisions that fit within the existing rebuild budget; they replace ad-hoc dispatch with clean registry dispatch at roughly equal line count.

The single discipline commitment here: **when the rebuild ships, it ships with registry-based categories, silhouette-role awareness, and typed connection points, even though only the 4 current categories exist on day one.** Future expansion then adds data; it never retrofits code.

---

*Next: write `11_pygame_capability_audit.md`, then `12_agentic_graphics_workflow.md`, then run prototypes A/B/C to inform both this doc and the Aesthetic Bible.*
