# Space Combat Visual Overhaul

> **Status:** DESIGN — Tier 2 doc. Inherits from `20_aesthetic_bible.md` and `10_programmatic_generation_framework.md`.
>
> Defines the target visual experience for space combat and the rendering/engine changes required to get there. Gameplay is out of scope except where rendering problems expose balance or pacing issues that rendering alone cannot solve.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Rendering changes
5. Gameplay changes forced by rendering
6. Dependencies
7. Phasing

---

## 1. Current state — honest assessment

Factual snapshot as of 2026-04-20 (per survey of `combat_view.py`, `combat_vfx.py`, `projectiles.py`).

### 1.1 What's already strong

- **Destruction sequence** (`combat_vfx.py:493-779`): 1.1s cinematic — freeze → white flash → rotating hull fragments with gravity + fire/smoke → secondary explosions at 4 offset positions → persistent debris drift. This is genuinely good and stays.
- **Shield system**: directional-impact ripple rings, fragment break sequence, fade-in restore. Visually coherent and responsive.
- **Combat atmosphere**: danger-level tint overlay (safe → crimson) + dust-mote particles scaled to danger tier + arena frame with tech-UI border. The **framing** is right even though the **contents** are underbuilt.
- **Projectile variety**: laser (extending beam with glow+core+tip), missile (body + 5-dot exhaust trail, parabolic arc), cannon (3-5 staggered bursts). Each weapon type reads distinctly.
- **Damage state progression**: smoke at <50% hull, sparks at <75%, critical-pulse outline at <25%. Physical read on how beat-up a ship is.
- **Floating-text palette**: 8+ color-coded types (armor absorbed silver, graze orange, shield regen cyan, frozen ice-blue, burn orange, momentum gold, counterstrike cyan, shields-broken red). Useful information layer.

### 1.2 What's weak — the five gaps

**Gap 1: Module targeting has zero visual feedback.**

Module-targeted combat is a *headline feature* — players target specific modules (cockpit, engine, weapon) to disable or destroy them. Currently, the only indication that module targeting happened is text in the floating-damage readout: `"-15 [Engine]"`. No tint, no highlight, no overlay on the ship's physical module region. The player is doing surgical work and the game is showing them a receipt.

**Gap 2: Dual tech reveals lack cinematic weight.**

The dual tech system (7 techs, 2 bridge-crew participants, one of the game's most interesting mechanics) resolves like any other attack. The feedback is: a text banner appears at 1/3 screen height, fades over 0.3s, then the action plays like a regular weapon strike. Ultimates get a 0.5s screen darken — better, but still far short of "legendary." Compare to FF7's Knights of the Round or Chrono Trigger's triple techs: the game *stops the world* and gives the move its moment.

**Gap 3: No turn-to-turn pacing beats.**

Actions resolve continuously — projectile flies, hit resolves, particles burst, next action begins. No breathing room between meaningful beats. The arena is a static camera watching a pool fight. FF7/Chrono Trigger pause, zoom, frame the blow, then release. Without that rhythm, combat reads as a bar-filling exercise rather than turn-based drama.

**Gap 4: Ship rendering pipeline is split.**

Player ship uses `ShipComposite` — 7-phase procedural render with material fill, panel lines, edge highlight, texture, outline, slot indicators, animated engine glow. Enemies use `AnimatedSprite` — static sprite sheet with idle bob. The two look different. Under palette discipline (Aesthetic Bible §2), this is a correctness bug — enemies don't participate in the material/band system; their palette compliance is accidental. Also: enemy ships can't show real damage progression because the pipeline doesn't support it.

**Gap 5: Arena background is static.**

`AnimatedBackground` sets up 3-layer parallax starfield on entry but combat itself doesn't animate it. Dust motes twinkle in place; the arena frame is static. Compared to scale-reverence references (No Man's Sky warp, Starfield grav-jump), a combat arena that doesn't respond to action reads as a stage backdrop rather than a place.

### 1.3 What this doc addresses

- All five gaps above
- A **unified rendering pipeline** for every ship in combat (player + enemies), per Aesthetic Bible
- A **camera concept** — currently absent — so pacing beats become possible
- **Integration of the canonical palette** (AB §2) and elemental palettes (AB §3.5 emissive materials) into projectile/VFX color language

---

## 2. Target feel — influences and reference moments

### 2.1 The three-influence synthesis

Aurelia combat is **turn-based JRPG cinematic meets physical-mech weight**. Three references, each carrying specific cargo:

**FF7 — camera composition and per-element signature**

- The camera is a *character* — it zooms, pulls back, swings between actors. Static arenas read as budget compromises.
- Every element has a visual vocabulary: Fire rises and curls; Ice crystallizes and shatters; Thunder arcs and flashes; Water flows and splashes. Aurelia's five elements (Kinetic / Plasma / Ion / Cryo / Voltaic) must each have the same depth of signature.
- Damage numbers have *weight tiers*. Small hits pop and fade; critical hits flash large, hold, and trail.
- Summons and limit breaks **stop the world**. The game acknowledges you're doing something rare.

**Chrono Trigger — dual/triple tech fusion visuals**

- Dual techs are their own genre. When two characters combine moves, the visual is a *combination*, not a sequence — ice-ring + fire-spear = ice-shattered-by-fire with elements fusing on screen.
- Pause framing: the screen holds on the technique name for ~0.6s before execution. Small delay, enormous "this matters" effect.
- Character portraits appear at corner during the reveal — crew members are *seen* performing the technique, not just named.

**Armored Core — physical weight and modular damage**

- Mechs have weight. When they move, thrusters fire with visible plume-and-shockwave. When they get hit, they recoil — and that recoil is proportional to the weapon's mass.
- Damage is *visible on the ship itself*. A destroyed thruster leaves a blown-open socket. A severed wing changes the silhouette. Damage isn't an HP bar — damage is an observable condition.
- Sound design is mechanical: hydraulics, servos, metal impacts, thrust noise. No synthesizer pads; this is not Wipeout.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against. When a combat feature is being reviewed, ask: *which of these moments does this feature participate in?*

1. **FF7, "Bahamut ZERO summon"** (1997). ~30 seconds. Everything stops. Camera rises through the atmosphere, weapon charges, beam resolves the entire battlefield. The game *earns the right* to this moment because it's rare. Aurelia equivalent: legendary boss opening move, final dual tech, campaign-climax reveal. Budget: < 2 per playthrough.

