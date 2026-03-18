"""Tests for crew loyalty change sources — dialogue choices and faction rep."""

from spacegame.models.crew import (
    CrewAbility,
    CrewTemplate,
    CrewRoster,
)
from spacegame.models.dialogue import (
    DialogueManager,
    DialogueNode,
    DialogueResponse,
    DialogueTree,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_template(
    template_id: str = "elena_reeves",
    name: str = "Elena Reeves",
    faction_id: str = "commerce_guild",
    home_system_id: str = "stellaris_port",
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
                description="Test",
                unlock_level=1,
            )
        ],
        faction_id=faction_id,
        home_system_id=home_system_id,
        is_companion=True,
    )


def _make_roster() -> CrewRoster:
    templates = {
        "elena_reeves": _make_template(
            "elena_reeves", "Elena Reeves", "commerce_guild", "stellaris_port"
        ),
        "marcus_jin": _make_template(
            "marcus_jin", "Marcus Jin", "industrial_union", "breakstone"
        ),
        "dr_priya_osei": _make_template(
            "dr_priya_osei", "Dr. Priya Osei", "science_collective", "axiom_labs"
        ),
    }
    roster = CrewRoster(templates)
    roster.recruit("elena_reeves", crew_slots=5)
    roster.recruit("marcus_jin", crew_slots=5)
    roster.recruit("dr_priya_osei", crew_slots=5)
    return roster


def _make_dialogue_with_loyalty(
    crew_loyalty_changes: dict[str, int],
) -> tuple[DialogueTree, DialogueManager]:
    """Create a simple dialogue tree with crew loyalty changes on the response."""
    response = DialogueResponse(
        text="Test response",
        next_node_id=None,
        crew_loyalty_changes=crew_loyalty_changes,
    )
    node = DialogueNode(
        id="start",
        speaker_id="test_npc",
        text="Test dialogue",
        responses=[response],
    )
    tree = DialogueTree(
        id="test_dialogue",
        start_node_id="start",
        nodes={"start": node},
    )
    manager = DialogueManager()
    manager.start_dialogue(tree, npc_id="test_npc")
    return tree, manager


# ============================================================================
# Dialogue Loyalty Change Tests
# ============================================================================


class TestDialogueCrewLoyaltyChanges:
    """Tests for crew loyalty changes triggered by dialogue responses."""

    def test_dialogue_loyalty_change_applied(self) -> None:
        """Selecting a response with crew_loyalty_changes adjusts crew loyalty."""
        roster = _make_roster()
        initial = roster.get_member_state("elena_reeves")
        assert initial is not None
        initial_loyalty = initial["loyalty"]

        _, manager = _make_dialogue_with_loyalty({"elena_reeves": 10})
        manager.set_crew_roster(roster)
        manager.select_response(0)

        state = roster.get_member_state("elena_reeves")
        assert state is not None
        assert state["loyalty"] == initial_loyalty + 10

    def test_dialogue_loyalty_negative_change(self) -> None:
        """Negative crew_loyalty_changes reduce loyalty."""
        roster = _make_roster()
        _, manager = _make_dialogue_with_loyalty({"elena_reeves": -5})
        manager.set_crew_roster(roster)
        manager.select_response(0)

        state = roster.get_member_state("elena_reeves")
        assert state is not None
        assert state["loyalty"] == 25  # 30 - 5

    def test_dialogue_loyalty_multiple_crew(self) -> None:
        """A single response can affect multiple crew members."""
        roster = _make_roster()
        _, manager = _make_dialogue_with_loyalty(
            {"elena_reeves": 5, "marcus_jin": -3}
        )
        manager.set_crew_roster(roster)
        manager.select_response(0)

        elena = roster.get_member_state("elena_reeves")
        marcus = roster.get_member_state("marcus_jin")
        assert elena is not None and elena["loyalty"] == 35
        assert marcus is not None and marcus["loyalty"] == 27

    def test_dialogue_loyalty_no_roster_is_noop(self) -> None:
        """Without crew_roster set, crew_loyalty_changes are silently ignored."""
        _, manager = _make_dialogue_with_loyalty({"elena_reeves": 10})
        # Don't set crew_roster
        # Should not raise
        manager.select_response(0)

    def test_dialogue_loyalty_unknown_crew_ignored(self) -> None:
        """crew_loyalty_changes for non-recruited crew are silently ignored."""
        roster = _make_roster()
        _, manager = _make_dialogue_with_loyalty({"nonexistent_crew": 10})
        manager.set_crew_roster(roster)
        # Should not raise
        manager.select_response(0)

    def test_dialogue_empty_loyalty_changes(self) -> None:
        """Empty crew_loyalty_changes dict is a no-op."""
        roster = _make_roster()
        _, manager = _make_dialogue_with_loyalty({})
        manager.set_crew_roster(roster)
        manager.select_response(0)
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["loyalty"] == 30


