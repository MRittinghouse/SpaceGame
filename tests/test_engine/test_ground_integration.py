"""Tests for ground mission integration in the game engine.

Tests start_ground_mission(), _ensure_ground_*() methods,
state transitions, and _apply_ground_result().
"""

import pygame
import pygame_gui
import pytest

from spacegame.config import GameState
from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    MissionOutcome,
)
from spacegame.models.ground_mapgen import DifficultyTier, MissionType


@pytest.fixture(scope="module")
def _init_pygame():
    """Initialize pygame once for all tests in this module."""
    pygame.init()
    yield
    pygame.quit()


def _make_config(**overrides) -> GroundMissionConfig:
    """Create a test GroundMissionConfig."""
    defaults = {
        "id": "test_ground_01",
        "name": "Test Ground Mission",
        "description": "Infiltrate the test facility.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "commerce_guild",
        "objectives": ["Reach the exit"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=500, xp=25, crew_xp=10),
        "max_crew": 2,
        "seed": 42,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_result(config: GroundMissionConfig = None, **overrides) -> GroundMissionResult:
    """Create a test GroundMissionResult."""
    if config is None:
        config = _make_config()
    defaults = {
        "config": config,
        "outcome": MissionOutcome.SUCCESS,
        "objectives_completed": 1,
        "objectives_total": 1,
        "turns_taken": 20,
        "enemies_defeated": 2,
        "enemies_talked": 1,
        "loot_credits": 150,
        "loot_items": [],
        "progress_percent": 1.0,
        "crew_ids": [],
        "detected": True,
    }
    defaults.update(overrides)
    return GroundMissionResult(**defaults)


def _make_game(_init_pygame):
    """Create a Game instance with a new game initialized."""
    from spacegame.engine.game import Game

    game = Game()
    game.initialize_new_game("TestCaptain")
    game._create_gameplay_views()
    return game


class TestEnsureGroundBriefingView:
    """_ensure_ground_briefing_view creates and registers the briefing view."""

    def test_creates_briefing_view(self, _init_pygame):
        """Briefing view is created with the config."""
        game = _make_game(_init_pygame)
        config = _make_config()
        game._ensure_ground_briefing_view(config)
        assert game.ground_briefing_view is not None

    def test_registers_briefing_state(self, _init_pygame):
        """Briefing view is registered with state manager."""
        game = _make_game(_init_pygame)
        config = _make_config()
        game._ensure_ground_briefing_view(config)
        # Verify we can change to this state without error
        game.state_manager.change_state(GameState.GROUND_BRIEFING)
        assert game.state_manager.current_state == GameState.GROUND_BRIEFING


class TestEnsureGroundResultView:
    """_ensure_ground_result_view creates and registers the result view."""

    def test_creates_result_view(self, _init_pygame):
        """Result view is created with the result."""
        game = _make_game(_init_pygame)
        result = _make_result()
        game._ensure_ground_result_view(result)
        assert game.ground_result_view is not None

    def test_registers_result_state(self, _init_pygame):
        """Result view is registered with state manager."""
        game = _make_game(_init_pygame)
        result = _make_result()
        game._ensure_ground_result_view(result)
        game.state_manager.change_state(GameState.GROUND_RESULT)
        assert game.state_manager.current_state == GameState.GROUND_RESULT


class TestStartGroundMission:
    """start_ground_mission() sets up briefing and transitions."""

    def test_creates_briefing_and_transitions(self, _init_pygame):
        """start_ground_mission creates briefing view and changes state."""
        game = _make_game(_init_pygame)
        config = _make_config()
        game.start_ground_mission(config)
        assert game.ground_briefing_view is not None
        assert game.state_manager.current_state == GameState.GROUND_BRIEFING


class TestApplyGroundResult:
    """_apply_ground_result() modifies player state based on outcome."""

    def test_success_awards_credits(self, _init_pygame):
        """Successful mission awards mission credits + loot."""
        game = _make_game(_init_pygame)
        initial_credits = game.player.credits
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            loot_credits=100,
        )
        game._apply_ground_result(result)
        expected_gain = result.config.rewards.credits + result.loot_credits
        assert game.player.credits == initial_credits + expected_gain

    def test_success_awards_xp(self, _init_pygame):
        """Successful mission awards XP."""
        game = _make_game(_init_pygame)
        initial_xp = game.player.progression.xp
        result = _make_result(outcome=MissionOutcome.SUCCESS)
        game._apply_ground_result(result)
        assert game.player.progression.xp == initial_xp + result.config.rewards.xp

    def test_ghost_bonus_credits(self, _init_pygame):
        """Undetected success awards ghost run bonus."""
        game = _make_game(_init_pygame)
        initial_credits = game.player.credits
        config = _make_config(rewards=GroundMissionRewards(credits=1000, xp=0))
        result = _make_result(
            config=config,
            outcome=MissionOutcome.SUCCESS,
            detected=False,
            loot_credits=0,
        )
        game._apply_ground_result(result)
        # Ghost bonus = 10% of mission credits
        expected = 1000 + int(1000 * 0.10)
        assert game.player.credits == initial_credits + expected

    def test_failure_loses_credits(self, _init_pygame):
        """Failed mission applies credit loss penalty."""
        game = _make_game(_init_pygame)
        game.player.credits = 1000
        result = _make_result(
            outcome=MissionOutcome.DEFEATED,
            progress_percent=0.50,  # Commitment zone
            loot_credits=0,
        )
        game._apply_ground_result(result)
        # Should lose some credits based on consequence curve
        assert game.player.credits < 1000

    def test_extracted_keeps_loot_no_reward(self, _init_pygame):
        """Extraction keeps loot but no mission reward."""
        game = _make_game(_init_pygame)
        initial_credits = game.player.credits
        result = _make_result(
            outcome=MissionOutcome.EXTRACTED,
            loot_credits=200,
        )
        game._apply_ground_result(result)
        assert game.player.credits == initial_credits + 200

    def test_crew_xp_awarded_on_success(self, _init_pygame):
        """Crew members receive XP on successful mission."""
        game = _make_game(_init_pygame)

        # Recruit a crew member (need crew_slots from ship)
        if game.crew_roster and game.player:
            crew_slots = game.player.ship.ship_type.crew_slots
            game.crew_roster.recruit("elena_reeves", crew_slots)
            initial_xp = 0
            for t, state in game.crew_roster.get_recruited_members():
                if t.id == "elena_reeves":
                    initial_xp = state.get("xp", 0)
                    break

            result = _make_result(
                outcome=MissionOutcome.SUCCESS,
                crew_ids=["elena_reeves"],
            )
            config_crew_xp = result.config.rewards.crew_xp
            game._apply_ground_result(result)

            for t, state in game.crew_roster.get_recruited_members():
                if t.id == "elena_reeves":
                    assert state.get("xp", 0) >= initial_xp + config_crew_xp


