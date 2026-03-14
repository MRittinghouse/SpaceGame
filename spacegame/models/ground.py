"""Ground exploration models.

Core data types for the turn-based grid exploration system: tile types,
fog of war, map structure, and player ground state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from spacegame.config import GROUND_BASE_VISION_RADIUS


class TileType(Enum):
    """Types of tiles in a ground exploration map."""

    FLOOR = "floor"
    WALL = "wall"
    DOOR_CLOSED = "door_closed"
    DOOR_OPEN = "door_open"
    EXIT = "exit"
    ENTRANCE = "entrance"
    NOISY_FLOOR = "noisy_floor"
    TERMINAL = "terminal"
    HAZARD = "hazard"
    VENT = "vent"


class FogState(Enum):
    """Visibility state of a tile from the player's perspective."""

    UNEXPLORED = "unexplored"
    EXPLORED = "explored"
    VISIBLE = "visible"


_WALKABLE_TYPES = frozenset({
    TileType.FLOOR,
    TileType.DOOR_OPEN,
    TileType.EXIT,
    TileType.ENTRANCE,
    TileType.NOISY_FLOOR,
    TileType.TERMINAL,
    TileType.HAZARD,
})

_VISION_BLOCKING_TYPES = frozenset({
    TileType.WALL,
    TileType.DOOR_CLOSED,
    TileType.VENT,
})


