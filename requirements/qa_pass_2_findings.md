# QA Pass 2 — Content Validation Findings

Generated 2026-04-21. Result of running the new validation tests in `tests/test_data/test_cross_references.py` and `tests/test_data/test_dialogue_integrity.py` against the current data set.

**Bottom line:** 14 new validation tests added, all green as guards. The audit surfaced **9 likely real bugs** (broken campaign flag gates) and ~30 detector misses (flags set/read by paths the audit can't see). Real bugs are listed below for Pass 5 triage. Test count went from 6,835 → 6,849.

---

## Tests added

| Class | File | What it guards |
|---|---|---|
| `TestEnemySubsystemTags` | test_cross_references.py | Every `targetable_subsystems` entry is in canonical 6-tag palette; no duplicates; ≤4 per enemy |
| `TestSkillBonusConsumers` | test_cross_references.py | Every `bonus_type` in `create_default_skills()` appears as a string literal somewhere in source |
| `TestFactionPerks` | test_cross_references.py | Perks reference real factions, valid tier names, and consumed perk_types |
| `TestModuleReferences` | test_cross_references.py | Drydock catalog modules / shapes / materials and enemy `composite_build` slots all resolve |
| `TestDialogueFlagAudit` | test_dialogue_integrity.py | Every flag has both producer and consumer (with snapshotted exceptions) |

All 14 tests green.

---

## Real bugs found (Pass 5 triage candidates)

### Campaign flag gates that never fire

These flags are referenced as `requires_flags` on campaign encounters but **no producer exists anywhere** in data or code. The encounters they gate will never trigger.

| Flag | Referenced by | Severity |
|---|---|---|
| `completed_mission_5` | 3 campaign encounters | **HIGH** — campaign Act One progression |
| `completed_mission_10` | 3 campaign encounters | **HIGH** |
| `completed_mission_15` | 3 campaign encounters | **HIGH** |
| `completed_mission_20` | 1 campaign encounter | **HIGH** |
| `discovered_ledger_connection` | 3 campaign encounters | **HIGH** |
| `black_market_access` | 1 campaign encounter | MEDIUM |
| `met_torres` | 1 campaign encounter | MEDIUM |
| `talked_to_larsen` | 1 campaign encounter | MEDIUM |
| `forgery_appraised` | 2 dialogue branches + 1 mission objective | **HIGH** — gates the appraisal mission outcome |

**Recommendation:** add producers in Pass 5. Likely fixes:
- `completed_mission_N` → set in `engine/game.py` mission completion handler when player reaches N total campaign completions.
- `discovered_ledger_connection` → likely wants to fire from a specific Act One mission completion (Sienna Vek warning chain?). Check campaign reference doc.
- `forgery_appraised` → the appraisal dialogue tree should call `set_flag: forgery_appraised` somewhere.
- `met_torres` / `talked_to_larsen` → either NPCs need an `auto_trigger_gate_flag` set, or the dialogue should set it on first response.

### Module ID drift discovered

None — the union of `ship_parts` (166) + `ship_modules` (144) covers all drydock catalog references. Test now permanently guards against drift.

### Subsystem tag drift discovered

None — all 60 enemies use canonical tags only (validated). The test will catch any future typo.

### Skill bonus orphans

None **net** orphans — only `price_memory` was orphaned (already known per combat balance §12 deferred items log; needs `TradeRouteTracker`). Whitelisted with justification.

### Faction perk orphans

None — all 13 perks have consumer wiring through `politics.get_perk_bonus` / `politics.has_perk` call sites in `engine/game.py`.

---

## Detector misses (not bugs, just hidden producers)

The flag audit can't trace dynamic flag-setting paths. These flags appear "consumer-only" but are actually set by code my regex doesn't catch:

- **`*_ground_complete`** (6 flags) — set when ground combat / ground exploration completes a mission objective
- **`*_resolved`** (15+ flags) — set inside mission flow on objective completion / choice resolution
- **Other in-mission flags** — `pesticide_acquired`, `seeds_delivered`, `signal_amplifier_deployed`, etc. — set by mission-internal events

These are documented in `KNOWN_CONSUMER_ONLY_ORPHANS` with classification. Pass 5 can re-classify any that turn out to be real bugs.

## Player-choice memory flags (intentional one-sided)

~50 flags are produced but never read. These are narrative state flags meant for save state and future content (Act Two, replays). Examples:
- `marcus_went_public` vs `marcus_alternate_inspector` (companion arc choices)
- `escaped_through_warp_gate` vs `expanse_collapsed` (Act One ending state)
- `lore_*` flags (collectible discovery flags)
- `builder_hint_*` (tutorial state)

Documented in `KNOWN_PRODUCER_ONLY_ORPHANS`. Not a Pass 5 concern — they're load-bearing for save state continuity.

---

## Pass 2 → Pass 5 handoff

The Pass 5 triage session should walk through the **Real bugs found** section above. Each item is one of:
- **Wire it now** — clear producer location, easy fix
- **Defer with reason** — needs design decision (e.g., what counts as "completed_mission_5"?)
- **Kill the encounter** — gate is unused content; remove the encounter

Estimated cost to fix all 9 high/medium items: 1–2 sessions. Most are 1–3 line changes once the design intent is clarified.
