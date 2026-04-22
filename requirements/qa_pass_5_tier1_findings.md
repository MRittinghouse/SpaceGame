# QA Pass 5 Tier 1 — Quick-Win Fixes

Generated 2026-04-21. Tier 1 closed out all 8 quick-win items from Pass 5 triage. Every item was a 1-20 line fix; collectively they unlock substantial narrative content that was previously unreachable.

**Bottom line:** 8 items resolved. 10+ campaign encounters unblocked. +2 new tests (regression guards). Test count 7,022 → 7,025.

---

## 1.1 — `completed_mission_5/10/15/20` milestone flags

**Fix:** Added campaign-completion counter in `engine/game.py`'s mission-completion handler. When a campaign mission completes, it counts all completed campaign missions and sets `completed_mission_N` (N ∈ {5, 10, 15, 20}) whenever the threshold is crossed.

**Unlocks:** 10 campaign encounters across `data/encounters/campaign.json` that gate on these flags (pirate_weapons_intel, sato_ghost, sato_returns, anomaly_deepens, larsen_warning, torres_tip, final_warning, guild_shadow, refugee_testimony, old_allies).

**Files:** `spacegame/engine/game.py`.

---

## 1.2 — `discovered_ledger_connection` producer

**Fix:** Added `set_flag` reward to mission `the_ledger` in `data/missions/missions.json`. This is the narratively correct moment — when the player first confirms the Ledger conspiracy with Dr. Osei.

**Unlocks:** 3 campaign encounters gated on this flag (`campaign_black_market_intel_01`, `campaign_final_warning_01`, `campaign_guild_shadow_01`).

**Files:** `data/missions/missions.json`.

---

## 1.3 — `black_market_access` reward_type ↔ dialogue_flag alignment

**Fix:** `Player.grant_black_market_access()` now also sets a global `dialogue_flags["black_market_access"]` so encounter `requires_flags` (which treats strings as flags) fires correctly. The per-system set is retained for system-specific gating.

**Unlocks:** Encounter `campaign_black_market_intel_01` (also needs `discovered_ledger_connection` which 1.2 fixes).

**Files:** `spacegame/models/player.py`.

---

## 1.4 — `met_torres` typo + `talked_to_larsen` producer

Two distinct fixes:

**Typo:** Encounter `campaign_torres_tip_01` referenced `met_torres` but the NPC's actual `auto_trigger_gate_flag` is `met_malia_torres`. Fixed the encounter to use the correct flag. **Files:** `data/encounters/campaign.json`.

**Missing producer:** Officer Larsen had no `auto_trigger_gate_flag` (intentionally — mission M01 handles his trigger per existing test). Added `set_flag: "talked_to_larsen"` to the first response in Larsen's dialogue tree instead. **Files:** `data/dialogue/dialogues.json`.

**Unlocks:** `campaign_torres_tip_01`, `campaign_larsen_warning_01`.

---

## 1.5 — `forgery_appraised` producer

**Fix:** Added `set_flag: "forgery_appraised"` to the "[Leave — complete the appraisal off-screen]" response on the `in_progress` node of the `cassiel_maren_forgery` dialogue. Represents the player completing the appraisal trip to Haven's Rest and returning to report.

**Unlocks:** The confrontation branch in Cassiel's dialogue (required_flags: forgery_appraised). Without this, players couldn't confront Cassiel about the forgeries, stalling the mission.

**Known residual concern:** The mission's auto-resolve behaviour in `mission.py` may set both `forgery_appraised` and `forgery_resolved` too aggressively (all-HAS_FLAG incomplete objectives get auto-set once non-HAS_FLAG objectives complete). That's a deeper design issue — filed as a Tier 3 item for a dedicated session rather than a Tier 1 quick-fix.

**Files:** `data/dialogue/dialogues.json`.

---

## 1.6 — Iron Dominion → Miners Union doc rename

**Fix:** Renamed reference in `combat_balance_design.md §4.6` from "Iron Dominion" (non-existent faction) to "Miners Union" (canon faction). Marked the §12 deferred item as RESOLVED with date.

**Files:** `requirements/combat_balance_design.md`.

---

## 1.7 — ActionQueue `slot_key` footgun test

**Fix:** Added `TestActionQueueMoveIdFootgun` class in `test_combat_golden.py` with two tests:
1. `test_unknown_move_id_logs_move_not_found_and_no_ops` — passing a slot_key-style string fails silently; engine emits the documented log line.
2. `test_correct_move_id_resolves_normally` — positive control.

Captures the combat_balance §12 B6 documented contract; future instrumentation (or agents) can't rediscover the footgun by accident.

**Files:** `tests/test_models/test_combat_golden.py`.

---

## 1.8 — Travel-encounter boss filter guard

**Fix:** Added defense-in-depth guard inside `check_travel_encounter()` that strips boss templates from the enemy pool before selecting. The DataLoader lookup is wrapped in try/except so tests using mock template IDs aren't broken.

**Guards against:** future callers forgetting the filter. Bosses now can't leak into random travel rolls regardless of how the caller composes the pool.

**Files:** `spacegame/models/encounter.py`.

---

## Pass 2 bug status update

After Tier 1, the Pass 2 findings tracker updates:

| Flag | Pass 2 Severity | Status |
|---|---|---|
| `completed_mission_5/10/15/20` | HIGH (4 flags) | ✅ **Fixed** — set by mission-completion handler |
| `discovered_ledger_connection` | HIGH | ✅ **Fixed** — `the_ledger` mission reward |
| `forgery_appraised` | HIGH | ✅ **Fixed** — dialogue response set_flag |
| `black_market_access` | MEDIUM | ✅ **Fixed** — `grant_black_market_access` updates flag |
| `met_torres` | MEDIUM | ✅ **Fixed** — typo corrected in encounter |
| `talked_to_larsen` | MEDIUM | ✅ **Fixed** — dialogue response set_flag |

**All 9 Pass 2 campaign-gate bugs resolved.** 10+ campaign encounters that were previously unreachable now fire at the intended progression points.

---

## Test count trajectory (end of Tier 1)

| Pass | Running Total |
|---|---|
| Pre-QA | 6,835 |
| Pass 2 | 6,849 |
| Pass 3 | 6,907 |
| Pass 3.5 | 6,936 |
| Pass 4A | 6,975 |
| Pass 4B | 7,022 |
| **Pass 5 Tier 1** | **7,025** |

**Delta:** +190 tests (+2.78%) across 6 QA phases. **12 real bugs found and fixed** (9 data/flag bugs + 1 combat defeat crash + 1 crew quest gating + 1 module ID drift from drydock catalogs, caught in Pass 2 validation).

---

## What's next

**Tier 2** (medium-effort items, 1-3 hours each):
- Phase Shift "first vs all attacks per round" implementation
- §6 round-count documentation revision
- Colorblind profile real values
- Legacy ShipType combat path documentation

**Tier 3** (multi-session features, require dedicated design sessions):
- `call_reinforcement`, `price_memory`+`TradeRouteTracker`, per-instance ShipComposite cache, ally-targeted heals, etc.

Ready for Tier 2 when you are.
