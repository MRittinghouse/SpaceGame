"""The SimRng vectors are the contract with the GDScript twin (SP2 spec 3.4)."""

from __future__ import annotations

from spacegame.sim_rng import SimRng
from tools.parity.rng_vectors import build_cases


class TestRngVectors:
    def test_one_case_per_key_including_unicode_and_empty(self) -> None:
        keys = [case.setup["key"] for case in build_cases()]
        assert ["a"] in keys
        assert ["Ωmega", "naïve", "星"] in keys, "a non-ASCII key must be pinned"
        assert [""] in keys
        assert ["neg", -5] in keys

    def test_first_step_is_the_seeded_state(self) -> None:
        case = next(c for c in build_cases() if c.setup["key"] == ["a"])
        first = case.steps[0]
        assert first["call"] == "state"
        assert first["result"] == list(SimRng.from_key("a").state())

    def test_every_step_records_the_state_after_it(self) -> None:
        for case in build_cases():
            for step in case.steps:
                words = step["state"]["s"]
                assert isinstance(words, list) and len(words) == 4

    def test_vectors_are_stable(self) -> None:
        assert [c.to_json("x") for c in build_cases()] == [c.to_json("x") for c in build_cases()]
