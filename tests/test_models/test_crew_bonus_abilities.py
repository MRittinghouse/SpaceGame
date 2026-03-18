"""Tests for permanent crew bonus abilities from quest completion."""

from spacegame.models.crew import (
    CrewAbility,
    CrewTemplate,
    CrewRoster,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_template(
    template_id: str = "elena_reeves",
    name: str = "Elena Reeves",
) -> CrewTemplate:
    return CrewTemplate(
        id=template_id,
        name=name,
        role="navigator",
        description=f"Test: {name}",
        portrait_color=[100, 180, 255],
        abilities=[
            CrewAbility(
                bonus_type="fuel_efficiency_bonus",
                bonus_value=2.0,
                description="Efficient Routing",
                unlock_level=1,
            ),
        ],
        is_companion=True,
    )


def _make_roster() -> CrewRoster:
    templates = {"elena_reeves": _make_template()}
    return CrewRoster(templates)


def _make_bonus_ability() -> CrewAbility:
    return CrewAbility(
        bonus_type="fuel_efficiency_bonus",
        bonus_value=5.0,
        description="Legacy Navigation",
        unlock_level=1,
    )


# ============================================================================
# Tests
# ============================================================================


class TestBonusAbilities:
    """Tests for permanent bonus abilities from quest rewards."""

    def test_add_bonus_ability(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        success, msg = roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        assert success, f"Should succeed: {msg}"

    def test_bonus_ability_included_in_get_bonus(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        base_bonus = roster.get_bonus("fuel_efficiency_bonus")

        roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        new_bonus = roster.get_bonus("fuel_efficiency_bonus")

        assert new_bonus == base_bonus + 5.0, (
            f"Expected {base_bonus + 5.0}, got {new_bonus}"
        )

    def test_bonus_ability_persists_through_save_load(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.add_bonus_ability("elena_reeves", _make_bonus_ability())

        saved = roster.get_state()
        roster2 = _make_roster()
        roster2.load_state(saved)

        bonus = roster2.get_bonus("fuel_efficiency_bonus")
        # Template ability (2.0) + bonus ability (5.0) = 7.0
        assert bonus == 7.0, f"Expected 7.0 after load, got {bonus}"

    def test_bonus_ability_stacks_with_template(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        # Template: 2.0, Bonus: 5.0 = 7.0
        assert roster.get_bonus("fuel_efficiency_bonus") == 7.0

    def test_cannot_add_duplicate_bonus_ability(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        success, msg = roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        assert not success, "Duplicate bonus ability should fail"

    def test_add_bonus_to_unrecruited_fails(self) -> None:
        roster = _make_roster()
        success, msg = roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        assert not success, "Should fail for unrecruited crew"

    def test_old_save_without_bonus_abilities_loads(self) -> None:
        """Saves from before bonus abilities were added should load fine."""
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        saved = roster.get_state()

        # Simulate old save by removing bonus_abilities key
        if "bonus_abilities" in saved["members"]["elena_reeves"]:
            del saved["members"]["elena_reeves"]["bonus_abilities"]

        roster2 = _make_roster()
        roster2.load_state(saved)
        # Should work fine with no bonus abilities
        assert roster2.get_bonus("fuel_efficiency_bonus") == 2.0

    def test_bonus_ability_with_loyalty_multiplier(self) -> None:
        """Bonus abilities should also benefit from loyalty multiplier."""
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["loyalty"] = 85  # Devoted = 1.5x

        roster.add_bonus_ability("elena_reeves", _make_bonus_ability())
        # (2.0 + 5.0) * 1.5 = 10.5
        bonus = roster.get_bonus("fuel_efficiency_bonus")
        assert bonus == 10.5, f"Expected 10.5, got {bonus}"
