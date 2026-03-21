# SpaceGame: Game Systems Reference

> Current as of March 2026. For historical design documents, see requirements/archive/

Narrative-driven space trading RPG built with Python 3.13+, pygame-ce, and pygame_gui. Single-player. Set in the Aurelia Expanse, year 2335.

**Content at a glance**: 4,649 tests, 34 views, 55 missions, 31 NPCs, 45 dialogues, 131 random encounters, 28 enemy templates, 24 player ships, 60 commodities, 58 upgrades, 9 skill trees, 62 achievements, 19 crew members, 11 star systems, 4 factions + Crimson Reach.

---

## 1. Core Gameplay Loop

The player commands a single ship through the Aurelia Expanse, trading commodities, completing missions, recruiting crew, and advancing a campaign narrative.

**Primary loop (trading cycle):**
1. Survey market prices across accessible systems
2. Plan routes considering cargo capacity, fuel, and risk
3. Travel between systems (turn-based, fuel cost based on distance)
4. Trade: buy low, sell high
5. Invest profits in ship upgrades, new ships, or skill progression

**Secondary loop (RPG/narrative):**
1. Accept and complete campaign, side, or crew missions
2. Develop captain skills across 9 skill trees
3. Recruit and manage crew members
4. Engage in dialogue with NPCs, make narrative choices
5. Build faction reputation for perks and gated content

Both loops interweave: story missions require cargo deliveries, crew provide trading bonuses, skills improve economic efficiency, and faction standing unlocks markets and ships.

---

## 2. Setting and Worldbuilding

**Year**: 2335 CE. **Location**: The Aurelia Expanse, a remote 10-system cluster.

The Expanse was settled by the colony ship *Aurelia*, a late-wave refugee vessel carrying ~12,000 passengers from 43 nations. After 140 years of independent development, four factions have emerged from blended Earth cultures. The setting avoids geographic-bloc factions; each faction is culturally mixed.

Full worldbuilding details: `requirements/cultural_guide.md`

---

## 3. Economy and Trading

### Currency
- **Credits (CR)**: integer-based universal currency
- Starting capital: 5,000 CR
- Formatted with thousand separators, color-coded (green for gains, red for losses)

### Commodities (60 total)
Organized across basic, industrial, luxury, and refined categories. Each commodity has:
- Base price, variance range (min/max percentage)
- Volume per unit (cargo space consumed)
- Legality status (legal, restricted, illegal)
- Production/consumption tags driving supply and demand per system

### Regional Markets (11 systems)
Each system has economic tags (production/consumption) that create natural trade routes. Systems that produce a commodity sell it cheaply; systems that consume it pay a premium.

### Pricing Model
```
current_price = base_price * (1 + supply_demand_modifier + random_variance + event_modifier)
```
- Random variance: seeded deterministically per game day, commodity, and system
- Market events: shortage (+40%), surplus (-30%), disaster, boom
- Galaxy events (5 types, 18 templates, 1 chain) affect prices region-wide

### Trading Mechanics
- Buy/sell interface with cargo volume management
- Price comparison to galactic average
- Trend indicators (rising/falling/stable)
- Supply limits per station prevent infinite exploits
- Transaction confirmation with cost/revenue preview

### Smuggling
Illegal goods can be traded through black markets. Higher risk, higher reward. Detection chance, fines, and confiscation if caught. Smuggling skill tree reduces detection and penalties.

---

## 4. Galaxy and Navigation

### Structure
- 11 star systems with 2D coordinates (Euclidean distance model)
- System types: trade hub, agricultural, industrial, mining, research, frontier
- Each system has stations with docking fees, market variety, and available services

### Travel
- Turn-based: each jump consumes fuel based on distance and ship efficiency
- Fuel is a managed resource; running out strands the player
- Random encounters can trigger during travel (131 encounters across 11 types)

### Galaxy Map View
- 2D interactive map with system nodes, connection lines, faction color coding
- Current location pulsing indicator
- Click to select, hover for info tooltip
- System detail panel shows stations, faction control, danger level, fuel cost estimate

---

## 5. Ships and Upgrades

Full spec: `requirements/17_ships_and_upgrades.md`

### Ships (24 total)

Organized into five tiers, each with meaningful trade-offs:

