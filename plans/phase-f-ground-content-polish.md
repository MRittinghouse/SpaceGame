# Phase F: Ground Exploration — Content & Polish

## Plan Overview

**Goal**: Complete the ground exploration system with briefing/result views, game engine integration, campaign maps, repeatable contracts, equipment, minimap, and achievements.

**Prerequisites**: Phases A-E complete (GroundMap, stealth, combat, crew, mapgen all working)
**Blocks**: Campaign Act One Chapters 3-5 (Missions 08-17)
**Spec**: requirements/13_ground_exploration.md (Sections 8, 11-14)

**Current state**:
- GameState.GROUND_BRIEFING / GROUND_RESULT defined in config.py but no views exist
- game.py has ZERO ground hooks — no `_ensure_*` methods, no state transition handling
- GroundExplorationView exits hardcoded to GALAXY_MAP
- Mission model has no ground-related fields or ObjectiveType entries
- No data/ground/ directory exists
- MapGenResult.build_mission_state() factory already works

---

## Cycle F.1: Ground Mission Model & Briefing View

**Goal**: Define ground mission data structures, build the pre-mission briefing screen with crew selection.

### Step F.1.1 — GroundMissionConfig model

**File**: `spacegame/models/ground_mission.py` (NEW)

```python
@dataclass
class GroundMissionConfig:
    """Configuration for a ground mission — bridges campaign/contract to mapgen."""

    id: str                          # e.g. "ground_mission_10" or "contract_nexus_001"
    name: str                        # Display name
    description: str                 # 2-4 sentence atmospheric briefing text
    mission_type: MissionType        # From ground_mapgen (INFILTRATION, RETRIEVAL, etc.)
    difficulty: DifficultyTier       # LOW, MODERATE, HIGH, EXTREME
    faction_id: str                  # Determines aesthetics and enemy pool
    objectives: list[str]            # Bullet-point objective descriptions for briefing
    intel_hints: list[IntelHint]     # Hints gated by ACU/Observation level
    rewards: GroundMissionRewards    # Credits, XP, reputation, items
    campaign_mission_id: Optional[str]  # Links to MissionManager mission, or None for contracts
    campaign_map_data: Optional[dict]   # Hand-authored map JSON (None = procedural)
    seed: Optional[int]              # Deterministic seed for procedural maps
    max_crew: int = 2                # Max crew members allowed

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> GroundMissionConfig: ...

@dataclass
class IntelHint:
    """A hint revealed if player meets skill threshold."""
    text: str
    required_skill: str       # "observation", "acuity", or skill node id
    required_level: int       # Minimum level to reveal

@dataclass
class GroundMissionRewards:
    """Rewards for completing a ground mission."""
    credits: int = 0
    xp: int = 0
    reputation: dict[str, int] = field(default_factory=dict)  # faction_id -> rep change
    items: list[str] = field(default_factory=list)  # Equipment IDs
    crew_xp: int = 0  # XP awarded to participating crew

@dataclass
class GroundMissionResult:
    """Outcome of a completed ground mission."""
    config: GroundMissionConfig
    outcome: str              # "success", "extracted", "defeated", "fled"
    objectives_completed: int
    objectives_total: int
    turns_taken: int
    enemies_defeated: int
    enemies_talked: int
    loot_credits: int         # Credits looted from containers/enemies
    loot_items: list[str]     # Equipment/item IDs found
    progress_percent: float   # 0.0-1.0, for consequence curve
    crew_ids: list[str]       # Crew that participated
    detected: bool            # Whether player was ever detected
```

**Tests** (`tests/test_models/test_ground_mission.py`):
- GroundMissionConfig round-trip serialization
- IntelHint filtering by player skill level
- GroundMissionRewards defaults
- GroundMissionResult consequence curve calculation
- Campaign vs contract config distinction

### Step F.1.2 — Consequence curve calculator

**File**: `spacegame/models/ground_mission.py` (add to GroundMissionResult)

```python
def calculate_penalties(self) -> dict:
    """Calculate failure penalties based on progress bell curve.

    Returns:
        Dict with credit_loss_percent, keep_loot_percent, xp_penalty.
    """
```

