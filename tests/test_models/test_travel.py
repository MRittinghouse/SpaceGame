"""Jump rules lifted from GalaxyMapView (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.encounter import EncounterRef
from spacegame.models.travel import (
    fuel_after_jump,
    jump_fuel_cost,
    jump_hull_restore,
    post_process_encounter,
)
from spacegame.sim_rng import SimRng


def _systems() -> dict:
    dl = get_data_loader()
    dl.load_all()
    return dl.systems


def _hostile(demand: int = 0, def_id: str = "") -> EncounterRef:
    return EncounterRef(
        enemy_template_ids=["pirate_scout"],
        encounter_seed=7,
        encounter_type="shakedown" if demand else "hostile",
        shakedown_demand=demand,
        encounter_def_id=def_id,
    )


class TestFuel:
    def test_matches_the_old_view_formula(self) -> None:
        systems = _systems()
        a, b = systems["nexus_prime"], systems["forgeworks"]
        base = a.fuel_cost_to(b, 10)
        assert jump_fuel_cost(a, b, 10, 0.0) == base
        assert jump_fuel_cost(a, b, 10, 0.25) == max(1, int(base * (1 - 0.25)))

    def test_reserve_floor(self) -> None:
        assert fuel_after_jump(0, 1.0) == 1
        assert fuel_after_jump(0, 0.0) == 0
        assert fuel_after_jump(5, 1.0) == 5


class TestPostProcess:
    def test_no_mods_leaves_the_encounter_alone(self) -> None:
        enc = _hostile()
        assert post_process_encounter(enc, {}, safe_passage=True, game_day=1, system_id="x") is enc

    def test_shakedown_scaling_keeps_every_other_field(self) -> None:
        enc = _hostile(demand=150, def_id="kept")
        out = post_process_encounter(
            enc, {"shakedown_multiplier": 2.0}, safe_passage=False, game_day=1, system_id="x"
        )
        assert out is not None
        assert out.shakedown_demand == 300
        assert out.encounter_def_id == "kept"
        assert out.encounter_seed == enc.encounter_seed

    def test_safe_passage_cancels_hostiles(self) -> None:
        out = post_process_encounter(
            _hostile(), {"protection_chance": 0}, safe_passage=True, game_day=1, system_id="x"
        )
        assert out is None

    def test_protection_roll_is_keyed(self) -> None:
        mods = {"protection_chance": 30}
        cancelled = 0
        for day in range(1, 201):
            out = post_process_encounter(
                _hostile(), mods, safe_passage=False, game_day=day, system_id="nexus_prime"
            )
            roll = SimRng.from_key("protection", day, "nexus_prime").randint(0, 99)
            assert (out is None) == (roll < 30)
            cancelled += out is None
        assert 30 < cancelled < 90, "about 30% of 200 rolls cancel"


class TestHullRestore:
    def test_restore(self) -> None:
        assert jump_hull_restore(100, 0.0) == 0
        assert jump_hull_restore(100, 0.05) == 5
        assert jump_hull_restore(10, 0.01) == 1