| Tier | Count | Examples |
|------|-------|---------|
| Starter | 1 | Shuttle |
| Early Game | 3 | Light Freighter, Prospector, Patrol Cutter |
| Mid Game | 8 | Medium Freighter, Fast Courier, Corsair, Mining Barge, Smuggler's Sloop |
| Late Game | 8 | Bulk Hauler, War Frigate, Phantom, Industrial Titan, Diplomatic Cruiser |
| Faction | 4 | Consortium Merchantman, Syndicate Enforcer, Frontier Runner, Institute Vessel |

**Key ship attributes**: cargo capacity, fuel capacity, fuel efficiency, hull HP, shields, weapon/defense/utility slots, speed multiplier, purchase price, special abilities.

Faction ships require Allied reputation (50+) with the corresponding faction and are only available at that faction's home station.

### Upgrades (58 total)

Categories: weapons, defenses, utility (cargo, fuel, mining, scanner, smuggling). Each ship has a fixed number of weapon, defense, and utility slots.

**Mark Enhancement System**: upgrades can be enhanced from Mk1 (base) to Mk3 (mastered).
- Mk2: +25% effectiveness, choose one of two tuning specializations
- Mk3: +50% effectiveness, tuning bonus doubles
- Enhancement costs credits plus specific commodities

**Tuning examples**: a Laser Cannon can be tuned "Overcharged" (+damage) or "Precision" (+accuracy). A Cargo Bay Extension can be "Reinforced" (+hull HP) or "Optimized" (+cargo).

Faction-locked upgrades (4) require reputation. Quest-unlocked upgrades (3) require specific mission completion.

### Ship Purchase
- Shipyard at eligible stations shows available ships filtered by faction reputation
- Side-by-side stat comparison with current ship
- Trade-in value system (resale percentage of purchase price)

---

## 6. Player Progression

### Leveling
- Uncapped leveling system with formula-based XP thresholds
- Milestone skill points every 5 levels
- XP from: trading, missions, discoveries, combat, mini-games

### Character Attributes (5)
Five core attributes that provide passive bonuses and gate certain dialogue/mission options.

### Skill Trees (9 trees, 89 skills, 175 total points)

| Tree | Focus |
|------|-------|
| Trading Mastery | Economic efficiency, profit maximization |
| Resource Gathering | Mining and salvage bonuses |
| Leadership | Crew effectiveness, fleet prep |
| Combat | Weapon damage, defense, tactics |
| Exploration | Travel efficiency, discovery rewards |
| Smuggling | Evasion, hidden cargo, black market access |
| Social | Dialogue options, reputation gains, NPC relationships |
| Ground Operations | Ground exploration combat and survival |
| Refining | Recipe efficiency, advanced recipe access |

Players cannot max all trees, forcing meaningful specialization choices. Respec available at major stations for a fee.

### Achievements (62)
Tracked across categories: trading, wealth, exploration, combat, mining, salvage, progression, crew, faction, campaign. Achievements award XP, credits, or skill points.

### Statistics Tracking
Lifetime stats across economic, exploration, combat, crew, and meta categories. Viewable in the Statistics screen.

---

## 7. Combat

### Overview
Turn-based tactical combat triggered by encounters (pirate attacks, mission events, hostile NPCs). 28 enemy templates across varying difficulty tiers.

### Combat Mechanics
- Each turn: choose from available combat moves (attack, defend, use ability)
- Ship weapons and defenses drawn from installed upgrades
- Each weapon/defense has energy cost, damage, accuracy, and cooldown
- Crew members provide combat bonuses based on their roles
- Victory yields loot, XP, and reputation changes
- Retreat option with consequences

### Combat Moves
Derived from installed weapon and defense upgrades. Mark enhancement and tuning bonuses apply to combat stats. Higher-tier upgrades provide stronger moves with additional effects (armor piercing, suppressive fire, shield regeneration).

---

## 8. Mini-Games

### Mining (5 configs)
Interactive mini-game where the player drills asteroid rocks for ore. Danger-based yield scaling rewards riskier mining sites with better materials. 4+ ore types feed into the refining system.

### Salvage (5 configs)
Exploration mini-game where the player searches debris fields for useful components. Salvage types vary by location and danger level. Recovered items can be sold or used in refining.

### Refining (38 recipes: 21 base + 17 advanced)
Combine raw ores and salvage into refined commodities. Recipe discovery system with schematic data unlocks. Advanced recipes require specific skill levels or discovered schematics. Refined goods are generally more valuable than raw materials.

---

## 9. Ground Exploration

### Overview
5 campaign ground maps with tile-based exploration. The player moves through a 2D grid, encountering hazards, NPCs, loot caches, and story events.

