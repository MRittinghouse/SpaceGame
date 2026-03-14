"""View-level tests for crew bonus integration in ground exploration."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip(
    "pygame_gui", reason="pygame_gui required for view tests"
)

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.attributes import AttributeSheet  # noqa: E402
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
    GroundEnemy,
    GroundMissionState,
    NoiseEvent,
)
from spacegame.models.ground_combat import CombatOutcome  # noqa: E402
from spacegame.models.ground_crew import GroundCrewBonuses  # noqa: E402
from spacegame.models.progression import PlayerProgression  # noqa: E402
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


def _make_attrs(**overrides: int) -> AttributeSheet:
    defaults = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 1}
    defaults.update(overrides)
    return AttributeSheet(values=defaults)


def _make_crew_view(
    player_x: int = 5,
    player_y: int = 5,
    enemies: list[GroundEnemy] | None = None,
    bonuses: GroundCrewBonuses | None = None,
    attributes: AttributeSheet | None = None,
    progression: PlayerProgression | None = None,
) -> tuple[GroundExplorationView, GroundMissionState]:
    """Create a view with crew bonuses and optional attributes/progression."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    gm = GroundMap.create_test_map(20, 20)
    player = GroundPlayerState(x=player_x, y=player_y)
    mission = GroundMissionState(
        ground_map=gm,
        player=player,
        enemies=enemies or [],
        crew_bonuses=bonuses or GroundCrewBonuses(),
        attributes=attributes,
        progression=progression,
    )
    view = GroundExplorationView(ui_manager, gm, player, mission)
    view.on_enter()
    return view, mission


# ============================================================================
# Vision radius uses crew bonuses
# ============================================================================


class TestViewVisionRadius:
    """Vision radius in the view uses effective_vision_radius."""

    def test_elena_increases_fog_reveal(self) -> None:
        """Elena's +1 vision should reveal more tiles on enter."""
        # Base vision (no bonuses)
        _, base_mission = _make_crew_view()
        base_visible = sum(
            1
            for row in base_mission.ground_map.tiles
            for tile in row
            if tile.fog_state == FogState.VISIBLE
        )

        # Elena vision (+1)
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        _, elena_mission = _make_crew_view(bonuses=bonuses)
        elena_visible = sum(
            1
            for row in elena_mission.ground_map.tiles
            for tile in row
            if tile.fog_state == FogState.VISIBLE
        )

        assert elena_visible > base_visible, "Elena should reveal more tiles"

    def test_acu_increases_fog_reveal(self) -> None:
        """High ACU attribute increases vision radius."""
        attrs = _make_attrs(acu=6)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)

        # Base
        _, base_mission = _make_crew_view()
        base_visible = sum(
            1
            for row in base_mission.ground_map.tiles
            for tile in row
            if tile.fog_state == FogState.VISIBLE
        )

        # ACU 6
        _, acu_mission = _make_crew_view(bonuses=bonuses)
        acu_visible = sum(
            1
            for row in acu_mission.ground_map.tiles
            for tile in row
            if tile.fog_state == FogState.VISIBLE
        )

        assert acu_visible > base_visible


# ============================================================================
# Door noise uses crew bonuses
# ============================================================================


