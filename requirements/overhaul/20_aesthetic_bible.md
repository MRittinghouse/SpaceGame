# Aurelia Aesthetic Bible

> **Status:** v1 — informed by Spikes 01 / 02 / 03, promoted from framework speculation to canonical discipline. Living document; revisions tracked in §9.
>
> The single source of truth for Aurelia's visual voice. Every procedural renderer, every per-system overhaul doc, every asset decision inherits from here. If code and Bible disagree, Bible wins or Bible updates — never silent drift.

---

## Table of Contents

1. Voice — what Aurelia looks like and why
2. Canonical palette — material bands + role table
3. Material library — parametric surfaces with shade bands
4. Manufacturer profiles — who makes what, and how it reads
5. Category × manufacturer identity grid — the authored combinatorics
6. Composition, connection, lighting — sacrosanct rules
7. Anti-patterns — what Aurelia must never look like
8. Scene mood overlays — how the base palette flexes without breaking
9. Reserved expansion + governance — the living-doc contract
10. Identity architecture — the five-faction × five-activity × five-identity mapping

---

## 1. Voice

### 1.1 The one-sentence description

**Aurelia is warm-industrial grounded sci-fi with chunky palette-banded lighting, visible seams and wear, and legible faction identity — lived-in, hand-built, analog-future.**

Every design decision downstream of this doc gets tested against that sentence. If a choice doesn't serve "warm-industrial, grounded, lived-in, analog-future," it's wrong — regardless of how technically clean or visually punchy it might be.

### 1.2 Reference constellation

What Aurelia IS reaching toward:

- **The Expanse** — the Rocinante as an engineering diagram with patina. Believable hardware. Things bolt onto things. People live in ships that smell like coolant and instant coffee.
- **Hyper Light Drifter** — chunky palette-banded lighting. Discrete color bands read as stylistic choice, not as limitation. Every pixel intentional.
- **Alien (Nostromo) / Dark Star** — lived-in industrial grime. Corridors are narrow. Ceramics are scorched. Plastic has yellowed. This is not a showroom.
- **Into the Breach / FTL** — readable top-down silhouettes. Small canvases carrying rich faction identity. Modularity visible but composed.
- **Starfield (the good parts)** — manufacturer coherence. You know a Deimos ship from a Stroud-Eklund at a glance. The visual signature does work the HUD doesn't have to.

What Aurelia is NOT:

- **No Man's Sky's kaleidoscopic palette.** Over-saturated infinite variety reads as procedural soup. Aurelia values legibility over novelty.
- **Star Citizen's hyperrealism.** Photorealism costs more than it earns; the uncanny valley of almost-real-but-not is worse than confident stylization.
- **Destiny / Halo's clean power fantasy.** Those worlds are sculpted by armies of art directors for power-fantasy readability. Aurelia is a solo+AI-built game; our cost structure and our voice both point toward honest-industrial, not clean-heroic.
- **Cyberpunk neon as default voice.** Neon exists as a contextual overlay (§8), not the base. Crimson Reach stays crimson; it does not become magenta.

### 1.3 What "warm-industrial" means technically

Not a marketing phrase. A set of measurable claims:

- **Warmth skew ≈ +14.** Palette mean R channel exceeds mean B channel by ~14 units. This is a conscious decision: cool industrial (stainless steel studio) reads as sterile; warm industrial (oxidized copper, sodium lighting, oil-stained concrete) reads as inhabited.
- **Luminance range ≈ 240.** Wide enough for meaningful lighting contrast, narrow enough that nothing is pure-white or pure-black. The world has atmosphere; bloom and vignette carry the extremes, not raw pixel values.
- **Saturation mean ≈ 65.** Moderate chroma. Saturated enough that color identity is legible; muted enough that nothing cartoons.
- **Palette-snapped rendering as default.** Every surface pixel lands on a palette entry — no continuous gradients on materials. Discrete bands read as *metal under light*, not *computer gradient*. This is the Hyper Light Drifter lever, applied with industrial discipline.

### 1.4 What "lived-in" means technically

- **Wear is a parameter, not an afterthought.** Every material has a `wear_intensity`. Fresh-from-drydock ships read lighter; combat-veteran ships read scorched. Wear persists in save state; the galaxy ages with the player.
- **Seams are visible.** Panel gaps, weld lines, rivets. Connection-layer detail (§6.3) is how the ship reads as assembled hardware rather than a solid die-cast object.
- **Rivets and bolts use Poisson-disc placement.** Deterministic, even distribution without grid-visible regularity. Visible craft at close range.
- **No clean-room perfection.** Even Solari — the "polished mirror" faction — has reflection noise, edge scuffing, and micro-wear. No material is noise-free.

### 1.5 What "analog-future" means technically

- **Physical controls over holographic UI.** Where the game shows hardware, hardware reads as physical — switches, dials, vented panels, exposed conduit. Holographic elements exist (targeting overlays, faction insignia projections) but play supporting role.
- **Limited emissive budget.** Emissive pixels are precious. Engine cores, cockpit windows at night, warning lights, plasma effects. If everything glows, nothing reads as dangerous or powered.
- **Warm glow, cool sky.** Interior lights and engine plasma lean warm (plasma_core = 255/175/58). Void and cryo emissives stay cool (cryo_fractal = 127/225/255). The warm-cool contrast does narrative work: "you are in a metal tube; space is very cold."

### 1.6 Budget and ceiling

Aurelia is built by one developer + AI coding agents. Its visual ceiling is defined by:

- **Procedural discipline** — programmatic generation as medium, not fallback. The framework (`10_programmatic_generation_framework.md`) sets the capability; this Bible sets the voice.
- **Palette discipline** — 40 canonical entries organized into material bands + role table (§2). Additions require a Bible revision.
- **Material discipline** — 10 v1 materials (§3). Additions require justification: "existing material genuinely cannot carry this aesthetic."
- **Composition discipline** — unified-object lighting, typed connection points, silhouette-role awareness (§6). These are rules, not guidelines.

The ceiling is **credibly modern and intentional**, not photorealistic. Hyper Light Drifter ships look at the full-price RRP shelf and hold their own without a AAA art team. That's the move.

---

## 2. Canonical palette

*Promoted from Spike 03's balanced candidate (65% conservative + 35% high_contrast blend) into the band-structured form specified in framework §8.1. The spike's flat candidates remain as `tools/overhaul_spike/palette_candidates.py` for historical reference; this section is the production canon.*