class TestViewVarsInitialized:
    """Ground view variables are initialized in Game.__init__."""

    def test_ground_view_vars_exist(self, _init_pygame):
        """Game has ground view references initialized to None."""
        game = _make_game(_init_pygame)
        assert hasattr(game, "ground_briefing_view")
        assert hasattr(game, "ground_exploration_view")
        assert hasattr(game, "ground_result_view")
        assert game.ground_briefing_view is None
        assert game.ground_exploration_view is None
        assert game.ground_result_view is None


class TestGroundViewsResetOnNewGame:
    """Ground view references are reset in _create_gameplay_views."""

    def test_ground_views_reset(self, _init_pygame):
        """Ground views are set to None when gameplay views are recreated."""
        game = _make_game(_init_pygame)
        game.ground_briefing_view = "something"
        game.ground_result_view = "something"
        game._create_gameplay_views()
        assert game.ground_briefing_view is None
        assert game.ground_result_view is None


class TestGroundContractManagerIntegration:
    """GroundContractManager wired into game engine."""

    def test_manager_initialized_on_new_game(self, _init_pygame):
        """New game creates an empty GroundContractManager."""
        game = _make_game(_init_pygame)
        assert game.ground_contract_manager is not None
        assert len(game.ground_contract_manager.active_contracts) == 0

    def test_get_ground_contracts_generates(self, _init_pygame):
        """get_ground_contracts generates contracts at current system."""
        game = _make_game(_init_pygame)
        contracts = game.get_ground_contracts()
        assert len(contracts) >= 1
        for c in contracts:
            assert c.system_id == game.player.current_system_id

    def test_get_ground_contracts_idempotent(self, _init_pygame):
        """Calling get_ground_contracts twice returns the same contracts."""
        game = _make_game(_init_pygame)
        first = game.get_ground_contracts()
        second = game.get_ground_contracts()
        assert len(first) == len(second)
        assert {c.id for c in first} == {c.id for c in second}

    def test_contract_completion_awards_bonus(self, _init_pygame):
        """Completing a contract via _apply_ground_result awards bonus credits."""
        game = _make_game(_init_pygame)
        contracts = game.get_ground_contracts()
        contract = contracts[0]

        initial_credits = game.player.credits
        config = contract.config
        result = _make_result(
            config=config,
            outcome=MissionOutcome.SUCCESS,
            loot_credits=0,
            detected=True,
        )
        game._apply_ground_result(result)

        # Should get mission reward + contract bonus
        expected_gain = config.rewards.credits + contract.bonus_credits
        assert game.player.credits == initial_credits + expected_gain

    def test_advance_day_prunes_expired(self, _init_pygame):
        """Day advancement removes expired contracts."""
        game = _make_game(_init_pygame)
        game.get_ground_contracts()
        assert len(game.ground_contract_manager.active_contracts) > 0
        # Advance far into the future
        game.ground_contract_manager.advance_day(game_day=9999)
        assert len(game.ground_contract_manager.active_contracts) == 0

    def test_save_load_preserves_contracts(self, _init_pygame):
        """Ground contract state survives save/load cycle."""
        game = _make_game(_init_pygame)
        contracts = game.get_ground_contracts()
        contract_ids = {c.id for c in contracts}
        completed_id = contracts[0].id
        game.ground_contract_manager.complete_contract(completed_id)

        # Sync state to player dict
        game.player.ground_contract_state = game.ground_contract_manager.to_dict()

        # Simulate restore
        from spacegame.models.ground_contracts import GroundContractManager

        restored = GroundContractManager.from_dict(game.player.ground_contract_state)
        restored_ids = {c.id for c in restored.active_contracts}
        assert restored_ids == contract_ids
        assert restored.completed_count == 1


