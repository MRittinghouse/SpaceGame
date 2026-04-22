# Visual Polish & Developer Tooling Plan

> **Status**: PLANNING
> **Created**: 2026-03-25
> **Context**: After completing the Shipbuilder Upgrade (14 phases), Systems Unification (U1-U4), and Tech Debt Cleanup, this plan addresses visual polish and development experience improvements identified during dependency review.

---

## Session P1: Custom Font Integration

> **Impact**: HIGH — transforms the game from "programmer art" to "polished indie"
> **Risk**: LOW — no new dependencies, just TTF files + FontCache updates

### Font Selection (6 fonts, 5 categories)

| Role | Font | License | Source | Usage |
|------|------|---------|--------|-------|
| **Body / Dialogue** | Pixeloid Sans | OFL 1.1 | itch.io | NPC dialogue, descriptions, item text, menu body text |
| **Headers / Titles** | Press Start 2P | OFL 1.1 | Google Fonts | Screen titles ("SHIPYARD", "COMBAT"), section headers |
| **Narration / Flavor** | Silver | CC BY 4.0 | itch.io | Environmental descriptions, flavor text, station atmosphere, journal entries |
| **Machine / System** | Space Mono | OFL 1.1 | Google Fonts | System messages, scan results, build codes, "LEGENDARY THREAT" flash, computer readouts |
| **Numbers / Stats** | monogram | CC0 | itch.io | Stat panels, credit amounts, coordinates, weight bars, combat damage numbers |
| **Small Labels** | Tiny5 | OFL 1.1 | Google Fonts | UI badges, category tabs, slot identifiers, minimap labels |

### Narrative Design Intent

The font split serves a storytelling purpose:
- **Pixel fonts** (Pixeloid, Press Start, Silver, monogram, Tiny5) feel *human* — warm, crafted, personal
- **Space Mono** feels *synthetic* — cold, precise, mechanical
- When the Ledger Phantom speaks, it uses Space Mono. When an NPC at Haven's Rest tells you about their garden, it uses Pixeloid Sans. When the narrator describes a nebula, it uses Silver. The font IS the voice.

### Implementation

- [ ] Download all 6 fonts as TTF files
- [ ] Create `assets/fonts/` directory with subdirectories per font
- [ ] Add license files for each font (OFL, CC BY, CC0)
- [ ] Update `spacegame/engine/fonts.py`:
  - Add font category enum: `FONT_ROLE_BODY`, `FONT_ROLE_HEADER`, `FONT_ROLE_NARRATION`, `FONT_ROLE_MACHINE`, `FONT_ROLE_STATS`, `FONT_ROLE_LABEL`
  - Update `FontCache` to load TTF by role + size (not just size)
  - Keep system font as fallback if TTF file missing
  - Resolution scaling still applies (720p reference)
- [ ] Add semantic font constants to replace current numeric-only system:
  ```python
  # Current: FONT_LG, FONT_MD, FONT_SM (size only)
  # New: FONT_DIALOGUE_MD, FONT_HEADER_LG, FONT_NARRATION_MD, etc.
  ```
- [ ] Update key rendering call sites (prioritized by visibility):
  - Combat view: damage numbers → monogram, action names → Pixeloid, "LEGENDARY THREAT" → Space Mono
  - Station hub: location names → Press Start 2P (headers), descriptions → Silver (narration), chatter → Pixeloid (dialogue)
  - Ship builder: title → Press Start 2P, stats → monogram, module names → Pixeloid, advisory warnings → Silver
  - Dialogue view: NPC speech → Pixeloid, narrator text → Silver, system/AI text → Space Mono
  - Galaxy map: system names → Press Start 2P, danger labels → Tiny5
- [ ] Add attribution in credits screen for Silver (CC BY requirement)

### Verification
- [ ] All text renders correctly at 720p, 900p, 1080p
- [ ] No text overflow or clipping from font size differences
- [ ] Font fallback works if TTF files are missing
- [ ] All tests pass

---

## Session P2: Easing Functions — COMPLETE

