"""SA-B2: RoundState bid validation, min increment scale, snipe-window logic."""

from __future__ import annotations

import pytest

from spacegame.models.bidding_round import (
    DEFAULT_SPEED_SETTING,
    SPEED_SETTINGS,
    RoundPhase,
    RoundState,
    min_increment_for_appraisal,
    opening_bid_for_lot,
)


class TestMinIncrementScale:
    @pytest.mark.parametrize(
        "base_appraisal,expected",
        [
            (0, 50),
            (500, 50),
            (2000, 50),
            (2001, 200),
            (5000, 200),
            (10000, 200),
            (10001, 500),
            (28000, 500),
            (30000, 500),
            (30001, 1000),
            (50000, 1000),
            (1_000_000, 1000),
        ],
    )
    def test_increment_buckets(self, base_appraisal: int, expected: int) -> None:
        assert min_increment_for_appraisal(base_appraisal) == expected


class TestOpeningBidFloor:
    def test_kings_repeater_opening(self) -> None:
        """Kings Repeater: reserve 21000 + min_increment 500 = 21500."""
        assert opening_bid_for_lot(28000, 21000) == 21500

    def test_axiom_array_opening(self) -> None:
        """Axiom array: base 8500 in 200-credit bucket, reserve 6970 + 200."""
        assert opening_bid_for_lot(8500, 6970) == 7170

    def test_reach_contraband_opening(self) -> None:
        """Reach contraband: base 6000, reserve 3900 + 200."""
        assert opening_bid_for_lot(6000, 3900) == 4100


class TestSpeedSettings:
    def test_all_four_settings_present(self) -> None:
        assert set(SPEED_SETTINGS.keys()) == {"slow", "normal", "fast", "asap"}

    def test_default_is_normal(self) -> None:
        assert DEFAULT_SPEED_SETTING == "normal"

    def test_slow_normal_5_second_snipe_window(self) -> None:
        assert SPEED_SETTINGS["slow"][1] == 5.0
        assert SPEED_SETTINGS["normal"][1] == 5.0

    def test_fast_3_second_snipe_window(self) -> None:
        assert SPEED_SETTINGS["fast"][1] == 3.0

    def test_asap_2_second_snipe_window(self) -> None:
        assert SPEED_SETTINGS["asap"][1] == 2.0


class TestRoundLifecycle:
    def test_open_round_sets_state(self) -> None:
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(
            round_number=1,
            round_duration_seconds=30.0,
            snipe_window_seconds=5.0,
            round_min_increment=500,
        )
        assert rs.round_number == 1
        assert rs.phase == RoundPhase.BID_WINDOW
        assert rs.time_remaining == pytest.approx(30.0)
        assert rs.round_min_increment == 500
        assert rs.snipe_reset_used is False

    def test_tick_decrements_timer(self) -> None:
        rs = RoundState(bidders_active={"player"})
        rs.open_round(1, 10.0, 3.0, 500)
        rs.tick(2.0)
        assert rs.time_remaining == pytest.approx(8.0)

    def test_tick_clamps_to_zero(self) -> None:
        rs = RoundState(bidders_active={"player"})
        rs.open_round(1, 10.0, 3.0, 500)
        rs.tick(20.0)
        assert rs.time_remaining == 0.0

    def test_tick_transitions_to_round_close_at_zero(self) -> None:
        rs = RoundState(bidders_active={"player"})
        rs.open_round(1, 10.0, 3.0, 500)
        rs.tick(10.0)
        assert rs.phase == RoundPhase.ROUND_CLOSE

    def test_tick_no_op_after_round_close(self) -> None:
        rs = RoundState(bidders_active={"player"})
        rs.open_round(1, 10.0, 3.0, 500)
        rs.tick(15.0)
        rs.tick(5.0)
        # Should remain at ROUND_CLOSE; time stays 0.
        assert rs.phase == RoundPhase.ROUND_CLOSE
        assert rs.time_remaining == 0.0


