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
| Tests passing | 7,316 | **7,439** |
| Tests skipped | 98 | 98 |
| xfails | 0 | 0 |
| Playtest findings received | 0 | 15 |
| Findings fixed | 0 | **15** |
| Findings scoped, awaiting direction | 0 | 0 |
| Findings pending investigation | 0 | 0 |

---

## Themes

Every finding slots into one of these. Themes are how we batch work, not bureaucratic labels. A theme with 3+ findings graduates to a dedicated sprint.

### Theme P1 — Onboarding narrative

Guidance, hand-holding, and first-time teaching through the early-game screens. The standards doc calls for diegetic UI; playtest is showing specific places where guidance is weak or absent.

**Current findings**: 5 (PT-007 tutorial narration shipped; PT-010/11/13/15 open, coalesced into the Onboarding Design scoping arc).

**Scope direction**: the second playtest round revealed the post-tutorial gap is a first-principles issue, not a polish issue. Design doc: `requirements/onboarding_design.md`. Derived sprints: PT-H / PT-I / PT-J / PT-L.

### Theme P2 — Flow friction

Transitions between views, exit paths, navigation clarity. The UI should be predictable: where you came from, where you're going, how to leave.

**Current findings**: 3 (PT-006 shipbuilder exit shipped; PT-008 part descriptions, PT-012 rename re-prompt open).

### Theme P3 — Visual polish

Rendering details that produce "that doesn't look right" playtester reactions. Overlap, overflow, z-order, alignment, composition.

**Current findings**: 3 (Station Board reward overflow, cantina tooltip z-order, AI image in shipyard top-right — all shipped).

### Theme P4 — Thematic fit

Labels, identities, narrative-voice matches. When the game classifies something in a way that contradicts its framing, the player notices.

**Current findings**: 1 (tiny shuttle labeled JUGGERNAUT — shipped).

### Theme P5 — Technical bugs

Clear-cut "the code does X, it should do Y." No design ambiguity.

**Current findings**: 1 (PT-003 engine rotation shipped).

### Theme P6 — Infrastructure

Systemic affordances that affect the whole game, not any one view.

**Current findings**: 1 (PT-009 window resizing).

### Theme P7 — System transparency

Hidden state that should be visible. Skill checks, faction deltas, cargo mass, mission objectives — the game knows, the player doesn't.

**Current findings**: consolidated from PT-014 design direction. See `onboarding_design.md` §System transparency hooks and sprint PT-K.

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

### [PT-008] P2 · medium · OPEN · Part descriptions not viewable at tutorial start

**Reported**: 2026-04-22 (playtest round 2). Player couldn't see module descriptions in the tutorial shop. "Even if they aren't very important it doesn't feel good to not be able to see them."

**Read**: minor on its own, but a symptom of the broader onboarding gap — the player has no way to learn what anything does without an NPC telling them. Hygiene fix (add description panel on hover/click) is cheap and should ship independently of the design arc.

**Status**: SHIPPED in PT-E (2026-04-22). Tutorial shop word-wraps descriptions across two lines (`tutorial_shop_view.py::_render_part_card`). Cost pinned to card bottom to make room.

**Sprint**: PT-E.

### [PT-009] P2 · high · OPEN · Window not resizable, objectives clipped off-screen

**Reported**: 2026-04-22. Player had to drag the window above the top of the screen to read an objective. Current display is `pygame.SCALED` with fixed resolution.

**Direction**: user chose straight to `pygame.RESIZABLE` rather than the cheap path. Needs careful handling because our `scale_x/scale_y` system is keyed to 720p base and 24 of 34 views bind `WINDOW_WIDTH/HEIGHT` at module scope (flagged in Sprint 3a). Letterboxing or live re-scale are the two architectural paths; implementation sprint will scope.

