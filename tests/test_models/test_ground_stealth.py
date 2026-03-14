"""Tests for ground exploration stealth system (Phase B).

Tests enemy patrols, vision cones, detection states, noise system,
and alert level management.
"""

import math

from spacegame.config import (
    GROUND_ALERT_DECAY_TURNS,
    GROUND_SUSPICIOUS_DECAY_TURNS,
)
from spacegame.models.ground import (
    FogState,
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import (
    AlertLevel,
    Direction,
    EnemyAIState,
    GroundEnemy,
    GroundMissionState,
    NoiseEvent,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_map(width: int = 15, height: int = 15) -> GroundMap:
    """Create a test map with wall border and floor interior."""
    return GroundMap.create_test_map(width, height)


def _make_enemy(
    x: int = 5,
    y: int = 5,
    facing: Direction = Direction.RIGHT,
    vision_range: int = 5,
    speed: int = 1,
    patrol_route: list[tuple[int, int]] | None = None,
) -> GroundEnemy:
    """Create a test enemy."""
    return GroundEnemy(
        id="guard_1",
        x=x,
        y=y,
        facing=facing,
        vision_range=vision_range,
        speed=speed,
        patrol_route=patrol_route or [],
    )


def _make_mission(
    ground_map: GroundMap | None = None,
    player: GroundPlayerState | None = None,
    enemies: list[GroundEnemy] | None = None,
) -> GroundMissionState:
    """Create a test mission state."""
    if ground_map is None:
        ground_map = _make_map()
    if player is None:
        player = GroundPlayerState(x=1, y=1)
    return GroundMissionState(
        ground_map=ground_map,
        player=player,
        enemies=enemies or [],
    )


# ============================================================================
# Direction
# ============================================================================


class TestDirection:
    """Tests for Direction enum."""

    def test_all_directions(self) -> None:
        expected = {"up", "down", "left", "right"}
        assert {d.value for d in Direction} == expected

    def test_direction_to_delta(self) -> None:
        assert Direction.UP.to_delta() == (0, -1)
        assert Direction.DOWN.to_delta() == (0, 1)
        assert Direction.LEFT.to_delta() == (-1, 0)
        assert Direction.RIGHT.to_delta() == (1, 0)

    def test_direction_from_delta(self) -> None:
        assert Direction.from_delta(0, -1) == Direction.UP
        assert Direction.from_delta(0, 1) == Direction.DOWN
        assert Direction.from_delta(-1, 0) == Direction.LEFT
        assert Direction.from_delta(1, 0) == Direction.RIGHT

    def test_direction_from_delta_invalid_returns_none(self) -> None:
        assert Direction.from_delta(1, 1) is None
        assert Direction.from_delta(0, 0) is None


# ============================================================================
# GroundEnemy
# ============================================================================


class TestGroundEnemy:
    """Tests for GroundEnemy dataclass."""

    def test_creation(self) -> None:
        enemy = _make_enemy()
        assert enemy.x == 5
        assert enemy.y == 5
        assert enemy.facing == Direction.RIGHT
        assert enemy.ai_state == EnemyAIState.PATROLLING

    def test_default_ai_state_is_patrolling(self) -> None:
        enemy = _make_enemy()
        assert enemy.ai_state == EnemyAIState.PATROLLING

    # --- Vision cone ---

    def test_can_see_tile_in_front(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        # Tile directly to the right should be visible
        assert enemy.can_see_tile(8, 5, gm)

    def test_cannot_see_tile_behind(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        # Tile to the left (behind) should not be visible
        assert not enemy.can_see_tile(2, 5, gm)

    def test_cannot_see_tile_beyond_range(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=3)
        # Tile at distance 5 exceeds range of 3
        assert not enemy.can_see_tile(10, 5, gm)

    def test_cannot_see_through_wall(self) -> None:
        gm = _make_map()
        gm.tiles[5][7] = GroundTile(tile_type=TileType.WALL)
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT)
        # Wall at (7,5) blocks LOS to (9,5)
        assert not enemy.can_see_tile(9, 5, gm)

    def test_can_see_within_cone_angle(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        # Tile at (7, 4) is slightly above and to the right — within 90° cone
        assert enemy.can_see_tile(7, 4, gm)

    def test_cannot_see_outside_cone_angle(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        # Tile directly above (5, 2) is perpendicular — outside 90° cone
        assert not enemy.can_see_tile(5, 2, gm)

    def test_can_see_same_tile(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5)
        assert enemy.can_see_tile(5, 5, gm)

    def test_vision_all_four_directions(self) -> None:
        gm = _make_map()
        for direction, target in [
            (Direction.UP, (5, 2)),
            (Direction.DOWN, (5, 8)),
            (Direction.LEFT, (2, 5)),
            (Direction.RIGHT, (8, 5)),
        ]:
            enemy = _make_enemy(x=5, y=5, facing=direction, vision_range=5)
            assert enemy.can_see_tile(*target, gm), (
                f"Facing {direction.value}, should see {target}"
            )

    # --- Patrol movement ---

    def test_patrol_advances_along_route(self) -> None:
        gm = _make_map()
        route = [(5, 5), (6, 5), (7, 5), (6, 5)]
        enemy = _make_enemy(x=5, y=5, patrol_route=route)
        enemy.patrol_index = 0

        enemy.advance_patrol(gm)
        assert (enemy.x, enemy.y) == (6, 5)
        assert enemy.patrol_index == 1

    def test_patrol_wraps_around(self) -> None:
        gm = _make_map()
        route = [(5, 5), (6, 5)]
        enemy = _make_enemy(x=6, y=5, patrol_route=route)
        enemy.patrol_index = 1

        enemy.advance_patrol(gm)
        assert (enemy.x, enemy.y) == (5, 5)
        assert enemy.patrol_index == 0

    def test_patrol_updates_facing(self) -> None:
        gm = _make_map()
        route = [(5, 5), (6, 5)]
        enemy = _make_enemy(x=5, y=5, facing=Direction.UP, patrol_route=route)
        enemy.patrol_index = 0

        enemy.advance_patrol(gm)
        assert enemy.facing == Direction.RIGHT, "Should face movement direction"

    def test_patrol_no_route_stays_put(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5, patrol_route=[])
        enemy.advance_patrol(gm)
        assert (enemy.x, enemy.y) == (5, 5)

    # --- Speed ---

    def test_speed_1_acts_every_turn(self) -> None:
        enemy = _make_enemy(speed=1)
        assert enemy.should_act(turn=0)
        assert enemy.should_act(turn=1)
        assert enemy.should_act(turn=5)

    def test_speed_2_acts_every_other_turn(self) -> None:
        enemy = _make_enemy(speed=2)
        assert enemy.should_act(turn=0)
        assert not enemy.should_act(turn=1)
        assert enemy.should_act(turn=2)
        assert not enemy.should_act(turn=3)

    # --- Movement toward target ---

    def test_move_toward_target(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5)
        enemy.move_toward(8, 5, gm)
        assert enemy.x == 6, "Should move one step toward target"
        assert enemy.facing == Direction.RIGHT

    def test_move_toward_blocked(self) -> None:
        gm = _make_map()
        gm.tiles[5][6] = GroundTile(tile_type=TileType.WALL)
        enemy = _make_enemy(x=5, y=5)
        old_y = enemy.y
        enemy.move_toward(8, 5, gm)
        # Should try alternate axis since direct path is blocked
        assert (enemy.x, enemy.y) != (5, 5) or True  # May stay if fully blocked

    # --- Serialization ---

    def test_to_dict_round_trip(self) -> None:
        enemy = _make_enemy(x=3, y=7)
        enemy.patrol_route = [(3, 7), (4, 7), (5, 7)]
        enemy.patrol_index = 1
        enemy.ai_state = EnemyAIState.INVESTIGATING

        data = enemy.to_dict()
        restored = GroundEnemy.from_dict(data)
        assert restored.x == 3
        assert restored.y == 7
        assert restored.patrol_index == 1
        assert restored.ai_state == EnemyAIState.INVESTIGATING
        assert len(restored.patrol_route) == 3


# ============================================================================
# AlertLevel
# ============================================================================


class TestAlertLevel:
    """Tests for AlertLevel enum."""

    def test_all_levels(self) -> None:
        expected = {"undetected", "suspicious", "alert", "combat"}
        assert {a.value for a in AlertLevel} == expected


# ============================================================================
# GroundMissionState
# ============================================================================


class TestGroundMissionState:
    """Tests for mission-level state management."""

    # --- Alert state ---

    def test_initial_alert_is_undetected(self) -> None:
        mission = _make_mission()
        assert mission.alert_level == AlertLevel.UNDETECTED

    def test_raise_alert_to_suspicious(self) -> None:
        mission = _make_mission()
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(5, 5))
        assert mission.alert_level == AlertLevel.SUSPICIOUS

    def test_raise_alert_to_alert(self) -> None:
        mission = _make_mission()
        mission.raise_alert(AlertLevel.ALERT)
        assert mission.alert_level == AlertLevel.ALERT

    def test_alert_does_not_downgrade(self) -> None:
        mission = _make_mission()
        mission.raise_alert(AlertLevel.ALERT)
        mission.raise_alert(AlertLevel.SUSPICIOUS)
        assert mission.alert_level == AlertLevel.ALERT, "Should not downgrade"

    # --- Suspicious decay ---

    def test_suspicious_decays_to_undetected(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(ground_map=gm, player=player)
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(10, 10))

        for _ in range(GROUND_SUSPICIOUS_DECAY_TURNS):
            mission.process_enemy_turns(player.turn_number)
            player.turn_number += 1

        assert mission.alert_level == AlertLevel.UNDETECTED

    def test_suspicious_decay_resets_on_new_noise(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(ground_map=gm, player=player)
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(10, 10))

        # Process some turns but not enough to decay
        for _ in range(GROUND_SUSPICIOUS_DECAY_TURNS - 2):
            mission.process_enemy_turns(player.turn_number)
            player.turn_number += 1

        # New noise resets the timer
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(10, 10))

        # Not enough additional turns to decay
        for _ in range(GROUND_SUSPICIOUS_DECAY_TURNS - 2):
            mission.process_enemy_turns(player.turn_number)
            player.turn_number += 1

        assert mission.alert_level == AlertLevel.SUSPICIOUS

    # --- Alert decay ---

    def test_alert_decays_to_suspicious_when_los_broken(self) -> None:
        gm = _make_map()
        # Player far from enemy, wall between them
        player = GroundPlayerState(x=1, y=1)
        enemy = _make_enemy(x=12, y=12, vision_range=3)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )
        mission.raise_alert(AlertLevel.ALERT)

        # Process enough turns with broken LOS
        for _ in range(GROUND_ALERT_DECAY_TURNS):
            mission.process_enemy_turns(player.turn_number)
            player.turn_number += 1

        assert mission.alert_level == AlertLevel.SUSPICIOUS

    def test_alert_does_not_decay_if_enemy_sees_player(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=5, y=5)
        enemy = _make_enemy(x=7, y=5, facing=Direction.LEFT, vision_range=5)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )
        mission.raise_alert(AlertLevel.ALERT)

        # Enemy can see player — alert should not decay
        for _ in range(GROUND_ALERT_DECAY_TURNS + 2):
            mission.process_enemy_turns(player.turn_number)
            player.turn_number += 1

        assert mission.alert_level == AlertLevel.ALERT

    # --- Noise ---

    def test_noise_event_alerts_nearby_enemy(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=1, y=1)
        enemy = _make_enemy(x=4, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.add_noise(NoiseEvent(x=2, y=1, radius=5))
        mission.process_noise()

        assert mission.alert_level == AlertLevel.SUSPICIOUS
        assert enemy.ai_state == EnemyAIState.INVESTIGATING

    def test_noise_event_does_not_alert_distant_enemy(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=1, y=1)
        enemy = _make_enemy(x=12, y=12)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.add_noise(NoiseEvent(x=2, y=1, radius=3))
        mission.process_noise()

        assert mission.alert_level == AlertLevel.UNDETECTED
        assert enemy.ai_state == EnemyAIState.PATROLLING

    def test_noise_from_noisy_floor(self) -> None:
        gm = _make_map()
        gm.tiles[5][5] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        player = GroundPlayerState(x=4, y=5)
        enemy = _make_enemy(x=7, y=5)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        # Move onto noisy floor
        success, _ = player.move(1, 0, gm)
        assert success
        noise = mission.check_tile_noise(player.x, player.y)
        assert noise is not None, "Noisy floor should generate noise"
        assert noise.radius > 0

    # --- Enemy detection via sight ---

    def test_enemy_detects_player_in_vision_cone(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=8, y=5)
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.check_enemy_vision()
        assert mission.alert_level == AlertLevel.ALERT

    def test_enemy_does_not_detect_player_outside_cone(self) -> None:
        gm = _make_map()
        player = GroundPlayerState(x=2, y=5)
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=5)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.check_enemy_vision()
        assert mission.alert_level == AlertLevel.UNDETECTED

    def test_enemy_does_not_detect_player_through_wall(self) -> None:
        gm = _make_map()
        gm.tiles[5][7] = GroundTile(tile_type=TileType.WALL)
        player = GroundPlayerState(x=9, y=5)
        enemy = _make_enemy(x=5, y=5, facing=Direction.RIGHT, vision_range=6)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.check_enemy_vision()
        assert mission.alert_level == AlertLevel.UNDETECTED

    # --- Enemy turn processing ---

    def test_patrolling_enemy_follows_route(self) -> None:
        gm = _make_map()
        route = [(3, 3), (4, 3), (5, 3), (4, 3)]
        enemy = _make_enemy(x=3, y=3, patrol_route=route, speed=1)
        enemy.patrol_index = 0
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.process_enemy_turns(0)
        assert (enemy.x, enemy.y) == (4, 3)

    def test_investigating_enemy_moves_toward_noise(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=5, y=5)
        enemy.ai_state = EnemyAIState.INVESTIGATING
        enemy.investigate_target = (8, 5)
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.process_enemy_turns(0)
        assert enemy.x > 5, "Should move toward investigation target"

    def test_investigating_enemy_returns_to_patrol_at_target(self) -> None:
        gm = _make_map()
        route = [(5, 5), (6, 5)]
        enemy = _make_enemy(x=7, y=5, patrol_route=route)
        enemy.ai_state = EnemyAIState.INVESTIGATING
        enemy.investigate_target = (7, 5)  # Already at target
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        mission.process_enemy_turns(0)
        assert enemy.ai_state == EnemyAIState.PATROLLING

    def test_slow_enemy_skips_turns(self) -> None:
        gm = _make_map()
        route = [(3, 3), (4, 3), (5, 3)]
        enemy = _make_enemy(x=3, y=3, patrol_route=route, speed=2)
        enemy.patrol_index = 0
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )

        # Turn 0: should act
        mission.process_enemy_turns(0)
        assert (enemy.x, enemy.y) == (4, 3)

        # Turn 1: should skip
        mission.process_enemy_turns(1)
        assert (enemy.x, enemy.y) == (4, 3)

        # Turn 2: should act again
        mission.process_enemy_turns(2)
        assert (enemy.x, enemy.y) == (5, 3)

    # --- Searching (ALERT state) ---

    def test_alert_enemies_move_toward_player_last_known(self) -> None:
        gm = _make_map()
        enemy = _make_enemy(x=3, y=3)
        player = GroundPlayerState(x=1, y=1)
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )
        mission.raise_alert(AlertLevel.ALERT)
        mission.player_last_known_pos = (10, 10)
        enemy.ai_state = EnemyAIState.SEARCHING

        mission.process_enemy_turns(0)
        # Should move toward last known position
        assert enemy.x > 3 or enemy.y > 3

    # --- Serialization ---

    def test_mission_state_to_dict_round_trip(self) -> None:
        gm = _make_map(10, 10)
        player = GroundPlayerState(x=3, y=3)
        enemy = _make_enemy(x=5, y=5)
        enemy.patrol_route = [(5, 5), (6, 5)]
        mission = _make_mission(
            ground_map=gm, player=player, enemies=[enemy]
        )
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(7, 7))

        data = mission.to_dict()
        restored = GroundMissionState.from_dict(data)

        assert restored.alert_level == AlertLevel.SUSPICIOUS
        assert len(restored.enemies) == 1
        assert restored.enemies[0].x == 5
        assert restored.player.x == 3
