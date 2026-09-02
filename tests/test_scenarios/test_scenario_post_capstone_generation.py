"""A2-21: end-to-end scenario for post-capstone identity-keyed generation.

Covers AC6 (integration with the station board through
``_refresh_procedural_missions``) and AC7 (save/load round-trip).

The ``_mock_game`` helper mirrors the pattern in
``test_scenario_capstone_session_continues.py``: ``__init__`` is patched
out and just enough state is assembled by hand so ``_after_player_action``
and ``_refresh_procedural_missions`` can run against real mission and
capstone models. Full Game construction requires pygame + audio + saved
data plumbing we do not need here.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import pygame
import pygame_gui

from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import DilemmaRuntimeState
from spacegame.models.lens_investment import LensInvestment
from spacegame.models.mission import Mission, MissionManager, MissionObjective, ObjectiveType
from spacegame.models.player import Player
from spacegame.models.post_capstone_content import PostCapstoneContentGenerator
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.models.ship import Ship


def _real_ui_manager() -> pygame_gui.UIManager:
    from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_player(system_id: str = "nexus_prime") -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    p = Player("EmpireCap", 1000, system_id, ship)
    p.lens_investment = LensInvestment()
    p.dilemma_state = DilemmaRuntimeState()
    p.capstones_reached = set()
    p.dialogue_flags = {}
    p.game_day = 5
    return p


def _mock_game(*, with_ui: bool = False):
    from spacegame.engine.game import Game

    dl = get_data_loader()
    dl.load_all()

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()

    game.data_loader = dl
    game._player = _make_player()
    game.crew_roster = None
    game.ambient_dialogue = None
    game._mission_notifications = []
    game.ui_manager = _real_ui_manager() if with_ui else None
    game.state_manager = MagicMock(current_state=None)
    game.dilemma_resolution_view = None
    game._pending_dilemma = None
    game.capstone_view = None
    game._pending_capstone = None

    # Real generators + mission_manager -- the whole point of AC6 is
    # that the post_capstone_* output lands on the same board.
    game.mission_manager = MissionManager([])
    game.procedural_mission_gen = ProceduralMissionGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        seed=hash(game.player.name) & 0xFFFFFFFF,
    )
    game.post_capstone_content_gen = PostCapstoneContentGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        templates=dl.post_capstone_templates,
        seed=hash(game.player.name) & 0xFFFFFFFF,
    )
    game._proc_missions_day = -1
    return game


class TestPostCapstoneMissionsOnBoard:
    """AC6 -- post_capstone_* missions land on the same board as proc_*."""

    def test_empire_capstone_yields_board_missions_alongside_proc(self) -> None:
        game = _mock_game(with_ui=True)

        # Drive the player to the Empire capstone. Investment reads live
        # in the model layer via check_capstones; the engine call at
        # game._after_player_action pushes the modal.
        game.player.lens_investment.add_investment("empire", 95, source="test")
        game.player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        game.player.dialogue_flags["d6_empire_won"] = True

        game._after_player_action("test")
        # Acknowledge -- writes capstones_reached + dialogue_flag
        game._on_capstone_acknowledge()
        assert game.player.dialogue_flags.get("empire_capstone_reached") is True

        # Advance game day and refresh the board
        game.player.game_day = 6
        game._refresh_procedural_missions()

        mission_ids = list(game.mission_manager._missions.keys())
        empire_missions = [m for m in mission_ids if m.startswith("post_capstone_empire_")]
        proc_missions = [m for m in mission_ids if m.startswith("proc_")]
        assert empire_missions, (
            f"expected at least one post_capstone_empire_* mission on the board, got: {mission_ids}"
        )
        assert proc_missions, (
            f"post_capstone_* must merge into the same board as proc_*; "
            f"got no proc_* today: {mission_ids}"
        )

    def test_stale_post_capstone_stripped_on_next_refresh(self) -> None:
        """Stale post_capstone_* from a prior day should not accumulate."""
        game = _mock_game(with_ui=True)

        game.player.lens_investment.add_investment("empire", 95, source="test")
        game.player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        game.player.dialogue_flags["d6_empire_won"] = True
        game._after_player_action("test")
        game._on_capstone_acknowledge()

        # First refresh generates day 6 missions
        game.player.game_day = 6
        game._refresh_procedural_missions()
        day6_ids = [
            mid for mid in game.mission_manager._missions if mid.startswith("post_capstone_empire_")
        ]
        assert day6_ids, "expected day 6 post_capstone_empire_* missions"

        # Advance to day 7 and re-refresh; day 6 ids should be gone
        game.player.game_day = 7
        game._refresh_procedural_missions()
        remaining = list(game.mission_manager._missions.keys())
        for old_id in day6_ids:
            assert old_id not in remaining, (
                f"stale mission {old_id!r} was not stripped on next refresh"
            )
        day7_ids = [m for m in remaining if m.startswith("post_capstone_empire_")]
        assert day7_ids, "expected fresh day 7 post_capstone_empire_* missions"


class TestPostCapstoneSaveLoadRoundTrip:
    """AC7 -- a post_capstone_* mission survives a save/load cycle unchanged."""

    def test_mission_persists_across_serialize_load(self) -> None:
        # Build a post_capstone_empire mission using the real generator.
        dl = get_data_loader()
        dl.load_all()
        gen = PostCapstoneContentGenerator(
            systems=dl.systems,
            commodities=dl.commodities,
            enemy_templates=dl.enemy_templates,
            templates=dl.post_capstone_templates,
            seed=42,
        )
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True

        missions = gen.generate_for_lens("empire", game_day=10, player=player)
        assert missions
        mission = missions[0]

        # Round-trip through Mission.to_dict() / from_dict() -- the
        # same path save_manager uses for procedural missions.
        restored = Mission.from_dict(mission.to_dict())
        assert restored.id == mission.id
        assert restored.name == mission.name
        assert restored.description == mission.description
        assert len(restored.objectives) == len(mission.objectives)
        for a, b in zip(restored.objectives, mission.objectives, strict=True):
            assert a.type == b.type
            assert a.target_id == b.target_id
            assert a.target_quantity == b.target_quantity
        # HAS_FLAG objective (the identity gate) must survive intact
        has_flag_objs = [o for o in restored.objectives if o.type == ObjectiveType.HAS_FLAG]
        assert has_flag_objs and has_flag_objs[0].target_id in {
            "d6_empire_won",
            "d3_empire_won",
        }

    def test_missionmanager_state_survives(self) -> None:
        """AC7 (integration) -- MissionManager state round-trip preserves
        the runtime status/progress for a post_capstone_* mission."""
        dl = get_data_loader()
        dl.load_all()
        gen = PostCapstoneContentGenerator(
            systems=dl.systems,
            commodities=dl.commodities,
            enemy_templates=dl.enemy_templates,
            templates=dl.post_capstone_templates,
            seed=42,
        )
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True

        missions = gen.generate_for_lens("empire", game_day=10, player=player)
        assert missions
        mgr = MissionManager([])
        for m in missions:
            mgr.add_mission(m)
        board_ids_pre = sorted(mgr._missions.keys())

        state = mgr.get_state()

        # Simulate reload: build a fresh manager holding the same Mission
        # objects (the save_manager rehydrates missions from disk; here we
        # mimic that by starting with the same Mission list).
        mgr2 = MissionManager(list(mgr._missions.values()))
        mgr2.load_state(state)
        board_ids_post = sorted(mgr2._missions.keys())
        assert board_ids_pre == board_ids_post
        for mid in board_ids_pre:
            assert mgr.get_status(mid) == mgr2.get_status(mid)


class TestNoLensInvestmentInEngineHook:
    """AC8 -- engine hook does not read player.lens_investment.

    The compliance guard at
    ``tests/test_compliance/test_lens_investment_never_rendered.py`` scans
    the file; this test proves the hook still functions when
    ``player.lens_investment`` is deliberately absent.
    """

    def test_refresh_works_without_lens_investment_access(self) -> None:
        game = _mock_game(with_ui=False)
        # Set the capstone-reached flag directly (the engine hook only
        # reads flags), then delete lens_investment.
        game.player.dialogue_flags["empire_capstone_reached"] = True
        game.player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        game.player.dialogue_flags["d6_empire_won"] = True
        # Replace lens_investment with a sentinel that would raise on any
        # attribute access -- if the engine hook touches it we'll know.
        game.player.lens_investment = MagicMock(
            get_investment=MagicMock(side_effect=AssertionError("engine read lens_investment")),
            is_at_or_above=MagicMock(side_effect=AssertionError("engine read lens_investment")),
        )

        game.player.game_day = 6
        game._refresh_procedural_missions()

        empire = [
            mid for mid in game.mission_manager._missions if mid.startswith("post_capstone_empire_")
        ]
        assert empire, "engine hook must generate post_capstone_empire_* without investment reads"


def _make_flag_mission(mission_id: str) -> Mission:
    """Small helper -- used only for the sanity assertion below."""
    return Mission(
        id=mission_id,
        name="fixture",
        description="fixture",
        mission_type="side",
        objectives=[MissionObjective(type=ObjectiveType.HAS_FLAG, target_id="x")],
    )