**Status**: SHIPPED in PT-F (2026-04-22). **Much smaller change than feared.** `pygame.SCALED` was already doing the aspect-preserving scaling from logical to physical — adding `pygame.RESIZABLE` alongside it gave us free window dragging without touching scale_x/scale_y or any of the 24 module-scope-bound views. Mouse coordinates auto-translate back through the SCALED layer. New `build_display_flags()` helper in `game.py` composes flags cleanly; F11 upgraded to use it so RESIZABLE survives fullscreen round-trip.

**Sprint**: PT-F.

### [PT-010] P1 · high · OPEN · Security desk: no "come back later" option

**Reported**: 2026-04-22. "I was wishing I would be able to leave the security desk and come back later before making a decision about who to blame... I couldn't see any sensible reason the character would have asked me in the first place."

**Read**: two problems in one. (1) Pre-choice framing is thin — the player doesn't understand why *they* are being asked. (2) The choice is hard-locked with no retreat, contradicting the "stations let you come back" pattern the rest of the game honors.

**Direction**: user greenlit "come back later" branch + decision-lock after first commitment. Paired with PT-011 in one sprint.

**Status**: SHIPPED in PT-I (2026-04-22). Scene is `dead_ledger_investigation` (Sgt. Mossa at Nexus Prime). Greet opening strengthened with explicit "why you" beat. Come-back-later responses added to `suspects` and `evidence_synthesis` nodes (top-level greet already had one). Greet responses gated on `excluded_flags: ["dead_ledger_accusation_made"]` so the investigation options vanish once an accusation is filed; new `case_closed` recap node takes their place.

**Sprint**: PT-I.

### [PT-011] P1 · medium · OPEN · Dialogue re-prompts after decision is confusing

**Reported**: 2026-04-22. After making the security desk choice, re-entering the conversation re-offered the choice menu. Felt like the decision didn't stick.

**Read**: technical manifestation of PT-010's design flaw. Once a decision is committed, the NPC should acknowledge rather than re-open.

**Direction**: bundled with PT-010. Decision-lock logic via dialogue_flags; NPC follow-up acknowledges the committed choice instead of re-branching.

**Status**: SHIPPED in PT-I (2026-04-22). Response-level `excluded_flags: ["dead_ledger_accusation_made"]` on the greet node's four investigation responses removes them from the menu once an accusation is filed. A fifth response ("Any word from the prosecutor?") appears only when `dead_ledger_accusation_made` is set, routing to the new `case_closed` recap node. Single generic recap (not per-suspect) because the existing mission objective reads the umbrella `dead_ledger_accusation_made` flag and splitting into three sub-flags would have required mission-schema changes out of scope.

**Sprint**: PT-I.

### [PT-012] P5 · high · OPEN · Ship naming re-prompted on drydock re-entry, Enter key unresponsive

**Reported**: 2026-04-22. Player named their ship at intro (via `name_input_view`). On returning to the drydock after a build, the builder opened its own naming dialog, pre-populated with the existing name. "Press Enter to confirm" didn't work.

**Read**: two issues. (1) The builder's `_confirm_build` always opens the naming dialog when outside tutorial mode — should skip if `player.ship_name` is already set. (2) Enter key — handler binds `K_RETURN` at `ship_builder_view.py:3901`, so the bug is either input focus getting eaten by pygame_gui, a dialog-activation race, or the playtester saw "press Enter" on a different surface. Needs a quick repro pass.

**Direction**: user chose explicit RENAME button on the builder toolbar; naming dialog no longer auto-opens on confirm.

**Status**: SHIPPED in PT-E (2026-04-22). CONFIRM BUILD no longer auto-opens the naming dialog when the ship already has a name — goes straight to finalize. New RENAME button on the builder toolbar opens the naming dialog on demand via a rename-only path that updates the name without re-triggering _finalize_build. Numpad Enter (K_KP_ENTER) added to the naming handler's accept key set — defensive fix for the playtester's "Enter didn't work" report (consistent with a numpad keyboard sending K_KP_ENTER instead of K_RETURN). Rename button hidden in tutorial mode.

**Sprint**: PT-E.

