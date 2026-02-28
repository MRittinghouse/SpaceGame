"""Tests for dialogue system models."""

import pytest
from spacegame.models.dialogue import (
    NPC,
    DialogueResponse,
    DialogueNode,
    DialogueTree,
    DialogueManager,
)

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
