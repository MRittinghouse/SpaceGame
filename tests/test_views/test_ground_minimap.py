"""Tests for ground exploration minimap rendering.

Tests minimap surface creation, tile color mapping, fog respect,
player/enemy dot positioning, and interactable markers.
"""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for view tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GROUND_TILE_SIZE  # noqa: E402
from spacegame.models.ground import (  # noqa: E402
    FogState,
    GroundInteractable,
    GroundMap,
    GroundPlayerState,
    GroundStoryTrigger,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import (  # noqa: E402
    Direction,
    GroundEnemy,
    GroundMissionState,
)
from spacegame.views.ground_exploration_view import (  # noqa: E402
    GroundExplorationView,
    MINIMAP_SIZE,
    MINIMAP_MARGIN,
)


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for minimap tests."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_view(
    width: int = 15,
    height: int = 15,
    player_x: int = 5,
    player_y: int = 5,
    mission_state: GroundMissionState = None,
) -> GroundExplorationView:
    """Create a view with optional mission state."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    ground_map = GroundMap.create_test_map(width, height)
    player_state = GroundPlayerState(x=player_x, y=player_y)
    view = GroundExplorationView(
        ui_manager,
        ground_map,
        player_state,
        mission_state=mission_state,
    )
    view.on_enter()
    return view


def _make_mission_state(
    width: int = 15,
    height: int = 15,
    enemies: list = None,
    interactables: list = None,
    story_triggers: list = None,
) -> GroundMissionState:
    """Create a mission state with optional entities."""
    ground_map = GroundMap.create_test_map(width, height)
    return GroundMissionState(
        ground_map=ground_map,
        player=GroundPlayerState(x=5, y=5),
        enemies=enemies or [],
        interactables=interactables or [],
        story_triggers=story_triggers or [],
    )


# === Minimap Constants ===


class TestMinimapConstants:
    """Minimap sizing and positioning constants exist."""

    def test_minimap_size_defined(self):
        """MINIMAP_SIZE constant exists and is reasonable."""
        assert MINIMAP_SIZE > 0
        assert MINIMAP_SIZE <= 200

    def test_minimap_margin_defined(self):
        """MINIMAP_MARGIN constant exists."""
        assert MINIMAP_MARGIN >= 0


# === Minimap Surface ===


class TestMinimapSurface:
    """Minimap surface creation and lifecycle."""

    def test_minimap_surface_created(self):
        """View creates a minimap surface on init."""
        view = _make_view()
        assert view._minimap_surface is not None
        view.on_exit()

    def test_minimap_surface_size(self):
        """Minimap surface matches MINIMAP_SIZE constant."""
        view = _make_view()
        w, h = view._minimap_surface.get_size()
        assert w == MINIMAP_SIZE
        assert h == MINIMAP_SIZE
        view.on_exit()

    def test_minimap_renders_without_error(self):
        """Calling render() with minimap doesn't crash."""
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()


# === Minimap Pixel Scaling ===


class TestMinimapScaling:
    """Minimap scales tile positions to fit within the surface."""

    def test_pixels_per_tile_uses_larger_dimension(self):
        """Scale factor is based on max(width, height)."""
        view = _make_view(width=20, height=10)
        # 20 is the larger dimension
        expected = MINIMAP_SIZE / 20
        assert abs(view._minimap_scale - expected) < 0.01
        view.on_exit()

    def test_square_map_scale(self):
        """Square maps use width (or height, they're equal)."""
        view = _make_view(width=15, height=15)
        expected = MINIMAP_SIZE / 15
        assert abs(view._minimap_scale - expected) < 0.01
        view.on_exit()


# === Fog of War Respect ===


