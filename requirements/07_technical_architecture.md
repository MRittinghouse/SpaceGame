# Technical Architecture Requirements

> **Implementation Status** (Updated 2026-02-27): FULLY IMPLEMENTED
>
> - **Tech stack**: Python 3.13+, pygame-ce, pygame_gui, JSON data — all as specified
> - **Architecture**: Engine/Model/View/Data layers — `spacegame/engine/`, `spacegame/models/`, `spacegame/views/`, `data/`
> - **Game loop**: 60 FPS target with delta time, state manager, transition manager
> - **Data loading**: DataLoader singleton, JSON-based content — `spacegame/data_loader.py`
> - **Save system**: JSON saves with version field, 12 slots — `spacegame/save_manager.py`
> - **Code quality**: Black (100 chars), MyPy strict, pytest, pylint — all configured in `pyproject.toml`
> - **Additions beyond spec**: Particle system (object-pooled), animated parallax backgrounds with procedural generation, screen transitions (fade/warp/slide), vignette and screen shake effects, activity registry for data-driven mini-game availability

## 1. Overview

This document defines the technical structure, design patterns, data management, and implementation guidelines for the space trading game built with PyGame.

## 2. Technology Stack

### 2.1 Core Technologies

**Programming Language:**
- **Python 3.13+** (as specified in pyproject.toml)
- Modern Python features (type hints, dataclasses, etc.)

**Game Framework:**
- **PyGame 2.5+** - Core game engine
- **pygame-gui** - UI component library (recommended)

**Data Storage:**
- **JSON** - Configuration data, save files
- **SQLite** (optional) - Persistent game state, statistics

**Build and Packaging:**
- **pyproject.toml** - Dependency management
- **pip** - Package installer
- **PyInstaller** (future) - Executable creation for distribution

### 2.2 Development Tools

**Version Control:**
- Git for source control
- GitHub/GitLab for repository hosting

**IDE/Editor:**
- PyCharm, VSCode, or similar with Python support

**Testing:**
- **pytest** - Unit testing framework
- **pygame.test** - PyGame-specific tests

**Linting/Formatting:**
- **black** - Code formatting
- **pylint/flake8** - Linting
- **mypy** - Type checking

## 3. Architecture Pattern

### 3.1 High-Level Architecture

**Pattern**: Model-View-Controller (MVC) / Entity-Component-System (ECS) Hybrid

```
┌─────────────────────────────────────────────────────┐
│                   Game Engine                       │
│  ┌───────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │   Input   │→ │  Update  │→ │     Render      │  │
│  │  Handler  │  │  Loop    │  │     System      │  │
│  └───────────┘  └──────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────┘
           ↓              ↓               ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Models     │  │  Controllers  │  │    Views     │
│  (Game Data) │  │   (Logic)     │  │ (UI/Render)  │
└──────────────┘  └──────────────┘  └──────────────┘
           ↓              ↓               ↓
    ┌──────────────────────────────────────────┐
    │         Data Layer (Save/Load)           │
    └──────────────────────────────────────────┘
```

### 3.2 Core Systems

#### Game Engine
- Main game loop
- Frame rate management (60 FPS target)
- Event handling
- State management

#### Models (Data)
- Galaxy (systems, connections)
- Markets (commodities, prices)
- Ships (definitions, player fleet)
- Player (credits, reputation, progress)

#### Controllers (Logic)
- Trading logic (buy/sell, price calculations)
- Navigation (pathfinding, travel)
- Progression (achievements, reputation)
- Economy simulation (price updates)

#### Views (UI/Rendering)
- Screen management
- UI components (buttons, lists, etc.)
- Visual effects
- Galaxy map rendering

## 4. Module Structure

### 4.1 Project Directory Layout

