"""
Market and pricing system.

Implements dynamic pricing based on supply/demand, system economy, and random variance.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from spacegame.models.commodity import Commodity
from spacegame.models.event import MarketEvent
from spacegame.models.system import StarSystem

if TYPE_CHECKING:
    from spacegame.models.politics_dispute import PoliticsMarketShift


@dataclass
class PriceHistory:
    """Tracks per-system, per-commodity price history over recent days.

    Used to show price trend indicators in the trading view.
    """

    _history: dict[str, dict[str, list[tuple[int, int]]]] = field(default_factory=dict)
    max_days: int = 7

    def record(self, system_id: str, commodity_id: str, day: int, price: int) -> None:
        """Record a price data point.

        Args:
            system_id: System where the price was observed.
            commodity_id: Commodity being tracked.
            day: Game day of the observation.
            price: The observed price.
        """
        if system_id not in self._history:
            self._history[system_id] = {}
        if commodity_id not in self._history[system_id]:
            self._history[system_id][commodity_id] = []

        entries = self._history[system_id][commodity_id]
        entries.append((day, price))

        # Trim to max_days most recent
        if len(entries) > self.max_days:
            self._history[system_id][commodity_id] = entries[-self.max_days :]

    def get_history(self, system_id: str, commodity_id: str) -> list[tuple[int, int]]:
        """Get price history for a system/commodity pair.

        Args:
            system_id: System to look up.
            commodity_id: Commodity to look up.

        Returns:
            List of (day, price) tuples, oldest first.
        """
        return self._history.get(system_id, {}).get(commodity_id, [])

    def get_trend(self, system_id: str, commodity_id: str) -> str:
        """Determine price trend from recent history.

        Args:
            system_id: System to analyze.
            commodity_id: Commodity to analyze.

        Returns:
            "rising", "falling", or "stable".
        """
        entries = self.get_history(system_id, commodity_id)
        if len(entries) < 2:
            return "stable"

        first_price = entries[0][1]
        last_price = entries[-1][1]
        diff_pct = (last_price - first_price) / max(1, first_price)

        if diff_pct > 0.05:
            return "rising"
        elif diff_pct < -0.05:
            return "falling"
        return "stable"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "max_days": self.max_days,
            "history": self._history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceHistory":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with max_days and history.

        Returns:
            PriceHistory instance.
        """
        ph = cls(max_days=data.get("max_days", 7))
        raw = data.get("history", {})
        # Convert nested lists back to list of tuples
        for sys_id, commodities in raw.items():
            ph._history[sys_id] = {}
            for com_id, entries in commodities.items():
                ph._history[sys_id][com_id] = [(e[0], e[1]) for e in entries]
        return ph