> **Impact**: MEDIUM — every animation in the game gets more polished
> **Risk**: ZERO — pure math, no dependencies

### Implementation

- [x] `spacegame/engine/easing.py` — 9 easing functions + Tween/TweenGroup + `lerp()` + `lerp_color()`:
  - `linear`, `ease_in_quad`, `ease_out_quad`, `ease_in_out_quad`
  - `ease_out_cubic`, `ease_in_out_cubic`, `ease_out_back`, `ease_out_bounce`, `ease_out_elastic`
  - `lerp(a, b, t, ease=None)` — convenience interpolation with optional easing
  - `lerp_color(c1, c2, t, ease=None)` — per-channel color interpolation with clamping
  - `Tween` class with on_complete callback, `TweenGroup` for batch management

- [x] Updated animation call sites (high-value only, no over-engineering):
  - **Combat bar lerps** (combat_view.py): exponential decay replaces constant-speed chase — big hits snap, small changes settle
  - **Galaxy map travel** (galaxy_map_view.py): `ease_in_out_quad` — ships accelerate on departure, decelerate on arrival
  - **Build confirmation** (ship_builder_view.py): `ease_out_back` scale pop-in + `ease_out_quad` alpha/flash — satisfying bounce
  - **Module placement flash** (ship_builder_view.py): `ease_out_quad` — bright flash, smooth fade
  - Floating text already used `ease_out_cubic` (no change needed)
  - Panel slide-ins / mode toggle: no actual animations exist yet (aspirational, skipped)

- [x] 44 tests (boundaries, midpoints, monotonicity, overshoot, clamping, Tween lifecycle, TweenGroup pruning)

### Verification
- [x] All 5,788 tests pass
- [x] Clamping prevents visual glitches at edge cases (t<0, t>1)
- [x] No regression in existing animations

---

## Session P3: Developer Tooling — COMPLETE

> **Impact**: Development speed and feedback loops
> **Risk**: LOW — dev-only dependencies, don't ship with game

### P3a: ruff (Lint + Format) — COMPLETE

- [x] ruff installed and configured as the **sole linter and formatter** in `pyproject.toml`
- [x] **Replaced black** — `ruff format` now handles all formatting (93 files reformatted on adoption)
- [x] **Replaced pylint** — ruff + mypy covers 95%+ of practical value; pylint was never installed
- [x] **Replaced isort** — ruff's `I` rules handle import sorting natively
- [x] Lint rules: `E`, `F`, `W`, `I`, `B` (bugbear), `C4` (comprehensions), `PIE`, `RUF`
- [x] Deliberately excluded: `UP` (contradicts `Optional[X]` conventions), `N` (game code false positives), `SIM` (opinionated about nested ifs), `RET` (subjective style)
- [x] All findings resolved:
  - 245 auto-fixed (import sorting, unused imports, f-strings)
  - 20 unused variables manually removed, 1 bare `except` fixed
  - 28 unused loop/unpacked variables renamed to `_`
  - 12 bugbear/comprehension/pie fixes
  - 3 `zip()` calls given `strict=True`
  - 1 real bug found and fixed: `target_name` undefined in chain fire code
- [x] `ruff check spacegame/` and `ruff format --check spacegame/ tests/` both pass clean

### P3b: pytest-xdist (Parallel Tests) — COMPLETE

- [x] pytest-xdist installed and added to dev dependencies
- [x] `pytest -n auto`: 5,788 tests in ~17s (down from ~38s sequential) — 2x speedup
- [x] Zero isolation issues — passed on first parallel run, stable across multiple runs
- [x] `[tool.pytest.ini_options]` added with `testpaths = ["tests"]`
- [x] NOT defaulted to parallel — opt-in via `-n auto` (conflicts with `--pdb` and coverage)

### P3c: uv (Package Management) — COMPLETE

- [x] uv already available on system (v0.7.3)
- [x] `uv sync --extra dev` successfully manages full dependency tree
- [x] `uv.lock` generated with pinned versions + hashes for all 27 packages
- [x] No changes needed to pyproject.toml or hatchling build system
- [x] Added `uv sync --extra dev` as preferred install command in CLAUDE.md