```
SpaceGame/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── requirements/              # Requirements documents (already created)
├── spacegame/                 # Main package
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── config.py              # Game configuration constants
│   │
│   ├── engine/                # Core engine
│   │   ├── __init__.py
│   │   ├── game.py            # Main game loop
│   │   ├── state_manager.py  # Game state management
│   │   └── event_handler.py  # Input/event handling
│   │
│   ├── models/                # Data models
│   │   ├── __init__.py
│   │   ├── galaxy.py          # Galaxy, systems, connections
│   │   ├── commodity.py       # Commodity definitions
│   │   ├── market.py          # Market data and pricing
│   │   ├── ship.py            # Ship classes and stats
│   │   ├── player.py          # Player state and progression
│   │   └── faction.py         # Faction data
│   │
│   ├── controllers/           # Game logic
│   │   ├── __init__.py
│   │   ├── trading.py         # Trading mechanics
│   │   ├── navigation.py      # Travel and pathfinding
│   │   ├── economy.py         # Price simulation
│   │   ├── progression.py     # Reputation, achievements
│   │   └── ship_manager.py    # Ship purchases/upgrades
│   │
│   ├── views/                 # UI and rendering
│   │   ├── __init__.py
│   │   ├── base_view.py       # Base view class
│   │   ├── main_menu.py       # Main menu screen
│   │   ├── galaxy_map.py      # Galaxy map view
│   │   ├── trading_view.py    # Trading interface
│   │   ├── ship_view.py       # Ship management
│   │   └── hud.py             # Heads-up display elements
│   │
│   ├── ui/                    # UI components
│   │   ├── __init__.py
│   │   ├── button.py          # Custom button widget
│   │   ├── list_view.py       # List widget
│   │   ├── modal.py           # Modal dialogs
│   │   └── tooltip.py         # Tooltip system
│   │
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── pathfinding.py     # Graph pathfinding algorithms
│   │   ├── formatter.py       # String/number formatting
│   │   └── logger.py          # Logging setup
│   │
│   └── data/                  # Game data and assets
│       ├── saves/             # Save game files
│       ├── config/            # JSON configuration files
│       │   ├── commodities.json
│       │   ├── ships.json
│       │   ├── systems.json
│       │   └── factions.json
│       ├── assets/            # Graphics and audio
│       │   ├── images/
│       │   ├── icons/
│       │   ├── fonts/
│       │   └── sounds/
│       └── localization/      # Language files (future)
│
└── tests/                     # Unit tests
    ├── __init__.py
    ├── test_trading.py
    ├── test_navigation.py
    ├── test_economy.py
    └── test_models.py
```

### 4.2 Key Module Responsibilities

#### `main.py`
- Initialize PyGame
- Load configuration
- Start game loop
- Handle top-level exceptions

#### `engine/game.py`
- Main game loop (update/render cycle)
- FPS management
- State transitions
- Event dispatch

#### `engine/state_manager.py`
- Track current game state (menu, map, trading, etc.)
- Handle state transitions
- Manage state stack (for overlays/modals)

#### `models/galaxy.py`
- Galaxy graph structure (systems and connections)
- System properties (type, faction, stations)
- Pathfinding graph representation

#### `controllers/economy.py`
- Price update simulation
- Supply/demand calculations
- Event-driven price changes
- Market restocking

#### `views/galaxy_map.py`
- Render galaxy visualization
- Handle map interactions (click, hover, zoom)
- Display system information
- Show current location and routes

## 5. Data Management

### 5.1 Data Flow

**Loading Flow:**
```
Game Start → Load Config Files (JSON) → Build Models → Initialize Controllers → Render Views
```

**Save Flow:**
```
Player Action → Update Models → Trigger Save → Serialize to JSON → Write to File
```

**Game Loop:**
```
Input Events → Controllers Update Models → Views Render from Models → Display to Screen
```

### 5.2 Configuration Data (JSON)

#### `commodities.json`
```json
{
  "commodities": [
    {
      "id": "food",
      "name": "Food & Water",
      "category": "basic",
      "base_price": 50,
      "variance_min": -0.2,
      "variance_max": 0.2,
      "volume_per_unit": 1,
      "legality": "legal",
      "production_tags": ["agricultural"],
      "consumption_tags": ["all"]
    },
    ...
  ]
}
```

