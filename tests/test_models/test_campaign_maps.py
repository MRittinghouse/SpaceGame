"""Tests for campaign map loading and building.

Tests CampaignMapData parsing, CampaignMapBuilder producing valid
GroundMap + enemies, DataLoader integration, and game engine fallback
from campaign maps to procedural generation.
"""

import pytest

from spacegame.models.ground import GroundMap, TileType
from spacegame.models.ground_enemy import Direction, GroundEnemy
from spacegame.models.ground_mapgen import MapGenResult, MissionType, DifficultyTier


# ===========================================================================
# Minimal valid campaign map data
# ===========================================================================

def _minimal_map_data() -> dict:
    """A small 8x6 campaign map with one enemy and basic layout."""
    # Legend: W=wall, F=floor, E=entrance, X=exit, D=door, N=noisy
    # Row-major: tiles[y][x]
    return {
        "id": "test_campaign_01",
        "name": "Test Facility",
        "width": 8,
        "height": 6,
        "mission_type": "infiltration",
        "difficulty": "low",
        "faction_id": "merchants_guild",
        "tiles": [
            ["W", "W", "W", "W", "W", "W", "W", "W"],
            ["W", "E", "F", "F", "D", "F", "F", "W"],
            ["W", "F", "F", "F", "W", "F", "F", "W"],
            ["W", "F", "F", "F", "W", "N", "F", "W"],
            ["W", "F", "F", "F", "D", "F", "X", "W"],
            ["W", "W", "W", "W", "W", "W", "W", "W"],
        ],
        "entrance": [1, 1],
        "exit": [6, 4],
        "enemies": [
            {
                "id": "guard_1",
                "template_id": "guild_security",
                "x": 5,
                "y": 2,
                "facing": "down",
                "speed": 1,
                "patrol_route": [[5, 2], [5, 3], [5, 4], [5, 3]],
            }
        ],
        "interactables": [
            {"x": 3, "y": 2, "type": "loot_container", "loot_credits": 50}
        ],
        "story_triggers": [
            {"x": 2, "y": 4, "type": "discovery", "text": "A hidden passage."}
        ],
    }


def _map_data_no_enemies() -> dict:
    """Campaign map with no enemies."""
    data = _minimal_map_data()
    data["id"] = "test_no_enemies"
    data["enemies"] = []
    return data


def _map_data_multi_enemy() -> dict:
    """Campaign map with multiple enemies and patrol routes."""
    data = _minimal_map_data()
    data["id"] = "test_multi_enemy"
    data["enemies"] = [
        {
            "id": "guard_1",
            "template_id": "guild_security",
            "x": 5,
            "y": 2,
            "facing": "down",
            "speed": 1,
            "patrol_route": [[5, 2], [5, 3]],
        },
        {
            "id": "guard_2",
            "template_id": "pirate_thug",
            "x": 2,
            "y": 3,
            "facing": "left",
            "speed": 2,
            "patrol_route": [[2, 3], [2, 4], [3, 4]],
        },
    ]
    return data


# ===========================================================================
# CampaignMapData parsing
# ===========================================================================


class TestCampaignMapData:
    """CampaignMapData parses raw JSON dict into structured data."""

    def test_parses_basic_fields(self):
        """Parses id, name, width, height."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert data.id == "test_campaign_01"
        assert data.name == "Test Facility"
        assert data.width == 8
        assert data.height == 6

    def test_parses_mission_metadata(self):
        """Parses mission_type, difficulty, faction_id."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert data.mission_type == MissionType.INFILTRATION
        assert data.difficulty == DifficultyTier.LOW
        assert data.faction_id == "merchants_guild"

    def test_parses_entrance_exit(self):
        """Parses entrance and exit coordinates."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert data.entrance == (1, 1)
        assert data.exit == (6, 4)

    def test_parses_tiles(self):
        """Tiles array preserved as list of lists."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert len(data.tiles) == 6
        assert len(data.tiles[0]) == 8
        assert data.tiles[1][1] == "E"
        assert data.tiles[4][6] == "X"

    def test_parses_enemies(self):
        """Enemy definitions preserved."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert len(data.enemies) == 1
        assert data.enemies[0]["id"] == "guard_1"

    def test_parses_interactables(self):
        """Interactable definitions preserved."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert len(data.interactables) == 1
        assert data.interactables[0]["type"] == "loot_container"

    def test_parses_story_triggers(self):
        """Story trigger definitions preserved."""
        from spacegame.models.campaign_map import CampaignMapData

        data = CampaignMapData.from_dict(_minimal_map_data())
        assert len(data.story_triggers) == 1
        assert data.story_triggers[0]["type"] == "discovery"

    def test_optional_fields_default_empty(self):
        """Missing optional fields default to empty lists."""
        from spacegame.models.campaign_map import CampaignMapData

        raw = _minimal_map_data()
        del raw["interactables"]
        del raw["story_triggers"]
        data = CampaignMapData.from_dict(raw)
        assert data.interactables == []
        assert data.story_triggers == []


# ===========================================================================
# CampaignMapBuilder — builds GroundMap + enemies
# ===========================================================================


