# Playtest Roadmap — Aurelia: A Ledger of Stars

Living document. Tracks playtest findings from start of playtest (2026-04-22) through iteration cycles. Every piece of feedback slots into a theme. Every theme ships as a focused sprint. Nothing falls off.

**Last updated: 2026-04-22.**

---

## Vision

**The first two hours of Aurelia feel deliberate.** Every screen teaches, every transition flows, every label fits the world. Nothing reads as an oversight, a placeholder, or an unintended experience.

The first two hours are disproportionate because:
- They decide whether the player stays
- They set the voice and register for every screen thereafter
- They are the one place we can ask *every* playtester to report on consistently

By the end of the playtest arc, the first two hours should be:
- **Guided** without being hand-holding — narrative framing carries teaching load
- **Visually coherent** — no AI-image throwbacks, no thematic misfires, no z-order jank
- **Functionally smooth** — exits are obvious, rewards display in full, tooltips land where they should
- **Thematically honest** — a scrap-built shuttle isn't a juggernaut; a tutorial NPC doesn't call you Captain

The second two hours are the first test of whether gameplay loops compound. That's where combat balance, economy pacing, and mission variety get stress-tested. Different concerns, different sprint cadence.

---

## Design principles for the playtest arc

1. **Playtest drives priority.** We don't guess what matters; feedback does. Frequency × severity determines sprint order, not developer instinct.
2. **Small bugs fixed in-line, big design questions discussed first.** Bug hygiene is continuous. Design decisions that affect voice, narrative, or UX pattern get explicit scoping before code.
3. **Every fix respects the standards doc.** `ui_design_standards.md`, `dialogue_writing_guide.md`, and the palette infrastructure are load-bearing. No fix may regress them.
4. **Write narrative first, code second.** Voice-checked copy, then implementation. Avoids two-pass rework.
5. **Catalog honestly, don't gatekeep.** Every finding logs here, even ones we defer or decide against. Visibility prevents rediscovery.
6. **Regression test every real bug.** Playtest-found bugs become permanent tests. "We found this once" is the signal to prevent "we'll find it again."

---

## Status summary (as of 2026-04-22)

| Metric | Pre-playtest (2026-04-22) | Current |
|---|---|---|
| Tests passing | 7,316 | **7,333** |
| Tests skipped | 98 | 98 |
| xfails | 0 | 0 |
| Playtest findings received | 0 | 7 |
| Findings fixed | 0 | **7** |
| Findings scoped, awaiting direction | 0 | 0 |
| Findings pending investigation | 0 | 0 |

---

## Themes

Every finding slots into one of these. Themes are how we batch work, not bureaucratic labels. A theme with 3+ findings graduates to a dedicated sprint.

### Theme P1 — Onboarding narrative

Guidance, hand-holding, and first-time teaching through the early-game screens. The standards doc calls for diegetic UI; playtest is showing specific places where guidance is weak or absent.

**Current findings**: 1 (tutorial narrative expansion for shop / drydock / shipyard).

**Scope direction**: medium-sized cohesive pass — inline prompts + bookend mechanic dialogues at transitions. Scope locked, awaiting NPC identity + progression gating decisions from user.

### Theme P2 — Flow friction

Transitions between views, exit paths, navigation clarity. The UI should be predictable: where you came from, where you're going, how to leave.

**Current findings**: 1 (shipbuilder-to-galaxy exit unintuitive).

### Theme P3 — Visual polish

Rendering details that produce "that doesn't look right" playtester reactions. Overlap, overflow, z-order, alignment, composition.

**Current findings**: 3 (Station Board reward overflow, cantina tooltip z-order, AI image in shipyard top-right).

### Theme P4 — Thematic fit

Labels, identities, narrative-voice matches. When the game classifies something in a way that contradicts its framing, the player notices.

**Current findings**: 1 (tiny shuttle labeled JUGGERNAUT).

### Theme P5 — Technical bugs

Clear-cut "the code does X, it should do Y." No design ambiguity.

**Current findings**: 1 (engine rotation not persisting in Loadout view).

---

## Findings log

Format: `[ID] Theme · Severity · Status · Title`. Severity scale: **blocker** (stops playtest), **high** (breaks feel for most players), **medium** (breaks feel for some), **low** (noticed by attentive players). Status: **open**, **in-progress**, **scoped**, **shipped**, **won't fix**.

---

### [PT-001] P4 · medium · SHIPPED · Tiny shuttle labeled JUGGERNAUT