class TestBuildGroundMap:
    """_build_ground_map uses campaign maps when available."""

    def test_procedural_fallback(self, _init_pygame):
        """Falls back to procedural generation when no campaign map exists."""
        game = _make_game(_init_pygame)
        config = _make_config(id="no_campaign_map_here")
        result = game._build_ground_map(config)
        assert result.ground_map.width > 0
        assert len(result.enemies) >= 0

    def test_uses_campaign_map(self, _init_pygame):
        """Uses campaign map data when config ID matches."""
        game = _make_game(_init_pygame)
        # Inject a campaign map into the data loader
        game.data_loader.campaign_ground_maps["test_campaign"] = {
            "id": "test_campaign",
            "name": "Test Campaign Map",
            "width": 10,
            "height": 8,
            "mission_type": "infiltration",
            "difficulty": "low",
            "faction_id": "merchants_guild",
            "tiles": [
                ["W"] * 10,
                ["W", "E", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "X", "W"],
                ["W"] * 10,
            ],
            "entrance": [1, 1],
            "exit": [8, 6],
            "enemies": [],
        }
        config = _make_config(id="test_campaign")
        result = game._build_ground_map(config)
        # Campaign map has fixed dimensions
        assert result.ground_map.width == 10
        assert result.ground_map.height == 8
