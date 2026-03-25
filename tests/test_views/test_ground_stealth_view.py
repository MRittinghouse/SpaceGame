"""Tests for ground exploration view stealth integration (Phase B)."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for view tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.models.ground import (  # noqa: E402
    FogState,
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import (  # noqa: E402
    AlertLevel,
    Direction,
    EnemyAIState,
    GroundEnemy,
    GroundMissionState,
)
from spacegame.views.ground_exploration_view import GroundExplorationView  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all tests."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _send_key(view: GroundExplorationView, key: int) -> None:
    """Simulate a KEYDOWN event."""
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)
    view.handle_event(event)


def _make_stealth_view(
    player_x: int = 2,
    player_y: int = 2,
    enemies: list[GroundEnemy] | None = None,
) -> tuple[GroundExplorationView, GroundMissionState]:
    """Create a view with a mission state containing enemies."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    gm = GroundMap.create_test_map(15, 15)
    player = GroundPlayerState(x=player_x, y=player_y)
    mission = GroundMissionState(
        ground_map=gm,
        player=player,
        enemies=enemies or [],
    )
    view = GroundExplorationView(ui_manager, gm, player, mission)
    view.on_enter()
    return view, mission


class TestEnemyRendering:
    """Tests that enemies render without crashing."""

    def test_render_with_enemies(self) -> None:
        enemy = GroundEnemy(id="guard", x=5, y=5, facing=Direction.RIGHT, vision_range=3)
        view, _ = _make_stealth_view(enemies=[enemy])
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_enemy_only_on_visible_tile(self) -> None:
        # Enemy far from player should not crash even if fog is unexplored
        enemy = GroundEnemy(id="guard", x=12, y=12, facing=Direction.LEFT, vision_range=3)
        view, _ = _make_stealth_view(player_x=2, player_y=2, enemies=[enemy])
        screen = pygame.display.get_surface()
        view.render(screen)  # Should not crash, enemy tile is unexplored
        view.on_exit()


class TestEnemyTurnProcessing:
    """Tests that enemy turns are processed after player actions."""

    def test_enemy_moves_after_player_move(self) -> None:
        route = [(10, 5), (11, 5), (12, 5), (11, 5)]
        enemy = GroundEnemy(
            id="guard",
            x=10,
            y=5,
            facing=Direction.RIGHT,
            vision_range=3,
            patrol_route=route,
        )
        view, mission = _make_stealth_view(player_x=2, player_y=2, enemies=[enemy])
        _send_key(view, pygame.K_RIGHT)  # Player moves
        # Enemy should have advanced along patrol
        assert (enemy.x, enemy.y) == (11, 5), "Enemy should patrol after player moves"
        view.on_exit()

    def test_enemy_moves_after_wait(self) -> None:
        route = [(10, 5), (11, 5)]
        enemy = GroundEnemy(
            id="guard",
            x=10,
            y=5,
            facing=Direction.RIGHT,
            vision_range=3,
            patrol_route=route,
        )
        view, mission = _make_stealth_view(player_x=2, player_y=2, enemies=[enemy])
        _send_key(view, pygame.K_SPACE)  # Wait
        assert (enemy.x, enemy.y) == (11, 5), "Enemy should patrol after wait"
        view.on_exit()


class TestDetectionIntegration:
    """Tests that vision detection works through the view."""

    def test_enemy_detects_player_raises_alert(self) -> None:
        # Enemy facing left, player in direct LOS
        enemy = GroundEnemy(id="guard", x=6, y=2, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_stealth_view(player_x=2, player_y=2, enemies=[enemy])
        # Player moves — triggers enemy turn which checks vision
        _send_key(view, pygame.K_RIGHT)
        assert mission.alert_level == AlertLevel.ALERT
        view.on_exit()

    def test_enemy_does_not_detect_player_behind(self) -> None:
        # Enemy facing right, player is to the left (behind)
        enemy = GroundEnemy(id="guard", x=5, y=2, facing=Direction.RIGHT, vision_range=5)
        view, mission = _make_stealth_view(player_x=2, player_y=2, enemies=[enemy])
        _send_key(view, pygame.K_RIGHT)
        assert mission.alert_level == AlertLevel.UNDETECTED
        view.on_exit()


class TestNoiseIntegration:
    """Tests that noise from tiles triggers detection."""

    def test_noisy_floor_triggers_suspicion(self) -> None:
        view, mission = _make_stealth_view(player_x=3, player_y=5)
        # Place noisy floor at (4,5) and enemy within noise radius but
        # facing away so they don't visually detect the player
        mission.ground_map.tiles[5][4] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        enemy = GroundEnemy(id="guard", x=6, y=6, facing=Direction.DOWN, vision_range=3)
        mission.enemies.append(enemy)

        _send_key(view, pygame.K_RIGHT)  # Move onto noisy floor at (4,5)
        # Noise radius 3, enemy at Manhattan distance 3 from (4,5) — in range
        assert mission.alert_level in (AlertLevel.SUSPICIOUS, AlertLevel.ALERT)
        view.on_exit()

    def test_door_open_generates_noise(self) -> None:
        view, mission = _make_stealth_view(player_x=5, player_y=5)
        # Place closed door to the right and a nearby enemy
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        enemy = GroundEnemy(id="guard", x=7, y=5, facing=Direction.LEFT, vision_range=2)
        mission.enemies.append(enemy)

        # Face right then interact
        _send_key(view, pygame.K_RIGHT)  # Fails (door), but sets direction
        _send_key(view, pygame.K_e)  # Open door

        # Enemy is 2 tiles away, door noise radius is 2
        assert mission.alert_level in (AlertLevel.SUSPICIOUS, AlertLevel.ALERT)
        view.on_exit()


class TestAlertHUD:
    """Tests that alert level appears in HUD."""

    def test_render_with_alert_level(self) -> None:
        enemy = GroundEnemy(id="guard", x=5, y=5, facing=Direction.RIGHT, vision_range=3)
        view, mission = _make_stealth_view(enemies=[enemy])
        mission.raise_alert(AlertLevel.SUSPICIOUS, investigate_pos=(5, 5))
        screen = pygame.display.get_surface()
        view.render(screen)  # Should not crash, should show alert HUD
        view.on_exit()
