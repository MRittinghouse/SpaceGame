"""Combat loot rolls and the victory reward record (SP3 spec 6.1).

Loot used to roll on ``random.Random(encounter_seed + stable_seed("enemy", id) [+ 7919])``
in the combat view. It now rolls on SimRng keyed ``("loot" | "rare_loot", encounter_seed,
template_id)``, so the preview and the applied loot share one keyed stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spacegame.sim_rng import SimRng

LOOT_KEY = "loot"
RARE_LOOT_KEY = "rare_loot"


def loot_rng(encounter_seed: int, template_id: str, rare: bool) -> SimRng:
    """The loot stream for one enemy in one fight."""
    return SimRng.from_key(RARE_LOOT_KEY if rare else LOOT_KEY, encounter_seed, template_id)


def roll_loot(loot_table: list[dict[str, Any]], rng: SimRng) -> dict[str, int]:
    """Roll each entry of a loot table in order.

    Args:
        loot_table: Entries with ``commodity_id``, ``min_qty``, ``max_qty``, ``chance``.
        rng: The stream to draw from (see ``loot_rng``).

    Returns:
        Commodity id to quantity for the entries that dropped, summed per commodity.
    """
    result: dict[str, int] = {}
    for entry in loot_table:
        if rng.random() < entry["chance"]:
            qty = rng.randint(entry["min_qty"], entry["max_qty"])
            commodity = entry["commodity_id"]
            result[commodity] = result.get(commodity, 0) + qty
    return result


@dataclass
class CombatVictory:
    """What a won fight paid the player."""

    xp: int
    credits: int
    loot: dict[str, int] = field(default_factory=dict)
    xp_messages: list[str] = field(default_factory=list)
