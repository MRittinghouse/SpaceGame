# VFX Particle Vocabulary

> **Status:** DESIGN — Tier 3 parallel-track doc. Formalizes the particle taxonomy already present in `engine/particles.py` (610 lines, object-pooled, 15+ shared presets) and the domain-specific VFX files built on top. The engineering is in place; this doc defines **vocabulary and discipline** — when to use which preset, how to respect the palette (AB §2), and how elemental identity (combat's five elements) surfaces through particles.
>
> Inherits from `10_programmatic_generation_framework.md §3` (primitive vocabulary), `20_aesthetic_bible.md §2` (palette) and §3.5 (emissive rules). Referenced by every Tier 2 overhaul doc.

---

## Table of Contents

1. Current state — honest assessment
2. Particle philosophy — the discipline
3. Shared particle taxonomy
4. Domain-specific VFX discipline
5. Elemental particle vocabulary (combat)
6. Palette compliance for particles
7. Performance discipline
8. Screen effects and backgrounds
9. Anti-patterns
10. Governance
11. Out of scope

---

## 1. Current state — honest assessment

Factual snapshot per survey of `particles.py`, `combat_vfx.py`, `mining_vfx.py`, `salvage_vfx.py`, `refining_vfx.py`, `backgrounds.py`, `screen_effects.py`.

### 1.1 What's already in place — the foundation

- **Shared particle engine** (`particles.py`, 610 lines):
  - `Particle` dataclass — position, velocity, life, color-gradient, size-gradient, gravity, glow, blend mode
  - `ParticleConfig` preset system — parameterized emission recipes
  - `ParticlePool` object pool (max 500 particles) — zero per-frame allocation
- **15+ shared presets** already defined as module constants:
  - `SPARK_BURST`, `MINING_DUST`, `SCAN_PULSE`, `WARP_TRAIL`, `COLLECT_SPARKLE`, `CLICK_HIT`, `DRONE_SPARK`, `STAR_TWINKLE`, `LASER_HIT`, `MISSILE_EXPLOSION`, `SHIELD_IMPACT`, `HEAL_SPARKLE`, and more
- **Domain-specific VFX files** compose these presets into system-appropriate effects:
  - `combat_vfx.py` (999 lines) — shield ripples/break/restore, damage states, destruction sequences, atmosphere
  - `mining_vfx.py` (430 lines) — depth layer atmospheres (5 zones), layer transitions
  - `salvage_vfx.py` (617 lines) — derelict atmospheres (3 types), corruption overlays, scan pulses
  - `refining_vfx.py` (464 lines) — forge heat levels (5 tiers), mastery momentum, buffer pressure
- **Backgrounds** (`backgrounds.py`, 122 lines) — procedural parallax starfield, seed-deterministic
- **Screen effects** (`screen_effects.py`, 90 lines) — vignette, screen shake

### 1.2 What's weak — the central gap

**No vocabulary document.** The 15+ presets exist as code constants. There is no canonical "when to use `SPARK_BURST` vs `CLICK_HIT`" reference. Domain-specific VFX files invent per-use parameters each time rather than reaching for defined vocabulary. Result: subtle inconsistencies — two systems emit similar effects at different parameters, and the visual discipline drifts.

The engineering is *coherent*. The discipline is *informal*.

### 1.3 Secondary gaps

**Gap 1: No elemental taxonomy for combat.** Combat's five elements (Kinetic / Plasma / Ion / Cryo / Voltaic per `30_overhaul_space_combat.md` §4.3) each need distinct particle visual signatures. Currently `LASER_HIT` and `MISSILE_EXPLOSION` are element-agnostic — every weapon, regardless of element, produces similar particle behavior with a color shift at best.

**Gap 2: Palette drift risk.** Existing particle colors are set in per-preset `start_color` / `end_color` tuples. Mostly these match palette roles; occasionally they drift (hand-tuned RGB values that don't correspond to a canonical role). No automated compliance check.

**Gap 3: No cross-system coordination on "which preset for which moment."** Combat emits `LASER_HIT`; ship-builder emits something else for module-slot activation; salvage emits `SCAN_PULSE` — but overlapping moments (e.g., a UI-level confirmation) might use different presets in different views. Coordination is absent.

**Gap 4: Performance ceilings not documented.** Pool cap is 500, hard-coded. Per-scene reasonable budgets (combat with destruction + shields + projectiles + atmosphere) aren't defined. Overflow silently drops new emissions, which is fine mechanically but can undermine cinematic moments if it happens at the wrong time.

**Gap 5: No emissive-budget enforcement.** AB §3.5 committed to "emissive ≤15% of opaque pixels per ship." At the particle level, this implies some presets (especially `MISSILE_EXPLOSION`, `SHIELD_IMPACT`, plasma trails) burn emissive budget generously. No mechanism checks this.

### 1.4 What this doc addresses

- Gap 1 (elemental taxonomy) via §5 combat elemental vocabulary
- Gap 2 (palette drift) via §6 compliance rules + migration from hand-tuned RGB to palette roles
- Gap 3 (cross-system coordination) via §3 shared preset canonical use cases
- Gap 4 (performance ceilings) via §7 budget guidelines
- Gap 5 (emissive budget) via §6 emissive-share discipline

---

## 2. Particle philosophy — the discipline

### 2.1 The six rules

**1. Every particle is palette-snapped or palette-consistent.** RGB values in particle configs must either be exact palette-role lookups OR within-band gradients. Raw hand-tuned hex values are banned post-migration.

**2. Every particle has a reason.** Ambient particles carry mood (dust motes = inhabited space); gameplay particles carry feedback (click hit = acknowledgment of action); cinematic particles carry weight (destruction fragments = consequence). A particle without a reason is noise to cull.

**3. Particles obey the emissive budget** (AB §3.5). Emissive-bright particles are expensive in visual currency; use them for signal, not decoration. At any given frame, emissive-bright particle pixels should not exceed ~15% of the scene's total opaque pixel count.

**4. Particles respect the shared engine.** No system rolls its own particle system. All particle emission flows through `ParticlePool`. New particle *types* may extend the engine (with coordination); new emission *patterns* compose existing types.

**5. Particles are additive, not subtractive.** Particles layer on top of rendered content. They do not modify underlying pixels (except via blend modes); they add. A particle system removed mid-development should leave the underlying render still coherent.

**6. Particles are performance-budgeted per scene.** The pool is a shared resource (max 500). Systems that emit heavily in one frame must coordinate — combat's destruction sequence is cinematic and gets budget priority; ambient dust must yield.

### 2.2 Philosophy per system register

Particle density varies by register (established by AB §1):

- **Industrial / grounded scenes** (station hub, ship builder) — sparse particles; dust, steam, occasional spark. Ambient carries mood; particles punctuate.
- **Mechanical-intensity scenes** (combat, destruction, dual techs) — dense particles acceptable; emissive layered; cinematic moments burn budget.
- **Investigative scenes** (salvage, ground exploration) — tension through sparse, specific particles; occasional anomalous particle reads as a *signal*.
- **Craft scenes** (mining, refining) — rhythmic particle emission (click by click, forge pulse by pulse); particles as feedback-rhythm.

### 2.3 Relationship to framework and Bible

The vocabulary inherits from:

- **Framework §3 primitives** — particles are *built from* primitives (lines, circles, polygons, noise). Particle configs are recipes; primitives are ingredients.
- **Bible §2 palette** — all particle colors pull from palette roles. Emissive particles use `PALETTE_ROLES` emissive entries (`plasma_core`, `cryo_fractal`, `ion_arc`, `voltaic_strike`, `glow_warm`, `glow_cool`). Material-surface particles can use material-band entries.
- **Bible §3.5 emissive rules** — budget discipline; emissive bypasses snap; pulse modulation canonical.

---

## 3. Shared particle taxonomy

The canonical catalog. Each preset has a documented behavior, use case, and typical parameters. **Systems must use existing presets when a preset matches the need.** New presets require §10 governance justification.

### 3.1 Core presets (universal)

| Preset | Behavior | Canonical use | Palette source |
|---|---|---|---|
| `CLICK_HIT` | Small spark burst, 4-8 particles, 0.15s life, outward radial | UI feedback; tactile confirmation (trading buy, builder place, mining click tier 1) | `hud_text` + `glow_warm` |
| `SPARK_BURST` | Larger spark cluster, 12-18 particles, 0.35s life, gravity-down | Moderate impact (mining click tier 2, activity unlock, module rotate) | `plasma_core` + `glow_warm` |
| `COLLECT_SPARKLE` | Rising glints, 6-10 particles, 0.8s life, upward drift + fade | Resource pickup, ore collection, positive outcome | `cryo_fractal` + `glow_cool` |
| `HEAL_SPARKLE` | Soft green sparkles, upward, 0.8s | Shield regen, HP restore, healing actions | Green-tint gradient from palette (new role TBD) |
| `STAR_TWINKLE` | Single-point alpha oscillation, long life (~3-5s) | Background ambient starfield | `hud_text` at varying alpha |
| `MINING_DUST` | Particle cloud, gravity-affected, 1.5-2s life | Mining-specific dust (rock fragment, atmosphere) | `frontier_canvas` band + `void_light` |
| `DRONE_SPARK` | Tiny colored dots, 0.3s, emitted from drone sprites | Auto-drill / drone operation | `plasma_hot` |

### 3.2 Combat-specialized presets

| Preset | Behavior | Canonical use | Palette source |
|---|---|---|---|
| `LASER_HIT` | Radial burst with horizontal streak, 0.3s | Laser projectile impact | Element-specific (§5) |
| `MISSILE_EXPLOSION` | Spherical expanding cloud + secondary sparks, 0.6s | Missile detonation | `plasma_core` + `plasma_hot` (kinetic default) |
| `SHIELD_IMPACT` | Concentric ring from impact point + fragment sparks, 0.25s | Shield hit (directional) | `cryo_fractal` (default) or element-specific |
| `WARP_TRAIL` | Elongating streak particles, 0.5s, emitted during travel | Ship travel animation; jump sequence | `plasma_hot` + `glow_warm` |
| `EXPLOSION_FRAGMENT` | Rotating polygon with gravity + fire trail, 0.9s | Destruction sequence ship fragments | Material band dark + `plasma_core` fire |
| `DESTRUCTION_SECONDARY` | Offset explosion burst, 0.5s, 4× staggered | Secondary explosions during destruction | `plasma_core` + `glow_warm` |

### 3.3 Scanning and detection presets

| Preset | Behavior | Canonical use | Palette source |
|---|---|---|---|
| `SCAN_PULSE` | Expanding ring with decreasing alpha, 0.4s | Salvage scan, sensor ping, dialogue-mode initiation | `cryo_fractal` ring |
| `QUALITY_BURST_GOOD` | Blue sparkles, 8 count, 0.6s | Good-quality salvage extraction | `hud_cyan` |
| `QUALITY_BURST_EXCELLENT` | Gold sparkles, 15 count, 0.8s | Excellent-quality salvage extraction; S-grade refining | `hud_warning` + gold tint |

### 3.4 Atmosphere presets

| Preset | Behavior | Canonical use | Palette source |
|---|---|---|---|
| `AMBIENT_DUST` | Slow-drifting small particles, very long life (~5s) | Combat atmosphere, ground interior, station backdrops | Contextual — scene-tint |
| `AMBIENT_VAPOR` | Brownian-motion particles, slightly glowing, 3s life | Lab / science atmosphere, refining forge | `glow_cool` faint |
| `AMBIENT_SPARK` | Gravity-affected falling particles, 0.8s life | Industrial atmosphere, foundry, welding zones | `glow_warm` |
| `AMBIENT_STEAM` | Upward-drifting alpha-fading particles, 2s life | Hot environments, coolant vents | `hud_text_dim` |

### 3.5 New preset proposals (v1 additions)

Presets referenced in Tier 2 docs but not yet implemented. Added with governance:

| Preset | Purpose | Referenced by |
|---|---|---|
| `CLICK_HIT_RARE` | Tier-3 click feedback (mining, salvage) | mining §8.1, salvage §8.1 |
| `CLICK_HIT_LEGENDARY` | Tier-4 click feedback (cinematic beat) | mining §8.1, salvage §8.1 |
| `ELEMENT_TRAIL_*` | Per-element projectile trails (5 variants) | combat §4.3, §4.5 |
| `DUAL_TECH_RESOLVE` | Dual-tech cinematic impact burst | combat §4.3 |
| `MODULE_RECOVERY_LIFT` | Module recovery cinematic particle trail | salvage §4.7 |
| `JUMP_STREAK` | Jump cinematic streak phase | galaxy §4.1 |
| `JUMP_CHARGE` | Jump cinematic charge phase | galaxy §4.1 |
| `NAMED_ENCOUNTER_INTRO` | Named-encounter arrival sparkle | mining §6.2, salvage §6.2, ground §5.2 |
| `ANOMALY_PRESENCE` | Ambient "something's wrong" particle for anomaly content | mining §7.3, salvage §7.3, ground §5.2 |
| `MASTERY_GOLD_BURST` | Gold-tier mastery-up celebration | refining §8.1 |
| `S_GRADE_SHIMMER` | Quality-variance S-grade output | refining §4.4 |

Total new presets: 11. Authoring cost: ~2-3 weeks, done lazily as each Tier 2 phase implements its referring features.

---

## 4. Domain-specific VFX discipline

Each domain VFX file (`combat_vfx.py`, `mining_vfx.py`, `salvage_vfx.py`, `refining_vfx.py`) *composes* presets but doesn't *duplicate* particle primitives. Rules:

### 4.1 What domain VFX files do

- **Compose presets** into sequences (e.g., destruction sequence = freeze flash + multiple `EXPLOSION_FRAGMENT` + `DESTRUCTION_SECONDARY` + lingering `AMBIENT_DUST`)
- **Define atmospheres** — long-running scene-level particle emitters (mining depth atmosphere, forge heat atmosphere, combat atmosphere)
- **Orchestrate timing** — sequenced emissions over seconds for cinematic moments
- **Scale emissions** — combat atmosphere's dust count scales with danger tier; forge atmosphere's spark rate scales with queue size

### 4.2 What domain VFX files do NOT do

- **Define new particle primitives** — if a fundamentally-new particle behavior is needed, it gets added to `particles.py` as a shared preset with §10 governance
- **Roll their own particle pool** — all emissions go through the shared `ParticlePool`
- **Hand-tune RGB per use** — colors come from palette (§6)
- **Exceed performance budget** — each system has a budget (§7)

### 4.3 Per-system particle responsibility

| System | VFX responsibility | Shared presets used | Atmosphere |
|---|---|---|---|
| Combat | Shield effects, damage states, destruction, atmosphere, projectile impact | `LASER_HIT`, `MISSILE_EXPLOSION`, `SHIELD_IMPACT`, `EXPLOSION_FRAGMENT`, `DESTRUCTION_SECONDARY`, `AMBIENT_DUST`, `WARP_TRAIL` | Combat atmosphere, destruction |
| Mining | Click feedback, depth atmosphere, layer transitions | `CLICK_HIT`, `SPARK_BURST`, `CLICK_HIT_RARE` (new), `CLICK_HIT_LEGENDARY` (new), `MINING_DUST`, `DRONE_SPARK`, `STAR_TWINKLE` | Depth layer atmosphere (5 zones) |
| Salvage | Scan feedback, extraction quality, corruption, deck transitions | `SCAN_PULSE`, `QUALITY_BURST_GOOD`, `QUALITY_BURST_EXCELLENT`, `AMBIENT_DUST`, `AMBIENT_VAPOR`, `AMBIENT_SPARK` | Derelict atmosphere (3 types) |
| Refining | Forge heat, mastery progression, buffer pressure | `SPARK_BURST`, `AMBIENT_STEAM`, `AMBIENT_VAPOR`, `MASTERY_GOLD_BURST` (new), `S_GRADE_SHIMMER` (new) | Forge heat atmosphere (5 tiers) |
| Ship builder | Module placement, confirm-build cinematic, engine glow | `SPARK_BURST`, `CLICK_HIT`, `DRONE_SPARK`, `COLLECT_SPARKLE` | Hangar environment ambient |
| Galaxy map | Jump sequence, landmark discovery, ticker | `JUMP_STREAK` (new), `JUMP_CHARGE` (new), `WARP_TRAIL`, `STAR_TWINKLE`, `SCAN_PULSE` | Parallax starfield + nebula variants |
| Trading | Transaction feedback, event indicators | `CLICK_HIT`, `SPARK_BURST`, `COLLECT_SPARKLE` | — (no atmosphere) |
| Station hub | Hub entrance, activity card activation, ambient | `COLLECT_SPARKLE`, `CLICK_HIT`, faction-specific ambient particles | Faction-specific ambient (5 variants) |
| Ground exploration | Movement feedback, combat effects, ambient tile effects | `CLICK_HIT`, `MINING_DUST`, `AMBIENT_SPARK`, `AMBIENT_VAPOR`, domain combat presets | Tile-biome ambient |

---

## 5. Elemental particle vocabulary (combat)

Combat's five elements (per `30_overhaul_space_combat.md` §4.3) require distinct particle signatures. The per-element vocabulary:

### 5.1 Kinetic (no emissive, physical)

- **Projectile trail:** no emissive, faint dust trail via `AMBIENT_DUST` variant
- **Impact:** `LASER_HIT` with `hud_text_dim` neutral-gray color; small sparks
- **Muzzle flash:** `SPARK_BURST` in `glow_warm` (warm but neutral)
- **Destruction fire:** default material-band-dark + standard fire gradient
- **Character:** physical, mechanical, understated — the element that respects you

### 5.2 Plasma (warm emissive)

- **Projectile trail:** `ELEMENT_TRAIL_PLASMA` (new) — orange-emissive streak using `plasma_core` + `plasma_hot` additive
- **Impact:** `LASER_HIT` with `plasma_core` outer + `plasma_hot` center; lingering glow
- **Muzzle flash:** `SPARK_BURST` in `plasma_hot`
- **Destruction fire:** amplified — `plasma_core` → `plasma_hot` → `glow_warm` gradient
- **Character:** hot, physical, enthusiastic — the workhorse energy weapon

### 5.3 Ion (cool emissive with arc detail)

- **Projectile trail:** `ELEMENT_TRAIL_ION` (new) — violet-emissive with arc-line noise jitter; uses `ion_arc` primary
- **Impact:** `LASER_HIT` with `ion_arc` + branching arc-line sparks (emissive lines extending from impact point)
- **Muzzle flash:** `SPARK_BURST` in `ion_arc` + secondary violet pulse
- **Destruction fire:** ion-tech weapons don't explode conventionally — `MISSILE_EXPLOSION` replaced with ion-arc burst (no fire; lingering arcs)
- **Character:** disruptive, electrical, precise — the tech-enthusiast's choice

### 5.4 Cryo (cool emissive with crystal detail)

- **Projectile trail:** `ELEMENT_TRAIL_CRYO` (new) — cyan-emissive with occasional crystal-shape fragments shedding; uses `cryo_fractal`
- **Impact:** `LASER_HIT` with `cryo_fractal` plus crystalline fragment particles (small rotating polygons)
- **Muzzle flash:** `SPARK_BURST` in `cryo_fractal` + `glow_cool`
- **Destruction fire:** cryo weapons produce a shatter-explosion — polygon fragments with inverse-fire (cold → void_deep fade)
- **Character:** chilling, slowing, elegant — the subtle weapon that punishes complacency

### 5.5 Voltaic (sharp emissive with arc flash)

- **Projectile trail:** `ELEMENT_TRAIL_VOLTAIC` (new) — yellow-emissive with stuttering (on/off flicker at high frequency); uses `voltaic_strike`
- **Impact:** `LASER_HIT` with `voltaic_strike` + branching yellow lightning (similar to ion but faster, sharper, fewer)
- **Muzzle flash:** `SPARK_BURST` in `voltaic_strike` with 3× rapid flash
- **Destruction fire:** arc-flash explosion — brief overload, then dark cavity (emissive-then-dark)
- **Character:** sudden, devastating, punishing — the unpredictable ultimate-class weapon

### 5.6 Dual-tech combinations

When two elements combine in a dual tech (combat §4.3), particles fuse. Examples:

- **Ion + Cryo** (e.g., "Frozen Disruption") — ion arc branches terminate in cryo crystallization; impact produces both arc-lines and crystal fragments
- **Plasma + Voltaic** (e.g., "Overload Forge") — plasma trail intermittently arc-flashes voltaic; impact fire layered with arc-branches
- **Ion + Voltaic** (e.g., "Neural Storm") — ion arc shapes with voltaic flicker rate; dense electrical impact
- **Plasma + Cryo** (e.g., "Thermal Shock") — plasma projectile with cryo crystallization at impact; fire meets frost
- **Kinetic + any** — kinetic provides physical structure (sparks, dust) while element adds emissive layer

v1 dual-tech vocabulary covers 7 tech combinations (per combat §4.3); each gets a bespoke particle recipe layered on the base element vocabulary.

### 5.7 Damage-number weight tiers particle layer

Per combat §4.7 damage number tiers:

- **Tier 1 (minor)** — no additional particles beyond standard impact
- **Tier 2 (standard)** — standard impact + small `CLICK_HIT` at damage-number origin
- **Tier 3 (threshold)** — standard impact + `SPARK_BURST` at damage-number origin; brief glow trail as number rises
- **Tier 4 (cinematic)** — standard impact + `COLLECT_SPARKLE` + lingering shimmer trail as number persists longer

---

## 6. Palette compliance for particles

### 6.1 The rule

Every particle's color values must come from one of:

1. **`PALETTE_ROLES` entries** (AB §2.3) — for emissive particles and scene-general particles
2. **Material band entries** (AB §2.2) — for surface-fragment particles (e.g., destruction hull fragments)
3. **A gradient between two canonical entries** — when a particle fades from, say, `plasma_core` to `glow_warm`, that's compliant

### 6.2 Compliance test

Runs against particle configurations at import time. For each `ParticleConfig`:

- `start_color` and `end_color` must be within 4 RGB units of a palette entry (snap tolerance for emissives)
- Material-fragment particles: colors must be within 2 RGB units of a material band entry (tight tolerance per AB §2.5)
- Failure → ImportError with diagnostic listing the offending preset and which palette the color should have come from

Migration (Phase V2, §10) audits existing presets against this rule; hand-tuned RGB values get normalized to canonical roles.

### 6.3 Emissive budget

Per AB §3.5 ≤15% rule. At the particle-system level:

- **Soft cap:** each scene declares an emissive-particle budget (combat = 20%, mining = 10%, station hub = 5%, etc.)
- **Monitoring:** `ParticlePool` tracks live emissive-particle count at render time; logs warning if budget exceeded in a frame
- **Hard cap:** pool-level 500-particle cap already exists

### 6.4 Bypass exceptions

Emissive particles bypass palette snap (AB §3.5). This is already handled correctly in existing code; documented here for explicitness.

---

## 7. Performance discipline

### 7.1 Pool capacity

Current: 500 particles max. Justification: empirical — covers most combat scenes with destruction + shields + atmosphere. Observed headroom in salvage and mining scenes (typical steady-state: 50-150 active particles).

**Increase only if:** a specific scene (e.g., full dual-tech cinematic + enemy destruction + player ship atmosphere) demonstrably exceeds 500 and drops a mechanically-important particle. Profile first; decide after evidence.

### 7.2 Per-scene particle budgets

Soft budgets for typical steady-state (non-cinematic) frames:

| Scene | Budget |
|---|---|
| Cockpit idle | 30-50 (ambient starfield only) |
| Galaxy map | 50-100 (starfield + minor dust + event indicators) |
| Combat steady-state | 150-250 (atmosphere + damage states + shield if active) |
| Combat destruction sequence | 300-400 (burst budget for ~1 second) |
| Mining session | 80-120 (depth atmosphere + click feedback) |
| Salvage session | 100-150 (derelict atmosphere + scan/extract feedback) |
| Refining session | 80-120 (forge atmosphere) |
| Station hub | 60-100 (faction ambient + UI feedback) |
| Ground exploration | 100-200 (tile ambient + combat if active) |

Systems staying within budget preserve headroom for cinematic moments.

### 7.3 Cinematic particle budget

Cinematic moments may burst over steady-state (acceptable; pool capacity allows). Rules:

- No more than one system bursting at a time (combat destruction OR dual-tech reveal, not both; if both happen, cinematic-layer manager sequences)
- Cinematic budget ceiling: 400 particles (leaves 100 headroom for other systems)
- Cinematic bursts should complete within 1.5 seconds — no lingering tail

### 7.4 Pool eviction discipline

When pool is near-full, new emissions at `priority < 0.5` drop silently. This protects cinematic (priority 1.0) and critical-gameplay (0.8+) particles. Implementation: `ParticlePool.emit(preset, priority)` — priority-aware claiming.

---

## 8. Screen effects and backgrounds

### 8.1 Screen effects (`screen_effects.py`)

Current: vignette + screen shake. Per `10_programmatic_generation_framework.md §2`, `screen_effects.py` is scoped for rebuild as `post_processing.py`.

Until rebuild: preserve existing behavior; document as temporary.

Post-rebuild: the post-processing pipeline (bloom, chromatic aberration, vignette, grain, scene tint) per framework §9.2 replaces the current simple effects file. This doc deprecates on rebuild.

### 8.2 Backgrounds (`backgrounds.py`)

Procedural parallax starfield, seed-deterministic. Covered by galaxy map overhaul doc §4.4 for extensions (nebula regions, arm structure, traffic lanes).

Implementation note: backgrounds are not particles technically — they're rendered via a separate system. But they share palette discipline and performance considerations, so documented here for completeness.

---

## 9. Anti-patterns

### 9.1 Hand-tuning RGB in particle configs

**Don't:** `start_color=(180, 120, 60)` in a new particle config. Might be close to `plasma_core` (255, 175, 58) but not exact; palette drift.

**Do:** `start_color=rgb("plasma_core")` via palette lookup helper. If no role matches, a new role gets added to the Bible — don't introduce off-palette colors by default.

### 9.2 Rolling your own particle pool

**Don't:** a new VFX file declaring `self.my_particles = []` and managing its own lifecycle.

**Do:** use `ParticlePool` for all emissions. If a new behavior needs a new particle preset, add to shared `particles.py`.

### 9.3 Emissive sprawl

**Don't:** every particle glows. Destruction sequences with 80% emissive pixels read as fireworks, not combat.

**Do:** reserve emissive for signal. Ambient + surface-fragment particles stay non-emissive; only plasma cores, shields, tech signatures, and specific cinematic beats emit.

### 9.4 Ignoring scene budget

**Don't:** a system emits 200 particles per frame during steady-state. Pool fills; cinematic moments drop particles.

**Do:** tune emission rates to steady-state budgets; reserve capacity for bursts.

### 9.5 Particles without purpose

**Don't:** decorative particles "because it looked nice." Every particle has a reason (§2.1 rule 2).

**Do:** justify each emission. If a particle can be removed without reducing gameplay or mood communication, remove it.

### 9.6 Long-life particles in tight scenes

**Don't:** 5-second-life particles emitted rapidly during fast-paced combat. Pool clogs.

**Do:** match particle lifetime to scene pace. Combat particles: 0.3-1.0s. Station ambient: 3-5s. Cinematic bursts: 0.5-1.5s.

---

## 10. Governance

### 10.1 Adding a new particle preset

Triggers:
- A specific Tier 2 doc references a particle effect not in the current catalog
- Implementation of a Tier 2 phase discovers a gap

Process:
1. Propose preset name, behavior, canonical use case, palette source
2. Coordinate with at least one Tier 2 doc that will consume it
3. Add entry to §3 of this doc
4. Implement in `particles.py` as module-level constant
5. Domain VFX file consumes the preset

Adding a new preset is *additive* — existing systems keep working. Removing or renaming is a breaking change requiring coordinated migration.

### 10.2 Cross-system preset sharing

When two systems use similar effects (e.g., combat click + mining click), they **must share** the preset. Divergence is a drift signal.

If two systems need *slightly different* versions of a similar effect, the right answer is usually:
- A single preset with parameters (scale, count, color) configurable at emission time
- Not two presets with overlapping meaning

### 10.3 Migration schedule

| Phase | Work | Timing |
|---|---|---|
| V1 | This doc shipped; preset catalog formalized | Now |
| V2 | Palette compliance audit + migration of hand-tuned RGB to palette roles | ~2 weeks, coordinate with early implementation phases |
| V3 | 11 new presets (§3.5) implemented as referring Tier 2 phases land | Lazy — ~6 weeks distributed |
| V4 | Performance budget monitoring added to `ParticlePool` | ~1 week, pre-beta |
| V5 | Cross-system coordination audit + optimization | Before release |

### 10.4 Versioning

Doc versions as vocabulary expands. Revision history at header.

---

## 11. Out of scope

- **3D particle systems** — flat 2D; no depth-sorted particle arrays
- **GPU-accelerated particles** — pygame-ce default rendering; no shader-based compute
- **Physics-driven particles** (cloth, fluid dynamics, rigid body) — gravity is the only physics currently; not expanded
- **AI-generated particle art** — category excluded per project no-AI-content constraint
- **Third-party particle libraries** — Aurelia is pygame-ce native; no Pyglet / arcade / Panda dependencies
- **Real-time particle editing tools** — authoring is via code constants; no in-game particle editor

---

*Revision history:*
- *v1 — initial vocabulary doc. Formalizes existing taxonomy, proposes 11 new presets, defines palette compliance + performance + elemental vocabulary.*

*Next Tier 3 doc: `42_ui_chrome_components.md` — formalizes the UI component patterns already present in `draw_utils.py`, `table_widget.py`, `scrollable_panel.py`, and cross-references the UI additions from every Tier 2 doc.*
