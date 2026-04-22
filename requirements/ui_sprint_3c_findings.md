# UI Review Sprint 3c — Container Overflow Probes

Generated 2026-04-22. Data-driven overflow probes that iterate real game content through each view's container math and assert fit.

**Bottom line:** 6 new probes covering mission list items, crew roster items, trading commodity rows, achievement cards, galaxy system labels, and enemy card headers. **Five pass cleanly with current content** — writing is well-curated. **One real architectural concern catalogued** (commodity legality suffix overflow in trading rows). Tests serve as regression guards against future content additions.

Test count: **7,252 → 7,257 (+5)** plus 1 xfailed catalog entry. Full suite green, lint clean.

---

## Why 720p is the tight case

A key insight from Sprint 3a underpins Sprint 3c's scope: **fonts are fixed pixel size, containers scale proportionally**. At 1080p, every container is 1.5× wider than at 720p, but every rendered text string is the same pixel width. So text that fits a container at 720p fits the same container at every higher resolution in our matrix.

The laptop 1366×768 is wider than 720p horizontally. Steam Deck 1280×800 has the same width as 720p. So 720p and Steam Deck are the tightest horizontal constraints; testing at 720p covers both.

This is why all Sprint 3c probes run at 720p. For vertical layouts (panel height), 720p is also the tightest preset. Steam Deck 1280×800 has 80 more vertical pixels than 720p, so vertical overflow tests at 720p catch everything.

---

## Findings by view

### Mission log list items — all current content fits

`_MissionItem.render` blits `mission.name` left-anchored, status badge right-anchored, no truncation. Drydock-class pattern in theory; verified safe in practice because mission writers kept titles ≤209px rendered at 720p with 245px available (after reserving 81px for the longest badge "ABANDONED" plus margins).

Longest mission names surveyed:
- `The Wreck of the Meridian` — 209px
- `The Price of Information` — 198px
- `The Scholar's Dilemma` — 176px

Test passes. Regression guard is in place: any future mission name exceeding 245px will fail with a clear report.

### Crew roster list items — all current content fits

`_CrewItem.render` same pattern. All 19 crew templates fit with the `Lv 99`-sized badge reserved.

Test passes. Regression guard for future crew additions.

### Trading commodity rows — CATALOGUED overflow

Commodity names with legality suffix (`"Overclocked Scanner Assembly RESTRICTED"` = 355px) exceed the trading view's name-column budget (~160px at 720p, generous estimate).

The rendering pattern in `trading_view.py` line 366-378 appends a text suffix to the commodity name when legality is `RESTRICTED` or `ILLEGAL`:

```python
name_display = (f"{commodity.name} RESTRICTED", Colors.YELLOW)
name_display = (f"{commodity.name} ILLEGAL", Colors.RED)
```

Catalog mode: this is an architectural decision, not a simple overflow bug. Proper fix (when scheduled): render legality as a separate badge or color-modifier, not a text suffix. The column width estimate in the test is also conservative; actual column width at 720p may be wider. Documented with xfail so the finding stays visible without breaking the suite.

### Achievement cards — all current content fits

Achievement card at 550px width reserves 30px left padding, 100px right reward badge, and 10px gap. Available for name: 410px. Every achievement name fits.

### Galaxy map system labels — all within soft budget

System names rendered on the galaxy map stay under a 160px soft budget. The map has pan/zoom so a slightly wider label is tolerable; the test prints a warning instead of failing if the soft budget is exceeded. No entries currently exceed.

### Enemy card headers — all current content fits

All 60 enemy templates' names fit the combat card's available width (240px after reserving tier stamp).

---

## Pattern that the probes encode

Each probe follows a three-step structure:

1. Load the real data via `DataLoader`
2. Compute the view's available content width (mirroring the view's render math)
3. Measure rendered width of every entry's display text against the budget

The probes **do not render views** — they exercise the layout math directly. Cheap (~0.8s total), resilient to the Sprint 3a stale-`WINDOW_WIDTH` concerns, and surfaces what matters: does real content fit real containers.

The mirror-view's-math pattern carries a maintenance cost: if a view's render logic changes its container widths or fonts, the probe's computation must update in lockstep. That cost is acceptable for the high-visibility content types we've covered; it would not scale to every small UI region.

---

## What this sprint did NOT attempt

Per catalog mode, Sprint 3c did not:

- Probe every rendered text surface in every view (would be ~500 tests)
- Test multi-line text wrapping for panel height overflow (vertical overflow is a different class; less common in our data)
- Test truncation behavior for tooltips and transient text (tooltips auto-size; generally not a risk)
- Validate font-role-to-content-type consistency (different concern)

Future follow-ups that could build on this infrastructure:

- **Sprint 3d** (if desired): vertical overflow probes for panels with description text — mission descriptions, NPC dialogue preview, achievement tooltips
- **Trading legality refactor**: render legality as a badge instead of a text suffix; would clear the Sprint 3c xfail
- **UI chrome audit**: every card/panel with a right-anchored badge gets a targeted overlap test, applying the ground_briefing fix pattern broadly

---

## Summary of the Sprint 3 arc

| Sub-sprint | Shipped |
|---|---|
| 3a | Resolution × view smoke matrix + production-faithful subprocess bounds harness at 6 resolutions. 16 views × 6 resolutions all bounds-clean. |
| 3b | Targeted overlap tests for 5 YELLOW-risk views. 1 drydock-class bug fixed (ground_briefing). 1 fragility catalogued (dialogue response button). |
| 3c | Content-overflow probes for 6 content types. 1 architectural concern catalogued (trading legality suffix). All other content fits. |

**Sprint 3 total**: +148 tests (7,110 → 7,258), 1 real bug fixed, 2 architectural concerns catalogued, 0 regressions. The game's layout is now substantively covered by automated tests that match production behavior and iterate through real content.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,257 passed, 98 skipped, 1 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| Sprint 3c probes | 5 pass, 1 xfail (commodity legality suffix) |
| Content types covered | 6 (missions, crew, commodities, achievements, systems, enemies) |

---

## What's next

With Sprint 3 substantively complete, the natural next moves are:

**Sprint 4** — the Colors→PALETTE_ROLES wrapper per Sprint 1 Decision 1. The ship_builder and combat_view themed palettes are already prepped; the wrapper work unifies the backend and delivers colorblind remapping to the entire codebase through one file change. Probably the single highest-leverage piece of UI work remaining.

**Sprint 5** — copy compliance (UI voice audit with automated compliance tests). Partially covered today by the narrative voice tests; Sprint 5 would extend to every UI string.

**Controller support conversation** — still flagged for a dedicated session when you want to pick it up. The journal in particular likely needs a UX rethink, not just an input remap.

My recommendation is Sprint 4 next — high-leverage, well-scoped, and unblocks the colorblind accessibility goal that's been implicit in the standards doc since it shipped.
