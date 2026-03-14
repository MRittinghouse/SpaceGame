"""Campaign map loading and building.

Converts hand-authored JSON campaign maps into the same MapGenResult
output that the procedural GroundMapGenerator produces, so the game
engine can use either source interchangeably.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from spacegame.models.ground import (
    GroundInteractable,
    GroundMap,
    GroundStoryTrigger,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import Direction, GroundEnemy
from spacegame.models.ground_mapgen import (
    DifficultyTier,
    MapGenConfig,
    MapGenResult,
    MissionType,
)
from spacegame.models.ground_combat import GROUND_ENEMY_TEMPLATES


# Single-character tile codes used in campaign map JSON
TILE_CODE_MAP: dict[str, TileType] = {
    "W": TileType.WALL,
    "F": TileType.FLOOR,
    "D": TileType.DOOR_CLOSED,
    "E": TileType.ENTRANCE,
    "X": TileType.EXIT,
    "N": TileType.NOISY_FLOOR,
    "T": TileType.TERMINAL,
    "H": TileType.HAZARD,
    "V": TileType.VENT,
}


@dataclass
class CampaignMapData:
    """Parsed campaign map definition from JSON.

    Holds the raw layout, enemy placements, and metadata before
    conversion into a playable GroundMap.
    """

    id: str
    name: str
    width: int
    height: int
    mission_type: MissionType
    difficulty: DifficultyTier
    faction_id: str
    tiles: list[list[str]]
    entrance: tuple[int, int]
    exit: tuple[int, int]
    enemies: list[dict] = field(default_factory=list)
    interactables: list[dict] = field(default_factory=list)
    story_triggers: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> CampaignMapData:
        """Parse a campaign map JSON dict.

        Args:
            data: Raw JSON dict with map layout and metadata.

        Returns:
            CampaignMapData instance.
        """
        entrance = data["entrance"]
        exit_pos = data["exit"]
        return cls(
            id=data["id"],
            name=data["name"],
            width=data["width"],
            height=data["height"],
            mission_type=MissionType(data["mission_type"]),
            difficulty=DifficultyTier(data["difficulty"]),
            faction_id=data.get("faction_id", ""),
            tiles=data["tiles"],
            entrance=(entrance[0], entrance[1]),
            exit=(exit_pos[0], exit_pos[1]),
            enemies=data.get("enemies", []),
            interactables=data.get("interactables", []),
            story_triggers=data.get("story_triggers", []),
        )


class CampaignMapBuilder:
    """Builds a MapGenResult from a CampaignMapData definition."""

    @staticmethod
    def build(data: CampaignMapData) -> MapGenResult:
        """Convert campaign map data into a playable MapGenResult.

        Args:
            data: Parsed campaign map definition.

        Returns:
            MapGenResult with ground_map and enemies ready for play.
        """
        # Build tile grid
        tiles: list[list[GroundTile]] = []
        for row in data.tiles:
            tile_row: list[GroundTile] = []
            for code in row:
                tile_type = TILE_CODE_MAP.get(code, TileType.WALL)
                tile_row.append(GroundTile(tile_type=tile_type))
            tiles.append(tile_row)

        ground_map = GroundMap(
            width=data.width,
            height=data.height,
            tiles=tiles,
            entrance_pos=data.entrance,
            exit_pos=data.exit,
        )

        # Build enemies
        enemies = _build_enemies(data.enemies, data.difficulty)

        # Build interactables
        interactables = _build_interactables(data.interactables)

        # Build story triggers
        story_triggers = _build_story_triggers(data.story_triggers)

        # Build config for result compatibility
        config = MapGenConfig(
            mission_type=data.mission_type,
            difficulty=data.difficulty,
            seed=0,
            faction_id=data.faction_id,
        )

        return MapGenResult(
            ground_map=ground_map,
            enemies=enemies,
            config=config,
            interactables=interactables,
            story_triggers=story_triggers,
        )


def _build_enemies(
    enemy_defs: list[dict], difficulty: DifficultyTier
) -> list[GroundEnemy]:
    """Build GroundEnemy instances from campaign map enemy definitions.

    Args:
        enemy_defs: List of enemy definition dicts from campaign JSON.
        difficulty: Mission difficulty for loot scaling.

    Returns:
        List of GroundEnemy instances.
    """
    enemies: list[GroundEnemy] = []
    for edef in enemy_defs:
        template_id = edef.get("template_id", "guild_security")
        template = GROUND_ENEMY_TEMPLATES.get(
            template_id, GROUND_ENEMY_TEMPLATES["guild_security"]
        )

        # Parse patrol route (list of [x, y] -> list of (x, y))
        raw_patrol = edef.get("patrol_route", [])
        patrol_route = [(p[0], p[1]) for p in raw_patrol]

        loot = int(template.get("loot_credits", 20) * difficulty.loot_multiplier)

        enemies.append(
            GroundEnemy(
                id=edef["id"],
                x=edef["x"],
                y=edef["y"],
                facing=Direction(edef.get("facing", "right")),
                speed=edef.get("speed", 1),
                patrol_route=patrol_route,
                loot_credits=loot,
                template_id=template_id,
            )
        )
    return enemies


def _build_interactables(defs: list[dict]) -> list[GroundInteractable]:
    """Build GroundInteractable instances from campaign map definitions.

    Args:
        defs: List of interactable dicts from campaign JSON.

    Returns:
        List of GroundInteractable instances.
    """
    return [
        GroundInteractable(
            x=d["x"],
            y=d["y"],
            interact_type=d.get("type", "loot_container"),
            loot_credits=d.get("loot_credits", 0),
            description=d.get("description", ""),
        )
        for d in defs
    ]


def _build_story_triggers(defs: list[dict]) -> list[GroundStoryTrigger]:
    """Build GroundStoryTrigger instances from campaign map definitions.

    Args:
        defs: List of story trigger dicts from campaign JSON.

    Returns:
        List of GroundStoryTrigger instances.
    """
    return [
        GroundStoryTrigger(
            x=d["x"],
            y=d["y"],
            trigger_type=d.get("type", "atmosphere"),
            text=d.get("text", ""),
        )
        for d in defs
    ]