class Market:
    """
    Manages commodity pricing for a specific system.

    Prices are calculated dynamically based on:
    - Base commodity price
    - System production/consumption tags
    - Random variance
    - Game events (future feature)
    """

    # Player activity impact per unit bought/sold
    _PLAYER_MODIFIER_PER_UNIT = 0.02
    _PLAYER_MODIFIER_CAP = 0.30
    _PLAYER_MODIFIER_DECAY = 0.70  # Retain 70% per day (30% decay)

    # Stock levels by production relationship
    _STOCK_PRODUCED = 100
    _STOCK_CONSUMED = 30
    _STOCK_NEUTRAL = 10
    _STOCK_REGEN_RATE = 0.30  # 30% of base stock regenerated per day

    def __init__(self, system: StarSystem, commodities: List[Commodity], game_day: int = 1):
        """
        Initialize market for a system.

        Args:
            system: The star system this market serves
            commodities: List of all available commodities
            game_day: Current game day (for seeding variance)
        """
        self.system = system
        self._all_commodities = {c.id: c for c in commodities}

        # Filter to only commodities available at this system
        available = system.economy.available_commodities
        if available is not None:
            self.commodities = {
                cid: c for cid, c in self._all_commodities.items() if cid in available
            }
        else:
            self.commodities = self._all_commodities

        self.game_day = game_day
        self._price_cache: Dict[str, int] = {}
        self.active_event: Optional[MarketEvent] = None  # Current market event
        self.galaxy_events: list = []  # Active GalaxyEvent instances at this system
        self._player_supply_demand: Dict[str, float] = {}
        self._stock: Dict[str, int] = {}
        self._base_stock: Dict[str, int] = {}
        # SA-P2 politics market shifts. Keyed by (commodity_id, system_id).
        # Stack rule (§11 decision 14): the largest absolute magnitude
        # active for the pair is the one applied; shifts decay
        # independently after their own duration_days expire.
        self._politics_shifts: Dict[
            tuple[str, str], list["PoliticsMarketShift"]
        ] = {}
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

        # Player activity modifier
        player_mod = self._player_supply_demand.get(commodity.id, 0.0)

        # Calculate base final price
        total_modifier = 1.0 + supply_demand_mod + random_mod + player_mod
        final_price = int(base_price * total_modifier)

        # Apply event multiplier if active event affects this commodity
        if (
            self.active_event
            and self.active_event.commodity_id == commodity.id
            and self.active_event.is_active(self.game_day)
        ):
            final_price = int(final_price * self.active_event.price_multiplier)

        # SA-P2: apply the largest-magnitude active politics shift for
        # (commodity, system). Shifts coexist with `active_event`: they
        # multiply on top, they don't replace.
        politics_shift = self._dominant_politics_shift(commodity.id)
        if politics_shift is not None:
            final_price = int(final_price * (1.0 + politics_shift.magnitude))

        # Apply galaxy event effects (embargo, festival, breakthrough, strike)
        for ge in self.galaxy_events:
            if not ge.is_active(self.game_day):
                continue

            # EMBARGO: blocked commodities cannot be traded legally
            if commodity.id in ge.blocked_commodities:
                return 0

            # FESTIVAL / BREAKTHROUGH: apply price modifiers
            if commodity.id in ge.price_modifiers:
                final_price = int(final_price * ge.price_modifiers[commodity.id])

            # LABOR_STRIKE: production shutdown raises prices at producing systems
            if ge.shutdown_tags:
                for tag in ge.shutdown_tags:
                    if tag in self.system.economy.production_tags:
                        if commodity.is_produced_by([tag]):
                            final_price = int(final_price * 1.25)

        # Ensure minimum price of 1 CR (events can push outside normal range)
        # Except for embargoed commodities (returned 0 above)
        return max(1, final_price)

    # Specialty pricing modifiers (stacks with production/consumption tags)
    _SPECIALTY_EXPORT_MODIFIER = -0.15  # 15% additional discount
    _SPECIALTY_IMPORT_MODIFIER = 0.15  # 15% additional premium

    def _get_supply_demand_modifier(self, commodity: Commodity) -> float:
        """
        Calculate supply/demand modifier based on system economy.

        Production systems (supply) → Lower prices (-25%)
        Consumption systems (demand) → Higher prices (+25%)
        Specialty exports → Additional -15% (stacks with production)
        Specialty imports → Additional +15% (stacks with consumption)

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

        # Specialty export: this system is known for selling this cheap
        if commodity.id in self.system.economy.specialty_exports:
            modifier += self._SPECIALTY_EXPORT_MODIFIER

        # Specialty import: this system has high demand for this
        if commodity.id in self.system.economy.specialty_imports:
            modifier += self._SPECIALTY_IMPORT_MODIFIER

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

    # Penalty applied when selling goods the local market doesn't normally stock
    _OFF_MARKET_SELL_PENALTY = 0.50  # 50% of base price

    def get_sell_price(self, commodity_id: str) -> int:
        """
        Get price player receives when selling.

        If the commodity is available at this market, returns the market price.
        If not available (off-market sale), returns base price × 50% penalty —
        the player can always sell cargo, but gets a poor deal at the wrong port.

        Args:
            commodity_id: ID of commodity

        Returns:
            Sell price (always >= 1 for valid commodities)
        """
        market_price = self.get_price(commodity_id)
        if market_price > 0:
            return market_price

        # Off-market sale: commodity not stocked here, but player can still sell
        commodity = self._all_commodities.get(commodity_id)
        if commodity and commodity.base_price > 0:
            return max(1, int(commodity.base_price * self._OFF_MARKET_SELL_PENALTY))
        return 0

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
        if base_price > 0:
            price_diff_pct = ((current_price - base_price) / base_price) * 100
        else:
            price_diff_pct = 0.0

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
        is_specialty_export = commodity_id in self.system.economy.specialty_exports
        is_specialty_import = commodity_id in self.system.economy.specialty_imports

        if is_specialty_export:
            analysis = "Regional specialty - Excellent for buying"
        elif is_produced:
            analysis = "Local production - Good for buying"
        elif is_specialty_import:
            analysis = "High local demand - Excellent for selling"
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
            "is_specialty_export": is_specialty_export,
            "is_specialty_import": is_specialty_import,
        }

    def record_buy(self, commodity_id: str, quantity: int) -> None:
        """Record player buying, increasing demand pressure.

        Args:
            commodity_id: Commodity bought.
            quantity: Amount purchased.
        """
        current = self._player_supply_demand.get(commodity_id, 0.0)
        new_mod = current + quantity * self._PLAYER_MODIFIER_PER_UNIT
        self._player_supply_demand[commodity_id] = min(new_mod, self._PLAYER_MODIFIER_CAP)

    def record_sell(self, commodity_id: str, quantity: int) -> None:
        """Record player selling, increasing supply pressure.

        Args:
            commodity_id: Commodity sold.
            quantity: Amount sold.
        """
        current = self._player_supply_demand.get(commodity_id, 0.0)
        new_mod = current - quantity * self._PLAYER_MODIFIER_PER_UNIT
        self._player_supply_demand[commodity_id] = max(new_mod, -self._PLAYER_MODIFIER_CAP)

    def initialize_stock(self, system: StarSystem, commodities: List[Commodity]) -> None:
        """Initialize stock levels based on system production/consumption.

        Args:
            system: The star system.
            commodities: All commodities (used for tag checking).
        """
        self._stock.clear()
        self._base_stock.clear()

        for commodity_id, commodity in self.commodities.items():
            if commodity.base_price <= 0:
                continue  # Skip quest items
            is_produced = commodity.is_produced_by(system.economy.production_tags)
            is_consumed = commodity.is_consumed_by(system.economy.consumption_tags)

            if is_produced:
                base = self._STOCK_PRODUCED
            elif is_consumed:
                base = self._STOCK_CONSUMED
            else:
                base = self._STOCK_NEUTRAL

            self._base_stock[commodity_id] = base
            self._stock[commodity_id] = base

    def get_stock(self, commodity_id: str) -> int:
        """Get current stock of a commodity.

        Args:
            commodity_id: Commodity to check.

        Returns:
            Current stock level, 0 if not stocked.
        """
        return self._stock.get(commodity_id, 0)

    def get_base_stock(self, commodity_id: str) -> int:
        """Get base (maximum) stock of a commodity.

        Args:
            commodity_id: Commodity to check.

        Returns:
            Base stock level, 0 if not stocked.
        """
        return self._base_stock.get(commodity_id, 0)

    def deplete_stock(self, commodity_id: str, quantity: int) -> tuple[bool, str]:
        """Deplete stock when player buys.

        Args:
            commodity_id: Commodity being purchased.
            quantity: Amount to deplete.

        Returns:
            Tuple of (success, message).
        """
        current = self._stock.get(commodity_id, 0)
        if quantity > current:
            return (False, f"Only {current} units in stock")
        self._stock[commodity_id] = current - quantity
        return (True, f"Stock depleted: {current - quantity} remaining")

    def regenerate_stock(self) -> None:
        """Regenerate stock for all commodities (called daily).

        Restores 30% of base stock per day, capped at base.
        """
        for commodity_id, base in self._base_stock.items():
            current = self._stock.get(commodity_id, 0)
            regen = int(base * self._STOCK_REGEN_RATE)
            self._stock[commodity_id] = min(base, current + regen)

    def update_day(self, new_day: int) -> None:
        """
        Update market for a new game day.

        Regenerates prices with new random variance.
        Decays player supply/demand modifiers.
        Checks if active event has expired.
        Expires SA-P2 politics shifts whose ``start_day + duration_days``
        has elapsed.

        Args:
            new_day: New game day number
        """
        self.game_day = new_day

        # Decay player supply/demand modifiers
        expired_keys = []
        for cid in self._player_supply_demand:
            self._player_supply_demand[cid] *= self._PLAYER_MODIFIER_DECAY
            if abs(self._player_supply_demand[cid]) < 0.001:
                expired_keys.append(cid)
        for cid in expired_keys:
            del self._player_supply_demand[cid]

        # Clear expired events
        if self.active_event and not self.active_event.is_active(new_day):
            self.active_event = None

        # SA-P2: expire politics shifts whose duration has elapsed.
        empty_keys: list[tuple[str, str]] = []
        for key, shifts in self._politics_shifts.items():
            self._politics_shifts[key] = [
                s for s in shifts if new_day < s.start_day + s.duration_days
            ]
            if not self._politics_shifts[key]:
                empty_keys.append(key)
        for key in empty_keys:
            del self._politics_shifts[key]

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

    # ------------------------------------------------------------------
    # SA-P2 politics market shift registry (§7.2)
    # ------------------------------------------------------------------

    def add_politics_shift(self, shift: "PoliticsMarketShift") -> None:
        """Register a politics-driven price shift on this market.

        Multiple shifts may target the same (commodity, system) pair;
        the largest absolute magnitude wins per §11 decision 14. Shifts
        decay independently when their own duration_days expire.
        """
        if shift.system_id != self.system.id:
            return
        key = (shift.commodity_id, shift.system_id)
        self._politics_shifts.setdefault(key, []).append(shift)
        self._generate_prices()

    def get_active_politics_shifts(
        self, commodity_id: str, system_id: str
    ) -> list["PoliticsMarketShift"]:
        """Return active (unexpired) politics shifts for this (commodity, system)."""
        key = (commodity_id, system_id)
        shifts = self._politics_shifts.get(key, [])
        return [
            s for s in shifts if self.game_day < s.start_day + s.duration_days
        ]

    def _dominant_politics_shift(
        self, commodity_id: str
    ) -> Optional["PoliticsMarketShift"]:
        """Largest-absolute-magnitude active shift for a commodity at this market."""
        actives = self.get_active_politics_shifts(commodity_id, self.system.id)
        if not actives:
            return None
        return max(actives, key=lambda s: abs(s.magnitude))

    def to_dict(self) -> dict:
        """Serialize player-driven supply/demand and stock state.

        Returns:
            Dictionary with player_supply_demand and stock data.
        """
        return {
            "player_supply_demand": dict(self._player_supply_demand),
            "stock": dict(self._stock),
            "base_stock": dict(self._base_stock),
            "politics_shifts": [
                {
                    "commodity_id": s.commodity_id,
                    "system_id": s.system_id,
                    "magnitude": s.magnitude,
                    "duration_days": s.duration_days,
                    "start_day": s.start_day,
                }
                for shifts in self._politics_shifts.values()
                for s in shifts
            ],
        }

    def load_supply_demand(self, data: dict) -> None:
        """Restore player supply/demand and stock from saved data.

        Args:
            data: Dictionary from to_dict().
        """
        self._player_supply_demand = dict(data.get("player_supply_demand", {}))
        if "stock" in data:
            self._stock = dict(data["stock"])
        if "base_stock" in data:
            self._base_stock = dict(data["base_stock"])
        # SA-P2 politics shifts.
        from spacegame.models.politics_dispute import PoliticsMarketShift

        self._politics_shifts = {}
        for entry in data.get("politics_shifts", []):
            shift = PoliticsMarketShift(
                commodity_id=entry["commodity_id"],
                system_id=entry["system_id"],
                magnitude=float(entry["magnitude"]),
                duration_days=int(entry.get("duration_days", 30)),
                start_day=int(entry.get("start_day", 0)),
            )
            self.add_politics_shift(shift)
