# Aurelia Overhaul Glossary

> **Status:** v1 — canonical reference for every coined term across the 17-doc overhaul corpus. Consult this before authoring content or naming new systems to maintain consistency across multi-agent workstreams.
>
> Entries reference their source doc(s) in `[brackets]`. Categories are organized for scan-ability, not alphabetical.

---

## Table of Contents

1. Tonal / voice discipline
2. Architectural primitives
3. Factions and cultural entities
4. Manufacturers
5. Identity architecture (the five-mapping pattern)
6. The Prospector (mining)
7. The Salvager (salvage)
8. The Fabricator (refining)
9. Combat terminology
10. Ground Exploration terminology
11. Ship builder, galaxy map, trading, station hub
12. VFX, audio, UI primitives
13. Palette and material canon
14. Content authoring constraints (banned terms, anti-patterns)

---

## 1. Tonal / voice discipline

| Term | Definition |
|---|---|
| **warm-industrial** | Aurelia's base aesthetic voice — grounded sci-fi with mechanical authenticity and visible wear. Warmth skew ≈ +14 in palette terms. [Bible §1] |
| **lived-in** | Wear is a parameter, not an afterthought. Every material has visible history. Seams, rivets, scorch marks, patina are legible. [Bible §1] |
| **analog-future** | Physical controls over holographic UI. Hardware reads as physical (switches, dials, vented panels). Limited emissive budget. Warm glow, cool sky. [Bible §1] |
| **pivot-from-base-voice** | Core discipline: each faction/identity inflects the warm-industrial base without contradicting it. [Bible §10] |
| **palette-snapped rendering** | Default rendering mode — pixels snap to palette entries post-lighting. Produces chunky, material-honest lighting bands. [Bible §2.1, Framework §5.1.1] |
| **banded lighting** | The visual result of palette-snap: discrete color bands read as *metal under light* rather than *computer gradient*. |
| **emissive budget** | ≤15% of opaque pixels per ship (and analogous caps for scenes) can be emissive. Emissive is signal, not decoration. [Bible §3.5] |
| **silence as signal** | Audio discipline: scenes without music trust ambient + SFX. Music earns its entrance at weighted moments. [Audio §5.5] |

---

## 2. Architectural primitives

Cross-cutting systems consumed by multiple Tier 2 overhauls.

| Term | Definition |
|---|---|
| **SceneCamera** | Shared camera primitive consumed by 9 systems (combat, builder, galaxy, mining, salvage, station hub, ground). Tracks offset + zoom + shake + transition state. Combat-specific state set is one flavor of a general primitive. [Combat §4.4, detailed spec in `91_scene_camera_api.md`] |
| **ShipComposite** | Unified ship rendering pipeline. Rebuilt per Framework §2 to support 5 consumers (combat, builder preview, builder test flight, salvage module recovery, station hub docked glimpse). [Framework §2] |
| **ParticlePool** | Shared object-pooled particle system (max 500 live particles). All particle emissions flow through this; no system rolls its own. [VFX §1.1] |
| **AudioManager** | Engine audio singleton with pygame.mixer backend. Supports music / ambient / SFX with 3-tier volume mixing. Already implemented. [Audio §1.1] |
| **hangar environment system** | Procedural backdrop system introduced by ship builder doc. 14 total variants across 3 systems (builder / station hub / salvage broker docksides). [Builder §4.1] |
| **faction color overlay** | Accent-layer discipline: faction identity expressed through stripe colors, insignia, tinted emissives. 5 consumers. [Bible §4.8] |
| **news ticker** | Scrolling Expanse-wide headlines from `news_ticker` model. Integrated in trading + station hub. [Trading §4.2, Hub §4.4] |
| **journal surface family** | Shared UI anatomy for in-game journals. 4 realizations: Claim Ledger, Wrecker's Log, Fabricator's Register, Expedition Log. [UI Chrome §5.6] |
| **skill voice corner region** | Shared UI overlay for Disco Elysium-inspired inner-voice skills. 3 consumers × 5 voices each = 15 total voices. [UI Chrome §5.7] |
| **thought cabinet** | Permanent identity-internalization mechanic. 3 realizations: mining (6 thoughts), salvage (6 thoughts), refining (4 thoughts). [Mining §5.3, Salvage §5.3, Refining §5.3] |

