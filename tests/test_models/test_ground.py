"""Tests for ground exploration models.

Tests the tile grid, player movement, fog of war, and serialization
for the turn-based ground exploration system (Phase A).
"""

from spacegame.models.ground import (
    FogState,
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
)


class TestTileType:
    """Tests for TileType enum."""

    def test_all_tile_types_have_string_values(self) -> None:
        expected = {
            "floor",
            "wall",
            "door_closed",
            "door_open",
            "exit",
            "entrance",
            "noisy_floor",
            "terminal",
            "hazard",
            "vent",
        }
        actual = {t.value for t in TileType}
        assert actual == expected

    def test_walkable_types(self) -> None:
        walkable = {
            TileType.FLOOR,
            TileType.DOOR_OPEN,
            TileType.EXIT,
            TileType.ENTRANCE,
            TileType.NOISY_FLOOR,
            TileType.TERMINAL,
            TileType.HAZARD,
        }
        for tt in TileType:
            tile = GroundTile(tile_type=tt)
            if tt in walkable:
                assert tile.is_walkable, f"{tt.value} should be walkable"
            else:
                assert not tile.is_walkable, f"{tt.value} should not be walkable"

    def test_vision_blocking_types(self) -> None:
        blocking = {TileType.WALL, TileType.DOOR_CLOSED, TileType.VENT}
        for tt in TileType:
            tile = GroundTile(tile_type=tt)
            if tt in blocking:
                assert tile.blocks_vision, f"{tt.value} should block vision"
            else:
                assert not tile.blocks_vision, f"{tt.value} should not block vision"


class TestFogState:
    """Tests for FogState enum."""

    def test_all_fog_states(self) -> None:
        expected = {"unexplored", "explored", "visible"}
        actual = {f.value for f in FogState}
        assert actual == expected


class TestGroundTile:
    """Tests for GroundTile dataclass."""

    def test_default_fog_state_is_unexplored(self) -> None:
        tile = GroundTile(tile_type=TileType.FLOOR)
        assert tile.fog_state == FogState.UNEXPLORED

    def test_floor_is_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.FLOOR)
        assert tile.is_walkable

    def test_wall_is_not_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.WALL)
        assert not tile.is_walkable

    def test_closed_door_is_not_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.DOOR_CLOSED)
        assert not tile.is_walkable

    def test_open_door_is_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.DOOR_OPEN)
        assert tile.is_walkable

    def test_closed_door_blocks_vision(self) -> None:
        tile = GroundTile(tile_type=TileType.DOOR_CLOSED)
        assert tile.blocks_vision

    def test_open_door_does_not_block_vision(self) -> None:
        tile = GroundTile(tile_type=TileType.DOOR_OPEN)
        assert not tile.blocks_vision

    def test_exit_is_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.EXIT)
        assert tile.is_walkable

    def test_entrance_is_walkable(self) -> None:
        tile = GroundTile(tile_type=TileType.ENTRANCE)
        assert tile.is_walkable

    def test_to_dict(self) -> None:
        tile = GroundTile(tile_type=TileType.FLOOR, fog_state=FogState.VISIBLE)
        data = tile.to_dict()
        assert data["tile_type"] == "floor"
        assert data["fog_state"] == "visible"

    def test_from_dict(self) -> None:
        data = {"tile_type": "wall", "fog_state": "explored"}
        tile = GroundTile.from_dict(data)
        assert tile.tile_type == TileType.WALL
        assert tile.fog_state == FogState.EXPLORED

    def test_to_dict_round_trip(self) -> None:
        original = GroundTile(tile_type=TileType.DOOR_CLOSED, fog_state=FogState.EXPLORED)
        restored = GroundTile.from_dict(original.to_dict())
        assert restored.tile_type == original.tile_type
        assert restored.fog_state == original.fog_state


