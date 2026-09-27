"""Skills, galaxy, and crew goldens cover what SP3-c ports (SP3 spec 6.2)."""

from __future__ import annotations

from tools.parity.drivers import crew, galaxy, skills


def _named(module) -> dict:  # type: ignore[no-untyped-def]
    return {case.name: case for case in module.build_cases()}


class TestSkills:
    def test_catalog_and_every_tree(self) -> None:
        cases = _named(skills)
        assert len(cases["catalog"].steps[0]["result"]) == 89
        for tree in ("commerce", "combat", "exploration", "leadership", "social", "industry"):
            assert f"learn_{tree}" in cases

    def test_every_bonus_type_is_recorded(self) -> None:
        steps = _named(skills)["all_bonuses_maxed"].steps
        assert len(steps) == 88


class TestGalaxy:
    def test_run_and_chain(self) -> None:
        cases = _named(galaxy)
        run = cases["events_days_1_200"]
        assert any(step["result"] is not None for step in run.steps)
        chain = cases["strike_chain"]
        started = [s["result"] for s in chain.steps if s["result"] is not None]
        assert any(event["chain_step"] == 1 for event in started)


class TestCrew:
    def test_failed_recruit_and_loyalty_flags(self) -> None:
        steps = _named(crew)["companions"].steps
        recruits = [s["result"] for s in steps if s["call"] == "recruit"]
        assert any(r[0] is False for r in recruits)
        flags = [s["result"] for s in steps if s["call"] == "adjust_loyalty"]
        assert any(flags), "crossing 50/70/85 yields flags"


def test_cases_are_stable() -> None:
    for module in (skills, galaxy, crew):
        first = [c.to_json("x") for c in module.build_cases()]
        assert first == [c.to_json("x") for c in module.build_cases()]
