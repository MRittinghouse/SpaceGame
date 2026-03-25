"""Tests for ground mission stat tracking in _apply_ground_result."""

from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    MissionOutcome,
)
from spacegame.models.ground_mapgen import MissionType, DifficultyTier
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


def _make_ship_type() -> ShipType:
    return ShipType(
        id="test",
        name="Test",
        ship_class="starter",
        description="",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=5,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=2,
        special_abilities=[],
        availability="common",
    )


def _make_player() -> Player:
    return Player(
        name="Tester",
        credits=1000,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


def _make_config(is_campaign: bool = False) -> GroundMissionConfig:
    return GroundMissionConfig(
        id="test_mission",
        name="Test Mission",
        description="A test mission",
        mission_type=MissionType.INFILTRATION,
        difficulty=DifficultyTier.LOW,
        faction_id="",
        objectives=["obj1"],
        intel_hints=[],
        rewards=GroundMissionRewards(credits=100, xp=50),
        campaign_mission_id="camp_1" if is_campaign else None,
    )


def _make_result(
    outcome: MissionOutcome = MissionOutcome.SUCCESS,
    enemies_defeated: int = 3,
    enemies_talked: int = 1,
    detected: bool = False,
    is_campaign: bool = False,
    loot_credits: int = 50,
) -> GroundMissionResult:
    return GroundMissionResult(
        config=_make_config(is_campaign=is_campaign),
        outcome=outcome,
        objectives_completed=3,
        objectives_total=3,
        turns_taken=10,
        enemies_defeated=enemies_defeated,
        enemies_talked=enemies_talked,
        loot_credits=loot_credits,
        loot_items=[],
        progress_percent=1.0 if outcome == MissionOutcome.SUCCESS else 0.5,
        crew_ids=[],
        detected=detected,
    )


class TestGroundResultProperties:
    """Verify GroundMissionResult properties used for stat tracking."""

    def test_ghost_run_success_undetected(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=False)
        assert result.is_ghost_run is True

    def test_not_ghost_run_if_detected(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=True)
        assert result.is_ghost_run is False

    def test_not_ghost_run_on_failure(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, detected=False)
        assert result.is_ghost_run is False

    def test_campaign_flag(self) -> None:
        result = _make_result(is_campaign=True)
        assert result.config.is_campaign is True

    def test_not_campaign_flag(self) -> None:
        result = _make_result(is_campaign=False)
        assert result.config.is_campaign is False

    def test_failure_outcome(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED)
        assert result.outcome.is_failure is True

    def test_extraction_not_failure(self) -> None:
        result = _make_result(outcome=MissionOutcome.EXTRACTED)
        assert not result.outcome.is_failure


class TestGroundStatsIntegration:
    """Integration: simulate the stat-tracking that _apply_ground_result should do."""

    def _apply_ground_stats(self, player: Player, result: GroundMissionResult) -> None:
        """The stat tracking logic that game.py should have.

        This mirrors what we expect _apply_ground_result to do.
        """
        player.ground_enemies_defeated += result.enemies_defeated
        player.ground_enemies_talked += result.enemies_talked

        if result.outcome == MissionOutcome.SUCCESS:
            player.ground_missions_completed += 1
            if result.is_ghost_run:
                player.ground_undetected_completions += 1
            if result.config.is_campaign:
                player.ground_campaign_missions_completed += 1
        elif result.outcome.is_failure:
            player.ground_missions_failed += 1

    def test_success_increments_all_stats(self) -> None:
        player = _make_player()
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            enemies_defeated=4,
            enemies_talked=2,
            detected=False,
            is_campaign=True,
        )

        assert player.ground_missions_completed == 0

        self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 1
        assert player.ground_missions_failed == 0
        assert player.ground_enemies_defeated == 4
        assert player.ground_enemies_talked == 2
        assert player.ground_undetected_completions == 1
        assert player.ground_campaign_missions_completed == 1

    def test_failure_increments_failed_and_enemies(self) -> None:
        player = _make_player()
        result = _make_result(
            outcome=MissionOutcome.DEFEATED,
            enemies_defeated=2,
            enemies_talked=0,
        )

        self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 0
        assert player.ground_missions_failed == 1
        assert player.ground_enemies_defeated == 2
        assert player.ground_undetected_completions == 0

    def test_extraction_no_success_or_failure(self) -> None:
        player = _make_player()
        result = _make_result(
            outcome=MissionOutcome.EXTRACTED,
            enemies_defeated=1,
            enemies_talked=1,
        )

        self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 0
        assert player.ground_missions_failed == 0
        assert player.ground_enemies_defeated == 1
        assert player.ground_enemies_talked == 1

    def test_detected_success_no_ghost_credit(self) -> None:
        player = _make_player()
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            detected=True,
        )

        self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 1
        assert player.ground_undetected_completions == 0

    def test_non_campaign_no_campaign_stat(self) -> None:
        player = _make_player()
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            is_campaign=False,
        )

        self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 1
        assert player.ground_campaign_missions_completed == 0

    def test_stats_accumulate_across_missions(self) -> None:
        player = _make_player()

        for _ in range(3):
            result = _make_result(enemies_defeated=2, enemies_talked=1)
            self._apply_ground_stats(player, result)

        assert player.ground_missions_completed == 3
        assert player.ground_enemies_defeated == 6
        assert player.ground_enemies_talked == 3
