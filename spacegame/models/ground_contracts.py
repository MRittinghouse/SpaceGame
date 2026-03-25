"""Ground mission contracts — repeatable procedural ground missions.

Contracts are time-limited ground missions posted at stations. Each
system offers 1-3 contracts deterministically seeded by system ID
and game day. Difficulty scales with player level.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass
from typing import Any

from spacegame.models.ground_mapgen import DifficultyTier, MissionType
from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionRewards,
)

# ===========================================================================
# Reward scaling by difficulty
# ===========================================================================

_REWARD_RANGES: dict[DifficultyTier, dict[str, tuple[int, int]]] = {
    DifficultyTier.LOW: {"credits": (200, 400), "xp": (10, 20), "bonus": (50, 150)},
    DifficultyTier.MODERATE: {"credits": (350, 700), "xp": (20, 35), "bonus": (100, 300)},
    DifficultyTier.HIGH: {"credits": (600, 1200), "xp": (30, 50), "bonus": (200, 500)},
    DifficultyTier.EXTREME: {"credits": (1000, 2000), "xp": (45, 75), "bonus": (400, 800)},
}

# Difficulty tiers available at each player level range
_LEVEL_TIERS: list[tuple[int, list[DifficultyTier]]] = [
    (1, [DifficultyTier.LOW]),
    (3, [DifficultyTier.LOW, DifficultyTier.MODERATE]),
    (5, [DifficultyTier.LOW, DifficultyTier.MODERATE, DifficultyTier.HIGH]),
    (7, [DifficultyTier.MODERATE, DifficultyTier.HIGH, DifficultyTier.EXTREME]),
]

_ALL_MISSION_TYPES = list(MissionType)


def _tiers_for_level(level: int) -> list[DifficultyTier]:
    """Get available difficulty tiers for a player level."""
    result = [DifficultyTier.LOW]
    for min_level, tiers in _LEVEL_TIERS:
        if level >= min_level:
            result = tiers
    return result


# ===========================================================================
# GroundContract
# ===========================================================================


@dataclass
class GroundContract:
    """A time-limited ground mission contract.

    Contracts are posted at stations and expire after a set number
    of game days. Completing a contract within the time limit awards
    bonus credits on top of the mission reward.
    """

    id: str
    config: GroundMissionConfig
    system_id: str
    target_system_id: str
    expiry_day: int
    bonus_credits: int
    completed: bool = False

    def is_expired(self, current_day: int) -> bool:
        """Check if this contract has expired.

        Args:
            current_day: Current game day.

        Returns:
            True if the current day is past the expiry day.
        """
        return current_day > self.expiry_day

    def days_remaining(self, current_day: int) -> int:
        """Days remaining before expiry.

        Args:
            current_day: Current game day.

        Returns:
            Days remaining (0 if expired).
        """
        return max(0, self.expiry_day - current_day)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "config": self.config.to_dict(),
            "system_id": self.system_id,
            "target_system_id": self.target_system_id,
            "expiry_day": self.expiry_day,
            "bonus_credits": self.bonus_credits,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundContract:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with contract fields.

        Returns:
            GroundContract instance.
        """
        return cls(
            id=data["id"],
            config=GroundMissionConfig.from_dict(data["config"]),
            system_id=data["system_id"],
            target_system_id=data.get("target_system_id", data["system_id"]),
            expiry_day=data["expiry_day"],
            bonus_credits=data["bonus_credits"],
            completed=data.get("completed", False),
        )


# ===========================================================================
# GroundContractManager
# ===========================================================================


