"""Tests for smuggling contracts UI integration (Phase E.4).

Covers contract display at black markets, accept/complete/expire flows,
and contract persistence across save/load.
"""

from spacegame.models.smuggling import SmugglingContractManager


# ============================================================================
# Contract Display at Black Markets
# ============================================================================


class TestContractDisplayAtBlackMarket:
    """Contracts should be generated and displayed at black markets."""

    def test_contracts_generated_at_black_market(self) -> None:
        """SmugglingContractManager generates contracts for a black market system."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        assert len(contracts) >= 1
        assert len(contracts) <= 3

    def test_available_contracts_accessible(self) -> None:
        """get_available_contracts returns generated contracts."""
        mgr = SmugglingContractManager()
        mgr.generate_contracts("crimson_reach", 10, 3)
        available = mgr.get_available_contracts("crimson_reach")
        assert len(available) >= 1

    def test_contracts_have_display_info(self) -> None:
        """Contracts have all info needed for UI display."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        for c in contracts:
            assert c.commodity_id
            assert c.quantity > 0
            assert c.destination_system
            assert c.payment > 0
            assert c.deadline_days > 0
            assert c.difficulty in ("low", "medium", "high")
            assert c.client_name


# ============================================================================
# Contract Accept
# ============================================================================


class TestContractAccept:
    """Players can accept smuggling contracts at black markets."""

    def test_accept_contract_succeeds(self) -> None:
        """Accepting a contract adds it to active list."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]

        success, msg = mgr.accept_contract(contract.id, accepted_day=10)
        assert success is True
        active = mgr.get_active_contracts()
        assert any(c.id == contract.id for c in active)

    def test_accept_max_three_active(self) -> None:
        """Cannot accept more than 3 contracts."""
        mgr = SmugglingContractManager()
        # Generate many contracts across different days
        for day in range(10, 30):
            mgr.generate_contracts("crimson_reach", day, 5)

        available = mgr.get_available_contracts("crimson_reach")
        accepted = 0
        for c in available:
            success, _ = mgr.accept_contract(c.id, accepted_day=15)
            if success:
                accepted += 1
            if accepted >= 4:
                break

        active = mgr.get_active_contracts()
        assert len(active) <= 3

    def test_accept_duplicate_fails(self) -> None:
        """Cannot accept the same contract twice."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]

        mgr.accept_contract(contract.id, accepted_day=10)
        success, _ = mgr.accept_contract(contract.id, accepted_day=10)
        assert success is False


# ============================================================================
# Contract Complete
# ============================================================================


class TestContractComplete:
    """Players can complete contracts at the correct destination."""

    def test_complete_at_correct_destination(self) -> None:
        """Completing at correct destination returns payment."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system=contract.destination_system,
            current_day=12,
        )
        assert result.success is True
        assert result.payment == contract.payment

    def test_complete_at_wrong_destination_fails(self) -> None:
        """Cannot complete at the wrong system."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system="wrong_system",
            current_day=12,
        )
        assert result.success is False

    def test_complete_expired_fails_with_penalty(self) -> None:
        """Expired contract returns failure with penalty."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system=contract.destination_system,
            current_day=10 + contract.deadline_days + 5,
        )
        assert result.success is False
        assert result.penalty > 0


# ============================================================================
# Contract Persistence
# ============================================================================


class TestContractPersistence:
    """Smuggling contracts persist across save/load via player state."""

    def test_contract_state_serialization(self) -> None:
        """SmugglingContractManager state survives to_dict/from_dict."""
        mgr = SmugglingContractManager()
        mgr.generate_contracts("crimson_reach", 10, 3)
        available = mgr.get_available_contracts("crimson_reach")
        if available:
            mgr.accept_contract(available[0].id, accepted_day=10)

        data = mgr.to_dict()
        restored = SmugglingContractManager.from_dict(data)

        assert len(restored.get_available_contracts("crimson_reach")) == len(
            mgr.get_available_contracts("crimson_reach")
        )
        assert len(restored.get_active_contracts()) == len(mgr.get_active_contracts())

    def test_full_save_load_roundtrip(self) -> None:
        """Smuggling contracts survive full save/load via player.smuggling_contract_state."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="Basic ship", cargo_capacity=50, fuel_capacity=100,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=1, special_abilities=[], availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        player = Player(
            name="Test", credits=5000,
            current_system_id="nexus_prime", ship=ship,
        )

        # Set up contracts
        mgr = SmugglingContractManager()
        mgr.generate_contracts("crimson_reach", 10, 3)
        available = mgr.get_available_contracts("crimson_reach")
        if available:
            mgr.accept_contract(available[0].id, accepted_day=10)

        # Sync state to player (mirrors game.py _save_game)
        player.smuggling_contract_state = mgr.to_dict()

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            restored = SmugglingContractManager.from_dict(p2.smuggling_contract_state)
            assert len(restored.get_active_contracts()) == len(mgr.get_active_contracts())
