# QA Audit Report — SpaceGame

**Date**: 2026-03-16
**Scope**: Full codebase review — models, views, engine, data files, tests
**Methodology**: 8 parallel specialist audits + verification pass

### Sprint 1 Status (COMPLETED)
- 2.1 Hull/shields clamping — **FIXED** (combat_engine.py)
- 2.2 Ground mission stats — **FIXED** (game.py)
- 5.1 Ship model tests — **DONE** (51 tests in test_ship.py)
- 1.1 Trade route tracker — **FALSE POSITIVE** (already serialized at save_manager.py:319-364)
- 3.1 Investment deduction — **FALSE POSITIVE** (investment_view.py:322 handles it)
- 4.1 DialogueView _destroy_ui — **FALSE POSITIVE** (_ResponseButton is custom-rendered, not pygame_gui)

### Sprint 2 Status (COMPLETED)
- 1.2 Atomic save writes — **FIXED** (save_manager.py: write to .tmp then os.replace)
- 1.3 DataLoader error handling — **FIXED** (data_loader.py: _safe_load wrapper with file/field context)
- 1.4 Tomas faction_id — **FIXED** ("free_alliance" → "frontier_alliance" in crew_members.json)
- 2.3 Rare ore chance cap — **FIXED** (mining.py: effective_rare capped at 2.0)
- 3.2 Respec cost — **FIXED** (progression.py: 100 CR × level, skill_tree_view deducts)
- 3.3 Achievement reward guard — **FIXED** (achievement_manager.py: _rewarded_ids prevents double-apply)
- 6.3 Crew slot validation on load — **FIXED** (save_manager.py: logs warning if crew > slots)
- 3.4 Repeatable missions — **SKIPPED** (dead feature, no data files use repeatable: true)
- 6.2 Price history div-by-zero — **FALSE POSITIVE** (already guarded with max(1, first_price))

### Sprint 3 Status (COMPLETED)
- 4.2 Scroll offset upper bound — **FIXED** (achievements_view.py: _clamp_scroll() method added)
- 5.2 Save/load round-trip tests — **DONE** (27 tests in test_save_roundtrip.py)
- 5.3 Integration tests — **DONE** (13 tests in test_integration_loops.py: trade, progression, achievement, crew, travel)
- 5.4 View cleanup tests — **DONE** (8 tests in test_view_cleanup.py + found/fixed SettingsView leak)
- 6.1 Player name validation — **FIXED** (name_input_view.py: 20 char limit, alphanumeric + spaces only)
- 4.3 Tab click hitboxes — **SKIPPED** (no action needed per audit: currently correct, fragile only if responsive layout added)

---

## Severity Legend

| Level | Meaning |
|-------|---------|
| **CRITICAL** | Game-breaking bug, data loss risk, or exploit that undermines core systems |
| **HIGH** | Significant gameplay bug or architectural flaw that affects player experience |
| **MEDIUM** | Functional issue, missing validation, or gap that could cause edge-case problems |
| **LOW** | Polish issue, minor inconsistency, or improvement opportunity |

---

## Group 1: Data Integrity & Save System

### 1.1 — Trade route tracker not serialized [HIGH]
**File**: `spacegame/save_manager.py`
**Issue**: `TradeRouteTracker` state is not included in save/load. Players lose all tracked trade route data on save and reload.
**Fix**: Add `trade_route_tracker.to_dict()` / `from_dict()` to the save/load chain.

### 1.2 — No atomic writes for save files [MEDIUM]
**File**: `spacegame/save_manager.py:144-146`
**Issue**: Save writes directly to the target file. A crash or power loss mid-write corrupts the save with no recovery path.
**Fix**: Write to a `.tmp` file first, then `os.replace()` to the target path (atomic on all platforms). Optionally keep one `.bak` of the previous save.

### 1.3 — No error handling in DataLoader JSON parsing [MEDIUM]
**File**: `spacegame/data_loader.py`
**Issue**: Malformed JSON or missing required fields in data files cause unhandled exceptions at startup with no indication of which file or field failed.
**Fix**: Wrap JSON loads in try/except with file path context. Validate required fields and raise clear `DataLoadError` with file + field info.

### 1.4 — Tomas Drifter has invalid faction_id [MEDIUM]
**File**: `data/crew/crew_members.json`
**Issue**: Tomas's entry uses `"faction_id": "free_alliance"` which doesn't match any defined faction. Should be `"frontier_alliance"` or left empty.
**Fix**: Correct to `"frontier_alliance"` (matches his lore as a Frontier Alliance-adjacent drifter).

---

## Group 2: Combat System

