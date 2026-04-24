"""CE-5b: combat view crew interjection integration.

Builds a real CombatView with a stubbed player + crew_roster + a small
in-memory interjection bank, then drives state transitions and asserts
interjections surface in the combat log + floating-text overlay.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
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
from spacegame.models.crew_interjection import CrewInterjection
from spacegame.views.combat_view import CombatPhase, CombatView


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _ui_manager() -> pygame_gui.UIManager:
    _init_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _player_state() -> PlayerCombatState:
    return PlayerCombatState(
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
        equipment_moves=[
            CombatMove(
                id="laser",
                name="Laser",
                description="x",
                effects=[CombatEffect(type=EffectType.DAMAGE, value=10.0)],
                energy_cost=2,
            )
        ],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )


def _enemy_template(tid: str = "pirate_scout") -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id=tid,
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
                id="bite",
                name="Bite",
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


def _make_engine(seed: int = 42, enemy_tid: str = "pirate_scout") -> CombatEngine:
    template = _enemy_template(enemy_tid)
    encounter = CombatEncounter(enemy_templates=[template], encounter_seed=seed)
    state = CombatState(
        player=_player_state(),
        enemies=[EnemyShip.from_template(template)],
        encounter=encounter,
        combat_log=[],
    )
    return CombatEngine(state, seed=seed)


def _player_with_crew(crew: list[tuple[str, str]]) -> object:
    """Build a player stub whose crew_roster yields the listed crew."""
    members = [
        (MagicMock(id=cid, name=cname), MagicMock())
        for cid, cname in crew
    ]
    roster = MagicMock()
    roster.get_recruited_members.return_value = members
    player = MagicMock()
    player.crew_roster = roster
    player.dialogue_flags = {}
    return player


def _patch_data_loader_with(monkeypatch, bank: list[CrewInterjection]) -> None:
    from spacegame import data_loader as dl_mod

    original = dl_mod.get_data_loader

    def _fake_dl():
        dl = original()
        dl.crew_interjections = bank
        return dl

    monkeypatch.setattr(dl_mod, "get_data_loader", _fake_dl)


# ---------------------------------------------------------------------------
# Resolver wiring
# ---------------------------------------------------------------------------


class TestResolverWiring:
    def test_resolver_built_with_recruited_crew(self, monkeypatch) -> None:
        bank = [CrewInterjection("elena_reeves", "first_turn", ["Engagement window."])]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([("elena_reeves", "Elena")]),
        )
        view.on_enter()
        assert view._interjection_resolver is not None
        view.on_exit()

    def test_no_resolver_when_no_crew_aboard(self, monkeypatch) -> None:
        bank = [CrewInterjection("elena_reeves", "first_turn", ["x"])]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([]),
        )
        view.on_enter()
        assert view._interjection_resolver is None
        view.on_exit()

    def test_no_resolver_when_bank_empty(self, monkeypatch) -> None:
        _patch_data_loader_with(monkeypatch, [])
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([("elena_reeves", "Elena")]),
        )
        view.on_enter()
        assert view._interjection_resolver is None
        view.on_exit()


# ---------------------------------------------------------------------------
# Round-end interjection surfacing
# ---------------------------------------------------------------------------


class TestRoundEndSurfacing:
    def test_first_turn_interjection_surfaces_at_round_end(
        self, monkeypatch
    ) -> None:
        bank = [CrewInterjection("elena_reeves", "first_turn", ["Engagement."])]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([("elena_reeves", "Elena")]),
        )
        view.on_enter()
        view._maybe_surface_round_interjection()
        # Combat log gets the line
        assert any(
            "Elena" in line for line in view.visible_log_lines
        ), view.visible_log_lines
        # Floating subtitle pushed
        assert view.floating_texts, "expected floating subtitle"
        view.on_exit()

    def test_one_interjection_per_round_throttle(self, monkeypatch) -> None:
        bank = [
            CrewInterjection("elena_reeves", "first_turn", ["a"]),
            CrewInterjection("marcus_jin", "first_turn", ["b"]),
        ]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew(
                [("elena_reeves", "Elena"), ("marcus_jin", "Marcus")]
            ),
        )
        view.on_enter()
        view._maybe_surface_round_interjection()
        view._maybe_surface_round_interjection()
        # Only one fired even though both crew were eligible
        assert view._interjections_this_fight == 1
        view.on_exit()

    def test_max_per_fight_throttle(self, monkeypatch) -> None:
        # 5 crew with enemy_type_match (always eligible while enemy alive).
        # Throttle caps total fires at 4 across the fight.
        crew = [(f"crew_{i}", f"C{i}") for i in range(5)]
        bank = [
            CrewInterjection(
                cid,
                "enemy_type_match",
                ["x"],
                conditions={"enemy_template_id": "pirate_scout"},
            )
            for cid, _ in crew
        ]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew(crew),
        )
        view.on_enter()
        state = view.engine.get_state()
        for r in range(1, 11):
            state.round_number = r
            view._maybe_surface_round_interjection()
        assert view._interjections_this_fight == 4
        view.on_exit()


# ---------------------------------------------------------------------------
# Combat-outcome interjection
# ---------------------------------------------------------------------------


class TestOutcomeSurfacing:
    def test_victory_outcome_surfaces(self, monkeypatch) -> None:
        bank = [
            CrewInterjection(
                "elena_reeves",
                "combat_outcome",
                ["Engagement closed."],
                conditions={"outcome": "victory"},
            )
        ]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([("elena_reeves", "Elena")]),
        )
        view.on_enter()
        # Force a victory result
        view.engine.get_state().result = CombatResult.VICTORY
        view._maybe_surface_outcome_interjection()
        assert view._interjections_this_fight == 1
        assert any("Engagement closed." in line for line in view.visible_log_lines)
        view.on_exit()

    def test_captain_outcome_line_surfaces_on_victory(
        self, monkeypatch
    ) -> None:
        """CE-6: when encounter has captain_id, defeat_line surfaces on victory."""
        from spacegame.models.enemy_captain import EnemyCaptain

        captain = EnemyCaptain(
            id="test_capn",
            name="Test Cap",
            nickname="The Test",
            home_sector="havens_rest",
            signature_ship_template="pirate_scout",
            pre_combat_hail="hail",
            surrender_line="surrender_text",
            retreat_line="retreat_text",
            victory_line="victory_text",
            defeat_line="captain_defeated_text",
        )

        from spacegame import data_loader as dl_mod

        original = dl_mod.get_data_loader

        def _fake_dl():
            dl = original()
            dl.captains["test_capn"] = captain
            return dl

        monkeypatch.setattr(dl_mod, "get_data_loader", _fake_dl)

        engine = _make_engine()
        engine.get_state().encounter.captain_id = "test_capn"
        engine.get_state().result = CombatResult.VICTORY

        view = CombatView(_ui_manager(), engine, _player_with_crew([]))
        view.on_enter()
        view._maybe_surface_captain_outcome_line()
        # Captain's defeat_line should appear (player won → captain lost)
        assert any(
            "captain_defeated_text" in line for line in view.visible_log_lines
        ), view.visible_log_lines
        view.on_exit()

    def test_captain_outcome_line_surfaces_on_negotiate(
        self, monkeypatch
    ) -> None:
        from spacegame.models.enemy_captain import EnemyCaptain

        captain = EnemyCaptain(
            id="test_capn2",
            name="X",
            nickname="Y",
            home_sector="",
            signature_ship_template="pirate_scout",
            pre_combat_hail="x",
            surrender_line="surrender_text",
            retreat_line="",
            victory_line="",
            defeat_line="",
        )
        from spacegame import data_loader as dl_mod

        original = dl_mod.get_data_loader

        def _fake_dl():
            dl = original()
            dl.captains["test_capn2"] = captain
            return dl

        monkeypatch.setattr(dl_mod, "get_data_loader", _fake_dl)

        engine = _make_engine()
        engine.get_state().encounter.captain_id = "test_capn2"
        engine.get_state().result = CombatResult.NEGOTIATED

        view = CombatView(_ui_manager(), engine, _player_with_crew([]))
        view.on_enter()
        view._maybe_surface_captain_outcome_line()
        assert any(
            "surrender_text" in line for line in view.visible_log_lines
        )
        view.on_exit()

    def test_captain_outcome_silent_when_no_captain_attached(
        self, monkeypatch
    ) -> None:
        engine = _make_engine()
        engine.get_state().result = CombatResult.VICTORY
        view = CombatView(_ui_manager(), engine, _player_with_crew([]))
        view.on_enter()
        log_before = list(view.visible_log_lines)
        view._maybe_surface_captain_outcome_line()
        # No new lines added
        assert view.visible_log_lines == log_before
        view.on_exit()

    def test_no_outcome_on_flee(self, monkeypatch) -> None:
        bank = [
            CrewInterjection(
                "elena_reeves", "combat_outcome", ["x"]
            )
        ]
        _patch_data_loader_with(monkeypatch, bank)
        view = CombatView(
            _ui_manager(),
            _make_engine(),
            _player_with_crew([("elena_reeves", "Elena")]),
        )
        view.on_enter()
        view.engine.get_state().result = CombatResult.FLED
        view._maybe_surface_outcome_interjection()
        assert view._interjections_this_fight == 0
        view.on_exit()
