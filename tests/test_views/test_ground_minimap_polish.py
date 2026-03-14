"""Tests for ground minimap polish improvements.

Tests exit tile highlighting, back button placement (not overlapping minimap),
and story trigger message duration.
"""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip(
    "pygame_gui", reason="pygame_gui required for view tests"
)

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.ground import (  # noqa: E402
    FogState,
    GroundMap,
    GroundPlayerState,
    GroundStoryTrigger,
    TileType,
)
from spacegame.models.ground_enemy import (  # noqa: E402
    GroundMissionState,
)
from spacegame.views.ground_exploration_view import (  # noqa: E402
    GroundExplorationView,
    MINIMAP_SIZE,
    MINIMAP_MARGIN,
)


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for polish tests."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_view(
    width: int = 15, height: int = 15, player_x: int = 5, player_y: int = 5,
    mission_state: GroundMissionState = None,
) -> GroundExplorationView:
    """Create a view with optional mission state."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    ground_map = GroundMap.create_test_map(width, height)
    player_state = GroundPlayerState(x=player_x, y=player_y)
    view = GroundExplorationView(
        ui_manager, ground_map, player_state, mission_state=mission_state,
    )
    view.on_enter()
    return view


# === Exit Tile Minimap Highlight ===


class TestMinimapExitHighlight:
    """Exit tile should be highlighted on minimap when visible."""

    def test_visible_exit_has_bright_color(self):
        """Exit tile on minimap should be green-ish when visible."""
        view = _make_view(player_x=5, player_y=5)
        # Set exit position and make it visible
        view.ground_map.exit_pos = (6, 5)
        tile = view.ground_map.get_tile(6, 5)
        if tile:
            tile.tile_type = TileType.EXIT
        view.ground_map.update_fog_of_war(5, 5, 6)
        view._update_minimap()
        scale = view._minimap_scale
        px = int(6 * scale + scale / 2)
        py = int(5 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Exit should be bright green
        assert pixel[1] > 100, f"Exit green channel should be bright, got {pixel}"
        view.on_exit()


# === Back Button Placement ===


class TestBackButtonPlacement:
    """Back button should not overlap with minimap."""

    def test_back_button_not_overlapping_minimap(self):
        """Exit button should be placed below or left of minimap area."""
        view = _make_view()
        minimap_right = WINDOW_WIDTH - MINIMAP_MARGIN
        minimap_bottom = MINIMAP_MARGIN + MINIMAP_SIZE
        btn = view._back_button
        assert btn is not None
        btn_rect = btn.relative_rect
        # Button should NOT be in the minimap zone (top-right)
        # Either it's below minimap bottom, or left of minimap left edge
        minimap_left = WINDOW_WIDTH - MINIMAP_SIZE - MINIMAP_MARGIN
        overlaps_minimap = (
            btn_rect.right > minimap_left
            and btn_rect.left < minimap_right
            and btn_rect.top < minimap_bottom
            and btn_rect.bottom > MINIMAP_MARGIN
        )
        assert not overlaps_minimap, (
            f"Button rect {btn_rect} overlaps minimap area "
            f"({minimap_left}, {MINIMAP_MARGIN}, {minimap_right}, {minimap_bottom})"
        )
        view.on_exit()


# === Story Trigger Message Duration ===


class TestStoryTriggerDuration:
    """Story triggers should show messages long enough to read."""

    def test_story_message_duration(self):
        """Story trigger messages should display longer than normal messages."""
        state = GroundMissionState(
            ground_map=GroundMap.create_test_map(15, 15),
            player=GroundPlayerState(x=5, y=5),
            enemies=[],
            story_triggers=[
                GroundStoryTrigger(
                    x=5, y=5,
                    trigger_type="atmosphere",
                    text="The corridor opens into a vast cargo hold.",
                ),
            ],
        )
        view = _make_view(player_x=5, player_y=5, mission_state=state)
        view.ground_map = state.ground_map
        # Fire the trigger
        view._check_story_triggers()
        # Message timer should be longer than standard 2.0s
        assert view._message_timer >= 4.0, (
            f"Story trigger should show for at least 4s, got {view._message_timer}"
        )
        view.on_exit()

    def test_normal_message_duration(self):
        """Normal messages (non-story) should use standard duration."""
        view = _make_view()
        view._show_message("A door opened.")
        assert view._message_timer == 2.0
        view.on_exit()