### Tool Consolidation Summary

| Before | After | Notes |
|--------|-------|-------|
| black (formatter) | **ruff format** | Single tool for lint + format |
| pylint (linter) | **ruff check** | Never installed; ruff + mypy sufficient |
| isort (imports) | **ruff I-rules** | Built into ruff |
| pip (packages) | **uv sync** | Lockfile, faster installs |
| mypy (types) | **mypy** | Unchanged — ruff doesn't do type checking |
| pytest + xdist | **pytest -n auto** | 2x faster with parallel |

Dev toolchain: **ruff + mypy + pytest** — three tools, complete coverage.

---

## Session P4: Procedural Generation Enhancement — COMPLETE

> **Impact**: MEDIUM — better space backgrounds and atmosphere
> **Risk**: ZERO — no new dependencies, pure pygame math

### Evaluation Decision

Evaluated opensimplex and NumPy noise. **Decided against external dependencies.** The visual improvements
achievable with pure pygame drawing primitives and Gaussian math exceeded what noise libraries would
add at this project's pixel scale. Starfields were already effective; nebulae and planets were the targets.

### Nebula Generation — Rewritten

- [x] Replaced flat transparent circles with **Gaussian radial falloff blobs**
- [x] Three-layer structure: large diffuse base (8-14 blobs), medium detail (15-25 blobs), small bright cores (5-10 blobs)
- [x] Soft cloud-like edges instead of visible disc outlines
- [x] Performance: 6.6ms at 720p, 14ms at 1080p (generated once, cached)
- [x] Seeded determinism preserved

### Planet Generation — Improved

- [x] Replaced per-pixel alpha blending with **circular-masked band rendering** (pygame primitives)
- [x] Varied band widths with 55% coverage probability for natural patterns
- [x] Added **light crescent** effect (sunlight from upper-left) for 3D depth
- [x] Performance: 0.04ms per planet at r=12 (gallery map size) — effectively free
- [x] Scalable to larger radii without per-pixel bottleneck
- [x] 11 planet types with distinct color palettes retained

### Starfield — Unchanged (already effective)

- Evaluated adding dust lanes and density variation
- Decided against: parallax scrolling layer already provides visual interest
- Uniform scatter reads naturally as deep space at game scale

### Not in scope:
- Shader effects (requires OpenGL, different rendering paradigm)
- Real-time lighting (wrong for pixel art aesthetic)
- opensimplex/NumPy noise (overkill for this visual scale)

---

## Future Evaluation: UI Framework

> **Status**: EARMARKED for future discussion, not planned

The current custom UI works and is well-tested. However, as the game grows:
- More complex dialogues (branching with portraits, emotions)
- Inventory management (drag-and-drop)
- Settings menus (sliders, toggles, keybinding)
- Tooltips (rich, positioned, multi-line)

**Options to evaluate when the need arises:**
1. **Deeper pygame_gui usage** — We use <10% of its widgets. UIPanel, UIScrollingContainer, UISelectionList could replace some custom rendering.
2. **Thorpy** — pygame UI library with more modern widget set, theme support. Would require significant migration.
3. **Dear ImGui (via pyimgui)** — Immediate-mode GUI, excellent for dev tools and debug overlays. Could coexist with pygame_gui for game UI.
4. **Custom evolution** — Continue building our own, extracting reusable components as patterns stabilize.

**Decision criteria**: evaluate when we hit a UI task that the current system handles poorly (e.g., complex settings menu, drag-and-drop inventory, accessibility features).

---

## Implementation Order

| Session | What | When |
|---------|------|------|
| **P1** | Custom fonts (6 TTFs + FontCache) | Next — highest visual impact |
| **P2** | Easing functions + animation updates | After P1 — builds on visual polish |
| **P3a** | ruff linter | Quick setup, do alongside P1 |
| **P3b** | pytest-xdist | After P3a — needs test isolation verification |
| **P4** | Procedural gen evaluation | Future visual polish pass |
