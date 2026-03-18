# Implementation Roadmap

## Document Overview

This roadmap tracks the implementation status of SpaceGame, organized into completed work and future phases. Each future phase builds on the previous, expanding from the current core trading game into RPG/campaign systems.

**Last Updated**: 2026-03-16

---

## Current Status

**Phases 1-6 are COMPLETE.** The game is feature-complete through Act One with full visual overhaul, sprites, animations, and UI chrome. The Refinement Roadmap (`requirements/16_refinement_roadmap.md`) is now the active development document — it tracks the work to transform Act One from a linear narrative demo into a living, replayable universe with strategic depth. Act Two, Act Three, and Fleet Management remain future work (Phase 7).

The project has 3,680 tests across 34 views. See the refinement roadmap for current cycle status.

> **Note**: This document is now a historical record of Phases 1-6. For active development tracking, see `requirements/16_refinement_roadmap.md`.

### What's Built

**Galaxy & World**
- 10 star systems across multiple quadrants with distinct economies
- 19 tradeable commodities across basic, industrial, and luxury categories
- Dynamic pricing with supply/demand tags and market events (shortage, surplus, disaster, boom)
- Danger levels (safe, moderate, dangerous) per system
- Turn-based travel with fuel costs based on distance
- Random encounters during travel (7 types: hostile, distress signal, shakedown, derelict, merchant, debris, anomaly)

**Gameplay Systems**
- Full buy/sell trading at stations with BUY MAX / SELL MAX buttons and dynamic activity buttons
- Mining mini-game (6x4 asteroid grid, 4 rock types, click-to-mine with passive drill and 3-tier drone automation)
- Salvaging puzzle (5x5 grid scanning, 3 item types, charge-based extraction)
- Refining system (6 recipes, job queue with up to 5 concurrent jobs, real-time processing)
- Ship purchase and comparison at the shipyard
- Turn-based space combat (player moves, crew phase, enemy phase, flee/negotiate/bribe options)
- Data-driven encounter system with EncounterView for non-hostile encounters
- Advanced trading: price history, supply/demand dynamics, trade route tracking, trade contracts
- Smuggling & contraband: black markets, hidden compartments, customs inspections, bounty hunters, smuggling contracts, criminal heat system

**Combat**
- 28 enemy ship templates across 5 archetypes with 4 AI behaviors (aggressive, defensive, cowardly, evasive)
- Faction-themed enemies filtered by system faction and danger level
- 5 weapon upgrades + 5 defense upgrades with combat moves
- 4 crew combat abilities (evasion, repair, analyze, accuracy)
- Flee (speed-based), negotiate (social skill), bribe (credits-based) non-combat resolution
- Shakedown encounters in dangerous systems (pay tribute or fight)
- Combat outcome screen with stats, XP rewards, and defeat consequences

**Progression**
- 10-level XP system with cumulative thresholds (0-5200 XP)
- 6 skill trees: Trading Mastery (5), Resource Gathering (5), Mining Mastery (8), Leadership & Operations (5), Social (3), Ground (6) — 32 skills total
- 5 character attributes: Commerce, Acuity, Resolve, Ingenuity, Synergy — point allocation at creation and level-up
- Mining skill tree unlocks 3 drone tiers, click power, passive drill speed, ore targeting
- Skill prerequisites and multi-level skills with stacking bonuses
- 20 ship upgrades (5 standard + 5 combat + 7 weapon + 3 smuggling) with per-category slot limits (weapon, defense, utility)
- 43 achievements across 8 categories with varied rewards (XP, credits, skill points)

**RPG & Social**
- 3 social skills (Persuasion, Intimidation, Observation) with use-based growth
- NPC disposition system (per-NPC relationship 0-100)
- Dialogue skill checks with deterministic resolution and visual feedback
- 4 factions with reputation tiers, tariffs, and rivalry pairs
- Political system: faction-to-faction relationships, political events, intel system, expanded reputation consequences, centralized spillover
- Crew system: 4 recruitable members with passive abilities, leveling, loyalty
- Character creation view with attribute point allocation
- 17 NPCs with dialogue trees, 22 campaign missions across 5 chapters

**Ships**
- 9 ship classes: Shuttle, Light Freighter, Medium Freighter, Fast Courier, Bulk Hauler, Luxury Yacht, Armed Trader, Clipper, Heavy Hauler
- Cargo capacity (50-600), fuel system, speed multipliers, special abilities
- Combat stats: hull, shields, weapon power, evasion, accuracy, speed, energy

**Player Experience**
- Event notification system: modal dialogs for DISASTER events, timed banners for SHORTAGE/SURPLUS/BOOM
- Event indicators on galaxy map (pulsing warning dots) and event details in system info panel
- Active event banners in trading view showing current system's event
- Event log (last 15 events, persisted across saves)
- Statistics view with categorized player stats (Economic, Exploration, Activities, Progression)
- Achievements view with progress bars, locked/unlocked state, and reward info
- 5-step tutorial system with auto-trigger on new game, skip option, and replay from settings
- Journal system for tracking story events and world lore

**Ground Exploration** (Phases A-F complete)
- Turn-based, stealth-first, grid-based exploration system (GroundExplorationView ~1700 lines)
- 13 tile types: floor, wall, door (open/closed), entrance, exit, noisy floor, cover, hazard, interactable, dark floor, hidden passage
- Fog of war with 3 states (hidden, explored, visible), line-of-sight vision with wall blocking
- Enemy patrols with facing, vision cones, 4 detection states (UNDETECTED → SUSPICIOUS → ALERT → COMBAT)
- Noise system: noisy floor tiles, door opening noise, alert radius propagation
- Ground combat: 1d6+modifier exchanges, fight/retreat/talk actions, social skill integration for talk
- Crew ground abilities: Elena (+1 vision), Marcus (bypass locked doors), Priya (analyze weakness +3 attack), Tomas (reveal patrol routes)
- Attribute integration: ACU → vision, RES → defense, COM → loot bonus, SYN → talk bonus
- Procedural map generation: 8 chunk templates with interior features, 4 difficulty tiers, 5 mission types, faction-specific enemy pools
- Deterministic seeding for reproducible maps, chunk stamping with tactical variety (barriers, shelving, pillars, crates)
- Loot system: per-enemy credit drops scaled by difficulty and COM attribute

**Infrastructure**
- Save/Load system with 12 slots (slot 0 = autosave), JSON format with version field
- Save metadata (timestamp, credits, location, playtime)
- 34 views: main menu, galaxy map, trading, mining, salvage, refining, skill tree, shipyard, save/load, settings, pause menu, startup, statistics, achievements, event notification, dialogue, mission log, crew roster, name input, character creation, character, combat, encounter, journal, ground exploration, ground briefing, ground results, station hub, repair bay, investment, and more
- Particle system (object-pooled, 14+ presets including combat effects), screen transitions (fade, warp, slide)
- Animated parallax backgrounds with procedural generation
- Screen effects (vignette, screen shake)
- 16-bit pixel art sprite system: SpriteManager, palette system, pixel pipeline, sprites for ships (player + enemy), NPC portraits, commodities, faction emblems, upgrade icons, ground tiles
- Comprehensive test suite (2948 tests) covering all models, views, data loading, combat, encounters, social, attributes, achievements, tutorial, events, drones, mining, factions, dialogue, missions, crew, campaign, trading, ground exploration, smuggling, politics, investment, sprites, and palettes

### Implementation Notes

Several systems were simplified or expanded from original spec during implementation:
- **Skill trees**: 5 trees with 26 skills (Trading 5, Gathering 5, Mining 8, Leadership 5, Social 3). The original spec proposed 3 trees with 15 skills — Mining tree was added with 8 skills for drone/click mechanics, Leadership tree added after crew and faction systems were built, Social tree added for speech system integration.
- **Levels**: 10-level cap (original spec proposed 20). The current curve provides meaningful progression with multiple XP sources.
- **Upgrades**: 20 upgrades (6 utility + 7 weapon + 5 defense + 3 smuggling) with per-category slot limits (weapon, defense, utility). Smuggling upgrades require black market access. Expanded from original 5 flat-bonus upgrades as combat and smuggling systems were added.
- **Ship purchase**: Integrated into shipyard view rather than a separate dealership view.
- **Market events**: Fully implemented with tiered notifications (modal for DISASTER, banner for others), galaxy map indicators, trading view banners, and persistent event log.
- **Combat**: Turn-based RPG combat with 13 enemy templates, 4 AI behaviors, flee/negotiate/bribe resolution. Full CombatView with animation queue and particle effects.
- **Advanced trading**: PriceHistory, supply/demand dynamics, trade routes with efficiency bonuses, and time-limited trade contracts — partially implemented from the original Phase 4 Advanced Trading spec.
- **Encounters**: 7 encounter types with data-driven definitions. Hostile → CombatView, non-hostile → EncounterView with choices and rewards.
- **Character attributes**: 5 sci-fi attributes with point allocation at creation and level-up milestones. Attributes provide passive bonuses and enhance social skill checks.

