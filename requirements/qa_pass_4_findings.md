# QA Pass 4 Part A — View Lifecycle Smoke Runner

Generated 2026-04-21. Result of building a parametrized smoke-test harness for 13 views that had 0% or minimal test coverage per Pass 1's audit.

**Bottom line:** 39 new smoke tests added, all green. No crash-class bugs found in any of the 13 views exercised. Test count 6,936 → 6,975. Authoring-time friction surfaced several harness-side mistakes (wrong attribute names, wrong constructor arg types) which are now documented in the harness as working examples for future view tests.

---

## What shipped

### Harness (`tests/test_scenarios/_view_harness.py`)

Functional module with three concerns:

1. **Pygame init** — `ensure_pygame()` sets `SDL_VIDEODRIVER=dummy` and initializes the display exactly once per test session. `fresh_ui_manager()` returns an isolated UIManager per test; `fresh_screen()` returns a throwaway Surface for render calls.
2. **Shared manager factories** — `smoke_player()`, `smoke_mission_manager()`, `smoke_crew_roster()`, `smoke_achievement_manager()`, `smoke_politics_manager()`, etc. Each builds a realistic mid-game instance using the real DataLoader. No mocks.
3. **View factory registry** — 13 registered view factories in `VIEW_FACTORIES`. Each knows its view's specific constructor requirements and composes the shared managers.

### Smoke tests (`tests/test_scenarios/test_view_smoke.py`)

Three parametrized test classes × 13 views = 39 tests:

- **TestViewLifecycleSmoke.test_view_lifecycle_completes** — construct → on_enter → update → render → on_exit without exception
- **TestViewLifecycleSmoke.test_view_cleans_up_ui_elements** — UIManager element count after on_exit ≤ element count before on_enter (zero leakage)
- **TestViewConstructionRobustness.test_view_constructs_without_exception** — `__init__` alone succeeds

### Views covered

**Tier D (0% coverage before Pass 4):**
- main_menu_view
- crew_roster_view
- mission_log_view
- skill_tree_view
- achievements_view
- dialogue_view
- ship_builder_view (2,300 statements — largest view in the codebase)
- shipyard_view (1,551 statements)
- character_creation_view
- event_notification_view
- tutorial_shop_view

**Tier C (low coverage):**
- cantina_view
- station_hub_view

---

## What Pass 4 did NOT find

Zero real bugs in view construction, lifecycle, or cleanup. Every view:

1. Constructs without exception given realistic dependencies
2. Runs `on_enter()` without crash
3. Renders 10 consecutive frames without crash (verified via an ad-hoc multi-frame run)
4. Cleans up its UI elements correctly on `on_exit()` — no leaks

This is meaningful. The views in Tier D were flagged as highest crash risk (ship_builder_view alone has 2,300 untested statements). They're solid on the lifecycle contract.

**Caveats:**
- Smoke tests don't exercise user interaction (clicks, text input, state changes mid-frame). They verify the "happy path on empty state."
- A view that crashes only after a specific button press or state transition won't fail these tests.
- Views that render fine on fresh state but misbehave with non-default player progression/mission state aren't covered.

---

## Friction encountered (documented for future test authors)

Several harness-side mistakes were made and fixed during authoring. These are captured as working reference in `_view_harness.py`:

| Attempted | Correct |
|---|---|
| `dl.system_locations` | `dl.locations` |
| `dl.achievements.values()` | `list(dl.achievements)` (it's already a list) |
| `DialogueManager(dialogue_trees=..., player_flags=...)` | `DialogueManager()` (no args) |
| `from spacegame.models.event import Event, EventChoice` | `from spacegame.models.event import MarketEvent, EventType` |
| `ShipyardView(..., all_upgrades=list(...), all_ship_types=list(...))` | Pass the dicts directly (both are Dict[str, X]) |

These match the API rough edges noted in Pass 3. Each one was a ~1-line fix once identified. The harness now serves as a quick-reference for constructor signatures.

---

## Remaining Pass 4 scope (Part B — scheduled separately)

Part B scenarios absorbed from Pass 3 deferrals:
- **Tutorial completion happy path** — extended lifecycle across multiple views
- **Mining session** — `MiningView` interaction loop
- **Death/respawn flow** — combat loss → game-state transition → respawn

These need more than lifecycle smoke — they need multi-view state transitions. The harness built in Part A is the foundation; Part B builds on top.

**Estimated cost for Part B:** 1 session (~15 tests). Lower priority than Part A because Part A closed the biggest risk (crash-class bugs in untested views).

---

## Views NOT covered (deliberate deferrals)

The registry intentionally excludes:

- **`combat_view.py`** — already has 109 dedicated tests (Tier B baseline); smoke would be redundant
- **`trading_view.py`** — Pass 1 audit flagged this at 19% coverage but Pass 3's trading scenario exercises the model layer; view-layer coverage is a Pass 4 Part B candidate but not blocking
- **`galaxy_map_view.py`** — 48% coverage; similar reasoning
- **`mining_view.py`, `refining_view.py`, `salvage_view.py`** — mini-game views better served by Part B scenarios that exercise the actual session loop
- **`cockpit_hud.py`** — overlay, not a full view
- **`tutorial_overlay.py`** — same
- **`base_view.py`, `layout.py`, `table_widget.py`** — utility modules without a state transition

---

## Test count trajectory

| Pass | Added | Running Total |
|---|---|---|
| Pre-QA | — | 6,835 |
| Pass 2 | +14 | 6,849 |
| Pass 3 | +58 | 6,907 |
| Pass 3.5 | +29 | 6,936 |
| Pass 4 Part A | +39 | 6,975 |

## Pass 4 → Pass 5 handoff

Pass 4 Part A is complete. The roadmap now has exactly two streams remaining:

- **Pass 4 Part B** (tutorial / mining / death-respawn scenarios) — discrete follow-up
- **Pass 5** (deferred items triage with the user) — conversation-heavy, decision-making

Either can proceed independently.
