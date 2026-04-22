# Ground Exploration Overhaul

> **Status:** DESIGN — Tier 2 doc, **middle-scope** overhaul. Sits between the pure-visual Tier 2 docs (combat/builder/galaxy/trading/hub) and the full mini-game identity docs (mining/salvage/refining). Keeps the mechanical foundation (tactical grid + Dice & Grit combat + fog-of-war) intact; adds structural gameplay (party formation, expedition resolve, afflictions, named encounters) and narrative depth (in-exploration dialogue, expedition voice) on top.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `30_overhaul_space_combat.md` (camera + unified pipeline), `35_overhaul_station_hub.md` (station-hub recovery phase). Coordinates with `requirements/cultural_guide.md` for worldbuilding voice and `requirements/dialogue_writing_guide.md` for encounter dialogue.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Structural additions — party, resolve, afflictions
5. Narrative additions — encounters, expedition voice, consequence
6. Rendering changes — visual overhaul
7. Gameplay changes forced by structural and rendering work
8. Dependencies
9. Phasing
10. Success criteria
11. Open questions
12. Out of scope

---

## 1. Current state — honest assessment

Factual snapshot per survey of `ground_briefing_view.py`, `ground_exploration_view.py`, `ground_result_view.py`, `models/ground.py`, `models/ground_combat.py`, `models/ground_crew.py`, `models/ground_equipment.py`, and 5 campaign map JSONs.

### 1.1 What's already strong

- **Turn-based cardinal-grid tactical movement.** Cardinal-only movement (1 tile/turn), Manhattan-adjacent interaction, deterministic turn order. Fallout 1/2's tactical bones, present and working.
- **Dice & Grit combat system.** 1d6 + modifier vs 1d6 + modifier exchanges. Real tactical depth: outnumbered penalty, momentum bonus (2 consecutive wins), last-stand bonus (<25% HP), ambush bonus (+3 first exchange), disadvantaged penalty (no cover). Special actions: Retreat, Talk (social-skill-gated), Analyze Weakness. Crits on natural 6 double damage.
- **Fog of war + line-of-sight.** Bresenham LOS, Chebyshev vision radius, three fog states (UNEXPLORED / EXPLORED / VISIBLE). Authentic stealth tension.
- **Five hand-authored campaign maps** (25×20 typical, TileType enum with 10+ types including doors, vents, hazards, terminals). Mission-critical content exists.
- **Procedural map generation** via chunk-based room-templates + connectors with 5 mission types (INFILTRATION, RETRIEVAL, SABOTAGE, EXPLORATION, EXTRACTION) and 4 difficulty tiers. Foundation for repeatable content.
- **Crew bonus integration.** Elena (vision / retreat), Marcus (silent doors / noise), Priya (analyze weakness), Tomas (talk / noise). Attributes (ACU/RES/COM/ING) stack with equipment effects and skill-tree bonuses.
- **Equipment system.** 10 ground-specific items (personal_shield, noise_dampener, vision_enhancer, lockpick_set, emp_grenade, thermal_visor, breaching_charge, adrenal_compound, deep_scan_probe) with distinct effects.
- **Alert system.** Enemy AI with alert levels (CALM / SUSPICIOUS / ALARMED / HOSTILE) and decay behavior. Stealth has teeth.
- **Briefing + Result loop.** Pre-mission briefing with crew selection (0-2 crew, intel hints); post-mission result screen with stats summary, rewards/penalties, consequence curve.
- **Ghost-run bonus** (+10% on success-undetected). Stealth has a material reward.

### 1.2 What's weak — the five gaps

**Gap 1: Crew are pre-mission bonuses, not field party members.**

The biggest structural gap. When the player selects 0-2 crew at briefing, those crew members apply their bonuses as abstractions — vision bonus, silent doors, talk bonus — but they never *appear on the ground*. The player walks the map alone. There is no visible party, no formation, no crew-specific combat moves, no crew dialogue during exploration. For a game with 19 crew members and strong narrative crew content, this is a profound under-utilization.

**Gap 2: No ground NPCs / no in-field dialogue.**

Story triggers are one-way atmosphere text ("Wrecker's Market") — no branching, no NPC interaction, no faction representatives encountered underground. Fallout 1/2's signature — *dialogue-rich exploration* — is entirely absent. Every encounter is either combat or a one-line flavor blip.

**Gap 3: No expedition-level pressure.**

Darkest Dungeon's core mechanic (stress/torch/resolve building tension over a run) has no analog. The current combat has turn-level tension (Dice & Grit), but across a multi-room expedition, there's no accumulating weight. A 1-room mission and a 15-room mission feel mechanically identical at the meta-run level.

**Gap 4: No persistent crew consequence from ground expeditions.**

Crew return from expeditions unchanged. No injuries carrying over, no stress afflictions, no bonded positive traits from shared runs. Contrast Darkest Dungeon: a hero who survived the deepest dungeon gains the *Flagellant* quirk; a hero who failed a run picks up *Abusive* or *Kleptomaniac*. Aurelia's crew have quirks and loyalty mechanics elsewhere; ground exploration doesn't touch them.

**Gap 5: Visual flatness.**

