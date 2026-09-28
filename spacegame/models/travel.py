"""Jump rules: fuel cost, the reserve floor, encounter post-processing, hull restore.

Lifted from GalaxyMapView (SP3 spec 6.1). The protection roll moves from an md5 of a
formatted string onto SimRng, keyed ``("protection", game_day, system_id)``.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Optional

from spacegame.sim_rng import SimRng

if TYPE_CHECKING:
    from spacegame.models.encounter import EncounterRef
    from spacegame.models.system import StarSystem

PROTECTION_KEY = "protection"


def jump_fuel_cost(
    origin: StarSystem, dest: StarSystem, fuel_efficiency: int, fuel_reduction: float
) -> int:
    """Fuel a jump costs, after the Exploration ``fuel_reduction`` bonus."""
    base_cost = origin.fuel_cost_to(dest, fuel_efficiency)
    if fuel_reduction > 0:
        base_cost = max(1, int(base_cost * (1 - fuel_reduction)))
    return base_cost


def fuel_after_jump(current_fuel: int, emergency_reserves: float) -> int:
    """Fuel left after spending: Emergency Reserves keeps at least 1."""
    if emergency_reserves > 0 and current_fuel < 1:
        return 1
    return current_fuel


def post_process_encounter(
    encounter: Optional[EncounterRef],
    enc_mods: dict[str, float],
    *,
    safe_passage: bool,
    game_day: int,
    system_id: str,
) -> Optional[EncounterRef]:
    """Apply reputation modifiers to a rolled encounter.

    Args:
        encounter: The rolled encounter, or None.
        enc_mods: ``PoliticsManager.get_encounter_modifier`` output ({} without one).
        safe_passage: Whether the system's faction grants the safe-passage perk.
        game_day: Arrival day (keys the protection roll).
        system_id: Destination system (keys the protection roll).

    Returns:
        The encounter after scaling, or None when escorted or protected.
    """
    if encounter is None or not enc_mods:
        return encounter
    if encounter.shakedown_demand > 0:
        mult = enc_mods.get("shakedown_multiplier", 1.0)
        encounter = dataclasses.replace(
            encounter, shakedown_demand=int(encounter.shakedown_demand * mult)
        )
    if safe_passage and encounter.encounter_type == "hostile":
        return None
    protection = enc_mods.get("protection_chance", 0)
    if protection > 0 and encounter.encounter_type == "hostile":
        roll = SimRng.from_key(PROTECTION_KEY, game_day, system_id).randint(0, 99)
        if roll < protection:
            return None
    return encounter


def jump_hull_restore(max_hull: int, restore_pct: float) -> int:
    """Hull the Field Repairs skill restores on arrival (0 without the skill)."""
    if restore_pct <= 0:
        return 0
    return max(1, int(max_hull * restore_pct))
