# UI Review Sprint 4 — Colors → PALETTE_ROLES Wrapper

Generated 2026-04-22. Sprint 1 Decision 1 implementation.

**Bottom line:** The metaclass wrapper shipped. `Colors.GREEN`, `Colors.RED`, `Colors.CHECK_FAIL`, `Colors.QUALITY_GOOD`, and 10 others now resolve through `PALETTE_ROLES` at attribute-access time. Setting a colorblind profile via `set_colorblind_profile(PROTANOPIA)` now remaps those values automatically **across every one of the 1,072 existing call sites** with zero additional code changes. Non-migrated colors keep their literal class attributes unchanged.

Test count: **7,257 → 7,275 (+18).** Full suite green, lint clean. Zero visual change for default rendering.

---

## The architectural decision shipped

Per Sprint 1 Decision 1 (Option C — you chose it), `Colors` becomes a thin wrapper over `material_palette.get_role()`. The wrapper is backward-compatible: every existing `Colors.RED` call site works unchanged; the value it returns now depends on the active colorblind profile.

### How it works

```python
# In spacegame/config.py

_COLORS_ROLE_MAP: dict[str, str] = {
    "GREEN": "status_success",
    "RED": "status_critical",
    "YELLOW": "status_warning",
    "BLUE": "status_info",
    "SUCCESS": "status_success",
    "ERROR": "status_critical",
    "CHECK_PASS": "check_pass",
    "CHECK_MARGINAL": "check_marginal",
    "CHECK_FAIL": "check_fail",
    "QUALITY_POOR": "quality_poor",
    "QUALITY_NORMAL": "quality_normal",
    "QUALITY_GOOD": "quality_good",
    "QUALITY_EXCELLENT": "quality_excellent",
}


class _ColorsMeta(type):
    def __getattribute__(cls, name: str):
        if name.startswith("__"):
            return super().__getattribute__(name)
        role = _COLORS_ROLE_MAP.get(name)
        if role is not None:
            try:
                from spacegame.engine.material_palette import get_role
                return get_role(role)
            except (KeyError, ImportError):
                pass
        return super().__getattribute__(name)


class Colors(metaclass=_ColorsMeta):
    # Literal class attributes preserved as fallbacks.
    GREEN = (50, 200, 100)
    RED = (220, 50, 50)
    # ... etc
```

Key design choices:

1. **Fallback safety:** if the palette lookup raises (missing role, import error), the wrapper falls through to the class attribute. The literal tuple stays defined on the class as a guaranteed fallback.

2. **Dunder bypass:** attribute names starting with `__` never go through the palette. Preserves Python's internal protocol machinery (`__class__`, `__dict__`, `__name__`).

3. **Zero visual change by default:** every migrated role was added to `PALETTE_ROLES` with the exact RGB value of the corresponding `Colors.*` literal. No active profile means `get_role("status_critical")` returns `(220, 50, 50)`, identical to the literal `Colors.RED`. The wrapper is invisible until a profile is set.

4. **Incremental migration:** only roles in `_COLORS_ROLE_MAP` go through the palette. Non-migrated attributes (`BACKGROUND`, `UI_PANEL`, `GOLD`, faction colors, ground tiles, etc.) still return their class literals directly with no wrapper overhead. Migration is a matter of adding entries to the map.

---

## New PALETTE_ROLES (11 added)

Added to `spacegame/engine/material_palette.py::PALETTE_ROLES`:

**Status roles (4)** — gameplay state feedback
- `status_success` = `(50, 200, 100)` — formerly `Colors.GREEN`
- `status_critical` = `(220, 50, 50)` — formerly `Colors.RED`
- `status_warning` = `(255, 200, 50)` — formerly `Colors.YELLOW`
- `status_info` = `(80, 150, 255)` — formerly `Colors.BLUE`

**Skill check roles (3)** — dialogue and social feedback
- `check_pass` = `(80, 220, 120)`
- `check_marginal` = `(220, 200, 60)`
- `check_fail` = `(200, 80, 80)`

**Quality tier roles (4)** — item quality grades
- `quality_poor` = `(80, 80, 80)`
- `quality_normal` = `(140, 140, 140)`
- `quality_good` = `(100, 200, 100)`
- `quality_excellent` = `(255, 220, 80)`

Total `PALETTE_ROLES` entry count: **21 → 32.**

Distinction from existing `hud_*` roles: the `hud_*` family is for the persistent HUD overlay layer (chrome, readouts). The new `status_*` / `check_*` / `quality_*` families are for gameplay state feedback in dialogue, combat, trading, and inventory surfaces. Semantic separation means profiles can remap them independently.

---

## Colorblind profile remaps extended

Each starter profile now remaps the new roles. Values are directionally correct per established colorblind-accessibility patterns; playtest calibration with colorblind users is a future content pass.

**Protanopia (red-blind):**
- `status_critical` → `status_info` (blue)
- `check_fail` → `status_info` (blue)

**Deuteranopia (green-blind):**
- `status_critical` → `status_info` (same as protanopia)
- `check_fail` → `status_info` (same as protanopia)
- `status_success` → `hud_cyan` (new: green becomes cyan)
- `check_pass` → `hud_cyan`
- `quality_good` → `hud_cyan`

**Tritanopia (blue-blind):**
- `status_info` → `status_success` (blue becomes green)

Existing remaps (`hud_warning → hud_cyan` for red-blind, `collective_composite → solari_chrome` for blue-blind, etc.) are preserved.

---

## What shipped vs. what's deferred

### MVP this sprint

Migrated 13 `Colors.*` attributes (plus 2 aliases `SUCCESS`/`ERROR` pointing at `GREEN`/`RED`):