---

## 3. Factions and cultural entities

The five factions of the Aurelia Expanse. Faction voice references in `requirements/cultural_guide.md`.

| Faction | Register | Primary activity | Identity |
|---|---|---|---|
| **Commerce Guild** | Data-dense brutalism; commercial order | Trading | The Merchant |
| **Crimson Reach** | Raider, outlaw, threat | Combat | The Captain |
| **Miners Union** | Solidarity labor, working-class | Mining | The Prospector |
| **Frontier Alliance** | Self-reliant, outlaw-adjacent, patchwork | Salvage | The Salvager |
| **Science Collective** | Precise, institutional, clinical | Refining | The Fabricator |

Each faction occupies a cultural register that pivots from warm-industrial in a distinct direction [Bible §10].

---

## 4. Manufacturers

Production ship-part brands (from `data/ships/modules.json`). Orthogonal to factions — any manufacturer can be used by any faction, tinted via faction color overlay. [Bible §4]

| ID | Brand register | Shape vocabulary | Primary material |
|---|---|---|---|
| `reyes_kowalski` | Workhorse, civilian | Modular, rectangular, predictable | brushed_steel |
| `foundry` | Heavy industrial | Modular, chunky, oversized rivets | union_ceramic |
| `talon` | Precision | Angular, asymmetric, aggressive | solari_chrome |
| `sable` | Low-signature stealth | Rounded, recessed, smoothed | collective_composite (dark variant) |
| `meridian` | Efficient | Rounded, curved, organic-precision | collective_composite (bright variant) |
| `salvage_rat` | Scrap, jury-rigged | Modular with broken symmetry | frontier_canvas |

---

## 5. Identity architecture

The five-faction × five-activity × five-identity mapping. Canonical per Bible §10.

| Identity | Treatment depth | Main content |
|---|---|---|
| **The Prospector** | Full (mining) | 6-chapter Prospector's Road + 4 optional tracks |
| **The Salvager** | Full (salvage) | 6-chapter Wrecker's Log + 4 optional tracks |
| **The Fabricator** | Lighter (refining) | Seasonal events + milestone progression (no chaptered campaign) |
| **The Captain** | Visual overhaul only (combat) | Identity accumulates through UX/encounters |
| **The Merchant** | Visual overhaul only (trading) | Identity accumulates through UX/encounters |

**Cultural geography by work** — a player who inhabits multiple identities traverses Aurelia's cultural space through chosen work. [Bible §10.5]

---

## 6. The Prospector (mining)

**Voice anchor:** Appalachian coal miner / Wyoming oilfield worker. Union-solidarity, wry understatement, earned authority. [Mining §5.1]

### Campaign — The Prospector's Road

Six-chapter main campaign, linear structure, ~25-40 sessions to complete.

| Chapter | Title | Unlock reward |
|---|---|---|
| 1 | First Claim | Claim Ledger UI, Union reputation track begins |
| 2 | The Union Question | Deep Core upgrades tier 2; faction-aligned path (Union or Frontier) |
| 3 | The Seam Wars | Rival Prospectors + Legendary Seams tracks unlock |
| 4 | The Deep Vein | Master-tier Deep Core upgrades + glasswater ore |
| 5 | The Name on the Door | Prestige levels 6-10 + Prospector callsign |
| 6 | The Abyss (optional lore) | Thought cabinet entry "The Long Dark Remembers" — no mechanical gating |

### Named NPCs

| Name | Role | Introduction |
|---|---|---|
| **Augustyn "Auggie" Voss** | Old-timer mentor at starter mining site | Chapter 1 |
| **Marta Beleń** | Miners Union organizer; offers Union membership | Chapter 2 |
| **Itzal Remé** | Rival prospector working the same seam | Chapter 3 |
| **Cesarine Vega** | New prospector the player mentors | Chapter 5 |

### Skill voices (5)

Inner-voice inner instincts. Italicized, palette-colored, sparse (1-3 per session).

| Skill | Palette | Personality |
|---|---|---|
| **Ore Sense** | solari_chrome_bright | Intuitive, soft, observational |
| **Seismic Instinct** | plasma_core | Technical, alert, precise |
| **Union Heart** | union_ceramic_bright | Solidarity, wry, elder |
| **Deep Ear** | cryo_fractal | Eerie, patient, ancient |
| **Weathered Hands** | frontier_canvas mid | Veteran-grizzled, deadpan |