2. **Chrono Trigger, "Frog + Crono: X-Strike"** (1995). ~3 seconds. Portraits appear bottom-corner, two characters cross-dash, impact combines their element signatures, number + aftermath. Aurelia equivalent: every dual tech. This is the *default* presentation for any two-crew coordinated move.

3. **Armored Core 6, "first AC boot-up from hangar"** (2023). ~8 seconds. Thrusters ignite, mech lifts, inertia visible, engine-noise builds, then movement. Aurelia equivalent: combat-start animation when the player ship enters arena. Currently absent.

4. **FFVI, "Sabin Blitz inputs"** (1994). Damage number pops huge when a technique lands a bonus. Aurelia equivalent: momentum-threshold hits (currently gold-text via floating number — needs weight-tier upgrade per §4.8).

5. **Armored Core 4, "enemy mech losing a leg mid-combat"** (2006). Module destruction mid-fight visibly alters silhouette. Aurelia equivalent: module destruction in combat produces a silhouette change on the ship composite, not just a debuff indicator.

### 2.3 What this is not

- **Not real-time action.** Turn-based. Time between actions is directed pacing, not reaction-testing.
- **Not visual-novel stillness.** Arena is alive — backgrounds parallax, dust drifts, wreckage lingers, power readouts pulse.
- **Not Michael Bay.** Explosions are weighted and readable, not maximally loud. Destruction sequence (§1.1) is already roughly right; we don't turn every hit into that.
- **Not anime over-bloom.** Bloom threshold is calibrated (Aesthetic Bible §2); emissive ≤15% per ship (AB §3.5). Everything-glows is the anti-pattern.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

For each canonical combat moment, what should the player *feel*?

| Moment | Target emotion | Visual signal doing the work |
|---|---|---|
| Combat opens (arena reveal) | Tension + commitment | Camera push-in on player ship; engine ignition; arena atmosphere resolves from tint |
| Routine player attack lands | Satisfaction | Weighted recoil, tight damage-number pop, shield/hull flash proportional to damage |
| Player chains multiple actions (momentum build) | Rising competence | Stacking visual glyph(s) on player ship frame; HUD momentum gauge pulses warmer |
| Player lands a critical (threshold hit) | Punch through | Screen shake +50%, damage number jumps to weight-tier-2 size, impact flash extends into slow-mo (~0.15s, one frame of hold) |
| Dual tech triggers | Legendary (rare, earned) | Cinematic framing: zoom, darken, portraits enter corner, tech name holds 0.6s, combined-element visual resolves across 1.2s |
| Ultimate/legendary boss move | Overwhelming (rarer still) | Full 2-3s cinematic: camera rises, beam/strike charges, impact dims all non-subject pixels |
| Enemy destruction | Relief + triumph | Existing destruction sequence (§1.1). Already right. |
| Player takes hit on shield | Contained alarm | Shield ripple (existing). HUD shield gauge pulses cyan inward. |
| Player takes hit on hull | Anxiety | Hull flash + recoil + minor camera shake + damage state progression (smoke/sparks if threshold crossed) |
| Player module destroyed | Real loss (feature, not bug) | Module region on ship composite visibly darkens; silhouette changes if structural; persistent visual marker on the ship for rest of combat |
| Player critical HP | Edge-of-seat | Red vignette pulses; HUD edge flickers; combat atmosphere intensifies (tint deepens); heartbeat-pace UI animation |
| Player flees | Resignation, intact | Warp animation with camera push-out; enemies fade; overlay tint cools |

### 3.2 What each emotion serves gameplay

- **Tension + commitment** (open) → combat is not casually entered; the player has to read the setup
- **Satisfaction** (routine) → every turn should feel like a move, not a button-click
- **Rising competence** (momentum) → the momentum mechanic has visual legibility; players *see* their turn-economy advantage
- **Punch through** (crit) → threshold hits matter; the build-for-crits decision is rewarded visibly
- **Legendary** (dual tech) → crew composition matters; rare powerful moves *feel* rare and powerful
- **Real loss** (module destruction) → module-targeted combat matters; players see their ship getting carved up

### 3.3 The non-goal: photorealism

We are not trying to make combat look "real." We are trying to make combat *feel committed, weighted, and rhythmically framed*. Palette-banded lighting + particle discipline carries style; camera + pacing carries weight. Neither asks for photoreal detail.

---

## 4. Rendering changes

The meat of this doc. Each subsection describes a discrete engineering change.

### 4.1 Unified ship rendering pipeline

**Current:** Player uses `ShipComposite` (procedural 7-phase); enemies use `AnimatedSprite` (sprite sheet).

**Target:** All combat ships render via the new `ShipComposite` pipeline (rebuilt per Aesthetic Bible §6 and framework §2). This means:

- Enemy ship data migrates from sprite-sheet references to a ship-build (modules + layout), even if that build is a hand-authored "enemy template" rather than a player-buildable configuration
- Enemy ships participate in the material/band system — palette compliance holds for them as for player
- Enemy damage states progress visibly through the composite (wear parameter + module destruction visual)
- Shared caching — an enemy ship's composite is cached like a player ship's

**Cost:** ~1-2 weeks. Requires the `ship_composite.py` rebuild (already scoped in framework §2) plus ~28 enemy template conversions (mostly data work — the visual templates inherit manufacturer identity from Aesthetic Bible §4).

**Benefit unlocks:** module-targeting visual feedback (§4.2), module-destruction silhouette change (§4.3), palette compliance holds across combat, damage-progression visual consistency.

### 4.2 Module targeting visual layer

**The headline gap (§1.2 Gap 1).** When a player targets a module for attack, the UI must show:

1. **Module outline highlight** on the ship composite during target selection — the targeted module's bounding region gets a 2-pixel inset outline in `hud_warning` (pre-fire) or `hud_critical` (committed).
2. **Hit region flash** at moment of impact — the targeted module's material pixels flash to their band's `specular` entry (index 4) for 0.1s before settling.
3. **Damage overlay** persists on damaged modules — scorch tint using `rivet` role + subtle smoke particle emitter anchored to module center if module is below 50% module-HP.
4. **Destruction overlay** — once a module is destroyed, its region swaps to a `steel_shadow_deep` + `seam` fill with emissive-absent behavior (no engine glow, no weapon charge). If structural, the region also gets an `appendage_severed` particle burst (one-shot). The persistent visual marker stays for the rest of combat.