Penalty zones from spec:
| Progress | Zone | Credit Loss | Loot Kept | XP Penalty |
|---|---|---|---|---|
| 0-15% | Grace | 5% | 100% | 0 |
| 15-40% | Escalating | 10-15% | 10% | 0 |
| 40-65% | Commitment | 15-20% | 0% | small |
| 65-85% | Easing | 10% | 50% | 0 |
| 85-100% | So close | 5% | 80% | 0 |

**Tests**:
- Each zone boundary (0%, 15%, 40%, 65%, 85%, 100%)
- Interpolation within zones
- Success outcome returns no penalties

### Step F.1.3 — GroundBriefingView

**File**: `spacegame/views/ground_briefing_view.py` (NEW)

**Layout** (1200x900 window):
```
┌─────────────────────────────────────────────────┐
│  GROUND MISSION BRIEFING                        │
│  ─────────────────────────────                  │
│  [Mission Name]                    [Difficulty]  │
│                                                  │
│  [2-4 line atmospheric description]              │
│                                                  │
│  OBJECTIVES                                      │
│  • Reach Malia Torres's workshop                 │
│  • Avoid detection by station security           │
│                                                  │
│  INTEL (if any unlocked)                         │
│  ◆ Guards rotate on 6-turn cycle                 │
│  ◆ East wing maintenance shaft found             │
│                                                  │
│  ──────────────── CREW ─────────────────         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ [Elena]  │  │ [Marcus] │  │ [Priya]  │ ...   │
│  │ Vision+1 │  │ Silent   │  │ Analyze  │       │
│  │ Patrol   │  │ Doors    │  │ Hazard   │       │
│  │ [SELECT] │  │ [SELECT] │  │ [SELECT] │       │
│  └──────────┘  └──────────┘  └──────────┘       │
│  Selected: 0/2                                   │
│                                                  │
│  [LAUNCH MISSION]              [CANCEL]          │
└─────────────────────────────────────────────────┘
```

**Constructor**: `__init__(self, ui_manager, player, config: GroundMissionConfig)`
**Outputs**:
- `next_state = GameState.GROUND_EXPLORATION` (launch) or return_state (cancel)
- `selected_crew: list[str]` — crew IDs chosen by player
- `mission_config: GroundMissionConfig` — passed through to exploration

**Follows**: BaseView lifecycle (_create_ui/_destroy_ui), AnimatedBackground, dim overlay

**Tests** (`tests/test_views/test_ground_briefing_view.py`):
- View construction and lifecycle (on_enter/on_exit)
- Crew selection toggle (select/deselect, max cap)
- Intel hint filtering (show only unlocked hints)
- Launch button sets GROUND_EXPLORATION state
- Cancel button returns to previous state
- Crew abilities displayed correctly per crew member
- Empty crew selection allowed (solo mission)

---

## Cycle F.2: Ground Result View

**Goal**: Build the post-mission results screen, mirroring combat outcome display patterns.

### Step F.2.1 — GroundResultView

**File**: `spacegame/views/ground_result_view.py` (NEW)

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  ░░░░ dim background ░░░░░░░░░░░░░░░░░░░░░░░░  │
│  ┌───────────── RESULT PANEL ──────────────┐    │
│  │  MISSION COMPLETE  (or MISSION FAILED)  │    │
│  │  ──────────────────────────────────────  │    │
│  │  Mission: The Crimson Run               │    │
│  │                                          │    │
│  │  Objectives: 2/2 completed       ✓      │    │
│  │  Turns taken: 34                        │    │
│  │  Detection: Undetected           ★      │    │
│  │  Enemies defeated: 1                    │    │
│  │  Enemies talked past: 2                 │    │
│  │                                          │    │
│  │  ─────────── REWARDS ─────────────      │    │
│  │  Credits looted: +180 CR                │    │
│  │  Mission reward: +500 CR                │    │
│  │  XP earned: +25                         │    │
│  │  Crew XP: +15 (Elena, Tomas)            │    │
│  │  Reputation: +10 Frontier Alliance      │    │
│  │                                          │    │
│  │  (or PENALTIES section for failure)      │    │
│  │  Credits lost: -45 CR (10%)             │    │
│  │  Loot dropped: 50% kept                 │    │
│  │                                          │    │
│  │         [CONTINUE]                       │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**Constructor**: `__init__(self, ui_manager, player, result: GroundMissionResult)`
**Title colors**: SUCCESS → GREEN, EXTRACTED → YELLOW, DEFEATED → RED, FLED → ORANGE
**Exit**: Continue button or Enter key → `next_state = return_state`