### 2.1 Structure

Two tiers, disjoint by construction:

- **Material bands** — for material surfaces. Each material references its own shade band (4–5 palette entries, darkest → brightest). Material-rendering pixels are snapped to their band only. Prevents UI colors from accidentally becoming hull highlights (Spike 02 Finding 3).
- **Palette roles** — for everything non-material: void/sky, emissive cores, UI chrome, particles, glow-bleed. Not a fallback for material snap. Role-rendering pixels are snapped to role entries only.

A band entry never appears in the role table; a role entry never appears in a band. This disjointness is what makes compliance testable.

### 2.2 Material bands

```python
MATERIAL_BANDS: dict[str, tuple[tuple[int, int, int], ...]] = {

    # --- Default hull metal ---
    # Cool industrial steel. Base of most ships. Lighting range intentionally
    # wide so banded lighting has room to breathe.
    "steel": (
        (24, 30, 42),      # steel_shadow_deep    — 0: cast shadow, unlit panels
        (52, 62, 82),      # steel_shadow         — 1: lit ambient shadow
        (88, 100, 122),    # steel_base           — 2: lit base
        (136, 156, 188),   # steel_bright         — 3: lit highlight
        (190, 210, 238),   # steel_specular       — 4: edge gloss
    ),

    # --- Solari Chrome ---
    # Polished mirror — brightest material in the game. FORCED-WIDE band spread
    # to resolve Spike 01/02/03 Solari lighting failure: a naive narrow
    # chrome range collapses under palette-snap, so the band is hand-tuned
    # to span from pewter (darkest) to near-white (brightest) even though
    # "reality" would keep all chrome bright. Lighting legibility wins.
    "solari_chrome": (
        (82, 92, 108),     # solari_pewter        — 0: cast shadow (darker than pure chrome would be — see note above)
        (140, 152, 172),   # solari_dim           — 1: occluded chrome
        (200, 212, 226),   # solari_base          — 2: lit chrome
        (232, 240, 248),   # solari_bright        — 3: highlight
        (252, 253, 255),   # solari_mirror        — 4: specular near-white
    ),

    # --- Crimson Iron (Reach hull) ---
    # Patinated red-brown. Matte, heavy grain, lots of wear. The most
    # saturated faction material; its darkness sells "combat veteran."
    "reach_crimson": (
        (40, 10, 12),      # reach_shadow_deep    — 0: deep rust pit
        (78, 22, 24),      # reach_shadow         — 1: unlit patina
        (138, 42, 40),     # reach_base           — 2: lit crimson
        (186, 78, 62),     # reach_bright         — 3: lit highlight (warmer, near-orange)
        (224, 128, 92),    # reach_specular       — 4: rim glow (sunset orange)
    ),

    # --- Union Ceramic ---
    # Matte heat-tile. Off-white base, carbon scoring, warm undertone.
    # Utilitarian, not elegant. Think spacecraft heat-shield + rust streaks.
    "union_ceramic": (
        (78, 68, 58),      # union_shadow_deep    — 0: scorched underside
        (132, 118, 98),    # union_shadow         — 1: shadowed tile
        (202, 192, 170),   # union_base           — 2: lit tile
        (232, 222, 202),   # union_bright         — 3: lit highlight
        (248, 240, 222),   # union_specular       — 4: unscorched edge
    ),

    # --- Frontier Canvas ---
    # Welded patchwork, visible seams. The outlaw/salvage look. Cooler and
    # grittier than Union; panels don't match because they weren't designed
    # to match.
    "frontier_canvas": (
        (32, 26, 22),      # frontier_shadow_deep
        (62, 52, 44),      # frontier_shadow
        (108, 92, 72),     # frontier_base        — oxidized brown
        (160, 142, 112),   # frontier_bright      — exposed lighter patch
        (208, 192, 158),   # frontier_specular    — fresh weld silver-tan
    ),

    # --- Collective Composite ---
    # Science Collective lab equipment. Sterile-leaning blue-white with
    # a cooler cast than Solari. The clean-room faction.
    "collective_composite": (
        (40, 52, 68),      # collective_shadow_deep
        (90, 108, 128),    # collective_shadow
        (168, 192, 212),   # collective_base
        (210, 228, 242),   # collective_bright
        (240, 248, 254),   # collective_specular
    ),

    # --- Glass Viewport ---
    # Narrow band by nature — glass is mostly one tone. Emissive override
    # active at night (swaps to a role-table emissive entry).
    "glass_viewport": (
        (14, 28, 42),      # glass_shadow
        (30, 58, 80),      # glass_base_dim
        (52, 96, 126),     # glass_base
        (96, 146, 176),    # glass_bright         — reflected highlight
    ),
}
```

**Discipline notes:**

- Bands are defined **darkest-first**. Index 0 = cast shadow; index len-1 = specular highlight. Renderers lerp lighting value 0..1 across the band.
- **Solari's band is hand-tuned, not derived.** Spike 01/02/03 all showed that naive Solari bands (using palette chrome entries as-is) collapse to ~30 luminance units of spread and fail lighting tests. The Bible's Solari band forces a ~170-unit luminance spread by pushing index 0 down into pewter territory. The "reality" cost: Solari ships have darker shadow recesses than a real chrome mirror would. The legibility gain is worth it. This is the kind of call the Bible makes that the code can't.
- **Crimson's specular is warm-orange.** Not red. Combat-spec highlights on oxidized red iron read as sunset glow; a red-on-red highlight has no read. Intentional hue shift within the band.
- **Every band has 4–5 entries.** Glass is the only 4-entry band (narrow by design). All others are 5.

### 2.3 Palette roles

