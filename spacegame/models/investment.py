"""Investment system — passive income from per-system investments.

Players can invest credits in system-specific operations that generate
daily returns (credits or commodities). Three tiers per system with
increasing costs and returns.
"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class InvestmentTier:
    """A single investment tier with cost and return info."""

    tier: int
    cost: int
    daily_return_amount: int
    returns_type: str  # "credits" or "commodity"
    returns_commodity: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "cost": self.cost,
            "daily_return_amount": self.daily_return_amount,
            "returns_type": self.returns_type,
            "returns_commodity": self.returns_commodity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvestmentTier":
        return cls(
            tier=data["tier"],
            cost=data["cost"],
            daily_return_amount=data["daily_return_amount"],
            returns_type=data["returns_type"],
            returns_commodity=data.get("returns_commodity"),
        )


@dataclass
class InvestmentTemplate:
    """Template defining what investment is available at a system."""

    system_id: str
    investment_type: str
    name: str
    description: str
    tiers: list[InvestmentTier]

    def get_tier(self, tier_num: int) -> Optional[InvestmentTier]:
        """Get tier info by tier number."""
        for t in self.tiers:
            if t.tier == tier_num:
                return t
        return None

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "investment_type": self.investment_type,
            "name": self.name,
            "description": self.description,
            "tiers": [t.to_dict() for t in self.tiers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvestmentTemplate":
        return cls(
            system_id=data["system_id"],
            investment_type=data["investment_type"],
            name=data["name"],
            description=data["description"],
            tiers=[InvestmentTier.from_dict(t) for t in data["tiers"]],
        )


@dataclass
class Investment:
    """Active investment at a system."""

    system_id: str
    tier: int
    accumulated_returns: int = 0
    last_processed_day: int = 0
    halted_until_day: int = 0

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "tier": self.tier,
            "accumulated_returns": self.accumulated_returns,
            "last_processed_day": self.last_processed_day,
            "halted_until_day": self.halted_until_day,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Investment":
        return cls(
            system_id=data["system_id"],
            tier=data["tier"],
            accumulated_returns=data.get("accumulated_returns", 0),
            last_processed_day=data.get("last_processed_day", 0),
            halted_until_day=data.get("halted_until_day", 0),
        )


class InvestmentManager:
    """Manages investment templates and active player investments."""

    def __init__(
        self,
        templates: dict[str, InvestmentTemplate],
        active: Optional[dict[str, Investment]] = None,
    ) -> None:
        self.templates = templates
        self.active: dict[str, Investment] = active if active is not None else {}

    def get_template(self, system_id: str) -> Optional[InvestmentTemplate]:
        """Get investment template for a system."""
        return self.templates.get(system_id)

    def get_investment(self, system_id: str) -> Optional[Investment]:
        """Get active investment at a system."""
        return self.active.get(system_id)

    def invest(
        self,
        available_credits: int,
        system_id: str,
        current_day: int,
    ) -> tuple[bool, str]:
        """Create a new tier-1 investment at a system.

        Args:
            available_credits: Player's current credits.
            system_id: System to invest in.
            current_day: Current game day.

        Returns:
            Tuple of (success, message).
        """
        template = self.templates.get(system_id)
        if not template:
            return (False, "No investment available at this system.")

        if system_id in self.active:
            return (False, "You already have an investment here.")

        tier_info = template.get_tier(1)
        if not tier_info:
            return (False, "Investment tier data missing.")

        if available_credits < tier_info.cost:
            return (
                False,
                f"Insufficient credits. Need {tier_info.cost:,} CR, have {available_credits:,} CR.",
            )

        self.active[system_id] = Investment(
            system_id=system_id,
            tier=1,
            last_processed_day=current_day,
        )
        return (True, f"Invested {tier_info.cost:,} CR in {template.name}.")

    def upgrade(
        self,
        available_credits: int,
        system_id: str,
    ) -> tuple[bool, str]:
        """Upgrade an existing investment to the next tier.

        Args:
            available_credits: Player's current credits.
            system_id: System to upgrade investment at.

        Returns:
            Tuple of (success, message).
        """
        inv = self.active.get(system_id)
        if not inv:
            return (False, "No investment at this system.")

        template = self.templates.get(system_id)
        if not template:
            return (False, "Investment template missing.")

        next_tier = inv.tier + 1
        tier_info = template.get_tier(next_tier)
        if not tier_info:
            return (False, "Investment is already at maximum tier.")

        if available_credits < tier_info.cost:
            return (
                False,
                f"Insufficient credits. Need {tier_info.cost:,} CR, have {available_credits:,} CR.",
            )

        inv.tier = next_tier
        return (True, f"Upgraded {template.name} to tier {next_tier}. Cost: {tier_info.cost:,} CR.")

    def advance_day(
        self,
        current_day: int,
        active_events: dict,
        danger_levels: dict[str, str],
    ) -> list[str]:
        """Process daily returns for all active investments.

        Args:
            current_day: Current game day.
            active_events: Dict of system_id -> market event (with event_type).
            danger_levels: Dict of system_id -> danger level string.

        Returns:
            List of notification messages.
        """
        messages: list[str] = []
        for system_id, inv in self.active.items():
            if inv.last_processed_day >= current_day:
                continue

            template = self.templates.get(system_id)
            if not template:
                continue

            tier_info = template.get_tier(inv.tier)
            if not tier_info:
                continue

            days_elapsed = current_day - inv.last_processed_day

            # Check for disaster halt
            event = active_events.get(system_id)
            if event and getattr(event, "event_type", "") == "disaster":
                inv.halted_until_day = current_day + 1
                inv.last_processed_day = current_day
                messages.append(f"{template.name} at {system_id}: returns halted by disaster.")
                continue

            # Skip if still halted from previous disaster
            if inv.halted_until_day > current_day:
                inv.last_processed_day = current_day
                continue

            # Accumulate returns
            total_return = 0
            for _ in range(days_elapsed):
                day_return = tier_info.daily_return_amount
                # Dangerous systems: 10% chance of pirate interference
                danger = danger_levels.get(system_id, "safe")
                if danger == "dangerous" and random.random() < 0.10:
                    day_return = day_return // 2
                total_return += day_return

            inv.accumulated_returns += total_return
            inv.last_processed_day = current_day

        return messages

    def collect_returns(
        self,
        system_id: str,
    ) -> tuple[bool, str, int, Optional[str], Optional[int]]:
        """Collect accumulated returns from an investment.

        Args:
            system_id: System to collect from.

        Returns:
            Tuple of (success, message, credits, commodity_id, commodity_qty).
            For credit returns: credits > 0, commodity is None.
            For commodity returns: credits = 0, commodity and qty set.
        """
        inv = self.active.get(system_id)
        if not inv:
            return (False, "No investment at this system.", 0, None, None)

        if inv.accumulated_returns <= 0:
            return (False, "No returns to collect.", 0, None, None)

        template = self.templates.get(system_id)
        if not template:
            return (False, "Investment template missing.", 0, None, None)

        tier_info = template.get_tier(inv.tier)
        if not tier_info:
            return (False, "Tier data missing.", 0, None, None)

        amount = inv.accumulated_returns
        inv.accumulated_returns = 0

        if tier_info.returns_type == "commodity" and tier_info.returns_commodity:
            return (
                True,
                f"Collected {amount} {tier_info.returns_commodity.replace('_', ' ')} from {template.name}.",
                0,
                tier_info.returns_commodity,
                amount,
            )
        else:
            return (
                True,
                f"Collected {amount:,} CR from {template.name}.",
                amount,
                None,
                None,
            )

    def to_dict(self) -> dict:
        """Serialize active investments."""
        return {
            "active": {sid: inv.to_dict() for sid, inv in self.active.items()},
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        templates: dict[str, InvestmentTemplate],
    ) -> "InvestmentManager":
        """Deserialize investment manager state."""
        active = {}
        for sid, inv_data in data.get("active", {}).items():
            active[sid] = Investment.from_dict(inv_data)
        return cls(templates=templates, active=active)
