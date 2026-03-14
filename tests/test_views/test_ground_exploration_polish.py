"""Tests for ground exploration view polish fixes.

Covers E-key loot container interaction through the view, story trigger
fire-on-movement integration, enemy template fallback behavior,
combat-to-result flow, and all mission ending paths.
"""

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState
from spacegame.models.ground import (
    GroundInteractable,
    GroundMap,
    GroundPlayerState,
    GroundStoryTrigger,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import (
    AlertLevel,
    Direction,
    GroundEnemy,
    GroundMissionState,
)
from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionRewards,
    MissionOutcome,
)
from spacegame.models.ground_mapgen import DifficultyTier, MissionType
from spacegame.views.ground_exploration_view import GroundExplorationView


@pytest.fixture(autouse=True, scope="module")
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
        "objectives": ["Reach the exit"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=500, xp=25, crew_xp=10),
        "max_crew": 2,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_view_with_state(
    width: int = 10,
    height: int = 10,
    player_x: int = 3,
    player_y: int = 3,
    interactables: list = None,
    story_triggers: list = None,
    enemies: list = None,
    mission_config: GroundMissionConfig = None,
) -> GroundExplorationView:
    """Create a view with a mission state containing entities."""
    ground_map = GroundMap.create_test_map(width, height)
    player_state = GroundPlayerState(x=player_x, y=player_y)
    mission_state = GroundMissionState(
        ground_map=ground_map,
        player=player_state,
        enemies=enemies or [],
        interactables=interactables or [],
        story_triggers=story_triggers or [],
    )
    ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = GroundExplorationView(
        ui_manager=ui,
        ground_map=ground_map,
        player_state=player_state,
        mission_state=mission_state,
        mission_config=mission_config,
    )
    view.on_enter()
    return view


def _send_key(view: GroundExplorationView, key: int) -> None:
    """Simulate a KEYDOWN event."""
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)
    view.handle_event(event)


# ============================================================================
# GAP 1: E-Key Loot Container Interaction (through the view)
# ============================================================================


class TestViewLootInteraction:
    """E-key looting through the view updates mission tracking."""

    def test_e_key_loots_adjacent_container(self):
        """E key interaction with adjacent container increments total_loot_credits."""
        container = GroundInteractable(
            x=4, y=3, interact_type="loot_container",
            loot_credits=75, description="Supply crate",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, interactables=[container],
        )
        # Face right toward container
        _send_key(view, pygame.K_RIGHT)
        # Player hits wall or moves; either way _last_dx is set to right.
        # Reset player position to ensure adjacency
        view.player_state.x = 3
        view.player_state.y = 3
        view._last_dx = 1
        view._last_dy = 0

        _send_key(view, pygame.K_e)

        assert container.looted is True
        assert view.total_loot_credits == 75
        view.on_exit()

    def test_e_key_shows_container_description(self):
        """Looting a container with description shows it in the message."""
        container = GroundInteractable(
            x=4, y=3, interact_type="loot_container",
            loot_credits=100, description="Salvage bin",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, interactables=[container],
        )
        view._last_dx = 1
        view._last_dy = 0

        _send_key(view, pygame.K_e)

        assert "Salvage bin" in view._message
        assert "100" in view._message
        view.on_exit()

    def test_e_key_looted_container_does_not_add_credits(self):
        """Looting an already-looted container doesn't add to total."""
        container = GroundInteractable(
            x=4, y=3, interact_type="loot_container",
            loot_credits=50, description="Empty box",
        )
        container.loot()  # Already looted
        view = _make_view_with_state(
            player_x=3, player_y=3, interactables=[container],
        )
        view._last_dx = 1
        view._last_dy = 0

        _send_key(view, pygame.K_e)

        assert view.total_loot_credits == 0
        view.on_exit()

    def test_e_key_door_does_not_trigger_loot_tracking(self):
        """Opening a door via E key does not add to loot credits."""
        view = _make_view_with_state(player_x=3, player_y=3)
        # Place a door to the right
        view.ground_map.tiles[3][4] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        view._last_dx = 1
        view._last_dy = 0

        _send_key(view, pygame.K_e)

        assert view.total_loot_credits == 0
        assert view.ground_map.get_tile(4, 3).tile_type == TileType.DOOR_OPEN
        view.on_exit()

    def test_e_key_door_triggers_noise(self):
        """Opening a door triggers door noise processing (not loot)."""
        view = _make_view_with_state(player_x=3, player_y=3)
        view.ground_map.tiles[3][4] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        view._last_dx = 1
        view._last_dy = 0

        initial_turn = view.player_state.turn_number
        _send_key(view, pygame.K_e)

        # Door interaction costs a turn
        assert view.player_state.turn_number == initial_turn + 1
        view.on_exit()


