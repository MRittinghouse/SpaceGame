# Station Hub Visual Overhaul

> **Status:** DESIGN — Tier 2 doc, visual-overhaul scope per master plan §5. The station hub is Aurelia's **connective tissue** — the hub the player returns to between every outbound activity. Trading, mining, salvage, refining, shipyard, cantina all live through it. A strong station hub makes every system feel like a *place you visit*, not a menu you click through.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `31_overhaul_ship_builder.md` (hangar environment system). Coordinates with `requirements/cultural_guide.md` for faction worldbuilding and `requirements/dialogue_writing_guide.md` for station chatter voice.

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

Factual snapshot per survey of `station_hub_view.py` and `engine/station_layouts.py`.

### 1.1 What's already strong

- **Five faction-specific layouts** with legitimate visual differentiation:
  - **Guild Deck** (Commerce Guild) — vertical hierarchy, blue accent, holographic motes, *"Commerce. Order. Prosperity."*
  - **Union Blueprint** (Miners Union) — grid-based, rust/amber, industrial sparks, blueprint background, *"Built by hands, not contracts."*
  - **Collective Radial** (Science Collective) — circular radial, cyan, concentric geometry, pulsing central node, *"Understanding. Innovation. Discovery."*
  - **Frontier Freeform** (Frontier Alliance) — scattered hand-drawn, green, organic particles, *"Freedom. Self-reliance. Survival."*
  - **Reach Minimal** (Crimson Reach) — sparse dark, deep crimson, minimal particles, oppressive, *"Power. Cunning. Survival of the fittest."*
  
  **This is the foundation we build on, not replace.** Per-faction identity is already real.

- **Entrance animation** — 0.5s fade-in with faction tagline fading at 0.8-1.0 timer. Arrival has character.
- **Station chatter** — 148 lines of reputation-filtered, event-filtered ambient flavor. 10s rotation with fade. Atmosphere delivered.
- **Header card** — system name, description, atmosphere flavor, faction + danger indicator. At-a-glance clear.
- **Location cards** — 8-9 activity types (TRADE, REPAIR, SOCIAL, MINING, SALVAGE, REFINE, SHIPS, INVEST, EXPLORE) with distinct accent colors, hover states, tooltips.
- **Ambient particle systems** — each layout has its own particles (blue motes, rust sparks, leaves, etc.) reinforcing identity.
- **Story-gated NPC buttons** in cantina zone — first-visit hire, re-recruitment of dismissed crew, mission contracts, dialogue triggers.

### 1.2 What's weak — the five gaps

**Gap 1: No "you are somewhere" backdrop.**

The station hub renders faction-themed UI elements over a dim starfield. There is no **painted panorama** — no view of the docked bay, no glimpse of station architecture, no sense of being *inside* a station rather than *looking at* a menu. The master plan's "painted panorama" target isn't present.

**Gap 2: Service availability is silent.**

When mining / refining / cantina isn't available at a station, the card is simply absent. No "UNAVAILABLE" badge, no "LOCKED" state, no flavor explanation. Players don't know *why* Crimson Reach doesn't have a cantina or why a backwater system lacks refining. Service availability is discovered by absence, which is anti-communication.

**Gap 3: No ambient NPC presence in the hub itself.**

NPCs exist as dialogue triggers (in cantina), hire buttons, re-recruitment offers. No NPCs are *visible in the hub*. A cantina with no visible patrons, a commerce district with no visible crowd, a mining hall with no visible workers — each station reads as deserted. Reference games (Cyberpunk districts, Starfield stations) all show background life.

**Gap 4: News ticker absent from station hub.**

`news_ticker` model exists and is integrated into trading view (per 34 overhaul). Station hub — the next most-visited surface — doesn't display it. News headlines are exactly the kind of atmospheric detail that makes a station feel like a *place where people are*.

**Gap 5: No first-visit vs. recurring-visit differentiation.**

Arriving at Nexus Prime for the first time and arriving for the 40th time look identical. The entrance animation plays the same way; no "welcome, new docker" flavor on first; no "returning stranger" or "regular" texture on recurring. Small investment, meaningful atmospheric payoff.

### 1.3 Secondary gaps

