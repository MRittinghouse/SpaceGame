"""The dialogue manager's entry node and F-45 (polish design 3.1; SpaceGame register F-015)."""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.dialogue import (
    DialogueManager,
    DialogueNode,
    DialogueResponse,
    DialogueTree,
)


def _tree(gain: int = 10) -> DialogueTree:
    start = DialogueNode(
        id="start",
        speaker_id="elena_reeves",
        text="First.",
        responses=[
            DialogueResponse(
                text="Thank you.",
                next_node_id=None,
                crew_loyalty_changes={"elena_reeves": gain},
            )
        ],
    )
    ask_again = DialogueNode(
        id="ask_again",
        speaker_id="elena_reeves",
        text="Again.",
        responses=[DialogueResponse(text="Not yet.", next_node_id=None)],
    )
    return DialogueTree(
        id="test_tree", start_node_id="start", nodes={"start": start, "ask_again": ask_again}
    )


class TestTheEntryNode:
    def test_a_dialogue_opens_at_its_entry_node(self) -> None:
        manager = DialogueManager()
        manager.start_dialogue(_tree(), entry_node_id="ask_again")
        node = manager.get_current_node()
        assert node is not None and node.id == "ask_again"

    def test_without_an_entry_node_a_dialogue_opens_at_its_start(self) -> None:
        manager = DialogueManager()
        manager.start_dialogue(_tree())
        node = manager.get_current_node()
        assert node is not None and node.id == "start"

    def test_an_unknown_entry_node_is_refused(self) -> None:
        manager = DialogueManager()
        with pytest.raises(ValueError, match="No node nowhere in test_tree"):
            manager.start_dialogue(_tree(), entry_node_id="nowhere")
        assert not manager.is_active


class TestF45:
    def test_a_dialogue_loyalty_gain_keeps_its_threshold_flag(self) -> None:
        loader = get_data_loader()
        loader.load_all()
        roster = CrewRoster(loader.crew_templates)
        ok, msg = roster.recruit("elena_reeves", 4)
        assert ok, msg
        roster.adjust_loyalty("elena_reeves", 15)  # 30 to 45
        manager = DialogueManager()
        manager.set_crew_roster(roster)
        manager.start_dialogue(_tree())
        manager.select_response(0)
        assert manager.get_flag("crew_loyalty_elena_reeves_50"), (
            "A loyalty gain made in dialogue that crosses 50 keeps its flag (F-45)"
        )

    def test_a_gain_that_crosses_two_marks_keeps_both_flags(self) -> None:
        loader = get_data_loader()
        loader.load_all()
        roster = CrewRoster(loader.crew_templates)
        ok, msg = roster.recruit("elena_reeves", 4)
        assert ok, msg
        roster.adjust_loyalty("elena_reeves", 35)  # 30 to 65
        manager = DialogueManager()
        manager.set_crew_roster(roster)
        manager.start_dialogue(_tree(gain=25))
        manager.select_response(0)
        assert manager.get_flag("crew_loyalty_elena_reeves_70")
        assert manager.get_flag("crew_loyalty_elena_reeves_85"), (
            "A +25 reply from 65 crosses 70 and 85 and keeps both flags (SpaceGame F-015)"
        )
