# QA Pass 5 Tier 3 — Per-Instance ShipComposite Cache + Destruction Driver

Generated 2026-04-21. First Tier 3 session. Shipped one architectural change that resolves a known Impl 5 deferral and fully wires the destruction driver that was blocked by it.

**Bottom line:** 2 Tier 3 items resolved (3.A + 3.B stretch). +7 new tests. Test count 7,034 → 7,041. The combat visual pipeline now wrecks ships progressively as hull depletes — a player-visible change.

---

## 3.A — Per-Instance ShipComposite Cache

**Problem:** `EnemyCompositeProvider._composite_cache` was keyed by `template_id`. Multiple living enemies of the same template (e.g., two pirate_scouts in one encounter) shared a single composite instance. Any per-enemy mutable state — destruction progress, per-module overlays, wear level — would thrash: enemy B's state writes would flash-cancel enemy A's.

**Fix:**
- Cache key changed to `(template_id, instance_id)` where `instance_id = id(enemy_ship)` when the caller provides one, else `None` (falls back to template-scoped for backward compat).
- Added `get_composite(template_id, instance_key=...)` + `get_surface(...)` signatures — the existing string-only callers still work untouched.
- Added `prune_dead_instances(living_enemies)` — evicts instance-scoped entries whose object is no longer alive in the current combat; preserves template-scoped entries.
- Internal cache type changed from `dict[str, ShipComposite]` to `dict[tuple[str, Optional[int]], ShipComposite]`.

**Backward compatibility:** all 19 pre-existing provider tests pass unchanged. The `instance_key` parameter is optional; callers that don't need per-enemy state (portrait-only paths, tests) get the previous behavior.

**Tests added:** 7 new tests in `TestPerInstanceCaching` covering: different instances → different composites, same instance → reuse, destruction isolation between instances, template-scoped fallback, prune-dead eviction, prune-preserves-template-scope, reset-destruction cascades.

**Files:** `enemy_composite_provider.py`, `test_enemy_composite_provider.py`.

---

## 3.B — Destruction Driver Wiring (stretch goal, shipped)

**Problem:** Impl 5 landed the destruction-pipeline infrastructure (5-bucket `set_destruction_progress` API with cache invalidation) but the driver was explicitly deferred in combat_view.py with the comment:

> "driving it from this card path is blocked by the per-template (not per-instance) composite cache — two enemies of the same template would thrash the cache when their hull ratios fall in different buckets. Wire-up will land alongside per-instance composites in a follow-up pass."

3.A landed that follow-up. 3.B wires the driver.

**Fix:** In `_render_enemy_card`, before fetching the surface for the card sprite:

```python
card_composite = self._enemy_composite_provider.get_composite(
    enemy.template.id, instance_key=enemy
)
if card_composite is not None and enemy.template.hull > 0:
    hull_ratio = max(0.0, min(1.0, enemy.current_hull / enemy.template.hull))
    card_composite.set_destruction_progress(1.0 - hull_ratio)
```

Bucket quantization (5 levels) means chip damage doesn't force a rebuild every frame — progress advances one bucket at 25%/50%/75% hull loss, each step triggers at most one rebuild.

**Visual outcome (player-facing):**
- Ship at full hull: clean, intact render
- Ship at 25% damage: darkening, some rivets fail
- Ship at 50% damage: smoke + module-destruction states
- Ship at 75% damage: heavy structural damage, silhouette breaks
- Ship at 100% damage (dead): skeletal wreck

**Per-encounter reset:** `on_enter()` now calls `prune_dead_instances(state.enemies)` after `reset_destruction()`, so stale instance-scoped entries from prior encounters don't accumulate.

**Files:** `combat_view.py`, spec `30_overhaul_space_combat.md`.

---

## Spec doc status

The `30_overhaul_space_combat.md` §11 implementation-status table was updated:

| Before | After |
|---|---|
| Impl 5: "✅ shipped infrastructure … Driver wiring deferred" | Impl 5: "✅ **fully shipped**" |

And §11.4 "Driver wiring deferred" section rewritten to document the completed wiring.

---

## Performance verification

Per the Impl 5 benchmark (`tools/benchmark_composite_rebuild.py`):
- Small regular: 0.4ms / rebuild
- Mid regular: 1.6ms
- Legendary (1031 px): 3.3ms median, 4.1ms p95

Bucket quantization means ≤5 rebuilds per enemy over the course of a kill. Worst-case (legendary boss destruction): ~20ms total rebuild cost distributed across ~60-120 frames of hull depletion. Average <0.5ms/frame extra — well within budget.

Per-instance caching does add memory: one ShipComposite per living enemy instead of one per template. Combat has at most ~3-5 living enemies at once; composite size is small (a few surfaces + state dicts). Total overhead: ~1-2 MB worst case. Negligible.

---

## Tier 3 remaining

| # | Item | Status |
|---|---|---|
| 3.A | Per-instance composite cache | ✅ shipped this session |
| 3.B | Destruction driver wiring | ✅ shipped this session |
| 9 | Module overlay integration | **Now unblocked** — uses the same per-instance cache |
| 10 | `call_reinforcement` move | Independent engine feature |
| 11 | `price_memory` + `TradeRouteTracker` | Independent new-model feature |
| 12 | Ally-targeted heals (`EffectTarget.ALLY`) | Independent engine feature |
| 13 | Hand-authored `composite_build` content | Content authoring, 1-2 hrs |
| 14 | Narrative encounters for T4 bosses | Content work |
| 15 | Legacy ShipType combat path removal | Deferred — requires exception-free preset gen + save-migration tests |
| 16 | Schema migration framework | Deferred until breaking format change |

(The Pass 1 triage listed 10 Tier 3 items; these are the items remaining after resolving 3.A + 3.B. Item 9 is now unblocked by today's work.)

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 1 | 7,025 |
| Pass 5 Tier 2 | 7,034 |
| **Pass 5 Tier 3 (session 1)** | **7,041** |

**Delta:** +7 tests, 2 Tier 3 items resolved, 1 Tier 3 item (module overlay integration) newly unblocked.