**Implementation:** a new `ship_module_overlay.py` that consumes the `PlacedModule` list from the ship's build and produces per-module regions that can be addressed in combat. Overlay renders AFTER the ship composite, before VFX.

**Depends on:** §4.1 (unified pipeline so the enemy ships can participate).

### 4.3 Dual tech cinematic framework

**The second headline gap (§1.2 Gap 2).**

**The cinematic shape (Chrono Trigger X-Strike model):**

```
t=0.0    — Tech trigger confirmed. Camera begins zoom-in on player ship (600ms).
t=0.6    — Screen darkens to 70% black. Portraits of the two participating crew members
           slide in from bottom-left and bottom-right (300ms slide).
t=0.9    — Tech name holds center-screen in large type, stroke in the dominant element's
           emissive role (plasma_core / cryo_fractal / ion_arc / voltaic_strike). Holds 600ms.
t=1.5    — Tech name fades, portraits hold. Combined visual resolves across 1200ms:
           the tech's shape (ice ring + fire spear, etc.) traces its path using
           elemental-role emissives + additive blend.
t=2.7    — Impact. Screen shake at +100% baseline. Damage number at weight-tier-3
           (largest). Portraits fade. Screen un-darkens.
t=3.2    — Normal playback resumes.
```

**3.2 seconds total.** Significantly longer than current (0.5s darken + 0.3s banner = 0.8s). This is the point. Dual techs *stop the world* because they are meant to.

**Ultimate techs (legendary/rare):** extend to ~4.5s total with an additional "charge" phase (t=1.5 to t=3.0: emissive light builds on the player ship, particles swirl inward) before impact resolution. Budget: < 2 ultimates per playthrough on average.

**Per-element visual palette (integration with AB §2):**

| Element | Primary emissive | Trail/glow | Impact flash color |
|---|---|---|---|
| Kinetic | (neutral, no emissive) — uses `glow_warm` for muzzle | dust + spark | white with warm tint |
| Plasma | `plasma_core` (orange) | `plasma_hot` additive | yellow-white → orange |
| Ion | `ion_arc` (violet) | `glow_cool` additive with arc-line noise | violet-white with arc branches |
| Cryo | `cryo_fractal` (cyan) | `glow_cool` with crystallization overlay | cyan-white, crystal fragments |
| Voltaic | `voltaic_strike` (yellow) | arc-line flash (1-frame hold, repeat 3x) | yellow-white, branching |

Dual techs **combine two element palettes** — an ion-cryo dual tech starts with violet trail, arcs into cyan crystallization at impact, damage number stroke is cyan with ion-arc outer glow.

**Implementation:** a new `dual_tech_cinematic.py` overlay system that the combat controller triggers. Uses the combat view's existing darken/banner primitives, extended with portrait renderer + element-palette-driven particle sequencer.

**Depends on:** framework §9.2 post-processing pipeline (for darken), AB §3.5 (emissive palettes), portrait sprite system (existing).

### 4.4 Camera system and pacing beats

**The third headline gap (§1.2 Gap 3).** Currently there is no camera — the arena is a static viewport. We introduce a lightweight camera.

**Naming and scope note (post-Tier-2 coherence review):** this camera is referenced by 8 systems beyond combat (Ship Builder preview orbit + test flight, Galaxy Map jump cinematic, Mining prestige cinematic, Salvage module recovery + cycle, Station Hub docking, Ground Exploration deployment). The abstraction is therefore **`SceneCamera`**, not combat-specific. Combat consumes it through `ArenaCamera`-specific states below, but the camera primitive itself lives in `scene_camera.py` as a shared engine facility.

```python
@dataclass
class SceneCamera:
    offset: tuple[float, float]       # additive to rendered positions
    zoom: float                       # 1.0 = default
    shake_amp: float
    shake_time: float
    target_offset: tuple[float, float]
    target_zoom: float
    transition_time: float            # seconds to reach target
    ease: Callable[[float], float]    # ease curve
    parallax_factors: dict[int, float]  # per-layer parallax (0.0-1.0)
```

**Combat-arena canonical states** (one set of named states consumed by combat view):

| State | Offset | Zoom | Used when |
|---|---|---|---|
| `DEFAULT` | (0, 0) | 1.0 | Idle between turns |
| `FOCUS_PLAYER` | (−80, 0) | 1.25 | Player-committed action (brief, 300ms) |
| `FOCUS_ENEMY(i)` | toward target enemy | 1.25 | Targeted attack resolution |
| `WIDE` | (0, 0) | 0.85 | Dual tech establishing shot |
| `CINEMATIC` | per-script | 0.7-1.5 | Dual tech / ultimate / boss reveal |
| `SHAKE` | random within amp | 1.0 | Impact resolution (additive to current) |

**Other systems consume the same primitive with different state sets:**
- Ship Builder defines `PREVIEW_ORBIT` (angle-cycling) and test-flight tracking states
- Galaxy Map defines `GALACTIC`, `REGIONAL`, `DEFAULT`, `CLOSE` zoom tiers
- Each consumer declares its own states; the `SceneCamera` primitive is generic

**Pacing beats between turns:** after an action resolves, before the next begins, the camera relaxes to DEFAULT over 250ms. This is the "breath" that turn-based combat needs. Currently absent — actions run back-to-back with no relaxation.

**Implementation:** a `scene_camera.py` module. All rendering passes through the camera transform (offset + zoom + per-layer parallax). Combat-specific state behavior can live in `combat_view.py` consuming the shared primitive.

**Depends on:** nothing. This can ship first — and **should** ship first, because 8 systems block on it.

### 4.5 VFX element-palette integration

Per §4.3 element-palette table, all combat VFX draw from the canonical emissive roles. Currently projectiles use hand-coded RGB: laser is orange-white, missile is gray, cannon is yellow. Migrate:

| VFX system | Current color source | Target (per AB §2.3) |
|---|---|---|
| Laser beams (weapon element-specific) | Hand-coded orange | `plasma_core` / `ion_arc` / `cryo_fractal` / `voltaic_strike` per element |
| Missile exhaust trail | Hand-coded orange | `plasma_hot` additive with `plasma_core` core |
| Cannon muzzle flash | Hand-coded yellow | `glow_warm` + `voltaic_strike` if voltaic-tech weapon |
| Shield ripple | Hand-coded cyan | `cryo_fractal` (default) or `ion_arc` (ion-shielded) |
| Damage floating text stroke | Hand-coded per-type | role-table entries: armor-absorbed = `hud_muted`, graze = `hud_warning`, critical = `hud_critical`, etc. |
| Destruction fragment fire | Hand-coded gradient | `plasma_core` → `plasma_hot` → `glow_warm` |
| Dust motes | Hand-coded | `void_light` with `glow_cool` twinkle |

**Cost:** ~3 days. Mostly mechanical — replace RGB literals with palette role lookups. Forces projectile color to respond to weapon element, which the current system can't always do.

**Benefit:** palette compliance holds in combat; element identity is immediately visible; colorblind modes (AB §2.4) Just Work in combat because VFX flows through the same palette-remap hook as everything else.

### 4.6 Background animation during combat

**Gap 5 from §1.2.** Current combat uses `AnimatedBackground` as setup but doesn't animate during the fight. Two changes:

1. **Starfield parallax responds to camera** — when camera zooms or pans during a cinematic (§4.4), starfield layers drift at their respective percentages. Cost: trivial; `AnimatedBackground.update(dt)` already exists, just needs camera hook.
2. **Danger-level-specific atmospheric detail** — instead of only dust motes + tint, add:
   - `safe`: calm distant stars only
   - `moderate`: dust motes (existing)
   - `dangerous`: dust + occasional small debris passing through (elongated streak, 2-3s lifespan)
   - `crimson`: heavy debris + faint pulsing red glow at screen edges + ambient arc-flash at random intervals (1-2 per minute, flashes edge of screen voltaic-style)

**Cost:** ~4 days. Existing `CombatAtmosphere` class extended per danger level.

**Benefit:** the arena becomes a *place* with mood that scales with threat. Especially for crimson-tier encounters which currently look like regular fights with a tint.

### 4.7 Damage number weight tiers

Current floating text is uniform size with color coding. Split into weight tiers per §3.1:

| Tier | Font size | Animation | When |
|---|---|---|---|
| 1 (minor) | 12pt | Quick fade 0.6s, gentle rise | Graze, shield chip, armor absorb |
| 2 (standard) | 16pt | Current behavior (0.8-1.0s, rise+fade) | Normal damage |
| 3 (threshold) | 22pt bold | Pop + brief hold 0.15s + fade 1.2s, impact-direction drift | Critical, momentum threshold, elemental effectiveness |
| 4 (cinematic) | 32pt with stroke | Large pop + hold 0.4s + slow fade 2.0s, stays center-ish | Dual tech impact, ultimate, boss-critical |

Stroke/fill colors pull from palette roles per element (§4.5 table).

**Cost:** ~2 days. Refactor `_render_floating_texts` to accept tier parameter; update all emit sites to declare tier.

### 4.8 Arena entry animation

New moment per §3.1 (Combat opens). Canonical 1.5s sequence:

```
t=0.0  — Scene transitions from prior state (warp/fade). Camera enters arena at WIDE zoom.
t=0.3  — Danger-level tint resolves (fade-in over 500ms). Dust motes appear.
t=0.5  — Camera pushes in toward FOCUS_PLAYER over 600ms. Player ship's engine emissive
         ignites (pulse from dim to normal intensity).
t=1.1  — Camera reaches DEFAULT. Enemies slide in from right over 400ms, each with
         engine-ignite cue staggered 100ms.
t=1.5  — Normal combat resumes, first turn begins.
```

Combat feels less like "button opens menu" and more like "fight commences." Sets the §3.1 tension + commitment beat.

**Cost:** ~3 days. Scripted sequence using camera (§4.4) + existing engine glow + new enemy-slide-in routine.

### 4.9 Crew portrait integration

Dual techs and ultimates (§4.3) render crew portraits. Portraits already exist (hand-authored pixel art per framework §11.5). Add:

- Portrait render-in/out animation (slide + scale + alpha)
- Portrait border styled per-crew-member faction (uses `PALETTE_ROLES` stripe color from AB §4.8)
- Portrait "expression" variants — optional, if portrait sprite sheets support multiple frames. Triggered per tech: e.g., Elena's portrait shows her concentration-frame during ice techs. Deferred unless the art budget supports it.

**Cost:** ~2 days core; +2 days per expression-variant if pursued.

---

## 5. Gameplay changes forced by rendering

Per the Bible's discipline, gameplay changes ONLY if rendering exposes problems rendering cannot solve.

### 5.1 Turn pacing — a small change

The 3.2s dual tech cinematic (§4.3) interrupts turn flow. Two options:

**Option A: purely visual interrupt.** Turn resolves at t=2.7 (impact); visual continues to t=3.2 but next turn starts at t=2.7. Feels rushed — visual still playing during next turn's selection.

**Option B: turn clock pauses during cinematic.** Turn clock resumes at t=3.2. Adds ~2.4s to turns with dual techs. Players learn dual techs are slow-but-legendary.

**Recommendation: Option B.** Matches reference games (FFVII summons *did* add time). Subtle gameplay change: dual techs are slightly more committed because the turn they were queued in resolves in ~2.4 extra seconds. Communicates the trade: legendary moves have legendary presence.

This is the only intentional gameplay change. Everything else is additive-visual.

### 5.2 Module destruction signal — no change, but confirms existing behavior

Module destruction already has gameplay effects (disabled weapons, severed structural chains per Shipbuilder phase 14). Rendering gains the visual marker (§4.2); no new gameplay impact.

### 5.3 Arena-entry time — strict additive

The 1.5s arena entry animation (§4.8) is purely visual. It does not consume turn clock; it precedes combat state. No impact on AI planning or queue resolution.

---

## 6. Dependencies

### 6.1 On other overhaul docs

- **`20_aesthetic_bible.md` §2** (canonical palette) — required for VFX element palette migration (§4.5)
- **`20_aesthetic_bible.md` §3.5** (emissive rules, ≤15% budget) — constrains how bright dual tech cinematics get
- **`20_aesthetic_bible.md` §6** (composition/lighting) — ship rendering in combat inherits these
- **`20_aesthetic_bible.md` §8** (scene mood overlays) — combat-intensity and red-line overlays live here
- **`10_programmatic_generation_framework.md` §2** — `ship_composite.py` rebuild is a blocking dependency for §4.1 (unified pipeline)
- **`10_programmatic_generation_framework.md` §9.2** — post-processing pipeline needed for dual tech cinematic darken

