# QA Pass 1 — Inventory & Audit

Generated 2026-04-21. Snapshot of test coverage, deferred items, and cross-system integration risk to drive Passes 2–5.

> **Pre-playtest final state (2026-04-21, post-wrap-up):** 7,086 tests passing, 2 intentionally skipped (documented B6 placeholder scenarios awaiting authoring). Parallel `pytest -n auto` runs green on first try — the pre-existing rivet-test flake was root-caused to `hash()`-randomized-per-process and fixed at source by switching to `hashlib.md5` for build seeds. Every Pass 2 bug, every Tier 1/2/3 engineering deferral is closed. Remaining items are content authoring (composite_build for marquee bosses, narrative encounters for T4 bosses) which the QA plan explicitly defers until after manual playtesting informs the content choices. See `qa_pass_wrapup_findings.md` for the final checklist.

**Headline (original):** 6,835 tests passing (3 skipped). Total line coverage **59%** (41,173 statements). Coverage is heavily bimodal: data models are 90–100%, large views are 0–50%. Deferred items are well-documented but unprioritized — biggest log lives in `combat_balance_design.md §12`. The biggest integration-risk cells are skill-bonus → combat (dual code paths), mission → dialogue flags (cross-cutter), and module destruction → save persistence (recently added, no round-trip test).

---

## 1. Test Coverage Map

### Tier A — Solid (≥85%, no action needed)

Data models: `enemy_subsystems` (100%), `progression` (99%), `dialogue` (98%), `politics` (97%), `dual_tech` (97%), `crew` (91%), `mining` (91%), `salvage` (96%), `market` (95%), `mission` (79% — borderline), `ground_*` (95–99%), `combat` (80% — borderline), `ship_build` (91%), `player` (90%), `smuggling` (97%), `save_manager` (85%), `data_loader` (86%).

Engine: `enemy_build_generator` (100%), `enemy_composite_provider` (98%), `ship_composite` (93%), `arena_entry` (99%), `combat_vfx` (82% — borderline), `dual_tech_*` cinematic (97–100%), `scene_camera` (94%), `damage_text` (99%), `transitions` (97%), `procedural` (74% — weakest in tier).

### Tier B — Watch list (50–84%)

| Module | Cov | Why it matters |
|---|---|---|
| **`combat_engine.py`** | 70% | Most missed lines are legendary mechanics (Phase Shift, Void Absorption, Chain Fire) and module-targeted combat — exactly the recently added paths. |
| `module_combat.py` | 59% | Module-targeted damage routing. Shipped functionality, thinly tested. |
| `ship_module.py` | 67% | Module data plumbing. |
| `slot_definition.py` | 51% | Slot resolution rules. |
| `audio_manager.py` | 63% | Headless tests don't exercise audio playback. Mostly safe to ignore. |
| `mining_vfx.py` / `salvage_vfx.py` / `refining_vfx.py` / `screen_effects.py` | 62–67% | Animation paths; visual side effects, low correctness risk. |
| `input_handler.py` / `state_manager.py` | 45% / 54% | Plumbing — covered indirectly through view tests. |
| `mission.py` | 79% | Mission progression and reward paths. Some corners missed. |

### Tier C — Thin (<50%, integration scenarios needed)

| Module | Cov | Notes |
|---|---|---|
| **`engine/game.py`** | **19%** | 5,113 statements, 2,212 missed. The state-transition router and `_ensure_*_view` factories live here. Untested by unit tests because it's the integration layer — exactly what Pass 3 scenarios target. |
| **`combat_view.py`** | **38%** | 2,488 stmts; render/animation paths uncovered. Recent C-phase work added a lot of code. |
| **`trading_view.py`** | **19%** | 851 stmts; almost none covered. |
| `galaxy_map_view.py` | 48% | 949 stmts. Travel paths thinly covered. |
| `mining_view.py` / `refining_view.py` / `salvage_view.py` | 57–67% | Mini-game views; exercised by happy-path tests but rare branches missed. |
| `cockpit_hud.py` | 51% | Persistent overlay; many context-map branches uncovered. |
| `journal_view.py` | 51% | New journal entries paths thin. |
| `station_hub_view.py` / `station_layouts.py` | 33% / 32% | Station entry; lots of layout code untouched in tests. |
| `pause_menu_view.py` | 52% | Settings + flow control. |
| `investment_view.py` | 60%, `repair_bay_view.py` 58%, `save_load_view.py` 63%, `settings_view.py` 58% | Functional views, decent baseline. |

