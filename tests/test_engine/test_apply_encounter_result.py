"""Game-level coverage of Game._apply_encounter_result's orchestration.

``apply_encounter_outcome`` (``spacegame/models/encounter.py``) applies an outcome's
rewards to the player and returns ``EncounterEffects``; ``Game._apply_encounter_result``
turns those effects into orchestration: the politics spillover hook, dialogue flags,
the smuggling hook, bounty immunity, pending bounty combat, and the unique-encounter
seen flag. The model tests call the function directly and never see what ``game.py``
does with its result, so these tests drive the real method with only the collaborators
it reaches (``encounter_view``, ``politics_manager``, ``dialogue_manager``,
``_after_player_action``) and assert each effect lands.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call, patch

from spacegame.constants.flags import encounter_seen
from spacegame.engine.game import Game
from spacegame.models.encounter import EncounterDefinition, EncounterOutcome
from spacegame.models.mission import MissionReward
from tests.test_scenarios._helpers import fresh_player

GAME_DAY = 12


def _make_game(
    rewards: list[MissionReward], *, encounter_def: EncounterDefinition | None = None
) -> Any:
    """A ``Game`` with just enough wiring for ``_apply_encounter_result`` to run.

    Returns ``Any`` so the tests can read the mocked collaborators' call records.
    """
    with patch.object(Game, "__init__", lambda self: None):
        game: Any = Game()
    game._player = fresh_player(credits=1000)
    game._player.game_day = GAME_DAY
    game.politics_manager = MagicMock()
    game.dialogue_manager = MagicMock()
    game._after_player_action = MagicMock()
    game._mission_notifications = []
    game._bounty_immunity_until = 0
    game._pending_bounty_combat_ids = None
    game.encounter_view = MagicMock()
    game.encounter_view.chosen_outcome = EncounterOutcome("outcome", rewards)
    game.encounter_view.encounter_def = encounter_def
    return game


def _unique_definition() -> EncounterDefinition:
    return EncounterDefinition(
        id="once_only",
        encounter_type="diplomatic",
        name="Once Only",
        description="",
        choices=[],
        unique=True,
    )


class TestApplyEncounterResult:
    def test_modify_reputation_goes_through_the_politics_spillover(self) -> None:
        game = _make_game([MissionReward("modify_reputation", 15, "commerce_guild")])

        game._apply_encounter_result()

        assert game.politics_manager.apply_reputation_with_spillover.call_args_list == [
            call(game._player, "commerce_guild", 15)
        ], "the reputation reward must reach PoliticsManager's spillover path"
        assert game._player.faction_reputation.get("commerce_guild", 0) == 0, (
            "with a politics manager, the reward must not also apply directly"
        )

    def test_each_set_flag_reward_reaches_the_dialogue_manager(self) -> None:
        game = _make_game(
            [
                MissionReward("set_flag", 1, "first_flag"),
                MissionReward("set_flag", 1, "second_flag"),
            ]
        )

        game._apply_encounter_result()

        assert game.dialogue_manager.set_flag.call_args_list == [
            call("first_flag"),
            call("second_flag"),
        ]
        assert game._player.dialogue_flags["first_flag"] is True
        assert game._player.dialogue_flags["second_flag"] is True

    def test_criminal_heat_fires_the_smuggling_hook_once_per_outcome(self) -> None:
        game = _make_game(
            [MissionReward("add_criminal_heat", 10), MissionReward("add_criminal_heat", 5)]
        )

        game._apply_encounter_result()

        assert game._after_player_action.call_args_list == [call("smuggling_caught")], (
            "two heat rewards in one outcome must fire smuggling_caught exactly once"
        )
        assert game._player.times_caught_smuggling == 2

    def test_bounty_immunity_runs_from_the_current_game_day(self) -> None:
        game = _make_game([MissionReward("bounty_immunity", 7)])

        game._apply_encounter_result()

        assert game._bounty_immunity_until == GAME_DAY + 7

    def test_bounty_combat_ids_are_the_split_target(self) -> None:
        game = _make_game([MissionReward("start_bounty_combat", 0, "pirate_raider,pirate_scout")])

        game._apply_encounter_result()

        assert game._pending_bounty_combat_ids == ["pirate_raider", "pirate_scout"]

    def test_a_unique_encounter_sets_its_seen_flag(self) -> None:
        game = _make_game([MissionReward("credits", 10)], encounter_def=_unique_definition())

        game._apply_encounter_result()

        flag = encounter_seen("once_only")
        assert game._player.dialogue_flags.get(flag) is True
        assert game.dialogue_manager.set_flag.call_args_list == [call(flag)]

    def test_an_outcome_without_follow_ups_leaves_the_orchestration_state_alone(self) -> None:
        game = _make_game([MissionReward("credits", 10)])

        game._apply_encounter_result()

        assert game._player.credits == 1010
        game._after_player_action.assert_not_called()
        game.dialogue_manager.set_flag.assert_not_called()
        game.politics_manager.apply_reputation_with_spillover.assert_not_called()
        assert game._bounty_immunity_until == 0
        assert game._pending_bounty_combat_ids is None
