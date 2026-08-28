# Act II Ambition - sprint sections A2-5 through A2-21

Source: `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` (Spec F) and
`docs/superpowers/specs/2026-08-27-act-two-decomposition.md`. A2-1 through A2-4 are authored
in a separate file and merged into `requirements/roadmap/ROADMAP.md` alongside this one.

## Conventions this file assumes from A2-1 through A2-4

These are not this file's deliverables. They are read-only inputs every sprint below depends
on. Stated once here so no individual sprint has to re-derive them.

- **Lens registry (A2-1)**: `spacegame/models/lens.py` (`Lens` dataclass), data at
  `data/narrative/lenses.json` (top-level key `"lenses"`), `DataLoader._parse_lenses()` →
  `DataLoader.lenses: dict[str, Lens]`. Sixteen lens ids, snake_case: `vengeance`, `wealth`,
  `political_power`, `exploration`, `discovery`, `justice`, `crime`, `revolution`, `empire`,
  `community`, `legacy`, `faith`, `transcendence`, `connection`, `truth`, `preservation`.
- **Investment tracking (A2-4)**: assumed to land as `spacegame/models/lens_investment.py`
  defining `LensInvestment` (a `dict[str, int]` of lens id to investment, 0-100 integer scale,
  raised via an `add_investment(lens_id, amount, source)`-shaped method) attached to
  `Player` as `player.lens_investment: LensInvestment = field(default_factory=LensInvestment)`,
  round-tripped through `Player.to_dict()` / `Player.from_dict()`. If A2-4 lands with a
  different type or scale, every numeric threshold below scales proportionally; the mechanism
  (telegraph strictly below collision) does not change.
- **Capstone format (A2-3)**: assumed to land as `spacegame/models/capstone.py` (`Capstone`
  dataclass: `id`, `lens_id`, `capstone_threshold`, `narration_key`) plus a hook-registration
  contract, data at `data/narrative/capstones.json`. No capstone prose is authored anywhere in
  this file - "Authored galaxy content" is explicitly out of scope for the whole arc.

## Design decisions this file treats as fixed (see task brief for full rationale)

Investment is fully oblique (no meter; NPC address and offered work are the only readout).
A dilemma cannot be declined. Closure is a trade (`tier_unlocks` mandatory on every outcome).
Closure leaves a scar (the refusing NPC still exists). The telegraph is an enforced invariant:
`telegraph_threshold < collision_threshold` on every dilemma, checked by a build-failing test.

## One structural decision made in this file, not in the source docs

Dilemma data lives one file per dilemma under `data/narrative/dilemmas/<dilemma_id>.json`
(each containing `{"dilemmas": [...]}` with one entry), not a single shared
`data/narrative/dilemmas.json`. The eight dilemma sprints (A2-12 through A2-19) are siblings
by design, eligible to run concurrently; a single shared data file would force the dispatcher
to serialize all eight on touch-zone conflict for no reason. `DataLoader._parse_dilemmas()`
globs the directory. This does not change any dependency edge given in the decomposition.

---

#### A2-5 — Lens definitions 1-8

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 5-7 days
**Depends on**: A2-1 | **Blocks**: none