- **Docked-ship framing absent.** The player's ship is physically at the station but not visible in the hub. A corner glimpse of the ship docked (through a window, at a gantry) would anchor presence.
- **Station descriptor info thin.** Header shows name + description + atmosphere line + faction/danger. Missing: population tier, facility roster, last-visit flavor ("you were here 8 days ago"), station archetype (spaceport vs research station vs mining platform).
- **Taglines fade and disappear.** Good moment at 0.8-1.0 timer; but players can't re-trigger or re-read them. A persistent but dim faction tagline in the header would reinforce identity throughout the session.
- **No neon-on-darkness contextual treatment.** Per AB §8.2, neon is reserved as a scene overlay for specific contexts — station hub could trigger this for cyberpunk-coded district stations. Currently no station leans neon.

### 1.4 What this doc addresses

- Gap 1 (backdrop) via painted-panorama backdrops per faction (§4.1)
- Gap 2 (service opacity) via availability badges + lock states (§4.2)
- Gap 3 (NPC presence) via ambient NPC sprites in layouts (§4.3)
- Gap 4 (news absent) via station-hub ticker integration (§4.4)
- Gap 5 (first-visit) via arrival texture + memory-based flavor (§4.5)
- Secondary gaps via docked-ship corner glimpse (§4.6), expanded descriptor (§4.7), persistent faction heraldry (§4.8), neon-district overlay (§4.9)

---

## 2. Target feel — influences and reference moments

### 2.1 The three-influence synthesis

Station hub is **painted-panorama atmospheric-hub with faction-specific district character**. Three references:

**Cyberpunk 2077 districts — each place has a specific character**

- Watson is brutalist-industrial. Westbrook is neon-commercial. Heywood is working-residential. Pacifica is ruin-haunted. You *know* which district you're in within seconds of arrival.
- Ambient NPCs populate each district — they're not interactive but they're *present*. The city is inhabited.
- Backdrops carry the architectural signature. Watson's overpasses, Westbrook's billboards, Heywood's markets are *visible* behind the menus.
- Sound and visual design reinforce district feel in concert (sound is Tier 3; visual is our lane).

**Starfield stations — the docked-ship moment**

- Upon landing, a short cinematic: exterior view of your ship approaching the station, docking sequence, interior resolution. The transition establishes *you are here*.
- Stations have multi-level interiors with visible NPCs walking, talking, interacting.
- Facility roster is visible — you can see at a glance what's at this station vs. what's not.
- Each station has architectural identity (UC Vigilance military-grey, Neon cyberpunk, Akila frontier-wood).

**Deus Ex: Human Revolution — hub districts with worldbuilding depth**

- Each hub city has specific flavor: Detroit's industrial decay, Hengsha's dense vertical sprawl, Montreal's corporate-sterile. You feel the faction alignment from the architecture.
- Ambient NPCs have posture and staging — some cluster around vendors, some lean against walls, some hurry through. Crowd choreography without interactivity.
- Information density is respected. Info panels with depth, readable without interrupting flow.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Cyberpunk 2077, "first walk through Jig-Jig Street"** (2020). Within five seconds of entering, the player knows this is a red-light district. Signage, NPC behavior, tint, ambient motion all concur. Aurelia equivalent: entering a Reach-controlled station (e.g., crimson_reach) establishes *threat* and *underworld* in the backdrop + NPC staging + tint, without a single line of text.

2. **Starfield, "docking at New Atlantis"** (2023). The establishing beat — your ship approaches, exterior reveals, you exit into a hub. Clear "you are now here." Aurelia equivalent: docking cinematic (§4.5) — brief (1.5-2.0s) arrival beat when entering a station, with the ship visible as it comes to rest against the station frame.

3. **Cyberpunk 2077, "Afterlife bar ambient patrons"** (2020). The bar is full of NPCs. None are critical quest givers; they're just there, drinking, talking in pairs, hunched over terminals. The bar feels *inhabited*. Aurelia equivalent: ambient NPCs in cantina, commerce market, industrial floor — sprite figures, staged, non-interactive, *present*.

4. **Deus Ex: Human Revolution, "Detroit's police-corporate overlook"** (2011). The backdrop shows city architecture that matches the hub's thematic register — brutalist civic architecture carrying faction identity. Aurelia equivalent: painted-panorama backdrops per faction (§4.1), rendered as atmospheric layer visible behind the faction-specific layout.

5. **Starfield, "the mission board at The Lodge"** (2023). A facility is visible (the mission board, the lounge, the training room). You see what's available as visual furniture, not menu text. Aurelia equivalent: service-availability badges (§4.2) + facility roster (§4.7) — the station *shows* what's here and what's not.

