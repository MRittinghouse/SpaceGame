"""Tests for regional market filtering and specialty pricing (Cycle R1)."""

from spacegame.models.commodity import Commodity, CommodityCategory, Legality
from spacegame.models.system import StarSystem, Station, Economy, Coordinates
from spacegame.models.market import Market


def _make_commodity(
    id: str,
    base_price: int = 100,
    category: str = "basic",
    production_tags: list[str] | None = None,
    consumption_tags: list[str] | None = None,
) -> Commodity:
    return Commodity(
        id=id,
        name=id.replace("_", " ").title(),
        category=CommodityCategory(category),
        description="Test commodity",
        base_price=base_price,
        variance_min=0.0,
        variance_max=0.0,
        volume_per_unit=1,
        legality=Legality.LEGAL,
        production_tags=production_tags or [],
        consumption_tags=consumption_tags or [],
    )


def _make_system(
    id: str = "test_system",
    production_tags: list[str] | None = None,
    consumption_tags: list[str] | None = None,
    available_commodities: list[str] | None = None,
    specialty_exports: list[str] | None = None,
    specialty_imports: list[str] | None = None,
) -> StarSystem:
    return StarSystem(
        id=id,
        name=id.replace("_", " ").title(),
        type="trade_hub",
        description="A test system",
        coordinates=Coordinates(x=0, y=0),
        danger_level="safe",
        faction="Test Faction",
        stations=[
            Station(
                id=f"{id}_station",
                name="Test Station",
                type="major",
                description="A test station",
                docking_fee=100,
                market_variety="full",
            )
        ],
        economy=Economy(
            production_tags=production_tags or [],
            consumption_tags=consumption_tags or [],
            tariff_rate=0.0,
            available_commodities=available_commodities,
            specialty_exports=specialty_exports or [],
            specialty_imports=specialty_imports or [],
        ),
        rest_cost=100,
    )


# ============================================================================
# Regional Filtering
# ============================================================================


class TestMarketRegionalFiltering:
    """Market should only list commodities available at the current system."""

    def test_all_commodities_available_when_no_filter(self) -> None:
        """When available_commodities is None, all commodities should appear."""
        food = _make_commodity("food")
        metals = _make_commodity("common_metals")
        art = _make_commodity("art", category="luxury")

        system = _make_system(available_commodities=None)
        market = Market(system, [food, metals, art])

        prices = market.get_all_prices()
        assert "food" in prices, "food should be available when no filter set"
        assert "common_metals" in prices, "metals should be available when no filter set"
        assert "art" in prices, "art should be available when no filter set"

    def test_only_listed_commodities_available(self) -> None:
        """When available_commodities is set, only listed commodities should appear."""
        food = _make_commodity("food")
        metals = _make_commodity("common_metals")
        art = _make_commodity("art", category="luxury")

        system = _make_system(available_commodities=["food", "common_metals"])
        market = Market(system, [food, metals, art])

        prices = market.get_all_prices()
        assert "food" in prices, "food should be available"
        assert "common_metals" in prices, "metals should be available"
        assert "art" not in prices, "art should be filtered out"

    def test_empty_available_list_means_no_commodities(self) -> None:
        """An empty available list should result in no market listings."""
        food = _make_commodity("food")
        system = _make_system(available_commodities=[])
        market = Market(system, [food])

        prices = market.get_all_prices()
        assert len(prices) == 0, "No commodities should be available with empty list"

    def test_unknown_commodity_in_available_list_ignored(self) -> None:
        """IDs in available_commodities that don't match any commodity are ignored."""
        food = _make_commodity("food")
        system = _make_system(available_commodities=["food", "nonexistent_item"])
        market = Market(system, [food])

        prices = market.get_all_prices()
        assert "food" in prices
        assert len(prices) == 1

    def test_get_price_returns_zero_for_unavailable_commodity(self) -> None:
        """get_price() should return 0 for commodities not in this market."""
        food = _make_commodity("food")
        art = _make_commodity("art", category="luxury")
        system = _make_system(available_commodities=["food"])
        market = Market(system, [food, art])

        assert market.get_price("food") > 0, "available commodity should have price"
        assert market.get_price("art") == 0, "unavailable commodity should return 0"

    def test_get_market_report_empty_for_unavailable(self) -> None:
        """get_market_report() should return empty dict for unavailable commodity."""
        food = _make_commodity("food")
        art = _make_commodity("art", category="luxury")
        system = _make_system(available_commodities=["food"])
        market = Market(system, [food, art])

        assert market.get_market_report("food") != {}, "available commodity should have report"
        assert market.get_market_report("art") == {}, "unavailable commodity should have no report"

    def test_commodities_dict_only_contains_available(self) -> None:
        """market.commodities should only contain available commodities."""
        food = _make_commodity("food")
        metals = _make_commodity("common_metals")
        art = _make_commodity("art", category="luxury")

        system = _make_system(available_commodities=["food"])
        market = Market(system, [food, metals, art])

        assert len(market.commodities) == 1
        assert "food" in market.commodities


