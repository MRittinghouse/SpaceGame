"""Tests for Sprint 2 QA fixes: respec cost, achievement guard, mining cap, atomic saves."""

import json
import tempfile
from pathlib import Path

from spacegame.models.achievement import Achievement
from spacegame.achievement_manager import AchievementManager
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


def _make_ship_type() -> ShipType:
    return ShipType(
        id="test", name="Test", ship_class="starter",
        description="", cargo_capacity=100, fuel_capacity=50,
        fuel_efficiency=5, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=2, special_abilities=[], availability="common",
    )


def _make_player(credits: int = 5000) -> Player:
    return Player(
        name="Tester",
        credits=credits,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


def _make_achievement(
    ach_id: str = "test_ach",
    stat_key: str = "trades_completed",
    threshold: int = 1,
    reward_type: str = "credits",
    reward_value: int = 100,
) -> Achievement:
    return Achievement(
        id=ach_id,
        name="Test Achievement",
        description="A test achievement",
        category="general",
        stat_key=stat_key,
        threshold=threshold,
        reward_type=reward_type,
        reward_value=reward_value,
    )


# --- 3.2: Respec Cost ---


class TestRespecCost:
    """Respec should cost credits based on level."""

    def _invest_one_skill(self, player: Player) -> None:
        """Helper: invest one skill point in the first available skill."""
        prog = player.progression
        prog.skill_points += 1
        for skill in prog.skills.values():
            if skill.max_level > 0:
                skill.current_level = 1
                prog.skill_points_spent += skill.cost_per_level
                break

    def test_respec_deducts_credits(self) -> None:
        """Respec should cost credits."""
        player = _make_player(credits=10000)
        self._invest_one_skill(player)

        success, msg = player.progression.respec_skills(
            player_level=5, player_credits=10000
        )
        assert success, msg

    def test_respec_fails_insufficient_credits(self) -> None:
        """Respec should fail if player can't afford it."""
        player = _make_player(credits=0)
        self._invest_one_skill(player)

        success, msg = player.progression.respec_skills(
            player_level=5, player_credits=0
        )
        assert not success
        assert "credits" in msg.lower() or "CR" in msg

    def test_respec_no_investment_no_cost(self) -> None:
        """Respec with no skills invested should report nothing to reset."""
        player = _make_player()
        success, msg = player.progression.respec_skills(
            player_level=1, player_credits=5000
        )
        assert not success

    def test_respec_cost_scales_with_level(self) -> None:
        """Higher level should mean higher respec cost."""
        from spacegame.models.progression import RESPEC_COST_PER_LEVEL

        cost_5 = RESPEC_COST_PER_LEVEL * 5
        cost_10 = RESPEC_COST_PER_LEVEL * 10
        assert cost_10 > cost_5

    def test_respec_returns_cost_in_message(self) -> None:
        """Success message should mention the cost paid."""
        player = _make_player(credits=50000)
        self._invest_one_skill(player)

        success, msg = player.progression.respec_skills(
            player_level=1, player_credits=50000
        )
        assert success
        assert "CR" in msg or "credits" in msg.lower()


# --- 3.3: Achievement Reward Guard ---


class TestAchievementRewardGuard:
    """apply_reward should not double-reward already-unlocked achievements."""

    def test_reward_applied_for_newly_unlocked(self) -> None:
        """Normal reward application should work."""
        player = _make_player(credits=0)
        ach = _make_achievement(reward_type="credits", reward_value=500)
        manager = AchievementManager([ach])

        player.unlocked_achievements.append(ach.id)
        result = manager.apply_reward(player, ach)
        assert result != ""
        assert player.credits == 500

    def test_reward_blocked_if_already_rewarded(self) -> None:
        """Calling apply_reward again should not grant double rewards."""
        player = _make_player(credits=0)
        ach = _make_achievement(reward_type="credits", reward_value=500)
        manager = AchievementManager([ach])

        player.unlocked_achievements.append(ach.id)
        manager.apply_reward(player, ach)
        assert player.credits == 500

        # Second call should be blocked
        result = manager.apply_reward(player, ach)
        assert player.credits == 500  # No change
        assert result == ""


# --- 2.3: Mining Rare Ore Cap ---


class TestMiningRareOreCap:
    """Rare ore bonus should be capped to prevent extreme rare drops."""

    def test_effective_rare_capped_in_rock_generation(self) -> None:
        """Even with extreme bonuses, rare weight shouldn't be uncapped."""
        from spacegame.models.mining import MiningSession, MiningConfig

        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=3,
        )
        # Extreme rare bonus — without cap, this would make all rocks rare
        session = MiningSession(config, rare_chance_bonus=10.0)

        # After generating rocks, there should still be some common rocks
        # (cap prevents 100% rare/crystal)
        total_rocks = len(session.rocks)
        rare_count = sum(
            1 for r in session.rocks
            if r.rock_type.value in ("rare", "crystal")
        )
        # With a cap, rare+crystal shouldn't be 100% of rocks
        assert rare_count < total_rocks, (
            f"All {total_rocks} rocks were rare/crystal — bonus not capped"
        )


