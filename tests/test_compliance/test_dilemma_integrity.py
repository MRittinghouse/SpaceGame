"""Integrity guard for the dilemma registry loaded by DataLoader.

Enforces six structural invariants that must hold for every Dilemma and
DilemmaOutcome in the data directory. These are build-failing rather than
hoped-for -- if a data-authoring sprint ships a hollow outcome or an ambush
threshold pair, this module fails the suite instead of failing at runtime
during play.

Pattern follows tests/test_compliance/test_findings_register.py: guard against
scanning nothing, then assert each invariant with an error message that names
every offending id, not just a boolean failure.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import Dilemma, DilemmaOutcome


def _load_dilemmas() -> dict[str, Dilemma]:
    """Return the dilemma registry from the singleton DataLoader."""
    return get_data_loader().dilemmas


# === Pure helper functions (module-level so meta-tests can invoke them directly) ===


def _outcomes_with_empty_tier_unlocks(
    dilemmas: dict[str, Dilemma],
) -> list[tuple[str, str]]:
    """Return (dilemma_id, winning_lens_id) for every outcome with an empty tier_unlocks."""
    offenders: list[tuple[str, str]] = []
    for did, d in dilemmas.items():
        for outcome in d.outcomes:
            if not outcome.tier_unlocks:
                offenders.append((did, outcome.winning_lens_id))
    return offenders


def _dilemmas_with_bad_thresholds(
    dilemmas: dict[str, Dilemma],
) -> list[tuple[str, int, int]]:
    """Return (dilemma_id, telegraph_threshold, collision_threshold) where telegraph >= collision."""
    return [
        (did, d.telegraph_threshold, d.collision_threshold)
        for did, d in dilemmas.items()
        if d.telegraph_threshold >= d.collision_threshold
    ]


def _outcomes_with_empty_closes(
    dilemmas: dict[str, Dilemma],
) -> list[tuple[str, str]]:
    """Return (dilemma_id, winning_lens_id) for every outcome with an empty closes list."""
    offenders: list[tuple[str, str]] = []
    for did, d in dilemmas.items():
        for outcome in d.outcomes:
            if not outcome.closes:
                offenders.append((did, outcome.winning_lens_id))
    return offenders


def _dilemmas_with_pole_outcome_mismatch(
    dilemmas: dict[str, Dilemma],
) -> list[str]:
    """Return dilemma_ids where poles and outcome winning_lens_ids don't match 1:1."""
    offenders: list[str] = []
    for did, d in dilemmas.items():
        if set(d.poles) != {o.winning_lens_id for o in d.outcomes}:
            offenders.append(did)
    return offenders


def _dilemmas_with_empty_telegraph_lines(
    dilemmas: dict[str, Dilemma],
) -> list[str]:
    """Return dilemma_ids where telegraph_lines is empty (IndexError risk at runtime)."""
    return [did for did, d in dilemmas.items() if not d.telegraph_lines]


def _dilemmas_with_bad_collision_requires(
    dilemmas: dict[str, Dilemma],
) -> list[tuple[str, int, int]]:
    """Return (dilemma_id, collision_requires, pole_count) where collision_requires not in [1, len(poles)]."""
    offenders: list[tuple[str, int, int]] = []
    for did, d in dilemmas.items():
        pole_count = len(d.poles)
        if not (1 <= d.collision_requires <= pole_count):
            offenders.append((did, d.collision_requires, pole_count))
    return offenders


