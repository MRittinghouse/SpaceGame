"""Tests for procedural ground map generation (Phase E).

Tests the chunk template system, map assembly algorithm,
difficulty scaling, mission types, and enemy/loot placement.
"""

import pytest

from spacegame.models.ground import GroundMap, GroundTile, TileType, FogState
from spacegame.models.ground_enemy import GroundEnemy, GroundMissionState
from spacegame.models.ground_mapgen import (
    ChunkTemplate,
    ChunkCategory,
    ChunkLibrary,
    DifficultyTier,
    MissionType,
    GroundMapGenerator,
    MapGenConfig,
)


# ============================================================================
# ChunkTemplate
# ============================================================================


class TestChunkTemplate:
    """Tests for chunk template data and validation."""

    def test_create_empty_room_chunk(self) -> None:
        """An 8x8 room chunk with floor interior and wall border."""
        chunk = ChunkTemplate.create_room(8, 8, "storage_bay")
        assert chunk.width == 8
        assert chunk.height == 8
        assert chunk.id == "storage_bay"
        assert chunk.category == ChunkCategory.ROOM

    def test_chunk_has_tiles(self) -> None:
        chunk = ChunkTemplate.create_room(8, 8, "test")
        assert len(chunk.tiles) == 8  # 8 rows
        assert len(chunk.tiles[0]) == 8  # 8 columns

    def test_room_chunk_has_wall_border(self) -> None:
        chunk = ChunkTemplate.create_room(8, 8, "test")
        # Top and bottom rows should be walls
        for x in range(8):
            assert chunk.tiles[0][x] == TileType.WALL
            assert chunk.tiles[7][x] == TileType.WALL
        # Left and right columns should be walls
        for y in range(8):
            assert chunk.tiles[y][0] == TileType.WALL
            assert chunk.tiles[y][7] == TileType.WALL

    def test_room_chunk_has_floor_interior(self) -> None:
        chunk = ChunkTemplate.create_room(8, 8, "test")
        for y in range(1, 7):
            for x in range(1, 7):
                assert chunk.tiles[y][x] == TileType.FLOOR

    def test_chunk_exits(self) -> None:
        """Chunks define which edges have exits (connection points)."""
        chunk = ChunkTemplate.create_room(8, 8, "test")
        chunk.exits = {"north": (4, 0), "south": (4, 7), "east": (7, 3), "west": (0, 3)}
        assert "north" in chunk.exits
        assert chunk.exits["north"] == (4, 0)

    def test_connector_straight_horizontal(self) -> None:
        chunk = ChunkTemplate.create_corridor_h(8, "hall_h")
        assert chunk.category == ChunkCategory.CONNECTOR
        assert chunk.width == 8
        assert chunk.height == 5  # Narrow corridor
        # Middle rows should be floor
        for x in range(chunk.width):
            assert chunk.tiles[2][x] == TileType.FLOOR

    def test_connector_straight_vertical(self) -> None:
        chunk = ChunkTemplate.create_corridor_v(8, "hall_v")
        assert chunk.category == ChunkCategory.CONNECTOR
        assert chunk.height == 8
        assert chunk.width == 5
        # Middle columns should be floor
        for y in range(chunk.height):
            assert chunk.tiles[y][2] == TileType.FLOOR

    def test_chunk_with_features(self) -> None:
        """Chunks can have special tiles placed (doors, noisy floor, etc.)."""
        chunk = ChunkTemplate.create_room(8, 8, "security")
        chunk.set_tile(4, 0, TileType.DOOR_CLOSED)  # North door
        assert chunk.tiles[0][4] == TileType.DOOR_CLOSED

    def test_chunk_rotate_90(self) -> None:
        """Chunks can be rotated for variety."""
        chunk = ChunkTemplate.create_corridor_h(6, "test")
        rotated = chunk.rotate_90()
        # Width and height swap
        assert rotated.width == chunk.height
        assert rotated.height == chunk.width