### 2.3 What this is not

- **Not 3D exploration.** Aurelia's station hub remains a 2D interaction surface. "Painted panorama" means atmospheric 2D backdrops, not navigable 3D spaces.
- **Not a crowd-simulation.** Ambient NPCs are handful of sprites, staged deterministically. No pathfinding, no interaction. Presence is the goal, not simulation.
- **Not full Cyberpunk neon saturation.** Per AB §1.2, Aurelia rejects cyberpunk-as-default. Neon is a *contextual* overlay (§4.9) for specific stations, not a base aesthetic. Most stations stay warm-industrial per AB §1.1.
- **Not a full redesign of faction layouts.** The 5 existing layouts (Guild Deck, Union Blueprint, Collective Radial, Frontier Freeform, Reach Minimal) are preserved. We add atmospheric depth around them, not replace them.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Visual signal |
|---|---|---|
| Docking approach | Arrival | Docking cinematic: ship approaches station exterior, comes to rest, HUD transitions to hub |
| Hub resolves | Sense of place | Painted panorama backdrop fades in behind faction layout; ambient NPCs become visible; particles start |
| First-visit arrival | "New to this place" | Flavor chatter line specific to first-visit; brief atmosphere narration; unlock-sound cue for available services |
| Recurring visit | "A familiar place" | Chatter references passage of time ("been a while"); ambient NPCs may have rotated; last-visit info in descriptor |
| Notice unavailable service | Clear explanation | Service card shows UNAVAILABLE badge with reason (faction lock, station archetype, reputation) |
| Enter cantina | Inhabited space | Ambient NPCs visible (4-8 sprites staged); chatter continues; quest-giver NPCs highlighted among crowd |
| News scrolls across ticker | Ambient awareness | Headlines crawl at top of hub; relevant ones (local events, faction news) can be tapped for expansion |
| Descriptor expanded | Station context | Population, facility roster, last-visit flavor populate; station identity deepens |
| Select activity | Deliberate transition | Card highlight + brief particle burst on activation; scene transitions to activity view |
| Undock | Departure | UNDOCK button; brief reverse-docking cinematic; return to galaxy map |

### 3.2 What each emotion serves gameplay

- **Arrival / sense of place** → the station is a *place*, not a menu
- **New to this place** → first-visits feel novel; hooks the worldbuilding immediately
- **A familiar place** → recurring visits have texture; the player's history is acknowledged
- **Clear explanation** (unavailable) → no silent refusals; player learns the economy's shape through visible gates
- **Inhabited space** → the cantina / market / industrial floor has people in it; Aurelia is populated
- **Ambient awareness** → news crawls at the edge; the galaxy continues around the player
- **Station context** → descriptor deepens worldbuilding without requiring quest logs
- **Deliberate transition** → activity selection is a committed action, not a casual click
- **Departure** → undocking carries the same weight as arrival

### 3.3 The non-goal: station-as-destination

The station hub is a *hub*, not an end in itself. Players arrive, select an activity, move to that activity, return. Making the hub *too* rich risks turning it into a place players dwell for its own sake, which would slow the gameplay loop. Discipline: atmosphere serves orientation and transition, never competes for primary attention. Ambient NPCs are *present*, not *interactive*. Backdrops are *visible*, not *explorable*.

---

## 4. Rendering changes

### 4.1 Painted-panorama backdrops per faction layout

Each of the 5 faction layouts gains a **painted panorama** — a wide, atmospheric 2D backdrop rendered behind the layout chrome. Not a static image but a multi-layer composition with subtle parallax and ambient animation.

**Backdrop composition per faction:**

| Layout | Backdrop themes | Parallax layers |
|---|---|---|
| **Guild Deck** | Commerce arcade overlook — distant gantries, transit tubes, hovering freight, cool-cyan civic lighting | Far: gantries + hologram billboards; mid: traffic streams; near: dock architecture with guild-insignia |
| **Union Blueprint** | Industrial heart — smelters in middle distance, forge glow, cranes moving cargo, warm industrial lighting | Far: smelters/chimneys with plasma-core glow; mid: cranes + cargo shuttles; near: riveted structural beams |
| **Collective Radial** | Research station arboretum — dome structures, cool laboratory glow, visible specimen tanks, clean sterile environment | Far: dome lattice with cryo_fractal highlights; mid: laboratory signage + tanks; near: smooth architectural curves |
| **Frontier Freeform** | Frontier boomtown — ramshackle buildings, visible patch-welded architecture, warm-worn lighting, crude signage | Far: horizon with varied architecture; mid: banners, chains; near: mismatched dock plating |
| **Reach Minimal** | Underlit crimson bay — dim industrial, visible scrap, flicker lighting, sparse threatening architecture | Far: dim silhouettes with red emergency lighting; mid: broken gantries; near: crimson-stained metal |