class GroundContractManager:
    """Generates and manages repeatable ground mission contracts.

    Contracts are deterministically generated per system and game day.
    The manager tracks active contracts, handles completion, and
    prunes expired entries.
    """

    def __init__(self) -> None:
        self.active_contracts: list[GroundContract] = []
        self.completed_count: int = 0

    def generate_contracts(
        self,
        system_id: str,
        faction_id: str,
        game_day: int,
        player_level: int,
    ) -> list[GroundContract]:
        """Generate 1-3 contracts for a system visit.

        Uses deterministic seeding from system_id + game_day so the
        same visit always produces the same contracts.

        Args:
            system_id: System where contracts are posted.
            faction_id: Faction controlling the system.
            game_day: Current game day.
            player_level: Player's current level for difficulty scaling.

        Returns:
            List of newly generated contracts.
        """
        seed_str = f"{system_id}_{game_day}_ground_contracts"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = _rng.Random(seed)

        # Load templates for briefing text
        templates = self._load_templates()
        available_tiers = _tiers_for_level(player_level)

        num_contracts = rng.randint(1, 3)
        new_contracts: list[GroundContract] = []

        for i in range(num_contracts):
            mission_type = rng.choice(_ALL_MISSION_TYPES)
            difficulty = rng.choice(available_tiers)
            duration = rng.randint(5, 14)

            # Build rewards scaled to difficulty
            ranges = _REWARD_RANGES[difficulty]
            credits = rng.randint(*ranges["credits"])
            xp = rng.randint(*ranges["xp"])
            bonus = rng.randint(*ranges["bonus"])
            crew_xp = max(5, xp // 3)

            # Build briefing text from templates
            name, description, objectives = self._build_briefing(
                mission_type, faction_id, system_id, templates, rng
            )

            # Create the mission config
            contract_id = f"gc_{system_id}_{game_day}_{i}"
            mission_seed = rng.randint(0, 2**31)
            config = GroundMissionConfig(
                id=contract_id,
                name=name,
                description=description,
                mission_type=mission_type,
                difficulty=difficulty,
                faction_id=faction_id,
                objectives=objectives,
                intel_hints=[],
                rewards=GroundMissionRewards(
                    credits=credits,
                    xp=xp,
                    crew_xp=crew_xp,
                ),
                seed=mission_seed,
            )

            contract = GroundContract(
                id=contract_id,
                config=config,
                system_id=system_id,
                target_system_id=system_id,
                expiry_day=game_day + duration,
                bonus_credits=bonus,
            )
            new_contracts.append(contract)
            self.active_contracts.append(contract)

        return new_contracts

    def get_available(self, system_id: str, game_day: int) -> list[GroundContract]:
        """Get non-expired, non-completed contracts for a system.

        Args:
            system_id: System to filter by.
            game_day: Current game day.

        Returns:
            List of available contracts.
        """
        return [
            c
            for c in self.active_contracts
            if c.system_id == system_id and not c.completed and not c.is_expired(game_day)
        ]

    def complete_contract(self, contract_id: str) -> tuple[bool, str]:
        """Mark a contract as completed.

        Args:
            contract_id: ID of the contract to complete.

        Returns:
            Tuple of (success, message).
        """
        for c in self.active_contracts:
            if c.id == contract_id:
                if c.completed:
                    return False, "Contract already completed."
                c.completed = True
                self.completed_count += 1
                return True, f"Contract complete! Bonus: {c.bonus_credits} CR"
        return False, "Contract not found."

    def advance_day(self, game_day: int) -> None:
        """Remove expired and completed contracts.

        Args:
            game_day: Current game day.
        """
        self.active_contracts = [
            c for c in self.active_contracts if not c.completed and not c.is_expired(game_day)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Serialize all state."""
        return {
            "contracts": [c.to_dict() for c in self.active_contracts],
            "completed_count": self.completed_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundContractManager:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with contracts list and completed count.

        Returns:
            GroundContractManager instance.
        """
        mgr = cls()
        mgr.active_contracts = [GroundContract.from_dict(c) for c in data.get("contracts", [])]
        mgr.completed_count = data.get("completed_count", 0)
        return mgr

    # === Private helpers ===

    def _load_templates(self) -> dict[str, dict]:
        """Load contract templates from DataLoader."""
        try:
            from spacegame.data_loader import get_data_loader

            dl = get_data_loader()
            return dl.contract_templates
        except (ImportError, AttributeError):
            return {}

    def _build_briefing(
        self,
        mission_type: MissionType,
        faction_id: str,
        system_id: str,
        templates: dict[str, dict],
        rng: _rng.Random,
    ) -> tuple[str, str, list[str]]:
        """Build briefing name, description, and objectives from templates.

        Args:
            mission_type: Type of ground mission.
            faction_id: Faction ID for text substitution.
            system_id: System ID for text substitution.
            templates: Loaded contract templates.
            rng: Seeded random for deterministic selection.

        Returns:
            Tuple of (name, description, objectives).
        """
        type_key = mission_type.value
        template = templates.get(type_key, {})

        # Faction display name (fallback to ID with title case)
        faction_display = faction_id.replace("_", " ").title()
        system_display = system_id.replace("_", " ").title()

        # Name
        names = template.get("names", [])
        if names:
            name = rng.choice(names)
        else:
            name = f"{type_key.title()} Contract"

        # Description
        descriptions = template.get("descriptions", [])
        if descriptions:
            desc_template = rng.choice(descriptions)
            description = desc_template.format(faction=faction_display, system=system_display)
        else:
            description = f"A {type_key} mission at {system_display}."

        # Objectives
        obj_templates = template.get("objectives", [])
        if obj_templates:
            objectives = [rng.choice(obj_templates)]
        else:
            objectives = [mission_type.description]

        return name, description, objectives
