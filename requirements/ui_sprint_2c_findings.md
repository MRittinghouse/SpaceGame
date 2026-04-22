# UI Review Sprint 2c — `combat_view.py` Color Consolidation

Generated 2026-04-22. Focused sub-sprint off Sprint 2. Scope: eliminate every raw RGB tuple literal in `spacegame/views/combat_view.py` and replace with a `Colors.*` reference, a module-level named constant (preserved for legacy), or a named entry in a new `_COMBAT_COLORS` themed palette.

**Bottom line:** 91 literal replacements across 86 unique call sites. Zero raw RGB tuples remain in the view code outside the palette dict. Full test suite green on first run. **+4 compliance tests** guard the discipline against silent regression.

Test count: **7,106 → 7,110.**

With Sprint 2c complete, the two largest RED views from Sprint 1 are now fully discipline-compliant on colors. Sprint 2 is substantively done.

---

## What shipped

### `_COMBAT_COLORS` themed palette

A single source of themed colors at module scope, between the bar-rendering constants and the utility-function block. The dict has **~75 semantically-named keys** grouped into ten sections:

1. **Core element signatures** — `shield`, `energy`. Exported via the module-level aliases `SHIELD_COLOR` and `ENERGY_COLOR` that now resolve through the dict.
2. **Banners and callouts** — `combo_banner`, `boss_header`, `boss_accent`, `boss_bg_dark`, `boss_bg_border`, `combo_tag`, `ult_text_pulse`.
3. **Momentum and ultimate bar thresholds** — `momentum_charged`, `momentum_surging`, `momentum_overload`, `momentum_blazing`, `double_damage`.
4. **Telegraph states (enemy intent)** — `tele_evading`, `tele_fortifying`, `tele_draining`, `tele_charging`, `tele_attacking`, `tele_frozen`.
5. **Archetype identities** — `archetype_juggernaut`, `archetype_sentinel`, `archetype_ghost`. Visual values deliberately match the ship builder's archetype dict so the same ship reads the same across both contexts.
6. **Boss bar stages** — `boss_bar_low`, `boss_bar_mid`, `boss_bar_danger`.
7. **Damage-text palette** — `dmg_cryo`, `dmg_generic_warm`, `dmg_armor_deflect`, `dmg_near_miss`, `dmg_shield_regen`, `dmg_energy_boost`, `dmg_momentum`, `dmg_chill`, `dmg_burn`, `dmg_voltaic`, `dmg_counterstrike`, `dmg_vulnerability`.
8. **Passive text colors** — `passive_last_stand`, `passive_positive_dim`, `passive_counterstrike_bright`.
9. **Modal and action chrome** — `panel_modal_bg`, `panel_modal_bg_dark`, `tab_{attack,defend,utility,coord}_{bg,border}`, `tab_inactive_text`, plus the queue / execute / undo / skip-hint tones.
10. **Legendary active buttons** — `void_release_{bg,border,text}`, `overdrive_{bg,border,text}`.

Header comment on the dict documents the Sprint 4 migration intent: every entry resolves through `PALETTE_ROLES` once the Colors-wrapper ships.

### What became `Colors.*` references (shared palette wins)

Where a `Colors` class entry already represented the intended color, the migration used the named reference directly rather than creating a palette key:

- `(0, 0, 0)` → `Colors.BLACK` (background dim fill)
- `(255, 255, 255)` → `Colors.WHITE` (badge text)
- `(20, 25, 40)` → `Colors.UI_PANEL` (inactive tab bg)

This preserves the "shared palette wins" rule from Sprint 1 Decision 3.

### Module-level aliases preserved, re-anchored

`SHIELD_COLOR` and `ENERGY_COLOR` are used from nine call sites across the file. Instead of renaming every call site or embedding a raw tuple at module scope, the aliases now resolve through the palette:

```python
SHIELD_COLOR = _COMBAT_COLORS["shield"]
ENERGY_COLOR = _COMBAT_COLORS["energy"]
```

The legacy call sites keep working unchanged, and the palette remains the single source of truth. A dedicated compliance test asserts the alias shape stays correct.

### Compliance regression guards

New test file `tests/test_views/test_combat_view_compliance.py`:

- `test_palette_dict_present` — asserts the `_COMBAT_COLORS` dict exists with the expected type annotation.
- `test_no_raw_rgb_tuples_in_view_code` — scans the file, skips the palette dict and comment-only lines, asserts zero raw RGB tuple literals remain. Fails with a precise line-and-context report if someone adds one.
- `test_palette_has_expected_semantic_groups` — spot-check for 24 key semantic keys covering core elements, banners, momentum, telegraphs, archetypes, damage text, action tabs, and legendary actives.
- `test_module_level_aliases_reference_palette` — asserts `SHIELD_COLOR` and `ENERGY_COLOR` are defined as palette references, not raw tuples.

These four tests plus the three from Sprint 2b bring the total compliance-spine count for color discipline to **seven** across two views.

---

## Process notes

The refactor again used a one-shot transformation script (`tools/sprint_2c_transform.py`, deleted after use). One twist compared to Sprint 2b: the first script attempt had wrong indentation in its search strings because I had based them on the Sprint 1 dump (pre-palette-insertion) instead of the current file state. After inserting the palette dict (113 new lines), line numbers shifted but indentation was unchanged; the search-string indentation was off for reasons unrelated to line numbers.

Fix: re-dumped the file after palette insertion and rebuilt the script with exact indentation. Second run applied 91 replacements across 86 unique rules on first try. Three nominal rule misses were because the first occurrence's `str.replace` had already handled both instances of the same search string (both archetype dicts share the same 12-space indent).

Unit tests caught **zero regressions**. Lint pass clean on first run.

---

## What changed in the view's behavior

**Nothing visible.** Every replacement preserved the exact RGB value. The visual output at every resolution is byte-identical to pre-refactor render. The refactor is pure code quality.

What changed is the *access pattern*: every site now goes through a named key or shared palette constant. When Sprint 4 rewrites `Colors` as a `PALETTE_ROLES` wrapper, the `_COMBAT_COLORS` dict becomes the single file to update to deliver colorblind remapping across this entire view.

---

## Correction to Sprint 1 accounting

Sprint 1 findings estimated ~70 raw RGB tuples in `combat_view.py`. Actual count: **104 occurrences** of 73 unique colors. The undercount echoes the same issue Sprint 2b found in `ship_builder_view.py` — the Sprint 1 static grep was narrower than the final scan. No work-product change; the number was simply under-reported.

---

## Sprint 2 status after this sub-sprint

| Sub-sprint | Target view | Status |
|---|---|---|
| Sprint 2 (main) | `achievements_view.py`, cockpit Captain fix, decisions | DONE |
| Sprint 2b | `ship_builder_view.py` | DONE |
| Sprint 2c | `combat_view.py` | DONE |

All three Sprint 1 RED views are now discipline-compliant. The remaining 13 YELLOW views have smaller, scattered issues that will be absorbed into Sprint 3 (layout compliance) and Sprint 4 (color/font compliance) as they land.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,110 passed, 2 skipped, 0 failed** |
| `ruff check` on touched file | Clean |
| Raw RGB tuple literals in `combat_view.py` view code | **0** (down from 104) |
| `_COMBAT_COLORS` palette keys | ~75 semantic names |
| New compliance tests | 4, all green |

---

## What's next

### Sprint 3 — layout compliance

The tutorial drydock overlap bug that kicked off this arc was a layout-collision defect (tag-over-title on the same Y coordinate). Sprint 3's goal is to implement automated overlap detection at 720p, 900p, and 1080p so the same class of bug cannot ship again undetected.

Key tasks:

- Test harness that renders a view to a Surface at each supported resolution and captures element rects.
- Overlap detection per z-layer with clear failure reporting.
- Scale-compliance assertion: toggling resolution scales all rects proportionally.
- Apply first to the 13 YELLOW views flagged in Sprint 1, prioritizing those with confirmed overlap-risk patterns (`character_view`, `dialogue_view`, `galaxy_map_view`, `ground_briefing_view`, `cockpit_hud`).

### Alternative: deep Sprint 4 (color wrapper implementation)

If the playtest priority is colorblind support, Sprint 4 (the Colors→PALETTE_ROLES wrapper per Sprint 1 Decision 1) may justify jumping ahead. The two major views are already palette-ready; the wrapper work becomes high-leverage.

Both paths are viable. Recommending Sprint 3 next for the layout-regression safety net, but deferring to preference.
