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

    def test_cap_blocks_a_rolled_day(self) -> None:
        cases = _named(galaxy)
        run_steps = cases["events_days_1_200"].steps
        day_40 = next(s for s in run_steps if s["args"] == [40])
        assert day_40["result"]["id"] == "forgeworks_strike_40"

        cap_steps = cases["cap_blocks_roll"].steps
        blocked = next(s for s in cap_steps if s["args"] == [40])
        assert blocked["result"] is None
        assert len(blocked["state"]["active"]) == 2

        freed = next(s for s in cap_steps if s["args"] == [52])
        assert freed["result"]["id"] == "collective_symposium_52"


class TestCrew:
    def test_failed_recruit_and_loyalty_flags(self) -> None:
        steps = _named(crew)["companions"].steps
        recruits = [s["result"] for s in steps if s["call"] == "recruit"]
        assert any(r[0] is False for r in recruits)
        flags = [s["result"] for s in steps if s["call"] == "adjust_loyalty"]
        assert any(flags), "crossing 50/70/85 yields flags"

    def test_triggers_record_levelups_and_flags(self) -> None:
        steps = _named(crew)["triggers"].steps
        trade_results = [s["result"] for s in steps if s["call"] == "on_trades"]
        assert any(
            levelups
            and all("reached level" in msg for msg in levelups)
            and flags
            and all(flag.startswith("crew_loyalty_") for flag in flags)
            for levelups, flags in trade_results
        )
        jump_results = [s["result"] for s in steps if s["call"] == "on_jumps"]
        assert any(jump_results), "some on_jumps step records level-ups"

    def test_leadership_offset_and_floor_reset(self) -> None:
        steps = _named(crew)["leadership"].steps

        def loyalty(step: dict) -> int:  # type: ignore[type-arg]
            return step["state"]["roster"]["members"]["elena_reeves"]["loyalty"]

        assert steps[6]["result"] == []
        assert loyalty(steps[6]) == 0

        assert steps[8]["result"] == ["crew_loyalty_elena_reeves_50"]
        assert loyalty(steps[8]) == 45

        assert steps[10]["result"] == ["crew_loyalty_elena_reeves_50"]
        assert loyalty(steps[10]) == 55


def test_cases_are_stable() -> None:
    for module in (skills, galaxy, crew):
        first = [c.to_json("x") for c in module.build_cases()]
        assert first == [c.to_json("x") for c in module.build_cases()]