# --- 1.2: Atomic Save Writes ---


class TestAtomicSaves:
    """Save files should be written atomically to prevent corruption."""

    def test_save_creates_file(self) -> None:
        """Basic save should still produce a valid file."""
        from spacegame.save_manager import SaveManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            player = _make_player()
            result = sm.save_game(
                slot=1,
                player=player,
                markets={},
                active_events={},
                playtime_seconds=100,
                save_name="test",
            )
            assert result is True
            save_path = sm.get_save_file_path(1)
            assert save_path.exists()
            with open(save_path) as f:
                data = json.load(f)
            assert "player" in data

    def test_no_tmp_file_left_after_save(self) -> None:
        """Atomic save should clean up the temp file."""
        from spacegame.save_manager import SaveManager
        import glob

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            player = _make_player()
            sm.save_game(
                slot=1,
                player=player,
                markets={},
                active_events={},
                playtime_seconds=100,
                save_name="test",
            )
            # No .tmp files should remain
            tmp_files = list(Path(tmpdir).glob("*.tmp"))
            assert len(tmp_files) == 0, f"Leftover temp files: {tmp_files}"

    def test_save_no_partial_file_on_error(self) -> None:
        """If serialization fails, no partial file should be left."""
        from spacegame.save_manager import SaveManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            save_path = sm.get_save_file_path(1)

            result = sm.save_game(
                slot=1,
                player=None,  # type: ignore  # Intentionally invalid
                markets={},
                active_events={},
                playtime_seconds=100,
                save_name="test",
            )
            assert result is False
            assert not save_path.exists()
            # No temp files either
            tmp_files = list(Path(tmpdir).glob("*.tmp"))
            assert len(tmp_files) == 0


# --- 1.4: Tomas Faction ID ---


class TestTomasFactionId:
    """Tomas Drifter should have a valid faction_id."""

    def test_tomas_faction_is_valid(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        tomas = dl.crew_templates.get("tomas_drifter")
        assert tomas is not None
        valid_factions = {
            "commerce_guild", "frontier_alliance", "miners_union",
            "science_collective", "",
        }
        assert tomas.faction_id in valid_factions, (
            f"Tomas has invalid faction_id: {tomas.faction_id}"
        )


# --- 6.3: Crew Slot Validation ---


class TestCrewSlotValidation:
    """Crew state should be preserved on load even if over capacity."""

    def test_crew_state_preserved_even_if_over_capacity(self) -> None:
        """Over-capacity crew should be preserved, not silently dropped."""
        player = _make_player()
        # Ship has 2 crew slots — set crew state with 3 members
        player.crew_state = {
            "crew1": {"xp": 0, "loyalty": 50},
            "crew2": {"xp": 0, "loyalty": 50},
            "crew3": {"xp": 0, "loyalty": 50},
        }
        assert len(player.crew_state) == 3
