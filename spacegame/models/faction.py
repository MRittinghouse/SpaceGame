"""
Faction reputation system models.

Defines factions, reputation tiers, tariff modifiers, and random faction assignment.
"""

import random
from dataclasses import dataclass
from enum import Enum


class ReputationTier(Enum):
    """Player reputation standing with a faction."""

    HOSTILE = "Hostile"
    UNFRIENDLY = "Unfriendly"
    NEUTRAL = "Neutral"
    FRIENDLY = "Friendly"
    ALLIED = "Allied"


# Tier thresholds: (min_rep, tier)
_TIER_THRESHOLDS: list[tuple[int, ReputationTier]] = [
    (50, ReputationTier.ALLIED),
    (20, ReputationTier.FRIENDLY),
    (-19, ReputationTier.NEUTRAL),
    (-49, ReputationTier.UNFRIENDLY),
]

# Tariff modifiers per tier
_TARIFF_MODIFIERS: dict[ReputationTier, float] = {
    ReputationTier.HOSTILE: 0.30,
    ReputationTier.UNFRIENDLY: 0.15,
    ReputationTier.NEUTRAL: 0.0,
    ReputationTier.FRIENDLY: -0.10,
    ReputationTier.ALLIED: -0.20,
}


def get_reputation_tier(rep: int) -> ReputationTier:
    """Get the reputation tier for a given reputation value.

    Args:
        rep: Reputation value (-100 to +100).

    Returns:
        The corresponding ReputationTier.
    """
    for threshold, tier in _TIER_THRESHOLDS:
        if rep >= threshold:
            return tier
    return ReputationTier.HOSTILE


def get_tariff_modifier(rep: int) -> float:
    """Get the tariff price modifier for a given reputation value.

    Args:
        rep: Reputation value (-100 to +100).

    Returns:
        Tariff modifier as a float (e.g., 0.30 for +30%, -0.20 for -20%).
    """
    tier = get_reputation_tier(rep)
    return _TARIFF_MODIFIERS[tier]


@dataclass
class Faction:
    """A faction that controls star systems.

    Attributes:
        id: Unique faction identifier (snake_case).
        name: Display name (Title Case).
        description: Flavor text.
        color: RGB color tuple for UI display.
        rivalry: Faction ID of the rival faction.
    """

    id: str
    name: str
    description: str
    color: tuple[int, int, int]
    rivalry: str


def generate_faction_assignments(system_ids: list[str], faction_ids: list[str]) -> dict[str, str]:
    """Randomly assign systems to factions in a balanced distribution.

    Shuffles systems and deals them round-robin to factions, ensuring each
    faction gets a roughly equal number of systems.

    Args:
        system_ids: List of system IDs to assign.
        faction_ids: List of faction IDs to assign to.

    Returns:
        Dict mapping system_id -> faction_id.
    """
    shuffled = list(system_ids)
    random.shuffle(shuffled)
    assignments: dict[str, str] = {}
    for i, system_id in enumerate(shuffled):
        assignments[system_id] = faction_ids[i % len(faction_ids)]
    return assignments
