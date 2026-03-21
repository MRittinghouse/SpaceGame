# Space Trader

A broke orphan, a broken shuttle, and a galaxy full of secrets.

Space Trader is a narrative-driven space trading RPG set in the Aurelia Expanse, a remote frontier cluster in the year 2335. Start from nothing at Nexus Prime and build your way up: run trade routes, dodge pirates, recruit a crew, pick sides in faction politics, and pull the thread on a conspiracy that could unravel the entire sector.

Built with Python, pygame-ce, and pygame_gui.

## Playing the Game

### Option A: Standalone Build (No Python Required)

Download the latest release and run `SpaceGame.exe`. Save files are stored in `%APPDATA%/SpaceGame/saves/`.

### Option B: Install from Source (Windows)

1. Install [Python 3.13+](https://www.python.org/downloads/) (check **"Add Python to PATH"** during install)
2. Double-click **`install.bat`** to create a virtual environment and install dependencies
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

The game includes a built-in tutorial that walks you through core systems as you encounter them.

## What You Can Do

**Trade.** Buy low, sell high across 11 star systems. Each system has its own regional market shaped by what it produces and consumes. Learn the patterns, find the margins, exploit the events.

**Fight.** Turn-based tactical combat with energy management, weapon loadouts, shields, and special abilities. Pirates, military patrols, and worse are out there.

**Mine, salvage, and refine.** Grid-based mini-games let you crack asteroids for ore and scavenge wrecks for parts. Back at the station, refine raw materials into valuable goods using recipes you discover along the way.

**Smuggle.** High risk, high reward. Run contraband past inspections, manage your criminal heat, find black market contacts, and install hidden compartments. Just don't get caught.

**Build your ship.** 24 ships across 5 tiers, from a tin-can Shuttle to faction prestige vessels. Every ship has a distinct identity: slot layouts, speed, cargo capacity, and fuel range define your playstyle. Outfit it with upgrades that can be enhanced from Mk1 to Mk3, with tuning specializations at Mk2 that let you shape your build.

**Grow your crew.** Recruit companions and specialists, each with their own personality, skill bonuses, and personal quest arcs. Assign them to roles on your ship and build loyalty over time.

**Pick sides.** Four factions vie for influence in the Expanse. Your reputation with each unlocks perks, gated content, and faction-exclusive ships, but getting close to one may cost you standing with another.

**Follow the story.** A 22-mission campaign across Act One, plus side missions and crew quests. Dialogue choices matter. The world reacts. The conspiracy at the center of it all has a name, but you won't learn it until you're already in too deep.

**Explore on foot.** Tile-based ground missions with stealth mechanics, ground combat, hazards, and discoveries. Some things can only be found by leaving the cockpit.

### Ships and Progression

Your ship defines your role:

| Path | Early Ship | Late Ship | Key Trait |
|------|-----------|-----------|-----------|
| Trade | Light Freighter | Bulk Hauler | Max cargo capacity |
| Combat | Patrol Cutter | War Frigate | 4 weapon + 3 defense slots |
| Exploration | Scout Vessel | Deep Explorer | 500 fuel, 5 utility slots |
| Mining | Prospector | Industrial Titan | 6 utility slots, 0 weapons |
| Smuggling | Smuggler's Sloop | Phantom | Fastest ship (2.2x), stealth |
| Diplomacy | Courier | Diplomatic Cruiser | 6 crew, rep bonus |

Four **faction ships** reward deep reputation with unique abilities: tariff immunity, hull regeneration, double salvage yields, and quantum sensors.

Your captain levels up with uncapped progression across 9 skill trees. Every 5 levels you earn milestone bonus points. Specialize in trading, combat, exploration, mining, smuggling, diplomacy, salvage, leadership, or social skills.

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
pytest                                      # Run all tests (4,649+)
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
  requirements/           # Active game design and spec documents
  requirements/archive/   # Historical design docs and completed roadmaps
  docs/                   # Player guides and feature documentation
  tools/                  # Asset generation scripts (sprites, audio)
```

### Architecture

- **TDD**: Tests written first, 4,649+ tests covering models, data, views
- **Models**: `@dataclass` classes with business logic, `tuple[bool, str]` for failable ops
- **Views**: Strict `BaseView` lifecycle with `_create_ui`/`_destroy_ui` pairing
- **Data-driven**: All game content is JSON files in `data/`, not hardcoded
- **Composition over inheritance**: Player has Ship, Ship has ShipType, Player has Progression

See `CLAUDE.md` for comprehensive architecture and coding conventions.

### Content Stats

| Category | Count |
|----------|-------|
| Tests | 4,649+ |
| Views | 34 |
| Ships | 24 (5 tiers) |
| Upgrades | 58 (Mk1-Mk3 tiered) |
| Commodities | 60 |
| Refining Recipes | 38 (21 base + 17 advanced) |
| Random Encounters | 131 (11 types) |
| Skill Trees | 9 (89 skills, 175 points) |
| Achievements | 62 |
| Campaign Missions | 22 |
| Side Missions | 21 |
| Crew Quests | 12 |
| NPCs | 31 |
| Crew Members | 19 (4 companions + 15 specialists) |
| Dialogue Trees | 45 |
| Enemy Templates | 28 |
| Star Systems | 11 (regional markets) |
| Factions | 4 + Crimson Reach |
| Faction Perks | 12 |
| Galaxy Events | 5 types, 18 templates |

## Credits

Built with [pygame-ce](https://pyga.me/), [pygame_gui](https://pygame-gui.readthedocs.io/), and Python 3.13+.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE). You are free to use, modify, and distribute this software under the terms of the GPL. See the LICENSE file for details.