#### `ships.json`
```json
{
  "ships": [
    {
      "id": "shuttle",
      "name": "Shuttle",
      "class": "starter",
      "cargo_capacity": 50,
      "fuel_capacity": 100,
      "fuel_efficiency": 10,
      "purchase_price": 5000,
      "resale_value": 3000
    },
    ...
  ]
}
```

#### `systems.json`
```json
{
  "systems": [
    {
      "id": "alpha_centauri",
      "name": "Alpha Centauri",
      "type": "trade_hub",
      "danger_level": "safe",
      "faction_id": "trade_federation",
      "connected_systems": ["sol", "proxima"],
      "position": {"x": 100, "y": 200},
      "production_tags": ["industrial"],
      "consumption_tags": ["luxury"]
    },
    ...
  ]
}
```

### 5.3 Save Data (JSON)

**Save File Structure:**
```json
{
  "version": "1.0",
  "timestamp": "2025-10-18T14:30:00",
  "player": {
    "credits": 125450,
    "current_system": "alpha_centauri",
    "current_station": "main_station",
    "ships": [
      {
        "ship_id": "medium_freighter",
        "custom_name": "Endeavor",
        "fuel_current": 180,
        "cargo": [
          {"commodity_id": "food", "quantity": 50},
          {"commodity_id": "metals", "quantity": 30}
        ],
        "upgrades": ["cargo_expansion_1", "fuel_tank_upgrade"]
      }
    ],
    "reputation": {
      "trade_federation": 67,
      "industrial_consortium": 42
    },
    "discovered_systems": ["sol", "alpha_centauri", "proxima"],
    "achievements": ["first_trade", "first_ship_purchase"],
    "statistics": {
      "trades_completed": 156,
      "jumps_traveled": 243,
      "credits_earned_lifetime": 387230
    }
  },
  "galaxy_state": {
    "systems": {
      "alpha_centauri": {
        "markets": {
          "food": {"price": 52, "supply": 450},
          "metals": {"price": 118, "supply": 320}
        }
      }
    },
    "active_events": []
  }
}
```

### 5.4 Database Option (SQLite)

**Use Case**: For more complex queries or large datasets

**Tables:**
- `player_stats` - Player progression and statistics
- `market_history` - Historical price data
- `transactions` - Trade log for analytics
- `achievements` - Achievement unlock tracking

**Pros**: Easier querying, better for analytics
**Cons**: More complexity, slower for simple reads
**Recommendation**: Start with JSON, migrate to SQLite if needed

## 6. State Management

### 6.1 Game States

**Enumeration of States:**
```python
class GameState(Enum):
    MAIN_MENU = "main_menu"
    GALAXY_MAP = "galaxy_map"
    TRADING = "trading"
    SHIP_MANAGEMENT = "ship_management"
    TRAVEL = "travel"
    PAUSE_MENU = "pause_menu"
    OPTIONS = "options"
    LOADING = "loading"
```

### 6.2 State Stack

- States can be stacked (e.g., Pause Menu over Galaxy Map)
- Top state receives input and renders
- Lower states may render in background (dimmed)

### 6.3 State Transitions

```python
# Example state transition
state_manager.push_state(GameState.TRADING)  # Open trading view
state_manager.pop_state()                    # Return to previous state
state_manager.change_state(GameState.GALAXY_MAP)  # Replace current state
```

## 7. Game Loop Architecture

### 7.1 Main Loop Structure

```python
def game_loop():
    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds

        # 1. Handle Input
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            state_manager.handle_event(event)

        # 2. Update Game State
        state_manager.update(dt)

        # 3. Render
        screen.fill(BLACK)
        state_manager.render(screen)
        pygame.display.flip()

    pygame.quit()
```

### 7.2 Delta Time (dt)

- Pass delta time to all update methods
- Ensures consistent behavior across frame rates
- Use for animations, time-based events

### 7.3 Fixed Time Step (Optional)

