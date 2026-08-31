"""Tests for the A2-8 dilemma engine (models/dilemma.py).

Covers:
- ``DilemmaOutcome`` / ``Dilemma`` / ``DilemmaRuntimeState`` /
  ``DilemmaCheckResult`` dataclasses and their save round-trips.
- Pure predicates ``check_collision`` / ``check_telegraph``.
- Model-layer coordinator ``check_dilemmas`` that classifies loaded
  dilemmas into newly_telegraphed / re_telegraphed / newly_collided
  from a player's investment + runtime state.
- ``DataLoader.load_dilemmas`` glob + duplicate-id behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.models.dilemma import (
    Dilemma,
    DilemmaCheckResult,
    DilemmaOutcome,
    DilemmaRuntimeState,
    check_collision,
    check_dilemmas,
    check_telegraph,
)
from spacegame.models.lens_investment import LensInvestment


def _outcome(winning_lens: str, closes: list[str] | None = None) -> DilemmaOutcome:
    return DilemmaOutcome(
        winning_lens_id=winning_lens,
        closes=list(closes or [winning_lens]),
        tier_unlocks=[],
        outcome_flag=f"outcome_{winning_lens}",
        narration_summary=f"Chose {winning_lens}.",
    )


def _pair_dilemma() -> Dilemma:
    return Dilemma(
        id="d_test_pair",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["one", "two", "three"],
        outcomes=[_outcome("wealth"), _outcome("community")],
    )


def _triangle_dilemma() -> Dilemma:
    return Dilemma(
        id="d_test_triangle",
        poles=["order", "freedom", "faith"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["alpha", "beta"],
        outcomes=[_outcome("order"), _outcome("freedom"), _outcome("faith")],
    )


def _player_stub(investment: dict[str, int], runtime: DilemmaRuntimeState | None = None):
    """Minimal duck-typed player accepted by ``check_dilemmas``."""

    class _Stub:
        pass

    stub = _Stub()
    stub.lens_investment = LensInvestment(_values=dict(investment))
    stub.dilemma_state = runtime if runtime is not None else DilemmaRuntimeState()
    return stub


class TestCheckCollisionPair:
    """AC1 + AC2: two-pole collision predicate."""

    def test_returns_false_when_only_one_pole_at_threshold(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 80, "community": 0})
        assert check_collision(dilemma, investment) is False

    def test_returns_false_when_only_one_pole_far_above_threshold(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 200, "community": 0})
        assert check_collision(dilemma, investment) is False, (
            "Collision must count poles individually above threshold, "
            "not sum them — 200/0 is one pole, not a collision."
        )

    def test_returns_true_when_both_poles_at_threshold(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 80, "community": 80})
        assert check_collision(dilemma, investment) is True

    def test_result_independent_of_which_pole_is_higher(self) -> None:
        dilemma = _pair_dilemma()
        wealth_higher = LensInvestment(_values={"wealth": 120, "community": 90})
        community_higher = LensInvestment(_values={"wealth": 90, "community": 120})
        assert check_collision(dilemma, wealth_higher) is True
        assert check_collision(dilemma, community_higher) is True


class TestCheckTelegraphPair:
    """AC3: telegraph fires strictly before collision."""

    def test_telegraph_true_at_or_above_telegraph_threshold(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 55, "community": 55})
        assert check_telegraph(dilemma, investment) is True

    def test_telegraph_true_between_telegraph_and_collision(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 60, "community": 60})
        assert check_telegraph(dilemma, investment) is True
        assert check_collision(dilemma, investment) is False

    def test_collision_true_at_or_above_collision_threshold(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 85, "community": 85})
        assert check_telegraph(dilemma, investment) is True
        assert check_collision(dilemma, investment) is True

    def test_telegraph_false_with_one_pole_below(self) -> None:
        dilemma = _pair_dilemma()
        investment = LensInvestment(_values={"wealth": 100, "community": 0})
        assert check_telegraph(dilemma, investment) is False


class TestCheckCollisionTriangle:
    """AC6: three-pole synthetic fixture with ``collision_requires=2``."""

    def test_two_of_three_above_threshold_triggers(self) -> None:
        dilemma = _triangle_dilemma()
        investment = LensInvestment(_values={"order": 90, "freedom": 90, "faith": 0})
        assert check_collision(dilemma, investment) is True

    def test_only_one_of_three_above_does_not_trigger(self) -> None:
        dilemma = _triangle_dilemma()
        investment = LensInvestment(_values={"order": 90, "freedom": 0, "faith": 0})
        assert check_collision(dilemma, investment) is False

    def test_all_three_above_still_triggers(self) -> None:
        dilemma = _triangle_dilemma()
        investment = LensInvestment(_values={"order": 90, "freedom": 90, "faith": 90})
        assert check_collision(dilemma, investment) is True


class TestDilemmaOutcomeRoundTrip:
    def test_round_trip_preserves_all_fields(self) -> None:
        outcome = DilemmaOutcome(
            winning_lens_id="wealth",
            closes=["wealth", "community"],
            tier_unlocks=["wealth.tier2"],
            outcome_flag="wealth_win",
            narration_summary="A ledger closed, a well opened.",
        )
        restored = DilemmaOutcome.from_dict(outcome.to_dict())
        assert restored == outcome


class TestDilemmaRoundTrip:
    def test_round_trip_preserves_all_fields(self) -> None:
        dilemma = _pair_dilemma()
        restored = Dilemma.from_dict(dilemma.to_dict())
        assert restored.id == dilemma.id
        assert restored.poles == dilemma.poles
        assert restored.collision_requires == dilemma.collision_requires
        assert restored.telegraph_threshold == dilemma.telegraph_threshold
        assert restored.collision_threshold == dilemma.collision_threshold
        assert restored.telegraph_npc_id == dilemma.telegraph_npc_id
        assert restored.telegraph_lines == dilemma.telegraph_lines
        assert len(restored.outcomes) == len(dilemma.outcomes)
        assert restored.outcomes[0].winning_lens_id == "wealth"


class TestDilemmaRuntimeStateRoundTrip:
    """AC7 (partial — the full save-load scenario lives in test_scenario_save_load.py)."""

    def test_default_round_trip_is_empty(self) -> None:
        state = DilemmaRuntimeState()
        restored = DilemmaRuntimeState.from_dict(state.to_dict())
        assert restored.telegraphed == set()
        assert restored.telegraph_cursor == {}
        assert restored.resolved == {}
        assert restored.closed_lenses == set()

    def test_round_trip_preserves_telegraph_cursor(self) -> None:
        state = DilemmaRuntimeState(
            telegraphed={"d_1", "d_2"},
            telegraph_cursor={"d_1": 2, "d_2": 5},
            resolved={"d_1": "wealth"},
            closed_lenses={"community"},
        )
        restored = DilemmaRuntimeState.from_dict(state.to_dict())
        assert restored.telegraphed == {"d_1", "d_2"}
        assert restored.telegraph_cursor == {"d_1": 2, "d_2": 5}
        assert restored.resolved == {"d_1": "wealth"}
        assert restored.closed_lenses == {"community"}

    def test_from_dict_missing_keys_defaults_safely(self) -> None:
        restored = DilemmaRuntimeState.from_dict({})
        assert restored.telegraphed == set()
        assert restored.telegraph_cursor == {}
        assert restored.resolved == {}
        assert restored.closed_lenses == set()

    def test_from_dict_none_defaults_safely(self) -> None:
        restored = DilemmaRuntimeState.from_dict(None)
        assert restored.telegraphed == set()
        assert restored.telegraph_cursor == {}
        assert restored.resolved == {}
        assert restored.closed_lenses == set()


class TestCheckDilemmasClassification:
    def test_below_telegraph_is_untouched(self) -> None:
        dilemma = _pair_dilemma()
        stub = _player_stub({"wealth": 30, "community": 30})
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result == DilemmaCheckResult(
            newly_telegraphed=[], re_telegraphed=[], newly_collided=[]
        )

    def test_first_qualifying_pass_is_newly_telegraphed(self) -> None:
        dilemma = _pair_dilemma()
        stub = _player_stub({"wealth": 60, "community": 60})
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result.newly_telegraphed == [dilemma.id]
        assert result.re_telegraphed == []
        assert result.newly_collided == []

    def test_second_pass_moves_to_re_telegraphed(self) -> None:
        dilemma = _pair_dilemma()
        runtime = DilemmaRuntimeState(telegraphed={dilemma.id})
        stub = _player_stub({"wealth": 60, "community": 60}, runtime=runtime)
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result.newly_telegraphed == []
        assert result.re_telegraphed == [dilemma.id]
        assert result.newly_collided == []

    def test_first_pass_that_crosses_collision_reports_both(self) -> None:
        """Documented gotcha: a single action can jump investment past both
        thresholds. The engine must fire the telegraph *and* the modal in
        that order — this classifier reports both, the caller decides order."""
        dilemma = _pair_dilemma()
        stub = _player_stub({"wealth": 90, "community": 90})
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result.newly_telegraphed == [dilemma.id]
        assert result.newly_collided == [dilemma.id]

    def test_previously_telegraphed_still_collides_when_thresholds_cross(self) -> None:
        dilemma = _pair_dilemma()
        runtime = DilemmaRuntimeState(telegraphed={dilemma.id})
        stub = _player_stub({"wealth": 90, "community": 90}, runtime=runtime)
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result.newly_telegraphed == []
        assert result.re_telegraphed == [dilemma.id]
        assert result.newly_collided == [dilemma.id]

    def test_resolved_dilemmas_are_skipped(self) -> None:
        dilemma = _pair_dilemma()
        runtime = DilemmaRuntimeState(
            telegraphed={dilemma.id},
            resolved={dilemma.id: "wealth"},
        )
        stub = _player_stub({"wealth": 200, "community": 200}, runtime=runtime)
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result == DilemmaCheckResult(
            newly_telegraphed=[], re_telegraphed=[], newly_collided=[]
        )

    def test_empty_registry_returns_empty_result(self) -> None:
        stub = _player_stub({"wealth": 200, "community": 200})
        result = check_dilemmas(stub, {})
        assert result == DilemmaCheckResult(
            newly_telegraphed=[], re_telegraphed=[], newly_collided=[]
        )

    def test_triangle_dilemma_classifies_when_exactly_two_cross(self) -> None:
        dilemma = _triangle_dilemma()
        stub = _player_stub({"order": 90, "freedom": 90, "faith": 0})
        result = check_dilemmas(stub, {dilemma.id: dilemma})
        assert result.newly_telegraphed == [dilemma.id]
        assert result.newly_collided == [dilemma.id]


class TestLoadDilemmas:
    """AC (Task 3): DataLoader.load_dilemmas() mirrors load_lenses()."""

    def _write_dilemma_file(self, tmp_path: Path, filename: str, dilemma: dict) -> None:
        dilemmas_dir = tmp_path / "narrative" / "dilemmas"
        dilemmas_dir.mkdir(parents=True, exist_ok=True)
        (dilemmas_dir / filename).write_text(json.dumps({"dilemmas": [dilemma]}), encoding="utf-8")

    def _dilemma_dict(self, dilemma_id: str = "d_test", pole_a: str = "wealth") -> dict:
        return {
            "id": dilemma_id,
            "poles": [pole_a, "community"],
            "collision_requires": 2,
            "telegraph_threshold": 55,
            "collision_threshold": 80,
            "telegraph_npc_id": "priya_osei",
            "telegraph_lines": ["only one"],
            "outcomes": [
                {
                    "winning_lens_id": pole_a,
                    "closes": [pole_a],
                    "tier_unlocks": [],
                    "outcome_flag": f"outcome_{pole_a}",
                    "narration_summary": "test",
                },
                {
                    "winning_lens_id": "community",
                    "closes": ["community"],
                    "tier_unlocks": [],
                    "outcome_flag": "outcome_community",
                    "narration_summary": "test",
                },
            ],
        }

    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        """No data/narrative/dilemmas/ directory must not crash the loader."""
        from spacegame.data_loader import DataLoader

        loader = DataLoader(data_dir=tmp_path)
        loader.load_dilemmas()
        assert loader.dilemmas == {}

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        """An existing but empty dilemmas directory returns {} rather than raising."""
        from spacegame.data_loader import DataLoader

        (tmp_path / "narrative" / "dilemmas").mkdir(parents=True)
        loader = DataLoader(data_dir=tmp_path)
        loader.load_dilemmas()
        assert loader.dilemmas == {}

    def test_single_valid_file_loads(self, tmp_path: Path) -> None:
        from spacegame.data_loader import DataLoader

        self._write_dilemma_file(tmp_path, "d_wealth_community.json", self._dilemma_dict())

        loader = DataLoader(data_dir=tmp_path)
        loader.load_dilemmas()

        assert set(loader.dilemmas.keys()) == {"d_test"}
        d = loader.dilemmas["d_test"]
        assert isinstance(d, Dilemma)
        assert d.poles == ["wealth", "community"]
        assert d.telegraph_threshold == 55
        assert d.collision_threshold == 80
        assert len(d.outcomes) == 2

    def test_two_files_load_both(self, tmp_path: Path) -> None:
        from spacegame.data_loader import DataLoader

        self._write_dilemma_file(tmp_path, "a.json", self._dilemma_dict("d_a", "wealth"))
        self._write_dilemma_file(tmp_path, "b.json", self._dilemma_dict("d_b", "order"))

        loader = DataLoader(data_dir=tmp_path)
        loader.load_dilemmas()
        assert set(loader.dilemmas.keys()) == {"d_a", "d_b"}

    def test_duplicate_id_across_files_raises(self, tmp_path: Path) -> None:
        from spacegame.data_loader import DataLoader

        self._write_dilemma_file(tmp_path, "a.json", self._dilemma_dict("dupe"))
        self._write_dilemma_file(tmp_path, "b.json", self._dilemma_dict("dupe"))

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="dupe"):
            loader.load_dilemmas()

    def test_real_data_directory_loads_cleanly(self) -> None:
        """A2-8 ships the empty directory + .gitkeep; production load returns {}."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        loader.load_all()
        assert isinstance(loader.dilemmas, dict)


