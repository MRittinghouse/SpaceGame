"""Tests for smuggling achievements and stat tracking (Phase E.8).

Covers new player stats (inspections_passed_with_contraband,
max_criminal_heat_reached), achievements, and max heat tracking.
"""

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.achievement import Achievement
from spacegame.achievement_manager import AchievementManager


def _make_player() -> Player:
    ship_type = ShipType(
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
    ship = Ship(ship_type=ship_type, current_fuel=100)
    return Player(
        name="Test",
        credits=5000,
        current_system_id="nexus_prime",
        ship=ship,
    )


# ============================================================================
# New Player Stats
# ============================================================================


class TestSmugglingStats:
    """Player should track smuggling-specific stats for achievements."""

    def test_inspections_passed_default_zero(self) -> None:
        """inspections_passed_with_contraband defaults to 0."""
        player = _make_player()
        assert player.inspections_passed_with_contraband == 0

    def test_max_criminal_heat_reached_default_zero(self) -> None:
        """max_criminal_heat_reached defaults to 0."""
        player = _make_player()
        assert player.max_criminal_heat_reached == 0

    def test_add_criminal_heat_tracks_max(self) -> None:
        """add_criminal_heat should update max_criminal_heat_reached."""
        player = _make_player()
        player.add_criminal_heat(30)
        assert player.max_criminal_heat_reached == 30

        player.decay_criminal_heat(10)
        # Max should NOT decrease on decay
        assert player.max_criminal_heat_reached == 30

        player.add_criminal_heat(50)
        # Heat is now 20 + 50 = 70
        assert player.criminal_heat == 70
        assert player.max_criminal_heat_reached == 70

    def test_add_criminal_heat_capped_at_100(self) -> None:
        """Max heat tracking respects the 100 cap."""
        player = _make_player()
        player.add_criminal_heat(120)
        assert player.criminal_heat == 100
        assert player.max_criminal_heat_reached == 100


# ============================================================================
# Save/Load New Stats
# ============================================================================


class TestSmugglingStatsSaveLoad:
    """New smuggling stats survive save/load cycle."""

    def test_new_stats_serialized(self) -> None:
        """inspections_passed_with_contraband and max_criminal_heat_reached save/load."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()
        player.inspections_passed_with_contraband = 5
        player.max_criminal_heat_reached = 42

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.inspections_passed_with_contraband == 5
            assert p2.max_criminal_heat_reached == 42

    def test_backward_compat_missing_stats(self) -> None:
        """Old saves without new stats load as 0."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()
        # Don't set new stats — they stay at default 0

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.inspections_passed_with_contraband == 0
            assert p2.max_criminal_heat_reached == 0


# ============================================================================
# Smuggling Achievements
# ============================================================================


class TestSmugglingAchievements:
    """Achievement definitions for smuggling milestones."""

    def test_first_smuggle_achievement_exists(self) -> None:
        """first_smuggle achievement exists in data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ids = [a.id for a in dl.achievements]
        assert "first_smuggle" in ids

    def test_heat_survivor_achievement_exists(self) -> None:
        """heat_survivor achievement exists in data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ids = [a.id for a in dl.achievements]
        assert "heat_survivor" in ids

    def test_clean_getaway_achievement_exists(self) -> None:
        """clean_getaway achievement exists in data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        ids = [a.id for a in dl.achievements]
        assert "clean_getaway" in ids

    def test_first_smuggle_triggers(self) -> None:
        """first_smuggle unlocks when goods_smuggled >= 1."""
        achievement = Achievement(
            id="first_smuggle",
            name="Contraband Runner",
            description="Smuggle your first goods.",
            category="smuggling",
            stat_key="goods_smuggled",
            threshold=1,
            reward_type="xp",
            reward_value=100,
        )
        mgr = AchievementManager([achievement])
        player = _make_player()

        # Not yet
        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 0

        player.goods_smuggled = 1
        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 1
        assert unlocked[0].id == "first_smuggle"

    def test_heat_survivor_triggers(self) -> None:
        """heat_survivor unlocks when max_criminal_heat_reached >= 75."""
        achievement = Achievement(
            id="heat_survivor",
            name="Heat Survivor",
            description="Reach 75 criminal heat and survive.",
            category="smuggling",
            stat_key="max_criminal_heat_reached",
            threshold=75,
            reward_type="credits",
            reward_value=2000,
        )
        mgr = AchievementManager([achievement])
        player = _make_player()

        player.max_criminal_heat_reached = 50
        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 0

        player.max_criminal_heat_reached = 75
        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 1
        assert unlocked[0].id == "heat_survivor"

    def test_clean_getaway_triggers(self) -> None:
        """clean_getaway unlocks when inspections_passed_with_contraband >= 1."""
        achievement = Achievement(
            id="clean_getaway",
            name="Clean Getaway",
            description="Pass a customs inspection while carrying contraband.",
            category="smuggling",
            stat_key="inspections_passed_with_contraband",
            threshold=1,
            reward_type="xp",
            reward_value=150,
        )
        mgr = AchievementManager([achievement])
        player = _make_player()

        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 0

        player.inspections_passed_with_contraband = 1
        unlocked = mgr.check_achievements(player)
        assert len(unlocked) == 1
        assert unlocked[0].id == "clean_getaway"