# ============================================================================
# Faction Reputation -> Crew Loyalty Tests
# ============================================================================


class TestFactionRepToCrewLoyalty:
    """Tests for faction reputation changes affecting crew loyalty."""

    def test_positive_faction_rep_boosts_matching_crew(self) -> None:
        """When commerce_guild rep increases, Elena (Guild) gets loyalty boost."""
        roster = _make_roster()
        roster.adjust_loyalty_for_faction("commerce_guild", 2)
        elena = roster.get_member_state("elena_reeves")
        assert elena is not None and elena["loyalty"] == 32

    def test_negative_faction_rep_hurts_matching_crew(self) -> None:
        """When industrial_union rep decreases, Marcus (Union) loses loyalty."""
        roster = _make_roster()
        messages = roster.adjust_loyalty_for_faction("industrial_union", -2)
        marcus = roster.get_member_state("marcus_jin")
        assert marcus is not None and marcus["loyalty"] == 28

    def test_faction_rep_does_not_affect_non_matching_crew(self) -> None:
        """Crew from other factions are unaffected by faction rep changes."""
        roster = _make_roster()
        roster.adjust_loyalty_for_faction("commerce_guild", 5)
        marcus = roster.get_member_state("marcus_jin")
        priya = roster.get_member_state("dr_priya_osei")
        assert marcus is not None and marcus["loyalty"] == 30
        assert priya is not None and priya["loyalty"] == 30

    def test_faction_rep_affects_all_matching_crew(self) -> None:
        """If two crew share a faction, both are affected."""
        # Add second Guild crew
        templates = {
            "elena_reeves": _make_template(
                "elena_reeves", "Elena", "commerce_guild", "stellaris_port"
            ),
            "guild_trader": _make_template(
                "guild_trader", "Guild Trader", "commerce_guild", "nexus_prime"
            ),
        }
        roster = CrewRoster(templates)
        roster.recruit("elena_reeves", crew_slots=5)
        roster.recruit("guild_trader", crew_slots=5)

        roster.adjust_loyalty_for_faction("commerce_guild", 3)
        elena = roster.get_member_state("elena_reeves")
        trader = roster.get_member_state("guild_trader")
        assert elena is not None and elena["loyalty"] == 33
        assert trader is not None and trader["loyalty"] == 33

    def test_unknown_faction_is_noop(self) -> None:
        """Adjusting loyalty for a faction with no crew does nothing."""
        roster = _make_roster()
        messages = roster.adjust_loyalty_for_faction("unknown_faction", 5)
        assert len(messages) == 0


# ============================================================================
# CrewTemplate New Fields Tests
# ============================================================================


class TestCrewTemplateNewFields:
    """Tests for new faction_id and home_system_id fields."""

    def test_faction_id_default_empty(self) -> None:
        template = CrewTemplate(
            id="test",
            name="Test",
            role="test",
            description="test",
            portrait_color=[0, 0, 0],
        )
        assert template.faction_id == ""

    def test_home_system_id_default_empty(self) -> None:
        template = CrewTemplate(
            id="test",
            name="Test",
            role="test",
            description="test",
            portrait_color=[0, 0, 0],
        )
        assert template.home_system_id == ""

    def test_faction_id_set(self) -> None:
        template = _make_template(faction_id="commerce_guild")
        assert template.faction_id == "commerce_guild"

    def test_home_system_id_set(self) -> None:
        template = _make_template(home_system_id="stellaris_port")
        assert template.home_system_id == "stellaris_port"
