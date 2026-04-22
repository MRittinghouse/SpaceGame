# Questing Overhaul Roadmap (Q1-Q8)

## Context

Playtester feedback revealed multiple quest-blocking bugs, a combat crash, and UI issues. Root cause analysis shows these stem from three systemic weaknesses: (1) no cross-reference validation between JSON data files, (2) quest activation timing gaps in save/load and dialogue flows, and (3) insufficient integration testing of end-to-end quest flows. Beyond fixes, the player's experience reveals opportunities to make quests more discoverable, NPCs more alive, and the quest pipeline more robust for future content.

This roadmap addresses immediate bugs first, then builds testing infrastructure that prevents regression, then improves quest systems and game design.

## Phases

### Q1: Critical Bugfixes (Data + Code)
### Q2: Data Validation Test Suite
### Q3: End-to-End Quest Flow Tests
### Q4: Quest Activation & Save/Load Reliability
### Q5: Combat & UI Bugfixes
### Q6: Quest System Robustness & Developer Tooling
### Q7: Quest Journal & Player Guidance Improvements
### Q8: NPC & Dialogue Expansion (Living World)

---

## Q1: Critical Bugfixes

**Goal**: Fix the 4 data bugs that directly block playtester quest progression.

### Q1.1 — Miner's Plight commodity ID mismatch
- **File**: `data/missions/side_missions.json` (miners_plight objective)
- **Bug**: `target_id: "medicine"` -- no commodity with that ID exists
- **Fix**: Change to `"medical"` (Medical Supplies, ID confirmed in `data/economy/commodities.json`)
- **Test**: Write `test_miners_plight_commodity_exists` in Q2

### Q1.2 — Sgt. Mossa auto_trigger chicken/egg
- **File**: `data/characters/npcs.json` (dock_investigator NPC)
- **Bug**: `auto_trigger_prerequisites: ["the_dead_ledger_accepted"]` -- this flag is never set by any dialogue or game action, so Mossa never appears
- **Fix**: Remove `auto_trigger_prerequisites` and `auto_trigger_gate_flag` from Mossa. Instead, gate Mossa's visibility on `iron_ore_delivered` (same gate as other post-early-game NPCs). The Dead Ledger quest itself already has `available_after: "iron_delivery"` so the station board posting controls timing. Mossa should be a regular cantina NPC the player can talk to after accepting the quest.
- **Test**: Write `test_all_npc_prerequisite_flags_settable` in Q2

### Q1.3 — The Stowaway missing encounter
- **File**: `data/encounters/generic.json` (new encounter), `data/dialogue/dialogues.json` (new dialogue tree)
- **Bug**: Quest has `discovery_method: "encounter"` but no encounter definition exists. The `stowaway_discovered` flag is never set.
- **Fix**: Create a cargo-type encounter with 3 choices matching the quest design:
  1. Turn them in at next port (bounty credits)
  2. Drop them at Haven's Rest (reputation with Frontier Alliance)
  3. Put them to work (temporary crew stat bonus for 5 jumps)
  - All paths set `stowaway_discovered` and `stowaway_resolved` flags
- **Test**: Write `test_encounter_triggered_quests_have_encounters` in Q2

### Q1.4 — Elena Old Charts guidance
- **File**: `data/missions/crew_quests.json` (elena_old_charts), `data/dialogue/crew_quest_dialogues.json`
- **Bug**: Player reaches Stellaris Port but doesn't know how to trigger the archives dialogue. The dialogue exists (`elena_archives_dialogue`) but the trigger mechanism is unclear.
- **Fix**:
  - Update hint text: "Travel to Stellaris Port with Elena in your crew, then speak with her at the cantina."
  - Verify the crew quest dialogue auto-trigger fires on arrival at Stellaris Port with Elena in party
  - If auto-trigger isn't working, add Elena as a temporary cantina NPC at Stellaris Port when the quest is active

---

## Q2: Data Validation Test Suite

**Goal**: Build cross-referencing tests that validate ALL JSON data relationships. These tests run against real game data and would have caught every data bug in Q1.

### New file: `tests/test_data/test_cross_references.py`

