"""The captain's pronouns live on the Player and survive a save (writing discipline spec 2.5)."""

from __future__ import annotations

import pytest

from spacegame.models.captain_tokens import Pronouns
from spacegame.save_manager import SaveManager
from tools.parity.snapshots import WAVE_A_PLAYER_KEYS, fresh_player, player_snapshot


def test_a_new_player_is_they_them() -> None:
    assert fresh_player().pronouns is Pronouns.THEY


@pytest.mark.parametrize("choice", list(Pronouns))
def test_the_choice_round_trips_through_a_save(choice: Pronouns) -> None:
    manager = SaveManager()
    player = fresh_player()
    player.pronouns = choice
    data = manager._serialize_player(player)
    assert data["pronouns"] == choice.value
    assert manager._deserialize_player(data).pronouns is choice


def test_a_save_without_the_key_loads_they_them() -> None:
    manager = SaveManager()
    data = manager._serialize_player(fresh_player())
    del data["pronouns"]
    assert manager._deserialize_player(data).pronouns is Pronouns.THEY


def test_an_unknown_saved_value_loads_they_them() -> None:
    manager = SaveManager()
    data = manager._serialize_player(fresh_player())
    data["pronouns"] = "xe/xem"
    assert manager._deserialize_player(data).pronouns is Pronouns.THEY


def test_the_parity_snapshot_carries_the_choice() -> None:
    """The port's PlayerIdentity saves the choice, so the goldens compare it (wave A)."""
    player = fresh_player()
    player.pronouns = Pronouns.HE
    assert "pronouns" in WAVE_A_PLAYER_KEYS
    assert player_snapshot(player)["pronouns"] == "he/him"