@dataclass
class GroundTile:
    """A single tile in a ground exploration map."""

    tile_type: TileType
    fog_state: FogState = FogState.UNEXPLORED

    @property
    def is_walkable(self) -> bool:
        """Whether the player can move onto this tile."""
        return self.tile_type in _WALKABLE_TYPES

    @property
    def blocks_vision(self) -> bool:
        """Whether this tile blocks line of sight."""
        return self.tile_type in _VISION_BLOCKING_TYPES

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "tile_type": self.tile_type.value,
            "fog_state": self.fog_state.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundTile:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with tile_type and fog_state.

        Returns:
            GroundTile instance.
        """
        return cls(
            tile_type=TileType(data["tile_type"]),
            fog_state=FogState(data.get("fog_state", "unexplored")),
        )


@dataclass
class GroundMap:
    """A grid of tiles representing a ground exploration area.

    Tiles are stored in row-major order: tiles[y][x].
    """

    width: int
    height: int
    tiles: list[list[GroundTile]]
    entrance_pos: tuple[int, int]
    exit_pos: tuple[int, int]

    def get_tile(self, x: int, y: int) -> Optional[GroundTile]:
        """Get tile at position, or None if out of bounds.

        Args:
            x: Horizontal position (column).
            y: Vertical position (row).

        Returns:
            GroundTile at position, or None if out of bounds.
        """
        if not self.is_in_bounds(x, y):
            return None
        return self.tiles[y][x]

    def is_in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within map boundaries."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile exists and is walkable."""
        tile = self.get_tile(x, y)
        return tile is not None and tile.is_walkable

    def open_door(self, x: int, y: int) -> tuple[bool, str]:
        """Open a closed door at the given position.

        Args:
            x: Door x position.
            y: Door y position.

        Returns:
            Tuple of (success, message).
        """
        tile = self.get_tile(x, y)
        if tile is None:
            return False, "Position is out of bounds"
        if tile.tile_type != TileType.DOOR_CLOSED:
            return False, "Not a closed door"
        tile.tile_type = TileType.DOOR_OPEN
        return True, "Door opened"

    def has_line_of_sight(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if there is a clear line of sight between two positions.

        Uses Bresenham's line algorithm. The source and destination tiles
        themselves do not block the check — only intermediate tiles matter.

        Args:
            x1: Source x.
            y1: Source y.
            x2: Target x.
            y2: Target y.

        Returns:
            True if line of sight is clear.
        """
        if x1 == x2 and y1 == y2:
            return True

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        cx, cy = x1, y1
        while True:
            # Check intermediate tiles (not source, not destination)
            if (cx, cy) != (x1, y1) and (cx, cy) != (x2, y2):
                tile = self.get_tile(cx, cy)
                if tile is None or tile.blocks_vision:
                    return False

            if cx == x2 and cy == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

        return True

    def update_fog_of_war(
        self, player_x: int, player_y: int, vision_radius: int
    ) -> None:
        """Update fog state based on player position and vision.

        All currently VISIBLE tiles become EXPLORED, then tiles within
        the vision radius with clear line of sight become VISIBLE.

        Args:
            player_x: Player x position.
            player_y: Player y position.
            vision_radius: How far the player can see in tiles.
        """
        # Demote all visible tiles to explored
        for row in self.tiles:
            for tile in row:
                if tile.fog_state == FogState.VISIBLE:
                    tile.fog_state = FogState.EXPLORED

        # Mark tiles within vision radius as visible if LOS is clear
        for dy in range(-vision_radius, vision_radius + 1):
            for dx in range(-vision_radius, vision_radius + 1):
                tx = player_x + dx
                ty = player_y + dy
                if not self.is_in_bounds(tx, ty):
                    continue
                # Use Chebyshev distance (square radius)
                if max(abs(dx), abs(dy)) > vision_radius:
                    continue
                if self.has_line_of_sight(player_x, player_y, tx, ty):
                    self.tiles[ty][tx].fog_state = FogState.VISIBLE

    def to_dict(self) -> dict:
        """Serialize map to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": [
                [tile.to_dict() for tile in row] for row in self.tiles
            ],
            "entrance_pos": list(self.entrance_pos),
            "exit_pos": list(self.exit_pos),
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundMap:
        """Deserialize map from dictionary.

        Args:
            data: Dictionary with width, height, tiles, entrance_pos, exit_pos.

        Returns:
            GroundMap instance.
        """
        tiles = [
            [GroundTile.from_dict(td) for td in row]
            for row in data["tiles"]
        ]
        return cls(
            width=data["width"],
            height=data["height"],
            tiles=tiles,
            entrance_pos=tuple(data["entrance_pos"]),
            exit_pos=tuple(data["exit_pos"]),
        )

    @classmethod
    def create_test_map(cls, width: int = 10, height: int = 10) -> GroundMap:
        """Create a simple test map with wall border and floor interior.

        Entrance at (1, 1), exit at (width-2, height-2).

        Args:
            width: Map width in tiles.
            height: Map height in tiles.

        Returns:
            GroundMap with wall borders and floor interior.
        """
        tiles: list[list[GroundTile]] = []
        entrance_pos = (1, 1)
        exit_pos = (width - 2, height - 2)

        for y in range(height):
            row: list[GroundTile] = []
            for x in range(width):
                if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                    row.append(GroundTile(tile_type=TileType.WALL))
                elif (x, y) == entrance_pos:
                    row.append(GroundTile(tile_type=TileType.ENTRANCE))
                elif (x, y) == exit_pos:
                    row.append(GroundTile(tile_type=TileType.EXIT))
                else:
                    row.append(GroundTile(tile_type=TileType.FLOOR))
            tiles.append(row)

        return cls(
            width=width,
            height=height,
            tiles=tiles,
            entrance_pos=entrance_pos,
            exit_pos=exit_pos,
        )