class TestBidValidation:
    def _open(self) -> RoundState:
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(1, 30.0, 5.0, 500)
        rs.current_high_bid = 21500
        return rs

    def test_valid_bid_above_min_increment(self) -> None:
        rs = self._open()
        ok, msg = rs.submit_bid("player", 22000)
        assert ok, msg
        assert rs.current_high_bid == 22000
        assert rs.current_high_bidder_id == "player"

    def test_bid_at_exact_min_increment_passes(self) -> None:
        rs = self._open()
        ok, msg = rs.submit_bid("player", 22000)
        assert ok, msg

    def test_bid_one_credit_below_min_fails(self) -> None:
        rs = self._open()
        ok, msg = rs.submit_bid("player", 21999)
        assert not ok
        assert "at least" in msg.lower()

    def test_bid_below_current_high_fails(self) -> None:
        rs = self._open()
        ok, _msg = rs.submit_bid("player", 21000)
        assert not ok

    def test_bidder_already_high_cannot_bid(self) -> None:
        rs = self._open()
        rs.submit_bid("player", 22000)
        ok, msg = rs.submit_bid("player", 23000)
        assert not ok
        assert "already" in msg.lower()

    def test_bidding_outside_window_fails(self) -> None:
        rs = self._open()
        rs.phase = RoundPhase.ROUND_CLOSE
        ok, _msg = rs.submit_bid("player", 22000)
        assert not ok

    def test_folded_bidder_cannot_bid(self) -> None:
        rs = self._open()
        rs.fold("p1")
        ok, _msg = rs.submit_bid("p1", 22000)
        assert not ok


class TestSnipeWindow:
    def _make_round(self, time_remaining: float = 4.0, snipe_window: float = 5.0) -> RoundState:
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(1, 30.0, snipe_window, 500)
        rs.current_high_bid = 21500
        rs.time_remaining = time_remaining
        return rs

    def test_bid_inside_snipe_window_resets_timer(self) -> None:
        rs = self._make_round(time_remaining=2.0)
        rs.submit_bid("player", 22000)
        assert rs.time_remaining == pytest.approx(5.0)
        assert rs.snipe_reset_used is True

    def test_bid_outside_snipe_window_does_not_reset(self) -> None:
        rs = self._make_round(time_remaining=20.0)
        rs.submit_bid("player", 22000)
        assert rs.time_remaining == pytest.approx(20.0)
        assert rs.snipe_reset_used is False

    def test_second_snipe_does_not_chain_reset(self) -> None:
        rs = self._make_round(time_remaining=2.0)
        rs.submit_bid("player", 22000)
        # Reset once -> time_remaining now 5.0. Decrement to 1.0 again
        # and bid -> still inside snipe window, but reset already used.
        rs.time_remaining = 1.0
        rs.submit_bid("p1", 22500)
        assert rs.time_remaining == pytest.approx(1.0)
        assert rs.snipe_reset_used is True  # Still flagged as used.

    @pytest.mark.parametrize(
        "speed,expected_window",
        [("slow", 5.0), ("normal", 5.0), ("fast", 3.0), ("asap", 2.0)],
    )
    def test_snipe_window_per_speed_setting(self, speed: str, expected_window: float) -> None:
        round_dur, snipe_w = SPEED_SETTINGS[speed]
        assert snipe_w == expected_window
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(1, round_dur, snipe_w, 500)
        rs.current_high_bid = 1000
        # Land bid 0.5s into snipe window.
        rs.time_remaining = expected_window - 0.5
        ok, _ = rs.submit_bid("player", 1500)
        assert ok
        assert rs.time_remaining == pytest.approx(expected_window)


class TestFolding:
    def test_fold_removes_bidder(self) -> None:
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(1, 30.0, 5.0, 500)
        ok, _ = rs.fold("p1")
        assert ok
        assert "p1" not in rs.bidders_active
        assert "player" in rs.bidders_active

    def test_fold_idempotent_returns_false(self) -> None:
        rs = RoundState(bidders_active={"player"})
        rs.open_round(1, 30.0, 5.0, 500)
        rs.fold("p1")
        ok, _ = rs.fold("p1")
        assert not ok


class TestRoundStateSerialization:
    def test_round_trip(self) -> None:
        rs = RoundState(bidders_active={"player", "p1"})
        rs.open_round(2, 15.0, 3.0, 200)
        rs.submit_bid("player", 8200)
        d = rs.to_dict()
        restored = RoundState.from_dict(d)
        assert restored.round_number == rs.round_number
        assert restored.phase == rs.phase
        assert restored.current_high_bid == rs.current_high_bid
        assert restored.current_high_bidder_id == rs.current_high_bidder_id
        assert restored.bidders_active == rs.bidders_active

    def test_from_dict_uses_safe_defaults_for_missing(self) -> None:
        rs = RoundState.from_dict({})
        assert rs.round_number == 1
        assert rs.phase == RoundPhase.OPEN_CALL
        assert rs.current_high_bid == 0
        assert rs.bidders_active == set()
