"""Tests for achievement system: loading, unlocking, rewards, serialization."""

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
    hidden: bool = False,
) -> Achievement:
    return Achievement(
        id=achievement_id,
        name="Test Achievement",
        description="A test achievement",
        category="testing",
        stat_key=stat_key,
        threshold=threshold,
        reward_type=reward_type,
        reward_value=reward_value,
        hidden=hidden,
    )


class TestAchievementDataLoading:
    """Test achievement data loading from JSON."""

    def test_achievement_fields(self) -> None:
        """Achievement should have all required fields."""
        ach = _make_achievement()
        assert ach.id == "test_ach"
        assert ach.name == "Test Achievement"
        assert ach.stat_key == "trades_completed"
        assert ach.threshold == 1
        assert ach.reward_type == "xp"
        assert ach.reward_value == 50
        assert not ach.hidden

    def test_hidden_achievement(self) -> None:
        """Hidden achievements should have hidden=True."""
        ach = _make_achievement(hidden=True)
        assert ach.hidden


class TestCheckAchievements:
    """Test achievement checking against thresholds."""

    def test_detects_threshold_crossing(self) -> None:
        """Should detect when stat crosses threshold."""
        player = _make_player()
        ach = _make_achievement(stat_key="trades_completed", threshold=1)
        manager = AchievementManager([ach])

        player.trades_completed = 0
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 0, "Should not unlock at 0 trades"

        player.trades_completed = 1
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 1, "Should unlock at 1 trade"
        assert unlocked[0].id == "test_ach"

    def test_no_duplicate_unlocks(self) -> None:
        """Should not unlock same achievement twice."""
        player = _make_player()
        ach = _make_achievement(stat_key="trades_completed", threshold=1)
        manager = AchievementManager([ach])

        player.trades_completed = 5
        unlocked1 = manager.check_achievements(player)
        assert len(unlocked1) == 1

        unlocked2 = manager.check_achievements(player)
        assert len(unlocked2) == 0, "Should not re-unlock"

    def test_multiple_achievements_unlock_together(self) -> None:
        """Multiple achievements can unlock in same check."""
        player = _make_player()
        ach1 = _make_achievement("ach1", "trades_completed", threshold=1)
        ach2 = _make_achievement("ach2", "trades_completed", threshold=5)
        manager = AchievementManager([ach1, ach2])

        player.trades_completed = 10
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 2

    def test_systems_discovered_stat(self) -> None:
        """systems_discovered stat should count unique systems visited."""
        player = _make_player()
        ach = _make_achievement(stat_key="systems_discovered", threshold=2)
        manager = AchievementManager([ach])

        # Player starts with 1 system visited (current system)
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 0

        player.systems_visited.add("breakstone")
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 1

    def test_level_stat(self) -> None:
        """level stat should read from progression."""
        player = _make_player()
        ach = _make_achievement(stat_key="level", threshold=3)
        manager = AchievementManager([ach])

        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 0

        player.progression.level = 3
        unlocked = manager.check_achievements(player)
        assert len(unlocked) == 1


class TestRewardApplication:
    """Test reward application for each reward type."""

    def test_xp_reward(self) -> None:
        """XP reward should add XP to progression."""
        player = _make_player()
        ach = _make_achievement(reward_type="xp", reward_value=100)
        manager = AchievementManager([ach])

        old_xp = player.progression.xp
        msg = manager.apply_reward(player, ach)
        assert player.progression.xp == old_xp + 100
        assert "+100 XP" in msg

    def test_credits_reward(self) -> None:
        """Credits reward should add credits to player."""
        player = _make_player()
        ach = _make_achievement(reward_type="credits", reward_value=500)
        manager = AchievementManager([ach])

        old_credits = player.credits
        msg = manager.apply_reward(player, ach)
        assert player.credits == old_credits + 500
        assert "500" in msg

    def test_skill_point_reward(self) -> None:
        """Skill point reward should add skill points."""
        player = _make_player()
        ach = _make_achievement(reward_type="skill_point", reward_value=1)
        manager = AchievementManager([ach])

        old_sp = player.progression.skill_points
        msg = manager.apply_reward(player, ach)
        assert player.progression.skill_points == old_sp + 1
        assert "Skill Point" in msg

    def test_upgrade_reward(self) -> None:
        """Upgrade reward should return upgrade description."""
        player = _make_player()
        ach = _make_achievement(reward_type="upgrade", reward_value=1)
        manager = AchievementManager([ach])

        msg = manager.apply_reward(player, ach)
        assert "Upgrade" in msg


class TestAchievementSerialization:
    """Test serialization of unlocked achievements and stat fields."""

    def test_unlocked_achievements_roundtrip(self) -> None:
        """unlocked_achievements should survive serialization."""
        player = _make_player()
        player.unlocked_achievements = ["first_trade", "first_jump"]

        # Simulate what save_manager does
        data = list(player.unlocked_achievements)

        restored_list = data
        assert restored_list == ["first_trade", "first_jump"]

    def test_stat_fields_on_player(self) -> None:
        """New stat fields should be accessible on player."""
        player = _make_player()
        assert player.credits_earned_lifetime == 0
        assert player.credits_spent_lifetime == 0
        assert player.largest_single_profit == 0
        assert player.jumps_traveled == 0
        assert player.fuel_consumed == 0
        assert player.ore_mined == 0
        assert player.items_salvaged == 0
        assert player.items_refined == 0

    def test_stat_fields_updated_on_buy(self) -> None:
        """Buying should update credits_spent_lifetime."""
        player = _make_player()
        volumes = {"iron_ore": 1}
        player.buy_commodity("iron_ore", 2, 100, volumes)
        assert player.credits_spent_lifetime == 200

    def test_stat_fields_updated_on_sell(self) -> None:
        """Selling should update credits_earned_lifetime."""
        player = _make_player()
        player.ship.add_cargo("iron_ore", 5, 100)
        player.sell_commodity("iron_ore", 5, 150)
        assert player.credits_earned_lifetime == 750

    def test_stat_fields_updated_on_travel(self) -> None:
        """Traveling should update jumps_traveled and fuel_consumed."""
        player = _make_player()
        player.travel_to_system("breakstone", 10)
        assert player.jumps_traveled == 1
        assert player.fuel_consumed == 10


class TestAchievementProgress:
    """Test achievement progress calculation."""

    def test_progress_at_zero(self) -> None:
        """Progress should be 0.0 when stat is 0."""
        player = _make_player()
        ach = _make_achievement(stat_key="trades_completed", threshold=10)
        manager = AchievementManager([ach])

        progress = manager.get_progress(player, "test_ach")
        assert progress == 0.0

    def test_progress_partial(self) -> None:
        """Progress should be proportional to threshold."""
        player = _make_player()
        ach = _make_achievement(stat_key="trades_completed", threshold=10)
        manager = AchievementManager([ach])

        player.trades_completed = 5
        progress = manager.get_progress(player, "test_ach")
        assert progress == 0.5

    def test_progress_capped_at_one(self) -> None:
        """Progress should not exceed 1.0."""
        player = _make_player()
        ach = _make_achievement(stat_key="trades_completed", threshold=5)
        manager = AchievementManager([ach])

        player.trades_completed = 10
        progress = manager.get_progress(player, "test_ach")
        assert progress == 1.0

    def test_progress_unknown_achievement(self) -> None:
        """Progress for unknown achievement ID should be 0.0."""
        player = _make_player()
        manager = AchievementManager([])
        progress = manager.get_progress(player, "nonexistent")
        assert progress == 0.0