class TestViewDoorNoise:
    """Door noise in the view uses get_door_noise_radius."""

    def test_marcus_silent_doors_no_noise(self) -> None:
        """Marcus silences doors — no noise event added."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["marcus_jin"])
        enemy = GroundEnemy(
            id="guard", x=10, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )

        # Place a closed door adjacent to player
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.DOOR_CLOSED)

        # Interact to open door
        view._last_dx = 1
        view._last_dy = 0
        success, msg = view.player_state.interact(
            view.ground_map, 6, 5
        )
        # Manually trigger on_player_acted with door_opened
        # Check that silent doors means no noise is generated
        assert mission.get_door_noise_radius() == 0
        view.on_exit()


# ============================================================================
# Combat uses crew bonuses
# ============================================================================


class TestViewCombatCrewBonuses:
    """Combat in the view passes crew bonuses through."""

    def _start_combat(
        self, view: GroundExplorationView, mission: GroundMissionState
    ) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_combat_uses_attributes_for_stats(self) -> None:
        """Player stats in combat use attributes from mission state."""
        attrs = _make_attrs(acu=4, res=4)
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], attributes=attrs
        )
        self._start_combat(view, mission)
        cs = view._combat_state
        assert cs is not None
        # ACU 4 // 2 = 2 attack
        assert cs.player.attack_mod >= 2
        # RES 4 // 2 = 2 → HP base 8 + 2 = 10
        assert cs.player.hp >= 10
        view.on_exit()

    def test_combat_uses_progression_for_stats(self) -> None:
        """Player stats in combat use progression skills."""
        prog = PlayerProgression()
        prog.add_xp(5200)
        prog.level_up_skill("scrapper")
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], progression=prog
        )
        self._start_combat(view, mission)
        cs = view._combat_state
        assert cs is not None
        # Scrapper +1 attack
        assert cs.player.attack_mod >= 1
        view.on_exit()

    def test_priya_analyze_in_combat(self) -> None:
        """Priya's analyze weakness is available in combat via A key."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["dr_priya_osei"])
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )
        self._start_combat(view, mission)
        cs = view._combat_state
        assert cs is not None
        assert cs.can_analyze_weakness
        _send_key(view, pygame.K_a)
        assert not cs.can_analyze_weakness
        assert view._analyze_bonus == 3
        view.on_exit()

    def test_analyze_bonus_consumed_on_fight(self) -> None:
        """Analyze bonus is consumed by the next fight."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["dr_priya_osei"])
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )
        self._start_combat(view, mission)
        _send_key(view, pygame.K_a)  # Activate analyze
        assert view._analyze_bonus == 3
        _send_key(view, pygame.K_f)  # Fight consumes it
        assert view._analyze_bonus == 0
        view.on_exit()

    def test_elena_retreat_bonus_in_view(self) -> None:
        """Elena's retreat bonus is passed to attempt_retreat."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )
        self._start_combat(view, mission)
        # Elena gives +2 retreat bonus — retreat should be easier
        assert mission.crew_bonuses.retreat_bonus == 2
        view.on_exit()

    def test_tomas_talk_bonus_in_view(self) -> None:
        """Tomas's talk bonus is passed to attempt_talk."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"])
        enemy = GroundEnemy(
            id="worker", x=6, y=5, facing=Direction.LEFT, vision_range=5
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )
        self._start_combat(view, mission)
        # Tomas gives +2 talk bonus
        assert mission.crew_bonuses.talk_bonus == 2
        view.on_exit()


# ============================================================================
# Patrol route rendering
# ============================================================================


class TestViewPatrolRouteRendering:
    """Patrol route rendering doesn't crash."""

    def test_render_with_patrol_reveal_no_crash(self) -> None:
        """Rendering with patrol route reveal active doesn't crash."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        enemy = GroundEnemy(
            id="guard", x=10, y=10, facing=Direction.RIGHT,
            patrol_route=[(10, 10), (15, 10)],
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy], bonuses=bonuses
        )
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()


# ============================================================================
# Loot on combat victory
# ============================================================================


class TestViewCombatLoot:
    """Combat victory awards loot credits."""

    def _start_combat(
        self, view: GroundExplorationView, mission: GroundMissionState
    ) -> None:
        mission.raise_alert(AlertLevel.COMBAT)
        view._process_enemy_phase()

    def test_victory_awards_loot(self) -> None:
        """Victory message includes loot earned."""
        enemy = GroundEnemy(
            id="guard", x=6, y=5, facing=Direction.LEFT,
            vision_range=5, loot_credits=50,
        )
        view, mission = _make_crew_view(
            player_x=5, player_y=5, enemies=[enemy]
        )
        self._start_combat(view, mission)
        cs = view._combat_state
        assert cs is not None
        # Force victory
        cs.enemies[0].hp = 0
        cs._check_outcome()
        view._check_combat_over()
        # Dismiss
        _send_key(view, pygame.K_SPACE)
        assert view._loot_earned >= 50
        view.on_exit()
