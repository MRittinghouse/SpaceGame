# QA Pass 5 Tier 3.F — `PriceMemory` model + `price_memory` skill wire-up

Generated 2026-04-21. Fifth Tier 3 session. Closes the last orphan skill from Pass 2's content audit. The `price_memory` skill finally does what its description promises: "Galaxy map shows last-known prices for visited systems."

**Bottom line:** 1 Tier 3 item + 1 in-source TODO + 1 Pass 2 skill-orphan resolved. +14 new tests. Test count 7,072 → 7,086. Players can now see remembered prices on the galaxy map for systems they've visited.

---

## Design gap closed

Three loosely-related items were all blocked on the same missing infrastructure:

1. **Pass 2 orphan skill.** The skill audit found `price_memory` as the only unused bonus_type — declared in `create_default_skills()` but nothing read `progression.get_bonus("price_memory")`. It was whitelisted in `ALLOWED_ORPHANS` pending a dedicated fix.
2. **In-source TODO.** `galaxy_map_view.py:1466` had a TODO dating back to the shipyard revamp: `# TODO S4: price_memory needs TradeRouteTracker or price history model`.
3. **Tier 3 scope.** The Pass 5 triage called this "whole new model" work — not a trivial fix because it needs record-on-visit hook, save/load, and UI rendering.

All three resolved in one session.

---

## What shipped

### `spacegame/models/trade_route.py` — new `PriceMemory` dataclass

Sibling to the existing `TradeRouteTracker` in the same module. Same shape: dataclass with a nested dict, `to_dict`/`from_dict` for save/load, tolerant of malformed data.

```python
@dataclass
class PriceMemory:
    # system_id → {commodity_id: (price, game_day_seen)}
    _snapshots: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)

    def record(system_id, prices, game_day) -> None
    def get_last_known(system_id, commodity_id) -> tuple[int, int] | None
    def get_snapshot(system_id) -> dict[str, tuple[int, int]]
    def known_systems() -> set[str]
    def has_memory(system_id) -> bool
    def clear() -> None
    def to_dict() -> dict
    @classmethod from_dict(data) -> "PriceMemory"
```

Design:
- **Always the LATEST snapshot per system** — no history/decay. "Last known" is the whole value proposition.
- **Per-commodity day stamps** for UI freshness display.
- **Zero-price commodities skipped** (quest items, unavailable stock).
- **Malformed serialization tolerated** — broken entries drop silently, the rest load correctly.

### `spacegame/models/player.py` — integration

- New field: `price_memory: PriceMemory = field(default_factory=PriceMemory)` alongside the existing `trade_route_tracker`.
- Import added at module top (single line).

### `spacegame/save_manager.py` — save/load wire-up

- `_serialize_player`: `"price_memory": player.price_memory.to_dict()` in the result dict.
- `_deserialize_player`: if `"price_memory"` key present, restore via `PriceMemory.from_dict`. Backward-compat: missing key → default empty memory.

### `spacegame/views/galaxy_map_view.py` — record + display

**Record hook** in `_finalize_arrival()` after `systems_visited.add()`:
- Gate on `progression.get_bonus("price_memory") > 0`.
- Construct an on-demand Market for the destination system (same pattern as the existing `_get_remote_price_lines`).
- Call `player.price_memory.record(dest_id, market.get_all_prices(), player.game_day)`.
- Wrapped in try/except — failures log a warning but don't break travel.

**Display helper** `_get_price_memory_lines(system)`:
- Reads `player.price_memory.get_snapshot(system_id)`.
- Prioritizes `specialty_exports` (Buy cheap: green) and `specialty_imports` (Sell high: yellow-gold) for actionable info.
- Shows `"Metals: 120 CR (3d ago)"` with freshness string.
- Falls back to first 5 commodities if the system has no export/import context.