# ============================================================================
# GAP 2: Story Trigger Fire on Movement (integration)
# ============================================================================


class TestStoryTriggerOnMovement:
    """Story triggers fire automatically when player moves onto their tile."""

    def test_trigger_fires_on_player_movement(self):
        """Moving onto a story trigger tile fires it automatically."""
        trigger = GroundStoryTrigger(
            x=4, y=3, trigger_type="atmosphere",
            text="Rust-stained walls whisper of forgotten cargo.",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, story_triggers=[trigger],
        )

        # Move right onto trigger position
        _send_key(view, pygame.K_RIGHT)

        assert view.player_state.x == 4
        assert trigger.triggered is True
        assert "Rust-stained" in view._message
        view.on_exit()

    def test_trigger_does_not_fire_twice(self):
        """Returning to a triggered tile does not fire it again."""
        trigger = GroundStoryTrigger(
            x=4, y=3, trigger_type="atmosphere",
            text="First time only.",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, story_triggers=[trigger],
        )

        # Move right onto trigger
        _send_key(view, pygame.K_RIGHT)
        assert trigger.triggered is True

        # Move away and back
        _send_key(view, pygame.K_LEFT)
        view._message = ""  # Clear message
        _send_key(view, pygame.K_RIGHT)

        # Should not show the message again
        assert view._message == "" or "First time" not in view._message
        view.on_exit()

    def test_trigger_not_on_player_tile_does_not_fire(self):
        """Triggers at other positions don't fire when player moves elsewhere."""
        trigger = GroundStoryTrigger(
            x=8, y=8, trigger_type="discovery",
            text="Should not appear.",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, story_triggers=[trigger],
        )

        _send_key(view, pygame.K_RIGHT)

        assert trigger.triggered is False
        view.on_exit()

    def test_trigger_uses_extended_message_duration(self):
        """Story trigger messages use longer display time than normal messages."""
        trigger = GroundStoryTrigger(
            x=4, y=3, trigger_type="atmosphere",
            text="A narrative moment.",
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, story_triggers=[trigger],
        )

        _send_key(view, pygame.K_RIGHT)

        assert view._message_timer >= 4.0
        view.on_exit()


# ============================================================================
# GAP 3: Enemy Template Fallback
# ============================================================================


class TestEnemyTemplateFallback:
    """Combat initialization handles unknown enemy IDs gracefully."""

    def test_unknown_enemy_id_uses_fallback(self):
        """Enemy with unrecognized ID falls back to guild_security template."""
        enemy = GroundEnemy(
            id="completely_unknown_type",
            x=4, y=3,
            facing=Direction.LEFT,
            patrol_route=[(4, 3)],
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, enemies=[enemy],
        )
        # Set alert to combat to trigger combat start
        view.mission_state.alert_level = AlertLevel.COMBAT
        view._start_combat()

        # Should not crash — should use fallback template
        assert view._combat_state is not None
        assert len(view._combat_state.enemies) == 1
        view.on_exit()

    def test_campaign_enemy_id_uses_fallback(self):
        """Campaign map enemy IDs (like 'guild_watch_1') use fallback gracefully."""
        enemy = GroundEnemy(
            id="guild_watch_1",
            x=4, y=3,
            facing=Direction.RIGHT,
            patrol_route=[(4, 3)],
        )
        view = _make_view_with_state(
            player_x=3, player_y=3, enemies=[enemy],
        )
        view.mission_state.alert_level = AlertLevel.COMBAT
        view._start_combat()

        assert view._combat_state is not None
        assert len(view._combat_state.enemies) == 1
        view.on_exit()


