#### A2-1 — Lens data model and registry

**Status**: todo
**Phase**: Act II | **Size**: M | **Effort**: 1 week
**Depends on**: none | **Blocks**: A2-4, A2-5, A2-6, A2-7

**Goal.** Build the data model that makes an ambition addable as data rather than code. A lens is a *reading* of the shared world, not a questline, so the registry holds declarations and the world stays single. This is the foundation the entire Act II arc consumes.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` (the sixteen lenses table)
- `docs/superpowers/specs/2026-08-27-act-two-decomposition.md`
- `spacegame/data_loader.py` (singleton pattern, `_parse_*` conventions)
- `spacegame/models/progression.py` (an existing model with registry-shaped data)
- `tests/test_compliance/test_findings_register.py` (the data-integrity guard pattern to copy)

**Touch zones.**
- `spacegame/models/lens.py` (NEW)
- `data/narrative/lenses.json` (NEW — directory is new; existing siblings are `data/economy/`, `data/galaxy/`, `data/progression/`, `data/ships/`)
- `spacegame/data_loader.py` (add `_parse_lenses()`, register in `load_all()`)
- `tests/test_models/test_lens.py` (NEW)
- `tests/test_compliance/test_lens_registry.py` (NEW)

**Deliverables.**
- `Lens` as a frozen `@dataclass`: `lens_id`, `name`, `core_fantasy`, `question`, `minigame_shape`.
- JSON-backed registry loaded through `get_data_loader()`, following the existing singleton access rule.
- `to_dict()` / `from_dict()` round-trip.
- A data-integrity test that fails the build on a malformed or incomplete lens.

**Acceptance criteria.**
1. A new lens can be added to `data/narrative/lenses.json` and appears in the registry with **no Python change**. A test proves this by adding a fixture lens and asserting it loads.
2. `minigame_shape` is REQUIRED. A lens missing it fails the build with a message naming the offending `lens_id`. This field is what stops a later lens shipping as a reskin of another, so its absence must be loud.
3. Round-trip `to_dict()` → `from_dict()` preserves every field.
4. Duplicate `lens_id` values fail the build rather than silently overwriting.
5. Loading is exercised through `get_data_loader()`, not by constructing `DataLoader()` directly.
6. 15+ new tests.

**Activity log.**
- 2026-08-27 — todo (created)

#### A2-2 — Lens authoring guide

**Status**: todo
**Phase**: Act II | **Size**: S | **Effort**: 3 days
**Depends on**: none | **Blocks**: none

**Goal.** Extend the writing bible so later content sprints author lenses consistently instead of each inventing its own conventions. Documentation only, no code. It depends on nothing and can run immediately.

**Context to read.**
- `requirements/dialogue_writing_guide.md` (the existing 11-section Writing Bible)
- `requirements/character_voices.md`
- `requirements/cultural_guide.md` (year 2335, the Aurelia Expanse)
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md`

**Touch zones.**
- `requirements/lens_authoring_guide.md` (NEW)

**Deliverables.**
- Per-lens voice notes for all sixteen: what a character who reads the world this way sounds like.
- NPC construction patterns per lens, including how a scar NPC (one who refused the player) differs from a hostile one.
- How an authored location takes a per-lens reading without becoming sixteen locations.
- Worked examples: one location read through three different lenses.
- A written warning against the failure mode the spec names, sixteen shallow reskins, with concrete tells to check for.

**Acceptance criteria.**
1. Every one of the sixteen lenses has voice notes and at least one NPC pattern.
2. The worked example shows one location under three lenses, with text that could not be swapped between them.
3. No banned NPC names appear (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose).
4. No em-dashes, no "no X, no Y" constructions, per the project's anti-GenAI writing rules.
5. A compliance test asserts the guide covers all sixteen `lens_id` values once A2-1's registry exists, or is skipped cleanly if it does not.

**Activity log.**
- 2026-08-27 — todo (created)

#### A2-3 — Capstone format and hook contract

**Status**: todo
**Phase**: Act II | **Size**: S | **Effort**: 3 days
**Depends on**: none | **Blocks**: A2-20

**Goal.** Define what a capstone IS as data and where it fires, without authoring any capstone content. Aurelia has no hard ending, so a capstone is punctuation rather than a terminus and the contract must make continuing play the default rather than an afterthought.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` ("Endings are capstones, and the game does not stop")
- `spacegame/engine/transitions.py` (existing cutscene and transition hooks)
- `spacegame/config.py` (`GameState` enum)

**Touch zones.**
- `spacegame/models/capstone.py` (NEW)
- `data/narrative/capstones.json` (NEW, schema plus one fixture entry only)
- `tests/test_models/test_capstone.py` (NEW)

**Deliverables.**
- `Capstone` dataclass: `capstone_id`, `lens_id`, `trigger_condition`, `cutscene_ref`.
- The hook contract: what the engine calls, what it passes, and what it guarantees afterward.
- An explicit statement in the module docstring that firing a capstone MUST NOT end the session.
- One fixture capstone for tests. No authored narrative content.

**Acceptance criteria.**
1. The contract states, in code and in tests, that play continues after a capstone fires.
2. A capstone declares exactly one `lens_id` and a test rejects one that declares none or several.
3. `cutscene_ref` may be null so the format is usable before any cutscene exists.
4. Schema round-trips through save/load.
5. 10+ new tests.

**Activity log.**
- 2026-08-27 — todo (created)

#### A2-4 — Per-lens investment tracking

**Status**: todo
**Phase**: Act II | **Size**: L | **Effort**: 1-2 weeks
**Depends on**: A2-1 | **Blocks**: A2-8

**Goal.** Track how far the player has invested in each lens, persist it, and expose it to the dilemma engine. Investment is what makes a collision possible, so this is the load-bearing state for the whole arc.

**Context to read.**
- `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md` (success criteria 3 and 6)
- `docs/superpowers/specs/2026-08-27-act-two-decomposition.md` (the resolved Q1: investment is fully oblique)
- `spacegame/models/player.py`
- `spacegame/models/progression.py` (bonus accumulation patterns)
- `spacegame/save_manager.py`

**Touch zones.**
- `spacegame/models/lens_investment.py` (NEW)
- `spacegame/models/player.py` (investment state field)
- `spacegame/save_manager.py`
- `tests/test_models/test_lens_investment.py` (NEW)
- `tests/test_scenarios/test_scenario_investment_persists.py` (NEW)

**Deliverables.**
- Per-lens investment accumulation keyed by `lens_id`.
- Save/load round-trip preserving all sixteen values.
- A query API the dilemma engine consumes: current investment for a lens, and whether it exceeds a given threshold.
- Backward-compatible `from_dict()` that defaults missing lens keys to zero, per the project's save-migration rules.

**Acceptance criteria.**
1. Investment accrues from player action and is readable per lens.
2. Save, reload, and confirm every value survives exactly.
3. An older save with no investment data loads without crashing, defaulting to zero for every lens.
4. **Investment is NEVER rendered as a meter, bar, or numeric panel.** This is a binding design decision. A compliance test asserts no UI surface exposes a raw investment number.
5. Criterion 3 of the spec is satisfied obliquely and testably: a scenario test drives one lens high and asserts that NPC address and offered work measurably change. The assertion is on world behaviour, not on the existence of a UI element.
6. Adding a seventeenth lens to the registry requires no change here.
7. 25+ new tests.

**Activity log.**
- 2026-08-27 — todo (created)
