"""Tests for player mining persistent state (strata tokens, deep core, silos)."""

import pytest

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.ore_silo import OreSiloManager
from spacegame.models.deep_core import DeepCoreUpgradeState


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    return Player(
        name="TestCaptain",
        credits=5000,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


class TestStrataTokens:
    """Tests for strata token operations on Player."""

    def test_initial_strata_is_zero(self) -> None:
        player = _make_player()
        assert player.strata_tokens == 0

    def test_add_strata(self) -> None:
        player = _make_player()
        player.add_strata_tokens(15)
        assert player.strata_tokens == 15

    def test_add_strata_accumulates(self) -> None:
        player = _make_player()
        player.add_strata_tokens(10)
        player.add_strata_tokens(7)
        assert player.strata_tokens == 17

    def test_spend_strata_success(self) -> None:
        player = _make_player()
        player.strata_tokens = 50
        assert player.spend_strata_tokens(20)
        assert player.strata_tokens == 30

    def test_spend_strata_insufficient(self) -> None:
        player = _make_player()
        player.strata_tokens = 5
        assert not player.spend_strata_tokens(10)
        assert player.strata_tokens == 5

    def test_spend_strata_exact(self) -> None:
        player = _make_player()
        player.strata_tokens = 10
        assert player.spend_strata_tokens(10)
        assert player.strata_tokens == 0


class TestMiningPersistentState:
    """Tests for deep core and silo state on Player."""

    def test_initial_prestige_level(self) -> None:
        player = _make_player()
        assert player.mining_prestige_level == 0

    def test_deep_core_upgrades_initialized(self) -> None:
        player = _make_player()
        assert isinstance(player.deep_core_upgrades, DeepCoreUpgradeState)
        assert player.deep_core_upgrades.get_level("core_resonance") == 0

    def test_ore_silo_manager_initialized(self) -> None:
        player = _make_player()
        assert isinstance(player.ore_silo_manager, OreSiloManager)

    def test_silo_persists_across_access(self) -> None:
        player = _make_player()
        silo = player.ore_silo_manager.get_silo("breakstone")
        silo.add_ore("iron_ore", 10)
        assert player.ore_silo_manager.get_silo("breakstone").contents["iron_ore"] == 10
