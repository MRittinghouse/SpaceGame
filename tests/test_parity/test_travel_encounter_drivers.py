"""Travel and encounter goldens (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
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
    assert {"hostile", "shakedown"} <= kinds


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
