"""SA-2: DeepShaftsState model + helper tests.

Covers:
- ``DeepShaftsState`` round-trip via ``to_dict`` / ``from_dict`` (including
  legacy-save fallback on missing keys).
- Pilgrimage rep-grant economy: first-visit +5, recurring +2 after a 7-day
  cooldown, cumulative cap +20.
- Cooldown math at the 7-day boundary.
- Journal-threshold helper: returns the right entry id at visits
  [1, 3, 5, 8, 12] with the ≥3-day spacing rule, ``None`` between
  thresholds, ``None`` after all 5 unlock.
"""

from __future__ import annotations

import pytest

from spacegame.models.deep_shafts import (
    PILGRIMAGE_BLESSING_CAP,
    PILGRIMAGE_COOLDOWN_DAYS,
    PILGRIMAGE_FIRST_GRANT,
    PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS,
    PILGRIMAGE_JOURNAL_THRESHOLDS,
    PILGRIMAGE_RECURRING_GRANT,
    DeepShaftsState,
    apply_visit,
)


class TestDeepShaftsStateDefaults:
    """A fresh ``DeepShaftsState`` carries safe defaults."""

    def test_default_fields(self) -> None:
        state = DeepShaftsState()
        assert state.visit_count == 0
        assert state.last_pilgrimage_day == 0
        assert state.blessing_total == 0
        assert state.scripted_scene_played is False
        assert state.last_journal_unlock_day == 0


class TestDeepShaftsStateRoundTrip:
    """``to_dict`` / ``from_dict`` round-trips populated state cleanly."""

    def test_round_trip_preserves_all_fields(self) -> None:
        state = DeepShaftsState(
            visit_count=4,
            last_pilgrimage_day=37,
            blessing_total=11,
            scripted_scene_played=True,
            last_journal_unlock_day=37,
        )
        restored = DeepShaftsState.from_dict(state.to_dict())
        assert restored == state

    def test_legacy_save_missing_keys_default_safely(self) -> None:
        """Legacy / partial saves load with defaults instead of crashing."""
        restored = DeepShaftsState.from_dict({})
        assert restored == DeepShaftsState()


class TestPilgrimageBlessingMath:
    """``apply_visit`` carries the rep-grant economy."""

    def test_first_visit_grants_first_amount(self) -> None:
        state = DeepShaftsState()
        rep, _journal = apply_visit(state, current_day=2)
        assert rep == PILGRIMAGE_FIRST_GRANT
        assert state.visit_count == 1
        assert state.blessing_total == PILGRIMAGE_FIRST_GRANT
        assert state.last_pilgrimage_day == 2

    def test_first_visit_marks_received_blessing_state(self) -> None:
        """The first-grant flag is signalled by ``blessing_total > 0``."""
        state = DeepShaftsState()
        apply_visit(state, current_day=1)
        assert state.blessing_total >= PILGRIMAGE_FIRST_GRANT

    def test_second_visit_within_cooldown_grants_zero(self) -> None:
        state = DeepShaftsState()
        apply_visit(state, current_day=10)
        rep, _journal = apply_visit(state, current_day=10 + (PILGRIMAGE_COOLDOWN_DAYS - 1))
        assert rep == 0
        assert state.visit_count == 2
        assert state.blessing_total == PILGRIMAGE_FIRST_GRANT

    def test_second_visit_exactly_at_cooldown_grants_recurring(self) -> None:
        state = DeepShaftsState()
        apply_visit(state, current_day=10)
        rep, _journal = apply_visit(state, current_day=10 + PILGRIMAGE_COOLDOWN_DAYS)
        assert rep == PILGRIMAGE_RECURRING_GRANT
        assert state.blessing_total == PILGRIMAGE_FIRST_GRANT + PILGRIMAGE_RECURRING_GRANT
        assert state.last_pilgrimage_day == 10 + PILGRIMAGE_COOLDOWN_DAYS

    def test_blessing_cap_holds_when_reached(self) -> None:
        """Once cumulative ``blessing_total`` reaches the cap, no more rep grants."""
        state = DeepShaftsState(
            visit_count=20,
            last_pilgrimage_day=0,
            blessing_total=PILGRIMAGE_BLESSING_CAP,
            scripted_scene_played=True,
        )
        rep, _journal = apply_visit(state, current_day=200)
        assert rep == 0
        assert state.blessing_total == PILGRIMAGE_BLESSING_CAP

    def test_blessing_cap_partial_top_up(self) -> None:
        """Recurring grant clamps at the cap if it would overshoot."""
        state = DeepShaftsState(
            visit_count=8,
            last_pilgrimage_day=0,
            blessing_total=PILGRIMAGE_BLESSING_CAP - 1,
            scripted_scene_played=True,
        )
        rep, _journal = apply_visit(state, current_day=200)
        assert rep == 1, "Should top up by exactly the gap to cap"
        assert state.blessing_total == PILGRIMAGE_BLESSING_CAP

    def test_visit_count_increments_even_when_capped(self) -> None:
        state = DeepShaftsState(
            visit_count=20,
            last_pilgrimage_day=0,
            blessing_total=PILGRIMAGE_BLESSING_CAP,
            scripted_scene_played=True,
        )
        apply_visit(state, current_day=300)
        assert state.visit_count == 21


