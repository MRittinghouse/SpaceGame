"""Trade contracts for bonus rewards on specific commodity trades.

Contracts are generated per system and offer bonus credits for
fulfilling buy/sell orders within a time limit.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass, field


@dataclass
class TradeContract:
    """A time-limited trade contract offering bonus credits.

    Contracts specify a commodity, quantity, fixed price, and bonus.
    Must be fulfilled at the designated system before expiry.
    """

    id: str
    contract_type: str  # "buy" or "sell"
    commodity_id: str
    quantity: int
    price_per_unit: int
    bonus_credits: int
    system_id: str
    day_offered: int
    expiry_day: int
    completed: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "contract_type": self.contract_type,
            "commodity_id": self.commodity_id,
            "quantity": self.quantity,
            "price_per_unit": self.price_per_unit,
            "bonus_credits": self.bonus_credits,
            "system_id": self.system_id,
            "day_offered": self.day_offered,
            "expiry_day": self.expiry_day,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeContract":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with contract fields.

        Returns:
            TradeContract instance.
        """
        return cls(
            id=data["id"],
            contract_type=data["contract_type"],
            commodity_id=data["commodity_id"],
            quantity=data["quantity"],
            price_per_unit=data["price_per_unit"],
            bonus_credits=data["bonus_credits"],
            system_id=data["system_id"],
            day_offered=data["day_offered"],
            expiry_day=data["expiry_day"],
            completed=data.get("completed", False),
        )


class TradeContractManager:
    """Manages generation, fulfillment, and expiry of trade contracts."""

    def __init__(self) -> None:
        self._contracts: list[TradeContract] = []

    def generate_contracts(
        self,
        system_id: str,
        commodity_ids: list[str],
        game_day: int,
    ) -> list[TradeContract]:
        """Generate 1-3 contracts for a system visit.

        Uses a deterministic seed from system_id + game_day.

        Args:
            system_id: System to generate contracts for.
            commodity_ids: Available commodity IDs.
            game_day: Current game day.

        Returns:
            List of newly generated contracts.
        """
        if not commodity_ids:
            return []

        seed_str = f"{system_id}_{game_day}_contracts"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = _rng.Random(seed)

        num_contracts = rng.randint(1, 3)
        new_contracts: list[TradeContract] = []

        for i in range(num_contracts):
            contract_type = rng.choice(["buy", "sell"])
            commodity_id = rng.choice(commodity_ids)
            quantity = rng.randint(3, 15)

            # Base price range (will be overridden by market in real usage)
            base_price = rng.randint(50, 300)
            if contract_type == "sell":
                # Sell contracts: offer 10-25% above market
                bonus_pct = rng.uniform(0.10, 0.25)
                price_per_unit = int(base_price * (1 + bonus_pct))
            else:
                # Buy contracts: offer 10-20% discount
                discount_pct = rng.uniform(0.10, 0.20)
                price_per_unit = int(base_price * (1 - discount_pct))

            bonus_credits = rng.randint(50, 300)
            duration = rng.randint(5, 10)

            contract_id = f"{system_id}_{game_day}_{i}"
            contract = TradeContract(
                id=contract_id,
                contract_type=contract_type,
                commodity_id=commodity_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
                bonus_credits=bonus_credits,
                system_id=system_id,
                day_offered=game_day,
                expiry_day=game_day + duration,
            )
            new_contracts.append(contract)
            self._contracts.append(contract)

        return new_contracts

    def get_available(
        self, system_id: str, game_day: int
    ) -> list[TradeContract]:
        """Get unfulfilled, non-expired contracts for a system.

        Args:
            system_id: System to filter by.
            game_day: Current day for expiry check.

        Returns:
            List of available contracts.
        """
        return [
            c
            for c in self._contracts
            if c.system_id == system_id
            and not c.completed
            and game_day <= c.expiry_day
        ]

    def try_fulfill(
        self,
        contract_id: str,
        current_system: str,
        commodity_id: str,
        available_qty: int,
    ) -> tuple[bool, str]:
        """Attempt to fulfill a contract.

        Args:
            contract_id: ID of the contract to fulfill.
            current_system: Player's current system.
            commodity_id: Commodity being traded.
            available_qty: Quantity available for the trade.

        Returns:
            Tuple of (success, message).
        """
        contract = None
        for c in self._contracts:
            if c.id == contract_id:
                contract = c
                break

        if contract is None:
            return False, "Contract not found."

        if contract.completed:
            return False, "Contract already completed."

        if contract.system_id != current_system:
            return False, "Must be at the contract's system to fulfill."

        if available_qty < contract.quantity:
            return (
                False,
                f"Need {contract.quantity} units, only have {available_qty}.",
            )

        contract.completed = True
        return (
            True,
            f"Contract fulfilled! Bonus: {contract.bonus_credits} CR",
        )

    def expire_old(self, game_day: int) -> None:
        """Remove expired and completed contracts.

        Args:
            game_day: Current game day.
        """
        self._contracts = [
            c
            for c in self._contracts
            if not c.completed and game_day <= c.expiry_day
        ]

    def to_dict(self) -> dict:
        """Serialize all contracts."""
        return {"contracts": [c.to_dict() for c in self._contracts]}

    @classmethod
    def from_dict(cls, data: dict) -> "TradeContractManager":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with contracts list.

        Returns:
            TradeContractManager instance.
        """
        mgr = cls()
        mgr._contracts = [
            TradeContract.from_dict(c) for c in data.get("contracts", [])
        ]
        return mgr