**Tests** (`tests/test_views/test_ground_result_view.py`):
- Construction with each outcome type
- Correct title/color for each outcome
- Stats display accuracy (objectives, turns, enemies, etc.)
- Rewards section for success
- Penalties section for failure (consequence curve applied)
- Continue button sets next_state
- Enter key advances
- Ghost bonus indicator (undetected completion)
- Crew XP display when crew participated

---

## Cycle F.3: Game Engine Integration

**Goal**: Wire ground missions into game.py state machine. This is the critical integration cycle.

### Step F.3.1 — View registration methods

**File**: `spacegame/engine/game.py`

Add three `_ensure_*` methods:

```python
def _ensure_ground_briefing_view(self, config: GroundMissionConfig) -> None:
    """Create and register the ground briefing view."""
    from spacegame.views.ground_briefing_view import GroundBriefingView
    self.ground_briefing_view = GroundBriefingView(
        self.ui_manager, self.player, config
    )
    self.state_manager.register_state(
        GameState.GROUND_BRIEFING, self.ground_briefing_view
    )

def _ensure_ground_exploration_view(
    self, mission_state: GroundMissionState, config: GroundMissionConfig
) -> None:
    """Create and register the ground exploration view."""
    from spacegame.views.ground_exploration_view import GroundExplorationView
    self.ground_exploration_view = GroundExplorationView(
        self.ui_manager, mission_state, config
    )
    self.state_manager.register_state(
        GameState.GROUND_EXPLORATION, self.ground_exploration_view
    )

def _ensure_ground_result_view(self, result: GroundMissionResult) -> None:
    """Create and register the ground result view."""
    from spacegame.views.ground_result_view import GroundResultView
    self.ground_result_view = GroundResultView(
        self.ui_manager, self.player, result
    )
    self.state_manager.register_state(
        GameState.GROUND_RESULT, self.ground_result_view
    )
```

### Step F.3.2 — State transition handling

**File**: `spacegame/engine/game.py` — in `_handle_state_transitions()`

Add ground state transition cases:

```python
# GROUND_BRIEFING → GROUND_EXPLORATION (launch) or return_state (cancel)
if current == GameState.GROUND_BRIEFING:
    next_state = self.ground_briefing_view.get_next_state()
    if next_state == GameState.GROUND_EXPLORATION:
        # Build mission state from config + selected crew
        crew_ids = self.ground_briefing_view.selected_crew
        config = self.ground_briefing_view.mission_config
        mission_state = self._build_ground_mission_state(config, crew_ids)
        self._ensure_ground_exploration_view(mission_state, config)
        # Transition with appropriate effect

# GROUND_EXPLORATION → GROUND_RESULT
if current == GameState.GROUND_EXPLORATION:
    next_state = self.ground_exploration_view.get_next_state()
    if next_state == GameState.GROUND_RESULT:
        result = self.ground_exploration_view.get_mission_result()
        self._ensure_ground_result_view(result)
        # Transition

# GROUND_RESULT → return state (apply rewards/penalties)
if current == GameState.GROUND_RESULT:
    next_state = self.ground_result_view.get_next_state()
    if next_state:
        self._apply_ground_result(self.ground_result_view.result)
        # Transition to return_state
```

### Step F.3.3 — Ground mission launcher

**File**: `spacegame/engine/game.py`