# ============================================================================
# Specialty Pricing
# ============================================================================


class TestMarketSpecialtyPricing:
    """Specialty exports should be cheaper, specialty imports more expensive."""

    def test_specialty_export_reduces_price(self) -> None:
        """Commodities in specialty_exports should be cheaper than base price."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_exports=["food"])
        market = Market(system, [food])

        price = market.get_price("food")
        assert price < 100, f"Specialty export should reduce price, got {price}"

    def test_specialty_import_increases_price(self) -> None:
        """Commodities in specialty_imports should be more expensive than base price."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_imports=["food"])
        market = Market(system, [food])

        price = market.get_price("food")
        assert price > 100, f"Specialty import should increase price, got {price}"

    def test_specialty_stacks_with_production_tags(self) -> None:
        """Specialty export bonus should stack with production tag discount."""
        food = _make_commodity("food", base_price=100, production_tags=["food"])

        system_specialty = _make_system(
            production_tags=["food"],
            specialty_exports=["food"],
        )
        system_normal = _make_system(production_tags=["food"])

        market_specialty = Market(system_specialty, [food])
        market_normal = Market(system_normal, [food])

        assert market_specialty.get_price("food") < market_normal.get_price("food"), (
            "Specialty + production should be cheaper than production alone"
        )

    def test_specialty_import_stacks_with_consumption_tags(self) -> None:
        """Specialty import bonus should stack with consumption tag premium."""
        food = _make_commodity("food", base_price=100, consumption_tags=["food"])

        system_specialty = _make_system(
            consumption_tags=["food"],
            specialty_imports=["food"],
        )
        system_normal = _make_system(consumption_tags=["food"])

        market_specialty = Market(system_specialty, [food])
        market_normal = Market(system_normal, [food])

        assert market_specialty.get_price("food") > market_normal.get_price("food"), (
            "Specialty + consumption should be more expensive than consumption alone"
        )

    def test_specialty_export_amount(self) -> None:
        """Specialty export should reduce price by ~15%."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_exports=["food"])
        market = Market(system, [food])

        price = market.get_price("food")
        assert price == 85, f"Specialty export should be 85 CR (−15%), got {price}"

    def test_specialty_import_amount(self) -> None:
        """Specialty import should increase price by ~15%."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_imports=["food"])
        market = Market(system, [food])

        price = market.get_price("food")
        # int(100 * 1.15) can be 114 or 115 due to float rounding
        assert 114 <= price <= 116, f"Specialty import should be ~115 CR (+15%), got {price}"

    def test_market_report_shows_specialty_export(self) -> None:
        """Market report should flag specialty export status."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_exports=["food"])
        market = Market(system, [food])

        report = market.get_market_report("food")
        assert report.get("is_specialty_export") is True
        assert report.get("is_specialty_import") is False
        assert "Excellent for buying" in report["analysis"]

    def test_market_report_shows_specialty_import(self) -> None:
        """Market report should flag specialty import status."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_imports=["food"])
        market = Market(system, [food])

        report = market.get_market_report("food")
        assert report.get("is_specialty_import") is True
        assert report.get("is_specialty_export") is False
        assert "Excellent for selling" in report["analysis"]

    def test_non_specialty_has_no_bonus(self) -> None:
        """Commodities not in specialty lists should have no specialty modifier."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(specialty_exports=["art"])  # food is not specialty
        market = Market(system, [food])

        price = market.get_price("food")
        assert price == 100, f"Non-specialty should be base price, got {price}"


class TestOffMarketSelling:
    """Players should be able to sell cargo even at systems that don't stock it."""

    def test_off_market_sell_returns_penalized_price(self) -> None:
        """Selling a commodity not available at this market gives 50% of base price."""
        food = _make_commodity("food", base_price=100)
        art = _make_commodity("art", base_price=500, category="luxury")

        # System only sells food — art is off-market
        system = _make_system(available_commodities=["food"])
        market = Market(system, [food, art])

        sell_price = market.get_sell_price("art")
        assert sell_price == 250, f"Off-market sell should be 50% of base (250), got {sell_price}"

    def test_on_market_sell_returns_full_price(self) -> None:
        """Selling a commodity the market stocks gives full market price."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(available_commodities=["food"])
        market = Market(system, [food])

        sell_price = market.get_sell_price("food")
        assert sell_price == 100, f"On-market sell should be full price (100), got {sell_price}"

    def test_off_market_sell_minimum_one_credit(self) -> None:
        """Off-market sell should never return 0 for valid commodities."""
        cheap = _make_commodity("cheap_thing", base_price=1)
        system = _make_system(available_commodities=[])
        market = Market(system, [cheap])

        sell_price = market.get_sell_price("cheap_thing")
        assert sell_price >= 1, "Off-market sell should be at least 1 CR"

    def test_unknown_commodity_returns_zero(self) -> None:
        """Selling a commodity that doesn't exist at all returns 0."""
        food = _make_commodity("food", base_price=100)
        system = _make_system(available_commodities=["food"])
        market = Market(system, [food])

        sell_price = market.get_sell_price("totally_fake_thing")
        assert sell_price == 0

    def test_off_market_incentivizes_proper_routes(self) -> None:
        """Selling at the right port should always be better than off-market."""
        art = _make_commodity("art", base_price=500, category="luxury")

        # Stellaris sells art (on-market)
        stellaris = _make_system("stellaris", available_commodities=["art"])
        # Breakstone doesn't sell art (off-market)
        breakstone = _make_system("breakstone", available_commodities=[])

        stellaris_price = Market(stellaris, [art]).get_sell_price("art")
        breakstone_price = Market(breakstone, [art]).get_sell_price("art")

        assert stellaris_price > breakstone_price, (
            f"On-market sell ({stellaris_price}) should beat off-market ({breakstone_price})"
        )


