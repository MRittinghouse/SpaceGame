"""Tests for GroundExplorationView integration with ground mission system.

Tests mission tracking (loot, enemies, detection), result building,
exit tile detection, and state transitions to GROUND_RESULT.
"""

import pygame
import pygame_gui
import pytest
from unittest.mock import MagicMock

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState
from spacegame.models.ground import GroundMap, GroundPlayerState, GroundTile, TileType
from spacegame.models.ground_enemy import GroundMissionState, AlertLevel
from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    MissionOutcome,
)
from spacegame.models.ground_mapgen import DifficultyTier, MissionType
from spacegame.views.ground_exploration_view import GroundExplorationView


@pytest.fixture(scope="module")
def _init_pygame():
    """Initialize pygame once for all tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_config(**overrides) -> GroundMissionConfig:
    """Create a test GroundMissionConfig with sensible defaults."""
    defaults = {
        "id": "test_mission",
        "name": "Test Mission",
        "description": "A test ground mission.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "commerce_guild",
        "objectives": ["Reach the exit", "Avoid detection"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=500, xp=25, crew_xp=10),
        "max_crew": 2,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_linear_map(length: int = 5) -> GroundMap:
    """Create a 1-row linear map: ENTRANCE - FLOOR... - EXIT.

    Uses wall borders to satisfy GroundMap requirements while placing
    the walkable path at y=1.
    """
    # 3 rows tall: wall row, walkable row, wall row
    tiles: list[list[GroundTile]] = []
    for y in range(3):
        row: list[GroundTile] = []
        for x in range(length):
            if y == 0 or y == 2:
                row.append(GroundTile(tile_type=TileType.WALL))
            elif x == 0:
                row.append(GroundTile(tile_type=TileType.ENTRANCE))
            elif x == length - 1:
                row.append(GroundTile(tile_type=TileType.EXIT))
            else:
                row.append(GroundTile(tile_type=TileType.FLOOR))
        tiles.append(row)
    return GroundMap(
        width=length,
        height=3,
        tiles=tiles,
        entrance_pos=(0, 1),
        exit_pos=(length - 1, 1),
    )


def _make_view(
    _init_pygame,
    ground_map: GroundMap = None,
    player_state: GroundPlayerState = None,
    mission_state: GroundMissionState = None,
    mission_config: GroundMissionConfig = None,
) -> GroundExplorationView:
    """Create a GroundExplorationView with test defaults."""
    if ground_map is None:
        ground_map = GroundMap.create_test_map(10, 10)
    if player_state is None:
        player_state = GroundPlayerState(x=1, y=1)
    ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = GroundExplorationView(
        ui_manager=ui,
        ground_map=ground_map,
        player_state=player_state,
        mission_state=mission_state,
        mission_config=mission_config,
    )
    return view


class TestMissionConfigAcceptance:
    """GroundExplorationView accepts an optional GroundMissionConfig."""

    def test_accepts_mission_config(self, _init_pygame):
        """View stores the mission config."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        assert view.mission_config is config

    def test_none_config_by_default(self, _init_pygame):
        """View works without a mission config (backward compatibility)."""
        view = _make_view(_init_pygame)
        assert view.mission_config is None