class TestGroundMap:
    """Tests for GroundMap dataclass."""

    def _make_map(self, width: int = 10, height: int = 10) -> GroundMap:
        """Create a test map with wall border and floor interior."""
        return GroundMap.create_test_map(width, height)

    # --- Construction ---

    def test_create_map_dimensions(self) -> None:
        gm = self._make_map(15, 20)
        assert gm.width == 15
        assert gm.height == 20

    def test_create_test_map_has_walls_on_border(self) -> None:
        gm = self._make_map()
        # Top row
        for x in range(gm.width):
            assert gm.get_tile(x, 0).tile_type == TileType.WALL, f"Top border ({x},0)"
        # Bottom row
        for x in range(gm.width):
            assert gm.get_tile(x, gm.height - 1).tile_type == TileType.WALL
        # Left column
        for y in range(gm.height):
            assert gm.get_tile(0, y).tile_type == TileType.WALL
        # Right column
        for y in range(gm.height):
            assert gm.get_tile(gm.width - 1, y).tile_type == TileType.WALL

    def test_create_test_map_has_floor_interior(self) -> None:
        gm = self._make_map()
        for y in range(1, gm.height - 1):
            for x in range(1, gm.width - 1):
                tile = gm.get_tile(x, y)
                if (x, y) == gm.entrance_pos or (x, y) == gm.exit_pos:
                    continue  # Skip entrance/exit
                assert tile.tile_type == TileType.FLOOR, f"Interior ({x},{y})"

    def test_create_test_map_entrance_and_exit(self) -> None:
        gm = self._make_map()
        assert gm.entrance_pos == (1, 1)
        assert gm.exit_pos == (gm.width - 2, gm.height - 2)
        assert gm.get_tile(*gm.entrance_pos).tile_type == TileType.ENTRANCE
        assert gm.get_tile(*gm.exit_pos).tile_type == TileType.EXIT

    # --- Bounds and access ---

    def test_get_tile_in_bounds(self) -> None:
        gm = self._make_map()
        tile = gm.get_tile(1, 1)
        assert tile is not None

    def test_get_tile_out_of_bounds_returns_none(self) -> None:
        gm = self._make_map()
        assert gm.get_tile(-1, 0) is None
        assert gm.get_tile(0, -1) is None
        assert gm.get_tile(gm.width, 0) is None
        assert gm.get_tile(0, gm.height) is None

    def test_is_in_bounds_true(self) -> None:
        gm = self._make_map()
        assert gm.is_in_bounds(0, 0)
        assert gm.is_in_bounds(gm.width - 1, gm.height - 1)
        assert gm.is_in_bounds(5, 5)

    def test_is_in_bounds_false(self) -> None:
        gm = self._make_map()
        assert not gm.is_in_bounds(-1, 0)
        assert not gm.is_in_bounds(0, -1)
        assert not gm.is_in_bounds(gm.width, 0)
        assert not gm.is_in_bounds(0, gm.height)

    # --- Walkability ---

    def test_is_walkable_floor(self) -> None:
        gm = self._make_map()
        assert gm.is_walkable(2, 2)  # Interior floor

    def test_is_walkable_wall(self) -> None:
        gm = self._make_map()
        assert not gm.is_walkable(0, 0)  # Border wall

    def test_is_walkable_out_of_bounds(self) -> None:
        gm = self._make_map()
        assert not gm.is_walkable(-1, -1)

    def test_is_walkable_entrance_and_exit(self) -> None:
        gm = self._make_map()
        assert gm.is_walkable(*gm.entrance_pos)
        assert gm.is_walkable(*gm.exit_pos)

    # --- Door operations ---

    def test_open_door_success(self) -> None:
        gm = self._make_map()
        # Place a closed door
        gm.tiles[3][3] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        assert not gm.is_walkable(3, 3)

        success, msg = gm.open_door(3, 3)
        assert success, f"Should open door: {msg}"
        assert gm.get_tile(3, 3).tile_type == TileType.DOOR_OPEN
        assert gm.is_walkable(3, 3)

    def test_open_door_not_a_door(self) -> None:
        gm = self._make_map()
        success, msg = gm.open_door(2, 2)  # Floor tile
        assert not success
        assert "not a closed door" in msg.lower()

    def test_open_door_already_open(self) -> None:
        gm = self._make_map()
        gm.tiles[3][3] = GroundTile(tile_type=TileType.DOOR_OPEN)
        success, msg = gm.open_door(3, 3)
        assert not success

    def test_open_door_out_of_bounds(self) -> None:
        gm = self._make_map()
        success, msg = gm.open_door(-1, -1)
        assert not success

    # --- Line of sight ---

    def test_los_same_tile(self) -> None:
        gm = self._make_map()
        assert gm.has_line_of_sight(3, 3, 3, 3)

    def test_los_adjacent(self) -> None:
        gm = self._make_map()
        assert gm.has_line_of_sight(3, 3, 3, 4)
        assert gm.has_line_of_sight(3, 3, 4, 3)

    def test_los_clear_path(self) -> None:
        gm = self._make_map()
        # Interior is all floor, should have clear LOS
        assert gm.has_line_of_sight(1, 1, 5, 5)

    def test_los_blocked_by_wall(self) -> None:
        gm = self._make_map()
        # Place a wall in the middle
        gm.tiles[3][3] = GroundTile(tile_type=TileType.WALL)
        # LOS from (1,3) to (5,3) goes through the wall at (3,3)
        assert not gm.has_line_of_sight(1, 3, 5, 3)

    def test_los_blocked_by_closed_door(self) -> None:
        gm = self._make_map()
        gm.tiles[3][3] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        assert not gm.has_line_of_sight(1, 3, 5, 3)

    def test_los_not_blocked_by_open_door(self) -> None:
        gm = self._make_map()
        gm.tiles[3][3] = GroundTile(tile_type=TileType.DOOR_OPEN)
        assert gm.has_line_of_sight(1, 3, 5, 3)

    def test_los_diagonal_blocked(self) -> None:
        gm = self._make_map()
        gm.tiles[3][3] = GroundTile(tile_type=TileType.WALL)
        # Diagonal line that passes through (3,3)
        assert not gm.has_line_of_sight(1, 1, 5, 5)

    # --- Fog of war ---

    def test_initial_fog_all_unexplored(self) -> None:
        gm = self._make_map()
        for y in range(gm.height):
            for x in range(gm.width):
                assert gm.get_tile(x, y).fog_state == FogState.UNEXPLORED

    def test_update_fog_marks_visible(self) -> None:
        gm = self._make_map()
        gm.update_fog_of_war(5, 5, 3)
        # The tile at player position should be visible
        assert gm.get_tile(5, 5).fog_state == FogState.VISIBLE
        # Adjacent tiles with LOS should be visible
        assert gm.get_tile(5, 6).fog_state == FogState.VISIBLE
        assert gm.get_tile(6, 5).fog_state == FogState.VISIBLE

    def test_update_fog_previous_visible_becomes_explored(self) -> None:
        gm = self._make_map()
        # First update at (3, 3)
        gm.update_fog_of_war(3, 3, 2)
        assert gm.get_tile(3, 3).fog_state == FogState.VISIBLE

        # Move far away — previous visible tiles become explored
        gm.update_fog_of_war(8, 8, 2)
        assert gm.get_tile(3, 3).fog_state == FogState.EXPLORED
        assert gm.get_tile(8, 8).fog_state == FogState.VISIBLE

    def test_update_fog_blocked_by_wall(self) -> None:
        gm = self._make_map()
        # Place a wall between player and target
        gm.tiles[5][4] = GroundTile(tile_type=TileType.WALL)
        gm.update_fog_of_war(3, 5, 5)
        # Tile behind the wall should not be visible
        assert gm.get_tile(5, 5).fog_state != FogState.VISIBLE

    def test_update_fog_respects_vision_radius(self) -> None:
        gm = self._make_map(20, 20)
        gm.update_fog_of_war(10, 10, 2)
        # Tiles within radius 2 should be visible (if LOS clear)
        assert gm.get_tile(10, 10).fog_state == FogState.VISIBLE
        assert gm.get_tile(11, 10).fog_state == FogState.VISIBLE
        assert gm.get_tile(12, 10).fog_state == FogState.VISIBLE
        # Tiles beyond radius 2 should remain unexplored
        assert gm.get_tile(13, 10).fog_state == FogState.UNEXPLORED

    def test_update_fog_walls_remain_visible_when_adjacent(self) -> None:
        gm = self._make_map()
        # Player at (1,1), wall at (0,0) is adjacent border wall
        gm.update_fog_of_war(1, 1, 3)
        # The wall itself should be visible (we can see it, we just can't see through it)
        assert gm.get_tile(0, 1).fog_state == FogState.VISIBLE

    # --- Serialization ---

    def test_to_dict_from_dict_round_trip(self) -> None:
        gm = self._make_map(8, 6)
        # Modify some state
        gm.update_fog_of_war(3, 3, 2)
        gm.tiles[2][2] = GroundTile(tile_type=TileType.DOOR_CLOSED, fog_state=FogState.EXPLORED)

        data = gm.to_dict()
        restored = GroundMap.from_dict(data)

        assert restored.width == gm.width
        assert restored.height == gm.height
        assert restored.entrance_pos == gm.entrance_pos
        assert restored.exit_pos == gm.exit_pos

        # Check a few tiles
        assert restored.get_tile(2, 2).tile_type == TileType.DOOR_CLOSED
        assert restored.get_tile(2, 2).fog_state == FogState.EXPLORED
        assert restored.get_tile(3, 3).fog_state == FogState.VISIBLE