```python
def start_ground_mission(self, config: GroundMissionConfig) -> None:
    """Launch a ground mission from dialogue, mission, or station UI."""
    self._ensure_ground_briefing_view(config)
    self.state_manager.change_state(GameState.GROUND_BRIEFING)

def _build_ground_mission_state(
    self, config: GroundMissionConfig, crew_ids: list[str]
) -> GroundMissionState:
    """Build GroundMissionState from config and selected crew."""
    # Compute crew bonuses
    crew_bonuses = GroundCrewBonuses.compute(crew_ids, self.player.attributes)

    if config.campaign_map_data:
        # Hand-authored: load map from campaign data
        ground_map = GroundMap.from_dict(config.campaign_map_data)
        enemies = [GroundEnemy.from_dict(e) for e in config.campaign_map_data["enemies"]]
        mission_state = GroundMissionState(
            ground_map=ground_map, player=GroundPlayerState(...),
            enemies=enemies, crew_bonuses=crew_bonuses, ...
        )
    else:
        # Procedural: use MapGenConfig → GroundMapGenerator
        gen_config = MapGenConfig(
            mission_type=config.mission_type, difficulty=config.difficulty,
            seed=config.seed or hash(config.id), faction_id=config.faction_id
        )
        result = GroundMapGenerator().generate(gen_config)
        mission_state = result.build_mission_state(
            crew_bonuses, self.player.attributes, self.player.progression
        )
    return mission_state

def _apply_ground_result(self, result: GroundMissionResult) -> None:
    """Apply ground mission outcome to player state."""
    if result.outcome == "success":
        self.player.credits += result.config.rewards.credits + result.loot_credits
        self.player.progression.add_xp(result.config.rewards.xp)
        # Award reputation
        for faction_id, rep in result.config.rewards.reputation.items():
            self.player.faction_reputation.modify(faction_id, rep)
        # Award crew XP
        for crew_id in result.crew_ids:
            self.player.ship.crew_roster.add_xp(crew_id, result.config.rewards.crew_xp)
        # Complete campaign mission objective if applicable
        if result.config.campaign_mission_id:
            self.mission_manager.complete_objective(...)
    else:
        # Apply consequence curve penalties
        penalties = result.calculate_penalties()
        credit_loss = int(self.player.credits * penalties["credit_loss_percent"] / 100)
        self.player.credits -= credit_loss
        # Partial loot based on keep_loot_percent
        kept_credits = int(result.loot_credits * penalties["keep_loot_percent"] / 100)
        self.player.credits += kept_credits
```

### Step F.3.4 — GroundExplorationView modifications

**File**: `spacegame/views/ground_exploration_view.py`

Changes needed:
1. Accept `GroundMissionConfig` in constructor (for objective tracking)
2. Track mission progress (objectives completed, loot collected, enemies defeated/talked)
3. Build `GroundMissionResult` on mission end (exit tile, defeat, flee)
4. Change `next_state` from hardcoded `GALAXY_MAP` to `GROUND_RESULT`
5. Add `get_mission_result() -> GroundMissionResult` method

**Tests** (`tests/test_views/test_ground_exploration_integration.py`):
- Exploration view accepts config
- Mission result built correctly on exit tile
- Mission result built correctly on defeat
- Progress tracking (objectives, loot, enemies)
- next_state is GROUND_RESULT not GALAXY_MAP

### Step F.3.5 — Integration tests

**Tests** (`tests/test_engine/test_ground_integration.py`):
- Full flow: start_ground_mission → BRIEFING → EXPLORATION → RESULT
- Cancel from briefing returns to previous state
- Success applies rewards correctly
- Failure applies consequence curve penalties
- Campaign mission objective completed on success
- Crew XP awarded on completion
- Procedural map generated from config
- Campaign map loaded from config data

---

## Cycle F.4: Ground Equipment & Loot

**Goal**: Ground-exclusive equipment system and loot tables.

### Step F.4.1 — GroundEquipment model

**File**: `spacegame/models/ground_equipment.py` (NEW)

```python
@dataclass
class GroundEquipment:
    """Equipment usable only during ground missions."""
    id: str
    name: str
    description: str
    slot: str                    # "utility" or "defense"
    effects: dict[str, float]    # e.g. {"noise_reduction": 1, "vision_bonus": 1}

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> GroundEquipment: ...
```