### Tier D — Untested (0%, high crash risk)

These views have **zero** test coverage — likely never instantiated in tests. Pass 4 (smoke test runner) is mandatory for these:

- **`ship_builder_view.py`** (2,300 stmts!) — the entire builder. Massive surface area, no automated guard.
- **`shipyard_view.py`** (1,551 stmts, 7%) — recently revamped; only constructor barely touched.
- `crew_roster_view.py` (413 stmts) — recently added Coordinated tab loci touched here.
- `dialogue_view.py` (422 stmts) — entire dialogue UI.
- `mission_log_view.py` (473 stmts).
- `skill_tree_view.py` (437 stmts) — capstone visual treatment in here.
- `character_creation_view.py` (138 stmts), `event_notification_view.py` (83), `tutorial_shop_view.py` (196).
- `combat_tutorial_helper.py`, `keybindings.py`, `image_loader.py`, `main.py` — utility modules.

**Total view code untested**: ~6,300 statements across these 12 files. Almost all crash-class risk lives in this tier — a single AttributeError on `on_enter` will break a screen for the player.

---

## 2. Deferred Items Index

### A. Combat Balance Log (`requirements/combat_balance_design.md §12`)

Eleven well-documented items. Status as of today:

| # | Item | Phase | Recommendation |
|---|---|---|---|
| 1 | "Iron Dominion" → Miners Union mapping | B2 | Pass 5 triage — likely lightweight rename |
| 2 | Ally-targeted heals (`EffectTarget.ALLY`) | B2 | Defer until Support archetype playtest signal |
| 3 | `call_reinforcement` move | B2 | Defer; not blocking |
| 4 | Legendary superboss retuning verification | B2 | Pass 6 manual playtest |
| 5 | Phase Shift "all vs first attack per round" | B7 | Defer; current behaviour is power-skewed but not broken |
| 6 | §6 round-count targets vs current tuning | B6 | Pass 5 — likely revise §6 expectations rather than retune |
| 7 | ActionQueue `slot_key` footgun test | B6 | Pass 2 candidate — easy documentation test |
| 8 | Narrative encounters for new T4 bosses | B3 | Content work; campaign Act Two |
| 9 | Pruning legacy enemies from random pools | B3 | Pass 6 playtest signal |
| 10 | Travel-encounter boss filter defense-in-depth | B3 | Defer; belt-and-suspenders only |
| 11 | Legacy `ShipType` combat path (`combat.py:802+`) | U5 | Pass 5 triage — risk vs benefit of removal |

### B. Combat Overhaul (`30_overhaul_space_combat.md`)

- ⏳ **Module overlay integration in combat_view** (line 455) — primitive shipped + tested; combat_view doesn't construct per-enemy overlays yet. Pairs with the per-instance composite work below.
- ⏳ **Hand-authored composite_build content** for marquee bosses — override mechanism shipped (Impl 3); no boss has authored content. Content work, not engineering.
- ⏳ **C4 destruction driver wiring** (Impl 5 deferral) — bucketed pipeline complete; driver from hull damage waits on per-instance composites.
- ⏳ **Per-instance ShipComposite cache** — currently per-template_id. Blocks the destruction driver and module overlays. Real architectural decision needed.

### C. Code-Level Deferrals (in-source)

- `galaxy_map_view.py:1466` — TODO S4: `price_memory` skill needs `TradeRouteTracker` to display last-known prices on the galaxy map. Skill exists, not wired.
- `material_palette.py:193` — colorblind profiles (PROTANOPIA, etc.) are stubs; content deferred per accessibility post-v1 plan.
- `save_manager.py:194` — schema migration framework deferred until first breaking format change. Currently we rely on `data.get(field, default)` patterns.
- `dual_tech.py:520` (combat_balance §12) — `bridge_crew_ids` kwarg hook exists; not surfaced. Closed as not-applicable today; revisit at fleet management.