```python
PALETTE_ROLES: dict[str, tuple[int, int, int]] = {

    # --- Void / sky ---
    # Deep space, with enough midtone that silhouettes have context.
    "void_deep":        (8, 10, 17),      # primary background
    "void_mid":         (17, 20, 33),     # near-edge silhouettes, nebula valleys
    "void_light":       (29, 36, 53),     # distant starfield wash, scene ambient

    # --- Emissive cores ---
    # These bypass material snap entirely. Used for additive blends on top
    # of lit bases; also seed gradients for particle systems.
    "plasma_core":      (255, 175, 58),   # engine exhaust, primary warm emissive
    "plasma_hot":       (255, 225, 180),  # plasma center (bloom seed)
    "cryo_fractal":     (127, 225, 255),  # cryo weapons, coolant glow
    "ion_arc":          (198, 110, 255),  # ion weaponry, EW effects
    "voltaic_strike":   (255, 232, 108),  # voltaic weapons, arc flash
    "glow_warm":        (255, 200, 120),  # interior lights, bridge warmth
    "glow_cool":        (108, 185, 255),  # cryo/tech ambient

    # --- UI chrome ---
    # HUD layer. Disjoint from material bands so UI never accidentally
    # reads as material (and vice versa).
    "hud_cyan":         (85, 207, 236),   # primary HUD accent
    "hud_warning":      (245, 145, 55),   # yellow-orange warning band
    "hud_critical":     (245, 65, 65),    # red critical
    "hud_muted":        (108, 119, 142),  # disabled / secondary
    "hud_text":         (225, 230, 240),  # primary HUD text
    "hud_text_dim":     (160, 168, 185),  # secondary HUD text
    "hud_accent_warm":  (232, 180, 110),  # warm accent (faction cross-refs)

    # --- Details ---
    "rivet":            (20, 23, 30),     # rivet cores (dark)
    "rivet_gloss":      (110, 128, 155),  # rivet highlights
    "seam":             (14, 16, 22),     # panel seams
    "weld":             (178, 148, 92),   # weld-bead accent
}
```

**29 entries in PALETTE_ROLES. Plus material bands (29 band entries across 7 materials = 29).** Total canonical palette: **58 entries**, organized and testable. More than the framework's rough estimate of ~40, but the extras earn their place (wider material bands for legibility; split plasma into core + hot for bloom; split hud_text into primary + dim; explicit seam/weld/rivet_gloss entries instead of implicit variants).

### 2.4 Colorblind modes

Handled via **band-remap + role-remap functions**, not per-renderer code. A colorblind profile defines:

- A `band → band'` mapping for each material band (swapping the red-family band for a magenta-family, etc.)
- A `role → role'` mapping for emissive and HUD roles

Every renderer works unchanged. This is achievable because renderers already index by role name and band position, never by raw RGB.

Three colorblind profiles planned for v1 (details deferred to a Tier 3 doc): protanopia, deuteranopia, tritanopia. The palette's disjoint-tier structure is what makes this tractable.

### 2.5 Compliance tests

```python
def assert_band_compliance(
    surface: pygame.Surface,
    band: tuple[tuple[int, int, int], ...],
    tolerance: float = 2.0,
) -> None:
    """Material renders must land on band entries (post-snap). Tolerance
    is tight because snap output should be exact. Non-trivial violation =
    material renderer bug or mis-applied snap."""

def assert_role_compliance(
    surface: pygame.Surface,
    tolerance: float = 4.0,
) -> None:
    """Scene/UI renders must land on role entries. Tolerance is looser
    because particles and emissive bleed blend between roles."""
```

Both tests run in CI as part of the visual regression suite. Violations block merges.

### 2.6 Why these specific RGB values

They descend from Spike 03's balanced candidate, which the user chose after viewing the 4-palette comparison atlas. The balanced candidate itself was a 65/35 blend of:

- **conservative** — grounded, muted, faithful to the cultural guide
- **high_contrast** — same hue families but wider dynamic range

Picking 65/35 (leaning conservative) plus hand-tuned band-spread adjustments (Solari widened, crimson warmed at specular) produces the values above. Each palette entry has a documented reason. Additions or changes require that kind of reason.

---

## 3. Material library

A material is a parametric surface definition: a shade band (§2.2) plus rendering parameters. Materials are the primary unit of "what this thing is made of." Ten v1 materials, committed. Additions require justification per §9.

### 3.1 Material schema (canonical)

Promoted from framework §4.1:

```python
@dataclass(frozen=True)
class Material:
    name: str                      # "brushed_steel", "solari_chrome", ...
    band: str                      # MATERIAL_BANDS key (§2.2) — or None if emissive-only
    noise_scale: float             # 0.15-0.40 typical; lower = bigger patches
    noise_intensity: float         # 0 (clean) — 1 (heavy grain)
    wear_intensity: float          # baseline grime level before per-instance wear
    rivet_density: float           # rivets per 1000 px², 0 = none
    gloss: float                   # 0 (matte) — 1 (mirror)
    category_offset: int = 0       # per-category band-index shift (-1/0/+1)
    kind: Literal["solid", "emissive"] = "solid"
    emissive_role: str | None = None   # PALETTE_ROLES entry if kind == "emissive"
    signature_stripe_role: str | None = None  # optional PALETTE_ROLES accent
```

### 3.2 The ten v1 materials

| ID | Band | noise_int | wear | rivets | gloss | Notes |
|---|---|---|---|---|---|---|
| `brushed_steel` | `steel` | 0.18 | 0.15 | 1.0 | 0.30 | Default hull metal. Industrial honest. Most modules use this. |
| `solari_chrome` | `solari_chrome` | 0.06 | 0.04 | 0.3 | 0.75 | Polished, minimalist. Flagship/prestige aesthetic. Cyan stripe accent. |
| `crimson_iron` | `reach_crimson` | 0.35 | 0.45 | 1.5 | 0.12 | Patinated, scuffed, combat-veteran. Plasma-orange stripe accent. |
| `union_ceramic` | `union_ceramic` | 0.22 | 0.28 | 2.2 | 0.08 | Matte heat-tile with carbon scoring. Warning-orange stripe. |
| `frontier_canvas` | `frontier_canvas` | 0.40 | 0.55 | 0.8 | 0.10 | Welded patchwork. High wear, visible seams. Weld-bead accents. |
| `collective_composite` | `collective_composite` | 0.08 | 0.05 | 0.4 | 0.45 | Sterile lab clean. Low wear, moderate gloss. Cyan stripe. |
| `glass_viewport` | `glass_viewport` | 0.02 | 0.03 | 0.0 | 0.90 | Cockpit glass. Emissive override at night (swaps to `glow_warm`). |
| `plasma_energy` | — | — | — | — | — | Emissive. Uses `plasma_core` + `plasma_hot` roles with additive blend. |
| `cryo_fractal` | — | — | — | — | — | Emissive. Uses `cryo_fractal` + `glow_cool` roles. Crystalline pattern overlay. |
| `ion_field` | — | — | — | — | — | Emissive. Uses `ion_arc` role with arc-line detail. |