---

## Phase 1 (Completed): Polish & Player Experience

**Goal**: Surface existing systems better, add engagement tracking, and onboard new players
**Status**: COMPLETE — all 3 cycles implemented

---

### Cycle 1.1: Event Display & UX Polish

**Status**: IMPLEMENTED
**Priority**: P1 — quick win, highest impact-to-effort ratio

The market event system works mechanically (events generate on time advance, affect prices in `models/event.py` and `models/market.py`) but is nearly invisible to the player. This cycle surfaces that existing backend work.

**What to build**:
- Event notification overlay when a new event triggers (modal dialog with event type, affected commodity, price impact, duration)
- Active event banner in trading view showing current system's event (if any)
- Event indicators on galaxy map (icon or color on systems with active events, tooltip on hover)
- Event log accessible from trading or galaxy view (last 10-15 events with timestamps)

**Architecture guidance**:
- Follow the existing overlay pattern — pause menu uses `push_state()`/`pop_state()` for overlays. Event notification can work the same way, or use a simpler approach: a transient modal rendered on top of the current view (similar to the `_show_message()` pattern but larger).
- Event data already flows through `Game` → `Market` → `Player.rest_at_system()` / `Player.travel_to_system()`. The notification hook should be added where `try_generate_market_event()` is called — capture the return value and queue it for display.
- For galaxy map indicators, `GalaxyMapView` already renders system icons with hover detection. Add an event check per system during render (events are stored in Market instances accessible via Game).
- The event log can be a simple `list[dict]` on the Game or Market object, appended when events trigger, serialized in save data.

**Key decisions**:
- Should the event notification pause gameplay (modal) or appear as a banner?
- Should the event log persist across saves?

**Files to modify**: `spacegame/engine/game.py` (notification queue), `spacegame/views/trading_view.py` (active event banner), `spacegame/views/galaxy_map_view.py` (event indicators), `spacegame/save_manager.py` (event log persistence)
**Files to create**: Event notification overlay (could be a simple method in `game.py` or a lightweight overlay view)

**Tests**: Test that events correctly queue for notification, that the event log accumulates and truncates, and that event display state survives save/load.

**Acceptance criteria**:
- Player sees a notification when a market event triggers
- Player can see which systems have active events from the galaxy map
- Trading view shows the current system's active event (if any)
- Event information is clear: what commodity, what price impact, how long it lasts

---

### Cycle 1.2: Statistics & Achievements

**Status**: IMPLEMENTED
**Priority**: P1

Give players explicit goals and a visible record of their progress. The Player model already tracks `career_profit`, `trade_count`, `systems_visited` — this cycle extends that and builds an achievement layer on top.

**What to build**:
- Extend Player stat tracking: add `credits_earned_lifetime`, `credits_spent_lifetime`, `largest_single_profit`, `ore_mined`, `items_salvaged`, `items_refined`, `jumps_traveled`, `fuel_consumed`, `playtime_seconds` (some may already exist)
- Achievement data file defining milestones with thresholds and XP rewards
- AchievementManager that checks conditions when stats change
- Achievement unlock notification (particle burst + overlay message)
- Statistics view accessible from pause menu or main menu (show all tracked stats)
- Achievements view showing all achievements with progress bars for incomplete ones

**Architecture guidance**:
- Create `data/achievements.json` following existing JSON conventions: array of objects with `id` (snake_case), `name` (Title Case), `description`, `stat_key`, `threshold`, `xp_reward`, `category`.
- `AchievementManager` should be a lightweight class owned by `Game`, initialized with achievement data from DataLoader. On stat update, call `check_achievements(player)` — compare each uncompleted achievement's `stat_key` against the player's stat value.
- Stat increment should happen in the model layer (Player methods like `buy_commodity`, `travel_to_system`, etc.) — add stat tracking calls at the point of success, before the return tuple.
- Achievement unlocks should be stored in player save data (`unlocked_achievements: list[str]`). Add to `Player.to_dict()` / `from_dict()`.
- Statistics view and achievements view: create as new BaseView subclasses following the standard lifecycle. Register as `GameState.STATISTICS` and `GameState.ACHIEVEMENTS` (add to config.py enum).
- Achievement notification: use the particle system (`COLLECT_SPARKLE` preset) plus a timed overlay message, similar to the existing `_show_message()` + `_add_feedback()` patterns.

**Key decisions**:
- Should achievements reward XP (feeds into existing leveling) or just be cosmetic recognition?
- Hidden achievements (not visible until unlocked) for surprise milestones?
- How many achievements for launch? (Suggest 15-25 across economic, exploration, mining/salvage, and progression categories)

**Files to create**: `data/achievements.json`, `spacegame/achievement_manager.py`, `spacegame/views/statistics_view.py`, `spacegame/views/achievements_view.py`
**Files to modify**: `spacegame/models/player.py` (extend stat tracking, achievement storage), `spacegame/data_loader.py` (load achievements), `spacegame/engine/game.py` (own AchievementManager, hook notifications), `spacegame/save_manager.py` (serialize achievement state), `spacegame/config.py` (add GameState values), `spacegame/views/pause_menu_view.py` (add Stats/Achievements buttons)

**Tests**: Test stat increments on player actions, achievement threshold detection, achievement persistence through save/load, no duplicate unlocks.

**Acceptance criteria**:
- Player stats update correctly on all major actions (trade, travel, mine, salvage, refine)
- Achievements unlock with visible notification when thresholds are met
- Statistics screen shows all tracked stats clearly
- Achievements screen shows locked/unlocked state with progress
- Achievement state persists across save/load

---

### Cycle 1.3: Tutorial System

**Status**: IMPLEMENTED
**Priority**: P2

Guide new players through the core game loop. By this point, events are visible and achievements provide goals — the tutorial can reference both.

**What to build**:
- Hybrid tutorial: first-time modal walkthrough (5 steps) + persistent contextual hints for advanced features
- Tutorial steps: (1) Welcome/premise, (2) Trading basics (buy low/sell high), (3) Galaxy map and travel, (4) Mining/resource gathering overview, (5) Goals and next steps (point to achievements)
- TutorialManager tracks progress, persisted in save data
- Tutorial overlay with highlight system (dim everything except the target UI area)
- "Skip Tutorial" option, "Replay Tutorial" in settings

**Architecture guidance**:
- `TutorialManager` is a simple state machine: tracks `current_step: int`, `completed: bool`, `hints_dismissed: set[str]`. Owned by `Game`, serialized in save data.
- Tutorial overlay should be a lightweight view or overlay that renders on top of the current view. It needs: semi-transparent background, dialog box with text, highlight cutout for target UI area, Next/Skip buttons.
- Step triggers: each step activates when the player enters the relevant view for the first time. Use `on_enter()` hooks in views to check `tutorial_manager.should_show_step(step_id)`.
- Contextual hints: small tooltip-style messages that appear on first interaction with advanced features (refining, skill trees, shipyard). Track dismissal in TutorialManager.
- The highlight system can use a full-screen semi-transparent Surface with a cleared rectangle over the target area (similar to vignette rendering approach).

**Key decisions**:
- Should the tutorial be mandatory on first play or opt-in from main menu?
- Tutorial reward (e.g., 1,000 bonus credits) to incentivize completion?
- Should the tutorial pause the game or be dismissible?

**Files to create**: `spacegame/tutorial_manager.py`, `spacegame/views/tutorial_overlay.py`
**Files to modify**: `spacegame/engine/game.py` (own TutorialManager), `spacegame/views/main_menu_view.py` (trigger on new game), `spacegame/save_manager.py` (persist tutorial state), gameplay views (step trigger hooks in `on_enter()`)

**Tests**: Test tutorial state progression, step trigger conditions, persistence through save/load, skip functionality.