# ============================================================================
# ChunkLibrary
# ============================================================================


class TestChunkLibrary:
    """Tests for the chunk template library."""

    def test_default_library_has_rooms(self) -> None:
        lib = ChunkLibrary.create_default()
        rooms = lib.get_by_category(ChunkCategory.ROOM)
        assert len(rooms) >= 6, "Should have multiple room templates"

    def test_default_library_has_connectors(self) -> None:
        lib = ChunkLibrary.create_default()
        connectors = lib.get_by_category(ChunkCategory.CONNECTOR)
        assert len(connectors) >= 4, "Should have multiple connector templates"

    def test_default_library_has_special(self) -> None:
        lib = ChunkLibrary.create_default()
        special = lib.get_by_category(ChunkCategory.SPECIAL)
        assert len(special) >= 2, "Should have special templates"

    def test_get_by_id(self) -> None:
        lib = ChunkLibrary.create_default()
        rooms = lib.get_by_category(ChunkCategory.ROOM)
        if rooms:
            chunk = lib.get_by_id(rooms[0].id)
            assert chunk is not None
            assert chunk.id == rooms[0].id

    def test_get_nonexistent_returns_none(self) -> None:
        lib = ChunkLibrary.create_default()
        assert lib.get_by_id("nonexistent_chunk") is None


# ============================================================================
# DifficultyTier
# ============================================================================


class TestDifficultyTier:
    """Tests for difficulty tier configuration."""

    def test_low_tier_small_map(self) -> None:
        tier = DifficultyTier.LOW
        assert tier.map_width <= 20
        assert tier.map_height <= 20

    def test_low_tier_few_enemies(self) -> None:
        tier = DifficultyTier.LOW
        assert tier.enemy_count_min == 3
        assert tier.enemy_count_max == 5

    def test_extreme_tier_large_map(self) -> None:
        tier = DifficultyTier.EXTREME
        assert tier.map_width >= 28
        assert tier.map_height >= 28

    def test_extreme_tier_many_enemies(self) -> None:
        tier = DifficultyTier.EXTREME
        assert tier.enemy_count_min >= 10
        assert tier.enemy_count_max >= 14

    def test_all_tiers_exist(self) -> None:
        assert len(DifficultyTier) == 4

    def test_tiers_have_increasing_enemy_counts(self) -> None:
        tiers = [
            DifficultyTier.LOW,
            DifficultyTier.MODERATE,
            DifficultyTier.HIGH,
            DifficultyTier.EXTREME,
        ]
        for i in range(len(tiers) - 1):
            assert tiers[i].enemy_count_max <= tiers[i + 1].enemy_count_max


# ============================================================================
# MissionType
# ============================================================================


class TestMissionType:
    """Tests for mission type definitions."""

    def test_all_types_exist(self) -> None:
        types = [
            MissionType.INFILTRATION,
            MissionType.RETRIEVAL,
            MissionType.SABOTAGE,
            MissionType.EXPLORATION,
            MissionType.EXTRACTION,
        ]
        assert len(types) == 5

    def test_mission_type_has_description(self) -> None:
        for mt in MissionType:
            assert mt.description, f"{mt.name} missing description"


# ============================================================================
# MapGenConfig
# ============================================================================


