# UI Design Standards

**Aurelia: A Ledger of Stars — UI Foundations**

Generated 2026-04-21. Foundational standards document. Intended to inform multiple dedicated review sprints.

---

## Purpose

This document captures the design principles, layout contracts, and implementation discipline that make Aurelia's UI feel like a single, coherent artifact rather than 35 views that happen to ship together.

It complements, and does not duplicate:

- `requirements/overhaul/42_ui_chrome_components.md`, which defines component anatomy (panels, cards, buttons, stamps, badges).
- `requirements/overhaul/20_aesthetic_bible.md`, which defines palette, fonts, and the visual foundation.
- `spacegame/views/CLAUDE.md`, which defines the `BaseView` lifecycle and state transitions.

Those documents answer "what does it look like" and "how is it constructed." This document answers three questions those do not:

1. **Why do we make the choices we make?** Opinionated principles that decide tradeoffs.
2. **What patterns cause recurring bugs?** Anti-patterns we have actually seen, not hypothetical ones.
3. **How do we stay compliant over time?** Review checklists and compliance tests, modeled on the narrative voice tests in `tests/test_models/test_tutorial_narrative_voice.py`.

Intended readers: anyone touching a view, adding UI chrome, writing UI copy, or reviewing a PR that affects any of the above.

## Relationship to other docs

When the principles here conflict with the specifications in `42_ui_chrome_components.md` or `20_aesthetic_bible.md`, the specification wins for *what* (anatomy, palette role, sizing) and this document wins for *why* and *when* (tradeoffs, priorities, context sensitivity).

If a principle here suggests a component spec should change, update the spec rather than diverging from it.

---

## Core principles

Seven principles. Each decides a tradeoff. Each has a consequence list. Each has a counter-example from actual code so the principle is falsifiable.

### 1. The UI is the world

Every screen the player sees is a diegetic artifact. A cracked shuttle terminal, a scrapyard mechanic's clipboard, a station dossier, a galaxy chart on a scratched table. We are not presenting a dashboard. We are showing in-world readouts.

Consequences:

- Fonts are chosen for voice, not only hierarchy. Mechanical readouts use `SpaceMono`. Dialogue uses `PixeloidSans`. Narration uses `Silver`. See `spacegame/engine/fonts.py`.
- UI copy follows `requirements/dialogue_writing_guide.md`. That means working-class register, second-person internal voice, no corporate marketing tone.
- Chrome detailing (rivets, weathering, stamps, stencil labels) carries narrative weight. Panels are not neutral. They reflect who made them.
- Before deciding what a new UI surface looks like, decide what it *is* in-world.

Counter-example: the pre-polish tutorial opened with "Welcome to Aurelia! You are a trader in a galaxy of opportunity." That is a marketing voice, not a diegetic one. Rewritten in QA Pass 6 into the protagonist's internal voice, rooted in the orphan-on-a-colony-ship backstory.

### 2. Readability wins every conflict

When density, visual polish, consistency, or chrome fights legibility, legibility wins. The game ships at 720p, 900p, and 1080p. Pixel fonts at 720p are small. Contrast minima are tight. Redundant labels cost space that clarity needs.

Consequences:

- Text has minimum contrast against its background. Text on `hud_muted` against a dark panel is fine. Text on `hud_muted` against a medium panel is not.
- Never reduce a font below `FONT_MICRO` to fit content. Reflow, abbreviate, or use an icon.
- Overflow is a bug, not a visual choice. Truncate with `truncate_text()`, wrap with `word_wrap()`. Both in `spacegame/engine/draw_utils.py`.
- Line length 50 to 70 characters for body copy. Longer wraps strain pixel fonts.

Counter-example: the tutorial drydock rendered "REQUIRED" and "CHOOSE ONE" twice. Once as clean section headers above each grid (intended) and once as per-card tags at the top-right of every card (overlapping the card title at the same Y coordinate). The per-card tag was removed. The section header and border color already carried the information.

### 3. Show what the player needs to act

Not more, not less. Progressive disclosure is a tool. It is not an excuse to bury critical state under a tooltip.

Consequences:

- Critical state is visible without hovering. Low hull, insufficient fuel, illegal cargo, hostile system, locked purchase.
- Tooltips clarify. They never carry the only copy of a gameplay-relevant fact.
- Secondary information lives one layer down (detail panel, tooltip, dedicated view).
- Empty states, loading states, and error states all have copy. "Nothing here yet" is content, not silence.

