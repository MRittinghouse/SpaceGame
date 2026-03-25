"""Procedural ground map generation (Phase E).

Assembles ground exploration maps from hand-authored chunk templates
using a critical-path-first algorithm. Supports 5 mission types,
4 difficulty tiers, and deterministic seeding for reproducibility.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from spacegame.models.ground import (
    _WALKABLE_TYPES,
    GroundInteractable,
    GroundMap,
    GroundPlayerState,
    GroundStoryTrigger,
    GroundTile,
    TileType,
)
from spacegame.models.ground_combat import GROUND_ENEMY_TEMPLATES
from spacegame.models.ground_crew import GroundCrewBonuses
from spacegame.models.ground_enemy import Direction, GroundEnemy, GroundMissionState

if TYPE_CHECKING:
    from spacegame.models.attributes import AttributeSheet
    from spacegame.models.progression import PlayerProgression


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ChunkCategory(Enum):
    """Category of a map chunk template."""

    ROOM = "room"
    CONNECTOR = "connector"
    SPECIAL = "special"


class MissionType(Enum):
    """Ground mission objective type."""

    INFILTRATION = "infiltration"
    RETRIEVAL = "retrieval"
    SABOTAGE = "sabotage"
    EXPLORATION = "exploration"
    EXTRACTION = "extraction"

    @property
    def description(self) -> str:
        """Human-readable mission description."""
        return _MISSION_DESCRIPTIONS[self]


_MISSION_DESCRIPTIONS: dict[MissionType, str] = {
    MissionType.INFILTRATION: "Reach the target room and interact with the objective.",
    MissionType.RETRIEVAL: "Find and extract a specific item from deep in the facility.",
    MissionType.SABOTAGE: "Disable multiple targets spread across the facility.",
    MissionType.EXPLORATION: "Map the facility and reach the extraction point.",
    MissionType.EXTRACTION: "Locate the target and escort them to the exit.",
}


# ---------------------------------------------------------------------------
# DifficultyTier
# ---------------------------------------------------------------------------


class DifficultyTier(Enum):
    """Difficulty tier with associated generation parameters."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

    @property
    def enemy_count_min(self) -> int:
        return _TIER_PARAMS[self]["enemy_min"]

    @property
    def enemy_count_max(self) -> int:
        return _TIER_PARAMS[self]["enemy_max"]

    @property
    def map_width(self) -> int:
        return _TIER_PARAMS[self]["width"]

    @property
    def map_height(self) -> int:
        return _TIER_PARAMS[self]["height"]

    @property
    def enemy_speed_weights(self) -> list[tuple[int, int]]:
        """(speed, weight) pairs for random enemy speed selection."""
        return _TIER_PARAMS[self]["speed_weights"]

    @property
    def loot_multiplier(self) -> float:
        return _TIER_PARAMS[self]["loot_mult"]

    @property
    def room_count_range(self) -> tuple[int, int]:
        """(min, max) number of rooms to place."""
        return _TIER_PARAMS[self]["rooms"]


_TIER_PARAMS: dict[DifficultyTier, dict] = {
    DifficultyTier.LOW: {
        "enemy_min": 3,
        "enemy_max": 5,
        "width": 18,
        "height": 18,
        "speed_weights": [(2, 3), (1, 1)],
        "loot_mult": 1.0,
        "rooms": (3, 5),
    },
    DifficultyTier.MODERATE: {
        "enemy_min": 5,
        "enemy_max": 8,
        "width": 22,
        "height": 22,
        "speed_weights": [(2, 2), (1, 3)],
        "loot_mult": 1.3,
        "rooms": (4, 7),
    },
    DifficultyTier.HIGH: {
        "enemy_min": 8,
        "enemy_max": 12,
        "width": 26,
        "height": 28,
        "speed_weights": [(1, 4), (2, 1)],
        "loot_mult": 1.7,
        "rooms": (5, 8),
    },
    DifficultyTier.EXTREME: {
        "enemy_min": 10,
        "enemy_max": 15,
        "width": 30,
        "height": 30,
        "speed_weights": [(1, 3), (2, 1)],
        "loot_mult": 2.0,
        "rooms": (6, 10),
    },
}


# ---------------------------------------------------------------------------
# ChunkTemplate
# ---------------------------------------------------------------------------


