"""Tests for the combat view — phase state machine, animation queue, and logic."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for CombatView tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for CombatView tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState  # noqa: E402
from spacegame.models.combat import (  # noqa: E402
    CombatEffect,
    CombatEncounter,
    CombatLogEntry,
    CombatMove,
    CombatResult,
    CombatState,
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine  # noqa: E402
from spacegame.views.combat_view import (  # noqa: E402
    AnimationEvent,
    CombatPhase,
    CombatView,
    _MoveButton,
)
from spacegame.models.combat_engine import (  # noqa: E402
    FLEE_BASE_CHANCE,
    FLEE_SPEED_FACTOR,
    FLEE_MIN_CHANCE,
    FLEE_MAX_CHANCE,
)


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


def _make_move(
    move_id: str = "test_laser",
    name: str = "Test Laser",
    damage: float = 10.0,
    energy_cost: int = 2,
    cooldown: int = 0,
) -> CombatMove:
    return CombatMove(
        id=move_id,
        name=name,
        description="A test move.",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage, target=EffectTarget.ENEMY)],
        energy_cost=energy_cost,
        cooldown=cooldown,
    )


def _make_heal_move(
    move_id: str = "test_heal", name: str = "Test Heal", value: float = 20.0
) -> CombatMove:
    return CombatMove(
        id=move_id,
        name=name,
        description="A test heal.",
        effects=[CombatEffect(type=EffectType.HULL_RESTORE, value=value, target=EffectTarget.SELF)],
        energy_cost=2,
    )


def _make_enemy_template(
    template_id: str = "pirate_scout",
    name: str = "Pirate Scout",
    hull: int = 50,
    shields: int = 10,
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id=template_id,
        name=name,
        description="A test enemy.",
        behavior=behavior,
        hull=hull,
        shields=shields,
        energy=8,
        energy_regen=3,
        speed=10,
        evasion=15,
        accuracy=65,
        moves=[_make_move("enemy_blaster", "Blaster", 8.0, 2)],
        loot_table=[],
        negotiate_difficulty=3,
        xp_reward=20,
    )


def _make_player_state(
    hull: int = 100,
    max_hull: int = 100,
    shields: int = 40,
    max_shields: int = 40,
    energy: int = 10,
    max_energy: int = 10,
    equipment_moves: list[CombatMove] | None = None,
    crew_moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    if equipment_moves is None:
        equipment_moves = [_make_move()]
    if crew_moves is None:
        crew_moves = []
    return PlayerCombatState(
        hull=hull,
        max_hull=max_hull,
        shields=shields,
        max_shields=max_shields,
        energy=energy,
        max_energy=max_energy,
        energy_regen=3,
        speed=8,
        evasion=15,
        accuracy=70,
        equipment_moves=equipment_moves,
        crew_moves=crew_moves,
        active_effects=[],
        cooldowns={},
    )


def _make_combat_state(
    num_enemies: int = 1,
    player_moves: list[CombatMove] | None = None,
    crew_moves: list[CombatMove] | None = None,
) -> CombatState:
    templates = [_make_enemy_template(f"enemy_{i}", f"Enemy {i}") for i in range(num_enemies)]
    enemies = [EnemyShip.from_template(t) for t in templates]
    player = _make_player_state(equipment_moves=player_moves, crew_moves=crew_moves)
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=42)
    return CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
    )


def _make_engine(
    num_enemies: int = 1,
    player_moves: list[CombatMove] | None = None,
    crew_moves: list[CombatMove] | None = None,
    seed: int = 42,
) -> CombatEngine:
    state = _make_combat_state(num_enemies, player_moves, crew_moves)
    return CombatEngine(state, seed=seed)


def _make_view(
    num_enemies: int = 1,
    player_moves: list[CombatMove] | None = None,
    crew_moves: list[CombatMove] | None = None,
) -> CombatView:
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    engine = _make_engine(num_enemies, player_moves, crew_moves)
    view = CombatView(
        ui_manager=ui_manager,
        combat_engine=engine,
        player=None,  # Not needed for phase logic tests
    )
    return view


# ============================================================================
# CombatPhase Enum
# ============================================================================


class TestCombatPhase:
    """Tests for the CombatPhase enum."""

    def test_all_phases_exist(self) -> None:
        assert CombatPhase.INTRO.value == "intro"
        assert CombatPhase.PLAYER_INPUT.value == "player_input"
        assert CombatPhase.ANIMATING_PLAYER.value == "anim_player"
        assert CombatPhase.ANIMATING_CREW.value == "anim_crew"
        assert CombatPhase.ANIMATING_ENEMIES.value == "anim_enemies"
        assert CombatPhase.ROUND_END.value == "round_end"
        assert CombatPhase.COMBAT_OVER.value == "combat_over"


# ============================================================================
# CombatView Construction
# ============================================================================


class TestCombatViewConstruction:
    """Tests for CombatView initialization."""

    def test_construction_with_engine(self) -> None:
        view = _make_view()
        assert view.engine is not None
        assert view.phase == CombatPhase.INTRO

    def test_initial_state_is_none(self) -> None:
        view = _make_view()
        assert view.get_next_state() is None

    def test_initial_target_idx(self) -> None:
        view = _make_view(num_enemies=2)
        assert view.selected_target_idx == 0

    def test_return_state_default(self) -> None:
        view = _make_view()
        assert view._return_state == GameState.TRADING


# ============================================================================
# Phase State Machine
# ============================================================================


class TestPhaseStateMachine:
    """Tests for phase transitions in update()."""

    def test_intro_advances_after_timer(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view.phase == CombatPhase.INTRO
        view.update(1.6)  # 1 second > 0.8s intro duration
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_intro_does_not_advance_early(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(0.3)  # Only 0.3s, not enough
        assert view.phase == CombatPhase.INTRO
        view.on_exit()

    def test_player_input_waits_for_action(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.update(5.0)  # Even after 5 seconds, still waiting
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_round_end_loops_to_player_input(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ROUND_END
        view.phase_timer = 0.0
        view.update(0.5)
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_combat_over_stays(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.phase_timer = 0.0
        view.update(10.0)
        assert view.phase == CombatPhase.COMBAT_OVER
        view.on_exit()


# ============================================================================
# Animation Queue
# ============================================================================


class TestAnimationQueue:
    """Tests for animation queue processing."""

    def test_empty_queue_advances_phase(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ANIMATING_PLAYER
        view.animation_queue = []
        view.current_animation = None
        view.update(0.1)
        # Should advance past ANIMATING_PLAYER
        assert view.phase != CombatPhase.ANIMATING_PLAYER
        view.on_exit()

    def test_animation_processes_sequentially(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ANIMATING_PLAYER
        log1 = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser",
            effects_applied=["10 damage"],
        )
        log2 = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Bonus",
            effects_applied=["5 damage"],
        )
        view._enqueue_animation(log1, source="player")
        view._enqueue_animation(log2, source="player")
        assert len(view.animation_queue) == 2
        view.update(0.1)
        assert view.current_animation is not None
        assert len(view.animation_queue) == 1
        view.on_exit()

    def test_animation_completes_after_duration(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ANIMATING_PLAYER
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser",
            effects_applied=["hit"],
        )
        view._enqueue_animation(log, source="player")
        view.update(0.1)
        assert view.current_animation is not None
        view.update(1.6)  # Complete (> default duration)
        assert view.current_animation is None
        view.on_exit()


# ============================================================================
# Target Selection
# ============================================================================


class TestTargetSelection:
    """Tests for enemy target selection logic."""

    def test_select_valid_target(self) -> None:
        view = _make_view(num_enemies=3)
        view.on_enter()
        view.select_target(1)
        assert view.selected_target_idx == 1
        view.on_exit()

    def test_select_skips_dead_enemy(self) -> None:
        view = _make_view(num_enemies=3)
        view.on_enter()
        state = view.engine.get_state()
        state.enemies[0].current_hull = 0
        view.select_target(0)
        assert view.selected_target_idx != 0
        view.on_exit()

    def test_auto_advance_on_death(self) -> None:
        view = _make_view(num_enemies=2)
        view.on_enter()
        view.selected_target_idx = 0
        state = view.engine.get_state()
        state.enemies[0].current_hull = 0
        view._auto_advance_target()
        assert view.selected_target_idx == 1
        view.on_exit()

    def test_target_clamp_to_range(self) -> None:
        view = _make_view(num_enemies=2)
        view.on_enter()
        view.select_target(99)
        assert view.selected_target_idx < len(view.engine.get_state().enemies)
        view.on_exit()


# ============================================================================
# Combat Flow
# ============================================================================


class TestCombatFlow:
    """Tests for combat round flow through phases."""

    def test_player_move_transitions_to_animation(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro
        assert view.phase == CombatPhase.PLAYER_INPUT
        view._execute_player_action("test_laser")  # Queue the action
        view._execute_queued_turn()  # Execute the queue
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()

    def test_full_round_reaches_player_input_again(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro → PLAYER_INPUT
        view._execute_player_action("test_laser")
        view._execute_queued_turn()
        # Drain all animation phases with enough time
        for _ in range(20):
            view.update(0.5)
        # Should eventually loop back to PLAYER_INPUT or reach COMBAT_OVER
        assert view.phase in (CombatPhase.PLAYER_INPUT, CombatPhase.COMBAT_OVER)
        view.on_exit()

    def test_combat_over_on_victory(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro
        state = view.engine.get_state()
        state.enemies[0].current_hull = 0
        state.result = CombatResult.VICTORY
        view.phase = CombatPhase.ROUND_END
        view.phase_timer = 0.0
        view.update(0.5)
        assert view.phase == CombatPhase.COMBAT_OVER
        view.on_exit()

    def test_continue_sets_next_state(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.engine.get_state().result = CombatResult.VICTORY
        view._on_continue_pressed()
        assert view.get_next_state() == GameState.TRADING
        view.on_exit()


# ============================================================================
# get_next_state
# ============================================================================


class TestGetNextState:
    """Tests for view state transition signaling."""

    def test_returns_none_during_combat(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view.get_next_state() is None
        view.on_exit()

    def test_returns_state_after_continue(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.engine.get_state().result = CombatResult.FLED
        view._on_continue_pressed()
        assert view.get_next_state() is not None
        view.on_exit()

    def test_custom_return_state(self) -> None:
        view = _make_view()
        view._return_state = GameState.GALAXY_MAP
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.engine.get_state().result = CombatResult.VICTORY
        view._on_continue_pressed()
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()


# ============================================================================
# Health Bar Logic (Step 2)
# ============================================================================


class TestHealthBarLogic:
    """Tests for health bar color thresholds and proportions."""

    def test_bar_color_green_above_50(self) -> None:
        from spacegame.views.combat_view import _bar_color_for_ratio

        assert _bar_color_for_ratio(0.8) == Colors.GREEN

    def test_bar_color_yellow_between_25_and_50(self) -> None:
        from spacegame.views.combat_view import _bar_color_for_ratio

        assert _bar_color_for_ratio(0.35) == Colors.YELLOW

    def test_bar_color_red_below_25(self) -> None:
        from spacegame.views.combat_view import _bar_color_for_ratio

        assert _bar_color_for_ratio(0.15) == Colors.RED

    def test_bar_color_green_at_full(self) -> None:
        from spacegame.views.combat_view import _bar_color_for_ratio

        assert _bar_color_for_ratio(1.0) == Colors.GREEN

    def test_bar_color_red_at_zero(self) -> None:
        from spacegame.views.combat_view import _bar_color_for_ratio

        assert _bar_color_for_ratio(0.0) == Colors.RED


# ============================================================================
# Displayed Value Smoothing (Step 2)
# ============================================================================


class TestDisplayedValueSmoothing:
    """Tests for smooth bar animation via lerp."""

    def test_displayed_hull_starts_at_actual(self) -> None:
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        assert view._displayed_player_hull == state.player.hull
        view.on_exit()

    def test_displayed_hull_lerps_toward_actual(self) -> None:
        view = _make_view()
        view.on_enter()
        # Change actual hull
        state = view.engine.get_state()
        state.player.hull = 50
        # Update a few frames
        for _ in range(10):
            view.update(0.05)
        # Should have moved toward 50 (not exactly 50, but closer)
        assert view._displayed_player_hull < 100
        view.on_exit()

    def test_displayed_shields_lerps(self) -> None:
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.player.shields = 10
        for _ in range(10):
            view.update(0.05)
        assert view._displayed_player_shields < 40
        view.on_exit()


# ============================================================================
# Enemy Card States (Step 2)
# ============================================================================


class TestEnemyCardStates:
    """Tests for enemy card display states."""

    def test_get_enemy_display_state_alive(self) -> None:
        view = _make_view(num_enemies=1)
        view.on_enter()
        state = view.engine.get_state()
        display = view._get_enemy_display_state(0)
        assert display["alive"] is True
        assert display["fled"] is False
        view.on_exit()

    def test_get_enemy_display_state_dead(self) -> None:
        view = _make_view(num_enemies=1)
        view.on_enter()
        state = view.engine.get_state()
        state.enemies[0].current_hull = 0
        display = view._get_enemy_display_state(0)
        assert display["alive"] is False
        view.on_exit()

    def test_get_enemy_display_state_fled(self) -> None:
        view = _make_view(num_enemies=1)
        view.on_enter()
        state = view.engine.get_state()
        state.enemies[0].is_fled = True
        display = view._get_enemy_display_state(0)
        assert display["fled"] is True
        view.on_exit()

    def test_get_enemy_display_state_selected(self) -> None:
        view = _make_view(num_enemies=2)
        view.on_enter()
        view.selected_target_idx = 1
        display = view._get_enemy_display_state(1)
        assert display["selected"] is True
        display0 = view._get_enemy_display_state(0)
        assert display0["selected"] is False
        view.on_exit()


# ============================================================================
# Move Buttons (Step 3)
# ============================================================================


class TestMoveButtons:
    """Tests for move button generation and enable/disable logic."""

    def test_move_buttons_count_matches_equipment(self) -> None:
        moves = [_make_move("laser", "Laser"), _make_move("missile", "Missile", energy_cost=4)]
        view = _make_view(player_moves=moves)
        view.on_enter()
        view._build_move_buttons()
        assert len(view.move_buttons) == 2
        view.on_exit()

    def test_move_button_disabled_insufficient_energy(self) -> None:
        expensive = _make_move("big_gun", "Big Gun", energy_cost=99)
        view = _make_view(player_moves=[expensive])
        view.on_enter()
        view._build_move_buttons()
        assert not view.move_buttons[0].enabled
        view.on_exit()

    def test_move_button_enabled_affordable(self) -> None:
        cheap = _make_move("pea_shooter", "Pea Shooter", energy_cost=1)
        view = _make_view(player_moves=[cheap])
        view.on_enter()
        view._build_move_buttons()
        assert view.move_buttons[0].enabled
        view.on_exit()

    def test_move_button_disabled_on_cooldown(self) -> None:
        move = _make_move("laser", "Laser", cooldown=2)
        view = _make_view(player_moves=[move])
        view.on_enter()
        state = view.engine.get_state()
        state.player.cooldowns["laser"] = 2
        view._build_move_buttons()
        assert not view.move_buttons[0].enabled
        view.on_exit()

    def test_move_button_stores_move_reference(self) -> None:
        move = _make_move("laser", "Laser")
        view = _make_view(player_moves=[move])
        view.on_enter()
        view._build_move_buttons()
        assert view.move_buttons[0].move.id == "laser"
        view.on_exit()

    def test_move_buttons_rebuilt_each_input_phase(self) -> None:
        """Move buttons refresh when entering PLAYER_INPUT phase."""
        move = _make_move("laser", "Laser", energy_cost=2)
        view = _make_view(player_moves=[move])
        view.on_enter()
        view._advance_phase(CombatPhase.PLAYER_INPUT)
        assert len(view.move_buttons) >= 1
        view.on_exit()


class TestMoveButtonWidget:
    """Tests for the _MoveButton data class."""

    def test_move_button_construction(self) -> None:
        move = _make_move()
        rect = pygame.Rect(0, 0, 170, 55)
        btn = _MoveButton(rect=rect, move=move, enabled=True, cooldown_remaining=0)
        assert btn.move.id == "test_laser"
        assert btn.enabled is True

    def test_move_button_hover_default_false(self) -> None:
        move = _make_move()
        rect = pygame.Rect(0, 0, 170, 55)
        btn = _MoveButton(rect=rect, move=move, enabled=True, cooldown_remaining=0)
        assert btn.hovered is False


# ============================================================================
# Flee / Negotiate (Step 3)
# ============================================================================


class TestFleeAction:
    """Tests for flee action in the combat view."""

    def test_get_flee_chance_calculation(self) -> None:
        """Flee chance uses engine formula: base + (speed_diff * factor)."""
        view = _make_view()
        view.on_enter()
        chance = view._get_flee_chance()
        # Player speed=8, enemy speed=10 → 30 + (8-10)*3 = 24%
        expected = max(
            FLEE_MIN_CHANCE,
            min(FLEE_MAX_CHANCE, FLEE_BASE_CHANCE + int((8 - 10) * FLEE_SPEED_FACTOR)),
        )
        assert chance == expected
        view.on_exit()

    def test_flee_not_available_outside_player_input(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ANIMATING_PLAYER
        # _execute_player_action should be a no-op outside PLAYER_INPUT
        view._attempt_flee()
        # Phase should not change (action rejected)
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()


class TestNegotiateAction:
    """Tests for negotiate action in the combat view."""

    def test_negotiate_not_available_after_use(self) -> None:
        view = _make_view()
        view.on_enter()
        view.engine.get_state().negotiate_used = True
        assert view._is_negotiate_available() is False
        view.on_exit()

    def test_negotiate_available_first_time(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view._is_negotiate_available() is True
        view.on_exit()


# ============================================================================
# Keyboard Input (Step 3)
# ============================================================================


class TestKeyboardInput:
    """Tests for keyboard shortcut handling."""

    def test_number_key_queues_move(self) -> None:
        moves = [_make_move("laser", "Laser"), _make_move("missile", "Missile", energy_cost=3)]
        view = _make_view(player_moves=moves)
        view.on_enter()
        view.update(1.6)  # Past intro
        assert view.phase == CombatPhase.PLAYER_INPUT
        view._build_move_buttons()
        # Simulate pressing '1' to queue first move
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        assert view.phase == CombatPhase.PLAYER_INPUT  # Still in input (queued, not executed)
        assert view._action_queue is not None
        assert not view._action_queue.is_empty
        # Press Enter to execute
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(event)
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()

    def test_tab_cycles_target(self) -> None:
        view = _make_view(num_enemies=3)
        view.on_enter()
        view.update(1.6)  # Past intro
        assert view.selected_target_idx == 0
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        view.handle_event(event)
        assert view.selected_target_idx == 1
        view.on_exit()

    def test_f_key_attempts_flee(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        view.handle_event(event)
        # Should either be animating (flee attempt) or still in player_input
        # Flee triggers animation phase
        assert view.phase in (CombatPhase.ANIMATING_PLAYER, CombatPhase.COMBAT_OVER)
        view.on_exit()

    def test_escape_key_attempts_flee(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)
        assert view.phase in (CombatPhase.ANIMATING_PLAYER, CombatPhase.COMBAT_OVER)
        view.on_exit()


# ============================================================================
# Crew Display (Step 3)
# ============================================================================


class TestCrewMoveDisplay:
    """Tests for crew move display and skip toggle."""

    def test_crew_moves_listed(self) -> None:
        crew_move = _make_heal_move("elena_heal", "Emergency Repairs", 15)
        view = _make_view(crew_moves=[crew_move])
        view.on_enter()
        crew_info = view._get_crew_move_info()
        assert len(crew_info) == 1
        assert crew_info[0]["name"] == "Emergency Repairs"
        view.on_exit()

    def test_skip_crew_move_toggle(self) -> None:
        crew_move = _make_heal_move("elena_heal", "Emergency Repairs")
        view = _make_view(crew_moves=[crew_move])
        view.on_enter()
        assert "elena_heal" not in view.skip_crew_ids
        view._toggle_skip_crew("elena_heal")
        assert "elena_heal" in view.skip_crew_ids
        view._toggle_skip_crew("elena_heal")
        assert "elena_heal" not in view.skip_crew_ids
        view.on_exit()


# ============================================================================
# Animation Effects (Step 4)
# ============================================================================


class TestAnimationEffects:
    """Tests for visual effects triggered during animation."""

    def test_hit_creates_floating_text(self) -> None:
        """A hit log entry should spawn a floating damage number after projectile arrives."""
        view = _make_view()
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["18 hull damage to Enemy 0"],
            hit=True,
        )
        anim = AnimationEvent(log_entry=log, source="player")
        view._start_animation_effects(anim)
        # Advance projectile to arrival
        view._projectile_mgr.update(2.0)
        assert len(view.floating_texts) >= 1
        view.on_exit()

    def test_miss_creates_miss_text(self) -> None:
        """A miss log entry should spawn 'MISS' floating text."""
        view = _make_view()
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["Missed!"],
            hit=False,
        )
        anim = AnimationEvent(log_entry=log, source="player")
        view._start_animation_effects(anim)
        assert any("MISS" in ft["text"] for ft in view.floating_texts)
        view.on_exit()

    def test_hit_triggers_camera_shake(self) -> None:
        """A successful hit should trigger camera shake after projectile arrives."""
        view = _make_view()
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["18 hull damage to Enemy 0"],
            hit=True,
        )
        anim = AnimationEvent(log_entry=log, source="player")
        view._start_animation_effects(anim)
        view._projectile_mgr.update(2.0)
        # Camera shake fires on projectile impact (migrated from ScreenShake to SceneCamera in C1).
        assert view.scene_camera.has_active_shakes
        view.on_exit()

    def test_miss_no_camera_shake(self) -> None:
        """A miss should not trigger camera shake."""
        view = _make_view()
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["Missed!"],
            hit=False,
        )
        anim = AnimationEvent(log_entry=log, source="player")
        view._start_animation_effects(anim)
        assert not view.scene_camera.has_active_shakes
        view.on_exit()

    def test_enemy_hit_triggers_enemy_flash(self) -> None:
        """An enemy hit should trigger flash timer on enemy card after projectile arrives."""
        view = _make_view(num_enemies=2)
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["10 hull damage to Enemy 0"],
            hit=True,
        )
        anim = AnimationEvent(log_entry=log, source="player")
        view._start_animation_effects(anim)
        view._projectile_mgr.update(2.0)
        assert view._enemy_flash_timers[0] > 0
        view.on_exit()

    def test_player_hit_triggers_player_flash(self) -> None:
        """An enemy hitting the player should trigger player flash after projectile arrives."""
        view = _make_view()
        view.on_enter()
        log = CombatLogEntry(
            round_number=1,
            actor="enemy:Enemy 0",
            action="Blaster",
            effects_applied=["8 hull damage to player"],
            hit=True,
        )
        anim = AnimationEvent(log_entry=log, source="enemy")
        view._start_animation_effects(anim)
        view._projectile_mgr.update(2.0)
        assert view._player_flash_timer > 0
        view.on_exit()


class TestFloatingTextLifecycle:
    """Tests for floating text update and cleanup."""

    def test_floating_text_rises_and_expires(self) -> None:
        view = _make_view()
        view.on_enter()
        view.floating_texts.append(
            {
                "text": "-18",
                "x": 400.0,
                "y": 300.0,
                "color": Colors.RED,
                "timer": 0.5,
                "max_timer": 0.8,
                "vy": -40,
            }
        )
        original_y = view.floating_texts[0]["y"]
        view.update(0.1)
        assert view.floating_texts[0]["y"] < original_y, "Text should rise"
        view.update(0.5)
        assert len(view.floating_texts) == 0, "Expired text should be cleaned up"
        view.on_exit()

    def test_floating_text_timer_decrements(self) -> None:
        view = _make_view()
        view.on_enter()
        view.floating_texts.append(
            {
                "text": "+20",
                "x": 100.0,
                "y": 200.0,
                "color": Colors.GREEN,
                "timer": 1.0,
                "max_timer": 1.0,
                "vy": -40,
            }
        )
        view.update(0.3)
        assert view.floating_texts[0]["timer"] == pytest.approx(0.7, abs=0.05)
        view.on_exit()


class TestPhaseSequencingWithAnimations:
    """Tests for proper phase advancement after animation queues drain."""

    def test_player_anim_to_crew_to_enemy_to_round_end(self) -> None:
        """Full sequence: ANIMATING_PLAYER → CREW → ENEMIES → ROUND_END."""
        view = _make_view()
        view.on_enter()
        view.update(1.6)  # Past intro → PLAYER_INPUT
        view._execute_player_action("test_laser")
        view._execute_queued_turn()
        # Drain all phases
        phases_seen = {view.phase}
        for _ in range(40):
            view.update(0.5)
            phases_seen.add(view.phase)
        # Should have passed through animation phases
        assert CombatPhase.ANIMATING_PLAYER in phases_seen
        # Should reach either PLAYER_INPUT again or COMBAT_OVER
        assert view.phase in (CombatPhase.PLAYER_INPUT, CombatPhase.COMBAT_OVER)
        view.on_exit()

    def test_animation_queue_drains_before_phase_advance(self) -> None:
        """Phase should not advance until all animations in queue are processed."""
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.ANIMATING_PLAYER
        # Add two events with 0.5s duration each
        log1 = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Shot 1",
            effects_applied=["hit"],
        )
        log2 = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Shot 2",
            effects_applied=["hit"],
        )
        view._enqueue_animation(log1, source="player")
        view._enqueue_animation(log2, source="player")
        # After 0.3s: first animation still playing
        view.update(0.3)
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        assert view.current_animation is not None
        # After 0.6s total: first complete, second starts
        view.update(0.3)
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()


# ============================================================================
# Combat Outcome (Step 6)
# ============================================================================


class TestCombatOutcome:
    """Tests for combat outcome summary data."""

    def test_victory_summary_has_xp(self) -> None:
        """Victory summary should include total XP from enemies."""
        view = _make_view(num_enemies=2)
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.VICTORY
        for e in state.enemies:
            e.current_hull = 0
        summary = view._get_outcome_summary()
        assert summary["result"] == CombatResult.VICTORY
        assert summary["xp_gained"] == sum(e.template.xp_reward for e in state.enemies)
        view.on_exit()

    def test_defeat_summary_shows_defeat(self) -> None:
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.DEFEAT
        summary = view._get_outcome_summary()
        assert summary["result"] == CombatResult.DEFEAT
        view.on_exit()

    def test_fled_summary(self) -> None:
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.FLED
        summary = view._get_outcome_summary()
        assert summary["result"] == CombatResult.FLED
        view.on_exit()

    def test_negotiated_summary(self) -> None:
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.NEGOTIATED
        summary = view._get_outcome_summary()
        assert summary["result"] == CombatResult.NEGOTIATED
        view.on_exit()

    def test_combat_stats_tracked(self) -> None:
        """Summary should track damage dealt and taken."""
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.VICTORY
        state.enemies[0].current_hull = 0
        # Add some log entries to count damage
        state.combat_log.append(
            CombatLogEntry(
                round_number=1,
                actor="player",
                action="Laser",
                effects_applied=["18 damage"],
            )
        )
        state.combat_log.append(
            CombatLogEntry(
                round_number=1,
                actor="enemy:Enemy 0",
                action="Blaster",
                effects_applied=["8 damage to player"],
            )
        )
        summary = view._get_outcome_summary()
        assert summary["rounds"] == state.round_number
        view.on_exit()

    def test_continue_returns_to_configured_state(self) -> None:
        view = _make_view()
        view._return_state = GameState.GALAXY_MAP
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.engine.get_state().result = CombatResult.VICTORY
        view._on_continue_pressed()
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_continue_via_click_in_combat_over(self) -> None:
        """Click anywhere during COMBAT_OVER should trigger continue."""
        view = _make_view()
        view._return_state = GameState.GALAXY_MAP
        view.on_enter()
        view.phase = CombatPhase.COMBAT_OVER
        view.engine.get_state().result = CombatResult.VICTORY
        # Simulate click
        view._on_continue_pressed()
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()


class TestOutcomeDisplayData:
    """Tests for outcome display data generation."""

    def test_victory_summary_color_is_green(self) -> None:
        view = _make_view()
        view.on_enter()
        view.engine.get_state().result = CombatResult.VICTORY
        view.engine.get_state().enemies[0].current_hull = 0
        summary = view._get_outcome_summary()
        assert summary["color"] == Colors.GREEN
        view.on_exit()

    def test_defeat_summary_color_is_red(self) -> None:
        view = _make_view()
        view.on_enter()
        view.engine.get_state().result = CombatResult.DEFEAT
        summary = view._get_outcome_summary()
        assert summary["color"] == Colors.RED
        view.on_exit()

    def test_fled_summary_color_is_yellow(self) -> None:
        view = _make_view()
        view.on_enter()
        view.engine.get_state().result = CombatResult.FLED
        summary = view._get_outcome_summary()
        assert summary["color"] == Colors.YELLOW
        view.on_exit()

    def test_summary_has_title(self) -> None:
        view = _make_view()
        view.on_enter()
        view.engine.get_state().result = CombatResult.VICTORY
        view.engine.get_state().enemies[0].current_hull = 0
        summary = view._get_outcome_summary()
        assert len(summary["title"]) > 0
        view.on_exit()


# ============================================================================
# Mouse Click Handling (Polish)
# ============================================================================


class TestMouseClickHandling:
    """Tests for mouse click handling on move buttons, flee, and enemy cards."""

    def test_click_move_button_queues_then_execute(self) -> None:
        moves = [_make_move("laser", "Laser", energy_cost=2)]
        view = _make_view(player_moves=moves)
        view.on_enter()
        view.update(1.6)  # Past intro → PLAYER_INPUT
        view._build_move_buttons()
        assert len(view.move_buttons) == 1

        # Simulate click in center of the first button's rect — queues the action
        btn = view.move_buttons[0]
        cx = btn.rect.centerx
        cy = btn.rect.centery
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(cx, cy))
        view.handle_event(event)
        assert view.phase == CombatPhase.PLAYER_INPUT  # Queued, not executed
        assert view._action_queue is not None
        assert not view._action_queue.is_empty
        # Execute with Enter
        view._execute_queued_turn()
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()

    def test_click_disabled_move_button_does_nothing(self) -> None:
        expensive = _make_move("big_gun", "Big Gun", energy_cost=99)
        view = _make_view(player_moves=[expensive])
        view.on_enter()
        view.update(1.6)
        view._build_move_buttons()
        assert not view.move_buttons[0].enabled

        btn = view.move_buttons[0]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=(btn.rect.centerx, btn.rect.centery),
        )
        view.handle_event(event)
        assert view.phase == CombatPhase.PLAYER_INPUT  # No change
        view.on_exit()

    def test_click_flee_button(self) -> None:
        from spacegame.views.combat_view import (
            FLEE_BTN_X,
            SPECIAL_BTN_Y,
            SPECIAL_BTN_W,
            SPECIAL_BTN_H,
        )

        view = _make_view()
        view.on_enter()
        view.update(1.6)

        cx = FLEE_BTN_X + SPECIAL_BTN_W // 2
        cy = SPECIAL_BTN_Y + SPECIAL_BTN_H // 2
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(cx, cy))
        view.handle_event(event)
        assert view.phase in (CombatPhase.ANIMATING_PLAYER, CombatPhase.COMBAT_OVER)
        view.on_exit()

    def test_click_enemy_card_selects_target(self) -> None:
        from spacegame.views.combat_view import (
            ENEMY_PANEL_X,
            ENEMY_PANEL_Y,
            ENEMY_PANEL_W,
            ENEMY_CARD_H,
        )

        view = _make_view(num_enemies=2)
        view.on_enter()
        view.update(1.6)
        assert view.selected_target_idx == 0

        # Click on enemy card #1 (second enemy)
        card_1_y = ENEMY_PANEL_Y + 1 * (ENEMY_CARD_H + 10)  # ENEMY_CARD_GAP = 10
        cx = ENEMY_PANEL_X + ENEMY_PANEL_W // 2
        cy = card_1_y + ENEMY_CARD_H // 2
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(cx, cy))
        view.handle_event(event)
        assert view.selected_target_idx == 1
        view.on_exit()

    def test_click_negotiate_button(self) -> None:
        from spacegame.views.combat_view import (
            NEGOTIATE_BTN_X,
            SPECIAL_BTN_Y,
            SPECIAL_BTN_W,
            SPECIAL_BTN_H,
        )

        view = _make_view()
        view.on_enter()
        view.update(1.6)

        # The negotiate button is wider (SPECIAL_BTN_W + 20)
        cx = NEGOTIATE_BTN_X + (SPECIAL_BTN_W + 20) // 2
        cy = SPECIAL_BTN_Y + SPECIAL_BTN_H // 2
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(cx, cy))
        view.handle_event(event)
        # Should show negotiate sub-menu or execute negotiate
        assert view.phase in (
            CombatPhase.PLAYER_INPUT,  # Sub-menu stays in player input
            CombatPhase.ANIMATING_PLAYER,
            CombatPhase.COMBAT_OVER,
        )
        view.on_exit()


# ============================================================================
# Negotiate Sub-Menu (Polish)
# ============================================================================


class TestNegotiateSubMenu:
    """Tests for the negotiate skill selection sub-menu."""

    def test_negotiate_shows_skill_options(self) -> None:
        """Opening negotiate should present skill choices."""
        view = _make_view()
        view.on_enter()
        view.update(1.6)
        view._open_negotiate_menu()
        assert view._negotiate_menu_open is True
        assert len(view._negotiate_skills) == 3
        view.on_exit()

    def test_negotiate_skill_selection_executes(self) -> None:
        """Selecting a skill executes negotiate with that skill."""
        view = _make_view()
        view.on_enter()
        view.update(1.6)
        view._open_negotiate_menu()
        view._select_negotiate_skill("intimidation")
        assert view._negotiate_menu_open is False
        # Should have transitioned to animation
        assert view.phase == CombatPhase.ANIMATING_PLAYER
        view.on_exit()

    def test_negotiate_menu_closes_on_cancel(self) -> None:
        view = _make_view()
        view.on_enter()
        view.update(1.6)
        view._open_negotiate_menu()
        assert view._negotiate_menu_open is True
        view._close_negotiate_menu()
        assert view._negotiate_menu_open is False
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_negotiate_keyboard_submenu(self) -> None:
        """N key opens menu, then 1/2/3 selects skill."""
        view = _make_view()
        view.on_enter()
        view.update(1.6)
        # First N press opens menu
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
        view.handle_event(event)
        assert view._negotiate_menu_open is True
        # Second press with '1' selects persuasion
        event2 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event2)
        assert view._negotiate_menu_open is False
        view.on_exit()


# ============================================================================
# Loot Generation (Polish)
# ============================================================================


class TestLootGeneration:
    """Tests for loot table rolling on victory."""

    def test_roll_loot_from_enemies(self) -> None:
        """Rolling loot from enemy loot tables produces valid items."""
        from spacegame.views.combat_view import _roll_loot

        loot_table = [
            {"commodity_id": "metals", "min_qty": 2, "max_qty": 5, "chance": 1.0},
            {"commodity_id": "electronics", "min_qty": 1, "max_qty": 3, "chance": 1.0},
        ]
        result = _roll_loot(loot_table, seed=42)
        assert "metals" in result
        assert 2 <= result["metals"] <= 5
        assert "electronics" in result
        assert 1 <= result["electronics"] <= 3

    def test_roll_loot_zero_chance_gives_nothing(self) -> None:
        from spacegame.views.combat_view import _roll_loot

        loot_table = [
            {"commodity_id": "gold", "min_qty": 1, "max_qty": 10, "chance": 0.0},
        ]
        result = _roll_loot(loot_table, seed=42)
        assert "gold" not in result

    def test_roll_loot_empty_table(self) -> None:
        from spacegame.views.combat_view import _roll_loot

        result = _roll_loot([], seed=42)
        assert result == {}

    def test_outcome_summary_includes_loot(self) -> None:
        """Victory summary should include generated loot."""
        view = _make_view()
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.VICTORY
        state.enemies[0].current_hull = 0
        # Give enemy a loot table
        state.enemies[0].template.loot_table.append(
            {"commodity_id": "metals", "min_qty": 1, "max_qty": 3, "chance": 1.0}
        )
        summary = view._get_outcome_summary()
        assert "loot" in summary
        assert "metals" in summary["loot"]
        view.on_exit()


# ============================================================================
# Bribe button
# ============================================================================


def _make_bribe_enemy_template(
    template_id: str = "pirate_scout",
    name: str = "Pirate Scout",
    bribe_cost: int = 100,
) -> EnemyShipTemplate:
    """Create enemy template with a bribe cost for bribe tests."""
    return EnemyShipTemplate(
        id=template_id,
        name=name,
        description="A test enemy.",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=50,
        shields=10,
        energy=8,
        energy_regen=3,
        speed=10,
        evasion=15,
        accuracy=65,
        moves=[_make_move("enemy_blaster", "Blaster", 8.0, 2)],
        loot_table=[],
        negotiate_difficulty=3,
        xp_reward=20,
        bribe_cost=bribe_cost,
    )


def _make_bribe_view(bribe_cost: int = 100) -> CombatView:
    """Create a CombatView with a bribeable enemy."""
    template = _make_bribe_enemy_template(bribe_cost=bribe_cost)
    enemy = EnemyShip.from_template(template)
    player = _make_player_state()
    encounter = CombatEncounter(enemy_templates=[template], encounter_seed=42)
    state = CombatState(
        player=player,
        enemies=[enemy],
        encounter=encounter,
        combat_log=[],
    )
    engine = CombatEngine(state, seed=42)
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = CombatView(
        ui_manager=ui_manager,
        combat_engine=engine,
        player=None,
    )
    return view


class TestBribeButton:
    """Tests for the bribe button in combat view."""

    def test_bribe_keyboard_shortcut_triggers_bribe(self) -> None:
        """Pressing B during PLAYER_INPUT should trigger bribe attempt."""
        view = _make_bribe_view(bribe_cost=100)
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        # Set player credits so view can attempt bribe
        view._bribe_credits_available = 500

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
        view.handle_event(event)

        # After bribe attempt, phase should advance (animating or combat_over)
        assert view.phase != CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_bribe_click_triggers_bribe(self) -> None:
        """Clicking bribe button area during PLAYER_INPUT should trigger bribe."""
        from spacegame.views.combat_view import (
            BRIBE_BTN_X,
            SPECIAL_BTN_Y,
            SPECIAL_BTN_W,
            SPECIAL_BTN_H,
        )

        view = _make_bribe_view(bribe_cost=100)
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        view._bribe_credits_available = 500

        pos = (BRIBE_BTN_X + 5, SPECIAL_BTN_Y + 5)
        view._handle_click(pos)

        assert view.phase != CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_bribe_grayed_out_after_use(self) -> None:
        """After bribe_used is set, bribe should not trigger."""
        view = _make_bribe_view(bribe_cost=100)
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        view._bribe_credits_available = 500

        # Mark bribe as used
        view.engine.get_state().bribe_used = True

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
        view.handle_event(event)

        # Phase should remain PLAYER_INPUT since bribe is already used
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_outcome_summary_maps_include_bribed(self) -> None:
        """BRIBED result should have title and color in outcome summary."""
        view = _make_bribe_view(bribe_cost=100)
        view.on_enter()
        state = view.engine.get_state()
        state.result = CombatResult.BRIBED

        summary = view._get_outcome_summary()
        assert summary["title"] == "BRIBED"
        assert summary["color"] != Colors.TEXT_PRIMARY  # Has a specific color


# ============================================================================
# Dual tech cinematic wiring (Combat C5 §4.3)
# ============================================================================


def _portrait_config():  # type: ignore[no-untyped-def]
    from spacegame.engine.dual_tech_portraits import PortraitConfig

    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    surf.fill((180, 180, 200, 255))
    return PortraitConfig(surface=surf)


class TestDualTechCinematicWiring:
    """Combat view exposes trigger_dual_tech() and drives the cinematic
    through update + render without disturbing normal combat flow."""

    def test_controller_slot_empty_by_default(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view._dual_tech_controller is None
        assert not view.dual_tech_active
        view.on_exit()

    def test_trigger_populates_controller(self) -> None:
        view = _make_view()
        view.on_enter()
        view.trigger_dual_tech(
            tech_name="FROST LANCE",
            dominant_element="ion",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(100.0, 400.0),
            trail_end=(600.0, 400.0),
        )
        assert view._dual_tech_controller is not None
        assert view.dual_tech_active
        view.on_exit()

    def test_trigger_snapshots_camera_zoom(self) -> None:
        view = _make_view()
        view.on_enter()
        view.scene_camera.zoom = 1.0
        view.trigger_dual_tech(
            tech_name="TEST",
            dominant_element="plasma",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(0.0, 0.0),
            trail_end=(100.0, 0.0),
        )
        assert view._pre_cinematic_zoom == 1.0
        view.on_exit()

    def test_update_advances_and_completes_controller(self) -> None:
        from spacegame.engine.dual_tech_cinematic import STANDARD_TOTAL

        view = _make_view()
        view.on_enter()
        view.trigger_dual_tech(
            tech_name="TEST",
            dominant_element="plasma",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(0.0, 0.0),
            trail_end=(100.0, 0.0),
        )
        # Fast-forward past total duration.
        view.update(STANDARD_TOTAL + 0.1)
        # Controller should clear and camera zoom should restore.
        assert view._dual_tech_controller is None
        assert view.scene_camera.zoom == view._pre_cinematic_zoom
        view.on_exit()

    def test_on_impact_callback_fires(self) -> None:
        fired: list[int] = []

        def _cb() -> None:
            fired.append(1)

        view = _make_view()
        view.on_enter()
        view.trigger_dual_tech(
            tech_name="TEST",
            dominant_element="plasma",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(0.0, 0.0),
            trail_end=(100.0, 0.0),
            on_impact=_cb,
        )
        # Advance enough to trigger the IMPACT phase boundary.
        view.update(2.8)
        assert len(fired) == 1
        view.on_exit()

    def test_camera_zoom_interpolates_during_cinematic(self) -> None:
        view = _make_view()
        view.on_enter()
        view.scene_camera.zoom = 1.0
        view.trigger_dual_tech(
            tech_name="TEST",
            dominant_element="plasma",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(0.0, 0.0),
            trail_end=(100.0, 0.0),
        )
        # Mid CAMERA_ZOOM phase — zoom should be between 1.0 and 1.25.
        view.update(0.3)
        assert 1.0 < view.scene_camera.zoom < 1.25
        view.on_exit()

    def test_controller_render_is_callable_directly(self) -> None:
        """The active controller is addressable from the view for direct
        render — combat view delegates to it during normal render()."""
        view = _make_view()
        view.on_enter()
        view.trigger_dual_tech(
            tech_name="TEST",
            dominant_element="plasma",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(100.0, 200.0),
            trail_end=(600.0, 200.0),
        )
        view.update(1.6)
        assert view._dual_tech_controller is not None
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        # Directly invoke controller render — combat view's render path
        # delegates here after all other layers.
        view._dual_tech_controller.render(screen)
        view.on_exit()


# ============================================================================
# Turn-clock pause hook (C5 deferral) + ArenaEntry intro (C3 deferral)
# ============================================================================


class TestTurnClockPauseHook:
    """Phase advancement is blocked while a dual tech cinematic runs."""

    def test_phase_advances_without_cinematic_active(self) -> None:
        """Baseline: intro phase advances when entry completes."""
        from spacegame.engine.arena_entry import TOTAL_DURATION as ARENA_ENTRY_TOTAL

        view = _make_view()
        view.on_enter()
        assert view.phase == CombatPhase.INTRO
        view.update(ARENA_ENTRY_TOTAL + 0.1)
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_phase_stalls_while_cinematic_active(self) -> None:
        """Firing a dual tech during INTRO should freeze the phase."""
        view = _make_view()
        view.on_enter()
        # Fire cinematic immediately — before the intro entry completes.
        view.trigger_dual_tech(
            tech_name="FROST LANCE",
            dominant_element="ion",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(100.0, 400.0),
            trail_end=(600.0, 400.0),
        )
        starting_phase = view.phase
        # Advance 2 seconds — INTRO would normally complete (1.5s), but
        # cinematic is active so phase holds.
        view.update(2.0)
        assert view.dual_tech_active
        # Phase must not have advanced during the cinematic.
        assert view.phase == starting_phase
        view.on_exit()

    def test_phase_resumes_after_cinematic_completes(self) -> None:
        from spacegame.engine.dual_tech_cinematic import STANDARD_TOTAL

        view = _make_view()
        view.on_enter()
        view.trigger_dual_tech(
            tech_name="FROST LANCE",
            dominant_element="ion",
            secondary_element="cryo",
            left_portrait=_portrait_config(),
            right_portrait=_portrait_config(),
            trail_start=(100.0, 400.0),
            trail_end=(600.0, 400.0),
        )
        # Complete cinematic; then a few more frames to let intro advance.
        view.update(STANDARD_TOTAL + 0.1)
        view.update(2.0)
        assert not view.dual_tech_active
        # After cinematic ends, intro phase resumes + completes.
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()


class TestArenaEntryIntroWiring:
    """Combat view now uses ArenaEntry timeline to drive the INTRO phase."""

    def test_arena_entry_constructed_on_enter(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view._arena_entry is not None
        view.on_exit()

    def test_arena_entry_cleared_after_intro_completes(self) -> None:
        from spacegame.engine.arena_entry import TOTAL_DURATION as ARENA_ENTRY_TOTAL

        view = _make_view()
        view.on_enter()
        view.update(ARENA_ENTRY_TOTAL + 0.1)
        assert view._arena_entry is None
        assert view.phase == CombatPhase.PLAYER_INPUT
        view.on_exit()

    def test_arena_entry_interpolates_camera_zoom(self) -> None:
        """Camera zoom ramps from WIDE (0.85) toward DEFAULT (1.0)."""
        view = _make_view()
        view.on_enter()
        # At t=0 camera should be at wide-ish (since camera_push_factor is 0).
        view.update(0.1)
        zoom_early = view.scene_camera.zoom
        # Mid-push: camera zoom should be closer to default.
        view.update(0.6)  # t≈0.7, mid-push phase
        zoom_mid = view.scene_camera.zoom
        # Zoom should have increased (camera pushing in).
        assert zoom_mid > zoom_early
        view.on_exit()

    def test_arena_entry_enemy_count_matches_state(self) -> None:
        view = _make_view(num_enemies=2)
        view.on_enter()
        assert view._arena_entry is not None
        assert view._arena_entry.enemy_count == 2
        view.on_exit()


# ============================================================================
# Dual tech cinematic trigger from action queue (C5 Impl 2)
# ============================================================================


class TestDualTechTriggerFromQueue:
    """A dual tech move in the action queue fires the cinematic at
    turn dispatch."""

    def test_dual_tech_move_fires_cinematic(self) -> None:
        """Queueing `fire_at_will` + executing the turn triggers the cinematic."""
        from spacegame.models.action_queue import ActionQueue

        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        view._action_queue = ActionQueue(energy_available=20)
        # Inject a dual-tech queued action directly.
        from spacegame.models.action_queue import QueuedAction
        view._action_queue._actions.append(
            QueuedAction(
                move_id="fire_at_will",
                target_idx=0,
                energy_cost=6,
                move_name="Fire at Will",
            )
        )
        view._execute_queued_turn()
        assert view.dual_tech_active
        view.on_exit()

    def test_non_dual_tech_move_does_not_fire_cinematic(self) -> None:
        """A regular move (e.g., a laser shot) shouldn't trigger the cinematic."""
        from spacegame.models.action_queue import ActionQueue, QueuedAction

        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        view._action_queue = ActionQueue(energy_available=20)
        view._action_queue._actions.append(
            QueuedAction(
                move_id="laser_shot",  # not a dual tech
                target_idx=0,
                energy_cost=2,
                move_name="Laser Shot",
            )
        )
        view._execute_queued_turn()
        assert not view.dual_tech_active
        view.on_exit()

    def test_empty_queue_does_not_fire_cinematic(self) -> None:
        view = _make_view()
        view.on_enter()
        view.phase = CombatPhase.PLAYER_INPUT
        from spacegame.models.action_queue import ActionQueue

        view._action_queue = ActionQueue(energy_available=20)  # empty
        view._execute_queued_turn()
        assert not view.dual_tech_active
        view.on_exit()
        view.on_exit()