# ============================================================================
# Trade Route Integration
# ============================================================================


class TestTradeRouteIntegration:
    """Integration tests verifying realistic multi-system market scenarios."""

    def test_trade_route_profit_differential(self) -> None:
        """Buying specialty exports and selling as specialty imports should be profitable."""
        food = _make_commodity("food", base_price=50, production_tags=["food"],
                               consumption_tags=["food"])

        verdant = _make_system(
            "verdant",
            production_tags=["food"],
            specialty_exports=["food"],
        )
        breakstone = _make_system(
            "breakstone",
            consumption_tags=["food"],
            specialty_imports=["food"],
        )

        verdant_market = Market(verdant, [food])
        breakstone_market = Market(breakstone, [food])

        buy_price = verdant_market.get_price("food")
        sell_price = breakstone_market.get_sell_price("food")

        assert sell_price > buy_price, (
            f"Trade route should be profitable: buy@{buy_price}, sell@{sell_price}"
        )
        # With production(-25%) + specialty_export(-15%) = -40% buy
        # And consumption(+25%) + specialty_import(+15%) = +40% sell
        # Margin should be huge
        margin = (sell_price - buy_price) / buy_price
        assert margin >= 0.50, f"Profit margin should be >= 50%, got {margin:.0%}"

    def test_different_systems_different_commodities(self) -> None:
        """Two systems with different available lists should have different offerings."""
        food = _make_commodity("food")
        metals = _make_commodity("common_metals")
        art = _make_commodity("art", category="luxury")

        verdant = _make_system("verdant", available_commodities=["food"])
        forgeworks = _make_system("forgeworks", available_commodities=["common_metals"])

        verdant_market = Market(verdant, [food, metals, art])
        forge_market = Market(forgeworks, [food, metals, art])

        verdant_prices = verdant_market.get_all_prices()
        forge_prices = forge_market.get_all_prices()

        assert "food" in verdant_prices and "food" not in forge_prices
        assert "common_metals" in forge_prices and "common_metals" not in verdant_prices
        assert "art" not in verdant_prices and "art" not in forge_prices

    def test_trade_hub_has_widest_selection(self) -> None:
        """Trade hubs should offer more commodities than specialized systems."""
        commodities = [
            _make_commodity("food"),
            _make_commodity("common_metals"),
            _make_commodity("art", category="luxury"),
            _make_commodity("electronics", category="industrial"),
            _make_commodity("fuel"),
        ]

        trade_hub = _make_system(
            "nexus",
            available_commodities=["food", "common_metals", "art", "electronics", "fuel"],
        )
        mining_outpost = _make_system(
            "breakstone",
            available_commodities=["common_metals", "fuel"],
        )

        hub_market = Market(trade_hub, commodities)
        mining_market = Market(mining_outpost, commodities)

        assert len(hub_market.get_all_prices()) > len(mining_market.get_all_prices())

    def test_same_commodity_different_prices_across_systems(self) -> None:
        """The same commodity should have different prices at different systems."""
        food = _make_commodity("food", base_price=50, production_tags=["food"],
                               consumption_tags=["food"])

        producer = _make_system("verdant", production_tags=["food"],
                                specialty_exports=["food"])
        neutral = _make_system("nexus")
        consumer = _make_system("breakstone", consumption_tags=["food"],
                                specialty_imports=["food"])

        producer_price = Market(producer, [food]).get_price("food")
        neutral_price = Market(neutral, [food]).get_price("food")
        consumer_price = Market(consumer, [food]).get_price("food")

        assert producer_price < neutral_price < consumer_price, (
            f"Price gradient should be producer({producer_price}) < neutral({neutral_price}) "
            f"< consumer({consumer_price})"
        )