class TestDilemmaIntegrity:
    """Real-content tests run against DataLoader.dilemmas."""

    def test_register_present_when_any_content_landed(self) -> None:
        """Guard against the scan silently passing over an empty registry.

        Skips while the registry is empty (before A2-12..A2-19 populate it);
        once content lands this converts silently to a pass.
        """
        dilemmas = _load_dilemmas()
        if not dilemmas:
            pytest.skip("no dilemma content yet; A2-12..A2-19 will populate this")

    def test_every_outcome_has_tier_unlocks(self) -> None:
        """Every DilemmaOutcome must name at least one tier unlock flag."""
        dilemmas = _load_dilemmas()
        offenders = _outcomes_with_empty_tier_unlocks(dilemmas)
        assert not offenders, (
            "DilemmaOutcomes with empty tier_unlocks: "
            + ", ".join(f"{did}.{pole}" for did, pole in offenders)
            + ". Every outcome must unlock at least one tier flag."
        )

    def test_telegraph_strictly_below_collision(self) -> None:
        """Every Dilemma must have telegraph_threshold < collision_threshold."""
        dilemmas = _load_dilemmas()
        offenders = _dilemmas_with_bad_thresholds(dilemmas)
        assert not offenders, (
            "Dilemmas with telegraph_threshold >= collision_threshold: "
            + ", ".join(
                f"{did}(telegraph={tele}, collision={coll})" for did, tele, coll in offenders
            )
            + ". Telegraph must strictly lead collision."
        )

    def test_every_outcome_closes_something(self) -> None:
        """Every DilemmaOutcome.closes must be non-empty."""
        dilemmas = _load_dilemmas()
        offenders = _outcomes_with_empty_closes(dilemmas)
        assert not offenders, (
            "DilemmaOutcomes with empty closes: "
            + ", ".join(f"{did}.{pole}" for did, pole in offenders)
            + ". Closure is a trade, not a subtraction -- there is always a losing pole."
        )

    def test_poles_and_outcomes_agree(self) -> None:
        """Every dilemma's poles must match its outcome winning_lens_ids exactly."""
        dilemmas = _load_dilemmas()
        offenders = _dilemmas_with_pole_outcome_mismatch(dilemmas)
        assert not offenders, (
            "Dilemmas with pole/outcome mismatch: "
            + ", ".join(offenders)
            + ". Each pole must have exactly one matching outcome and vice versa."
        )

    def test_telegraph_lines_non_empty(self) -> None:
        """Every Dilemma must have at least one telegraph line."""
        dilemmas = _load_dilemmas()
        offenders = _dilemmas_with_empty_telegraph_lines(dilemmas)
        assert not offenders, (
            "Dilemmas with empty telegraph_lines: "
            + ", ".join(offenders)
            + ". Round-robin cursor arithmetic requires at least one line."
        )

    def test_collision_requires_within_pole_count(self) -> None:
        """Every Dilemma must have collision_requires in [1, len(poles)]."""
        dilemmas = _load_dilemmas()
        offenders = _dilemmas_with_bad_collision_requires(dilemmas)
        assert not offenders, (
            "Dilemmas with out-of-range collision_requires: "
            + ", ".join(f"{did}(collision_requires={cr}, poles={pc})" for did, cr, pc in offenders)
            + ". collision_requires must be between 1 and len(poles) inclusive."
        )


# === Synthetic-fixture factories for meta-verification ===


def _make_outcome(
    winning_lens_id: str = "lens_a",
    closes: list[str] | None = None,
    tier_unlocks: list[str] | None = None,
    outcome_flag: str = "outcome_a",
    narration_summary: str = "lens a wins",
) -> DilemmaOutcome:
    return DilemmaOutcome(
        winning_lens_id=winning_lens_id,
        closes=closes if closes is not None else ["lens_b"],
        tier_unlocks=tier_unlocks if tier_unlocks is not None else ["tier_flag_a"],
        outcome_flag=outcome_flag,
        narration_summary=narration_summary,
    )


def _make_dilemma(
    id_: str = "test_d",
    poles: list[str] | None = None,
    collision_requires: int = 2,
    telegraph_threshold: int = 50,
    collision_threshold: int = 80,
    telegraph_lines: list[str] | None = None,
    outcomes: list[DilemmaOutcome] | None = None,
) -> Dilemma:
    poles = poles if poles is not None else ["lens_a", "lens_b"]
    telegraph_lines = telegraph_lines if telegraph_lines is not None else ["warning line 1"]
    if outcomes is None:
        outcomes = [
            DilemmaOutcome(
                winning_lens_id="lens_a",
                closes=["lens_b"],
                tier_unlocks=["tier_flag_a"],
                outcome_flag="outcome_a",
                narration_summary="lens a wins",
            ),
            DilemmaOutcome(
                winning_lens_id="lens_b",
                closes=["lens_a"],
                tier_unlocks=["tier_flag_b"],
                outcome_flag="outcome_b",
                narration_summary="lens b wins",
            ),
        ]
    return Dilemma(
        id=id_,
        poles=poles,
        collision_requires=collision_requires,
        telegraph_threshold=telegraph_threshold,
        collision_threshold=collision_threshold,
        telegraph_npc_id="test_npc",
        telegraph_lines=telegraph_lines,
        outcomes=outcomes,
    )


