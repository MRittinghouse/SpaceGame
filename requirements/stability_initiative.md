# Stability Initiative (SI)

## Status (2026-04-24)

- **SI-1** — ✅ shipped end-to-end
- **SI-2 Stream 1** (scenario tests) — ✅ 5 scenarios shipped (combat
  victory, mining → refining chain, random encounter, shipyard install,
  ground mission lifecycle); 1 latent crash fixed (`game.py:3305`)
- **SI-2 Stream 2** (TypedDict/dataclass migration) — ✅ cookbook +
  5 tables migrated (`TUTORIAL_PARTS`, `_DEFAULT_EVENT_TEMPLATES`,
  `MILESTONE_POOL`, `TRADE_MILESTONES`, `TUTORIAL_STEPS`,
  `MINIGAME_HINTS`); Scanner B broadened to catch four shapes;
  20 baseline orphans catalogued for follow-up
- **SI-2 Stream 3** (flag registry backfill) — ✅ first wave shipped:
  cookbook + 5 helpers (~30+ flag sites migrated across
  `completed_mission_*`, `met_*`, `talked_to_*`, `dual_tech_*_revealed`,
  `encounter_seen_*`); Scanner A widened to auto-discover registered
  prefixes; integrity scanner taught to recognize helper-routed reads
- **SI-3** — ratchet active via two compliance scanners auto-tracking
  the registry; no per-migration scanner edits required

## Origin

Two game-breaking crashes from the same latent bug (`KeyError: 'slot_def_id'`
in `ship_builder_view`) surfaced within a single playtest session. The fix
for one site did not cover the second site. Root cause analysis identified
a stack of missing defenses: stringly-typed content, unchecked cross-module
string contracts, test fixtures that mirrored the production bug, no
critical-path runtime smoke, and repeat-pattern bugs not caught at fix time.

SI is a layered response. It establishes defenses going forward, builds
infrastructure once, and backfills targeted high-risk surfaces. It is NOT
a big-bang refactor — ongoing game development continues in parallel.

## Phases

### SI-1 — First wave (this sprint)

Concrete, self-contained, ~4 hours of focused work. Addresses the stack
of defenses for the exact bug class that just caused two crashes.

- **Flag registry**: `spacegame/constants/flags.py`. Tutorial flags as
  module constants / helper functions. Both shop and builder import from
  it — drift becomes impossible.
- **TutorialPart dataclass**: `TUTORIAL_PARTS: list[dict]` migrates to
  `list[TutorialPart]` (frozen dataclass). Attribute access replaces dict
  indexing; MyPy catches schema mismatches at import time.
- **New-game happy-path scenario test**: end-to-end exercise of
  `new_game → tutorial_shop → buy parts → ship_builder → render palette
  → render narration → confirm build`. Would have caught both crashes
  on day zero.
- **Two compliance scanners**:
  - **Flag-string discipline**: raw `"tutorial_bought_*"` strings outside
    the flags registry fail the suite.
  - **list[dict] content discipline**: advisory-mode detection of
    module-level `list[dict]` content declarations. Allowlist-based so
    SI-2 backfill can tighten progressively.

### SI-2 — Backfill (opportunistic, post-SI-1)

Longer-horizon work. Each item ships as a self-contained sprint between
game-development sprints. No single sprint gates game work.

#### Stream 1 — Scenario test expansion ✅ shipped

Five scenarios shipped, covering the highest-leverage gameplay loops a
playtester hits in a typical session. Each scenario mirrors the
relevant view-layer dispatch inline so a regression in any reward
primitive surfaces immediately.

- `tests/test_scenarios/test_scenario_combat_victory.py` — engine
  victory detection + reward dispatch (mirrors `game.py:3039`)
- `tests/test_scenarios/test_scenario_mining_to_refining.py` — full
  ore → silo → cargo → recipe → buffer → cargo chain
- `tests/test_scenarios/test_scenario_random_encounter.py` — trigger,
  selection, skill-check branching, all 8 reward types
- `tests/test_scenarios/test_scenario_shipyard_install.py` — gating,
  transaction guards, mark enhancement, stats reflection
- `tests/test_scenarios/test_scenario_ground_mission_lifecycle.py` —
  outcome semantics across SUCCESS / EXTRACTED / DEFEATED / FLED
  (surfaced and fixed `game.py:3305` reputation crash in the process)

Combined with the scenarios that already existed (save/load,
subsystem combat, skill combat paths, mission flow, trading, crew
quest, galaxy events, tutorial state machine, mining session,
death/respawn, NV skill checks, new-game happy path), the suite now
covers 19 critical paths.

