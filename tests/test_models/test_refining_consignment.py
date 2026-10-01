"""Bug bash BB-1: refining never draws a mission's accept cargo."""

from __future__ import annotations

from spacegame.models.refining import Recipe, RefiningSession, start_on_free_cargo


def _recipe() -> Recipe:
    return Recipe(
        id="test_smelt",
        name="Test Smelt",
        description="A test recipe.",
        inputs={"iron_ore": 4},
        outputs={"common_metals": 1},
        processing_time=1.0,
        location_ids=["forgeworks"],
    )


def test_a_recipe_never_draws_consigned_ore() -> None:
    session = RefiningSession([_recipe()], "forgeworks")
    cargo = {"iron_ore": 10}
    ok, msg = start_on_free_cargo(session, _recipe(), cargo, {}, 1)
    assert not ok
    assert msg == "Missing: 4 iron_ore"
    assert cargo == {"iron_ore": 10}


def test_a_recipe_takes_the_captains_own_units() -> None:
    session = RefiningSession([_recipe()], "forgeworks")
    cargo = {"iron_ore": 14}
    ok, _msg = start_on_free_cargo(session, _recipe(), cargo, {"iron_ore": 4}, 1)
    assert ok
    assert cargo == {"iron_ore": 10}


def test_a_batch_counts_the_free_hold() -> None:
    session = RefiningSession([_recipe()], "forgeworks")
    cargo = {"iron_ore": 18}
    ok, msg = start_on_free_cargo(session, _recipe(), cargo, {"iron_ore": 8}, 3)
    assert not ok
    assert msg == "Need 12 iron_ore, have 8"
    ok, _msg = start_on_free_cargo(session, _recipe(), cargo, {"iron_ore": 8}, 2)
    assert ok
    assert cargo == {"iron_ore": 10}