### 3.3 Category-offset defaults

Per framework §4.1 (Spike 02 Finding 4), per-category variation uses band-index shifts, not RGB multiplication. Defaults when the category isn't explicitly overridden:

| Category | category_offset | Effect |
|---|---|---|
| `weapon` | −1 | Shift one band entry darker. Weapons read as heavier, more serious. |
| `structural` | +1 | Shift one band entry brighter. Structurals read as cleaner, "fresh paint." |
| `cockpit`, `engine` | 0 | Base — no shift. |

A module's `category_offset` can override this default (e.g., a scorched-veteran structural uses -1 instead of +1). Module data declares this per-module.

### 3.4 Wear as a parameter, not a phase

`wear_intensity` in the material schema is the **baseline** wear — how grimy a fresh-from-factory instance looks. Per-instance wear is additive on top: `effective_wear = material.wear_intensity + instance.wear`, clamped to 1.0.

- `instance.wear = 0.0` → material looks like its spec
- `instance.wear = 0.5` → mid-life ship, visible combat history
- `instance.wear = 1.0` → battle-wrecked, scorched, heavily patinated

Instance wear advances slowly via combat damage, hull stress, and time. Persists across save/load. Never decreases except on explicit refit service (which becomes a station-economy hook).

### 3.5 Emissive rules

Emissive materials (`plasma_energy`, `cryo_fractal`, `ion_field`) differ from solid materials in three ways:

1. **They bypass palette-snap entirely.** Emissive pixels are additive-blended on top of the snapped base; they do not need to land on palette entries.
2. **They use role-table entries, not bands.** `plasma_energy` draws from `plasma_core` + `plasma_hot`; `cryo_fractal` from `cryo_fractal` + `glow_cool`; `ion_field` from `ion_arc`.
3. **They pulse.** Every emissive material has an animated intensity (default sine wave, period ~1.2s, amplitude 15% of base). Static emissive reads as dead; pulse reads as powered.

Emissive budget per ship: ≤15% of opaque pixels. Violating this makes the whole ship read as a light fixture rather than a vehicle.

### 3.6 When to add a material

The v1 list covers:
- Default industrial (steel)
- Three faction-signature hull looks (solari_chrome, crimson_iron, union_ceramic)
- Two outlier/variant hulls (frontier_canvas, collective_composite)
- Glass (viewport)
- Three emissive classes (plasma, cryo, ion)

That's enough for 80% of ship-builder output. New materials require:

1. A concrete asset that existing materials genuinely can't carry (not "would be nice to have").
2. A shade band added to §2.2 if solid, or role entries added to §2.3 if emissive.
3. A Bible revision note in §9.

**Likely future additions (flagged, not committed):**
- `voltaic_plate` — weapons with voltaic tech signature (§8 frames tech overlays)
- `sensor_glass` — radar/sensor dome material (category expansion per §15 framework)
- `shield_lattice` — emissive shield-field material
- `cooling_fin_ceramic` — textured heat-radiator material (cooling category)

---

## 4. Manufacturer profiles

Six manufacturers, aligned with production data (`data/ships/modules.json`). Each profile declares shape vocabulary, primary material, signature accent, and detail density. Manufacturer identity is orthogonal to faction identity — a Foundry module can be sponsored by Crimson Reach or Miners Union; the visual signature of the *build* is manufacturer-driven, the visual signature of the *paint* is faction-driven (§4.8).

### 4.1 Reyes-Kowalski (`reyes_kowalski`)

The workhorse. Civilian and contract-labor standard. You see more RK modules than any other brand in the Expanse. Moderate everything, priced to move, reliable over exceptional.

- **Primary material:** `brushed_steel`
- **Accent stripe:** `hud_text_dim` (understated grey)
- **Shape vocabulary:** `modular` — rectangles and rounded-rects; predictable proportions; engineering-diagram clarity
- **Detail density:** 0.5 (moderate) — visible rivets and panel lines, no flourish
- **Silhouette tendency:** boxy, symmetric, readable from any angle
- **Voice statement:** *"This works. Next."* — no marketing, no prestige play; parts catalog sensibility

### 4.2 Foundry (`foundry`)

Heavy industrial. The corp that builds capital-class powerplants, broadside batteries, quad mounts. Union-aligned in culture though not exclusively. Chunky, over-engineered, rivet-heavy.

- **Primary material:** `union_ceramic` (for hull panels) over `brushed_steel` (for structural cores)
- **Accent stripe:** `hud_warning` (safety-orange warning bands)
- **Shape vocabulary:** `modular` with chunkier proportions; thick structural bands; oversized rivets
- **Detail density:** 0.85 (high) — rivets everywhere, visible bolt-heads, structural reinforcement bands
- **Silhouette tendency:** wide, low, heavy-read
- **Voice statement:** *"Built for capital work. Will outlast the ship it's bolted to."*

### 4.3 Talon (`talon`)

Precision brand. Accuracy-focused weapons and cockpits; split-canopy designs, vectored thrust, dual-link weapon mounts. Favored by competitive pilots and prestige owners. Guild-aligned.

- **Primary material:** `solari_chrome` (polished) on visible surfaces; `brushed_steel` on internals
- **Accent stripe:** `hud_cyan` (electric cyan — precision signature)
- **Shape vocabulary:** `angular` — sharp edges, asymmetric splits, aggressive lines
- **Detail density:** 0.35 (low-moderate) — clean surfaces emphasized over rivets; visual signature in silhouette, not texture
- **Silhouette tendency:** asymmetric, aggressive, tech-forward read
- **Voice statement:** *"Every degree of accuracy earned in engineering — not bolted on."*

### 4.4 Sable (`sable`)

Low-signature brand. Recessed cockpits, concealed weapon bays, whisper drives. Collective-aligned (stealth-tech research). Dark, matte, minimal emissive.

- **Primary material:** `collective_composite` — dark variant (uses band shade entries 0–2 preferentially, rarely touches 3–4)
- **Accent stripe:** `hud_muted` (grey-blue — barely visible)
- **Shape vocabulary:** `rounded` — smoothed silhouettes, recessed features, no sharp protrusions
- **Detail density:** 0.25 (low) — smooth panels, minimal rivets, seams hidden
- **Silhouette tendency:** low-profile, compact, hard-to-read-against-void
- **Voice statement:** *"If they see you, we failed."* — Sable's entire aesthetic is negative-space

