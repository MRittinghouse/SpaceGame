# Code-Touch Map

> **Status:** v1 — consolidated matrix of which Tier 2/3 phases modify which production files. Written pre-implementation as an onboarding aid, coordination tool, and estimation reference. Expected to be revised after Combat C1 ships (real implementation reveals accuracy of claims).
>
> Each Tier 2/3 doc has its own "Dependencies — on production code" section; this document consolidates and cross-references them to reveal **overlap hotspots** where multiple phases touch the same files.

---

## Table of Contents

1. How to use this document
2. Overlap hotspots (shared files touched by multiple phases)
3. Per-phase file touches
4. New files created by phase
5. Data file modifications
6. Coordination protocol

---

## 1. How to use this document

### 1.1 Before starting a phase

1. Find the phase in §3
2. List the files it modifies
3. Cross-check §2 — does this phase touch any hotspot files?
4. If yes, check which other phases also touch those files — coordinate order/merging

### 1.2 When agent-onboarding for a phase

Read §3 for your phase first. Read the referenced Tier 2 doc for intent. Read §2 for overlap awareness.

### 1.3 When estimating scope

§3 entries are annotated with rough size: **RB** (rebuild), **HX** (heavy extension), **LX** (light extension), **N** (new file).

### 1.4 Accuracy caveat

