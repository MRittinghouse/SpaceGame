"""Tests for hidden compartment integration (Phase E.6).

Covers Player.hidden_compartment field, cargo transfer,
capacity enforcement, and serialization.
"""

from spacegame.models.smuggling import HiddenCompartment
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


def _make_player() -> Player:
    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )
    ship = Ship(ship_type=ship_type, current_fuel=100)
    return Player(
        name="Test",
        credits=5000,
        current_system_id="nexus_prime",
        ship=ship,
    )


# ============================================================================
# Player Hidden Compartment Field
# ============================================================================


class TestPlayerHiddenCompartment:
    """Player should have an optional hidden compartment."""

    def test_hidden_compartment_default_none(self) -> None:
        """hidden_compartment defaults to None."""
        player = _make_player()
        assert player.hidden_compartment is None

    def test_hidden_compartment_assignable(self) -> None:
        """Can assign a HiddenCompartment to player."""
        player = _make_player()
        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=player.ship.max_cargo)
        assert player.hidden_compartment is not None
        assert player.hidden_compartment.hidden_capacity > 0


# ============================================================================
# Cargo Transfer
# ============================================================================


class TestCargoTransfer:
    """Transfer cargo between main and hidden holds."""

    def test_transfer_to_hidden_hold(self) -> None:
        """Can move cargo from main hold to hidden hold."""
        player = _make_player()
        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=50)
        player.ship.add_cargo("weapons_components", 5, 100)

        success, msg = player.hidden_compartment.add_to_hidden("weapons_components", 3)
        assert success is True
        assert player.hidden_compartment.hidden_cargo["weapons_components"] == 3

    def test_transfer_from_hidden_hold(self) -> None:
        """Can move cargo from hidden hold back to main."""
        player = _make_player()
        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=50)
        player.hidden_compartment.add_to_hidden("weapons_components", 5)

        success, msg = player.hidden_compartment.remove_from_hidden("weapons_components", 3)
        assert success is True
        assert player.hidden_compartment.hidden_cargo["weapons_components"] == 2

    def test_hidden_hold_capacity_enforced(self) -> None:
        """Cannot exceed hidden hold capacity."""
        compartment = HiddenCompartment(total_cargo_capacity=50)
        # Hidden capacity is 30% of 50 = 15
        assert compartment.hidden_capacity == 15

        success, _ = compartment.add_to_hidden("contraband", 15)
        assert success is True

        success, _ = compartment.add_to_hidden("more_stuff", 1)
        assert success is False


# ============================================================================
# Hidden Compartment Serialization
# ============================================================================


class TestHiddenCompartmentSerialization:
    """Hidden compartment survives save/load."""

    def test_hidden_compartment_roundtrip(self) -> None:
        """HiddenCompartment serializes and deserializes correctly."""
        compartment = HiddenCompartment(total_cargo_capacity=50)
        compartment.add_to_hidden("weapons_components", 3)
        compartment.add_to_hidden("stolen_data", 2)

        data = compartment.to_dict()
        restored = HiddenCompartment.from_dict(data)

        assert restored.total_cargo_capacity == 50
        assert restored.hidden_cargo["weapons_components"] == 3
        assert restored.hidden_cargo["stolen_data"] == 2

    def test_player_hidden_compartment_save_load(self) -> None:
        """Player.hidden_compartment survives full save/load."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()
        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=50)
        player.hidden_compartment.add_to_hidden("weapons_components", 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.hidden_compartment is not None
            assert p2.hidden_compartment.hidden_cargo["weapons_components"] == 5
            assert p2.hidden_compartment.hidden_capacity == 15

    def test_backward_compat_no_hidden_compartment(self) -> None:
        """Old saves without hidden_compartment load as None."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = _make_player()
        # No hidden compartment set

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.hidden_compartment is None
