"""Sub-reputation system for per-organization standing (SA-B-EXT-1).

Provides the foundational types and helpers that consumer sprints (SA-1,
SA-B3, etc.) build on.  No concrete organization configs are defined here;
each consumer sprint declares its own config in its own module.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import Optional


@total_ordering
@dataclass(frozen=True)
class OrganizationTier:
    """A standing tier within a specific organization.

    Attributes:
        id: Stable snake_case identifier (used in gating checks).
        name: Display name shown in UI.
        rank: Ordering value; higher rank = higher standing.
        min_rep: Minimum sub-rep value required to hold this tier.
    """

    id: str
    name: str
    rank: int
    min_rep: int

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, OrganizationTier):
            return NotImplemented
        return self.rank >= other.rank

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, OrganizationTier):
            return NotImplemented
        return self.rank < other.rank


@dataclass(frozen=True)
class OrganizationConfig:
    """Configuration for a single organization's sub-reputation system.

    Attributes:
        id: Stable snake_case identifier for the organization.
        name: Display name.
        tiers: Tuple of tiers in ascending rank / min_rep order.
        min_rep: Clamp floor for sub-rep values (default 0).
        max_rep: Clamp ceiling for sub-rep values (default 100).
    """

    id: str
    name: str
    tiers: tuple[OrganizationTier, ...]
    min_rep: int = 0
    max_rep: int = 100

    def __post_init__(self) -> None:
        if not self.tiers:
            raise ValueError(f"OrganizationConfig '{self.id}' must have at least one tier.")
        ids = [t.id for t in self.tiers]
        if len(ids) != len(set(ids)):
            raise ValueError(f"OrganizationConfig '{self.id}' has duplicate tier IDs: {ids}")
        for i in range(1, len(self.tiers)):
            prev, curr = self.tiers[i - 1], self.tiers[i]
            if curr.rank <= prev.rank:
                raise ValueError(
                    f"OrganizationConfig '{self.id}' tiers must have strictly ascending "
                    f"ranks; found rank {prev.rank} then {curr.rank}."
                )
            if curr.min_rep <= prev.min_rep:
                raise ValueError(
                    f"OrganizationConfig '{self.id}' tiers must have strictly ascending "
                    f"min_rep values; found {prev.min_rep} then {curr.min_rep}."
                )


@dataclass(frozen=True)
class SubReputationDelta:
    """Notification record queued when a player crosses a tier threshold.

    Attributes:
        org_id: Organization whose tier changed.
        effective_amount: Actual rep delta after clamping.
        old_tier: Tier before the change.
        new_tier: Tier after the change.
    """

    org_id: str
    effective_amount: int
    old_tier: OrganizationTier
    new_tier: OrganizationTier


def get_tier_for_rep(config: OrganizationConfig, value: int) -> OrganizationTier:
    """Return the tier whose min_rep is the largest still <= value.

    If value is below the first tier's min_rep, the first (lowest) tier is
    returned.

    Args:
        config: Organization configuration.
        value: Current sub-rep value.

    Returns:
        The matching OrganizationTier.
    """
    best: Optional[OrganizationTier] = None
    for tier in config.tiers:
        if value >= tier.min_rep:
            best = tier
    # If no tier matched (value < first tier's min_rep), return the lowest
    return best if best is not None else config.tiers[0]


def is_at_least(config: OrganizationConfig, value: int, tier_id: str) -> bool:
    """Return True if the current rep value reaches at least the named tier.

    Returns False (not raises) when tier_id is not present in config.

    Args:
        config: Organization configuration.
        value: Current sub-rep value.
        tier_id: ID of the tier to check against.

    Returns:
        True if the current tier's rank >= the target tier's rank.
    """
    target: Optional[OrganizationTier] = None
    for tier in config.tiers:
        if tier.id == tier_id:
            target = tier
            break
    if target is None:
        return False
    current = get_tier_for_rep(config, value)
    return current >= target
