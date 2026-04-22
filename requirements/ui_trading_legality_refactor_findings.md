# Trading Legality Badge Refactor

Generated 2026-04-22. Clears the final Sprint 3c catalog item (the last `xfail` in the test suite).

**Bottom line:** Trading view now renders commodity legality as a dedicated narrow column (`LEG`) rather than as a text suffix on the commodity name. The old design let 44 of 61 commodities lose their `RESTRICTED` label to name-column truncation at 720p — a legitimate gameplay bug (smuggling feedback disappeared). The new design shows the legality marker consistently regardless of name length.

Test count: **7,301 → 7,303** (the xfail converted into two passing assertions). Suite now has **zero xfails**.

---

## The bug

Before the refactor, `trading_view.py::_build_market_rows` rendered legality by appending a text suffix to the commodity name:

```python
if commodity.legality == Legality.RESTRICTED:
    name_display = (f"{commodity.name} [R]", Colors.YELLOW)
elif commodity.legality == Legality.ILLEGAL:
    name_display = (f"{commodity.name} [!]", Colors.RED)

if has_smugglers_eye:
    if commodity.legality == Legality.RESTRICTED:
        name_display = (f"{commodity.name} RESTRICTED", Colors.YELLOW)
    elif commodity.legality == Legality.ILLEGAL:
        name_display = (f"{commodity.name} ILLEGAL", Colors.RED)
```

With smugglers_eye active (the natural state for anyone paying attention to legality), **44 of 61 commodities** rendered wider than the 240px COMMODITY column's ~224px text budget. The `TableWidget` correctly truncated with ellipsis, but that ellipsis ate the `RESTRICTED` / `ILLEGAL` suffix — so the player saw `"Overclocked Scanner Assem..."` instead of the full `"Overclocked Scanner Assembly RESTRICTED"`.

Net effect: the smuggling feedback system silently failed for most commodities.

Sprint 3c catalogued this as an architectural concern because the proper fix was not a local patch but a rendering pattern change — render legality as a badge, not a suffix.

---

## The fix

### Column change

Added a new `LEG` column between `COMMODITY` and `PRICE` in the market table:

```python
columns=[
    ColumnDef("COMMODITY", scale_x(240), "left"),
    ColumnDef("LEG", scale_x(35), "center"),   # NEW
    ColumnDef("PRICE", scale_x(85), "right"),  # slightly tightened from 90
    ColumnDef("STOCK", scale_x(60), "right"),  # slightly tightened from 65
    ColumnDef("WT", scale_x(40), "right"),     # slightly tightened from 45
    ColumnDef("TREND", scale_x(120), "left"),
]
```

Total width stays within the 620px table rect. Four columns gave up 1-5px each to fund the 35px LEG column.

### Cell content change

```python
name_display: str | tuple[str, tuple] = commodity.name
leg_display: str | tuple[str, tuple] = ""
if commodity.legality == Legality.RESTRICTED:
    name_display = (commodity.name, Colors.YELLOW)
    leg_display = ("R*" if has_smugglers_eye else "R", Colors.YELLOW)
elif commodity.legality == Legality.ILLEGAL:
    name_display = (commodity.name, Colors.RED)
    leg_display = ("!*" if has_smugglers_eye else "!", Colors.RED)
```

- **Name** stays in the COMMODITY cell, colored by legality (color survives truncation)
- **LEG cell** holds the shape-based marker: `R` / `!` for normal visibility, `R*` / `!*` with smugglers_eye for emphatic signal

The shape-based marker preserves legality information regardless of name length. The color reinforces it. Together they satisfy `ui_design_standards.md` principle 6 ("Color informs; it never carries alone") — the R/! shape carries the signal even in grayscale or colorblind rendering.

### smugglers_eye semantics preserved

The original design differentiated smugglers_eye skill by swapping `[R]` → `RESTRICTED` (more conspicuous text). Post-refactor, smugglers_eye appends `*` to the marker (`R*` / `!*`). The skill still has a visible in-game effect; the information conveyed is equivalent (the player sees which cargo is restricted/illegal) but the rendering no longer depends on text-suffix overflow.

The skill also retains its economic effects (`get_black_market_price_modifier` at lines 752/763), which are the main mechanical value.

---

## Tests updated

The Sprint 3c `xfail` test in `tests/test_ui_layout/test_container_overflow.py` was converted into two passing assertions:

1. **`test_commodity_names_fit_column_without_suffix`** — plain commodity names (no suffix) fit the COMMODITY column, with an accepted baseline of up to 2 names that exceed the budget and rely on clean truncation.

2. **`test_legality_column_width_fits_markers`** — verifies the LEG column is wide enough for every marker variant (`R`, `!`, `R*`, `!*`) at 720p.

Four tests in `tests/test_views/test_trend_visibility.py` accessed `rows[0][4]` expecting trend at column index 4. The LEG column insertion shifted trend to index 5; updated to `rows[0][5]` with an in-line comment explaining the index shift.

---

## Final xfail status

Before this refactor: **1 xfail** across the whole test suite — the Sprint 3c commodity-suffix overflow finding.

After this refactor: **0 xfails.** Every test in the suite now either passes or is explicitly skipped with a documented reason (the 2 pre-existing skipped placeholder tests in `test_archetype_playtest_b6.py`).

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,303 passed, 98 skipped, 0 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| xfails in the suite | **0** (down from 1) |
| Trading commodities losing legality label to truncation | **0** (down from 44 / 61) |

---

## What's next

With this cleanup, the Sprint arc state is:

**Completed:** Sprint 1 → 2 → 2b → 2c → 3a → 3b → 3c → 4 → 4b → 5 → 5b → trading legality refactor.

**Remaining:**

- **Sprint 6** — state and motion polish (5 interactive states × 4 content states audit per view, motion-timing discipline). Systematic but lower-leverage than prior sprints since touched views already have most states covered through normal usage.
- **Colorblind calibration content pass** — find colorblind playtesters, empirically refine Sprint 4/4b remap tables. Needs external input, not code.
- **Controller support conversation** — flagged for a dedicated session when you want to pick it up.

My recommendation: **Sprint 6** if you want to continue the systematic cadence, or pause the UI-review arc and move to other work since the major architectural items are now closed. The remaining pieces are either content-focused (colorblind calibration) or design-shaping (controller) rather than code-focused.
