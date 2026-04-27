"""RC-2: CombatView records captain encounter at COMBAT_OVER.

Uses real Player + CaptainMemory (not mocks) so the test exercises the
actual record_captain_encounter pipeline end-to-end.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_DEFEAT,
    OUTCOME_FLED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    STATUS_ACTIVE,
    STATUS_BRIBED_OFF,
    STATUS_DEFEATED,
    STATUS_TRUCE,
)
from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatResult,
    CombatState,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.views.combat_view import CombatView


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _ui_manager() -> pygame_gui.UIManager:
    _init_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_player(game_day: int = 5) -> Player:
    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="x",
        cargo_capacity=10,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=2,
        special_abilities=[],
        availability="all",
    )
    player = Player(
        name="Test",
        credits=500,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


def _make_engine(captain_id: str = "") -> CombatEngine:
    template = EnemyShipTemplate(
        id="pirate_scout",
        name="Pirate",
        description="x",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=80,
        shields=0,
        energy=10,
        energy_regen=3,
        speed=8,
        evasion=0,
        accuracy=70,
        moves=[
            CombatMove(
                id="m",
                name="m",
                description="",
                effects=[CombatEffect(type=EffectType.DAMAGE, value=5.0)],
                energy_cost=2,
            )
        ],
        loot_table=[],
        negotiate_difficulty=3,
        flee_threshold=0.0,
        bribe_cost=0,
    )
    encounter = CombatEncounter(
        enemy_templates=[template], encounter_seed=42, captain_id=captain_id
    )
    state = CombatState(
        player=PlayerCombatState(
            hull=100,
            max_hull=100,
            shields=20,
            max_shields=40,
            energy=10,
            max_energy=10,
            energy_regen=3,
            speed=8,
            evasion=10,
            accuracy=80,
            equipment_moves=[],
            crew_moves=[],
            active_effects=[],
            cooldowns={},
        ),
        enemies=[EnemyShip.from_template(template)],
        encounter=encounter,
        combat_log=[],
    )
    return CombatEngine(state, seed=42)


def _make_view(captain_id: str = "", player: Player | None = None) -> CombatView:
    if player is None:
        player = _make_player()
    view = CombatView(_ui_manager(), _make_engine(captain_id), player)
    view.on_enter()
    return view


# ---------------------------------------------------------------------------
# Result -> outcome mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "result,expected_outcome,expected_status",
    [
        (CombatResult.VICTORY, OUTCOME_VICTORY, STATUS_DEFEATED),
        (CombatResult.NEGOTIATED, OUTCOME_NEGOTIATED, STATUS_TRUCE),
        (CombatResult.BRIBED, OUTCOME_BRIBED, STATUS_BRIBED_OFF),
        (CombatResult.DEFEAT, OUTCOME_DEFEAT, STATUS_ACTIVE),
        (CombatResult.FLED, OUTCOME_FLED, STATUS_ACTIVE),
    ],
)
class TestResultMapping:
    def test_records_outcome_and_resolves_status(
        self, result, expected_outcome, expected_status
    ) -> None:
        player = _make_player(game_day=10)
        view = _make_view(captain_id="vela_wolfs_ear", player=player)
        view.engine.get_state().result = result
        view._maybe_record_captain_encounter()

        mem = player.captain_memory["vela_wolfs_ear"]
        assert mem.last_outcome == expected_outcome
        assert mem.status == expected_status
        assert mem.encounter_count == 1
        assert mem.first_seen_day == 10
        assert mem.last_seen_day == 10
        view.on_exit()


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------


class TestSkipConditions:
    def test_no_captain_attached_skips_recording(self) -> None:
        player = _make_player()
        view = _make_view(captain_id="", player=player)
        view.engine.get_state().result = CombatResult.VICTORY
        view._maybe_record_captain_encounter()
        assert player.captain_memory == {}
        view.on_exit()

    def test_no_player_skips_recording(self) -> None:
        view = CombatView(_ui_manager(), _make_engine(captain_id="vela_wolfs_ear"), None)
        view.on_enter()
        view.engine.get_state().result = CombatResult.VICTORY
        view._maybe_record_captain_encounter()
        # Doesn't crash, doesn't record (no player to record on)
        view.on_exit()

    def test_in_progress_result_skips_recording(self) -> None:
        player = _make_player()
        view = _make_view(captain_id="vela_wolfs_ear", player=player)
        # Result is IN_PROGRESS by default
        view._maybe_record_captain_encounter()
        assert player.captain_memory == {}
        view.on_exit()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_double_call_does_not_double_record(self) -> None:
        player = _make_player()
        view = _make_view(captain_id="vela_wolfs_ear", player=player)
        view.engine.get_state().result = CombatResult.VICTORY
        view._maybe_record_captain_encounter()
        view._maybe_record_captain_encounter()
        view._maybe_record_captain_encounter()
        # Encounter count should be 1, not 3
        assert player.captain_memory["vela_wolfs_ear"].encounter_count == 1
        view.on_exit()

    def test_on_enter_resets_guard_for_next_fight(self) -> None:
        """A new fight (new on_enter) should be free to record again."""
        player = _make_player()
        view = _make_view(captain_id="vela_wolfs_ear", player=player)
        view.engine.get_state().result = CombatResult.FLED
        view._maybe_record_captain_encounter()
        assert player.captain_memory["vela_wolfs_ear"].encounter_count == 1
        # Simulate next fight
        view.on_exit()
        view.engine = _make_engine(captain_id="vela_wolfs_ear")
        view.engine.get_state().result = CombatResult.FLED
        view.on_enter()
        view._maybe_record_captain_encounter()
        # Now at 2 encounters across 2 fights
        assert player.captain_memory["vela_wolfs_ear"].encounter_count == 2
        view.on_exit()


# ---------------------------------------------------------------------------
# Multi-encounter sequencing toward auto-retire (RC-1 threshold = 3)
# ---------------------------------------------------------------------------


class TestThresholdReachedAcrossFights:
    def test_three_unresolved_fights_auto_retire_to_wanderer(self) -> None:
        from spacegame.models.captain_memory import STATUS_WANDERER

        player = _make_player()
        for _ in range(3):
            view = _make_view(captain_id="vela_wolfs_ear", player=player)
            view.engine.get_state().result = CombatResult.FLED
            view._maybe_record_captain_encounter()
            view.on_exit()
        mem = player.captain_memory["vela_wolfs_ear"]
        assert mem.encounter_count == 3
        assert mem.status == STATUS_WANDERER
