"""Random encounter model with distance-based probability scaling.

Provides deterministic encounter generation for travel between systems.
Encounter probability scales with travel distance: short hops are safer,
long journeys through dangerous space are riskier.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.combat import EnemyShipTemplate
    from spacegame.models.mission import MissionReward


# Base encounter chances by danger level (percentage, 0-100)
ENCOUNTER_CHANCE_SAFE = 0
ENCOUNTER_CHANCE_MODERATE = 20
ENCOUNTER_CHANCE_DANGEROUS = 40

# Distance scaling bounds (units)
_DISTANCE_MIN = 40.0
_DISTANCE_MAX = 180.0

# Probability that a triggered encounter is a distress signal instead of hostile (%)
DISTRESS_SIGNAL_CHANCE = 20

# Probability that an encounter in a dangerous system is a shakedown (%)
SHAKEDOWN_CHANCE = 15

# Percentage of encounters that are non-hostile (have choices via EncounterView)
NON_HOSTILE_CHANCE = 35

# Non-hostile type weights per danger level
_NON_HOSTILE_WEIGHTS: dict[str, dict[str, int]] = {
    "moderate": {
        "distress_signal": 30,
        "derelict": 25,
        "merchant": 30,
        "debris": 15,
    },
    "dangerous": {
        "distress_signal": 20,
        "derelict": 20,
        "merchant": 15,
        "debris": 15,
        "anomaly": 10,
        "shakedown": 20,
    },
}


@dataclass
class EncounterRef:
    """Lightweight encounter reference for travel encounters.

    Contains template IDs (not full objects) so game.py can resolve them
    via DataLoader.
    """

    enemy_template_ids: list[str]
    encounter_seed: int
    encounter_type: str = "hostile"  # "hostile", "distress_signal", "shakedown", etc.
    shakedown_demand: int = 0  # Credits demanded in a shakedown encounter
    encounter_def_id: str = ""  # References EncounterDefinition.id (set by game.py)


def calculate_encounter_chance(base_chance: float, distance: float) -> float:
    """Scale encounter probability by travel distance.

    Args:
        base_chance: Base encounter percentage (0-100) for the danger level.
        distance: Euclidean distance between origin and destination systems.

    Returns:
        Scaled encounter chance clamped to [0, 100].
    """
    if base_chance <= 0:
        return 0.0

    # Linear interpolation: t=0 at 40u, t=1 at 180u
    t = (distance - _DISTANCE_MIN) / (_DISTANCE_MAX - _DISTANCE_MIN)
    t = max(0.0, min(1.0, t))

    # Multiplier ranges from 0.5 (short hop) to 1.5 (long journey)
    multiplier = 0.5 + t

    result = base_chance * multiplier
    return max(0.0, min(100.0, result))


def _select_non_hostile_type(rng: _rng.Random, system_danger: str) -> str:
    """Select a non-hostile encounter type using weighted random selection.

    Args:
        rng: Seeded Random instance.
        system_danger: System danger level for weight table lookup.

    Returns:
        Encounter type string (e.g. "distress_signal", "derelict").
    """
    weights = _NON_HOSTILE_WEIGHTS.get(system_danger, _NON_HOSTILE_WEIGHTS["moderate"])
    types = list(weights.keys())
    type_weights = list(weights.values())
    total = sum(type_weights)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for enc_type, weight in zip(types, type_weights):
        cumulative += weight
        if roll <= cumulative:
            return enc_type
    return types[-1]  # Fallback


def check_travel_encounter(
    system_danger: str,
    enemy_template_ids: list[str],
    game_day: int,
    system_id: str,
    distance: float = 80.0,
) -> Optional[EncounterRef]:
    """Check if a random combat encounter triggers on travel.

    Uses a deterministic seed from game_day + system_id so the same
    travel on the same day always produces the same result. Distance
    scales the probability: short hops are safer, long journeys riskier.

    Args:
        system_danger: "safe", "moderate", or "dangerous".
        enemy_template_ids: Available enemy template IDs for this region.
        game_day: Current in-game day for seed.
        system_id: Destination system ID for seed.
        distance: Travel distance in world units (default 80.0).

    Returns:
        EncounterRef if triggered, None otherwise.
    """
    base_chance = {
        "safe": ENCOUNTER_CHANCE_SAFE,
        "moderate": ENCOUNTER_CHANCE_MODERATE,
        "dangerous": ENCOUNTER_CHANCE_DANGEROUS,
    }.get(system_danger, ENCOUNTER_CHANCE_MODERATE)

    chance = calculate_encounter_chance(base_chance, distance)

    if chance <= 0:
        return None

    # Deterministic seed
    seed_str = f"{game_day}_{system_id}_encounter"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = _rng.Random(seed)

    roll = rng.uniform(0, 100)
    if roll >= chance:
        return None

    if not enemy_template_ids:
        return None

    # Determine encounter category: non-hostile (35%) or hostile (65%)
    type_roll = rng.uniform(0, 100)
    if type_roll < NON_HOSTILE_CHANCE:
        # Non-hostile: select specific type via weighted table
        enc_type = _select_non_hostile_type(rng, system_danger)

        # Shakedown: single enemy demands credits
        if enc_type == "shakedown":
            chosen_enemy = rng.choice(enemy_template_ids)
            demand = 50 + rng.randint(0, 200)
            return EncounterRef(
                enemy_template_ids=[chosen_enemy],
                encounter_seed=seed,
                encounter_type="shakedown",
                shakedown_demand=demand,
            )

        # All other non-hostile types: no enemies
        return EncounterRef(
            enemy_template_ids=[],
            encounter_seed=seed,
            encounter_type=enc_type,
        )

    # Hostile encounter: pick 1-3 enemies based on danger level
    max_enemies = 1 if system_danger == "moderate" else min(3, len(enemy_template_ids))
    num_enemies = rng.randint(1, max_enemies)
    chosen = [rng.choice(enemy_template_ids) for _ in range(num_enemies)]

    return EncounterRef(enemy_template_ids=chosen, encounter_seed=seed, encounter_type="hostile")


# Danger tiers allowed per system danger level
_ALLOWED_TIERS: dict[str, set[str]] = {
    "safe": {"low"},
    "moderate": {"low", "moderate"},
    "dangerous": {"low", "moderate", "dangerous"},
}


def filter_enemies_for_system(
    all_templates: dict[str, EnemyShipTemplate],
    system_faction_id: str,
    system_danger: str,
) -> list[str]:
    """Filter enemy IDs appropriate for a system.

    Generic enemies (faction_id="") appear anywhere.
    Faction enemies only appear in their faction's systems.
    Danger tier filtering:
      - "safe" systems: only "low" tier enemies
      - "moderate" systems: "low" + "moderate" tier
      - "dangerous" systems: all tiers

    Args:
        all_templates: All loaded enemy ship templates.
        system_faction_id: Faction controlling this system ("" for unaligned).
        system_danger: System danger level ("safe", "moderate", "dangerous").

    Returns:
        List of enemy template IDs valid for this system.
    """
    allowed_tiers = _ALLOWED_TIERS.get(system_danger, {"low", "moderate"})
    result: list[str] = []
    for eid, template in all_templates.items():
        # Tier filter
        if template.danger_tier not in allowed_tiers:
            continue
        # Faction filter: generics appear anywhere, faction enemies only in own systems
        if template.faction_id == "" or template.faction_id == system_faction_id:
            result.append(eid)
    return result


# ============================================================================
# Encounter Definition Models
# ============================================================================


@dataclass
class EncounterOutcome:
    """Result of selecting an encounter choice."""

    description: str
    rewards: list["MissionReward"]
    leads_to_combat: bool = False


@dataclass
class EncounterChoice:
    """A player choice within a non-hostile encounter."""

    id: str
    label: str
    description: str
    outcome: EncounterOutcome


@dataclass
class EncounterDefinition:
    """Data-driven encounter template loaded from JSON."""

    id: str
    encounter_type: str
    name: str
    description: str
    choices: list[EncounterChoice]
    weight: int = 10
    danger_levels: list[str] = field(default_factory=lambda: ["moderate", "dangerous"])
    icon_color: tuple[int, int, int] = (200, 200, 200)


def lookup_encounter_definition(
    definitions: list[EncounterDefinition],
    encounter_def_id: str,
) -> Optional[EncounterDefinition]:
    """Look up a specific encounter definition by ID.

    Args:
        definitions: All loaded encounter definitions.
        encounter_def_id: The ID to find.

    Returns:
        The matching EncounterDefinition, or None if not found.
    """
    for d in definitions:
        if d.id == encounter_def_id:
            return d
    return None


def select_encounter_definition(
    definitions: list[EncounterDefinition],
    encounter_type: str,
    danger_level: str,
    seed: int,
) -> Optional[EncounterDefinition]:
    """Select a weighted random encounter definition for the given type and danger.

    Args:
        definitions: All loaded encounter definitions.
        encounter_type: The type to filter by.
        danger_level: Current system danger level.
        seed: Deterministic seed for selection.

    Returns:
        Selected EncounterDefinition, or None if no valid definitions exist.
    """
    candidates = [
        d
        for d in definitions
        if d.encounter_type == encounter_type and danger_level in d.danger_levels
    ]
    if not candidates:
        return None

    rng = _rng.Random(seed)
    weights = [c.weight for c in candidates]
    total = sum(weights)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for candidate, weight in zip(candidates, weights):
        cumulative += weight
        if roll <= cumulative:
            return candidate
    return candidates[-1]  # Fallback for floating-point edge case
