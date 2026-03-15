# Space Trader — A Narrative-Driven Space Trading RPG

A single-player space trading RPG set in the Aurelia Expanse, year 2335. Trade commodities across star systems, build your ship, recruit crew, navigate faction politics, and uncover a conspiracy that threatens the frontier.

Built with Python, pygame-ce, and pygame_gui.

## Playing the Game

### Option A: Standalone Build (Recommended for Playtesters)

No Python required. Download the latest build and run:

```
dist/SpaceGame/SpaceGame.exe
```

Double-click `SpaceGame.exe` and play. Save files are stored in `%APPDATA%/SpaceGame/saves/`.

### Option B: Install from Source (Windows)

1. Install [Python 3.13+](https://www.python.org/downloads/) — check **"Add Python to PATH"** during install
2. Double-click **`install.bat`** — creates a virtual environment and installs dependencies
3. Double-click **`play.bat`** to launch

### Option C: Manual Setup

```bash
git clone <repo-url>
cd SpaceGame
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -e .
python -m spacegame.main
```

## Controls

| Key | Action |
|-----|--------|
| Mouse | Navigate menus, click buttons, select items |
| Arrow keys | Navigate lists and skill trees |
| Escape | Back / Cancel |
| Number keys | Quick-select dialogue options |

## Game Overview

You start with a Shuttle and a handful of credits at Nexus Prime. From there, the galaxy is yours.

### Core Systems

- **Trading** — Buy low, sell high across 11 star systems. Each system produces and consumes different commodities. 27 trade goods with dynamic pricing.
- **Combat** — Turn-based tactical combat with energy management, weapons, shields, and special moves. 28 enemy templates from pirates to military patrols.
- **Mining & Salvage** — Grid-based mini-games for extracting ore and scavenging wrecks. Refine raw materials into valuable goods.
- **Crew** — Recruit up to 17 unique NPCs with their own personalities and skill bonuses. Assign them to roles, manage loyalty, build relationships.
- **Progression** — Uncapped leveling with 9 skill trees (63 skills). Milestone bonus points every 5 levels. Specialize in trading, combat, exploration, smuggling, and more.
- **Ships** — 24 ships across 5 tiers from a tin-can Shuttle to faction prestige vessels. Each ship is a statement of intent with distinct trade-offs.
- **Upgrades** — 40 upgrades with a Mk1-Mk3 enhancement system. At Mk2, choose a tuning specialization that defines your build identity.
- **Campaign** — 22 story missions across Act One. Faction politics, ground exploration, dialogue choices that matter.
- **Ground Exploration** — Tile-based exploration of planetary surfaces with encounters, hazards, and discoveries.

### Ships & Progression

Your ship defines your role:

| Path | Early Ship | Late Ship | Key Trait |
|------|-----------|-----------|-----------|
| Trade | Light Freighter | Bulk Hauler | Max cargo capacity |
| Combat | Patrol Cutter | War Frigate | 4 weapon + 3 defense slots |
| Exploration | Scout Vessel | Deep Explorer | 500 fuel, 5 utility slots |
| Mining | Prospector | Industrial Titan | 6 utility slots, 0 weapons |
| Smuggling | Smuggler's Sloop | Phantom | Fastest ship (2.2x), stealth |
| Diplomacy | — | Diplomatic Cruiser | 6 crew, rep bonus |

Four **faction ships** reward deep reputation with unique abilities like tariff immunity, hull regeneration, double salvage yields, and quantum sensors.

### Enhancement System

Every upgrade can be enhanced from Mk1 to Mk3:

- **Mk1** — Base stats (purchase price)
- **Mk2** — +25% effectiveness, choose a tuning specialization (+100% base price)
- **Mk3** — +50% effectiveness, tuning bonus doubles (+200% base price)

Two players with the same Laser Cannon can have completely different builds: one overcharged for raw damage, another precision-tuned to never miss.

## For Developers

### Requirements

- Python 3.13+
- pygame-ce 2.5+
- pygame_gui 0.6.9+

### Dev Setup

```bash
pip install -e ".[dev]"    # Includes pytest, black, mypy, pylint, pyinstaller
```

### Quick Commands

```bash
python -m spacegame.main                    # Run the game
pytest                                      # Run all tests (3415+)
pytest tests/test_models/test_market.py     # Run a single test file
black spacegame/ tests/                     # Format code
mypy spacegame/                             # Type check
```

### Building a Standalone Executable

```bash
python -m PyInstaller spacegame.spec --noconfirm
```

Output: `dist/SpaceGame/SpaceGame.exe` (~340MB with all assets)

### Project Structure

```
SpaceGame/
  spacegame/              # Main game package
    config.py             # Constants, colors, game state enum, paths
    data_loader.py        # JSON data loading singleton
    save_manager.py       # Save/load with 12 slots
    main.py               # Entry point
    engine/               # Game loop, state manager, particles, transitions, audio
    models/               # Data + logic (@dataclass), no rendering code
    views/                # 34 BaseView subclasses, one per game screen
    utils/                # Logger
    data/                 # Theme config, assets (sprites, audio)
  data/                   # JSON content files (economy, galaxy, ships, progression)
  tests/                  # pytest tests mirroring spacegame/ structure
  requirements/           # Game design and spec documents
  spacegame.spec          # PyInstaller build config
  install.bat             # Automated installer for from-source players
  play.bat                # Quick launcher (after install.bat)
```

### Architecture

- **TDD**: Tests written first, 3415+ tests covering models, data, views
- **Models**: `@dataclass` classes with business logic, `tuple[bool, str]` for failable ops
- **Views**: Strict `BaseView` lifecycle with `_create_ui`/`_destroy_ui` pairing
- **Data-driven**: All game content is JSON files in `data/`, not hardcoded
- **Composition over inheritance**: Player has Ship, Ship has ShipType, Player has Progression

See `CLAUDE.md` for comprehensive architecture and coding conventions.

### Content Stats

| Category | Count |
|----------|-------|
| Tests | 3,415+ |
| Views | 34 |
| Ships | 24 (5 tiers) |
| Upgrades | 40 (with tuning) |
| Commodities | 27 |
| Skill Trees | 9 (63 skills) |
| Story Missions | 22 |
| NPCs | 17 |
| Enemy Templates | 28 |
| Star Systems | 11 |
| Factions | 4 + Crimson Reach |

## Credits

Built with [pygame-ce](https://pyga.me/), [pygame_gui](https://pygame-gui.readthedocs.io/), and Python 3.13+.

## License

[To be determined]