**Acceptance criteria**:
- New game triggers tutorial walkthrough
- Each step highlights the relevant UI area and explains the mechanic
- Player can skip at any point
- Tutorial state persists (don't re-show after completion)
- "Replay Tutorial" works from settings

---

## Phase 2 (Completed): RPG Foundation

**Goal**: Add RPG systems that give the game narrative depth and character progression beyond trading
**Status**: COMPLETE — all 4 cycles implemented (Factions, Dialogue/Missions, Crew, Leadership Skill Tree)

---

### Cycle 2.1: Faction Reputation System

**Status**: IMPLEMENTED
**Priority**: P1 within Phase 2

4 factions (Commerce Guild, Miners Union, Science Collective, Frontier Alliance) with 2 rivalry pairs. Systems are randomly assigned to factions on each new game for replayability (balanced 3/3/2/2 distribution across 10 systems). 5 reputation tiers (Hostile → Unfriendly → Neutral → Friendly → Allied) with tariff modifiers affecting buy/sell prices. Trading at a station grants +2 rep with the controlling faction and -1 with their rival. Galaxy map shows faction-colored rings; trading view shows faction name, tier, and floating rep change feedback. Fully persisted in save/load with backward compatibility for old saves.

**Files created**: `data/factions.json`, `spacegame/models/faction.py`, `tests/test_models/test_faction.py` (25 tests)
**Files modified**: `player.py`, `data_loader.py`, `save_manager.py`, `game.py`, `trading_view.py`, `galaxy_map_view.py`, `config.py`, `skill_tree_view.py`, `test_player.py` (+11 tests)

---

### Cycle 2.2: Campaign Framework & Dialogue System

**Status**: IMPLEMENTED (infrastructure complete — dialogue/NPC + mission framework)
**Priority**: P1 within Phase 2

**Dialogue infrastructure**: NPC model (`spacegame/models/dialogue.py`), dialogue tree data structure with branching responses and flag-setting, DialogueManager state machine, DialogueView with portrait placeholders (colored rect + initials), typewriter text reveal, clickable response buttons. 4 placeholder NPCs (Elena Reeves at Nexus Prime, Marcus Jin at Breakstone, Dr. Priya Osei at Axiom Labs, Tomas Drifter at Haven's Rest) with intro conversations. TALK buttons appear in trading view when NPCs are present. Dialogue flags persist through save/load. 31 dialogue tests.

**Mission framework**: Mission, MissionObjective, MissionReward models (`spacegame/models/mission.py`). MissionManager state machine with lifecycle (available → active → completed), 4 objective types (reach_system, talk_to_npc, have_credits, collect_cargo), prerequisite gating, reward application (credits, XP). MissionLogView with tabs (Active/Available/Completed), detail panel with objective checklists and reward display, ACCEPT button. MISSIONS button on galaxy map, pulsing diamond markers on mission target systems. 4 placeholder missions exercising all objective types. Auto-complete on objective fulfillment with blue notification banner. Mission state persists through save/load. 28 mission tests.

**Remaining for future**: Act I story content, story-driven mission offering via NPC dialogue, mission markers in trading view.

Build the infrastructure for story missions and NPC dialogue. Implement Act I (3-4 linear missions) as proof of concept. The campaign integrates with existing trading mechanics — missions have trading objectives (deliver cargo, earn credits, travel to system).

**What to build**:
- Mission data structure (JSON) with objectives, prerequisites, rewards, and dialogue references
- MissionManager class: tracks active mission, completed missions, objective progress, story flags
- Objective types for MVP: `deliver_to_system` (have cargo X at system Y), `earn_credits` (reach N credits), `reach_system` (travel to system), `talk_to_npc` (interact at location)
- Dialogue system: branching text conversations with NPC name, portrait placeholder, dialogue lines, player choices
- Mission log view (active mission with objectives checklist, completed missions list)
- Dialogue view (NPC text display, player choice buttons)
- Mission markers on galaxy map (destination indicators)
- Mission objective checking hooks in gameplay actions

**Architecture guidance**:
- `data/campaign/missions.json`: array of mission objects with `id`, `title`, `act`, `description`, `prerequisites` (list of completed mission IDs), `objectives` (list of objective objects), `rewards` (credits, xp, reputation, unlocks), `dialogue_id`.
- `data/campaign/dialogues.json`: dialogue trees keyed by ID. Each dialogue has `lines` (sequential NPC text) and `choices` (player options that branch or end).
- `MissionManager` owned by `Game`. Checks objective completion on relevant player actions — hook into `Player.travel_to_system()`, `Player.buy_commodity()`, `Player.sell_commodity()`, and a new `interact_at_location()` method.
- `GameState.DIALOGUE` and `GameState.MISSION_BRIEFING` already exist in config.py. DialogueView is a new BaseView that displays dialogue lines with typewriter effect (optional) and choice buttons via pygame_gui.
- MissionLogView: list-based UI showing active mission objectives with checkmarks. Follow the existing list patterns from trading_view.py.
- Story flags: `dict[str, bool]` on MissionManager, serialized in save data. Used for conditional dialogue and mission availability.
- Act I missions (suggested): (1) "A Chance Encounter" — meet Elena at Nexus Prime (dialogue), (2) "First Delivery" — deliver medical supplies to Verdant, (3) "Supply Run" — acquire rare commodity from Breakstone, (4) "The Investigation" — travel to Axiom Labs, discover story hook.

**Key decisions**:
- Should dialogue pause the game world (freeze time) or happen in real-time?
- NPC portraits: placeholder colored rectangles for now, or skip portraits?
- Should missions be tracked in Player model or separately in MissionManager?
- One active mission at a time, or allow a quest log?

**Files to create**: `data/campaign/missions.json`, `data/campaign/dialogues.json`, `spacegame/models/mission.py` (@dataclass: Mission, Objective, DialogueNode), `spacegame/mission_manager.py`, `spacegame/views/mission_log_view.py`, `spacegame/views/dialogue_view.py`
**Files to modify**: `spacegame/engine/game.py` (own MissionManager, objective hooks), `spacegame/models/player.py` (mission state in save data), `spacegame/data_loader.py` (load missions/dialogues), `spacegame/save_manager.py`, `spacegame/views/galaxy_map_view.py` (mission markers), `spacegame/views/trading_view.py` (mission log button, objective triggers)

**Tests**: Test mission state machine (available → active → objectives met → complete), objective detection for each type, prerequisite gating, dialogue tree traversal, save/load of mission progress.

**Acceptance criteria**:
- Player can accept and track a mission with objectives
- Objectives complete automatically when conditions are met
- Dialogue view presents NPC text and player choices
- Completed missions unlock next missions via prerequisites
- Mission progress persists across save/load
- At least 3-4 playable Act I missions

---

### Cycle 2.3: Crew System

**Status**: IMPLEMENTED
**Priority**: P2 within Phase 2

Crew system with 4 recruitable members (one per NPC), passive ability bonuses, leveling, XP, loyalty tracking, and a dedicated crew roster view. Crew are recruited via missions (one per NPC, gated by existing mission prerequisites). CrewRoster follows the MissionManager pattern: immutable templates from JSON + separate runtime state (level/xp/loyalty). Three-layer bonus stacking: progression skills + ship upgrades + crew abilities, all additive.

**Crew members**: Elena Reeves (Navigator — fuel efficiency/fuel bonuses), Marcus Jin (Engineer — cargo/fuel bonuses), Dr. Priya Osei (Scientist — scan charges/extract speed/rare chance), Tomas Drifter (Trader — buy price reduction/sell price bonus). Each has 3 abilities unlocking at levels 1, 3, and 5. Max level 5 with XP thresholds [0, 50, 150, 350, 700].

**Crew XP sources**: +5 per trade, +3 per jump, +20 per mission completion. Loyalty: starts at 50, +1 per trade, +5 per mission, capped 0-100. No gameplay consequences for low loyalty yet (infrastructure for future).

**Ship integration**: Ship properties (max_cargo, max_fuel, effective_fuel_efficiency) include crew bonuses via `get_crew_bonus()` public API. Trading view applies crew buy_price_reduction and sell_price_bonus alongside skill bonuses.

**Galaxy map**: 7 buttons at 36px spacing (added CREW between Missions and Shipyard). CrewRosterView: dual-panel layout (crew list + detail panel with portrait, stats, loyalty bar, abilities with locked/unlocked state, dismiss button).

**Files created**: `spacegame/models/crew.py`, `spacegame/views/crew_roster_view.py`, `data/crew/crew_members.json`, `tests/test_models/test_crew.py` (25 tests)
**Files modified**: `player.py` (crew_state field), `ship.py` (set_crew_roster, get_crew_bonus, property updates), `mission.py` (MissionReward.target_id), `data_loader.py` (crew template loading), `save_manager.py` (crew state persistence), `config.py` (GameState.CREW_ROSTER), `game.py` (crew initialization, XP hooks, mission recruitment, state transitions, save/load), `galaxy_map_view.py` (7-button layout, CREW button), `trading_view.py` (crew bonus in price calculations), `data/missions/missions.json` (4 recruitment missions)

---

### Cycle 2.4: Fourth Skill Tree (Leadership & Operations)

**Status**: IMPLEMENTED
**Priority**: P3 within Phase 2

5 skills in a Leadership & Operations tree that tie crew and faction systems together. Every bonus type is consumed in actual gameplay code — no dead skills.

**Skills**: Crew Manager (+1 crew slot, root), Diplomatic Relations (+1 rep/trade, max 2), Inspiring Leader (+1 crew loyalty/trade, max 2), Tariff Negotiation (-5% tariff, max 2), Crew Mentor (+2 crew XP/event, max 2). Tree structure: Crew Manager branches into Diplomatic Relations (→ Tariff Negotiation) and Inspiring Leader (→ Crew Mentor). Total 9 points to max, matching Trading tree.

**Bonus consumption**: `crew_slot_bonus` in game.py crew recruitment and crew roster view slot display. `reputation_gain_bonus` in trading_view.py `_apply_trade_reputation()`. `crew_loyalty_bonus` and `crew_xp_bonus` in game.py `check_crew_xp()`. `tariff_reduction` in trading_view.py buy/sell price calculations (only reduces penalty tariffs, not discounts).

**View layout**: 4-tree layout across 1280px — Trading (160), Gathering (460), Mining (740), Leadership (1080). Gathering shifted -20, Mining shifted -60/-80 from previous positions. Leadership header in purple (FACTION_SCIENCE).

**Files modified**: `progression.py` (LEADERSHIP enum + 5 skills), `skill_trees.json` (leadership tree data), `skill_tree_view.py` (4-tree layout + header), `game.py` (crew_slot/loyalty/xp bonus consumption), `trading_view.py` (tariff_reduction + reputation_gain consumption), `test_progression.py` (11 new tests)
**Total**: 23 skills across 4 trees, 338 tests

---

## Campaign Act One: Missions 01-02 (Completed)

**Goal**: First two story missions establishing the new game flow and trade permit system
**Status**: COMPLETE

---

### Mission 01: Bill of Landing

**Status**: IMPLEMENTED

Trade permit system gates buying/selling at faction-controlled stations. New players must acquire a "bill of landing" from Customs Officer Larsen at Nexus Prime (costs 250 credits). Auto-triggers when first entering trading at Nexus Prime. Completing the mission grants a trade permit for the current system's faction and 20 XP.

**Trade permit system**: Per-faction `trade_permits: set[str]` on Player model. Trading view checks for permit before allowing buy/sell operations. Legacy saves grant all permits for backward compatibility.

### Mission 02: Iron Ore Delivery

**Status**: IMPLEMENTED

Cargo Broker at Nexus Prime offers 500 credits to deliver 10 iron ore to Forgeworks. Prerequisites: bill_of_landing completed. Accepting the mission auto-loads 10 iron ore into cargo (via `on_accept_cargo` system). Uses non-sticky `collect_cargo` objectives — selling the cargo before delivery reverts objective progress. Completing at Forgeworks grants 500 credits, removes the cargo, and awards 40 XP.

### Supporting Systems

**Player name input**: New `NAME_INPUT` GameState and `NameInputView` — text input with "BEGIN JOURNEY" button replaces hardcoded "Captain" name. New Game → NAME_INPUT → intro narration → GALAXY_MAP.

**Intro narration**: 5-node narrator dialogue presenting the player's backstory (mining colony, father's death, departing for the stars). Uses narrator mode in DialogueView (full-width text, no portrait, secondary text color). Returns to GALAXY_MAP instead of TRADING.

**Auto-trigger dialogues**: Game engine detects campaign-relevant conditions (e.g., first visit to Nexus Prime trading) and auto-starts the appropriate dialogue before entering the view.

**Mission model extensions**: `AcceptCargo` dataclass for granting cargo on mission accept. New reward types: `deduct_credits`, `remove_cargo`, `trade_permit`. Non-sticky `collect_cargo` objectives re-evaluated each frame.

**Dialogue system extensions**: Configurable `_return_state` on DialogueView (defaults to TRADING, set to GALAXY_MAP for intro). Narrator mode renders full-width text without portrait. Generalized dialogue end handler supports any return state.

**Files created**: `spacegame/views/name_input_view.py`, `tests/test_models/test_campaign.py` (19 tests)
**Files modified**: `player.py` (trade_permits), `mission.py` (AcceptCargo, rewards, non-sticky cargo), `dialogue_view.py` (narrator mode, return state), `trading_view.py` (permit gating), `config.py` (NAME_INPUT), `game.py` (new game flow, auto-dialogue, rewards), `save_manager.py` (trade_permits), `data_loader.py` (on_accept_cargo), `npcs.json` (+2 NPCs), `dialogues.json` (+3 trees), `missions.json` (+2 missions)
**Total**: 19 views, 10 missions, 346 tests

---

## Phase 3 (Completed): Core Combat & Interaction Systems

**Goal**: Build the foundational systems required for Act One completion (Missions 03-17) and future campaign content
**Status**: COMPLETE — all 5 cycles implemented (Speech & Social, Random Encounters, Space Combat, Combat View, Combat Depth & Advanced Trading)
**Ref**: See `requirements/campaign_act_one.md` for narrative context and mission-by-system mapping

---

### Cycle 3.1: Speech & Social System

**Status**: IMPLEMENTED
**Priority**: P1 within Phase 3 — foundational for multiple missions
**Campaign need**: Missions 07, 09, 11, 13, 16 (Union/Alliance paths)

Social interaction system with use-based social skills and dialogue skill checks. Deterministic check resolution (no dice rolls) — player sees effective level vs. difficulty before choosing.

**What was built**:
- **SocialSkill dataclass + SocialManager** (`spacegame/models/social.py`): 3 skills (Persuasion, Intimidation, Observation), use-based growth separate from skill tree economy
- **Skill growth**: +2 XP per successful check, +1 XP per failure. XP thresholds [0, 5, 15, 30, 50] for levels 1-5
- **NPC disposition**: Per-NPC relationship (0-100, default 50). Modifier = `(disposition - 50) // 10`, adjusts effective level for checks. +3 disposition on successful check, -2 on failure
- **SkillCheck dataclass** on `DialogueResponse`: skill, difficulty, success_node_id, failure_node_id, conditional flags
- **DialogueResponse.disposition_change**: non-check disposition adjustments from dialogue choices
- **DialogueManager integration**: `set_social_manager()`, `start_dialogue(tree, npc_id)`, check resolution in `select_response()`, graceful fallback without social manager
- **DialogueView visual feedback**: color-coded skill check indicators (green/yellow/red stripe), `[Skill: effective/difficulty]` prefix, pass/fail feedback overlay with fade
- **Player.social_state**: opaque dict serialized in save_manager (backward compatible with old saves)
- **DataLoader**: parses optional `skill_check` and `disposition_change` from dialogue JSON

**Files created**: `spacegame/models/social.py`, `tests/test_models/test_social.py` (42 tests)
**Files modified**: `dialogue.py` (SkillCheck, DialogueResponse, DialogueManager extensions), `dialogue_view.py` (check indicators + feedback), `player.py` (social_state), `save_manager.py` (social_state persistence), `data_loader.py` (skill_check parsing), `game.py` (SocialManager creation + wiring), `config.py` (check colors + feedback duration), `test_dialogue.py` (+18 tests)

---

### Cycle 3.2: Random Encounter Framework

**Status**: IMPLEMENTED
**Priority**: P1 within Phase 3
**Campaign need**: Mission 08 (distress signal), Mission 12 (pirate attack)

Data-driven encounter system with 7 encounter types triggering during travel. Non-hostile encounters (distress signal, derelict, merchant, debris, anomaly, shakedown) route through a dedicated EncounterView with choice buttons and reward outcomes. Hostile encounters go directly to combat.

**What was built**:
- **EncounterDefinition, EncounterChoice, EncounterOutcome** dataclasses in `models/encounter.py` — data-driven encounter templates loaded from JSON
- **12 encounter definitions** in `data/encounters/encounters.json` across 6 non-hostile types with 2-3 choices each
- **EncounterView** (`views/encounter_view.py`): phase state machine (CHOOSING → OUTCOME → DONE), keyboard shortcuts (1-3 for choices, Enter for continue), template string substitution for shakedown demands
- **Type distribution**: 65% hostile, 35% non-hostile (weighted per danger level — moderate has no shakedown/anomaly, dangerous has all types)
- **select_encounter_definition()**: filters by type + danger level, weighted random with deterministic seed
- **game.py integration**: GameState.ENCOUNTER routing, encounter view lifecycle, reward application (credits, deduct_credits, XP, set_flag), shakedown sentinel resolution
- **Galaxy map refactor**: removed inline distress/shakedown overlays, unified all non-hostile encounters through ENCOUNTER state, updated encounter alert styling for all 7 types

**Files created**: `spacegame/views/encounter_view.py`, `data/encounters/encounters.json`, `tests/test_data/test_encounter_data.py`, `tests/test_views/test_encounter_view.py`
**Files modified**: `models/encounter.py` (3 new dataclasses, type distribution, selection), `data_loader.py` (encounter definition parsing), `config.py` (GameState.ENCOUNTER), `game.py` (state transitions, reward application), `galaxy_map_view.py` (remove overlays, ENCOUNTER routing), `test_encounter.py` (+27 tests), `test_galaxy_map_view.py` (routing tests)

---

### Cycle 3.3: Space Combat Foundation (Models & Engine)

**Status**: IMPLEMENTED
**Priority**: P2 within Phase 3
**Campaign need**: Mission 12 (tutorial combat), Mission 16 (Guild path — strike force)

Turn-based RPG combat with player moves, crew phase, and enemy phase. Full combat model with 13 enemy templates, 5 weapon upgrades, 5 defense upgrades, and 4 crew combat abilities. Flee, negotiate, and bribe non-combat resolution paths.

**What was built**:
- **CombatMove/CombatEffect** data models with 8 effect types (damage, shield_restore, hull_restore, evasion_mod, accuracy_mod, shield_drain, damage_reduction, energy_drain)
- **EnemyShipTemplate/EnemyShip**: 5 base archetypes + 8 faction-themed variants with 4 AI behaviors (aggressive/defensive/cowardly/evasive)
- **CombatEngine**: damage resolution (accuracy vs evasion, clamped 5-95%), shields absorb first, damage reduction, energy costs, cooldowns
- **PlayerCombatState/CombatState**: full combat state tracking, build_player_combat_state factory
- **ShipType**: 7 combat stats (hull, shields, weapon_power, evasion, accuracy, speed, energy) + 3 slot categories (weapon/defense/utility)
- **Flee mechanic**: speed-based chance with parting shots at -20 accuracy
- **Negotiate**: uses SocialManager with faction rep modifiers
- **Bribe**: credits-based with persuasion discount
- **Player.apply_combat_defeat()**: 30% cargo loss, hull to 25%, shields to 0

**Files created**: `spacegame/models/combat.py`, `data/combat/enemies.json`, `tests/test_models/test_combat.py` (129 tests)
**Files modified**: `models/ship.py` (combat stats, slot categories), `models/player.py` (combat defeat), `data/ships/ship_types.json` (combat stats), `data/ships/upgrades.json` (+10 combat upgrades), `config.py` (GameState.COMBAT, 9 combat constants)

---

### Cycle 3.4: Combat View & Travel Encounters

**Status**: IMPLEMENTED
**Priority**: P2 within Phase 3

Polished turn-based combat UI with phase-driven state machine, animation system, and travel encounter integration.

**What was built**:
- **CombatView** (~1800 lines): 7-phase state machine (INTRO → PLAYER_INPUT → ANIMATING_PLAYER → ANIMATING_CREW → ANIMATING_ENEMIES → ROUND_END → COMBAT_OVER)
- **Animation queue system**: AnimationEvent processed sequentially with configurable duration and visual effects
- **Status panels**: player hull/shield/energy bars with smooth lerp, enemy cards with pulsing target selection
- **Action bar**: custom _MoveButton with energy cost/cooldown overlays, flee (% display), negotiate, bribe
- **Keyboard shortcuts**: 1-4 for moves, Tab for target cycle, F/Escape for flee, N for negotiate, Enter to continue
- **Visual effects**: 6 combat particle configs (LASER_HIT, MISSILE_EXPLOSION, SHIELD_IMPACT, HEAL_SPARKLE, SHIELD_RESTORE), screen shake, damage flash, floating damage numbers
- **Travel encounter system**: `_check_travel_encounter()` with danger-based chance (safe=0%, moderate=15%, dangerous=30%), deterministic seeding
- **Combat outcome screen**: polished panel with result title, stats, XP gained, result-specific messages

**Files created**: `spacegame/views/combat_view.py`, `tests/test_views/test_combat_view.py` (80 tests)
**Files modified**: `engine/game.py` (start_combat, _apply_combat_result, travel encounter hook), `galaxy_map_view.py` (encounter alert during travel)

---

### Cycle 3.5: Combat Depth & Balance + Advanced Trading

**Status**: IMPLEMENTED
**Priority**: P1 within Phase 3

Enemy variety, non-combat resolution depth, and advanced trading features.

**What was built**:
- **Enemy variety**: faction_id/danger_tier/bribe_cost on EnemyShipTemplate, 8 faction-themed enemies (13 total), filter_enemies_for_system() by faction+danger
- **Non-combat resolution**: bribe action (credits-based, persuasion discount), enhanced negotiation (faction rep modifiers, partial loot, rival rep), emergency thrusters upgrade (+15% flee)
- **Shakedown encounters**: dangerous systems only, pay tribute or fight
- **PriceHistory**: per-system/commodity, 7-day rolling, trend detection (rising/falling/stable)
- **Dynamic supply/demand**: player activity shifts prices ±0.02/unit, ±0.30 cap, 30% daily decay
- **TradeRouteTracker**: symmetric route keys, efficiency bonuses at 3/5/10 trips (5%/10%/15%)
- **TradeContractManager**: deterministic generation, time-limited contracts with bonus credits
- **Bug fixes**: SellMax XP/rep parity, total_profit tracking actual profit, market events activated

**Files created**: `tests/test_models/test_advanced_trading.py`, `tests/test_models/test_combat_depth.py` (184 new tests)
**Files modified**: `models/combat.py` (bribe, negotiation), `models/market.py` (PriceHistory, supply/demand), `models/player.py` (trade routes, contracts), `engine/game.py` (market integration)

---

### Cycle 3.6: Campaign Act One — Full Implementation

**Status**: COMPLETE
**Priority**: P1 within Phase 3

All Act One campaign content implemented — 22 missions across 5 chapters, 17 NPCs, 18 dialogue trees.

**What's implemented**:
- **Chapter 1 (M01-M02)**: Bill of Landing (trade permit), Iron Ore Delivery
- **Chapter 2 (M03-M08)**: Faction introductions (Union Territory, Foreman's Son, Scholar's Errand, Drifter's Deal, Drifter's Delivery), 4 crew recruitment missions
- **Chapter 3 (M09-M12)**: Cargo Lost (Reva Sato distress), Whispers at the Bar (Dex Halloran), The Crimson Run (Malia Torres), Embassy Visit (faction summit), Under Fire (Ledger pirates)
- **Chapter 4-5 (M13-M17+)**: The Favor Returned, Iron Depths Investigation, The Ledger, Point of No Return, The Collapse
- **Character & Attribute System**: 5 sci-fi attributes with point allocation at creation and level-up
- **Social Skill Tree**: 3 social skill nodes in SkillTreeType.SOCIAL
- **Journal System**: JournalView for tracking story events and world lore
- **Political System**: Faction-to-faction relationships, political events, intel system, reputation consequences
- **NPCs**: Officer Larsen, Cargo Broker, Elena Reeves, Marcus Jin, Dr. Priya Osei, Tomas Drifter, Hanna Voss, Reva Sato, Dex Halloran, Malia Torres, Oren Tak, Sienna Vek, and more

**Total**: 22 missions, 17 NPCs, 34 views, 2948 tests

---

## Phase 4: World Depth & Gameplay Polish

**Goal**: Deepen existing gameplay systems, add world variety, and introduce new economic mechanics
**Status**: COMPLETE — all 3 cycles (Planet Infrastructure, Mini-Game Overhaul, Smuggling)

---

### Cycle 4.1: Planet Infrastructure

**Status**: COMPLETE (all phases A-F)
**Priority**: P1 within Phase 4
**Campaign need**: Mission 11 (embassy summit), general world depth

Each system gains distinct explorable locations with their own services and character.

**What was built**:
- **Location data model**: `Location` @dataclass with id, name, location_type, description, flavor_text, system_id, repair_cost_per_hp
- **Location JSON**: `data/galaxy/locations.json` — 10 systems with 3-6 locations each (market, repair_bay, cantina, mining, salvaging, refining, shipyard, unique)
- **DataLoader integration**: `load_locations()`, `get_locations_for_system()`, called from `load_all()`
- **Repair model**: `Player.repair_at_station(cost_per_hp)` — hull repair for credits, uses existing `Ship.repair_hull()`
- **StationHubView**: Location selection screen with card-based UI, cantina NPC panel (toggle), unique location detail panels, UNDOCK back to galaxy map
- **RepairBayView**: Hull repair service with damage bar, cost display, repair action, message feedback, HEAL_SPARKLE particles on repair
- **Navigation rewiring**: Galaxy Map → STATION_HUB (was → TRADING), STATION_HUB → TRADING/REPAIR_BAY/MINING/SALVAGING/REFINING/SHIPYARD/DIALOGUE, mini-games return to STATION_HUB, shipyard returns to STATION_HUB
- **Shields auto-restore on dock**: `player.ship.restore_shields()` called on StationHubView entry
- **Activity/NPC buttons moved**: From TradingView to StationHubView — TradingView simplified to pure market operations
- **Rich faction flavor**: 50+ location descriptions drawing from cultural guide system profiles
- **2 new GameStates**: STATION_HUB, REPAIR_BAY
- **Phase F polish**: Faction color theming (header, dot indicator), rotating flavor text with fade transitions, enhanced card accents (wider stripe, top bar, type labels), word-wrapped unique location detail panels, hull/shield visual bars in repair bay, HEAL_SPARKLE particle effects on repair, status bar with colored values and background panel, location name/flavor passed to RepairBayView
- Embassy/political entity locations deferred to Political Systems cycle

---

### Cycle 4.2: Mini-Game Depth & Polish

**Status**: COMPLETE (all 5 cycles A-E, including Investment system)
**Priority**: P1 within Phase 4

Comprehensive overhaul of all three resource mini-games (mining, salvaging, refining) plus investment system for passive income. Activates unused skill bonuses, adds strategic depth mechanics, and brings visual polish.

**Ref**: See `requirements/12_minigame_overhaul.md` for full specification

**What was built**:
- **Mining (Cycle A)**: Energy system (20 base, 1 cost/click, 3s regen), rare ore chance bonuses (rich_veins + deep_scan wired), depth scaling (1-10+ with escalating rare/yield bonuses), chain detonation (8-directional cascades), session milestones (3 random from 9-entry pool)
- **Salvage (Cycle B)**: Minesweeper-style proximity hints on empty cells, parallel extraction (2 base + 1 from master_extractor lv3), item quality variance (0.8-1.5, 4 tiers), corruption timer (90s countdown, 2-charge scan cost), 3 derelict type presets (Cargo Bay, Lab Module, Engine Room)
- **Refining (Cycle C)**: Delta time conversion (replaced time.time() with dt accumulation), speed/yield skill bonuses (efficient_refining, yield_mastery), batch queuing (atomic start_batch(), +/- UI), 3 new recipes (forge_alloy, purify_crystal, advanced_electronics), 2 new commodities (alloy_composite, purified_crystal)
- **Skills & Achievements (Cycle D)**: 4 new skill nodes (energy_reserves, efficient_refining, yield_mastery, chain_reaction), 2 previously unused bonuses wired (rich_veins, deep_scan), 10 new achievements across mining/salvage/refining, session summary overlays with stats + XP, 8 new player stats
- **Investment + Polish (Cycle E)**: InvestmentManager with 3-tier investments at all 10 systems, InvestmentView with invest/upgrade/collect UI, day-advance return accumulation with disaster halt and pirate risk, S/A/B/C/D session rating system for all 3 mini-games, 5 particle configs (MINING_CHAIN, ENERGY_REGEN, SALVAGE_SCAN, SALVAGE_CORRUPT, REFINE_COMPLETE), save/load with backward compat

---

### Cycle 4.3: Smuggling & Contraband

**Status**: COMPLETE (Phases A-E model layer + Phase E view integration)
**Campaign need**: Mission 07 (Tomas's scheme), Mission 10 (Crimson Reach underground)

Underground economy with illegal goods, black markets, and criminal contacts.

**What was built**:
- **Contraband commodities**: 5 contraband goods (weapons_components, restricted_tech, stolen_data, exotic_samples, counterfeit_goods) with Legality enum (LEGAL/RESTRICTED/ILLEGAL) on all 26 commodities
- **Detection system**: Per-faction customs inspections on arrival with configurable inspection chance, fine multipliers, and contraband confiscation. Faction laws loaded from JSON. Encounter-based resolution (comply/persuade/bribe/intimidate)
- **Black markets**: Permit-based access (`player.black_market_access: set[str]`), per-system black market names, mode toggle in TradingView with legality-modified pricing (LEGAL +15%, RESTRICTED 0%, ILLEGAL -10%), no tariffs in black market mode
- **Smuggling contracts**: `SmugglingContractManager` with deterministic generation, time-limited delivery contracts, accept/complete/expire lifecycle, max 3 active, penalty on failure, daily expiration check in game loop
- **Criminal heat**: 0-100 scale, +heat from smuggling/caught, -1/day decay, triggers bounty hunter encounters at 26+ (3 tiers: freelance/licensed/elite), color-coded display in station hub and galaxy map
- **Hidden compartments**: `HiddenCompartment` model (30% of cargo capacity hidden), cargo transfer UI in trading view, reduced scan detection, doubled penalties if found, save/load support
- **Ship modifications**: 3 smuggling upgrades (hidden_compartment, signal_jammer, false_transponder) with `requires_black_market` flag — only visible in shipyard at black market locations
- **Bounty hunters**: Chance-based encounters scaling with criminal heat, safe havens (Crimson Reach), combat resolution via existing combat system
- **Achievements**: 3 smuggling achievements (first_smuggle, heat_survivor, clean_getaway), 2 new player stats (inspections_passed_with_contraband, max_criminal_heat_reached)
- **Save/load**: Full backward-compatible serialization for all new fields (black_market_access, hidden_compartment, smuggling_contract_state, criminal heat stats)

**Key files**: `models/smuggling.py` (~1800 lines), `views/trading_view.py` (black market mode), `engine/game.py` (inspection/bounty hooks), `data/economy/faction_laws.json`, `data/economy/commodities.json` (legality field)

---

## Phase 5: Campaign Expansion

**Goal**: Complete Act One, continue the story through Acts Two and Three, deepen political systems
**Status**: COMPLETE — Ground Exploration (5.1), Political Systems (5.2), and Campaign Act One (5.3) all implemented. 22 missions, 17 NPCs, political system with faction relationships/events/intel/consequences.

---

### Cycle 5.1: Ground Exploration

**Status**: COMPLETE (Phases A-F)
**Priority**: P1 within Phase 5

Turn-based, stealth-first, grid-based roguelike exploration system. Full specification in `requirements/13_ground_exploration.md`.

**Implementation phases**:
- **Phase A — Grid Foundation**: COMPLETE — GroundMap model (13 tile types, fog of war 3-state), GroundExplorationView (~1700 lines) with scrolling viewport, player movement, tile rendering, minimap corner display
- **Phase B — Stealth Core**: COMPLETE — GroundEnemy model with facing/direction, vision cones, 4 detection states (UNDETECTED → SUSPICIOUS → ALERT → COMBAT), noise system (noisy floor, door opening), alert decay timers, patrol route following
- **Phase C — Ground Combat (Dice & Grit)**: COMPLETE — GroundCombatState with 1d6+modifier exchanges, fight/retreat/talk actions, social skill integration (Persuasion/Intimidation checks for talk), combat message overlay, enemy defeat/loot, 8 enemy templates with loot_credits
- **Phase D — Crew & Attributes**: COMPLETE — GroundCrewBonuses pre-computed dataclass, Elena (+1 vision radius), Marcus (bypass locked doors silently), Priya (analyze weakness +3 attack), Tomas (reveal patrol routes). Attribute integration: ACU → vision, RES → defense, COM → loot bonus (COM//2 * 10%), SYN → talk bonus. Full view wiring with 11 view-level tests
- **Phase E — Procedural Generation**: COMPLETE — ChunkTemplate/ChunkLibrary with 8 hand-authored 8x8 room templates (security_checkpoint, storage_bay, mess_hall, lab, office, cargo_hold, server_room, workshop) each with interior wall features (barriers, shelving, pillars, crates). GroundMapGenerator: room-placement + corridor-carving, L-shaped connections, chunk stamping. 4 DifficultyTiers (LOW→EXTREME) scaling map size/enemies/speed/loot. 5 MissionTypes with map adjustments. Faction-specific enemy pools (4 factions). Deterministic seeding. 62 mapgen tests including 100-seed stress tests and BFS connectivity verification
- **Phase F — Content & Polish**: COMPLETE — briefing view (pre-mission), result view (post-mission), game engine integration, ground equipment/loot system, repeatable ground contracts, 3 hand-crafted campaign maps (Missions 10, 13, 16), interactables/triggers, minimap, 7 ground achievements, visual effects polish

**Key files**:
- `spacegame/models/ground.py` — GroundMap, GroundTile, TileType, FogState, GroundPlayerState
- `spacegame/models/ground_enemy.py` — GroundEnemy, GroundMissionState, detection/noise logic
- `spacegame/models/ground_combat.py` — GroundCombatState, enemy templates, fight/retreat/talk
- `spacegame/models/ground_crew.py` — GroundCrewBonuses, crew ability definitions
- `spacegame/models/ground_mapgen.py` — ChunkTemplate, ChunkLibrary, GroundMapGenerator, MapGenConfig/Result
- `spacegame/views/ground_exploration_view.py` — Full exploration view with stealth, combat, and crew integration
- Tests: test_ground.py, test_ground_enemy.py, test_ground_combat.py, test_ground_crew_integration.py, test_ground_polish.py, test_ground_mapgen.py, test_ground_crew_view.py

**Key design pillars**:
- Stealth-first identity — patience and observation, not aggression
- Grid-native "Dice & Grit" combat — fast 1d6 exchanges, distinct from space combat's move/energy/cooldown system
- Voluntary extraction — push-your-luck tension, keep what you've found or risk going deeper
- Bell-curve failure consequences — grace period early, peak penalty mid-mission, easing near completion
- Multiple playstyles: Ghost (stealth), Scrapper (combat), Silver Tongue (social), Opportunist (balanced)
- Dual content pipeline: hand-authored campaign maps + procedural generation for repeatable gameplay loop

### Cycle 5.2: Political Systems

**Status**: COMPLETE

Full political system implemented in `spacegame/models/politics.py` (751 lines):
- **PoliticsManager**: faction-to-faction bilateral relationships (-100 to +100), centralized reputation with 30% spillover
- **Political events**: 6 event types (trade_dispute, border_incident, aid_request, diplomatic_summit, sanction, pirate_crisis), 4 player actions (side_with_a/b, mediate, ignore), daily generation chance, event duration and drift
- **Intel system**: IntelReport model with 3 quality tiers (rumor/report/classified), delivery to factions for credits + rep, rival bonus multiplier
- **Expanded reputation consequences**: docking denial (HOSTILE), encounter modifiers, NPC disposition modifiers, trade restrictions
- **Data**: `data/politics/faction_relationships.json` with initial bilateral values for all 6 faction pairs
- **Integration**: game.py day-advance hooks, centralized spillover replacing per-view rep logic, save/load with backward compatibility
- **Tests**: 88+ tests in test_politics.py and test_politics_integration.py

### Cycle 5.3: Campaign Act One Completion (Chapters 3-5)

**Status**: COMPLETE

All Act One chapters implemented — 22 missions total (see Cycle 3.6 for full details):
- Chapter 3 (M09-M12): Reva Sato distress, Dex Halloran intel broker, Malia Torres underground, embassy summit, Ledger pirate attack
- Chapter 4-5 (M13-M17+): The Favor Returned, Iron Depths Investigation, The Ledger, Point of No Return, The Collapse
- 17 NPCs including Hanna Voss, Reva Sato, Dex Halloran, Malia Torres, Oren Tak, Sienna Vek
- Hand-authored ground exploration maps for campaign missions
- 28 enemy templates including faction-themed and Ledger-specific enemies

---

## Phase 6 (Complete): Visual Overhaul & Polish

**Goal**: Transform the game from "functional with sprites" into a visually polished, cohesive 16-bit pixel art experience. This phase is prioritized BEFORE Act Two content.
**Status**: COMPLETE — Infrastructure, sprite generation, view wiring, sprite sheet animations (75 sheets), UI chrome (9-slice panels, cursor, skill/hub icons, ground characters). Audio and remaining minor visual items deferred to polish passes.
**Ref**: See `requirements/15_visual_overhaul.md` for full specification

### Cycle 6.1: Visual Overhaul Phase A (Infrastructure)

**Status**: COMPLETE

Built the technical foundation for all sprite rendering:
- **Palette system**: PaletteManager, 7 JSON palette definitions (UI + 5 factions + master)
- **Sprite engine**: SpriteSheet, AnimatedSprite, AnimationDef, SpriteManager in `spacegame/engine/sprites.py`
- **Pixel pipeline**: `tools/pixel_pipeline.py` — PIL-based resize, quantize, outline, alpha, pack/unpack, palette swap
- **Asset generation**: DALL-E 3 concept art → pixel pipeline → game-ready sprites
- **Directory structure**: `spacegame/data/assets/sprites/` with portraits, ships (player + enemy), commodities, factions, ground_tiles, upgrades, ui subdirectories
- **SpriteManager convenience API**: get_ship_sprite, get_enemy_sprite, get_portrait_sprite, get_commodity_icon, get_faction_emblem, get_ground_tile, get_upgrade_icon — all with graceful None fallback
- 110 sprite/palette tests

### Cycle 6.2: Sprite Generation & View Wiring

**Status**: COMPLETE

Generated all static sprites and wired them into game views:
- **Player ships**: 9 ship sprites (shuttle through heavy_hauler) at 32×32 native
- **Enemy ships**: 28 enemy sprites across all factions at 32×32 native, 2-3 distinct silhouettes per faction
- **NPC portraits**: 17 portrait sprites at 50×60 native for all NPCs
- **Commodity icons**: 27 icons at 16×16 native for all tradeable goods
- **Faction emblems**: 5 emblems at 24×24 native
- **Upgrade icons**: 21 upgrade icons at 16×16 native
- **Ground tiles**: 13 tile types × 5 palettes (neutral + 4 factions) at 16×16 native
- **View wiring**: Combat view (ship sprites + hull tinting), dialogue view (portrait rendering), trading view (commodity icons in market table), shipyard view (ship preview + upgrade icons), station hub (faction emblems), crew roster (crew portraits), ground exploration (tile sprites), mining view (ore icons replacing procedural polygons)

### Cycle 6.3: Animation & Visual Effects (MOSTLY COMPLETE)

**Status**: IN PROGRESS
**Priority**: P1 — transforms static sprites into living game world

**Completed**:
- Ship animation sheets: 2-frame engine idle (75 sprite sheets via sprite_sheet_gen.py)
- Portrait animation: 2-frame breathing cycle (12 portrait sheets)
- Commodity animation: 2-frame color pulse (27 sheets)
- Faction emblem animation: 2-frame shimmer (5 sheets)
- Animation JSON configs: ship_anims.json, portrait_anims.json
- AnimatedSprite integration in combat, dialogue, crew_roster, galaxy_map, and main_menu views
- Combat ship hit flash (white overlay on hull damage, 0.12s decay)
- Combat shield shimmer (cyan glow ring on shield absorb, 0.2s decay)
- Ground character directional rotation (player + enemies rotate sprite based on facing)
- PIXELATE transition effect (used for ground exploration entry)

**Remaining**:
- Ship destruction sequence (multi-frame)
- Portrait expression variants (neutral/confident/stern/surprised) — model supports it, needs DALL-E + dialogue JSON tagging
- Ground tile animation: terminal blink, hazard pulse, vent steam (requires new TileType additions)
- Damage state overlays (scorch marks, sparks, missing panels)

### Cycle 6.4: UI Chrome & Polish (MOSTLY COMPLETE)

**Status**: IN PROGRESS
**Priority**: P2 — final visual cohesion pass

**Completed**:
- 9-slice pixel art panel system (procedural, replaces all draw_panel() calls game-wide)
- Pixel art beveled bar frames (inset highlight/shadow on all draw_bar() calls)
- Custom 16×16 pixel art cursor (blue accent arrow, set on game startup)
- Skill tree node icons (35 DALL-E generated icons wired into skill_tree_view.py)
- Station hub location type icons (8 DALL-E icons wired into station_hub_view.py)
- Ground enemy sprites (8 DALL-E 16×16 sprites, replacing circle+triangle renderers)
- Player ground sprite (DALL-E 16×16, replacing yellow square)
- Achievement category badges (procedural hexagonal icons, 10 categories)
- Achievement checkmark (pixel art tick replacing "OK" text)
- Consistency audit: all fonts → FontCache, hardcoded colors → Colors constants, manual bars → draw_bar(), manual panels → draw_panel()

**Remaining**:
- Status effect icons (12×12 buff/debuff indicators for combat)
- System portraits (80×60 per system, for galaxy map and trading view header)

### Cycle 6.5: Audio (REMAINING)

**Status**: NOT STARTED
**Priority**: P2

- Sound effects for trading, mining, salvage, travel, UI, combat
- Background music per system/situation/combat
- Ambient audio and station atmosphere sounds

### Cycle 6.6: Performance & Distribution (REMAINING)

**Status**: NOT STARTED
**Priority**: P3

- Performance optimization and profiling
- Installer/packaging (PyInstaller or similar)
- Steam/itch.io distribution
- Marketing materials

---

## Phase 7 (Future): Campaign Acts Two & Three

**Goal**: Continue and complete the conspiracy storyline. Deferred until visual overhaul and polish are complete.

### Cycle 7.1: Campaign Act Two — "The Ledger"
- Continue the conspiracy storyline from Act One's revelation
- Explore new regions beyond the original 10 systems
- Faction alignment consequences from Act One choices shape the story
- Deeper companion personal quests (Elena's corporate corruption, Marcus's cover-up, Priya's suppressed research, Tomas's past identity)
- The Ledger's operations exposed across the sector
- 15-20 additional missions with branching paths
- New crew members recruitable in Act Two
- **Fleet Management** introduced as Act Two feature (see Cycle 7.2)

### Cycle 7.2: Fleet Management (Act Two Feature)
- Own and manage multiple ships simultaneously
- Assign crew to different ships with distinct bonuses
- AI-controlled trade routes for owned fleet (trade route automation)
- Fleet view UI showing all ships, crew assignments, route status
- Fleet-scale combat encounters (command multiple ships)
- Futures trading and remaining advanced trading features
- Narratively tied to Act Two's expanded scope — player's growing influence justifies a fleet

### Cycle 7.3: Campaign Act Three — Resolution
- Final act resolving The Ledger conspiracy
- Multiple endings based on faction alignment, companion loyalty, and player choices
- 10-15 missions leading to climax
- Epilogue showing consequences of player's journey on the sector
- Total campaign target: 15-20 hours across all three acts

---

## Technical Debt & Quality

Ongoing throughout all phases:
- Unit tests for all new model methods (TDD workflow)
- Integration tests for save/load with new systems
- Playtesting after each major feature
- Balance tuning based on playtesting
- Documentation updates in docs/ and CLAUDE.md

---

## Success Metrics

**Phase 1 Success** (ACHIEVED):
- New players can learn the game without external help
- Players have clear goals via statistics and achievements
- Market events feel impactful and visible

**Phase 2 Success** (ACHIEVED):
- RPG systems feel integrated, not bolted on
- Faction choices create meaningful trade-offs
- Campaign missions provide narrative motivation
- At least one crew member enhances gameplay

**Phase 3 Success** (ACHIEVED):
- Speech/social system makes dialogue feel interactive, not passive
- Space combat adds tension without overwhelming the trading core
- Random encounters make travel feel alive and unpredictable
- Character attributes create meaningful build diversity
- Advanced trading rewards market knowledge and route optimization

**Phase 4 Success** (ACHIEVED):
- Mini-games feel deep and replayable with strategic decision-making
- Each system feels like a distinct place with its own character
- Smuggling provides a viable alternative playstyle with real risk
- Investment system rewards long-term economic planning
- Unused skill bonuses are all active and impactful

**Phase 5 Success** (ACHIEVED):
- Ground exploration feels mechanically distinct from space combat — stealth-first, not aggression-first
- Multiple viable ground playstyles (ghost, scrapper, silver tongue, opportunist)
- Procedural ground maps provide sustainable repeatable content with unique rewards
- Political systems create faction-level consequences that players can influence
- Act One campaign complete (22 missions) with branching story and meaningful faction choices

**Phase 6+ Success**:
- Visual overhaul creates a cohesive 16-bit pixel art aesthetic
- Animations bring the game world to life (ships, portraits, tiles)
- UI polish makes every screen feel intentional and crafted
- Audio adds atmosphere and feedback to all gameplay systems
- 15-20 hour campaign playthrough across three acts (Acts Two & Three)
- Fleet management (Act Two) adds strategic depth as player influence grows
- Multiple endings reflect the player's journey and choices
- Companion stories feel personal and emotionally resonant

---

**Document Status**: v17.0
**Last Updated**: 2026-03-16
**v17.0**: Phase 6 marked COMPLETE. Implementation Roadmap retired as active development tracker — Refinement Roadmap (`16_refinement_roadmap.md`) is now the primary development document. Updated counts: 3,680 tests, 34 views, 55 missions (22 campaign + 21 side + 12 crew quests), 131 encounters, 28 NPCs, 24 ship types, 40 upgrades, 43 achievements, 4 crew members with loyalty system. Phase 7 (Act Two, Act Three, Fleet Management) remains future work.
**v16.0**: Major status update — Phase 5 marked COMPLETE (Political Systems 5.2, Campaign Act One 5.3 with 22 missions, 17 NPCs). Visual Overhaul infrastructure (Phase A) and sprite generation/wiring (Phase B) complete: all ship, portrait, commodity, faction, upgrade, and ground tile sprites generated and integrated into views. Mini-Game Overhaul Cycle E (Investment system) confirmed COMPLETE. Roadmap reorganized: Visual Overhaul & Polish promoted to Phase 6 (next priority), Campaign Acts Two & Three deferred to Phase 7. Updated counts: 2948 tests, 34 views, 22 missions, 17 NPCs, 28 enemy templates, 27 commodities, 9 ship types, 43 achievements, 6 skill trees with 32 skills.
**v14.0**: Ground Exploration and Political Systems split into separate cycles (5.1 and 5.2). Ground Exploration fully specified in new `requirements/13_ground_exploration.md` — turn-based stealth-first grid roguelike with "Dice & Grit" combat, procedural generation, crew integration, voluntary extraction, bell-curve failure consequences, and 6 implementation phases (A-F). Phase 5 renumbered: Ground Exploration (5.1), Political Systems (5.2), Act One Completion (5.3), Act Two + Fleet (5.4/5.4.1), Act Three (5.5).
**v13.0**: Fleet Management moved from Cycle 5.1 to Act Two feature (Cycle 5.3.1) — narratively tied to player's growing influence. Phase 5 renumbered: Ground Exploration (5.1), Act One Completion (5.2), Act Two + Fleet (5.3/5.3.1), Act Three (5.4). Phase 5 title updated from "Campaign Expansion & Fleet" to "Campaign Expansion".
**v12.0**: Phase 3 COMPLETE (all 5 cycles). Phase 4 restructured: 3 cycles (Planet Infrastructure, Mini-Game Depth & Polish, Smuggling). New `requirements/12_minigame_overhaul.md` details the mini-game overhaul spec. Political/Espionage and Advanced Trading deferred to Phase 5. Ground Exploration deferred to Phase 5.2 (prerequisite for Act One Chapters 3-5). 1088 tests, 26 views, 26 skills across 5 trees, 21 achievements, 13 enemy templates, 12 encounter definitions.
**v11.0**: Cycle 3.1 Speech & Social System implemented — SocialSkill/SocialManager, dialogue skill checks with SkillCheck dataclass, NPC disposition, DialogueView visual feedback, save/load integration. 423 tests, 19 views.
**v10.0**: Expanded Phase 3-6 roadmap to incorporate narrative arc systems from campaign_act_one.md. Phase 3: Speech & Social, Random Encounters, Space Combat, Ground Exploration, Act One Completion. Phase 4: Planet Infrastructure, Political & Espionage, Smuggling & Contraband, Idle Resource Generation, Advanced Trading. Phase 5: Fleet Management, Campaign Acts Two & Three. Phase 6: Polish & Release (audio, visuals, distribution). Save system wiring fixed (event routing, rendering, update in game loop), main menu Continue/Load Game enabled, galaxy map Save button added.
**v9.0**: Campaign Act One Missions 01-02 implemented (Bill of Landing, Iron Ore Delivery), trade permit system, player name input, intro narration, auto-trigger dialogues, AcceptCargo system, non-sticky collect_cargo, narrator mode in DialogueView. 19 views, 10 missions, 346 tests.
**v8.0**: Cycle 2.4 implemented (Leadership & Operations skill tree — 5 skills, 4-tree layout, all bonuses consumed), Phase 2 COMPLETE, updated test count (338), 23 skills across 4 trees
**v7.0**: Cycle 2.3 implemented (crew system — 4 crew members, CrewRoster, CrewRosterView, recruitment missions, bonus stacking), updated test count (333), 18 views
**v6.0**: Cycle 2.2 implemented (dialogue/NPC + mission framework), updated test count (308), 17 views
**v5.0**: Cycle 2.1 implemented (faction reputation), dialogue/NPC infrastructure for 2.2, updated test count (287), 16 views
**v4.0**: Updated current state (3 skill trees/18 skills, 220 tests, mining overhaul with click-to-mine + drones, BUY MAX/SELL MAX), renamed Cycle 2.4 to "Fourth Skill Tree"
**v3.0**: Added architecture guidance, key decisions, and acceptance criteria for all Phase 1 and Phase 2 cycles
**v2.0**: Rewrote to reflect current implementation status, reorganized phases
**v1.0** (2025-10-19): Original roadmap with Phase 1-3 planning
