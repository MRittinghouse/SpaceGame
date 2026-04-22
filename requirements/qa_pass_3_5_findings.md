# QA Pass 3.5 — Model-Layer Scenario Closeout

Generated 2026-04-21. Closes the three remaining model-layer scenarios from the Pass 3 deferred list. The other three deferred scenarios (tutorial, mining, death/respawn) were formally routed to Pass 4 in `qa_pass_1_audit.md` because they're view-shaped.

**Bottom line:** 29 new scenario tests added, **one real bug found and fixed**, test count 6,907 → 6,936. Pass 3's coverage of model-layer integration is now comprehensive.

---

## Scenarios shipped

| File | Purpose | Tests |
|---|---|---|
| `test_scenario_trading.py` | Buy low → travel → sell high; cargo purchase prices survive travel; trade failure cases; market state mutations | 10 |
| `test_scenario_crew_quest.py` | Crew quests gate on crew membership; loyalty threshold flags fire on upward crossing only; per-companion quest coverage | 9 |
| `test_scenario_galaxy_events.py` | Event building from templates, chain triggering + delayed fire, max-active cap, deterministic generation | 10 |

All 29 tests green.

---

## Real bug found and fixed

### `DataLoader._parse_mission` drops `crew_member_id`

**Symptom:** every mission loaded through the DataLoader had `crew_member_id = ""`, even though `data/missions/crew_quests.json` sets it correctly (e.g., `"crew_member_id": "elena_reeves"`).

**Consequence:** `MissionManager.check_objectives` contains a guard:

```python
if mission.crew_member_id and mission.crew_member_id not in recruited_crew_ids:
    continue  # Skip crew quests whose crew member isn't in the party
```

Because `mission.crew_member_id` was always empty, the guard never fired. Result: **crew quests could progress even when the crew member wasn't recruited**. A player could complete Elena's entire questline by traveling to the right systems without ever having Elena aboard.

**Location:** `spacegame/data_loader.py` `_parse_mission` around line 1200. The Mission dataclass's own `from_dict` classmethod handled it correctly; `_parse_mission` (a parallel loader used by DataLoader) was missing the field.

**Fix:** one line in `_parse_mission`:
```python
crew_member_id=data.get("crew_member_id", ""),
```

**Why this wasn't caught earlier:** all existing mission tests use `Mission.from_dict` (the classmethod) or build Mission instances directly. None exercised the DataLoader's `_parse_mission` path on crew quests specifically. Pass 3.5's scenarios were the first tests to assert on `mission.crew_member_id` AFTER a DataLoader load.

**Regression guard:** Scenario H's `TestCrewMembershipGatesQuestProgression` now fails loudly if this regresses. The assertion "quest must not complete when crew member isn't recruited" can only pass when `crew_member_id` is wired.

---

## Secondary observations

### API drift noted during authoring

- **`Commodity.volume` vs `Commodity.volume_per_unit`.** Natural guess was `.volume`; actual field is `.volume_per_unit`. Not a bug, but worth knowing when writing helpers that pass commodity volumes around.
- **`Market.record_buy` doesn't deplete stock.** It pushes supply-demand pressure that affects future price calcs. Stock depletion is a separate `deplete_stock` call. Both tests were adapted to the actual contract.
- **`Mission.from_dict` vs `DataLoader._parse_mission` duplication.** These two parsers are divergent (the crew_member_id bug was only in one). Keeping both in sync is fragile; worth a future refactor to have the DataLoader delegate to `Mission.from_dict`.

### Coverage quality

**Scenario G (Trading)** is the first scenario that exercises cross-system state (market → player → travel → market). It catches any regression in:
- Profit math (`total_profit`, `largest_single_profit`, `credits_earned_lifetime`)
- `cargo_purchase_prices` survival across `travel_to_system`
- Trade failure invariants (no state mutation on error)

**Scenario H (Crew Quest)** directly validates the design intent that crew quests follow their crew member. Without the bug-fix above, this scenario couldn't pass — confirming the value.

**Scenario I (Galaxy Events)** closes a long-standing coverage gap. Events + chains had unit tests for individual methods but no end-to-end "event expires → chain follow-up fires on delay" verification.

---

## Remaining deferred items (post-Pass 3.5)

All items are now routed with clear ownership:

### Routed to Pass 4
- Tutorial completion happy path (view-layer)
- Mining session end-to-end (view-layer)
- Death/respawn flow (view-layer)

### Routed to Pass 5
- 9 real bugs from Pass 2 findings (campaign mission gates, forgery_appraised, met_torres/talked_to_larsen, discovered_ledger_connection, black_market_access)
- 11 items from combat_balance_design.md §12
- 4 items from combat overhaul §11 deferrals
- 4 in-source TODOs (price_memory skill, colorblind profiles, schema migration, bridge-crew hook)

### Monitor-only (no action needed)
- Accessibility implementation (post-v1 per framework §42)
- 40 consumer-only dialogue flag orphans (mostly detector misses + campaign gate bugs already in Pass 5)
- 60+ producer-only dialogue flag orphans (narrative-state memory for future Act Two)

The roadmap doc `qa_pass_1_audit.md` has been updated with the routing. Every deferred item is now in exactly one owned bucket — nothing lives in limbo.

---

## Pass 3.5 → Pass 4 handoff

Pass 3's harness + scenarios are complete. The functional-style helpers in `_helpers.py` (fresh_player, attach_build, round_trip_save, real_enemy) are reusable as-is; Pass 4 can extend them with view-instantiation helpers.

**Recommended Pass 4 scope order:**
1. View lifecycle smoke runner (primary deliverable, catches AttributeErrors on all 35 views)
2. Tutorial / mining / death-respawn scenarios as follow-ups using the view harness
3. Handoff to Pass 5 deferred triage with a clean bug list

Test count trajectory: 6,835 (pre-Pass 2) → 6,849 (+14 Pass 2) → 6,907 (+58 Pass 3) → 6,936 (+29 Pass 3.5).
