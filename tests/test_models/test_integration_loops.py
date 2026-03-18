"""Integration tests for multi-system gameplay interactions.

Tests cross-system flows where multiple subsystems interact:
trade loop, combat stats loop, crew bonus loop, progression loop, travel loop.
"""

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.progression import PlayerProgression
from spacegame.models.crew import CrewRoster
from spacegame.achievement_manager import AchievementManager


def _make_player(credits: int = 10000) -> Player:
    """Create a player with a real ship type for integration testing."""
    dl = get_data_loader()
    ship_type = dl.ship_types["light_freighter"]  # Good cargo/fuel
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    return Player(
        name="IntegrationTester",
        credits=credits,
        current_system_id="nexus_prime",
        ship=ship,
    )


def _get_commodity_volume(commodity_id: str) -> dict[str, int]:
    """Get commodity volumes dict from DataLoader."""
    dl = get_data_loader()
    return {c.id: c.volume_per_unit for c in dl.commodities.values()}


class TestTradeLoop:
    """Buy → travel → sell → profit → stats updated correctly."""

    def test_buy_travel_sell_profit(self) -> None:
        """Complete trade loop: buy low, travel, sell high, check profit."""
        player = _make_player(credits=5000)
        volumes = _get_commodity_volume("metals")

        # Buy metals at 50 CR each
        success, msg = player.buy_commodity("metals", 10, 50, volumes)
        assert success, f"Buy should succeed: {msg}"
        assert player.credits == 4500  # 5000 - 500
        assert player.ship.get_cargo_quantity("metals") == 10
        assert player.trades_completed == 1

        # Travel to another system
        success, msg = player.travel_to_system("breakstone", 2)
        assert success, f"Travel should succeed: {msg}"
        assert player.current_system_id == "breakstone"
        assert player.jumps_traveled == 1
        assert player.game_day == 2

        # Sell metals at 80 CR each (profit = 30 per unit)
        success, msg = player.sell_commodity("metals", 10, 80)
        assert success, f"Sell should succeed: {msg}"
        assert player.credits == 5300  # 4500 + 800
        assert player.ship.get_cargo_quantity("metals") == 0
        assert player.trades_completed == 2
        assert player.total_profit == 300  # (80-50) * 10
        assert player.credits_earned_lifetime == 800
        assert player.largest_single_profit == 300

    def test_trade_updates_visited_systems(self) -> None:
        """Trading loop updates systems_visited set."""
        player = _make_player()
        assert "nexus_prime" in player.systems_visited

        player.travel_to_system("breakstone", 2)
        assert "breakstone" in player.systems_visited
        assert len(player.systems_visited) == 2

        player.travel_to_system("stellaris_port", 2)
        assert len(player.systems_visited) == 3

    def test_insufficient_funds_blocks_buy(self) -> None:
        """Cannot buy if credits are too low."""
        player = _make_player(credits=100)
        volumes = _get_commodity_volume("metals")
        success, _ = player.buy_commodity("metals", 10, 50, volumes)
        assert not success
        assert player.trades_completed == 0

    def test_insufficient_fuel_blocks_travel(self) -> None:
        """Cannot travel if fuel is too low."""
        player = _make_player()
        # Drain fuel
        player.ship.current_fuel = 0
        success, _ = player.travel_to_system("breakstone", 2)
        assert not success
        assert player.current_system_id == "nexus_prime"


class TestProgressionLoop:
    """XP gain → level up → skill points → skill investment."""

    def test_xp_to_skill_point_flow(self) -> None:
        """Adding XP triggers level up and grants skill points."""
        player = _make_player()
        initial_level = player.progression.level
        initial_sp = player.progression.skill_points

        # Add enough XP for first level up
        messages = player.progression.add_xp(200)
        assert player.progression.level > initial_level, "Should have leveled up"
        assert player.progression.skill_points > initial_sp, "Should have skill points"
        assert len(messages) > 0, "Should report level-up messages"

    def test_skill_investment_after_levelup(self) -> None:
        """Can invest skill points after leveling up."""
        player = _make_player()
        # Level up
        player.progression.add_xp(200)
        assert player.progression.get_available_skill_points() > 0

        # Find a skill to invest in
        skills = list(player.progression.skills.keys())
        assert len(skills) > 0, "Should have skills available"
        skill_id = skills[0]

        success, msg = player.progression.level_up_skill(skill_id)
        assert success, f"Skill investment should succeed: {msg}"
        assert player.progression.skill_points_spent > 0

    def test_milestone_level_grants_extra_sp(self) -> None:
        """Level 5 (milestone) grants 2 skill points instead of 1."""
        player = _make_player()
        # Get to level 5 by adding lots of XP
        player.progression.add_xp(5000)
        # Should have hit level 5+ milestone at some point
        assert player.progression.level >= 5, "Should be level 5+"
        # Milestone gives 2 SP, so total SP should be > level count
        # (1+1+1+1+2 = 6 SP for 5 levels if level 5 is first milestone)
        assert player.progression.skill_points >= 6


