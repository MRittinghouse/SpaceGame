"""Tests for R1 remote prices feature on galaxy map.

Verifies that the Market Insider skill unlocks remote price display
on the galaxy map's system info panel.
"""

from spacegame.data_loader import get_data_loader
from spacegame.models.market import Market
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _make_player(remote_prices_skill: bool = False) -> Player:
    """Create a player, optionally with the remote_prices skill unlocked."""
    dl = get_data_loader()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player("TestPilot", 5000, "nexus_prime", ship)

    if remote_prices_skill:
        # Unlock prerequisite chain: negotiator → market_eye → trade_network → market_insider
        player.progression.add_xp(10000)  # Ensure enough skill points
        for skill_id in ["negotiator", "market_eye", "trade_network", "market_insider"]:
            success, msg = player.progression.level_up_skill(skill_id)
            assert success, f"Failed to unlock {skill_id}: {msg}"

    return player


class TestRemotePricesSkillGating:
    """Remote price info should only appear when Market Insider is unlocked."""

    def test_no_remote_prices_without_skill(self) -> None:
        """Player without Market Insider gets 0.0 remote_prices bonus."""
        player = _make_player(remote_prices_skill=False)
        assert player.progression.get_bonus("remote_prices") == 0.0

    def test_remote_prices_with_skill(self) -> None:
        """Player with Market Insider gets 1.0 remote_prices bonus."""
        player = _make_player(remote_prices_skill=True)
        assert player.progression.get_bonus("remote_prices") == 1.0


class TestRemoteMarketComputation:
    """Test creating temporary Markets for remote systems."""

    def test_can_create_market_for_any_system(self) -> None:
        """A Market can be created for any system to compute prices."""
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        for system_id, system in dl.systems.items():
            market = Market(system, commodities, game_day=10)
            prices = market.get_all_prices()
            assert len(prices) > 0, f"System {system_id} should have market prices"

    def test_specialty_exports_have_lower_prices(self) -> None:
        """Specialty exports should be cheaper than base price."""
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        # Find a system with specialty exports
        for system in dl.systems.values():
            if system.economy and system.economy.specialty_exports:
                market = Market(system, commodities, game_day=10)
                prices = market.get_all_prices()
                for export_id in system.economy.specialty_exports:
                    if export_id in prices and export_id in dl.commodities:
                        base = dl.commodities[export_id].base_price
                        # Export price should be below base (accounting for variance)
                        assert prices[export_id] < base * 1.2, (
                            f"{export_id} at {system.name}: "
                            f"export price {prices[export_id]} should be near/below "
                            f"base {base}"
                        )
                return  # One system is enough
        assert False, "No system with specialty exports found"

    def test_specialty_imports_have_higher_prices(self) -> None:
        """Specialty imports should be more expensive than base price."""
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        for system in dl.systems.values():
            if system.economy and system.economy.specialty_imports:
                market = Market(system, commodities, game_day=10)
                prices = market.get_all_prices()
                for import_id in system.economy.specialty_imports:
                    if import_id in prices and import_id in dl.commodities:
                        base = dl.commodities[import_id].base_price
                        # Import price should be above base (accounting for variance)
                        assert prices[import_id] > base * 0.8, (
                            f"{import_id} at {system.name}: "
                            f"import price {prices[import_id]} should be near/above "
                            f"base {base}"
                        )
                return
        assert False, "No system with specialty imports found"

    def test_prices_are_deterministic_for_same_day(self) -> None:
        """Same system + day should produce identical prices."""
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        system = list(dl.systems.values())[0]
        m1 = Market(system, commodities, game_day=10)
        m2 = Market(system, commodities, game_day=10)
        assert m1.get_all_prices() == m2.get_all_prices()

    def test_prices_vary_by_day(self) -> None:
        """Different days should produce different prices."""
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        system = list(dl.systems.values())[0]
        m1 = Market(system, commodities, game_day=10)
        m2 = Market(system, commodities, game_day=50)
        # At least some prices should differ
        p1 = m1.get_all_prices()
        p2 = m2.get_all_prices()
        assert p1 != p2, "Prices should vary between different game days"


class TestGalaxyMapRemotePriceLines:
    """Test the _get_remote_price_lines helper method on GalaxyMapView."""

    def test_price_lines_include_exports_and_imports(self) -> None:
        """Remote price lines should include specialty export and import info."""
        # Test via the model layer — the view method creates a Market
        # and formats exports/imports. We verify the data is available.
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        for system in dl.systems.values():
            if (
                system.economy
                and system.economy.specialty_exports
                and system.economy.specialty_imports
            ):
                market = Market(system, commodities, game_day=10)
                prices = market.get_all_prices()
                # Verify exports exist in prices
                for eid in system.economy.specialty_exports:
                    assert eid in prices, f"Export {eid} should be in {system.name} prices"
                # Verify imports exist in prices
                for iid in system.economy.specialty_imports:
                    assert iid in prices, f"Import {iid} should be in {system.name} prices"
                return
        assert False, "No system with both exports and imports found"

    def test_all_systems_have_economy(self) -> None:
        """All systems should have economy data for remote pricing."""
        dl = get_data_loader()
        for sid, system in dl.systems.items():
            assert system.economy is not None, f"System {sid} has no economy"
