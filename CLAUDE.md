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
pytest -n auto                                   # Run tests in parallel (~2x faster)
pytest tests/test_models/test_market.py           # Run a single test file
pytest --cov=spacegame --cov-report=html         # Tests with coverage report
ruff format spacegame/ tests/                    # Format code (replaces black)
ruff check spacegame/                            # Lint (<1s)
ruff check spacegame/ --fix                      # Auto-fix lint issues
mypy spacegame/                                  # Type check
uv sync --extra dev                              # Install all dependencies (preferred)
pip install -e ".[dev]"                          # Install with dev dependencies (fallback)
```

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
- No conftest.py / shared fixtures currently — each test is self-contained

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

The progression uses 6 skill trees with 75 total skills. Skills are defined in Python code (`create_default_skills()` in `progression.py`), NOT in JSON. The old `data/progression/skill_trees.json` was removed.

- **Trees**: Commerce, Combat, Exploration, Leadership, Social, Industry
- **Point economy**: 1 skill point per level, no cap, no milestones
- **Bonus pattern**: Every system reads bonuses via `progression.get_bonus("bonus_type_name")`
- **Prerequisites**: Tier 1 (roots) → Tier 2 (specialization) → Tier 3 (capstones)
- **Capstones**: Identity-defining skills (Juggernaut, Sentinel, Ghost, Peacemaker, etc.)

When modifying any gameplay system, check if a skill bonus should apply. Search `create_default_skills()` for existing bonus_types before adding new ones.

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
| Skill bonus_types | `create_default_skills()`, the system that reads it, integration test |
| GameState enum | `game.py` transition router, `_ensure_*_view()` factory, cockpit_hud context map |
| Commodity/system data | `test_cross_references.py` data validation tests |
| Dialogue flags | Use `spacegame/constants/flags.py` helpers for cross-module flags (cookbook: `requirements/si3_flag_registry_cookbook.md`); check all `dialogue_flags.get(...)` consumers |
| Module-level content tables | If declaring a `list[dict]` or `dict[str, dict]` at module scope, use `@dataclass(frozen=True)` instead — Scanner B fails the build otherwise (cookbook: `requirements/si2_dataclass_migration_cookbook.md`) |
| Ship stats | Both build-derived path AND legacy ShipType path in `build_player_combat_state()` |
| Crew abilities | `crew.py` template, `game.py` crew bonus application, combat engine crew moves |
| Tutorial flow | Shop → builder → station hub chain; check narration, completion flags, view lifecycle |

## Common Pitfalls

- Views **must** call `super().on_enter()` / `super().on_exit()` — these set `self.active`
- Views **must** `_destroy_ui()` on exit — call `.kill()` on all pygame_gui elements
- Models **must not** create pygame objects (Surfaces, Fonts) — that belongs in views
- Use `get_data_loader()`, not `DataLoader()` directly — it's a singleton
- Deterministic randomness: seed with `f"{game_day}_{commodity_id}_{system_id}"` for market prices
- Never create Surfaces inside `update()` — create in `__init__` or `on_enter()`, reuse each frame
- Use `.convert_alpha()` on loaded images for rendering performance
- Pool particles and reuse objects — avoid GC pressure in the game loop
- Use `pytest.approx()` for float comparisons — skill bonuses accumulate floating point error
- `SocialManager()` takes no constructor args — use `sm.set_progression(prog)` after creation
- `ActionQueue.actions` returns a **copy** — don't append to it directly, use `queue.add()`
- `ShipType` has many required fields — avoid constructing in tests; use data loader or mock
- `build_player_combat_state()` has TWO code paths (build-derived vs legacy) — skill bonuses must be applied in BOTH
- Tutorial views set `_tutorial_mode = True` on the view instance, but this is NOT persisted to save files