# ============================================================================
# Economy Model
# ============================================================================


class TestEconomyModel:
    """Tests for the Economy dataclass new fields."""

    def test_economy_defaults(self) -> None:
        """New fields should have sensible defaults for backward compatibility."""
        economy = Economy(
            production_tags=["food"],
            consumption_tags=["fuel"],
            tariff_rate=0.02,
        )
        assert economy.available_commodities is None
        assert economy.specialty_exports == []
        assert economy.specialty_imports == []

    def test_economy_with_all_fields(self) -> None:
        """Economy should accept all new fields."""
        economy = Economy(
            production_tags=["food"],
            consumption_tags=["fuel"],
            tariff_rate=0.02,
            available_commodities=["food", "fuel", "metals"],
            specialty_exports=["food"],
            specialty_imports=["fuel"],
        )
        assert economy.available_commodities == ["food", "fuel", "metals"]
        assert economy.specialty_exports == ["food"]
        assert economy.specialty_imports == ["fuel"]


# ============================================================================
# Data Loading Integration
# ============================================================================


class TestDataLoaderRegionalMarket:
    """Tests that DataLoader correctly parses new economy fields from systems.json."""

    def test_systems_load_without_new_fields(self) -> None:
        """Systems without new economy fields should load with defaults."""
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()

        # All systems should load successfully
        nexus = loader.get_system("nexus_prime")
        assert nexus is not None
        assert nexus.economy is not None

    def test_existing_market_still_works(self) -> None:
        """Existing market creation should still work with loaded data."""
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()

        nexus = loader.get_system("nexus_prime")
        commodities = loader.get_all_commodities()

        # Should not crash
        market = Market(nexus, commodities, game_day=1)

        # Should have prices
        prices = market.get_all_prices()
        assert len(prices) > 0, "Market should have at least some commodities"

        # All prices should be positive
        for cid, price in prices.items():
            assert price > 0, f"{cid} should have positive price"