**Commodity validation:**
- Every `collect_cargo` objective `target_id` exists in commodities
- Every `on_accept_cargo` commodity_id exists in commodities
- Every `remove_cargo` reward `target_id` exists in commodities

**NPC validation:**
- Every `talk_to_npc` objective `target_id` exists in NPCs
- Every NPC `dialogue_id` references a valid dialogue tree
- Every NPC `home_system_id` exists in systems
- Every NPC `faction_id` (if set) exists in factions

**System validation:**
- Every `reach_system` objective `target_id` exists in systems
- Every mission `available_at` system exists
- Every ground_mission_system_id exists

**Mission chain validation:**
- Every `prerequisites` mission ID exists as a loadable mission
- Every `available_after` mission ID exists
- Every `available_before` mission ID exists
- No circular prerequisite chains (topological sort)

**Flag reachability validation:**
- Every `required_flags` entry on a mission can be set by at least one: dialogue `set_flag`, mission reward `set_flag`, skill check flag, or game.py hardcoded flag
- Every NPC `auto_trigger_prerequisites` flag can be set by something

**Encounter-quest validation:**
- Every mission with `discovery_method: "encounter"` has a corresponding encounter that can set the discovery flag

### New file: `tests/test_data/test_dialogue_integrity.py`

**Node reachability:**
- Every dialogue tree's `start_node_id` exists in its nodes
- Every `next_node_id` in responses references a valid node in the same tree
- Every `success_node_id`/`failure_node_id` in skill checks references valid nodes
- No orphan nodes (unreachable from start via BFS)
- Every path eventually reaches a terminal node (no infinite loops)

**Flag consistency:**
- Every `required_flags` and `excluded_flags` in dialogue responses references a flag that can be set somewhere in the game
- Flag names follow consistent naming convention (snake_case)

### Files affected
- `tests/test_data/test_cross_references.py` (new, ~400 lines)
- `tests/test_data/test_dialogue_integrity.py` (new, ~250 lines)

---

## Q3: End-to-End Quest Flow Tests

**Goal**: Test the full player journey through representative quest types. These are integration tests that wire up real models (MissionManager + DialogueManager + Player) and simulate complete quest flows.

### New file: `tests/test_integration/test_quest_flows.py`

**Campaign quest flow:**
- Start with bill_of_landing available
- Accept -> collect cargo -> talk to NPC -> complete -> verify rewards + next quest unlocks

**Side mission NPC-discovery flow:**
- Complete prerequisite campaign mission
- Simulate dialogue with side quest NPC (set acceptance flag)
- Verify mission transitions UNAVAILABLE -> AVAILABLE -> ACTIVE (via auto_accept)
- Complete objectives
- Verify rewards applied and completion flag set
- **This test would have caught bug #4 (Neve/Petra/Cassiel activation)**

**Side mission station-board flow:**
- Mission becomes available at system
- Accept from board
- Complete objectives
- Verify completion

**Crew quest flow:**
- Recruit crew member
- Reach loyalty threshold (simulate loyalty flag)
- Verify crew quest activates
- Complete objectives via dialogue flags
- Verify stage 1 complete flag enables stage 2

**Save/load mid-quest flow:**
- Set quest flags via dialogue
- Save game state (mission_manager.get_state() + player.dialogue_flags)
- Recreate MissionManager from saved state
- Call update_availability with saved flags
- Verify quest status is correct after reload

**Forced encounter flow:**
- Accept mission with forced_encounter
- Verify encounter triggers during travel to target system
- Verify encounter doesn't re-trigger after flag is set

### Files affected
- `tests/test_integration/test_quest_flows.py` (new, ~500 lines)
- May need small test helper utilities

---

## Q4: Quest Activation & Save/Load Reliability

**Goal**: Fix the systemic quest activation bug and combat flee routing.

### Q4.1 — update_availability after save/load
- **File**: `spacegame/engine/game.py` (~line 3457-3460)
- **Bug**: `update_availability()` is in an `else` branch -- only runs for new games, NOT after `load_state()`. If flags were set before save but mission status wasn't updated, the mission stays stuck as UNAVAILABLE after reload.
- **Fix**: Call `update_availability(self.player.dialogue_flags)` unconditionally after both `load_state()` and new game init.