Remaining candidates if the suite ever needs more breadth: salvage
session (mining session's twin), save-mid-combat fidelity, save
schema migration round-trip. Defer until a real bug points at one
of these surfaces.

#### Stream 2 — TypedDict / dataclass migration ✅ infrastructure shipped, backlog ongoing

Cookbook + scanner + first migrations all shipped:

- `requirements/si2_dataclass_migration_cookbook.md` — 1-page recipe
  for converting `list[dict]` and `dict[str, dict]` content into
  frozen dataclasses. Every migration commit references this doc.
- `tests/test_compliance/test_list_dict_content_discipline.py` —
  Scanner B catches four content-declaration shapes (annotated and
  un-annotated, list-of-dict and dict-of-dict). Empty literal
  values excluded so runtime caches don't false-positive.
  `KNOWN_ORPHANS` is the migration backlog.
- Migrations shipped (each cites the cookbook in its commit message):
  `TutorialPart` (SI-1b), `_DEFAULT_EVENT_TEMPLATES` →
  `PoliticalEventTemplate`, `MILESTONE_POOL` → `list[MiningMilestone]`,
  `TRADE_MILESTONES` → `TradeMilestone`, `TUTORIAL_STEPS` →
  `TutorialStep`, `MINIGAME_HINTS` → `dict[str, MinigameHint]`.

20 baseline orphans remain catalogued in `KNOWN_ORPHANS` (12 schema
tables in models, 2 config tier tables, 6 visual-profile tables in
engine/). Pick them off opportunistically — each migration is ~30-60
min following the cookbook recipe. Drop the allowlist line as each
table lands.

#### Stream 3 — Flag registry backfill ✅ infrastructure shipped, backlog ongoing

Cookbook + scanner + first wave all shipped:

- `requirements/si3_flag_registry_cookbook.md` — 1-page recipe for
  moving a cluster of `dialogue_flags` strings into the registry.
  Two helper shapes (parameterized helper, module constant), naming
  canonicalization rules, and the "call the helper at the access
  site" lesson (locals hide the helper from the scanner).
- Scanner A (`tests/test_compliance/test_flag_string_discipline.py`)
  auto-discovers registered prefixes by runtime-introspecting
  `spacegame/constants/flags.py` with sentinel values. Captures both
  prefix AND suffix so sandwich helpers (e.g.
  `dual_tech_<id>_revealed`) match precisely without over-flagging
  unrelated strings (e.g. `"dual_tech_moves"` attribute names).
- Integrity scanner (`tests/test_data/test_dialogue_integrity.py`)
  uses the same discovery to recognize helper-routed reads. Without
  this, every Stream 3 migration would orphan its flags from the
  audit and the allowlist would balloon.
- Helpers shipped (each in `spacegame/constants/flags.py`):
  - `tutorial_bought_part(part_id)` + `extract_tutorial_bought_part_id`
    (SI-1a — original)
  - `campaign_mission_milestone(n)` — campaign Act One milestone
    crossings (5/10/15/20)
  - `met_npc(npc_id)` — first-introduction flag for named NPCs
  - `talked_to_npc(npc_id)` — conversation-completion gates
  - `dual_tech_revealed(tech_id)` — first-use cinematic markers;
    `models/dual_tech_dialogue.reveal_flag_key` delegates to it
  - `encounter_seen(encounter_id)` — unique encounter once-only
    markers
- Latent bug fix surfaced during migration: `player.py:708` docstring
  hard-coded a flag name as an example. Rewrote to reference the
  helper so docstring drift is impossible.

Remaining clusters from the Pass 3.1 audit are lower-priority
(single-file scope, low cross-module drift risk): `seen_tip_*`,
`builder_*`, `*_tutorial_done`, `dex_favor/drifter_deal` arc. Per the
cookbook scope rule, register only when a flag crosses module
boundaries — these don't, so they stay in place. Test fixtures using
raw `talked_to_*` strings (~30 sites) were also intentionally not
migrated; Scanner A scopes to `spacegame/` only, and test-fixture
strings carry less drift risk than production. Widen Scanner A's
scope if that calculus changes.

### SI-3 — Ongoing culture / enforcement

Non-negotiable rules for all code from here forward, enforced by
scanners where possible, by discipline where not.

- **New content dicts MUST be `@dataclass(frozen=True)` (preferred)
  or `TypedDict`.** Enforced by Scanner B
  (`tests/test_compliance/test_list_dict_content_discipline.py`).
  Pattern reference: `requirements/si2_dataclass_migration_cookbook.md`.
  Scanner now catches four shapes: annotated/un-annotated list-of-dict
  and dict-of-dict declarations at module scope. Empty literals
  (runtime caches) are excluded.
- **String contracts crossing module boundaries MUST go through a
  constants module.** Enforced by Scanner A
  (`tests/test_compliance/test_flag_string_discipline.py`). Add a
  helper function in `spacegame/constants/flags.py` (or a sibling
  module) for any new shared string. Pattern reference:
  `requirements/si3_flag_registry_cookbook.md`. Scanner
  auto-discovers registered prefixes (and suffixes) by
  runtime-introspecting `flags.py` — adding a new helper
  automatically widens the scanner's reach with zero per-helper
  edits. Call the helper *at the access site*, not via a local
  variable, so the scanner can trace it.
- **Test fixtures MUST use real content types, not shadow dicts.**
  Enforced indirectly by the dataclass migration (raw dicts can't pass
  type checks); reinforced by review.
- **Bug fixes MUST grep-find-all-sites before calling done.** Commit
  messages for bug fixes note "grep'd for pattern X: N sites, all
  fixed" so it's visible and auditable.
- **QA passes MUST audit adjacent systems, not just touched code.**
  A "map adjacent surfaces" step is part of every QA sprint.

## What success looks like

- The same crash cannot recur in two different functions — scanner or
  type system catches the second site at import time.
- A test fixture that mirrors a production bug fails type-check.
- Critical-path crashes are caught in CI before a playtester sees them.
- The team can move fast on game content because the infrastructure
  underneath is solid.

## Tracking

Task IDs: SI-1a/b/c/d carry the concrete first-wave work. SI-2 and SI-3
are roadmap — scheduled between game-development sprints, opportunistic
on specific content migrations, but committed.
