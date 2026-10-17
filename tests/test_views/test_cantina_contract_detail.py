"""BB-11: the cantina board detail lists a contract's rewards, never its cargo hand-over.

A delivery's `deliver_cargo` and a smuggling run's `remove_cargo` take the goods the
objectives name, so the detail leaves them out, as the mission log does; route fuel shows
as its own credits line.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import Mission
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.sim_rng import stable_seed
from spacegame.views.cantina_view import CantinaView


def _generator() -> ProceduralMissionGenerator:
    dl = get_data_loader()
    return ProceduralMissionGenerator(
        dl.systems, dl.commodities, dl.enemy_templates, seed=stable_seed("player", "Tavi Okonkwo")
    )


def _texts(mission: Mission) -> list[str]:
    return [text for text, _color in CantinaView._contract_reward_lines(mission)]


def test_a_delivery_lists_its_pay_and_not_its_hand_over() -> None:
    delivery = _generator().generate_delivery("nexus_prime", game_day=1)
    assert delivery is not None
    assert any(r.reward_type == "deliver_cargo" for r in delivery.rewards)
    assert _texts(delivery) == ["  360 Credits", "  45 XP"]


def test_a_smuggling_run_lists_its_pay_and_not_its_hand_over() -> None:
    run = _generator().generate_smuggling("nexus_prime", game_day=1)
    assert any(r.reward_type == "remove_cargo" for r in run.rewards)
    credits = next(r.amount for r in run.rewards if r.reward_type == "credits")
    xp = next(r.amount for r in run.rewards if r.reward_type == "xp")
    assert _texts(run) == [f"  {credits:,} Credits", f"  {xp:,} XP"]


def test_a_salvage_lists_its_route_fuel() -> None:
    salvage = _generator().generate_salvage("nexus_prime", game_day=10)
    fuel = next(r.amount for r in salvage.rewards if r.reward_type == "route_fuel")
    assert fuel > 0
    assert _texts(salvage)[-1] == f"  {fuel:,} Credits (route fuel, once per landing)"