### D. Accessibility (`99_CORPUS_COHERENCE_REVIEW.md`)

- §42 UI Chrome documents colorblind / keyboard / motion-reduction hooks. Implementation deferred to post-v1. Not a Pass 5 concern; full audit is a separate pre-release pass.

### E. Open Design Questions (combat_balance §10)

Six questions still open. Pass 5 triage candidates: encounter pool migration policy, element resistance granularity, support archetype heal math (partly resolved), dual tech first-fire UX (pause vs overlay), triad loyalty gate, legendary superboss retuning curve.

---

## 3. Cross-System Integration Matrix

Rows: writer. Columns: reader. Cells flag which paths are most exposed to bugs from cross-system drift.

| Writer ↓ \ Reader → | Combat | Mission | Save | Faction | Crew | Skill/Prog | Market | Galaxy |
|---|---|---|---|---|---|---|---|---|
| **Combat** | — | flags + rewards | hull/credits/cargo | reputation drift | crew XP | combat XP | (none) | (none) |
| **Mission** | forced encounters | — | flag state | rep + perk gates | quest acceptance | mission XP | (none) | location gates |
| **Skill/Prog** | bonuses (BOTH paths!) | check thresholds | progression state | (none) | crew interactions | — | price bonuses | scan/fuel |
| **Faction** | perks + bonuses | mission availability | rep state | — | recruitment gates | (none) | discounts | system access |
| **Crew** | combat moves | crew quest unlocks | roster + loyalty | (none) | — | crew passives | (none) | (none) |
| **Market/Trade** | (none) | trade missions | market state | (none) | (none) | trade XP | — | regional prices |
| **Save/Load** | resets state | restores flags | — | restores rep | restores roster | restores skills | restores markets | restores location |
| **Galaxy/Travel** | encounter rolls | mission progress | location | system access | (none) | exploration XP | regional shifts | — |

### Hotspots (highest integration risk)

1. **Skill/Prog → Combat** — the CLAUDE.md "common pitfalls" already calls this out: `build_player_combat_state()` has TWO code paths (build-derived vs legacy ShipType) and skill bonuses must be applied in BOTH. Pass 3 scenario candidate.
2. **Mission → dialogue_flags** — flat dict means producer/consumer drift is silent. Cross-reference test coverage exists but is shallow. Pass 2 priority.
3. **Save/Load → everything** — to_dict/from_dict chain. Recent additions (subsystem state, destruction state, dual_tech reveals, focused_subsystem) need round-trip verification. Pass 3 scenario priority.
4. **Combat → Module destruction → Save** — Impl 4 added subsystem_hp/destroyed/focused_subsystem to runtime EnemyShip. Are these persisted? **Likely NOT** — these are runtime fields on `EnemyShip`, which only exists during combat. Combat doesn't save mid-fight. ✅ Probably fine, but worth one assertion.
5. **Faction → Mission availability** — perks + reputation gate missions and dialogue. Quest validation tooling exists; perk validation is thinner.
6. **Crew → Combat / Crew Quests** — recent dual_tech work threads crew loyalty into combat. Crew quest completion paths are individually tested but not as scenarios.

---

## 4. Recommendations for Subsequent Passes

### Pass 2 (Content Validation Sweep) — high priority

Extend `tests/test_data/test_cross_references.py` (or split into a new `test_data_graph.py`):

