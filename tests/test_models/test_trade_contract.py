"""Tests for trade contracts."""

from spacegame.models.trade_contract import TradeContract, TradeContractManager


class TestTradeContract:
    """Tests for TradeContract dataclass."""

    def test_creation(self) -> None:
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=120,
            bonus_credits=200,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=6,
        )
        assert c.id == "c1"
        assert c.contract_type == "sell"
        assert not c.completed

    def test_serialization_roundtrip(self) -> None:
        c = TradeContract(
            id="c1",
            contract_type="buy",
            commodity_id="fuel_cells",
            quantity=5,
            price_per_unit=50,
            bonus_credits=100,
            system_id="breakstone",
            day_offered=1,
            expiry_day=8,
        )
        data = c.to_dict()
        restored = TradeContract.from_dict(data)
        assert restored.id == c.id
        assert restored.commodity_id == c.commodity_id
        assert restored.quantity == c.quantity
        assert restored.bonus_credits == c.bonus_credits


class TestTradeContractManager:
    """Tests for TradeContractManager."""

    def test_generate_contracts(self) -> None:
        """Should generate 1-3 contracts for a system."""
        mgr = TradeContractManager()
        commodities = ["metals", "fuel_cells", "electronics", "food"]
        contracts = mgr.generate_contracts("nexus_prime", commodities, game_day=1)
        assert 1 <= len(contracts) <= 3
        for c in contracts:
            assert c.system_id == "nexus_prime"

    def test_deterministic_generation(self) -> None:
        """Same inputs should produce same contracts."""
        mgr1 = TradeContractManager()
        mgr2 = TradeContractManager()
        commodities = ["metals", "fuel_cells"]
        c1 = mgr1.generate_contracts("nexus_prime", commodities, game_day=1)
        c2 = mgr2.generate_contracts("nexus_prime", commodities, game_day=1)
        assert len(c1) == len(c2)
        for a, b in zip(c1, c2):
            assert a.id == b.id
            assert a.commodity_id == b.commodity_id

    def test_get_available_filters_expired(self) -> None:
        """Expired contracts should not appear in available list."""
        mgr = TradeContractManager()
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=50,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=5,
        )
        mgr._contracts.append(c)
        # Day 3: available
        avail = mgr.get_available("nexus_prime", 3)
        assert len(avail) == 1
        # Day 6: expired
        avail = mgr.get_available("nexus_prime", 6)
        assert len(avail) == 0

    def test_get_available_filters_by_system(self) -> None:
        """Only contracts for the requested system should appear."""
        mgr = TradeContractManager()
        c1 = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=50,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=10,
        )
        c2 = TradeContract(
            id="c2",
            contract_type="buy",
            commodity_id="fuel_cells",
            quantity=5,
            price_per_unit=50,
            bonus_credits=30,
            system_id="breakstone",
            day_offered=1,
            expiry_day=10,
        )
        mgr._contracts.extend([c1, c2])
        assert len(mgr.get_available("nexus_prime", 3)) == 1
        assert len(mgr.get_available("breakstone", 3)) == 1

    def test_fulfill_sell_contract(self) -> None:
        """Fulfilling a sell contract should mark it completed and return bonus."""
        mgr = TradeContractManager()
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=200,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=10,
        )
        mgr._contracts.append(c)
        success, msg = mgr.try_fulfill("c1", "nexus_prime", "metals", 10)
        assert success
        assert c.completed
        assert "200" in msg  # mentions bonus

    def test_fulfill_wrong_system_fails(self) -> None:
        """Cannot fulfill a contract from the wrong system."""
        mgr = TradeContractManager()
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=200,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=10,
        )
        mgr._contracts.append(c)
        success, msg = mgr.try_fulfill("c1", "breakstone", "metals", 10)
        assert not success

    def test_fulfill_insufficient_qty_fails(self) -> None:
        """Cannot fulfill a contract without enough quantity."""
        mgr = TradeContractManager()
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=200,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=10,
        )
        mgr._contracts.append(c)
        success, msg = mgr.try_fulfill("c1", "nexus_prime", "metals", 5)
        assert not success

    def test_expire_old_removes_expired(self) -> None:
        """expire_old should remove completed and expired contracts."""
        mgr = TradeContractManager()
        c1 = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=50,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=5,
        )
        c2 = TradeContract(
            id="c2",
            contract_type="buy",
            commodity_id="fuel_cells",
            quantity=5,
            price_per_unit=50,
            bonus_credits=30,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=20,
        )
        mgr._contracts.extend([c1, c2])
        mgr.expire_old(10)
        assert len(mgr._contracts) == 1
        assert mgr._contracts[0].id == "c2"

    def test_manager_serialization(self) -> None:
        """Manager should serialize and deserialize contracts."""
        mgr = TradeContractManager()
        c = TradeContract(
            id="c1",
            contract_type="sell",
            commodity_id="metals",
            quantity=10,
            price_per_unit=100,
            bonus_credits=50,
            system_id="nexus_prime",
            day_offered=1,
            expiry_day=10,
        )
        mgr._contracts.append(c)

        data = mgr.to_dict()
        restored = TradeContractManager.from_dict(data)
        assert len(restored._contracts) == 1
        assert restored._contracts[0].id == "c1"
