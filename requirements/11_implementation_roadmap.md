# Implementation Roadmap

## Document Overview

This roadmap tracks the implementation status of SpaceGame, organized into completed work and future phases. Each future phase builds on the previous, expanding from the current core trading game into RPG/campaign systems.

**Last Updated**: 2026-02-27

---

## Current Status

The core game is feature-complete with a robust trading, exploration, and progression loop. Phase 1 polish features (event display, achievements, tutorial) are implemented. Phase 2 RPG foundation is complete: factions, dialogue/missions, crew, and leadership skill tree. Campaign Act One (Missions 01-02) is implemented with trade permit system, intro narration, player name input, and two story missions.

### What's Built

**Galaxy & World**
- 10 star systems across multiple quadrants with distinct economies
- 19 tradeable commodities across basic, industrial, and luxury categories
- Dynamic pricing with supply/demand tags and market events (shortage, surplus, disaster, boom)
- Danger levels (safe, moderate, dangerous) per system
- Turn-based travel with fuel costs based on distance

**Gameplay Systems**
- Full buy/sell trading at stations with BUY MAX / SELL MAX buttons and dynamic activity buttons
- Mining mini-game (6x4 asteroid grid, 4 rock types, click-to-mine with passive drill and 3-tier drone automation)
- Salvaging puzzle (5x5 grid scanning, 3 item types, charge-based extraction)
- Refining system (6 recipes, job queue with up to 5 concurrent jobs, real-time processing)
- Ship purchase and comparison at the shipyard

**Progression**
- 10-level XP system with cumulative thresholds (0-5200 XP)
- 4 skill trees: Trading Mastery (5 skills), Resource Gathering (5 skills), Mining Mastery (8 skills), Leadership & Operations (5 skills) — 23 skills total
- Mining skill tree unlocks 3 drone tiers, click power, passive drill speed, ore targeting
- Skill prerequisites and multi-level skills with stacking bonuses
- 5 ship upgrades with 3-slot system per ship (cargo, fuel, engine, mining, scanner)
- 21 achievements across 6 categories with varied rewards (XP, credits, skill points)

**Ships**
- 6 ship classes: Shuttle, Light Freighter, Medium Freighter, Fast Courier, Bulk Hauler, Luxury Yacht
- Cargo capacity (50-600), fuel system, speed multipliers, special abilities

**Player Experience**
- Event notification system: modal dialogs for DISASTER events, timed banners for SHORTAGE/SURPLUS/BOOM
- Event indicators on galaxy map (pulsing warning dots) and event details in system info panel
- Active event banners in trading view showing current system's event
- Event log (last 15 events, persisted across saves)
- Statistics view with categorized player stats (Economic, Exploration, Activities, Progression)
- Achievements view with progress bars, locked/unlocked state, and reward info
- 5-step tutorial system with auto-trigger on new game, skip option, and replay from settings

**Infrastructure**
- Save/Load system with 12 slots (slot 0 = autosave), JSON format with version field
- Save metadata (timestamp, credits, location, playtime)
- 19 views: main menu, galaxy map, trading, mining, salvage, refining, skill tree, shipyard, save/load, settings, pause menu, startup, statistics, achievements, event notification, dialogue, mission log, crew roster, name input
- Particle system (object-pooled, 8 presets including CLICK_HIT and DRONE_SPARK), screen transitions (fade, warp, slide)
- Animated parallax backgrounds with procedural generation
- Screen effects (vignette, screen shake)
- Comprehensive test suite (346 tests) covering models, data loading, achievements, tutorial, events, drones, mining, factions, dialogue, missions, crew, leadership skills, and campaign

### Implementation Notes

Several systems were simplified from original spec during implementation:
- **Skill trees**: 4 trees with 23 skills (Trading 5, Gathering 5, Mining 8, Leadership 5). The original spec proposed 3 trees with 15 skills — Mining tree was added with 8 skills for drone/click mechanics, Leadership tree added after crew and faction systems were built.
- **Levels**: 10-level cap (original spec proposed 20). The current curve provides meaningful progression without requiring the unbuilt RPG systems for XP sources.
- **Upgrades**: 5 upgrades with flat bonuses and a 3-slot limit (original spec proposed 15+ upgrades with percentage multipliers and tiered variants). Current system is clean and balanced.
- **Ship purchase**: Integrated into shipyard view rather than a separate dealership view.
- **Market events**: Fully implemented with tiered notifications (modal for DISASTER, banner for others), galaxy map indicators, trading view banners, and persistent event log.

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

