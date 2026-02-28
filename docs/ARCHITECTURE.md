# SpaceGame Architecture

## Module Dependency Graph

```
run.py -> spacegame/main.py -> engine/game.py
                                    |
    +-------------------------------+-------------------------------+
    |               |               |               |               |
    v               v               v               v               v
state_manager   input_handler   activity_registry   data_loader   save_manager
    |                               |               |
    v                               v               v
  views/*                       models/*          data/*.json
```

## Core Systems

### Engine Layer (`spacegame/engine/`)
- **game.py** - Main game loop, state orchestration, view lifecycle
- **state_manager.py** - View registration, state transitions, overlay stack
- **input_handler.py** - Event distribution, key/mouse callbacks
- **activity_registry.py** - Data-driven mini-game availability per system
- **particles.py** - Object-pooled particle system with ParticleConfig presets
- **transitions.py** - Screen transitions (fade, warp, slide) with midpoint callbacks
- **backgrounds.py** - Procedural parallax starfields with seed-based variation
- **screen_effects.py** - Vignette overlay and screen shake
- **procedural.py** - Cached procedural generation (planet thumbnails, etc.)

### Model Layer (`spacegame/models/`)
- **player.py** - Player state, credits, trading, progression reference, lifetime stats
- **ship.py** - Ship types, cargo management, fuel system
- **market.py** - Dynamic pricing with supply/demand and events
- **commodity.py** - Tradeable goods with categories and legality
- **system.py** - Star systems, stations, economies, coordinates
- **event.py** - Random market events (shortage, surplus, disaster, boom)
- **mining.py** - Asteroid rocks, energy system, drill mechanics
- **salvage.py** - Grid scanning, extraction, charge system
- **refining.py** - Recipes, job queue, real-time processing
- **progression.py** - XP, levels, skill trees (Trading + Gathering)
- **upgrades.py** - Ship component upgrades with slot limits
- **achievement.py** - Achievement data model (pure data container)

### Manager Layer (`spacegame/`)
- **achievement_manager.py** - Achievement checking, unlocking, and reward application
- **tutorial_manager.py** - 5-step tutorial progression with skip/replay/serialization

### View Layer (`spacegame/views/`)
- **base_view.py** - Abstract base with on_enter/on_exit/update/render
- **main_menu_view.py** - Title screen, new game, continue
- **galaxy_map_view.py** - 2D star map, travel, system info
- **trading_view.py** - Buy/sell market with dynamic activity buttons
- **mining_view.py** - Asteroid grid mini-game with drill progress
- **salvage_view.py** - Scan/extract grid puzzle
- **refining_view.py** - Recipe selection, job queue, progress bars
- **skill_tree_view.py** - Visual skill tree with clickable nodes
- **shipyard_view.py** - Upgrade shop and ship purchase with install/uninstall
- **save_load_view.py** - Save slot management with metadata display
- **settings_view.py** - Game options and preferences (includes tutorial replay)
- **pause_menu_view.py** - In-game pause with resume/save/quit/stats/achievements
- **startup_view.py** - Logo/splash screen
- **statistics_view.py** - Player stats display organized by category
- **achievements_view.py** - Achievement list with progress bars and rewards
- **event_notification_view.py** - Modal overlay for DISASTER market events
- **tutorial_overlay.py** - Lightweight tutorial step overlay (not a full BaseView)

### Data Layer (`data/`)
- `galaxy/systems.json` - 10 star systems
- `economy/commodities.json` - 19 tradeable commodities
- `economy/mining_configs.json` - Per-system mining parameters
- `economy/salvage_configs.json` - Per-system salvage parameters
- `economy/recipes.json` - 6 refining recipes
- `ships/ship_types.json` - 6 ship classes
- `ships/upgrades.json` - 5 ship upgrades
- `progression/skill_trees.json` - 10 skills across 2 trees

## Data Flow

```
Player Action -> View -> Model -> State Change
                  |                    |
                  v                    v
              UI Update          Save Manager
```

## Game States

STARTUP -> MAIN_MENU -> GALAXY_MAP <-> TRADING <-> MINING
                ^            ^    |         ^    +-> SALVAGING
                |            |    |         +------> REFINING
             SAVE/LOAD       |    +-> SKILL_TREE
             SETTINGS        +------> SHIPYARD
                             |
                          PAUSED (overlay)
```

## Future Systems (Phase 2+)

The following GameState values are reserved in `config.py` but have no corresponding views yet:
- `DIALOGUE` — NPC dialogue for campaign missions
- `MISSION_BRIEFING` — Mission acceptance and objective display

Planned future modules: campaign/mission system, crew management, faction reputation, fleet management. See `requirements/10_campaign_rpg_crew.md` and `requirements/11_implementation_roadmap.md` for design details.
