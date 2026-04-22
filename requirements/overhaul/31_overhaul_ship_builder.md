# Ship Builder Visual Overhaul

> **Status:** DESIGN — Tier 2 doc. Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, and `30_overhaul_space_combat.md` (unified pipeline + camera).
>
> The ship builder is the player's most prolonged visual engagement with an individual ship. Combat shows ships in motion for seconds; the builder stages them for minutes. This doc defines the visual experience of assembling, inspecting, and customizing a ship.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Rendering changes
5. Gameplay changes forced by rendering
6. Dependencies
7. Phasing
8. Success criteria
9. Open questions
10. Out of scope

---

## 1. Current state — honest assessment

Factual snapshot per survey of `ship_builder_view.py` (~3,300 lines) and `shipyard_view.py` (~2,500 lines).

### 1.1 What's already strong

- **7-step composite rendering pipeline** — material fill → panel lines → edge highlight → material texture → outline → slot indicators → engine glow. Even simple builds look hand-crafted. This is the *foundation* we build on, not replace.
- **Physics constraint overlays** (`[I]` integrity, `[O]` center-of-mass, `[P]` exposure). Real-time visual feedback on structural validity, with semi-transparent color tints on the grid. Good discipline; aligns with AB §6.5 detail-density-as-signal.
- **Ghost preview with validation color coding** (red/amber/orange/gray). Placement feedback is immediate and readable.
- **Hull pixel mode** — 9 tools, shape palette, 4 material types, ghost preview. A real customization surface, not a token.
- **Rotation and flip during placement** (R cycles 0/90/180/270°, Q flips). Framework §15 already lived at module scale in the builder — it's the rendering pipeline that needs to catch up.
- **Cost-delta system with 80% refund on reduction** — thoughtful gameplay economy visible at checkout.

### 1.2 What's weak — the seven gaps

**Gap 1: The preview is a thumbnail, not a hero.**

The ship-composite render is a 100×80px panel in the bottom-right corner. The builder's entire visual focus is on the grid — a schematic — and the ship itself is a footnote. For a system the master plan frames as "Armored Core" influence (where assembly is a visual centerpiece), the ship being smaller than the module catalog is inverted.

**Gap 2: The ship floats in a void.**