Tile rendering is functional (faction-aware sprite fallback to colored rectangles) but lacks atmosphere. No lighting direction (tiles are flat-lit). No ambient animation (dust, flickering panels, steam from vents). Alert indicators are dots, not integrated. Minimap is functional but not polished. Ground view reads as a top-down dungeon map without Aurelia's "lived-in industrial" voice.

### 1.3 Secondary gaps

- **Terminal interactions are flavor-only.** Terminals exist as tile type but yield no puzzle, readable data, or unlock content.
- **Equipment is 10 items with static effects.** No progression, no crafting, no specialization — you buy it once, it works forever.
- **Retreat is an all-or-nothing combat action.** No partial retreat, no withdraw-to-reconsider, no tactical fallback to a better position.
- **Contract repeatability is mechanical.** Procedural contracts use templates but don't feel meaningfully different run-to-run beyond seed-variance.

### 1.4 What this doc addresses

- Gap 1 (crew absent) via visible ground party + formation system (§4.1)
- Gap 2 (no dialogue) via in-field NPC encounters + branching interactions (§5.1)
- Gap 3 (no expedition pressure) via Expedition Resolve meter (§4.2)
- Gap 4 (no crew consequence) via Ground Afflictions system (§4.3)
- Gap 5 (visual flatness) via ground rendering overhaul (§6.1-§6.6)
- Secondary gaps via terminal content (§5.4), equipment depth (§7.3), tactical retreat (§4.4), named encounters (§5.2)

---

## 2. Target feel — influences and reference moments

### 2.1 The synthesis — Corridor Expedition with Choice Pressure

Ground exploration pulls from two distinct genres and blends them for Aurelia's register.

**Darkest Dungeon — expedition as committed run with persistent consequence**

Imported elements:
- **Party presence and formation.** Your heroes are *there*, visible, positioned. Combat respects position.
- **Expedition Resolve / stress / torch.** A meter that builds through the run, creating pressure without single-encounter binary outcomes.
- **Afflictions and virtues.** Heroes can return broken or emboldened; persistent quirks carry across runs.
- **Named encounters with consequence.** Specific moments that *mean something* — the Collector, the Shambler, the Fanatic — recognized across the community because they're specific.
- **Between-runs recovery.** Heroes need time at the hamlet to recover; ground expeditions similarly impose station-stay recovery.

What we reject from Darkest Dungeon:
- **The relentless pessimism.** DD's "remind yourself that overconfidence is a slow and insidious killer" tone is specifically gothic-horror. Aurelia is industrial-frontier, not gothic. Our narrator voice is *weight without despair*.
- **The hand-painted gothic aesthetic.** Stays 2D pixel-art per AB.
- **The side-scrolling corridor-only structure.** We keep Fallout's tile grid; we add DD-style pacing *within* the grid (commit-to-advance moments, but not a linear corridor).

**Fallout 1/2 — dialogue-rich tactical exploration**

