# UI Review Sprint 2 — Primitive Consolidation (Partial)

Generated 2026-04-21. Scope: apply the three decisions from Sprint 1 and begin primitive consolidation on the RED views.

**Bottom line:** Decision-point items delivered. `achievements_view.py` refactored off its reinvented card primitive and onto `draw_panel`. Cockpit HUD voice violation eliminated with compliance tests. `ship_builder_view.py` and `combat_view.py` scoped and staged; full refactor requires their own focused sub-sprints because the color surface is larger than Sprint 1 estimated.

Test count: **7,101 → 7,103** (+2 voice compliance tests). All tests green on first run.

---

## Decisions applied (from Sprint 1)

### Decision 1: Colors→PALETTE_ROLES wrapper

**Locked as direction for Sprint 4.** No code change this session. When Sprint 4 runs, the `Colors` class in `spacegame/config.py` gets rewritten as a metaclass or property-backed wrapper that resolves through `PALETTE_ROLES` / `get_role()`. This preserves all 1,072 call sites while unifying the backend and delivering colorblind remapping to the whole codebase.

Palette coverage gap noted: `PALETTE_ROLES` today has 29 entries; `Colors` has 70+ attributes. The wrapper design for Sprint 4 must either add new roles or pass-through unmapped colors as literals.

### Decision 2: Cockpit "Captain" replaced with player name

**Shipped.** `spacegame/views/cockpit_hud.py`:

- `_NAV_BUTTONS[0]` was `("CPT", "Captain", GameState.CHARACTER)`. Now `("YOU", "", GameState.CHARACTER)`.
- `_render_buttons` substitutes `self.player.name` for the empty full-label at render time, so the button shows the player's chosen name whenever it fits. On narrow screens, the short label "YOU" shows. The tooltip also uses the player name.
- Inline doc-comment explains the intent so a future editor does not revert it.

**Regression guards added** in `tests/test_views/test_cockpit_hud.py::TestHUDVoiceCompliance`:

- `test_nav_buttons_do_not_use_captain` — asserts no `_NAV_BUTTONS` entry uses "Captain" in short or full labels.
- `test_character_button_uses_player_name` — asserts the Character button's static full label is the empty sentinel (signaling dynamic substitution) and the short label does not encode rank ("Cpt").

### Decision 3: Themed palette pattern preserved, entries migrate to canonical palette

**Partial application this sprint.** In `achievements_view.py`, the `_BADGE_COLORS` dict remains as a named themed palette at module top (the pattern we want to preserve), with a header comment making the Sprint 4 migration intent explicit. Where a natural `Colors.*` equivalent existed (the gold `wealth` tone), we swapped the literal tuple for `Colors.GOLD`. The other 11 entries stay literal until Sprint 4 adds matching palette roles.

---

## Primitive consolidation: `achievements_view.py`

**Status: DONE.**

Changes in `spacegame/views/achievements_view.py`:

1. **Card rendering now uses `draw_panel`.** The pattern that was:

   ```python
   card_surf = pygame.Surface((width, height), pygame.SRCALPHA)
   if is_unlocked:
       card_surf.fill((25, 35, 20, 200))
   else:
       card_surf.fill((20, 20, 30, 200))
   screen.blit(card_surf, (x, y))
   border_color = Colors.GREEN if is_unlocked else Colors.UI_BORDER
   pygame.draw.rect(screen, border_color, (x, y, width, height), 1)
   ```

   Is now:

   ```python
   if is_unlocked:
       bg_color = _CARD_BG_UNLOCKED
       border_color = Colors.GREEN
   else:
       bg_color = _CARD_BG_LOCKED
       border_color = Colors.UI_BORDER
   draw_panel(
       screen,
       (x, y, width, height),
       alpha=200,
       bg_color=bg_color,
       border_color=border_color,
   )
   ```

   One primitive call replaces two draw operations. The 9-slice border renders at pixel edges rather than the crisp anti-aliased rectangle pygame draws; this matches the look of every other panel in the game.

2. **Card background tints extracted to module constants** (`_CARD_BG_UNLOCKED`, `_CARD_BG_LOCKED`). Previously inline literals.

3. **Background dim uses `Colors.BLACK`** instead of `(0, 0, 0)` literal.