**Equipment types** (from spec):
| ID | Name | Slot | Effect |
|---|---|---|---|
| personal_shield | Personal Shield Module | defense | +2 ground HP, absorbs first hit |
| noise_dampener | Noise Dampener | utility | -1 noise radius on all actions |
| vision_enhancer | Vision Enhancer | utility | +2 vision radius |
| lockpick_set | Lockpick Set | utility | Can open locked doors silently |
| emp_grenade | EMP Grenade | utility | Disable 1 automated enemy for 5 turns |

### Step F.4.2 — Equipment data file

**File**: `data/ground/equipment.json` (NEW)

```json
{
    "ground_equipment": [
        {
            "id": "personal_shield",
            "name": "Personal Shield Module",
            "description": "Generates a localized energy barrier. Absorbs the first hit taken.",
            "slot": "defense",
            "effects": {"hp_bonus": 2, "absorb_first_hit": true}
        },
        ...
    ]
}
```

### Step F.4.3 — Loot tables

**File**: `spacegame/models/ground_mission.py` (extend)

```python
@dataclass
class GroundLootTable:
    """Defines possible loot for a ground mission difficulty/faction."""
    credit_range: tuple[int, int]         # min, max per container
    equipment_chance: float               # 0.0-1.0
    equipment_pool: list[str]             # Equipment IDs
    commodity_drops: list[tuple[str, int]] # (commodity_id, max_quantity)

    def roll_container_loot(self, com_bonus: float, rng: random.Random) -> dict:
        """Generate loot for a single container. COM attribute improves quality."""
```

### Step F.4.4 — Player ground equipment inventory

**File**: `spacegame/models/player.py` (extend)

Add `ground_equipment: list[str]` field — equipment IDs owned by player.
Add to `to_dict`/`from_dict` (backward compatible, defaults empty).

### Step F.4.5 — Equipment integration into GroundCrewBonuses

Extend `GroundCrewBonuses.compute()` to also accept equipped items and apply their effects.

**Tests**:
- GroundEquipment serialization round-trip
- Loot table rolls (COM bonus, seeded determinism)
- Player equipment persistence
- Equipment effects applied in GroundCrewBonuses
- DataLoader loads equipment JSON

---

## Cycle F.5: Repeatable Contracts

**Goal**: Procedurally generated ground missions posted at stations.

### Step F.5.1 — GroundContractManager model

**File**: `spacegame/models/ground_contracts.py` (NEW)

```python
@dataclass
class GroundContract:
    """A time-limited ground mission contract."""
    id: str
    config: GroundMissionConfig
    system_id: str              # Where the contract is posted
    target_system_id: str       # Where the mission takes place
    expiry_day: int             # Game day when contract expires
    bonus_credits: int          # Extra credits for completion before expiry
    completed: bool = False

    def is_expired(self, current_day: int) -> bool: ...
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> GroundContract: ...

class GroundContractManager:
    """Generates and manages repeatable ground contracts."""

    def __init__(self) -> None:
        self.active_contracts: list[GroundContract] = []
        self.completed_count: int = 0

    def generate_contracts(
        self, system_id: str, faction_id: str,
        game_day: int, player_level: int
    ) -> list[GroundContract]:
        """Generate 2-3 contracts for a system, deterministically seeded."""

    def get_available(self, system_id: str, game_day: int) -> list[GroundContract]:
        """Get non-expired, non-completed contracts for a system."""

    def complete_contract(self, contract_id: str) -> GroundContract: ...

    def advance_day(self, game_day: int) -> None:
        """Remove expired contracts."""

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> GroundContractManager: ...
```

### Step F.5.2 — Contract template data

**File**: `data/ground/contract_templates.json` (NEW)

Templates for procedural briefing text assembly:
```json
{
    "contract_templates": {
        "infiltration": {
            "descriptions": [
                "Intelligence suggests a {faction} facility on {system} holds valuable data.",
                "A contact needs someone to slip into the {faction} compound at {system}."
            ],
            "objective_templates": [
                "Reach the target terminal and download data",
                "Access the restricted area without triggering alarms"
            ]
        },
        ...
    }
}
```

### Step F.5.3 — Contract UI in trading/station view