@dataclass
class GroundPlayerState:
    """Player state during ground exploration.

    Tracks position, vision, and turn count. Ephemeral — exists only
    during an active ground mission.
    """

    x: int
    y: int
    vision_radius: int = GROUND_BASE_VISION_RADIUS
    turn_number: int = 0

    def move(self, dx: int, dy: int, ground_map: GroundMap) -> tuple[bool, str]:
        """Attempt to move by (dx, dy).

        Only cardinal movement is allowed (exactly one of dx/dy non-zero,
        magnitude 1).

        Args:
            dx: Horizontal movement (-1, 0, or 1).
            dy: Vertical movement (-1, 0, or 1).
            ground_map: The current ground map.

        Returns:
            Tuple of (success, message).
        """
        # Validate cardinal movement
        if abs(dx) + abs(dy) != 1:
            if dx == 0 and dy == 0:
                return False, "No movement specified"
            return False, "Only cardinal movement allowed (no diagonal)"

        new_x = self.x + dx
        new_y = self.y + dy

        if not ground_map.is_walkable(new_x, new_y):
            tile = ground_map.get_tile(new_x, new_y)
            if tile is None:
                return False, "Cannot move out of bounds"
            return False, f"Cannot move onto {tile.tile_type.value}"

        self.x = new_x
        self.y = new_y
        self.turn_number += 1

        tile = ground_map.get_tile(new_x, new_y)
        if tile is not None and tile.tile_type == TileType.HAZARD:
            return True, "Moved onto hazard — taking damage!"

        return True, "Moved"

    def wait(self) -> None:
        """Skip turn without moving."""
        self.turn_number += 1

    def interact(
        self,
        ground_map: GroundMap,
        target_x: int,
        target_y: int,
        interactables: Optional[list[GroundInteractable]] = None,
    ) -> tuple[bool, str]:
        """Interact with a tile or object at the target position.

        Must be adjacent (Manhattan distance 1). Supports door opening
        and loot container interaction.

        Args:
            ground_map: The current ground map.
            target_x: Target tile x position.
            target_y: Target tile y position.
            interactables: Optional list of interactables on the map.

        Returns:
            Tuple of (success, message).
        """
        # Check adjacency (Manhattan distance must be 1)
        dist = abs(target_x - self.x) + abs(target_y - self.y)
        if dist != 1:
            return False, "Target is too far away (must be adjacent)"

        tile = ground_map.get_tile(target_x, target_y)
        if tile is None:
            return False, "Target is out of bounds"

        # Door interaction
        if tile.tile_type == TileType.DOOR_CLOSED:
            success, msg = ground_map.open_door(target_x, target_y)
            if success:
                self.turn_number += 1
            return success, msg

        # Terminal interaction
        if tile.tile_type == TileType.TERMINAL:
            self.turn_number += 1
            return True, "Accessed terminal"

        # Check for interactable at target position
        if interactables is not None:
            for obj in interactables:
                if obj.x == target_x and obj.y == target_y and not obj.looted:
                    credits = obj.loot()
                    self.turn_number += 1
                    return True, f"Looted {credits} credits"

        return False, "Nothing to interact with"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "vision_radius": self.vision_radius,
            "turn_number": self.turn_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundPlayerState:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with x, y, vision_radius, turn_number.

        Returns:
            GroundPlayerState instance.
        """
        return cls(
            x=data["x"],
            y=data["y"],
            vision_radius=data.get("vision_radius", GROUND_BASE_VISION_RADIUS),
            turn_number=data.get("turn_number", 0),
        )


@dataclass
class GroundInteractable:
    """An interactable object on the ground map (loot container, terminal, etc.).

    Tracks position, type, loot value, and whether it has been looted.
    """

    x: int
    y: int
    interact_type: str
    loot_credits: int = 0
    description: str = ""
    looted: bool = False

    def loot(self) -> int:
        """Collect loot from this interactable.

        Returns:
            Credits looted, or 0 if already looted.
        """
        if self.looted:
            return 0
        self.looted = True
        return self.loot_credits

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "interact_type": self.interact_type,
            "loot_credits": self.loot_credits,
            "description": self.description,
            "looted": self.looted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundInteractable:
        """Deserialize from dictionary."""
        return cls(
            x=data["x"],
            y=data["y"],
            interact_type=data.get("interact_type", "loot_container"),
            loot_credits=data.get("loot_credits", 0),
            description=data.get("description", ""),
            looted=data.get("looted", False),
        )


@dataclass
class GroundStoryTrigger:
    """A position-based narrative trigger on the ground map.

    Fires once when the player steps on the tile, displaying
    atmospheric text.
    """

    x: int
    y: int
    trigger_type: str
    text: str
    triggered: bool = False

    def fire(self) -> Optional[str]:
        """Fire this trigger.

        Returns:
            The trigger text, or None if already triggered.
        """
        if self.triggered:
            return None
        self.triggered = True
        return self.text

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "trigger_type": self.trigger_type,
            "text": self.text,
            "triggered": self.triggered,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundStoryTrigger:
        """Deserialize from dictionary."""
        return cls(
            x=data["x"],
            y=data["y"],
            trigger_type=data.get("trigger_type", "atmosphere"),
            text=data.get("text", ""),
            triggered=data.get("triggered", False),
        )