### 6.2 On Tier 3 parallel docs (not-yet-written)

- **`41_vfx_particle_vocabulary.md` (Tier 3, not written)** — establishes particle-class standards that this overhaul wants to consume. Can ship without it but work is smoother if it lands first.
- **`42_ui_chrome_components.md` (Tier 3, not written)** — arena frame, HUD edge treatment, portrait frames all would consume standards from here. Again, can ship without.

### 6.3 On production code

- `spacegame/engine/ship_composite.py` — current impl, target for rebuild
- `spacegame/views/combat_view.py` — target for heavy extension (camera, overlays, cinematic)
- `spacegame/engine/combat_vfx.py` — extension for element palette integration
- `spacegame/engine/projectiles.py` — extension for element-driven color
- `spacegame/engine/particles.py` — existing, extended per §4.5
- `data/ships/enemy_templates.json` (new or extended) — for enemy-ship-as-composite

---

## 7. Phasing

Combat overhaul is large. Suggest 5 phases. Each ships standalone; none blocks the next from starting (where parallelizable).

### Phase C1 — Camera and pacing beats (~1 week) ✅ SHIPPED

- ✅ Implement `SceneCamera` class (§4.4, generalized post-coherence to serve 9 systems)
- ✅ Wire camera into combat_view render pipeline
- ✅ Ship DEFAULT / FOCUS_PLAYER / FOCUS_ENEMY / WIDE / CINEMATIC / SHAKE states
- ✅ Add pacing beat (250ms relaxation between turns)

**Delivered as:** `spacegame/engine/scene_camera.py` + combat_view integration.

### Phase C2 — VFX element palette integration (~1 week) ✅ SHIPPED

- ✅ Migrate projectile colors to element-palette roles (§4.5) — `projectiles.py`
- ✅ Migrate shield ripple colors to palette — `combat_vfx.py::ShieldState.element`
- ✅ Migrate destruction fragment fire to palette gradient — `_fire_palette()`
- ✅ Migrate dust motes + atmosphere tint to palette (void_light / role-based tint)
- ✅ combat_view spawn call sites forward element strings

**Delivered as:** modifications to `engine/projectiles.py` + `engine/combat_vfx.py` + `views/combat_view.py`. Test suite: `tests/test_engine/test_combat_palette_integration.py` (31 tests).

**Note:** Floating-text color-source migration is partial — sites that auto-classify into Tier 3/4 use palette roles; Tier 1/2 still accept caller-supplied RGBs. Full migration blocked on nothing — just un-touched sites.

### Phase C3 — Damage number weight tiers + arena entry (~1 week) ✅ SHIPPED

- ✅ Implement Tier 1-4 damage number primitive (§4.7) — `engine/damage_text.py`
- ✅ `classify_damage_text` auto-tier heuristic (graze/normal/threshold/cinematic)
- ✅ combat_view `_render_floating_texts` recognizes tier field + renders stroke for CINEMATIC
- ✅ VOID RELEASE + OVERDRIVE emit sites classified as CINEMATIC tier
- ✅ Arena entry 1.5s timeline primitive (§4.8) — `engine/arena_entry.py`
- ✅ **ArenaEntry wired into combat_view INTRO phase** — timeline drives phase duration, camera push (WIDE 0.85 → DEFAULT 1.0), and atmospheric tint/dust fade-in via `tint_alpha_factor`

**Delivered as:** `damage_text.py` + `arena_entry.py` primitives + combat_view wiring. Test suite: 67 primitive tests + 4 intro wiring tests.

**Remaining polish (optional):** `player_engine_ignite_factor` + `enemy_slide_offset(i)` are exposed on the timeline but combat_view doesn't consume them yet — the player engine emissive ramp and enemy slide-in are a polish pass across arena render sites.

### Phase C4 — Unified ship pipeline + module targeting visuals (~2-3 weeks) ⚠️ PARTIALLY SHIPPED

- ✅ Module overlay primitive (§4.2) — `engine/ship_module_overlay.py`
  - 5 persistent states (NORMAL / HIGHLIGHTED / COMMITTED / DAMAGED / DESTROYED)
  - Transient flash with band specular
  - Hit detection in ship-local coords
  - Palette-role-driven rendering
- ✅ Enemy build generator (§4.1) — `engine/enemy_build_generator.py`
  - Every one of the 60 live enemy templates generates a valid ShipBuild
  - Faction → primary material mapping (5 factions incl. Crimson Reach default)
  - Danger tier → weight class; Boss → large override
  - Behavior → accent material
  - Deterministic silhouette seeded on template.id
- ✅ Enemy composite provider (§4.1) — `engine/enemy_composite_provider.py`
  - Cached ShipComposite per-template with portrait-friendly config
  - Injected template lookup (test-isolatable)
- ✅ combat_view integration — enemy card portraits render via ShipComposite with AnimatedSprite fallback

**Delivered as:** 4 engine modules + combat_view wiring. Test suites: `test_ship_module_overlay.py` (34), `test_enemy_build_generator.py` (31), `test_enemy_composite_provider.py` (16) = **81 tests** total for C4.

**Deferred from C4 — tracked for follow-up:**

