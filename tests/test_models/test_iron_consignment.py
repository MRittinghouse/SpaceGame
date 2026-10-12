"""Odom's iron job: state, sensors, clock and close (BB-1, BB-4; polish design 2.2, 2.9)."""

from __future__ import annotations

from typing import Any

import pytest

from spacegame.constants.flags import (
    broker_ore_lost,
    broker_ore_sold,
    iron_delivery_closed,
    iron_delivery_failed,
    iron_delivery_moved_on,
    iron_delivery_resolved,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.iron_consignment import (
    BROKER,
    CLERK,
    CLOSED_LINE,
    FAILED_LINE,
    FILING_LINE,
    MISSION,
    STATE_FLAGS,
    close_on_exit,
    closers,
    hidable,
    late_tier_offset,
    moved_on_due,
    note_defeat,
    note_sale,
    on_clock,
    refresh_state,
    state_of,
)
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _manager(accepted_day: int | None = None, **statuses: str) -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    manager = MissionManager(dl.missions)
    state: dict[str, Any] = {"status": dict(statuses)}
    if accepted_day is not None:
        state["accepted_day"] = {MISSION: accepted_day}
    manager.load_state(state)
    return manager


def _player(ore: int = 0, hidden: int = 0) -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    player = Player("TestPilot", 5000, "nexus_prime", ship)
    if ore:
        player.ship.add_cargo("iron_ore", ore, 0)
    if hidden:
        from spacegame.models.smuggling import HiddenCompartment

        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=50)
        ok, message = player.hidden_compartment.add_to_hidden("iron_ore", hidden)
        assert ok, message
    return player


def _open() -> MissionManager:
    return _manager(accepted_day=1, bill_of_landing="completed", iron_delivery="active")


class TestTheStateTable:
    """Polish design 2.2 rule 3: exactly one state, and a sale dominates a loss."""

    @pytest.mark.parametrize(
        ("held", "sold", "lost", "state"),
        [
            (10, False, False, "iron_job_full"),
            (13, False, False, "iron_job_full"),
            (10, False, True, "iron_job_made_good"),
            (10, True, False, "iron_job_replaced"),
            (13, True, True, "iron_job_replaced"),
            (9, False, True, "iron_job_short_lost"),
            (7, False, True, "iron_job_short_lost"),
            (1, False, True, "iron_job_short_lost"),
            (0, False, True, "iron_job_gone_lost"),
            (9, True, False, "iron_job_moved"),
            (0, True, True, "iron_job_moved"),
        ],
    )
    def test_each_open_state_is_one_flag(
        self, held: int, sold: bool, lost: bool, state: str
    ) -> None:
        flags = {broker_ore_sold(): sold, broker_ore_lost(): lost}
        assert state_of(_open(), _player(held), flags) == state
        written = dict(flags)
        refresh_state(_open(), _player(held), written)
        assert [name for name in STATE_FLAGS if written.get(name)] == [state]

    def test_hidden_ore_is_held(self) -> None:
        assert state_of(_open(), _player(6, hidden=4), {}) == "iron_job_full"

    def test_fewer_than_ten_with_neither_record_names_no_state(self) -> None:
        assert state_of(_open(), _player(7), {}) == ""

    @pytest.mark.parametrize(
        ("flags", "state"),
        [
            ({}, "iron_job_done_clean"),
            ({"broker_ore_lost": True}, "iron_job_done_made_good"),
            ({"broker_ore_lost": True, "iron_ore_signed_short": True}, "iron_job_done_short"),
            ({"broker_ore_sold": True}, "iron_job_done_replaced"),
            ({"broker_ore_sold": True, "broker_ore_lost": True}, "iron_job_done_replaced"),
        ],
    )
    def test_each_done_state(self, flags: dict[str, bool], state: str) -> None:
        manager = _manager(iron_delivery="completed")
        assert state_of(manager, _player(), flags) == state

    def test_no_state_before_the_job_or_after_a_close(self) -> None:
        for status in ("unavailable", "available", "failed"):
            assert state_of(_manager(iron_delivery=status), _player(10), {}) == "", status

    def test_the_refresh_writes_only_what_changes(self) -> None:
        flags: dict[str, bool] = {}
        assert refresh_state(_manager(iron_delivery="available"), _player(), flags) == ()
        assert flags == {}
        assert refresh_state(_open(), _player(10), flags) == ("iron_job_full",)
        assert refresh_state(_open(), _player(10), flags) == ()
        flags[broker_ore_lost()] = True
        assert refresh_state(_open(), _player(7), flags) == (
            "iron_job_full",
            "iron_job_short_lost",
        )
        assert flags["iron_job_full"] is False


