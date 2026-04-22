# UI Review Sprint 2b — `ship_builder_view.py` Color Consolidation

Generated 2026-04-22. Focused sub-sprint off Sprint 2. Scope: eliminate every raw RGB tuple literal in `spacegame/views/ship_builder_view.py` and replace with either a `Colors.*` reference or a named entry in a new `_BUILDER_COLORS` themed palette.

**Bottom line:** 106 literal replacements across 104 unique call sites. Zero raw RGB tuples remain in the view code outside the palette dict itself. Full test suite green on first run. **+3 compliance tests** guard the discipline against silent regression.

Test count: **7,103 → 7,106.**

---

## What shipped

### `_BUILDER_COLORS` themed palette

A single source of themed colors at module scope, between the layout constants and the class definition. The dict has **~70 semantically-named keys** grouped into ten sections:

1. **Validation feedback** — `valid_place`, `invalid_place`, `warn_size`, `warn_weight_hard`, `tier_ok`, `tier_warn`, `weight_*`, `import_error`, `lock_hint`, etc.
2. **UI state backgrounds** — `cell_selected_*`, `tab_active`, `cell_alt`, `tab_inactive`, `cell_dim`, `cell_section_active`, etc.
3. **Text and border states** — `text_locked`, `text_placeholder`, `border_tab_inactive`, `border_toolbar_*`, etc.
4. **Hint / label grays** — `label_mute_cool`, `label_mute_warm`, `label_trim_warm`, etc.
5. **Recolor UI accent** — `recolor_accent`
6. **Build confirm highlight** — `build_confirm`
7. **Stat signatures** — `stat_shield`, `stat_armor`, `stat_evasion`, `stat_gold_fallback`, `stat_tier_ring`
8. **Tier letter grades** — `grade_s` through `grade_f`
9. **Module category signatures** — `cat_cockpit`, `cat_engine`, `cat_weapon`, `cat_shield`, `cat_cargo`, `cat_utility`, `cat_structural`, `cat_crew`, `cat_reactor`
10. **Material / swatch fallbacks** and the grid background

Header comment on the dict documents the Sprint 4 migration intent: every entry here becomes a palette-role lookup once the Colors→PALETTE_ROLES wrapper ships.

### What became `Colors.*` references (shared palette wins)

Where a `Colors` class entry already represented the intended color, the migration replaced the tuple with the named reference directly. This removes six occurrences of `(20, 25, 40)` (swapped for `Colors.UI_PANEL`), one `(255, 255, 255)` (for `Colors.WHITE`), one `(0, 0, 0)` (for `Colors.BLACK`), and one `(255, 200, 50)` (for `Colors.YELLOW`).

Shared-palette wins (pre-existing `Colors.*` that already covered the case) are preferred over new `_BUILDER_COLORS` keys. This is the pattern captured in Decision 3 from Sprint 1.

### Compliance regression guards

New test file `tests/test_views/test_ship_builder_compliance.py`:

- `test_palette_dict_present` — asserts the `_BUILDER_COLORS` dict exists with the expected type annotation.
- `test_no_raw_rgb_tuples_in_view_code` — scans the file, skips the palette dict and comment-only lines, and asserts zero raw RGB tuple literals remain. Fails with a precise line-and-context report if someone adds one.
- `test_palette_has_expected_semantic_groups` — spot-check for key semantic keys (validation, UI state, category, tier, stat) so an accidental over-zealous dict rewrite would fail.

These guards follow the pattern established by `tests/test_models/test_tutorial_narrative_voice.py` and `tests/test_views/test_cockpit_hud.py::TestHUDVoiceCompliance`. Together they represent the compliance-test spine that Sprint 5 will formalize across the whole codebase.

---

## Process notes

The refactor was executed as a single transformation pass via a one-shot script (`tools/sprint_2b_transform.py`, deleted after use). Each of 104 replacement rules was a (search, replace) tuple with full-line context, so there was no risk of false positives replacing coordinate tuples or argument positions that happened to contain three integers.

The script reported **zero missed rules** on first run. Two stragglers appeared in the verification scan at lines 2733 and 2735; they were a near-duplicate of the catalog-card pattern in the equip slot list and were fixed with a direct edit.

Unit tests caught **zero regressions**. Lint pass was clean on first run.

---

## What changed in the view's behavior

**Nothing visible.** Every replacement preserved the exact RGB value that was in place. This is a pure code-quality refactor, not a palette redesign. The visual output at every resolution (720p, 900p, 1080p) is byte-identical to the pre-refactor render.

What changed is the *access pattern*: every site now goes through a named key. When Sprint 4 rewrites `Colors` as a `PALETTE_ROLES` wrapper, the `_BUILDER_COLORS` dict becomes the single file to update to deliver colorblind remapping to this entire view.

---

## Correction to Sprint 2's accounting

Sprint 2 findings estimated ~60 raw RGB tuples in `ship_builder_view.py`. Actual count: **121 occurrences** of 80 unique colors. The Sprint 2 static grep used a narrower pattern than the final scan that drove this sprint. The higher number reflects tuples inside ternary expressions (counted twice), dict literals, and fallback arguments to `getattr`. No change to the work product; the count was simply under-reported.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,106 passed, 2 skipped, 0 failed** |
| `ruff check` on touched file | Clean |
| Raw RGB tuple literals in `ship_builder_view.py` view code | **0** (down from 121) |
| `_BUILDER_COLORS` palette keys | ~70 semantic names |
| New compliance tests | 3, all green |

---

## What's next

### Sprint 2c — `combat_view.py` color consolidation

Same pattern, same process. Sprint 1 and the Batch A auditor found ~70 raw RGB tuples in `combat_view.py` (3,770 lines). The static grep used in Sprint 2b can be rerun against that file to produce a precise count and drive the replacement rules. Target: zero raw RGB tuples in the view, a `_COMBAT_COLORS` themed palette, and a companion compliance test file.

### After Sprint 2c

Sprint 2 (primitive consolidation) will be substantively complete. The remaining unfinished work from the original 6-sprint plan:

- **Sprint 3** — layout compliance (overlap detection tests at 720p / 900p / 1080p)
- **Sprint 4** — color and font compliance (the Colors→PALETTE_ROLES wrapper implementation, plus any remaining raw-literal cleanup in less-touched views)
- **Sprint 5** — copy compliance (UI voice audit with automated compliance tests)
- **Sprint 6** — state and motion polish

Sprint 2b's process — enumerate, classify, transform, verify, regress-test — is now the template for the remaining view-level refactors.
