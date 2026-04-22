# Spike 02 Findings — Ship Composition (Unified-Object Algorithm)

> Framework Spike B per `00_master_plan.md` and `10_programmatic_generation_framework.md §6`.
>
> Purpose: validate that 6 modules can be composed into a single coherent ship via unified-object lighting, and surface any composition-level issues not visible at module scale.

---

## TL;DR

**The composition algorithm works.** After iteration, all three manufacturers produce connected, distinctly-identifiable ships with clean lighting direction and palette compliance. Reach and Union pass 7/7 checks; Solari passes 6/7 (lighting consistency marginally below threshold).

The failing Solari check is informative — it revealed a **real design issue** with palette snapping when a material's shadow-base-highlight triple spans a narrow luminance range. This surfaces a required improvement to the framework's palette system: **material sub-palettes with dedicated intermediate shade bands**, so gradient lighting survives the snap.

Also surfaced: **module rotation is required eventually** for coherent ship orthography. Current modules have fixed intrinsic orientations (engine-thruster-right, cockpit-nose-up, weapon-barrel-right) that don't compose coherently without rotation support. Out of scope for the spike, flagged for framework revision.

---

## Spike Scope

Built on top of Spike A, adding:

- `module_types.py` — 4 module type rasterizers (cockpit, engine, weapon_small, structural)
- `ship_render.py` — the unified-object composition algorithm per framework §6
- `spike_ship.py` — entry point; composes 6-module ships for 3 manufacturers

Added critique dimensions:
- `check_ship_single_connected` — silhouette must be one connected component
- `check_ship_lighting_consistency` — upper-right brighter than lower-left (global light direction)

Output: `tools/overhaul_spike/output/ship_*.png` + atlas + comparison with gradient variant.

---

## What Worked (after iteration)

### 1. Ship connectivity (3/3 pass after layout fix)

Initial layout produced disconnected fragments (664 / 4947 opaque pixels in largest component). After redesigning the layout with heavy bounding-box overlap, all three ships produce a single connected silhouette of 4412–4714 pixels. **The unified-object algorithm produces ships that read as one object when layout is correct.**

### 2. Variant distinctness (90.7 mean pairwise RGB diff, target 15)

With the opaque-only critique fix, manufacturer identity at ship scale is strongly distinct — ~6× the pass threshold. Composing 6 modules didn't wash out manufacturer identity; it sharpened it. Per-category tinting plus per-material palette subsets produce clearly different visual signatures.

### 3. Determinism (3/3 pass)

Composite ship hashing works. Three renders of the same seed produce byte-identical output. Ship builder can cache ship composites indefinitely.

### 4. Palette compliance (3/3 pass at both strict and line-compliance)

With palette-snap as the default, every output pixel is exactly a palette color. 100% compliance across all three ships on both critique dimensions.

### 5. Performance (40.6ms for 3 ships)

Three ship renders including composition, lighting, wear, emissive, snap, and rivets: ~40ms total. At 60 FPS budget of 16.6ms, a single ship render is well within budget (~13ms) even without caching. With the planned ship-build-hash cache, this becomes a one-time cost.

### 6. Unified-object lighting validates

The §6 algorithm (one global light across the whole silhouette, not per-module) produces lighting that's consistent across the ship. Reach (+10.4 UR-LL luminance diff) and Union (+6.9) show clear directional lighting. Solari struggles due to palette width — see Finding 3.

---

## What Didn't Work (honest findings)

### Finding 1: Layout math doesn't auto-produce overlap

The first layout placed modules with edge-adjacency (touching bounding boxes) rather than overlap. Because module coverage masks don't fill their bounding boxes (cockpit has narrow nose, weapons have thin barrels), edge-adjacent modules produced disconnected coverage.

**Implication:** production module placement will need either:
- A **connection validator** that checks silhouette connectivity at build time and flags gaps
- A **"bridge pixel" pass** that fills small gaps between adjacent modules automatically
- **Connection points as metadata** — each module declares its connection points, and the composer enforces overlap between them

All three are framework-worthy. Easiest to prototype first: bridge pixels. Flag this for `ship_composite.py` rebuild.

### Finding 2: Module rotation is eventually required

Current module shapes have fixed intrinsic orientations that don't compose coherently. A ship with engines pointing right, cockpit pointing up, and weapons pointing right is visually incoherent at orthography level. The spike worked around this by accepting an abstract layout, but production ships need rotation.

**Implication:** `ModuleType.rasterize()` should accept a `rotation_degrees` parameter (90° increments sufficient for square/rect modules; arbitrary for circles). Plus a connection-point metadata that rotates with the module.

This is the kind of feature that's easy to defer but painful to retrofit. **Recommend: add to `ship_composite.py` rebuild scope.** 1–2 day extension.

### Finding 3: Narrow palette ranges lose lighting under snap (Solari)

Solari's material has base (218) / highlight (247) / shadow (158) luminance. The gradient between them (89 units) ought to produce visible banding after snap. But when snap operates against the **full 24-color palette**, intermediate gradient values snap to whatever palette color is *nearest in RGB space* — which can be a UI role (e.g., `hud_text` at 220/225/235) rather than a material shade.

Observed in the Solari ship: `hud_text` (a UI color role) appears as an accidental material band. The lighting still goes "UR brighter than LL" directionally, but the luminance delta is too narrow to pass the test strictly.

**Implication — FRAMEWORK REVISION REQUIRED:** palette snap should be **material-aware**. Each material declares a shade band (4–5 palette entries spanning its lighting range); snap constrains output to that band only. This is a meaningful addition to the framework doc §4.2 (material schema) and §8 (palette system).

