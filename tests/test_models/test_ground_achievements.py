"""Tests for ground exploration achievements and player stat tracking.

Tests ground-specific statistics on Player, achievement threshold triggers,
save/load round-trips for new stats, and ground achievement data loading.
"""

from spacegame.models.achievement import Achievement
from spacegame.achievement_manager import AchievementManager
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    ship_type = _make_ship_type()
    ship = Ship(ship_type=ship_type, current_fuel=100)
    return Player(
        name="Test",
        credits=5000,
        current_system_id="nexus_prime",
        ship=ship,
    )


def _make_achievement(
    achievement_id: str = "test_ach",
    stat_key: str = "trades_completed",
    threshold: int = 1,
    reward_type: str = "xp",
    reward_value: int = 50,
) -> Achievement:
    return Achievement(
        id=achievement_id,
        name="Test Achievement",
        description="A test achievement",
        category="ground",
        stat_key=stat_key,
        threshold=threshold,
        reward_type=reward_type,
        reward_value=reward_value,
    )


# === Player Ground Statistics ===


class TestPlayerGroundStats:
    """Player should have ground exploration stat fields."""

    def test_ground_missions_completed_default(self) -> None:
        """Player should have ground_missions_completed defaulting to 0."""
        player = _make_player()
        assert player.ground_missions_completed == 0

    def test_ground_missions_failed_default(self) -> None:
        """Player should have ground_missions_failed defaulting to 0."""
        player = _make_player()
        assert player.ground_missions_failed == 0

    def test_ground_enemies_defeated_default(self) -> None:
        """Player should have ground_enemies_defeated defaulting to 0."""
        player = _make_player()
        assert player.ground_enemies_defeated == 0

    def test_ground_enemies_talked_default(self) -> None:
        """Player should have ground_enemies_talked defaulting to 0."""
        player = _make_player()
        assert player.ground_enemies_talked == 0

    def test_ground_tiles_explored_default(self) -> None:
        """Player should have ground_tiles_explored defaulting to 0."""
        player = _make_player()
        assert player.ground_tiles_explored == 0

    def test_ground_undetected_completions_default(self) -> None:
        """Player should have ground_undetected_completions defaulting to 0."""
        player = _make_player()
        assert player.ground_undetected_completions == 0

    def test_ground_stats_mutable(self) -> None:
        """Ground stats should be incrementable."""
        player = _make_player()
        player.ground_missions_completed = 5
        player.ground_enemies_defeated = 12
        player.ground_tiles_explored = 300
        assert player.ground_missions_completed == 5
        assert player.ground_enemies_defeated == 12
        assert player.ground_tiles_explored == 300

    def test_ground_stats_in_statistics(self) -> None:
        """Ground stats should appear in get_statistics() output."""
        player = _make_player()
        player.ground_missions_completed = 3
        player.ground_enemies_defeated = 8
        stats = player.get_statistics()
        assert stats["ground_missions_completed"] == 3
        assert stats["ground_enemies_defeated"] == 8


# === Ground Stats Serialization ===


class TestGroundStatsSerialization:
    """Ground stats should survive save/load round-trip."""

    def test_ground_stats_serialize_roundtrip(self) -> None:
        """All ground stats should survive save/load cycle."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()
        player.ground_missions_completed = 7
        player.ground_missions_failed = 2
        player.ground_enemies_defeated = 25
        player.ground_enemies_talked = 15
        player.ground_tiles_explored = 500
        player.ground_undetected_completions = 3

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.ground_missions_completed == 7
            assert p2.ground_missions_failed == 2
            assert p2.ground_enemies_defeated == 25
            assert p2.ground_enemies_talked == 15
            assert p2.ground_tiles_explored == 500
            assert p2.ground_undetected_completions == 3

    def test_ground_stats_backward_compatible(self) -> None:
        """Old saves without ground stats should load with defaults."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.ground_missions_completed == 0
            assert p2.ground_missions_failed == 0
            assert p2.ground_enemies_defeated == 0
            assert p2.ground_enemies_talked == 0
            assert p2.ground_tiles_explored == 0
            assert p2.ground_undetected_completions == 0


# === Ground Achievement Triggers ===


