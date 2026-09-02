"""Futures contract sub-system for Meridian Financial Exchange (SA-F2).

Model layer only: SA-F3 owns the Meridian broker terminal UI and the
preview surface. This module owns:

- :class:`FuturesContract` dataclass — a single accepted futures position.
- :class:`FuturesState` sub-model — the player's active + settled contract
  registry with per-day settlement lifecycle.
- :class:`PricingEngine` — deterministic offer generation per Section 3.2
  of ``requirements/sa_financial_design.md``.

The pricing formula, hop-distance quantization, speculator-reduction cap,
and settlement math all live inside this file. Callers (the SA-F3 view,
tests, and ``engine/game.py::_check_day_advance``) inject the market,
progression, crew roster, journal, news ticker, and reputation manager
explicitly — the model never reaches up into game state.

Pre-SA-F2 saves load cleanly with an empty ``FuturesState`` because every
field read in :func:`FuturesState.from_dict` uses ``data.get(field,
default)`` per CLAUDE.md migration discipline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from spacegame.constants.flags import (
    futures_first_contract_accepted,
    futures_first_loss,
    futures_first_win,
)

if TYPE_CHECKING:  # pragma: no cover - import-time hints only.
    from spacegame.models.commodity import Commodity
    from spacegame.models.crew import CrewRoster
    from spacegame.models.journal import Journal
    from spacegame.models.market import Market
    from spacegame.models.news_ticker import NewsTicker
    from spacegame.models.player import Player
    from spacegame.models.politics import PoliticsManager
    from spacegame.models.progression import PlayerProgression
    from spacegame.models.system import StarSystem


# ---------------------------------------------------------------------------
# Section 3.2 pricing constants (locked by SA-F1)
# ---------------------------------------------------------------------------

TREND_PREMIUM: dict[str, float] = {"rising": 0.04, "stable": 0.01, "falling": 0.00}
HOP_PENALTY: float = 0.01  # per hop from producer to Nexus Prime
DURATION_SPREAD: dict[int, float] = {7: 0.02, 14: 0.05, 21: 0.09}
BASE_BROKER_SPREAD: float = 0.04

# Section 2.4 / Section 11 Decision 2: 20-unit minimum quantity.
MIN_QUANTITY: int = 20

# Section 11 Decision 8: 7 / 14 / 21 game-day whitelist.
VALID_DURATIONS: frozenset[int] = frozenset({7, 14, 21})

# Section 7.5 / Section 11 Decision 6: skill + crew stack additively,
# capped at 0.25 total (spread_trader 0.10 max + Brix Tano 0.10 + 0.05
# edge-case headroom).
MAX_SPECULATOR_REDUCTION: float = 0.25

# Section 2.3: quantity * strike_price > 10,000 cr flags a headliner
# contract whose settlement fires a news ticker event.
HEADLINER_NOTIONAL_THRESHOLD: int = 10_000

# Section 7.6: settlements with payoff > 5,000 cr trigger a +2 standing
# delta with the Commerce Guild ("noteworthy client" record).
COMMERCE_GUILD_PROFIT_THRESHOLD: int = 5_000
COMMERCE_GUILD_STANDING_DELTA: int = 2
COMMERCE_GUILD_FACTION_ID: str = "stellaris_commerce_guild"

# Hop-distance bucket table (Section 3.4 calibration note in the SA-F2
# planner's Risks section). Bucket widths use a 30-unit stride so they
# align with ``StarSystem.fuel_cost_to``'s /30 normalizer. Empirically
# the current galaxy places every commodity's nearest producer between
# ~83 and ~110 units from Nexus Prime (0, 0), so under this table the
# common_metals / medical / manufactured_goods examples in Section 3.4
# all resolve to hop 3 rather than the illustrative 3 / 2 / 1 the design
# doc used. The Section 3.4 example tests inject synthetic systems at
# chosen coordinates so the formula tests still verify strike/entry-cost
# to the exact integers the design doc names; the *quantize-euclidean-
# min-distance-from-producer* strategy stays locked per the planner's
# risks table.
_HOP_BUCKETS: tuple[tuple[float, int], ...] = (
    (30.0, 1),
    (60.0, 2),
    (90.0, 3),
    (120.0, 4),
)
_HOP_MAX: int = 5


def _bucket_distance(distance: float) -> int:
    """Quantize a Euclidean distance to a 1-5 hop bucket.

    Args:
        distance: Euclidean distance from a producing system to Nexus Prime.

    Returns:
        Hop bucket integer in the closed interval [1, 5].
    """
    for upper, bucket in _HOP_BUCKETS:
        if distance < upper:
            return bucket
    return _HOP_MAX


# ---------------------------------------------------------------------------
# FuturesContract
# ---------------------------------------------------------------------------


@dataclass
class FuturesContract:
    """A single accepted futures position on a commodity price at Nexus Prime.

    Direction ``"LONG"`` profits if the settlement price at maturity rises
    above ``strike_price``; ``"SHORT"`` profits if it falls below. The
    entry cost is paid at acceptance and is never refunded (see Section 2.2).
    """

    contract_id: str
    commodity_id: str
    direction: str  # "LONG" or "SHORT"
    strike_price: int
    quantity: int
    duration_days: int
    entry_cost: int
    accept_day: int
    maturity_day: int
    settled: bool = False
    payoff: Optional[int] = None
    settlement_day: Optional[int] = None
    settlement_price: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a save-friendly dict."""
        return {
            "contract_id": self.contract_id,
            "commodity_id": self.commodity_id,
            "direction": self.direction,
            "strike_price": self.strike_price,
            "quantity": self.quantity,
            "duration_days": self.duration_days,
            "entry_cost": self.entry_cost,
            "accept_day": self.accept_day,
            "maturity_day": self.maturity_day,
            "settled": self.settled,
            "payoff": self.payoff,
            "settlement_day": self.settlement_day,
            "settlement_price": self.settlement_price,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FuturesContract":
        """Deserialize from a save-friendly dict."""
        return cls(
            contract_id=data["contract_id"],
            commodity_id=data["commodity_id"],
            direction=data["direction"],
            strike_price=int(data["strike_price"]),
            quantity=int(data["quantity"]),
            duration_days=int(data["duration_days"]),
            entry_cost=int(data["entry_cost"]),
            accept_day=int(data["accept_day"]),
            maturity_day=int(data["maturity_day"]),
            settled=bool(data.get("settled", False)),
            payoff=data.get("payoff"),
            settlement_day=data.get("settlement_day"),
            settlement_price=data.get("settlement_price"),
        )


# ---------------------------------------------------------------------------
# PricingEngine
# ---------------------------------------------------------------------------


class PricingEngine:
    """Deterministic offer generation per Section 3.2.

    The engine reads ``Market.get_price`` and ``PriceHistory.get_trend`` on
    the offer day, quantizes the hop distance from the commodity's nearest
    producing system to Nexus Prime, and derives the strike + entry cost
    from the locked constants above. Callers pass ``progression`` and
    ``crew_roster`` explicitly so the model never imports view/engine
    modules.
    """

    def hop_distance(
        self,
        commodity: "Commodity",
        all_systems: list["StarSystem"],
        nexus_prime: "StarSystem",
    ) -> int:
        """Quantized hop count from nearest producing system to Nexus Prime.

        Args:
            commodity: The commodity being priced.
            all_systems: All galaxy systems (Nexus Prime may be included).
            nexus_prime: The Nexus Prime system reference.

        Returns:
            Hop bucket integer 1..5. Defaults to 5 if no producing system
            exists.
        """
        producer_tags = set(commodity.production_tags)
        if not producer_tags:
            return _HOP_MAX
        min_distance: Optional[float] = None
        for system in all_systems:
            if system.id == nexus_prime.id:
                continue
            sys_tags = set(system.economy.production_tags)
            if not (producer_tags & sys_tags):
                continue
            distance = system.distance_to(nexus_prime)
            if min_distance is None or distance < min_distance:
                min_distance = distance
        if min_distance is None:
            return _HOP_MAX
        return _bucket_distance(min_distance)

    @staticmethod
    def speculator_reduction(
        progression: Optional["PlayerProgression"],
        crew_roster: Optional["CrewRoster"],
    ) -> float:
        """Combined skill + crew speculator premium reduction, capped at 0.25.

        Args:
            progression: Player progression (or None to skip skill contribution).
            crew_roster: Crew roster (or None to skip crew contribution).

        Returns:
            Effective reduction rate in the closed interval [0.0, 0.25].
        """
        total = 0.0
        if progression is not None:
            total += progression.get_bonus("speculator_premium_reduction")
        if crew_roster is not None:
            total += crew_roster.get_bonus("speculator_premium_reduction")
        return min(MAX_SPECULATOR_REDUCTION, max(0.0, total))

    def generate_offer(
        self,
        commodity: "Commodity",
        direction: str,
        duration_days: int,
        quantity: int,
        current_day: int,
        market: "Market",
        progression: Optional["PlayerProgression"],
        crew_roster: Optional["CrewRoster"],
        all_systems: list["StarSystem"],
        nexus_prime: "StarSystem",
        sequence: int,
        *,
        price_history: Any = None,
        hop_distance_override: Optional[int] = None,
    ) -> "tuple[bool, str] | FuturesContract":
        """Build a Meridian futures offer for the given commodity + direction.

        Returns a :class:`FuturesContract` on success or a
        ``(False, reason)`` tuple on validation failure (invalid direction,
        duration outside the whitelist, or quantity below the minimum).

        Args:
            commodity: The commodity to price.
            direction: ``"LONG"`` or ``"SHORT"``.
            duration_days: Player-selected duration in game-days (7 / 14 / 21).
            quantity: Player-selected unit count (>= 20).
            current_day: Offer day (also the accept day).
            market: The Nexus Prime market to read the current price from.
            progression: Player progression for skill bonuses (or None).
            crew_roster: Crew roster for Brix Tano's bonus (or None).
            all_systems: All galaxy systems (used for hop-distance).
            nexus_prime: Nexus Prime system reference.
            sequence: Monotonic contract ID counter (usually
                ``FuturesState._contract_seq``).
            price_history: Optional ``PriceHistory`` to read a trend from;
                if None, trend defaults to ``"stable"`` (which yields the
                cheapest premium and matches Section 3.1's read).
            hop_distance_override: Test/debug hook that skips the
                galaxy-derived hop distance in favour of a caller-supplied
                integer. Production callers leave this as None.

        Returns:
            Either a :class:`FuturesContract` (success) or a
            ``(False, reason)`` tuple (validation failure).
        """
        if direction not in ("LONG", "SHORT"):
            return (False, f"invalid direction '{direction}'; use LONG or SHORT")
        if duration_days not in VALID_DURATIONS:
            return (
                False,
                f"duration must be one of {sorted(VALID_DURATIONS)} game-days",
            )
        if quantity < MIN_QUANTITY:
            return (False, f"minimum {MIN_QUANTITY} units per contract")

        current_price = market.get_price(commodity.id)
        if current_price <= 0:
            return (
                False,
                f"no live market price for {commodity.id} at Nexus Prime",
            )

        if price_history is not None:
            trend = price_history.get_trend(nexus_prime.id, commodity.id)
        else:
            trend = "stable"
        trend_premium = TREND_PREMIUM.get(trend, TREND_PREMIUM["stable"])

        if hop_distance_override is not None:
            hops = hop_distance_override
        else:
            hops = self.hop_distance(commodity, all_systems, nexus_prime)
        hop_contribution = hops * HOP_PENALTY

        duration_spread = DURATION_SPREAD[duration_days]
        forward_spread = trend_premium + hop_contribution + duration_spread
        strike_price = int(current_price * (1 + forward_spread))

        reduction = self.speculator_reduction(progression, crew_roster)
        broker_spread_rate = BASE_BROKER_SPREAD * (1 - reduction)
        entry_cost = int(strike_price * quantity * broker_spread_rate)

        contract_id = f"futures_{current_day}_{commodity.id}_{sequence:03d}"
        return FuturesContract(
            contract_id=contract_id,
            commodity_id=commodity.id,
            direction=direction,
            strike_price=strike_price,
            quantity=quantity,
            duration_days=duration_days,
            entry_cost=entry_cost,
            accept_day=current_day,
            maturity_day=current_day + duration_days,
        )


# ---------------------------------------------------------------------------
# FuturesState
# ---------------------------------------------------------------------------


@dataclass
class FuturesState:
    """Player-side registry of active and settled futures contracts.

    Serializes to a plain dict via :func:`to_dict`. ``_contract_seq`` is
    persisted so contract IDs remain unique across save/load cycles.
    """

    active_contracts: list[FuturesContract] = field(default_factory=list)
    settled_contracts: list[FuturesContract] = field(default_factory=list)
    total_credits_won: int = 0
    total_credits_lost: int = 0
    _contract_seq: int = 0

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a save-friendly dict."""
        return {
            "active_contracts": [c.to_dict() for c in self.active_contracts],
            "settled_contracts": [c.to_dict() for c in self.settled_contracts],
            "total_credits_won": self.total_credits_won,
            "total_credits_lost": self.total_credits_lost,
            "contract_seq": self._contract_seq,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "FuturesState":
        """Deserialize; tolerates missing keys per the CLAUDE.md pattern."""
        if not isinstance(data, dict):
            return cls()
        state = cls()
        active_raw = data.get("active_contracts", [])
        if isinstance(active_raw, list):
            state.active_contracts = [
                FuturesContract.from_dict(c) for c in active_raw if isinstance(c, dict)
            ]
        settled_raw = data.get("settled_contracts", [])
        if isinstance(settled_raw, list):
            state.settled_contracts = [
                FuturesContract.from_dict(c) for c in settled_raw if isinstance(c, dict)
            ]
        state.total_credits_won = int(data.get("total_credits_won", 0))
        state.total_credits_lost = int(data.get("total_credits_lost", 0))
        state._contract_seq = int(data.get("contract_seq", 0))
        return state

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def next_sequence(self) -> int:
        """Return and advance the monotonic contract-ID counter.

        Callers that build a ``FuturesContract`` via :class:`PricingEngine`
        should use this to keep IDs unique per save. The counter is
        persisted, so save/load never issues a duplicate ID even after a
        reload.
        """
        self._contract_seq += 1
        return self._contract_seq

    def accept(
        self,
        contract: FuturesContract,
        player: "Player",
        *,
        journal: Optional["Journal"] = None,
    ) -> tuple[bool, str]:
        """Pay entry cost and move the contract into ``active_contracts``.

        Fires the ``futures_first_contract_accepted`` flag on the first
        accept per save (idempotent thereafter). If ``journal`` is
        supplied, adds a ``futures_position_open`` auto-entry keyed by
        contract ID.

        Args:
            contract: The offered contract to accept.
            player: The player state to debit and flag.
            journal: Optional journal for the "Position Open" entry.

        Returns:
            ``(True, message)`` on success, or ``(False, reason)`` if the
            player cannot afford the entry cost. On failure no state
            mutates.
        """
        if player.credits < contract.entry_cost:
            return (
                False,
                f"Insufficient credits: {contract.entry_cost} CR entry cost, "
                f"{player.credits} available.",
            )

        player.deduct_credits(contract.entry_cost)
        self.active_contracts.append(contract)

        flag_name = futures_first_contract_accepted()
        if not player.dialogue_flags.get(flag_name):
            player.dialogue_flags[flag_name] = True

        if journal is not None:
            body = _position_open_entry_text(contract)
            journal.add_auto_entry(
                entry_id=f"futures_position_open_{contract.contract_id}",
                text=body,
                game_day=contract.accept_day,
                system_id="nexus_prime",
                tag="goals",
            )

        return (
            True,
            f"Accepted {contract.direction} on {contract.commodity_id} "
            f"({contract.quantity} u @ {contract.strike_price} cr, "
            f"matures day {contract.maturity_day}).",
        )

    def advance_day(
        self,
        current_day: int,
        nexus_market: "Market",
        player: "Player",
        *,
        journal: Optional["Journal"] = None,
        news_ticker: Optional["NewsTicker"] = None,
        reputation_manager: Optional["PoliticsManager"] = None,
    ) -> list[str]:
        """Settle every matured contract; return a notification list.

        A contract matures when ``maturity_day <= current_day``. Settlement
        reads ``nexus_market.get_price(commodity_id)``; a zero price
        defers the contract one game-day and emits a deferral notification
        instead of settling it (Section 6.2 mirrors the regulatory_capture
        embargo path — SA-F6 wires that event, SA-F2 handles the fallout
        today).

        Args:
            current_day: The advancing game day.
            nexus_market: A Market seeded for Nexus Prime on ``current_day``.
            player: Player to credit / debit and flag.
            journal: Optional journal for settlement auto-entries.
            news_ticker: Optional news ticker for headliner events (fires
                when ``quantity * strike_price > 10,000 cr``).
            reputation_manager: Optional politics manager for the Commerce
                Guild standing delta on payoffs > 5,000 cr.

        Returns:
            A list of one-line notifications suitable for the mission-
            notification queue.
        """
        notifications: list[str] = []
        still_active: list[FuturesContract] = []

        for contract in self.active_contracts:
            if contract.maturity_day > current_day:
                still_active.append(contract)
                continue

            settlement_price = nexus_market.get_price(contract.commodity_id)
            if settlement_price <= 0:
                still_active.append(contract)
                display_name = _commodity_display(nexus_market, contract.commodity_id)
                notifications.append(
                    f"Futures: {display_name} settlement deferred — market disruption."
                )
                continue

            if contract.direction == "LONG":
                payoff = (settlement_price - contract.strike_price) * contract.quantity
            else:  # SHORT
                payoff = (contract.strike_price - settlement_price) * contract.quantity

            contract.settled = True
            contract.payoff = payoff
            contract.settlement_day = current_day
            contract.settlement_price = settlement_price
            self.settled_contracts.append(contract)

            if payoff >= 0:
                player.add_credits(payoff)
                self.total_credits_won += payoff
            else:
                # Obligation semantics: allow credits below zero per
                # SA-F1 §2.2 ("A negative settlement_payoff debits the
                # player").
                player.credits += payoff
                self.total_credits_lost += -payoff

            self._fire_settlement_side_effects(
                contract=contract,
                player=player,
                journal=journal,
                news_ticker=news_ticker,
                reputation_manager=reputation_manager,
            )

            display_name = _commodity_display(nexus_market, contract.commodity_id)
            if payoff >= 0:
                notifications.append(
                    f"Futures: {display_name} settled at {settlement_price} cr — +{payoff:,} cr."
                )
            else:
                notifications.append(
                    f"Futures: {display_name} settled at {settlement_price} cr — {payoff:,} cr."
                )

        self.active_contracts = still_active
        return notifications

    # ------------------------------------------------------------------
    # Side effects
    # ------------------------------------------------------------------

    def _fire_settlement_side_effects(
        self,
        *,
        contract: FuturesContract,
        player: "Player",
        journal: Optional["Journal"],
        news_ticker: Optional["NewsTicker"],
        reputation_manager: Optional["PoliticsManager"],
    ) -> None:
        """Fire journal, news, flag, and reputation side effects on settle."""
        payoff = contract.payoff or 0

        # Flags (idempotent one-shot per save).
        if payoff >= 0:
            flag_name = futures_first_win()
            if not player.dialogue_flags.get(flag_name):
                player.dialogue_flags[flag_name] = True
        else:
            flag_name = futures_first_loss()
            if not player.dialogue_flags.get(flag_name):
                player.dialogue_flags[flag_name] = True

        # Journal (per-contract auto-entry).
        if journal is not None:
            if payoff >= 0:
                body = _closed_profit_entry_text(contract)
                entry_id = f"futures_closed_profit_{contract.contract_id}"
            else:
                body = _closed_loss_entry_text(contract)
                entry_id = f"futures_closed_loss_{contract.contract_id}"
            journal.add_auto_entry(
                entry_id=entry_id,
                text=body,
                game_day=contract.settlement_day or 0,
                system_id="nexus_prime",
                tag="goals",
            )

        # Headliner news (queued for the news ticker to consume next tick).
        if news_ticker is not None:
            notional = contract.quantity * contract.strike_price
            if notional > HEADLINER_NOTIONAL_THRESHOLD:
                queue = getattr(news_ticker, "pending_events", None)
                if queue is None:
                    queue = []
                    news_ticker.pending_events = queue  # type: ignore[attr-defined]
                queue.append(
                    {
                        "trigger": "futures_headliner_settled",
                        "commodity_id": contract.commodity_id,
                        "payoff": payoff,
                        "direction": contract.direction,
                    }
                )

        # Commerce Guild standing delta on profits above the Section 7.6
        # threshold.
        if reputation_manager is not None and payoff > COMMERCE_GUILD_PROFIT_THRESHOLD:
            reputation_manager.apply_reputation_with_spillover(
                player,
                COMMERCE_GUILD_FACTION_ID,
                COMMERCE_GUILD_STANDING_DELTA,
            )


# ---------------------------------------------------------------------------
# Journal templates (Section 9.2)
# ---------------------------------------------------------------------------


def _commodity_display(market: "Market", commodity_id: str) -> str:
    """Best-effort human name; fall back to the id if the commodity is unknown."""
    commodity = market._all_commodities.get(commodity_id)
    if commodity is not None:
        return commodity.name
    return commodity_id.replace("_", " ").title()


def _position_open_entry_text(contract: FuturesContract) -> str:
    """Section 9.2 "Position Open" body with per-contract substitution."""
    return (
        f"Position Open. Opened a {contract.direction} position on "
        f"{contract.commodity_id.replace('_', ' ')} at {contract.strike_price} cr. "
        f"Maturity in {contract.duration_days} days. Spread cost "
        f"{contract.entry_cost} cr. We will see if it holds."
    )


def _closed_profit_entry_text(contract: FuturesContract) -> str:
    """Section 9.2 "Closed" (profit) body with per-contract substitution."""
    payoff = contract.payoff or 0
    net = payoff - contract.entry_cost
    return (
        f"Closed. Settled the "
        f"{contract.commodity_id.replace('_', ' ')} position at "
        f"{contract.settlement_price} cr. Payoff: {payoff:,} cr. "
        f"Net after spread: {net:,} cr."
    )


def _closed_loss_entry_text(contract: FuturesContract) -> str:
    """Section 9.2 "Closed at a Loss" body with per-contract substitution."""
    payoff = contract.payoff or 0
    net = payoff - contract.entry_cost
    return (
        f"Closed at a Loss. Settled the "
        f"{contract.commodity_id.replace('_', ' ')} position at "
        f"{contract.settlement_price} cr. Down {net:,} cr all in. "
        f"The spread does not care which way it went."
    )