### [PT-013] P2 · medium · OPEN · Missions visible before initiating NPC conversation

**Reported**: 2026-04-22. "Feels a little strange if you accept the delivery mission and then talk to the courier." Missions surface on the Station Board and in the Trade menu before the player has spoken to the NPC who originates them.

**Read**: a flow-friction symptom of the broader onboarding pattern the design doc addresses. Missions should originate from people, with the board as a ledger, not a source.

**Direction**: add initiator-gating via dialogue_flags. Auxiliary menus (Station Board, Trade menu, Mission Log) show only missions whose initiator has been met.

**Status**: SHIPPED in PT-J (2026-04-22). Investigation found the cantina Station Board was already filtering correctly (`discovery_method == "station_board"`) and all current NPC missions use `auto_accept=true` so they never linger in the Available status. The Mission Log's Available tab was the one remaining leak — it showed everything with status AVAILABLE regardless of discovery channel. Added a filter: Available tab now hides `discovery_method in ("npc", "encounter")`. Trading view doesn't surface missions, so no change needed there.

**Sprint**: PT-J.

### [PT-014] P1 · DESIGN QUESTION · DECIDED · Hand-holding calibration

**Reported**: 2026-04-22. "Are you going for a no hand holding kind of feeling with it? Because I was wishing for a little more guidance in parts."

**Read**: direct question to design. Player is flagging that the post-tutorial hand-off to autonomy is abrupt. They didn't play long enough to know if the opacity paid off, and that uncertainty itself is the problem.

**Decision**: we significantly increase guidance in the early game. Character voice and system transparency are the defaults; UI overlays are permitted where narrative can't carry the load or would confuse the player. Player experience is the ceiling. Documented in `requirements/onboarding_design.md` — see principle 1 and "When UI overlays are appropriate." The tutorial system AS IT STANDS is insufficient; we're not rebuilding it, we're extending it forward into the first two hours of post-tutorial play.

**Sprint**: N/A — closed as a decision record. Sprints PT-H through PT-L implement the decision.

### [PT-015] P1 · high · OPEN · No "safe path" signpost NPC

**Reported**: 2026-04-22. "Maybe having an NPC that tells you like 'the safe path' could help, that way on first playthrough someone can kind of have a good idea of where to go and then experiment more on other playthroughs."

**Read**: the player is asking exactly for what the onboarding design doc calls the Dockmaster role. Spot-on feedback; we implement it as proposed.

**Direction**: new NPC, **Arna**, at starting station concourse. Intercepts first galaxy arrival. Teaches: jobs come from people, here's a safe first run, coming back is expected. Fades after Mission 1.

**Status**: SHIPPED in PT-H (2026-04-22). Arna + Rhea NPCs authored (Dockmaster at Nexus Prime, Agri Hub Receiver at Verdant). Four-stage dialogue tree for Arna (first_encounter / pre_completion / post_completion / retired), one dialogue for Rhea. `coolant_run` mission (Nexus Prime → Verdant, 18 machinery, 2000 CR + 50 XP). Odom (delivery_merchant) expanded with teaching branch gated on `first_delivery_complete`. Auto-fire interception in `StationHubView.on_enter()`. Settings toggle for cockpit objective hint (default on). +37 regression tests.

**Sprint**: PT-H.

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

### Sprint PT-D — superseded

Originally planned as "Second conversation" pairing PT-010 + PT-011. Renamed PT-I after the round-2 playtest revealed the broader onboarding gap. Design doc (`requirements/onboarding_design.md`) restructures the arc.

### Sprint PT-E — "Forms that behave" (SHIPPED 2026-04-22)

- [PT-008] Tutorial shop now word-wraps descriptions across two lines instead of truncating; cost pinned to card bottom. Descriptions for all 6 tutorial parts now render in full.
- [PT-012] Explicit RENAME button on builder toolbar. CONFIRM BUILD no longer auto-opens the naming dialog when the ship already has a name. RENAME opens the dialog on demand via a rename-only path that saves the name without re-finalizing the build. Numpad Enter (K_KP_ENTER) now confirms alongside main Enter — likely explanation for the playtester's "Enter didn't work" report.

