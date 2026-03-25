"""Legendary boss-drop module combat mechanics.

Implements the 5 unique mechanics from superboss trophy modules:
1. Chain Fire (King's Repeater) — chance for follow-up attacks
2. Void Absorption (Void Maw Reactor) — store damage, release as AOE
3. Heat Hardening (Forgeborn Bulwark) — armor stacks from shield hits
4. Cooldown Reduction (Collection Engine) — faster ability cycling
5. Phase Shift (Phantom Shroud) — guaranteed dodge on interval

Each mechanic is implemented as a pure function operating on
LegendaryState, making them testable and composable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from spacegame.models.ship_build import ShipBuild
from spacegame.models.ship_module import ShipModule


@dataclass
class LegendaryState:
    """Tracks all legendary module combat state for one combatant."""

    # Chain Fire (King's Repeater)
    chain_fire_chance: float = 0.0
    chain_fire_damage_mult: float = 0.5

    # Void Absorption (Void Maw Reactor)
    void_absorption_rate: float = 0.0
    void_charge: int = 0
    void_release_available: bool = False

    # Heat Hardening (Forgeborn Bulwark)
    heat_hardening_per_hit: int = 0
    heat_hardening_max: int = 0
    heat_stacks: int = 0
    low_shield_regen_mult: float = 1.0

    # Cooldown Reduction (Collection Engine)
    cooldown_reduction: int = 0
    overdrive_available: bool = False

    # Phase Shift (Phantom Shroud)
    phase_shift_interval: int = 0


def init_legendary_state(
    build: ShipBuild,
    module_catalog: dict[str, ShipModule],
) -> LegendaryState:
    """Scan a build's modules for legendary provides and init state.

    Args:
        build: The ship build with placed modules.
        module_catalog: Module blueprints for provides lookup.

    Returns:
        LegendaryState populated from any legendary modules found.
    """
    state = LegendaryState()

    for placed in build.modules:
        module = module_catalog.get(placed.module_id)
        if not module:
            continue
        p = module.provides

        # Chain Fire
        if "chain_fire_chance" in p:
            state.chain_fire_chance = max(state.chain_fire_chance, p["chain_fire_chance"])
            state.chain_fire_damage_mult = p.get("chain_fire_damage_mult", 0.5)

        # Void Absorption
        if "void_absorption_rate" in p:
            state.void_absorption_rate = max(state.void_absorption_rate, p["void_absorption_rate"])
            state.void_release_available = bool(p.get("void_release_available", False))

        # Heat Hardening
        if "heat_hardening_per_hit" in p:
            state.heat_hardening_per_hit = max(
                state.heat_hardening_per_hit, p["heat_hardening_per_hit"]
            )
            state.heat_hardening_max = max(state.heat_hardening_max, p.get("heat_hardening_max", 5))
            state.low_shield_regen_mult = max(
                state.low_shield_regen_mult, p.get("low_shield_regen_mult", 1.0)
            )

        # Cooldown Reduction
        if "cooldown_reduction" in p:
            state.cooldown_reduction = max(state.cooldown_reduction, p["cooldown_reduction"])
            if p.get("overdrive_available"):
                state.overdrive_available = True

        # Phase Shift
        if "phase_shift_interval" in p:
            state.phase_shift_interval = p["phase_shift_interval"]

    return state


# ============================================================================
# Chain Fire
# ============================================================================


def process_chain_fire(
    state: LegendaryState,
    base_damage: float,
) -> tuple[bool, float]:
    """Roll for chain fire after a weapon hit.

    Args:
        state: Legendary combat state.
        base_damage: The original hit's damage.

    Returns:
        (triggered, damage_multiplier). If triggered is True, a follow-up
        attack should fire at base_damage * damage_multiplier.
    """
    if state.chain_fire_chance <= 0:
        return False, 0.0

    if random.random() < state.chain_fire_chance:
        return True, state.chain_fire_damage_mult

    return False, 0.0


# ============================================================================
# Void Absorption
# ============================================================================


def process_void_absorption(
    state: LegendaryState,
    hull_damage: int,
) -> int:
    """Absorb a percentage of hull damage as void charge.

    Args:
        state: Legendary combat state.
        hull_damage: Hull damage being taken this hit.

    Returns:
        Amount of damage absorbed into void charge.
    """
    if state.void_absorption_rate <= 0 or hull_damage <= 0:
        return 0

    absorbed = int(hull_damage * state.void_absorption_rate)
    state.void_charge += absorbed
    return absorbed


def process_void_release(state: LegendaryState) -> int:
    """Release accumulated void charge as AOE damage.

    Once per combat. Returns the damage to deal to all enemies.

    Args:
        state: Legendary combat state.

    Returns:
        Damage amount (0 if no charge or already used).
    """
    if not state.void_release_available or state.void_charge <= 0:
        return 0

    damage = state.void_charge
    state.void_charge = 0
    state.void_release_available = False
    return damage


# ============================================================================
# Heat Hardening
# ============================================================================


def process_heat_hardening(
    state: LegendaryState,
    shield_absorbed: int,
) -> int:
    """Process heat hardening when shields absorb damage.

    Each shield hit adds armor stacks up to the cap.

    Args:
        state: Legendary combat state.
        shield_absorbed: Shield damage absorbed this hit.

    Returns:
        Armor bonus gained from this hit (0 if no change).
    """
    if state.heat_hardening_per_hit <= 0 or shield_absorbed <= 0:
        return 0

    if state.heat_stacks >= state.heat_hardening_max:
        return 0

    gained = min(state.heat_hardening_per_hit, state.heat_hardening_max - state.heat_stacks)
    state.heat_stacks += gained
    return gained


# ============================================================================
# Cooldown Reduction
# ============================================================================


def apply_cooldown_reduction(
    state: LegendaryState,
    cooldowns: dict[str, int],
) -> None:
    """Apply legendary cooldown reduction to all active cooldowns.

    Called during end_round after normal cooldown tick.

    Args:
        state: Legendary combat state.
        cooldowns: Mutable cooldown dict to modify in place.
    """
    if state.cooldown_reduction <= 0:
        return

    for key in cooldowns:
        cooldowns[key] = max(0, cooldowns[key] - state.cooldown_reduction)


# ============================================================================
# Phase Shift
# ============================================================================


def check_phase_shift(
    state: LegendaryState,
    round_number: int,
) -> bool:
    """Check if phase shift activates this round.

    Phase shift triggers every N rounds, granting guaranteed dodge
    on the next incoming attack.

    Args:
        state: Legendary combat state.
        round_number: Current combat round (1-indexed).

    Returns:
        True if phase shift is active this round.
    """
    if state.phase_shift_interval <= 0 or round_number <= 0:
        return False

    return round_number % state.phase_shift_interval == 0
