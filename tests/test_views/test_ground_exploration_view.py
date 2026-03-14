"""Tests for ground exploration view — input handling, camera, fog, state transitions."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip(
    "pygame_gui", reason="pygame_gui required for view tests"
)

from spacegame.config import (  # noqa: E402
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    GameState,
    GROUND_TILE_SIZE,
)
from spacegame.models.ground import (  # noqa: E402
    FogState,
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
)
from spacegame.views.ground_exploration_view import GroundExplorationView  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_view(
    width: int = 15, height: int = 15, player_x: int = 5, player_y: int = 5
) -> tuple[GroundExplorationView, GroundMap, GroundPlayerState]:
    """Create a view with a test map and player state."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    ground_map = GroundMap.create_test_map(width, height)
    player_state = GroundPlayerState(x=player_x, y=player_y)
    view = GroundExplorationView(ui_manager, ground_map, player_state)
    view.on_enter()
    return view, ground_map, player_state


def _send_key(view: GroundExplorationView, key: int) -> None:
    """Simulate a KEYDOWN event."""
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)
    view.handle_event(event)


# ============================================================================
# Construction
# ============================================================================


class TestConstruction:
    """Tests for view initialization."""

    def test_view_created_with_map_and_player(self) -> None:
        view, gm, ps = _make_view()
        assert view.ground_map is gm
        assert view.player_state is ps
        view.on_exit()

    def test_initial_camera_at_player_position(self) -> None:
        view, _, ps = _make_view(player_x=7, player_y=3)
        expected_x = 7 * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        expected_y = 3 * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        assert view._camera_x == float(expected_x)
        assert view._camera_y == float(expected_y)
        view.on_exit()

    def test_next_state_initially_none(self) -> None:
        view, _, _ = _make_view()
        assert view.get_next_state() is None
        view.on_exit()

    def test_fog_updated_on_enter(self) -> None:
        view, gm, ps = _make_view()
        # Player position should be visible after on_enter
        assert gm.get_tile(ps.x, ps.y).fog_state == FogState.VISIBLE
        view.on_exit()


# ============================================================================
# Player Input
# ============================================================================


class TestPlayerInput:
    """Tests for keyboard-driven player movement."""

    def test_arrow_up_moves_player(self) -> None:
        view, _, ps = _make_view()
        initial_y = ps.y
        _send_key(view, pygame.K_UP)
        assert ps.y == initial_y - 1
        view.on_exit()

    def test_arrow_down_moves_player(self) -> None:
        view, _, ps = _make_view()
        initial_y = ps.y
        _send_key(view, pygame.K_DOWN)
        assert ps.y == initial_y + 1
        view.on_exit()

    def test_arrow_left_moves_player(self) -> None:
        view, _, ps = _make_view()
        initial_x = ps.x
        _send_key(view, pygame.K_LEFT)
        assert ps.x == initial_x - 1
        view.on_exit()

    def test_arrow_right_moves_player(self) -> None:
        view, _, ps = _make_view()
        initial_x = ps.x
        _send_key(view, pygame.K_RIGHT)
        assert ps.x == initial_x + 1
        view.on_exit()

    def test_wasd_movement(self) -> None:
        view, _, ps = _make_view()
        start_x, start_y = ps.x, ps.y
        _send_key(view, pygame.K_w)
        assert ps.y == start_y - 1, "W should move up"
        _send_key(view, pygame.K_s)
        assert ps.y == start_y, "S should move down"
        _send_key(view, pygame.K_a)
        assert ps.x == start_x - 1, "A should move left"
        _send_key(view, pygame.K_d)
        assert ps.x == start_x, "D should move right"
        view.on_exit()

    def test_move_into_wall_shows_message(self) -> None:
        view, _, ps = _make_view(player_x=1, player_y=1)
        _send_key(view, pygame.K_UP)  # Into border wall
        assert ps.y == 1, "Should not move"
        assert view._message != "", "Should show failure message"
        view.on_exit()

    def test_move_increments_turn(self) -> None:
        view, _, ps = _make_view()
        assert ps.turn_number == 0
        _send_key(view, pygame.K_RIGHT)
        assert ps.turn_number == 1
        view.on_exit()

    def test_space_waits(self) -> None:
        view, _, ps = _make_view()
        _send_key(view, pygame.K_SPACE)
        assert ps.turn_number == 1
        view.on_exit()


