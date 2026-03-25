"""Tests for ground combat overlay panel in the exploration view (Phase C)."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for view tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.models.ground import (  # noqa: E402
    GroundMap,
    GroundPlayerState,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import (  # noqa: E402
    AlertLevel,
    Direction,
    GroundEnemy,
    GroundMissionState,
)
from spacegame.models.ground_combat import (  # noqa: E402
    CombatOutcome,
    GroundCombatState,
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


def _make_combat_view(
    player_x: int = 5,
    player_y: int = 5,
    enemies: list[GroundEnemy] | None = None,
) -> tuple[GroundExplorationView, GroundMissionState]:
    """Create a view with a mission state containing enemies."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    gm = GroundMap.create_test_map(20, 20)
    player = GroundPlayerState(x=player_x, y=player_y)
    mission = GroundMissionState(
        ground_map=gm,
        player=player,
        enemies=enemies or [],
    )
    view = GroundExplorationView(ui_manager, gm, player, mission)
    view.on_enter()
    return view, mission


class TestCombatTrigger:
    """Tests that combat triggers when alert reaches COMBAT."""

    def test_no_combat_state_initially(self) -> None:
        view, _ = _make_combat_view()
        assert view._combat_state is None
        view.on_exit()

    def test_combat_starts_on_alert_combat(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        # Manually raise alert to COMBAT to trigger
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()
        assert view._combat_state is not None, "Combat should have started"
        view.on_exit()

    def test_combat_state_has_enemies(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()
        assert len(view._combat_state.enemies) >= 1
        view.on_exit()


class TestCombatInputBlocking:
    """Tests that normal input is blocked during combat."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_movement_blocked_during_combat(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        start_x = mission.player.x
        _send_key(view, pygame.K_RIGHT)
        assert mission.player.x == start_x, "Movement blocked during combat"
        view.on_exit()

    def test_escape_blocked_during_combat(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        _send_key(view, pygame.K_ESCAPE)
        assert view.get_next_state() is None, "Escape blocked during combat"
        view.on_exit()

    def test_wait_blocked_during_combat(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        turn = mission.player.turn_number
        _send_key(view, pygame.K_SPACE)
        assert mission.player.turn_number == turn, "Wait blocked during combat"
        view.on_exit()


class TestCombatFightAction:
    """Tests for the fight action via keyboard."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_f_key_triggers_fight(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        assert view._combat_state is not None
        initial_round = view._combat_state.round_number
        _send_key(view, pygame.K_f)
        # Fight should have executed (round advances)
        assert view._combat_state.round_number > initial_round
        view.on_exit()

    def test_fight_damages_enemy(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        cs = view._combat_state
        initial_hp = cs.enemies[0].hp
        # Use execute_fight directly with known rolls to avoid RNG flakiness.
        # Player rolls 6, enemy rolls 1 — guarantees player wins the exchange.
        cs.execute_fight(player_roll=6, enemy_roll=1)
        final_hp = cs.enemies[0].hp
        assert final_hp < initial_hp, f"Enemy should take damage: {initial_hp} -> {final_hp}"
        view.on_exit()

    def test_tab_cycles_target(self) -> None:
        enemies = [
            GroundEnemy(id="a", x=6, y=5, facing=Direction.LEFT, vision_range=5),
            GroundEnemy(id="b", x=4, y=5, facing=Direction.RIGHT, vision_range=5),
        ]
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=enemies)
        self._start_combat(view, mission)
        assert view._combat_state.target_index == 0
        _send_key(view, pygame.K_TAB)
        assert view._combat_state.target_index == 1
        view.on_exit()


class TestCombatRetreatAction:
    """Tests for the retreat action."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_r_key_attempts_retreat(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        # Press R many times — eventually should succeed or combat should change
        for _ in range(20):
            if view._combat_state is None:
                break
            if view._combat_state.outcome != CombatOutcome.IN_PROGRESS:
                break
            _send_key(view, pygame.K_r)
        # Should have resolved (retreat success or player defeated from free attacks)
        assert view._combat_state is None or view._combat_state.outcome != CombatOutcome.IN_PROGRESS
        view.on_exit()


class TestCombatTalkAction:
    """Tests for the talk action."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_t_key_attempts_talk(self) -> None:
        # Use a weak enemy with low talk difficulty
        enemy = GroundEnemy(id="worker", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        # Set talk difficulty low for test
        view._combat_state.enemies[0].talk_difficulty = 2
        view._combat_state.enemies[0].is_automated = False
        # Attempt talk — may succeed immediately or fail
        _send_key(view, pygame.K_t)
        # Combat state should still exist (waiting for player to dismiss)
        cs = view._combat_state
        assert cs is not None
        assert len(cs.used_social_skills) >= 1 or cs.outcome == CombatOutcome.TALKED
        view.on_exit()


class TestCombatOutcomes:
    """Tests for combat resolution and cleanup."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_victory_clears_combat_state(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        # Manually set enemy HP to 0 to trigger victory
        view._combat_state.enemies[0].hp = 0
        view._combat_state._check_outcome()
        view._check_combat_over()
        # Combat state persists until player dismisses
        assert view._combat_state.outcome == CombatOutcome.VICTORY
        # Press Space to dismiss
        _send_key(view, pygame.K_SPACE)
        assert view._combat_state is None, "Space should clear combat state"
        view.on_exit()

    def test_victory_drops_alert(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        view._combat_state.enemies[0].hp = 0
        view._combat_state._check_outcome()
        view._check_combat_over()
        # Dismiss with Space
        _send_key(view, pygame.K_SPACE)
        assert mission.alert_level != AlertLevel.COMBAT
        view.on_exit()


class TestCombatPanelRendering:
    """Smoke tests for combat panel rendering."""

    def _start_combat(self, view: GroundExplorationView, mission: GroundMissionState) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_render_during_combat_no_crash(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_after_fight_no_crash(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        _send_key(view, pygame.K_f)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_on_exit_during_combat_no_leak(self) -> None:
        enemy = GroundEnemy(id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5)
        view, mission = _make_combat_view(player_x=5, player_y=5, enemies=[enemy])
        self._start_combat(view, mission)
        view.on_exit()  # Should not crash, should clean up combat state