### 2.1 — Hull and shields can go negative [CRITICAL]
**File**: `spacegame/models/combat_engine.py:645-651`
**Issue**: After applying damage, neither `hull` nor `shields` is clamped to `max(0, ...)`. Negative values propagate through combat math, potentially causing incorrect damage routing, display bugs, and division anomalies.
**Fix**: Add `self.hull = max(0, self.hull)` and `self.shields = max(0, self.shields)` after every damage application. Apply to both player and enemy combatants.

### 2.2 — Ground mission completion flags not set [HIGH]
**File**: `spacegame/engine/game.py:2531-2624`
**Issue**: `_apply_ground_result()` processes loot, XP, and outcomes but never sets the mission's completion flag. Ground missions can be replayed indefinitely for infinite rewards.
**Fix**: After successful ground mission outcome, set the mission completion flag via the mission manager (e.g., `self.mission_manager.complete_mission(mission_id)`).

### 2.3 — Rare ore chance bonus not clamped [MEDIUM]
**File**: `spacegame/models/mining.py:405-410`
**Issue**: Stacking multiple rare ore chance bonuses (skills + crew + upgrades) could push the probability above 1.0, which while not crashing would make every ore hit "rare" — breaking economy balance.
**Fix**: Clamp the final rare chance: `rare_chance = min(rare_chance, 0.5)` (or whatever the design cap should be).

---

## Group 3: Economy & Progression

### 3.1 — Investment credits not deducted by model [HIGH]
**File**: `spacegame/models/investment.py:129-164`
**Issue**: The `invest()` method records the investment but does not call `player.remove_credits()`. Credits are only deducted if the caller (view/engine) remembers to do it separately. This is an architectural inconsistency — most other economic actions handle deduction internally.
**Fix**: Either have `invest()` accept and deduct from the player, or document and enforce the caller contract with a test that verifies credits decrease after investment.

### 3.2 — Respec has no cost or cooldown [MEDIUM]
**File**: `spacegame/models/progression.py:197-206`
**Issue**: `respec_skills()` is free and unlimited. Players can respec before every encounter to min-max for the situation, undermining build commitment.
**Fix**: Add a credit cost (e.g., `500 * level`) and/or a cooldown (once per N game days). Return `(False, "message")` if cost/cooldown not met.

### 3.3 — Achievement rewards can be applied multiple times [MEDIUM]
**File**: `spacegame/achievement_manager.py`
**Issue**: If `apply_rewards()` is called directly (bypassing the normal unlock check), rewards stack. While the normal flow prevents this, there's no guard in the method itself.
**Fix**: Add an `already_rewarded` set or check `is_unlocked` inside `apply_rewards()` before granting.

### 3.4 — Repeatable missions flag ignored [MEDIUM]
**File**: `spacegame/models/mission.py:310-324`
**Issue**: The `repeatable` field exists on missions but the completion check doesn't use it. Repeatable missions behave identically to one-time missions.
**Fix**: In the mission completion/availability logic, allow repeatable missions to reset their state after completion.

---

## Group 4: UI & View Lifecycle

### 4.1 — DialogueView missing _destroy_ui() [HIGH]
**File**: `spacegame/views/dialogue_view.py:179-181`
**Issue**: `on_exit()` calls `super().on_exit()` but doesn't call `_destroy_ui()`. pygame_gui elements created in `_create_ui()` are never killed, causing zombie UI elements that persist across state transitions and can intercept clicks.
**Fix**: Add `self._destroy_ui()` call in `on_exit()` before `super().on_exit()`, following the standard BaseView pattern used by all other views.

### 4.2 — Scroll offset not clamped to content bounds [LOW]
**File**: `spacegame/views/achievements_view.py:149`
**Issue**: `scroll_offset` is only clamped at `max(0, ...)` but has no upper bound. Players can scroll far past the last achievement into empty space.
**Fix**: Calculate max scroll from `len(filtered) * (card_height + spacing)` and clamp the upper bound.

### 4.3 — Tab click hitboxes don't account for scroll position [LOW]
**File**: `spacegame/views/achievements_view.py:195`
**Issue**: Tab rects are computed at render time from absolute screen positions, which is correct. However, if the tab bar ever scrolls or moves (e.g., window resize), the hitboxes would be stale. Currently not a problem but fragile.
**Fix**: No immediate action needed. Note for future if responsive layout is added.

---

## Group 5: Test Coverage Gaps

### 5.1 — Six core models completely untested [HIGH]
**Files**:
- `spacegame/models/ship.py`
- `spacegame/models/commodity.py`
- `spacegame/models/system.py`
- `spacegame/models/campaign_map.py`
- `spacegame/models/ground_crew.py`
- `spacegame/models/ground_enemy.py`

**Issue**: These models have zero dedicated test files. Ship damage routing, commodity price calculations, system connectivity, campaign map traversal, ground crew abilities, and ground enemy behavior are all untested.
**Fix**: Create test files for each. Priority order: `ship.py` (most complex, damage routing), `commodity.py` (economy foundation), `ground_crew.py`/`ground_enemy.py` (combat correctness), `system.py`, `campaign_map.py`.

