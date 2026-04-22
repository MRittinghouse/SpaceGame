# UI Review Sprint 6 — State and Motion Polish

Generated 2026-04-22. Final sprint of the UI review arc per the standards doc plan.

**Bottom line:** Sprint 6 is predominantly a **confirmation pass** — the underlying state and motion discipline in the codebase is already strong. Motion rules are upheld (no input-blocking animations, palette-driven colors, timers bounded). State coverage has two concrete gaps that got filled (mission log and achievements filtered-empty states). 

Test count: **7,303** (unchanged — state changes are visual UX, not automatable). Full suite green, lint clean.

---

## What Sprint 6 scope looked for

Per `requirements/ui_design_standards.md`, Sprint 6 audits:

- **Five interactive states** per element: default, hover, active, disabled, busy
- **Four content states** per surface: loaded-with-content, loaded-empty, loading, error
- **Motion discipline**: 250ms input-blocking cap, palette-role colors, graceful degradation

The scope across 34 views is potentially thousands of individual elements. This sprint was restrained to three focused scans plus small fixes — no systematic re-audit of every element.

---

## Findings

### 1. Motion discipline — CLEAN

Scanned every view's `handle_event` method for patterns like `if self._X_timer > 0: return` that would block input during animations. **Zero views found** with blocking animation gates. Input remains responsive at all times.

Animation timer durations found:

| Timer | View | Duration | Blocking? |
|---|---|---|---|
| `_banner_timer` | `combat_view.py` | 1.5s | No — combo banner overlay |
| `_flash_timer` | `refining_view.py` | 0.6s | No — feedback flash |
| `_anim_timer` | `ship_builder_view.py` | 1.2s | No — build-confirm animation |
| `_guidance_banner_timer` | `shipyard_view.py` | 8.0s | No — fading informational banner |

The shipyard's 8-second banner caught my attention on first scan — long duration suggested blocking risk. On inspection it's correct: a post-build guidance overlay ("Browse the Shop to buy parts, then equip them in Loadout") with a 2-second alpha fade at the end. Player can interact with the view throughout.

No motion violations. Sprint 6 adds no motion-related fixes.

### 2. Disabled-state coverage — ADEQUATE

Nine views actively manage pygame_gui button enabled/disabled state via `.enable()` and `.disable()` calls:

| View | Enable | Disable | Notes |
|---|---|---|---|
| `cantina_view.py` | 0 | 2 | Disable-only pattern |
| `character_creation_view.py` | 3 | 3 | Balanced |
| `galaxy_map_view.py` | 2 | 5 | Traveling disables most buttons |
| `main_menu_view.py` | 0 | 1 | Minimal |
| `save_load_view.py` | 2 | 3 | Balanced |
| `settings_view.py` | 6 | 3 | Apply/cancel dynamics |
| `station_hub_view.py` | 0 | 2 | Disable-only pattern |
| `trading_view.py` | 0 | 1 | Minimal |
| `tutorial_shop_view.py` | 0 | 2 | Disable-only pattern |

Views not in this list (shipyard, combat, mining, etc.) rely on the click-then-show-error pattern for invalid actions rather than pre-emptive button disable. Both patterns are legitimate per the standards doc; the "disable + tooltip" preference is a design ideal, not a hard rule.

No systematic gap found. A future polish pass could convert click-then-error patterns to pre-emptive disable on a per-view basis if playtester feedback indicates confusion.

### 3. Content state (empty) coverage — 2 GAPS FIXED

Three list-detail views in the game expose the player to an empty list on first encounter. Coverage check:

| View | Empty-state copy | Status |
|---|---|---|
| Crew roster | "No crew members recruited yet." | Already in place |
| Journal | Filter-aware: "No entries yet." / "No entries tagged \"X\"." | Already in place |
| Mission log | **MISSING** (before Sprint 6) | **Added this sprint** |
| Achievements filtered | **MISSING** (before Sprint 6) | **Added this sprint** |

#### Mission log empty-state additions

