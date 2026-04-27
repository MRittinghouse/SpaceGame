"""
Energy economy computation for the ship builder's B5 widget.

Turns a ShipBuild + data loader into a compact dataclass that describes
the player's per-turn combat budget:

- Pool + regen from reactors and cockpit core
- Equipped weapon inventory by tier (Sidearm / Tech / Burst)
- Sustain capacity: how many sidearms the ship can fire every turn
  on regen alone
- Alpha-strike capacity: whether the pool can fire every weapon at once
- Advisory warnings the builder surfaces to the player

Classification follows the B4 weapon tier bands in
requirements/combat_balance_design.md §2.3:
    T1 Sidearm: cooldown 0,     energy 2,   damage 10-18
    T2 Tech:    cooldown 1-2,   energy 3-5, damage 20-35
    T3 Burst:   cooldown 3-4,   energy 5-8, damage 40-60
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WeaponTier(Enum):
    """Combat weapon tier from B4 catalog."""

    SIDEARM = "sidearm"
    TECH = "tech"
    BURST = "burst"
    UNKNOWN = "unknown"


def classify_weapon(combat_move: dict) -> WeaponTier:
    """Classify a weapon's tier from its combat_move cooldown and energy.

    Args:
        combat_move: The raw combat_move dict from a ship part.

    Returns:
        The WeaponTier the weapon belongs to, or UNKNOWN if it doesn't
        fit any band cleanly.
    """
    cd = int(combat_move.get("cooldown", 0))
    eng = int(combat_move.get("energy_cost", 0))
    if cd == 0 and eng == 2:
        return WeaponTier.SIDEARM
    if 1 <= cd <= 2 and 3 <= eng <= 5:
        return WeaponTier.TECH
    if 3 <= cd <= 4 and 5 <= eng <= 8:
        return WeaponTier.BURST
    return WeaponTier.UNKNOWN


@dataclass
class EnergyEconomy:
    """A snapshot of the build's per-turn combat budget."""

    pool: int = 0
    regen: int = 0
    sidearm_count: int = 0
    tech_count: int = 0
    burst_count: int = 0
    unknown_count: int = 0
    # Cost to fire every equipped weapon once. If > pool, alpha strike is
    # impossible in a single turn.
    total_alpha_cost: int = 0
    # Cost of the cheapest equipped weapon — used to check sustain feasibility.
    min_weapon_cost: int = 0
    # How many sidearm-equivalents (2-energy weapons) regen alone can power
    # every turn. Computed as regen // 2, floor.
    sustain_capacity: int = 0
    # Whether the pool can fund a full-loadout alpha strike in turn 1.
    can_alpha_strike: bool = False
    # Whether regen sustains at least one sidearm per turn indefinitely.
    can_sustain_sidearm: bool = False
    # Human-readable advisories shown in the builder.
    advisories: list[str] = field(default_factory=list)

    @property
    def total_weapons(self) -> int:
        return self.sidearm_count + self.tech_count + self.burst_count + self.unknown_count


# ============================================================================
# Top-level computation
# ============================================================================


def compute_energy_economy(
    build: Any,
    data_loader: Any,
) -> EnergyEconomy:
    """Compute the build's energy economy.

    Reads reactor power_output / energy_regen from placed modules and
    walks placed_slots to find equipped weapon parts.

    Args:
        build: A ShipBuild instance.
        data_loader: DataLoader providing ``ship_parts`` and
            ``slot_definitions`` lookups.

    Returns:
        A fully populated EnergyEconomy.
    """
    eco = EnergyEconomy()

    # --- Pool + regen from the computed stats if available; otherwise
    # sum from placed modules directly (parity with ShipStatsComputer).
    computed = getattr(build, "computed_stats", None)
    if computed is not None:
        eco.pool = int(getattr(computed, "energy_pool", 0))
        eco.regen = int(getattr(computed, "energy_regen", 0))
    else:
        eco.pool, eco.regen = _sum_reactor_output(build)

    # --- Equipped weapon inventory from placed_slots
    parts_catalog = getattr(data_loader, "ship_parts", {}) or {}
    slot_defs = getattr(data_loader, "slot_definitions", {}) or {}

    weapon_costs: list[int] = []
    for ps in getattr(build, "placed_slots", []) or []:
        equipped_id = getattr(ps, "equipped_part_id", None)
        if not equipped_id:
            continue
        part = parts_catalog.get(equipped_id)
        if not part:
            continue
        if getattr(part, "slot_type", None) != "weapon":
            # Skip non-weapon equipped parts (shields, engines, etc.).
            # Slot-type can also be checked via slot_def for correctness:
            sdef = slot_defs.get(getattr(ps, "slot_def_id", ""))
            if sdef is None or getattr(sdef, "slot_type", None) != "weapon":
                continue
        combat_move = getattr(part, "combat_move", None)
        if not combat_move:
            continue

        tier = classify_weapon(combat_move)
        cost = int(combat_move.get("energy_cost", 0))
        weapon_costs.append(cost)

        if tier is WeaponTier.SIDEARM:
            eco.sidearm_count += 1
        elif tier is WeaponTier.TECH:
            eco.tech_count += 1
        elif tier is WeaponTier.BURST:
            eco.burst_count += 1
        else:
            eco.unknown_count += 1

    eco.total_alpha_cost = sum(weapon_costs)
    eco.min_weapon_cost = min(weapon_costs) if weapon_costs else 0
    eco.sustain_capacity = eco.regen // 2 if eco.regen > 0 else 0
    eco.can_alpha_strike = eco.total_weapons > 0 and eco.total_alpha_cost <= eco.pool
    eco.can_sustain_sidearm = eco.regen >= 2

    eco.advisories = _derive_advisories(eco)

    return eco


# ============================================================================
# Internals
# ============================================================================


def _sum_reactor_output(build: Any) -> tuple[int, int]:
    """Fallback pool/regen calculation when computed_stats is absent.

    Reads provides.power_output and provides.energy_regen from any
    placed_module whose module definition declares them.
    """
    pool = 0
    regen = 0
    for pm in getattr(build, "modules", []) or []:
        module = getattr(pm, "module", None) or getattr(pm, "module_def", None)
        if module is None:
            continue
        provides = getattr(module, "provides", {}) or {}
        pool += int(provides.get("power_output", 0))
        regen += int(provides.get("energy_regen", 0))
    return pool, regen


def _derive_advisories(eco: EnergyEconomy) -> list[str]:
    """Produce the player-facing advisory list for this economy snapshot."""
    advisories: list[str] = []

    if eco.total_weapons == 0:
        advisories.append("No weapons equipped — build cannot deal direct damage")
        return advisories

    if eco.sidearm_count == 0:
        advisories.append("No sidearm equipped — no between-burst sustain")

    if eco.burst_count == 0:
        advisories.append("No burst weapon equipped — no alpha strike option")

    if not eco.can_alpha_strike:
        advisories.append(
            f"Pool too small for full alpha strike "
            f"({eco.total_alpha_cost} needed, {eco.pool} available)"
        )

    if eco.min_weapon_cost > 0 and eco.regen < eco.min_weapon_cost:
        advisories.append(
            f"Regen ({eco.regen}/turn) below cheapest weapon cost "
            f"({eco.min_weapon_cost}) — sustain will drain"
        )

    if eco.unknown_count > 0:
        advisories.append(
            f"{eco.unknown_count} weapon(s) outside tier bands — balance tuning is uncertain"
        )

    return advisories