class TestGroundPlayerState:
    """Tests for GroundPlayerState dataclass."""

    def _make_map(self) -> GroundMap:
        """Create a 10x10 test map."""
        return GroundMap.create_test_map(10, 10)

    def _make_player(self, x: int = 5, y: int = 5) -> GroundPlayerState:
        """Create a player state at the given position."""
        return GroundPlayerState(x=x, y=y)

    # --- Movement ---

    def test_move_up(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(0, -1, gm)
        assert success, f"Move up should succeed: {msg}"
        assert ps.x == 5
        assert ps.y == 4

    def test_move_down(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(0, 1, gm)
        assert success, f"Move down should succeed: {msg}"
        assert ps.y == 6

    def test_move_left(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(-1, 0, gm)
        assert success, f"Move left should succeed: {msg}"
        assert ps.x == 4

    def test_move_right(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(1, 0, gm)
        assert success, f"Move right should succeed: {msg}"
        assert ps.x == 6

    def test_move_into_wall_fails(self) -> None:
        gm = self._make_map()
        ps = self._make_player(1, 1)
        success, msg = ps.move(0, -1, gm)  # Up into border wall
        assert not success
        assert ps.y == 1, "Position should not change on failed move"

    def test_move_into_closed_door_fails(self) -> None:
        gm = self._make_map()
        gm.tiles[5][4] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        ps = self._make_player(3, 5)
        success, msg = ps.move(1, 0, gm)  # Right into closed door at (4, 5)
        assert not success

    def test_move_into_open_door_succeeds(self) -> None:
        gm = self._make_map()
        gm.tiles[5][4] = GroundTile(tile_type=TileType.DOOR_OPEN)
        ps = self._make_player(3, 5)
        success, msg = ps.move(1, 0, gm)
        assert success, f"Should walk through open door: {msg}"
        assert ps.x == 4

    def test_move_diagonal_rejected(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(1, 1, gm)
        assert not success
        assert "cardinal" in msg.lower() or "diagonal" in msg.lower()

    def test_move_zero_rejected(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(0, 0, gm)
        assert not success

    def test_move_too_far_rejected(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.move(2, 0, gm)
        assert not success

    def test_move_increments_turn_number(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        assert ps.turn_number == 0
        ps.move(1, 0, gm)
        assert ps.turn_number == 1
        ps.move(1, 0, gm)
        assert ps.turn_number == 2

    def test_failed_move_does_not_increment_turn(self) -> None:
        gm = self._make_map()
        ps = self._make_player(1, 1)
        ps.move(0, -1, gm)  # Into wall
        assert ps.turn_number == 0

    def test_move_onto_exit(self) -> None:
        gm = self._make_map()
        exit_x, exit_y = gm.exit_pos
        ps = self._make_player(exit_x - 1, exit_y)
        success, msg = ps.move(1, 0, gm)
        assert success, f"Should be able to move onto exit: {msg}"

    def test_move_onto_entrance(self) -> None:
        gm = self._make_map()
        ent_x, ent_y = gm.entrance_pos
        ps = self._make_player(ent_x + 1, ent_y)
        success, msg = ps.move(-1, 0, gm)
        assert success

    # --- Wait ---

    def test_wait_increments_turn(self) -> None:
        ps = self._make_player(5, 5)
        assert ps.turn_number == 0
        ps.wait()
        assert ps.turn_number == 1

    # --- Interact ---

    def test_interact_open_adjacent_door(self) -> None:
        gm = self._make_map()
        gm.tiles[5][6] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        ps = self._make_player(5, 5)
        success, msg = ps.interact(gm, 6, 5)
        assert success, f"Should open adjacent door: {msg}"
        assert gm.get_tile(6, 5).tile_type == TileType.DOOR_OPEN

    def test_interact_non_adjacent_fails(self) -> None:
        gm = self._make_map()
        gm.tiles[5][7] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        ps = self._make_player(5, 5)
        success, msg = ps.interact(gm, 7, 5)
        assert not success
        assert "adjacent" in msg.lower() or "too far" in msg.lower()

    def test_interact_floor_nothing_to_interact(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        success, msg = ps.interact(gm, 6, 5)
        assert not success

    def test_interact_increments_turn(self) -> None:
        gm = self._make_map()
        gm.tiles[5][6] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        ps = self._make_player(5, 5)
        ps.interact(gm, 6, 5)
        assert ps.turn_number == 1

    def test_failed_interact_does_not_increment_turn(self) -> None:
        gm = self._make_map()
        ps = self._make_player(5, 5)
        ps.interact(gm, 7, 5)  # Too far
        assert ps.turn_number == 0

    # --- Serialization ---

    def test_to_dict(self) -> None:
        ps = GroundPlayerState(x=3, y=7, vision_radius=6, turn_number=12)
        data = ps.to_dict()
        assert data["x"] == 3
        assert data["y"] == 7
        assert data["vision_radius"] == 6
        assert data["turn_number"] == 12

    def test_from_dict(self) -> None:
        data = {"x": 4, "y": 8, "vision_radius": 7, "turn_number": 5}
        ps = GroundPlayerState.from_dict(data)
        assert ps.x == 4
        assert ps.y == 8
        assert ps.vision_radius == 7
        assert ps.turn_number == 5

    def test_to_dict_round_trip(self) -> None:
        original = GroundPlayerState(x=5, y=3, vision_radius=4, turn_number=10)
        restored = GroundPlayerState.from_dict(original.to_dict())
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.vision_radius == original.vision_radius
        assert restored.turn_number == original.turn_number
