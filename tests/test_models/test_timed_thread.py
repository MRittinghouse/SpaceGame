"""TW-1: TimedThread + SoftDeadline model + Player + save/load tests.

Revised in QA-F-1 to reflect the interaction-day touch model (touches
recorded via Player.record_interaction, not sniffed from dialogue_flags).
"""

from __future__ import annotations

import pytest

from spacegame.models.soft_deadline import (
    DEFAULT_LATE_MULTIPLIER,
    SoftDeadline,
)
from spacegame.models.timed_thread import (
    DriftEvent,
    DriftState,
    TimedThread,
    TimedThreadState,
    initial_state_for_thread,
)


# ---------------------------------------------------------------------------
# DriftState + TimedThread model
# ---------------------------------------------------------------------------


class TestDriftStateModel:
    def test_round_trip(self) -> None:
        original = DriftState(
            id="cold",
            threshold_days=30,
            journal_entry_on_enter="Marcus has gone cold.",
            flag_to_set_on_enter="marcus_cold",
            narration="Marcus's lead went cold.",
        )
        restored = DriftState.from_dict(original.to_dict())
        assert restored == original

    def test_defaults_empty_strings(self) -> None:
        d = DriftState(id="x", threshold_days=10)
        assert d.journal_entry_on_enter == ""
        assert d.flag_to_set_on_enter == ""
        assert d.narration == ""


class TestTimedThreadModel:
    def test_round_trip(self) -> None:
        original = TimedThread(
            id="marcus_lead_cold",
            touch_triggers=["talked_to_marcus_jin"],
            drift_states=[
                DriftState(id="cold", threshold_days=30),
                DriftState(id="gone", threshold_days=60),
            ],
        )
        restored = TimedThread.from_dict(original.to_dict())
        assert restored == original

    def test_drift_states_sorted_on_load(self) -> None:
        """from_dict sorts drift states in threshold-ascending order so
        evaluators can short-circuit."""
        raw = {
            "id": "x",
            "touch_triggers": [],
            "drift_states": [
                {"id": "late", "threshold_days": 60},
                {"id": "early", "threshold_days": 20},
                {"id": "mid", "threshold_days": 40},
            ],
        }
        t = TimedThread.from_dict(raw)
        thresholds = [s.threshold_days for s in t.drift_states]
        assert thresholds == [20, 40, 60]


# ---------------------------------------------------------------------------
# TimedThreadState runtime
# ---------------------------------------------------------------------------


class TestTimedThreadState:
    def test_fresh_state_is_inactive(self) -> None:
        s = TimedThreadState()
        assert s.last_touched_day is None
        assert s.entered_states == []

    def test_mark_entered_dedupes(self) -> None:
        s = TimedThreadState()
        s.mark_entered("cold")
        s.mark_entered("cold")
        s.mark_entered("cold")
        assert s.entered_states == ["cold"]
        assert s.has_entered("cold")
        assert not s.has_entered("gone")

    def test_round_trip(self) -> None:
        original = TimedThreadState(
            last_touched_day=12,
            entered_states=["cold"],
        )
        restored = TimedThreadState.from_dict(original.to_dict())
        assert restored == original

    def test_round_trip_inactive(self) -> None:
        original = TimedThreadState(last_touched_day=None, entered_states=[])
        restored = TimedThreadState.from_dict(original.to_dict())
        assert restored == original
        assert restored.last_touched_day is None

    def test_pre_qaf1_save_with_zero_treated_as_inactive(self) -> None:
        """Legacy saves wrote last_touched_day=0 as the 'never touched'
        sentinel. Load should treat zero as None so those threads stay
        inactive instead of spuriously drifting."""
        state = TimedThreadState.from_dict({
            "last_touched_day": 0,
            "entered_states": [],
        })
        assert state.last_touched_day is None

    def test_initial_state_for_thread_is_inactive(self) -> None:
        t = TimedThread(id="x")
        s = initial_state_for_thread(t)
        assert s.last_touched_day is None
        assert s.entered_states == []


# ---------------------------------------------------------------------------
# SoftDeadline tier resolution
# ---------------------------------------------------------------------------