Contracts are accessed from the galaxy map or trading view. Add a "Contracts" button that shows available ground contracts for the current system. Selecting one launches `start_ground_mission()`.

**Tests**:
- Contract generation (deterministic seeding, correct difficulty scaling)
- Contract expiry
- Contract completion
- Save/load round-trip
- Available contracts filtered by system
- Briefing text assembly from templates

---

## Cycle F.6: Campaign Maps

**Goal**: Hand-authored maps for Missions 10, 13, 16.

### Step F.6.1 — Campaign map format

**File**: `data/ground/campaign/` directory (NEW)

Each campaign map is a JSON file defining:
```json
{
    "id": "mission_10_crimson_reach",
    "name": "Wrecker's Outpost",
    "width": 25,
    "height": 20,
    "tiles": [[...]],
    "entrance": [2, 18],
    "exit": [22, 3],
    "enemies": [
        {
            "id": "outpost_guard_1",
            "template_id": "frontier_patrol",
            "x": 10, "y": 12,
            "patrol_route": [[10, 12], [10, 8], [14, 8], [14, 12]],
            "facing": "up"
        }
    ],
    "interactables": [
        {"x": 15, "y": 5, "type": "npc_encounter", "dialogue_id": "malia_ground"}
    ],
    "story_triggers": [
        {"x": 8, "y": 10, "type": "discovery", "text": "The corridor opens into a bustling black market..."}
    ]
}
```

### Step F.6.2 — Mission 10: The Crimson Run

**Map**: Wrecker's Outpost (Crimson Reach station)
- **Size**: 25x20, LOW difficulty
- **Layout**: Docking bay (entrance) → market corridor → workshop bay (objective)
- **Enemies**: 3-4 Frontier Alliance patrols (relaxed, wide gaps)
- **Flavor**: Atmospheric introduction, lots of flavor text tiles, NPCs in market area
- **Objective**: Reach Malia Torres (NPC encounter tile at workshop)
- **Special**: Market section has salvage piles (searchable for items)

### Step F.6.3 — Mission 13: The Favor Returned

**Map**: Breakstone Mining Tunnels
- **Size**: 30x25, MODERATE difficulty
- **Layout**: Union checkpoint → mining tunnels → deep tunnels (Oren Tak)
- **Enemies**: 5-6 Union security + workers (dense NPC presence)
- **Flavor**: Hand-painted murals, heavy machinery (noise cover), steam vents
- **Objective**: Navigate to Oren Tak's location
- **Special**: Marcus companion path — speech check at checkpoint (or Marcus vouches)
- **Hazards**: Steam vents, unstable ground

### Step F.6.4 — Mission 16: The Operation (Alliance path)

**Map**: Pirate Base Interior
- **Size**: 35x30, HIGH difficulty
- **Layout**: Maintenance port → corridors → guard stations → command center
- **Enemies**: 8-10 tight patrols, overlapping routes
- **Flavor**: Frontier Alliance aesthetic — eclectic, salvaged, loud doors
- **Objective**: Reach command center (multi-phase: port → corridors → center)
- **Special**: Tomas companion provides stealth bonus, sabotage sub-objectives optional

### Step F.6.5 — Campaign map loader

**File**: `spacegame/data_loader.py` (extend)

```python
def _load_campaign_maps(self) -> None:
    """Load hand-authored campaign ground maps."""
    campaign_dir = DATA_DIR / "ground" / "campaign"
    self.campaign_ground_maps: dict[str, dict] = {}
    if campaign_dir.exists():
        for path in campaign_dir.glob("*.json"):
            data = self._read_json(path)
            self.campaign_ground_maps[data["id"]] = data
```

### Step F.6.6 — Mission model integration

**File**: `spacegame/models/mission.py` (extend)

Add new ObjectiveType:
```python
class ObjectiveType(Enum):
    ...
    COMPLETE_GROUND_MISSION = "complete_ground_mission"  # target_id = ground_mission_config_id
```

Add to mission JSON for Missions 10, 13, 16:
```json
{
    "type": "complete_ground_mission",
    "target_id": "mission_10_crimson_reach",
    "description": "Navigate Wrecker's Outpost and find Malia Torres"
}
```