For deterministic physics/simulation:
```python
accumulator = 0.0
fixed_dt = 1/60.0  # 60 updates per second

while running:
    frame_time = clock.tick(60) / 1000.0
    accumulator += frame_time

    while accumulator >= fixed_dt:
        update_logic(fixed_dt)
        accumulator -= fixed_dt

    render()
```

## 8. Rendering Architecture

### 8.1 Rendering Pipeline

1. **Clear Screen** - Fill with background color
2. **Render Current State** - Call state's render method
3. **Render HUD** - Overlay persistent UI elements
4. **Render Tooltips** - Top layer, always visible
5. **Flip Display** - Update screen

### 8.2 Layered Rendering

**Layer Order (back to front):**
1. Background (starfield, etc.)
2. Main content (galaxy map, trading UI)
3. Overlays (modals, dialogs)
4. HUD (credits, fuel, cargo)
5. Tooltips and notifications

### 8.3 Dirty Rect Optimization (Optional)

- Only redraw changed regions
- Improves performance for complex scenes
- PyGame built-in support via `pygame.sprite.RenderUpdates`

### 8.4 Asset Management

**Asset Loading:**
- Load assets at startup or on-demand
- Cache in memory for reuse
- Organize by type (images, fonts, sounds)

**Asset Structure:**
```python
class AssetManager:
    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.sounds = {}

    def load_image(self, name, path):
        self.images[name] = pygame.image.load(path).convert_alpha()

    def get_image(self, name):
        return self.images.get(name)
```

## 9. Event System

### 9.1 PyGame Events

**Standard Events:**
- `QUIT` - Window close
- `KEYDOWN/KEYUP` - Keyboard input
- `MOUSEBUTTONDOWN/UP` - Mouse clicks
- `MOUSEMOTION` - Mouse movement

**Custom Events:**
```python
TRADE_COMPLETED = pygame.USEREVENT + 1
ACHIEVEMENT_UNLOCKED = pygame.USEREVENT + 2
REPUTATION_CHANGED = pygame.USEREVENT + 3

# Post custom event
pygame.event.post(pygame.event.Event(TRADE_COMPLETED, {"profit": 1500}))
```

### 9.2 Event Bus (Optional)

For decoupled communication between systems:
```python
class EventBus:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def publish(self, event_type, data):
        for callback in self.listeners.get(event_type, []):
            callback(data)
```

## 10. Performance Considerations

### 10.1 Optimization Targets

- **Frame Rate**: 60 FPS target, 30 FPS minimum
- **Load Time**: <3 seconds to main menu
- **Save/Load**: <1 second for save operations
- **Memory**: <500 MB RAM usage

### 10.2 Performance Best Practices

**Asset Caching:**
- Pre-load and cache frequently used assets
- Don't reload on every frame

**Minimize Redraws:**
- Only redraw changed elements
- Use dirty rect rendering

**Efficient Data Structures:**
- Use dictionaries for lookups (O(1))
- Pre-calculate values when possible
- Avoid nested loops in hot paths

**Profile and Measure:**
- Use cProfile to identify bottlenecks
- Monitor frame time with in-game profiler

### 10.3 Lazy Loading

- Load game data on-demand for large datasets
- Example: Load market data only when visiting system
- Balance between memory usage and load times

## 11. Error Handling and Logging

### 11.1 Error Handling Strategy

**Graceful Degradation:**
- Catch exceptions and log them
- Show user-friendly error messages
- Attempt recovery or safe shutdown

**Critical Errors:**
- Save game state before crashing
- Log full stack trace for debugging
- Notify user and offer bug report option

### 11.2 Logging Levels

```python
import logging

logging.debug("Detailed diagnostic info")
logging.info("General informational messages")
logging.warning("Warning messages for potential issues")
logging.error("Error messages for failures")
logging.critical("Critical failures")
```

**Log Output:**
- Console output during development
- File output for release builds
- Rotating log files to prevent disk fill

### 11.3 Validation

**Input Validation:**
- Validate user inputs before processing
- Check data types, ranges, and constraints
- Prevent crashes from malformed data

