"""QA-F-2: wanderer auto-retire emits a journal entry in both views.

Without this, a captain that auto-retires after 3 unresolved encounters
just silently disappears from the pool. Player has no narrative cue
that the rivalry ended.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.captain_memory import (
    OUTCOME_FLED,
    STATUS_ACTIVE,
    STATUS_WANDERER,
    CaptainMemory,
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
from spacegame.models.journal import Journal
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


def _make_player() -> Player:
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
    return Player(
        name="T",
        credits=500,
        current_system_id="havens_rest",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )


def _make_engine(captain_id: str) -> CombatEngine:
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


class TestWandererJournalEntry:
    def test_third_fled_encounter_fires_wanderer_entry(self) -> None:
        """Build up memory to 2 unresolved encounters, then the 3rd flee
        transitions to wanderer status and fires the journal entry."""
        player = _make_player()
        player.game_day = 50
        # Pre-set memory with 2 unresolved encounters
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=2,
            last_outcome=OUTCOME_FLED,
            status=STATUS_ACTIVE,
            first_seen_day=10,
            last_seen_day=30,
        )
        journal = Journal()
        view = CombatView(
            _ui_manager(),
            _make_engine(captain_id="vela_wolfs_ear"),
            player,
            journal=journal,
        )
        view.on_enter()
        # Third encounter — player flees again -> transitions to wanderer
        view.engine.get_state().result = CombatResult.FLED
        view._maybe_record_captain_encounter()
        # Wanderer status transitioned
        assert player.captain_memory["vela_wolfs_ear"].status == STATUS_WANDERER
        # Journal entry was added
        entries = journal.get_entries()
        wanderer_entries = [e for e in entries if "moved on" in e.text]
        assert len(wanderer_entries) == 1
        view.on_exit()

    def test_already_wanderer_does_not_duplicate_entry(self) -> None:
        """If somehow re-encountering an already-wanderer captain, no
        second journal entry fires."""
        player = _make_player()
        player.game_day = 50
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=5,
            last_outcome=OUTCOME_FLED,
            status=STATUS_WANDERER,
            first_seen_day=10,
            last_seen_day=40,
        )
        journal = Journal()
        view = CombatView(
            _ui_manager(),
            _make_engine(captain_id="vela_wolfs_ear"),
            player,
            journal=journal,
        )
        view.on_enter()
        view.engine.get_state().result = CombatResult.FLED
        view._maybe_record_captain_encounter()
        wanderer_entries = [e for e in journal.get_entries() if "moved on" in e.text]
        assert wanderer_entries == []
        view.on_exit()

    def test_first_flee_does_not_trigger_wanderer_entry(self) -> None:
        """Flee on first encounter: counted but not auto-retired."""
        player = _make_player()
        player.game_day = 5
        journal = Journal()
        view = CombatView(
            _ui_manager(),
            _make_engine(captain_id="vela_wolfs_ear"),
            player,
            journal=journal,
        )
        view.on_enter()
        view.engine.get_state().result = CombatResult.FLED
        view._maybe_record_captain_encounter()
        # Not wanderer yet
        assert player.captain_memory["vela_wolfs_ear"].status == STATUS_ACTIVE
        # Only first_meeting entry, no wanderer entry
        wanderer_entries = [e for e in journal.get_entries() if "moved on" in e.text]
        assert wanderer_entries == []
        view.on_exit()
