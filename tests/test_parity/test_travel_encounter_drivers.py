"""Travel and encounter goldens (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.encounter import _NON_HOSTILE_WEIGHTS
from tools.parity.drivers import encounters, travel


def _named(module) -> dict:  # type: ignore[no-untyped-def]
    return {case.name: case for case in module.build_cases()}


def test_travel_covers_every_pair_and_every_mod() -> None:
    cases = _named(travel)
    systems = get_data_loader().systems
    pairs = {tuple(s["args"][:2]) for s in cases["fuel"].steps}
    assert len(pairs) == len(systems) * (len(systems) - 1)
    results = [s["result"] for s in cases["post_process"].steps]
    assert any(r is None for r in results) and any(r is not None for r in results)


def test_a_roll_case_per_system_with_every_encounter_kind() -> None:
    cases = _named(encounters)
    for system_id in get_data_loader().systems:
        assert f"roll_{system_id}" in cases
    kinds = {
        s["result"]["encounter_type"]
        for name, c in cases.items()
        if name.startswith("roll_")
        for s in c.steps
        if s["result"] is not None
    }
    expected = {
        "hostile",
        *_NON_HOSTILE_WEIGHTS["moderate"],
        *_NON_HOSTILE_WEIGHTS["dangerous"],
    }
    assert expected <= kinds, f"roll goldens never draw {sorted(expected - kinds)}"


def test_every_definition_choice_is_resolved() -> None:
    cases = _named(encounters)
    recorded = {
        (s["args"][0], s["args"][1])
        for name, c in cases.items()
        if name.startswith("outcomes_")
        for s in c.steps
    }
    for definition in get_data_loader().encounter_definitions:
        for choice in definition.choices:
            assert (definition.id, choice.id) in recorded


def test_cases_are_stable() -> None:
    for module in (travel, encounters):
        assert [c.to_json("x") for c in module.build_cases()] == [
            c.to_json("x") for c in module.build_cases()
        ]


def test_post_process_scales_a_shakedown() -> None:
    cases = _named(travel)
    shakedown_steps = [
        s
        for s in cases["post_process"].steps
        if s["args"][0] is not None and s["args"][0]["encounter_type"] == "shakedown"
    ]
    assert shakedown_steps
    for step in shakedown_steps:
        rolled = step["args"][0]
        result = step["result"]
        assert result is not None
        for key, value in rolled.items():
            if key == "shakedown_demand":
                continue
            assert result[key] == value
    assert any(
        step["result"]["shakedown_demand"] != step["args"][0]["shakedown_demand"]
        for step in shakedown_steps
    )
    halved_odd = [
        step
        for step in shakedown_steps
        if step["args"][1].get("shakedown_multiplier") == 0.5
        and step["args"][0]["shakedown_demand"] % 2 == 1
    ]
    assert halved_odd
    assert all(
        step["result"]["shakedown_demand"] == step["args"][0]["shakedown_demand"] // 2
        for step in halved_odd
    )


def test_setups_rebuild_every_case() -> None:
    cases = _named(encounters)
    knob_keys = {
        "player_level",
        "defensive_identity",
        "encounter_reduction",
        "anomaly_sense",
        "anomaly_chance_bonus",
    }
    player_keys = {"name", "credits", "system_id", "ship_type", "fuel"}
    for name, case in cases.items():
        if name.startswith("roll_"):
            system_id = name[len("roll_") :]
            assert case.setup["system_id"] == system_id
            profiles = case.setup["profiles"]
            for step in case.steps:
                assert step["args"][0] in profiles
            for knobs in profiles.values():
                assert set(knobs) == knob_keys
        elif name == "select":
            assert {"player_level", "system_id", "dialogue_flags", "resolved_captain_ids"} <= set(
                case.setup
            )
        elif name.startswith("outcomes_"):
            assert set(case.setup["player"]) == player_keys
            assert "cargo" in case.setup
        elif name == "skill_checks":
            profiles = case.setup["social_profiles"]
            for step in case.steps:
                assert step["args"][0] in profiles
        elif name == "captains":
            days = sorted({step["args"][2] for step in case.steps})
            assert case.setup["days"] == days
