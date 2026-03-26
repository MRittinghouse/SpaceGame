"""Momentum gauge system for combat.

Tracks combat momentum that builds through actions and damage,
unlocking progressively powerful abilities at threshold levels.
Part of the JRPG-inspired combat evolution (Phase 8).
"""

from dataclasses import dataclass, field
from typing import Optional

# === Momentum Thresholds ===

THRESHOLD_CHARGED = 0.25  # 25% — Crew Synergy (combos available)
THRESHOLD_SURGING = 0.50  # 50% — Overdriven Weapon (2x next hit)
THRESHOLD_OVERLOAD = 0.75  # 75% — System Overclock (+3 regen 2 turns)
THRESHOLD_ULTIMATE = 1.00  # 100% — Ship Ultimate (unique per class)

# Momentum buildup amounts
MOMENTUM_ON_HIT = 0.07  # +7% per hit dealt (buffed from 5% — reward aggression)
MOMENTUM_ON_HULL_DAMAGE = 0.05  # +5% per hit received (nerfed from 8% — reduce turtle incentive)
MOMENTUM_ON_KILL = 0.15  # +15% per enemy killed
MOMENTUM_ON_CREW_ABILITY = 0.03  # +3% per crew ability used
MOMENTUM_ON_STATUS_APPLIED = 0.03  # +3% per elemental status stack (buffed from 2%)
MOMENTUM_ON_CRITICAL_HP = 0.20  # +20% one-time when hull drops below 25%


# === Ship Class Categories ===

SHIP_CLASS_CATEGORIES: dict[str, list[str]] = {
    "starter": ["shuttle"],
    "early_combat": ["patrol_cutter"],
    "trade_freighter": ["light_freighter", "medium_freighter", "bulk_hauler", "armed_trader"],
    "fast_scout": ["fast_courier", "scout_vessel", "corsair"],
    "mining_salvage": ["prospector", "mining_barge", "salvage_rig"],
    "stealth": ["phantom", "smugglers_sloop"],
    "heavy_combat": ["war_frigate", "clipper"],
    "luxury_diplomat": ["luxury_yacht", "diplomatic_cruiser"],
    "explorer": ["deep_explorer"],
    "industrial": ["industrial_titan"],
    "faction_guild": ["consortium_merchantman"],
    "faction_union": ["syndicate_enforcer"],
    "faction_frontier": ["frontier_runner"],
    "faction_science": ["institute_vessel"],
}

# Reverse lookup: ship_id → category
_SHIP_TO_CATEGORY: dict[str, str] = {}
for _cat, _ships in SHIP_CLASS_CATEGORIES.items():
    for _ship_id in _ships:
        _SHIP_TO_CATEGORY[_ship_id] = _cat


def get_ship_class_category(ship_id: str) -> Optional[str]:
    """Look up the ship class category for a given ship type ID.

    Args:
        ship_id: The ship type identifier.

    Returns:
        Category string or None if ship not found.
    """
    return _SHIP_TO_CATEGORY.get(ship_id)


# === Momentum Gauge ===


@dataclass
class MomentumGauge:
    """Tracks combat momentum with threshold-triggered abilities.

    Momentum builds from 0.0 to 1.0 during a single combat encounter.
    At key thresholds, powerful abilities unlock. Resets between encounters.
    """

    current: float = 0.0
    overdriven_available: bool = False
    overclock_triggered: bool = False
    _thresholds_crossed: set[str] = field(default_factory=set)

    @property
    def ultimate_available(self) -> bool:
        """True when momentum has reached 100% and ultimate hasn't been used."""
        return self.current >= THRESHOLD_ULTIMATE

    def add(self, amount: float) -> list[str]:
        """Add momentum and return list of newly crossed threshold names.

        Args:
            amount: Momentum to add (0.0 to 1.0 scale). Negative ignored.

        Returns:
            List of threshold names crossed by this addition.
            Possible values: "charged", "surging", "overload", "ultimate".
        """
        if amount <= 0:
            return []

        old = self.current
        self.current = min(1.0, self.current + amount)
        crossed: list[str] = []

        if old < THRESHOLD_CHARGED <= self.current and "charged" not in self._thresholds_crossed:
            crossed.append("charged")
            self._thresholds_crossed.add("charged")

        if old < THRESHOLD_SURGING <= self.current and "surging" not in self._thresholds_crossed:
            crossed.append("surging")
            self._thresholds_crossed.add("surging")
            self.overdriven_available = True

        if old < THRESHOLD_OVERLOAD <= self.current and "overload" not in self._thresholds_crossed:
            crossed.append("overload")
            self._thresholds_crossed.add("overload")
            self.overclock_triggered = True

        if old < THRESHOLD_ULTIMATE <= self.current and "ultimate" not in self._thresholds_crossed:
            crossed.append("ultimate")
            self._thresholds_crossed.add("ultimate")

        return crossed

    def consume_overdriven(self) -> None:
        """Mark Overdriven Weapon as used.

        Does not reduce momentum. Recharges when momentum drops below 50%
        and re-crosses (e.g., after ultimate reset).
        """
        self.overdriven_available = False

    def consume_ultimate(self) -> None:
        """Activate the ship ultimate, resetting momentum to zero.

        Clears all threshold states so they can be re-crossed on rebuild.
        """
        self.current = 0.0
        self.overdriven_available = False
        self.overclock_triggered = False
        self._thresholds_crossed.clear()

    def to_dict(self) -> dict:
        """Serialize gauge state."""
        return {
            "current": self.current,
            "overdriven_available": self.overdriven_available,
            "overclock_triggered": self.overclock_triggered,
            "thresholds_crossed": sorted(self._thresholds_crossed),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MomentumGauge":
        """Restore gauge from serialized data."""
        gauge = cls(
            current=data.get("current", 0.0),
            overdriven_available=data.get("overdriven_available", False),
            overclock_triggered=data.get("overclock_triggered", False),
        )
        gauge._thresholds_crossed = set(data.get("thresholds_crossed", []))
        return gauge


# === Ship Ultimate ===


@dataclass
class ShipUltimate:
    """Definition of a ship class's ultimate ability.

    Each ship class category has exactly one ultimate. Ultimates are
    powerful one-shot abilities that consume all accumulated momentum.
    """

    id: str
    name: str
    ship_class_category: str
    description: str
    effects: list[dict]
    visual_type: str  # "damage_aoe", "damage_single", "buff_self", "control", "utility"

    def to_dict(self) -> dict:
        """Serialize ultimate definition."""
        return {
            "id": self.id,
            "name": self.name,
            "ship_class_category": self.ship_class_category,
            "description": self.description,
            "effects": self.effects,
            "visual_type": self.visual_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipUltimate":
        """Restore ultimate from serialized data."""
        return cls(
            id=data["id"],
            name=data["name"],
            ship_class_category=data["ship_class_category"],
            description=data["description"],
            effects=data.get("effects", []),
            visual_type=data.get("visual_type", "utility"),
        )