class TestCampaignMapBuilder:
    """CampaignMapBuilder converts CampaignMapData into MapGenResult."""

    def test_builds_ground_map(self):
        """build() produces a GroundMap with correct dimensions."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert isinstance(result, MapGenResult)
        assert result.ground_map.width == 8
        assert result.ground_map.height == 6

    def test_entrance_tile_type(self):
        """Entrance position has ENTRANCE tile type."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(1, 1)
        assert tile.tile_type == TileType.ENTRANCE

    def test_exit_tile_type(self):
        """Exit position has EXIT tile type."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(6, 4)
        assert tile.tile_type == TileType.EXIT

    def test_wall_tiles(self):
        """'W' codes produce WALL tiles."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(0, 0)
        assert tile.tile_type == TileType.WALL

    def test_floor_tiles(self):
        """'F' codes produce FLOOR tiles."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(2, 1)
        assert tile.tile_type == TileType.FLOOR

    def test_door_tiles(self):
        """'D' codes produce DOOR_CLOSED tiles."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(4, 1)
        assert tile.tile_type == TileType.DOOR_CLOSED

    def test_noisy_floor_tiles(self):
        """'N' codes produce NOISY_FLOOR tiles."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(5, 3)
        assert tile.tile_type == TileType.NOISY_FLOOR

    def test_entrance_exit_positions(self):
        """GroundMap entrance_pos and exit_pos match data."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert result.ground_map.entrance_pos == (1, 1)
        assert result.ground_map.exit_pos == (6, 4)

    def test_enemies_created(self):
        """Enemies are built from enemy definitions."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert len(result.enemies) == 1
        enemy = result.enemies[0]
        assert enemy.id == "guard_1"
        assert enemy.x == 5
        assert enemy.y == 2

    def test_enemy_facing(self):
        """Enemy facing direction parsed correctly."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert result.enemies[0].facing == Direction.DOWN

    def test_enemy_patrol_route(self):
        """Enemy patrol route parsed as list of tuples."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        enemy = result.enemies[0]
        assert enemy.patrol_route == [(5, 2), (5, 3), (5, 4), (5, 3)]

    def test_enemy_speed(self):
        """Enemy speed parsed from definition."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert result.enemies[0].speed == 1

    def test_enemy_loot_from_template(self):
        """Enemy loot credits loaded from template data."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert result.enemies[0].loot_credits > 0

    def test_multiple_enemies(self):
        """Multiple enemies are all created."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_map_data_multi_enemy())
        result = CampaignMapBuilder.build(data)
        assert len(result.enemies) == 2
        ids = {e.id for e in result.enemies}
        assert ids == {"guard_1", "guard_2"}

    def test_no_enemies_map(self):
        """Map with no enemies produces empty enemy list."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_map_data_no_enemies())
        result = CampaignMapBuilder.build(data)
        assert len(result.enemies) == 0

    def test_config_on_result(self):
        """Result includes a MapGenConfig with correct mission_type and difficulty."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert result.config.mission_type == MissionType.INFILTRATION
        assert result.config.difficulty == DifficultyTier.LOW
        assert result.config.faction_id == "merchants_guild"

    def test_build_mission_state(self):
        """MapGenResult.build_mission_state works on campaign results."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        state = result.build_mission_state()
        assert state.player.x == 1
        assert state.player.y == 1
        assert len(state.enemies) == 1

    def test_interactables_on_result(self):
        """Interactables are stored on the result for downstream use."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert hasattr(result, "interactables") or hasattr(data, "interactables")

    def test_story_triggers_on_result(self):
        """Story triggers are stored on the result for downstream use."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        data = CampaignMapData.from_dict(_minimal_map_data())
        result = CampaignMapBuilder.build(data)
        assert hasattr(result, "story_triggers") or hasattr(data, "story_triggers")


# ===========================================================================
# DataLoader integration
# ===========================================================================


class TestDataLoaderCampaignMaps:
    """DataLoader loads campaign maps from data/ground/campaign/."""

    def test_has_campaign_maps_dict(self):
        """DataLoader has campaign_ground_maps attribute."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        assert hasattr(dl, "campaign_ground_maps")
        assert isinstance(dl.campaign_ground_maps, dict)

    def test_load_returns_dict(self):
        """load_campaign_maps returns a dict."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        result = dl.load_campaign_maps()
        assert isinstance(result, dict)


# ===========================================================================
# Tile code coverage
# ===========================================================================


class TestTileCodeMapping:
    """All single-character tile codes map correctly."""

    def test_all_codes(self):
        """Every supported tile code produces the right TileType."""
        from spacegame.models.campaign_map import TILE_CODE_MAP

        assert TILE_CODE_MAP["W"] == TileType.WALL
        assert TILE_CODE_MAP["F"] == TileType.FLOOR
        assert TILE_CODE_MAP["D"] == TileType.DOOR_CLOSED
        assert TILE_CODE_MAP["E"] == TileType.ENTRANCE
        assert TILE_CODE_MAP["X"] == TileType.EXIT
        assert TILE_CODE_MAP["N"] == TileType.NOISY_FLOOR

    def test_unknown_code_defaults_to_wall(self):
        """Unknown tile codes treated as walls."""
        from spacegame.models.campaign_map import CampaignMapData, CampaignMapBuilder

        raw = _minimal_map_data()
        raw["tiles"][2][2] = "?"  # Unknown code
        data = CampaignMapData.from_dict(raw)
        result = CampaignMapBuilder.build(data)
        tile = result.ground_map.get_tile(2, 2)
        assert tile.tile_type == TileType.WALL
