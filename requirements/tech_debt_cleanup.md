# Technical Debt Cleanup Plan

> **Status**: PLANNING
> **Created**: 2026-03-25
> **Context**: After completing the Shipbuilder Upgrade (14 phases) and Systems Unification (U1-U4, U2.5a-c), a codebase audit identified 6 categories of technical debt. This plan organizes them into prioritized sessions.

---

## Session 1: Legacy System Retirement (U5 Completion)

> **Priority**: HIGH — removes confusion between old and new systems
> **Estimated scope**: Focused refactor session

### 1A: Retire SLOT_POOLS from Module-Based Builds

**Problem**: `SLOT_POOLS` (weapon: 4, defense: 3, utility: 4, engine: 3 per weight class) was the old system for limiting equipment slots. It's been replaced by `MODULE_CAPS` (which limits module count per category) and the EQUIP mode (which installs equipment into modules). But SLOT_POOLS is still actively referenced in 35+ locations.

**What to do:**
- [ ] Remove `SLOT_POOLS` usage from `ShipGridManager.can_place_slot()` — this validation is now handled by `MODULE_CAPS` in `can_place_module()`
- [ ] Remove `_get_slot_pool_remaining()` from ship_builder_view.py — replaced by MODULE_CAPS display in requirements checklist
- [ ] Remove the `[D] Slot` tool key binding from ship_builder_view.py keyboard handler
- [ ] Remove `_render_slot_type_panel()` from ship_builder_view.py — replaced by EQUIP mode
- [ ] Remove slot-related rendering in hull mode (slot indicator overlays in `_render_grid`)
- [ ] Keep `SLOT_POOLS` constant definition for backward compat with old saves (comment as "LEGACY — used only for save migration")
- [ ] Keep `DesignatedSlot` dataclass for backward compat with old saves (comment as "LEGACY")
- [ ] Update `_build_move_buttons` in builder if it references slot pools
- [ ] Update tutorial hints that reference `[D] Slot` tool

**Files to modify:**
- `spacegame/models/ship_build.py` — comment SLOT_POOLS as legacy
- `spacegame/views/ship_builder_view.py` — remove slot tool, slot panel, slot pool references
- `spacegame/tutorial_manager.py` — update builder_tools hint text
- `tests/test_models/test_ship_build.py` — update/remove slot pool tests that test retired behavior

**Tests to update:**
- Any test that calls `can_place_slot()` or `_get_slot_pool_remaining()` for module-based builds
- Keep tests for `DesignatedSlot` serialization (backward compat with old saves)

**Verification:**
- [ ] The `[D]` key does nothing in hull mode
- [ ] No slot type panel renders in hull mode
- [ ] Module-based builds validate via MODULE_CAPS, not SLOT_POOLS
- [ ] Old saves with DesignatedSlots still load correctly
- [ ] All tests pass

### 1B: Clean Unused Import

**Problem**: `res_scale` imported but potentially unused in shipyard_view.py line 19.

**What to do:**
- [ ] Grep for `res_scale` usage in shipyard_view.py
- [ ] If unused, remove from import line
- [ ] If used indirectly (e.g., passed to a function), add a comment explaining why

**Verification:**
- [ ] `python -c "from spacegame.views.shipyard_view import ShipyardView"` succeeds
- [ ] All tests pass

### 1C: Resolve TODO Comments

**Problem**: 2 TODO comments left in production code.

**Items:**
1. `save_manager.py:193` — "TODO: Implement save migration in future"
   - **Action**: This is now partially addressed (ShipBuild.from_dict handles missing modules field). Update the comment to document what migration exists and what's still needed.

2. `player.py:523` — "TODO: Add cargo value calculation when market prices available"
   - **Action**: If cargo value is now calculable (market system exists), implement it. If not, convert to a tracked issue comment with context.

**What to do:**
- [ ] Review each TODO in context
- [ ] Either implement the feature (if small) or convert to a descriptive comment explaining the gap and when it should be addressed
- [ ] Remove the TODO prefix so it doesn't appear in future debt scans