This document is written **pre-implementation**. Some file references are aspirational (the file exists in the Tier 2 doc's reference but implementation may find different files to modify). Expect ~20% of references to be adjusted after Combat Phase C1 completes.

---

## 2. Overlap hotspots

Files touched by three or more phases. These are the coordination-critical files.

### 2.1 `spacegame/engine/ship_composite.py` — 5 consumers

| Phase | Nature of change |
|---|---|
| **Framework §2 rebuild (foundation)** | RB — full rebuild per `10_programmatic_generation_framework.md §2`. Must support all downstream consumers. |
| Combat C4 | HX — integrate enemy ships into unified pipeline |
| Builder B1 | HX — large preview pane rendering (multi-angle) |
| Builder B5 | HX — test flight rendering |
| Salvage S5 | HX — module recovery visualization (cells render module silhouettes) |
| Station Hub H5 | LX — docked-ship corner glimpse |

**Coordination:** rebuild must ship *before* any downstream consumer. Write `92_ship_composite_api.md` equivalent before rebuild begins (similar to what `91_scene_camera_api.md` does for SceneCamera).

### 2.2 `spacegame/engine/scene_camera.py` — 9 consumers (N)

| Phase | Nature of change |
|---|---|
| **Combat C1 (foundation)** | N — new file per `91_scene_camera_api.md` |
| Builder B1 | LX — register state transitions for preview orbit |
| Builder B5 | LX — register state transitions for test flight |
| Galaxy G1 | LX — zoom tier states + parallax factors |
| Galaxy G2 | LX — scripted jump cinematic state |
| Mining M2 | LX — prestige cinematic state |
| Salvage S5 | LX — module recovery + cycle cinematic states |
| Station Hub H5 | LX — docking/undocking cinematic state |
| Ground GR3 | LX — deployment/extraction/combat focus states |

**Coordination:** scene_camera.py is new; no existing behavior to preserve. Must ship during Combat C1 (foundation). Downstream consumers just register states.

### 2.3 `spacegame/engine/particles.py` — 3+ consumers (shared primitives)

| Phase | Nature of change |
|---|---|
| VFX §3.5 (foundation) | LX — add 11 new presets (`CLICK_HIT_RARE`, `CLICK_HIT_LEGENDARY`, `ELEMENT_TRAIL_*` ×5, `DUAL_TECH_RESOLVE`, `MODULE_RECOVERY_LIFT`, `JUMP_STREAK`, `JUMP_CHARGE`, `NAMED_ENCOUNTER_INTRO`, `ANOMALY_PRESENCE`, `MASTERY_GOLD_BURST`, `S_GRADE_SHIMMER`) |
| Combat C2 | LX — element-specific palette migration (`LASER_HIT` per element) |
| VFX §6.2 audit | HX — palette compliance migration (hand-tuned RGB → role lookups) |
| Mining M2 | LX — consume new tier-weighted presets |
| Salvage S2 | LX — consume new tier-weighted presets |

**Coordination:** preset additions are additive; preset migrations are breaking. Migration should ship during VFX foundation pass, before Tier 2 consumers adopt.

### 2.4 `spacegame/engine/draw_utils.py` — 10+ consumers

| Phase | Nature of change |
|---|---|
| UI Chrome §7.3 (foundation) | HX — add `draw_badge`, `draw_glyph`, `draw_stamp` primitives + glyph sheet loader |
| UI Chrome §5 | LX — extend card anatomy helpers |
| UI Chrome §12.3 audit | HX — color compliance migration (grep `(\d+,\s*\d+,\s*\d+)` tuples → palette role lookups) |
| UI Chrome §12.3 audit | HX — font compliance (grep `pygame.font.Font(` → canonical fonts) |
| Trading T1 | LX — consume badge/glyph/stamp primitives for commodity rows |
| Trading T4 | LX — consume stamp primitives for permits |
| Station Hub H1 | LX — consume badge primitives for service availability |
| Mining M2 | LX — consume badge primitives for mastery tiers |
| Salvage S3 | LX — consume badge primitives for broker rep |
| Refining F5 | LX — consume badge primitives for quality grades |
| Ground GR2 | LX — consume badge primitives for afflictions |
| Galaxy G5 | LX — consume glyph primitives for landmarks |

**Coordination:** badge/glyph/stamp primitives land during UI Chrome foundation phase. All Tier 2 phases consume, none modify primitives themselves.

### 2.5 `spacegame/models/player.py` — 7+ consumers (save state)

| Phase | Nature of change |
|---|---|
| Mining M3-M6 | HX — new fields: prospector_standing, claim_ledger entries, thought_cabinet_internalizations, rival_relationships, anomaly_progress, union_reputation, prestige_level |
| Salvage S3-S6 | HX — new fields: wrecker_standing, broker_reps (5), named_wreck_history, collector_wall, wrecker_cycles_completed, thought_cabinet (salvage variant) |
| Refining F3-F5 | HX — new fields: fabricator_standing, exposition_history, commission_log, correspondence_archive, masterwork_registry, rediscovery_progress, thought_cabinet (refining variant) |
| Ground GR2, GR4, GR7 | HX — new fields per-crew: affliction_state, virtue_state, expedition_count, wound_history; global: expedition_log, named_encounters_met, terminal_content_read |
| Galaxy G5 | LX — home_system designation |
| Station Hub H2 | LX — visited_stations metadata (last_visit_day, transactions_summary) |
| Combat C4 | LX — module_damage_state tracking (persistent per ship) |

**Coordination:** per alpha "be bold" stance (`feedback_alpha_no_backcompat.md` in memory), new fields don't need backward-compat scaffolding. Save wipes between version bumps are acceptable. All phases can add fields freely; `to_dict`/`from_dict` updates inline.

### 2.6 `spacegame/data/economy/commodities.json` — 2 consumers

| Phase | Nature of change |
|---|---|
| Trading T1 | LX — add `tier` field (bulk/standard/premium/luxury/restricted/illegal) to each commodity |
| Trading T1 | LX — add `faction_affinity` field (optional; points to faction id) |

### 2.7 `spacegame/data/ships/modules.json` — 2 consumers (indirect)

| Phase | Nature of change |
|---|---|
| Framework §2 rebuild | LX — add rotation + connection-point metadata per module |
| Salvage S5 | LX — salvaged-variant flag support (modules recovered from wrecks) |

### 2.8 `spacegame/config.py` — 5+ consumers

| Phase | Nature of change |
|---|---|
| All Tier 2 phases | LX — new constants as needed (`GROUND_RESOLVE_MAX`, `MINING_PRESTIGE_MAX_V2`, `SALVAGE_CYCLE_THRESHOLDS`, etc.) |

**Coordination:** config.py is a shared dumping ground; keep new constants grouped by system (`# === GROUND EXPLORATION ===`, etc.). No coordination issue; additive.

### 2.9 `spacegame/engine/audio_manager.py` + `data/assets/audio/manifest.json` — foundation + 9 consumers

| Phase | Nature of change |
|---|---|
| **Audio §5 orchestration (foundation)** | HX — wire music/ambient API to game states; 5 new faction-specific ambient variants |
| Audio §6 per-Tier-2 triggers | LX per system — add SFX entries to manifest |
| Combat C2 | LX — element-specific weapon SFX (`combat_hit_plasma`, `combat_hit_ion`, etc.) |
| Mining M2 | LX — tier-weighted click SFX |
| Salvage S2 | LX — tier-weighted extraction SFX |
| Galaxy G2 | LX — 4-phase jump sequence audio |
| Station Hub H2 | LX — faction ambient variants (5 new loops) |
| Refining F5 | LX — gold mastery + quality S-grade SFX |
| Builder B2 | LX — test flight audio sequence |
| Ground GR3 | LX — positional combat audio + resolve threshold ambient |

**Coordination:** foundation orchestration wiring lands first. Per-system SFX additions are additive to manifest.

---

## 3. Per-phase file touches

### 3.1 Foundation phase (must ship before other work)

**Combat C1 — SceneCamera + pacing beats (1 week)**
- `spacegame/engine/scene_camera.py` **(N)** — new per `91_scene_camera_api.md`
- `spacegame/engine/easing.py` **(LX)** — add curves if not present
- `spacegame/views/combat_view.py` **(HX)** — route rendering through camera
- `tests/engine/test_scene_camera.py` **(N)** — unit tests per spec §10

**Framework §2 — ShipComposite rebuild (2-3 weeks)**
- `spacegame/engine/ship_composite.py` **(RB)** — full rebuild
- `spacegame/models/ship_build.py` **(LX)** — rotation/flip as first-class fields
- `data/ships/modules.json` **(LX)** — rotation + connection-point metadata
- `tests/engine/test_ship_composite.py` **(HX)** — test suite for new API
- `tests/visual_refs/` **(N)** — reference renders for visual regression

**Bible §2 palette implementation (1-2 weeks)**
- `spacegame/engine/palettes.py` **(RB)** — band-structured palette
- `spacegame/engine/draw_utils.py` **(LX)** — palette lookup helpers
- `tests/engine/test_palette.py` **(HX)** — compliance test suite

**UI Chrome foundation (1 week)**
- `spacegame/engine/draw_utils.py` **(HX)** — `draw_badge`, `draw_glyph`, `draw_stamp`
- `spacegame/data/assets/ui/glyphs.png` **(N)** — glyph sheet
- `spacegame/data/ui_theme.json` **(N)** — pygame_gui theme config
- `spacegame/engine/fonts.py` **(LX)** — `FONT_TINY` if missing

**Audio §5 orchestration wiring (1 week)**
- `spacegame/engine/audio_manager.py` **(LX)** — scene-to-music mapping API
- `spacegame/engine/game.py` **(LX)** — state-change hooks triggering music/ambient transitions
- `spacegame/data/assets/audio/manifest.json` **(LX)** — 5 faction ambient variants added

### 3.2 Combat (phases C1-C6, ~7-9 weeks total)

Already covered: **C1** in §3.1.

**C2 — VFX element palette integration**
- `spacegame/engine/combat_vfx.py` **(HX)** — element-specific VFX per element
- `spacegame/engine/projectiles.py` **(HX)** — element-driven color
- `spacegame/engine/particles.py` **(LX)** — new element-trail presets
- `spacegame/data/assets/audio/manifest.json` **(LX)** — element-specific weapon SFX

**C3 — Damage tiers + arena entry**
- `spacegame/views/combat_view.py` **(HX)** — tier-selection on damage events, arena entry sequence
- `spacegame/engine/fonts.py` **(LX)** — tier-specific font access
- `spacegame/data/assets/audio/manifest.json` **(LX)** — arena entry cue

**C4 — Unified ship pipeline + module targeting**
- `spacegame/views/combat_view.py` **(HX)** — consume rebuilt ship composite
- `spacegame/engine/ship_module_overlay.py` **(N)** — module highlight/flash/damage/destruction overlay
- `data/ships/enemy_templates.json` **(N)** — enemy-ship-as-composite data

**C5 — Dual tech cinematic**
- `spacegame/engine/dual_tech_cinematic.py` **(N)** — overlay system
- `spacegame/views/combat_view.py` **(LX)** — cinematic trigger integration

**C6 — Background atmospheric detail (optional)**
- `spacegame/engine/combat_vfx.py` **(LX)** — extended CombatAtmosphere per danger

### 3.3 Ship Builder (phases B1-B6, ~6-8 weeks)

**B1 — Hangar + unified preview pipeline**
- `spacegame/views/ship_builder_view.py` **(HX)** — preview pane expansion
- `spacegame/engine/hangar_environment.py` **(N)** — 4 procedural backdrops
- `spacegame/views/shipyard_view.py` **(LX)** — hangar environment consumption

**B2 — Catalog preview + placement ghost**
- `spacegame/views/ship_builder_view.py` **(HX)** — module preview panel, ghost rendering

**B3 — Faction shop chrome**
- `spacegame/views/shipyard_view.py` **(HX)** — faction tinting, insignia
- `spacegame/data/assets/ui/faction_insignia/` **(N)** — 5 hand-authored pixel artworks

**B4 — Hull pixel mode unification + physics overlay palette**
- `spacegame/views/ship_builder_view.py` **(HX)** — pixel mode band-index support
- `spacegame/models/ship_build.py` **(LX)** — pixel data structure update

**B5 — Test flight mode**
- `spacegame/views/ship_builder_view.py` **(LX)** — test flight trigger
- `spacegame/views/test_flight_view.py` **(N)** — scripted sim sequence

**B6 — Confirm animation polish + build sharing UI**
- `spacegame/views/ship_builder_view.py` **(LX)** — confirm flourish
- `spacegame/views/build_share_view.py` **(N)** — dedicated share/import overlay

### 3.4 Mining (phases M1-M7)

**M1 — Balance discipline formalization**
- `spacegame/models/mining_session.py` **(LX)** — 3-tier currency enforcement
- `tests/models/test_mining_balance.py` **(N)** — anti-cheese test suite

**M2 — Visual overhaul baseline**
- `spacegame/views/mining_view.py` **(HX)** — click tier weighting, visible drones, prestige cinematic
- `spacegame/engine/mining_vfx.py` **(HX)** — tier-weighted VFX, drone sprites
- `spacegame/data/assets/sprites/drones/` **(N)** — 3 drone sprite variants
- `spacegame/engine/skill_voice_overlay.py` **(N)** — shared skill voice UI

**M3 — Prospector's Road Ch1-2 + core NPCs**
- `spacegame/views/claim_ledger_view.py` **(N)** — new view
- `spacegame/views/union_hall_view.py` **(N)** — new view
- `spacegame/data/mining/campaign/chapter_01.json` **(N)**
- `spacegame/data/mining/campaign/chapter_02.json` **(N)**
- `spacegame/data/mining/npcs.json` **(N)** — Augustyn, Marta
- `spacegame/data/assets/sprites/portraits/mining/` **(N)** — 2 portraits (Auggie, Marta)
- `spacegame/data/mining/skill_voices.json` **(N)** — skill voice content
- `spacegame/models/player.py` **(LX)** — prospector_standing, claim_ledger fields

**M4 — Ch3-5 + rivals**
- `spacegame/data/mining/campaign/chapter_03-05.json` **(N)** ×3
- `spacegame/data/mining/rivals.json` **(N)** — 5 named rivals
- `spacegame/data/mining/legendary_seams.json` **(N)** — 3 of 6
- `spacegame/data/assets/sprites/portraits/mining/` **(N)** — 6 portraits (Itzal, Cesarine, 4 rivals)

**M5 — Ch6 + anomalies + remaining content**
- `spacegame/data/mining/campaign/chapter_06.json` **(N)**
- `spacegame/data/mining/anomalies.json` **(N)**
- `spacegame/data/mining/legendary_seams.json` **(HX)** — 3 more
- `spacegame/data/mining/deep_core_dives.json` **(N)**

**M6 — World-contextual entry + polish**
- `spacegame/views/mining_view.py` **(LX)** — entry transition

**M7 — Ongoing content expansion**

### 3.5 Galaxy Map (phases G1-G5, ~9-11 weeks)

**G1 — Zoom + pan**
- `spacegame/views/galaxy_map_view.py` **(HX)** — camera integration, zoom tiers

**G2 — Jump cinematic**
- `spacegame/views/galaxy_map_view.py` **(HX)** — scripted sequence
- `spacegame/engine/backgrounds.py` **(LX)** — streak effect

**G3 — Responsive starfield + nebula**
- `spacegame/engine/backgrounds.py` **(HX)** — multi-layer parallax + nebula regions
- `spacegame/data/galaxy/systems.json` **(LX)** — nebula region metadata

**G4 — Dominion overlay + living galaxy**
- `spacegame/models/politics.py` **(LX)** — territory data extension
- `spacegame/views/galaxy_map_view.py` **(LX)** — Voronoi dominion rendering

**G5 — Landmarks + approach + info panel polish**
- `spacegame/views/galaxy_map_view.py` **(HX)** — landmark rendering, approach animations

### 3.6 Trading (phases T1-T5, ~9-11 weeks)

**T1 — Commodity rows + sparklines + glyphs**
- `spacegame/views/trading_view.py` **(HX)** — richer row rendering
- `spacegame/data/economy/commodities.json` **(LX)** — tier + faction_affinity metadata

**T2 — Ticker + multi-event slot**
- `spacegame/views/trading_view.py` **(LX)** — ticker integration
- `spacegame/models/news_ticker.py` **(LX)** — station-hub-specific filter

**T3 — Market Intel Panel**
- `spacegame/views/market_intel_panel.py` **(N)** — new UI
- `spacegame/models/player.py` **(LX)** — visited-systems price history access

**T4 — Permit stamps + quantity polish**
- `spacegame/views/trading_view.py` **(LX)** — stamp rendering, quantity widget

**T5 — Smuggling layer chrome**
- `spacegame/views/trading_view.py` **(LX)** — hidden-hold visual treatment

### 3.7 Station Hub (phases H1-H6, ~12-15 weeks)

**H1 — Service badges + descriptor + heraldry**
- `spacegame/views/station_hub_view.py` **(HX)** — badge rendering, descriptor expansion, heraldry
- `spacegame/data/assets/ui/faction_insignia/` **(shared with B3)**

**H2 — Ticker + visit-state**
- `spacegame/views/station_hub_view.py` **(HX)** — ticker integration, visit-state rendering
- `spacegame/data/station_chatter/` **(LX)** — 150 new chatter lines per faction

**H3 — Painted panoramas**
- `spacegame/engine/hangar_environment.py` **(HX)** — 5 faction variants extended

**H4 — Ambient NPCs**
- `spacegame/engine/station_layouts.py` **(HX)** — NPC staging per layout
- `spacegame/data/assets/sprites/station_npcs/` **(N)** — ~15-25 NPC sprites

**H5 — Docked-ship glimpse + docking cinematic**
- `spacegame/views/station_hub_view.py` **(LX)** — corner panel integration
- `spacegame/views/docking_cinematic_view.py` **(N)** — scripted sequence

**H6 — Neon-district overlay (optional)**
- `spacegame/engine/scene_overlays.py` **(LX)** — neon variant

### 3.8 Salvage (phases S1-S7, ~17-22 weeks)

**S1 — Balance + derelict-type binding**
- `spacegame/models/salvage_session.py` **(LX)** — 3-tier currency
- `spacegame/data/economy/salvage_configs.json` **(LX)** — derelict-type binding per system

**S2 — Visual overhaul baseline**
- `spacegame/views/salvage_view.py` **(HX)** — tier VFX, persistent fragment log
- `spacegame/engine/salvage_vfx.py` **(HX)** — wreck-specific atmosphere

**S3 — Wrecker's Log + Mattsen + Ch1**
- `spacegame/views/wreckers_log_view.py` **(N)**
- `spacegame/data/salvage/campaign/chapter_01.json` **(N)**
- `spacegame/data/salvage/brokers.json` **(N)** — Mattsen
- `spacegame/data/assets/sprites/portraits/salvage/` **(N)** — Mattsen

**S4 — Ch2-3 + broker expansion + named wrecks**
- `spacegame/data/salvage/campaign/chapter_02-03.json` **(N)** ×2
- `spacegame/data/salvage/named_wrecks.json` **(N)** — 3 of 6
- `spacegame/data/salvage/brokers.json` **(HX)** — Erika, Third Shift
- `spacegame/data/assets/sprites/portraits/salvage/` **(HX)** — Erika portrait

**S5 — Ch4 + module recovery + Cesarine**
- `spacegame/data/salvage/campaign/chapter_04.json` **(N)**
- `spacegame/views/module_recovery_cinematic.py` **(N)**
- `spacegame/data/salvage/brokers.json` **(HX)** — Cesarine Marrot
- `spacegame/models/module_inventory.py` **(LX)** — salvaged-variant support

**S6 — Ch5-6 + cycles + collector's wall**
- `spacegame/data/salvage/campaign/chapter_05-06.json` **(N)** ×2
- `spacegame/data/salvage/brokers.json` **(HX)** — Pell Bray
- `spacegame/views/wreckers_log_view.py` **(HX)** — Collector's Wall section

**S7 — Ongoing content**

### 3.9 Refining (phases F1-F6, ~10-13 weeks)

**F1 — Balance + quality variance foundation**
- `spacegame/models/refining_session.py` **(LX)** — 3-tier currency, quality variance
- `spacegame/data/economy/recipes.json` **(LX)** — quality variance data

**F2 — Visual overhaul baseline**
- `spacegame/views/refining_view.py` **(HX)** — extended gold mastery, quality VFX, queue animation
- `spacegame/engine/refining_vfx.py` **(HX)** — new VFX preset usage

**F3 — Fabricator's Register + correspondence**
- `spacegame/views/fabricators_register_view.py` **(N)**
- `spacegame/data/refining/correspondence/` **(N)** — peer letters

**F4 — Seasonal events**
- `spacegame/models/seasonal_events.py` **(N)**
- `spacegame/data/refining/expositions.json` **(N)**
- `spacegame/data/refining/commissions.json` **(N)** — named clients + scenarios
- `spacegame/data/refining/rediscoveries.json` **(N)**
- `spacegame/data/assets/sprites/portraits/refining/` **(N)** — 6 peer portraits

**F5 — Skill voices + Masterwork Registry**
- `spacegame/data/refining/skill_voices.json` **(N)**
- `spacegame/views/fabricators_register_view.py` **(HX)** — Masterwork section

**F6 — Fabricator dockside (optional) + polish**
- `spacegame/engine/hangar_environment.py` **(LX)** — Fabricator dockside variant (if pursued)

### 3.10 Ground Exploration (phases GR1-GR7, ~15-20 weeks)

**GR1 — Party + formation**
- `spacegame/models/ground.py` **(HX)** — party state, formation
- `spacegame/models/ground_combat.py` **(HX)** — party dice pool, positional bonuses
- `spacegame/views/ground_exploration_view.py` **(HX)** — party rendering
- `spacegame/data/assets/sprites/ground/crew/` **(N)** — crew sprites

**GR2 — Expedition Resolve + afflictions**
- `spacegame/models/ground.py` **(LX)** — resolve meter
- `spacegame/models/ground_crew.py` **(HX)** — affliction / virtue tracking
- `spacegame/views/station_hub_view.py` **(LX)** — Cantina crew recovery panel (cross-doc)

**GR3 — Visual overhaul**
- `spacegame/views/ground_exploration_view.py` **(HX)** — lighting, ambient effects, sprite upgrades
- `spacegame/engine/ground_vfx.py` **(N)** — biome-specific ambient

**GR4 — NPC encounters + dialogue**
- `spacegame/models/ground.py` **(LX)** — `NPC_ENCOUNTER` tile type
- `spacegame/data/ground/campaign/*.json` **(HX)** — existing 5 maps extended with NPCs
- `spacegame/data/ground/encounters.json` **(N)** — procedural templates

**GR5 — Named encounters + expedition voice + terminals**
- `spacegame/data/ground/named_encounters.json` **(N)** — 5 named NPCs
- `spacegame/data/ground/expedition_voice.json` **(N)** — 3 voice libraries
- `spacegame/data/ground/terminals.json` **(N)** — 40+ terminal entries

**GR6 — Equipment + retreat**
- `spacegame/data/ground/equipment.json` **(HX)** — 8-12 new items
- `spacegame/models/ground_combat.py` **(LX)** — tactical retreat variants

**GR7 — Expedition Log + polish**
- `spacegame/views/expedition_log_view.py` **(N)**

---

## 4. New files created by phase

Count of completely new files by phase type:

| Phase category | New files | Primary types |
|---|---|---|
| Foundation (C1, F§2, Bible §2, UI foundation, Audio) | ~8 | engine/ + tests/ + data/assets/ui/ |
| Combat (C1-C6) | ~4 | views + engine + data |
| Ship Builder (B1-B6) | ~6 | views + engine + assets |
| Mining (M1-M7) | ~25 | data/mining/ content + views + assets |
| Galaxy (G1-G5) | ~0 (mostly extensions) | — |
| Trading (T1-T5) | ~1 | views |
| Station Hub (H1-H6) | ~3 | views + assets |
| Salvage (S1-S7) | ~25 | data/salvage/ content + views + assets |
| Refining (F1-F6) | ~15 | data/refining/ + views + assets |
| Ground (GR1-GR7) | ~10 | data/ground/ + views + assets |
| **Total** | **~97 new files** | |

**Data files dominate** (~70% of new files are JSON content). Python file count is manageable (~30 new Python files across all phases).

---

## 5. Data file modifications

New data directories created:

```
spacegame/data/
  mining/
    campaign/        # Chapters 1-6
    npcs.json        # Augustyn, Marta, etc.
    rivals.json
    legendary_seams.json
    anomalies.json
    deep_core_dives.json
    skill_voices.json
  salvage/
    campaign/        # Chapters 1-6
    brokers.json
    named_wrecks.json
    skill_voices.json
  refining/
    correspondence/  # Peer letters
    expositions.json
    commissions.json
    rediscoveries.json
    skill_voices.json
  ground/
    named_encounters.json
    expedition_voice.json
    terminals.json
    encounters.json  # procedural templates
  assets/
    sprites/
      portraits/
        mining/      # Auggie, Marta, Itzal, Cesarine, rivals
        salvage/     # Mattsen, Erika, Cesarine, Pell (Third Shift = none)
        refining/    # 6 peers
      ground/
        crew/        # 24-32px crew sprites
      station_npcs/  # 15-25 ambient NPC sprites
      drones/        # Mining drone variants
    ui/
      glyphs.png     # Shared glyph sheet
      faction_insignia/
```

Existing data files extended (LX):
- `data/economy/commodities.json` — tier + faction_affinity
- `data/economy/salvage_configs.json` — derelict-type binding
- `data/economy/recipes.json` — quality variance
- `data/ships/modules.json` — rotation + connection points
- `data/galaxy/systems.json` — nebula region metadata + home system support
- `data/ground/campaign/*.json` — NPC encounter additions
- `data/ground/equipment.json` — new items
- `data/assets/audio/manifest.json` — new SFX + ambient entries
- `data/station_chatter/` — visit-state + faction-specific additions

---

## 6. Coordination protocol

### 6.1 Overlap resolution

When two phases want to modify the same file:

1. **Check §2 hotspots** — does the file appear there?
2. **If yes**: phases coordinate. The earlier phase ships first; the later phase branches from the updated file.
3. **If no**: check whether changes are orthogonal (different sections of the same file). If orthogonal, parallel development is safe. If overlapping, coordinate.

### 6.2 Shared primitive API stability

Shared primitives (SceneCamera, ShipComposite, particles, draw_utils badges) ship during foundation phase with stable APIs. Subsequent Tier 2 phases **consume** the APIs; they do not **modify** them. If a Tier 2 phase needs an API change, it's a foundation revision (goes back to foundation phase discipline, not as a Tier 2 add-on).

### 6.3 New-file authoring

New files created during a phase follow existing codebase conventions:
- Python: snake_case filename, MyPy-strict typing, docstrings per Google style
- JSON: snake_case keys, `id` + `name` fields standard, see `CLAUDE.md` §Data Conventions
- Assets: hand-authored pixel art per framework §11.5 boundary (procedural attempts for small sprites like ambient NPCs)

### 6.4 Cross-system integration points

Integration points identified in coherence review §3:

- **Combat → Salvage bridge** (Ground §7.4 Hostile Recoveries) — coordinate Combat Phase C4/C5 with Salvage Phase S5
- **Mining ↔ Salvage** — abandoned mining operations appear as salvage Named Wrecks; coordinate Mining M4 and Salvage S4 content
- **Refining ↔ Mining/Salvage** — correspondence references ingredient origins; coordinate content authoring across three agents
- **Station Hub crew recovery panel** (Ground §7.4) — Station Hub Phase H1/H2 integrates with Ground Phase GR2

These coordination points are called out in the referenced sections of each Tier 2 doc.

### 6.5 Audit pass timing

Audit tasks (UI Chrome §12.3) run opportunistically during foundation phase:

- **Font audit** — during UI Chrome foundation
- **Color audit** — during UI Chrome foundation + palette implementation
- **VFX palette audit** — during VFX foundation
- **Banned-name / GenAI-trope scan** — during each content authoring batch (not a one-time audit; ongoing discipline)

---

## 7. Post-implementation update process

This document is **living**. After each phase ships, update:

- §3 to reflect actual files touched (vs aspirational)
- §2 hotspots if new overlaps surface
- §5 data directory tree as new content lands

Next update scheduled: **after Combat Phase C1 completes.** Real implementation reveals accuracy; update from experience.

---

*Revision history:*
- *v1 — pre-implementation consolidation. ~97 new files tracked, 9 overlap hotspots identified, coordination protocol established.*
- *v1.1 — Combat C1 complete. Actual files touched matched the pre-implementation prediction: `spacegame/engine/scene_camera.py` (N), `tests/test_engine/test_scene_camera.py` (N), `spacegame/views/combat_view.py` (HX — added SceneCamera integration, ArenaCameraState enum, _enter_camera_state helper, migrated 3 shake triggers, split render UI/arena offsets). easing.py required no changes (all curves present). screen_effects.py left alone (still used by game.py globally). Test regression: 1 combat_view test updated to reflect shake migration. Full suite: 6,084 passing, 3 skipped.*