**Rendering:**

- Three parallax layers per backdrop (far / mid / near)
- Each layer procedurally generated using framework §3 primitives (rectangles for architecture, lines for structural elements, polygons for silhouettes)
- Palette-snapped per AB §2; faction band colors dominant
- Subtle ambient animation: distant lights flicker, occasional cargo shuttle crosses the mid-layer, steam/smoke plumes rise in industrial scenes
- Dim tint (40-60% opacity) so foreground layout reads clearly on top

Backdrops render behind the dim starfield overlay, not instead of it. Stars remain visible through gaps / sky zones.

**Cost:** ~3 weeks. Five backdrops × three layers each = 15 procedural scene compositions. Significant asset work but all procedural (no hand-authored pixel art), so scales with framework §3 discipline.

**Benefit:** ends Gap 1. Every station feels like a *place*.

### 4.2 Service availability badges

Each location card's state is visually explicit:

| State | Treatment |
|---|---|
| **Available** | Current behavior preserved — normal card rendering, hover brightens, click activates |
| **Unavailable (station archetype)** | Card rendered at 40% opacity with "NOT AT THIS STATION" label in `hud_muted`. Hover tooltip: "This station doesn't offer [service]. Look for [station type]." |
| **Locked (reputation)** | Card shown with `hud_warning` border stripe + "REQUIRES [faction] REP" badge. Hover shows exact threshold and current rep. |
| **Locked (quest)** | Card shown with `hud_cyan` border stripe + "QUEST REQUIRED" badge. Hover shows hint without spoiling (e.g., "Unlocks after completing the Cardinal mission arc"). |
| **Time-locked (event)** | Card shown with `plasma_core` border + "TEMPORARY CLOSURE" badge. Hover shows event info + expected reopen. |

All locked cards remain visible but non-clickable — players see the *full suite* of possible services and learn which ones need what.

**Cost:** ~1 week. Card state rendering + availability-reason lookup + hover tooltip extension.

**Benefit:** ends Gap 2. Service economy becomes visible; absence is explained.

### 4.3 Ambient NPCs in layouts

Each faction layout gets **ambient NPC sprites** staged deterministically. These are non-interactive background life:

| Layout | NPC sprite count | Staging |
|---|---|---|
| Guild Deck | 6-8 | Clustered around upper deck market; one at a transit-tube; two in service deck |
| Union Blueprint | 5-7 | Clustered around industrial deck; one inspecting blueprint schematic panels; worker near service deck |
| Collective Radial | 4-6 | Walking slowly around central pulsing node; one at each radial lab; sparse but purposeful |
| Frontier Freeform | 7-10 | Scattered and un-choreographed; small groups in conversation; one traveler-with-pack |
| Reach Minimal | 3-5 | Sparse; each isolated; some in shadow; one leaning against a wall watching |

**Sprite design:**
- 24-32px character sprites, hand-authored or procedural (follow framework §11.5 portrait boundary — these are small enough that procedural works)
- 3-5 poses per layout (standing, leaning, walking, talking-in-pair, working)
- Simple idle animation (~0.6s breathing cycle, occasional weight-shift)
- Some pairs in conversation — two sprites facing each other, occasional gesture
- Color-coded per faction (faction band colors in their clothing palette)

NPC positions are deterministic per-station (seed = station_id + day), so players see the same arrangement on recurring visits unless time advances significantly (sprites "rotate" on return after long absence).

**Cost:** ~3-4 weeks. Sprite authoring / procedural generation + staging system + per-layout choreography.

**Benefit:** ends Gap 3. Stations become inhabited.

### 4.4 News ticker in station hub

Ticker integration — same pattern as trading view (§34 doc §4.2):