### Thought cabinet (6)

| Thought | Effect |
|---|---|
| **The Good Strike is Enough** | +2 energy pool; "I don't chase the deep." |
| **The Union Pays Its Dues** | +5% wholesale in Union systems |
| **I Work Alone** | +1 click power |
| **The Deep Calls** | +10% strata token yield at depth 80+ |
| **A Prospector's Superstitions** | +5% rare ore chance |
| **The Name on the Door** | Prospector callsign cosmetic |

### Mechanics

| Term | Definition |
|---|---|
| **Strata Tokens** | Internal mining currency. Earned from depth + full-clears. Never converts to CR. [Mining §4.1] |
| **Prestige** | Reset depth + upgrades; gain +10% strata multiplier per level. Max 10 (Ch5 unlocks levels 6-10). [Mining §8.4] |
| **Deep Core Upgrades** | 9 strata-token purchases (Silo Expansion, Ore Scanner, Auto-Drill, Drill Power, Energy Conduit, Seismic Pulse, Depth Scanner, Automaton Core, Deep Strata). |
| **Claim Ledger** | Prospector's journal surface (aged paper aesthetic). Persistent record of chapters, NPCs, thought cabinet, stats. [Mining §8.7] |
| **Glasswater ore** | Top-tier ore unlocked at Chapter 4, appears only at depth 100+. |
| **Union Hall** | Station subsystem in Miners Union systems. Augustyn, Marta, bulletin board, memorial wall. [Mining §8.8] |

### Depth layers

Surface → Shallow Rock → Mid Strata → Deep Core → Abyssal Vein.

### Optional content tracks

| Track | Count (v1) | Examples |
|---|---|---|
| **Rival Prospectors** | 5 NPCs × 6-8 scenes | Named persistent rivals |
| **Legendary Seams** | 6 | The Echo Vein, The Cold Heart, The Old Mine, The Singing Glass, The Breathing Vein (+ 1 reserved) |
| **Anomaly Investigations** | 3 chains × ~3 sessions | The Breathing Rock, The Silent Layer, Whispers from the Deep |
| **Deep-Core Dives** | 3 scenarios | Endgame timed sessions at depth 150+ |

---

## 7. The Salvager (salvage)

**Voice anchor:** Newfoundland shipwreck hunter + post-war battlefield archaeologist + deep-sea commercial salvor. Terse, haunted-in-a-working-way, morally grey. [Salvage §5.1]

### Campaign — The Wrecker's Log

Six-chapter episodic campaign. Each chapter is a named wreck; wrecks can persist and be revisited. ~20-30 sessions for core chapters.

| Chapter | Title | Unlock reward |
|---|---|---|
| 1 | First Wake | Wrecker's Log UI, Mattsen broker, broker rep system |
| 2 | The Signal Ship | Signal Tracker capability + Named Wrecks track + Erika broker |
| 3 | What Was Taken | Master-tier salvage upgrades + Third Shift broker + moral-weight faction path |
| 4 | The Butcher's Bill | **Module Recovery capability** + Cesarine broker + glasswater tier content |
| 5 | The Long Wake | Wrecker Cycles capability + Pell broker + Wrecker callsign |
| 6 | The Long Dark (optional lore) | Thought cabinet entry — no mechanical gating |

### Brokers (5)

Each with distinct voice, buying specialty, mutual tensions.

| Broker | Specialty | Voice |
|---|---|---|
| **Mattsen Holt** | Generalist | Honest-fence, dry |
| **Erika Sennen** | Historical / pre-Expansion | Tense, scholarly |
| **The Third Shift** | No-questions anonymous | Encrypted; text-only UI (no portrait) |
| **Cesarine "Ces" Marrot** | Military-grade | Former military, tight |
| **Pell Bray** | Expeditionary (post-cycle only) | Quiet, long-sighted |

### Skill voices (5)

| Skill | Palette | Personality |
|---|---|---|
| **Forensic Eye** | cryo_fractal | Observational, precise, attends to detail |
| **Wreck Logic** | plasma_core | Structural, practical, experienced |
| **Ghost Channel** | hud_muted | Haunted, patient, rare |
| **Trained Hand** | frontier_canvas | Practiced, deadpan, workmanlike |
| **Buyer's Memory** | hud_cyan | Mercantile, knowing, wry |

