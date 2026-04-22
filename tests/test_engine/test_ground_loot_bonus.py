"""Tests for ground loot bonus skill application."""

from unittest.mock import MagicMock, patch

import pytest

from spacegame.models.progression import PlayerProgression


class TestGroundLootBonusApplication:
    """Verify ground_loot_bonus skill modifies loot credits in _apply_ground_result."""

    def _make_game_with_loot_bonus(self, bonus_level: int = 0) -> "Game":
        """Create a minimal Game with controllable ground_loot_bonus level."""
        from spacegame.engine.game import Game

        with patch.object(Game, "__init__", lambda self: None):
            game = Game()

        game.player = MagicMock()
        game.player.credits = 1000
        game.player.progression = PlayerProgression()
        game.player.faction_reputation = MagicMock()
        game.crew_roster = None
        game.ground_contract_manager = None
        game.ambient_dialogue = None
        game._mission_notifications = []

        # Level up combat_scavenger to desired level
        if bonus_level > 0:
            # Prerequisite chain: weapon_specialization -> ground_veteran -> combat_scavenger
            game.player.progression.skill_points = 20
            game.player.progression.level_up_skill("weapon_specialization")
            game.player.progression.level_up_skill("ground_veteran")
            for _ in range(bonus_level):
                ok, msg = game.player.progression.level_up_skill("combat_scavenger")
                assert ok, f"Failed to level combat_scavenger: {msg}"

        return game

    def _make_result(
        self,
        outcome_name: str,
        loot_credits: int = 100,
        reward_credits: int = 200,
        reward_xp: int = 50,
        crew_xp: int = 10,
    ) -> MagicMock:
        """Create a mock GroundMissionResult."""
        from spacegame.models.ground_mission import MissionOutcome

        result = MagicMock()
        result.outcome = MissionOutcome(outcome_name)
        result.loot_credits = loot_credits
        result.is_ghost_run = False
        result.crew_ids = []
        result.config.rewards.credits = reward_credits
        result.config.rewards.xp = reward_xp
        result.config.rewards.crew_xp = crew_xp
        result.config.rewards.reputation = {}
        result.config.id = "test_mission"
        return result

    def test_no_bonus_no_change(self) -> None:
        """Without the skill, loot credits are unmodified."""
        game = self._make_game_with_loot_bonus(0)
        result = self._make_result("success", loot_credits=100, reward_credits=200)
        game._apply_ground_result(result)
        # 1000 + 200 (reward) + 100 (loot) = 1300
        assert game.player.credits == 1300

    def test_level_1_adds_15_percent(self) -> None:
        """Level 1 combat_scavenger adds 15% to loot credits on success."""
        game = self._make_game_with_loot_bonus(1)
        result = self._make_result("success", loot_credits=100, reward_credits=200)
        game._apply_ground_result(result)
        # loot: 100 * 1.15 = 115, total = 1000 + 200 + 115 = 1315
        assert game.player.credits == 1315

    def test_level_2_adds_30_percent(self) -> None:
        """Level 2 combat_scavenger adds 30% to loot credits on success."""
        game = self._make_game_with_loot_bonus(2)
        result = self._make_result("success", loot_credits=100, reward_credits=200)
        game._apply_ground_result(result)
        # loot: 100 * 1.30 = 130, total = 1000 + 200 + 130 = 1330
        assert game.player.credits == 1330

    def test_bonus_applies_to_extraction(self) -> None:
        """Loot bonus applies when player extracts (keeps loot, no reward)."""
        game = self._make_game_with_loot_bonus(1)
        result = self._make_result("extracted", loot_credits=100)
        game._apply_ground_result(result)
        # 1000 + 115 (100 * 1.15)
        assert game.player.credits == 1115

    def test_bonus_applies_to_failure_partial_loot(self) -> None:
        """Loot bonus applies to partial loot kept on failure."""
        game = self._make_game_with_loot_bonus(1)
        result = self._make_result("defeated", loot_credits=200)
        result.calculate_penalties.return_value = {
            "credit_loss_percent": 10,
            "loot_kept_percent": 50,
            "xp_penalty": 0,
        }
        game._apply_ground_result(result)
        # credit_loss: 1000 * 10% = 100
        # kept_loot base: 200 * 50% = 100, with 15% bonus: 115
        # 1000 - 100 + 115 = 1015
        assert game.player.credits == 1015

    def test_zero_loot_unaffected(self) -> None:
        """Bonus on zero loot still results in zero."""
        game = self._make_game_with_loot_bonus(2)
        result = self._make_result("success", loot_credits=0, reward_credits=200)
        game._apply_ground_result(result)
        assert game.player.credits == 1200

    def test_crew_bonus_stacks_with_skill(self) -> None:
        """Crew ground_loot_bonus stacks additively with skill bonus."""
        game = self._make_game_with_loot_bonus(1)
        game.crew_roster = MagicMock()
        game.crew_roster.get_bonus.return_value = 0.10  # 10% from crew
        result = self._make_result("success", loot_credits=100, reward_credits=200)
        game._apply_ground_result(result)
        # skill: 0.15 + crew: 0.10 = 0.25 total
        # loot: 100 * 1.25 = 125, total = 1000 + 200 + 125 = 1325
        assert game.player.credits == 1325