class TestTheSensors:
    """BB-1: a sale and a defeat are recorded where they happen; the captain's own go first."""

    def test_one_unit_of_the_ten_sold_is_a_sale(self) -> None:
        flags: dict[str, bool] = {}
        assert note_sale(_open(), flags, "iron_ore", 10, 1)
        assert flags[broker_ore_sold()] is True

    def test_the_captains_own_ore_goes_first(self) -> None:
        flags: dict[str, bool] = {}
        assert not note_sale(_open(), flags, "iron_ore", 15, 5)
        assert flags == {}
        assert note_sale(_open(), flags, "iron_ore", 15, 6)

    def test_no_open_job_no_sale(self) -> None:
        for status in ("completed", "failed", "available"):
            assert not note_sale(_manager(iron_delivery=status), {}, "iron_ore", 10, 10), status

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
        assert not note_sale(_open(), {}, "food", 3, 3)

    def test_a_defeat_is_a_loss_and_never_a_sale(self) -> None:
        flags: dict[str, bool] = {}
        assert note_defeat(_open(), flags, 10, 7)
        assert flags == {broker_ore_lost(): True}

    def test_a_defeat_that_spares_the_ten_is_no_loss_of_his(self) -> None:
        flags: dict[str, bool] = {}
        assert not note_defeat(_open(), flags, 20, 14)
        assert not note_defeat(_open(), flags, 10, 10)
        assert flags == {}

    def test_a_defeat_with_no_open_job_records_nothing(self) -> None:
        flags: dict[str, bool] = {}
        assert not note_defeat(_manager(iron_delivery="completed"), flags, 10, 7)
        assert flags == {}


class TestTheClock:
    """BB-4: the campaign never waits on the errand; a sale on record is filed."""

    def test_the_late_tier_starts_nineteen_days_after_the_accept(self) -> None:
        mission = _manager().get_mission(MISSION)
        assert mission is not None
        assert late_tier_offset(mission) == 19

    def test_an_open_job_moves_the_campaign_on_from_the_late_tier(self) -> None:
        manager = _manager(accepted_day=3, bill_of_landing="completed", iron_delivery="active")
        flags: dict[str, bool] = {}
        assert not on_clock(manager, _player(10), flags, 21)
        assert iron_delivery_moved_on() not in flags
        notice = on_clock(manager, _player(10), flags, 22)
        assert notice.flags == (iron_delivery_moved_on(),)
        assert notice.lines == ()
        assert manager.get_status(MISSION) == MissionStatus.ACTIVE

    def test_a_job_never_taken_moves_it_on_from_day_20(self) -> None:
        for status in ("unavailable", "available"):
            manager = _manager(bill_of_landing="completed", iron_delivery=status)
            assert not moved_on_due(manager, {}, 19), status
            assert moved_on_due(manager, {}, 20), status

    def test_without_the_permit_the_clock_waits(self) -> None:
        assert not moved_on_due(_manager(bill_of_landing="active"), {}, 40)

    def test_the_clock_writes_once(self) -> None:
        flags = {iron_delivery_moved_on(): True}
        assert not on_clock(_open(), _player(10), flags, 30)

    def test_an_open_job_with_no_accept_day_counts_from_day_one(self) -> None:
        manager = _manager(bill_of_landing="completed", iron_delivery="active")
        assert not moved_on_due(manager, {}, 19)
        assert moved_on_due(manager, {}, 20)

    def test_the_clock_files_a_sale_once(self) -> None:
        manager = _open()
        player = _player(4)
        flags = {broker_ore_sold(): True}
        assert not on_clock(manager, player, flags, 19)
        notice = on_clock(manager, player, flags, 20)
        assert notice.lines == (FAILED_LINE, "Odom's crew took back 4 Iron Ore", FILING_LINE)
        assert manager.get_status(MISSION) == MissionStatus.FAILED
        assert player.ship.get_cargo_quantity("iron_ore") == 0
        assert player.get_reputation("commerce_guild") == -10
        assert flags[iron_delivery_failed()] is True
        assert flags[iron_delivery_resolved()] is True
        assert flags[iron_delivery_moved_on()] is True
        assert not on_clock(manager, player, flags, 21)
        assert player.get_reputation("commerce_guild") == -10

    def test_a_filing_with_nothing_aboard_takes_nothing(self) -> None:
        flags = {broker_ore_sold(): True, iron_delivery_moved_on(): True}
        notice = on_clock(_open(), _player(), flags, 25)
        assert notice.lines == (FAILED_LINE, FILING_LINE)

    def test_a_covered_sale_is_not_filed(self) -> None:
        manager = _open()
        flags = {broker_ore_sold(): True}
        notice = on_clock(manager, _player(10), flags, 25)
        assert notice.lines == ()
        assert manager.get_status(MISSION) == MissionStatus.ACTIVE