4. **`_BADGE_COLORS` dict header-commented** with Sprint 4 migration intent. `wealth` entry points at `Colors.GOLD`.

5. **Import**: `from spacegame.engine.draw_utils import draw_bar, draw_panel` (added `draw_panel`).

Tests: 23 view tests and 120 achievement-manager tests all green.

---

## Primitive consolidation: `ship_builder_view.py` and `combat_view.py`

**Status: STAGED. Dedicated sub-sprints recommended.**

### Why deferred

The Sprint 1 findings document underestimated the scale in two ways:

1. **ship_builder_view.py color surface**: static scan found **60+** raw RGB tuples (Sprint 1 estimated 36+). The tuples split across status feedback colors, UI state backgrounds, text-state colors, category tints, tier grades, and recolor UI. A correct extraction builds a themed palette with named semantic keys (validation, cell states, tab states, locked text, tier grades) and updates every call site. That is one to two hours of surgical work on a 3,300-line file, not an aside inside Sprint 2.

2. **combat_view.py font violations overstated**. Sprint 1 findings claimed 25 instances of `pygame.font.Font(None, ...)`. Actual count on direct grep: **1 instance** (line 4582, local damage-tier bold cache with a defensible comment). The 25 was a synthesis error confusing it with the `pygame.draw.rect` count. Correction noted for the Sprint 1 record.

### What "staged" means

- ship_builder_view raw color tuples: enumerated and classified (validation, cell states, tab states, locked text, tier grades, recolor, import UI, stat deltas). Extraction plan ready.
- ship_builder_view `pygame.draw.rect` pairs: classified. Most are small toggle-button patterns (bg + border, border_radius) that are not classic card/panel reinventions. `draw_panel` is a poor fit for them; a small `draw_button` primitive would be, or they can stay inline with palette-role colors. Sprint 2b decides.
- combat_view `pygame.font.Font(None, ...)`: one call, defensible comment, low priority. Fix: swap for `fonts.get_font("machine_bold", size)` or document the exception; defer.
- combat_view raw color tuples (~70): similar scale to ship_builder. Plan the same kind of themed palette extraction after ship_builder proves the pattern.

### Recommended next sessions

- **Sprint 2b**: ship_builder_view themed palette extraction. Build `_BUILDER_COLORS` dict. Migrate every inline tuple. Update tests if any compare colors directly. Target: zero inline RGB tuples in ship_builder_view.
- **Sprint 2c**: combat_view themed palette extraction. Same pattern. Target: zero inline RGB tuples in combat_view.
- **Sprint 2d (optional)**: small `draw_button` primitive in `draw_utils.py` if the button pattern repeats often enough across ship_builder and other views to justify it.

---

## Corrections to Sprint 1 findings

- **combat_view.py `pygame.font.Font(None, ...)` count**: claimed 25, actual 1. Synthesis error during report compilation. Update the Sprint 1 findings doc if a clean record is wanted.
- **ship_builder_view.py raw RGB tuple count**: claimed 36+, actual 60+. Sprint 1 grep was narrower than the final scan revealed.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,103 passed, 2 skipped, 0 failed** |
| `ruff check` on touched files | Clean |
| Voice compliance tests in place for cockpit | 2 new tests, both green |

Cockpit HUD voice violation is the only concrete bug fix from this sprint (the achievements refactor is a primitive consolidation, not a bug). The player no longer sees "Captain" as a persistent HUD label; they see their own name.

---

## Sprint 2 deliverables

- [x] Decision 1 captured for Sprint 4, documented.
- [x] Decision 2 shipped: cockpit "Captain" eliminated, player name substituted, compliance tests added.
- [x] Decision 3 partially applied in `achievements_view.py`, pattern documented for Sprint 4.
- [x] `achievements_view.py` refactored off reinvented card primitive onto `draw_panel`.
- [ ] `ship_builder_view.py` primitive and color consolidation — **staged for Sprint 2b**.
- [ ] `combat_view.py` primitive and color consolidation — **staged for Sprint 2c**.

Next session: decide whether to dedicate a focused Sprint 2b to ship_builder_view, or proceed directly to Sprint 3 (layout compliance and overlap detection).
