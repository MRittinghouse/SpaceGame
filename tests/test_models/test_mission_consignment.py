"""Bug bash BB-1 and BB-11: a mission's accept cargo is reserved for that mission.

Python keeps counts, not lots, so a mission's ``on_accept_cargo`` is held for it while it
is active: other missions' collect legs and every captain-chosen disposal see only the
units left over. A board contract's accept cargo is also sealed against a sale.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _manager(**statuses: str) -> MissionManager:
    manager = MissionManager(_dl().missions)
    manager.load_state({"status": dict(statuses)})
    return manager


def _player(system_id: str = "nexus_prime") -> Player:
    ship = Ship(ship_type=_dl().ship_types["shuttle"], current_fuel=40)
    return Player("TestPilot", 5000, system_id, ship)


def _contract(mission_id: str, commodity_id: str, quantity: int) -> Mission:
    return Mission(
        id=mission_id,
        name=mission_id,
        description="A test contract.",
        objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")],
        rewards=[MissionReward(reward_type="credits", amount=100)],
        on_accept_cargo=[AcceptCargo(commodity_id=commodity_id, quantity=quantity)],
    )


class TestReservedUnits:
    def test_an_active_missions_accept_cargo_is_reserved(self) -> None:
        manager = _manager(iron_delivery="active")
        assert manager.reserved_units("iron_ore") == 10
        assert manager.reserved_units("food") == 0

    def test_only_an_active_mission_reserves(self) -> None:
        for status in ("available", "completed", "failed"):
            assert _manager(iron_delivery=status).reserved_units("iron_ore") == 0, status

    def test_a_mission_never_reserves_against_itself(self) -> None:
        manager = _manager(iron_delivery="active")
        assert manager.reserved_units("iron_ore", except_mission="iron_delivery") == 0

    def test_only_a_board_contracts_cargo_is_sealed(self) -> None:
        manager = _manager(iron_delivery="active")
        manager.add_mission(
            _contract("proc_smuggling_test", "weapons_components", 3), MissionStatus.ACTIVE
        )
        assert manager.sealed_units("weapons_components") == 3
        assert manager.reserved_units("weapons_components") == 3
        assert manager.sealed_units("iron_ore") == 0

    def test_free_units_hold_back_the_reserved(self) -> None:
        manager, player = _manager(iron_delivery="active"), _player()
        player.ship.add_cargo("iron_ore", 13, 0)
        assert manager.free_units(player, "iron_ore") == 3
        assert manager.free_units(player, "iron_ore", except_mission="iron_delivery") == 13
        player.ship.remove_cargo("iron_ore", 6)
        assert manager.free_units(player, "iron_ore") == 0

    def test_free_cargo_leaves_out_a_good_that_is_all_reserved(self) -> None:
        manager, player = _manager(iron_delivery="active"), _player()
        player.ship.add_cargo("iron_ore", 10, 0)
        player.ship.add_cargo("food", 4, 0)
        assert manager.free_cargo(player) == {"food": 4}

    def test_hidden_units_count_as_aboard(self) -> None:
        """Five of Odom's ten hidden and five of the captain's own in the main hold."""
        from spacegame.models.mission import held_units
        from spacegame.models.smuggling import HiddenCompartment

        manager, player = _manager(iron_delivery="active"), _player()
        player.hidden_compartment = HiddenCompartment(
            total_cargo_capacity=50, hidden_cargo={"iron_ore": 5}
        )
        player.ship.add_cargo("iron_ore", 10, 0)
        assert held_units(player, "iron_ore") == 15
        assert manager.free_units(player, "iron_ore") == 5
        player.ship.remove_cargo("iron_ore", 5)
        assert manager.free_units(player, "iron_ore") == 0

    def test_a_sale_draws_sealed_cargo_only_past_the_captains_own(self) -> None:
        """Three contract units aboard with two of the captain's own: two may be sold."""
        manager, player = _manager(iron_delivery="active"), _player()
        manager.add_mission(
            _contract("proc_smuggling_test", "weapons_components", 3), MissionStatus.ACTIVE
        )
        player.ship.add_cargo("weapons_components", 5, 0)
        assert not manager.sale_draws_sealed(player, "weapons_components", 2)
        assert manager.sale_draws_sealed(player, "weapons_components", 3)
        # a sale larger than the hold is the sell path's own "not enough cargo", not a seal
        assert not manager.sale_draws_sealed(player, "weapons_components", 6)
        # a campaign mission's cargo is never sealed: naming it sells it
        player.ship.add_cargo("iron_ore", 10, 0)
        assert not manager.sale_draws_sealed(player, "iron_ore", 10)

    @pytest.mark.parametrize("end", ["completed", "failed"])
    def test_the_seal_lifts_when_a_board_contract_stops_running(self, end: str) -> None:
        """Design 5.1, choice 19: a contract's own cargo is sealed while the contract runs.

        A finished contract stays a runtime mission (``remove_mission`` refuses a COMPLETED
        one), so the seal's own ACTIVE filter is what makes its good sellable again.
        """
        manager, player = _manager(), _player()
        manager.add_mission(
            _contract("proc_smuggling_test", "weapons_components", 3), MissionStatus.ACTIVE
        )
        player.ship.add_cargo("weapons_components", 3, 0)
        assert manager.sale_draws_sealed(player, "weapons_components", 3)
        if end == "failed":
            ok, msg = manager.fail_mission("proc_smuggling_test")
            assert ok, f"Failing the contract should succeed: {msg}"
        else:
            manager.load_state({"status": {"proc_smuggling_test": "completed"}})
        assert manager.get_status("proc_smuggling_test") == MissionStatus(end)
        assert manager.get_mission("proc_smuggling_test") is not None, "still a runtime mission"
        assert manager.sealed_units("weapons_components") == 0, f"a {end} contract seals nothing"
        assert not manager.sale_draws_sealed(player, "weapons_components", 3), (
            f"a {end} contract's cargo should sell"
        )


class TestCollectLegsCountFreeUnits:
    def test_another_missions_accept_cargo_does_not_fill_a_collect_leg(self) -> None:
        """the_heirloom_seeds loads three food it never hands over; Union Territory wants five."""
        manager = _manager(the_heirloom_seeds="active", union_territory="active")
        player = _player("breakstone")
        player.ship.add_cargo("food", 7, 0)
        manager.check_objectives(player)
        assert manager.get_objective_progress("union_territory")[0] is False
        player.ship.add_cargo("food", 1, 0)
        manager.check_objectives(player)
        assert manager.get_objective_progress("union_territory")[0] is True

    def test_a_mission_counts_its_own_accept_cargo(self) -> None:
        manager, player = _manager(iron_delivery="active"), _player()
        player.ship.add_cargo("iron_ore", 10, 0)
        manager.check_objectives(player)
        assert manager.get_objective_progress("iron_delivery")[0] is True