Imported elements:
- **NPC encounters during exploration** (not only at briefing / result). People underground, in facilities, in ruins. They talk.
- **Branching interaction outcomes** — persuade, intimidate, bribe, observe, fight. Already-present social skills (Tomas's talk bonus) gain meaningful exploration surface.
- **Faction-reputation-consequence encounters.** Who you meet depends on who you've been.
- **Environmental storytelling via readable content.** Terminals yield logs, notes, maps, codes. Loot containers have narrative flavor beyond numeric rewards.
- **Choice consequence that carries forward.** A Fallout encounter's outcome might close a faction, change a quest, shift a town's politics. Aurelia's ground encounters should have similar persistent effects.

What we reject from Fallout:
- **Perks-and-stats theater.** Aurelia's skill tree is already rich; ground exploration doesn't get its own perk system.
- **The 1990s RPG pacing.** Fallout ground exploration was slow; Aurelia's stays tight.

### 2.2 Tonal adjustments for Aurelia

Aurelia is *competent industrial-frontier sci-fi with weight*, not gothic horror or post-nuclear survival. Specific adjustments:

- **Narrator voice** (see §5.3) — closer to Kim Stanley Robinson's Mars trilogy narration or Fiasco's consequence-weight than to DD's relentless dread. The voice respects the expedition and its cost, without moralizing.
- **Affliction language** — "Shaken" not "Paranoid"; "Focused" not "Righteous." Afflictions reflect professional/emotional weight rather than Victorian disorder.
- **Expedition Resolve** — builds tension through the run, but resolves; it isn't an unwinnable spiral. Aurelia expeditions end; DD spirals can consume runs whole.
- **Consequence scope** — afflictions persist *across days*, not permanently, unless the player neglects recovery. DD's permanent madness doesn't fit.

### 2.3 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Darkest Dungeon, "the first time a hero gets Paranoid"** (2016). A non-combat consequence that reshapes your run — the hero doesn't heal from camping; trust breaks down. Aurelia equivalent: crew member returns from a bad expedition with a **Shaken** affliction (§4.3) — for the next 3-5 game days, their bonuses at briefing are reduced and their dialogue flavors changes; station-stay recovery required.

2. **Darkest Dungeon, "the Collector's appearance"** (2017). A specific named enemy, rare, recognized. Meeting one is a story. Aurelia equivalent: **named encounters** (§5.2) — specific NPCs (hostile or not) who appear under specific conditions in specific expedition types. The Archivist, the Foreman, the Walker — each a moment.

3. **Fallout 2, "entering Vault City for the first time"** (1998). The gate NPC stops you. Dialogue branches. Choice of approach (polite / aggressive / deceptive) affects entry. Aurelia equivalent: NPC encounters during exploration have real dialogue trees with skill checks (§5.1), affecting whether the encounter ends friendly, hostile, or neutral.

4. **Fallout 1, "the Master's dungeon terminals"** (1997). Terminals contain logs that *matter* — intel on the Master, passwords for deeper sections, backstory. Aurelia equivalent: terminal content (§5.4) — readable logs that reveal lore, provide passwords for locked doors, show maps of unexplored sections, or connect to salvage narrative (abandoned mining-operation logs echo back to mining Named Wrecks).

5. **Darkest Dungeon, "heroes dying in the Ancestor's estate"** (2016). A hero doesn't come back. Roster permanent loss. The weight of the decision. Aurelia equivalent: **crew can be badly injured** during ground expeditions (§4.3); if the player doesn't retreat in time, crew can be permanently wounded (affliction-chain requiring station-stay recovery, not combat death in campaign content — death remains reserved for specific narrative moments).

### 2.4 What this is not

- **Not Darkest Dungeon: Aurelia Edition.** We import DD's structural weight, not its horror aesthetic or voice.
- **Not Fallout Tactics.** The grid is tactical but not squad-strategy-heavy. Existing Dice & Grit is the combat depth; we don't deepen it.
- **Not a dungeon-crawl roguelike.** Campaign maps are authored; contracts are template-driven. No procedural narrative.
- **Not an open-world.** Ground exploration is per-mission scoped. Maps have entrances, exits, objectives. You don't free-roam a planet.
- **Not crew-death-permadeath.** Crew can be injured / afflicted / require recovery, but not killed outside specific narrative story beats.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Visual / mechanical signal |
|---|---|---|
| Arriving at briefing | Gathering for a job | Crew sprites visible at briefing table; equipment loadout; mission recap with stakes |
| Selecting expedition party | Weighted choice | Crew selection UI shows each crew member's ground-specific bonus + current affliction state; "who can we afford to risk?" |
| Deploying to ground | Commitment | Brief descent/landing cinematic; party appears on map at entrance tile together |
| First corridor / room reveal | Tactical awareness | Fog lifts progressively; party visible at entrance; first interactables catalogued |
| Encountering an NPC (non-hostile) | Curiosity | Dialogue initiates with party-formation visible; skill-check options surfaced per crew present |
| Successful dialogue resolution | Competence | Outcome plays out (doors open, new info gained, faction noted); no combat needed |
| Failed dialogue (negotiation breaks down) | Committed stakes | Transition to combat; party takes formation positions |
| First combat exchange (party formation) | Tactical depth | Combat overlay shows party in formation; positional bonuses visible; crew special abilities available |
| Expedition Resolve depleting | Rising pressure | UI meter visible; ambient tint shifts slightly; crew may develop afflictions if resolve is critical |
| Named encounter | Recognized moment | Specific NPC sprite + name + scripted intro line; "this is the Foreman" moment |
| Terminal reveals lore | Discovery | Terminal screen with readable log; cross-references to known systems / characters |
| Extraction / objective complete | Earned success | Party regroups at exit; results screen tallies not just rewards but crew state changes |
| Crew returns with affliction | Lived consequence | Result screen flags affliction; station-stay recovery suggested; crew dialogue flavor reflects the expedition |
| Crew returns with virtue | Earned bond | Opposite — some runs produce Focused / Hardened / Kin-tied positive quirks |

### 3.2 What each emotion serves gameplay

- **Gathering / weighted choice** → party selection has real weight; crew aren't fungible
- **Commitment** (deployment) → the expedition is a *thing you do*, not a screen
- **Tactical awareness** → the ground map is a place; navigation is deliberate
- **Curiosity / competence / committed stakes** → NPC encounters are moments with real outcome branches
- **Tactical depth** → formation + party makes combat richer without breaking Dice & Grit
- **Rising pressure** → Expedition Resolve adds meta-run tension
- **Recognized moment** → named encounters are memorable
- **Discovery** → terminals and readable content deepen worldbuilding
- **Lived consequence** → crew returning different makes expeditions matter across runs
- **Earned bond** → virtues reward skilled play and party cohesion

### 3.3 The non-goal: punishment spiral

Darkest Dungeon's famous spiral-into-disaster is *not* the Aurelia feel. Our version rewards careful play with survivable-but-weighty expeditions. An afflicted crew member recovers; a bad expedition costs recovery time and rewards, not permanent ruin. The game weighs your choices; it doesn't bury you.

---

## 4. Structural additions — party, resolve, afflictions

### 4.1 Ground Party — crew visible on the map

**The headline structural change.** Selected crew members (v1 cap: 3 crew + player = 4-member party) appear as sprites on the ground map, walking with the player, participating in combat, triggering dialogue moments.

**Party movement:**
- **Formation modes** (toggleable with `F` key):
  - **Line** — party walks single-file, default
  - **Spread** — party occupies 2-3 adjacent tiles, better in open spaces
  - **Guard** — party tight around player, defensive bonus when stationary
- Formation tile footprint scales with party size
- Crew sprites drawn 24×24px, player sprite slightly larger (28×28)
- Party cohesion: members can't drift more than 3 tiles from player; non-cardinal movement synchronizes

**Party combat:**
- **Positional bonuses:** front-line (tank, melee priority, takes first-hit disadvantage in ambush), mid-line (flexible, most crew default here), back-line (support / ranged / talk actions)
- Each crew member contributes an independent combat "turn" in the exchange round — expanded Dice & Grit: up to 4 party dice rolled per exchange, highest wins if cooperating (with party-synergy bonus)
- **Crew-specific abilities** become active:
  - Elena (front-line): "Cover Fire" — absorbs first hit of an exchange (1×)
  - Marcus (mid-line): "Silent Breach" — breach a door silently without alert (1× per expedition)
  - Priya (back-line): "Analyze Weakness" — existing ability stays
  - Tomas (mid-line): "Negotiate" — extended talk action with higher difficulty ceiling
- Player still rolls their own die independent of crew; party cooperation adds a synergy modifier
- Retreat discipline: retreating requires the whole party to disengage; can take 2 turns if mid-combat

**Party health tracking:**
- Each crew member has HP on the ground (calculated from RES attribute + equipment)
- HP damage during expedition persists to expedition end; result screen reports
- A crew member at 0 HP is **wounded** (not dead) — they're carried by party for the rest of the expedition, don't contribute combat, and trigger a post-expedition "Wounded" affliction

**Cost:** ~3-4 weeks. Party rendering + formation logic + positional combat extension + crew abilities wiring.

### 4.2 Expedition Resolve — the meta-run pressure meter

Expedition Resolve is a single meter that tracks the party's accumulated pressure over the run. Starts at 100 at deployment. Depletes through events:

| Event | Resolve cost |
|---|---|
| Each enemy encounter (combat resolved) | −5 |
| Each enemy encounter (stealth bypass) | −2 |
| Hazardous tile crossing | −3 |
| Crew member wounded | −10 |
| Named encounter (non-hostile) | −3 |
| Each 10 tiles traversed | −2 |
| Failed dialogue check | −4 |
| Successful dialogue resolution (combat avoided) | −2 |
| Resting at a "safe" tile (when flagged) | +10 (rare; some maps have safe rooms) |
| Equipment usage (medkit, adrenal compound) | +5 (varies) |

**Resolve thresholds and effects:**
- **100-75 (Steady)** — no effects; party performs normally
- **74-50 (Pressed)** — combat modifier −1 on party dice; ambient tint slight warm red; skill voice lines more frequent
- **49-25 (Strained)** — combat modifier −2; retreat difficulty reduced (easier); crew may trigger stress events on failed rolls
- **24-0 (Broken)** — combat modifier −3; party refuses to advance unless player spends an equipment item or retreats; affliction chance high at expedition end
- **Below 0** — automatic expedition failure; forced retreat to extraction

**Resolve recovery:**
- Cannot recover Resolve within an expedition except via specific tiles (safe rooms) or equipment (stim / adrenal items)
- Between expeditions, station rest + station-hub Cantina visit + specific recovery actions restore Resolve to 100 for next expedition

**Cost:** ~2 weeks. Resolve meter + threshold effects + UI integration + equipment rebalance for stim items.

**Benefit:** ends Gap 3. Expedition-scale pressure exists; long expeditions feel different from short ones.

### 4.3 Ground Afflictions and Virtues

Persistent crew traits earned during ground expeditions. Parallel to Darkest Dungeon's quirks but tonally adjusted for Aurelia.

**Afflictions (negative, earned from bad expeditions):**

| Affliction | Trigger | Effect | Recovery |
|---|---|---|---|
| **Shaken** | Return from expedition with Resolve <25% | −1 combat mod for 3 game-days; ground bonuses halved | 3 days station rest + Cantina visit |
| **Wounded** | Reduced to 0 HP during expedition | Cannot join next 2 expeditions; HP regen slowed | 5 days station rest + possibly medical service |
| **Paranoid** (reworded: **Overvigilant**) | Multiple ambush failures in one expedition | +1 vision but −1 party cohesion (slower formation); Elena / scout variant | 2 days station rest |
| **Fatigued** | Three consecutive expeditions without rest | −1 attribute bonuses while active; cumulative if unaddressed | 2 days station rest |
| **Distrustful** | Party member wounded under your command | Dialogue flavor turns terse; reduces mission-success narrative bonuses until resolved | Dialogue with crew at station + 2 days |

**Virtues (positive, earned from good expeditions):**

| Virtue | Trigger | Effect | Duration |
|---|---|---|---|
| **Focused** | Full expedition success (all objectives, no wounds, Resolve >75%) | +1 combat mod for next 2 expeditions | 2 expeditions |
| **Hardened** | Survive a Broken-resolve expedition without wounds | +5 HP ceiling permanently; 1-use | Permanent |
| **Bonded** | Two crew members who've both been in 5+ expeditions together | Party-synergy bonus +1 permanently when these two are together | Permanent |
| **Resourceful** | Use equipment creatively in 3 distinct tile types during one expedition | Unlock unique equipment stamp (cosmetic + minor bonus) | Permanent |
| **Veteran** | 20 expeditions without a wound | +1 all attributes | Permanent |

Afflictions/virtues are tracked per crew member. Display in crew roster (station hub cantina + Wrecker-Log-adjacent expedition journal).

**Cost:** ~2 weeks. Affliction tracking data model + station-hub recovery flow integration + UI display.

### 4.4 Tactical retreat

Current: retreat is all-or-nothing. New:

- **Partial withdraw** — one crew member can retreat from combat while the rest remain engaged (difficulty +2 over standard retreat); useful for pulling a wounded party member back
- **Fallback to last safe position** — combat retreat option that moves party one formation-step backward rather than full extraction
- **Emergency extract** — expend a specific equipment item ("emergency beacon") to trigger full-party retreat without difficulty check, once per expedition

**Cost:** ~1 week. Retreat option expansion + equipment item addition.

---

## 5. Narrative additions — encounters, expedition voice, consequence

### 5.1 In-field NPC encounters with branching dialogue

NPCs can appear on ground maps as **encounter tiles** (new TileType: `NPC_ENCOUNTER`). When the party reaches an encounter tile, a dialogue interaction initiates.

**Encounter structure:**
- NPC sprite (28×28, hand-authored or procedural depending on importance)
- Dialogue opens using existing dialogue system
- Branch options gated by:
  - **Skill levels** (Persuasion, Intimidation, Observation, Combat Reputation)
  - **Faction reputation** (hostile factions react differently to each other)
  - **Active crew member presence** (certain crew enable certain dialogue options)
  - **Player history** (prior encounters with this NPC, relevant story flags)
- Outcomes:
  - **Peaceful resolution** — NPC helps / trades / shares info; Resolve cost −2 (successful non-combat)
  - **Hostile resolution** — drops into combat with specific NPC template
  - **Neutral walk-away** — both parties disengage; potentially closes content for this expedition

**Encounter content volume:**
- **Campaign maps** — each of the 5 hand-authored maps gets 3-5 authored NPC encounters (15-25 total encounters across campaign)
- **Procedural contracts** — template-based NPC encounters drawn from a shared pool of ~20 encounter templates (variable NPC + dialogue + outcome paths)

**Cost:** ~3 weeks for campaign encounters + 2 weeks for template system. Total ~5 weeks, heavily content-authoring-weighted.

### 5.2 Named encounters

**Specific, recognized NPCs** who appear under specific conditions. Parallel to Darkest Dungeon's Collector/Shambler pattern — when you see one, you know it's a story.

v1 named encounters:

| Name | Context | Encounter type |
|---|---|---|
| **The Archivist** | Any Collective research station map; appears once per playthrough | Non-hostile; offers trade of data for unique reputation; extended dialogue |
| **The Foreman** | Any Miners Union mining facility map; appears after player has completed mining Prospector's Road Chapter 2 | Peaceful; offers Union-aligned mission hooks + rare equipment |
| **The Walker** | Any frontier / outlaw map; rare (10% per expedition); appears on deepest room of map | Mystery encounter; vague dialogue; hints at larger Expanse stories (Ch6-style lore connection) |
| **The Whisper** | Any lab / research map; appears when party's Resolve drops below 30 | Warning encounter; gives party a choice: flee with bonus / press on with escalation |
| **The Claim-Ghost** | Abandoned mining operation maps (cross-pollinate with mining / salvage); appears once ever per save | Unique dialogue; connects to mining/salvage narratives; lore-significant |

Named encounters are one-time per playthrough (with rare exceptions) and gain **distinct visual treatment** — slightly-larger sprite, named badge on reveal, extended intro cinematic (~1.5s camera focus + skill voice line).

**Cost:** ~3 weeks. Named NPC design + content authoring + trigger integration.

### 5.3 Expedition voice / narrator

Ground expeditions gain a **narrator voice** — brief lines that surface at key moments. Voice character calibrated for Aurelia's industrial-frontier register.

**Voice options (decide at briefing or on first expedition):**
- **Ship's Log** — the expedition records as if transcribed by ship's AI; dry, factual, occasionally wry. Default voice.
- **Expedition Leader** — the player's crew captain persona narrates; reflective, competent, takes responsibility.
- **Crew Voice (rotating)** — one line per expedition from a randomized crew member; most personable but least consistent.

Voice surfaces at:
- Deployment ("Landing zone confirmed. Air's breathable. Primary objective is 200 meters down the corridor.")
- First enemy detection ("Contacts ahead. Three on overwatch. Elena's got a clean line if we need it.")
- Low Resolve threshold ("We're running thin. One more bad turn and someone's getting carried out.")
- Named encounter arrival ("That's the Foreman. Union old-school. Let's keep this civil.")
- Terminal read (quoting a log entry directly)
- Extraction ("That's everyone. Back to the ship. The door closes behind us.")

Voice content: ~40 lines per voice × 3 voices = ~120 lines authored for v1.

**Cost:** ~1.5 weeks content + 3 days implementation.

### 5.4 Terminal content

Terminals become readable. When interacted with, display a **log entry overlay** showing:
- Timestamp (in-universe date)
- Author (named or anonymous)
- Body text (3-6 paragraphs)
- Sometimes an action button: "Download" (store in Expedition Log), "Extract Password" (unlocks adjacent door), "Transmit" (sends data to player's ship for later review)

Terminal content types:
- **Operational logs** — who worked here, what they were doing, what went wrong
- **Personal logs** — a worker's thoughts, reveals human cost (connects narratively to salvage's Wrecker's Log themes)
- **Intel data** — passwords, maps of adjacent areas, faction secrets, cross-references to other systems/characters
- **Lore fragments** — worldbuilding (Expanse history, Aurelia political events, pre-campaign context)

v1: ~40 terminal entries across 5 campaign maps + ~20 procedural-pool entries for contracts.

**Cost:** ~2 weeks. Content authoring + terminal UI overlay + password-unlocking mechanic.

### 5.5 Expedition Log (UI additions)

A persistent log accessible from the result screen and station hub. Contains:

- All named encounters met (with location, date, outcome)
- All terminal content read (indexed by type: operational / personal / intel / lore)
- Affliction/virtue history per crew member (when, where, recovery status)
- Major choice moments (faction consequences, dialogue outcomes that persisted)

**Cost:** ~1.5 weeks. New UI + data persistence.

---

## 6. Rendering changes — visual overhaul

### 6.1 Ground lighting and palette

Current: tiles are flat-lit, rendered from sprite fallback to colored rectangles. Upgrade:

- Apply AB §6.1 global lighting (upper-right 45°) to all tile rendering — tile sprites gain shading per their material band
- Palette snap compliance: all ground tiles render through §2 palette discipline
- Fog states redefined in palette terms: UNEXPLORED = `void_deep` solid fill; EXPLORED = dim tint at 40% + `void_mid`; VISIBLE = full tile render
- Hazard tiles glow with tier-4-appropriate emissive (`plasma_core` for thermal hazards, `cryo_fractal` for cold, `ion_arc` for electrical)

**Cost:** ~1.5 weeks. Tile rendering refactor to palette-snap discipline.

### 6.2 Ambient environmental effects

Per tile type / biome, ambient VFX adds life:

- **Lab / research tiles** — occasional spark at broken equipment; steam from vents (`glow_cool` tint)
- **Industrial / mining tiles** — dust motes drifting; faint red-amber glow from distant forges
- **Frontier / outlaw tiles** — flickering fluorescent (occasional alpha dip on tile)
- **Abandoned / wreck tiles** — drift particles; occasional debris skitter
- **Crimson Reach tiles** — dim, red emergency lighting pulse

Effects are low-intensity (AB §3.5 — emissive ≤15% of opaque pixels per tile).

**Cost:** ~2 weeks. Ambient particle systems per tile biome.

### 6.3 Party and enemy sprite upgrades

- Party member sprites rendered with per-crew identity (distinct silhouettes + faction coloring if applicable)
- Facing direction preserved (existing 4-way rotation)
- Health-state overlays — wounded crew member sprite gets visible damage marker (scrolling red tint at edges, slight limp animation)
- Crew-specific idle animations (Elena leans into cover, Priya scans surroundings, etc.)
- Enemy sprites gain alert-state visual treatment: CALM / SUSPICIOUS shows thought-bubble animation; ALARMED / HOSTILE shows exclamation + eye-glow

**Cost:** ~2-3 weeks. Sprite authoring + animation state integration.

### 6.4 Fog of war polish

Current: binary fog overlay. Upgrade:

- Smooth fog edges via signed-distance-field (SDF) per-tile alpha gradient; tiles at exact LOS boundary fade smoothly
- Recently-visible tiles (visible last turn, now out of LOS) have a brief "after-image" fade (2 turns) before returning to EXPLORED state
- Vision radius visualization — optional faint circle overlay around player shows current vision radius
- Vision-enhancing equipment effects visible as UI glyph

**Cost:** ~1 week. Fog system refinement.

### 6.5 Minimap polish

- Integrated with main camera — minimap and main view now share palette discipline
- Named encounters shown as distinct symbols on minimap
- Interactables (terminals, loot, NPCs) shown with distinct glyphs
- Expedition Resolve meter integrated above minimap
- Minimap expandable (`M` key) to full-screen overview showing entire explored map

**Cost:** ~1 week. UI refinement.

### 6.6 Expedition entry / extraction cinematics

Brief transition beats for deployment and extraction:

**Deployment:**
- 0.0–0.6s: briefing fade; transition through short "descending" visual (cockpit → hull opening → ground approach)
- 0.6–1.2s: party arrives at entrance tile; formation forms
- 1.2–1.5s: ground view resolves; first turn begins

**Extraction:**
- 0.0–0.5s: objective-complete banner
- 0.5–1.2s: party moves to extraction tile; shuttle / transport sprite arrives
- 1.2–1.8s: ascent visual; transition to result screen

Skippable per player preference.

**Cost:** ~1.5 weeks. Scripted cinematic beats.

---

## 7. Gameplay changes forced by structural and rendering work

### 7.1 Crew participation in expeditions is now real gameplay

§4.1 changes crew from pre-mission bonuses to field party members. This is a **meaningful gameplay change** — parties are allocated, positioned, can be wounded. Calibration: existing crew bonuses still apply (they're now amplified by crew presence); combat scaling may need retuning for 3-4 party members vs. 1 player.

### 7.2 Expedition Resolve adds a new win/loss condition

§4.2 adds a new failure mode: Resolve dropping below 0 forces extraction. This is a new expedition-failure state the narrative must handle ("The expedition was pulled back before objectives were complete — what happens?"). Needs result-screen copy for partial-success states.

### 7.3 Equipment depth

Equipment roster grows from 10 items to ~18-22 items with new categories:

- **Medical/recovery** (stim packs, field medkits, adrenal compound variants) — restore HP or Resolve
- **Emergency** (emergency beacon, distress flare) — one-time extraction or combat-avoidance
- **Tactical** (formation beacon, ambush disruptor) — modify combat positioning
- **Terminal tools** (splicer, signal decoder) — reveal terminal content or bypass locks

Acquired via station shops (Shipyard ground-gear tab), campaign rewards, and crafted from refining (per `37_overhaul_refining.md` — ground equipment already exists as refining output).

**Cost:** ~1 week for item design + data integration.

### 7.4 Station-hub recovery integration

§4.3 afflictions require station-stay recovery. This is **new gameplay** in the station hub:

- Cantina gains a "Crew Recovery" panel showing each crew member's status (Healthy / Shaken / Wounded / etc.) and expected recovery time
- Player can visit Cantina and "spend time" (fast-forward in-game days) to accelerate recovery
- Medical services at specific stations can expedite recovery (Collective / Union medical districts)
- Crew in recovery cannot be selected for next expedition

**Cost:** ~1 week. Integration with station hub doc §35.

### 7.5 Faction reputation consequences from ground expeditions

NPC encounters (§5.1) with faction representatives affect faction reputation — killing an NPC loses faction rep; peaceful resolution gains small rep. Already-present faction rep system, now affected by ground content.

### 7.6 No other gameplay changes

Dice & Grit combat mechanics, skill tree, core stats — unchanged.

---

## 8. Dependencies

### 8.1 On other overhaul docs

- **`20_aesthetic_bible.md`** — palette, lighting, material bands
- **`30_overhaul_space_combat.md` §4.4** — camera system (deployment cinematic, combat focus)
- **`30_overhaul_space_combat.md` §4.7** — damage number weight tiers (combat damage numbers reuse)
- **`35_overhaul_station_hub.md` §4.7** — expanded station descriptor + service availability (affliction recovery panel lives here)
- **`35_overhaul_station_hub.md` §4.10** — docking/undocking cinematics (deployment cinematic shares pattern)
- **`36_overhaul_salvage.md`** — cross-pollination with Named Wrecks; abandoned mining operations narrative threads
- **`37_overhaul_refining.md`** — ground equipment crafted via refining

### 8.2 On production systems

- `spacegame/views/ground_*.py` — extended heavily
- `spacegame/models/ground.py` — party support, resolve, afflictions, encounter tiles
- `spacegame/models/ground_combat.py` — party combat, formation bonuses, party dice pool
- `spacegame/models/ground_crew.py` — affliction integration, party member field state
- `spacegame/models/ground_equipment.py` — expanded item roster
- `data/ground/campaign/` — extended with encounter NPCs, terminal content
- `data/ground/encounters.json` (new) — procedural encounter templates
- `data/ground/terminals.json` (new) — procedural terminal content
- Save system — persistent afflictions, encounter history

### 8.3 On content authoring

- **Campaign NPC encounters:** 5 maps × 4 encounters avg × ~300 words = ~6,000 words
- **Named encounter content:** 5 named NPCs × ~800 words each = ~4,000 words
- **Terminal content:** 40 campaign terminals × ~150 words + 20 procedural × ~150 = ~9,000 words
- **Expedition voice:** 3 voices × 40 lines each = ~120 lines (~2,000 words)
- **Affliction/virtue flavor:** crew-specific dialogue lines per affliction × 19 crew = ~30 lines (~1,500 words)
- **Procedural encounter templates:** 20 templates × ~200 words = ~4,000 words

**Total: ~26,500 words** of ground-specific narrative content. Comparable to salvage's 26,600.

---

## 9. Phasing

Ground exploration overhaul is substantial. 7 phases; parallelizable where noted.

### Phase GR1 — Ground party + formation (~3-4 weeks)

- Crew sprites on map
- Formation modes (Line / Spread / Guard)
- Party movement synchronization
- Party combat extension (party dice pool, positional bonuses)
- Crew abilities in-field

**Why first:** the structural gap (Gap 1) is the biggest; solving it unlocks everything else.

### Phase GR2 — Expedition Resolve + afflictions (~2-3 weeks)

- Resolve meter + threshold effects
- Affliction tracking data model
- Virtue tracking data model
- UI integration (meter, crew status)
- Station-hub recovery panel (§35 integration)

**Why second:** enables expedition-scale tension; requires party from GR1 for wound-tracking.

### Phase GR3 — Ground visual overhaul (~2-3 weeks)

- Tile lighting + palette compliance (§6.1)
- Ambient environmental effects (§6.2)
- Sprite upgrades (§6.3)
- Fog polish + minimap polish (§6.4 / §6.5)
- Deployment / extraction cinematics (§6.6)

**Parallelizable** with GR1/GR2.

### Phase GR4 — In-field NPC encounters + dialogue system integration (~3-4 weeks)

- `NPC_ENCOUNTER` tile type + encounter trigger
- Branching dialogue UI (reuses existing dialogue system)
- Skill-check / faction-rep / crew-presence gating
- Authoring: campaign NPC encounters (15-25 encounters)
- Authoring: procedural encounter templates (20)

### Phase GR5 — Named encounters + expedition voice + terminal content (~3-4 weeks)

- 5 named encounters authored + integrated
- Expedition voice system + 3 voice content libraries
- Terminal content (~40 campaign + 20 procedural entries)
- Cross-pollination with salvage / mining narrative threads

### Phase GR6 — Equipment depth + tactical retreat polish (~1-2 weeks)

- New equipment items (8-12 additions)
- Tactical retreat variants (§4.4)
- Emergency beacon integration
- Refining integration (equipment crafting hooks)

### Phase GR7 — Expedition Log + polish pass (~1-2 weeks)

- Expedition Log UI (§5.5)
- Result screen refinement (wound / affliction summary)
- Final polish on all integrations

### Total estimate: ~15-20 weeks

Parallelizable substantially with other Tier 2 overhauls.

---

## 10. Success criteria

Ground exploration overhaul is done when:

1. **Crew are physically present.** Players refer to their ground team by name, remember specific crew moments from specific expeditions.
2. **Expeditions have weight.** A long, hard-fought expedition feels meaningfully different from a quick extraction.
3. **Resolve creates tension.** Players triage risk; they understand "we're pressed, let's fall back."
4. **Afflictions / virtues matter.** Crew return from expeditions *different*; the player plans around recovery.
5. **NPCs make the Expanse feel populated.** Ground expeditions encounter people, not just enemies; dialogue branches have real outcomes.
6. **Named encounters are memorable.** Meeting the Foreman is an event players discuss.
7. **Terminals reward curiosity.** Players read terminal content; it deepens their understanding of the world.
8. **Visual voice matches Aurelia.** Ground scenes feel industrial-frontier, lit consistently, palette-compliant.
9. **Fallout bones preserved.** Tactical grid + Dice & Grit + fog of war remain intact and effective.
10. **Darkest Dungeon weight achieved without DD's despair.** Expeditions are serious, consequential, survivable, rewarding.
11. **Performance.** Ground view holds 60 FPS with 4-member party + 6-8 visible enemies + ambient effects on a 25×20 map.

---

## 11. Open questions

1. **Party cap — 3 crew + player, or 4?** v1 proposal: 3 crew + player = 4-member party. Calibrate during GR1 playtesting; could scale up with veteran player.
2. **Party-dice synergy curves.** Rolling up to 4 party dice per exchange could make combat trivially easy at high party count. Synergy bonus applies only on cooperation (not raw "highest of 4 dice"). Needs careful Dice & Grit calibration.
3. **Named encounter frequency.** v1 proposes 5 named encounters, each one-time per playthrough. Players who miss one (skip a content type entirely) never see it. Acceptable trade for rarity feel; flag if playtest shows misses.
4. **Narrator voice delivery — text only, or with audio?** Text only for v1 (Tier 3 audio concern). Text positioning: dedicated corner region like skill voices (mining/salvage pattern).
5. **Cross-pollination scope.** Some ground content references salvage Named Wrecks or mining Prospector's Road. Requires coordinated implementation — flag for phase timing.
6. **Wound threshold calibration.** Crew at 0 HP = wounded (not dead). Is 0 the right threshold? Or should wounded state trigger at 25%? v1: 0, with "incapacitated" state at 25% as potential future.
7. **Procedural encounter variety.** 20 encounter templates may feel repetitive with high contract volume. Scale expandable in GR7+ / post-launch.

---

## 12. Out of scope

- **Open-world planetary exploration** — expeditions remain mission-scoped
- **Full perks-and-stats ground-specific system** — Aurelia's existing skill tree is enough
- **Crew permadeath** — crew can be wounded, afflicted, require recovery, but not killed outside specific narrative story beats
- **Ground combat mechanical redesign** — Dice & Grit preserved; positional bonuses layered on, not replacement
- **Multiplayer / co-op expeditions** — single-player only
- **Ground vehicle combat** — if vehicles exist, they're part of a separate system not this doc
- **Planet-scale terrain generation** — maps are mission-scoped, not planet-surface-scoped
- **Full voice acting** — Tier 3 audio framework

---

*Tier 2 docs complete. The nine Tier 2 overhauls (`30`–`38`) form the complete system-overhaul set per master plan §5. Next work is either:*

- ***Tier 3 parallel docs*** — `40_audio_synthesis_framework.md`, `41_vfx_particle_vocabulary.md`, `42_ui_chrome_components.md`. These coordinate cross-system visual/audio discipline.
- ***Implementation phasing*** — pick the first concrete phase to build (candidates: Combat C1 camera + pacing beats; Ship Builder B1 hangar environments; Mining M1 balance formalization). Infrastructure work unblocks everything else.
- ***Revisiting design*** — review the full corpus for consistency, scope realism, content-authoring load, or scope cuts before implementation begins.

*User's call on next direction.*