### Flow
1. Ground Briefing view presents the mission context
2. Ground Exploration view: tile-based movement, fog of war, encounters
3. Ground Result view: summary of findings, rewards

### Ground Combat
Separate from ship combat. Uses party composition (captain + crew). Ground Operations skill tree improves survival and combat effectiveness on the surface.

---

## 10. Crew System

### Crew Members (19 total)
- 4 companions (story-significant, personal quest arcs)
- 15 crew specialists (recruited at stations, provide specific bonuses)

### Party Management
- Ships have crew slot limits (varies by ship type, 2-6 slots)
- Active crew provide bonuses to trading, combat, mining, navigation, etc.
- Each crew member has a role, level, loyalty score, and personal quest

### Crew Quests (12)
Personal storylines for crew members. Completing quests boosts loyalty, unlocks upgraded abilities, and provides narrative depth.

### Crew Bonuses
- Primary bonus based on role (e.g., engineer reduces repair costs)
- Secondary ability unlocked at higher loyalty or quest completion
- Crew level increases through participating in activities

---

## 11. Factions and Reputation

### Factions (4 + Crimson Reach)

| Faction | Focus | Home Systems |
|---------|-------|-------------|
| Nexus Trade Consortium | Commerce and trade | Nexus Prime area |
| Forgeworks Industrial | Manufacturing and mining | Forgeworks area |
| Free Salvagers Union | Salvage and frontier freedom | Crimson Reach area |
| Axiom Research | Science and technology | Axiom Labs area |
| Crimson Reach | Antagonist faction | Crimson Reach |

### Reputation System
- Range: -100 (Hostile) to +100 (Revered)
- Reputation tiers unlock benefits: reduced tariffs, exclusive goods, special missions, faction ships
- Gaining reputation with one faction may reduce standing with rivals
- 12 faction perks unlocked at specific reputation thresholds

### Reputation Sources
- Completing faction missions
- Trading in faction systems
- Story choices and mission outcomes
- Delivering aid during crises

---

## 12. Campaign and Missions

### Campaign Structure
Three-act structure (Act One complete, Act Two planned):
- **Act One** (22 campaign missions): Introduction to the Expanse, meet core characters, establish the central conflict ("The Ledger" conspiracy)
- **Act Two** (planned): Conspiracy deepens, new systems, companion quests, fleet management
- **Act Three** (planned): Resolution with multiple endings

### Mission Types
- **Campaign missions** (22): advance the main narrative
- **Side missions** (21): self-contained stories for rewards and worldbuilding
- **Crew quests** (12): personal stories for recruited crew members
- Total: 55 missions

### Dialogue System
- 45 dialogue files with branching conversation trees
- 31 NPCs with distinct personalities
- Player choices affect reputation, relationships, and story outcomes
- Station chatter (148 lines) and news ticker (44 templates) for ambient worldbuilding

---

## 13. Random Encounters and Events

### Encounters (131 total, 11 types)
Events triggered during travel, at stations, or by specific conditions. Types include pirate attacks, distress signals, debris fields, trade opportunities, NPC encounters, and story triggers.

### Galaxy Events
- 5 event types, 18 templates, 1 event chain
- Affect market prices, system danger levels, and available missions
- Displayed via modal dialogs, timed banners, and galaxy map indicators

### Living Universe Features
- Station chatter: 148 context-sensitive ambient lines
- News ticker: 44 templates reflecting galaxy state
- Travel log tracking the player's journey

---

## 14. UI/UX

### Design Principles
1. Clarity over flash: information must be immediately readable
2. Minimize clicks: common actions require few inputs
3. Always informed: credits, cargo, fuel, location always visible
4. Consistent layout: similar actions work similarly everywhere
5. Forgiveness: confirmation prompts for major decisions
6. Keyboard + mouse: both input methods supported

### Visual Style
- Dark backgrounds, bright text, accent colors
- 9-slice panels for consistent UI chrome
- Custom cursor
- Full sprite set: ships, portraits, commodities, factions, upgrades, ground tiles
- Animated parallax starfield backgrounds (seed-based procedural)

### Views (34 total)
Key screens: main menu, galaxy map, station hub, trading, shipyard, skill tree, combat, dialogue, journal/mission log, crew roster, character view, mining, salvage, refining, ground exploration, cantina, investment, repair bay, statistics, achievements, settings, save/load.

### Visual Effects
- Particle system (object-pooled, 6+ presets)
- Screen transitions (fade, warp, slide)
- Vignette overlay and screen shake
- Color-coded feedback (green gains, red losses)