**Tests**:
- Campaign map loading from JSON
- Map validation (entrance/exit exist, tiles are valid)
- Mission 10 map structure
- Mission 13 map structure
- Mission 16 map structure
- ObjectiveType.COMPLETE_GROUND_MISSION handled by MissionManager
- Ground mission completion triggers mission objective

---

## Cycle F.7: Minimap

**Goal**: Corner minimap showing explored areas, player position, and detected enemies.

### Step F.7.1 — Minimap renderer

**File**: `spacegame/views/ground_exploration_view.py` (extend)

Add minimap rendering to GroundExplorationView:

```python
# Minimap constants
MINIMAP_SIZE = 150          # Pixels (square)
MINIMAP_MARGIN = 10         # From top-right corner
MINIMAP_ALPHA = 200         # Background transparency

# Color coding per tile type and fog state
MINIMAP_COLORS = {
    (TileType.FLOOR, FogState.VISIBLE): (80, 85, 95),
    (TileType.FLOOR, FogState.EXPLORED): (50, 52, 60),
    (TileType.WALL, FogState.VISIBLE): (35, 35, 45),
    (TileType.WALL, FogState.EXPLORED): (25, 25, 32),
    (TileType.EXIT, FogState.VISIBLE): (50, 200, 100),
    ...
}
MINIMAP_PLAYER_COLOR = (255, 220, 80)   # Bright yellow dot
MINIMAP_ENEMY_COLOR = (220, 60, 60)     # Red dot (visible enemies only)
```

**Implementation**:
1. Create a Surface of MINIMAP_SIZE x MINIMAP_SIZE in `_create_ui()`
2. Scale: `pixels_per_tile = MINIMAP_SIZE / max(map.width, map.height)`
3. Each frame in `render()`: draw minimap after main viewport
4. Only draw tiles that are EXPLORED or VISIBLE (UNEXPLORED = black)
5. Player = bright dot, visible enemies = red dots
6. Semi-transparent background behind minimap

**Tests**:
- Minimap surface created with correct dimensions
- Unexplored tiles not drawn
- Player position correctly mapped
- Visible enemies shown, non-visible hidden
- Minimap scales to map dimensions

---

## Cycle F.8: Achievements & Polish

**Goal**: Ground-specific achievements, interactable tiles, visual polish.

### Step F.8.1 — Ground achievements

**File**: `data/journal/achievements.json` (extend)

Add ground-specific achievements:
| ID | Name | Description | Condition |
|---|---|---|---|
| ground_first_mission | First Steps | Complete your first ground mission | 1 ground mission completed |
| ground_ghost_run | Ghost | Complete a ground mission without being detected | Undetected completion |
| ground_veteran | Ground Veteran | Complete 10 ground missions | 10 completions |
| ground_scrapper | Scrapper | Defeat 25 enemies in ground combat | 25 ground kills |
| ground_silver_tongue | Silver Tongue | Talk past 15 enemies | 15 ground talks |
| ground_explorer | Cartographer | Discover 500 ground tiles | Cumulative tiles explored |
| ground_campaign_all | Deep Cover | Complete all campaign ground missions | M10 + M13 + M16 |

### Step F.8.2 — Player ground statistics

**File**: `spacegame/models/player.py` (extend)

Add tracked stats (backward compatible):
```python
ground_missions_completed: int = 0
ground_missions_failed: int = 0
ground_enemies_defeated: int = 0
ground_enemies_talked: int = 0
ground_tiles_explored: int = 0
ground_undetected_completions: int = 0
```

### Step F.8.3 — Interactable tile types

**File**: `spacegame/models/ground.py` (extend TileType)