class TestMinimapFog:
    """Minimap respects fog of war state."""

    def test_unexplored_tiles_are_dark(self):
        """Unexplored tiles render as the background (dark) on minimap."""
        # Use a large map so far corner is definitely unexplored
        view = _make_view(width=30, height=30, player_x=2, player_y=2)
        view._update_minimap()
        # Sample the far corner — well outside vision radius from (2,2)
        scale = view._minimap_scale
        px = int(28 * scale + scale / 2)
        py = int(28 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Should be the dark bg color, not tile color
        assert pixel[0] <= 15 and pixel[1] <= 15 and pixel[2] <= 20
        view.on_exit()

    def test_visible_tiles_have_color(self):
        """Visible tiles render with their tile color on minimap."""
        view = _make_view(player_x=5, player_y=5)
        # Update fog to make tiles around player visible
        view.ground_map.update_fog_of_war(5, 5, 4)
        view._update_minimap()
        # Sample a visible floor tile near player
        scale = view._minimap_scale
        px = int(5 * scale + scale / 2)
        py = int(5 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Should NOT be black — visible floor has color
        assert pixel[0] > 30 or pixel[1] > 30 or pixel[2] > 30
        view.on_exit()


# === Player Dot ===


class TestMinimapPlayerDot:
    """Player position shown on minimap."""

    def test_player_dot_rendered(self):
        """Player position has a bright pixel on the minimap."""
        view = _make_view(player_x=7, player_y=7)
        view.ground_map.update_fog_of_war(7, 7, 4)
        view._update_minimap()
        scale = view._minimap_scale
        px = int(7 * scale + scale / 2)
        py = int(7 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Player dot should be bright (yellow-ish)
        assert pixel[0] > 200  # R channel high
        assert pixel[1] > 150  # G channel moderate-high
        view.on_exit()


# === Enemy Dots ===


class TestMinimapEnemyDots:
    """Enemy positions shown on minimap when visible."""

    def test_visible_enemy_shown(self):
        """Visible enemy appears as a dot on minimap."""
        enemy = GroundEnemy(
            id="test_e",
            x=7,
            y=7,
            facing=Direction.RIGHT,
            patrol_route=[(7, 7), (7, 7)],
        )
        state = _make_mission_state(enemies=[enemy])
        # Make enemy tile visible
        state.ground_map.update_fog_of_war(7, 7, 4)
        view = _make_view(player_x=5, player_y=5, mission_state=state)
        view.ground_map = state.ground_map  # Use same map for fog
        view.ground_map.update_fog_of_war(5, 5, 6)
        view._update_minimap()
        scale = view._minimap_scale
        px = int(7 * scale + scale / 2)
        py = int(7 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Enemy dot should be red-ish
        assert pixel[0] > 150  # R high
        view.on_exit()

    def test_non_visible_enemy_hidden(self):
        """Enemy on unexplored tile is NOT shown on minimap."""
        enemy = GroundEnemy(
            id="test_e",
            x=12,
            y=12,
            facing=Direction.RIGHT,
            patrol_route=[(12, 12), (12, 12)],
        )
        state = _make_mission_state(enemies=[enemy])
        view = _make_view(player_x=2, player_y=2, mission_state=state)
        # Don't update fog near enemy — stays unexplored
        view._update_minimap()
        scale = view._minimap_scale
        px = int(12 * scale + scale / 2)
        py = int(12 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Should be dark (unexplored), NOT red
        assert pixel[0] < 50
        view.on_exit()


# === Interactable Markers ===


class TestMinimapInteractables:
    """Un-looted interactables shown on minimap when visible."""

    def test_visible_interactable_shown(self):
        """Visible un-looted interactable appears on minimap."""
        obj = GroundInteractable(x=6, y=6, interact_type="loot_container", loot_credits=50)
        state = _make_mission_state(interactables=[obj])
        state.ground_map.update_fog_of_war(6, 6, 4)
        view = _make_view(player_x=5, player_y=5, mission_state=state)
        view.ground_map = state.ground_map
        view.ground_map.update_fog_of_war(5, 5, 6)
        view._update_minimap()
        scale = view._minimap_scale
        px = int(6 * scale + scale / 2)
        py = int(6 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Interactable should have a distinct color (not just floor gray)
        # Typically cyan/teal or bright marker
        brightness = pixel[0] + pixel[1] + pixel[2]
        assert brightness > 150  # Should be visible, not dark
        view.on_exit()

    def test_looted_interactable_not_marked(self):
        """Looted interactable doesn't get special marker."""
        obj = GroundInteractable(x=6, y=6, interact_type="loot_container", loot_credits=50)
        obj.loot()  # Already looted
        state = _make_mission_state(interactables=[obj])
        state.ground_map.update_fog_of_war(6, 6, 4)
        view = _make_view(player_x=5, player_y=5, mission_state=state)
        view.ground_map = state.ground_map
        view.ground_map.update_fog_of_war(5, 5, 6)
        view._update_minimap()
        scale = view._minimap_scale
        px = int(6 * scale + scale / 2)
        py = int(6 * scale + scale / 2)
        pixel = view._minimap_surface.get_at((px, py))
        # Should be normal floor color, not bright marker
        # Floor color is (60, 65, 75) — should be in that range
        assert pixel[0] < 120
        view.on_exit()


# === Minimap Position ===


class TestMinimapPosition:
    """Minimap renders in the top-right corner."""

    def test_minimap_position(self):
        """Minimap is placed at top-right with margin."""
        view = _make_view()
        expected_x = WINDOW_WIDTH - MINIMAP_SIZE - MINIMAP_MARGIN
        expected_y = MINIMAP_MARGIN
        assert view._minimap_x == expected_x
        assert view._minimap_y == expected_y
        view.on_exit()