`mission_log_view.py::render` previously rendered the list panel and simply drew no items when `self._mission_items` was empty. Player would see a bordered empty panel and the detail panel beside it, with no explanation of WHY the list was blank.

Added per-tab empty copy:

```python
_TAB_EMPTY_COPY = {
    "active": "Nothing active. Pick something up from Available.",
    "available": "Nothing on the board yet.",
    "completed": "Nothing finished yet.",
}
```

The "Active" tab's copy doubles as a gentle nudge to the Available tab — useful for a new player who opens the log before accepting any missions.

#### Achievements filtered-empty addition

`achievements_view.py::render` previously iterated the `filtered` list with no guard. If the player filtered to a category with no achievements (unlikely today but possible with future category additions or content gating), they would see a blank content area below the filter tabs.

Added:

```python
if not filtered:
    empty_text = (
        "No achievements in this category yet."
        if self._active_filter != "all"
        else "No achievements yet."
    )
    # ... centered text rendered below the filter tabs
```

### 4. Loading and error content states — N/A

The game loads data synchronously at startup and does not make runtime data requests that could be "loading." Error states for save/load are handled by `SaveManager` at the infrastructure level. No gaps here.

---

## What Sprint 6 did NOT do

Sprint 6 scope was restrained deliberately:

- **Did not audit hover/active states element-by-element.** pygame_gui handles these via themes; custom widgets (like the _MissionItem list rows) handle them inline with explicit hover tracking. A case-by-case visual review would require running the game and hovering every element — outside automated-test scope.
- **Did not convert click-then-error patterns to pre-emptive disabled buttons.** That's a design-ideal shift that would benefit from playtester input first.
- **Did not audit every list in every view for empty-state coverage.** The high-traffic views (mission log, crew roster, journal, achievements) were checked. Edge-case views (cantina NPC list when a station has no NPCs, investment view when no investments available) were not exhaustively reviewed.

These are all valid follow-up items. The standards doc's Sprint 6 plan anticipates "tests where automatable" but much of state/motion polish is inherently UX-judgment work that benefits from playtest observation.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,303 passed, 98 skipped, 0 failed, 0 xfailed** |
| `ruff check` on touched files | Clean |
| Motion violations found | **0** |
| Empty-state gaps filled | **2** (mission log, achievements filtered) |
| Tests added | 0 (visual changes; existing smoke matrix covers the render path) |

---

## UI review arc — final status

Sprint 6 closes the formal UI review arc per the standards doc roadmap. Totals across the arc:

| Sprint | Headline |
|---|---|
| 1 | UI standards doc + 34-view inventory |
| 2 / 2b / 2c | Primitive consolidation; `_BUILDER_COLORS` + `_COMBAT_COLORS`; ~225 raw RGB tuples eliminated |
| 3a / 3b / 3c | Resolution matrix (6 resolutions), subprocess bounds harness, overlap tests, overflow probes |
| 4 / 4b | Colors→PALETTE_ROLES wrapper; 30 attributes palette-backed; colorblind propagation live |
| 5 / 5b | Writing bible compliance across every UI surface; 19 voice fixes |
| Trading legality refactor | Final xfail cleared |
| 6 | Motion discipline confirmed; 2 empty-state gaps filled |

**Test growth: 7,110 → 7,303 (+193 tests, +2.7%).** Two game-affecting bugs surfaced and fixed (tutorial drydock overlap, trading legality truncation). Three architectural systems shipped (palette wrapper, subprocess resolution harness, writing bible scanner). Zero regressions introduced.

---

## What's next (non-code items)

With the code-focused arc done, the remaining UI work is content-focused or requires external input:

- **Colorblind calibration content pass** — find colorblind playtesters, empirically refine Sprint 4/4b remap tables. The infrastructure is ready; this is playtester coordination.
- **Controller support conversation** — design discussion for how the journal and drydock work with gamepad input. UX-shaping, not code-starting.
- **Sprint 5b follow-ups (optional)** — click-then-error to disabled-button conversions on a per-view basis, informed by playtester feedback.

Sprint 6 is the natural stopping point for the UI review arc until external input surfaces new direction.
