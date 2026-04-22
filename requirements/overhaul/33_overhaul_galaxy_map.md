# Galaxy Map Visual Overhaul

> **Status:** DESIGN — Tier 2 doc, visual-overhaul scope per master plan §5. The galaxy map is Aurelia's most-frequently-visited screen after the cockpit HUD; players look at it constantly for navigation, mission selection, market routing, and worldbuilding recall. Every visual investment here compounds across every play session.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `30_overhaul_space_combat.md` (shared camera system), `31_overhaul_ship_builder.md` (unified pipeline). Coordinates with `requirements/cultural_guide.md` for galactic worldbuilding.

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

Factual snapshot per survey of `galaxy_map_view.py` (~1,695 lines).

### 1.1 What's already strong

- **Rich per-system visual language.** Circular portraits, danger-dot indicator (safe/moderate/dangerous), faction halo ring, reputation pip, current-system pulse, hover glow, selection ring. Six visual layers stacked per system card with distinct meanings — information-dense without being noisy.
- **Pulsing mission markers + animated dashed route preview.** The diamond-glow markers + real-time route line with midway fuel/distance labels are genuinely clear. Navigation intent communicates immediately. Best feel element in the current view.
- **Event / political indicators** on systems (yellow pulsing dot for galactic events, cyan diamond for political events) — the galaxy feels *partially* alive already.
- **Intel-gated information discipline.** Danger and faction details hidden for unvisited systems until `system_intel` skill threshold is reached. Remote-price surfacing requires `remote_prices` skill. Knowledge feels earned.
- **Travel animation exists** — ~0.5s + distance-scaled, eased with warp-trail particles, mid-route encounter interruption. The bones of a jump sequence are present.
- **Animated starfield backdrop** with seeded procedural generation + parallax. Not empty.
- **Route encounter risk calculation** (danger level × distance) with color-coded warning when risk > 20%. Gameplay-legible.

### 1.2 What's weak — the five gaps

**Gap 1: No scale reverence.**

The galaxy reads as a schematic diagram, not as a place with cosmic scale. Travel is ~0.5s of eased motion across a 2D plane. Destination resolves instantly. There is no moment where the player *feels* the jump. The master plan's explicit target — No Man's Sky warp / Starfield grav-jump parallax and scale reverence — is the largest missing beat.

**Gap 2: No zoom or pan.**

Fixed 2.4x scale, static viewport. Player has no control over how they look at the galaxy. As the galaxy grows (11 systems v1, more in future content), viewport lock becomes limiting. Players can't inspect clusters, can't pull back for dominion-view, can't zoom on a specific route.

**Gap 3: No faction territory visualization.**

Faction halos are **per-system** only. There is no visible "this region of space is Crimson Reach," no shifting borders as political events resolve, no sense of contested space. For a game with faction-driven narrative and territory-based gameplay (per `requirements/game_systems.md`), the political geography is invisible at the galaxy level.

**Gap 4: Parallax starfield exists but doesn't do work.**

The backdrop is present but static in response to player motion. It animates (slow drift) but doesn't react to zoom/pan (because neither exists) or to travel (stars don't streak during jump). The parallax investment isn't paying off visually.

**Gap 5: Travel is a screen-wipe, not an event.**