class TestDilemmaIntegrityMetaVerification:
    """Synthetic-fixture verification: confirms each helper discriminates correctly.

    For each invariant: construct one bad fixture (helper returns an offender),
    then one fixed fixture (helper returns empty list). Exercises ACs 1-3 and
    the four folded invariants from the plan.
    """

    # --- tier_unlocks invariant (AC 1) ---

    def test_meta_tier_unlocks_bad(self) -> None:
        """Helper returns offender when an outcome has empty tier_unlocks."""
        bad = _make_outcome(winning_lens_id="lens_a", tier_unlocks=[])
        good = _make_outcome(
            winning_lens_id="lens_b",
            closes=["lens_a"],
            outcome_flag="outcome_b",
            narration_summary="lens b wins",
        )
        d = _make_dilemma(id_="d_bad_tier", outcomes=[bad, good])
        assert _outcomes_with_empty_tier_unlocks({"d_bad_tier": d}) == [("d_bad_tier", "lens_a")]

    def test_meta_tier_unlocks_good(self) -> None:
        """Helper returns empty list when all outcomes have non-empty tier_unlocks."""
        d = _make_dilemma(id_="d_good_tier")
        assert _outcomes_with_empty_tier_unlocks({"d_good_tier": d}) == []

    # --- telegraph < collision invariant (ACs 2 and 3) ---

    def test_meta_threshold_equal_bad(self) -> None:
        """Equal thresholds (80, 80) are rejected -- telegraph must strictly lead collision."""
        d = _make_dilemma(id_="d_equal", telegraph_threshold=80, collision_threshold=80)
        assert _dilemmas_with_bad_thresholds({"d_equal": d}) == [("d_equal", 80, 80)]

    def test_meta_threshold_reversed_bad(self) -> None:
        """Reversed thresholds (telegraph=90, collision=80) are also rejected."""
        d = _make_dilemma(id_="d_rev", telegraph_threshold=90, collision_threshold=80)
        assert _dilemmas_with_bad_thresholds({"d_rev": d}) == [("d_rev", 90, 80)]

    def test_meta_threshold_good(self) -> None:
        """Helper returns empty list when telegraph is strictly below collision."""
        d = _make_dilemma(id_="d_good_thresh", telegraph_threshold=50, collision_threshold=80)
        assert _dilemmas_with_bad_thresholds({"d_good_thresh": d}) == []

    # --- closes non-empty invariant ---

    def test_meta_closes_bad(self) -> None:
        """Helper returns offender when an outcome has empty closes."""
        bad = _make_outcome(winning_lens_id="lens_a", closes=[])
        good = _make_outcome(
            winning_lens_id="lens_b",
            closes=["lens_a"],
            outcome_flag="outcome_b",
            narration_summary="lens b wins",
        )
        d = _make_dilemma(id_="d_bad_closes", outcomes=[bad, good])
        assert _outcomes_with_empty_closes({"d_bad_closes": d}) == [("d_bad_closes", "lens_a")]

    def test_meta_closes_good(self) -> None:
        """Helper returns empty list when all outcomes have non-empty closes."""
        d = _make_dilemma(id_="d_good_closes")
        assert _outcomes_with_empty_closes({"d_good_closes": d}) == []

    # --- pole/outcome 1:1 invariant ---

    def test_meta_pole_outcome_bad(self) -> None:
        """Helper returns offender when an outcome references a non-existent pole."""
        bad_outcomes = [
            _make_outcome(winning_lens_id="lens_c"),  # typo: not in poles
            _make_outcome(
                winning_lens_id="lens_b",
                closes=["lens_c"],
                outcome_flag="outcome_b",
                narration_summary="lens b wins",
            ),
        ]
        d = _make_dilemma(id_="d_bad_poles", poles=["lens_a", "lens_b"], outcomes=bad_outcomes)
        assert _dilemmas_with_pole_outcome_mismatch({"d_bad_poles": d}) == ["d_bad_poles"]

    def test_meta_pole_outcome_good(self) -> None:
        """Helper returns empty list when poles and outcomes match exactly."""
        d = _make_dilemma(id_="d_good_poles")
        assert _dilemmas_with_pole_outcome_mismatch({"d_good_poles": d}) == []

    # --- telegraph_lines non-empty invariant ---

    def test_meta_telegraph_lines_bad(self) -> None:
        """Helper returns offender when telegraph_lines is empty."""
        d = _make_dilemma(id_="d_no_tele", telegraph_lines=[])
        assert _dilemmas_with_empty_telegraph_lines({"d_no_tele": d}) == ["d_no_tele"]

    def test_meta_telegraph_lines_good(self) -> None:
        """Helper returns empty list when telegraph_lines is non-empty."""
        d = _make_dilemma(id_="d_good_tele")
        assert _dilemmas_with_empty_telegraph_lines({"d_good_tele": d}) == []

    # --- collision_requires in [1, len(poles)] invariant ---

    def test_meta_collision_requires_bad(self) -> None:
        """Helper returns offender when collision_requires exceeds pole count."""
        d = _make_dilemma(id_="d_bad_cr", poles=["lens_a", "lens_b"], collision_requires=3)
        assert _dilemmas_with_bad_collision_requires({"d_bad_cr": d}) == [("d_bad_cr", 3, 2)]

    def test_meta_collision_requires_good(self) -> None:
        """Helper returns empty list when collision_requires is within [1, len(poles)]."""
        d = _make_dilemma(id_="d_good_cr", poles=["lens_a", "lens_b"], collision_requires=2)
        assert _dilemmas_with_bad_collision_requires({"d_good_cr": d}) == []