class TestTheClose:
    """Polish design 2.2 rule 6: one close hook, two unpaid endings, and the decline's exit."""

    def test_the_betrayal_fails_the_job_and_takes_back_the_ore(self) -> None:
        manager = _open()
        player = _player(13)
        flags = {iron_delivery_failed(): True}
        notice = close_on_exit(manager, player, flags)
        assert notice.lines == (FAILED_LINE, "Odom's crew took back 10 Iron Ore")
        assert manager.get_status(MISSION) == MissionStatus.FAILED
        assert player.ship.get_cargo_quantity("iron_ore") == 3
        assert flags[iron_delivery_resolved()] is True
        assert flags[iron_delivery_moved_on()] is True

    def test_a_no_fault_close_closes_the_job(self) -> None:
        manager = _open()
        player = _player(7)
        flags = {iron_delivery_closed(): True}
        notice = close_on_exit(manager, player, flags)
        assert notice.lines == (CLOSED_LINE, "Odom's crew took back 7 Iron Ore")
        assert manager.get_status(MISSION) == MissionStatus.FAILED
        assert notice.flags == (iron_delivery_resolved(), iron_delivery_moved_on())

    def test_a_write_off_with_nothing_aboard_posts_only_the_close(self) -> None:
        notice = close_on_exit(_open(), _player(), {iron_delivery_closed(): True})
        assert notice.lines == (CLOSED_LINE,)

    def test_the_close_needs_an_open_job(self) -> None:
        manager = _manager(iron_delivery="failed")
        flags = {iron_delivery_failed(): True, iron_delivery_moved_on(): True}
        assert not close_on_exit(manager, _player(), flags)
        assert manager.get_status(MISSION) == MissionStatus.FAILED

    def test_without_a_close_the_exit_does_nothing(self) -> None:
        manager = _open()
        flags: dict[str, bool] = {}
        assert not close_on_exit(manager, _player(10), flags)
        assert manager.get_status(MISSION) == MissionStatus.ACTIVE
        assert flags == {}

    def test_a_declined_offer_moves_the_campaign_on_at_the_exit(self) -> None:
        manager = _manager(bill_of_landing="completed", iron_delivery="available")
        flags = {iron_delivery_resolved(): True}
        notice = close_on_exit(manager, _player(), flags)
        assert notice.flags == (iron_delivery_moved_on(),)
        assert notice.lines == ()
        assert manager.get_status(MISSION) == MissionStatus.AVAILABLE


class TestWhoCanCloseIt:
    """Polish design 6.1: the clerk while the ore can be weighed, Odom while he can close it."""

    @pytest.mark.parametrize(
        ("state", "npcs"),
        [
            ("iron_job_full", {CLERK}),
            ("iron_job_made_good", {CLERK}),
            ("iron_job_replaced", {CLERK}),
            ("iron_job_short_lost", {CLERK, BROKER}),
            ("iron_job_gone_lost", {BROKER}),
            ("iron_job_moved", {BROKER}),
            ("iron_job_done_clean", set()),
        ],
    )
    def test_closers_follow_the_state(self, state: str, npcs: set[str]) -> None:
        assert closers({state: True}) == npcs

    def test_no_state_no_closer(self) -> None:
        assert closers({}) == frozenset()


class TestTheHiddenHold:
    """Odom's consigned ore stays in the main hold while the job is open."""

    def test_only_the_captains_own_ore_can_be_hidden(self) -> None:
        assert hidable(_open(), _player(13), "iron_ore") == 3
        assert hidable(_open(), _player(10), "iron_ore") == 0

    def test_other_goods_and_closed_jobs_hide_freely(self) -> None:
        player = _player(10)
        player.ship.add_cargo("food", 4, 0)
        assert hidable(_open(), player, "food") == 4
        assert hidable(_manager(iron_delivery="completed"), player, "iron_ore") == 10
        assert hidable(None, player, "iron_ore") == 10