### Thought cabinet (6)

| Thought | Effect |
|---|---|
| **I Don't Ask Where** | +8% broker rate |
| **The Dead Don't Pay Rent** | +5% extraction speed |
| **Some Things Aren't For Sale** | +3 Wrecker Standing per named wreck |
| **I Know a Buyer** | +10% CR on commodity sales |
| **The Long Dark Remembers** | Skill voices trigger +20% |
| **The Trade Is Old** | +5% discovery rate permanently |

### Mechanics

| Term | Definition |
|---|---|
| **Reputation Fragments** | Internal salvage currency. Spent on upgrades + broker-specific rep. Never converts to CR. |
| **Wrecker Standing** | Salvage campaign currency. Gates master-tier capabilities. Never converts to CR. |
| **Wrecker Cycles** | Prestige-equivalent. Move to a new region; broker rep resets, Wrecker Standing compounds +5%/cycle. Max 5. |
| **Module Recovery** | Salvager's signature capability (unlocked Chapter 4). Recover ship modules directly from wrecks. Rate-limited: 1/session, 1/named-wreck-visit, capped at current ship tier. Modules have 60% durability — must be refit. [Salvage §9.1] |
| **Wrecker's Log** | Salvager's journal surface (battered leather aesthetic). [Salvage §8.4] |
| **Collector's Wall** | Museum-like UI within Wrecker's Log showing kept artifacts. 24-slot equip system with passive bonuses. [Salvage §7.3] |
| **Corruption Pressure** | Timer-based extraction tension (preserved from current game). [Salvage §1.1] |
| **Signal Tracker** | Capability unlocked Chapter 2 — reveals adjacent-cell signals passively. |

### Named wrecks

Campaign-embedded persistent wrecks + optional-track wrecks.

| Wreck | Source | Notes |
|---|---|---|
| **The Signal Ship** | Chapter 2 | Broadcasts 40-year-old distress call; return multiple sessions |
| **The Drift** | Named Wrecks track | Habitat module adrift decades |
| **The Negotiator** | Named Wrecks track | Diplomatic courier; encrypted files |
| **The Museum Ship** | Named Wrecks track | Already-salvaged items; meta-archaeology |
| **The Long Dark** | Chapter 6 | Pre-Expansion metallurgy; shouldn't exist |

### Optional content tracks

| Track | Count | Notes |
|---|---|---|
| **Named Wrecks** | 6 v1 | Each with 3-4 sessions of unique content |
| **Broker Relationships** | 5 brokers × 8-12 scenes each | Persistent relationships |
| **The Collector's Wall** | 24 artifact slots v1 | Cosmetic + small passive bonuses |
| **Hostile Recoveries** | 4 scenarios v1 | Post-combat salvage on wreckage |

---

## 8. The Fabricator (refining)

**Voice anchor:** Postwar Japanese swordsmith + Bauhaus workshop master + Bell Labs engineer + Arts & Crafts woodworker. Precise, measured, craft-pride without pretension. Quiet. [Refining §5.1]

### No chaptered campaign

Refining uses **seasonal events + milestone progression + correspondence**, not chapters. [Refining §6]

### Seasonal events (3)

| Event | Cadence | Purpose |
|---|---|---|
| **The Exposition** | Quarterly (~90 in-game days) | Collective crafting showcase. Submit up to 3 crafts; themed judging. |
| **The Commission** | Throughout year | Named clients commission specific complex crafts with deadlines. |
| **The Rediscovery** | Yearly | Lost-technique investigation; reconstruct a forgotten recipe. |

### Named peer NPCs (5)

Fabricator correspondence archive. No dramatic NPCs — peers who write letters referencing player's craft.

| Name | Affiliation |
|---|---|
| **Adisa Lark** | Medical-research fabrication firm |
| (4 others — named in content authoring phase) | Collective researchers, craft-firm owners, former mentors |

### Skill voices (5)

| Skill | Palette | Personality |
|---|---|---|
| **Material Sense** | collective_composite bright | Reads raw inputs; knows purity |
| **Heat Eye** | plasma_core | Reads forge conditions |
| **Recipe Memory** | solari_chrome_bright | Institutional knowledge |
| **Patient Hand** | union_ceramic_bright | Doesn't rush |
| **Quality Ear** | hud_cyan | Hears when something rings true |

