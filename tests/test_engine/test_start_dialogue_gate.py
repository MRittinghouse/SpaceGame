"""Opening an NPC sets its gate flag in both flag stores (bug bash BB-38).

Polish design 6.1: "the scene is the scene whoever opens it." A Talk click goes through
``Game.start_dialogue``, which writes the NPC's ``auto_trigger_gate_flag`` into the
player's store before the dialogue manager copies that store, so the next departure's
auto-trigger does not play the scene again. This builds a whole Game, as
``test_save_flag_stores.py`` does, and pins the behaviour the AST order test only
guards by shape.
"""

from __future__ import annotations

from unittest.mock import patch

import pygame

from spacegame.constants.flags import iron_delivery_moved_on


def test_a_talk_click_plays_the_scene_once() -> None:
    """A click sets the gate in both stores, so the auto-trigger finds nothing to open."""
    from spacegame.engine.game import Game

    game = Game()
    try:
        game.initialize_new_game(player_name="Test")
        elena = game.data_loader.npcs["elena_reeves"]
        gate = elena.auto_trigger_gate_flag
        game.player.current_system_id = elena.home_system_id
        game.player.dialogue_flags[iron_delivery_moved_on()] = True
        assert gate, "Elena needs a gate flag for this test to mean anything"
        assert not game.player.dialogue_flags.get(gate), "the gate starts unset"
        assert all(
            game.player.dialogue_flags.get(flag) for flag in elena.auto_trigger_prerequisites
        ), "every prerequisite is set, so only the gate can stop the auto-trigger"

        game.start_dialogue("elena_reeves")

        assert game.player.dialogue_flags.get(gate) is True
        assert game.dialogue_manager.get_flags().get(gate) is True
        with patch.object(game, "start_dialogue") as opened:
            game._check_auto_triggers()
        opened.assert_not_called()
    finally:
        pygame.quit()