- Single-line scrolling text at top of station hub, below header card
- Scroll direction: right-to-left, ~40px/s
- Headlines colored by category (market events `hud_warning`, political `hud_cyan`, ambient `hud_text_dim`)
- Click a headline → inline expansion with full text + "dismiss" action
- Pauses on hover
- Dismissible via station hub settings toggle

Station-hub-specific ticker behavior: headlines about the **current system** or its **faction** surface with a brighter color stripe, drawing the eye. The ticker feels more local when you're at a specific place.

**Cost:** ~4 days. Reuses ticker rendering from trading view; adds local-filter highlighting.

### 4.5 First-visit vs. recurring-visit treatment

**First visit** (no `visited_stations[system_id]` flag):
- Brief additional atmosphere narration at top of chatter card (one line, specific to first-visit)
- "Welcome to [Station Name]" toast that fades after 2 seconds
- Service availability badges linger at full opacity longer (players notice the locked states)
- Faction tagline holds slightly longer on entrance (reinforces identity on first encounter)

**Recurring visit** (visited before):
- Chatter may reference time passage ("Been a while," "Haven't seen you since the Embargo")
- Last-visit descriptor: "Last visit: [X] days ago. [Brief summary: sold X cargo, met Y]"
- If significant events have happened locally since last visit (faction rep change, event resolved, crew left), brief flash of that info
- Ambient NPCs may show slight "rotation" (different poses, slight position variation) on each return after significant time gaps

**First-visit-after-event** (player visited before, but a major event has changed the station):
- Specific flavor noting the change ("The district feels different — tension in the air")
- Affected services may be marked with "CHANGED SINCE LAST VISIT" indicator

Station memory — the state the game needs for this — piggybacks on existing save-state tracking (visit counts, last-visit day, events-since-visit). No new data model; just new rendering logic.

**Cost:** ~1.5 weeks. Visit-state tracking extension + rendering integration + additional chatter content (~30 lines authored per faction × 5 = ~150 lines).

### 4.6 Docked-ship corner glimpse

Bottom corner of hub view gains a small (~120×80px) **docked-ship panel** showing the player's ship as it's visible from the station's perspective:

- Rendered through the unified ship composite pipeline (combat §4.1 / builder §4.2)
- Three-quarter angle matching the builder preview angle (familiar view)
- Dim ambient lighting matching the hangar environment (per AB §1)
- Optional corner overlay for ship-specific state (e.g., "NEEDS REPAIR" if hull damage exists, "FUEL 20%" if low fuel)

The corner glimpse is **persistent** — the player always sees their ship is *there*, physically, while they're at the hub. Reinforces "you are docked."

**Cost:** ~1 week. Reuses builder preview pipeline.

### 4.7 Expanded station descriptor

Current header: name + description + atmosphere + faction/danger. Extend to:

- **Archetype tag** — "Spaceport," "Research Station," "Mining Platform," "Frontier Outpost," "Crimson Bastion" (one per station, hand-authored)
- **Population tier** — abstract scale (Busy / Active / Sparse / Isolated) rather than specific numbers
- **Facility roster** — small icon row showing what services the station has (active + grayed-out for unavailable); visible in header, matches §4.2 card states
- **Last-visit summary** (for recurring visits) — "Last visit: [day]; net transactions: ±[credits]; events since: [count]"
- **Atmosphere flavor** (existing) preserved
- **Reputation with dominant faction** (if faction-owned) — discrete tier visible (Hostile / Unfriendly / Neutral / Friendly / Allied)

Descriptor expands into a **collapsible panel** — by default shows core info; click to expand for full detail. Respects the non-goal (§3.3) of making the hub a dwelling place.

**Cost:** ~1 week. Extended descriptor UI + data integration.

### 4.8 Persistent faction heraldry

Current faction tagline fades in at entrance and disappears. Upgrade to **persistent but dim** treatment:

- Faction insignia (hand-authored pixel art per framework §11.5 — 5 required, one per faction) visible in the corner of the header at 40% opacity
- Faction tagline rendered beneath insignia at 30% opacity (visible but subdued — doesn't compete with active content)
- On hover over the insignia, tagline and faction-info card can expand
- Entrance animation still does the big reveal (§1.1 existing); post-entrance, heraldry persists subtly

**Cost:** ~1 week. Insignia design (5 hand-authored pixel artworks) + header UI integration.

### 4.9 Neon-district contextual overlay

Per AB §8.2, neon is reserved as a scene overlay for specific contexts. Station hub gets a **neon-district variant** for specific stations that lean cyberpunk-coded:

- Only applies to specifically-flagged stations (v1: 1-2 candidate stations with cultural-guide justification — e.g., a Commerce Guild neon-district hub, or a black-market crimson bastion)
- Overlay swaps emissive palette: `plasma_core` → hot-pink neon variant; `hud_cyan` → electric-cyan; ambient particles gain glow trails
- Backdrop (§4.1) uses a neon-variant rendering (bright signage, holographic ads, rain/mist ambient)
- NPCs (§4.3) unchanged in silhouette but pick up neon rim-lighting
- Faction tagline styling shifts to neon-glyph typography

This is the cyberpunk-districts reference landing deliberately in specific places, not sprayed across the whole hub system. Prevents neon-drift.

**Cost:** ~1.5 weeks. Overlay rendering system + 1-2 per-station variant data.

### 4.10 Docking / undocking cinematics

Brief transition beats for arrival and departure:

**Arrival (docking):**
- 0.0–0.8s: galaxy map fades; ship approaches station exterior (silhouette rendered procedurally)
- 0.8–1.5s: ship docks; view rotates to interior perspective; station-hub chrome fades in
- 1.5–2.0s: hub layout resolves; entrance animation begins

**Departure (undocking):**
- 0.0–0.5s: UNDOCK click; hub chrome fades
- 0.5–1.2s: view rotates back to exterior; ship disengages
- 1.2–1.5s: galaxy map resolves

All skippable (any key press abbreviates to 0.3s fade).

**Cost:** ~2 weeks. Procedural station-exterior rendering + scripted cinematic beats.

---

## 5. Gameplay changes forced by rendering

### 5.1 Service availability badges require availability reason data

§4.2 requires each service-station pairing to know *why* the service is unavailable (station type, rep requirement, quest gate, event lockout). Most of this data exists; some may need exposure for the UI. Not a gameplay change — a data-surfacing change.

### 5.2 Visit-state tracking extension

§4.5 needs to track "days since last visit" and "events since last visit" per station. Data infrastructure exists; surfacing to UI may require small extensions to `player.visited_stations` save state.

### 5.3 No other gameplay changes

Activity gating, faction rep, quest hooks, crew hiring, contract flow — all preserved.

---

## 6. Dependencies

### 6.1 On other overhaul docs

- **`20_aesthetic_bible.md` §2** — palette for backdrops, NPC sprites, ticker, heraldry
- **`20_aesthetic_bible.md` §4.8** — faction color overlay values for insignia + layout chrome
- **`20_aesthetic_bible.md` §8.2** — scene mood overlays (neon-district variant)
- **`30_overhaul_space_combat.md` §4.1** — unified ship composite (docked-ship glimpse)
- **`31_overhaul_ship_builder.md` §4.1** — hangar environment primitives (backdrops borrow similar architecture approach)
- **`33_overhaul_galaxy_map.md` §4.1** — jump sequence coordinates with docking/undocking cinematic transitions
- **`34_overhaul_trading.md` §4.2** — news ticker shared implementation

### 6.2 On production systems

- `spacegame/views/station_hub_view.py` — extended
- `spacegame/engine/station_layouts.py` — extended for NPC staging
- `spacegame/models/player.py` — visited_stations metadata extension (last_visit_day, transactions_summary)
- `data/galaxy/systems.json` — station archetype, facility roster metadata
- Faction insignia asset pipeline (5 hand-authored pieces)

### 6.3 On Tier 3 parallel docs

- **`42_ui_chrome_components.md` (Tier 3, not written)** — header card patterns, service badge styling, descriptor panel all consume standards from here when it lands

---

## 7. Phasing

Station hub overhaul is moderate scope. 6 phases, parallelizable with galaxy map and trading work.

### Phase H1 — Service availability badges + expanded descriptor (~1.5 weeks)

- Availability state system (§4.2)
- Expanded station descriptor (§4.7)
- Persistent faction heraldry (§4.8)

**Why first:** highest clarity-per-unit-effort. Fixes silent-absence gap immediately.

### Phase H2 — News ticker integration + first/recurring-visit treatment (~1.5 weeks)

- Ticker adaptation from trading view (§4.4)
- Visit-state tracking and rendering (§4.5)
- Additional chatter content (~150 new lines)

**Parallelizable** with H1.

### Phase H3 — Painted-panorama backdrops (~3 weeks)

- Five faction backdrops (§4.1)
- Three-layer parallax rendering
- Ambient animations (lights, cargo traffic, steam)

**Why middle:** significant procedural art work; doesn't block other phases.

### Phase H4 — Ambient NPC staging (~3-4 weeks)

- NPC sprite authoring or procedural generation
- Per-layout staging
- Conversation-pair animations
- Visit-state rotation

**Why later:** heaviest authoring phase; can parallelize with H3.

### Phase H5 — Docked-ship glimpse + docking cinematic (~2 weeks)

- Docked-ship corner panel (§4.6)
- Docking/undocking cinematics (§4.10)

**Why later:** depends on unified ship pipeline (combat §4.1) landing first.

### Phase H6 — Neon-district overlay (~1.5 weeks, optional polish)

- Overlay rendering system (§4.9)
- 1-2 flagged station variants

**Why last:** polish tier, specific-station scope.

### Total estimate: ~12-15 weeks

Parallelizable significantly. Solo+agent realistic: ~10-14 weeks including coordination.

---

## 8. Success criteria

Station hub overhaul is done when:

1. **Every station feels like a place.** The painted panorama + ambient NPCs + faction layout combine into "you are somewhere specific."
2. **Faction identity reinforced.** A player entering a Reach station feels the threat before reading any text; a Collective station feels clinical.
3. **Service availability is legible.** Players know immediately what this station does and doesn't offer, and why.
4. **Stations feel inhabited.** Ambient NPCs populate without requiring interaction. The cantina has patrons.
5. **News ticker brings the galaxy in.** Station hub feels connected to the Expanse, not isolated.
6. **First-visit lands.** Arriving somewhere new feels distinctive from recurring visits.
7. **Docking carries weight.** Arrival and departure are small cinematic beats, not instantaneous transitions.
8. **Existing strong work preserved.** The 5 faction-specific layouts remain intact and visually coherent; the overhaul wraps them in atmosphere rather than replacing them.
9. **Palette compliance holds** across backdrops, NPC sprites, and ticker integration.
10. **Performance.** Station hub holds 60 FPS with backdrop + up to 10 ambient NPCs + ticker + all layout particles active.

---

## 9. Open questions

1. **NPC sprite authoring — procedural or hand-authored?** Framework §11.5 puts portraits in hand-authored pixel art. Ambient NPCs are smaller (24-32px); procedural may be feasible. Decision affects sprite-count budget and Phase H4 scope. Lean: **procedural with hand-authored details for named NPCs only**.
2. **Backdrop parallax on pan.** Station hub currently doesn't pan. If galaxy map's zoom/pan introduces parallax-responsive backdrops elsewhere, should the hub adopt a subtle parallax on mouse-position? v1 proposal: no — the hub is a focused view. Reassess if it feels static.
3. **Neon-district station candidates.** v1 proposes 1-2 stations lean cyberpunk-coded. Which specific stations? Cultural guide implies no established neon-district stations exist yet. May require worldbuilding addition. Defer to H6.
4. **Docking cinematic for unvisited systems.** First-time dockings could get extended cinematic (~3s vs 1.5s recurring). Adds specificity at low cost. Flag for playtest.
5. **Crowd density calibration.** NPC counts per layout (§4.3 table) are provisional. Playtest may suggest denser (more Cyberpunk-feel) or sparser (more Starfield-clean).
6. **Backdrop idle animation intensity.** Mid-layer cargo shuttles crossing, near-layer steam plumes — how distracting? Preserve attention on primary UI. v1 proposal: very subtle (1-2 ambient events per 30 seconds).

---

## 10. Out of scope

- **Per-station dialogue authoring** — content, not rendering; handled via existing dialogue system
- **Multi-level interactive station layouts** — not 3D-explorable; 2D hub remains
- **New factions** — five existing factions + layouts; not extended here
- **Ground exploration integration** — ground-exploration doc covers that system separately
- **Station-specific economy mechanics** — handled by trading / activity systems
- **Per-NPC AI behaviors** — ambient only; no pathfinding, no dynamic interactions

---

*Next Tier 2 doc: `38_overhaul_ground_exploration.md`. The ground-exploration influence anchor is TBD per master plan §5 ("Fallout 1/2 isometric? Invisible Inc?") — needs decision before doc can be written. User call.*