class TestSoftDeadlineResolution:
    @pytest.mark.parametrize(
        "elapsed,expected",
        [
            (0, 1.0),
            (5, 1.0),
            (10, 1.0),
            (11, 0.75),
            (14, 0.75),
            (15, 0.75),
            (16, DEFAULT_LATE_MULTIPLIER),
            (100, DEFAULT_LATE_MULTIPLIER),
        ],
    )
    def test_tier_boundaries(self, elapsed, expected) -> None:
        sd = SoftDeadline(
            full_reward_day_count=10,
            partial_reward_day_count=15,
        )
        assert sd.resolve_multiplier(elapsed) == pytest.approx(expected)

    def test_never_returns_zero(self) -> None:
        sd = SoftDeadline(
            full_reward_day_count=5,
            partial_reward_day_count=10,
        )
        assert sd.resolve_multiplier(9999) > 0

    def test_round_trip(self) -> None:
        original = SoftDeadline(
            full_reward_day_count=20,
            partial_reward_day_count=30,
            partial_reward_multiplier=0.6,
            late_multiplier=0.3,
        )
        restored = SoftDeadline.from_dict(original.to_dict())
        assert restored == original


# ---------------------------------------------------------------------------
# Player integration — QA-F-1 interaction API
# ---------------------------------------------------------------------------


def _make_player():
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="x", cargo_capacity=10, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=2, special_abilities=[],
        availability="all",
    )
    return Player(
        name="T", credits=500, current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )


class TestPlayerInteractionAPI:
    def test_record_interaction_sets_day(self) -> None:
        player = _make_player()
        player.game_day = 7
        player.record_interaction("talked_to_marcus_jin")
        assert player.last_interaction_day["talked_to_marcus_jin"] == 7

    def test_record_interaction_overwrites_previous(self) -> None:
        """Recurring touches: each call records the current day."""
        player = _make_player()
        player.game_day = 3
        player.record_interaction("talked_to_elena_reeves")
        assert player.last_interaction_day["talked_to_elena_reeves"] == 3
        player.game_day = 40
        player.record_interaction("talked_to_elena_reeves")
        assert player.last_interaction_day["talked_to_elena_reeves"] == 40

    def test_record_interaction_explicit_day(self) -> None:
        player = _make_player()
        player.game_day = 10
        player.record_interaction("key", game_day=42)
        assert player.last_interaction_day["key"] == 42


# ---------------------------------------------------------------------------
# Save/load round-trip for TW state
# ---------------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    def test_timed_thread_state_survives_save_load(self, tmp_path) -> None:
        from spacegame.save_manager import SaveManager

        player = _make_player()
        player.timed_thread_state["marcus_lead_cold"] = TimedThreadState(
            last_touched_day=12,
            entered_states=["cold"],
        )
        player.timed_thread_state["priya_impatience"] = TimedThreadState(
            last_touched_day=8,
        )
        # QA-F-1: last_interaction_day survives too
        player.record_interaction("talked_to_marcus_jin", game_day=12)
        player.record_interaction("any_mission_accepted", game_day=15)

        sm = SaveManager(save_directory=tmp_path)
        ok = sm.save_game(
            slot=0, player=player, markets={}, active_events={},
            playtime_seconds=0,
        )
        assert ok

        loaded = sm.load_game(slot=0)
        assert loaded is not None
        loaded_player = loaded["player"]

        assert "marcus_lead_cold" in loaded_player.timed_thread_state
        m = loaded_player.timed_thread_state["marcus_lead_cold"]
        assert isinstance(m, TimedThreadState)
        assert m.last_touched_day == 12
        assert m.entered_states == ["cold"]

        # QA-F-1: interaction records preserved
        assert loaded_player.last_interaction_day["talked_to_marcus_jin"] == 12
        assert loaded_player.last_interaction_day["any_mission_accepted"] == 15

    def test_legacy_save_without_interaction_day_loads_empty(
        self, tmp_path
    ) -> None:
        """Pre-QA-F-1 saves don't have last_interaction_day field."""
        import json

        from spacegame.save_manager import SaveManager

        player = _make_player()
        sm = SaveManager(save_directory=tmp_path)
        sm.save_game(
            slot=0, player=player, markets={}, active_events={},
            playtime_seconds=0,
        )

        path = sm.get_save_file_path(0)
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["player"].pop("last_interaction_day", None)
        raw["player"].pop("timed_thread_state", None)
        path.write_text(json.dumps(raw), encoding="utf-8")

        loaded = sm.load_game(slot=0)
        assert loaded is not None
        assert loaded["player"].timed_thread_state == {}
        assert loaded["player"].last_interaction_day == {}


# ---------------------------------------------------------------------------
# DriftEvent dataclass
# ---------------------------------------------------------------------------


class TestDriftEvent:
    def test_construct_full_event(self) -> None:
        e = DriftEvent(
            thread_id="marcus_lead_cold",
            state_id="cold",
            journal_entry="Marcus has gone cold.",
            flag_to_set="marcus_cold",
            narration="Marcus's lead went cold.",
            game_day=35,
        )
        assert e.thread_id == "marcus_lead_cold"
        assert e.game_day == 35
