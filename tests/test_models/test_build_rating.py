"""Tests for ship build rating system."""

from spacegame.models.build_rating import GRADE_ORDER, compute_build_rating
from spacegame.models.ship_build import PlacedSlot, ShipBuild


def _make_build(weight_class: str = "small", slots: list | None = None) -> ShipBuild:
    return ShipBuild(weight_class=weight_class, placed_slots=slots or [])


def _slot(def_id: str, x: int = 0, y: int = 0) -> PlacedSlot:
    return PlacedSlot(slot_def_id=def_id, x=x, y=y)


class TestGradeOrder:
    def test_s_is_highest(self) -> None:
        assert GRADE_ORDER["S"] > GRADE_ORDER["A"]

    def test_f_is_lowest(self) -> None:
        assert GRADE_ORDER["F"] < GRADE_ORDER["D"]


class TestEmptyBuild:
    def test_empty_build_returns_ratings(self) -> None:
        build = _make_build()
        result = compute_build_rating(build, {}, {})
        assert "combat" in result
        assert "trade" in result
        assert "mobility" in result
        assert "durability" in result

    def test_empty_build_has_low_grades(self) -> None:
        build = _make_build()
        result = compute_build_rating(build, {}, {})
        for _axis, (grade, score, _feedback) in result.items():
            assert grade in GRADE_ORDER
            assert score >= 0.0


class TestCombatRating:
    def test_weapons_improve_combat(self) -> None:
        build_0 = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"), _slot("reactor_small"),
            _slot("fuel_small"),
        ])
        build_2 = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"), _slot("reactor_small"),
            _slot("fuel_small"),
            _slot("weapon_small", x=4), _slot("weapon_small", x=6),
        ])
        r0 = compute_build_rating(build_0, {}, {})
        r2 = compute_build_rating(build_2, {}, {})
        assert r2["combat"][1] > r0["combat"][1], "More weapons should improve combat score"

    def test_defense_improves_combat(self) -> None:
        build = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"), _slot("reactor_small"),
            _slot("fuel_small"),
            _slot("weapon_small", x=4), _slot("defense_small", x=6),
        ])
        result = compute_build_rating(build, {}, {})
        assert result["combat"][1] > 0


class TestTradeRating:
    def test_cargo_improves_trade(self) -> None:
        build_0 = _make_build(slots=[_slot("cockpit_scout_pod"), _slot("engine_small"),
                                      _slot("reactor_small"), _slot("fuel_small")])
        build_cargo = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"), _slot("reactor_small"),
            _slot("fuel_small"),
            _slot("cargo_small", x=4), _slot("cargo_small", x=6),
            _slot("cargo_medium", x=8),
        ])
        r0 = compute_build_rating(build_0, {}, {})
        rc = compute_build_rating(build_cargo, {}, {})
        assert rc["trade"][1] > r0["trade"][1]


class TestMobilityRating:
    def test_engines_improve_mobility(self) -> None:
        build_1e = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"),
            _slot("reactor_small"), _slot("fuel_small"),
        ])
        build_2e = _make_build(slots=[
            _slot("cockpit_scout_pod"), _slot("engine_small"), _slot("engine_small", x=4),
            _slot("reactor_small"), _slot("fuel_small"),
        ])
        r1 = compute_build_rating(build_1e, {}, {})
        r2 = compute_build_rating(build_2e, {}, {})
        assert r2["mobility"][1] > r1["mobility"][1]


class TestFeedbackText:
    def test_feedback_is_string(self) -> None:
        build = _make_build(slots=[_slot("cockpit_scout_pod")])
        result = compute_build_rating(build, {}, {})
        for _axis, (_grade, _score, feedback) in result.items():
            assert isinstance(feedback, str)

    def test_empty_combat_has_feedback(self) -> None:
        build = _make_build(slots=[_slot("cockpit_scout_pod")])
        result = compute_build_rating(build, {}, {})
        assert len(result["combat"][2]) > 0, "Should explain low combat rating"