Current travel animation is functional — ship icon moves, arrives. There is no spatial drama. Compare to reference games where jumping between stars is a *whole-screen cinematic event* (Starfield) or a *cosmic-scale transit* (No Man's Sky). Aurelia's travel currently reads as "navigating a menu at speed."

### 1.3 Secondary gaps

- **No dynamic galaxy breathing.** Events tick per `game_day` but the visual representation doesn't reward players for observing the map over time. A player who opens the galaxy map after 30 days should *see* that things moved.
- **No galactic-landmark features.** Anomalies, wrecks, legendary points of interest mentioned in other overhaul docs (salvage's Named Wrecks, mining's Legendary Seams) have no representation on the galaxy map.
- **System transitions are view-state changes, not places.** Arriving at a system drops the player straight into trading view. There's no "approach" moment where the system is established visually.

### 1.4 What this doc addresses

- Gap 1 (scale reverence) via cinematic jump sequence (§4.1)
- Gap 2 (zoom/pan) via camera controls (§4.2)
- Gap 3 (faction territory) via dominion overlay (§4.3)
- Gap 4 (parallax) via responsive starfield (§4.4)
- Gap 5 (travel as event) via full jump cinematic (§4.1 integrated)
- Secondary gaps via living-galaxy breathing (§4.5), landmark integration (§4.6), system approach moments (§4.7)

---

## 2. Target feel — influences and reference moments

### 2.1 The three-influence synthesis

Galaxy map is **lived-in-cosmic — a navigation tool that acknowledges cosmic scale without theatricality**. Three references:

**Starfield — grav-jump as mundane industrial cinematic**

- The jump is a cinematic beat, 2-3 seconds, punchy.
- The ship *does this* because that's what ships do. It's not miraculous.
- Jump animation establishes destination — the target system resolves with atmospheric detail as you arrive.
- Navigation UI is clean, slightly brutalist, information-dense without being crowded.

**No Man's Sky — warp depth and cosmic scale**

- Starfield-style jump is punchy but shallow; NMS warp goes deeper — stars streak into lines, the galaxy's scale is felt.
- Parallax during warp carries the perception of passing through real distance.
- The galaxy map itself has scale reverence: the camera can pull *way* back, showing arm structures, clusters, the vastness.

**Mass Effect (galaxy map) — dignity of choice and faction geography**

- The galaxy map frames *a decision space*. Each system is a potential story.
- Faction territory is visible — blue Citadel space, yellow Alliance, red Terminus.
- Zoom hierarchy: galaxy → cluster → system → planet → surface. Each level has its own visual language.
- Navigation feels deliberate, not arcade-like.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Starfield, "first grav-jump"** (2023). ~2.5s. Ship orients, jump drive charges visibly, flash, arrival. The ship *tilts* into the jump — there's physicality. Aurelia equivalent: travel cinematic (§4.1) — full 3-4s sequence with charge, flash, streak, arrival.

2. **No Man's Sky, "galactic map zoom-out to galactic scale"** (2016+). Start at your system; pull back; pass through the local cluster; pass through nebula structures; arrive at a view of the entire galaxy spiral. Aurelia equivalent: zoom-out view (§4.2) reveals regional structure the player wasn't necessarily aware of — faction territory, trade lanes, anomaly zones.

3. **Mass Effect 2, "Omega 4 relay approach"** (2010). A specific system has a specific *approach*. Not all systems are visually identical. Aurelia equivalent: system approach animation (§4.7) — arriving at a notable system (home system, story-critical system, anomaly) has a specific visual signature.

4. **Elite Dangerous, "witch-space transit"** (2014). Between jumps, a tunnel of light; something unsettling about being *between* places. Aurelia equivalent: the brief mid-jump view (§4.1 mid-sequence) where the player is neither at origin nor destination — acknowledges the space between.

5. **Starfield galaxy map, "faction territory at galactic zoom"** (2023). Faction boundaries visible as subtle regional tints at high zoom. Aurelia equivalent: dominion overlay (§4.3) — active at medium/far zoom, fades at close zoom to avoid clutter.

### 2.3 What this is not

- **Not Eve Online.** We are not building a data-dense 3D galaxy for strategic warfare. 2D is the medium.
- **Not Sid Meier's Space Empires.** Not a strategy layer. The map serves travel + mission-selection + worldbuilding recall; it is not a territorial wargame in itself.
- **Not realistic astronomy.** The galaxy is stylized. Distances are gameplay-calibrated, not scientific.
- **Not a menu.** The galaxy map is a *place you look at*, not a screen you click through.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Visual signal |
|---|---|---|
| Open galaxy map from cockpit | Navigational intent | Map resolves from fade; current system highlighted with pulse; player orientation clear |
| Zoom out to regional view | Awareness of scale | Galaxy backdrop resolves at higher detail; faction territory overlay fades in; starfield density visible |
| Zoom out to galactic view | Cosmic reverence | Arm structures visible; anomaly zones marked; the Expanse *is big* |
| Hover a system | Evaluation | Info panel populates; route preview with distance/fuel; risk color-codes |
| Commit to travel | Intention | Confirmation modal; then jump sequence begins |
| Jump charge phase | Tension | Starfield dims slightly; ship icon glows; audio cue (Tier 3) |
| Jump transit (mid-sequence) | Motion | Stars streak; direction visible; destination system resolves from scale |
| Arrival at destination | Arrival | Jump flash fades; destination system resolves; brief atmospheric detail if system is notable |
| Route plotted with multiple hops | Plan-making | Multi-leg route line with intermediate-system labels; cumulative distance/fuel |
| Mission marker updates | Acknowledged progress | Marker pulses briefly differently when objective advances |
| Galactic event resolves | "Something moved" | Affected systems flicker briefly on next map-open; event-log accessible |
| Faction territory shifts | Political read | Dominion overlay updates with subtle animation on map-open after change |
| Discover a new landmark | Finding something | Landmark marker fades in with subtle particles; catalogued in map legend |
| Approach a notable system | Arrival moment | Specific approach animation — home system feels like home, hostile system feels hostile |

### 3.2 What each emotion serves gameplay

- **Navigational intent** (open) → the player knows where they are and where they can go in <1 second
- **Awareness of scale / cosmic reverence** (zoom) → the Expanse feels big; travel feels consequential
- **Evaluation → intention** (hover → commit) → route decisions are framed, not mechanical
- **Tension → motion → arrival** (jump sequence) → travel carries weight; destination matters because getting there was *something*
- **Plan-making** (multi-hop) → multi-system trading and questing are visible plans, not spreadsheets
- **"Something moved"** (events) → the galaxy persists when the player is elsewhere
- **Political read** (faction) → worldbuilding visible without exposition
- **Finding something** (landmarks) → the galaxy rewards attention

### 3.3 The non-goal: immersion-over-function

The galaxy map is first and foremost a navigation tool. Visual work must serve that function. Any cinematic beat (jump sequence, approach animation) must be **skippable / speed-upable** — the player who's jumped 40 times this session doesn't need the full 3.5s sequence every time. Discipline: cinematic on first use per session; abbreviated thereafter. Player-configurable.

---

## 4. Rendering changes

### 4.1 Jump sequence cinematic (the headline change)

Current: ~0.5s eased motion + warp-trail particles + distance-scaled time. Replace with a scripted multi-phase sequence:

**Phase A — Charge (t=0.0 to t=1.0s, ~1.0s)**
- Current system background darkens slightly (vignette intensifies)
- Player ship icon pulses at current position; emissive glow builds on the icon
- Distant stars in backdrop briefly zoom in (slight parallax)
- Audio cue slot for Tier 3 (charge hum)

**Phase B — Flash and streak (t=1.0s to t=2.2s, ~1.2s)**
- Bright flash at ship position (white → plasma_core gradient, 0.15s)
- Stars in backdrop stretch into lines in the travel direction; parallax accelerates
- Ship icon disappears into the streak
- Direction visible — the player sees they are *moving toward* the destination, not teleporting

**Phase C — Transit (t=2.2s to t=3.0s, ~0.8s)**
- Streak continues; destination system resolves from a point to its full representation (portrait, halo, pip)
- Briefly: a mid-jump "between" state where neither origin nor destination is dominant

**Phase D — Arrival (t=3.0s to t=3.5s, ~0.5s)**
- Streak resolves; destination system pulses briefly on arrival (inverse of current-system pulse)
- Ship icon re-materializes at destination
- Info panel updates

**Total: ~3.5s** for first-per-session jumps. Subsequent jumps abbreviate (Phase B + D only, ~1.5s total). Player-configurable "jump speed" setting (Full / Fast / Minimal / Instant).

**Mid-route encounter interruption** (existing behavior) preserved — if an encounter triggers during Phase B or C, sequence pauses cleanly and falls into encounter view.

**Cost:** ~2 weeks. Scripted sequence using existing camera/particle systems. New starfield-streaking effect.

### 4.2 Zoom and pan controls

Player-controllable camera with discrete zoom tiers:

| Zoom tier | Scale | Content visible |
|---|---|---|
| **Close** | 3.5x | Individual system detail, mission marker clutter, route preview |
| **Default** | 2.4x (current) | Standard navigation view |
| **Regional** | 1.2x | Cluster view; faction territory overlay prominent; trade lane visible |
| **Galactic** | 0.5x | Whole-galaxy view; arm structure + anomaly zones + faction regions |

Controls:
- Mouse wheel or `+` / `-` keys: zoom in/out one tier
- Click-drag or arrow keys: pan (limited by galaxy bounds + padding)
- Middle-click or `C` key: re-center on player
- `M` key: jump to active mission target (auto-zoom and pan)

**Zoom transitions:** 0.4s ease between tiers. Starfield density adjusts per tier (denser at close zoom, sparser at galactic zoom — parallax reveals scale).

**Cost:** ~1.5 weeks. Camera + zoom state machine + control wiring + zoom-specific rendering logic.

### 4.3 Faction dominion overlay

At Regional zoom and Galactic zoom tiers, render a **faction territory overlay**:

- Each faction has a defined "core" set of systems + "contested" boundary systems + "extended" influence systems
- Rendered as a low-alpha (20-30%) tinted region using Voronoi-like cell decomposition around faction systems
- Faction colors pulled from palette (AB §4.8): `reach_crimson` for Crimson Reach dominion, `hud_cyan` for Commerce Guild, `union_ceramic_bright` for Miners Union, `collective_composite` for Science Collective, `frontier_canvas` for Frontier Alliance
- Contested/boundary systems show blended colors — two factions' tints overlap
- Overlay fades to zero at Close and Default zoom (avoids cluttering navigation-focused view)
- Overlay responds to political events: faction expansion pushes the boundary outward; contested systems animate a slight border pulse during active political events

**Cost:** ~2 weeks. Voronoi decomposition of system positions; faction data extension; overlay rendering; political event response integration.

**Benefit:** ends Gap 3. Political geography becomes visible; faction narrative gains geographic presence.

### 4.4 Responsive starfield / nebula backdrop

Current backdrop is seeded procedural starfield. Extend:

- **Parallax response** — starfield drifts at 15-25% of camera pan speed (slower than foreground); zoom transitions cause stars to breathe (come in closer at low zoom, recede at high zoom)
- **Nebula density variation** — at Galactic zoom, major nebula structures become visible as colored regions (3-5 named regions v1: The Silk Drift (violet), The Anvil (orange-red), The Cold Veil (cyan-white), The Quiet Deep (muted), The Scattered Shoals (mixed))
- **Arm structure at Galactic zoom** — subtle spiral arm density variation (one full arm visible at galactic scale)
- **Traffic lanes (Regional zoom)** — trade routes visible as faintly-lit paths between high-commerce systems (renders automatically based on system trade_activity metadata)

**Cost:** ~1.5 weeks. Extension to `AnimatedBackground` system; new nebula rendering via framework §3 primitives; traffic-lane visualization.

**Benefit:** ends Gap 4. Parallax does real work; scale is felt.

### 4.5 Living-galaxy breathing

On map-open, check for changes since last map-open:

- **Event resolution** — systems affected by events that resolved since last session briefly flicker (subtle, 0.8s); affected-systems get a "recently changed" marker for the player's next visit
- **Faction territory shifts** — dominion overlay animates the change on open (old boundary → new boundary, 1.0s morph)
- **New landmarks** — newly-discovered/unlocked landmarks fade in with subtle particle beat
- **Active events pulse** — existing behavior (yellow pulsing dots) preserved; slightly richer with color variation per event type (SHORTAGE warm, ATTACK red, GLUT cyan, etc.)

**Cost:** ~1 week. Map-state-change tracking; morph animation; event-type color differentiation.

### 4.6 Landmark integration

Landmarks from other systems unify visually:

| Landmark source | Visual |
|---|---|
| Named Wrecks (salvage §7.1) | Small skull-or-wreck icon on system with wreck; fades in when wreck is discovered |
| Legendary Seams (mining §7.2) | Small gem-or-vein icon on mining systems with unfinished legendary seams |
| Anomaly Investigations (mining §7.3, salvage §7.3) | Small question-mark icon that resolves to anomaly type on hover |
| Story-critical systems | Faction-colored quest banner icon |
| Home system | Small house-or-hearth icon on the system the player designates as home |

All landmark icons are small (8-12px), placed slightly off the system portrait to avoid overlap, fade in/out based on zoom tier (visible at Close and Default; hidden at Regional and Galactic to avoid clutter).

**Cost:** ~1 week. Icon rendering system + data integration with other Tier 2 systems.

**Benefit:** cross-system integration becomes visible. Players see their salvage/mining/narrative progress on the map.

### 4.7 System approach animation

When the player arrives at a notable system, brief (~1.5s) approach moment before dropping into trading view:

- **Standard arrival** (any visited system): existing behavior — jump arrival resolves, trading view loads. No approach animation.
- **Home system**: 1.5s approach — camera pushes toward the system; ambient warm-glow overlay; cockpit HUD resolves with "welcome home" subtle cue
- **Hostile system** (faction hostile, high danger, active combat event): 1.5s approach — camera pushes with colder tint; threat-red vignette edge; HUD resolves with slight red pulse
- **Story-critical system** (first visit tied to campaign): 1.5s+ approach with scripted camera and atmospheric overlay (per campaign designer's spec for specific system)
- **Landmark-present system**: brief 1.0s approach with landmark icon highlighted

All approach animations **skippable** (press any key).

**Cost:** ~1.5 weeks. Scripted approach sequences; landmark-type routing; per-system spec data.

### 4.8 Info panel polish

Current info panel is dense but readable. Minor polish:

- **Faction banner** at top (currently text-only); add faction insignia icon
- **Danger tier visual bar** (currently just color dot); expand to a bar with tier text
- **Remote prices** (if skill-unlocked): replace text list with mini-sparkline visualization of commodity price trends over recent days
- **Event details**: rich card rather than text block; event-type icon, affected commodity, days-remaining bar, quick-action button if player can engage

**Cost:** ~1 week. UI refinement pass.

### 4.9 Multi-hop route display

Current route: single leg (current → destination). When a player plans a multi-system trade or quest route, show full route:

- All intermediate systems highlighted
- Route lines connect in sequence
- Cumulative distance/fuel at each leg + total
- Estimated travel time sum
- Per-leg risk color coding

**Cost:** ~1 week. Route-plan data model + multi-leg rendering.

---

## 5. Gameplay changes forced by rendering

### 5.1 Jump sequence skip-setting

§4.1 introduces a 3.5s cinematic on first-per-session jumps. Player must be able to configure ("Jump Cinematic: Full / Fast / Minimal / Instant"). This is a **settings addition**, minor gameplay surface, no balance implication.

### 5.2 Zoom tier gates for information density

Certain info (faction territory overlay, nebula names, landmark labels) is gated by zoom tier. Not a gameplay change — a UX affordance. Players who want full detail zoom to Galactic view.

### 5.3 Home system designation

§4.7 introduces "home system" as a designated concept. Player chooses one system to mark as home (default: starting system; re-designatable via settings). Cosmetic only; gameplay-neutral. Used by approach animation + potentially by Tier 2 Station Hub doc's "home station" behavior.

### 5.4 No other gameplay changes

Travel mechanics, encounter rates, fuel economy, intel skill gating, remote-price surfacing — unchanged.

---

## 6. Dependencies

### 6.1 On other overhaul docs

- **`20_aesthetic_bible.md` §2** — palette roles for jump-sequence colors, dominion overlay tints, landmark icons
- **`20_aesthetic_bible.md` §4.8** — faction color overlay values
- **`20_aesthetic_bible.md` §8** — scene mood overlays (home/hostile approach draws from here)
- **`30_overhaul_space_combat.md` §4.4** — camera system (zoom/pan implementation borrows architecture)
- **`30_overhaul_space_combat.md` §4.8** — arena entry animation (approach animation shares patterns)
- **`32_overhaul_mining.md` §7.2** — Legendary Seams landmark integration
- **`36_overhaul_salvage.md` §7.1** — Named Wrecks landmark integration
- **`10_programmatic_generation_framework.md` §3** — primitives for nebula backdrop, Voronoi for dominion

### 6.2 On production systems

- `spacegame/views/galaxy_map_view.py` — heavily extended
- `spacegame/engine/backgrounds.py` — extended for responsive parallax + nebula regions + arm structure
- `spacegame/models/politics.py` — faction territory data extension
- `data/galaxy/systems.json` — nebula/region metadata additions
- `spacegame/models/player.py` — home system designation
- Cockpit HUD → galaxy map entry transitions

### 6.3 On Tier 3 parallel docs

- **`42_ui_chrome_components.md` (Tier 3, not written)** — info panel card patterns inherit from here when it lands
- **`40_audio_synthesis_framework.md` (Tier 3, not written)** — jump sequence audio cues will consume standards from here

---

## 7. Phasing

Galaxy map overhaul is moderate scope. 5 phases, significant parallel opportunities with combat and builder work.

### Phase G1 — Zoom and pan controls (~1.5 weeks)

- Camera zoom tier state machine
- Pan controls (mouse-drag + keyboard)
- Re-center + jump-to-mission shortcuts
- Starfield density per zoom tier

**Why first:** enables everything else. Without zoom tiers, dominion overlay and nebula detail have no layer to render in.

### Phase G2 — Jump sequence cinematic (~2 weeks)

- Scripted multi-phase jump sequence (§4.1)
- Starfield streak effect
- Jump speed configuration setting

**Why early:** highest "feels different" payoff. Ends Gap 1 and Gap 5 in one phase.

### Phase G3 — Responsive starfield + nebula backdrop (~1.5 weeks)

- Parallax-camera integration
- 5 named nebula regions rendered
- Arm structure at galactic zoom
- Trade-lane visualization at regional zoom

**Parallelizable** with G2.

### Phase G4 — Faction dominion overlay + living galaxy (~2-3 weeks)

- Voronoi-based territory decomposition
- Faction tint rendering with contested-system blending
- Event-resolution change tracking
- Territory-shift morph animations

**Why later:** depends on G1 (zoom tiers) and G3 (backdrop) being in place.

### Phase G5 — Landmark integration + approach animations + info panel polish (~2 weeks)

- Cross-system landmark icons (§4.6)
- System approach animations (§4.7)
- Info panel polish (§4.8)
- Multi-hop route display (§4.9)

**Why last:** depends on other Tier 2 docs having landed landmark data (salvage Named Wrecks, mining Legendary Seams). Can ship the other improvements before landmark phase.

### Total estimate: ~9-11 weeks

---

## 8. Success criteria

Galaxy map overhaul is done when:

1. **Jumps feel like jumps.** Players pause to watch the jump sequence on first sessions; abbreviated versions land for routine travel.
2. **Zoom reveals scale.** Pulling back to Galactic zoom produces a "the Expanse is big" moment.
3. **Faction geography is legible.** A glance at the Regional-zoom map tells the player where each faction dominates.
4. **The galaxy breathes.** Returning to the map after time away shows visible change.
5. **Landmarks unify play.** Salvage/mining progress is visible at the galaxy level; the player sees their story on the map.
6. **Navigation is fast when needed.** Instant-jump config option keeps travel speed for players who don't want the cinematic every time.
7. **Information density preserved.** The rich per-system visual language + intel-gating discipline is maintained; no regression on information clarity.
8. **Performance.** Galaxy map holds 60 FPS at all zoom tiers with dominion overlay + backdrop + all landmark icons active. Target: 8ms per galaxy-map-render frame.

---

## 9. Open questions

1. **Nebula region count.** 5 v1 feels right for 11 systems. Scale up when galaxy expands (more systems → more regions); defer calibration.
2. **Jump cinematic timing — 3.5s too long?** Playtest. If players find full jump cinematic tedious after one session, move "Fast" to default.
3. **Dominion overlay visual discipline.** Voronoi can produce ugly cells. May need hand-tuned region polygons for v1 with 11 systems; transition to Voronoi if galaxy expands significantly.
4. **Approach animation per system — scripted vs procedural?** Scripted works for home/hostile categories; story-critical systems need per-designer specs. Procedural may be possible for landmark-present systems. Flag for playtest.
5. **Multi-hop route as permanent plan or per-session plan?** v1 proposal: per-session only (player plans, travels, plan clears on next session). Alternate: persistent plan with "auto-fly to next waypoint" behavior. Defer to playtest.

---

## 10. Out of scope

- **Galaxy-scale gameplay (4X, empire-building)** — not in scope
- **Real-time galaxy simulation** — events tick per game-day; no more granularity
- **Multiplayer / shared-galaxy state** — single-player only
- **Per-planet zoom (orbital view of individual planets)** — deferred; galaxy map resolves to system-portrait scale
- **Procedural galaxy generation** — galaxy structure is authored
- **New galactic events** — balance / narrative territory

---

*Next Tier 2 doc: `34_overhaul_trading.md` (Cyberpunk 2077 market brutalism — data density, ticker crawls, sparklines). Trading is Aurelia's second-most-frequently-visited system after the galaxy map; the pair form the player's primary economic-layer experience.*