@dataclass
class ChunkTemplate:
    """A small tile template that can be stamped onto the map grid.

    Tiles are stored row-major: tiles[y][x] as TileType enums.
    Exits define connection points on edges.
    """

    id: str
    width: int
    height: int
    category: ChunkCategory
    tiles: list[list[TileType]] = field(default_factory=list)
    exits: dict[str, tuple[int, int]] = field(default_factory=dict)

    def set_tile(self, x: int, y: int, tile_type: TileType) -> None:
        """Set a specific tile in the chunk."""
        if 0 <= y < self.height and 0 <= x < self.width:
            self.tiles[y][x] = tile_type

    def rotate_90(self) -> ChunkTemplate:
        """Return a new chunk rotated 90 degrees clockwise."""
        new_tiles: list[list[TileType]] = []
        new_w = self.height
        new_h = self.width
        for x in range(self.width):
            row: list[TileType] = []
            for y in range(self.height - 1, -1, -1):
                row.append(self.tiles[y][x])
            new_tiles.append(row)

        # Rotate exits
        new_exits: dict[str, tuple[int, int]] = {}
        rotation_map = {"north": "east", "east": "south", "south": "west", "west": "north"}
        for direction, (ex, ey) in self.exits.items():
            new_dir = rotation_map.get(direction, direction)
            new_exits[new_dir] = (self.height - 1 - ey, ex)

        return ChunkTemplate(
            id=f"{self.id}_r90",
            width=new_w,
            height=new_h,
            category=self.category,
            tiles=new_tiles,
            exits=new_exits,
        )

    @classmethod
    def create_room(cls, width: int, height: int, room_id: str) -> ChunkTemplate:
        """Create a room with wall border and floor interior.

        Args:
            width: Room width.
            height: Room height.
            room_id: Unique identifier.

        Returns:
            ChunkTemplate with walls on edges and floor inside.
        """
        tiles: list[list[TileType]] = []
        for y in range(height):
            row: list[TileType] = []
            for x in range(width):
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    row.append(TileType.WALL)
                else:
                    row.append(TileType.FLOOR)
            tiles.append(row)
        return cls(
            id=room_id,
            width=width,
            height=height,
            category=ChunkCategory.ROOM,
            tiles=tiles,
        )

    @classmethod
    def create_corridor_h(cls, length: int, corridor_id: str) -> ChunkTemplate:
        """Create a horizontal corridor (3 tiles wide with wall borders).

        Args:
            length: Corridor length.
            corridor_id: Unique identifier.

        Returns:
            ChunkTemplate for a horizontal corridor.
        """
        h = 5
        tiles: list[list[TileType]] = []
        for y in range(h):
            row: list[TileType] = []
            for _x in range(length):
                if y == 0 or y == h - 1:
                    row.append(TileType.WALL)
                elif y == 1 or y == 3:
                    row.append(TileType.WALL)
                else:
                    row.append(TileType.FLOOR)
            tiles.append(row)
        chunk = cls(
            id=corridor_id,
            width=length,
            height=h,
            category=ChunkCategory.CONNECTOR,
            tiles=tiles,
            exits={"west": (0, 2), "east": (length - 1, 2)},
        )
        return chunk

    @classmethod
    def create_corridor_v(cls, length: int, corridor_id: str) -> ChunkTemplate:
        """Create a vertical corridor (3 tiles wide with wall borders).

        Args:
            length: Corridor length.
            corridor_id: Unique identifier.

        Returns:
            ChunkTemplate for a vertical corridor.
        """
        w = 5
        tiles: list[list[TileType]] = []
        for _y in range(length):
            row: list[TileType] = []
            for x in range(w):
                if x == 0 or x == w - 1:
                    row.append(TileType.WALL)
                elif x == 1 or x == 3:
                    row.append(TileType.WALL)
                else:
                    row.append(TileType.FLOOR)
            tiles.append(row)
        chunk = cls(
            id=corridor_id,
            width=w,
            height=length,
            category=ChunkCategory.CONNECTOR,
            tiles=tiles,
            exits={"north": (2, 0), "south": (2, length - 1)},
        )
        return chunk


# ---------------------------------------------------------------------------
# ChunkLibrary
# ---------------------------------------------------------------------------


class ChunkLibrary:
    """Collection of categorized chunk templates."""

    def __init__(self) -> None:
        self._chunks: dict[str, ChunkTemplate] = {}

    def add(self, chunk: ChunkTemplate) -> None:
        """Add a chunk template to the library."""
        self._chunks[chunk.id] = chunk

    def get_by_id(self, chunk_id: str) -> Optional[ChunkTemplate]:
        """Get a chunk by ID, or None if not found."""
        return self._chunks.get(chunk_id)

    def get_by_category(self, category: ChunkCategory) -> list[ChunkTemplate]:
        """Get all chunks in a category."""
        return [c for c in self._chunks.values() if c.category == category]

    @classmethod
    def create_default(cls) -> ChunkLibrary:
        """Create the default chunk library with built-in templates.

        Returns:
            ChunkLibrary with rooms, connectors, and special chunks.
        """
        lib = cls()

        # --- Rooms (8x8) ---
        for room_id, features in _DEFAULT_ROOMS.items():
            chunk = ChunkTemplate.create_room(8, 8, room_id)
            # Add interior walls (cover, pillars, furniture)
            for wx, wy in features.get("interior_walls", []):
                chunk.set_tile(wx, wy, TileType.WALL)
            # Add doors at defined positions
            for dx, dy in features.get("doors", []):
                chunk.set_tile(dx, dy, TileType.DOOR_CLOSED)
            # Add noisy floor tiles
            for nx, ny in features.get("noisy", []):
                chunk.set_tile(nx, ny, TileType.NOISY_FLOOR)
            # Define exits at door positions
            exits: dict[str, tuple[int, int]] = {}
            for dx, dy in features.get("doors", []):
                if dy == 0:
                    exits["north"] = (dx, dy)
                elif dy == 7:
                    exits["south"] = (dx, dy)
                elif dx == 0:
                    exits["west"] = (dx, dy)
                elif dx == 7:
                    exits["east"] = (dx, dy)
            chunk.exits = exits
            lib.add(chunk)

        # --- Connectors ---
        lib.add(ChunkTemplate.create_corridor_h(8, "corridor_h"))
        lib.add(ChunkTemplate.create_corridor_v(8, "corridor_v"))
        lib.add(ChunkTemplate.create_corridor_h(6, "corridor_h_short"))
        lib.add(ChunkTemplate.create_corridor_v(6, "corridor_v_short"))

        # --- L-bend connector ---
        l_bend = _create_l_bend()
        lib.add(l_bend)

        # --- Special rooms ---
        vault = ChunkTemplate.create_room(8, 8, "vault")
        vault.set_tile(4, 0, TileType.DOOR_CLOSED)
        vault.exits = {"north": (4, 0)}
        vault.category = ChunkCategory.SPECIAL
        lib.add(vault)

        dead_end = ChunkTemplate.create_room(6, 6, "dead_end_loot")
        dead_end.set_tile(3, 0, TileType.DOOR_CLOSED)
        dead_end.exits = {"north": (3, 0)}
        dead_end.category = ChunkCategory.SPECIAL
        lib.add(dead_end)

        return lib


