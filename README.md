# Space Trader - A Narrative-Driven Space Trading RPG

A Python-based space trading game built with PyGame, featuring economic strategy, character progression, crew management, and a compelling campaign narrative.

## Project Status

**Current Phase**: Foundation Complete (Day 1-2 ✅)

The core game engine and architecture are now in place!

## What's Been Built

### ✅ Complete Foundation
- Full project structure following best practices
- PyGame game loop with state management
- Input handling system (keyboard + mouse)
- Logging and configuration systems
- Base view/screen architecture
- Unit testing framework

### 📁 Project Structure

```
SpaceGame/
├── requirements/              # 10 comprehensive requirement documents
├── spacegame/                 # Main game package
│   ├── engine/               # Core game loop, state manager, input handler
│   ├── views/                # UI screens (startup view implemented)
│   ├── utils/                # Logging and utilities
│   ├── data/                 # Assets and save data
│   ├── config.py             # Game constants and configuration
│   └── main.py               # Entry point
└── tests/                    # Unit tests

```

### Files Created (15+ files)
- ✅ Project directory structure
- ✅ Updated pyproject.toml with dependencies
- ✅ .gitignore
- ✅ config.py (game constants, colors, game states)
- ✅ utils/logger.py (logging system)
- ✅ engine/input_handler.py (keyboard/mouse input)
- ✅ engine/state_manager.py (screen/state transitions)
- ✅ engine/game.py (main game loop)
- ✅ views/base_view.py (base class for all screens)
- ✅ views/startup_view.py (test screen with interactive demo)
- ✅ main.py (application entry point)
- ✅ tests/test_engine/test_game.py (initial unit tests)
- ✅ All __init__.py files

## Installation

### Requirements

- **Python 3.13** (Recommended) or Python 3.11-3.12
- **Note**: Python 3.14 is not yet supported by pygame

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd SpaceGame
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv .venv

   # On Windows:
   .venv\Scripts\activate

   # On Unix/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   # If you have Python 3.13:
   pip install pygame pygame-gui pytest pytest-cov black pylint mypy

   # Or install everything:
   pip install -e ".[dev]"
   ```

## Running the Game

### Method 1: Using the Launcher (Easiest)

**Windows:**
```bash
# Double-click run.bat, or from terminal:
run.bat
```

**Any Platform:**
```bash
python run.py
```

### Method 2: Run as Module (Recommended)

From the **project root directory** (SpaceGame/):

```bash
# With virtual environment
.venv\Scripts\python.exe -m spacegame.main

# Or if venv is activated
python -m spacegame.main
```

### Method 3: Install Package First

```bash
pip install -e .
python -m spacegame.main
```

**⚠️ Important**: Don't run `spacegame/main.py` directly! Always run from the project root using one of the methods above.

**✅ You should see:**
- A 1280x720 window titled "Space Trader"
- "SPACE TRADER" title in bright blue
- "PyGame Foundation Test" screen
- Mouse position tracking (updates in real-time)
- Click counter
- Smooth 60 FPS rendering
- Press ESC to quit

**Status**: ✅ **WORKING** - Game successfully runs on Python 3.13!

## Running Tests

```bash
pytest tests/ -v
```

With coverage:
```bash
pytest --cov=spacegame --cov-report=html tests/
```

## Code Quality Tools

```bash
# Format code
black spacegame/

# Lint
pylint spacegame/

# Type checking
mypy spacegame/
```

## What's Next

### Immediate Next Steps (Days 3-5):
1. **Data Layer** - Create JSON files for galaxies, commodities, and ships
2. **Galaxy Map View** - Simple node-based star system visualization
3. **Basic Navigation** - Travel between systems
4. **Market Data Models** - Commodity and pricing structures

### Phase 1 Goals (Weeks 2-4):
- Complete trading MVP (galaxy map, market interface, player state)
- Save/load functionality
- Playable trading game loop

### Phase 2 Goals (Weeks 5-8):
- Character progression (captain skills)
- Crew system (3-5 initial crew members)
- Simple campaign (Act I story missions)

## Requirements Documents

Comprehensive design documents are available in the `requirements/` folder:

1. **Game Design Document** - Core gameplay vision and pillars
2. **Economic System** - Trading mechanics and market simulation
3. **Galaxy Map** - Star systems, travel, and exploration
4. **Ships & Fleet** - Ship types, progression, and crew positions
5. **Player Progression** - Character skills, XP, and advancement
6. **UI/UX** - Screen layouts and interaction patterns
7. **Technical Architecture** - Code structure and implementation
8. **Content Requirements** - Specific game content (15 systems, 12 commodities, crew)
9. **Coding Principles** - OOP, TDD, SOLID, Clean Code standards
10. **Campaign, RPG & Crew** - Story structure, character progression, crew management

## Contributing

This project follows:
- **Test-Driven Development** (TDD)
- **SOLID Principles**
- **Clean Code** practices
- **Object-Oriented Programming**

See [requirements/09_coding_principles.md](requirements/09_coding_principles.md) for detailed standards.

## Architecture Highlights

### Game Loop (60 FPS)
```python
while running:
    dt = clock.tick(60) / 1000.0
    handle_input(events)
    update(dt)
    render(screen)
```

### State Management
- Clean state transitions (Menu → Galaxy Map → Trading → etc.)
- Stack-based overlays for pause menus and modals
- Each state is self-contained (update/render methods)

### Input Handling
- Centralized event processing
- Callback system for custom key bindings
- Mouse and keyboard support

## License

[To be determined]

## Credits

Built with:
- **PyGame** - 2D game framework
- **pygame-gui** - UI components
- **Python 3.13+** - Programming language

---

**Game Design Philosophy**: "Trading First, Story Enhances"
- Core gameplay: Space trading simulation
- RPG layer: Character progression and crew management
- Narrative: Campaign that complements (not replaces) trading

**Status**: Foundation complete ✅ | Ready for core gameplay development 🚀
