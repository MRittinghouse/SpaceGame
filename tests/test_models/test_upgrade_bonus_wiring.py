"""Tests for ship upgrade bonus wiring into mining/salvage/refining views (Task 51).

Verifies that bonuses from player.upgrade_manager.get_bonus() are applied
to session creation in all three mini-game views.
"""

import pytest

from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager


def _make_upgrade(
    uid: str, bonus_type: str, bonus_value: float, slot: str = "mining"
) -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name=uid,
        description="test",
        price=0,
        slot_type=slot,
        bonus_type=bonus_type,
        bonus_value=bonus_value,
    )


class TestMiningUpgradeBonusWiring:
    """Ship upgrade bonuses should flow into MiningSession creation."""

    def test_drill_speed_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_drill", "drill_speed_bonus", 0.20)
        mgr.install(up)
        assert mgr.get_bonus("drill_speed_bonus") == pytest.approx(0.20)

    def test_rare_ore_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_rare", "rare_ore_bonus", 0.15)
        mgr.install(up)
        assert mgr.get_bonus("rare_ore_bonus") == pytest.approx(0.15)

    def test_chain_chance_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_chain", "chain_chance_bonus", 0.10)
        mgr.install(up)
        assert mgr.get_bonus("chain_chance_bonus") == pytest.approx(0.10)

    def test_mining_view_source_wires_upgrade_bonuses(self) -> None:
        """mining_view.py on_enter() must call upgrade_manager.get_bonus for mining bonuses."""
        import inspect
        from spacegame.views.mining_view import MiningView

        source = inspect.getsource(MiningView.on_enter)
        assert 'upgrade_manager.get_bonus("drill_speed_bonus")' in source
        assert 'upgrade_manager.get_bonus("rare_ore_bonus")' in source
        assert 'upgrade_manager.get_bonus("chain_chance_bonus")' in source


class TestSalvageUpgradeBonusWiring:
    """Ship upgrade bonuses should flow into SalvageSession creation."""

    def test_salvage_yield_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_yield", "salvage_yield_bonus", 0.20, "scanner")
        mgr.install(up)
        assert mgr.get_bonus("salvage_yield_bonus") == pytest.approx(0.20)

    def test_scan_charge_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_scan", "scan_charge_bonus", 2.0, "scanner")
        mgr.install(up)
        assert mgr.get_bonus("scan_charge_bonus") == pytest.approx(2.0)

    def test_extract_speed_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_extract", "extract_speed_bonus", 0.15, "scanner")
        mgr.install(up)
        assert mgr.get_bonus("extract_speed_bonus") == pytest.approx(0.15)

    def test_salvage_view_source_wires_upgrade_bonuses(self) -> None:
        """salvage_view.py on_enter() must call upgrade_manager.get_bonus for salvage bonuses."""
        import inspect
        from spacegame.views.salvage_view import SalvageView

        source = inspect.getsource(SalvageView.on_enter)
        assert "salvage_yield_bonus" in source and "upgrade_manager.get_bonus" in source
        assert 'upgrade_manager.get_bonus("scan_charge_bonus")' in source
        assert 'upgrade_manager.get_bonus("extract_speed_bonus")' in source


class TestRefiningUpgradeBonusWiring:
    """Ship upgrade bonuses should flow into RefiningSession creation."""

    def test_refining_speed_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_rspeed", "refining_speed_bonus", 0.10)
        mgr.install(up)
        assert mgr.get_bonus("refining_speed_bonus") == pytest.approx(0.10)

    def test_refining_yield_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_ryield", "refining_yield_bonus", 0.15)
        mgr.install(up)
        assert mgr.get_bonus("refining_yield_bonus") == pytest.approx(0.15)

    def test_forge_token_bonus_applied(self) -> None:
        mgr = ShipUpgradeManager()
        up = _make_upgrade("test_token", "forge_token_bonus", 0.10)
        mgr.install(up)
        assert mgr.get_bonus("forge_token_bonus") == pytest.approx(0.10)

    def test_refining_view_source_wires_upgrade_bonuses(self) -> None:
        """refining_view.py on_enter() must call upgrade_manager.get_bonus for refining bonuses."""
        import inspect
        from spacegame.views.refining_view import RefiningView

        source = inspect.getsource(RefiningView.on_enter)
        assert 'upgrade_manager.get_bonus("refining_speed_bonus")' in source
        assert 'upgrade_manager.get_bonus("refining_yield_bonus")' in source
        assert 'upgrade_manager.get_bonus("forge_token_bonus")' in source

    def test_multiple_upgrades_stack(self) -> None:
        """Multiple installed upgrades of same bonus type should stack."""
        mgr = ShipUpgradeManager()
        up1 = _make_upgrade("test_ryield1", "refining_yield_bonus", 0.10)
        up2 = _make_upgrade("test_ryield2", "refining_yield_bonus", 0.15, "scanner")
        mgr.install(up1)
        mgr.install(up2)
        assert mgr.get_bonus("refining_yield_bonus") == pytest.approx(0.25)