**Display gate** in `_draw_system_info()`:
- `remote_prices` skill (richer, realtime) takes priority.
- If remote_prices inactive BUT `price_memory` active AND system has a memory snapshot → show memory lines.
- Neither skill active OR no snapshot → no price section (unchanged behavior).

### Pass 2 skill audit update

`tests/test_data/test_cross_references.py::TestSkillBonusConsumers` had `price_memory` on its `ALLOWED_ORPHANS` whitelist. Since it now has a real consumer, the whitelist is EMPTY. Test passes with tighter guard — any future orphan skill fails loudly.

---

## Tests shipped (+14)

`TestPriceMemoryBasics` (7 tests):
- Fresh memory is empty
- `record` creates snapshot
- `record` overwrites prior snapshot (doesn't merge)
- Zero-price commodities skipped
- Empty system_id or empty prices → no-op
- `known_systems` returns all
- `clear` wipes all

`TestPriceMemorySerialization` (4 tests):
- `to_dict` shape is save-friendly (tuples as lists)
- JSON round-trip preserves snapshots
- `from_dict({})` tolerates missing snapshots key
- `from_dict` with malformed entries drops bad data, keeps good

`TestPriceMemoryIntegratesWithPlayer` (3 tests):
- Player has PriceMemory by default
- `SaveManager._serialize_player` emits `price_memory` key
- Full round-trip through `_serialize_player` → JSON → `_deserialize_player` preserves state

---

## Gameplay impact

**Before:** `price_memory` skill was purchasable but did nothing. Players selecting it saw no gameplay change. An effectively broken skill.

**After:** Player invests a point, visits a system, sees "Remembered Prices" on the galaxy map when looking at that system — commodity names, last seen price, "3d ago" freshness. Enables trade-route planning without needing `remote_prices` (which is a later-tier skill requiring `market_eye` prereq chain).

The skill now makes sense as a Tier 2 COMMERCE progression step: give up live remote-price visibility for a cheaper "remember where I've been" option. Natural complement to the `remote_prices` Tier 3 capstone.

---

## Tier 3 Roadmap state

| # | Item | Status |
|---|---|---|
| 3.A | Per-instance composite cache | ✅ |
| 3.B | Destruction driver wiring | ✅ |
| 3.C | Module overlay integration | ✅ |
| 3.D | Ally-targeted heals | ✅ |
| 3.E | Reinforcement spawning | ✅ |
| **3.F** | **PriceMemory + price_memory skill** | ✅ **shipped this session** |
| Remaining Tier 3: composite_build content for marquee bosses, narrative encounters for T4 bosses | Content work, playtest-informed |
| Permanently deferred: legacy ShipType removal, schema migration | — |

**Six Tier 3 items done across six sessions.** Every engineering item in Tier 3 is now complete. The two remaining items are pure content authoring (composite_build for 5-10 bosses, narrative encounters for T4 bosses) which the Pass 5 triage already noted are playtest-informed decisions — they should follow a manual playtest session, not precede one.

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 3.E | 7,072 |
| **Pass 5 Tier 3.F** | **7,086** |

**Delta:** +14 tests. All three §12-adjacent items (skill orphan, in-source TODO, tier 3 entry) marked resolved.

---

## QA Pass 5 session summary

Six consecutive Tier 3 sessions completed. Six engineering items from the deferred log resolved. The combat and economy systems now deliver every mechanical promise from the design spec:

- Combat: damage, heals (self/ally), DoTs, defense, dual-tech cinematic, subsystem targeting, destruction visuals, module overlays, legendary effects, reinforcement spawning, phase-shift first-attack semantics
- Economy: price memory for visited systems, trade route tracking (prior), regional markets (prior), commerce skill tree fully-wired

What's left on the whole QA roadmap:
- Manual playtest session (recommended before tackling content authoring)
- Content: composite_build for marquee bosses (5-10), narrative encounters for new T4 bosses
- Permanently deferred: legacy ShipType removal, schema migration

Every deferred item is accounted for — none have fallen off the plate.