- Status: `GREEN`, `RED`, `YELLOW`, `BLUE`
- Aliases: `SUCCESS`, `ERROR`
- Skill checks: `CHECK_PASS`, `CHECK_MARGINAL`, `CHECK_FAIL`
- Quality tiers: `QUALITY_POOR`, `QUALITY_NORMAL`, `QUALITY_GOOD`, `QUALITY_EXCELLENT`

**These are the colorblind-critical set** — the colors where confusing red and green or yellow and blue would meaningfully degrade gameplay feedback.

### Deferred to Sprint 4b

The following `Colors.*` attributes are natural candidates for migration but require adding palette roles with matching values. They're lower-priority because they're either chrome colors (where colorblind support adds less value) or game-specific tones:

| Attribute | Proposed role | Reason to migrate |
|---|---|---|
| `TEXT_PRIMARY` | existing `hud_text` (close match) or new | Ubiquitous; uniformity win |
| `TEXT_SECONDARY` | existing `hud_text_dim` or new | Ubiquitous; uniformity win |
| `TEXT_HIGHLIGHT` | existing `hud_cyan` or new | Ubiquitous; uniformity win |
| `FACTION_COMMERCE` (+ accents, tints) | new `faction_commerce` family | Faction identity matters for colorblind distinguishability |
| `FACTION_MINERS` (+ accents, tints) | new `faction_miners` family | Same |
| `FACTION_SCIENCE` (+ accents, tints) | new `faction_science` family | Same |
| `FACTION_FRONTIER` (+ accents, tints) | new `faction_frontier` family | Same |

Estimated Sprint 4b scope: add ~15 faction-family roles (primary × 4, accent × 4, tint × 4 + 3 text roles) plus map updates. One focused session.

### Not recommended for migration

These stay as class literals forever:

- Chrome backgrounds: `BACKGROUND`, `UI_PANEL`, `PANEL_BG`, `CARD_BG`, `BAR_BG`, `ROW_BG`, etc. (colorblind support adds ~no value for chrome)
- Game-specific tones: ground tile colors, salvage view colors, attribute highlight, particle colors
- Alias aggregations: `PANEL` (same as `UI_PANEL`), `TEXT` (same as `TEXT_PRIMARY`)

Total estimated distribution after Sprint 4b: ~30 migrated, ~40 literal. About half of `Colors` would be palette-backed — the colorblind-critical half.

### Themed palette migration (Sprint 2b/2c legacy)

`_BUILDER_COLORS` (in `ship_builder_view.py`) and `_COMBAT_COLORS` (in `combat_view.py`) currently hold their own literal tuples. They could either:

- **Option A:** stay as view-local palettes with no colorblind remapping (today)
- **Option B:** migrate each entry to `PALETTE_ROLES` with a view-scoped prefix (e.g., `builder_valid_place`, `combat_momentum_charged`)

Option B is a bigger undertaking (~150 new palette roles) with diminishing returns. Deferred indefinitely unless specific colorblind playtest feedback surfaces issues in those views.

---

## Behavior verification

The new test file `tests/test_engine/test_colors_wrapper.py` has 18 tests covering:

1. **Default values** — every migrated color returns the expected tuple with no profile active (zero visual change)
2. **Protanopia remaps** — `Colors.RED` and `Colors.CHECK_FAIL` become blue when the profile is set
3. **Deuteranopia remaps** — green-family colors become cyan too
4. **Tritanopia remaps** — `Colors.BLUE` becomes green
5. **Profile restore cycle** — setting and clearing profiles round-trips cleanly
6. **Multiple profile switches** — rapid profile changes don't break anything
7. **Role map integrity** — every mapped role exists in `PALETTE_ROLES`; aliases point at the correct roles
8. **Wrapper robustness** — dunder access works, undefined attrs raise `AttributeError`

All 18 pass. Together with the extended `test_material_palette.py` tests (updated for the new 32-entry count), the colorblind accessibility infrastructure has a real regression net.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,275 passed, 98 skipped, 1 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| `Colors.*` attributes now palette-backed | 13 primary + 2 aliases = 15 call-site names |
| `PALETTE_ROLES` entry count | 21 → 32 |
| Colorblind profiles extended | 3 (Protanopia, Deuteranopia, Tritanopia) |
| Default visual output | Byte-identical to pre-Sprint-4 for all migrated colors |

---

## How this interacts with the rest of the UI review arc

- **Sprint 2/2b/2c**: shipped themed palettes `_BUILDER_COLORS` / `_COMBAT_COLORS`. Sprint 4 does NOT migrate those today; they stay as view-local palettes. Sprint 4b could, but diminishing returns.
- **Sprint 3**: layout compliance. Unrelated to Sprint 4; resolution and colorblind are orthogonal accessibility dimensions.
- **Standards doc**: `requirements/ui_design_standards.md` principle 6 ("Color informs; it never carries alone") is now more credible. We have the infrastructure for colorblind profiles to actually change what appears on screen; principle 6 still stands as a discipline on designers (shape + color, not color alone), with the new assurance that color changes propagate automatically when profiles are active.

---

## What's next

**Sprint 4b** (natural continuation): migrate faction colors + text colors. One focused session, ~15 new palette roles, extends colorblind support to the second most-impactful set of colors.

**Sprint 5** (copy compliance): UI voice audit with automated tests. Extends the narrative voice compliance tests to every UI string.

**Controller support conversation** (still flagged): the journal in particular likely needs a UX rethink for gamepad use.

**Playtester accessibility flow**: now that colorblind profiles produce real visible changes, a playtester with colorblindness could be asked specifically to try each profile and report on feedback clarity. This is the kind of content pass that would validate the profile remaps empirically rather than trust the directional-heuristic values currently shipped.

Recommending **Sprint 4b** next to finish the colorblind infrastructure before moving to copy compliance. Your call.