# Default room definitions with door, feature, and interior wall positions
# interior_walls create cover, chokepoints, and tactical variety
_DEFAULT_ROOMS: dict[str, dict] = {
    "security_checkpoint": {
        "doors": [(4, 0), (4, 7)],
        "noisy": [(3, 3), (4, 3), (5, 3)],
        # Barrier wall across middle with gap — forces player through noisy strip
        "interior_walls": [(2, 3), (6, 3)],
    },
    "storage_bay": {
        "doors": [(4, 0), (7, 4)],
        "noisy": [],
        # Shelving rows — parallel internal walls creating aisles
        "interior_walls": [(2, 2), (2, 3), (2, 4), (5, 2), (5, 3), (5, 4)],
    },
    "mess_hall": {
        "doors": [(4, 0), (0, 4), (7, 4)],
        "noisy": [(2, 2), (5, 5)],
        # Tables as cover — scattered pillars
        "interior_walls": [(3, 3), (5, 3), (3, 5)],
    },
    "lab": {
        "doors": [(4, 0), (4, 7)],
        "noisy": [(2, 4)],
        # Lab benches — L-shaped internal wall
        "interior_walls": [(2, 2), (3, 2), (2, 3)],
    },
    "office": {
        "doors": [(0, 4), (7, 4)],
        "noisy": [],
        # Partition wall creating two areas
        "interior_walls": [(4, 2), (4, 3), (4, 5), (4, 6)],
    },
    "cargo_hold": {
        "doors": [(4, 0), (4, 7), (0, 4)],
        "noisy": [(3, 2), (5, 5), (3, 5)],
        # Cargo crates — scattered cover blocks
        "interior_walls": [(2, 2), (3, 2), (5, 5), (6, 5), (2, 5)],
    },
    "server_room": {
        "doors": [(4, 0), (4, 7)],
        "noisy": [(3, 4), (5, 4)],
        # Server rack rows
        "interior_walls": [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)],
    },
    "workshop": {
        "doors": [(0, 4), (7, 4)],
        "noisy": [(4, 2), (4, 5)],
        # Workbenches and machinery
        "interior_walls": [(3, 2), (3, 3), (5, 5), (5, 6)],
    },
}


def _create_l_bend() -> ChunkTemplate:
    """Create an L-shaped connector chunk (7x7)."""
    w, h = 7, 7
    tiles: list[list[TileType]] = [[TileType.WALL] * w for _ in range(h)]
    # Horizontal arm (top, rows 2-3)
    for x in range(w):
        tiles[2][x] = TileType.FLOOR
        tiles[3][x] = TileType.FLOOR
    # Vertical arm (right, cols 4-5)
    for y in range(h):
        tiles[y][4] = TileType.FLOOR
        tiles[y][3] = TileType.FLOOR
    return ChunkTemplate(
        id="l_bend",
        width=w,
        height=h,
        category=ChunkCategory.CONNECTOR,
        tiles=tiles,
        exits={"west": (0, 2), "south": (4, h - 1)},
    )


# ---------------------------------------------------------------------------
# MapGenConfig & MapGenResult
# ---------------------------------------------------------------------------


@dataclass
class MapGenConfig:
    """Configuration for procedural map generation."""

    mission_type: MissionType
    difficulty: DifficultyTier
    seed: int
    faction_id: Optional[str] = None


