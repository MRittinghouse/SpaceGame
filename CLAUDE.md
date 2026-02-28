# SpaceGame

Narrative-driven space trading RPG built with Python 3.13+, pygame-ce, and pygame_gui. Features trading, mining, salvaging, refining, skill trees, ship upgrades, and a procedurally-varied galaxy map.

## Quick Commands

```bash
python run.py                                    # Run the game (with environment checks)
python -m spacegame.main                         # Run directly
pytest                                           # Run all tests
pytest tests/test_models/test_market.py           # Run a single test file
pytest --cov=spacegame --cov-report=html         # Tests with coverage report
black spacegame/ tests/                          # Format code
mypy spacegame/                                  # Type check
pylint spacegame/                                # Lint
pip install -e ".[dev]"                          # Install with dev dependencies
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
docs/               -- Architecture and feature design documents
requirements/       -- Game design and specification documents
```

## Code Style

### Formatting
- **Black** formatter, **100 character** line length (configured in pyproject.toml)
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

## Gameplay Philosophy

- **Player agency**: every choice should have meaningful trade-offs
- **Risk vs. reward**: dangerous systems offer better prices and resources
- **Progression depth**: XP, skills, ship upgrades interconnect — each reinforces the others
- **Satisfying feedback**: particle effects, transitions, clear success/failure messages
- **Clarity**: the player should always understand what happened and why
- **Information asymmetry**: players learn market patterns through play; skills reveal more data

## Logging

```python
from spacegame.utils.logger import logger
```
- `logger.info()` — state changes, major events (save, load, level-up, state transition)
- `logger.debug()` — detailed diagnostics (mouse events, selection changes)
- `logger.warning()` — recoverable issues (missing data files, version mismatches)
- `logger.error()` — failures (save errors, data load failures)

## Common Pitfalls

- Views **must** call `super().on_enter()` / `super().on_exit()` — these set `self.active`
- Views **must** `_destroy_ui()` on exit — call `.kill()` on all pygame_gui elements
- Models **must not** create pygame objects (Surfaces, Fonts) — that belongs in views
- Use `get_data_loader()`, not `DataLoader()` directly — it's a singleton
- Deterministic randomness: seed with `f"{game_day}_{commodity_id}_{system_id}"` for market prices
- Never create Surfaces inside `update()` — create in `__init__` or `on_enter()`, reuse each frame
- Use `.convert_alpha()` on loaded images for rendering performance
- Pool particles and reuse objects — avoid GC pressure in the game loop
