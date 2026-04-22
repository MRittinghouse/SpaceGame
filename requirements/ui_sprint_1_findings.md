# UI Review Sprint 1 — Inventory and Baseline

Generated 2026-04-21. Scope: all 34 user-facing views under `spacegame/views/`. Audited against the principles in `requirements/ui_design_standards.md`.

---

## Bottom line

The codebase is in better shape than expected. **53% of views (18 of 34) are GREEN** at current standards. The principal risks are concentrated in three RED views that carry disproportionate rendering code and account for most of the raw color and primitive-reinvention violations. **Zero voice violations** across the entire view layer. Font compliance is **near-perfect** (37 of 38 views).

The main architectural finding: the codebase runs on two parallel color systems. The `Colors` class in `spacegame/config.py` is the de facto standard (37 views, 1,072 references). The newer `PALETTE_ROLES` / `get_role()` from `spacegame/engine/material_palette.py` is used in exactly one view, for four localized imports. The standards doc's "every color from PALETTE_ROLES" is aspirational, not current reality. A decision is needed in Sprint 4 about how to reconcile them.

---

## Scoreboard

| Score | Count | Percentage |
|---|---|---|
| GREEN | 18 | 53% |
| YELLOW | 13 | 38% |
| RED | 3 | 9% |
| **Total** | **34** | **100%** |

### GREEN views (18)

No significant issues. Safe to leave untouched for now.

- `character_creation_view.py`
- `encounter_view.py`
- `ground_exploration_view.py`
- `ground_result_view.py`
- `investment_view.py`
- `journal_view.py`
- `main_menu_view.py`
- `mining_view.py`
- `mission_log_view.py`
- `name_input_view.py`
- `pause_menu_view.py`
- `refining_view.py`
- `repair_bay_view.py`
- `salvage_view.py`
- `save_load_view.py`
- `startup_view.py`
- `statistics_view.py`
- `tutorial_overlay.py`

### YELLOW views (13)

Three to five issues each, or one pattern that could produce overlap or sizing bugs. Candidates for Sprint 3 (layout compliance) and Sprint 4 (color discipline).

| View | Top issue |
|---|---|
| `cantina_view.py` | Raw RGB accent color, manual tooltip rendering, margin risk at screen edges |
| `character_view.py` | 4 raw RGB tuples, hardcoded panel padding (+15), milestone display squeeze at 720p |
| `cockpit_hud.py` | 14 raw RGB color constants in `_SHIP_PANEL_BG` family, button label clipping risk at 1080p |
| `crew_roster_view.py` | Local `_DismissButton` class reinvents button, 8 raw button colors, hardcoded (+14) padding |
| `dialogue_view.py` | Local `_ResponseButton` class, 6 raw RGB tuples, potential response text overlap |
| `event_notification_view.py` | Manual panel drawing instead of `draw_panel`, glow effect not a primitive |
| `galaxy_map_view.py` | `_STANDING_COLORS` dict with tier RGB, system-card and travel-confirm-overlay overlap risk at 720p |
| `ground_briefing_view.py` | 1 raw RGB (255,140,40), manual crew card rendering, grid layout overlap risk |
| `settings_view.py` | 3 raw RGB tuples for panel fill and border |
| `shipyard_view.py` | Mark color dict, repeated border color (45,52,72) not extracted |
| `skill_tree_view.py` | 8 inline state colors, dashed-line color (35,35,45), node border (60,60,70) |
| `trading_view.py` | Trend color tuple (100,200,130), inconsistent legality color assignments |
| `tutorial_shop_view.py` | Purchased-state background color (20,40,25) not a named constant |

### RED views (3)

These are the targets for Sprint 2.

1. **`combat_view.py`** — Batch A. ~70 raw RGB tuples scattered through animation, arena, and status-bar rendering. Reinvented animation rendering. Extensive inline pygame drawing across ~3,770 lines. Uses `pygame.font.Font(None, ...)` 25 times despite `get_font()` being available. This is the largest single source of violations in the codebase.

2. **`ship_builder_view.py`** — Batch C. 36+ raw RGB tuples across 3,300+ lines. 42 `pygame.draw.rect` calls with many functioning as panels rather than dividers. Mixed primitive approach: composes `draw_panel` in some places, rolls its own inline elsewhere.

3. **`achievements_view.py`** — Batch A. Local `_render_achievement_card` function reinvents the card primitive. Manual border rendering. `_BADGE_COLORS` dict holds 12 hardcoded RGB tuples.

---

## Violation totals by category

### Font compliance

