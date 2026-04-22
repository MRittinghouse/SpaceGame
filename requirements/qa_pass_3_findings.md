# QA Pass 3 — Integration Scenario Findings

Generated 2026-04-21. Result of building 58 integration scenario tests across 6 scenario files in `tests/test_scenarios/`. All green on first meaningful iteration — most tests exercised paths that unit tests already covered at the model level, so the scenario work primarily confirmed end-to-end glue holds. The *diagnostic* value was substantial: several rough edges in the APIs were surfaced through authoring friction rather than assertion failures.

**Bottom line:** 6,849 → 6,907 tests. No new real bugs found in the systems Pass 3 targeted — which means the underlying models are solid. What we *did* surface is an improved map of the integration surface, plus API rough edges worth noting for future work.

---

## Scenarios shipped

| File | Purpose | Tests |
|---|---|---|
| `_helpers.py` | Shared harness: `fresh_player`, `attach_build`, `round_trip_save`, `real_enemy` | — |
| `test_scenario_save_load.py` | Save/load round-trip with build-derived ship, dual_tech reveal flags, all 4 factions | 8 |
| `test_scenario_subsystem_combat.py` | Impl 4 end-to-end: focus → damage → destruction → effect | 11 |
| `test_scenario_skill_combat_paths.py` | CLAUDE.md warning: skill bonuses apply in BOTH combat paths | 12 |
| `test_scenario_mission_flow.py` | Full mission lifecycle with real data | 9 |
| `test_scenario_dual_tech.py` | Impl 2 reveal mechanism, one-shot contract, save persistence | 9 |
| `test_scenario_faction_perks.py` | Reputation → tier → perks → bonus query pipeline | 9 |

## What each scenario catches

**Scenario A (Save/Load):** regresses any field that silently fails serialization. Most valuable assertion: `ShipBuild.pixels` round-trip preserves identity, so no pixel-level save corruption. The previously-untested gap per Pass 1 audit (ShipBuild in save tests) is now closed.

**Scenario B (Subsystem Combat):** the most comprehensive end-to-end verification of Impl 4. Each of the 6 palette effects is exercised on a real enemy template. The test also catches the user's original "do enemies even try to flee" concern: engine destruction zeros `can_flee` regardless of AI behaviour.

**Scenario C (Skill Paths):** directly implements the CLAUDE.md warning. Exercises armor_bonus, shield_regen_bonus, dodge_chance, and hull_hp_bonus through BOTH `build_player_combat_state` code paths (build-derived vs legacy ShipType). Baseline comparison tests confirm no-skill players get exactly the ShipType/ComputedShipStats values — any future divergence fails loudly.

**Scenario D (Mission Flow):** drives missions through all states on real data. The `TestRewardApplication` class specifically catches the common class of bug where "mission completion doesn't actually grant the reward" — both credits and set_flag rewards are verified.

**Scenario E (Dual Tech):** Impl 2's reveal one-shot contract is the interesting assertion — `check_and_mark_reveal` is both a query and a side-effect, and the test confirms repeated calls behave correctly. Save-round-trip confirmation closes Pass 1's "dual_tech_reveal flags need save-load verification" gap.

**Scenario F (Faction Perks):** walks the full pipeline from rep shift to active perks to numeric bonus. The final assertion — `test_losing_rep_drops_perks` — catches exploit-class bugs where a player could lose rep but keep the benefit.

---

## API rough edges found during authoring

These aren't bugs but are friction points worth noting for Pass 5 triage or future refactor:

1. **`PoliticsManager` requires `relationships=` as first positional arg.** Natural authoring order is "just pass the perks"; having to also route `faction_relationships` through adds a step with no test value for perk-focused code. Would benefit from a `@classmethod from_data_loader(dl)` factory.

2. **`MissionManager._missions` is accessed as a private attribute.** All six scenario files touch `mgr._missions.items()` to find test-fixture missions. A public `list_missions()` or `find_missions(filter)` method would be cleaner; currently we rely on name-mangling being soft.

3. **`ShipUpgradeManager` module name drift.** I tried `spacegame.models.ship_upgrade` on reasonable guess; actual location is `spacegame.models.upgrades`. The class name (`ShipUpgradeManager`) doesn't match the module name (`upgrades`). Not blocking — just a small import-discovery friction.

4. **Skill prerequisite chain walking.** Scenario C's `_player_with_skill_level` walks prereqs to level them. The walker had to traverse bottom-up (root → leaf), not top-down as I first wrote it, because `level_up_skill` enforces prereq-unlocked. Fine as-is; documented in the helper.

5. **`can_flee` semantics.** Initially I expected `can_flee` to be gated by AI behavior (cowardly vs aggressive). Actual semantics: True until engines destroyed, period. AI behavior is a *separate* decision about whether to TRY to flee. This is correct — gameplay code uses `can_flee` as a capability check, not a prediction. But a docstring clarifying "can" vs "will" would prevent similar confusion.

---

## What Pass 3 did NOT find (and why that matters)

A scenario pass that found *zero* real bugs in 58 tests is a strong positive signal about the codebase:

- **Save/load**: Pass 1 flagged "recently added fields need round-trip testing" — we tested them; all pass. Existing `test_save_roundtrip.py` plus these scenarios now cover every recent addition.
- **Skill bonus paths**: CLAUDE.md explicitly warned about this class of bug; 12 tests across 4 bonus types × 2 paths all pass. The warning is being respected.
- **Impl 4 (subsystems)**: 11 end-to-end tests, all green. Confirms the model + engine layer integration is correct.
- **Impl 2 (dual techs)**: reveal contract + save persistence + palette coverage all verified.

Bugs do exist — the 9 campaign gate flags found in Pass 2 are real — but they're authoring/content bugs in the data layer, not integration bugs in the engine layer. Pass 3's scenarios weren't designed to catch those, and appropriately didn't.

---

## Scenarios DEFERRED (triaged across Passes 3.5 and 4)

The Pass 1 audit listed 12 scenarios. We shipped 6 in Pass 3. The remaining 6 were triaged at Pass 3 close based on whether they fit the model-layer harness or need view-layer scaffolding:

**Pass 3.5 scope** (fit the existing model-layer harness):
- **Trading arbitrage round-trip** — buy low / travel / sell high; market state + skill bonuses
- **Crew quest lifecycle** — loyalty-gated trigger, accept, complete, crew-specific rewards
- **Galaxy event chain progression** — trigger → consequence → chain follow-up

**Routed to Pass 4** (view-layer — wrong shape for Pass 3.5):
- **Tutorial completion happy path** — needs view state transitions + tutorial overlay
- **Mining session** — mini-game view; model yield math already covered, `MiningView` render isn't
- **Death/respawn flow** — crosses multiple `GameState` transitions; needs view lifecycle

The Pass 1 audit document has been updated with the same split so nothing falls off the plate.

---

## Pass 3 → Pass 4 handoff

The scenario harness (`_helpers.py`) is lightweight, functional, and could be extended to support Pass 4's smoke runner. The key insight from this session is that **models are strong, view integration is the real gap**. Pass 4's smoke test runner should target the Tier D views (ship_builder_view, shipyard_view, crew_roster_view, etc.) identified in Pass 1 — not more model-layer scenarios.