No hangar, no context, no place. A ship in the builder has no "this is where I'm working on my ship" physicality. The canvas is a grid on black; the thumbnail is on solid color. No anchoring environment. Reference games (Armored Core's hangar, Starfield's outfitting bay, FF7's menu dignity) all frame the ship somewhere — it exists *in a place*.

**Gap 3: No rotation / no multi-angle inspection.**

The ship is rendered from one fixed orthographic angle. Engine pulse is the only animation. You can't turn the ship to see a detail on the other side, can't see the profile or silhouette from another angle. For a custom build, this flattens the "I built this" reward.

**Gap 4: Module catalog has no per-module visual preview.**

The catalog is a scrollable list with text specs + small pixel-art icon at best. Until you select a module and *start to place it*, you don't see it as a ship-scale rendered object. A player reading the catalog is shopping by spreadsheet, not by eye.

**Gap 5: Station/faction catalogs look identical.**

All 10 stations render the same card UI with the same palette. The only faction-identification is text ("Available at: Kepler_Station") and rep-gate messages. Per AB §4.8, faction color overlay is a first-class visual layer — the builder should *feel* different in a Commerce Guild hub than in a Crimson Reach outpost.

**Gap 6: Lighting direction is absent.**

The composite uses hand-placed panel lines + edge highlight, but doesn't apply a global directional light (AB §6.1). Ships in the builder read flat — like diagram illustrations — rather than as physical objects lit from upper-right. Then they enter combat and suddenly *do* have implied lighting direction. The transition reveals the builder as a different rendering space.

**Gap 7: No test-flight / preview-in-motion.**

Master plan §5 calls this out explicitly: "live preview-in-flight." Currently absent. You can build a ship in the drydock and have no idea how it *reads in motion* — silhouette against void, engine plume scale, combat-view scale — until you're actually in combat. That's a long feedback loop for a system where most of the fun is iteration.

### 1.3 What this doc addresses

- All seven gaps above
- Bringing the builder's rendering pipeline into alignment with combat's (§4.1 of combat doc) — the builder is where the combat pipeline's quality is most visible
- Station/faction visual distinction (AB §4.8 applied at shop-UI level)
- A lightweight camera for multi-angle inspection, reusing combat's `ArenaCamera` where sensible

---

## 2. Target feel — influences and reference moments

### 2.1 The three-influence synthesis

Ship builder is **Armored Core hangar-as-place, Starfield outfitting clarity, FF7 menu dignity.** Three references, each carrying specific cargo:

**Armored Core — hangar-as-place and test-pilot moment**

- The AC hangar is a *physical location*. Your mech is in it. The space has scale, ambient sound, lighting. You are standing next to a machine, not looking at a spreadsheet.
- **Rotatable preview.** You orbit the mech to inspect. Details you built are visible from the angles you care about.
- **Assembly menu chrome** — each manufacturer's parts are presented with their own visual language. Buying from Emeraude feels different from buying from BAWS. The catalog carries the manufacturer's identity.
- **Test pilot moment** — after assembly, you can boot up and fly. Short test-run. "Does this build feel right?" answered immediately.

**Starfield — outfitting clarity and component hierarchy**

- **Part-by-part inspection.** Each part has a dedicated inspection view where it's rendered at the scale of *a part*, not of a ship. Specs overlay. This is how catalogs should feel.
- **Live spec comparison** — hovering a new part shows delta against current part. Green up-arrow / red down-arrow. Reduces cognitive load.
- **Before/after snapshot** — when you swap a part, the ship silhouette updates in view. No "commit then find out" loop.

**FF7 — menu dignity**

- The menu system treats the player's time as worth respecting. Layout is spacious, typography has weight, transitions are not instant but are not delayed. A decision point is *framed*.
- Numerical data is organized by importance. Big number for the one that matters; smaller supporting numbers below.
- Confirm animations acknowledge the weight of decision — when you assign materia, there's a small flourish, not a silent tick.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Armored Core 6, "hangar first-look at assembled AC"** (2023). Camera pans around a fully-assembled mech in a hangar. Ambient workshop sound. Lights catch different angles. The moment says: *this is yours*. Aurelia equivalent: default idle in the builder drydock — ship rotates slowly (or camera orbits slowly, same net effect) in a rendered drydock environment, not in void.

2. **Armored Core 6, "parts selection with preview"** (2023). Selecting a part in the catalog renders it at large scale in the preview pane, specs align to the right, stats-delta indicators show impact. Aurelia equivalent: catalog selection → large module preview + delta against current → stats-delta chips in same frame.

3. **Starfield, "ship outfitter modify menu"** (2023). Select a part, see it highlighted on the ship, swap, watch the silhouette update in real-time. Aurelia equivalent: placement preview should ghost the module into its actual rendered form at its placed position — not as a shape outline.

4. **FF7, "materia menu confirm"** (1997). Attaching a materia has a small sparkle + sound. Brief, intentional. Aurelia equivalent: module placement confirmation — small material-specific sparkle (a rivet settle for steel; a chrome flash for Solari-band materials; a weld-bead gleam for frontier_canvas).

5. **Armored Core 6, "test AC boot from hangar floor"** (2023). After assembly, boot sequence launches you into a short test arena. Aurelia equivalent: a "test flight" mode — brief (~20s) sim arena where the built ship performs idle, thrust, turn, weapon-fire animations. Not combat; kinematic demonstration.

### 2.3 What this is not

- **Not a 3D modeler.** Aurelia is 2D pixel-art at heart; the "rotation" is either orthographic multi-angle views (front/profile/iso) or gentle tilt within a 2D frame, not full 3D.
- **Not a mini-game.** Placement, physics constraints, hull pixel mode — all are gameplay. The overhaul adds visual presence without adding interaction complexity.
- **Not a realistic hangar sim.** Workshop ambiance is *implied* — a tinted surround, a grid floor, lighting cue — not rendered in photoreal detail.
- **Not Armored Core difficulty.** AC's parts selection respects deep mastery. Aurelia respects approachability. The visual language borrows; the depth budget stays where current gameplay sets it.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Visual signal doing the work |
|---|---|---|
| Enter drydock | Entering a workshop | Hangar environment resolves from fade; ambient tint; ship at center, slow orbit idle |
| Select a module in catalog | Curiosity + comparison | Preview pane renders the module large with material + lighting; stats chips show delta vs current slot |
| Place a module (ghost phase) | Contemplation | Real composite render of module ghosted at cursor position; placement validity color-codes the ghost |
| Confirm module placement | Tactile satisfaction | Material-specific "settle" sparkle; subtle grid ripple at placement cell |
| Rotate / flip module | Immediate understanding | Ghost rotates with cursor; silhouette change visible before commit |
| Toggle physics overlay | Problem-solving mode | Overlay fades in with clear semantics; ship reads as diagnostic data |
| Hull pixel mode | Craft session | Ship zooms in slightly; pixel tools feel weighted; painting is satisfying |
| Review assembled ship | Pride + ownership | Slow orbit; manufacturer / faction identity legible at a glance; stats panel understated |
| Test flight mode | "Let's see it go" | Scene transitions to sim arena; ship performs maneuver sequence; camera follows |
| Confirm build (checkout) | Commitment (proportional to scale) | 1.2s scale-pop (existing) gets palette-aware treatment — material-specific flash color; cost delta tallies up |
| Enter a faction-specific shop | Place identity | Shop UI chrome tinted / accented for the faction; faction insignia visible; NPC vendor sprite if present |
| Look at a locked part | Aspirational clarity | Locked-state badge (visual, not just text); path-to-unlock shown inline |
| Share build (export) | Accomplishment | Build code panel; copy-to-clipboard feedback; optionally a small "ship card" generated |

### 3.2 What each emotion serves gameplay

- **Workshop presence** (enter) → the builder is a *place*, encouraging extended sessions
- **Curiosity + comparison** (catalog) → reduces decision cost; more parts get tried
- **Contemplation** (ghost phase) → players trust the placement preview; fewer undo operations
- **Tactile satisfaction** (confirm placement) → the feedback loop for assembly feels rewarding in itself
- **Craft session** (hull pixel) → creative customization is its own satisfaction vs. the utility of stats
- **Pride + ownership** (review) → the "I built this" moment, ready for shareable screenshots
- **"Let's see it go"** (test flight) → closes the build-test-iterate loop at the builder, not after combat
- **Commitment** (checkout) → an intentional decision point that respects the investment
- **Place identity** (faction shop) → builds the world through shopping; Crimson Reach's cockpit shop is a different place from Commerce Guild's

### 3.3 The non-goal: complexity-signaling

Builder is large; its visual design should make it feel *tractable*, not impressive-because-complicated. Physics constraints are real but the overlay system already reads them as diagnostic data. We don't want the builder to feel like a nuclear reactor console. We want it to feel like a workshop with a patient supervisor.

---

## 4. Rendering changes

### 4.1 Hangar environment — end the void

The drydock becomes a *place*. Three environment variants, selected per station context:

| Environment | Tint | Ambient detail | When |
|---|---|---|---|
| `hangar_standard` | Warm-neutral (slight plasma_hot bias) | Faint grid floor, distant wall shapes, warm edge lighting | Default civilian/commerce stations |
| `hangar_industrial` | Cool-warm mix (union_ceramic base with plasma_core accents) | Visible gantries, hanging chains, welding spark occasional | Foundry / Miners Union stations |
| `hangar_military` | Cool (collective_composite tint, hud_cyan accents) | Grid deck lines, status readouts on walls | Science Collective / military stations |
| `hangar_outlaw` | Dim (frontier_canvas tint, hud_warning sparse accents) | Cluttered wall detritus, flickering fluorescent | Crimson Reach / black-market stations |

Implementation: each environment is a backdrop Surface rendered behind the ship preview + grid overlay. Generated procedurally (per framework §3) using the same palette the ships themselves are made from. Environment is *quiet* — not detailed enough to distract. Its job is to say "you are in a hangar" without pulling focus.

**Cost:** ~1 week — four procedurally-generated backdrop variants, integration into the builder view's rendering order.

**Benefit:** ends Gap 2 (void), establishes AB §8 scene-overlay discipline in the builder, sets faction-context before the shop UI does.

### 4.2 Ship preview as hero — large, rotatable, living

The current 100×80 thumbnail is replaced with a **large central preview pane**:

- **Default pane size:** ~560×400 at 1080p (scales per resolution setting). Dominant visual in the builder view.
- **Idle animation:** slow orbit (one full 360° in ~45s) via camera state `PREVIEW_ORBIT` — the camera pans; the ship doesn't actually rotate (orthographic 2D, no 3D). Three canonical angles: **front** (0°), **profile** (90°), **three-quarter** (45°). Orbit cycles through these with smooth tweening, not continuous rotation.
- **User control:** `[<]` `[>]` cycle manual angle. `[Space]` pauses orbit at current angle. `[R]` resumes.
- **Engine pulse** (existing) retained, amplified slightly — emissive reads stronger because the preview is larger.
- **Wear, damage, modifications** all render faithfully. This is where the player *sees* what they built.

**Multi-angle rendering strategy:** each module's `rasterize()` function (framework §15.1 registry) declares a `render_angle` parameter. The composite renders per angle. Same pipeline as combat (§4.1 of combat doc), but the preview pane renders at three angles rather than one.

**Cost:** ~2 weeks. Module rasterize functions extended to accept angle parameter (framework §15 already scoped this). Preview pane UI built. Camera orbit state integrated.

**Benefit:** ends Gap 1 (preview is hero now), Gap 3 (multi-angle). Directly serves §3.1 pride + ownership emotion.

### 4.3 Module catalog — preview-before-place

The catalog gains a **preview panel** that renders the currently-selected module in isolation, large:

- Module rendered with its manufacturer's material, lit per AB §6.1, at ~120×120 effective size
- Module rotates slowly in preview (same trick — camera orbits, not the module, but effect reads as rotation)
- Specs panel beside preview shows:
  - Current-slot occupant (if replacing) vs new module — **side-by-side silhouette + key stats**
  - Delta chips: `+4 Hull` (green), `-2 Weight` (green), `-1 Thrust` (red)
  - Manufacturer signature at bottom (logo + color strip, AB §4.8)

**Interaction:** selecting a catalog entry updates the preview in <200ms. Confirming the selection moves the module to the placement-ghost state on the grid.

**Cost:** ~1.5 weeks. New `module_preview_pane.py` rendering component. Stats-delta comparison logic.

**Benefit:** ends Gap 4 (no per-module preview). Serves §3.1 curiosity + comparison emotion.

### 4.4 Placement ghost — render the real module

Current ghost is a shape outline or simple block in red/amber/orange/gray. Upgrade:

- Ghost renders the **actual module composite** at the cursor position with reduced alpha (60%)
- Validity color-tint applies on top (red tint for invalid, amber for warning, no tint for valid)
- Ghost includes the module's **material**, not just shape — a Foundry weapon ghost *looks* like Foundry (union_ceramic band, rivets visible) even as a ghost
- Rotation/flip feedback: ghost updates immediately

**Cost:** ~3 days. Reuse module composite rendering; apply alpha + tint overlay.

**Benefit:** addresses Gap 4 at placement level. Serves §3.1 contemplation emotion.

### 4.5 Physics overlay — preserve, align with palette

The current `[I]` `[O]` `[P]` overlays work well. Minor changes:

- **Color source:** migrate from hand-coded RGB to palette roles per AB §2. Integrity passes use `hud_muted` / `hud_warning` / `hud_critical` role gradient.
- **Overlay opacity:** unchanged (existing feels right).
- **Addition:** overlays render *through* the palette-snap pipeline. This matters because the builder's overlay pixels must not drift from palette (colorblind modes need to work).

**Cost:** ~2 days. Color-source substitution.

### 4.6 Station shop visual identity — faction chrome

Each station's shop UI gains a **faction chrome layer** per AB §4.8:

- **Background tint** on the shop panel: subtle color wash matching the dominant faction (Commerce Guild = cool cyan wash; Crimson Reach = warm crimson wash; etc.)
- **Catalog card accent bars:** faction stripe color (the same stripe role a module from that faction would carry)
- **Faction insignia** in the shop header (hand-authored pixel art per framework §11.5 portrait/character boundary)
- **Locked items:** visual badge (crossed-bolt icon or faction-insignia with lock) instead of text-only tooltip; unlock path shown inline
- **NPC vendor sprite** (optional, if bandwidth) — faction-appropriate character pixel art in the shop corner. Silent — no dialogue. Just presence.

**Cost:** ~2 weeks. Four hangar environment overlays (§4.1) already establish the tint system; shop UI extends it. Locked badges are small icons. Insignia are hand-authored (one per faction = 5 total).

**Benefit:** ends Gap 5 (faction identity absent). Serves §3.1 place identity emotion. Reinforces worldbuilding coherence.

### 4.7 Test-flight preview mode — the Armored Core moment

A new mode: after a build is confirmed (or via explicit `[T]` button in drydock), the ship enters a **20-second test flight sim**:

- **Scene:** neutral sim arena — dark void with a grid floor vanishing into distance; three target drones visible at mid-range
- **Sequence (scripted):**
  - 0–3s: ship boots from hangar floor (arena-entry animation from combat §4.8 reused here)
  - 3–8s: ship thrusts forward (engine plume at full strength); camera tracks
  - 8–12s: ship maneuvers (90° turn + strafe — shows how center-of-mass affects handling visibly)
  - 12–18s: ship fires one burst from each equipped weapon (shows muzzle flash, projectile visual, impact on drone)
  - 18–20s: ship returns to idle; camera pulls back
- **Afterward:** player exits back to drydock with no resource cost — this is a sim

**Implementation:** reuses combat's `ArenaCamera`, arena entry animation (combat §4.8), projectile system. No AI — scripted sequence.

**Cost:** ~1.5 weeks. Mostly scripting + integration with existing combat-side systems.

**Benefit:** ends Gap 7 (no preview-in-flight). Serves the tight build-test-iterate loop master plan §5 named.

### 4.8 Hull pixel mode — lighting unification

Hull pixel mode currently renders flat — recoloring works but the ship doesn't change lighting response as pixels change. Update:

- Pixel-mode edits apply to the *material band* field of the pixel, not just a color value. A player setting a pixel to "highlight" changes that pixel's band-index.
- The rendered result applies global lighting per AB §6.1 even in pixel mode.
- Ghost preview shows lit result, not raw material swatch.

**Cost:** ~1 week. Data-model shift (pixel stores band-index, not RGB); pixel-mode tool UI updated.

**Benefit:** hull customization interacts with lighting discipline (AB §6); hull pixel creations will render consistently whether in builder preview or in combat.

### 4.9 Confirm animation — palette-aware

Existing 1.2s scale-pop with white flash is good. Upgrade:

- Flash color pulls from the dominant material's `specular` band entry (brightest in the band)
- Ship rendered at 3× during scale-pop uses the preview-pane render (lit, three-quarter angle)
- Post-flash: brief ambient glow pulse on engine modules (1 second fade from full-emissive to normal)

**Cost:** ~2 days. Tweaks to existing animation.

### 4.10 Build sharing UI — polish pass

Build sharing works functionally. Polish:

- **Share panel:** dedicated overlay (not just a button + clipboard). Shows the build's preview, the code, a QR variant (optional), copy-to-clipboard feedback animation
- **Import panel:** paste target, preview renders the shared build in a hangar context, unlock-check surfaces as visual badges on individual modules, confirm imports

**Cost:** ~1 week. Existing share/import hooks gain a wrapping UI.

**Benefit:** accomplishment emotion (§3.1 share build).

---

## 5. Gameplay changes forced by rendering

### 5.1 Test flight costs nothing

§4.7 test flight is a sim — no currency, no time, no cost. This is a gameplay commitment: players can iterate freely. No gameplay change vs current (there is no test mode to compare to), but worth stating explicitly: the test flight is *never* a gating mechanism for anything. It exists solely for player feedback.

### 5.2 Module rotation/flip persistence

Current placement supports rotation/flip but storage format per-module may or may not preserve it correctly across save/load. The unified pipeline (§4.2) depends on angle and rotation being faithful data. If the current save format drops rotation, migrate: rotation and flip become first-class `PlacedModule` fields.

### 5.3 No other gameplay changes

All other changes are visual or UI-chrome additive. Catalog still gates by faction rep. Physics constraints still block confirm when violated. Costs, refunds, blueprint unlocks — unchanged.

---

## 6. Dependencies

### 6.1 On other overhaul docs

- **`30_overhaul_space_combat.md` §4.1** (unified ship pipeline) — directly shared. The combat doc's §4.1 work is the builder's §4.2 preview upgrade.
- **`30_overhaul_space_combat.md` §4.4** (camera system) — reused for preview orbit (`PREVIEW_ORBIT` state) and test flight camera.
- **`30_overhaul_space_combat.md` §4.8** (arena entry animation) — reused for test flight boot sequence.
- **`20_aesthetic_bible.md` §4** (manufacturer profiles) — catalog must surface manufacturer identity (shape vocabulary, signature color)
- **`20_aesthetic_bible.md` §4.8** (faction color overlays) — station shop chrome depends on this
- **`20_aesthetic_bible.md` §6** (composition, lighting) — ship preview uses global lighting
- **`10_programmatic_generation_framework.md` §15** (extensibility) — rotation as first-class module data field

### 6.2 On production code

- `spacegame/views/ship_builder_view.py` — extended heavily
- `spacegame/views/shipyard_view.py` — extended for faction chrome
- `spacegame/engine/ship_composite.py` — rebuilt (framework §2), consumed by both
- `spacegame/models/ship_build.py` — rotation/flip as first-class PlacedModule fields
- `data/ships/frames.json`, `data/ships/modules.json` — unchanged
- `data/ships/factions.json` (or equivalent) — faction insignia references

### 6.3 On Tier 3 parallel docs

- **`42_ui_chrome_components.md` (Tier 3, not written)** — shop UI card layouts, catalog cards, overlay panels all want to inherit standards from here. Can ship without; benefits from coordination.

---

## 7. Phasing

Builder overhaul is substantial. Suggest 5 phases. Several parallelizable with combat overhaul phases; §7 notes where.

### Phase B1 — Hangar environment + unified preview pipeline (~2 weeks)

- Build four hangar-environment procedural backdrops (§4.1)
- Upgrade preview pane from thumbnail to large central hero (§4.2) — **depends on** combat Phase C4 (unified ship pipeline)
- Camera `PREVIEW_ORBIT` state — depends on combat Phase C1 (camera)

**Why first:** highest "feels different" payoff per unit. Ends Gaps 1, 2, 3 simultaneously. Can begin backdrops while combat C1/C4 are in flight.

### Phase B2 — Catalog preview + placement ghost upgrade (~1.5 weeks)

- Module preview panel with delta chips (§4.3)
- Placement ghost renders actual composite (§4.4)

**Why parallelizable:** doesn't block on B1; can co-develop.

### Phase B3 — Faction shop chrome (~2 weeks)

- Shop UI tinting + accent stripes per faction
- Faction insignia (5 hand-authored pixel artworks)
- Locked-item badges
- Optional vendor sprites

**Why third:** standalone scope. Depends on AB §4.8 (already defined). Can parallelize with B1/B2.

### Phase B4 — Hull pixel mode unification + physics overlay palette alignment (~1 week)

- Hull pixel mode stores band-index (§4.8)
- Physics overlays migrate to palette roles (§4.5)

**Why shorter:** mostly data model + color-source substitution.

### Phase B5 — Test flight mode (~1.5 weeks)

- Test flight scripted sequence (§4.7)
- Integration with combat arena-entry animation + camera

**Why last:** depends on combat Phase C1 (camera) AND C4 (unified pipeline for test-flight ship render). Ships after both.

### Phase B6 — Confirm animation polish + build sharing UI (~1 week, polish)

- Confirm animation palette-aware (§4.9)
- Build share/import overlay UI (§4.10)

**Why last:** polish tier.

### Total estimate: ~6-8 weeks

Assuming parallel development with combat overhaul where dependencies allow. Solo+agent realistic cadence: 8-10 weeks including coordination with combat work.

---

## 8. Success criteria

Builder overhaul is done when:

1. **The ship is the hero.** Preview pane is central; player's eye goes to the ship first, catalog and stats second.
2. **The drydock is a place.** Hangar environment reads. Faction-specific stations feel different.
3. **Multi-angle inspection works.** Player can orbit or cycle angles to see a build from profile, front, three-quarter.
4. **Catalog browsing is visual.** Selecting a module shows it at part-scale with lighting, with stat deltas. Shopping by eye, not spreadsheet.
5. **Placement ghost is faithful.** Ghosted module looks like the actual module at reduced alpha; rotation/flip preview is immediate.
6. **Test flight ships.** 20-second sim sequence loads, plays, returns to drydock without resource cost.
7. **Faction identity legible.** A Crimson Reach shop is visually distinct from a Commerce Guild shop without reading any text.
8. **Hull pixel mode unified.** Pixel edits render through global lighting; preview matches combat appearance.
9. **Palette compliance holds** across the builder view, including overlays, ghosts, preview panels.
10. **Performance.** Builder holds 60 FPS at 1080p with ~40 modules placed + hangar backdrop + preview orbit animation. Target: 10ms per builder-render frame (slightly more lenient than combat since builder is less particle-heavy).

---

## 9. Open questions

1. **Camera orbit interpolation: snap-between-angles or continuous tween?** Snap = simpler, reads as orthographic and honest. Continuous tween = smoother but reveals that underlying rendering is 2D (intermediate angles can't be authored). **Lean: three canonical angles with smooth-tween between them**, matching orthographic convention.
2. **Test flight arena — reuse combat arena or separate sim arena?** Separate sim avoids confusion ("is this a real fight?"). Reuse combat arena keeps rendering cost down. **Lean: separate sim arena with distinctive "SIMULATION" corner label.**
3. **Vendor sprite bandwidth.** Five faction shops × one vendor each = five sprites. Hand-authored pixel art, not procgen. If budget-constrained, defer vendor sprites; faction chrome alone (§4.6) still solves Gap 5.
4. **Hangar environment music/ambience.** Out of scope for this doc (Tier 3 audio), but the environment design allows for per-hangar ambient audio (workshop hum for industrial; distant news-ticker for commerce; tense silence for outlaw). Flagged for audio Tier 3.
5. **Pixel mode undo depth vs memory.** Current undo is limited. If hull pixel mode becomes a bigger craft session (§3.1), deeper undo might matter. Flagged, not scoped.

---

## 10. Out of scope

- **Ship blueprint unlock progression** — gameplay / economy
- **New ship frames or modules** — content scope, not visual
- **Combat integration of build-specific features** — covered in combat doc
- **Multiplayer / build-trading economy** — not in current project scope
- **Physics simulation accuracy** — current constraint system is approximate and that's fine; not a rendering concern
- **Audio / ambient sound** — Tier 3 audio framework

---

*Next Tier 2 doc candidate: `33_overhaul_galaxy_map.md` or `32_overhaul_mining.md`. Galaxy map has clear influence anchor (No Man's Sky warp / Starfield grav-jump) and is a high-traffic system. Mining has Cookie Clicker / Universal Paperclips influence for click-juice — also high-traffic but lower visual stakes. User's call which ships first.*