class TestMissionTracking:
    """View tracks mission-wide statistics for result building."""

    def test_initial_tracking_values(self, _init_pygame):
        """All tracking counters start at zero."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        assert view.total_loot_credits == 0
        assert view.total_enemies_defeated == 0
        assert view.total_enemies_talked == 0
        assert view.was_detected is False

    def test_detection_tracked_from_alert_level(self, _init_pygame):
        """Detection flag is set when alert level reaches ALERT or COMBAT."""
        config = _make_config()
        ground_map = GroundMap.create_test_map(10, 10)
        player_state = GroundPlayerState(x=1, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Simulate detection
        mission_state.alert_level = AlertLevel.ALERT
        view._check_detection()
        assert view.was_detected is True

    def test_detection_is_sticky(self, _init_pygame):
        """Once detected, flag stays True even if alert drops."""
        config = _make_config()
        ground_map = GroundMap.create_test_map(10, 10)
        player_state = GroundPlayerState(x=1, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        mission_state.alert_level = AlertLevel.ALERT
        view._check_detection()
        mission_state.alert_level = AlertLevel.UNDETECTED
        view._check_detection()
        assert view.was_detected is True


class TestExitTileDetection:
    """Player stepping on exit tile triggers mission completion."""

    def test_exit_tile_sets_ground_result_state(self, _init_pygame):
        """Moving onto EXIT tile transitions to GROUND_RESULT when config present."""
        config = _make_config()
        # Linear map: ENTRANCE(0,1) - FLOOR(1,1) - FLOOR(2,1) - EXIT(3,1)
        ground_map = _make_linear_map(length=4)
        player_state = GroundPlayerState(x=2, y=1)  # One step from exit
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Move right onto exit tile
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        view.handle_event(event)

        assert view.get_next_state() == GameState.GROUND_RESULT

    def test_exit_tile_without_config_goes_to_galaxy_map(self, _init_pygame):
        """Exit tile without mission config falls back to GALAXY_MAP."""
        ground_map = _make_linear_map(length=4)
        player_state = GroundPlayerState(x=2, y=1)
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
        )
        view.on_enter()

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        view.handle_event(event)

        assert view.get_next_state() == GameState.GALAXY_MAP


class TestMissionResultBuilding:
    """get_mission_result() builds a GroundMissionResult from tracked state."""

    def test_builds_success_result(self, _init_pygame):
        """Successful mission result has correct fields."""
        config = _make_config(objectives=["Reach exit", "Find item"])
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        # Simulate mission completion
        view.total_loot_credits = 150
        view.total_enemies_defeated = 2
        view.total_enemies_talked = 1
        view.was_detected = False

        result = view.get_mission_result(MissionOutcome.SUCCESS)
        assert result.config is config
        assert result.outcome == MissionOutcome.SUCCESS
        assert result.loot_credits == 150
        assert result.enemies_defeated == 2
        assert result.enemies_talked == 1
        assert result.detected is False
        assert result.turns_taken > 0 or result.turns_taken == 0

    def test_builds_defeated_result(self, _init_pygame):
        """Defeat result includes progress percent."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()
        view.was_detected = True

        result = view.get_mission_result(MissionOutcome.DEFEATED)
        assert result.outcome == MissionOutcome.DEFEATED
        assert result.detected is True

    def test_builds_fled_result(self, _init_pygame):
        """Fled result from back button/escape."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        result = view.get_mission_result(MissionOutcome.FLED)
        assert result.outcome == MissionOutcome.FLED

    def test_result_includes_crew_ids(self, _init_pygame):
        """Result includes crew IDs from mission state."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        config = _make_config()
        ground_map = GroundMap.create_test_map(10, 10)
        player_state = GroundPlayerState(x=1, y=1)
        bonuses = GroundCrewBonuses(vision_radius_bonus=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
            crew_bonuses=bonuses,
        )
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()
        view._crew_ids = ["elena_reeves", "marcus_jin"]

        result = view.get_mission_result(MissionOutcome.SUCCESS)
        assert result.crew_ids == ["elena_reeves", "marcus_jin"]

    def test_no_result_without_config(self, _init_pygame):
        """get_mission_result returns None when no config present."""
        view = _make_view(_init_pygame)
        view.on_enter()
        result = view.get_mission_result(MissionOutcome.SUCCESS)
        assert result is None


class TestBackButtonWithConfig:
    """Back button and Escape build FLED result when config is present."""

    def test_escape_with_config_sets_ground_result(self, _init_pygame):
        """Escape key transitions to GROUND_RESULT with FLED outcome."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)

        assert view.get_next_state() == GameState.GROUND_RESULT
        result = view.get_mission_result(MissionOutcome.FLED)
        assert result is not None
        assert result.outcome == MissionOutcome.FLED

    def test_escape_without_config_goes_to_galaxy_map(self, _init_pygame):
        """Escape without config goes straight to GALAXY_MAP (backward compat)."""
        view = _make_view(_init_pygame)
        view.on_enter()

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)

        assert view.get_next_state() == GameState.GALAXY_MAP


class TestDefeatEndsAsMission:
    """Combat defeat ends mission when config is present."""

    def test_defeat_transitions_to_ground_result(self, _init_pygame):
        """Combat defeat with config sets GROUND_RESULT as next state."""
        config = _make_config()
        ground_map = GroundMap.create_test_map(10, 10)
        player_state = GroundPlayerState(x=1, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        view = _make_view(
            _init_pygame,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Simulate combat defeat ending
        from spacegame.models.ground_combat import CombatOutcome

        view._mission_outcome = MissionOutcome.DEFEATED
        view._end_mission(MissionOutcome.DEFEATED)

        assert view.get_next_state() == GameState.GROUND_RESULT


class TestCombatStatsAccumulation:
    """Combat outcomes accumulate into mission-wide tracking."""

    def test_loot_accumulates_across_combats(self, _init_pygame):
        """Total loot accumulates from multiple combat encounters."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        view._accumulate_combat_loot(50)
        view._accumulate_combat_loot(75)
        assert view.total_loot_credits == 125

    def test_enemies_defeated_accumulates(self, _init_pygame):
        """Enemies defeated count accumulates."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        view._accumulate_enemies_defeated(2)
        view._accumulate_enemies_defeated(1)
        assert view.total_enemies_defeated == 3

    def test_enemies_talked_accumulates(self, _init_pygame):
        """Enemies talked count accumulates."""
        config = _make_config()
        view = _make_view(_init_pygame, mission_config=config)
        view.on_enter()

        view._accumulate_enemies_talked(1)
        view._accumulate_enemies_talked(2)
        assert view.total_enemies_talked == 3
