# QA Pass 5 Tier 3.D — Ally-Targeted Heals

Generated 2026-04-21. Third Tier 3 session. Closes the `EffectTarget.ALLY` design-spec gap in `combat_balance_design.md §4.4` and §12 — `medical_relay: heal 30 HP to lowest-HP ally` now actually does that.

**Bottom line:** 1 Tier 3 item resolved. +8 new tests. Test count 7,057 → 7,063 (one prior test updated). Support archetype enemies (`collective_medic`, `guild_relay_nexus`) now heal teammates instead of just themselves — changes the combat feel of multi-enemy encounters containing a medic.

---

## Design gap closed

From `combat_balance_design.md §12` before this session:

> **Ally-targeted heals for Support archetype.** The design doc §4.4
> specifies `medical_relay: heal 30 HP to lowest-HP ally`, but
> `EffectTarget` only has `SELF` and `ENEMY`. Support templates
> (`collective_medic`, `guild_relay_nexus`) use self-heals instead.

The dedicated Support enemies were effectively indistinguishable from Tank/Juggernaut archetypes at runtime — they took hits, they self-healed. The unique "medic" fantasy (keeping allies alive) never materialized because the target enum didn't support it. Tier 3.D fixes this.

---

## What shipped

### `spacegame/models/combat.py` — enum extension

- Added `EffectTarget.ALLY = "ally"` with a docstring documenting the routing rule (caster's lowest-HP teammate; player-side falls back to self since crew live inside `PlayerCombatState`).
- No `to_dict`/`from_dict` changes needed — the Enum already accepts any string via `EffectTarget(data.get("target", "enemy"))`.

### `spacegame/models/combat_engine.py` — routing + selection

- `_resolve_move` now splits effects into three buckets: `offensive_effects` (target=ENEMY), `self_effects` (SELF), `ally_effects` (ALLY).
- New `_select_ally_target(attacker, actor_name)` helper:
  - For enemy casters: picks the living enemy with the lowest hull ratio that isn't the caster.
  - For player casters: returns None (no distinct allies in the model).
- ALLY resolution path applies effects to the selected ally via `_apply_effects`. Solo-caster fallback redirects to self with a log annotation ("no ally to support — redirected to self") so the behavior is visible to players.
- Pure ally-effect moves (no offensive, no self) produce a combat log entry so the action surfaces visibly.

### `data/combat/enemies.json` — support templates updated

- `collective_medic`: replaced `repair_pulse` (18 HP self) with `medical_relay` (30 HP ally). Move count stays at 2 (T2 expected shape). Cryo pulse retained as offensive fallback.
- `guild_relay_nexus`: same swap. Move count stays at 3 (T3). Shield matrix + ion pulse retained.
- Description text updated to convey the medic's new role ("patches the most-wounded ally (or itself when alone)").

### Tests (+8 new)

- `TestEffectTarget.test_all_targets_exist` updated to include ALLY.
- `TestEffectTarget.test_ally_target_serializes` — round-trip an ALLY effect through to_dict/from_dict.
- `TestAllyTargetedHeals` — 5 tests:
  1. Ally heal restores wounded teammate (20 → 50 for 30 HP)
  2. Lowest-HP ally selected when multiple are wounded
  3. Dead allies skipped
  4. Solo medic fallback (heal redirects to self when no ally available)
  5. Player ally-heal falls back to self (player has no distinct allies)
- `TestAllyHealLogEntry.test_ally_only_move_produces_log_entry` — pure ally-effect moves generate a log entry so players see the action.

---

## Gameplay impact

**Before:** A 2-enemy encounter with `collective_medic + science_sentinel` played like any other pair — medic self-healed 18 HP when damaged, sentinel attacked normally. Player focused the medic to kill it first, then cleaned up the sentinel.

**After:** The medic actively keeps the sentinel alive. When the sentinel drops below the medic in hull, the medic's turn commits to `medical_relay` on the sentinel. Player must now choose: focus fire the sentinel to force a meaningful kill while the medic heals, OR kill the medic first to remove the heal support — different tactical shape per choice.

The player's subsystem targeting (Impl 4 / Tier 3.C) also interacts — destroying the medic's `reactor` subsystem disables its energy regen, eventually starving the heal cycle. So the combat layers now compose into real strategic variety for Support encounters.

---

## Graceful degradation

**Solo medic:** When an ally-effect move fires with no teammates alive, the effect redirects to self (logged as "no ally to support — redirected to self"). This means a lonely `collective_medic` can still heal itself — the ally-targeted move doesn't become a dead action. Previously `repair_pulse` handled solo self-heal; now the ALLY move does double duty.

**Player-side ally moves:** If a future player move specifies `target: "ally"`, it routes to the player itself. Same solo-fallback pattern. The path exists to avoid inventing a crew-targeting mechanic that isn't otherwise in the model.

---

## Tier 3 Roadmap state

| # | Item | Status |
|---|---|---|
| 3.A | Per-instance composite cache | ✅ |
| 3.B | Destruction driver wiring | ✅ |
| 3.C | Module overlay integration | ✅ |
| **3.D** | **Ally-targeted heals** | ✅ **shipped this session** |
| Remaining Tier 3: `call_reinforcement`, `price_memory`+`TradeRouteTracker`, composite_build content, narrative encounters for T4 bosses | Each a dedicated session |
| Permanently deferred: legacy ShipType removal, schema migration | — |

Four Tier 3 items done. The combat systems now deliver every mechanical promise from the design spec — destruction visuals drive from hull, module overlay shows subsystem state, support archetypes genuinely support, and per-instance caching isolates it all.

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 3.C | 7,057 |
| **Pass 5 Tier 3.D** | **7,063** |

**Delta:** +8 tests across the new ally-heal behavior, 1 prior test updated, 0 regressions. §12 log entry marked RESOLVED with date.
