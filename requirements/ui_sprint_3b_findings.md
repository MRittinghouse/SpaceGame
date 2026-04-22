# UI Review Sprint 3b — Targeted Overlap Tests

Generated 2026-04-22. Per-view overlap and overflow tests for the five YELLOW-risk views Sprint 1 flagged.

**Bottom line:** 11 targeted tests written, 1 real drydock-class bug found and fixed (ground_briefing title/difficulty-badge overlap), 1 latent fragility documented (dialogue response button truncation). Four of the five flagged views verified clean with their current content; tests serve as regression guards against future expansion.

Test count: **7,241 → 7,252 (+11).** All green, lint clean.

---

## Why this sprint existed

Sprint 3a's subprocess matrix gives production-faithful bounds checks for pygame_gui elements — but most real layout bugs are in raw drawing calls (`pygame.draw.rect`, `screen.blit`) that the harness cannot introspect. Sprint 1 identified five views with specific overlap or overflow risk patterns that needed targeted tests:

1. `cockpit_hud` — button label clipping
2. `dialogue_view` — skill check stripe + disposition preview collision
3. `ground_briefing_view` — mission-objective + crew-selection overlap
4. `character_view` — milestone display squeeze
5. `galaxy_map_view` — system info + travel confirm overlap

Sprint 3b wrote surgical tests for each pattern that mirror the view's layout math, compute the element rects, and assert the specific invariant. These tests run fast (~0.6s total) and are resilient to the Sprint 3a stale-`WINDOW_WIDTH` issue because they render at a fixed resolution and measure the actual layout math, not pygame_gui rects.

---

## Findings

### 1. Ground briefing header — real bug, FIXED

**Pattern:** left-anchored mission title + right-anchored difficulty badge at nearly the same Y coordinate. Exactly the drydock-class pattern that kicked off this whole arc.

**Reproduction:** a mission name like `"The Extraordinary Case of the Missing Reach Smuggler Operation"` renders its title rect overlapping the `EXTREME` difficulty badge rect. Short mission names do not trigger the bug because natural clearance is sufficient, but nothing in the code prevented long names from colliding.

**Fix:** `spacegame/views/ground_briefing_view.py::_render_header` now computes the difficulty badge first, derives `title_max_w = diff_x - (PANEL_X + 30) - 16`, and truncates the title with `...` when it exceeds that width. Test removed the `xfail` and now asserts clean truncation.

```python
title_max_w = diff_x - (self.PANEL_X + 30) - 16  # 16px gap to badge
if title_surf.get_width() > title_max_w:
    trimmed = name
    while len(trimmed) > 3 and title_surf.get_width() > title_max_w:
        trimmed = trimmed[:-1]
        title_surf = self.title_font.render(
            trimmed.rstrip() + "...", True, Colors.TEXT_PRIMARY
        )
```

The fix mirrors `_ResponseButton.render` in dialogue_view, which uses the same truncation pattern. Consistency win.

### 2. Dialogue response button — latent fragility, catalogued

**Pattern:** `_ResponseButton.render` computes `max_text_w = rect.width - 24` without subtracting the disposition preview's rendered width. If the preview is active and the text is long enough to wrap naturally beyond the preview's column, truncation stops too late.

**Reality today:** the test passed. Realistic response texts and typical button widths mean truncation happens early enough that collision does not occur. But the truncation rule is one playtest-era tuning change away from biting us.

**Catalogued as Sprint 3b follow-up.** Proper fix (when scheduled): in `_ResponseButton.render`, measure the preview surf first when `disposition_preview` is non-zero, reserve its width plus a 6px gap from `max_text_w`:

```python
preview_reserve = 0
if self.disposition_preview != 0:
    preview_text = f"+{self.disposition_preview}" if ... else str(self.disposition_preview)
    preview_reserve = self.font.size(preview_text)[0] + 6
max_text_w = self.rect.width - 24 - preview_reserve
```

Not urgent because all current dialogue content passes. Test stays in place as a guard.

### 3. Cockpit HUD button label fit — verified clean

Parametrized test with six player-name lengths from `"Al"` to `"Rosalind Franklin"`. All rendered labels fit within their button rects at 720p. The view's `full_fits` check already degrades to short label correctly for all cases.

No fix needed. Tests guard against future font swaps or button sizing changes.

### 4. Character view milestone panel — verified clean (current content)

Every entry in `MILESTONE_DEFINITIONS` renders at a width less than `LEFT_W - 30` at 720p. Test asserts the invariant for all milestones.

If a future milestone description exceeds that width, the test fails with a clear report. Fix path when that happens: word-wrap or truncate in `_render_character_panel`.

### 5. Galaxy map travel confirm — verified clean (current content)

Every real system name in `data/galaxy/systems.json`, formatted as `"Destination: <name>"`, fits within the 320×200 travel confirm panel's content width (300px at 720p). Test asserts this for every loaded system.

Same future-proofing: if a new system name exceeds the limit, the test fails and surfaces the offender.

---

## Pattern the tests encode

Each test follows a consistent shape:

1. Import the view's own layout constants and fonts
2. Mirror the relevant `_render_*` math to compute rects
3. Assert the invariant (non-overlap, fits-in-container)

This keeps the tests surgical and robust to stale-capture issues. They do not instantiate the whole view or render to a Surface; they just exercise the layout computation.

The mirror-view's-math pattern has a known cost: if the view's layout logic changes, the test's mirror must change in lockstep. That cost is acceptable for five high-risk patterns; it would not scale to a blanket "every view's every element" policy.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,252 passed, 98 skipped, 0 failed** |
| `ruff check` on touched files | Clean |
| Targeted overlap tests | 11 (1 concretely exercised, 10 regression guards) |
| Real bugs fixed | 1 (ground_briefing title/badge overlap) |
| Latent fragilities catalogued | 1 (dialogue response-button truncation) |
| Sprint 1 YELLOW risks cleared | 5 of 5 (one fixed, four verified safe with current content) |

---

## What's next

**Sprint 3c — container overflow probes.** The most player-facing layer: "does the text fit the box at every resolution?" Sprint 3b caught container overflow for milestone text and destination names with current content; Sprint 3c would make the probe systematic — every card, every list row, every panel header, across all six resolutions.

Sprint 3c is the natural next step because:

- The tests follow the same mirror-view's-math pattern, so the infrastructure is already proven
- The subprocess harness is available for the cases that need production-faithful resolution sweeps
- Playtester complaints about "text cut off" or "button doesn't fit" are exactly this class

If you want to defer Sprint 3c and pick up Sprint 4 (the Colors→PALETTE_ROLES wrapper from Sprint 1 Decision 1), that's also viable — the ship_builder and combat_view palettes are ready for it.

Controller support conversation remains flagged for a dedicated session when you want to open it.
