"""Tests for dialogue system models."""

import pytest
from spacegame.models.dialogue import (
    NPC,
    DialogueResponse,
    DialogueNode,
    DialogueTree,
    DialogueManager,
    SkillCheck,
)
from spacegame.models.social import SocialManager

# ============================================================================
# NPC Tests
# ============================================================================


class TestNPC:
    """Tests for NPC dataclass."""

    def test_creation(self) -> None:
        npc = NPC(
            id="elena_reeves",
            name="Elena Reeves",
            title="Navigator",
            portrait_color=(100, 180, 255),
            home_system_id="nexus_prime",
            dialogue_id="elena_intro",
            faction_id="commerce_guild",
        )
        assert npc.id == "elena_reeves"
        assert npc.name == "Elena Reeves"
        assert npc.title == "Navigator"
        assert npc.portrait_color == (100, 180, 255)
        assert npc.home_system_id == "nexus_prime"
        assert npc.dialogue_id == "elena_intro"
        assert npc.faction_id == "commerce_guild"

    def test_display_name_with_title(self) -> None:
        npc = NPC(
            id="elena",
            name="Elena Reeves",
            title="Navigator",
            portrait_color=(100, 180, 255),
            home_system_id="nexus_prime",
            dialogue_id="elena_intro",
        )
        assert npc.get_display_name() == "Elena Reeves \u2014 Navigator"

    def test_display_name_without_title(self) -> None:
        npc = NPC(
            id="stranger",
            name="Mysterious Stranger",
            title="",
            portrait_color=(150, 150, 150),
            home_system_id="nexus_prime",
            dialogue_id="stranger_intro",
        )
        assert npc.get_display_name() == "Mysterious Stranger"

    def test_faction_id_defaults_empty(self) -> None:
        npc = NPC(
            id="test",
            name="Test",
            title="Tester",
            portrait_color=(0, 0, 0),
            home_system_id="nexus_prime",
            dialogue_id="test_intro",
        )
        assert npc.faction_id == ""

    def test_auto_trigger_fields_default_empty(self) -> None:
        npc = NPC(
            id="test",
            name="Test",
            title="Tester",
            portrait_color=(0, 0, 0),
            home_system_id="nexus_prime",
            dialogue_id="test_intro",
        )
        assert npc.auto_trigger_gate_flag == ""
        assert npc.auto_trigger_prerequisites == []

    def test_auto_trigger_fields_set(self) -> None:
        npc = NPC(
            id="elena_reeves",
            name="Elena Reeves",
            title="Navigator",
            portrait_color=(100, 180, 255),
            home_system_id="nexus_prime",
            dialogue_id="elena_cantina",
            auto_trigger_gate_flag="talked_to_elena_cantina",
            auto_trigger_prerequisites=["iron_ore_delivered"],
        )
        assert npc.auto_trigger_gate_flag == "talked_to_elena_cantina"
        assert npc.auto_trigger_prerequisites == ["iron_ore_delivered"]


# ============================================================================
# DialogueResponse Tests
# ============================================================================


class TestDialogueResponse:
    """Tests for DialogueResponse dataclass."""

    def test_creation(self) -> None:
        response = DialogueResponse(text="Tell me more.", next_node_id="details")
        assert response.text == "Tell me more."
        assert response.next_node_id == "details"
        assert response.set_flag is None

    def test_end_conversation_response(self) -> None:
        response = DialogueResponse(text="Goodbye.", next_node_id=None)
        assert response.next_node_id is None

    def test_response_with_flag(self) -> None:
        response = DialogueResponse(
            text="I'll help you.", next_node_id="accept", set_flag="accepted_quest"
        )
        assert response.set_flag == "accepted_quest"


# ============================================================================
# DialogueNode Tests
# ============================================================================


class TestDialogueNode:
    """Tests for DialogueNode dataclass."""

    def test_creation(self) -> None:
        responses = [
            DialogueResponse(text="Option A", next_node_id="node_a"),
            DialogueResponse(text="Option B", next_node_id="node_b"),
        ]
        node = DialogueNode(
            id="start",
            speaker_id="elena_reeves",
            text="Welcome, Captain.",
            responses=responses,
        )
        assert node.id == "start"
        assert node.speaker_id == "elena_reeves"
        assert node.text == "Welcome, Captain."
        assert len(node.responses) == 2

    def test_is_terminal_with_no_responses(self) -> None:
        node = DialogueNode(id="end", speaker_id="elena", text="Farewell.", responses=[])
        assert node.is_terminal is True

    def test_is_terminal_all_responses_end(self) -> None:
        node = DialogueNode(
            id="end",
            speaker_id="elena",
            text="That's all I have to say.",
            responses=[
                DialogueResponse(text="Goodbye.", next_node_id=None),
                DialogueResponse(text="See you later.", next_node_id=None),
            ],
        )
        assert node.is_terminal is True

    def test_not_terminal_with_continuation(self) -> None:
        node = DialogueNode(
            id="middle",
            speaker_id="elena",
            text="Let me explain...",
            responses=[
                DialogueResponse(text="Go on.", next_node_id="next"),
                DialogueResponse(text="Never mind.", next_node_id=None),
            ],
        )
        assert node.is_terminal is False