class TestLiveMarketProfiles:
    """Validate the actual market profiles in systems.json are well-formed and strategic."""

    def _load(self):
        from spacegame.data_loader import DataLoader
        loader = DataLoader()
        loader.load_all()
        return loader

    def test_every_system_has_market_profile(self) -> None:
        """All systems should have available_commodities defined."""
        loader = self._load()
        for system_id in ["nexus_prime", "verdant", "forgeworks", "breakstone",
                          "axiom_labs", "havens_rest", "crimson_reach", "stellaris_port",
                          "iron_depths", "nova_research", "the_fulcrum"]:
            system = loader.get_system(system_id)
            assert system.economy.available_commodities is not None, (
                f"{system_id} should have available_commodities"
            )

    def test_specialty_exports_are_available(self) -> None:
        """Every specialty export should be in the available_commodities list."""
        loader = self._load()
        for sid, system in loader.systems.items():
            available = set(system.economy.available_commodities or [])
            for export in system.economy.specialty_exports:
                assert export in available, (
                    f"{sid}: specialty export '{export}' not in available_commodities"
                )

    def test_specialty_imports_are_available(self) -> None:
        """Every specialty import should be in the available_commodities list
        OR represent a commodity the system wants but doesn't stock
        (player can still sell it)."""
        loader = self._load()
        commodity_ids = set(loader.commodities.keys())
        for sid, system in loader.systems.items():
            for imp in system.economy.specialty_imports:
                assert imp in commodity_ids, (
                    f"{sid}: specialty import '{imp}' is not a valid commodity"
                )

    def test_available_commodities_are_valid(self) -> None:
        """All commodity IDs in available_commodities should be real commodity IDs."""
        loader = self._load()
        commodity_ids = set(loader.commodities.keys())
        for sid, system in loader.systems.items():
            for cid in (system.economy.available_commodities or []):
                assert cid in commodity_ids, (
                    f"{sid}: available commodity '{cid}' is not a valid commodity"
                )

    def test_all_commodities_available_somewhere(self) -> None:
        """Every non-quest commodity should be available in at least one system."""
        loader = self._load()
        commodity_ids = {
            cid for cid, c in loader.commodities.items()
            if c.base_price > 0
        }
        available_anywhere: set[str] = set()
        for system in loader.systems.values():
            available_anywhere.update(system.economy.available_commodities or [])

        missing = commodity_ids - available_anywhere
        assert missing == set(), f"Commodities not available anywhere: {missing}"

    def test_food_and_fuel_widely_available(self) -> None:
        """Food and fuel should be available at most systems (essential goods)."""
        loader = self._load()
        food_count = sum(
            1 for s in loader.systems.values()
            if "food" in (s.economy.available_commodities or [])
        )
        fuel_count = sum(
            1 for s in loader.systems.values()
            if "fuel" in (s.economy.available_commodities or [])
        )
        total = len(loader.systems)
        assert food_count >= total * 0.8, f"Food should be at 80%+ of systems, found {food_count}/{total}"
        assert fuel_count >= total * 0.8, f"Fuel should be at 80%+ of systems, found {fuel_count}/{total}"

    def test_trade_hubs_have_most_variety(self) -> None:
        """Trade hubs (Nexus Prime, Stellaris Port) should have the most commodities."""
        loader = self._load()
        nexus_count = len(loader.get_system("nexus_prime").economy.available_commodities)
        stellaris_count = len(loader.get_system("stellaris_port").economy.available_commodities)

        for sid, system in loader.systems.items():
            if system.type not in ("trade_hub",):
                system_count = len(system.economy.available_commodities or [])
                assert system_count <= max(nexus_count, stellaris_count), (
                    f"{sid} ({system_count} commodities) has more than trade hubs"
                )

    def test_food_trade_route_verdant_to_breakstone(self) -> None:
        """Classic route: buy food at Verdant (producer), sell at Breakstone (consumer)."""
        loader = self._load()
        commodities = loader.get_all_commodities()

        verdant_market = Market(loader.get_system("verdant"), commodities, game_day=1)
        breakstone_market = Market(loader.get_system("breakstone"), commodities, game_day=1)

        buy_price = verdant_market.get_price("food")
        sell_price = breakstone_market.get_sell_price("food")

        assert sell_price > buy_price, (
            f"Food should be cheaper at Verdant ({buy_price}) than Breakstone ({sell_price})"
        )

    def test_metals_trade_route_breakstone_to_forgeworks(self) -> None:
        """Buy raw ore at Breakstone, sell to Forgeworks."""
        loader = self._load()
        commodities = loader.get_all_commodities()

        # Both systems should have raw_ore or iron_ore
        breakstone = Market(loader.get_system("breakstone"), commodities, game_day=1)
        forgeworks = Market(loader.get_system("forgeworks"), commodities, game_day=1)

        # Breakstone exports ores cheaply
        for ore_id in ["raw_ore", "iron_ore"]:
            if breakstone.get_price(ore_id) > 0 and forgeworks.get_price(ore_id) > 0:
                assert breakstone.get_price(ore_id) <= forgeworks.get_price(ore_id), (
                    f"{ore_id} should be cheaper at Breakstone than Forgeworks"
                )

    def test_dangerous_systems_have_unique_goods(self) -> None:
        """Dangerous systems should have items not available in safe systems."""
        loader = self._load()
        safe_commodities: set[str] = set()
        dangerous_commodities: set[str] = set()

        for system in loader.systems.values():
            available = set(system.economy.available_commodities or [])
            if system.danger_level == "safe":
                safe_commodities.update(available)
            elif system.danger_level == "dangerous":
                dangerous_commodities.update(available)

        unique_to_dangerous = dangerous_commodities - safe_commodities
        assert len(unique_to_dangerous) > 0, (
            "Dangerous systems should have at least some goods not available in safe systems"
        )

    def test_no_system_has_all_commodities(self) -> None:
        """No single system should have every commodity — forces travel."""
        loader = self._load()
        all_commodity_count = len([c for c in loader.commodities.values() if c.base_price > 0])

        for sid, system in loader.systems.items():
            available_count = len(system.economy.available_commodities or [])
            assert available_count < all_commodity_count, (
                f"{sid} has all {available_count} commodities — should force travel"
            )