Counter-example: a tooltip-only warning about dangerous cargo would fail this principle. The warning must be a visible badge or stamp. The tooltip carries the rationale.

### 4. Shared primitives, always

If a card, panel, button, bar, stamp, or badge exists in `draw_utils` / `ui_chrome` / `layout`, use it. If you need a variant, extend the primitive. Do not copy it into the view.

Consequences:

- No hardcoded RGB values in views. Use `PALETTE_ROLES` from `spacegame/engine/material_palette.py`.
- No hardcoded font calls like `pygame.font.Font(None, 24)`. Use `fonts.get_font()`.
- No hardcoded pixel spacing. Use the constants in `spacegame/views/layout.py` (`PAD_XS`, `GAP_CARD`, `LIST_WIDTH`, and so on).
- Resolution scaling via `config.scale_x()` and `config.scale_y()`. Raw pixel values that do not scale are a bug at 900p and 1080p.
- When a new primitive is needed, add it. View-local reinventions compound. Each view invents its own bugs, and cross-cutting changes become prohibitively expensive.

Counter-example: `tutorial_shop_view.py::_render_part_card` reimplemented card anatomy inline rather than composing a shared `draw_panel()` plus a standard header layout. That is how the tag overlap shipped. No other view's card had that bug because no other view's card had that code.

### 5. Voice matches earned authority

The player is a scrapyard kid from a colony ship. The game addresses them accordingly until the narrative promotes them.

Consequences:

- No "Captain" in system UI, fallback strings, or error messages unless the player has earned the rank through story.
- No corporate marketing voice in tutorials, tooltips, or onboarding.
- Faction voices carry into their UI surfaces. A Consortium station's copy is clinical. A Miners Union station's copy is terse and functional. A Crimson Reach encounter's copy is menacing.
- Writing bible bans apply to UI copy as strictly as to dialogue: no em-dashes, no "couldn't help but", no "a testament to", no parallel-negation rhetoric ("no X, no Y").

### 6. Color informs; it never carries alone

Every state distinguished by color is also distinguished by shape, icon, position, or label. We ship colorblind profiles (Protanopia, Deuteranopia, Tritanopia). We also have players on laptop screens in daylight.

Consequences:

- Critical warnings use color and an icon and position.
- Faction identification uses color and a glyph.
- Status badges use color and a stamp shape.
- Hover, selected, and disabled states differ from default by more than color: border weight, inner highlight, small offset, or glyph.
- Screen must survive grayscale. If the screen is not readable without color, color is carrying too much.

### 7. Reversibility determines friction

Reversible actions are one click. Destructive, expensive, or irreversible actions confirm once. Chains of confirmation are contempt for the player's time.

Consequences:

- Equipping an upgrade with an 80% refund path does not need confirmation. The player can undo.
- Selling a legendary module with no recovery path confirms once.
- Destructive drydock actions (scrap, strip, reset) confirm once with clear copy.
- The confirmation overlay is the one defined in `42_ui_chrome_components.md`, not a view-local modal.

---

## Layout contracts

These are enforceable invariants every view must satisfy.

### Collision

No two interactive or text elements may overlap at any supported resolution. In particular:

- Two labels on the same visual row must not share a Y coordinate with overlapping X ranges. This is the exact class of bug that produced the tutorial drydock tag-over-title.
- Icons and text must not overlap unless composited deliberately (a badge over a card corner, for example).
- Scroll-clipped content must clip cleanly. Scrollbars and content must not overlap outside the scroll region.

Test pattern: render the view at 720p, 900p, and 1080p. Capture element rects. Assert non-overlap within the same z-layer.

### Safe area and margins

- Outer margin on any view: at least `PAD_MD` from the screen edge.
- Between cards in a grid: `GAP_CARD`.
- Between sections within a panel: `GAP_SECTION`.
- Between related items within a section: `GAP_ITEM`.

All constants live in `spacegame/views/layout.py`.

### Z-order

From back to front:

1. Background layer (starfield, station backdrop, galaxy map)
2. Scene chrome (panels, bars, fixed HUD)
3. View content (cards, lists, detail panels)
4. Modal overlays (confirmation, dialogue, tooltips)
5. Toast and transient feedback (achievement popup, damage number)
6. Cursor (if custom)

Within a layer, later-drawn wins on conflict. Mixing layers across draws is a bug.

### Resolution scaling