# ============================================================================
# Interact
# ============================================================================


class TestInteract:
    """Tests for E-key interaction."""

    def test_e_opens_adjacent_door(self) -> None:
        view, gm, ps = _make_view(player_x=5, player_y=5)
        # Place door to the right of player
        gm.tiles[5][6] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        # Press right to set facing direction (will fail — door is not walkable)
        _send_key(view, pygame.K_RIGHT)
        assert ps.x == 5, "Should not walk into closed door"
        # Now press E to interact in facing direction (right)
        _send_key(view, pygame.K_e)
        assert gm.get_tile(6, 5).tile_type == TileType.DOOR_OPEN
        view.on_exit()

    def test_e_interact_nothing_shows_message(self) -> None:
        view, _, _ = _make_view()
        # Face right (default), floor tile to the right
        _send_key(view, pygame.K_RIGHT)
        _send_key(view, pygame.K_e)  # Floor tile — nothing to interact with
        assert view._message != ""
        view.on_exit()


# ============================================================================
# Camera
# ============================================================================


class TestCamera:
    """Tests for camera follow behavior."""

    def test_camera_target_updates_on_move(self) -> None:
        view, _, ps = _make_view()
        _send_key(view, pygame.K_RIGHT)
        expected_x = ps.x * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        assert view._target_camera_x == float(expected_x)
        view.on_exit()

    def test_camera_lerps_toward_target(self) -> None:
        view, _, _ = _make_view()
        # Move to create a gap between camera and target
        _send_key(view, pygame.K_RIGHT)
        old_camera_x = view._camera_x
        # Simulate a frame
        view.update(0.016)
        # Camera should have moved toward target
        assert view._camera_x > old_camera_x, "Camera should lerp toward target"
        view.on_exit()

    def test_camera_converges(self) -> None:
        view, _, _ = _make_view()
        _send_key(view, pygame.K_RIGHT)
        # Run many update frames
        for _ in range(120):
            view.update(0.016)
        # Camera should be very close to target
        assert abs(view._camera_x - view._target_camera_x) < 1.0
        view.on_exit()


# ============================================================================
# Fog of War
# ============================================================================


class TestFogOfWar:
    """Tests for fog state updates after movement."""

    def test_fog_updates_after_movement(self) -> None:
        view, gm, ps = _make_view()
        _send_key(view, pygame.K_RIGHT)
        # New position should be visible
        assert gm.get_tile(ps.x, ps.y).fog_state == FogState.VISIBLE
        view.on_exit()

    def test_previous_position_stays_explored(self) -> None:
        view, gm, ps = _make_view(player_x=3, player_y=3)
        # Move far enough that (3,3) leaves vision
        for _ in range(8):
            _send_key(view, pygame.K_RIGHT)
        # Original position should be explored (was visible, now out of range)
        assert gm.get_tile(3, 3).fog_state == FogState.EXPLORED
        view.on_exit()


# ============================================================================
# State Transitions
# ============================================================================


class TestStateTransition:
    """Tests for exiting ground exploration."""

    def test_escape_sets_galaxy_map(self) -> None:
        view, _, _ = _make_view()
        _send_key(view, pygame.K_ESCAPE)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_back_button_sets_galaxy_map(self) -> None:
        view, _, _ = _make_view()
        # Simulate button press event
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view._back_button,
        )
        view.handle_event(event)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()


# ============================================================================
# Rendering (smoke test)
# ============================================================================


class TestRendering:
    """Smoke tests that rendering doesn't crash."""

    def test_render_does_not_crash(self) -> None:
        view, _, _ = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_after_movement(self) -> None:
        view, _, _ = _make_view()
        screen = pygame.display.get_surface()
        _send_key(view, pygame.K_RIGHT)
        _send_key(view, pygame.K_DOWN)
        view.update(0.016)
        view.render(screen)
        view.on_exit()

    def test_render_with_message(self) -> None:
        view, _, _ = _make_view(player_x=1, player_y=1)
        screen = pygame.display.get_surface()
        _send_key(view, pygame.K_UP)  # Into wall — triggers message
        view.render(screen)
        view.on_exit()