- ⏳ **Frame-animated destruction via ShipComposite.** The legacy `AnimatedSprite` sprite-sheet path is still live for the ship-destruction animation (combat_view line ~2021). Migrating requires ShipComposite to gain damage-progression + destruction-animation render states — substantial new functionality, not cleanup. Separate focused session.
- ✅ **Module overlay integration in combat_view** (QA Pass 5 Tier 3.C, 2026-04-21). `EnemyModuleOverlayProvider` caches one `ShipModuleOverlay` per living enemy instance (mirrors the Tier 3.A composite cache pattern). Subsystem tags (Combat §11.2's 6-tag palette) map to canonical grid regions via `canonical_subsystem_regions` — no per-template authoring needed because the procedural silhouette generator points ships right, giving stable spatial positions for cockpit/weapon_array (front), sensor_array/shield_generator/reactor (mid), engine (back). Combat view syncs overlay state each frame from `enemy.subsystems_destroyed` (→ DESTROYED) and `enemy.focused_subsystem` (→ HIGHLIGHTED). Rendered on a copy of the card composite so the overlay doesn't corrupt the cached surface.
- ⏳ **Hand-authored `composite_build` overrides for marquee bosses.** Optional polish. Content work, not engineering. Best done during playtesting once the procedural baseline is validated against real combat encounters. Adds an optional `composite_build` field on `EnemyShipTemplate` that provider checks before falling back to the generator.

### Phase C5 — Dual tech cinematic framework (~1.5 weeks) ⚠️ WIRED INTO COMBAT VIEW; TRIGGER DETECTION DEFERRED

- ✅ Timeline primitive (§4.3) — `engine/dual_tech_cinematic.py`
  - 6 phases (CAMERA_ZOOM / DARKEN_PORTRAITS / NAME_HOLD / COMBINED_RESOLVE / CHARGE / IMPACT / COMPLETE)
  - Standard (3.2s) + Ultimate (4.5s with CHARGE phase) variants
  - Factor queries for camera zoom, screen darken, portrait slide + alpha, tech-name alpha, combined resolve progress, charge intensity, impact shake
  - Element palette resolution — dominant_role / secondary_role / trail_role via spec §4.3 table
  - `consume_impact_trigger()` — one-shot trigger for emitting the tier-4 damage number + damage event
- ✅ Portrait renderer (§4.3 + §4.9) — `engine/dual_tech_portraits.py`
  - `PortraitConfig` dataclass (surface + optional faction_role)
  - `render_portraits(target, left, right, slide_factor, alpha, bottom_y)` — slide-in from screen edges, rests at bottom corners
  - Palette-role faction border stripe (callers choose role per crew member)
  - Decoupled from sprite pipeline — accepts pre-rendered `pygame.Surface` inputs
- ✅ Element trail renderer (§4.3) — `engine/dual_tech_element_trail.py`
  - `TrailConfig` dataclass (endpoints + dominant_role + trail_role + arc_height + trail_length)
  - `render_element_trail(target, config, progress)` — parabolic arc path, head at dominant_role + fading trail at trail_role
- ✅ **Controller orchestrator** — `engine/dual_tech_controller.py`
  - Owns timeline + renderer configs + on_impact callback
  - `from_inputs()` factory ties element roles through to the trail's dominant/trail roles
  - Single `update(dt)` / `render(screen)` / `is_complete` lifecycle
  - Tech-name text rendered with Tier-4 cinematic styling (dominant role + void_deep stroke, font size 32, bold)
- ✅ **combat_view wiring** — `spacegame/views/combat_view.py`
  - `_dual_tech_controller: Optional[DualTechController]` slot on the view
  - `trigger_dual_tech(...)` public method constructs controller + snapshots pre-cinematic camera zoom
  - `update()` delegates to controller when active, interpolates `SceneCamera.zoom` from `camera_zoom_factor`, clears slot + restores zoom on completion
  - `render()` delegates to controller last so the cinematic paints over all normal combat + UI layers
  - `dual_tech_active` property for external polling
- ✅ **Turn-clock pause hook** (§5.1) — combat_view `update()` blocks phase-specific logic while `dual_tech_active` is True. Animations, particles, and atmosphere continue updating; only phase advancement freezes.
- ⏳ **Deferred: trigger detection** — combat engine + content code decides which moves fire a dual tech and invokes `trigger_dual_tech()`. This is a mechanics question (what's a dual tech, how does the combo detector work?) outside engineering scope for this phase.

**Delivered as:**
- `engine/dual_tech_cinematic.py` + `tests/test_engine/test_dual_tech_cinematic.py` (65 tests)
- `engine/dual_tech_portraits.py` + `tests/test_engine/test_dual_tech_portraits.py` (14 tests)
- `engine/dual_tech_element_trail.py` + `tests/test_engine/test_dual_tech_element_trail.py` (17 tests)
- `engine/dual_tech_controller.py` + `tests/test_engine/test_dual_tech_controller.py` (23 tests)
- combat_view wiring + `tests/test_views/test_combat_view.py::TestDualTechCinematicWiring` (7 tests)
- **Total: 126 tests for C5**

### Phase C6 — Background atmospheric detail (~1 week, optional polish) ⚠️ DEBRIS + EDGE GLOW SHIPPED; ARC-FLASH + PARALLAX DEFERRED

- ✅ Debris streak + edge glow (§4.6) — `engine/combat_vfx.py` extensions
  - `_DebrisStreak` dataclass with ramp-in / hold / ramp-out alpha envelope
  - Per-danger spawn rate (safe + moderate = 0; dangerous = 0.25/sec; crimson = 1.5/sec)
  - Palette-role debris coloring (dangerous = `hud_warning`, crimson = `hud_critical`)
  - 2-3s lifespan per spec; 28-56px length range
  - Crimson-tier pulsing edge glow (`hud_critical` border with sine pulse, base alpha 22, amplitude 18, period 2.5s)
  - All effects gated on per-danger config — safe + moderate get a clean no-op
- ✅ **Arc-flash effect** — crimson-tier ambient arc-flash on 30-60s random timer (1-2 per minute per spec). `voltaic_strike`-colored edge band, peaks then decays linearly over 0.35s. Public `trigger_arc_flash()` for deterministic scripted fires.
- ✅ **Starfield parallax to camera** — `ParallaxStarfield.render` + `AnimatedBackground.render` accept `camera_offset`; each layer shifts by `offset * LAYER_PARALLAX[layer]`. combat_view passes `scene_camera.get_offset()` so far/mid/near starfield layers respond to cinematic pushes + shakes.

**Delivered as:** `engine/combat_vfx.py` extensions + `engine/backgrounds.py` extensions + `tests/test_engine/test_combat_atmosphere.py` (26 tests now) + `tests/test_engine/test_background_parallax.py` (6 tests).

### Total estimate: ~7-9 weeks

Parallelizable where noted. Realistic solo+agent cadence: one phase in flight at a time, 6-8 weeks end-to-end.

### Progress snapshot (as of C4 Session 3)

| Phase | State | Shipped |
|---|---|---|
| C1 Camera + pacing | ✅ | SceneCamera + combat_view integration |
| C2 VFX palette | ✅ | Projectiles / shields / destruction / atmosphere all palette-sourced |
| C3 Damage tiers + arena entry | ✅ primitives + view wiring (intro timeline drives camera + tint fade) | DamageTier primitive, ArenaEntry timeline, tier wiring, intro phase driven by timeline |
| C4 Unified pipeline + module targeting | ⚠️ 3 primitives shipped + portrait wiring; 3 follow-ups deferred (content/mechanics) | Module overlay, enemy build generator, enemy composite provider, portrait render swap |
| C5 Dual tech cinematic | ⚠️ all rendering + combat_view wiring + turn-clock pause shipped; trigger detection deferred (mechanics) | Timeline, portraits, element trail, controller, trigger_dual_tech() public API, pause hook |
| C6 Atmospheric detail | ✅ debris + edge glow + arc-flash + parallax shipped | _DebrisStreak primitive, per-danger spawn rates, crimson edge glow, voltaic arc-flash, camera-driven parallax |

---

## 8. Success criteria

Combat overhaul is done when:

1. **Visual palette compliance** holds across all combat output (player ship, enemies, VFX, UI). `assert_band_compliance` + `assert_role_compliance` pass for combat frame renders.
2. **Module targeting** is visually obvious: player can target a module, see it highlight, see the hit resolve on the specific region, see the damage persist on that region.
3. **Dual tech** triggers the cinematic framework. Player spontaneously says "oh that was sick" on first dual tech reveal.
4. **Camera responds** to action — zoom-in on attack, shake on impact, pacing beat between turns.
5. **Element identity visible** — player identifies which element a weapon is by its visual signature alone (without reading the name).
6. **Crimson-tier encounters** feel meaningfully different from moderate-tier, not just via tint but via atmospheric behavior.
7. **Destruction sequence** (already good) is preserved.
8. **Performance** holds 60 FPS with player + 4 enemies + 50 active particles + camera at 0.7 zoom on a 1080p arena. Target: 8ms per combat-render frame.

---

## 9. Open questions

1. **Enemy template migration format.** ✅ **RESOLVED** — Tag-based subsystems (see §11 below). Regular enemies get 1-2 subsystems from a canonical 6-tag palette; bosses/elites get 3-4.
2. **Dual tech portrait expressions.** Budget-dependent. If the existing portrait sprite sheets have only one expression, the cinematic works with neutral portraits; expression variants are a nice-to-have.
3. **Turn-clock pause during cinematics.** ✅ **RESOLVED** — implemented in combat_view (C5 session). ~2.4s pause accepted; playtesting will tune.
4. **Ultimate cinematic (~4.5s) budget.** Per-playthrough count of ultimates needs calibration. Currently estimated at < 2; might be ~4-6 given campaign flow. At 4.5s each, still well under 30s total screen time — not excessive.

---

## 11. Locked implementation decisions (post-deferral-review)

After shipping the engineering-scoped C-phase work, the five remaining deferrals were design-reviewed. Each now has a locked direction ready for implementation.

### 11.0 Implementation status

| Impl | Item | Status |
|---|---|---|
| 1 | C3 ArenaEntry polish (engine ignite + enemy slide-in) | ✅ shipped |
| 2 | C5 named pair registry + trigger detection | ✅ shipped (via bridge to existing `dual_tech.py`) |
| 3 | C4 boss `composite_build` override | ✅ shipped (data model + provider; no boss content yet) |
| 4 | C4 tag-based subsystems | ✅ shipped (palette, engine hooks, per-template authoring, backtick cycle + focus badge) |
| 5 | C4 destruction pipeline (benchmark + bucketed) | ✅ **fully shipped** — infrastructure (Impl 5) + per-instance composite cache + driver wiring (QA Pass 5 Tier 3.A–B, 2026-04-21). |

### 11.1 C5 dual tech trigger detection — **named pair registry**

**Decision:** Curated ~8-15 named crew pairs trigger dual techs. No emergent combo detection; no move-data flag.

**Data model:**

```python
# spacegame/models/dual_tech_registry.py (new)

@dataclass(frozen=True)
class DualTechPair:
    tech_id: str                # "frozen_inferno"
    tech_name: str              # "FROZEN INFERNO"
    crew_a_id: str              # "elena"
    crew_a_move_id: str         # "ice_spear"
    crew_b_id: str              # "marcus"
    crew_b_move_id: str         # "plasma_bolt"
    dominant_element: str       # "cryo"
    secondary_element: str      # "plasma"
    damage: int                 # base damage at tier-4 impact
    is_ultimate: bool = False   # 4.5s variant if True

DUAL_TECH_PAIRS: tuple[DualTechPair, ...] = (
    DualTechPair("frozen_inferno", "FROZEN INFERNO", "elena", "ice_spear",
                 "marcus", "plasma_bolt", "cryo", "plasma", damage=180),
    # ...8-15 curated pairs
)
```

**Trigger detection:** Combat engine's action-queue processor checks, at dispatch time, whether consecutive queued moves from different crew match a registered pair. On match → invoke `combat_view.trigger_dual_tech(...)` with pair's parameters + both crew portraits + tier-4 damage on impact.

### 11.2 C4 module targeting — **tag-based subsystems, 6-tag palette**

**Decision:** Universal mechanic. Every enemy has 1-2 subsystems (regular) or 3-4 (bosses/elites) drawn from a 6-tag canonical palette.

**Canonical subsystem palette:**

| Tag | Destruction effect | Read |
|---|---|---|
| `weapon_array` | Enemy damage output reduced by 40% | "break their guns" |
| `shield_generator` | Shield regen disabled + current shields stripped | "collapse the barrier" |
| `engine` | Evasion → 0 (universal); next turn skipped (universal tempo effect); flee disabled (cowardly bonus) | "cripple them" |
| `sensor_array` | Accuracy reduced by 30% | "blind them" |
| `cockpit` | Instant kill (low HP, high-risk target) | "headshot" |
| `reactor` | Energy regen → 0 | "brown them out" |

**Data model:**

```python
# EnemyShipTemplate adds:
targetable_subsystems: list[str] = field(default_factory=list)
# e.g., ["weapon_array", "engine"] for a pirate_raider

# EnemyShip (runtime) adds:
subsystem_hp: dict[str, int]           # per-subsystem HP remaining
subsystems_destroyed: set[str]         # which ones are gone
engines_just_destroyed: bool = False   # transient flag for tempo skip
```

**Combat engine integration:**
- Subsystem HP = `enemy.template.hull * 0.25` per subsystem (each takes 25% of enemy hull to destroy)
- Targeting: player selects target + optional subsystem focus
- Focused attacks deal half damage to hull, full damage to subsystem HP
- On subsystem HP → 0: apply effect, mark in `subsystems_destroyed`
- Engine destruction sets `engines_just_destroyed = True`; turn-skip path checks + clears this flag (mirrors existing `_frozen` check in `_execute_enemy_move`)

**Per-template authoring (✅ done):** All 60 enemies authored via `tools/assign_subsystems.py`. Rules applied:
- **Tier by hull:** regular (<150) → 2 subs, mid-boss (150-299) → 3 subs, big boss (≥300) → 4 subs. Named legendaries (Corsair King, Iron Maw, Void Leviathan, Ledger Phantom, The Collector, Pirate Lord, Crimson Dreadnought, Union Behemoth, Union Siege Cruiser) → 4 subs always.
- **Archetype order** (signature first, cockpit last for high-risk YOLO):
  - `aggressive` → weapon_array, engine, reactor, cockpit
  - `defensive` → shield_generator, reactor, weapon_array, cockpit
  - `evasive` → engine, sensor_array, weapon_array, cockpit
  - `cowardly` → engine, sensor_array, weapon_array, cockpit

**Player UX:** `` ` `` (backtick) cycles subsystem focus on the selected target; focus badge renders on enemy card (top-right, under sprite). Attacks against a focused subsystem route damage to its HP pool in addition to full hull damage (no split). Opt-in — no focus = classic combat.

### 11.3 C4 boss composite overrides — **optional field on EnemyShipTemplate**

**Decision:** `composite_build: Optional[dict]` in JSON. Provider checks before falling back to generator.

**Data model:**

```python
# EnemyShipTemplate adds:
composite_build: Optional[dict] = None  # ShipBuild.to_dict() format

# EnemyCompositeProvider.get_build checks:
if template.composite_build is not None:
    return ShipBuild.from_dict(template.composite_build)
return generate_enemy_build(template)  # current fallback
```

**Scope of authoring:** ~5-10 marquee bosses (legendary + act-one climaxes). Hand-authored silhouettes that read instantly distinct. Everyone else stays procedural.

### 11.4 C4 frame-animated destruction via ShipComposite — **bucketed progression**

**Decision:** Real-time `destruction_progress: float ∈ [0, 1]` on ShipComposite, quantized to 5 buckets (0, 0.25, 0.5, 0.75, 1.0). Rebuild on bucket change only. **Benchmark-first** — measure current pipeline cost before committing to universal rollout.

**Benchmark gate:** Reference ship (32×32 build, moderate complexity), measure rebuild cost in isolation. Thresholds:
- < 15ms/rebuild: proceed with direct bucketed implementation
- 15-30ms/rebuild: proceed with lazy precompute on encounter start (trade 40-60ms encounter-start spike for zero mid-combat cost)
- \> 30ms/rebuild: fall back to Option C (composite + particle hybrid; no destruction state in pipeline)

**Bucket visuals (✅ implemented in `_phase_destruction_damage`):**
- 0.0: intact
- 0.25: progressive RGB darkening (~14%), no dropout yet
- 0.50: ~28% darkening + 10% pixel dropout (early silhouette breaks)
- 0.75: ~41% darkening + 28% dropout (heavy structural damage)
- 1.0: ~55% darkening + 48% dropout (skeletal wreck)

Emissive pixels bypass both effects so engine glow / running lights stay readable through destruction. Pattern is seeded by build geometry → identical destruction across runs (replays + tests stable).

**Benchmark results (✅ measured via `tools/benchmark_composite_rebuild.py`):**
- Small regular (16×16, 119 px): 0.4 ms median
- Mid regular (40×28, 511 px): 1.6 ms median
- Legendary (56×40, 1031 px): 3.3 ms median, 4.1 ms p95

All well under the 15 ms direct-bucketed threshold → direct implementation chosen.

**API:** `ShipComposite.set_destruction_progress(float)` — quantizes to bucket, invalidates cache only on bucket change. `EnemyCompositeProvider.reset_destruction()` zeros all cached composites at encounter start (CombatView calls this in `on_enter`).

**Driver wiring — ✅ shipped (QA Pass 5 Tier 3.A–B, 2026-04-21):** Per-instance composite cache landed, unblocking the driver. `EnemyCompositeProvider.get_composite` now accepts an optional `instance_key` (the `EnemyShip` instance); per-instance entries isolate destruction progress so two enemies of the same template at different hull ratios no longer thrash the cache. Combat view's card-render path now sets `destruction_progress = 1.0 - (current_hull / template.hull)` before fetching the surface. `prune_dead_instances()` is called in `on_enter` to evict stale instance entries from prior encounters. Bucket quantization (5 levels) means rebuilds only fire on hull-threshold crossings — 0.8 → 0.75 triggers one rebuild, subsequent chip damage within the same bucket is free.

**Integration:** Existing `DestructionSequence` continues to drive fragments + flash + fire. The ShipComposite now wrecks progressively as hull depletes; the sequence plays over the already-damaged composite frame on kill.

### 11.5 C3 ArenaEntry polish — **wire engine ignite + enemy slide-in**

**Decision:** Full wiring. Combat view consumes `player_engine_ignite_factor` (multiplier on player ship's engine emissive) + `enemy_slide_offset(i)` (per-enemy x-offset from rest during INTRO phase).

**Implementation touch points:**
- Player ship render path applies `player_engine_ignite_factor * emissive_base` during INTRO
- Arena enemy render path offsets each enemy's x by `_arena_entry.enemy_slide_offset(i)` during INTRO
- All other render paths unchanged

---

## 10. Out of scope

- **Ground combat** — deferred; separate Tier 2 doc (`38_overhaul_ground_exploration.md`) per master plan
- **Combat AI behavior** — balance, not visual
- **Combat sound design** — Tier 3 audio framework (`40_audio_synthesis_framework.md`)
- **Campaign / story combat encounters** — the narrative framing around combat moments (pre-combat cutscenes, post-combat beats) — handled narratively in campaign docs
- **New crew abilities or tech types** — balance territory; this doc renders what exists

---

*Next Tier 2 doc candidate: `31_overhaul_ship_builder.md` — inherits camera and unified-pipeline work from this one; the ship builder is the second-most visible system.*
