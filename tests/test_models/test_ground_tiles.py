"""Tests for new ground tile types: TERMINAL, HAZARD, VENT."""

from spacegame.models.ground import (
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
    _WALKABLE_TYPES,
    _VISION_BLOCKING_TYPES,
)
from spacegame.models.campaign_map import TILE_CODE_MAP


class TestNewTileTypes:
    """TileType enum has TERMINAL, HAZARD, VENT values."""

    def test_terminal_exists(self) -> None:
        assert TileType.TERMINAL.value == "terminal"

    def test_hazard_exists(self) -> None:
        assert TileType.HAZARD.value == "hazard"

    def test_vent_exists(self) -> None:
        assert TileType.VENT.value == "vent"


class TestWalkability:
    """TERMINAL and HAZARD are walkable, VENT is not."""

    def test_terminal_is_walkable(self) -> None:
        assert TileType.TERMINAL in _WALKABLE_TYPES
        tile = GroundTile(tile_type=TileType.TERMINAL)
        assert tile.is_walkable

    def test_hazard_is_walkable(self) -> None:
        assert TileType.HAZARD in _WALKABLE_TYPES
        tile = GroundTile(tile_type=TileType.HAZARD)
        assert tile.is_walkable

    def test_vent_is_not_walkable(self) -> None:
        assert TileType.VENT not in _WALKABLE_TYPES
        tile = GroundTile(tile_type=TileType.VENT)
        assert not tile.is_walkable


class TestVisionBlocking:
    """VENT blocks vision, TERMINAL and HAZARD do not."""

    def test_vent_blocks_vision(self) -> None:
        assert TileType.VENT in _VISION_BLOCKING_TYPES
        tile = GroundTile(tile_type=TileType.VENT)
        assert tile.blocks_vision

    def test_terminal_does_not_block_vision(self) -> None:
        assert TileType.TERMINAL not in _VISION_BLOCKING_TYPES
        tile = GroundTile(tile_type=TileType.TERMINAL)
        assert not tile.blocks_vision

    def test_hazard_does_not_block_vision(self) -> None:
        assert TileType.HAZARD not in _VISION_BLOCKING_TYPES
        tile = GroundTile(tile_type=TileType.HAZARD)
        assert not tile.blocks_vision


class TestTileCodes:
    """Campaign map tile codes T, H, V map to new types."""

    def test_terminal_code(self) -> None:
        assert TILE_CODE_MAP["T"] == TileType.TERMINAL

    def test_hazard_code(self) -> None:
        assert TILE_CODE_MAP["H"] == TileType.HAZARD

    def test_vent_code(self) -> None:
        assert TILE_CODE_MAP["V"] == TileType.VENT


class TestSerialization:
    """New tile types survive to_dict/from_dict round-trip."""

    def test_terminal_roundtrip(self) -> None:
        tile = GroundTile(tile_type=TileType.TERMINAL)
        restored = GroundTile.from_dict(tile.to_dict())
        assert restored.tile_type == TileType.TERMINAL

    def test_hazard_roundtrip(self) -> None:
        tile = GroundTile(tile_type=TileType.HAZARD)
        restored = GroundTile.from_dict(tile.to_dict())
        assert restored.tile_type == TileType.HAZARD

    def test_vent_roundtrip(self) -> None:
        tile = GroundTile(tile_type=TileType.VENT)
        restored = GroundTile.from_dict(tile.to_dict())
        assert restored.tile_type == TileType.VENT


class TestVentBlocksLineOfSight:
    """VENT tiles block LOS like walls."""

    def _make_corridor_map(self, middle_type: TileType) -> GroundMap:
        """3x1 corridor with given tile in the middle."""
        tiles = [
            [
                GroundTile(tile_type=TileType.FLOOR),
                GroundTile(tile_type=middle_type),
                GroundTile(tile_type=TileType.FLOOR),
            ]
        ]
        return GroundMap(
            width=3,
            height=1,
            tiles=tiles,
            entrance_pos=(0, 0),
            exit_pos=(2, 0),
        )

    def test_vent_blocks_los(self) -> None:
        gmap = self._make_corridor_map(TileType.VENT)
        assert not gmap.has_line_of_sight(0, 0, 2, 0)

    def test_floor_does_not_block_los(self) -> None:
        gmap = self._make_corridor_map(TileType.FLOOR)
        assert gmap.has_line_of_sight(0, 0, 2, 0)


class TestTerminalInteraction:
    """Player can interact with adjacent TERMINAL tiles."""

    def _make_terminal_map(self) -> GroundMap:
        """3x3 map with terminal at (1,0), player area at (1,1)."""
        tiles = [
            [
                GroundTile(tile_type=TileType.WALL),
                GroundTile(tile_type=TileType.TERMINAL),
                GroundTile(tile_type=TileType.WALL),
            ],
            [
                GroundTile(tile_type=TileType.WALL),
                GroundTile(tile_type=TileType.FLOOR),
                GroundTile(tile_type=TileType.WALL),
            ],
            [
                GroundTile(tile_type=TileType.WALL),
                GroundTile(tile_type=TileType.WALL),
                GroundTile(tile_type=TileType.WALL),
            ],
        ]
        return GroundMap(
            width=3,
            height=3,
            tiles=tiles,
            entrance_pos=(1, 1),
            exit_pos=(1, 1),
        )

    def test_interact_with_terminal(self) -> None:
        gmap = self._make_terminal_map()
        player = GroundPlayerState(x=1, y=1)
        success, msg = player.interact(gmap, 1, 0)
        assert success, f"Should interact with terminal: {msg}"
        assert "terminal" in msg.lower()

    def test_interact_with_terminal_advances_turn(self) -> None:
        gmap = self._make_terminal_map()
        player = GroundPlayerState(x=1, y=1)
        player.interact(gmap, 1, 0)
        assert player.turn_number == 1


class TestHazardOnStep:
    """Player takes damage when stepping on HAZARD tiles."""

    def _make_hazard_map(self) -> GroundMap:
        """3x1 corridor: floor, hazard, floor."""
        tiles = [
            [
                GroundTile(tile_type=TileType.ENTRANCE),
                GroundTile(tile_type=TileType.HAZARD),
                GroundTile(tile_type=TileType.EXIT),
            ]
        ]
        return GroundMap(
            width=3,
            height=1,
            tiles=tiles,
            entrance_pos=(0, 0),
            exit_pos=(2, 0),
        )

    def test_move_onto_hazard_succeeds(self) -> None:
        gmap = self._make_hazard_map()
        player = GroundPlayerState(x=0, y=0)
        success, msg = player.move(1, 0, gmap)
        assert success

    def test_move_onto_hazard_warns(self) -> None:
        gmap = self._make_hazard_map()
        player = GroundPlayerState(x=0, y=0)
        _, msg = player.move(1, 0, gmap)
        assert "hazard" in msg.lower()


class TestPlayerCannotWalkOnVent:
    """Vent tiles are not walkable — player movement is blocked."""

    def test_cannot_move_onto_vent(self) -> None:
        tiles = [
            [
                GroundTile(tile_type=TileType.ENTRANCE),
                GroundTile(tile_type=TileType.VENT),
                GroundTile(tile_type=TileType.EXIT),
            ]
        ]
        gmap = GroundMap(
            width=3,
            height=1,
            tiles=tiles,
            entrance_pos=(0, 0),
            exit_pos=(2, 0),
        )
        player = GroundPlayerState(x=0, y=0)
        success, msg = player.move(1, 0, gmap)
        assert not success