Add new tile types:
```python
class TileType(Enum):
    ...
    CONTAINER = "container"        # Searchable loot container
    TERMINAL = "terminal"          # Hackable terminal (ING check)
    CONTROL_PANEL = "control_panel"  # Disable cameras/alarms
    HIDDEN_PASSAGE = "hidden_passage"  # Appears as wall until revealed
    COVER = "cover"                # Half-wall, provides stealth bonus
    HAZARD_STEAM = "hazard_steam"  # Periodic damage, RES check
    HAZARD_RADIATION = "hazard_radiation"  # Damage over time
    DARK_FLOOR = "dark_floor"      # Reduced vision for all
    SALVAGE_PILE = "salvage_pile"  # Frontier Alliance, searchable for items
    MACHINERY = "machinery"        # Union, creates noise cover within 2 tiles
    SENSOR_ARRAY = "sensor_array"  # Collective, detects movement within 3 tiles
    SECURITY_CAMERA = "security_camera"  # Guild, vision cone like enemy
```

### Step F.8.4 — Tile interaction system

**File**: `spacegame/models/ground.py` (extend GroundPlayerState)

Add interaction methods:
```python
def interact_container(self, tile: GroundTile, loot_table: GroundLootTable, ...) -> dict:
    """Search a container. Takes 1 turn, generates noise."""

def interact_terminal(self, tile: GroundTile, ing_level: int) -> tuple[bool, str]:
    """Hack a terminal. ING check, failure = noise."""

def interact_control_panel(self, tile: GroundTile) -> tuple[bool, str]:
    """Disable a security system (camera, alarm)."""
```

### Step F.8.5 — Visual polish

Enhancements to GroundExplorationView:
1. **Tile color variety**: Per-faction color palettes (Guild=clean blue-grey, Union=warm brown, Collective=sterile white, Alliance=eclectic)
2. **Interactable highlights**: Pulsing glow on containers, terminals, panels when visible
3. **Hazard effects**: Periodic pulsing color on steam/radiation tiles
4. **Screen shake**: On taking damage in ground combat
5. **Particle effects**: Combat hit sparks, door opening dust

**Tests**:
- Achievement unlock conditions
- Player stat tracking
- New tile types walkability and vision blocking
- Container interaction (loot generation, noise)
- Terminal interaction (ING check, success/failure)
- Hidden passage reveal logic
- Sensor array detection
- Machinery noise masking
- Faction color palette selection

---

## Cycle Summary

| Cycle | Scope | New Files | Est. Tests |
|---|---|---|---|
| F.1 | Mission model + Briefing view | ground_mission.py, ground_briefing_view.py, test files | ~40 |
| F.2 | Result view | ground_result_view.py, test file | ~25 |
| F.3 | Game engine integration | game.py extensions, exploration view mods, test files | ~35 |
| F.4 | Equipment & loot | ground_equipment.py, equipment.json, test files | ~25 |
| F.5 | Repeatable contracts | ground_contracts.py, contract_templates.json, test files | ~20 |
| F.6 | Campaign maps | 3 map JSONs, data_loader + mission.py extensions, test files | ~30 |
| F.7 | Minimap | exploration_view.py extension, test file | ~10 |
| F.8 | Achievements & polish | Multiple extensions, achievements.json, test files | ~30 |
| **Total** | | ~8 new files, ~6 extended files, ~5 data files | **~215** |

## Build Order & Dependencies

```
F.1 (Mission Model + Briefing)
 ↓
F.2 (Result View) ──────────────┐
 ↓                               │
F.3 (Engine Integration) ←───────┘
 ↓
F.4 (Equipment & Loot)     F.5 (Contracts)     F.6 (Campaign Maps)
 ↓                           ↓                    ↓
 └───────────────────────────┴────────────────────┘
                    ↓
              F.7 (Minimap)
                    ↓
              F.8 (Achievements & Polish)
```

F.1 → F.2 → F.3 are sequential (each depends on the prior).
F.4, F.5, F.6 can be built in any order after F.3.
F.7 and F.8 are final polish, after all content is in.

## TDD Approach

Each step within each cycle follows Red-Green-Refactor:
1. **Red**: Write failing tests for the new model/view/integration
2. **Green**: Implement minimum code to pass
3. **Refactor**: Clean up, extract helpers, ensure style compliance

Run `pytest` after each step. Run `black spacegame/ tests/` and `mypy spacegame/` at cycle boundaries.

## Version Target

Phase F completion → **v16.0**, ~1830+ tests (1614 current + ~215 new)
