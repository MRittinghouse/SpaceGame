"""
Faction perk system.

Provides mechanical bonuses when player reaches FRIENDLY or ALLIED reputation
with a faction while in that faction's controlled systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from spacegame.models.faction import ReputationTier


# Tiers that qualify for friendly-level perks
_FRIENDLY_TIERS = {ReputationTier.FRIENDLY, ReputationTier.ALLIED}
# Tiers that qualify for allied-level perks
_ALLIED_TIERS = {ReputationTier.ALLIED}


@dataclass
class FactionPerk:
    """A single faction perk unlocked at a reputation threshold."""

    id: str
    perk_type: str  # buy_price_bonus, sell_price_bonus, mining_yield_bonus, etc.
    value: Union[float, bool]  # float for bonuses, bool for flags
    name: str
    description: str
    faction_id: str  # Set during loading
    required_tier: str  # "friendly" or "allied"


def get_active_perks(
    all_perks: dict[str, dict[str, list[FactionPerk]]],
    faction_id: str,
    rep_tier: ReputationTier,
) -> list[FactionPerk]:
    """Return all perks a player qualifies for at the given faction/tier.

    Args:
        all_perks: Nested dict of faction_id -> tier_name -> perk list.
        faction_id: The faction whose perks to check.
        rep_tier: The player's current reputation tier with this faction.

    Returns:
        List of FactionPerk instances the player qualifies for.
    """
    faction_perks = all_perks.get(faction_id, {})
    active: list[FactionPerk] = []

    if rep_tier in _FRIENDLY_TIERS:
        active.extend(faction_perks.get("friendly", []))
    if rep_tier in _ALLIED_TIERS:
        active.extend(faction_perks.get("allied", []))

    return active


def get_perk_bonus(active_perks: list[FactionPerk], perk_type: str) -> float:
    """Sum all numeric bonuses of a given type from active perks.

    Args:
        active_perks: List of currently active perks.
        perk_type: The perk type to sum (e.g. "buy_price_bonus").

    Returns:
        Total bonus as a float (e.g. 0.10 for 10%).
    """
    total = 0.0
    for perk in active_perks:
        if (
            perk.perk_type == perk_type
            and isinstance(perk.value, (int, float))
            and not isinstance(perk.value, bool)
        ):
            total += perk.value
    return total


def has_perk(active_perks: list[FactionPerk], perk_type: str) -> bool:
    """Check if any boolean perk of the given type is active.

    Args:
        active_perks: List of currently active perks.
        perk_type: The perk type to check (e.g. "free_repairs").

    Returns:
        True if at least one perk of this type is active and truthy.
    """
    return any(
        perk.perk_type == perk_type and perk.value
        for perk in active_perks
    )
