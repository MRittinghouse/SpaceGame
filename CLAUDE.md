# SpaceGame (Aurelia: A Ledger of Stars)

Narrative-driven space trading RPG built with Python 3.13+, pygame-ce, and pygame_gui. Features trading, mining, salvaging, refining, skill trees, ship upgrades, and a procedurally-varied galaxy map.

## Before You Explore

**Read the architecture map first.** Before doing any broad codebase search, file exploration, or structural investigation, read the codebase architecture document in memory:

> `memory/codebase_architecture.md` (in the user's `.claude/projects/` memory directory)

It contains: layer diagrams, every module's purpose, all GameState transitions, model class summaries, data flow walkthroughs, and architectural patterns. This will save significant time and prevent redundant exploration.

## Quick Commands

```bash
python run.py                                    # Run the game (with environment checks)
python -m spacegame.main                         # Run directly
pytest                                           # Run all tests
pytest -n auto                                   # Run tests in parallel (~2x faster); 120s per-test timeout is active (override with @pytest.mark.timeout(N))
pytest tests/test_models/test_market.py           # Run a single test file
pytest --cov=spacegame --cov-report=html         # Tests with coverage report
ruff format spacegame/ tests/                    # Format code (replaces black)
ruff check spacegame/                            # Lint (<1s)
ruff check spacegame/ --fix                      # Auto-fix lint issues
mypy spacegame/                                  # Type check (raw, all errors)
python -m mypy spacegame/ | grep -v ": note:" | python -m mypy_baseline filter   # Type check against ratchet
python scripts/mypy_populations.py              # Print A/B/C population counts
python -m tools.parity.regen                     # Regenerate parity goldens (clean tree only; see Parity goldens)
python -m tools.parity.check_determinism         # Goldens byte-identical across PYTHONHASHSEED values
uv sync --extra dev                              # Install all dependencies (preferred)
pip install -e ".[dev]"                          # Install with dev dependencies (fallback)
pre-commit install                               # REQUIRED once per clone -- activates the local gate
```

### First-time setup (per clone)

```bash
uv sync --extra dev
pre-commit install          # without this, commits are completely ungated
```

`pre-commit install` is **not optional and not idempotent across clones**. `.git/hooks/` is untracked, so committing `.pre-commit-config.yaml` activates nothing — a fresh clone has no gate until this is run. This already bit once: QF-1 shipped the config and the hook was never installed, so lint, format, and type checks ran on nothing while everyone assumed the gate was live. `tests/test_compliance/test_precommit_hook_installed.py` now fails the suite if the hook is missing, so you will be told rather than left guessing.

### Type-check ratchet

`mypy-baseline.txt` records the current set of 768 known mypy errors so new errors are caught without blocking the whole project. The pre-commit hook and the `types` CI job both run `python -m mypy spacegame/ | grep -v ": note:" | python -m mypy_baseline filter`; that command exits 0 if no new errors were introduced, non-zero if any were. Note-severity lines (overload suggestions, annotation hints) are filtered before the baseline comparison because their message text varies across Python minor versions, causing spurious "new violation" alerts. Note: `set -o pipefail` is intentionally absent -- mypy exits 1 when errors exist, which would poison the pipeline; filter is the last command, so its exit code naturally propagates.

**Do not regenerate `mypy-baseline.txt` as part of a feature commit.** Regeneration is permitted only in a commit whose diff contains nothing but type annotations and None-guards (e.g., adding `Optional[X]`, fixing a return type). Regenerating during feature work silently swallows newly introduced type errors, defeating the ratchet. See `requirements/roadmap/ROADMAP.md#qf-2` and `docs/superpowers/specs/2026-08-23-quality-foundation-design.md` Section 1.

## Project Structure

```
spacegame/
  config.py         -- Constants, Colors, GameState enum, paths, game rules
  data_loader.py    -- JSON data loading singleton (get_data_loader())
  save_manager.py   -- Save/load with 12 slots, JSON serialization
  main.py           -- Entry point
  engine/           -- Game loop, state manager, input, particles, transitions, backgrounds
  models/           -- Data + logic classes (@dataclass), no rendering code
  views/            -- BaseView subclasses, one per game screen (see views/CLAUDE.md)
  utils/            -- Logger
  data/             -- Theme config (theme.json)
data/               -- JSON content files (economy/, galaxy/, progression/, ships/)
tests/              -- pytest tests mirroring spacegame/ structure
docs/               -- Player guides and feature documentation
requirements/       -- Active game design and spec documents (7 files)
requirements/archive/ -- Historical design docs and completed roadmaps
```

## Code Style

### Formatting
- **Ruff** formatter (`ruff format`), **100 character** line length (configured in pyproject.toml)
- **MyPy strict**: `disallow_untyped_defs = true` — all functions must have type hints
- Follow the **Google Python Style Guide** as baseline

### Naming
- `snake_case` — functions, methods, variables, module filenames
- `PascalCase` — classes
- `SCREAMING_SNAKE_CASE` — module-level constants
- `_leading_underscore` — private methods and attributes

### Type Hints
- Required on **all** public method signatures (parameters and return types)
- Use Python 3.13 builtins: `dict[str, int]`, `list[str]`, `tuple[bool, str]` (not `Dict`, `List`, `Tuple`)
- Use `Optional[X]` for nullable parameters and returns
- Use `TYPE_CHECKING` imports to break circular dependencies

### Docstrings (Google Style)
- **Module**: one-line summary of purpose
- **Class**: brief description of responsibility
- **Public method**: summary, then `Args:`, `Returns:`, `Raises:` sections
- **Private method**: brief one-liner is sufficient

```python
def buy_commodity(self, commodity_id: str, quantity: int,
                  price_per_unit: int) -> tuple[bool, str]:
    """Purchase commodity and add to ship cargo.

    Args:
        commodity_id: ID of commodity to buy.
        quantity: Amount to purchase.
        price_per_unit: Current market price per unit.

    Returns:
        Tuple of (success, message).
    """
```

### Comments
- Explain **why**, not what
- Use `# === SECTION NAME ===` separators for grouping in config files
- Mark future work with `TODO:` prefix

## Architecture

### Engine (spacegame/engine/)
- **Game** class initializes pygame, owns the main loop at 60 FPS
- Loop order: process input -> update UI manager -> handle state transitions -> update game state (if not paused) -> update effects -> render -> flip display
- Delta time (`dt`) in **seconds** passed to all `update()` methods
- **StateManager**: `register_state()`, `change_state()`, `push_state()`/`pop_state()` for overlays
- **TransitionManager**: visual transitions (FADE, WARP, SLIDE) with midpoint callbacks
- **ParticlePool**: object-pooled particles with `ParticleConfig` presets — no per-frame allocation
- **AnimatedBackground**: seed-based procedural starfields with 3-layer parallax

### Models (spacegame/models/)
- All models are **`@dataclass`** classes
- Models contain **data and business logic** — not just data containers
- Operations that can fail return **`tuple[bool, str]`** — (success, message)
- Serialization: `to_dict()` instance method, `from_dict()` `@classmethod`
- Use **`@property`** for computed/derived values (e.g., `ship.max_cargo`)
- Models **never** import from `views/` or `engine/` — dependency flows inward
- **Composition over inheritance**: Player has Ship, Ship has ShipType, Player has Progression

### Data Loading (spacegame/data_loader.py)
- `DataLoader` singleton — access via **`get_data_loader()`**, not `DataLoader()`
- `load_all()` reads all JSON on startup
- `_parse_<type>()` private methods convert raw dicts to model instances

### Save System (spacegame/save_manager.py)
- 12 slots (0 = autosave, 1-11 = manual)
- JSON format with `version` field for future migration
- Chain: `SaveManager` -> `Player.to_dict()` -> `Ship.to_dict()` -> `Progression.to_dict()`

## Testing

### Framework
- **pytest** — class-based tests with function-style also acceptable
- Naming: `class TestClassName:` containing `def test_behavior_description(self):`
- Helpers: `_make_<object>()` methods for creating test fixtures inline
- conftest.py at `tests/` sets `SDL_AUDIODRIVER=dummy` so pygame audio is silent during the suite. `tests/test_ui_layout/conftest.py` sets `SDL_VIDEODRIVER=dummy` and provides the resolution-matrix fixture.
- `tests/conftest.py` also holds two autouse fixtures that apply to every test (`tests/test_ralph/conftest.py` has one more for its own tests); beyond these, each test builds what it needs inline:
  - `_act_two_v1_marker`: for a test marked `act_two_v1`, sets `ACT_TWO_V1_ENABLED` to True and loads the Act II v1 registries.
  - `_reset_sim_rng_entropy`: calls `seed_entropy(None)` after every test, so a test that seeds `SimRng.from_entropy()` (directly or through `Game.seed_rngs`) cannot change the streams of later tests in the same xdist worker.

### Act II v1 (archived)
- `ACT_TWO_V1_ENABLED = False` in `spacegame/config.py` keeps the Act II v1 lens arc (tag `act2-v1-archive`) off, so the Python reference behaves as Act I only. The Godot port does not carry it. Read it as `sg_config.ACT_TWO_V1_ENABLED` so the fixture's monkeypatch takes effect.
- Tests that exercise Act II content carry the `act_two_v1` marker (`pytestmark = pytest.mark.act_two_v1` for a whole module). Without it, the flag stays off and the lens, dilemma, and capstone registries are not loaded for the test. The fixture never unloads them, so after a marked test they stay loaded on that worker's singleton; a test that needs them empty builds a fresh `DataLoader()`.

### Parity goldens (SP2, SP3)
- `parity/golden/` holds golden traces the Godot port replays; `tools/parity/` builds them. `tests/test_parity/test_goldens_current.py` fails when a committed golden or `parity/schema.json` no longer matches the code.
- After touching `spacegame/sim_rng.py`, any wave A model (player, ship, upgrades, market,
  commodity, event, galaxy, crew, progression, attributes, social, combat, encounter, captains,
  mission, procedural missions, dialogue, ambient lines, chatter, interjections), `data/`, or
  anything under `tools/parity/`: commit the code, run `python -m tools.parity.regen` from the
  clean tree, review the diff of `parity/`, and commit the goldens and schema on their own.
- regen refuses a dirty tree; `--allow-dirty` stamps `<sha>-dirty`, which the freshness test rejects.
- `python -m tools.parity.check_determinism` proves the goldens do not depend on `PYTHONHASHSEED` (the suite runs it too).

### Test-Driven Development
- **Write the failing test first** (Red), then implement (Green), then refactor
- Test both **success and failure** paths for every `tuple[bool, str]` operation
- Test edge cases: zero values, max capacity, insufficient resources, empty collections
- Verify **state changes and side effects**, not just return values

### Assertion Style
- Direct assertions with **descriptive messages**: `assert success, f"Purchase should succeed: {msg}"`
- Comparison context: `assert price > 0, f"{commodity} should have positive price"`

### What to Test
- All model methods, especially operations returning tuple[bool, str]
- Data loading and serialization round-trips (to_dict -> from_dict)
- State transitions and side effects (credits, cargo, XP changes)
- Edge cases and boundary conditions

## Data Conventions

### JSON Structure
- Top-level key is plural: `{"commodities": [...]}`, `{"systems": [...]}`
- Each item: `"id"` (snake_case), `"name"` (Title Case display name)
- All JSON keys are **snake_case**
- Economy: `production_tags` / `consumption_tags` arrays drive supply/demand
- Prices: `base_price` (int), `variance_min` / `variance_max` (float, e.g., -0.20 to 0.20)

### Adding New Content
1. Add JSON entry in the appropriate `data/` file matching existing schema
2. If new model type needed: create `@dataclass` in `models/`, add `_parse_*()` to DataLoader
3. Write tests **before** implementing model logic (TDD)
4. Add loading to `DataLoader.load_all()` if new data type

## Skill System (6 Trees)

The progression uses 6 skill trees with 89 skills and 88 bonus types. Skills are defined in `data/progression/skills.json`; `create_default_skills()` in `progression.py` builds fresh nodes from it, and the Godot port receives the same file through its `tools/sync_data.py`. `ghost_protocol` (bonus type `deception_contraband_bonus`) was designed to stack with the base `deception_bonus` only while the `contraband_present` flag is active, but nothing in `spacegame/` reads that bonus yet (finding F-13, owner SP3-c); the rule belongs in the consumer, not the skill data.

- **Trees**: Commerce, Combat, Exploration, Leadership, Social, Industry
- **Point economy**: 1 skill point per level, no cap, no milestones
- **Bonus pattern**: Every system reads bonuses via `progression.get_bonus("bonus_type_name")`
- **Prerequisites**: Tier 1 (roots) → Tier 2 (specialization) → Tier 3 (capstones)
- **Capstones**: Identity-defining skills (Juggernaut, Sentinel, Ghost, Peacemaker, etc.)

When modifying any gameplay system, check if a skill bonus should apply. Search `data/progression/skills.json` for existing bonus_types before adding new ones.

## Save Migration

Any change to model data structures MUST maintain backward compatibility:
- `from_dict()` must handle missing keys with sensible defaults
- New fields: use `data.get("new_field", default_value)`
- Renamed fields: add migration logic in `from_dict()` (see `_SKILL_MIGRATION_MAP` in `progression.py` for an example)
- Removed fields: silently ignore in `from_dict()` — don't crash on old save data
- Never change the semantics of existing serialized field names

## Gameplay Philosophy

- **Player agency**: every choice should have meaningful trade-offs
- **Risk vs. reward**: dangerous systems offer better prices and resources
- **Progression depth**: XP, skills, ship upgrades interconnect — each reinforces the others
- **Satisfying feedback**: particle effects, transitions, clear success/failure messages
- **Clarity**: the player should always understand what happened and why
- **Information asymmetry**: players learn market patterns through play; skills reveal more data
- **Deterministic outcomes**: social skill checks use threshold comparison (effective_level >= difficulty), NOT random rolls. No save scumming. Skills and investment determine success, not luck.

## Logging

```python
from spacegame.utils.logger import logger
```
- `logger.info()` — state changes, major events (save, load, level-up, state transition)
- `logger.debug()` — detailed diagnostics (mouse events, selection changes)
- `logger.warning()` — recoverable issues (missing data files, version mismatches)
- `logger.error()` — failures (save errors, data load failures)

## Narrative & Writing

- **Writing guide**: `requirements/dialogue_writing_guide.md` — 11-section Writing Bible. Read it before writing dialogue or narration.
- **Character voices**: `requirements/character_voices.md` — voice sheets for primary crew (Elena, Marcus, Priya, Tomas)
- **Cultural guide**: `requirements/cultural_guide.md` — worldbuilding bible (year 2335, Aurelia Expanse)
- **Banned NPC names**: Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose (AI-overused)
- **Anti-patterns**: No em-dashes. No "no X, no Y" constructions. No "a testament to" or "couldn't help but." These are GenAI tells.
- **Tutorial voice**: Tutorials should feel like dirty jobs and earned progressions, not hand-holding. NPCs supervise, they don't teach. The mechanic is impatient, not helpful. The shift supervisor gives orders, not lessons.
- **Flag-gated content**: Story progression uses `player.dialogue_flags` (a flat dict of string→bool). Missions, dialogues, and tutorials all gate on these flags. Cross-module flag strings go through `spacegame/constants/flags.py` — see `requirements/si3_flag_registry_cookbook.md` for the migration recipe and helper conventions.

## Cross-Cutting Concerns

When modifying a gameplay system, check these secondary impacts:

| If you change... | Also update... |
|-----------------|----------------|
| Model fields | `to_dict()`, `from_dict()`, relevant tests |
| Skill bonus_types | `data/progression/skills.json`, the system that reads it, integration test |
| GameState enum | `game.py` transition router, `_ensure_*_view()` factory, cockpit_hud context map |
| Commodity/system data | `test_cross_references.py` data validation tests |
| Dialogue flags | Use `spacegame/constants/flags.py` helpers for cross-module flags (cookbook: `requirements/si3_flag_registry_cookbook.md`); check all `dialogue_flags.get(...)` consumers |
| Module-level content tables | If declaring a `list[dict]` or `dict[str, dict]` at module scope, use `@dataclass(frozen=True)` instead — Scanner B fails the build otherwise (cookbook: `requirements/si2_dataclass_migration_cookbook.md`) |
| Ship stats | Both build-derived path AND legacy ShipType path in `build_player_combat_state()` |
| Crew abilities | `crew.py` template, `game.py` crew bonus application, combat engine crew moves |
| Tutorial flow | Shop → builder → station hub chain; check narration, completion flags, view lifecycle |
| Simulation randomness or the market model | SimRng keys (`SimRng.from_key` parts are part of the port contract), parity goldens (`python -m tools.parity.regen` from a clean tree, committed on their own), `parity/port_notes.md` |
| A formula in game.py or a view | Lift it into a model function the caller uses, and cover it with a golden driver (see `parity/port_notes.md`, SP3-a extractions) |

## Common Pitfalls

- Views **must** call `super().on_enter()` / `super().on_exit()` — these set `self.active`
- Views **must** `_destroy_ui()` on exit — call `.kill()` on all pygame_gui elements
- Models **must not** create pygame objects (Surfaces, Fonts) — that belongs in views
- Use `get_data_loader()`, not `DataLoader()` directly — it's a singleton
- Deterministic randomness: models draw only through a keyed `SimRng.from_key(...)` or an injected `rng: SimRng` (`spacegame/sim_rng.py`); the scanner `tests/test_compliance/test_no_global_random_in_models.py` enforces this. Use `stable_seed(...)`, never `hash()`, for seeds: `hash()` of a string is salted per process
- Never create Surfaces inside `update()` — create in `__init__` or `on_enter()`, reuse each frame
- Use `.convert_alpha()` on loaded images for rendering performance
- Pool particles and reuse objects — avoid GC pressure in the game loop
- Use `pytest.approx()` for float comparisons — skill bonuses accumulate floating point error
- `SocialManager()` takes no constructor args — use `sm.set_progression(prog)` after creation
- `ActionQueue.actions` returns a **copy** — don't append to it directly, use `queue.add()`
- `ShipType` has many required fields — avoid constructing in tests; use data loader or mock
- `build_player_combat_state()` has TWO code paths (build-derived vs legacy) — skill bonuses must be applied in BOTH
- Tutorial views set `_tutorial_mode = True` on the view instance, but this is NOT persisted to save files