### 4.5 Meridian (`meridian`)

Efficiency brand. Fuel-economy engines, ion arrays, clean propulsion tech. Alliance-aligned (Frontier Alliance). Technical elegance without Talon's sharpness.

- **Primary material:** `collective_composite` (bright variant — uses band entries 2–4 preferentially)
- **Accent stripe:** `ion_arc` (violet — ion-tech signature)
- **Shape vocabulary:** `rounded` — curves over angles; gentle taper; organic-precision hybrid
- **Detail density:** 0.45 (moderate) — visible vents, fins, structural curves; rivets present but subordinate
- **Silhouette tendency:** curvy, efficient-read, suggests motion
- **Voice statement:** *"Every joule earned — by design, not muscle."*

### 4.6 Salvage-Rat (`salvage_rat`)

The scrap brand. Jury-rigged cockpits, scrapyard burners, recycled-part everything. Not corporate — an aesthetic label applied to gear assembled from whatever was available. Frontier-aligned by necessity.

- **Primary material:** `frontier_canvas` — heavy wear baseline, patchwork panels
- **Accent stripe:** `weld` (weld-bead tan — visible weld beads used as decorative accents)
- **Shape vocabulary:** `modular` with broken symmetry; panels don't match; visible mismatches
- **Detail density:** 0.75 (high) — heavy wear, many weld seams, mismatched rivets (some from one era, some from another)
- **Silhouette tendency:** asymmetric by accident, never by design; reads as "assembled, not designed"
- **Voice statement:** *"Found it. Bolted it. Flies."*

### 4.7 Manufacturer × material matrix (default pairings)

When a module doesn't override its material, these are the defaults:

| Manufacturer | Default hull material | Default weapon material | Default engine material |
|---|---|---|---|
| reyes_kowalski | brushed_steel | brushed_steel | brushed_steel + plasma_energy |
| foundry | union_ceramic | brushed_steel | brushed_steel + plasma_energy |
| talon | solari_chrome | solari_chrome | solari_chrome + ion_field |
| sable | collective_composite | collective_composite | collective_composite + cryo_fractal |
| meridian | collective_composite | brushed_steel | collective_composite + ion_field |
| salvage_rat | frontier_canvas | frontier_canvas | frontier_canvas + plasma_energy |

Modules can override per-instance. This table sets defaults only.

### 4.8 Faction color overlays

Factions (Commerce Guild, Miners Union, Frontier Alliance, Science Collective, Crimson Reach) express their identity as a **color overlay layer** applied on top of manufacturer visuals — not as a replacement of the manufacturer.

A Reach raider flying a Foundry chassis shows:
- Foundry's chunky silhouette + union_ceramic hull material (manufacturer)
- Crimson-Reach color overlay: signature stripes in `reach_crimson` family, faction insignia, plasma-orange running lights

Faction overlays are expressed through:
- **Stripe accents** (swap manufacturer default stripe role for faction role)
- **Signature emissive color** (Union = warm, Guild = cyan, Reach = plasma-orange, Collective = cool, Alliance = violet)
- **Insignia decal** (hand-authored pixel art, overlaid at specific module positions)
- **Optional hull tint** — a one-band-index shift in the manufacturer's base material, if the faction has strong enough color identity (Crimson Reach ships read crimson-dominant; Miners Union ships read warm-yellow-dominant)

This keeps manufacturer identity legible while letting faction affiliation read as a second layer. Applicable to the ship builder UI (drydock filter by manufacturer OR by faction gate), combat (faction-identification at a glance), and the broader worldbuilding (faction ownership of Foundry vs Talon fleet compositions).

---

## 5. Category × manufacturer identity grid

The authored combinatorics that prevent the ship builder from feeling like random parts stapled together. Each manufacturer × category cell has a defined visual signature: what a Talon cockpit looks like that a Foundry cockpit doesn't.

### 5.1 The grid (v1 — 4 categories × 6 manufacturers)

| | Cockpit | Engine | Weapon | Structural |
|---|---|---|---|---|
| **reyes_kowalski** | Rectangular cabin, grid canopy, symmetric | Boxy thruster with visible cowling | Symmetric mount, barrel centered | Rectangular plate, grid rivets |
| **foundry** | Oversized bridge, multi-pane viewport, chunky frame | Capital-scale nozzle bank, reinforcement bands | Heavy housing, barrel recessed into armor | Thick plates, oversized rivets, structural bands |
| **talon** | Split canopy, asymmetric glass panes, aggressive prow | Bifurcated thrust, visible vectoring hardware | Twin-link barrels, precision hardpoint geometry | Angular plate, diagonal seams |
| **sable** | Recessed cockpit, flush canopy, minimal protrusion | Whisper-drive — flat exhaust, no visible plasma | Concealed bay door, barrel flush with hull | Smooth plate, seams hidden, matte finish |
| **meridian** | Rounded canopy, streamlined prow | Curved nacelle, visible cooling fins, ion-arc glow | Elegant hardpoint, curved housing | Curved panel edges, visible cooling vents |
| **salvage_rat** | Mismatched canopy panes, visible welds on frame | Exhaust from mismatched parts, uneven glow | Weapon bolted at odd angle, visible mount-shim | Patchwork plate, welds across seams, no two panels alike |

### 5.2 The grid's purpose

- **Readability at ship-builder shopping UI:** the player scrolling through 20+ cockpits can identify manufacturer by silhouette alone without reading the name label. A Talon cockpit *looks like* a Talon cockpit.
- **Readability at combat identification:** a Sable raider reads as stealthy-bad-news immediately; a Meridian ship reads as precision-tech; Foundry as heavy-industrial threat.
- **Readability at campaign narrative moments:** "the ship on the horizon is Crimson Reach, using Foundry chassis" is communicated by silhouette + color overlay without exposition.

### 5.3 Reserved slots for future categories

Per framework §15, future categories need matrix cells pre-reserved (not implemented) so expansion doesn't force retroactive manufacturer redesign. Reserved:

| Future category | Expected silhouette-role | Material tendency |
|---|---|---|
| `radar` | appendage | glass + light-metal; emissive sweep |
| `targeting` | internal | hidden; faction-color glow through viewport |
| `sensor_array` | appendage | cluster of antennae, glass domes |
| `cooling` | hull or appendage | fin/vent shapes, thermal emissive glow when hot |
| `shield_emitter` | hull | lattice texture, cool emissive at active |
| `electronic_warfare` | appendage | antenna dish + ion-arc emissive |
| `comms` | appendage | high-gain dish, blinking status light |
| `cargo_external` | hull | strapped containers, frontier-canvas wear |
| `repair_drone_bay` | hull | recessed bay door, mechanical-looking internals |

Each manufacturer should — when these categories are implemented — express its voice through the category. A Talon radar is precision-polished with narrow beam; a Foundry radar is oversized dish with warning stripes; a Salvage-Rat radar is a swap-meet antenna bolted onto a bent mast.

### 5.4 Grid governance

The grid is canonical. Any future module authored for Aurelia must fit a grid cell. Mixing manufacturer visuals within one module ("this is sort of Talon but with Foundry rivets") violates identity. Permitted exceptions:

- **Salvage-Rat modules explicitly reference other manufacturers in their wear/patchwork.** A Salvage-Rat cockpit with visible former-Foundry plating is canon — it's a junk-cockpit made from a wrecked Foundry ship. The "Salvage-Rat-ness" is the visible mismatch itself.
- **Hybrid faction modules (rare, story-linked)** may legitimately break cell boundaries. These require narrative justification and are hand-authored, not procgen.

---

## 6. Composition, connection, lighting

Sacrosanct rules for how modules come together into ships. Violations produce the "collage of parts" look we're explicitly escaping from the current ship builder.

### 6.1 Lighting direction

**Upper-right, 45° down from horizontal.** One global light across the entire ship silhouette. No per-module local lighting.

- Ship rendered to a silhouette mask first, then lit as a single object
- Light direction baked, not animated (static at runtime — per-frame lighting is forbidden)
- Rim-lighting for hero moments (player ship in combat, boss phase transitions, legendary drops) adds a faint inverse-direction glow; otherwise absent

### 6.2 Composition pipeline

Per framework §6.2, executed as seven phases:

1. **Silhouette pass** — union of all placed-module bounding shapes; rasterize to ship-silhouette mask
2. **Per-module base pass** — each module's material fill at its placed position, alpha-masked to silhouette
3. **Global lighting pass** — single directional light across the whole silhouette; lerp within each material's shade band
4. **Connection detail pass** — render seams between adjacent modules (§6.3)
5. **Decoration pass** — rivets (Poisson-disc), wear patches, signature stripes, faction insignia
6. **Emissive pass** — additive blend, pulse modulation, bloom-seed for post-processing
7. **Palette snap** — all non-emissive pixels to their material's shade band

### 6.3 Connection vocabulary (typed)

Per framework §15.3, connection points carry a `ConnectionKind`:

| ConnectionKind | Visual treatment | Example |
|---|---|---|
| `structural` | Thin dark weld seam (`seam` role); same-manufacturer welds darker, cross-manufacturer welds warm with `weld` role | Engine bolted to hull backbone |
| `data` | Thin cable run, minor detail, no glow | Targeting computer to cockpit |
| `power` | Glowing line in plasma/ion color; animated pulse | Reactor to weapon mount |
| `mount` | Bolted attachment, visible bolts, no seam gradient | Radar on mast, weapon on hardpoint |
| `coolant` | Pipe connection, steam/vent glow if active | Cooling fin to power core |

The composer enforces compatibility (matching kinds between connection points). Mismatches surface in the ship builder UI as warnings.

### 6.4 Silhouette discipline

- **One connected component.** A ship silhouette must be topologically one piece (per Spike 02 Finding 1). The composer flags disconnected output as build error.
- **No module overhangs its declared bounding box.** Every material pixel lies within the module's extent.
- **Overlap is permitted and encouraged for hull modules** — forces coverage-level connectivity rather than edge-adjacent fragility (Spike 02 finding).
- **Appendage modules (radar, antenna) connect via a single point, not overlap.** Distinct silhouette treatment.

### 6.5 Detail density budgets

Per framework §15.5, per-category detail-density expected ranges (for critique harness):

| Category | detail_density range | Rationale |
|---|---|---|
| cockpit | 0.08 – 0.25 | Canopy is mostly smooth glass; frame adds moderate detail |
| engine | 0.12 – 0.30 | Thruster cowlings + emissive detail |
| weapon | 0.10 – 0.28 | Mount + barrel; moderate |
| structural | 0.15 – 0.35 | Rivet-heavy, seam-rich — the "busy" category |
| radar (future) | 0.25 – 0.45 | Legitimately busy — mesh, array, antennae |
| shield_emitter (future) | 0.05 – 0.15 | Smooth surfaces with occasional lattice — low density base |

### 6.6 Wear carryover

A ship's `wear` is averaged across its modules for rendering purposes, but per-module wear can exceed or fall below ship-average (a recently-replaced part on an old ship reads fresh on a patinated frame). This contrast is desirable — it tells ownership-history stories.

---

## 7. Anti-patterns

Explicit list of what Aurelia must not look like. Named so reviewers (human and agent) can flag them.

### 7.1 GenAI-image tells

The whole reason we committed to procedural generation. Things that read as "this was AI-generated":

