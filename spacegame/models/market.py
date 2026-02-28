"""
Market and pricing system.

Implements dynamic pricing based on supply/demand, system economy, and random variance.
"""

import random
from typing import Dict, List, Optional
from spacegame.models.commodity import Commodity
from spacegame.models.system import StarSystem
from spacegame.models.event import MarketEvent


class Market:
    """
    Manages commodity pricing for a specific system.

    Prices are calculated dynamically based on:
    - Base commodity price
    - System production/consumption tags
    - Random variance
    - Game events (future feature)
    """

    def __init__(self, system: StarSystem, commodities: List[Commodity], game_day: int = 1):
        """
        Initialize market for a system.

        Args:
            system: The star system this market serves
            commodities: List of all available commodities
            game_day: Current game day (for seeding variance)
        """
        self.system = system
        self.commodities = {c.id: c for c in commodities}
        self.game_day = game_day
        self._price_cache: Dict[str, int] = {}
        self.active_event: Optional[MarketEvent] = None  # Current market event
        self._generate_prices()

    def _generate_prices(self) -> None:
        """Generate current prices for all commodities based on market conditions."""
        self._price_cache.clear()

        for commodity_id, commodity in self.commodities.items():
            price = self._calculate_price(commodity)
            self._price_cache[commodity_id] = price

    def _calculate_price(self, commodity: Commodity) -> int:
        """
        Calculate current market price for a commodity.

        Formula: base_price × (1 + supply_demand_modifier + random_variance) × event_multiplier

        Args:
            commodity: Commodity to price

        Returns:
            Current market price
        """
        base_price = commodity.base_price

        # Supply/Demand modifier based on system economy
        supply_demand_mod = self._get_supply_demand_modifier(commodity)

        # Random variance (small fluctuation)
        random_mod = self._get_random_variance(commodity)

        # Calculate base final price
        total_modifier = 1.0 + supply_demand_mod + random_mod
        final_price = int(base_price * total_modifier)

        # Apply event multiplier if active event affects this commodity
        if (
            self.active_event
            and self.active_event.commodity_id == commodity.id
            and self.active_event.is_active(self.game_day)
        ):
            final_price = int(final_price * self.active_event.price_multiplier)

        # Ensure minimum price of 1 CR (events can push outside normal range)
        return max(1, final_price)

    def _get_supply_demand_modifier(self, commodity: Commodity) -> float:
        """
        Calculate supply/demand modifier based on system economy.

        Production systems (supply) → Lower prices (-20% to -30%)
        Consumption systems (demand) → Higher prices (+20% to +30%)

        Args:
            commodity: Commodity to evaluate

        Returns:
            Modifier as decimal (e.g., -0.25 = -25%)
        """
        modifier = 0.0

        # Check if system produces this commodity (reduces price)
        if commodity.is_produced_by(self.system.economy.production_tags):
            modifier -= 0.25  # 25% discount

        # Check if system consumes this commodity (increases price)
        if commodity.is_consumed_by(self.system.economy.consumption_tags):
            modifier += 0.25  # 25% premium

        return modifier

    def _get_random_variance(self, commodity: Commodity) -> float:
        """
        Generate small random price fluctuation.

        Uses game day and commodity ID as seed for deterministic randomness.

        Args:
            commodity: Commodity to vary

        Returns:
            Small random modifier (-0.05 to +0.05 typically)
        """
        # Seed random with game day and commodity for determinism
        random.seed(f"{self.game_day}_{commodity.id}_{self.system.id}")

        # Small variance: ±5% to ±10% depending on commodity volatility
        variance_range = abs(commodity.variance_max - commodity.variance_min)
        max_random = min(0.10, variance_range * 0.2)  # 20% of commodity's total range

        variance = random.uniform(-max_random, max_random)

        # Reset random seed
        random.seed()

        return variance

    def get_price(self, commodity_id: str) -> int:
        """
        Get current buy price for a commodity.

        Args:
            commodity_id: ID of commodity

        Returns:
            Current market price, or 0 if commodity not available
        """
        return self._price_cache.get(commodity_id, 0)

    def get_sell_price(self, commodity_id: str) -> int:
        """
        Get price player receives when selling.

        Currently same as buy price. Could add spread/fee in future.

        Args:
            commodity_id: ID of commodity

        Returns:
            Sell price
        """
        return self.get_price(commodity_id)

    def get_all_prices(self) -> Dict[str, int]:
        """
        Get all current market prices.

        Returns:
            Dict mapping commodity_id to price
        """
        return self._price_cache.copy()

    def get_market_report(self, commodity_id: str) -> Dict[str, any]:
        """
        Get detailed market information for a commodity.

        Args:
            commodity_id: Commodity to analyze

        Returns:
            Dict with price, trend indicators, and analysis
        """
        if commodity_id not in self.commodities:
            return {}

        commodity = self.commodities[commodity_id]
        current_price = self.get_price(commodity_id)
        base_price = commodity.base_price

        # Calculate how current price compares to base
        price_diff_pct = ((current_price - base_price) / base_price) * 100

        # Determine trend
        if price_diff_pct < -15:
            trend = "Very Low"
        elif price_diff_pct < -5:
            trend = "Low"
        elif price_diff_pct > 15:
            trend = "Very High"
        elif price_diff_pct > 5:
            trend = "High"
        else:
            trend = "Normal"

        # Market analysis
        is_produced = commodity.is_produced_by(self.system.economy.production_tags)
        is_consumed = commodity.is_consumed_by(self.system.economy.consumption_tags)

        if is_produced:
            analysis = "Local production - Good for buying"
        elif is_consumed:
            analysis = "High demand - Good for selling"
        else:
            analysis = "No special factors"

        return {
            "commodity_id": commodity_id,
            "commodity_name": commodity.name,
            "current_price": current_price,
            "base_price": base_price,
            "price_diff_pct": price_diff_pct,
            "trend": trend,
            "analysis": analysis,
            "is_produced_here": is_produced,
            "is_consumed_here": is_consumed,
        }

    def update_day(self, new_day: int) -> None:
        """
        Update market for a new game day.

        Regenerates prices with new random variance.
        Checks if active event has expired.

        Args:
            new_day: New game day number
        """
        self.game_day = new_day

        # Clear expired events
        if self.active_event and not self.active_event.is_active(new_day):
            self.active_event = None

        self._generate_prices()

    def apply_event(self, event: MarketEvent) -> None:
        """
        Apply a market event to this market.

        Args:
            event: Market event to apply
        """
        self.active_event = event
        self._generate_prices()  # Recalculate prices with event

    def get_active_event(self) -> Optional[MarketEvent]:
        """
        Get the currently active event if any.

        Returns:
            Active market event or None
        """
        if self.active_event and self.active_event.is_active(self.game_day):
            return self.active_event
        return None