1. **Dialogue flag bidirectional audit** — every flag set somewhere must be read somewhere; every flag read must have at least one producer (with documented exceptions for save-load preserved flags).
2. **Skill `bonus_type` audit** — every bonus_type in `create_default_skills()` must have at least one consumer doing `progression.get_bonus("name")`.
3. **Faction perk audit** — every perk references a real bonus type (re-uses #2 if perks bridge into the bonus system).
4. **Module/Blueprint cross-references** — every module ID in templates / shop catalogs / blueprints exists in `data/builder/parts.json`. Spot-check from station catalogs.
5. **Subsystem tags** — every `targetable_subsystems` entry on enemies is in the canonical 6-tag palette. Trivial test, fast guard against typos.

Estimated cost: 1 session. Expected yield: 5–15 small bugs of the "renamed but not everywhere" class.

### Pass 3 (Integration Scenarios) — biggest payoff

Build `tests/test_scenarios/` with functional helpers (`fresh_player`, `attach_build`, `round_trip_save`, `real_enemy`). Tests invoke real models directly — no god-object `Scenario` class.

Scenarios authored (12 candidates, triaged during execution):

**Pass 3 — shipped (6, 58 tests):**
1. ✅ **Save/load round-trip with complex mid-state** — including ShipBuild + dual_tech reveals
2. ✅ **Combat: subsystem focus → destroy → effect applies** — Impl 4 end-to-end
3. ✅ **Skill bonus applies in BOTH combat paths** — CLAUDE.md warning made flesh
4. ✅ **Mission accept → progress → complete → reward**
5. ✅ **Dual tech reveal one-shot contract + save persistence** — Impl 2 end-to-end
6. ✅ **Faction rep shift gates perks + bonus query pipeline**

**Pass 3.5 — scoped (3, model-layer scenarios that fit the existing harness):**
7. ⏳ **Trading arbitrage round-trip** — buy low, travel, sell high, market state shifts, skill bonuses apply
8. ⏳ **Crew quest lifecycle** — loyalty-gated trigger, accept, complete, crew-specific rewards
9. ⏳ **Galaxy event chain progression** — trigger → consequence → chain follow-up

**Re-routed to Pass 4** (view-layer, wrong shape for model scenarios):
10. → **Tutorial completion happy path** — requires view state transitions + tutorial overlay orchestration
11. → **Mining session with skill bonuses** — mini-game view; model yield math already covered, what's uncovered is `MiningView` render + interaction
12. → **Death/respawn flow** — crosses multiple `GameState` transitions; needs view lifecycle harness

Estimated remaining cost: ~1 session for Pass 3.5 (scenarios 7–9, ~25 tests). Pass 4 will absorb 10–12 as scenarios within its smoke runner.

### Pass 4 (Smoke Test Runner + View-Layer Scenarios) — needed for Tier D

Two-part scope:

**Part A: view lifecycle smoke runner.** Single parametrized test that walks every `GameState` transition: instantiate view → `on_enter()` → one `render()` → `on_exit()` → assert no leaked pygame_gui elements. Catches AttributeError-class bugs in the 12 untested views.

**Part B: view-layer scenarios absorbed from Pass 3's original scope** (scenarios 10–12 re-routed here because they're view-shaped, not model-shaped):
- **Tutorial completion happy path** — exercise tutorial overlay + view state transitions end-to-end
- **Mining session** — `MiningView` render + interaction loop
- **Death/respawn flow** — combat loss → respawn view transitions, no state corruption

Estimated cost: 1–2 sessions. Expected yield: 3–8 crash-class bugs in views that haven't been exercised since the recent overhaul, plus view-integration coverage for the three absorbed scenarios.

### Pass 5 (Deferred Items Triage) — decision-making

Walk this audit's Section 2 with the user. Each item: **DO NOW** / **DEFER WITH REASON** / **KILL**. Convert DO-NOW → tasks. Most §12 items will defer; most ⏳ overhaul items will defer pending per-instance composite decision.

Estimated cost: 1 session (heavy on conversation, light on code).

### Pass 6 (Manual Playtest + Polish) — your job

Run through the recently-touched paths (combat with focus targeting, dual techs in live fights, shipyard rebuild flow, builder physics warnings) with a polish backlog open beside you. Pass 1–5 should have de-risked the codebase enough that this session is about feel, not bugs.

---

## 5. What's NOT in this audit

- **Performance profiling** — no benchmarks beyond the C4 destruction rebuild check. If frame-rate regressions appear in playtest, separate pass.
- **Visual/UX review** — Pass 6 territory.
- **Narrative QA** — the writing guide and faction voice sheets exist; a narrative pass is its own discipline.
- **Mypy / type debt** — 96 pre-existing mypy errors in `combat_engine.py` etc. Tracked but not blocking.
- **Long-session memory leak testing** — would need a dedicated harness; do if playtest surfaces it.