All pixel values that affect layout go through `config.scale_x()` or `config.scale_y()`. Raw pixel values are acceptable only for:

- Hardcoded font glyph sizes where the font itself scales.
- Internal primitive implementations whose callers cannot override.

Test at 720p, 900p, and 1080p before every playtest.

---

## Information architecture

### Hierarchy

Every screen has a visual hierarchy. In pixel art, hierarchy is carried by:

1. Position (top-left for primary, reading order for sequence).
2. Size (header fonts vs body fonts, large cards vs list rows).
3. Contrast (bright on dark for primary, dim for secondary).
4. Chrome weight (full panel for primary group, divider-only for secondary).

Color is a tiebreaker, never the primary carrier.

### Scanning patterns

Players scan list views in an F-pattern, card grids in a Z-pattern, and detail panels center-out. Place primary calls to action where the scan lands.

- List-detail views: list on the left (`LIST_WIDTH` from `layout.py`), detail on the right, detail CTA at the bottom-right of the detail panel.
- Card grids: the most important card sits top-left. Sort order is explicit.
- Detail panels: title top, stats below, description below, CTA bottom.

### Progressive disclosure

Primary surface shows: identity, current state, primary action.

One layer down (hover, detail tab, expand): full stats, history, secondary actions.

Two layers down (dedicated view): full authoring, full comparison, full configuration.

If a player must hover to know whether an action is available or dangerous, the primary surface is failing.

---

## UI copy and voice

UI copy is narrative, not instructional. This is the hardest rule to hold because the obvious voice for a button is corporate and the obvious voice for an error is technical.

### Rules

- Labels in the protagonist's voice where the protagonist would say them ("Yours", "Owed", "Bill").
- Labels in a mechanic's or faction's voice where that voice owns the screen ("Parts", "Bay", "Rating").
- Buttons name the action, not the abstraction. "Buy", not "Confirm purchase". "Jump", not "Initiate".
- Error messages tell the player what to do next, in voice. "Not enough credits. Ledger's short." beats "Insufficient funds."
- Empty states carry voice. "Nothing on the board yet." beats "No results."
- Never leak developer terminology. "Module slot" is fine. "placed_module" is not.

### Writing bible compliance

UI copy is bound by `requirements/dialogue_writing_guide.md`. Banned constructions apply:

- No em-dashes anywhere in UI text.
- No "couldn't help but".
- No "a testament to".
- No parallel-negation rhetoric ("no X, no Y").
- No overused trope words on the current banned list.
- No "Captain" unless the narrative has earned it.

These are tested in `tests/test_models/test_tutorial_narrative_voice.py`. Extend that test module to cover new UI surfaces as they ship.

---

## Component discipline

### When to use a shared primitive

Always, when one exists. Specifically:

| Need | Use |
|---|---|
| Panel background | `draw_panel()` or `draw_nine_slice_panel()` |
| Progress or status bar | `draw_bar()` |
| Badge (status, tier, faction) | `draw_badge()` in `ui_chrome.py` |
| Stamp (PERMIT, ILLEGAL, RESTRICTED, APPROVED) | `draw_stamp()` |
| Tier or faction glyph | `draw_glyph()` |
| Tooltip / summary overlay | `draw_summary_overlay()` plus conventions in `42_ui_chrome_components.md` |
| Card layout | Composition of `draw_panel()` plus header plus content. See existing cards for the canonical shape. |
| Text wrapping | `word_wrap()` |
| Text truncation | `truncate_text()` |
| Color brightening for hover | `brighten()` |
| Color dimming for disabled | `dim()` |

### When to add a new primitive

When a pattern appears in two or more views, or is likely to. Add it to `draw_utils.py` (drawing), `ui_chrome.py` (chrome), or `layout.py` (constants). Update `42_ui_chrome_components.md`. Refactor existing callers.

### When not to add a primitive