class TestDilemmaFlagHelpers:
    """AC (Task 4): the three parameterized helpers round-trip cleanly."""

    def test_dilemma_telegraphed_round_trip(self) -> None:
        from spacegame.constants.flags import (
            dilemma_telegraphed,
            extract_dilemma_telegraphed_id,
        )

        for dilemma_id in ("d_wealth_community", "d_order_freedom_faith", "d_stability_kin"):
            flag = dilemma_telegraphed(dilemma_id)
            assert extract_dilemma_telegraphed_id(flag) == dilemma_id

    def test_dilemma_telegraphed_canonical_prefix(self) -> None:
        from spacegame.constants.flags import dilemma_telegraphed

        assert dilemma_telegraphed("d_test") == "dilemma_telegraphed_d_test"

    def test_dilemma_telegraphed_returns_none_for_non_matching(self) -> None:
        from spacegame.constants.flags import extract_dilemma_telegraphed_id

        assert extract_dilemma_telegraphed_id("some_other_flag") is None
        assert extract_dilemma_telegraphed_id("") is None

    def test_dilemma_resolved_round_trip(self) -> None:
        from spacegame.constants.flags import (
            dilemma_resolved,
            extract_dilemma_resolved_id,
        )

        for dilemma_id in ("d_wealth_community", "d_debt_liberty"):
            flag = dilemma_resolved(dilemma_id)
            assert extract_dilemma_resolved_id(flag) == dilemma_id

    def test_dilemma_resolved_canonical_prefix(self) -> None:
        from spacegame.constants.flags import dilemma_resolved

        assert dilemma_resolved("d_test") == "dilemma_resolved_d_test"

    def test_lens_closed_round_trip(self) -> None:
        from spacegame.constants.flags import extract_lens_closed_id, lens_closed

        for lens_id in ("wealth", "community", "revolution", "preservation"):
            flag = lens_closed(lens_id)
            assert extract_lens_closed_id(flag) == lens_id

    def test_lens_closed_canonical_prefix(self) -> None:
        from spacegame.constants.flags import lens_closed

        assert lens_closed("wealth") == "lens_closed_wealth"

    def test_three_prefixes_are_distinct(self) -> None:
        """The three helpers must not collide — telegraphed / resolved /
        closed all key the same downstream dialogue_flags dict."""
        from spacegame.constants.flags import (
            dilemma_resolved,
            dilemma_telegraphed,
            lens_closed,
        )

        assert dilemma_telegraphed("x") != dilemma_resolved("x")
        assert dilemma_resolved("x") != lens_closed("x")
        assert dilemma_telegraphed("x") != lens_closed("x")