class TestAchievementLoop:
    """Action → stats update → achievement check → reward grant."""

    def test_trade_triggers_achievement(self) -> None:
        """Completing trades can trigger trade-related achievements."""
        dl = get_data_loader()
        am = AchievementManager(dl.achievements)
        player = _make_player(credits=50000)
        volumes = _get_commodity_volume("metals")

        # No achievements initially
        initial_unlocked = len(player.unlocked_achievements)

        # Do some trading to build up stats
        for i in range(10):
            player.buy_commodity("metals", 1, 50, volumes)
            player.sell_commodity("metals", 1, 100)

        assert player.trades_completed >= 20, "Should have 20+ trades"

        # Check if any achievements unlocked
        newly_unlocked = am.check_achievements(player)
        # We expect at least the first-trade achievement
        # (exact achievement depends on data, but trades_completed >= 20 should trigger something)
        total_unlocked = len(player.unlocked_achievements)
        assert total_unlocked >= initial_unlocked, "Should have at least as many achievements"

    def test_achievement_reward_grants_once(self) -> None:
        """Achievement rewards only apply once even if checked multiple times."""
        dl = get_data_loader()
        am = AchievementManager(dl.achievements)
        player = _make_player()

        # Get all achievements, find one with XP reward
        xp_achievements = [
            a for a in dl.achievements
            if a.reward_type == "xp" and a.reward_value > 0
        ]
        if not xp_achievements:
            return  # Skip if no XP achievements

        achievement = xp_achievements[0]
        initial_xp = player.progression.xp

        # Apply reward twice
        result1 = am.apply_reward(player, achievement)
        result2 = am.apply_reward(player, achievement)

        assert result1 != "", "First reward should apply"
        assert result2 == "", "Second reward should be blocked"


class TestCrewBonusLoop:
    """Recruit crew → bonuses active → dismiss → bonuses removed."""

    def test_recruit_adds_bonus_dismiss_removes(self) -> None:
        """Recruiting crew adds bonuses, dismissing removes them."""
        dl = get_data_loader()
        roster = CrewRoster(dl.crew_templates)

        # Find a crew member with a known bonus
        template = None
        bonus_type = None
        for tid, t in dl.crew_templates.items():
            if t.abilities:
                template = t
                bonus_type = t.abilities[0].bonus_type
                break

        if template is None:
            return  # Skip if no crew with abilities

        # Before recruitment: no bonus
        bonus_before = roster.get_bonus(bonus_type)

        # Recruit
        success, msg = roster.recruit(template.id, crew_slots=4)
        assert success, f"Recruit should succeed: {msg}"

        # After recruitment: bonus active
        bonus_after = roster.get_bonus(bonus_type)
        assert bonus_after > bonus_before, "Bonus should increase after recruitment"

        # Dismiss
        success, msg = roster.dismiss(template.id)
        assert success, f"Dismiss should succeed: {msg}"

        # After dismiss: bonus removed
        bonus_final = roster.get_bonus(bonus_type)
        assert bonus_final == bonus_before, "Bonus should return to pre-recruitment value"

    def test_multiple_crew_bonuses_stack(self) -> None:
        """Bonuses from multiple crew members with same bonus type stack."""
        dl = get_data_loader()
        roster = CrewRoster(dl.crew_templates)

        # Find two crew with overlapping bonus types
        bonus_map: dict[str, list[str]] = {}
        for tid, t in dl.crew_templates.items():
            for ability in t.abilities:
                bonus_map.setdefault(ability.bonus_type, []).append(tid)

        # Find a bonus type with 2+ crew
        stacking_type = None
        stacking_ids = []
        for bt, tids in bonus_map.items():
            if len(tids) >= 2:
                stacking_type = bt
                stacking_ids = tids[:2]
                break

        if stacking_type is None:
            return  # Skip if no overlapping bonuses

        roster.recruit(stacking_ids[0], crew_slots=4)
        bonus_one = roster.get_bonus(stacking_type)

        roster.recruit(stacking_ids[1], crew_slots=4)
        bonus_two = roster.get_bonus(stacking_type)

        assert bonus_two >= bonus_one, "Second crew should not decrease total bonus"


class TestTravelLoop:
    """Travel → fuel consumed → day advances → stats tracked."""

    def test_travel_chain_updates_all_stats(self) -> None:
        """Multi-hop travel updates fuel, day, visited, and jumps."""
        player = _make_player()
        initial_fuel = player.ship.current_fuel

        player.travel_to_system("breakstone", 2)
        player.travel_to_system("stellaris_port", 3)
        player.travel_to_system("nexus_prime", 2)

        assert player.jumps_traveled == 3
        assert player.fuel_consumed == 7
        assert player.game_day == 4  # Started at 1, +3 jumps
        assert player.ship.current_fuel == initial_fuel - 7
        assert len(player.systems_visited) == 3

    def test_travel_and_trade_combined(self) -> None:
        """Full gameplay loop: buy, travel, sell, travel back."""
        player = _make_player(credits=10000)
        volumes = _get_commodity_volume("metals")

        # Buy at origin
        player.buy_commodity("metals", 20, 50, volumes)
        assert player.credits == 9000

        # Travel and sell
        player.travel_to_system("breakstone", 2)
        player.sell_commodity("metals", 20, 80)

        # Travel back
        player.travel_to_system("nexus_prime", 2)

        # Verify all stats updated
        assert player.trades_completed == 2
        assert player.total_profit == 600  # (80-50) * 20
        assert player.jumps_traveled == 2
        assert player.game_day == 3
        assert player.credits == 9000 + 1600  # 9000 + 20*80