@dataclass
class MapGenResult:
    """Output of the map generation process."""

    ground_map: GroundMap
    enemies: list[GroundEnemy]
    config: MapGenConfig
    placed_chunks: list[tuple[str, int, int]] = field(default_factory=list)
    """List of (chunk_id, grid_x, grid_y) for each placed chunk template."""
    interactables: list[GroundInteractable] = field(default_factory=list)
    story_triggers: list[GroundStoryTrigger] = field(default_factory=list)

    def build_mission_state(
        self,
        crew_bonuses: Optional[GroundCrewBonuses] = None,
        attributes: Optional[AttributeSheet] = None,
        progression: Optional[PlayerProgression] = None,
    ) -> GroundMissionState:
        """Build a full mission state from the generated map and enemies.

        Args:
            crew_bonuses: Pre-computed crew bonuses for this mission.
            attributes: Player's attribute sheet.
            progression: Player's skill progression.

        Returns:
            GroundMissionState ready for play.
        """
        ex, ey = self.ground_map.entrance_pos
        player = GroundPlayerState(x=ex, y=ey)
        return GroundMissionState(
            ground_map=self.ground_map,
            player=player,
            enemies=list(self.enemies),
            crew_bonuses=crew_bonuses or GroundCrewBonuses(),
            attributes=attributes,
            progression=progression,
            interactables=list(self.interactables),
            story_triggers=list(self.story_triggers),
        )


# ---------------------------------------------------------------------------
# Enemy template IDs by rough strength tier
# ---------------------------------------------------------------------------

_WEAK_ENEMIES = ["union_worker", "station_sentry"]
_MEDIUM_ENEMIES = ["guild_security", "alliance_scrapper", "collective_drone"]
_STRONG_ENEMIES = ["pirate_thug", "crimson_enforcer", "elite_guard"]

# Faction-specific enemy pools (faction_id -> list of template IDs)
_FACTION_ENEMIES: dict[str, list[str]] = {
    "merchants_guild": ["guild_security", "guild_security", "station_sentry", "elite_guard"],
    "miners_union": ["union_worker", "union_worker", "alliance_scrapper", "pirate_thug"],
    "science_collective": ["collective_drone", "collective_drone", "station_sentry", "elite_guard"],
    "frontier_alliance": ["alliance_scrapper", "pirate_thug", "crimson_enforcer", "union_worker"],
}


# ---------------------------------------------------------------------------
# GroundMapGenerator
# ---------------------------------------------------------------------------


