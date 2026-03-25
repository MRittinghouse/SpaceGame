"""Tests for skill respec system."""

from spacegame.models.progression import PlayerProgression, RESPEC_COST_PER_LEVEL


class TestRespecSkills:
    """Tests for resetting all skill investments."""

    def test_respec_refunds_all_points(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 5
        prog.level_up_skill("negotiator")  # Root skill, cost 1
        prog.level_up_skill("negotiator")  # Level 2
        assert prog.skill_points_spent == 2
        assert prog.get_available_skill_points() == 3

        success, msg = prog.respec_skills(player_level=1, player_credits=10000)
        assert success
        assert prog.get_available_skill_points() == 5
        assert prog.skill_points_spent == 0

    def test_respec_resets_all_skill_levels(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 5
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")

        prog.respec_skills(player_level=1, player_credits=10000)
        for skill in prog.skills.values():
            assert skill.current_level == 0, f"{skill.id} should be reset to 0"

    def test_respec_preserves_total_skill_points(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 10
        prog.level_up_skill("negotiator")

        prog.respec_skills(player_level=1, player_credits=10000)
        assert prog.skill_points == 10

    def test_respec_with_no_skills_invested(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 3
        success, msg = prog.respec_skills(player_level=1, player_credits=10000)
        assert not success, "Respec with no investment should fail"

    def test_respec_allows_reinvestment(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 3
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")

        prog.respec_skills(player_level=1, player_credits=10000)
        # Invest in a different tree instead
        success, _ = prog.level_up_skill("weapons_training")
        assert success
        assert prog.skills["weapons_training"].current_level == 1
        assert prog.skills["negotiator"].current_level == 0

    def test_get_bonus_zero_after_respec(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 3
        prog.level_up_skill("negotiator")
        assert prog.get_bonus("buy_price_reduction") > 0

        prog.respec_skills(player_level=1, player_credits=10000)
        assert prog.get_bonus("buy_price_reduction") == 0.0

    def test_respec_across_multiple_trees(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 5
        prog.level_up_skill("negotiator")  # Trading
        prog.level_up_skill("weapons_training")  # Combat
        assert prog.skill_points_spent == 2

        prog.respec_skills(player_level=1, player_credits=10000)
        assert prog.skill_points_spent == 0
        assert prog.skills["negotiator"].current_level == 0
        assert prog.skills["weapons_training"].current_level == 0