### Thought cabinet (4 — lighter treatment)

| Thought | Effect |
|---|---|
| **I Work in Margins** | +3% yield on all recipes |
| **Patience Is A Tool** | +5% forge-token generation during long sessions |
| **The Recipe Remembers** | -1 schematic data cost on discoveries |
| **Craft Pride** | +3% S-grade probability |

### Mechanics

| Term | Definition |
|---|---|
| **Forge Tokens** | Internal refining currency. Spent on forge upgrades. Never converts to CR. [Refining §4.1] |
| **Fabricator Standing** | Refining campaign currency. Gates master-tier capabilities. Never converts to CR. |
| **Quality Variance** | Unlocked at Fabricator Standing tier 4 + gold mastery. Crafts roll S/A/B/C grades with upside-only bonuses. [Refining §9.1] |
| **Mastery tiers** | Per-recipe progression: Bronze (3 crafts) → Silver (8) → Gold (15). |
| **Fabricator's Register** | Refiner's journal surface (institutional-clean workshop notebook aesthetic). [Refining §8.7] |
| **Masterwork Registry** | Register section for S-grade + gold-mastered crafts. 20/50/100 slots by tier. [Refining §7.1] |
| **Masterwork Stamp** | Cosmetic mark applied to ship modules crafted as Masterworks. 3/5/7 equip slots by tier. |
| **Seasonal Archive** | Register section for Exposition submissions, Commission log, Rediscovery events. |
| **No prestige equivalent** | Unlike mining/salvage, refining has no reset mechanic — linear skill accumulation per Dwarf Fortress legendary-craftsman aesthetic. |

### Recipe tiers (existing)

- **Tier 1 (base)**: 22 recipes, available immediately
- **Tier 2 (advanced)**: 16 discoverable recipes — unlock via mastery or schematic data
- **Tier 3 (master)**: subset of tier 2 gated by Fabricator Standing

### Optional content tracks (3)

| Track | Purpose |
|---|---|
| **The Masterwork Registry** | S-grade + gold-mastered crafts archive with Masterwork Stamps |
| **Seasonal Archive** | Exposition / Commission / Rediscovery history |
| **Collective Correspondence** | Accumulated mail from Fabricator peers |

---

## 9. Combat terminology

Space combat specifics. Visual overhaul scope.