### Q4.2 — Debug logging in update_availability
- **File**: `spacegame/models/mission.py` (update_availability method)
- **Fix**: Add `logger.debug()` calls that log each UNAVAILABLE mission's condition evaluation:
  ```
  Mission {mid}: prereqs_met={prereqs_met}, flags_met={flags_met}, after_met={after_met}
  ```
  This makes future debugging trivial.

### Q4.3 — Combat flee return state
- **File**: `spacegame/engine/game.py` (encounter->combat transition), `spacegame/views/combat_view.py`
- **Bug**: Fleeing combat during travel returns to TRADING instead of GALAXY_MAP. The `_resume_travel_after_encounter` flag on galaxy_map_view is set but not checked when routing combat exit.
- **Fix**: When starting combat from a travel encounter, explicitly pass `return_state=GameState.GALAXY_MAP` to the combat view. Audit the encounter->combat->return chain to ensure the galaxy map's travel resume logic fires.

### Q4.4 — Verify dialogue-end mission activation covers all paths
- **File**: `spacegame/engine/game.py` (~line 1256-1276)
- **Audit**: Verify that every dialogue exit path (normal end, skill check end, auto-trigger end) runs the flag sync + update_availability sequence. Currently confirmed for the main path at line 1273-1276, but check edge cases.

### Tests
- Tests from Q3 cover the activation scenarios
- Add specific test for save/load + update_availability interaction
- Add test for combat return state during travel encounters

### Files affected
- `spacegame/engine/game.py` (save/load fix, combat return state)
- `spacegame/models/mission.py` (debug logging)
- `spacegame/views/combat_view.py` (return state audit)

---

## Q5: Combat & UI Bugfixes

**Goal**: Fix the multi-ship combat crash and crew roster UI overlap.

### Q5.1 — Multi-ship combat IndexError
- **File**: `spacegame/views/combat_view.py`
- **Bug**: When one enemy is defeated in multi-ship combat, `selected_target_idx` can reference an invalid index. Animation calculations, flash timers, and shield ripple effects access `state.enemies[idx]` without bounds checking.
- **Fix**:
  - Add bounds clamping: `self.selected_target_idx = min(self.selected_target_idx, len(state.enemies) - 1)` immediately when an enemy is removed
  - Call `_auto_advance_target()` as part of enemy death handling, BEFORE animation processing
  - Audit all `enemies[...]` accesses in the render path (grep shows ~15 such accesses) -- add bounds checks to each
  - Ensure `_enemy_flash_timers` list length stays in sync with `state.enemies` length

### Q5.2 — Crew roster dismiss button overlap
- **File**: `spacegame/views/crew_roster_view.py` (~line 205-206)
- **Bug**: Dismiss button at fixed Y position overlaps last 2 attribute rows for companions with many abilities
- **Fix**: Position the dismiss button dynamically based on rendered content height, OR move it to a fixed position outside the scrollable content area (e.g., bottom-right of detail panel with guaranteed clearance), OR make the detail panel scrollable with the button anchored outside the scroll region.

### Tests
- Test that defeating one enemy in multi-ship combat doesn't crash (model-level test with CombatState)
- Verify crew roster layout doesn't overlap (bounds check test if feasible)

### Files affected
- `spacegame/views/combat_view.py`
- `spacegame/views/crew_roster_view.py`

---

## Q6: Quest System Robustness & Developer Tooling

**Goal**: Add runtime validation, warnings, and content authoring tools.

### Q6.1 — DataLoader.validate() method
- **File**: `spacegame/data_loader.py`
- Run after `load_all()` -- cross-references all IDs and logs warnings for mismatches
- Non-fatal: game still runs, but bad data surfaces immediately in console
- Covers: commodity IDs, NPC IDs, dialogue IDs, system IDs, mission prerequisites, flag reachability
- Reuses the same logic as Q2 tests but runs at game startup

### Q6.2 — Quest validation CLI tool
- **File**: `tools/validate_quests.py` (new)
- Standalone script that loads all data and runs full validation suite
- Outputs human-readable report with errors and warnings
- Content authors run this before committing JSON changes
- Exit code 0 = clean, 1 = has errors