# ============================================================================
# GAP 4 & 5: Mission Ending Paths (success, fled, defeat)
# ============================================================================


def _make_linear_map(length: int = 5) -> GroundMap:
    """Create a 1-row linear map: ENTRANCE - FLOOR... - EXIT."""
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


class TestSuccessPathEndToEnd:
    """Walking onto exit tile builds SUCCESS result with correct data."""

    def test_exit_tile_builds_success_result(self):
        """Stepping on exit tile sets GROUND_RESULT and stores SUCCESS outcome."""
        config = _make_config()
        ground_map = _make_linear_map(length=5)
        player_state = GroundPlayerState(x=3, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = GroundExplorationView(
            ui_manager=ui,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Simulate some mission progress
        view.total_loot_credits = 200
        view.total_enemies_defeated = 3

        # Step onto exit
        _send_key(view, pygame.K_RIGHT)

        assert view.get_next_state() == GameState.GROUND_RESULT
        result = view.get_mission_result(MissionOutcome.SUCCESS)
        assert result is not None
        assert result.outcome == MissionOutcome.SUCCESS
        assert result.loot_credits == 200
        assert result.enemies_defeated == 3
        assert result.progress_percent == 1.0
        view.on_exit()

    def test_undetected_success_tracked(self):
        """Undetected completion is reflected in the result."""
        config = _make_config()
        ground_map = _make_linear_map(length=4)
        player_state = GroundPlayerState(x=2, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = GroundExplorationView(
            ui_manager=ui,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Step onto exit without being detected
        _send_key(view, pygame.K_RIGHT)

        result = view.get_mission_result(MissionOutcome.SUCCESS)
        assert result.detected is False
        assert result.is_ghost_run is True
        view.on_exit()


class TestFledPathEndToEnd:
    """Escape key builds FLED result with correct data."""

    def test_escape_builds_fled_result_with_progress(self):
        """Escape halfway through has partial progress in the result."""
        config = _make_config()
        ground_map = _make_linear_map(length=10)
        # Start at entrance, move to middle
        player_state = GroundPlayerState(x=0, y=1)
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
        )
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = GroundExplorationView(
            ui_manager=ui,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Move partway through
        for _ in range(5):
            _send_key(view, pygame.K_RIGHT)

        view.total_loot_credits = 30

        _send_key(view, pygame.K_ESCAPE)

        assert view.get_next_state() == GameState.GROUND_RESULT
        result = view.get_mission_result(MissionOutcome.FLED)
        assert result.outcome == MissionOutcome.FLED
        assert result.loot_credits == 30
        assert 0.0 < result.progress_percent < 1.0
        view.on_exit()


class TestDefeatPathEndToEnd:
    """Combat defeat ends mission and builds DEFEATED result."""

    def test_defeat_end_combat_sets_mission_outcome(self):
        """_end_combat with DEFEAT outcome triggers _end_mission."""
        from spacegame.models.ground_combat import CombatOutcome

        config = _make_config()
        ground_map = GroundMap.create_test_map(10, 10)
        player_state = GroundPlayerState(x=3, y=3)
        enemy = GroundEnemy(
            id="test_guard", x=4, y=3,
            facing=Direction.LEFT, patrol_route=[(4, 3)],
        )
        mission_state = GroundMissionState(
            ground_map=ground_map,
            player=player_state,
            enemies=[enemy],
        )
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = GroundExplorationView(
            ui_manager=ui,
            ground_map=ground_map,
            player_state=player_state,
            mission_state=mission_state,
            mission_config=config,
        )
        view.on_enter()

        # Simulate combat defeat
        view._end_combat(CombatOutcome.DEFEAT)

        assert view.get_next_state() == GameState.GROUND_RESULT
        result = view.get_mission_result(MissionOutcome.DEFEATED)
        assert result is not None
        assert result.outcome == MissionOutcome.DEFEATED
        assert result.detected is True  # Defeat implies detection
        view.on_exit()