---

## Session 2: game.py Monolith Decomposition

> **Priority**: MEDIUM — improves readability and maintainability
> **Estimated scope**: Careful refactor session (high-risk file)

### 2A: Extract View Factory

**Problem**: `game.py` is 4,611 lines. A significant portion (~800 lines) is `_ensure_*_view()` methods that lazily create view instances. Each follows the same pattern: check if view exists, create it, register with state manager.

**What to do:**
- [ ] Create `spacegame/engine/view_factory.py`
- [ ] Move all `_ensure_*_view()` methods into a `ViewFactory` class
- [ ] ViewFactory takes `ui_manager`, `player`, `data_loader` as constructor args
- [ ] Each `ensure_*()` method returns the view instance (same logic, just relocated)
- [ ] game.py delegates to `self._view_factory.ensure_combat_view(engine, return_state)` etc.
- [ ] This should remove ~800 lines from game.py

**Risk mitigation:**
- Each extracted method is a pure factory (no side effects beyond state registration)
- Test by running the game and verifying all state transitions still work
- Keep the same method signatures so call sites in game.py only change `self._ensure_*` to `self._view_factory.ensure_*`

**Files to create:**
- `spacegame/engine/view_factory.py`

**Files to modify:**
- `spacegame/engine/game.py` — replace inline factories with ViewFactory delegation

**Verification:**
- [ ] Game launches and all state transitions work (manual smoke test)
- [ ] All existing tests pass (especially test_game.py)
- [ ] game.py reduced by ~800 lines

### 2B: Extract State Transition Logic

**Problem**: `_handle_state_transitions()` in game.py is a massive switch statement (~400 lines) that routes between game states. Each case follows a pattern: check next_state on current view, call ensure_*_view, start transition.

**What to do:**
- [ ] Create a transition routing table: `dict[GameState, Callable]`
- [ ] Each entry maps a game state to its handler function
- [ ] `_handle_state_transitions()` becomes a simple lookup + call
- [ ] Handler functions live in game.py but are small, focused methods

**Risk mitigation:**
- The routing table is a pure refactor — same logic, better organization
- Each handler is testable in isolation

**Verification:**
- [ ] All state transitions verified via manual game testing
- [ ] All tests pass

---

## Session 3: View File Decomposition

> **Priority**: MEDIUM — improves maintainability of the three largest views
> **Estimated scope**: Safe refactor session

### 3A: Extract Ship Builder Modes

**Problem**: ship_builder_view.py is 3,330 lines with MODULES, HULL, EQUIP, and RECOLOR modes all inline. The EQUIP mode alone is ~300 lines, RECOLOR is ~150 lines.

**What to do:**
- [ ] Create `spacegame/views/builder_equip_mode.py` — extract EQUIP mode rendering + interaction methods
- [ ] Create `spacegame/views/builder_recolor_mode.py` — extract RECOLOR mode
- [ ] Each module exports a mixin or helper class that the main view delegates to
- [ ] Pattern: `self._equip_helper = EquipModeHelper(self)` in __init__, delegate calls

**Implementation pattern:**
```python
# builder_equip_mode.py
class EquipModeHelper:
    def __init__(self, builder_view):
        self.view = builder_view  # Reference to parent view for shared state

    def render_slot_list(self, screen):
        # Extracted from _render_equip_slot_list
        ...

    def render_panel(self, screen):
        # Extracted from _render_equip_panel
        ...

    def handle_click(self, mx, my):
        # Extracted from equip click routing
        ...
```

**Risk mitigation:**
- Extract one mode at a time
- Run full test suite after each extraction
- Keep the same method names so call sites are simple renames

**Verification:**
- [ ] Builder opens and all three modes work
- [ ] All builder tests pass
- [ ] ship_builder_view.py reduced by ~450 lines

### 3B: Document Combat View Structure

**Problem**: combat_view.py is 3,770 lines. It's well-organized internally (clear section comments, phase state machine) but has no file-level structure guide.

