"""Combat goldens cover every template, element, complication, ultimate, and dual tech."""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models import dual_tech, dual_tech_dialogue
from spacegame.models.dual_tech import DUAL_TECH_PALETTE
from tools.parity.drivers import combat

FIGHT_CALLS = {
    "player_turn",
    "enemy_turns",
    "end_round",
    "execute_ultimate",
    "attempt_flee",
    "attempt_bribe",
    "attempt_negotiate",
}


@pytest.fixture(scope="module")
def cases() -> dict:
    return {case.name: case for case in combat.build_cases()}


def _last_fight_state(case) -> dict:  # type: ignore[no-untyped-def]
    return [s for s in case.steps if s["call"] in FIGHT_CALLS][-1]["state"]


def test_every_template_fights(cases: dict) -> None:
    for template_id in get_data_loader().enemy_templates:
        assert f"fight_{template_id}" in cases


def test_every_element_is_fired(cases: dict) -> None:
    elements = {
        move["element"]
        for c in cases.values()
        for move in c.setup["player"]["equipment_moves"]
        if move.get("element")
    }
    assert {"kinetic", "plasma", "ion", "cryo", "voltaic"} <= elements


def test_every_complication_fires(cases: dict) -> None:
    for complication_id in get_data_loader().complications:
        final = _last_fight_state(cases[f"complication_{complication_id}"])
        assert complication_id in final["fired_complication_ids"], complication_id


def test_every_ultimate_and_dual_tech_is_used(cases: dict) -> None:
    for category in get_data_loader().ship_ultimates:
        case = cases[f"ultimate_{category}"]
        assert case.steps[0]["call"] == "execute_ultimate" and case.steps[0]["result"]
    for tech in DUAL_TECH_PALETTE.values():
        case = cases[f"dual_tech_{tech.id}"]
        assert any(tech.id in s["args"][0] for s in case.steps if s["call"] == "player_turn")


def test_bosses_reach_their_last_phase(cases: dict) -> None:
    for template_id, template in get_data_loader().enemy_templates.items():
        if not template.is_boss:
            continue
        final = _last_fight_state(cases[f"fight_{template_id}"])
        assert final["enemies"][0]["current_phase_idx"] == len(template.phases) - 1, template_id


def test_no_guarded_helper_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    raised: list[str] = []
    targets = [
        (dual_tech, "tick_dual_tech_end_of_round"),
        (dual_tech, "intercept_total_commitment_hull_damage"),
        (dual_tech, "inject_available_dual_techs"),
        (dual_tech_dialogue, "check_and_mark_reveal"),
    ]
    for module, name in targets:
        original = getattr(module, name)

        def wrapper(*args, _original=original, _name=name, **kwargs):  # type: ignore[no-untyped-def]
            try:
                return _original(*args, **kwargs)
            except Exception as exc:
                raised.append(f"{_name}: {exc!r}")
                raise

        monkeypatch.setattr(module, name, wrapper)
    combat.build_cases()
    assert raised == [], "a swallowed exception would record a golden the port cannot match"


def test_cases_are_stable() -> None:
    assert [c.to_json("x") for c in combat.build_cases()] == [
        c.to_json("x") for c in combat.build_cases()
    ]


def test_dual_tech_reveals_are_logged(cases: dict) -> None:
    for tech in DUAL_TECH_PALETTE.values():
        case = cases[f"dual_tech_{tech.id}"]
        found = any(
            entry[2].endswith(" (reveal)")
            for step in case.steps
            if step["call"] == "player_turn"
            for entry in step["result"]
        )
        assert found, tech.id


def test_payout_steps_rebuild_from_setup(cases: dict) -> None:
    for case in cases.values():
        assert set(case.setup["payout_player"].keys()) == {
            "name",
            "credits",
            "system_id",
            "ship_type",
            "fuel",
        }
        for step in case.steps:
            if step["call"] in ("apply_combat_victory", "apply_combat_negotiated"):
                enemies = step["args"][0]
                assert all(set(e.keys()) == {"template_id", "dead", "fled"} for e in enemies)
                assert step["args"][1] == case.setup["seed"]


def test_negotiation_succeeds_and_pays(cases: dict) -> None:
    negotiate = cases["resolve_negotiate"]
    assert negotiate.steps[0]["call"] == "attempt_negotiate"
    assert negotiate.steps[0]["result"][0] is True
    assert _last_fight_state(negotiate)["result"] == "negotiated"
    assert any(s["call"] == "apply_combat_negotiated" for s in negotiate.steps)

    failed = cases["resolve_negotiate_failed"]
    assert failed.steps[0]["result"][0] is False

    assert "social" in negotiate.setup
    assert "social" in failed.setup


def test_momentum_gauge_is_recorded_whole(cases: dict) -> None:
    dual_tech_states = [
        step["state"]
        for tech in DUAL_TECH_PALETTE.values()
        for step in cases[f"dual_tech_{tech.id}"].steps
        if step["call"] in FIGHT_CALLS
    ]
    assert any(
        s["player"]["momentum"] is not None and s["player"]["momentum"]["overdriven_available"]
        for s in dual_tech_states
    )
    for category in get_data_loader().ship_ultimates:
        case = cases[f"ultimate_{category}"]
        assert case.setup["player"]["momentum"]["current"] == 1.0


def test_shield_mastery_is_pinned(cases: dict) -> None:
    # BB-75: the one setup with a learned skill; every other setup keeps its shape.
    setup = cases["skill_shield_mastery"].setup
    assert setup["skill_levels"] == {"shield_mastery": 3}
    assert (setup["player"]["shields"], setup["player"]["max_shields"]) == (26, 26)
    learned = [name for name, case in cases.items() if "skill_levels" in case.setup]
    assert learned == ["skill_shield_mastery"]