### 5.2 — Save/load round-trip coverage incomplete [MEDIUM]
**Issue**: Save/load tests exist but don't cover all serialized subsystems. Missing coverage for: crew roster with new crew templates, investment portfolio, political state, achievement progress, trade route tracker (once serialized).
**Fix**: Add a comprehensive round-trip test that creates a fully-loaded player state, saves, loads, and asserts equality across all subsystems.

### 5.3 — No integration tests for multi-system interactions [MEDIUM]
**Issue**: Individual systems are tested in isolation, but interactions between systems (e.g., "complete a mission that triggers an achievement that grants credits that affect faction standing") are untested. These cross-system flows are where bugs hide.
**Fix**: Add 3-5 integration tests covering key gameplay loops:
1. Trade loop: buy → travel → sell → profit check → achievement trigger
2. Combat loop: encounter → fight → loot → XP → level up → skill point
3. Mission loop: accept → objectives → complete → rewards → faction rep
4. Ground loop: deploy → explore → loot → crew bonuses applied
5. Crew loop: recruit → bonuses active → dismiss → bonuses removed

### 5.4 — View tests don't verify UI element cleanup [LOW]
**Issue**: View tests call `on_enter()` and test rendering but rarely call `on_exit()` and verify that all pygame_gui elements are killed. This means issues like 4.1 (DialogueView) slip through.
**Fix**: Add a standard test pattern for each view: `on_enter()` → verify elements created → `on_exit()` → verify all elements killed (no zombie UI).

---

## Group 6: Edge Cases & Robustness

### 6.1 — No validation on player name length or characters [LOW]
**Issue**: Player name input has no length limit or character filtering. Extremely long names could overflow UI elements. Special characters could cause issues in save file paths.
**Fix**: Clamp name to 20 characters, allow only alphanumeric + spaces.

### 6.2 — Division by zero possible in price history calculations [MEDIUM]
**Issue**: Price history trend calculations divide by previous price. If a commodity's historical price is 0 (theoretically possible with extreme market events), this throws.
**Fix**: Guard division with `if prev_price > 0` check.

### 6.3 — Crew slot overflow not validated at load time [MEDIUM]
**Issue**: Ship crew capacity is enforced during recruitment but not validated when loading a save. If a player saved with a larger ship, then the save is loaded with a ship downgrade (modded save or data change), crew count could exceed slots.
**Fix**: On save load, validate `len(crew) <= ship.crew_slots`. If exceeded, log a warning and keep the crew (don't silently delete).

### 6.4 — Music/SFX systems referenced but not implemented [LOW]
**Issue**: Several views reference audio playback methods or config values that don't exist yet. These are guarded by try/except or hasattr checks, but the dead code paths add noise.
**Fix**: No action needed until Phase 6.5 (Audio). Note: clean up placeholder references during audio implementation.

---

## Recommended Fix Order

### Sprint 1: Critical & High (Game-Breaking)
| # | Issue | Effort |
|---|-------|--------|
| 2.1 | Hull/shields negative clamping | Small |
| 2.2 | Ground mission completion flags | Small |
| 4.1 | DialogueView _destroy_ui | Small |
| 1.1 | Trade route tracker serialization | Medium |
| 3.1 | Investment credit deduction | Medium |
| 5.1 | Core model test coverage (ship.py first) | Large |

### Sprint 2: Medium (Correctness & Safety)
| # | Issue | Effort |
|---|-------|--------|
| 1.2 | Atomic save writes | Small |
| 1.3 | DataLoader error handling | Medium |
| 1.4 | Tomas faction_id fix | Small |
| 2.3 | Rare ore chance clamping | Small |
| 3.2 | Respec cost/cooldown | Medium |
| 3.3 | Achievement reward guard | Small |
| 3.4 | Repeatable missions | Medium |
| 6.2 | Price history div-by-zero | Small |
| 6.3 | Crew slot validation on load | Small |

### Sprint 3: Polish & Coverage
| # | Issue | Effort |
|---|-------|--------|
| 4.2 | Scroll offset upper bound | Small |
| 5.2 | Save/load round-trip tests | Medium |
| 5.3 | Integration tests | Large |
| 5.4 | View cleanup tests | Medium |
| 6.1 | Player name validation | Small |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 5 |
| MEDIUM | 10 |
| LOW | 5 |
| **Total** | **21** |

The codebase is well-structured with strong conventions (TDD, BaseView lifecycle, data-driven design). The issues found are typical of a game at this stage of development — edge cases in combat math, serialization gaps, and test coverage holes in older models. No systemic architectural problems were found. The recommended fix order prioritizes data integrity and game-breaking bugs first, then correctness, then polish.
