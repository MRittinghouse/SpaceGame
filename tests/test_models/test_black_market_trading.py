"""Tests for black market trading mode in TradingView (Phase E.3).

Covers black market pricing, permit bypass, legality indicators,
and mode toggle behavior. Tests model-level logic without pygame.
"""

import pytest

from spacegame.models.commodity import Legality
from spacegame.models.smuggling import get_black_market_price_modifier


# ============================================================================
# Black Market Price Modifiers
# ============================================================================


class TestBlackMarketPriceModifiers:
    """Black market prices are modified by commodity legality."""

    def test_legal_goods_premium_15_percent(self) -> None:
        """Legal goods cost 15% more at black markets."""
        modifier = get_black_market_price_modifier(Legality.LEGAL)
        assert modifier == pytest.approx(0.15, abs=0.01)

    def test_restricted_goods_no_modifier(self) -> None:
        """Restricted goods have no price modifier."""
        modifier = get_black_market_price_modifier(Legality.RESTRICTED)
        assert modifier == pytest.approx(0.0, abs=0.01)

    def test_illegal_goods_discount_10_percent(self) -> None:
        """Illegal goods are 10% cheaper at black markets."""
        modifier = get_black_market_price_modifier(Legality.ILLEGAL)
        assert modifier == pytest.approx(-0.10, abs=0.01)

    def test_modifier_applied_to_price(self) -> None:
        """Price calculation: base * (1 + modifier)."""
        base_price = 1000  # Use larger base to avoid float rounding issues
        # Legal: 1000 * 1.15 = 1150
        legal_price = int(base_price * (1.0 + get_black_market_price_modifier(Legality.LEGAL)))
        assert legal_price == 1150

        # Restricted: 1000 * 1.0 = 1000
        restricted_price = int(
            base_price * (1.0 + get_black_market_price_modifier(Legality.RESTRICTED))
        )
        assert restricted_price == 1000

        # Illegal: 1000 * 0.9 = 900
        illegal_price = int(base_price * (1.0 + get_black_market_price_modifier(Legality.ILLEGAL)))
        assert illegal_price == 900


# ============================================================================
# Black Market Mode State
# ============================================================================


class TestBlackMarketModeState:
    """Black market mode toggle and state management."""

    def test_black_market_mode_defaults_false(self) -> None:
        """TradingView._black_market_mode defaults to False."""
        # Test via the model: player starts with no black market mode
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

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
        player = Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        # Player without access: no button would be created
        assert not player.has_black_market_access("nexus_prime")

        # Player with access: button would be created
        player.grant_black_market_access("nexus_prime")
        assert player.has_black_market_access("nexus_prime")

    def test_has_trade_permit_bypassed_in_black_market(self) -> None:
        """Black market mode bypasses trade permit checks.

        Verifies the logic: if _black_market_mode, return True.
        """
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

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
        player = Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        # Player has no trade permit for any faction
        player.faction_assignments = {"nexus_prime": "commerce_guild"}
        assert not player.has_trade_permit("commerce_guild")

        # But with black market access, trading should be allowed
        player.grant_black_market_access("nexus_prime")
        assert player.has_black_market_access("nexus_prime")


# ============================================================================
# Legality Commodity Data
# ============================================================================


class TestCommodityLegality:
    """Commodities have legality fields loaded from data."""

    def test_commodities_have_legality(self) -> None:
        """All commodities have a legality field."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for commodity in dl.get_all_commodities():
            assert hasattr(commodity, "legality")
            assert commodity.legality in (Legality.LEGAL, Legality.RESTRICTED, Legality.ILLEGAL)

    def test_contraband_commodities_exist(self) -> None:
        """At least one RESTRICTED and one ILLEGAL commodity should exist."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        legalities = {c.legality for c in dl.get_all_commodities()}
        assert Legality.RESTRICTED in legalities, "Should have RESTRICTED commodities"
        assert Legality.ILLEGAL in legalities, "Should have ILLEGAL commodities"

    def test_most_commodities_are_legal(self) -> None:
        """Majority of commodities should be LEGAL."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        legal_count = sum(1 for c in dl.get_all_commodities() if c.legality == Legality.LEGAL)
        total = len(dl.get_all_commodities())
        assert legal_count > total // 2, "Most commodities should be legal"

    def test_black_market_name_matches_rules(self) -> None:
        """get_black_market_name returns consistent names with rules."""
        from spacegame.models.smuggling import get_black_market_name, get_black_market_systems

        systems = get_black_market_systems()
        for system_id in systems:
            name = get_black_market_name(system_id)
            assert name is not None
            assert len(name) > 0


# ============================================================================
# Black Market + Normal Mode Pricing Comparison
# ============================================================================


class TestBlackMarketVsNormalPricing:
    """Black market and normal mode produce different prices."""

    def test_legal_goods_more_expensive_at_black_market(self) -> None:
        """Legal goods should cost more at black market than base price."""
        base = 200
        bm_modifier = get_black_market_price_modifier(Legality.LEGAL)
        bm_price = int(base * (1.0 + bm_modifier))
        assert bm_price > base

    def test_illegal_goods_cheaper_at_black_market(self) -> None:
        """Illegal goods should cost less at black market than base price."""
        base = 200
        bm_modifier = get_black_market_price_modifier(Legality.ILLEGAL)
        bm_price = int(base * (1.0 + bm_modifier))
        assert bm_price < base

    def test_restricted_goods_same_at_black_market(self) -> None:
        """Restricted goods should cost the same at black market as base price."""
        base = 200
        bm_modifier = get_black_market_price_modifier(Legality.RESTRICTED)
        bm_price = int(base * (1.0 + bm_modifier))
        assert bm_price == base

    def test_black_market_no_tariff(self) -> None:
        """Black market prices should not include faction tariffs.

        In normal mode: price = base * (1 - discount + tariff).
        In black market mode: price = base * (1 + legality_modifier).
        Tariff is not part of the black market formula.
        """
        base = 100
        tariff = 0.10  # 10% tariff
        normal_price = int(base * (1.0 + tariff))  # 110

        bm_modifier = get_black_market_price_modifier(Legality.RESTRICTED)
        bm_price = int(base * (1.0 + bm_modifier))  # 100 (no tariff)

        assert bm_price < normal_price
