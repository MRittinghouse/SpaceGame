"""Bug bash BB-4: the campaign never waits on Odom's iron errand."""

from __future__ import annotations

from typing import Any

from spacegame.constants.flags import iron_delivery_failed, iron_delivery_moved_on
from spacegame.data_loader import get_data_loader
from spacegame.models.iron_consignment import (
    MISSION,
    close_on_exit,
    late_tier_offset,
    moved_on_due,
    on_clock,
)
from spacegame.models.mission import MissionManager, MissionStatus


def _manager(accepted_day: int | None = None, **statuses: str) -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    manager = MissionManager(dl.missions)
    state: dict[str, Any] = {"status": dict(statuses)}
    if accepted_day is not None:
        state["accepted_day"] = {MISSION: accepted_day}
    manager.load_state(state)
    return manager


class TestTheClock:
    def test_the_late_tier_starts_nineteen_days_after_the_accept(self) -> None:
        mission = _manager().get_mission(MISSION)
        assert mission is not None
        assert late_tier_offset(mission) == 19

    def test_an_open_job_moves_the_campaign_on_from_the_late_tier(self) -> None:
        manager = _manager(accepted_day=3, bill_of_landing="completed", iron_delivery="active")
        flags: dict[str, bool] = {}
        assert not on_clock(manager, flags, 21)
        assert iron_delivery_moved_on() not in flags
        assert on_clock(manager, flags, 22)
        assert flags[iron_delivery_moved_on()] is True
        assert manager.get_status(MISSION) == MissionStatus.ACTIVE

    def test_a_job_never_taken_moves_it_on_from_day_20(self) -> None:
        for status in ("unavailable", "available"):
            manager = _manager(bill_of_landing="completed", iron_delivery=status)
            assert not moved_on_due(manager, {}, 19), status
            assert moved_on_due(manager, {}, 20), status

    def test_without_the_permit_the_clock_waits(self) -> None:
        manager = _manager(bill_of_landing="active")
        assert not moved_on_due(manager, {}, 40)

    def test_the_clock_writes_once(self) -> None:
        manager = _manager(accepted_day=1, bill_of_landing="completed", iron_delivery="active")
        flags = {iron_delivery_moved_on(): True}
        assert not on_clock(manager, flags, 30)

    def test_an_open_job_with_no_accept_day_counts_from_day_one(self) -> None:
        manager = _manager(bill_of_landing="completed", iron_delivery="active")
        assert not moved_on_due(manager, {}, 19)
        assert moved_on_due(manager, {}, 20)


class TestTheClose:
    def test_the_betrayal_fails_the_job_and_moves_the_campaign_on(self) -> None:
        manager = _manager(accepted_day=1, iron_delivery="active")
        flags = {iron_delivery_failed(): True}
        assert close_on_exit(manager, flags)
        assert manager.get_status(MISSION) == MissionStatus.FAILED
        assert flags[iron_delivery_moved_on()] is True

    def test_without_the_betrayal_the_exit_closes_nothing(self) -> None:
        manager = _manager(accepted_day=1, iron_delivery="active")
        flags: dict[str, bool] = {}
        assert not close_on_exit(manager, flags)
        assert manager.get_status(MISSION) == MissionStatus.ACTIVE
        assert flags == {}

    def test_the_close_needs_an_open_job(self) -> None:
        """Design 2.9: a job already failed closes nothing more."""
        manager = _manager(iron_delivery="failed")
        assert not close_on_exit(manager, {iron_delivery_failed(): True})
        assert manager.get_status(MISSION) == MissionStatus.FAILED