**What to do:**
- [ ] Add a comprehensive module docstring (like we did for ship_builder_view.py)
- [ ] Map all ~3,770 lines to functional sections
- [ ] Identify extraction candidates (HUD rendering, VFX management, action panel)
- [ ] Do NOT extract yet — document first, extract in a future session if the file grows further

**Verification:**
- [ ] Docstring added
- [ ] No code changes (documentation only)

---

## Session 4: Layout Constants Consolidation

> **Priority**: LOW — improves consistency, reduces copy-paste
> **Estimated scope**: Short cleanup session

### 4A: Layout Constants — RESOLVED (Documented, Not Extracted)

**Original estimate**: "~200-300 lines of repeated coordinate math across views."

**Actual finding**: Only ~19 lines of genuine duplication across 5 files:
- 5 constants shared by journal/mission_log/crew_roster (list-detail pattern)
- 1 centering formula shared by investment/repair_bay (modal pattern)
- Everything else is intentionally different (different card heights, list widths, margins)

**Decision**: Creating a shared `layout_constants.py` for 19 lines would be over-engineering. Instead, added comments at each usage site documenting which files share the same constants. This communicates intent without adding indirection.

**What to do:**
- [ ] Create `spacegame/views/layout_constants.py`
- [ ] Define common patterns:
  ```python
  # List-detail layout (used by mission_log, crew_roster, journal)
  LIST_DETAIL_LIST_X = scale_x(40)
  LIST_DETAIL_LIST_W = scale_x(360)
  LIST_DETAIL_DETAIL_X = LIST_DETAIL_LIST_X + LIST_DETAIL_LIST_W + scale_x(20)
  LIST_DETAIL_DETAIL_W = WINDOW_WIDTH - LIST_DETAIL_DETAIL_X - scale_x(40)

  # Modal centering
  MODAL_W = scale_x(500)
  MODAL_H = scale_y(400)
  MODAL_X = (WINDOW_WIDTH - MODAL_W) // 2
  MODAL_Y = (WINDOW_HEIGHT - MODAL_H) // 2

  # Standard card sizes
  CARD_H_COMPACT = scale_y(52)
  CARD_H_STANDARD = scale_y(85)
  CARD_H_DETAILED = scale_y(120)
  ```
- [ ] Update views to import from the shared module instead of defining locally
- [ ] Leave view-specific constants (GRID_AREA_*, SHAPE_PANEL_*) in their respective views

**Risk mitigation:**
- Only consolidate constants that are truly duplicated (same values, same purpose)
- Keep view-specific constants local
- Change one view at a time, test after each

**Verification:**
- [ ] All views render correctly at all supported resolutions (720p, 900p, 1080p)
- [ ] All tests pass
- [ ] ~200 lines of duplicated constants removed across views

---

## Session Summary

| Session | Items | Severity | Estimated Effort | Dependency |
|---------|-------|----------|-----------------|------------|
| **1** | U5 retirement + unused import + TODOs | HIGH | 1 focused session | None |
| **2** | game.py decomposition (view factory + transitions) | MEDIUM | 1 careful session | None |
| **3** | View file decomposition (builder modes + combat docs) | MEDIUM | 1 session | After Session 1 |
| **4** | Layout constants consolidation | LOW | Short session | After Session 3 |

**Recommended execution order**: Session 1 → Session 2 → Session 3 → Session 4

Session 1 removes active confusion (old slot system coexisting with new module system). Session 2 makes the engine file manageable. Session 3 makes the views manageable. Session 4 is polish.

---

## Success Criteria

After all 4 sessions:
- [ ] SLOT_POOLS and DesignatedSlot marked as legacy-only (old save support)
- [ ] No [D] slot tool in hull mode
- [ ] No TODO/FIXME comments in production code
- [ ] game.py under 3,800 lines (from 4,611)
- [ ] ship_builder_view.py under 2,900 lines (from 3,330)
- [ ] Common layout constants shared across views
- [ ] combat_view.py has structure documentation
- [ ] All 5,775+ tests still pass
- [ ] Game launches and all features work identically to before