### Q6.3 — Auto-flag resolution warning
- **File**: `spacegame/models/mission.py` (check_objectives, ~line 452-468)
- The auto-flag resolution for side missions silently sets HAS_FLAG objectives when all non-flag objectives are done. This masks content bugs.
- Add `logger.warning(f"Auto-resolved HAS_FLAG objective '{obj.target_id}' for mission '{mid}' -- consider adding proper flag-setting in dialogue/encounters")`
- This alerts developers without changing behavior

### Q6.4 — Mission state audit on day advance
- **File**: `spacegame/engine/game.py` (_advance_day)
- After update_availability, log a summary: how many missions per status, any that transitioned
- Helps diagnose quest progression issues in player saves

### Files affected
- `spacegame/data_loader.py` (validate method)
- `spacegame/models/mission.py` (warnings)
- `spacegame/engine/game.py` (audit logging)
- `tools/validate_quests.py` (new)

---

## Q7: Quest Journal & Player Guidance Improvements

**Goal**: Help players understand what to do next. Address the UX gap where quests activate but players don't know how to progress.

### Q7.1 — Enhanced mission log objectives display
- **File**: `spacegame/views/mission_log_view.py`
- Show clear checkmarks for completed objectives, highlight next incomplete objective
- Show the mission hint text prominently
- For `talk_to_npc` objectives, show NPC name and home system
- For `reach_system` objectives, show system name
- For `collect_cargo` objectives, show current/required quantity

### Q7.2 — Contextual quest hints at stations
- **File**: `spacegame/models/mission.py` (new method), `spacegame/views/station_hub_view.py`
- New method: `get_contextual_hints(current_system_id) -> list[str]`
  - Returns hints for any active mission with objectives completable at the current system
  - Example: "Sgt. Mossa is here -- she has information about the Dead Ledger case."
- Display in station hub view, below station chatter

### Q7.3 — Quest waypoints on galaxy map
- **File**: `spacegame/models/mission.py`, `spacegame/views/galaxy_map_view.py`
- Extend `get_active_target_systems()` to also include:
  - Systems where `talk_to_npc` objectives can be completed (lookup NPC home_system_id)
  - Systems where `collect_cargo` objectives have favorable market prices (optional, stretch)
- Render distinct markers: objective markers (where you need to go) vs. current quest markers

### Q7.4 — Mission accepted/completed feedback
- Verify mission acceptance notifications are visible and clear
- Add a brief "Quest Updated" notification when individual objectives complete
- Add a mission compass indicator in the cockpit HUD showing distance to nearest active objective

### Files affected
- `spacegame/models/mission.py` (contextual hints, waypoint expansion)
- `spacegame/views/mission_log_view.py` (enhanced display)
- `spacegame/views/station_hub_view.py` (contextual hints)
- `spacegame/views/galaxy_map_view.py` (waypoint markers)

---

## Q8: NPC & Dialogue Expansion (Living World)

**Goal**: Make the universe feel more alive through richer NPC interactions and dialogue variety.

### Q8.1 — NPC multi-state system
- **Current**: NPCs have binary show/hide via `auto_trigger_gate_flag` and `hide_after_flag`
- **Proposed**: Add optional `dialogue_states` array to NPC JSON schema:
  ```json
  "dialogue_states": [
    {"state": "pre_quest", "dialogue_id": "neve_intro", "conditions": {"flags_unset": ["price_of_info_accepted"]}},
    {"state": "quest_active", "dialogue_id": "neve_in_progress", "conditions": {"flags_set": ["price_of_info_accepted"], "flags_unset": ["price_of_info_complete"]}},
    {"state": "post_quest", "dialogue_id": "neve_resolved", "conditions": {"flags_set": ["price_of_info_complete"]}}
  ]
  ```
- NPC picks the first matching state; if no `dialogue_states` array, falls back to current behavior
- This allows NPCs to have different conversations at different quest stages without disappearing
- **Backward compatible**: existing NPCs without `dialogue_states` work unchanged