class TestPilgrimageJournalUnlocks:
    """``apply_visit`` returns the right journal id at the right thresholds."""

    def test_threshold_constants(self) -> None:
        assert PILGRIMAGE_JOURNAL_THRESHOLDS == (1, 3, 5, 8, 12)

    def test_first_visit_returns_first_journal(self) -> None:
        state = DeepShaftsState()
        _rep, journal = apply_visit(state, current_day=5)
        assert journal == "pilgrimage_journal_1"

    def test_visit_between_thresholds_returns_none(self) -> None:
        state = DeepShaftsState()
        apply_visit(state, current_day=1)  # visit 1 -> journal 1
        _rep, journal = apply_visit(state, current_day=10)  # visit 2 -> none
        assert journal is None

    def test_visit_at_threshold_returns_journal(self) -> None:
        state = DeepShaftsState()
        # Walk visits 1..3, expecting journals on 1 and 3.
        unlocks: list[str | None] = []
        day = 1
        for _ in range(3):
            _rep, j = apply_visit(state, current_day=day)
            unlocks.append(j)
            day += PILGRIMAGE_COOLDOWN_DAYS + 1
        assert unlocks[0] == "pilgrimage_journal_1"
        assert unlocks[1] is None
        assert unlocks[2] == "pilgrimage_journal_2"

    def test_journal_min_spacing_rule(self) -> None:
        """Two threshold visits within ``MIN_SPACING_DAYS`` only unlock the first."""
        state = DeepShaftsState()
        apply_visit(state, current_day=1)  # journal 1
        # Force visit_count=3 (a journal threshold) but with too-small day gap.
        # Manually advance visit_count to threshold without applying_visit
        # directly; simulate two more visits in quick succession.
        # Visit 2 is not a threshold so this is fine, journal stays None.
        _rep, j2 = apply_visit(state, current_day=1 + (PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS - 1))
        assert j2 is None
        # Visit 3 IS a threshold; if day gap is below the min, no unlock.
        _rep, j3 = apply_visit(state, current_day=1 + (PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS - 1))
        assert j3 is None, "Day gap below min spacing must suppress the unlock"

    def test_journal_unlocks_after_min_spacing(self) -> None:
        """Once spacing is satisfied, the threshold visit unlocks."""
        state = DeepShaftsState()
        apply_visit(state, current_day=1)  # journal 1
        apply_visit(state, current_day=10)  # visit 2, no journal
        # Visit 3 with adequate spacing from visit 1 -> journal 2
        _rep, j = apply_visit(state, current_day=20)
        assert j == "pilgrimage_journal_2"

    def test_all_five_journals_unlock_in_order(self) -> None:
        """Walk a sequence of well-spaced visits; collect all 5 unlocks."""
        state = DeepShaftsState()
        unlocked: list[str] = []
        # Visits at days 1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111
        # gives 12 visits, well-spaced enough for all journal unlocks.
        for visit_idx in range(12):
            day = 1 + visit_idx * 10
            _rep, j = apply_visit(state, current_day=day)
            if j is not None:
                unlocked.append(j)
        assert unlocked == [
            "pilgrimage_journal_1",
            "pilgrimage_journal_2",
            "pilgrimage_journal_3",
            "pilgrimage_journal_4",
            "pilgrimage_journal_5",
        ]

    def test_no_journal_after_all_unlocked(self) -> None:
        state = DeepShaftsState(
            visit_count=12,
            last_pilgrimage_day=120,
            blessing_total=10,
            scripted_scene_played=True,
            last_journal_unlock_day=120,
        )
        _rep, j = apply_visit(state, current_day=200)
        assert j is None


class TestPilgrimageGrantConstants:
    """The locked numbers from the SA-2 plan are exposed as constants."""

    def test_first_grant_value(self) -> None:
        assert PILGRIMAGE_FIRST_GRANT == 5

    def test_recurring_grant_value(self) -> None:
        assert PILGRIMAGE_RECURRING_GRANT == 2

    def test_blessing_cap_value(self) -> None:
        assert PILGRIMAGE_BLESSING_CAP == 20

    def test_cooldown_days(self) -> None:
        assert PILGRIMAGE_COOLDOWN_DAYS == 7

    def test_journal_min_spacing(self) -> None:
        assert PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS == 3


class TestApplyVisitReturnContract:
    """``apply_visit`` returns ``(rep_grant, journal_id)``."""

    def test_returns_int_and_optional_str(self) -> None:
        state = DeepShaftsState()
        result = apply_visit(state, current_day=1)
        assert isinstance(result, tuple)
        assert len(result) == 2
        rep, journal = result
        assert isinstance(rep, int)
        assert journal is None or isinstance(journal, str)

    def test_rep_grant_is_non_negative(self) -> None:
        state = DeepShaftsState()
        rep, _ = apply_visit(state, current_day=1)
        assert rep >= 0


@pytest.mark.parametrize(
    "blessing_total, expected_rep",
    [
        (0, 5),  # First visit: full first-grant
        (5, 2),  # Cooldown elapsed: full recurring
        (18, 2),  # Cooldown elapsed; +2 fits under cap (becomes 20)
        (19, 1),  # Cooldown elapsed; clamped to remaining gap (=1)
        (20, 0),  # At cap: no more grants
        (25, 0),  # Past cap (defensive): no grants
    ],
)
def test_blessing_grant_at_boundaries(blessing_total: int, expected_rep: int) -> None:
    """Boundary cases for the blessing-cap math, parameterized."""
    if blessing_total == 0:
        state = DeepShaftsState()
        rep, _ = apply_visit(state, current_day=1)
    else:
        state = DeepShaftsState(
            visit_count=5,
            last_pilgrimage_day=0,
            blessing_total=blessing_total,
            scripted_scene_played=True,
        )
        rep, _ = apply_visit(state, current_day=200)
    assert rep == expected_rep