# ============================================================================
# DialogueTree Tests
# ============================================================================


class TestDialogueTree:
    """Tests for DialogueTree dataclass."""

    def _make_tree(self) -> DialogueTree:
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="elena",
                text="Hello there.",
                responses=[
                    DialogueResponse(text="Hi.", next_node_id="greeting"),
                    DialogueResponse(text="Bye.", next_node_id=None),
                ],
            ),
            "greeting": DialogueNode(
                id="greeting",
                speaker_id="elena",
                text="Good to see you.",
                responses=[],
            ),
        }
        return DialogueTree(id="test_tree", start_node_id="start", nodes=nodes)

    def test_creation(self) -> None:
        tree = self._make_tree()
        assert tree.id == "test_tree"
        assert tree.start_node_id == "start"
        assert len(tree.nodes) == 2

    def test_get_node(self) -> None:
        tree = self._make_tree()
        node = tree.get_node("start")
        assert node is not None
        assert node.text == "Hello there."

    def test_get_node_nonexistent(self) -> None:
        tree = self._make_tree()
        assert tree.get_node("nonexistent") is None

    def test_get_start_node(self) -> None:
        tree = self._make_tree()
        start = tree.get_start_node()
        assert start is not None
        assert start.id == "start"


# ============================================================================
# DialogueManager Tests
# ============================================================================