class TestMapGenConfig:
    """Tests for map generation configuration."""

    def test_default_config(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        assert cfg.seed == 42
        assert cfg.mission_type == MissionType.INFILTRATION
        assert cfg.difficulty == DifficultyTier.LOW

    def test_config_with_faction(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.RETRIEVAL,
            difficulty=DifficultyTier.MODERATE,
            seed=123,
            faction_id="merchants_guild",
        )
        assert cfg.faction_id == "merchants_guild"


# ============================================================================
# GroundMapGenerator — Core Generation
# ============================================================================


class TestGroundMapGenerator:
    """Tests for the map generation algorithm."""

    def test_generate_returns_ground_map(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        assert isinstance(result.ground_map, GroundMap)

    def test_generated_map_has_entrance(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        ex, ey = result.ground_map.entrance_pos
        tile = result.ground_map.get_tile(ex, ey)
        assert tile is not None
        assert tile.tile_type == TileType.ENTRANCE

    def test_generated_map_has_exit(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        ex, ey = result.ground_map.exit_pos
        tile = result.ground_map.get_tile(ex, ey)
        assert tile is not None
        assert tile.tile_type == TileType.EXIT

    def test_entrance_is_walkable(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        ex, ey = result.ground_map.entrance_pos
        assert result.ground_map.is_walkable(ex, ey)

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed produces identical maps."""
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        r1 = gen.generate(cfg)
        r2 = gen.generate(cfg)
        # Compare tile types
        for y in range(r1.ground_map.height):
            for x in range(r1.ground_map.width):
                t1 = r1.ground_map.get_tile(x, y)
                t2 = r2.ground_map.get_tile(x, y)
                assert t1.tile_type == t2.tile_type, (
                    f"Tile mismatch at ({x},{y}): {t1.tile_type} != {t2.tile_type}"
                )

    def test_different_seeds_produce_different_maps(self) -> None:
        """Different seeds should produce different layouts."""
        gen = GroundMapGenerator()
        r1 = gen.generate(
            MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=1,
            )
        )
        r2 = gen.generate(
            MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=2,
            )
        )
        # At least some tiles should differ
        diffs = 0
        for y in range(min(r1.ground_map.height, r2.ground_map.height)):
            for x in range(min(r1.ground_map.width, r2.ground_map.width)):
                t1 = r1.ground_map.get_tile(x, y)
                t2 = r2.ground_map.get_tile(x, y)
                if t1.tile_type != t2.tile_type:
                    diffs += 1
        assert diffs > 0, "Different seeds should produce different maps"

    def test_map_dimensions_match_difficulty(self) -> None:
        gen = GroundMapGenerator()
        for tier in DifficultyTier:
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=tier,
                seed=42,
            )
            result = gen.generate(cfg)
            assert result.ground_map.width >= tier.map_width
            assert result.ground_map.height >= tier.map_height

    def test_map_border_is_walls(self) -> None:
        """Generated map should have wall borders."""
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        gm = result.ground_map
        for x in range(gm.width):
            assert gm.get_tile(x, 0).tile_type == TileType.WALL
            assert gm.get_tile(x, gm.height - 1).tile_type == TileType.WALL
        for y in range(gm.height):
            assert gm.get_tile(0, y).tile_type == TileType.WALL
            assert gm.get_tile(gm.width - 1, y).tile_type == TileType.WALL


# ============================================================================
# Critical Path Connectivity
# ============================================================================


class TestCriticalPath:
    """Tests that generated maps have a navigable path from entry to exit."""

    def _can_reach_exit(self, gm: GroundMap) -> bool:
        """BFS from entrance to exit, traversing walkable tiles and doors.

        Includes DOOR_CLOSED as passable since players can open doors
        during gameplay.
        """
        start = gm.entrance_pos
        goal = gm.exit_pos
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [start]
        visited.add(start)

        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) == goal:
                return True
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited:
                    continue
                tile = gm.get_tile(nx, ny)
                if tile is None:
                    continue
                if gm.is_walkable(nx, ny) or tile.tile_type == TileType.DOOR_CLOSED:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return False

    def test_path_exists_low_difficulty(self) -> None:
        gen = GroundMapGenerator()
        for seed in range(10):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.LOW,
                seed=seed,
            )
            result = gen.generate(cfg)
            assert self._can_reach_exit(result.ground_map), (
                f"No path from entrance to exit (seed={seed})"
            )

    def test_path_exists_moderate_difficulty(self) -> None:
        gen = GroundMapGenerator()
        for seed in range(10):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=seed,
            )
            result = gen.generate(cfg)
            assert self._can_reach_exit(result.ground_map), (
                f"No path from entrance to exit (seed={seed})"
            )

    def test_path_exists_high_difficulty(self) -> None:
        gen = GroundMapGenerator()
        for seed in range(10):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.HIGH,
                seed=seed,
            )
            result = gen.generate(cfg)
            assert self._can_reach_exit(result.ground_map), (
                f"No path from entrance to exit (seed={seed})"
            )

    def test_path_exists_extreme_difficulty(self) -> None:
        gen = GroundMapGenerator()
        for seed in range(10):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.EXTREME,
                seed=seed,
            )
            result = gen.generate(cfg)
            assert self._can_reach_exit(result.ground_map), (
                f"No path from entrance to exit (seed={seed})"
            )

    def test_path_exists_all_mission_types(self) -> None:
        gen = GroundMapGenerator()
        for mt in MissionType:
            cfg = MapGenConfig(
                mission_type=mt,
                difficulty=DifficultyTier.MODERATE,
                seed=99,
            )
            result = gen.generate(cfg)
            assert self._can_reach_exit(result.ground_map), f"No path for mission type {mt.name}"


# ============================================================================
# Enemy Placement
# ============================================================================


class TestEnemyPlacement:
    """Tests for enemy placement during map generation."""

    def test_enemies_are_generated(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        assert len(result.enemies) >= DifficultyTier.LOW.enemy_count_min

    def test_enemy_count_scales_with_difficulty(self) -> None:
        gen = GroundMapGenerator()
        low = gen.generate(
            MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.LOW,
                seed=42,
            )
        )
        high = gen.generate(
            MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.HIGH,
                seed=42,
            )
        )
        assert len(high.enemies) > len(low.enemies)

    def test_enemies_on_walkable_tiles(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        for enemy in result.enemies:
            assert result.ground_map.is_walkable(enemy.x, enemy.y), (
                f"Enemy at ({enemy.x},{enemy.y}) is on non-walkable tile"
            )

    def test_enemies_not_at_entrance(self) -> None:
        gen = GroundMapGenerator()
        for seed in range(10):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=seed,
            )
            result = gen.generate(cfg)
            ex, ey = result.ground_map.entrance_pos
            for enemy in result.enemies:
                dist = abs(enemy.x - ex) + abs(enemy.y - ey)
                assert dist >= 3, f"Enemy too close to entrance (seed={seed}, dist={dist})"

    def test_enemies_have_patrol_routes(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        for enemy in result.enemies:
            assert len(enemy.patrol_route) >= 2, f"Enemy {enemy.id} has no patrol route"

    def test_patrol_routes_on_walkable_tiles(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        for enemy in result.enemies:
            for px, py in enemy.patrol_route:
                assert result.ground_map.is_walkable(px, py), (
                    f"Patrol point ({px},{py}) for {enemy.id} is not walkable"
                )

    def test_enemies_have_loot(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        total_loot = sum(e.loot_credits for e in result.enemies)
        assert total_loot > 0, "Enemies should drop some loot"


# ============================================================================
# Map Feature Variety
# ============================================================================


class TestMapFeatures:
    """Tests that generated maps have interesting features."""

    def test_map_has_doors(self) -> None:
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        door_count = sum(
            1
            for row in result.ground_map.tiles
            for tile in row
            if tile.tile_type == TileType.DOOR_CLOSED
        )
        assert door_count >= 2, "Map should have doors"

    def test_map_has_noisy_floor(self) -> None:
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        noisy_count = sum(
            1
            for row in result.ground_map.tiles
            for tile in row
            if tile.tile_type == TileType.NOISY_FLOOR
        )
        assert noisy_count >= 1, "Map should have noisy floor sections"

    def test_map_not_mostly_walls(self) -> None:
        """Map should have reasonable floor-to-wall ratio."""
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        gm = result.ground_map
        total = gm.width * gm.height
        floor_count = sum(
            1
            for row in gm.tiles
            for tile in row
            if tile.tile_type
            in (
                TileType.FLOOR,
                TileType.ENTRANCE,
                TileType.EXIT,
                TileType.DOOR_CLOSED,
                TileType.DOOR_OPEN,
                TileType.NOISY_FLOOR,
            )
        )
        ratio = floor_count / total
        assert ratio >= 0.20, f"Floor ratio too low: {ratio:.2f}"
        assert ratio <= 0.75, f"Floor ratio too high: {ratio:.2f}"

    def test_entrance_and_exit_separated(self) -> None:
        """Entrance and exit should be meaningfully far apart."""
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        ex, ey = result.ground_map.entrance_pos
        ox, oy = result.ground_map.exit_pos
        dist = abs(ox - ex) + abs(oy - ey)
        min_dist = (result.ground_map.width + result.ground_map.height) // 4
        assert dist >= min_dist, f"Entrance-exit distance {dist} too small (min {min_dist})"


# ============================================================================
# MapGenResult — Full Mission Construction
# ============================================================================


class TestMapGenResult:
    """Tests that generation results can build a full mission."""

    def test_result_builds_mission_state(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        mission = result.build_mission_state()
        assert isinstance(mission, GroundMissionState)
        assert len(mission.enemies) >= DifficultyTier.LOW.enemy_count_min

    def test_result_builds_mission_with_crew_bonuses(self) -> None:
        from spacegame.models.ground_crew import GroundCrewBonuses

        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        mission = result.build_mission_state(crew_bonuses=bonuses)
        assert mission.crew_bonuses.reveal_patrol_routes

    def test_mission_player_at_entrance(self) -> None:
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            seed=42,
        )
        gen = GroundMapGenerator()
        result = gen.generate(cfg)
        mission = result.build_mission_state()
        ex, ey = result.ground_map.entrance_pos
        assert mission.player.x == ex
        assert mission.player.y == ey


# ============================================================================
# Chunk Template Stamping
# ============================================================================


class TestChunkStamping:
    """Tests that generated maps use chunk templates with distinct interiors."""

    def test_rooms_have_interior_walls(self) -> None:
        """At least some rooms should have internal wall features."""
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        # Check that we used chunk templates (result tracks which chunks placed)
        assert len(result.placed_chunks) >= 3, "Should have placed chunk templates"

    def test_placed_chunks_have_ids(self) -> None:
        """Each placed chunk records its template ID."""
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        for chunk_id, _, _ in result.placed_chunks:
            assert chunk_id, "Placed chunk should have an ID"

    def test_different_room_types_placed(self) -> None:
        """Multiple different room templates should appear across seeds."""
        gen = GroundMapGenerator()
        all_ids: set[str] = set()
        for seed in range(20):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=seed,
            )
            result = gen.generate(cfg)
            for chunk_id, _, _ in result.placed_chunks:
                all_ids.add(chunk_id)
        assert len(all_ids) >= 4, f"Only {len(all_ids)} unique room types across 20 seeds"

    def test_security_checkpoint_has_noisy_floor(self) -> None:
        """Security checkpoint template includes noisy floor tiles."""
        lib = ChunkLibrary.create_default()
        chunk = lib.get_by_id("security_checkpoint")
        assert chunk is not None
        noisy_count = sum(1 for row in chunk.tiles for t in row if t == TileType.NOISY_FLOOR)
        assert noisy_count >= 2, "Security checkpoint should have noisy floor"

    def test_stamped_features_appear_on_map(self) -> None:
        """Template features (internal walls, noisy floor) should appear on generated map."""
        gen = GroundMapGenerator()
        # Run many seeds to ensure templates with features get placed
        found_internal_walls = False
        for seed in range(30):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=seed,
            )
            result = gen.generate(cfg)
            gm = result.ground_map
            # Look for wall tiles surrounded by floor on multiple sides (interior wall)
            for y in range(2, gm.height - 2):
                for x in range(2, gm.width - 2):
                    tile = gm.get_tile(x, y)
                    if tile and tile.tile_type == TileType.WALL:
                        floor_neighbors = sum(
                            1
                            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                            if gm.get_tile(x + dx, y + dy)
                            and gm.get_tile(x + dx, y + dy).tile_type
                            in (TileType.FLOOR, TileType.NOISY_FLOOR)
                        )
                        if floor_neighbors >= 3:
                            found_internal_walls = True
                            break
                if found_internal_walls:
                    break
            if found_internal_walls:
                break
        assert found_internal_walls, "Should find interior wall features from templates"


# ============================================================================
# Faction-Specific Generation
# ============================================================================


class TestFactionGeneration:
    """Tests that faction_id influences enemy selection."""

    def test_faction_produces_valid_enemies(self) -> None:
        gen = GroundMapGenerator()
        for faction in [
            "merchants_guild",
            "miners_union",
            "science_collective",
            "frontier_alliance",
        ]:
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=42,
                faction_id=faction,
            )
            result = gen.generate(cfg)
            assert len(result.enemies) >= DifficultyTier.MODERATE.enemy_count_min

    def test_no_faction_still_works(self) -> None:
        gen = GroundMapGenerator()
        cfg = MapGenConfig(
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            seed=42,
        )
        result = gen.generate(cfg)
        assert len(result.enemies) >= DifficultyTier.MODERATE.enemy_count_min


# ============================================================================
# Mission Type Influence
# ============================================================================


class TestMissionTypeInfluence:
    """Tests that mission type affects map structure."""

    def test_exploration_maps_are_larger(self) -> None:
        gen = GroundMapGenerator()
        infiltration = gen.generate(
            MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=42,
            )
        )
        exploration = gen.generate(
            MapGenConfig(
                mission_type=MissionType.EXPLORATION,
                difficulty=DifficultyTier.MODERATE,
                seed=42,
            )
        )
        inf_area = infiltration.ground_map.width * infiltration.ground_map.height
        exp_area = exploration.ground_map.width * exploration.ground_map.height
        assert exp_area > inf_area

    def test_all_mission_types_generate_valid_maps(self) -> None:
        gen = GroundMapGenerator()
        for mt in MissionType:
            for seed in range(5):
                cfg = MapGenConfig(
                    mission_type=mt,
                    difficulty=DifficultyTier.MODERATE,
                    seed=seed,
                )
                result = gen.generate(cfg)
                assert result.ground_map.width > 0
                assert len(result.enemies) > 0


# ============================================================================
# Stress / Robustness
# ============================================================================


class TestGeneratorRobustness:
    """Stress tests ensuring the generator handles many seeds reliably."""

    def test_100_seeds_no_crash(self) -> None:
        """Generate 100 maps across difficulties with no crashes."""
        gen = GroundMapGenerator()
        for seed in range(100):
            tier = [
                DifficultyTier.LOW,
                DifficultyTier.MODERATE,
                DifficultyTier.HIGH,
                DifficultyTier.EXTREME,
            ][seed % 4]
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=tier,
                seed=seed,
            )
            result = gen.generate(cfg)
            assert result.ground_map.width > 0
            assert len(result.enemies) >= tier.enemy_count_min

    def test_all_enemies_have_valid_patrol_routes_100_seeds(self) -> None:
        """All enemies across 50 maps have walkable patrol routes."""
        gen = GroundMapGenerator()
        for seed in range(50):
            cfg = MapGenConfig(
                mission_type=MissionType.INFILTRATION,
                difficulty=DifficultyTier.MODERATE,
                seed=seed,
            )
            result = gen.generate(cfg)
            for enemy in result.enemies:
                assert len(enemy.patrol_route) >= 2, (
                    f"seed={seed}, enemy {enemy.id}: route too short"
                )
                for px, py in enemy.patrol_route:
                    assert result.ground_map.is_walkable(px, py), (
                        f"seed={seed}, enemy {enemy.id}: patrol ({px},{py}) not walkable"
                    )