When the pattern is genuinely unique to one view and unlikely to recur (the galaxy map's travel line renderer, for example). Document the intent inline.

---

## State and feedback

Every interactive element has five states:

1. Default
2. Hover (mouse over, or keyboard focus)
3. Active (mouse down, or selected)
4. Disabled (unavailable)
5. Busy (action in progress, if applicable)

Every list, grid, or content panel has four content states:

1. Loaded with content
2. Loaded empty
3. Loading
4. Error

All four content states have copy. Loading states time out. An indefinite loader is a bug.

### Disabled state

Disabled elements:

- Visually distinct via `dim()` color, and optionally a locked glyph.
- Still show a tooltip explaining why they are disabled.
- Never simply vanish if the player might look for them. A disabled "Buy" with "Not enough credits. Short by 340." is better than no "Buy" at all.

### Error state

Error states:

- Tell the player what happened, in voice.
- Tell the player what to do next.
- Do not destroy in-progress work. A field validation error is inline, not a full-screen modal.

---

## Motion and animation

Pixel art rewards restraint. Animation serves gameplay feedback. It does not decorate.

### What should animate

- Damage numbers floating up (gameplay feedback).
- Hit flashes on ships and modules (gameplay feedback).
- Card selection expanding (state feedback).
- Achievement popups (recognition feedback).
- Cinematic reveals for dual tech activations, boss entrances, legendary drops (narrative weight).

### What should not animate

- Text fading in on every label.
- Hover transitions that delay input response.
- Smooth gradients replacing palette-snapped colors.
- Idle ambient motion on static chrome.

### Animation rules

- An animation may not block input for more than 250ms without a skip affordance.
- Animations respect the palette. A flash is a palette role swap, not an arbitrary color.
- Animations degrade cleanly if the frame budget is tight. Prefer discrete animation frames over continuous interpolation for pixel fidelity.

---

## Accessibility

### Colorblind

- Three palette profiles defined: Protanopia, Deuteranopia, Tritanopia.
- Palette roles remap per profile. Individual views do not need profile-specific code.
- Design must survive grayscale. If the screen is not readable in grayscale, color is carrying too much.

### Readability

- Minimum font size `FONT_MICRO`. Below that, use an icon.
- Minimum contrast against panel backgrounds: pending explicit measurement. Until then, visually test in a sunlit room.
- Line length 50 to 70 characters.

### Input

- Every interactive element is reachable by mouse and keyboard where pygame_gui supports it.
- Enter confirms, Escape cancels, anywhere a modal is present.
- Tab order follows reading order.

---

## Anti-patterns gallery

Concrete bad patterns, with references to where they have actually appeared.

### Overlap on shared Y

Two labels on the same row, one left-anchored and one right-anchored, with overlapping X ranges.

Example: `tutorial_shop_view.py::_render_part_card` rendered the card title at `(cx + 10, cy + 6)` and a status tag at `(cx + card_w - tag_width - 8, cy + 6)`. At card widths where the title was long, they overlapped. Shipped to playtest and caught by screenshot.

Fix: remove redundant labels. The section header above the grid already said "REQUIRED" or "CHOOSE ONE". The border color already showed status.

Prevention: layout tests asserting non-overlap for every text element in every view at every supported resolution.

### Reinvented primitives

A view implementing its own card, panel, or bar rather than using the shared primitive.

Example: before consolidation, multiple views had local `_draw_card` functions. Each had subtly different padding. Each was independently buggy.

Fix: composition of `draw_panel()` plus content. Standard card layout documented in `42_ui_chrome_components.md`.

Prevention: grep tests looking for common pattern signatures (local `_draw_card`, `_draw_panel`, raw `pygame.draw.rect` used as a panel background).

### Hardcoded colors

A view using `(100, 120, 140)` instead of a palette role.

Problem: colorblind profiles cannot remap the color. Balance changes to the palette do not propagate. The color drifts relative to the rest of the UI.

Fix: replace with `PALETTE_ROLES["hud_muted"]` or the correct role.

Prevention: grep for RGB tuples in `spacegame/views/`. Allowed only when composed through a primitive that accepts a color (the primitive itself uses the role).

### Hardcoded fonts

A view calling `pygame.font.Font(None, 18)` instead of `fonts.get_font()`.

Problem: system-default fonts are not in the game's voice. Scale does not follow resolution changes. The font cache is bypassed.

Fix: use `fonts.get_font("label", "sm")` or the appropriate role.

Prevention: grep for `pygame.font.Font` outside `spacegame/engine/fonts.py`.

### Raw pixel spacing

A view with `cx + 10, cy + 6` instead of `cx + PAD_SM, cy + PAD_XS`.

Problem: changes to the spacing system do not propagate. Resolution scaling may be missed. Consistency drifts.

Fix: replace with layout constants.

Prevention: review checklist, lint rule if feasible.

### Tooltip-only critical info

A dangerous cargo tag visible only as a tooltip on hover.

Problem: players miss it. Mobile interaction patterns leak into a keyboard-and-mouse game.

Fix: badge or stamp visible at rest. Tooltip carries the rationale.

### Corporate voice

"Welcome to the adventure!" "Your journey begins!" "You are a trader in a galaxy of opportunity."

Problem: breaks diegesis. Voice mismatch with the rest of the game.

Fix: rewrite in protagonist voice. See the QA Pass 6 tutorial rewrite.

### Premature "Captain"

Any UI copy calling the player Captain before the narrative has earned it.

Problem: voice mismatch. The player knows they are a scrapyard kid.

Fix: no honorific, or an in-world fallback ("kid", "friend", context-dependent).

### Chain of confirmations

"Are you sure?" followed by "Really sure?" followed by "Final confirmation."

Problem: contempt for the player's time.

Fix: one confirmation for destructive actions. None for reversible ones.

### Stale label after state change

A button that still says "Buy" after the player equipped the item.

Problem: the view is not reacting to state correctly.

Fix: bind labels to state, not to initial conditions.

### Modal covering the data it describes

A confirmation overlay that hides the item it is confirming.

Problem: the player cannot verify what they are about to do.

Fix: confirmation overlay respects a safe area around the decision target, or quotes the target inside the overlay.

### Animations that block input

A card expansion animation taking 400ms and swallowing clicks.

Problem: players feel the game is sluggish.

Fix: snap or shorten. Accept clicks during animation.

---

## Review checklist

For every PR that touches a view, UI component, or UI copy, the author and the reviewer both tick:

**Lifecycle**

- [ ] View subclasses `BaseView`.
- [ ] `_create_ui` paired with `_destroy_ui`.
- [ ] `on_enter` and `on_exit` chain to super.
- [ ] pygame_gui elements are destroyed on exit.

**Primitives**

- [ ] Panels via `draw_panel` / `draw_nine_slice_panel` / pygame_gui panel.
- [ ] Cards compose shared panel plus standard header pattern.
- [ ] Bars via `draw_bar`.
- [ ] Badges and stamps via `ui_chrome.py`.
- [ ] Text wrapping via `word_wrap`, truncation via `truncate_text`.
- [ ] Raw `pygame.draw.rect` is not used as a panel background.

**Colors**

- [ ] Every color from `PALETTE_ROLES` or composed through a primitive.
- [ ] Zero raw RGB tuples in view code.
- [ ] Hover, selected, and disabled states distinct by more than color.

**Fonts**

- [ ] Every font via `fonts.get_font()`.
- [ ] Zero `pygame.font.Font(None, ...)` calls.
- [ ] Font role matches voice context (machine, dialogue, narration, label, stats, header).

**Layout**

- [ ] Spacing via `layout.py` constants.
- [ ] All pixel values scaled via `scale_x` and `scale_y`.
- [ ] Tested at 720p, 900p, and 1080p.
- [ ] Zero overlap between interactive or text elements at any resolution.

**Copy**

- [ ] Voice matches screen context and `dialogue_writing_guide.md`.
- [ ] Zero em-dashes. Zero banned tropes.
- [ ] Zero premature "Captain". Zero corporate voice.
- [ ] Empty, loading, and error states all have copy.
- [ ] Buttons name the action, not the abstraction.

**State and feedback**

- [ ] Every interactive element has five states covered (default, hover, active, disabled, busy).
- [ ] Every content surface has four states covered (content, empty, loading, error).
- [ ] Disabled elements still explain themselves.
- [ ] Errors say what to do next.

**Motion**

- [ ] Zero animations block input for more than 250ms without a skip.
- [ ] Animations use palette roles, not arbitrary colors.
- [ ] Motion serves feedback, not decoration.

**Accessibility**

- [ ] Screen survives grayscale.
- [ ] Screen tested with at least one colorblind profile.
- [ ] Zero information carried by color alone.
- [ ] Enter confirms, Escape cancels where modals are present.

---

## Compliance testing

Modeled on `tests/test_models/test_tutorial_narrative_voice.py`, which already guards the tutorial rewrite. Extend that test suite, or add new test files under `tests/test_ui/`.

### Static compliance tests

Cheap, and they catch entire classes of regression.

- **No raw RGB tuples in views.** Grep `spacegame/views/` for `\([0-9]+,\s*[0-9]+,\s*[0-9]+\)`. Assert zero matches outside allow-listed primitive implementations.
- **No `pygame.font.Font(None`.** Assert zero matches outside `spacegame/engine/fonts.py`.
- **No raw pixel spacing in views.** Harder to automate fully. Start with a manual audit, then add spot tests for high-risk files.
- **Writing bible compliance for UI strings.** Extend the existing narrative voice tests to cover every UI string: button labels, tooltips, error messages, empty states. Strings live in JSON data files and in class-level constants.

### Layout compliance tests

More expensive. These catch the tutorial drydock class of bug.

- **Overlap detection.** Render each view at 720p, 900p, and 1080p with test fixtures. Capture rects of all text and interactive elements. Assert non-overlap within each z-layer.
- **Margin compliance.** Assert outer elements respect `PAD_MD` from screen edges.
- **Scale compliance.** Assert that toggling resolution scales all UI element rects proportionally.

### Voice compliance tests

- **"Captain" scan.** Assert the literal string "Captain" appears only in story-gated contexts.
- **Corporate voice scan.** Assert banned phrases ("Welcome to the adventure", "Your journey begins", and the evolving list) do not appear.
- **Faction voice consistency.** For each faction's station copy, assert voice markers consistent with `character_voices.md`.

---

## Review sprint structure

Six sprints. Each produces green tests that make backsliding visible. Run them in order.

### Sprint 1: Inventory and baseline

Goal: know the current state.

- Run static compliance tests against the current codebase. Record violations.
- Audit all 35 views against the review checklist. Record a health score per view (green, yellow, red).
- Identify the three worst offenders. They become Sprint 2's targets.

Deliverables: inventory report, violation count by category, target list for subsequent sprints.

### Sprint 2: Primitive consolidation

Goal: eliminate view-local reinventions.

- Find local panel, card, and bar implementations. Replace with shared primitives.
- Add any missing primitives to `draw_utils` / `ui_chrome` / `layout`.
- Update `42_ui_chrome_components.md` with new or clarified primitives.

Deliverables: reduced duplication, updated component spec, green compliance tests for primitive use.

### Sprint 3: Layout compliance

Goal: eliminate overlap and spacing drift.

- Implement the overlap detection test suite.
- Fix every overlap it finds.
- Fix every hardcoded pixel value in views. Replace with `layout.py` constants.
- Verify every view at 720p, 900p, and 1080p.

Deliverables: green overlap tests, zero raw pixel values in views.

### Sprint 4: Color and font compliance

Goal: lock palette and font discipline.

- Replace every raw RGB tuple with a palette role.
- Replace every `pygame.font.Font(None, ...)` with `fonts.get_font`.
- Run grayscale test. Fix color-only information carriers.
- Run each colorblind profile. Fix any remaps that break readability.

Deliverables: green color and font compliance tests, colorblind-clean UI.

### Sprint 5: Copy compliance

Goal: unify UI voice.

- Audit every UI string against the writing bible.
- Audit every error and empty state for voice and actionability.
- Audit every button label for action-name clarity.
- Extend compliance tests to cover every string.

Deliverables: green copy compliance tests, voice consistency across all views.

### Sprint 6: State and motion

Goal: polish the feel.

- Audit every interactive element for five-state coverage.
- Audit every content surface for four-state coverage.
- Audit animations for input blocking and palette discipline.
- Fix. Test.

Deliverables: feel-polish report, tests where automatable.

### After the sprints

Compliance tests run in CI from this point forward. New views are born compliant or they do not merge. The review checklist is the PR template for any UI-affecting change.

---

## Living document

This document is expected to grow. When a review sprint uncovers a new anti-pattern, add it. When a principle turns out to be wrong in practice, revise it. When a primitive is added, link it.

Ownership: the standards document is owned by whoever is currently leading UI work. Material changes require a one-line note in `MEMORY.md` so cross-session context stays accurate.

---

## Appendix A: Principle quick card

For posting above a monitor during a review sprint.

1. The UI is the world.
2. Readability wins every conflict.
3. Show what the player needs to act.
4. Shared primitives, always.
5. Voice matches earned authority.
6. Color informs; it never carries alone.
7. Reversibility determines friction.

## Appendix B: "Always use" checklist

For every new view:

- `BaseView` for the class.
- `PALETTE_ROLES` for every color.
- `fonts.get_font()` for every font.
- `layout.py` constants for every pixel value.
- `scale_x` / `scale_y` for every position.
- Shared primitives from `draw_utils` and `ui_chrome` for every panel, bar, badge, and stamp.
- Writing bible for every string.
- Five interactive states. Four content states.

If any of those is missing, the view is not ready.