This is the most important finding of Spike B. It's not a blocker for proceeding; it's a **framework maturation** that should land before production use.

### Finding 4: Category tint is erased by palette snap

Per-category tinting (weapons × 0.92, structurals × 1.05) produces intermediate color values that snap to the nearest whole-palette entry — which is usually the *same* entry as un-tinted pixels. The tint's signal is lost in the snap.

**Implication:** per-category variation should be expressed via **different palette entries**, not multiplicative tints. For example, weapons could use a slightly-darker base-color entry; structurals a slightly-brighter one. Each material's band includes these as alternate entries.

Related to Finding 3 — both resolve via material sub-palettes.

### Finding 5: Lighting-consistency test needs a direction-not-magnitude variant

The current test asserts `UR_luminance - LL_luminance > 5`. For narrow-palette materials, the correct direction can pass at +3.7 but fail the magnitude threshold. A better test would assert: **the sign is correct** (UR > LL) and **the gradient is detectable** (non-zero after accounting for snap quantization).

**Implication:** refine the test to separate "direction correct" (required) from "magnitude sufficient" (advisory). Promote to framework-level `test_directional_lighting`.

---

## Design Decisions This Spike Forces

### Decision 1: Material sub-palettes are required (framework revision)

Each material gets a 4–5-entry palette band, not just shadow/base/highlight. Snap operates against the material's own band, not the whole palette. This:

- Prevents UI colors from being snapped into as "accidental" material shades
- Lets narrow-luminance materials (Solari) have more gradient resolution
- Keeps category tints distinguishable after snap
- Scales palette design from 24 flat entries to ~40 entries organized into bands

**Update required:** `10_programmatic_generation_framework.md §4.2` and `§8`. Palette structure goes from flat dict to nested `{material_name: [shade_roles]}`.

### Decision 2: Module rotation becomes part of the `ship_composite.py` rebuild

Already flagged as a rebuild in §2 of the framework doc. Extend its scope to include rotation as a first-class feature.

**Update required:** `10_programmatic_generation_framework.md §2` — `ship_composite.py` rebuild scope extended by ~200 lines.

### Decision 3: Connection validation is a build-time concern

When players place modules in the builder UI, silhouette connectivity should be checked live and violations surfaced ("disconnected — add structural here"). This is a **gameplay-layer** concern informed by the spike, not a rendering concern.

**Update required:** Tier 2 `31_overhaul_ship_builder.md` (not yet written) must include connection validation as a builder-view feature.

---

## Open Questions (flagged for future spikes / bible)

1. **Do we need module rotation support in the SPIKE rebuild, or defer to production?** Spike scope says defer; production scope says required. The first `ship_composite.py` rebuild iteration can start without it and add later.

2. **Do material sub-palettes imply a bigger palette (~40 entries) or tighter material discipline (~24 entries, shared across materials)?** The Aesthetic Bible needs to decide.

3. **Is the current lighting gradient (linear from 0 to 1 across bounding box) the right model?** Or should it be based on local surface normal approximation (which we don't have for 2D shapes)? Might matter for non-convex silhouettes.

4. **Should palette snap operate PER PHASE or ONCE AT END?** Currently it's once at end (after all compositing). Alternative: snap after each phase. Test result probably the same; snap-at-end is cheaper.

---

## Artifacts Produced

Files (keep — they seed framework implementation):

- `tools/overhaul_spike/module_types.py`
- `tools/overhaul_spike/ship_render.py`
- `tools/overhaul_spike/spike_ship.py`

Outputs (for Aesthetic Bible visual review):

- `tools/overhaul_spike/output/ship_solari.png`, `_reach.png`, `_union.png`
- `tools/overhaul_spike/output/ship_atlas.png`
- `tools/overhaul_spike/output/ship_atlas_gradient.png`
- `tools/overhaul_spike/output/ship_atlas_compare.png`
- `tools/overhaul_spike/output/ship_critique_report.txt`

---

## Recommended Next Actions

1. **Human view pass:** open `ship_atlas.png` (snapped) and `ship_atlas_gradient.png` (smooth). Report whether ships read as "one vehicle" at the composition level; whether manufacturer identity survives. (30 seconds)

2. **Apply framework doc revisions** from §Decisions above:
   - Material sub-palettes in `10_programmatic_generation_framework.md §4.2` and `§8`
   - Rotation support added to `ship_composite.py` rebuild scope in §2
   - Note directional-lighting test refinement for test discipline (§10)

3. **Spike C — Palette stress test.** Render the Spike B ships under 3 candidate palettes (conservative / high-contrast / neon). Feeds Aesthetic Bible palette decision.

4. **After Spike C: write the Aesthetic Bible.** Now with evidence from all three spikes; palette stress results concretely inform palette design; material sub-palette structure informed by Finding 3.

---

## Honest Assessment

The spike is a validation, not a perfection. It proved:

- **The unified-object composition algorithm works.** Ships render as coherent single objects with global lighting direction.
- **Iteration on the critique harness produces honest findings.** The failing lighting check is mechanically informative, not a blocker.
- **Framework architecture is sound but needs one meaningful addition** (material sub-palettes) before production use.

It didn't prove:

- **That ships LOOK good.** Requires human visual review of `ship_atlas.png`.
- **That connection detail (seams, power couplings) reads as intentional craft.** Currently implemented as simple darkening; may need richer treatment.
- **That rotation-aware composition works.** Deferred.

**Verdict: proceed to Spike C and then the Aesthetic Bible. Apply framework revisions first.**
