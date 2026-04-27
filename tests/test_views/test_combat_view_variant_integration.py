"""RC-3: CombatView variant consumption + ordering.

Verifies the COMBAT_OVER hook ordering: surface uses pre-recording
relationship state so the in-flight outcome line uses the right variant.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.captain_memory import (
    OUTCOME_FLED,
    OUTCOME_NEGOTIATED,
    STATUS_ACTIVE,
    STATUS_TRUCE,
    CaptainMemory,
)
from spacegame.models.captain_variant import (
    MEETING_STATE_POST_TRUCE,
    MEETING_STATE_RETURN,
    CaptainVariant,
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


def _make_engine(captain_id: str = "vela_wolfs_ear") -> CombatEngine:
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


def _patch_dl_with_variants(monkeypatch, variants_by_key: dict) -> None:
    from spacegame import data_loader as dl_mod

    original = dl_mod.get_data_loader

    def _fake_dl():
        dl = original()
        dl.captain_variants = dict(variants_by_key)
        return dl

    monkeypatch.setattr(dl_mod, "get_data_loader", _fake_dl)


# ---------------------------------------------------------------------------
# Variant overlay in COMBAT_OVER surfacing
# ---------------------------------------------------------------------------


class TestVariantSurfacing:
    def test_first_meeting_uses_base_defeat_line(self, monkeypatch) -> None:
        """Player has never met vela: combat outcome surfaces base line."""
        _patch_dl_with_variants(monkeypatch, {})
        player = _make_player()
        view = CombatView(_ui_manager(), _make_engine(), player)
        view.on_enter()
        view.engine.get_state().result = CombatResult.NEGOTIATED
        view._maybe_surface_captain_outcome_line()
        # Base vela surrender_line plays (from captains.json)
        from spacegame.data_loader import get_data_loader

        captain = get_data_loader().captains["vela_wolfs_ear"]
        assert any(captain.surrender_line in line for line in view.visible_log_lines), (
            view.visible_log_lines
        )
        view.on_exit()

    def test_return_meeting_uses_variant_when_authored(self, monkeypatch) -> None:
        """Player has met vela once with no resolution: variant fires."""
        variant = CaptainVariant(
            captain_id="vela_wolfs_ear",
            meeting_state=MEETING_STATE_RETURN,
            surrender_line="Wolf's Ear standing down again. We keep meeting.",
        )
        _patch_dl_with_variants(monkeypatch, {("vela_wolfs_ear", MEETING_STATE_RETURN): variant})
        player = _make_player()
        # Pre-existing memory: met once, fled (no resolution)
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            last_outcome=OUTCOME_FLED,
            status=STATUS_ACTIVE,
            first_seen_day=2,
            last_seen_day=2,
        )
        view = CombatView(_ui_manager(), _make_engine(), player)
        view.on_enter()
        view.engine.get_state().result = CombatResult.NEGOTIATED
        view._maybe_surface_captain_outcome_line()
        assert any("We keep meeting" in line for line in view.visible_log_lines)
        view.on_exit()

    def test_post_truce_meeting_uses_variant(self, monkeypatch) -> None:
        variant = CaptainVariant(
            captain_id="vela_wolfs_ear",
            meeting_state=MEETING_STATE_POST_TRUCE,
            defeat_line="Truce broken twice over. You and I are done.",
        )
        _patch_dl_with_variants(
            monkeypatch, {("vela_wolfs_ear", MEETING_STATE_POST_TRUCE): variant}
        )
        player = _make_player()
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            last_outcome=OUTCOME_NEGOTIATED,
            status=STATUS_TRUCE,
        )
        view = CombatView(_ui_manager(), _make_engine(), player)
        view.on_enter()
        view.engine.get_state().result = CombatResult.VICTORY
        view._maybe_surface_captain_outcome_line()
        assert any("Truce broken twice over" in line for line in view.visible_log_lines)
        view.on_exit()


# ---------------------------------------------------------------------------
# Surface-then-record ordering
# ---------------------------------------------------------------------------


class TestSurfaceBeforeRecordOrdering:
    """Critical: the in-flight outcome must use the meeting state going
    INTO the fight, not the resolution about to be written. Test by
    authoring distinct variants for `return` and `post_defeated` and
    observing which fires when the player wins for the first time."""

    def test_first_victory_uses_first_meeting_variant_not_post_defeated(self, monkeypatch) -> None:
        # Author distinct variants for both states
        return_variant = CaptainVariant(
            captain_id="vela_wolfs_ear",
            meeting_state=MEETING_STATE_RETURN,
            defeat_line="RETURN-state defeat line",
        )
        post_defeated_variant = CaptainVariant(
            captain_id="vela_wolfs_ear",
            meeting_state="post_defeated",
            defeat_line="POST-DEFEATED-state defeat line",
        )
        _patch_dl_with_variants(
            monkeypatch,
            {
                ("vela_wolfs_ear", MEETING_STATE_RETURN): return_variant,
                ("vela_wolfs_ear", "post_defeated"): post_defeated_variant,
            },
        )
        player = _make_player()
        # Pre-existing: met once before, no resolution yet (status=ACTIVE)
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            last_outcome=OUTCOME_FLED,
            status=STATUS_ACTIVE,
        )
        view = CombatView(_ui_manager(), _make_engine(), player)
        view.on_enter()
        view.engine.get_state().result = CombatResult.VICTORY

        # Surface should fire RETURN-state line (the player has met once,
        # hasn't resolved). The recorder will then update memory to
        # post_defeated, but that's for FUTURE encounters.
        view._maybe_surface_captain_outcome_line()
        view._maybe_record_captain_encounter()

        assert any("RETURN-state defeat line" in line for line in view.visible_log_lines), (
            view.visible_log_lines
        )
        assert not any("POST-DEFEATED-state" in line for line in view.visible_log_lines)
        # Memory is now updated for next time
        assert player.captain_memory["vela_wolfs_ear"].status == "defeated"
        view.on_exit()
