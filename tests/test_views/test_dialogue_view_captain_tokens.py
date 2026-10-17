"""The dialogue view renders the captain's tokens (writing discipline spec 2.5 to 2.7)."""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.data_loader import get_data_loader
from spacegame.models.captain_tokens import Pronouns
from spacegame.models.dialogue import (
    DialogueManager,
    DialogueNode,
    DialogueResponse,
    DialogueTree,
)
from spacegame.models.player import Player
from spacegame.views.dialogue_view import DialogueView
from tools.parity.snapshots import fresh_player


@pytest.fixture(autouse=True, scope="module")
def _display() -> None:
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _tree() -> DialogueTree:
    node = DialogueNode(
        id="greeting",
        speaker_id="officer_larsen",
        text="I need your registration, {sir}. {They}{v:'s|'re} next.",
        responses=[DialogueResponse(text="[Hand over {their} papers.]", next_node_id=None)],
        subtext="{They} {v:holds|hold} the papers out.",
    )
    return DialogueTree(id="tokens", start_node_id="greeting", nodes={"greeting": node})


def _record_tree() -> DialogueTree:
    node = DialogueNode(
        id="fare",
        speaker_id="officer_larsen",
        text="{They} {v:owes|owe} the {fee:bill_of_landing} credit fee.",
        responses=[DialogueResponse(text="{pay:the_informant} credits works.", next_node_id=None)],
        subtext="{fee:bill_of_landing} credits is a day's trade.",
    )
    return DialogueTree(id="records", start_node_id="fare", nodes={"fare": node})


def _view(player: Optional[Player], tree: Optional[DialogueTree] = None) -> DialogueView:
    manager = DialogueManager()
    if player is not None:
        manager.set_politics_manager(MagicMock(), player)
    manager.start_dialogue(tree if tree is not None else _tree())
    view = DialogueView(
        ui_manager=pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT)),
        dialogue_manager=manager,
        data_loader=get_data_loader(),
    )
    view.on_enter()
    return view


@pytest.mark.parametrize(
    ("choice", "text", "reply", "subtext"),
    [
        (
            Pronouns.HE,
            "I need your registration, sir. He's next.",
            "[Hand over his papers.]",
            "* He holds the papers out.",
        ),
        (
            Pronouns.SHE,
            "I need your registration, ma'am. She's next.",
            "[Hand over her papers.]",
            "* She holds the papers out.",
        ),
        (
            Pronouns.THEY,
            "I need your registration, Captain. They're next.",
            "[Hand over their papers.]",
            "* They hold the papers out.",
        ),
    ],
)
def test_node_text_replies_and_subtext_render_for_the_choice(
    choice: Pronouns, text: str, reply: str, subtext: str
) -> None:
    player = fresh_player()
    player.pronouns = choice
    view = _view(player)
    try:
        assert view._full_text == text
        assert [button.text for button in view._response_buttons] == [reply]
        node = view.dialogue_manager.get_current_node()
        assert node is not None
        assert view._subtext_line(node) == subtext
    finally:
        view.on_exit()


def test_the_subtext_printer_draws_the_rendered_line() -> None:
    """What the font draws is the rendered line, not the node's raw tokens."""
    player = fresh_player()
    player.pronouns = Pronouns.SHE
    view = _view(player)
    try:
        view.dialogue_manager.set_flag("empathic_read_active", True)
        view._text_complete = True
        view._subtext_font = MagicMock(wraps=view._subtext_font)
        view._render_subtext(pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)))
        drawn = [call.args[0] for call in view._subtext_font.render.call_args_list]
        assert drawn == ["* She holds the papers out."]
    finally:
        view.on_exit()


def test_the_intro_renders_without_a_player() -> None:
    """The intro narration plays before any player exists: they/them."""
    view = _view(None)
    try:
        assert view._full_text == "I need your registration, Captain. They're next."
    finally:
        view.on_exit()


def test_the_manager_exposes_the_player_it_addresses() -> None:
    manager = DialogueManager()
    assert manager.player is None
    player = fresh_player()
    manager.set_politics_manager(MagicMock(), player)
    assert manager.player is player


def test_the_record_tokens_render_from_the_loaders_missions() -> None:
    """Writing spec 3.7: the node text, the replies and the subtext print a mission's reward."""
    player = fresh_player()
    player.pronouns = Pronouns.SHE
    view = _view(player, _record_tree())
    try:
        assert view._full_text == "She owes the 250 credit fee."
        assert [button.text for button in view._response_buttons] == ["350 credits works."]
        node = view.dialogue_manager.get_current_node()
        assert node is not None
        assert view._subtext_line(node) == "* 250 credits is a day's trade."
    finally:
        view.on_exit()