**Reported**: 2026-04-22. 16×16 tutorial shuttle classified as JUGGERNAUT, thematically at odds with scrap-built DIY framing. Juggernaut implies bulk; a starter shuttle has none.

**Root cause**: `ShipStatsComputer.compute` classified identity by material-family ratio alone (≥35%). No absolute-size gate. A small ship with high heavy-armor ratio trivially qualified.

**Fix**: added two size gates in `spacegame/models/ship_build.py`. `MIN_IDENTITY_PIXELS=50` blocks any identity on tiny builds. `MIN_JUGGERNAUT_PIXELS=100` specifically requires bulk for juggernaut (Sentinel and Ghost can scale to smaller ships, so they only gate on the general minimum).

**Regression coverage**: 5 new tests in `tests/test_models/test_ship_build.py` (tiny-shuttle-no-identity, small-any-material-no-identity, small-sentinel-still-qualifies, small-ghost-still-qualifies, juggernaut-size-gate-boundary).

### [PT-002] P3 · medium · SHIPPED · AI ship sprite in shipyard top-right

**Reported**: 2026-04-22. The top-right preview in the shipyard showed an AI-generated ship sprite instead of the player's custom composite build. Feels inconsistent with the designed-ship experience.

**Root cause**: `_load_ship_anim` had a three-tier fallback chain. If `ShipComposite.get_surface()` returned None (or the composite wasn't set on a ship), the code fell through to a pre-baked PNG sprite from `data/assets/sprites/ships/player/` (AI-generated per the asset manifest).

**Fix**: removed the AI-sprite fallback and the polygon placeholder entirely in `shipyard_view.py`. The top-right now shows the composite of the player's build or nothing. When no composite is available, the area stays empty — the main viewport already shows the ship grid.

**Regression coverage**: no dedicated test (visual change). Inline docstring explains the rationale so future editors don't reintroduce the fallback.

### [PT-003] P5 · high · SHIPPED · Engine rotation not persisting in Loadout view

**Reported**: 2026-04-22. A module rotated in the drydock rendered in its default (unrotated) orientation in the Loadout view, making the ship preview look wrong.

**Root cause**: `ShipyardView._slot_screen_rect` computed cell dimensions with `slot_def.footprint_w` and `slot_def.footprint_h` directly, ignoring `placed_slot.rotation`. The ship_builder uses `slot_def.get_rotated(rotation)` correctly; the shipyard path did not.

**Fix**: `_slot_screen_rect` now calls `slot_def.get_rotated(placed_slot.rotation)` and uses the rotated dimensions. Covers both the Loadout grid and the Shop preview (both call through the same helper).

**Regression coverage**: 5 tests in `tests/test_views/test_shipyard_rotation.py` (rotations 0/1/2/3 plus missing-attribute default).

### [PT-004] P3 · medium · SHIPPED · Station Board quest rewards cut off

**Reported**: 2026-04-22. Side quest buttons on the cantina Station Board rendered both the contract name and credit reward inside a single fixed-width button. Long names truncated the reward text.

**Root cause**: `cantina_view.py` constructed button text as `f"Contract: {mission.name}{reward_text}"`. Single-button width could not carry both.

**Fix**: button text carries only the contract name (`"Contract: {mission.name}"`). The full reward breakdown already renders in the hover tooltip, which covers the information the button was trying to squeeze in. Side effect: removed an em-dash (`\u2014`) that the Writing Bible scanner missed because it was inside a bare variable assignment, not a direct `text=` / `.render(` call.

**Regression coverage**: no dedicated test yet; consider extending the Writing Bible scanner to catch bare-assignment em-dashes (follow-up task).

### [PT-005] P3 · medium · SHIPPED · Cantina tooltip z-order violation

**Reported**: 2026-04-22. Hover tooltips on Station Board buttons rendered BEHIND the Contacts / Crew / Station Board button panels. Playtester suggested a side pane to isolate tooltips from the menu.

**Root cause**: the view rendered the tooltip in `render()`. The game loop then ran `ui_manager.draw_ui()` AFTER `render()`, which drew pygame_gui buttons on top of the tooltip.

**Fix (architectural)**: added `render_top(screen)` hook to `BaseView` as a no-op. Game loop calls it AFTER `ui_manager.draw_ui()`, providing a dedicated "above-UI" rendering phase for views that need it. Cantina overrides `render_top` to draw the contract tooltip.

**Benefit beyond this finding**: the `render_top` hook is available to every view. Any future "this must sit on top" overlay (hover tooltips, modal confirmations, celebration banners that originate from view logic) can use it.

**Regression coverage**: none dedicated yet; the hook is simple enough that its correctness depends on docstrings and the game-loop invocation. Worth a smoke test that a view's `render_top` is called if defined (future task).

### [PT-006] P2 · medium · SHIPPED · Shipbuilder exit to galaxy is unintuitive

**Reported**: 2026-04-22. After creating their ship, the playtester struggled to figure out how to exit the builder and reach the galaxy view. Navigation was not obvious.

**Investigation**: the builder has three exit-ish buttons in the bottom bar: `BACK` (bottom-left, goes to `GameState.SHIPYARD`), `CONFIRM BUILD` (bottom-right, finalizes the build then transitions), `CLEAR ALL` (clears pixels). From the tutorial flow, the player needs to `CONFIRM BUILD` → arrive at shipyard → click `BACK` from shipyard → reach galaxy. That's two screens removed and the labels don't indicate the path.

**Fix**: shipped in the PT-C sprint alongside PT-007.

- Tutorial-mode BACK button now hidden (it routed to the shipyard, which is not useful in the tutorial flow — only CONFIRM BUILD is meaningful)
- Completion narration now points at the exit explicitly: "That'll fly. Hit CONFIRM BUILD, bottom-right, when you're ready."
- Post-confirm farewell notification surfaces on arrival at the station hub: "Mechanic: 'That'll fly. I'll push you off. Galaxy's waiting.'" — closes the loop on "now what do I do?"
- Post-tutorial, BACK remains as-is for experienced players (shipyard is a legitimate destination outside the tutorial)

### [PT-007] P1 · high · SHIPPED (Scope 2) · Narrative tutorial expansion for shop / drydock / shipyard

**Reported**: 2026-04-22. Playtester asked for "significantly stronger narrative guidance" walking the player through drydock, shop, shipyard. Current guidance is thin outside the tutorial shop.

**Scope 2 shipped** with defaults confirmed:
- NPC identity: existing unnamed "Mechanic" persona extended (working-class, terse register consistent with TUTORIAL_MANDATORY narration already in place)
- Progression gating: hybrid — prompts evolve based on build progress but never block input

**What shipped**:
- Four-priority narration state machine in the tutorial builder (`_pick_tutorial_narration`):
  1. Welcome beat ("Bay's yours. Pick a part from the list, drop it on the grid.")
  2. Rotation tip ("Tall module? Press R to rotate before you drop it.") — fires for non-square modules until the player presses R the first time, then suppresses permanently per session
  3. Per-part placement prompts (existing behavior, preserved)
  4. Completion beat pointing at CONFIRM BUILD (PT-006 resolution)
- Shop → builder bookend notification: "Mechanic: 'Bay's open. Grid's yours. Pick a part and drop it.'"
- Builder → station hub bookend notification: "Mechanic: 'That'll fly. I'll push you off. Galaxy's waiting.'"
- Tutorial-mode BACK button hidden
- 7 regression tests in `tests/test_views/test_ship_builder_tutorial_narration.py` covering each priority and priority ordering

---

## Sprint structure

Sprints are thematic batches, sized to fit a single focused session. We ship each and note what's next. No sprint attempts more than one theme; adjacent theme items get included opportunistically only when touching the same code.

### Sprint PT-A — "First visual read" (SHIPPED)

- [PT-001] Tiny shuttle JUGGERNAUT gate
- [PT-002] AI image removal
- [PT-003] Engine rotation in Loadout

**Delivered 2026-04-22.** 3 findings closed, +10 regression tests. Mostly P3 (visual polish) + P4 (thematic fit) + P5 (bug), one cohesive pass.

### Sprint PT-B — "Board & menus" (SHIPPED)

- [PT-004] Station Board reward overflow
- [PT-005] Cantina tooltip z-order + `render_top` architecture

**Delivered 2026-04-22.** 2 findings closed, 1 architectural hook shipped to support future top-layer rendering needs across every view.

### Sprint PT-C — "Onboarding narrative" (SHIPPED)

- [PT-007] Narrative tutorial expansion (Scope 2)
- [PT-006] Shipbuilder exit affordances (shipped with PT-007)

**Delivered 2026-04-22.** 2 findings closed, 7 regression tests added. Defaults accepted: existing Mechanic persona, hybrid self-paced progression. Rotation tip now has proper discoverability; exit path is explicit from both the narration and the notification on arrival.

### Sprint PT-D and beyond — reactive

Subsequent sprints formed reactively from incoming feedback. Likely themes that will emerge based on game surface area:
- Combat flow (balance, telegraph clarity, dual tech discoverability)
- Economy pacing (early-game credit tightness, mid-game progression stalls)
- Quest clarity (objectives readable, waypoints present, completion feels earned)
- Dialog & narrative (beat pacing, NPC voice coherence)

These themes will be populated as findings arrive.

---

## Decision log

Decisions we've made during this arc that we don't want to revisit unless playtest data invalidates them.

### D-001 — Fallback AI-generated sprites removed (not deprecated)

**Context**: PT-002 removed the AI-sprite fallback from the shipyard top-right. **Decision**: we are NOT deprecating AI-generated assets site-wide — they're still used for commodity icons, background art, portraits, etc. Only the ship-sprite fallback was removed, because composites are the canonical representation of the player's designed ship and the fallback contradicted that.

**If this decision breaks**: a future view shows stale AI ship art where composites belong. Re-examine that view's ship-loading path.

### D-002 — Juggernaut requires bulk, Sentinel/Ghost do not

**Context**: PT-001 added size gates. **Decision**: only juggernaut has an extra absolute-pixel requirement (`MIN_JUGGERNAUT_PIXELS=100`). Sentinel (shield-heavy) and Ghost (stealth) both have legitimate small-ship interpretations (scout craft, interceptors, shield frigates).

**If this decision breaks**: playtester finds a small ship classified as GHOST that doesn't feel right. Introduce a `MIN_GHOST_PIXELS` (or similar) proportional to observed mismatches.

### D-003 — `render_top` is the canonical place for above-UI overlays

**Context**: PT-005 added `BaseView.render_top()`. **Decision**: any view that needs to render ABOVE pygame_gui elements (tooltips, custom modals, celebrations triggered from view logic) should override `render_top` rather than render in `render()`. The render pipeline is: `render()` → `ui_manager.draw_ui()` → `render_top()` → achievement/celebration/HUD overlays → screen shake.

**If this decision breaks**: a view's tooltip still renders behind UI. Check that its `render_top` override actually exists and is spelled correctly.

---

## Out of scope for the playtest arc

Explicit non-goals so we don't scope-creep:

- **New content**: no new missions, no new systems, no new ships, no new bosses. Playtest tells us what to build; content comes after.
- **Architecture overhauls**: no rewriting combat, no new UI framework, no migrating away from pygame_gui. We polish and fix within the existing architecture.
- **Performance optimization**: unless playtest reports lag. The game runs at 60 FPS on reasonable hardware; that's the bar for now.
- **New accessibility infrastructure**: the Sprint 4/4b colorblind wrapper is live; actual remap calibration awaits colorblind playtester input. Beyond that, no new accessibility systems this arc.
- **Controller support**: flagged as a separate future design conversation; not a playtest response.
- **Fleet / multi-ship management**: Campaign Act 2 territory. Out of scope until core single-ship loop is validated.

---

## What comes after the playtest arc

When findings stop flowing (or slow to a trickle), the arc closes and we redirect:

1. **Campaign Act 2 planning** — "The Ledger" storyline continuation
2. **Content expansion** — 3 T4 boss narrative encounters; composite_build content for marquee bosses; expanded side quest diversity
3. **Colorblind calibration content pass** — with real colorblind playtesters
4. **Controller support design session**

Those are deliberate next chapters. Playtest informs which one is most urgent.

---

## How to use this document

**When a playtest finding arrives:**

1. Give it the next available `[PT-###]` ID
2. Classify into a theme (P1-P5 or introduce a new theme if warranted)
3. Assess severity (blocker / high / medium / low)
4. Assess status (open → in-progress → scoped → shipped / won't fix)
5. Append to Findings log
6. If shipping soon, batch with adjacent findings into a sprint

**When a sprint ships:**

1. Mark findings SHIPPED with commit / test references
2. Move the sprint entry to "delivered"
3. Note the fix in MEMORY.md for cross-session continuity
4. Write per-finding regression tests where applicable

**When a design decision locks in:**

1. Add to Decision log with context, decision, and "if this breaks" criterion
2. Don't re-debate closed decisions without new evidence

---

## Final notes

This roadmap is **alive**. Playtest findings will change what the sprints look like. The vision stays fixed; the route to get there adapts.

The ambition is high: "the first two hours feel deliberate" is a real bar, not a slogan. Every finding we close is one step closer. Every finding we defer with clear rationale is one piece of discipline that keeps the arc focused.

**Ship. Listen. Fix. Repeat.**
