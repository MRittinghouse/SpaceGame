"""Bug bash BB-4: the campaign never waits on Odom's iron errand."""

from __future__ import annotations

from typing import Any

from spacegame.constants.flags import (
    broker_ore_sold,
    iron_delivery_failed,
    iron_delivery_moved_on,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.iron_consignment import (
    MISSION,
    close_on_exit,
    late_tier_offset,
    moved_on_due,
    note_sale,
    on_clock,
)
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)


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


class TestTheSaleSensor:
    """BB-1: a sale that draws Odom's ore is on the floor log; a fight's loss is not a sale."""

    def test_one_unit_of_the_ten_sold_is_a_sale(self) -> None:
        manager = _manager(accepted_day=1, iron_delivery="active")
        flags: dict[str, bool] = {}
        assert note_sale(manager, flags, "iron_ore", 10, 1)
        assert flags[broker_ore_sold()] is True

    def test_the_captains_own_ore_goes_first(self) -> None:
        manager = _manager(accepted_day=1, iron_delivery="active")
        flags: dict[str, bool] = {}
        assert not note_sale(manager, flags, "iron_ore", 15, 5)
        assert flags == {}
        assert note_sale(manager, flags, "iron_ore", 15, 6)

    def test_no_open_job_no_sale(self) -> None:
        for status in ("completed", "failed", "available"):
            manager = _manager(iron_delivery=status)
            assert not note_sale(manager, {}, "iron_ore", 10, 10), status

    def test_a_closed_job_ignores_another_missions_ore(self) -> None:
        """Another mission reserves five ore; the count alone would call the sale Odom's."""
        manager = _manager(iron_delivery="completed")
        manager.add_mission(
            Mission(
                id="proc_other_ore",
                name="test",
                description="A test contract.",
                objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")],
                rewards=[],
                on_accept_cargo=[AcceptCargo(commodity_id="iron_ore", quantity=5)],
            ),
            MissionStatus.ACTIVE,
        )
        assert manager.reserved_units("iron_ore") == 5
        flags: dict[str, bool] = {}
        assert not note_sale(manager, flags, "iron_ore", 5, 1)
        assert flags == {}

    def test_other_goods_are_never_odoms(self) -> None:
        manager = _manager(accepted_day=1, iron_delivery="active")
        assert not note_sale(manager, {}, "food", 3, 3)