| Metric | Count |
|---|---|
| Views using `get_font()` | 37 of 38 |
| Files with `pygame.font.Font(None, ...)` in production code | 4 |

Violating files:
- `spacegame/views/combat_view.py` (25 instances)
- `spacegame/engine/dual_tech_controller.py`
- `spacegame/engine/damage_text.py`
- `spacegame/engine/skill_voice_overlay.py`

### Color compliance

| Metric | Count |
|---|---|
| Views using `Colors.*` (legacy) | 37 of 37 production views |
| `Colors.*` references total | 1,072 |
| Views importing `PALETTE_ROLES` or `get_role` | 1 (combat_view.py, 4 local imports) |
| Raw RGB tuple literals in view code (static scan) | 151 across 22 files |

Worst offenders for raw RGB tuples (static scan):
- `ship_builder_view.py`: 34
- `combat_view.py`: 30
- `cockpit_hud.py`: 22
- `crew_roster_view.py`: 10
- `skill_tree_view.py`: 9
- `shipyard_view.py`: 8
- `dialogue_view.py` / `journal_view.py`: 6 / 6
- `mining_view.py` / `salvage_view.py` / `refining_view.py`: 7 / 7 / 2

Distinguishing note: some RGB tuple literals live in module-level "themed palette" dicts (for example `_BADGE_COLORS`, `DERELICT_THEME`, `_STANDING_COLORS`, `_SHIP_PANEL_BG`). Those are a legitimate pattern. The violation is that they bypass the `Colors` class or `PALETTE_ROLES`, so they cannot be remapped for colorblind profiles and cannot be propagated by a palette change. Sprint 4 normalizes this.

### Primitive adoption

| Metric | Count |
|---|---|
| Views using `draw_panel` / `draw_bar` from `draw_utils.py` | ~25 of 34 |
| Views reinventing panel or card rendering inline | 3 confirmed (combat, ship_builder, achievements) |
| `pygame.draw.rect` occurrences in views | 257 across 31 files |

Not all 257 `pygame.draw.rect` calls are violations. Many are dividers, borders inside shared primitives, or small overlay accents. The violation threshold is: used as a panel background, used as a card frame, or used as a structural container.

Worst offenders for panel-like `pygame.draw.rect` patterns:
- `ship_builder_view.py`: 42 calls, many as panels
- `shipyard_view.py`: 33 calls, mostly overlays and borders (lower risk)
- `salvage_view.py`: 30 calls, mostly overlays (low risk)
- `combat_view.py`: 25 calls, mixed
- `mining_view.py` / `refining_view.py`: 16 / 16 (low risk, mostly overlays)

### Layout constants adoption

| Metric | Count |
|---|---|
| Views importing from `spacegame/views/layout.py` | 5 |
| Views using `scale_x` / `scale_y` | 32+ |

Views importing `layout.py`:
- `crew_roster_view.py`
- `galaxy_map_view.py`
- `journal_view.py`
- `mission_log_view.py`
- `station_hub_view.py`

The picture is less bad than it first looked. Most views define their own module-level constants and then use `scale_x`/`scale_y` consistently. That is acceptable but fragmented. Sprint 3 target: migrate those module-level constants into `layout.py` where they are semantically shared, leave them local where they are genuinely view-specific.

### Resolution scaling

| Metric | Count |
|---|---|
| Views using `scale_x` / `scale_y` | ~32 of 34 |
| Views with potential non-scaled pixel values | Not yet systematically tested at 720p / 900p / 1080p |

Scaling adoption is strong in principle. Sprint 3 will verify in practice with overlap-detection tests at each resolution.

### Overlap-prone patterns

No confirmed drydock-class bugs (left-anchored title + right-anchored tag on same Y) after the tutorial shop fix. Yellow-level risk areas flagged for 720p testing:

- `character_view.py` — milestone and faction display squeeze (Batch A)
- `cockpit_hud.py` — button label clipping at 1080p (Batch A)
- `dialogue_view.py` — skill check stripe and disposition preview on same row (Batch A)
- `galaxy_map_view.py` — system info panel and travel confirm overlay (Batch A)
- `ground_briefing_view.py` — crew card grid overlap (Batch A)
- `combat_view.py` — heavy animation text positioning, multi-card stacking (Batch A)

Sprint 3 will produce automated overlap tests.

### Voice compliance

**Zero violations across all 34 views.**

- No unearned "Captain" in narrative copy (one instance of "Captain" appears as a cockpit HUD button label; flagged as acceptable by the Batch A auditor since it is a UI label not a protagonist address — revisit if user disagrees).
- No "Welcome to the adventure" or "Your journey begins" copy.
- No em-dashes in view strings.
- No parallel-negation rhetoric.

