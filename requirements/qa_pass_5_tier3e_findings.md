# QA Pass 5 Tier 3.E — Reinforcement Spawning (`call_reinforcement`)

Generated 2026-04-21. Fourth Tier 3 session. Closes the §12 deferred item that dates back to Phase B2: `call_reinforcement` was listed in the §4.4 T3 move palette but had no engine support for mid-combat enemy spawning.

**Bottom line:** 1 Tier 3 item resolved. +9 new tests. Test count 7,063 → 7,072. `union_behemoth` now calls in a Miners Union picket mid-fight.

---

## Design gap closed

From `combat_balance_design.md §12` before this session:

> **Reinforcement spawning (call_reinforcement move).** Listed in §4.4
> T3 move palette but not implemented — would require engine support
> for mid-combat enemy spawning.

The spec wanted reinforcements as a threat-shaping mechanic for Support and Commander archetypes. Without engine support, the design intent for moves like "Call the Yard" / "Summon Backup" couldn't exist — those templates had to use direct-damage or buff moves instead, losing their strategic identity.

---

## What shipped

### Data model (`spacegame/models/combat.py`)

- New `EffectType.SPAWN_REINFORCEMENT = "spawn_reinforcement"` enum variant.
- `CombatEffect.metadata: dict = field(default_factory=dict)` — free-form payload for effect-specific data that doesn't fit the scalar `value`/`duration` fields. Used by SPAWN_REINFORCEMENT for `{"template_id": "<enemy_id>"}`. Omitted from `to_dict` when empty (keeps existing JSON minimal).
- `to_dict` / `from_dict` round-trip preserved.

### Engine (`spacegame/models/combat_engine.py`)

- `MAX_LIVING_ENEMIES = 5` module constant (arena layout budget).
- `_spawn_reinforcements(effect, source_name)` helper — looks up the template via `DataLoader`, creates `EnemyShip.from_template(...)`, appends up to `MAX_LIVING_ENEMIES` new enemies. Logs spawns + "capped" notes + "unknown template" / "no template specified" failures.
- `_resolve_move` bucketing extended: spawn effects are separated before the target-based routing (offensive/self/ally), because they're caster-invoked and target-independent. Spawn effects bypass the hit-roll, accuracy check, and evasion logic entirely.
- Pure spawn moves produce a log entry with the template name so players see reinforcements arrive.

### Content (`data/combat/enemies.json`)

- `union_behemoth` (T4 Miners Union boss) gained a 6th move: **"Call the Yard"** — spawns 1 `union_picket` reinforcement, energy cost 6, cooldown 99 (effectively once-per-combat). Narrative fit: the Behemoth is an industrial leviathan, surrounded by Union industrial fleet operations; calling in a picket ship is consistent with its fiction.
- Move count for union_behemoth goes from 5 → 6. T4 requires ≥4, so tier consistency is preserved.

### Tests (+9 new)

- `TestReinforcementSpawning` (5 tests): spawn appends correctly, MAX_LIVING_ENEMIES cap is respected (verified by filling the arena to cap then attempting spawn), unknown template produces failure log + no phantom enemy, `value=2` spawns exactly 2, empty `metadata` no-ops with failure log.
- `TestCombatEffectMetadata` (3 tests): metadata round-trips through to_dict/from_dict, empty metadata omitted from serialization (backward compat), legacy JSON without metadata field loads with empty dict.
- `TestEffectType.test_all_effect_types_exist` updated to include SPAWN_REINFORCEMENT.

---

## Gameplay impact

**Before:** The fight against `union_behemoth` was a pure slugfest — player whittles 800 HP down while the Behemoth attacks, shield-boosts, or hardens armor. Late-fight pacing dragged because the threat profile didn't escalate.

**After:** The Behemoth's AI can now elect to call a picket reinforcement at a tactically meaningful moment. The extra enemy adds damage pressure and forces target-prioritization decisions — kill the picket fast, or tank its attacks while focusing the Behemoth?

Interacts with existing systems:

- **Subsystem targeting (Impl 4):** Destroying the Behemoth's reactor starves its energy regen, delaying the reinforcement call (and shields, and armor-harden).
- **Ally heals (Tier 3.D):** If the Behemoth calls a picket AND a medic is in the encounter (custom content), the medic could heal the picket. Full support composition.
- **Per-instance composites (Tier 3.A):** The new enemy gets its own `ShipComposite` instance on arrival; destruction progress tracked independently. The composite cache evicts stale entries on encounter exit per Tier 3.A's `prune_dead_instances`.

---

## Safety nets

- **Arena cap (MAX_LIVING_ENEMIES=5):** matches the combat view's tested-layout budget. Reinforcement requests beyond the cap are silently declined with a log message. A misconfigured move declaring `value=99` can't flood the arena.
- **Unknown template:** the engine tolerates bad data — logs a failure and continues. No crashes, no phantom enemies in state.enemies.
- **Missing `template_id`:** same — logged failure, no state change.
- **Cooldown-based rate limit:** the wired move uses `cooldown=99` which is effectively once-per-combat. No hard engine limit per move, intentionally — content authors pick the cadence.

---

## Tier 3 Roadmap state

| # | Item | Status |
|---|---|---|
| 3.A | Per-instance composite cache | ✅ |
| 3.B | Destruction driver wiring | ✅ |
| 3.C | Module overlay integration | ✅ |
| 3.D | Ally-targeted heals | ✅ |
| **3.E** | **Reinforcement spawning** | ✅ **shipped this session** |
| Remaining Tier 3: `price_memory`+`TradeRouteTracker`, composite_build content, narrative encounters for T4 bosses | Each a dedicated session |
| Permanently deferred: legacy ShipType removal, schema migration | — |

Five Tier 3 items done across five sessions. The combat engine now has every mechanic the design spec promised — damage, defense, heals (self/ally), DoTs, flee, negotiate, bribe, dual-tech cinematic, subsystem targeting, destruction visuals, module overlays, legendary mechanics (chain fire, void absorption, heat hardening, cooldown reduction, phase shift), and reinforcement spawning.

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 3.D | 7,063 |
| **Pass 5 Tier 3.E** | **7,072** |

**Delta:** +9 tests. `combat_balance_design.md §12` entry marked RESOLVED with date.