class TestGroundAchievementTriggers:
    """Ground achievements should trigger at correct thresholds."""

    def test_first_mission_triggers(self) -> None:
        """ground_first_mission should unlock at 1 completion."""
        player = _make_player()
        ach = _make_achievement(
            "ground_first_mission",
            stat_key="ground_missions_completed",
            threshold=1,
        )
        manager = AchievementManager([ach])

        assert len(manager.check_achievements(player)) == 0
        player.ground_missions_completed = 1
        assert len(manager.check_achievements(player)) == 1

    def test_ghost_run_triggers(self) -> None:
        """ground_ghost_run should unlock at 1 undetected completion."""
        player = _make_player()
        ach = _make_achievement(
            "ground_ghost_run",
            stat_key="ground_undetected_completions",
            threshold=1,
        )
        manager = AchievementManager([ach])

        assert len(manager.check_achievements(player)) == 0
        player.ground_undetected_completions = 1
        assert len(manager.check_achievements(player)) == 1

    def test_veteran_triggers(self) -> None:
        """ground_veteran should unlock at 10 completions."""
        player = _make_player()
        ach = _make_achievement(
            "ground_veteran",
            stat_key="ground_missions_completed",
            threshold=10,
        )
        manager = AchievementManager([ach])

        player.ground_missions_completed = 9
        assert len(manager.check_achievements(player)) == 0
        player.ground_missions_completed = 10
        assert len(manager.check_achievements(player)) == 1

    def test_scrapper_triggers(self) -> None:
        """ground_scrapper should unlock at 25 enemies defeated."""
        player = _make_player()
        ach = _make_achievement(
            "ground_scrapper",
            stat_key="ground_enemies_defeated",
            threshold=25,
        )
        manager = AchievementManager([ach])

        player.ground_enemies_defeated = 24
        assert len(manager.check_achievements(player)) == 0
        player.ground_enemies_defeated = 25
        assert len(manager.check_achievements(player)) == 1

    def test_silver_tongue_triggers(self) -> None:
        """ground_silver_tongue should unlock at 15 enemies talked past."""
        player = _make_player()
        ach = _make_achievement(
            "ground_silver_tongue",
            stat_key="ground_enemies_talked",
            threshold=15,
        )
        manager = AchievementManager([ach])

        player.ground_enemies_talked = 14
        assert len(manager.check_achievements(player)) == 0
        player.ground_enemies_talked = 15
        assert len(manager.check_achievements(player)) == 1

    def test_cartographer_triggers(self) -> None:
        """ground_explorer should unlock at 500 tiles explored."""
        player = _make_player()
        ach = _make_achievement(
            "ground_explorer",
            stat_key="ground_tiles_explored",
            threshold=500,
        )
        manager = AchievementManager([ach])

        player.ground_tiles_explored = 499
        assert len(manager.check_achievements(player)) == 0
        player.ground_tiles_explored = 500
        assert len(manager.check_achievements(player)) == 1

    def test_deep_cover_triggers(self) -> None:
        """ground_campaign_all should unlock at 3 campaign completions."""
        player = _make_player()
        ach = _make_achievement(
            "ground_campaign_all",
            stat_key="ground_campaign_missions_completed",
            threshold=3,
        )
        manager = AchievementManager([ach])

        player.ground_campaign_missions_completed = 2
        assert len(manager.check_achievements(player)) == 0
        player.ground_campaign_missions_completed = 3
        assert len(manager.check_achievements(player)) == 1


# === Ground Achievement Data Loading ===


class TestGroundAchievementData:
    """Ground achievements should load from achievements.json."""

    def test_total_achievement_count(self) -> None:
        """Total achievement count = 62 prior + 4 SA-B2 + 1 SA-B4 = 67."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        assert len(dl.achievements) == 67

    def test_ground_category_achievements_loaded(self) -> None:
        """Should have 7 ground-category achievements."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ground_achs = [a for a in dl.achievements if a.category == "ground"]
        assert len(ground_achs) == 7

    def test_ground_achievement_ids(self) -> None:
        """All expected ground achievement IDs should exist."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ids = {a.id for a in dl.achievements}
        expected = {
            "ground_first_mission",
            "ground_ghost_run",
            "ground_veteran",
            "ground_scrapper",
            "ground_silver_tongue",
            "ground_explorer",
            "ground_campaign_all",
        }
        assert expected.issubset(ids), f"Missing: {expected - ids}"

    def test_ground_achievement_rewards_reasonable(self) -> None:
        """Ground achievement rewards should be reasonable values."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ground_achs = [a for a in dl.achievements if a.category == "ground"]
        for ach in ground_achs:
            assert ach.reward_type in ("xp", "credits", "skill_point")
            assert ach.reward_value > 0