- **Melty/incoherent small details.** Rivets that aren't circles. Seams that branch and rejoin. Text or symbols that aren't readable.
- **Over-elaborate backgrounds that don't serve the subject.** Aurelia's backgrounds are purposeful starfields and nebulae, not baroque cosmic events.
- **Inconsistent lighting direction within a single image.** We have one global light; AI-gen often has none.
- **Uncanny-valley semi-realism.** Either clearly stylized (what we do) or clearly photorealistic (what we don't attempt) — never in between.

### 7.2 Over-saturated fantasy sci-fi

- **Rainbow emissive.** Everything glows purple-cyan-magenta-green. Aurelia's emissive budget is ≤15% (§3.5) with mostly warm or mostly cool per scene.
- **Crystal spires, biomechanical organic ships, dragon-fighters.** Aurelia is analog-industrial. No biological ships. No magical-crystal tech.
- **Over-sized epic backgrounds that dwarf the action.** Ships in combat read at the scale of ships, not ants beneath nebulae.

### 7.3 Clean-studio sterility

- **Perfect reflective surfaces with no wear.** Even Solari/Talon chrome has scuffing (§3.2, `solari_chrome` wear_intensity = 0.04 is non-zero deliberately).
- **Flat untextured fills.** Every material has noise. Even Solari's minimum noise_intensity = 0.06 is visible at close range.
- **No rivets anywhere.** Rivets are part of the visual voice. Exception: Sable's stealth-flush aesthetic (rivet_density default 0.25, still non-zero).

### 7.4 Collage-of-modules

- **Edge-adjacent modules producing visible gaps.** Per Spike 02 Finding 1. Enforce via connectivity test.
- **Per-module lighting that doesn't unify.** Every module lit as its own mini-object. Enforce via unified-object render pipeline (§6.2).
- **Manufacturer-mixing within a single module.** Talon-like cockpit with Foundry rivets. Breaks identity grid (§5.4).

### 7.5 Cyberpunk-as-default drift

- **Neon base palette.** Per Spike 03 finding: neon reserved for contextual overlays (§8.2), not base. If routine ship renders start reading purple-magenta by default, the palette has drifted.
- **Magenta Reach.** Crimson Reach stays crimson. If faction color identity drifts toward cyberpunk-pink, retcon.
- **All-emissive HUD.** UI elements use `PALETTE_ROLES` hud entries; emissive over-saturation in UI reads cyberpunk, not grounded.

### 7.6 The "couldn't afford art" read

The whole framework is built to avoid this. Signals it's happening:

- Ships with no distinct silhouette from this manufacturer vs that one (identity grid failure)
- All ships of one manufacturer look identical (variation failure)
- Detail density too low (flat-lazy read) or too high (unreadable-noise read)
- Palette collapsed to grey-brown (saturation failed)
- Emissive absent (no visual hierarchy)

When any of these surface in review, the fix is in the framework discipline, not "add more detail" or "saturate more."

---

## 8. Scene mood overlays and post-processing

The base palette carries the default voice. Specific scenes and contexts apply **mood overlays** — tints, vignettes, post-processing — to flex the voice without breaking the base.

### 8.1 Overlay philosophy

- The base palette is sacrosanct at the *material and render* level
- Overlays apply AFTER the unified-object render, as post-processing
- An overlay never replaces palette values; it tints/dims/boosts them
- Scene overlays are reversible (leaving the scene restores base)

### 8.2 Committed scene overlays

| Overlay | Where it applies | Effect | Notes |
|---|---|---|---|
| **Combat intensity** | Combat view, phases 2+ | Slight warm tint (+5 warmth), vignette strengthens | Heightens pulse |
| **Red line (critical HP)** | Combat, player HP ≤ 20% | Strong warm tint, vignette pulses red-tint | Alarming — works against base voice intentionally |
| **Station interior warm** | Cozy/merchant stations | Warm tint + soft bloom boost | "Welcome to a place with lights" |
| **Station cold-industrial** | Mining/industrial stations | Slight cool tint + higher grain | "You are in a cold metal tube" |
| **Cyber-district (neon)** | Specific story stations (e.g., black-market hubs) | Neon palette's emissive roles swap in; `plasma_core` → `(255,130,180)` hot pink; `hud_cyan` gets electric-cyan treatment | Per Spike 03 — neon lives here |
| **Nebula (story-coded)** | Specific nebula systems | System-specific tint (one of: violet, green-acid, rust-red) | Narrative flag on system |
| **Crimson Reach territory** | Reach-controlled systems | Subtle crimson cast + warning-orange emissive boost | Reinforces faction presence |
| **Sable stealth gameplay** | Stealth infiltration sequences | Strong cool tint, vignette darkens, emissive dim | Tonal + mechanical |

### 8.3 Post-processing pipeline

Per framework §9.2, the pipeline order:

1. Bloom extract (emissive pixels exceed threshold)
2. Bloom blur (gaussian, 2-pass)
3. Bloom composite (additive)
4. Chromatic aberration (edge-weighted, subtle)
5. Scene tint overlay (§8.2)
6. Vignette
7. Noise/grain overlay (very subtle — ~3% intensity)

UI renders AFTER post-processing — HUD stays crisp regardless of scene tint.

### 8.4 Mood-overlay discipline

- **No more than one mood overlay active at a time.** Combat intensity + red-line is one overlay with two phases, not two stacked.
- **Overlays are declared per-scene, not per-frame.** Scene transitions fade overlays in/out over 0.5–1.0s.
- **Overlays never stack with scene tints.** A nebula tint replaces the base tint; a combat overlay layers on top of neither.

---

## 9. Reserved expansion, governance, living-doc rules

### 9.1 Reserved palette-band naming space

For future material classes (per framework §15.4), these band names are **reserved**. Do not use these keys for other purposes. When the category expansion lands, these become real bands:

- `sensor_glass` — translucent green-tint for radar/sensor domes
- `electronics_emissive` — for targeting-computer window glow, sensor-readout panels
- `cooling_vent` — textured metal with heat-gradient emissive
- `radar_mesh` — latticed reflective surface
- `shield_field` — emissive lattice, cool blue-cyan family
- `voltaic_plate` — lightning-etched metal for voltaic-tech weapons
- `cryo_frost` — frost accumulation on cryo weapons and hulls

These are noted in-code when the implementation lands; until then, nothing uses these names.

### 9.2 Reserved scene overlay names

For scene overlays not yet implemented but likely:

- `scene_derelict` — abandoned wrecks; dim, cool, high grain
- `scene_sandstorm` — atmosphere flight, dust-yellow tint + heavy grain
- `scene_boss_reveal` — phase-transition overlay for legendary encounters
- `scene_credits` — end-sequence mood (TBD per narrative team)

### 9.3 When this Bible changes

Triggers for Bible revision:

1. **New material needed** (per §3.6 rules) — author proposes, Bible gets a new material entry and band (if solid) or role entries (if emissive)
2. **New manufacturer** — per cultural-guide revision; Bible §4 gains a profile
3. **New category** — Bible §5 extends identity grid; §3 may add materials
4. **Palette drift noticed in review** — palette is the foundation; drift is corrected in the Bible, then the code
5. **Failure mode observed in play** — surfaces in §7 as new anti-pattern; visual regression test added

Revisions are versioned: v1, v1.1 (minor — add material), v2 (major — restructure palette, significant anti-pattern additions).

### 9.4 Who decides

This is a solo-developer project with agent collaboration. In practice:

- **User** (the solo developer) has final say on voice decisions (§1), palette (§2), and manufacturer identity (§4)
- **Agent** proposes revisions when implementation surfaces issues; user approves
- **Codebase** is secondary: if code and Bible disagree, Bible wins or Bible revises — never silent code drift

### 9.5 Out of scope

Intentionally excluded from this Bible (handled by other docs):

- **UI layout and typography** — Tier 3 `42_ui_chrome_components.md` (not yet written)
- **Particle/VFX vocabulary** — Tier 3 `41_vfx_particle_vocabulary.md` (not yet written)
- **Narrative content** — `requirements/cultural_guide.md`, `requirements/dialogue_writing_guide.md`
- **Audio/sound design** — separate (not yet scoped)
- **Specific portraits and character art** — hand-authored pixel art, not procedural (framework §11.5)

### 9.6 Dependencies

- **Depends on:** `00_master_plan.md` (umbrella philosophy), `10_programmatic_generation_framework.md` (mechanics)
- **Informs:** all Tier 2 per-system overhaul docs; all procedural renderers; all visual regression tests
- **Provenance:** Spikes 01 / 02 / 03 (recorded in `SPIKE_0{1,2,3}_FINDINGS.md`)

### 9.7 Revision history

- **v1** (this document) — initial canonical Bible informed by all three prototype spikes and the balanced palette decision.
- **v1.1** — §10 Identity Architecture added after corpus coherence review. Formalizes the five-faction × five-activity × five-identity pattern that emerged across Tier 2 docs.

---

## 10. Identity architecture

*Added v1.1 after corpus coherence review. This section names a pattern that emerged from the Tier 2 overhaul work rather than one that was pre-designed. Naming it makes it canonical — future content gets a test against this structure instead of drifting from it.*

### 10.1 The mapping

Aurelia's five factions map to five primary activity systems, each carrying a playable identity:

| Faction | Activity | Identity | Voice pivot from base |
|---|---|---|---|
| Commerce Guild | Trading (34) | **The Merchant** | warm-industrial + data-dense brutalism |
| Crimson Reach | Combat (30) | **The Captain** | warm-industrial + cinematic weight |
| Miners Union | Mining (32) | **The Prospector** | warm-industrial + solidarity labor |
| Frontier Alliance | Salvage (36) | **The Salvager** | warm-industrial + haunted archaeology |
| Science Collective | Refining (37) | **The Fabricator** | warm-industrial + craft precision |

**Every identity pivots from the base voice (§1.1) rather than contradicting it.** The Fabricator's clean/precise register and the Salvager's haunted register are both *still* warm-industrial; they inflect the register rather than replace it. This is the Bible's coherence test: *does this pivot from, or contradict, warm-industrial?*

### 10.2 Identity treatment depth

Not all five identities receive identical treatment:

- **Full identity treatment** — Mining (32), Salvage (36). Main chaptered campaign + skill voices + thought cabinet + optional content tracks + persistent journal. These are **optional deep pools** — a player chooses to specialize.
- **Lighter identity treatment** — Refining (37). Identity + skill voices + thought cabinet + seasonal events (no chaptered campaign). Optional but with lower narrative density.
- **Visual-overhaul scope only** — Combat (30), Trading (34). No chaptered campaign, no thought cabinet, no mini-campaign narrative arc. These are **primary gameplay systems everyone engages with** — identity comes from accumulated play, not authored campaign.

This asymmetry is deliberate. Systems that players *must* engage with (combat, trade) carry their identity through UX, palette, and encounter content. Systems players *choose* to inhabit (mining, salvage) earn authored narrative depth.

### 10.3 Cross-identity acknowledgment discipline

Identities exist in parallel but should acknowledge each other at key moments. Examples:

- Augustyn (mining mentor) may mention salvaged wrecks he worked decades ago — cross-references salvage's Named Wrecks
- Mattsen (salvage broker) notes when Fabricator peers request specific salvage types — cross-references refining's commission clients
- Fabricator correspondence from Collective peers may reference deep-seam ingredients as coming from a Prospector's work
- Combat encounter NPCs occasionally comment on player reputation earned in other tracks ("Heard about that Signal Ship work")

Each cross-reference is ONE LINE in dialogue. ~30-40 total lines across the corpus adds cross-identity tissue without scope expansion.

Discipline: cross-references flatter the player's accumulated identity. They do not gate content or provide mechanical reward — they're atmospheric acknowledgment that the Expanse *notices* the player's work.

### 10.4 Pivot constraints per identity

Each pivot direction has a limit beyond which it contradicts the base voice:

| Identity | Pivot direction | Constraint (beyond which we break base voice) |
|---|---|---|
| Prospector | Warm-industrial + solidarity | Do not drift into communist-workers' opera; Aurelia is union-labor-grounded, not political-propaganda |
| Salvager | Warm-industrial + haunted | Do not drift into gothic horror or Lovecraftian dread; Aurelia is weighted-industrial, not cosmic-alien |
| Fabricator | Warm-industrial + craft precision | Do not drift into sterile clean-room or minimalist-Apple; Aurelia's precision is craft-precision, not corporate-pristine |
| Captain (combat) | Warm-industrial + cinematic weight | Do not drift into space-opera melodrama; cinematic weight comes from grounded consequence, not theatrical staging |
| Merchant (trading) | Warm-industrial + data density | Do not drift into cyberpunk-neon or hedge-fund-finance; Aurelia's commerce is data-dense but industrial-honest, not synthwave |

### 10.5 Identity selection as worldbuilding

A player who completes the Prospector's Road, engages with the Wrecker's Log, and reaches Fabricator master tier has effectively **walked Aurelia's cultural geography through work**. They've inhabited union-labor, frontier-archaeology, and collective-craft in sequence. Their character has depth no single campaign path can produce.

This is the payoff: Aurelia isn't a linear story you complete. It's a cultural space you *move through* by choosing what work matters.

### 10.6 Future identity additions

New factions or activities added to Aurelia must declare their pivot from base voice explicitly. Adding an identity that contradicts warm-industrial (e.g., a horror-coded faction, a comedy-coded activity) is a major Bible revision, not an additive change.

Extending existing identities with new content (more Chapters, new skill voices, more optional content) is additive and follows existing patterns.

---

*Next: per-system overhaul docs (Tier 2). First candidate: space combat visual overhaul, since it's the highest-visibility system for this Bible's discipline to prove itself in.*