**Goal.** Author the first eight lens records as data: Vengeance, Wealth, Political Power,
Exploration, Discovery, Justice, Crime, Revolution. This is the first half of what makes
"sixteen ambitions" real instead of a table in a design doc - every field the `Lens` schema
requires, populated with setting-specific content, for eight of the sixteen.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - lens table (the "sixteen
  lenses" section) for core_fantasy/question/minigame_shape per lens; "Notes on lenses that
  are easy to collapse and must not be" for Exploration-vs-Discovery and Political-Power-vs-
  Revolution-vs-Empire differentiation.
- `spacegame/models/lens.py` - the `Lens` dataclass and its field contract (from A2-1).
- `docs/superpowers/specs/a2_sprint_sections.md` (this file) - "Conventions" section above,
  for lens ids and the investment scale.
- `requirements/act_one_reference.md` - "The Ledger" section (lines 21-25) and the M05/M07
  journal-entry examples, for Vengeance and Crime grounding that stays consistent with what
  Act I already established.
- `spacegame/models/ambient_dialogue.py` - `AmbientLine.action_type` docstring (examples:
  `"sold_cargo"`, `"combat_victory"`) for the vocabulary `investment_from` tags must match.
- `spacegame/models/procedural_missions.py` - module docstring, for the five existing
  procedural mission types (`bounty`, `delivery`, `smuggling`, `survey`, `salvage`) that
  `investment_from` tags may reference.

**Touch zones.**
- `data/narrative/lenses.json` (shared with A2-6 - both sprints append entries; do not
  overwrite the other's entries. If both run concurrently the dispatcher serializes them per
  `requirements/roadmap/CONVENTIONS.md`; this is expected, not a conflict to work around.)
- `tests/test_compliance/test_lens_content_uniqueness.py` (NEW)

**Deliverables.**
- Eight `Lens` records added to `data/narrative/lenses.json`, ids `vengeance`, `wealth`,
  `political_power`, `exploration`, `discovery`, `justice`, `crime`, `revolution`. Every
  field from the `Lens` schema populated for each: `id`, `name`, `core_fantasy`, `question`,
  `sees`, `wants`, `trades`, `investment_from`, `minigame_shape`, `voice`, `tier_unlocks`.
- `core_fantasy`, `question`, and `minigame_shape` copied verbatim in meaning from the design
  spec's lens table (rows 1-8) - do not paraphrase the mini-game shape, it is load-bearing.
- `investment_from` per lens is a list of concrete action-tag strings, each traceable to a
  real, already-implemented game system (not the eventual bespoke mini-game, which is out of
  scope for this arc). Minimum starting set:
  - `vengeance`: `["combat_victory_named_target", "mission_completed:bounty"]`
  - `wealth`: `["sold_cargo", "trade_profit_large", "auction_won", "investment_tier_purchased"]`
  - `political_power`: `["politics_favor_granted", "politics_vote_won", "council_seat_won"]`
  - `exploration`: `["reach_system_first_visit", "deep_scan_completed"]`
  - `discovery`: `["encounter_anomaly_resolved", "journal_entry:discovery"]`
  - `justice`: `["mission_completed:bounty_lawful", "politics_dispute_resolved_lawful"]`
  - `crime`: `["mission_completed:smuggling", "black_market_sale"]`
  - `revolution`: `["politics_dispute_resolved_uprising", "faction_reputation_up:frontier_alliance_labor"]`
- `sees` states what this lens notices in existing shared content (a wreck, a rumour, a
  person) in one sentence per lens, distinct from every other lens's reading of the same
  kind of content - this is what A2-7 will attach to actual `Location` records.
- `voice` follows `requirements/dialogue_writing_guide.md` register conventions and A2-2's
  lens authoring guide (read it if present; if A2-2 has not landed yet, follow the writing
  guide directly and do not block on it).
- `tier_unlocks` on the Lens record itself is a one-line category of what this lens's arc
  deepens into post-resolution (e.g. wealth: `["access to black-market financiers who do not
  ask where the capital originated"]`) - this is distinct from and does not substitute for
  the per-outcome `tier_unlocks` a dilemma sprint (A2-12 through A2-19) attaches to a specific
  collision resolution.
- `tests/test_compliance/test_lens_content_uniqueness.py`: asserts every lens in the full
  registry (once all sixteen exist) has a `minigame_shape` string not shared by any other
  lens, case-insensitive, exact match. Run it now against whatever subset of lenses already
  exists in `data/narrative/lenses.json` - it must not silently pass on an empty or
  partial registry (assert at least 1 lens loaded, same guard shape as
  `tests/test_compliance/test_findings_register.py`'s "guard against scanning nothing").

**Acceptance criteria.**
1. `get_data_loader().lenses` contains all eight ids after `load_all()`, each an instance of
   `Lens` with every schema field non-empty.
2. A2-1's lens data-integrity test (whatever file it landed in) passes against the expanded
   `lenses.json` with no code changes to that test.
3. `tests/test_compliance/test_lens_content_uniqueness.py` passes: no two lenses in the
   registry (across whatever subset exists) share a `minigame_shape` string.
4. Exploration and Discovery `sees`/`wants`/`question` fields are textually distinct enough
   that a unit test asserting `lenses["exploration"].question != lenses["discovery"].question`
   and the same for `sees` passes trivially (they must not be near-duplicates).
5. Every `investment_from` tag for these eight lenses is a string matching the pattern
   `^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)?$` (snake_case, optional single colon-qualifier),
   verified by a new test in `tests/test_compliance/test_lens_content_uniqueness.py`.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-6 — Lens definitions 9-16

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 5-7 days
**Depends on**: A2-1 | **Blocks**: none

**Goal.** Author the second eight lens records: Empire, Community, Legacy, Faith,
Transcendence, Connection, Truth, Preservation. Completes the sixteen-lens registry that
every downstream Act II sprint reads from.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - lens table rows 9-16;
  "Wealth vs Community" and "Vengeance vs Justice" notes (Community and Truth both appear
  in that "must not collapse" discussion even though their pair-partners are in A2-5).
- `spacegame/models/lens.py` - the `Lens` dataclass field contract.
- `docs/superpowers/specs/a2_sprint_sections.md` (this file) - "Conventions" section above.
- `requirements/act_one_reference.md` - M05 journal entry (Marcus Jin's buried safety
  report) for Community/Legacy grounding; the father's death from failing air recyclers is
  the emotional origin of both Wealth (A2-5) and Community.
- `spacegame/models/ambient_dialogue.py` and `spacegame/models/procedural_missions.py`, same
  reason as A2-5.
- `requirements/character_voices.md` - Dr. Nadia Kweon (Okafor Institute Director) and
  Sten Brygaard (Deep Shafts Caretaker) voice sheets; both are reused as dilemma-content NPCs
  in later sprints (A2-16, A2-17) and their established voice should inform Legacy's and
  Preservation's `voice` field so later sprints do not contradict this one.

**Touch zones.**
- `data/narrative/lenses.json` (shared with A2-5 - see A2-5's touch-zone note; append only)
- `tests/test_compliance/test_lens_content_uniqueness.py` (extend if A2-5 has already created
  it; create it if this sprint runs first - check before writing to avoid clobbering)

**Deliverables.**
- Eight `Lens` records added to `data/narrative/lenses.json`, ids `empire`, `community`,
  `legacy`, `faith`, `transcendence`, `connection`, `truth`, `preservation`. All schema
  fields populated, same rigor as A2-5.
- `investment_from` starting set:
  - `empire`: `["territory_investment_purchased", "politics_dispute_resolved_annex"]`
  - `community`: `["investment_tier_purchased:community", "wreckers_guild_contract_completed", "crew_loyalty_gained"]`
  - `legacy`: `["okafor_research_project_funded", "institution_founded"]`
  - `faith`: `["deep_shafts_pilgrimage_visited", "dialogue_completed:faith"]`
  - `transcendence`: `["okafor_research_project_funded:high_risk", "ship_upgrade_installed:experimental"]`
  - `connection`: `["crew_loyalty_gained", "dialogue_completed:crew_personal"]`
  - `truth`: `["investigation_flag_set", "dialogue_completed:evidence"]`
  - `preservation`: `["deep_shafts_pilgrimage_visited", "wreckers_guild_contract_completed:preservation"]`
- `sees`/`wants`/`trades` for `community` and `wealth` (A2-5) must read as "the same wound,
  opposite conclusion" per the design spec - this sprint's `community.sees` and A2-5's
  `wealth.sees` should both reference the derelict-hauler-style shared content but resolve
  it differently (community sees survivors who need somewhere to go; wealth sees salvage
  tonnage and a supply gap).
- `truth` and `vengeance` (A2-5) similarly must read as compatible-until-they-are-not: truth's
  `wants` is understanding, not punishment, and its `voice` should not read as covertly
  vengeful.
- `tier_unlocks` (lens-level, one-liner) for each of the eight.

**Acceptance criteria.**
1. `get_data_loader().lenses` contains all sixteen ids (eight from A2-5, eight from this
   sprint) after `load_all()`, each with every schema field non-empty. If A2-5 has not
   landed yet when this sprint runs, this criterion is checked only against this sprint's
   own eight and re-verified once A2-5 lands (do not block on A2-5's completion; both depend
   only on A2-1 and are siblings).
2. `tests/test_compliance/test_lens_content_uniqueness.py` passes against the full registry
   once both A2-5 and A2-6 are present: sixteen distinct `minigame_shape` strings.
3. A new unit test in `tests/test_models/test_lens.py` (create if it does not exist) asserts
   `lenses["community"].sees != lenses["wealth"].sees` (once A2-5 exists) and that both
   reference distinguishable resolutions of the same premise, checked via two required
   substrings unique to each (e.g. community's contains "survivors" or "cryo", wealth's
   contains "salvage" or "tonnage").
4. Every `investment_from` tag matches the snake_case-with-optional-qualifier pattern from
   A2-5's acceptance criterion 5.
5. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-7 — Per-lens readings on locations

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 4-6 days
**Depends on**: A2-1 | **Blocks**: none

**Goal.** Give the `Location` model a `lens_readings` field so a single authored place can be
read sixteen ways, and prove it on real data. This is Success Criterion 2 from the design
spec: a new location can be given per-lens readings without touching lens or dilemma code -
which means this sprint does the one-time code change so every later location author only
ever touches JSON.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The core architecture: a
  lens is a reading, not a track" section (the derelict-hauler table, lines 52-70) is the
  exact shape `lens_readings` must support.
- `spacegame/models/location.py` - current `Location` dataclass, `to_dict()`/`from_dict()`.
- `data/galaxy/locations.json` - existing location content to extend.
- `spacegame/models/lens.py` - for the set of valid lens ids to cross-reference against.
- `tests/test_data/test_cross_references.py` - the existing cross-reference validation
  pattern (commodity/mission ID checks) this sprint extends with a lens-id check.

**Touch zones.**
- `spacegame/models/location.py`
- `data/galaxy/locations.json`
- `tests/test_data/test_cross_references.py`
- `tests/test_models/test_location.py` (extend; create if it does not exist)

**Deliverables.**
- `Location.lens_readings: dict[str, str] = field(default_factory=dict)` - maps lens id to a
  one-to-two-sentence reading of this specific location through that lens. Not every
  location needs all sixteen; an empty dict is valid (most locations are read plainly, only
  narratively significant ones carry lens readings).
- `to_dict()` / `from_dict()` updated to round-trip `lens_readings` (per CLAUDE.md's Save
  Migration rules: `from_dict()` must default missing `lens_readings` to `{}` for old data).
- At least three existing entries in `data/galaxy/locations.json` given real `lens_readings`
  content across at least four lenses each, as a working example for future location
  authors. Pick locations with real narrative weight (e.g. a `unique` or `salvaging`
  `location_type` entry, not a generic market) so the readings are not filler.
- A helper on `DataLoader` or `Location` - `Location.reading_for(lens_id: str) -> str` -
  returning the lens-specific reading if present, else `""`, so callers do not need to probe
  the dict directly.

**Acceptance criteria.**
1. `Location.to_dict()` → `Location.from_dict()` round-trips `lens_readings` exactly,
   verified by a new test in `tests/test_models/test_location.py`.
2. `Location.from_dict()` on a dict with no `lens_readings` key returns a `Location` with
   `lens_readings == {}` rather than raising - verified by a test loading a pre-A2-7-shaped
   location dict (simulating an old save/data file).
3. `tests/test_data/test_cross_references.py` gains a new check: every key in every
   location's `lens_readings` is a real id in `DataLoader.lenses` after `load_all()`. A
   deliberately malformed lens id in a location's `lens_readings` fails this test - verified
   by a test that injects one and confirms the failure (then removes the injection; the
   production data file must end the sprint with zero invalid keys).
4. The three-plus example locations each have `lens_readings` covering at least four lens
   ids, and no two lenses' readings for the same location are near-duplicate text (a basic
   test asserts no two reading strings for the same location share more than half their
   words).
5. Adding a new location to `data/galaxy/locations.json` with a `lens_readings` block for a
   lens not yet exercised by the three examples requires zero changes to `location.py`,
   `lens.py`, or any dilemma code - verified by a test that constructs a location dict with a
   fifth lens's reading purely in test data and loads it successfully.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-8 — Dilemma model + threshold collision

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 2 weeks
**Depends on**: A2-4 | **Blocks**: A2-9, A2-10

**Goal.** Build the dilemma engine: the data model, the collision-detection logic that fires
only when the required poles cross threshold simultaneously, the guaranteed-delivery
telegraph mechanism, and the modal view the player resolves a collision through. This is the
mechanical core every one of the eight dilemma-content sprints and the two integrity/closure
sprints build on. No real dilemma content is authored here - this sprint proves the engine
with one synthetic test fixture, the same way A2-1 proves the lens registry before A2-5/A2-6
add real lenses.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "Anatomy of a dilemma"
  (telegraph/collision/visible cost/tier unlock) and "Permanent closure" sections.
- `docs/superpowers/specs/2026-08-27-act-two-decomposition.md` - "Consequence of Q1 + Q2
  together" section: the telegraph is the single point of failure for the whole mechanic,
  must fire before collision, must be unmissable, must persist (repeat, not one-shot).
- `spacegame/models/ambient_dialogue.py` - `AmbientLine`, `AmbientDialogueManager`; the
  telegraph reuses this fire-and-forget delivery shape rather than requiring the player to
  seek out a conversation.
- `spacegame/engine/game.py` lines ~4388-4412 (`_trigger_crew_reaction`) - the existing
  `action_type`-keyed hook point investment-raising and telegraph-checking both attach to.
- `spacegame/views/tutorial_narration_modal.py` and `spacegame/views/event_notification_view.py`
  - the existing push-state overlay pattern this sprint's dilemma-resolution modal follows.
- `spacegame/engine/state_manager.py` - `push_state()` / `pop_state()`.
- `spacegame/config.py` - `GameState` enum, for where to add the new state.
- `spacegame/constants/flags.py` and `requirements/si3_flag_registry_cookbook.md` - the flag
  is written by the dilemma engine and read by dialogue/station-chatter, a cross-module flag
  by the cookbook's own rule, so it belongs here, not inline.
- `spacegame/data_loader.py` - an existing `_parse_*` method (e.g. `_parse_mission`) as the
  template for `_parse_dilemmas()`.

**Touch zones.**
- `spacegame/models/dilemma.py` (NEW)
- `data/narrative/dilemmas/` (NEW directory; this sprint adds no real dilemma files, only a
  `.gitkeep` or equivalent plus test fixtures under `tests/`)
- `spacegame/data_loader.py` (`_parse_dilemmas()`, `DataLoader.dilemmas: dict[str, Dilemma]`)
- `spacegame/models/player.py` (new fields, see Deliverables)
- `spacegame/constants/flags.py` (`dilemma_telegraphed(dilemma_id)`,
  `dilemma_resolved(dilemma_id)`, `lens_closed(lens_id)` helpers)
- `spacegame/engine/game.py` (telegraph check + collision check wired alongside
  `_trigger_crew_reaction` call sites; new state transition handling)
- `spacegame/config.py` (`GameState.DILEMMA_RESOLUTION`)
- `spacegame/views/dilemma_resolution_view.py` (NEW)
- `tests/test_models/test_dilemma.py` (NEW)
- `tests/test_scenarios/test_scenario_dilemma_thresholds.py` (NEW)

**Deliverables.**
- `spacegame/models/dilemma.py`:
  - `DilemmaOutcome` dataclass: `winning_lens_id: str`, `closes: list[str]` (lens ids
    permanently closed by this outcome), `tier_unlocks: list[str]` (non-empty; not
    enforced yet - A2-9 adds the build-failing guard), `outcome_flag: str`,
    `narration_summary: str`. `to_dict()`/`from_dict()`.
  - `Dilemma` dataclass: `id: str`, `poles: list[str]` (2 or 3 lens ids - the model must not
    assume exactly 2, D3/A2-15 needs 3), `collision_requires: int` (how many of `poles` must
    individually cross `collision_threshold` simultaneously; 2 for a pair, 2 for the D3
    triangle), `telegraph_threshold: int`, `collision_threshold: int`, `telegraph_npc_id:
    str`, `telegraph_lines: list[str]`, `outcomes: list[DilemmaOutcome]` (one per pole).
    `to_dict()`/`from_dict()`.
  - `check_collision(dilemma: Dilemma, investment: LensInvestment) -> bool` - pure function,
    true iff at least `collision_requires` of `dilemma.poles` individually have investment
    `>= dilemma.collision_threshold`.
  - `check_telegraph(dilemma: Dilemma, investment: LensInvestment) -> bool` - true iff at
    least `collision_requires` of `dilemma.poles` individually have investment `>=
    dilemma.telegraph_threshold`.
- `DataLoader._parse_dilemmas()` globs `data/narrative/dilemmas/*.json`, each file shaped
  `{"dilemmas": [...]}` with exactly one entry; populates `DataLoader.dilemmas`.
- `Player.dilemma_state: DilemmaRuntimeState` (new small dataclass in `dilemma.py`, or plain
  fields directly on `Player` - implementer's call, but must include at minimum:
  `telegraphed: set[str]` (dilemma ids where the telegraph has fired at least once),
  `resolved: dict[str, str]` (dilemma id to winning lens id), `closed_lenses: set[str]`.
  Default-constructed, round-trips via `to_dict()`/`from_dict()` with missing-key defaults
  per CLAUDE.md Save Migration rules.
- Telegraph delivery: on every `action_type` event that also feeds `_trigger_crew_reaction`,
  `Game` also checks each loaded dilemma's `check_telegraph()`. On first crossing, force-
  deliver the telegraph line immediately via `self._mission_notifications.append(...)` (not
  a random ambient-dialogue roll) and set `dialogue_flags[flags.dilemma_telegraphed(id)]`.
  On every subsequent qualifying action while the dilemma remains uncollided, re-deliver
  (persist, per the decomposition's Q1+Q2 consequence) rather than staying silent.
- Collision: when `check_collision()` first becomes true for a dilemma not yet in
  `player.dilemma_state.resolved`, `Game` pushes `GameState.DILEMMA_RESOLUTION` via
  `push_state()`. `DilemmaResolutionView` presents the dilemma's poles as buttons (one per
  pole currently at/above `collision_threshold`, plus any pole below threshold if
  `len(poles) > collision_requires`, i.e. D3's third option) with no dismiss/cancel control.
  Selecting one calls a resolution function (this sprint provides the plumbing; A2-10 owns
  what "resolve" actually writes to the save).
- `flags.py` additions: `dilemma_telegraphed(dilemma_id: str) -> str`,
  `dilemma_resolved(dilemma_id: str) -> str`, `lens_closed(lens_id: str) -> str`, each with
  the paired extractor per the SI-3 cookbook's parameterized-helper shape.

**Acceptance criteria.**
1. `check_collision()` returns `False` when only one pole of a two-pole dilemma is at or
   above `collision_threshold` and the other is at 0 - verified by
   `tests/test_models/test_dilemma.py`.
2. `check_collision()` returns `True` when both poles are at or above `collision_threshold`,
   and this is independent of which pole is numerically higher.
3. `check_telegraph()` fires at `telegraph_threshold`, strictly before `check_collision()`
   would fire, verified with a synthetic `Dilemma` fixture where `telegraph_threshold=55`,
   `collision_threshold=80`: investment at 60/60 telegraphs but does not collide; investment
   at 85/85 collides.
4. `tests/test_scenarios/test_scenario_dilemma_thresholds.py`: drives one pole's investment
   to 90 and leaves the other at 0, confirms no collision fires and `GameState` never
   transitions to `DILEMMA_RESOLUTION`. Then drives both to 90, confirms the state
   transitions and the notification queue contains no further telegraph re-delivery once
   `DILEMMA_RESOLUTION` is active. This satisfies design-spec Success Criterion 4.
5. The telegraph line is delivered on the first qualifying action after crossing
   `telegraph_threshold` without requiring the player to initiate dialogue with
   `telegraph_npc_id` - verified by a scenario test that never calls any dialogue-open method
   and still observes the telegraph in `_mission_notifications`.
6. A three-pole synthetic fixture (`collision_requires=2`) collides when exactly two of
   three poles cross threshold and the third remains at 0, proving the model is not
   hard-coded to pairs.
7. Save/load round-trips `player.dilemma_state` with an in-progress telegraphed-but-not-
   resolved dilemma, verified in `tests/test_scenarios/test_scenario_save_load.py` (extend
   the existing scenario rather than duplicating it).
8. Full suite green; no regression from baseline. 20+ new tests across the two new test
   files.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-9 — `tier_unlocks` and telegraph-threshold integrity guard

**Status**: todo
**Phase**: Act II | **Size**: S | **Effort**: 2-3 days
**Depends on**: A2-8 | **Blocks**: A2-12, A2-13, A2-14, A2-15, A2-16, A2-17, A2-18, A2-19

**Goal.** Make two invariants build-failing instead of hoped-for: every `DilemmaOutcome` must
carry a non-empty `tier_unlocks`, and every `Dilemma` must have `telegraph_threshold` strictly
less than `collision_threshold`. This is Success Criterion 5 from the design spec, plus the
telegraph invariant the decomposition promotes to "the single point of failure for the entire
mechanic." Without this test, a dilemma sprint shipping a hollow outcome or an ambush
threshold pair fails silently instead of loudly.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-decomposition.md` - "Consequence of Q1 + Q2
  together" section, point 1: "A2-9's integrity guard is extended to fail the build on any
  dilemma where `telegraph_threshold >= collision_threshold` - same pattern as
  `tier_unlocks`."
- `tests/test_compliance/test_findings_register.py` - the exact pattern to follow: guard
  against scanning nothing, then assert the invariant, with an error message that names every
  offending id, not just a boolean failure.
- `spacegame/models/dilemma.py` (from A2-8) - `Dilemma`, `DilemmaOutcome` field shapes.
- `spacegame/data_loader.py` - `DataLoader.dilemmas`.

**Touch zones.**
- `tests/test_compliance/test_dilemma_integrity.py` (NEW)

**Deliverables.**
- `tests/test_compliance/test_dilemma_integrity.py` with, at minimum:
  - `test_register_exists_and_has_rows`-equivalent: loads `DataLoader.dilemmas` and asserts
    at least one dilemma is present once any dilemma-content sprint has landed; does not
    fail (skips with a clear message) if zero dilemmas exist yet, since this sprint is
    expected to land before any of A2-12 through A2-19 do.
  - `test_every_outcome_has_tier_unlocks`: every `DilemmaOutcome` in every loaded `Dilemma`
    has a non-empty `tier_unlocks` list. Failure message lists `dilemma_id` and
    `winning_lens_id` for every offending outcome.
  - `test_telegraph_strictly_below_collision`: every loaded `Dilemma` has
    `telegraph_threshold < collision_threshold`. Failure message lists `dilemma_id` and both
    threshold values for every offender.
  - `test_every_outcome_closes_something`: every `DilemmaOutcome.closes` is non-empty
    (permanent closure with nothing closed is a data-authoring mistake, not a valid design
    per "closure is a trade, not a subtraction" - there is always a losing pole).
  - `test_poles_and_outcomes_agree`: every `Dilemma.poles` entry has exactly one matching
    `DilemmaOutcome.winning_lens_id`, and vice versa (catches a dilemma authored with a
    typo'd pole/outcome mismatch).

**Acceptance criteria.**
1. A synthetic `Dilemma` fixture with an outcome carrying `tier_unlocks=[]` fails
   `test_every_outcome_has_tier_unlocks` with a message naming the specific dilemma and pole
   - verified by a test that injects the fixture via a temp data file or monkeypatched
   loader, confirms the failure, then confirms removing the empty list makes it pass.
2. A synthetic `Dilemma` fixture with `telegraph_threshold=80, collision_threshold=80` (equal,
   not strictly less) fails `test_telegraph_strictly_below_collision` - verified the same way.
3. A synthetic `Dilemma` fixture with `telegraph_threshold=90, collision_threshold=80`
   (telegraph above collision) also fails the same test.
4. Running these tests against zero real dilemma content (the state immediately after this
   sprint lands, before A2-12 runs) does not fail the suite - it either skips with a named
   reason or passes vacuously, verified explicitly rather than left to chance.
5. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-10 — Permanent closure + save/load

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-8 | **Blocks**: A2-11, A2-12, A2-13, A2-14, A2-15, A2-16, A2-17, A2-18, A2-19, A2-20

**Goal.** Wire what happens when the player picks a pole in `DilemmaResolutionView` from
A2-8: apply the winning outcome's `tier_unlocks`, permanently close the losing lens(es), write
it all to `dialogue_flags` so it survives save/load, and make sure a later save cannot reopen
a closed path. This is Success Criterion 6.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "Permanent closure"
  section: resolution is permanent and universe-wide, explicitly tied to the existing
  "Deterministic outcomes... No save scumming" principle from CLAUDE.md.
- `spacegame/models/dilemma.py`, `spacegame/views/dilemma_resolution_view.py` (from A2-8).
- `spacegame/models/player.py` - `dialogue_flags`, `dilemma_state` (from A2-8),
  `to_dict()`/`from_dict()`.
- `spacegame/save_manager.py` - save/load flow, for the round-trip test.
- `tests/test_scenarios/test_scenario_save_load.py` - existing save/load scenario pattern.

**Touch zones.**
- `spacegame/models/dilemma.py` (`resolve()` function)
- `spacegame/models/player.py` (apply resolution to `dilemma_state`, `dialogue_flags`,
  `lens_investment`)
- `spacegame/views/dilemma_resolution_view.py` (call `resolve()` on button press, pop state)
- `tests/test_models/test_dilemma.py` (extend)
- `tests/test_scenarios/test_scenario_dilemma_permanent_closure.py` (NEW)

**Deliverables.**
- `resolve(dilemma: Dilemma, chosen_lens_id: str, player: Player) -> None`:
  - Looks up the `DilemmaOutcome` for `chosen_lens_id`.
  - Sets `player.dialogue_flags[outcome.outcome_flag] = True`.
  - Sets `player.dialogue_flags[flags.dilemma_resolved(dilemma.id)] = True`.
  - For every lens id in `outcome.closes`: adds it to `player.dilemma_state.closed_lenses`
    and sets `player.dialogue_flags[flags.lens_closed(lens_id)] = True`.
  - Records `player.dilemma_state.resolved[dilemma.id] = chosen_lens_id`.
  - Applies `outcome.tier_unlocks` - this sprint stores them as a permanent, queryable record
    (`player.dilemma_state.tier_unlocks_granted: dict[str, list[str]]` keyed by winning
    lens id) rather than firing arbitrary game-system side effects; later sprints/specs that
    build the actual "deepened" content read this record. Do not invent bespoke per-unlock
    mechanics here - that is the eight dilemma sprints' job when they define what each
    specific unlock means.
  - Idempotency guard: calling `resolve()` again on an already-resolved dilemma is a no-op
    (logs a warning, does not double-apply or raise).
- Investment-raising and telegraph/collision checks (`Game`, from A2-8) skip any dilemma
  whose id is already in `player.dilemma_state.resolved` - a resolved dilemma cannot re-fire.
- Investment-raising for a lens in `player.dilemma_state.closed_lenses` is rejected (raises
  or silently no-ops, implementer's choice, but must be tested either way) - a closed path
  cannot accumulate further investment even if some other system tries to raise it.
- `DilemmaResolutionView` calls `resolve()` then `pop_state()` back to whatever `GameState`
  was active before the collision interrupted it (not to `GALAXY_MAP` unconditionally -
  confirm `StateManager.pop_state()` already restores the prior state; if it does not, that
  is this sprint's fix, not a new mechanism).

**Acceptance criteria.**
1. `resolve()` on a two-pole dilemma sets exactly one `dialogue_flags` entry for the winning
   outcome's `outcome_flag`, closes the losing lens, and this is verified against a synthetic
   fixture in `tests/test_models/test_dilemma.py`.
2. Calling `resolve()` twice on the same dilemma (simulating a bug elsewhere calling it
   redundantly) does not toggle `closed_lenses` membership, does not duplicate
   `tier_unlocks_granted` entries, and does not raise.
3. `tests/test_scenarios/test_scenario_dilemma_permanent_closure.py`: resolve a synthetic
   dilemma, save to a slot, load from that slot, confirm `player.dilemma_state.closed_lenses`
   and `dialogue_flags[flags.lens_closed(...)]` both survive the round-trip.
4. Same scenario, then attempt to raise investment on the closed lens post-load; confirm the
   investment value in `player.lens_investment` does not increase. This satisfies design-spec
   Success Criterion 6 ("reloading a later save cannot reopen a closed path").
5. `DilemmaResolutionView` pushed mid-`TRADING` (or any non-`GALAXY_MAP` state), resolved,
   returns control to `TRADING`, not to a hardcoded default - verified by a view-layer test
   using the existing `tests/test_scenarios/_view_harness.py` pattern.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-11 — Scars

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 4-6 days
**Depends on**: A2-10 | **Blocks**: none

**Goal.** Build the reusable mechanism for "the refusing NPC still exists and is occasionally
seen doing the work you did not" (Success Criterion 7). This lands generically, proven with
synthetic fixtures, because the eight dilemma-content sprints (A2-12 through A2-19) do not
depend on this one - they are siblings of each other and of this sprint, so each must be able
to author its own visible-cost content without waiting on this one to land first. This sprint
generalizes the pattern; each dilemma sprint wires its own NPC into it (or, if this sprint has
not landed yet when a dilemma sprint runs, that dilemma sprint uses the direct
`NPC.dialogue_states` + flag-gating mechanism described in its own Touch zones instead - both
paths converge on the same `lens_closed(lens_id)` flag from A2-10).

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "Scars, not gaps" section.
- `spacegame/models/station_chatter.py` - `ChatterLine`, `StationChatterManager`: the
  `required_flags`/`one_shot=False` shape this sprint's scar lines reuse directly.
- `spacegame/models/dialogue.py` - `NPC.dialogue_states`, `DialogueState.required_flags` -
  the alternate/complementary path for an NPC whose entire dialogue tree should change after
  a lens closes, not just their station chatter.
- `spacegame/constants/flags.py` - `lens_closed(lens_id)` (from A2-8/A2-10).

**Touch zones.**
- `spacegame/models/station_chatter.py` (`ChatterLine.category` gains `"scar"` as a
  recognised value; no dataclass field changes needed, `required_flags` already exists)
- `data/dialogue/` (wherever `ChatterLine` content is loaded from - confirm the exact file by
  reading `DataLoader._parse_*` for station chatter before editing; add one demonstration
  scar line using a synthetic flag, not a real dilemma's flag, since no real dilemma content
  is guaranteed to exist yet)
- `tests/test_models/test_station_chatter.py` (extend)
- `tests/test_scenarios/test_scenario_dilemma_scars.py` (NEW)

**Deliverables.**
- `StationChatterManager` (or its filtering logic, wherever it lives) treats `category ==
  "scar"` lines as eligible for repeated display (never `one_shot=True` - a scar is
  "occasionally seen", not once) gated by `required_flags` containing a
  `flags.lens_closed(lens_id)` string.
- A documented convention (a docstring addition on `ChatterLine` or a short note in this
  sprint's commit, not a new markdown doc) stating: every dilemma sprint that closes a lens
  must add at least one `category: "scar"` chatter line gated on that lens's closure flag,
  spoken from the perspective of the NPC or role the player refused, doing the work the
  player chose not to do.
- A demonstration: one synthetic scar `ChatterLine` (not tied to any of the eight real
  dilemmas) proving the mechanism end-to-end, using a test-only flag name so it never
  appears in a real playthrough - this is infrastructure proof, not shippable content.
- `tests/test_scenarios/test_scenario_dilemma_scars.py`: sets a synthetic `lens_closed`
  flag directly on a `Player` fixture (bypassing the full dilemma-resolution flow, since this
  sprint must not depend on A2-8's view layer being exercised), confirms a scar-category
  `ChatterLine` gated on that flag becomes eligible for display, and confirms it remains
  eligible across multiple calls (not retired after one showing, unlike a `one_shot` line).

**Acceptance criteria.**
1. A `ChatterLine` with `category="scar"`, `one_shot=False`, `required_flags=["lens_closed_
   test_lens"]` is excluded from `StationChatterManager` output when the flag is absent, and
   included once it is present - verified in `tests/test_models/test_station_chatter.py`.
2. The same line is eligible for selection on a second, independent call after having been
   shown once (proving it is not accidentally treated as one-shot) - verified explicitly,
   not inferred from the `one_shot=False` setting alone.
3. `tests/test_scenarios/test_scenario_dilemma_scars.py` passes without depending on any of
   A2-8's `DilemmaResolutionView`, `check_collision()`, or real dilemma data - it manipulates
   `player.dialogue_flags` directly, proving this sprint's mechanism does not require the
   full engine to be exercised to be tested.
4. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-12 — D4: Truth ↔ Vengeance

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 1.5-2 weeks
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author the first and sharpest dilemma. Per the design spec this one goes first
because it reaches back into Act I: the player has spent the game since the supernova hunting
Aldric Senn, the Ledger operative whose base was neutralized in Act I Mission 16 but who
escaped ("leadership escapes... operations in uncharted space beyond the Expanse's borders" -
`requirements/act_one_reference.md` line 25). If the player has invested in Truth, this
dilemma can reveal Senn was not who orchestrated what happened to their home galaxy - a
scapegoat, a mid-level operative left behind on purpose. Vengeance's question stops being "how
do I punish him" and becomes "does my rage transfer to whoever really did this, or does it
have nowhere left to go." This sprint also does the minimal Act I seeding this dilemma needs,
since no other sprint owns it.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D4, and "D4 is the sharpest and should be authored first" paragraph (lines 180-185).
- `requirements/act_one_reference.md` - full "The Ledger" section (lines 21-25), Chapter 5
  summary (lines 78-86), and the M16 journal-entry template (line 256).
- `spacegame/models/dilemma.py`, `spacegame/data_loader.py` `_parse_dilemmas()` (from A2-8).
- `spacegame/models/dialogue.py` - `NPC`, `DialogueState`, for authoring the telegraph and
  post-collision dialogue states.
- `requirements/character_voices.md` - Dr. Priya Osei ("provides analytical perspective on
  the conspiracy" per her Act I narrative role) is this dilemma's telegraph voice.
- `requirements/dialogue_writing_guide.md` - voice and register rules before writing any line.

**Touch zones.**
- `data/narrative/dilemmas/d4_truth_vengeance.json` (NEW)
- `data/characters/` (wherever NPC records live - confirm exact file via
  `DataLoader._parse_dialogue_tree`/NPC loading before editing) - add or extend the record
  for Aldric Senn (the escaped Ledger operative the player has been hunting) if he does not
  already exist as an NPC entity; he needs at minimum an id and a post-collision
  `DialogueState`.
- `data/dialogue/` - dialogue tree content for Priya's telegraph lines and Senn's two
  post-collision states (found/spared vs. found/killed, or equivalent to this dilemma's
  actual two outcomes).
- Minimal Act I seeding: one flag set at the end of Mission 17 ("New Horizons") recording
  that the player was told Senn orchestrated the operation - find Mission 17's data entry
  (search `data/missions/` for the Ledger-reveal mission) and add a
  `dialogue_flags["vengeance_primary_suspect_id"] = "aldric_senn"`-shaped flag-set effect if
  one is not already present. This is the only Act I file this sprint touches.
- `tests/test_compliance/test_dilemma_integrity.py` runs against this file automatically
  (no edits needed there, it globs the directory).
- `tests/test_scenarios/test_scenario_dilemma_d4.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d4_truth_vengeance"`, `poles: ["truth", "vengeance"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "priya_osei"`.
- Telegraph: 2-3 lines from Priya Osei, delivered per A2-8's guaranteed-delivery mechanism,
  making plain that continued Truth investigation is starting to point away from Senn as the
  architect - and that if the player keeps hunting him anyway once that becomes undeniable,
  that is a choice, not ignorance.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "truth"`: `closes: ["vengeance"]`. The player accepts what the
    investigation shows; Senn is confronted with what he actually did (not what he was
    blamed for) rather than killed or ruined for the larger conspiracy. `tier_unlocks`:
    concrete, e.g. `["Priya shares Science Collective intelligence contacts who only work
    with people who verify before they act", "access to the Ledger's real chain of command
    as a Truth investigation thread"]`.
  - `winning_lens_id: "vengeance"`: `closes: ["truth"]`. The player closes the file anyway.
    `tier_unlocks`: e.g. `["a reputation among information brokers as someone whose targets
    do not need to be guilty of the specific thing, only guilty of something", "Vengeance's
    minigame_shape gains access to coerced-informant leads Truth-aligned contacts would
    refuse to hand over"]`.
- `closes` lists reference the losing lens id from `poles`, checked by A2-9's
  `test_poles_and_outcomes_agree`.
- Visible cost: if Truth wins, Senn's post-collision `DialogueState` (gated on
  `dialogue_flags["lens_closed_vengeance"]`) shows him alive, changed, aware of what the
  player chose. If Vengeance wins, a scar chatter line (per A2-11's convention, or direct
  `NPC.dialogue_states` gating if A2-11 has not landed) has Priya declining to discuss Ledger
  intelligence with the player going forward, gated on `dialogue_flags["lens_closed_truth"]`.
- `tests/test_scenarios/test_scenario_dilemma_d4.py`: drives `truth` and `vengeance`
  investment to collision, resolves each outcome in a separate test, asserts the correct
  lens closes, the correct NPC dialogue state becomes reachable, and the flag from the
  Mission 17 seeding is present as a precondition the dilemma's data checks.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d4_truth_vengeance"]` loads successfully via `_parse_dilemmas()`
   with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file specifically:
   both outcomes carry non-empty `tier_unlocks`, `telegraph_threshold (55) <
   collision_threshold (80)`.
3. A scenario test drives only `truth` to 90 (vengeance at 0): no collision fires. Drives
   only `vengeance` to 90 (truth at 0): no collision fires. Drives both to 85: collision
   fires and `GameState.DILEMMA_RESOLUTION` is reachable in the harness.
4. Resolving in favor of `truth` sets `dialogue_flags["lens_closed_vengeance"]` and makes
   Senn's post-collision dialogue state the active one on next dialogue entry with him,
   verified via `NPC.get_active_dialogue_id()`.
5. Resolving in favor of `vengeance` sets `dialogue_flags["lens_closed_truth"]` and makes
   Priya's declined-intelligence scar content reachable (either through
   `StationChatterManager` if A2-11 landed, or through `NPC.get_active_dialogue_id()` on
   Priya's own dialogue states if it did not - the test checks whichever path this sprint
   actually implemented and documents which one in a code comment).
6. No em-dashes, no "no X, no Y" constructions, no banned NPC names appear in any authored
   line - verified by extending `tests/test_writing_bible_compliance.py`'s scan (or
   confirming it already scans `data/dialogue/` broadly enough to catch this file without
   changes; state which is true in the sprint's commit).
7. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-13 — D2: Wealth ↔ Community

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 1.5-2 weeks
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author the emotional centre of the arc. The player's father died because Marcus
Jin's safety report on the failing air recyclers "was buried" (`requirements/act_one_reference.md`
line 254). Wealth says: I will never again be the person a company can starve of resources.
Community says: nobody who depends on me will ever be left the way my father was. Same
childhood wound, opposite conclusion, and per the design spec this pairing "should be
authored with the most care" of all eight.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D2, and "Wealth vs Community" note (lines 149-152).
- `requirements/act_one_reference.md` line 254 (M05 journal entry, Marcus Jin, the buried
  report) - this is the wound both lenses spring from and must be referenced, not restated
  generically.
- `requirements/character_voices.md` - Marcus Jin voice sheet (direct, economical, dry dark
  humor) for the telegraph; Hanna Voss (Union Dock Boss) for the Community pole; Aldous
  Prentiss (Old-Money Collector) for the Wealth pole.
- `spacegame/models/dilemma.py`, `spacegame/models/dialogue.py`, `spacegame/models/investment.py`
  (the existing per-system investment-tier mechanic, distinct from `lens_investment` - do not
  confuse the two; `investment_tier_purchased` as an `investment_from` tag for `community` was
  set in A2-6, and this dilemma's collision naturally follows sustained use of that system).

**Touch zones.**
- `data/narrative/dilemmas/d2_wealth_community.json` (NEW)
- `data/dialogue/` - Marcus's telegraph lines, Hanna Voss's and Aldous Prentiss's
  post-collision dialogue states.
- `tests/test_scenarios/test_scenario_dilemma_d2.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d2_wealth_community"`, `poles: ["wealth", "community"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "marcus_jin"`.
- Telegraph: Marcus, blunt and specific, naming that the player is capitalizing on the exact
  kind of gap (a station, a colony, a supply chain, whichever concrete system the collision
  threshold is tracking) that the report he filed twenty years ago was trying to close, and
  that they cannot keep both funding their own accumulation and funding the people who need
  it out of the same finite time and capital.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "wealth"`: `closes: ["community"]`. `tier_unlocks`: e.g. `["Aldous
    Prentiss introduces the player to buyers who do not ask where capital originated, raising
    the ceiling on trade-route profit margins", "access to leveraged financing previously
    withheld because the player's reputation read as unreliable"]`.
  - `winning_lens_id: "community"`: `closes: ["wealth"]`. `tier_unlocks`: e.g. `["Hanna Voss
    opens Union Dock Boss channels that were closed to a trader who had not proven they would
    reinvest rather than extract", "housing and logistics contracts with guaranteed demand,
    at lower margin than open trade but immune to market swings"]`.
- Visible cost: Wealth-winning closes Community - a scar line has Hanna Voss's people doing,
  without the player, the housing/triage work the player chose not to fund, gated on
  `dialogue_flags["lens_closed_community"]`. Community-winning closes Wealth - Aldous
  Prentiss stops extending credit, gated on `dialogue_flags["lens_closed_wealth"]`.
- `tests/test_scenarios/test_scenario_dilemma_d2.py` covering both resolutions, mirroring
  A2-12's test shape.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d2_wealth_community"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file: non-empty
   `tier_unlocks` on both outcomes, `telegraph_threshold (55) < collision_threshold (80)`.
3. Scenario test: driving only `wealth` to 90 does not collide; driving only `community` to
   90 does not collide; driving both to 85 collides.
4. Resolving `wealth` closes `community` and makes Hanna Voss's scar content (or direct
   dialogue-state gating) reachable; resolving `community` closes `wealth` and makes Aldous
   Prentiss's declined-credit state reachable. Both verified explicitly, one per test.
5. Marcus Jin's telegraph line references the specific buried-report wound (via a shared
   constant or direct textual echo of "buried" / "report" / "recyclers"), not generic
   "you're choosing between two things" language - verified by a substring check in the test
   asserting the telegraph text contains at least one of those anchor words.
6. No em-dashes, no "no X, no Y" constructions, no "a testament to"/"couldn't help but", no
   banned NPC names.
7. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-14 — D1: Vengeance ↔ Justice

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author the personal-against-ideological dilemma. The player can hold "they took my
world" and "nobody should be permitted to do this to anyone" simultaneously for a long time -
that is what makes their eventual collision hurt. This sprint is independent of A2-12 (D4);
if D4 has already resolved Vengeance for a given player before this dilemma's threshold is
reached, this dilemma simply never fires for that player (its collision check requires
`vengeance` to still be an open lens - see acceptance criterion 3).

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D1, and "Vengeance vs Justice" note (lines 154-157).
- `requirements/character_voices.md` - Captain Reva Sato (Guild Military, established Act I
  contact via `met_reva_sato` flag per `act_one_reference.md` line 164) for the Justice pole
  and telegraph; Elena Reeves voice sheet for an alternate telegraph consideration (this
  sprint picks one, documented below).
- `spacegame/models/dilemma.py`, `spacegame/models/dialogue.py`.

**Touch zones.**
- `data/narrative/dilemmas/d1_vengeance_justice.json` (NEW)
- `data/dialogue/` - Elena's telegraph lines, Reva Sato's post-collision dialogue states.
- `tests/test_scenarios/test_scenario_dilemma_d1.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d1_vengeance_justice"`, `poles: ["vengeance", "justice"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "elena_reeves"` - Elena, not Reva, delivers the telegraph: she is the
  one who watches the player across both systems (bounty work and lawful dispute resolution)
  and per her voice sheet disagrees "with respect" rather than confronting directly, which
  fits telling the player something they do not want to hear without becoming an antagonist
  herself.
- The collision check for this dilemma additionally requires `vengeance` not already be in
  `player.dilemma_state.closed_lenses` (i.e. D4 has not already resolved it) - implemented as
  a guard in `Game`'s per-dilemma collision loop (from A2-8), generalized: any dilemma whose
  pole is already closed by another dilemma's resolution is permanently ineligible to
  collide. Add this as a general rule in `spacegame/models/dilemma.py`'s collision-checking
  path if A2-8/A2-10 did not already implement it (check before assuming; if it exists,
  this sprint's deliverable is just proving it against this specific pairing).
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "vengeance"`: `closes: ["justice"]`. `tier_unlocks`: e.g. `["access to
    methods Reva Sato's command would never sanction: coercion, off-books informants,
    unauthorized use of Guild Military intelligence contacts the player burned this
    relationship to reach"]`.
  - `winning_lens_id: "justice"`: `closes: ["vengeance"]`. `tier_unlocks`: e.g. `["Reva Sato
    sponsors the player for a warrant-holding authority previously unavailable to a
    civilian", "case-building contacts across factions who will testify for someone who has
    proven they will use due process even when it costs them a target"]`.
- Visible cost: Justice-winning closes Vengeance - the target(s) Vengeance would have pursued
  remain alive and known, occasionally referenced by name in ambient chatter as still out
  there, a permanent visible reminder of what was not done. Vengeance-winning closes
  Justice - Reva Sato's post-collision dialogue state has her declining further cooperation,
  gated on `dialogue_flags["lens_closed_justice"]`.
- `tests/test_scenarios/test_scenario_dilemma_d1.py` mirroring A2-12/A2-13's shape, plus a
  test proving the "already-closed pole is permanently ineligible" guard: close `vengeance`
  via a synthetic resolution first, then confirm this dilemma's collision never fires even
  when both raw investment values are driven above threshold.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d1_vengeance_justice"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file.
3. If `vengeance` is already in `player.dilemma_state.closed_lenses` (simulating D4 having
   resolved first), this dilemma's collision check returns `False` regardless of raw
   investment values - verified explicitly, not assumed.
4. Absent that precondition, driving both poles to 85 collides; driving only one does not.
5. Resolving `justice` closes `vengeance` and its scar (named targets still referenced in
   ambient content); resolving `vengeance` closes `justice` and reaches Reva Sato's
   post-collision state.
6. No em-dashes, no "no X, no Y" constructions, no banned NPC names.
7. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-15 — D3: Political Power ↔ Revolution ↔ Empire

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 1.5-2 weeks
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author the one three-way dilemma: master the system, break it, or become it. This
is the sprint that exercises A2-8's `collision_requires < len(poles)` support for real -
resolving to exactly one of three closes the other two simultaneously, which no other
dilemma in this arc does.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D3, "D3 is a triangle" note (line 177), and "Political Power vs Revolution vs Empire"
  differentiation note (lines 145-147).
- `spacegame/models/dilemma.py` - confirm `Dilemma.poles` and `collision_requires` support
  three entries with `collision_requires=2` (built in A2-8, criterion 6 there).
- `requirements/character_voices.md` - Mayor Cressida Vance (Verdant Mayor) for Political
  Power; Councillor Bram Wentworth (Alliance Congress, Haven's Rest) for Empire; Tomas
  Drifter (Frontier Alliance-aligned, freedom-focused per his voice sheet) for the telegraph.
  This dilemma needs a new NPC for Revolution - introduce **Organizer Sorcha Deng**, a Miners
  Union labor organizer (not a banned name; not reused from any existing sheet). Write her a
  short voice note in this sprint's own dialogue content (not a full character_voices.md
  entry - that document is Act I's, this is Act II data) establishing her as direct,
  impatient with process, distinct from Marcus Jin's dry resignation.

**Touch zones.**
- `data/narrative/dilemmas/d3_power_revolution_empire.json` (NEW)
- `data/dialogue/` - Tomas's telegraph lines, Vance's/Deng's/Wentworth's post-collision
  dialogue states, Deng's NPC record if she does not already exist.
- `tests/test_scenarios/test_scenario_dilemma_d3.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d3_power_revolution_empire"`,
  `poles: ["political_power", "revolution", "empire"]`, `collision_requires: 2`,
  `telegraph_threshold: 55`, `collision_threshold: 80`, `telegraph_npc_id: "tomas_drifter"`.
- Telegraph: Tomas, who left the Commerce Guild's tariff system behind for gray-market trade
  built on handshakes, notices the player is simultaneously courting Verdant's council,
  funding labor unrest, and buying territorial claims, and says plainly that whichever two of
  those the player is actually serious about, the third is about to become impossible.
- Three `DilemmaOutcome` entries, each closing the other two:
  - `winning_lens_id: "political_power"`: `closes: ["revolution", "empire"]`.
    `tier_unlocks`: e.g. `["Mayor Vance backs the player for a seat that does not exist yet,
    created specifically because the player proved they would work inside the system rather
    than around or over it"]`.
  - `winning_lens_id: "revolution"`: `closes: ["political_power", "empire"]`.
    `tier_unlocks`: e.g. `["Sorcha Deng's cells across multiple systems now coordinate
    through the player directly, access no negotiated council seat or claimed territory
    would have earned"]`.
  - `winning_lens_id: "empire"`: `closes: ["political_power", "revolution"]`.
    `tier_unlocks`: e.g. `["Councillor Wentworth cedes administrative authority over a
    contested border system, the first sovereign territory the player holds outright"]`.
- Visible cost per outcome: whichever two lose, both get a scar. E.g. Empire wins: Vance's
  post-collision state has her treating the player as an outside power now, not a peer
  seeking a council seat; Deng's scar chatter has her organizing against the player's new
  territory specifically.
- `tests/test_scenarios/test_scenario_dilemma_d3.py`: for each of the three outcomes, a
  dedicated test resolving to that pole and asserting the other two close simultaneously
  (single `resolve()` call closes two lenses at once - this is the concrete proof that
  `DilemmaOutcome.closes` supports more than one entry, which none of the seven pair-dilemmas
  exercise).

**Acceptance criteria.**
1. `DataLoader.dilemmas["d3_power_revolution_empire"]` loads with three outcomes, each
   `closes` containing exactly the other two pole ids.
2. `tests/test_compliance/test_dilemma_integrity.py` passes: all three outcomes carry
   non-empty `tier_unlocks`; `telegraph_threshold < collision_threshold`.
3. Collision requires exactly 2 of 3 poles at threshold: driving `political_power` and
   `revolution` to 85 with `empire` at 0 collides and offers all three as resolution options
   (per A2-8's rule that a pole below threshold is still offered when `len(poles) >
   collision_requires`); driving only `political_power` to 85 with the other two at 0 does
   not collide.
4. Resolving to any one of the three closes the other two in a single `resolve()` call,
   verified once per outcome (three tests).
5. Sorcha Deng is not a banned name and does not collide with an existing NPC id.
6. No em-dashes, no "no X, no Y" constructions, no banned NPC names anywhere in authored
   content including Deng's new voice note.
7. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-16 — D5: Legacy ↔ Connection

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author "remembered by history, or by the people who knew you?" Legacy pulls the
player toward institution-building that outlives them; Connection pulls toward the crew and
relationships in front of them right now. This is the dilemma most directly about the crew
the player has spent the whole game with, and it should cost the player time with them, not
just abstract lens investment.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D5.
- `requirements/character_voices.md` - Dr. Nadia Kweon (Okafor Institute Director) for
  Legacy, established via SA-R2 "Dr. Okafor's Legacy Narrative Arc"; Elena Reeves for
  Connection (established first-recruit, closest early confidante per
  `requirements/act_one_reference.md`'s closing-state description).
- `spacegame/models/okafor_research.py` - existing Legacy-adjacent system (research
  patronage, institution-founding) this dilemma's Legacy pole should reference concretely
  rather than invent a parallel system.
- `spacegame/models/crew.py` - crew loyalty mechanics, for how Connection's investment and
  visible cost should hook into something already tracked (loyalty), not a new parallel stat.

**Touch zones.**
- `data/narrative/dilemmas/d5_legacy_connection.json` (NEW)
- `data/dialogue/` - Marcus Jin's telegraph lines (chosen because Elena is one of this
  dilemma's poles, not its telegraph voice - using her would be a conflict of interest in the
  fiction itself), Kweon's and Elena's post-collision dialogue states.
- `tests/test_scenarios/test_scenario_dilemma_d5.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d5_legacy_connection"`, `poles: ["legacy", "connection"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "marcus_jin"`.
- Telegraph: Marcus, direct, notes the player has been funding institutions at Okafor and is
  increasingly absent from the ship's actual day-to-day; says the crew notices captains who
  are present and captains who are somewhere else even when they are on the bridge.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "legacy"`: `closes: ["connection"]`. `tier_unlocks`: e.g. `["Dr. Kweon
    names a wing of the Okafor Institute after the player while they are still alive to see
    it, and grants the player standing authority over its research direction"]`.
  - `winning_lens_id: "connection"`: `closes: ["legacy"]`. `tier_unlocks`: e.g. `["crew
    loyalty ceilings across the whole roster rise permanently, and previously unavailable
    personal dialogue and relationship content opens for every recruited member, not just
    Elena"]`.
- Visible cost: Legacy-winning closes Connection - Elena's post-collision dialogue state has
  her professional and correct with the player in a way that reads as distance, not warmth,
  gated on `dialogue_flags["lens_closed_connection"]`. Connection-winning closes Legacy -
  Kweon's scar content has the Institute's wing named after someone else, gated on
  `dialogue_flags["lens_closed_legacy"]`.
- `tests/test_scenarios/test_scenario_dilemma_d5.py` mirroring the established shape.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d5_legacy_connection"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file.
3. Collision behavior matches the established pair-dilemma pattern (one pole high does not
   collide, both high does).
4. Resolving `connection` raises (or unlocks the mechanism to raise) crew loyalty ceilings -
   verified by a test asserting the loyalty ceiling constant/lookup used by `crew.py` differs
   for a resolved-connection player versus an unresolved one. If `crew.py` has no existing
   loyalty-ceiling concept to hook into, this criterion is satisfied instead by asserting the
   unlock is recorded in `player.dilemma_state.tier_unlocks_granted["connection"]` and a
   TODO-free comment explains which future sprint wires the mechanical effect - do not
   silently drop the requirement.
5. No em-dashes, no "no X, no Y" constructions, no banned NPC names.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-17 — D6: Preservation ↔ Empire

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author "save what remains, or build over it?" This dilemma reuses the same Empire
figure (Councillor Bram Wentworth) introduced in A2-15's D3, so a player who has already
resolved D3 toward Empire meets the natural continuation of that choice here: having become a
territorial power, they now face what that power does to the things Preservation would have
protected.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D6.
- `requirements/character_voices.md` - Sten Brygaard (Deep Shafts Caretaker, established via
  SA-2 "Deep Shafts memorial/pilgrimage") for Preservation; Councillor Bram Wentworth for
  Empire, same NPC as A2-15 - do not create a second Wentworth record, extend the existing
  one's `dialogue_states` if A2-15 has already landed, or author it fresh (matching A2-15's
  voice) if this sprint runs first, since both are siblings with no ordering guarantee.
- `spacegame/models/deep_shafts.py` - existing Preservation-adjacent system this dilemma's
  Preservation pole should reference.

**Touch zones.**
- `data/narrative/dilemmas/d6_preservation_empire.json` (NEW)
- `data/dialogue/` - Priya Osei's telegraph lines (archivist-minded, fits Preservation
  proximity without being one of its two poles), Brygaard's and Wentworth's post-collision
  dialogue states.
- `tests/test_scenarios/test_scenario_dilemma_d6.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d6_preservation_empire"`, `poles: ["preservation", "empire"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "priya_osei"`.
- Telegraph: Priya notes that the sites the player has been cataloguing and protecting sit
  inside the borders the player is also claiming, and that a claimed border eventually gets
  developed, mined, or garrisoned whether or not the claimant intends it personally.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "preservation"`: `closes: ["empire"]`. `tier_unlocks`: e.g. `["Sten
    Brygaard grants standing archival authority over Deep Shafts-class sites across the
    Expanse, previously granted only after individual case-by-case review"]`.
  - `winning_lens_id: "empire"`: `closes: ["preservation"]`. `tier_unlocks`: e.g. `["the
    territory the player holds generates resource yield other empire-track content can draw
    on, at the cost of the sites within it"]`.
- Visible cost: Preservation-winning closes Empire - Wentworth's scar content has him
  administering the territory the player declined to claim, developing exactly the sites the
  player protected elsewhere. Empire-winning closes Preservation - Brygaard's post-collision
  state has him relocating what he can save away from the player's claimed territory,
  permanently reduced in scope, gated on `dialogue_flags["lens_closed_preservation"]`.
- `tests/test_scenarios/test_scenario_dilemma_d6.py` mirroring the established shape.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d6_preservation_empire"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file.
3. Collision behavior matches the established pattern.
4. If `data/dialogue/`'s Wentworth NPC record already exists (A2-15 landed first), this
   sprint extends it rather than duplicating the id - verified by a test asserting exactly
   one NPC record with id `bram_wentworth` exists after `load_all()` regardless of which of
   A2-15/A2-17 ran first.
5. No em-dashes, no "no X, no Y" constructions, no banned NPC names.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-18 — D7: Faith ↔ Transcendence

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author "find meaning, or manufacture it?" Faith searches for something in the
universe that already means something; Transcendence pushes past ordinary humanity to make
meaning irrelevant to the question. This is the one dilemma with no existing Act I grounding
to build on, so it introduces one new location-appropriate NPC.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D7.
- `requirements/cultural_guide.md` - Haven's Rest ("The Hearth") system profile (around line
  542) for tone/setting; Frontier Alliance cultural profile (line 281) since Haven's Rest is
  Frontier Alliance territory per the character-voice cross-references.
- `requirements/character_voices.md` - Dr. Iris Navarro (Okafor Institute Clinical Lead) for
  Transcendence, an established biotech/irreversible-upgrade-adjacent figure.
- `spacegame/models/okafor_research.py` - existing risk-tiered project system (`FAILURE_ODDS`,
  high-risk tier) this dilemma's Transcendence pole should reference for "irreversible
  upgrades with real costs" rather than invent a parallel risk mechanic.

**Touch zones.**
- `data/narrative/dilemmas/d7_faith_transcendence.json` (NEW)
- `data/dialogue/` - Tomas Drifter's telegraph lines (grounded skeptic-trader voice, distinct
  from both poles), a new NPC record for **Chaplain Imre Solano** of Haven's Rest (Faith
  pole), Navarro's post-collision dialogue state.
- `tests/test_scenarios/test_scenario_dilemma_d7.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d7_faith_transcendence"`, `poles: ["faith", "transcendence"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "tomas_drifter"`.
- Chaplain Imre Solano: a short voice note authored in this sprint (not
  `character_voices.md`, which is Act I's document) establishing a grounded, non-mystical
  register consistent with the writing guide's anti-GenAI-trope rules - he does not speak in
  vague cosmic pronouncements; per `requirements/dialogue_writing_guide.md`'s register rules,
  Haven's Rest speech is plain and handshake-direct (per the cultural guide's Frontier
  Alliance profile), so Solano's faith voice should sound like a person who works with his
  hands and thinks the universe rewards attention, not a priest reciting doctrine.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "faith"`: `closes: ["transcendence"]`. `tier_unlocks`: e.g. `["Solano
    grants the player standing invitation into Haven's Rest's closed pilgrimage sites,
    previously open only to residents"]`.
  - `winning_lens_id: "transcendence"`: `closes: ["faith"]`. `tier_unlocks`: e.g. `["Dr.
    Navarro authorizes an experimental procedure tier previously withheld pending the
    Institute's ethics review, on the strength of the player having already proven willing to
    accept irreversible personal cost"]`.
- Visible cost: Faith-winning closes Transcendence - Navarro's scar content has her
  proceeding with the procedure on another volunteer instead, referenced in passing. Faith
  losing to Transcendence - Solano's post-collision state has him treating the player as
  someone who chose to stop looking, gated on `dialogue_flags["lens_closed_faith"]`.
- `tests/test_scenarios/test_scenario_dilemma_d7.py` mirroring the established shape.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d7_faith_transcendence"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file.
3. Collision behavior matches the established pattern.
4. Imre Solano's authored lines contain no doctrinal-recitation or vague-mysticism phrasing -
   verified by a targeted substring/regex check (or, at minimum, a documented manual review
   note in the commit) rejecting stock phrases like "the universe has a plan" or "everything
   happens for a reason."
5. No em-dashes, no "no X, no Y" constructions, no "a testament to"/"couldn't help but", no
   banned NPC names (Imre Solano is not on the banned list).
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-19 — D8: Crime ↔ Community

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-9, A2-10 | **Blocks**: none

**Goal.** Author "your organisation, or the people it preys on?" This is the last of the
eight and reuses Hanna Voss (Union Dock Boss) as the Community pole, the same NPC used in
A2-13's D2 - the design intent is that Voss represents the same community the player either
builds, profits distantly from, or preys on, and whichever dilemma fires first for a given
player determines which way that relationship goes.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "The eight dilemmas" table
  row D8.
- `requirements/character_voices.md` - Vex Tarn (Reach Floor Manager, Crimson Reach) for
  Crime; Hanna Voss (Union Dock Boss) for Community, same record as A2-13.
- A2-13's sprint section (this file) for exactly how Hanna Voss's `DialogueState`s are
  structured, so this sprint extends rather than conflicts with them.

**Touch zones.**
- `data/narrative/dilemmas/d8_crime_community.json` (NEW)
- `data/dialogue/` - Elena Reeves's telegraph lines, Vex Tarn's post-collision dialogue
  state, Hanna Voss's post-collision dialogue state (a second gated state on the same NPC
  record A2-13 touches - if A2-13 has already landed, confirm the flag-gating key does not
  collide with A2-13's `dialogue_flags["lens_closed_community"]` state; this dilemma's
  Community-losing state is gated on a distinct flag since it is a different dilemma
  resolving against the same lens for the same underlying reason. Use
  `dialogue_flags["lens_closed_community"]` for both - the lens itself is what closes, not
  the dilemma, so both D2 and D8 closing Community should converge on the same flag and the
  same Voss dialogue state rather than authoring two redundant ones. If A2-13 has already
  authored that state, reuse it; do not duplicate.)
- `tests/test_scenarios/test_scenario_dilemma_d8.py` (NEW)

**Deliverables.**
- `Dilemma` record `id: "d8_crime_community"`, `poles: ["crime", "community"]`,
  `collision_requires: 2`, `telegraph_threshold: 55`, `collision_threshold: 80`,
  `telegraph_npc_id: "elena_reeves"`.
- Telegraph: Elena, precise and disapproving in her characteristic "with respect" register,
  notes that the black-market routes the player runs through Crimson Reach touch the same
  supply lines Hanna Voss's people depend on, and that "helping" a community while also
  running product through its docks is not a position that holds indefinitely.
- Two `DilemmaOutcome` entries:
  - `winning_lens_id: "crime"`: `closes: ["community"]`. `tier_unlocks`: e.g. `["Vex Tarn
    grants standing access to Crimson Reach's floor operations without per-run negotiation,
    previously earned only run by run"]`.
  - `winning_lens_id: "community"`: `closes: ["crime"]`. `tier_unlocks`: reuse/align with
    A2-13's `community`-winning `tier_unlocks` where the underlying unlock is the same
    (Hanna Voss's channels) - do not author a second, contradictory description of what
    resolving `community` grants; if A2-13 has already landed, read its `tier_unlocks` text
    and match it exactly or extend it, do not diverge.
- Visible cost: reuses A2-13's Voss scar/dialogue-state content if it exists (see Touch zones
  note above); Crime-winning's Community-side visible cost is Voss's people doing without
  the player, same convention as A2-13. Community-winning closes Crime - Vex Tarn's
  post-collision state has him treating the player as someone no longer welcome on the floor,
  gated on `dialogue_flags["lens_closed_crime"]`.
- `tests/test_scenarios/test_scenario_dilemma_d8.py` mirroring the established shape, plus a
  test confirming that if both this dilemma and A2-13's D2 resolve `community` as the winner
  for the same player (in either order), `dialogue_flags["lens_closed_community"]` is set
  exactly once with no conflicting duplicate flag, and Voss's dialogue state is the same one
  both dilemmas reference.

**Acceptance criteria.**
1. `DataLoader.dilemmas["d8_crime_community"]` loads with both outcomes populated.
2. `tests/test_compliance/test_dilemma_integrity.py` passes against this file.
3. Collision behavior matches the established pattern.
4. Resolving `crime` here and (in a separate test setup) resolving `wealth` in A2-13 against
   the same player both leave `community` closed via the same flag key, with no second,
   contradictory flag name introduced by this sprint.
5. No em-dashes, no "no X, no Y" constructions, no banned NPC names.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-20 — Capstones fire without ending the session

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 6-8 days
**Depends on**: A2-10, A2-3 | **Blocks**: A2-21

**Goal.** Wire the capstone hook contract A2-3 defines into an actual firing mechanism: when
a lens's investment crosses its capstone threshold and that lens has not been closed by a
dilemma, the game interrupts with a capstone moment and then hands control straight back -
play continues. No real capstone prose is authored here; "Authored galaxy content" stays out
of scope for this whole arc, so this sprint uses generated placeholder narration to prove the
mechanism, not sixteen hand-written cutscenes.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "Endings are capstones,
  and the game does not stop" section, and Success Criterion 8.
- `spacegame/models/capstone.py`, `data/narrative/capstones.json` (from A2-3) - read the
  actual hook-contract shape A2-3 shipped; if it differs from the assumption in this file's
  "Conventions" section above, adapt this sprint's implementation to match what A2-3 actually
  built rather than what was assumed.
- `spacegame/models/dilemma.py`, `spacegame/models/player.py` (`dilemma_state.closed_lenses`,
  from A2-8/A2-10) - a capstone must not be reachable for a closed lens.
- `spacegame/views/tutorial_narration_modal.py`, `spacegame/engine/state_manager.py` - same
  push/pop overlay pattern A2-8 used for `DilemmaResolutionView`.
- `spacegame/config.py` - `GameState` enum.

**Touch zones.**
- `spacegame/models/capstone.py` (extend with firing-condition helper if A2-3 did not
  already include one; see Deliverables)
- `spacegame/models/player.py` (`capstones_reached: set[str] = field(default_factory=set)`)
- `spacegame/engine/game.py` (capstone threshold check wired alongside the dilemma checks
  from A2-8)
- `spacegame/config.py` (`GameState.CAPSTONE`)
- `spacegame/views/capstone_view.py` (NEW)
- `data/narrative/capstones.json` - sixteen entries, one per lens, each with a
  `capstone_threshold` (suggest 95, above any dilemma's `collision_threshold` of 80, so a
  capstone typically follows a resolved dilemma rather than preceding it) and a
  `narration_key` pointing at generated, not hand-authored, text (see Deliverables).
- `tests/test_scenarios/test_scenario_capstone_session_continues.py` (NEW)

**Deliverables.**
- Sixteen `Capstone` records in `data/narrative/capstones.json`, one per lens id, each with
  `capstone_threshold: 95`. `narration_key` references a template string, not bespoke prose -
  e.g. `"{lens_name} capstone reached: your reputation as someone who chose {core_fantasy}
  is now fixed."` rendered by substituting the loaded `Lens.name`/`Lens.core_fantasy` at
  display time. This is explicitly placeholder, not final content; a code comment in
  `capstone_view.py` states this clearly for whichever future sprint replaces it.
- Firing condition: `lens_investment.get(lens_id) >= capstone.capstone_threshold AND lens_id
  not in player.dilemma_state.closed_lenses AND lens_id not in player.capstones_reached`.
  Checked alongside A2-8's per-action dilemma checks, same `action_type` hook points in
  `game.py`.
- On firing: `push_state(GameState.CAPSTONE)`, `CapstoneView` renders the rendered
  `narration_key` text with a single acknowledge control (no branching choice, unlike
  `DilemmaResolutionView` - a capstone is not a decision), adds `lens_id` to
  `player.capstones_reached`, then on acknowledge calls `pop_state()` back to the prior
  `GameState`.
- A closed lens can never reach its capstone - the guard above is permanent, not just a
  point-in-time check, since `closed_lenses` only grows.

**Acceptance criteria.**
1. Driving a lens's investment to `capstone_threshold` fires `GameState.CAPSTONE`; driving it
   one point short does not - verified in
   `tests/test_scenarios/test_scenario_capstone_session_continues.py`.
2. After acknowledging the capstone, `GameState` returns to whatever state was active before
   the interrupt (mirrors A2-10's criterion 5 for `DilemmaResolutionView`), and the
   underlying game loop continues - verified by asserting the player can immediately perform
   another action (e.g. a trade) in the same test without any additional setup, proving the
   session did not end. This satisfies design-spec Success Criterion 8 directly.
3. A lens already in `player.dilemma_state.closed_lenses` never fires its capstone even when
   a test directly sets its investment above `capstone_threshold` (simulating investment
   raised before closure, then closure happening) - verified explicitly.
4. Firing a capstone twice for the same lens (simulating investment staying above threshold
   after the first fire) does not push a second `GameState.CAPSTONE` - guarded by
   `capstones_reached` membership.
5. `capstones_reached` round-trips through save/load, extending
   `tests/test_scenarios/test_scenario_save_load.py`.
6. Full suite green; no regression from baseline.

**Activity log.**
- 2026-08-27 - todo (created)

---

#### A2-21 — Post-capstone generation keyed to resolved identity

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 1.5-2 weeks
**Depends on**: A2-20 | **Blocks**: none

**Goal.** Make the resolved identity into a content generator, per the design spec's "After
the capstone" section: Empire resolved begins the problems of empire; Community resolved
begins scarcity and outside interest; Vengeance resolved means meeting people who know what
the player did. This sprint implements exactly the three worked examples the design spec
gives, plus the general framework, keyed off `player.capstones_reached` and
`player.dilemma_state.resolved`. This is the last sprint in the Act II arc's dependency chain.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` - "After the capstone: identity
  is the generator" section in full (lines 251-296), especially the three worked examples
  (Empire, Community, Vengeance) and "Procedural plus lens stops being generic".
- `spacegame/models/procedural_missions.py` - `ProceduralMissionGenerator`, its five existing
  mission types and deterministic seeding (`random.Random(base_seed + system_id + game_day)`
  pattern) - this sprint's generator follows the same determinism discipline.
- `spacegame/models/galaxy_event.py` - `GalaxyEventGenerator`, `GalaxyEventType` enum, for
  the "world moves without the player" texture (explicitly the simulation half of this is
  deferred to a sibling spec per the design doc's Scope section, but generating a mission or
  event keyed to resolved identity is squarely in scope here).
- `spacegame/engine/game.py` lines ~682 and ~5042 - the two existing
  `ProceduralMissionGenerator(...)` construction sites this sprint's generator integrates
  alongside.

**Touch zones.**
- `spacegame/models/post_capstone_content.py` (NEW)
- `spacegame/models/procedural_missions.py` (extend, do not fork - add identity-keyed mission
  types alongside the existing five)
- `spacegame/models/galaxy_event.py` (extend `GalaxyEventGenerator` with identity-keyed event
  weighting)
- `spacegame/engine/game.py` (wire `post_capstone_content` generator alongside the existing
  procedural mission/event generation call sites)
- `tests/test_models/test_post_capstone_content.py` (NEW)
- `tests/test_scenarios/test_scenario_post_capstone_generation.py` (NEW)

**Deliverables.**
- `spacegame/models/post_capstone_content.py`:
  - `PostCapstoneContentGenerator` class, constructed with the same
    `(systems, commodities, enemy_templates, seed)` shape as `ProceduralMissionGenerator`
    for consistency, plus `player.capstones_reached` and `player.dilemma_state.resolved` as
    generation inputs.
  - `generate_for_lens(lens_id: str, game_day: int) -> list[Mission] | list[GalaxyEvent]`
    dispatches to a per-lens content template. This sprint implements three concretely, per
    the design spec's own worked examples, and stubs the rest with a documented
    not-yet-implemented path that does not crash (returns an empty list, logs at `debug`
    level) rather than raising, so a lens without a template does not break the game:
    - `empire`: generates succession/border-dispute missions - a `MissionObjective` set using
      `ObjectiveType.REACH_SYSTEM` plus `ObjectiveType.HAS_FLAG` against the player's held
      territory (from A2-15/A2-17's Empire outcomes), narratively a governor overreaching or
      a colony resisting.
    - `community`: generates scarcity/newcomer missions - `ObjectiveType.COLLECT_CARGO`
      objectives representing resource strain on what the player built, or an outside faction
      probing the settlement's value.
    - `vengeance`: generates encounters or dialogue-gated content where an NPC references
      what the player did to resolve Vengeance (reusing the `dialogue_flags` set by A2-12's
      or A2-14's resolution), not a generic bounty - the content must be textually specific
      to the fact that the player is known for this, not interchangeable with any other
      lens's content.
  - Determinism: seeded `random.Random(f"{lens_id}_{game_day}_{seed}")`, matching the
    project's existing "no save scumming" / deterministic-outcome convention from CLAUDE.md.
- Wiring in `game.py`: after a capstone fires (A2-20) and on subsequent game-day advances
  while a lens remains in `capstones_reached`, `PostCapstoneContentGenerator.generate_for_lens`
  is called and its output merged into the existing procedural mission board / galaxy event
  pool, not presented through a separate, disconnected UI surface.

**Acceptance criteria.**
1. `generate_for_lens("empire", game_day=N)` for a player with an Empire capstone reached and
   at least one held territory (from a resolved D3 or D6 outcome) returns at least one
   `Mission` whose objectives reference that territory's system id, verified with a fixture
   player.
2. `generate_for_lens("community", game_day=N)` for a player with a Community capstone
   reached returns content distinguishable from generic procedural missions - verified by
   asserting the generated mission's `id` or `description` contains a marker distinguishing
   it from `ProceduralMissionGenerator`'s five existing types (e.g. an id prefix like
   `post_capstone_community_`).
3. `generate_for_lens("vengeance", game_day=N)` for a player who resolved D4 or D1 in
   Vengeance's favor returns content referencing the specific resolution (via the
   `outcome_flag` set at resolution time), not generic bounty content - verified by asserting
   the generated content's flag-gating references that specific `outcome_flag`.
3a. Calling `generate_for_lens()` for any lens without an implemented template (e.g.
   `"faith"`) returns `[]` and does not raise - verified explicitly.
4. Two calls to `generate_for_lens("empire", game_day=10)` with the same seed and same player
   state produce identical output (same mission ids/parameters) - determinism, matching the
   project convention, verified by an equality assertion across two independent calls.
5. `tests/test_scenarios/test_scenario_post_capstone_generation.py`: drives a player to an
   Empire capstone (via A2-20's mechanism), advances the game day, and confirms the
   procedural mission board (as read by whatever existing accessor the station-hub view uses)
   contains at least one post-capstone-generated mission alongside the normal procedural set,
   proving the merge into existing systems rather than a disconnected surface.
6. Full suite green; no regression from baseline. This is the last sprint in the Act II
   dependency chain (`A2-21` blocks nothing further in this decomposition) - its own tests
   are the final gate for design-spec Success Criterion 9.

**Activity log.**
- 2026-08-27 - todo (created)