| Term | Definition |
|---|---|
| **ActionQueue** | Existing multi-action turn system. |
| **Dual Tech** | Two-crew coordinated attack. 7 techs v1. Gets cinematic framework. [Combat §4.3] |
| **Ultimate** | Rare legendary-class move. ~4.5s cinematic (vs. dual tech's 3.2s). Budget < 2 per playthrough. |
| **Elements** | Five elemental weapon types: Kinetic, Plasma, Ion, Cryo, Voltaic. Each has distinct particle vocabulary. [VFX §5] |
| **Momentum** | Combat mechanic: 2 consecutive hit successes grants +2 combat modifier. |
| **Dual Tech Cinematic** | 3.2s scripted framework: zoom → darken → portraits → name-hold → combined-element visual → tier-4 impact → restore. [Combat §4.3] |
| **Damage Number Weight Tiers** | 4 tiers from minor (12pt, quick fade) to cinematic (32pt stroked, 2.0s fade). [Combat §4.7] |
| **Module Targeting Visual Layer** | Visual feedback for module-targeted damage: outline highlight, hit flash, damage overlay, destruction marker. [Combat §4.2] |
| **Arena Entry Animation** | 1.5s scripted sequence: camera push-in → engine ignition → enemies slide in. [Combat §4.8] |
| **Red Line overlay** | Critical-HP scene overlay: warm tint + pulsing red vignette. [Bible §8.2, Combat §3.1] |

---

## 10. Ground Exploration terminology

Anchored on Darkest Dungeon structure + Fallout 1/2 flavor. [Ground Ex §2.1]

### Party and formation

| Term | Definition |
|---|---|
| **Ground Party** | Up to 3 crew + player = 4-member party. Crew visible on map (not pre-mission abstractions). [Ground §4.1] |
| **Formation (Line / Spread / Guard)** | 3 formation modes toggled with `F` key. |
| **Positional combat** | Front-line / mid-line / back-line positions; each crew member contributes to party dice pool. |

### Expedition Resolve

| Term | Definition |
|---|---|
| **Expedition Resolve** | Meter tracking party's accumulated pressure across a run. Starts at 100, depletes through events. [Ground §4.2] |
| **Resolve thresholds** | Steady (100-75), Pressed (74-50), Strained (49-25), Broken (24-0). Each threshold modifies combat + affliction risk. |

### Ground Afflictions (5 v1)

Persistent crew traits earned from bad expeditions.

| Affliction | Trigger |
|---|---|
| **Shaken** | Return with Resolve <25% |
| **Wounded** | Reduced to 0 HP during expedition |
| **Overvigilant** | Multiple ambush failures |
| **Fatigued** | 3 consecutive unrested expeditions |
| **Distrustful** | Crew member wounded under player's command |

### Ground Virtues (5 v1)

Positive traits earned from good expeditions.

| Virtue | Trigger |
|---|---|
| **Focused** | Full expedition success, no wounds, Resolve >75% |
| **Hardened** | Survive a Broken-resolve expedition without wounds |
| **Bonded** | Two crew have been in 5+ expeditions together |
| **Resourceful** | Use equipment creatively in 3 distinct tile types |
| **Veteran** | 20 expeditions without a wound |

### Named encounters (5 v1)

Specific NPCs with conditional appearance and scripted moments.

| Name | Context |
|---|---|
| **The Archivist** | Collective research station maps |
| **The Foreman** | Miners Union facility maps (post-mining Ch2) |
| **The Walker** | Frontier / outlaw maps (rare) |
| **The Whisper** | Lab / research maps (when Resolve <30) |
| **The Claim-Ghost** | Abandoned mining operation maps (cross-pollinate with mining/salvage) |

### Other

| Term | Definition |
|---|---|
| **Dice & Grit** | Existing ground combat system. 1d6 + mod vs 1d6 + mod. [Ground §1.1] |
| **Tactical Retreat** | Retreat variants: partial withdraw, fallback, emergency extract. [Ground §4.4] |
| **Hostile Recovery** | Post-combat salvage on wreckage. Bridges combat + salvage. [Ground §7.4] |
| **Expedition Log** | Ground exploration journal surface. [Ground §5.5] |
| **Narrator Voice** | Selectable expedition voice: Ship's Log (default, dry factual) / Expedition Leader (reflective) / Crew Voice Rotating (personable). [Ground §5.3] |
| **NPC_ENCOUNTER tile type** | New tile type for in-field NPC dialogue triggers. [Ground §5.1] |

---

## 11. Ship builder, galaxy map, trading, station hub

Visual-overhaul-only Tier 2 docs. Terminology shorter; not identity-scoped.

### Ship builder

| Term | Definition |
|---|---|
| **Hangar environments** | 4 procedural backdrops (standard / industrial / military / outlaw). [Builder §4.1] |
| **Preview Orbit** | SceneCamera state for builder preview — cycles 3 canonical angles (front, profile, three-quarter) with smooth tween. [Builder §4.2] |
| **Test Flight** | 20-second scripted sim sequence. Reuses combat camera + arena-entry + projectiles. [Builder §4.7] |
| **Hull Pixel Mode** | Existing per-pixel customization. Overhaul: pixels store band-index, not RGB. [Builder §4.8] |
| **Equip Mode** | Existing mode for installing weapons/shields into module slots. |
| **AURELIA:1 build codes** | Existing base64 build-sharing format. Security-hardened import validation. |

### Galaxy map

| Term | Definition |
|---|---|
| **Jump Cinematic** | 4-phase scripted sequence: Charge (1.0s) → Flash (0.15s) → Streak (1.2s) → Arrival (0.5s). Configurable speed (Full/Fast/Minimal/Instant). [Galaxy §4.1] |
| **Zoom Tiers** | Close (3.5x) / Default (2.4x) / Regional (1.2x) / Galactic (0.5x). [Galaxy §4.2] |
| **Faction Dominion Overlay** | Voronoi-based territory tinting at regional + galactic zoom. [Galaxy §4.3] |
| **Nebula regions (5)** | The Silk Drift (violet), The Anvil (orange-red), The Cold Veil (cyan-white), The Quiet Deep (muted), The Scattered Shoals (mixed). [Galaxy §4.4] |
| **Home system** | Designated system marked with house-or-hearth icon; triggers warm approach animation. [Galaxy §4.7] |
| **Multi-hop route** | Persistent multi-system route with intermediate stops + cumulative cost. [Galaxy §4.9] |

### Trading

| Term | Definition |
|---|---|
| **Market Intel Panel** | Headline new UI: cross-system price grid accessible via `I` key. [Trading §4.5] |
| **Sparkline** | 30-40px micro-chart of 7-day price history per commodity. [Trading §4.1] |
| **Volatility pip bar** | 5-segment bar showing rolling-window price volatility. [Trading §4.4] |
| **Supply depth bar** | 10-segment bar showing stock relative to base. |
| **Tier glyphs** | Commodity tier icons: bulk (single chevron) / standard (double) / premium (diamond) / luxury (star) / restricted (padlock) / illegal (skull). [Trading §4.3] |
| **Faction affinity glyphs** | Per-faction commodity markers (Collective cross, Reach crossed-bolts, Union hex, Alliance star, Guild tri). |
| **Permit stamps** | 4-state trade gating: PERMIT / RESTRICTED / ILLEGAL / APPROVED. [Trading §4.6] |
| **Route bonus** | Existing +% rate for returning to visited systems. |
| **Player impact modifier** | ±X% inline when player's trades moved local prices. |

### Station hub

| Term | Definition |
|---|---|
| **Guild Deck / Union Blueprint / Collective Radial / Frontier Freeform / Reach Minimal** | 5 existing faction-specific layouts. [Hub §1.1] |
| **Painted panorama backdrops** | Procedural 3-layer parallax backdrops per faction layout. [Hub §4.1] |
| **Service availability badges** | Visual states for locked / unavailable / requires-rep / quest-required / time-locked services. [Hub §4.2] |
| **Ambient NPCs** | 3-10 visible non-interactive NPC sprites per faction layout. [Hub §4.3] |
| **Visit-state treatment** | First-visit vs recurring-visit atmospheric differentiation. [Hub §4.5] |
| **Persistent faction heraldry** | 40% opacity insignia + 30% tagline in header after entrance animation. [Hub §4.8] |
| **Neon-district overlay** | Contextual scene overlay for specific cyberpunk-coded stations. [Hub §4.9] |
| **Docking / undocking cinematics** | 1.5-2.0s arrival + departure transitions. [Hub §4.10] |

---

## 12. VFX, audio, UI primitives

### Particle presets

Existing (implemented) and proposed (v1 additions). [VFX §3]

**Existing:** `CLICK_HIT`, `SPARK_BURST`, `COLLECT_SPARKLE`, `HEAL_SPARKLE`, `STAR_TWINKLE`, `MINING_DUST`, `DRONE_SPARK`, `LASER_HIT`, `MISSILE_EXPLOSION`, `SHIELD_IMPACT`, `WARP_TRAIL`, `EXPLOSION_FRAGMENT`, `DESTRUCTION_SECONDARY`, `SCAN_PULSE`, `QUALITY_BURST_GOOD`, `QUALITY_BURST_EXCELLENT`, `AMBIENT_DUST`, `AMBIENT_VAPOR`, `AMBIENT_SPARK`, `AMBIENT_STEAM`.

**Proposed v1:** `CLICK_HIT_RARE`, `CLICK_HIT_LEGENDARY`, `ELEMENT_TRAIL_*` (5 variants), `DUAL_TECH_RESOLVE`, `MODULE_RECOVERY_LIFT`, `JUMP_STREAK`, `JUMP_CHARGE`, `NAMED_ENCOUNTER_INTRO`, `ANOMALY_PRESENCE`, `MASTERY_GOLD_BURST`, `S_GRADE_SHIMMER`.

### Audio

| Term | Definition |
|---|---|
| **9 SFX categories** | combat, mining, salvage, trading, navigation, ui, builder, activity, ground. Each with volume ceiling. [Audio §3.1] |
| **Music tiers** | Foundation (main_theme, galaxy_exploration, station_hub) / Intensity (combat_intense, ground_stealth, frontier_danger) / Resolution (victory_fanfare, defeat_somber) / Intimate (dialogue_intimate, dialogue_neutral, mining_rhythm). [Audio §3.2] |
| **Ambient loops** | ambient_space, ambient_station, ambient_combat, ambient_ground + 5 faction-specific station variants (planned: ambient_station_guild, _union, _collective, _frontier, _reach). [Audio §3.3] |
| **Ducking** | Music → 40% under dialogue; music → 60% on critical SFX; ambient → 70% under music. [Audio §4.3] |

### UI components

| Term | Definition |
|---|---|
| **Font tiers** | FONT_HEADING (32pt) / FONT_LG (22pt) / FONT_MD (16pt) / FONT_SM (12pt) / FONT_TINY (9pt). [UI §3.1] |
| **9-slice panel** | Pixel-art border renderer with alpha cache. Primary panel type. [UI §5.1] |
| **Card anatomy** | Universal card structure: sprite + title + badges + content + stat chips + accent stripe. [UI §5.2] |
| **Overlay types** | Dialogue / Confirmation / Cinematic / Notification. [UI §8.1] |
| **Badge / glyph / stamp** | Three small-marker types (status / category / state). ~40 distinct across Tier 2 docs. [UI §7] |

---

## 13. Palette and material canon

Balanced palette (Spike 03 decision). 58 total entries: ~29 material band entries + ~29 role entries.

### Material bands (7)

| Band name | Purpose |
|---|---|
| `steel` | Default hull metal (5 entries: shadow_deep → specular) |
| `solari_chrome` | Talon/chrome material — forced-wide luminance spread |
| `reach_crimson` | Crimson Reach hull — specular hue-shifts warm |
| `union_ceramic` | Miners Union heat-tile |
| `frontier_canvas` | Welded patchwork |
| `collective_composite` | Clean sterile blue-white |
| `glass_viewport` | Cockpit glass (narrow 4-entry band) |

### Role palette (select entries)

| Category | Roles |
|---|---|
| **Void / sky** | void_deep, void_mid, void_light |
| **Emissive cores** | plasma_core, plasma_hot, cryo_fractal, ion_arc, voltaic_strike, glow_warm, glow_cool |
| **UI chrome** | hud_cyan, hud_warning, hud_critical, hud_muted, hud_text, hud_text_dim, hud_accent_warm |
| **Details** | rivet, rivet_gloss, seam, weld |

### Material library (10)

brushed_steel, solari_chrome, crimson_iron, union_ceramic, frontier_canvas, collective_composite, glass_viewport, plasma_energy (emissive), cryo_fractal (emissive), ion_field (emissive).

### Reserved band-name slots (per Framework §15)

For future category expansion: `sensor_glass`, `electronics_emissive`, `cooling_vent`, `radar_mesh`, `shield_field`, `voltaic_plate`, `cryo_frost`.

---

## 14. Content authoring constraints

### Banned NPC names

Do not use (AI-overused per MEMORY.md): **Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose**.

### GenAI tells to avoid

- **Em-dashes (—)** — banned outright
- **"No X, no Y" constructions** — banned
- **"A testament to"** — banned
- **"Couldn't help but"** — banned
- **Melodramatic stacking** (everything is "devastating" / "haunting" / "profound") — banned
- **Overly elaborate metaphors that don't serve the moment** — avoid

### Voice pivot constraints

Each identity pivots from warm-industrial but within limits. [Bible §10.4]

- **Prospector** — union-solidarity, not political propaganda
- **Salvager** — haunted-working, not gothic horror or Lovecraftian dread
- **Fabricator** — craft-precision, not sterile corporate-pristine
- **Captain** — cinematic weight, not space-opera melodrama
- **Merchant** — data-dense brutalism, not cyberpunk-neon or hedge-fund-finance

### Cross-identity acknowledgment discipline [Bible §10.3]

~30-40 lines total across corpus. Each cross-reference is 1-3 lines. Acknowledges player's accumulated identity without gating content. Examples:

- Augustyn mentions old salvage wrecks he worked decades ago
- Mattsen notes Fabricator peers requesting specific salvage types
- Fabricator correspondence references deep-seam ingredients as Prospector work
- Combat NPCs occasionally comment on player reputation ("Heard about that Signal Ship work")

---

*Revision history:*
- *v1 — initial glossary consolidated from 17-doc corpus. ~120 distinct terms cataloged across 14 categories.*