**Dialogue infrastructure**: NPC model (`spacegame/models/dialogue.py`), dialogue tree data structure with branching responses and flag-setting, DialogueManager state machine, DialogueView with portrait placeholders (colored rect + initials), typewriter text reveal, clickable response buttons. 4 placeholder NPCs (Elena Reeves at Nexus Prime, Marcus Jin at Breakstone, Dr. Yara Osei at Axiom Labs, Kael Drifter at Haven's Rest) with intro conversations. TALK buttons appear in trading view when NPCs are present. Dialogue flags persist through save/load. 31 dialogue tests.

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

**Crew members**: Elena Reeves (Navigator — fuel efficiency/fuel bonuses), Marcus Jin (Engineer — cargo/fuel bonuses), Dr. Yara Osei (Scientist — scan charges/extract speed/rare chance), Kael Drifter (Trader — buy price reduction/sell price bonus). Each has 3 abilities unlocking at levels 1, 3, and 5. Max level 5 with XP thresholds [0, 50, 150, 350, 700].

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

## Phase 3 (Future): Campaign & Depth

**Goal**: Full story campaign and advanced game systems
**Priority**: Low — long-term vision

### 3.1 Campaign Acts II & III
- Complete the 3-act story campaign (15-20 hours total)
- Branching story paths and multiple endings
- 5-10 additional crew members with personal quests

### 3.2 Fleet Management
- Own and manage multiple ships
- Assign crew to different ships
- AI-controlled trade routes for owned fleet
- Fleet view UI

### 3.3 Combat System
- Ship-to-ship encounters (pirates, hostile factions)
- Combat resolution (turn-based or real-time)
- Ship weapons and defensive systems
- Risk/reward for dangerous routes

### 3.4 Advanced Trading
- Trade contracts and futures
- Smuggling and contraband (illegal commodities)
- Trade route automation
- Black market locations

---

## Phase 4 (Future): Polish & Release

### 4.1 Audio
- Sound effects for trading, mining, salvage, travel, UI
- Background music per system/situation
- Ambient audio

### 4.2 Visual Polish
- Ship sprites/artwork
- NPC portraits
- System background artwork
- UI animations and transitions refinement

### 4.3 Performance & Distribution
- Performance optimization and profiling
- Installer/packaging
- Marketing materials

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

**Phase 1 Success**:
- New players can learn the game without external help
- Players have clear goals via statistics and achievements
- Market events feel impactful and visible

**Phase 2 Success**:
- RPG systems feel integrated, not bolted on
- Faction choices create meaningful trade-offs
- Campaign missions provide narrative motivation
- At least one crew member enhances gameplay

**Phase 3+ Success**:
- 15-20 hour campaign playthrough
- Fleet management adds strategic depth
- Combat encounters add tension to exploration

---

**Document Status**: v9.0
**Last Updated**: 2026-02-27
**v9.0**: Campaign Act One Missions 01-02 implemented (Bill of Landing, Iron Ore Delivery), trade permit system, player name input, intro narration, auto-trigger dialogues, AcceptCargo system, non-sticky collect_cargo, narrator mode in DialogueView. 19 views, 10 missions, 346 tests.
**v8.0**: Cycle 2.4 implemented (Leadership & Operations skill tree — 5 skills, 4-tree layout, all bonuses consumed), Phase 2 COMPLETE, updated test count (338), 23 skills across 4 trees
**v7.0**: Cycle 2.3 implemented (crew system — 4 crew members, CrewRoster, CrewRosterView, recruitment missions, bonus stacking), updated test count (333), 18 views
**v6.0**: Cycle 2.2 implemented (dialogue/NPC + mission framework), updated test count (308), 17 views
**v5.0**: Cycle 2.1 implemented (faction reputation), dialogue/NPC infrastructure for 2.2, updated test count (287), 16 views
**v4.0**: Updated current state (3 skill trees/18 skills, 220 tests, mining overhaul with click-to-mine + drones, BUY MAX/SELL MAX), renamed Cycle 2.4 to "Fourth Skill Tree"
**v3.0**: Added architecture guidance, key decisions, and acceptance criteria for all Phase 1 and Phase 2 cycles
**v2.0**: Rewrote to reflect current implementation status, reorganized phases
**v1.0** (2025-10-19): Original roadmap with Phase 1-3 planning