+9 regression tests (`tests/test_views/test_pt_e_forms.py`). 7,353 → 7,362 passing.

### Sprint PT-F — "Fit the monitor" (SHIPPED 2026-04-22)

- [PT-009] Window is now RESIZABLE in windowed mode. `pygame.SCALED` does the heavy lifting — it auto-scales our logical 720p/900p/1080p render surface to whatever size the player drags the window to, preserves aspect ratio via letterboxing, and translates mouse positions back into logical coordinates automatically. **Zero changes to scale_x/scale_y math** or to the 24 views that bind WINDOW_WIDTH/HEIGHT at module scope. Flags composed by new `build_display_flags(fullscreen: bool)` helper in `game.py`. F11 fullscreen toggle upgraded to explicit `set_mode` rebuild via the helper, so RESIZABLE is reliably restored on return to windowed mode across platforms (`toggle_fullscreen()`'s flag preservation is platform-dependent).

+7 regression tests (`tests/test_engine/test_display_flags.py`). 7,362 → 7,369 passing.

### Sprint PT-H — "Arrival" (SHIPPED 2026-04-22)

- [PT-015] Arna NPC + first-station arrival dialogue + cockpit HUD current-objective toggle + galaxy-map marker (already existed)
- `coolant_run` mission authored (Nexus Prime → Verdant, 18 machinery, 2000 CR)
- Secondary teacher: Odom (existing `delivery_merchant`) expanded with teaching branch, not a new NPC
- Rhea NPC at Verdant as the mission recipient
- Auto-fire interception via `StationHubView.on_enter()`; `tutorial_builder_complete` gate set in `ship_builder_view`
- Settings toggle for objective hint (default on, persisted to settings.json)

+37 regression tests. 7,316 → 7,353 passing. Test file: `tests/test_views/test_pt_h_onboarding.py`.

Load-bearing sprint. Everything downstream (PT-I, PT-J, PT-L) assumes Arna + Mission 1 exist.

### Sprint PT-I — "Second conversation" (SHIPPED 2026-04-22)

- [PT-010] Security desk "come back later" branch — added at `suspects` ("I need more time with this.") and `evidence_synthesis` ("Give me a minute with this.") nodes. Top-level greet already had one; nested nodes didn't, and the playtester was trapped in the suspect-review flow with no visible exit.
- [PT-010] Pre-choice narrative weight — Mossa's opening now explicitly names the "why you" beat: "I need someone outside the dock's gossip. You fly in, you fly out. That's why you." Replaces the subtle "second opinion" line the playtester missed.
- [PT-011] Decision-lock — greet responses now exclude on `dead_ledger_accusation_made`. Once accused, the investigation/accusation options vanish; a new "Any word from the prosecutor?" response routes to a new `case_closed` recap node in Mossa's voice ("Filed. Prosecutor's running it now... Record sticks. Truth wobbles. Work's done."). Decision is final.

+10 regression tests (`tests/test_views/test_pt_i_security_desk.py`). 7,369 → 7,379 passing.

### Sprint PT-J — "Where missions start" (SHIPPED 2026-04-22)

- [PT-013] Mission Log "Available" tab now hides missions with `discovery_method in ("npc", "encounter")`. NPC-initiated missions surface when the player accepts them in dialogue; encounter missions surface when the player triggers the encounter. Campaign missions (empty `discovery_method`) stay visible because they have no other surface. Cantina Station Board filter was already correct (`discovery_method == "station_board"`); test added to lock it in.

Investigation found the existing data is disciplined — all NPC-initiated missions have required_flags gating and auto_accept=true, so they already jump UNAVAILABLE → ACTIVE on dialogue without lingering in AVAILABLE. The Mission Log filter is a defensive future-proofing measure: any future NPC mission with auto_accept=false would leak into Available tab without it.

+9 regression tests (`tests/test_views/test_pt_j_mission_gating.py`). 7,379 → 7,388 passing.

### Sprint PT-K — "System transparency" (SHIPPED 2026-04-22)

Four hooks delivered (the fifth — current-objective line — shipped in PT-H):

- **Skill check readout** — `DialogueManager._resolve_skill_check` now captures a compact "PERSUASION 3 vs 2 PASS" readout alongside the existing pass/fail. Dialogue view renders it in the existing `_check_feedback` overlay, falling back to "Check Passed!/Check Failed." if no social manager is wired. Players see what level was checked against which difficulty.
- **Faction standing delta** — `Player.modify_reputation` appends the effective (clamp-aware) delta to an ephemeral `_pending_faction_deltas` attribute. Game loop drains the queue each frame into the existing `_mission_notifications` pipeline as "Commerce Guild: +5" / "Miners Union: -3". No save/serialization impact (plain attr, not a dataclass field).
- **Cargo mass in cockpit HUD** — cargo line now reads `Cargo: 5/10 (50%)` with tiered coloring: TEXT_SECONDARY under 60%, YELLOW at 60-89%, RED at 90%+. Replaces the all-or-nothing RED-at-capacity behavior.
- **Fuel cost on galaxy map hover** — new `_draw_hover_tooltip` renders a compact name / distance / fuel-cost overlay next to the hovered system. Gated on non-current, non-selected (the full info panel already covers selected). Fuel text colors RED if the player can't afford the jump.

+14 regression tests (`tests/test_views/test_pt_k_transparency.py`). 7,388 → 7,402 passing.

### Sprint PT-M — "Training wheels" (SHIPPED 2026-04-22)

**Component**: `spacegame/views/first_time_tip.py` — standalone `FirstTimeTipOverlay` class with 250ms fade-in, modal event capture (Enter/Space/Escape/click all dismiss), word-wrapped body, left accent stripe, custom-rendered "Got it." button, keyboard-hint label. No pygame_gui dependency. Renders via PT-005's `render_top` hook so it sits above pygame_gui elements.

**Main loop wiring**: before `ui_manager.process_events`, the event loop asks `state_manager.get_current_view()` whether it has a live tip and feeds events there first. Prevents clicks on the "Got it." button from leaking to underlying pygame_gui UIButton elements.

**Six priority views integrated** (each with a `_maybe_show_tip` helper that reads the flag, an overlay instantiation with body copy, a `_mark_*_tip_seen` helper that writes the flag, and a `render_top` override):
- Mission Log (`seen_tip_mission_log`)
- Galaxy Map (`seen_tip_galaxy_map`)
- Trading (`seen_tip_trading`)
- Shipyard (`seen_tip_shipyard`)
- Skill Tree (`seen_tip_skill_tree`)
- Character Sheet (`seen_tip_character`)

Literal flag strings live in each view's code so the dialogue-integrity scanner detects both the read and write. F-string construction was rejected for exactly this reason.

**Scope discipline**: refining, salvage, mining, combat, journal, cantina deferred. Those are deeper-session systems; tips on them are a later sprint once second-session playtest data arrives. The design doc's "contextual hint banners" (category b) were not shipped — the first-time modal covers the primary need; hint banners can land once the first-hour flow has been validated.

**Polish details worth naming**: fade-in animation (no pop-in), keyboard accelerators (Enter/Space/Escape/KP_Enter all dismiss — matches PT-012's Enter-key robustness fix), modal click absorption (clicks anywhere on screen are consumed while the tip is up, preventing accidental underlying button fires), hover state on the dismiss button.

+29 regression tests (`tests/test_views/test_pt_m_training_wheels.py`) — 13 overlay unit tests, 4 voice-compliance tests, 5 integration discipline tests, 5 mission-log runtime tests, 2 main-loop consumption guards. Also updated `test_galaxy_map_view.py::_make_view` to pre-set the galaxy-map tip flag so existing behavior tests run against steady-state view. 7,410 → 7,439 passing.

### Sprint PT-L — "Soft break" (SHIPPED 2026-04-22)

- **Arna dialogue fade** — already shipped in PT-H via `dialogue_states`: post-Mission-1 plays the one-time "you came back" recap and sets `arna_retired`; all subsequent visits route to `arna_retired` dialogue which is a single word, "Spacer." Training wheels came off without a banner.
- **Cockpit objective auto-retire** — new `check_soft_break_retirement()` method on Game, called every frame from the gameplay update loop next to `check_attribute_milestones`. When completed mission count reaches 3: flip `cockpit_hud.show_objective_hint` off (if still on), persist to settings.json, set `dialogue_flags["objective_hint_auto_retired"]` so the check never runs again. Silent — no banner, no announcement. Respects manual toggles: if the player has already disabled the hint OR re-enables it post-retirement, we don't interfere.

+8 regression tests (`tests/test_engine/test_pt_l_soft_break.py`) covering fire conditions, no-re-fire guard, persistence failure resilience, missing-HUD/missing-player guards. 7,402 → 7,410 passing.

### Subsequent sprints — reactive

Themes that will likely emerge from further playtesting:
- Combat flow (balance, telegraph clarity, dual tech discoverability)
- Economy pacing (early-game credit tightness, mid-game progression stalls)
- Dialog & narrative (beat pacing, NPC voice coherence)

---

## Decision log

Decisions we've made during this arc that we don't want to revisit unless playtest data invalidates them.

### D-001 — Fallback AI-generated sprites removed (not deprecated)

**Context**: PT-002 removed the AI-sprite fallback from the shipyard top-right. **Decision**: we are NOT deprecating AI-generated assets site-wide — they're still used for commodity icons, background art, portraits, etc. Only the ship-sprite fallback was removed, because composites are the canonical representation of the player's designed ship and the fallback contradicted that.

**If this decision breaks**: a future view shows stale AI ship art where composites belong. Re-examine that view's ship-loading path.

### D-002 — Juggernaut requires bulk, Sentinel/Ghost do not

**Context**: PT-001 added size gates. **Decision**: only juggernaut has an extra absolute-pixel requirement (`MIN_JUGGERNAUT_PIXELS=100`). Sentinel (shield-heavy) and Ghost (stealth) both have legitimate small-ship interpretations (scout craft, interceptors, shield frigates).

**If this decision breaks**: playtester finds a small ship classified as GHOST that doesn't feel right. Introduce a `MIN_GHOST_PIXELS` (or similar) proportional to observed mismatches.

### D-004 — Onboarding teaches through character first, UI overlays second

**Context**: round-2 playtest (PT-014) surfaced that the tutorial teaches mechanics but not the game. **Decision**: we extend the tutorial arc forward into the first two hours via new teacher NPCs (Arna, plus one secondary), system transparency hooks (PT-K), and explicit UI overlays where narrative can't carry the load (PT-M). Character voice is the default; UI overlays are permitted and voice-checked but not first-resort. Player experience wins over principle purity. Full scope: `requirements/onboarding_design.md`.

**If this decision breaks**: onboarding doubles back to a pure-NPC approach (playtesters find the overlays jarring) OR doubles down on overlays (playtesters find the character voice insufficient). Either adjustment is a design-doc update, not a code rewrite.

### D-005 — Arna is the Dockmaster

**Context**: PT-H names the first post-Mechanic teacher. **Decision**: single-name handle, **Arna**. Terse-observant voice register, retires after Mission 1, fades to neutral greeting thereafter. Bartender alternative rejected as tropey; secondary teacher candidate TBD between Cargo Broker, Archivist, Medic.

**If this decision breaks**: player dislikes Arna's voice or the fade timing reads wrong. Adjust voice sheet or extend/shorten retirement window; no structural rebuild needed.

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
