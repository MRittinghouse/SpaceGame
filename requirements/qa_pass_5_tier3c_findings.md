# QA Pass 5 Tier 3.C — Module Overlay Integration

Generated 2026-04-21. Second Tier 3 session. Ships the module overlay integration that was listed as ⏳ queued in the Combat overhaul §11 (deferred since the primitive was built but never wired into combat_view).

**Bottom line:** 1 Tier 3 item resolved. +16 new tests. Test count 7,041 → 7,057. Players can now see visual feedback for subsystem targeting, destruction, and damage directly on the enemy card composite.

---

## What was deferred (pre-Tier 3.C)

From the spec, circa QA Pass 1 audit:

> ⏳ **Module overlay integration in combat_view.** The overlay primitive
> is tested and ready; combat_view doesn't yet construct per-enemy overlay
> instances or call `set_state` / `trigger_flash` on them. Requires
> defining which modules each enemy exposes (enemies currently have no
> `placed_slots` in their generated builds — the spec intends simplified
> composition records per §9 Open Question 1).

Two blockers:

1. **Per-instance cache architecture** — overlays need per-enemy state (focused ≠ destroyed across instances). Tier 3.A resolved this for composites; same approach works here.

2. **Region mapping with no placed_slots** — §11.2's 6-tag subsystem palette is the answer. Tags map to canonical spatial regions based on the procedural silhouette orientation (ships point right). No per-template authoring needed to ship a working default; per-template overrides can land later.

Both blockers are addressed in this session.

---

## What shipped

### `spacegame/engine/enemy_overlay_provider.py` (new, ~180 lines)

- `EnemyModuleOverlayProvider` class with per-instance cache keyed by `(template_id, id(enemy_ship))`. Exactly mirrors the Tier 3.A composite provider pattern — same tuple key, same `prune_dead_instances`, same None-for-template-scoped fallback.
- `canonical_subsystem_regions(build, subsystem_tags)` helper that partitions a build's canvas into fixed grid regions for each of the 6 subsystem tags. Ship-points-right orientation drives the layout:
  - `cockpit` → front-top (right-upper)
  - `weapon_array` → front-middle
  - `sensor_array` → mid-top
  - `shield_generator` → center
  - `reactor` → back-middle
  - `engine` → back (leftmost)
- `sync_state_from_enemy(overlay, enemy)` translates the enemy's runtime `subsystems_destroyed` set and `focused_subsystem` into overlay state transitions each frame. Precedence: DESTROYED > HIGHLIGHTED > NORMAL.

### `spacegame/views/combat_view.py` (wire-up, ~30 lines)

- Construct provider in the same spot as the composite provider (__init__).
- `prune_dead_instances` called in `on_enter` alongside the composite prune.
- Per-frame `overlay.update(dt)` tick for every cached overlay (drives flash timers).
- In `_render_enemy_card`, after fetching `card_sprite` from the composite, build/sync the overlay and render it onto a **copy** of the card sprite (the composite surface is cached — drawing on it directly would corrupt the cache).

### `tests/test_engine/test_enemy_overlay_provider.py` (new, 16 tests)

- Canonical region layout (6 classes: tags produce regions, unknowns dropped, fit canvas, cockpit-at-front, engine-at-back, empty-list)
- Per-instance caching (3 tests — same template different instances, same instance reuse, regions registered lazily)
- Prune stale instances
- Sync state from enemy (5 tests — destroyed, focused, precedence, unfocus-resets, missing-fields-doesn't-crash)
- Render onto surface produces visible pixels

---

## Visual outcome (player-facing)

During combat, when the player focuses a subsystem via `` ` `` (backtick), the enemy's card composite now shows a **hud_warning-tinted outline** on the front-middle region (for weapon_array focus), front-top (cockpit), back (engine), etc. As subsystems get destroyed, their regions fill with **steel shadow_deep + seam outline** (spec §4.2 DESTROYED state). State updates happen each frame from the authoritative `subsystems_destroyed` set on EnemyShip — zero chance of visual drift from combat state.

The overlays are rendered at native composite scale (1 pixel per grid cell) because that's how the card sprite is presented. On a 16x16 canvas, regions are 4-8 pixels — subtle but present. When the arena-ship render path migrates from legacy AnimatedSprite to ShipComposite in a future session, the same overlay infrastructure automatically applies at larger cell_size, producing more prominent visual feedback on the big ship render.

---

## Design decisions documented

**Why canonical regions and not per-template placed_slots?**
Procedurally generated builds don't have placed_slots; adding them per-template would be content work for 60 enemies. The canonical layout works for ~every enemy because the silhouette generator produces ship-shaped footprints at a consistent orientation. Per-template override hooks can land for marquee bosses in a future session.

**Why render onto the card sprite (small) instead of the arena ship (large)?**
The arena ship still uses the legacy `AnimatedSprite` path, not `ShipComposite`. Module overlays need a composite surface to paint onto. This is a pending migration — when the arena ship moves to composite rendering, overlays render there at larger cell_size with no additional provider work.

**Why copy the card sprite before drawing?**
ShipComposite caches its rendered surfaces. Drawing the overlay onto the cached surface would permanently tint it, affecting all future frames AND any other call site that fetches the same composite. Copying costs a single surface blit but keeps the cache clean.

---

## Tier 3 Roadmap state

| # | Item | Status |
|---|---|---|
| 3.A | Per-instance composite cache | ✅ (prior session) |
| 3.B | Destruction driver wiring | ✅ (prior session) |
| **3.C** | **Module overlay integration** | ✅ **shipped this session** |
| Remaining: `call_reinforcement`, `price_memory` + `TradeRouteTracker`, ally-targeted heals, composite_build content, narrative encounters for T4 bosses | Each a dedicated session |
| Deferred: legacy ShipType removal, schema migration | Still deferred |

Three Tier 3 items done. Every remaining item is a dedicated feature session with clear scope documented.

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 3.A+B | 7,041 |
| **Pass 5 Tier 3.C** | **7,057** |

**Delta:** +16 tests, 1 Tier 3 item resolved. Spec §11 module overlay deferral closed with dated resolution note.