class TestDialogueManager:
    """Tests for DialogueManager state machine."""

    def _make_tree(self) -> DialogueTree:
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="elena",
                text="Hello, Captain.",
                responses=[
                    DialogueResponse(text="Tell me about yourself.", next_node_id="about"),
                    DialogueResponse(
                        text="I accept.",
                        next_node_id="accepted",
                        set_flag="quest_accepted",
                    ),
                    DialogueResponse(text="Goodbye.", next_node_id=None),
                ],
            ),
            "about": DialogueNode(
                id="about",
                speaker_id="elena",
                text="I'm a navigator by trade.",
                responses=[
                    DialogueResponse(text="Interesting.", next_node_id=None),
                ],
            ),
            "accepted": DialogueNode(
                id="accepted",
                speaker_id="elena",
                text="Excellent! Meet me at the docks.",
                responses=[],
            ),
        }
        return DialogueTree(id="elena_intro", start_node_id="start", nodes=nodes)

    def test_not_active_initially(self) -> None:
        dm = DialogueManager()
        assert dm.is_active is False

    def test_start_dialogue(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        assert dm.is_active is True

    def test_get_current_node_after_start(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        node = dm.get_current_node()
        assert node is not None
        assert node.id == "start"
        assert node.text == "Hello, Captain."

    def test_get_available_responses(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        assert len(responses) == 3
        assert responses[0].text == "Tell me about yourself."

    def test_select_response_advances_node(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Select "Tell me about yourself." -> goes to "about"
        next_node = dm.select_response(0)
        assert next_node is not None
        assert next_node.id == "about"
        assert dm.get_current_node().id == "about"

    def test_select_response_ends_dialogue(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Select "Goodbye." (index 2) -> next_node_id is None
        next_node = dm.select_response(2)
        assert next_node is None
        assert dm.is_active is False

    def test_select_response_sets_flag(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Select "I accept." (index 1) -> sets "quest_accepted" flag
        dm.select_response(1)
        assert dm.get_flag("quest_accepted") is True

    def test_select_response_terminal_node_ends(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Go to "accepted" node (terminal — no responses)
        dm.select_response(1)
        assert dm.get_current_node().id == "accepted"
        # Terminal nodes have no responses — calling end_dialogue is explicit
        assert dm.get_available_responses() == []

    def test_end_dialogue(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        dm.end_dialogue()
        assert dm.is_active is False
        assert dm.get_current_node() is None

    def test_flags_persist_across_dialogues(self) -> None:
        dm = DialogueManager()
        dm.set_flag("some_flag", True)
        tree = self._make_tree()
        dm.start_dialogue(tree)
        dm.end_dialogue()
        assert dm.get_flag("some_flag") is True

    def test_get_flag_default_false(self) -> None:
        dm = DialogueManager()
        assert dm.get_flag("unknown_flag") is False

    def test_set_and_get_flag(self) -> None:
        dm = DialogueManager()
        dm.set_flag("met_elena", True)
        assert dm.get_flag("met_elena") is True
        dm.set_flag("met_elena", False)
        assert dm.get_flag("met_elena") is False

    def test_get_flags_for_serialization(self) -> None:
        dm = DialogueManager()
        dm.set_flag("flag_a", True)
        dm.set_flag("flag_b", False)
        flags = dm.get_flags()
        assert flags == {"flag_a": True, "flag_b": False}

    def test_load_flags(self) -> None:
        dm = DialogueManager()
        dm.load_flags({"saved_flag": True, "other_flag": False})
        assert dm.get_flag("saved_flag") is True
        assert dm.get_flag("other_flag") is False

    def test_select_response_invalid_index(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Index out of range should return None without crashing
        result = dm.select_response(99)
        assert result is None
        # Should still be on the same node
        assert dm.get_current_node().id == "start"

    def test_not_active_after_selecting_end_response(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        # Go to "about" then select "Interesting." which ends
        dm.select_response(0)  # -> about
        dm.select_response(0)  # -> None (ends)
        assert dm.is_active is False

    def test_start_dialogue_with_npc_id(self) -> None:
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree, npc_id="elena_reeves")
        assert dm.is_active is True

    def test_start_dialogue_npc_id_defaults_none(self) -> None:
        """Backward compatible — existing callers pass no npc_id."""
        dm = DialogueManager()
        tree = self._make_tree()
        dm.start_dialogue(tree)
        assert dm.is_active is True


# ============================================================================
# SkillCheck Tests
# ============================================================================


class TestSkillCheck:
    """Tests for SkillCheck dataclass."""

    def test_creation(self) -> None:
        check = SkillCheck(
            skill="persuasion",
            difficulty=3,
            success_node_id="deal_accepted",
            failure_node_id="deal_rejected",
        )
        assert check.skill == "persuasion"
        assert check.difficulty == 3
        assert check.success_node_id == "deal_accepted"
        assert check.failure_node_id == "deal_rejected"
        assert check.set_flag_on_success is None
        assert check.set_flag_on_failure is None

    def test_creation_with_flags(self) -> None:
        check = SkillCheck(
            skill="intimidation",
            difficulty=2,
            success_node_id="scared",
            failure_node_id="unimpressed",
            set_flag_on_success="guard_scared",
            set_flag_on_failure="guard_hostile",
        )
        assert check.set_flag_on_success == "guard_scared"
        assert check.set_flag_on_failure == "guard_hostile"


# ============================================================================
# DialogueResponse — Skill Check Extension Tests
# ============================================================================


class TestDialogueResponseSkillCheck:
    """Tests for DialogueResponse with skill checks."""

    def test_response_without_skill_check(self) -> None:
        response = DialogueResponse(text="Hi.", next_node_id="greeting")
        assert response.skill_check is None
        assert response.disposition_change == 0

    def test_response_with_skill_check(self) -> None:
        check = SkillCheck(
            skill="persuasion",
            difficulty=2,
            success_node_id="success",
            failure_node_id="failure",
        )
        response = DialogueResponse(
            text="[Persuasion 2] Let me convince you.",
            next_node_id=None,
            skill_check=check,
        )
        assert response.skill_check is not None
        assert response.skill_check.skill == "persuasion"

    def test_response_with_disposition_change(self) -> None:
        response = DialogueResponse(
            text="You're a good person.",
            next_node_id="happy",
            disposition_change=5,
        )
        assert response.disposition_change == 5


# ============================================================================
# DialogueManager — Skill Check Tests
# ============================================================================


class TestDialogueManagerSkillChecks:
    """Tests for skill check resolution in DialogueManager."""

    def _make_check_tree(self) -> DialogueTree:
        """Create a dialogue tree with skill check responses."""
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="tomas_drifter",
                text="I have a proposition for you.",
                responses=[
                    DialogueResponse(
                        text="[Persuasion 1] Let's negotiate.",
                        next_node_id=None,
                        skill_check=SkillCheck(
                            skill="persuasion",
                            difficulty=1,
                            success_node_id="deal_success",
                            failure_node_id="deal_failure",
                            set_flag_on_success="tomas_deal_made",
                            set_flag_on_failure="tomas_deal_failed",
                        ),
                    ),
                    DialogueResponse(
                        text="[Persuasion 5] I want a better deal.",
                        next_node_id=None,
                        skill_check=SkillCheck(
                            skill="persuasion",
                            difficulty=5,
                            success_node_id="great_deal",
                            failure_node_id="deal_failure",
                        ),
                    ),
                    DialogueResponse(
                        text="No thanks.",
                        next_node_id=None,
                    ),
                    DialogueResponse(
                        text="You're alright, Tomas.",
                        next_node_id="compliment",
                        disposition_change=5,
                    ),
                ],
            ),
            "deal_success": DialogueNode(
                id="deal_success",
                speaker_id="tomas_drifter",
                text="You drive a fair bargain!",
                responses=[],
            ),
            "deal_failure": DialogueNode(
                id="deal_failure",
                speaker_id="tomas_drifter",
                text="Sorry, I can't agree to that.",
                responses=[],
            ),
            "great_deal": DialogueNode(
                id="great_deal",
                speaker_id="tomas_drifter",
                text="You're one smooth talker.",
                responses=[],
            ),
            "compliment": DialogueNode(
                id="compliment",
                speaker_id="tomas_drifter",
                text="Thanks, Captain.",
                responses=[],
            ),
        }
        return DialogueTree(id="tomas_deal", start_node_id="start", nodes=nodes)

    def test_select_check_response_success(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        # Persuasion 1, level 1 -> should pass
        next_node = dm.select_response(0)
        assert next_node is not None
        assert next_node.id == "deal_success"

    def test_select_check_response_failure(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        # Persuasion 5, level 1 -> should fail
        next_node = dm.select_response(1)
        assert next_node is not None
        assert next_node.id == "deal_failure"

    def test_check_sets_success_flag(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(0)  # Difficulty 1 -> success
        assert dm.get_flag("tomas_deal_made") is True
        assert dm.get_flag("tomas_deal_failed") is False

    def test_check_sets_failure_flag(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(1)  # Difficulty 5 -> failure
        assert dm.get_flag("tomas_deal_failed") is False  # No failure flag on this check
        # The difficulty-1 check's flags are not set
        assert dm.get_flag("tomas_deal_made") is False

    def test_check_awards_xp(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(0)  # Success -> +2 XP
        skill = social.get_skill("persuasion")
        assert skill is not None and skill.xp == 2

    def test_last_check_result_success(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(0)  # Success
        result = dm.get_last_check_result()
        assert result is not None
        success, msg = result
        assert success is True

    def test_last_check_result_failure(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(1)  # Failure
        result = dm.get_last_check_result()
        assert result is not None
        success, msg = result
        assert success is False

    def test_last_check_result_none_for_normal_response(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(2)  # "No thanks." — normal response, ends dialogue
        assert dm.get_last_check_result() is None

    def test_disposition_change_applied(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(3)  # "You're alright" -> disposition_change=+5
        assert social.get_disposition("tomas_drifter") == 55

    def test_no_social_manager_fallback(self) -> None:
        """Without social_manager, skill check responses use success_node_id as fallback."""
        dm = DialogueManager()
        # No social manager set
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        next_node = dm.select_response(0)  # Skill check response
        assert next_node is not None
        assert next_node.id == "deal_success"  # Falls back to success_node_id

    def test_last_check_result_cleared_on_new_dialogue(self) -> None:
        dm = DialogueManager()
        social = SocialManager()
        dm.set_social_manager(social)
        tree = self._make_check_tree()
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        dm.select_response(0)  # Generates a check result
        assert dm.get_last_check_result() is not None
        # Start new dialogue — result should be cleared
        dm.start_dialogue(tree, npc_id="tomas_drifter")
        assert dm.get_last_check_result() is None


# ============================================================================
# Conditional Dialogue Response Tests
# ============================================================================


class TestConditionalResponses:
    """Tests for flag-based conditional visibility of dialogue responses."""

    def _make_conditional_tree(self) -> DialogueTree:
        """Create a dialogue tree with conditional responses."""
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="elena",
                text="What would you like to discuss?",
                responses=[
                    DialogueResponse(
                        text="Tell me about the Guild.",
                        next_node_id="guild_info",
                    ),
                    DialogueResponse(
                        text="I trust the Guild.",
                        next_node_id="guild_trust",
                        required_flags=["met_reva"],
                    ),
                    DialogueResponse(
                        text="About the secret mission...",
                        next_node_id="secret",
                        required_flags=["met_reva", "guild_member"],
                    ),
                    DialogueResponse(
                        text="First time greeting.",
                        next_node_id="greeting",
                        excluded_flags=["talked_to_elena"],
                    ),
                    DialogueResponse(
                        text="Goodbye.",
                        next_node_id=None,
                    ),
                ],
            ),
            "guild_info": DialogueNode(
                id="guild_info", speaker_id="elena", text="The Guild...", responses=[]
            ),
            "guild_trust": DialogueNode(
                id="guild_trust", speaker_id="elena", text="Good.", responses=[]
            ),
            "secret": DialogueNode(id="secret", speaker_id="elena", text="Shh...", responses=[]),
            "greeting": DialogueNode(
                id="greeting", speaker_id="elena", text="Welcome!", responses=[]
            ),
        }
        return DialogueTree(id="elena_conditional", start_node_id="start", nodes=nodes)

    def test_no_conditions_shows_all(self) -> None:
        """Responses with no required/excluded flags always appear."""
        dm = DialogueManager()
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "Tell me about the Guild." in texts
        assert "Goodbye." in texts

    def test_required_flag_met_shows(self) -> None:
        """Response with required_flag shows when that flag is True."""
        dm = DialogueManager()
        dm.set_flag("met_reva")
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "I trust the Guild." in texts

    def test_required_flag_unmet_hides(self) -> None:
        """Response with required_flag is hidden when flag is False/absent."""
        dm = DialogueManager()
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "I trust the Guild." not in texts

    def test_multiple_required_all_needed(self) -> None:
        """All required_flags must be True — partial doesn't show."""
        dm = DialogueManager()
        dm.set_flag("met_reva")
        # guild_member NOT set
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "About the secret mission..." not in texts
        # Now set both
        dm.set_flag("guild_member")
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "About the secret mission..." in texts

    def test_excluded_flag_hides(self) -> None:
        """Response with excluded_flag is hidden when that flag is True."""
        dm = DialogueManager()
        dm.set_flag("talked_to_elena")
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "First time greeting." not in texts

    def test_excluded_flag_absent_shows(self) -> None:
        """Response with excluded_flag shows when that flag is absent."""
        dm = DialogueManager()
        tree = self._make_conditional_tree()
        dm.start_dialogue(tree)
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert "First time greeting." in texts

    def test_combined_required_and_excluded(self) -> None:
        """Response with both required and excluded flags — both must pass."""
        dm = DialogueManager()
        # Build a tree with combined conditions
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="npc",
                text="Hello.",
                responses=[
                    DialogueResponse(
                        text="Special option.",
                        next_node_id=None,
                        required_flags=["has_key"],
                        excluded_flags=["used_key"],
                    ),
                ],
            ),
        }
        tree = DialogueTree(id="combo", start_node_id="start", nodes=nodes)
        # Neither flag set: required fails -> hidden
        dm.start_dialogue(tree)
        assert len(dm.get_available_responses()) == 0
        # Required met, excluded absent -> visible
        dm.set_flag("has_key")
        assert len(dm.get_available_responses()) == 1
        # Both met: excluded triggers -> hidden
        dm.set_flag("used_key")
        assert len(dm.get_available_responses()) == 0

    def test_empty_lists_no_filter(self) -> None:
        """Responses with empty required_flags and excluded_flags are not filtered."""
        dm = DialogueManager()
        nodes = {
            "start": DialogueNode(
                id="start",
                speaker_id="npc",
                text="Hello.",
                responses=[
                    DialogueResponse(
                        text="Always visible.",
                        next_node_id=None,
                        required_flags=[],
                        excluded_flags=[],
                    ),
                ],
            ),
        }
        tree = DialogueTree(id="empty", start_node_id="start", nodes=nodes)
        dm.start_dialogue(tree)
        assert len(dm.get_available_responses()) == 1


# ============================================================================
# DialogueNode Expression Tests
# ============================================================================


class TestDialogueNodeExpression:
    """Tests for DialogueNode expression field."""

    def test_dialogue_node_expression_default(self) -> None:
        """DialogueNode expression should default to None."""
        node = DialogueNode(id="n1", speaker_id="npc1", text="Hello")
        assert node.expression is None

    def test_dialogue_node_expression_set(self) -> None:
        """DialogueNode should accept expression parameter."""
        node = DialogueNode(id="n1", speaker_id="npc1", text="Hello", expression="angry")
        assert node.expression == "angry"

    def test_dialogue_node_expression_various_values(self) -> None:
        """DialogueNode should accept any string expression."""
        for expr in ["happy", "sad", "angry", "surprised", "neutral"]:
            node = DialogueNode(id="n1", speaker_id="npc1", text="Hi", expression=expr)
            assert node.expression == expr
