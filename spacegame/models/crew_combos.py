"""Crew combo abilities for combat.

When specific crew pairs are both recruited and the Momentum gauge
is at 25%+, powerful combo abilities become available. Each combo
is more powerful than individual crew abilities, rewarding thoughtful
party composition. Part of Phase 9 of the combat overhaul.
"""

from dataclasses import dataclass, field
from typing import Optional

from spacegame.models.momentum import THRESHOLD_CHARGED


@dataclass
class CrewCombo:
    """A combo ability activated by a specific crew pair.

    Combos are discovered when both crew members are recruited and
    the player first reaches 25% momentum with that pair available.
    """

    id: str
    name: str
    description: str
    crew_pair: tuple[str, str]  # Two crew template IDs
    energy_cost: int
    effects: list[dict]  # Effect definitions (resolved by engine)
    visual_type: str = "buff"  # "buff", "heal", "offensive", "utility"

    def to_dict(self) -> dict:
        """Serialize combo definition."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "crew_pair": list(self.crew_pair),
            "energy_cost": self.energy_cost,
            "effects": self.effects,
            "visual_type": self.visual_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrewCombo":
        """Restore combo from serialized data."""
        pair = data["crew_pair"]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            crew_pair=(pair[0], pair[1]),
            energy_cost=data["energy_cost"],
            effects=data.get("effects", []),
            visual_type=data.get("visual_type", "buff"),
        )


# === The 6 Crew Combos ===

CREW_COMBOS: list[CrewCombo] = [
    CrewCombo(
        id="emergency_overhaul",
        name="Emergency Overhaul",
        description="Elena charts a safe vector while Marcus patches the hull. Full emergency response.",
        crew_pair=("elena", "marcus"),
        energy_cost=5,
        effects=[
            {"type": "hull_restore", "value": 40},
            {"type": "energy_restore", "value": 5},
        ],
        visual_type="heal",
    ),
    CrewCombo(
        id="precision_strike_protocol",
        name="Precision Strike Protocol",
        description="Priya identifies the weak point. Elena lines up the shot. One chance. Make it count.",
        crew_pair=("elena", "priya"),
        energy_cost=4,
        effects=[
            {"type": "accuracy_mod", "value": 100, "duration": 1},
            {"type": "damage_boost", "value": 50, "duration": 1},
        ],
        visual_type="offensive",
    ),
    CrewCombo(
        id="smugglers_escape",
        name="Smuggler's Escape",
        description="Tomas knows the blind spots. Elena punches the throttle. They'll never catch you.",
        crew_pair=("elena", "tomas"),
        energy_cost=3,
        effects=[
            {"type": "flee_bonus", "value": 60},
            {"type": "energy_restore", "value": 3},
        ],
        visual_type="utility",
    ),
    CrewCombo(
        id="system_purge",
        name="System Purge",
        description="Marcus reroutes the power. Priya targets the corrupted systems. Clean slate.",
        crew_pair=("marcus", "priya"),
        energy_cost=5,
        effects=[
            {"type": "cleanse", "value": 1},
            {"type": "shield_restore", "value": 20},
        ],
        visual_type="heal",
    ),
    CrewCombo(
        id="jury_rigged_countermeasures",
        name="Jury-Rigged Countermeasures",
        description="Marcus builds it from scrap. Tomas knows exactly where to place it. Incoming fire? What fire?",
        crew_pair=("marcus", "tomas"),
        energy_cost=4,
        effects=[
            {"type": "absorb", "value": 1},
            {"type": "energy_restore", "value": 4},
        ],
        visual_type="buff",
    ),
    CrewCombo(
        id="market_intelligence",
        name="Market Intelligence",
        description="Priya scans their systems. Tomas reads the data like a ledger. Every weakness, cataloged.",
        crew_pair=("priya", "tomas"),
        energy_cost=3,
        effects=[
            {"type": "reveal_stats", "value": 1},
            {"type": "energy_drain", "value": 4, "target": "single_enemy"},
        ],
        visual_type="offensive",
    ),
]

# Reverse lookup by ID
_COMBO_BY_ID: dict[str, CrewCombo] = {c.id: c for c in CREW_COMBOS}


def get_combo_by_id(combo_id: str) -> Optional[CrewCombo]:
    """Look up a crew combo by its ID.

    Args:
        combo_id: The combo identifier.

    Returns:
        The CrewCombo or None if not found.
    """
    return _COMBO_BY_ID.get(combo_id)


def get_available_combos(
    recruited_crew: set[str],
    discovered_combos: set[str],
    momentum_pct: float,
    energy: int,
) -> list[CrewCombo]:
    """Get all combos currently available for use.

    A combo is available when:
    1. Both crew members are recruited
    2. The combo has been discovered
    3. Momentum is at 25%+ (THRESHOLD_CHARGED)
    4. Player has enough energy

    Args:
        recruited_crew: Set of recruited crew template IDs.
        discovered_combos: Set of discovered combo IDs.
        momentum_pct: Current momentum as a fraction (0.0 to 1.0).
        energy: Player's current energy.

    Returns:
        List of available CrewCombo objects.
    """
    if momentum_pct < THRESHOLD_CHARGED:
        return []

    available: list[CrewCombo] = []
    for combo in CREW_COMBOS:
        if combo.id not in discovered_combos:
            continue
        if combo.crew_pair[0] not in recruited_crew or combo.crew_pair[1] not in recruited_crew:
            continue
        if energy < combo.energy_cost:
            continue
        available.append(combo)
    return available


def check_combo_discoveries(
    recruited_crew: set[str],
    already_discovered: set[str],
) -> list[CrewCombo]:
    """Check if any new combos should be discovered.

    A combo is discovered when both crew members are recruited.
    Discovery happens once — the combo is then permanently available
    (when momentum conditions are met).

    Args:
        recruited_crew: Set of currently recruited crew template IDs.
        already_discovered: Set of already-discovered combo IDs.

    Returns:
        List of newly discovered CrewCombo objects.
    """
    newly_discovered: list[CrewCombo] = []
    for combo in CREW_COMBOS:
        if combo.id in already_discovered:
            continue
        if (combo.crew_pair[0] in recruited_crew
                and combo.crew_pair[1] in recruited_crew):
            newly_discovered.append(combo)
    return newly_discovered