### Q8.2 — Disposition visibility
- **File**: `spacegame/views/dialogue_view.py`
- Show a relationship indicator next to NPC portrait during dialogue
- Use descriptive labels: "Stranger" (0-20), "Acquaintance" (21-40), "Friendly" (41-60), "Trusted" (61-80), "Close Ally" (81-100)
- Show disposition change feedback: "+5 Trust" floats up after positive dialogue choices

### Q8.3 — NPC reactions to player state
- Add contextual dialogue nodes gated on reputation, quest progress, or player stats
- Example: Neve comments on your faction standing if you've been doing work for Frontier Alliance
- This uses existing `required_flags` + `excluded_flags` system -- primarily a content task
- Write 2-3 contextual dialogue nodes per major NPC (Neve, Petra, Cassiel, Elena, Marcus)

### Q8.4 — Station atmosphere expansion
- Expand station chatter to react to more game events
- Add "news ticker" style updates about player actions ("A trader made a killing at Forgeworks today...")
- Gate chatter on quest completion flags for evolving station feel

### Q8.5 — Faction-gated missions (stretch)
- Add optional `required_reputation: {faction_id, min_reputation}` to Mission dataclass
- Check in `update_availability()` alongside flags and prerequisites
- Requires passing reputation data to the availability check
- Enables missions that only appear when player has built faction trust

### Files affected
- `spacegame/models/dialogue.py` (NPC state machine, backward compat)
- `spacegame/data_loader.py` (parse dialogue_states)
- `data/characters/npcs.json` (add dialogue_states to key NPCs)
- `data/dialogue/dialogues.json` (new dialogue trees for NPC states)
- `spacegame/views/dialogue_view.py` (disposition UI)
- `spacegame/models/mission.py` (faction gates)
- `data/crew/station_chatter.json` (expanded chatter)

---

## Phase Dependencies

```
Q1 (data bugfixes) --+-> Q2 (validation tests) --> Q6 (tooling)
                      +-> Q3 (flow tests)       --> Q7 (journal/guidance)
                      +-> Q4 (activation/routing)
                      +-> Q5 (combat/UI bugs)   --> Q8 (living world)
```

- Q1 is prerequisite for everything (fix what's broken)
- Q2, Q3, Q4, Q5 can proceed in parallel after Q1
- Q6 builds on Q2 (reuses validation logic)
- Q7 builds on Q3/Q4 (reliable quests before better UI)
- Q8 builds on everything (expansion after reliability)

## Testing Philosophy

Every phase follows TDD:
1. **Q1**: Fixes first (urgency), tests retroactively in Q2
2. **Q2-Q3**: Tests ARE the deliverable -- validation suite + integration tests
3. **Q4-Q5**: Write failing test -> fix bug -> verify test passes
4. **Q6-Q8**: Write tests for new features before implementing

Test categories:
- **Data validation** (Q2): Run against real JSON, catch ID mismatches
- **Integration flows** (Q3): Wire up real models, simulate player journeys
- **Unit tests** (Q4-Q8): Isolate specific behaviors with mocked data
- **Regression tests**: Every bug gets a test that would have caught it

## Q8 Expansion

Q8 has been expanded into a dedicated 8-sub-phase roadmap covering the full Living World dialogue overhaul. See `requirements/q8_living_world_roadmap.md` for complete details covering:
- SP1: Writing Guidelines & Dialogue Standards
- SP2: NPC Multi-State System
- SP3: Mechanical Consequence Retrofit (skill checks, disposition, faction rep)
- SP4: Disposition UI Visibility
- SP5: New NPCs for Underserved Systems (8 new atmosphere NPCs)
- SP6: Station Atmosphere Expansion (60 new chatter lines, flag-gated)
- SP7: Faction-Gated Mission Prerequisites
- SP8: Testing, Validation & Content Audit

## Verification Plan

After each phase:
1. Run `pytest` -- all tests pass
2. Run `ruff check spacegame/` -- no lint errors
3. Run `mypy spacegame/` -- no type errors
4. Manual playtest: verify the specific bugs/features addressed
5. For Q6: run `python tools/validate_quests.py` -- clean report