### Tutorial
5-step interactive tutorial with auto-trigger on new game, skip option, and replay from settings.

---

## 15. Technical Architecture

### Stack
- **Language**: Python 3.13+
- **Framework**: pygame-ce + pygame_gui
- **Data**: JSON files for all game content
- **Tests**: pytest (4,649 tests)
- **Quality**: Black (100 chars), MyPy strict, pylint

### Project Structure
```
spacegame/
  config.py         -- Constants, Colors, GameState enum, paths, game rules
  data_loader.py    -- JSON data loading singleton (get_data_loader())
  save_manager.py   -- Save/load with 12 slots, JSON serialization
  main.py           -- Entry point
  engine/           -- Game loop, state manager, input, particles, transitions, backgrounds
  models/           -- Data + logic classes (@dataclass), return tuple[bool, str] for failable ops
  views/            -- BaseView subclasses, one per game screen
  utils/            -- Logger
  data/             -- Theme config (theme.json)
data/               -- JSON content files (economy/, galaxy/, progression/, ships/)
tests/              -- pytest tests mirroring spacegame/ structure
```

### Architecture Pattern
Model-View with engine layer. Dependencies flow inward: views depend on models, models depend on nothing.

**Engine**: Game class owns the main loop at 60 FPS. StateManager handles state transitions with push/pop for overlays. TransitionManager provides visual transitions with midpoint callbacks. ParticlePool avoids GC pressure. AnimatedBackground uses seed-based procedural starfields.

**Models**: All `@dataclass` classes containing data and business logic. Operations that can fail return `tuple[bool, str]`. Serialization via `to_dict()` / `from_dict()`. Composition over inheritance (Player has Ship, Ship has ShipType, Player has Progression).

**Views**: BaseView subclasses with strict lifecycle: `on_enter()` calls `_create_ui()`, `on_exit()` calls `_destroy_ui()`. Each view manages its own pygame_gui elements. See `spacegame/views/CLAUDE.md` for patterns.

**Data Loading**: DataLoader singleton accessed via `get_data_loader()`. Loads all JSON on startup. Private `_parse_<type>()` methods convert raw dicts to model instances.

**Save System**: JSON format with version field for future migration. 12 slots (0 = autosave, 1-11 = manual). Chain: SaveManager -> Player.to_dict() -> Ship.to_dict() -> Progression.to_dict().

### Key Technical Decisions
- Deterministic randomness: seed with `f"{game_day}_{commodity_id}_{system_id}"` for market prices
- SpriteManager convenience API returns `Optional[Surface]` with graceful None fallback
- Never create Surfaces inside `update()`: create in `__init__` or `on_enter()`, reuse each frame
- Use `.convert_alpha()` on loaded images for rendering performance
- Pool particles and reuse objects to avoid GC pressure in the game loop

---

## 16. Code Style and Conventions

- **Formatting**: Black, 100-character line length
- **Type checking**: MyPy strict, all functions require type hints
- **Style guide**: Google Python Style Guide
- **Naming**: snake_case (functions/variables), PascalCase (classes), SCREAMING_SNAKE_CASE (constants)
- **Testing**: TDD (Red-Green-Refactor), pytest, class-based tests, self-contained fixtures
- **JSON**: top-level key is plural (`{"commodities": [...]}`), all keys snake_case

---

## 17. Content Data Files

All game content is data-driven via JSON:

| Directory | Contents |
|-----------|----------|
| `data/economy/` | Commodities, refining recipes, investment configs |
| `data/galaxy/` | Systems, stations, encounters, galaxy events |
| `data/ships/` | Ship types, upgrades |
| `data/progression/` | Skill trees, achievements, attributes |
| `data/crew/` | Crew member definitions, crew quests |
| `data/missions/` | Campaign, side, and crew mission definitions |
| `data/dialogue/` | NPC dialogue trees |
| `data/combat/` | Enemy templates, combat configs |
| `data/ground/` | Ground exploration maps and configs |
| `data/mining/` | Mining configs (5) |
| `data/salvage/` | Salvage configs (5) |

---

## 18. Future Work

### Campaign Act Two (next major milestone)
- "The Ledger" conspiracy continuation
- New star systems
- Companion quests for the 4 story companions
- Fleet management (multi-ship, crew assignment, trade automation)

### Campaign Act Three
- Multiple endings based on accumulated choices
- Resolution of faction conflicts and central conspiracy

### Other Planned Features
- Fleet management with automated trade routes
- Expanded galaxy with additional sectors
- Modding support for custom content