**Save File Validation:**
- Check save file version compatibility
- Validate JSON structure before parsing
- Handle corrupted save files gracefully

## 12. Testing Strategy

### 12.1 Unit Tests

**What to Test:**
- Model logic (price calculations, reputation changes)
- Controller functions (trading, pathfinding)
- Utility functions (formatters, validators)

**Framework**: pytest

**Example:**
```python
def test_trade_profit_calculation():
    buy_price = 100
    sell_price = 150
    quantity = 50
    profit = calculate_profit(buy_price, sell_price, quantity)
    assert profit == 2500
```

### 12.2 Integration Tests

**What to Test:**
- Save/load functionality
- State transitions
- Multi-system interactions (e.g., trading affects market)

### 12.3 Manual Testing

**Test Cases:**
- Full playthrough (start to endgame)
- Edge cases (no money, no fuel, etc.)
- UI interactions (all buttons, screens)
- Performance on target hardware

### 12.4 Test Coverage

**Goal**: 60-80% code coverage for core logic
**Tools**: pytest-cov for coverage reports

## 13. Build and Deployment

### 13.1 Development Build

**Run Locally:**
```bash
pip install -e .
python -m spacegame.main
```

### 13.2 Distribution Build

**PyInstaller** (create executable):
```bash
pyinstaller --onefile --windowed spacegame/main.py
```

**Distribute**:
- Windows: .exe
- macOS: .app bundle
- Linux: AppImage or binary

### 13.3 Version Management

**Semantic Versioning**: MAJOR.MINOR.PATCH
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

**Track in**: `pyproject.toml`, `__init__.py`

### 13.4 Configuration Management

**Environment-Specific Config:**
- `config.dev.json` - Development settings
- `config.prod.json` - Release settings
- Load based on environment flag

## 14. Extensibility and Modding (Future)

### 14.1 Modding Support

**Allow Users to Modify:**
- JSON config files (add ships, commodities, systems)
- Custom sprites/graphics
- Event scripts (Python or custom scripting language)

### 14.2 Plugin System (Post-MVP)

- Define plugin interface
- Load plugins from `mods/` directory
- Plugins can add content or modify behavior

## 15. Security Considerations

### 15.1 Save File Security

- Validate all loaded data
- Prevent code execution from save files
- Check for file tampering (optional: checksums)

### 15.2 Input Sanitization

- Sanitize all user inputs
- Prevent injection attacks (if using eval/exec)
- Validate file paths to prevent directory traversal

## 16. Documentation

### 16.1 Code Documentation

- **Docstrings**: All public functions and classes
- **Type Hints**: Use throughout codebase
- **Comments**: Explain complex logic

**Example:**
```python
def calculate_trade_profit(
    buy_price: int,
    sell_price: int,
    quantity: int,
    fees: int = 0
) -> int:
    """
    Calculate profit from a trade transaction.

    Args:
        buy_price: Price per unit when buying
        sell_price: Price per unit when selling
        quantity: Number of units traded
        fees: Additional transaction fees

    Returns:
        Total profit (can be negative for losses)
    """
    revenue = sell_price * quantity
    cost = (buy_price * quantity) + fees
    return revenue - cost
```

### 16.2 Architecture Documentation

- Keep this document updated as architecture evolves
- Diagrams for complex systems
- Decision log for major architectural choices

## 17. Open Questions and Decisions

### 17.1 Pending Decisions

- **Real-time vs. Turn-based**: How does time progress?
- **Procedural vs. Hand-crafted**: Galaxy generation approach
- **JSON vs. SQLite**: Long-term data storage
- **Custom UI vs. Library**: Full pygame-gui or hybrid?
- **Multiplayer**: Is this ever a consideration?

### 17.2 Future Enhancements

- Steam integration (achievements, cloud saves)
- Mod workshop support
- Localization for multiple languages
- Mobile port (PyGame Subset for Android)

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Next Steps**: Validate architecture with prototype implementation
