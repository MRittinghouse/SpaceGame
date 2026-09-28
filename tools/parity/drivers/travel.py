"""Jump rule goldens (SP3 spec 6.2)."""

from __future__ import annotations

import dataclasses

from spacegame.data_loader import get_data_loader
from spacegame.models.encounter import check_travel_encounter, filter_enemies_for_system
from spacegame.models.travel import (
    fuel_after_jump,
    jump_fuel_cost,
    jump_hull_restore,
    post_process_encounter,
)
from tools.parity.driver import Case

EFFICIENCIES = (10, 6)
REDUCTIONS = (0.0, 0.25)
MOD_SETS: tuple[dict[str, float], ...] = (
    {},
    {"shakedown_multiplier": 2.0},
    {"protection_chance": 15},
    {"protection_chance": 30, "shakedown_multiplier": 0.5},
)


def _fuel() -> Case:
    case = Case(
        "travel", "fuel", {"efficiencies": list(EFFICIENCIES), "reductions": list(REDUCTIONS)}
    )
    systems = get_data_loader().systems
    for origin_id, origin in systems.items():
        for dest_id, dest in systems.items():
            if origin_id == dest_id:
                continue
            for efficiency in EFFICIENCIES:
                for reduction in REDUCTIONS:
                    cost = jump_fuel_cost(origin, dest, efficiency, reduction)
                    case.record(
                        "jump_fuel_cost", [origin_id, dest_id, efficiency, reduction], cost, {}
                    )
    return case


def _small_formulas() -> Case:
    case = Case("travel", "reserve_and_restore", {})
    for fuel in (0, 1, 7):
        for reserves in (0.0, 1.0):
            case.record("fuel_after_jump", [fuel, reserves], fuel_after_jump(fuel, reserves), {})
    for max_hull in (10, 100, 340):
        for pct in (0.0, 0.01, 0.05, 0.1):
            case.record("jump_hull_restore", [max_hull, pct], jump_hull_restore(max_hull, pct), {})
    return case


def _post_process() -> Case:
    dl = get_data_loader()
    system = dl.systems["crimson_reach"]
    enemy_ids = filter_enemies_for_system(dl.enemy_templates, system.faction, system.danger_level)
    case = Case("travel", "post_process", {"system_id": system.id, "enemy_ids": enemy_ids})
    # The window runs through day 130 because crimson_reach's first shakedown
    # roll happens on day 126 at these arguments (distance 120.0, player_level
    # 5). The rolled encounter travels in the step args, so a port replays
    # post_process_encounter on it without re-rolling.
    for day in range(1, 131):
        rolled = check_travel_encounter(system.danger_level, enemy_ids, day, system.id, 120.0, 5)
        for mods in MOD_SETS:
            for safe in (False, True):
                out = post_process_encounter(
                    rolled, mods, safe_passage=safe, game_day=day, system_id=system.id
                )
                case.record(
                    "post_process_encounter",
                    [dataclasses.asdict(rolled) if rolled else None, mods, safe, day],
                    dataclasses.asdict(out) if out else None,
                    {},
                )
    return case


def build_cases() -> list[Case]:
    """Every travel case."""
    return [_fuel(), _small_formulas(), _post_process()]