Credit where due: the QA Pass 6 narrative tutorial rewrite and the existing writing bible compliance tests appear to have held the line across the whole codebase, not just the tutorials.

---

## Sprint 2 targets

Based on RED views and the highest-leverage pattern consolidations:

### Priority 1: `combat_view.py` primitive and color consolidation

- Replace all 25 `pygame.font.Font(None, ...)` calls with `fonts.get_font()`.
- Extract the ~70 raw RGB tuples into a themed palette dict (e.g., `_COMBAT_COLORS`) at module top, with each key a semantic role. Migrate to `Colors.*` or `PALETTE_ROLES` where a general-purpose role applies.
- Consolidate animation rendering into shared `draw_bar` / `draw_panel` calls where applicable.
- Split the 3,770-line file into behavior-focused modules if feasible during this sprint, or defer.

### Priority 2: `ship_builder_view.py` primitive and color consolidation

- Extract 36+ raw RGB tuples into a `_BUILDER_COLORS` dict.
- Consolidate the 42 `pygame.draw.rect` calls. Those functioning as panels go to `draw_panel`. Those functioning as dividers stay as `draw.rect` but with palette-role colors. Those functioning as module outlines get a new primitive (`draw_module_outline`) added to `draw_utils.py`.
- Resulting target: zero raw RGB tuples, zero inline panel rects.

### Priority 3: `achievements_view.py` card consolidation

- Replace `_render_achievement_card` with composition of `draw_panel` and a standard header layout.
- Migrate `_BADGE_COLORS` dict entries into `Colors.*` or into a shared badge-color map if they are cross-cutting.
- Add `draw_badge` variant for achievement badges if the existing signature is insufficient.

### Supporting work

- Audit every view for missing shared primitive opportunities. YELLOW views that use inline panel drawing (`event_notification_view`, `settings_view`, some `cantina_view` tooltip code) can be folded into the sprint if capacity allows.
- Document any new primitive added to `42_ui_chrome_components.md`.

---

## Decision points raised by this sprint

These are questions for the user, not for Sprint 2 to answer unilaterally.

### 1. Color system strategy

The standards doc says "every color from PALETTE_ROLES." The codebase says "Colors class is the standard." Three plausible strategies:

- **Strategy A**: Declare `Colors` the official system, treat `PALETTE_ROLES` as internal to the palette-snapping engine, update the standards doc.
- **Strategy B**: Declare `Colors` legacy, schedule migration to `PALETTE_ROLES` in Sprint 4, update the standards doc to note the transition.
- **Strategy C**: Rewrite `Colors` as a thin wrapper that resolves against `PALETTE_ROLES`, preserving the widely-used API while unifying the backend. Colorblind profiles then work through `Colors.*` automatically.

**Recommendation: Strategy C.** It preserves 1,072 existing call sites, unifies the backend, and delivers colorblind remapping to the whole codebase without per-view refactors. Requires auditing which `Colors.*` entries actually have a natural `PALETTE_ROLES` counterpart; some may need new roles added.

### 2. "Captain" in cockpit HUD

One "Captain" string appears as a cockpit HUD button label (per Batch A). The standards doc bans "Captain" before the narrative earns it. Is a UI label for a persistent HUD button an exception, or should it be reworded?

**Recommendation**: reword to "Log" or context-appropriate label; document the exception pattern if we want to preserve it.

### 3. Module-level themed palettes

Patterns like `_BADGE_COLORS`, `DERELICT_THEME`, `_STANDING_COLORS`, `_SHIP_PANEL_BG` are good software design (grouped, named, documented) but bypass the palette system. Should Sprint 4:

- **Option A**: preserve the pattern, migrate the dict values to reference `Colors.*` or `PALETTE_ROLES` entries.
- **Option B**: eliminate the pattern, make every color a direct `Colors.*` or palette-role reference at the call site.

**Recommendation: Option A.** The themed palette pattern is valuable for readability in complex scenes. The fix is to make the dict entries reference the canonical palette, not to eliminate the dict.

---

## Sprint 1 deliverables

- [x] Inventory complete: 34 views audited.
- [x] Violation counts by category recorded.
- [x] Per-view health scores assigned (18 GREEN, 13 YELLOW, 3 RED).
- [x] Top three Sprint 2 targets identified (`combat_view.py`, `ship_builder_view.py`, `achievements_view.py`).
- [x] Decision points surfaced for user input.

Ready for Sprint 2 once the color system strategy question is answered.