class GroundMapGenerator:
    """Procedural ground map generator.

    Uses a room-placement + corridor-carving approach:
    1. Start with a wall-filled grid
    2. Place rooms at random positions (non-overlapping)
    3. Connect rooms with corridors to ensure a critical path
    4. Place entrance and exit in the first and last rooms
    5. Add doors at room-corridor junctions
    6. Scatter noisy floor tiles
    7. Place enemies with patrol routes
    """

    def __init__(self, library: Optional[ChunkLibrary] = None) -> None:
        self._library = library or ChunkLibrary.create_default()

    def generate(self, config: MapGenConfig) -> MapGenResult:
        """Generate a complete ground map with enemies.

        Args:
            config: Generation parameters (mission type, difficulty, seed).

        Returns:
            MapGenResult with ground_map and enemies.
        """
        rng = random.Random(config.seed)
        tier = config.difficulty

        w = tier.map_width
        h = tier.map_height

        # Mission type adjustments
        if config.mission_type == MissionType.EXPLORATION:
            # Exploration maps are wider for more coverage gameplay
            w = min(w + 4, 34)
            h = min(h + 4, 34)
        elif config.mission_type == MissionType.EXTRACTION:
            # Extraction maps are tall for distance
            h = min(h + 2, 34)

        # 1. Initialize wall-filled grid
        tiles = [[GroundTile(tile_type=TileType.WALL) for _ in range(w)] for _ in range(h)]

        # 2. Place rooms using chunk templates
        rooms, placed_chunks = self._place_rooms(tiles, w, h, tier, rng)

        # 3. Connect rooms with corridors (ensure critical path)
        self._connect_rooms(tiles, rooms, w, h, rng)

        # 4. Place entrance and exit
        entrance_pos, exit_pos = self._place_entrance_exit(rooms, w, h, rng)

        # Set entrance/exit tile types
        tiles[entrance_pos[1]][entrance_pos[0]].tile_type = TileType.ENTRANCE
        tiles[exit_pos[1]][exit_pos[0]].tile_type = TileType.EXIT

        # 5. Add doors at room-corridor junctions
        self._place_doors(tiles, rooms, w, h, rng)

        # 6. Scatter noisy floor
        self._place_noisy_floor(tiles, w, h, rng, tier)

        # 6b. Scatter hazard and vent tiles
        self._place_hazards(tiles, w, h, rng, tier)
        self._place_vents(tiles, w, h, rng, tier, entrance_pos, exit_pos)

        # 7. Build the GroundMap
        ground_map = GroundMap(
            width=w,
            height=h,
            tiles=tiles,
            entrance_pos=entrance_pos,
            exit_pos=exit_pos,
        )

        # 8. Place enemies with patrol routes
        enemies = self._place_enemies(ground_map, rooms, entrance_pos, tier, rng, config)

        return MapGenResult(
            ground_map=ground_map,
            enemies=enemies,
            config=config,
            placed_chunks=placed_chunks,
        )

    # === Room Placement ===

    def _place_rooms(
        self,
        tiles: list[list[GroundTile]],
        map_w: int,
        map_h: int,
        tier: DifficultyTier,
        rng: random.Random,
    ) -> tuple[list[tuple[int, int, int, int]], list[tuple[str, int, int]]]:
        """Place non-overlapping rooms on the grid using chunk templates.

        Returns:
            Tuple of (room bounding boxes, placed chunk records).
        """
        min_rooms, max_rooms = tier.room_count_range
        target_count = rng.randint(min_rooms, max_rooms)
        rooms: list[tuple[int, int, int, int]] = []
        placed: list[tuple[str, int, int]] = []

        # Get available room templates
        room_templates = self._library.get_by_category(ChunkCategory.ROOM)

        for _ in range(target_count * 10):  # Up to 10x attempts
            if len(rooms) >= target_count:
                break

            # Pick a random room template
            if room_templates:
                chunk = rng.choice(room_templates)
                rw = chunk.width
                rh = chunk.height
            else:
                chunk = None
                rw = rng.choice([6, 7, 8])
                rh = rng.choice([6, 7, 8])

            # Random position with 1-tile border margin
            if map_w - rw - 1 < 1 or map_h - rh - 1 < 1:
                continue
            rx = rng.randint(1, map_w - rw - 1)
            ry = rng.randint(1, map_h - rh - 1)

            # Check overlap with existing rooms (with 1-tile gap)
            overlap = False
            for ex, ey, ew, eh in rooms:
                if rx - 1 < ex + ew and rx + rw + 1 > ex and ry - 1 < ey + eh and ry + rh + 1 > ey:
                    overlap = True
                    break

            if not overlap:
                rooms.append((rx, ry, rw, rh))
                if chunk is not None:
                    self._stamp_chunk(tiles, chunk, rx, ry)
                    placed.append((chunk.id, rx, ry))
                else:
                    self._carve_room(tiles, rx, ry, rw, rh)
                    placed.append(("generic", rx, ry))

        return rooms, placed

    def _stamp_chunk(
        self,
        tiles: list[list[GroundTile]],
        chunk: ChunkTemplate,
        ox: int,
        oy: int,
    ) -> None:
        """Stamp a chunk template onto the tile grid at offset (ox, oy).

        Copies all tile types from the chunk, preserving interior features
        like walls, noisy floor, and doors.
        """
        for cy in range(chunk.height):
            for cx in range(chunk.width):
                tx, ty = ox + cx, oy + cy
                if 0 <= ty < len(tiles) and 0 <= tx < len(tiles[0]):
                    tiles[ty][tx].tile_type = chunk.tiles[cy][cx]

    def _carve_room(
        self,
        tiles: list[list[GroundTile]],
        rx: int,
        ry: int,
        rw: int,
        rh: int,
    ) -> None:
        """Carve a plain rectangular room (fallback when no templates available)."""
        for dy in range(rh):
            for dx in range(rw):
                tx, ty = rx + dx, ry + dy
                if dx == 0 or dx == rw - 1 or dy == 0 or dy == rh - 1:
                    tiles[ty][tx].tile_type = TileType.WALL
                else:
                    tiles[ty][tx].tile_type = TileType.FLOOR

    # === Corridor Connection ===

    def _connect_rooms(
        self,
        tiles: list[list[GroundTile]],
        rooms: list[tuple[int, int, int, int]],
        map_w: int,
        map_h: int,
        rng: random.Random,
    ) -> None:
        """Connect all rooms with L-shaped corridors ensuring connectivity."""
        if len(rooms) < 2:
            return

        # Sort rooms by x position for more natural corridor layout
        sorted_rooms = sorted(rooms, key=lambda r: r[0] + r[1])

        # Connect each room to the next (chain connectivity)
        for i in range(len(sorted_rooms) - 1):
            r1 = sorted_rooms[i]
            r2 = sorted_rooms[i + 1]
            self._carve_corridor(tiles, r1, r2, map_w, map_h, rng)

        # Add 1-2 extra connections for alternate routes
        if len(sorted_rooms) >= 4:
            extras = rng.randint(1, min(2, len(sorted_rooms) // 2))
            for _ in range(extras):
                a = rng.randint(0, len(sorted_rooms) - 1)
                b = rng.randint(0, len(sorted_rooms) - 1)
                if a != b:
                    self._carve_corridor(
                        tiles,
                        sorted_rooms[a],
                        sorted_rooms[b],
                        map_w,
                        map_h,
                        rng,
                    )

    def _find_floor_in_room(
        self,
        tiles: list[list[GroundTile]],
        rx: int,
        ry: int,
        rw: int,
        rh: int,
    ) -> tuple[int, int]:
        """Find a floor tile inside a room, starting from center outward."""
        cx, cy = rx + rw // 2, ry + rh // 2
        # Try center first
        if tiles[cy][cx].tile_type == TileType.FLOOR:
            return cx, cy
        # Spiral outward within room interior
        for dy in range(1, rh // 2):
            for dx in range(1, rw // 2):
                for sx, sy in [
                    (cx + dx, cy + dy),
                    (cx - dx, cy + dy),
                    (cx + dx, cy - dy),
                    (cx - dx, cy - dy),
                ]:
                    if rx < sx < rx + rw - 1 and ry < sy < ry + rh - 1:
                        if tiles[sy][sx].tile_type == TileType.FLOOR:
                            return sx, sy
        # Fallback: use center anyway (corridor will carve through)
        return cx, cy

    def _carve_corridor(
        self,
        tiles: list[list[GroundTile]],
        r1: tuple[int, int, int, int],
        r2: tuple[int, int, int, int],
        map_w: int,
        map_h: int,
        rng: random.Random,
    ) -> None:
        """Carve an L-shaped corridor between two rooms."""
        # Find clear floor tile in each room for connection
        x1, y1 = self._find_floor_in_room(tiles, *r1)
        x2, y2 = self._find_floor_in_room(tiles, *r2)

        # L-shaped: go horizontal first, then vertical (or vice versa)
        if rng.random() < 0.5:
            self._carve_h_then_v(tiles, x1, y1, x2, y2, map_w, map_h)
        else:
            self._carve_v_then_h(tiles, x1, y1, x2, y2, map_w, map_h)

    def _carve_h_then_v(
        self,
        tiles: list[list[GroundTile]],
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        map_w: int,
        map_h: int,
    ) -> None:
        """Carve horizontal then vertical corridor."""
        sx = min(x1, x2)
        ex = max(x1, x2)
        for x in range(sx, ex + 1):
            self._carve_corridor_tile(tiles, x, y1, map_w, map_h)

        sy = min(y1, y2)
        ey = max(y1, y2)
        for y in range(sy, ey + 1):
            self._carve_corridor_tile(tiles, x2, y, map_w, map_h)

    def _carve_v_then_h(
        self,
        tiles: list[list[GroundTile]],
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        map_w: int,
        map_h: int,
    ) -> None:
        """Carve vertical then horizontal corridor."""
        sy = min(y1, y2)
        ey = max(y1, y2)
        for y in range(sy, ey + 1):
            self._carve_corridor_tile(tiles, x1, y, map_w, map_h)

        sx = min(x1, x2)
        ex = max(x1, x2)
        for x in range(sx, ex + 1):
            self._carve_corridor_tile(tiles, x, y2, map_w, map_h)

    def _carve_corridor_tile(
        self,
        tiles: list[list[GroundTile]],
        x: int,
        y: int,
        map_w: int,
        map_h: int,
    ) -> None:
        """Carve a single corridor tile (skip map border).

        Converts wall tiles to floor. Preserves doors, noisy floor,
        entrance, and exit tiles.
        """
        if 1 <= x < map_w - 1 and 1 <= y < map_h - 1:
            current = tiles[y][x].tile_type
            if current in (TileType.WALL, TileType.DOOR_CLOSED):
                tiles[y][x].tile_type = TileType.FLOOR

    # === Entrance / Exit Placement ===

    def _place_entrance_exit(
        self,
        rooms: list[tuple[int, int, int, int]],
        map_w: int,
        map_h: int,
        rng: random.Random,
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """Place entrance and exit in rooms maximizing distance.

        Returns (entrance_pos, exit_pos).
        """
        if not rooms:
            return (1, 1), (map_w - 2, map_h - 2)

        # Find the two rooms with maximum Manhattan distance
        best_dist = 0
        best_pair = (0, len(rooms) - 1)
        for i in range(len(rooms)):
            for j in range(i + 1, len(rooms)):
                r1, r2 = rooms[i], rooms[j]
                cx1 = r1[0] + r1[2] // 2
                cy1 = r1[1] + r1[3] // 2
                cx2 = r2[0] + r2[2] // 2
                cy2 = r2[1] + r2[3] // 2
                dist = abs(cx2 - cx1) + abs(cy2 - cy1)
                if dist > best_dist:
                    best_dist = dist
                    best_pair = (i, j)

        r_start = rooms[best_pair[0]]
        r_end = rooms[best_pair[1]]

        entrance = (r_start[0] + 1, r_start[1] + 1)
        exit_pos = (r_end[0] + r_end[2] - 2, r_end[1] + r_end[3] - 2)

        return entrance, exit_pos

    # === Door Placement ===

    def _place_doors(
        self,
        tiles: list[list[GroundTile]],
        rooms: list[tuple[int, int, int, int]],
        map_w: int,
        map_h: int,
        rng: random.Random,
    ) -> None:
        """Place doors where corridors meet room walls."""
        for rx, ry, rw, rh in rooms:
            # Check each room border tile
            for dx in range(rw):
                for dy in range(rh):
                    if dx != 0 and dx != rw - 1 and dy != 0 and dy != rh - 1:
                        continue  # Skip interior
                    tx, ty = rx + dx, ry + dy
                    if tiles[ty][tx].tile_type != TileType.WALL:
                        continue

                    # Check if this wall tile has corridor floor adjacent
                    # on the outside of the room
                    if self._is_room_corridor_junction(tiles, tx, ty, rx, ry, rw, rh, map_w, map_h):
                        # Only place door with some probability
                        if rng.random() < 0.6:
                            tiles[ty][tx].tile_type = TileType.DOOR_CLOSED

    def _is_room_corridor_junction(
        self,
        tiles: list[list[GroundTile]],
        tx: int,
        ty: int,
        rx: int,
        ry: int,
        rw: int,
        rh: int,
        map_w: int,
        map_h: int,
    ) -> bool:
        """Check if a wall tile is between a room interior and a corridor."""
        # Find direction from room center to this tile
        # Check the outside neighbor
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            ox, oy = tx + dx, ty + dy
            ix, iy = tx - dx, ty - dy

            # Outside must be in bounds and be floor (corridor)
            if not (0 <= ox < map_w and 0 <= oy < map_h):
                continue
            if tiles[oy][ox].tile_type != TileType.FLOOR:
                continue

            # Outside must actually be outside the room
            if rx <= ox < rx + rw and ry <= oy < ry + rh:
                continue

            # Inside must be in bounds and be floor (room interior)
            if not (0 <= ix < map_w and 0 <= iy < map_h):
                continue
            if tiles[iy][ix].tile_type != TileType.FLOOR:
                continue

            # Inside must be inside the room
            if rx < ix < rx + rw - 1 and ry < iy < ry + rh - 1:
                return True

        return False

    # === Noisy Floor Placement ===

    def _place_noisy_floor(
        self,
        tiles: list[list[GroundTile]],
        map_w: int,
        map_h: int,
        rng: random.Random,
        tier: DifficultyTier,
    ) -> None:
        """Scatter noisy floor tiles in corridors and rooms."""
        # Higher difficulty = more noisy tiles
        noisy_target = rng.randint(3, 5 + tier.enemy_count_min)

        floor_tiles: list[tuple[int, int]] = []
        for y in range(1, map_h - 1):
            for x in range(1, map_w - 1):
                if tiles[y][x].tile_type == TileType.FLOOR:
                    floor_tiles.append((x, y))

        if floor_tiles:
            rng.shuffle(floor_tiles)
            for x, y in floor_tiles[:noisy_target]:
                tiles[y][x].tile_type = TileType.NOISY_FLOOR

    # === Hazard & Vent Placement ===

    def _place_hazards(
        self,
        tiles: list[list[GroundTile]],
        map_w: int,
        map_h: int,
        rng: random.Random,
        tier: DifficultyTier,
    ) -> None:
        """Scatter hazard tiles on floor spaces. Higher difficulty = more hazards."""
        hazard_target = rng.randint(1, 2 + tier.enemy_count_min // 2)

        floor_tiles: list[tuple[int, int]] = []
        for y in range(1, map_h - 1):
            for x in range(1, map_w - 1):
                if tiles[y][x].tile_type == TileType.FLOOR:
                    floor_tiles.append((x, y))

        if floor_tiles:
            rng.shuffle(floor_tiles)
            for x, y in floor_tiles[:hazard_target]:
                tiles[y][x].tile_type = TileType.HAZARD

    def _place_vents(
        self,
        tiles: list[list[GroundTile]],
        map_w: int,
        map_h: int,
        rng: random.Random,
        tier: DifficultyTier,
        entrance_pos: tuple[int, int],
        exit_pos: tuple[int, int],
    ) -> None:
        """Place vent tiles along walls to create vision-blocking obstacles.

        Verifies each placement doesn't block the entrance-to-exit path.
        """
        vent_target = rng.randint(1, 2 + tier.enemy_count_min // 3)

        candidates: list[tuple[int, int]] = []
        for y in range(1, map_h - 1):
            for x in range(1, map_w - 1):
                if tiles[y][x].tile_type != TileType.FLOOR:
                    continue
                # Only place vents adjacent to walls
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < map_w and 0 <= ny < map_h:
                        if tiles[ny][nx].tile_type == TileType.WALL:
                            candidates.append((x, y))
                            break

        if candidates:
            rng.shuffle(candidates)
            placed = 0
            for x, y in candidates:
                if placed >= vent_target:
                    break
                # Tentatively place vent and check path connectivity
                tiles[y][x].tile_type = TileType.VENT
                if self._has_walkable_path(tiles, map_w, map_h, entrance_pos, exit_pos):
                    placed += 1
                else:
                    # Revert — this vent would block the critical path
                    tiles[y][x].tile_type = TileType.FLOOR

    @staticmethod
    def _has_walkable_path(
        tiles: list[list[GroundTile]],
        map_w: int,
        map_h: int,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> bool:
        """BFS check for walkable path between two positions."""
        visited: set[tuple[int, int]] = {start}
        queue = [start]
        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) == end:
                return True
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited:
                    continue
                if 0 <= nx < map_w and 0 <= ny < map_h:
                    if tiles[ny][nx].tile_type in _WALKABLE_TYPES:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return False

    # === Enemy Placement ===

    def _place_enemies(
        self,
        ground_map: GroundMap,
        rooms: list[tuple[int, int, int, int]],
        entrance_pos: tuple[int, int],
        tier: DifficultyTier,
        rng: random.Random,
        config: MapGenConfig,
    ) -> list[GroundEnemy]:
        """Place enemies with patrol routes on the map."""
        count = rng.randint(tier.enemy_count_min, tier.enemy_count_max)

        # Collect all walkable floor positions (not near entrance)
        floor_positions: list[tuple[int, int]] = []
        for y in range(1, ground_map.height - 1):
            for x in range(1, ground_map.width - 1):
                if not ground_map.is_walkable(x, y):
                    continue
                dist = abs(x - entrance_pos[0]) + abs(y - entrance_pos[1])
                if dist >= 5:
                    floor_positions.append((x, y))

        if not floor_positions:
            return []

        # Select enemy template IDs based on difficulty and faction
        template_pool = self._build_template_pool(tier, rng, config.faction_id)

        # Pick random speeds
        speed_pool: list[int] = []
        for speed, weight in tier.enemy_speed_weights:
            speed_pool.extend([speed] * weight)

        enemies: list[GroundEnemy] = []
        rng.shuffle(floor_positions)

        for i in range(min(count, len(floor_positions))):
            ex, ey = floor_positions[i]
            template_id = rng.choice(template_pool)
            template = GROUND_ENEMY_TEMPLATES.get(
                template_id, GROUND_ENEMY_TEMPLATES["guild_security"]
            )
            speed = rng.choice(speed_pool)
            facing = rng.choice(list(Direction))

            # Generate a patrol route near this position
            patrol = self._generate_patrol_route(ground_map, ex, ey, rng)

            loot = int(template.get("loot_credits", 20) * tier.loot_multiplier)

            enemies.append(
                GroundEnemy(
                    id=f"enemy_{i}",
                    x=ex,
                    y=ey,
                    facing=facing,
                    speed=speed,
                    patrol_route=patrol,
                    loot_credits=loot,
                    template_id=template_id,
                )
            )

        return enemies

    def _build_template_pool(
        self,
        tier: DifficultyTier,
        rng: random.Random,
        faction_id: Optional[str] = None,
    ) -> list[str]:
        """Build a weighted pool of enemy template IDs for this tier.

        Uses faction-specific enemies when faction_id is provided.
        """
        if faction_id and faction_id in _FACTION_ENEMIES:
            return _FACTION_ENEMIES[faction_id]

        if tier == DifficultyTier.LOW:
            return _WEAK_ENEMIES * 3 + _MEDIUM_ENEMIES
        elif tier == DifficultyTier.MODERATE:
            return _WEAK_ENEMIES + _MEDIUM_ENEMIES * 3
        elif tier == DifficultyTier.HIGH:
            return _MEDIUM_ENEMIES * 2 + _STRONG_ENEMIES * 2
        else:  # EXTREME
            return _MEDIUM_ENEMIES + _STRONG_ENEMIES * 3

    def _generate_patrol_route(
        self,
        ground_map: GroundMap,
        start_x: int,
        start_y: int,
        rng: random.Random,
    ) -> list[tuple[int, int]]:
        """Generate a patrol route starting from a position.

        Creates a 2-4 point route using walkable tiles nearby.
        """
        route: list[tuple[int, int]] = [(start_x, start_y)]
        current_x, current_y = start_x, start_y
        num_points = rng.randint(2, 4)

        for _ in range(num_points - 1):
            # Try to find a walkable tile 3-6 tiles away
            best: Optional[tuple[int, int]] = None
            best_dist = 0

            for _attempt in range(20):
                dx = rng.randint(-6, 6)
                dy = rng.randint(-6, 6)
                nx, ny = current_x + dx, current_y + dy

                if not ground_map.is_walkable(nx, ny):
                    continue

                # Don't overlap with existing route points
                if (nx, ny) in route:
                    continue

                dist = abs(dx) + abs(dy)
                if dist >= 3 and dist > best_dist:
                    best = (nx, ny)
                    best_dist = dist

            if best is not None:
                route.append(best)
                current_x, current_y = best

        # If we only got the start point, add a nearby point
        if len(route) < 2:
            for dx, dy in [(3, 0), (0, 3), (-3, 0), (0, -3), (2, 2), (-2, -2)]:
                nx, ny = start_x + dx, start_y + dy
                if ground_map.is_walkable(nx, ny):
                    route.append((nx, ny))
                    break

        # Last resort: duplicate start with offset
        if len(route) < 2:
            for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                nx, ny = start_x + dx, start_y + dy
                if ground_map.is_walkable(nx, ny):
                    route.append((nx, ny))
                    break

        return route
