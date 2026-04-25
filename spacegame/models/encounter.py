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

from spacegame.constants.flags import encounter_seen

if TYPE_CHECKING:
    from spacegame.models.combat import EnemyShipTemplate
    from spacegame.models.mission import MissionReward


# Base encounter chances by danger level (percentage, 0-100)
ENCOUNTER_CHANCE_SAFE = 0
ENCOUNTER_CHANCE_MODERATE = 20
ENCOUNTER_CHANCE_DANGEROUS = 40

# Early-game protection: below this level, encounters skew non-hostile
# and flee chance is boosted
EARLY_GAME_LEVEL = 3
EARLY_GAME_NON_HOSTILE_CHANCE = 55  # vs 35% normally
EARLY_GAME_FLEE_BONUS = 10  # Flat bonus to flee chance

# Distance scaling bounds (units)
_DISTANCE_MIN = 40.0
_DISTANCE_MAX = 180.0

# Probability that a triggered encounter is a distress signal instead of hostile (%)
DISTRESS_SIGNAL_CHANCE = 20

# Probability that an encounter in a dangerous system is a shakedown (%)
SHAKEDOWN_CHANCE = 15

# Percentage of encounters that are non-hostile (have choices via EncounterView)
NON_HOSTILE_CHANCE = 35

# Non-hostile type weights per danger level. CE-4 added five skill-gated
# encounter types: ransom_demand, cargo_shakedown, distress_bait,
# wandering_trader, and derelict_encounter. They share table space with the
# pre-existing types so the player meets the new content organically.
_NON_HOSTILE_WEIGHTS: dict[str, dict[str, int]] = {
    "moderate": {
        "distress_signal": 22,
        "derelict": 18,
        "merchant": 22,
        "debris": 8,
        "patrol": 7,
        "comm_intercept": 5,
        "refugee": 6,
        # CE-4 additions (lighter pressure in moderate space)
        "ransom_demand": 4,
        "cargo_shakedown": 3,
        "distress_bait": 4,
        "wandering_trader": 5,
        "derelict_encounter": 5,
    },
    "dangerous": {
        "distress_signal": 12,
        "derelict": 12,
        "merchant": 8,
        "debris": 6,
        "anomaly": 7,
        "shakedown": 10,
        "smuggler": 6,
        "patrol": 4,
        "comm_intercept": 6,
        "refugee": 3,
        "wildlife": 3,
        # CE-4 additions (QA tuned 2026-04-23: down from 4-8 to keep
        # combined CE-4 share at ~19% so repeat exposure isn't obvious
        # given only 4 instances per type).
        "ransom_demand": 5,
        "cargo_shakedown": 4,
        "distress_bait": 4,
        "wandering_trader": 3,
        "derelict_encounter": 4,
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


def _select_non_hostile_type(
    rng: _rng.Random, system_danger: str, anomaly_chance_bonus: float = 0.0
) -> str:
    """Select a non-hostile encounter type using weighted random selection.

    Args:
        rng: Seeded Random instance.
        system_danger: System danger level for weight table lookup.
        anomaly_chance_bonus: Fraction (0-1) to boost anomaly weight
            (from exploration skill "anomaly_chance").

    Returns:
        Encounter type string (e.g. "distress_signal", "derelict").
    """
    weights = dict(_NON_HOSTILE_WEIGHTS.get(system_danger, _NON_HOSTILE_WEIGHTS["moderate"]))
    # Exploration skill: anomaly_chance boosts anomaly discovery weight
    if anomaly_chance_bonus > 0:
        base_anomaly = weights.get("anomaly", 5)
        weights["anomaly"] = base_anomaly + int(anomaly_chance_bonus * 100)
    types = list(weights.keys())
    type_weights = list(weights.values())
    total = sum(type_weights)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for enc_type, weight in zip(types, type_weights, strict=True):
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
    player_level: int = 0,
    defensive_identity: str = "",
    encounter_reduction: float = 0.0,
    anomaly_sense: float = 0.0,
    anomaly_chance_bonus: float = 0.0,
) -> Optional[EncounterRef]:
    """Check if a random combat encounter triggers on travel.

    Uses a deterministic seed from game_day + system_id so the same
    travel on the same day always produces the same result. Distance
    scales the probability: short hops are safer, long journeys riskier.

    Early-game players (below EARLY_GAME_LEVEL) get a higher proportion
    of non-hostile encounters, giving them time to learn the system
    without removing danger entirely.

    Args:
        system_danger: "safe", "moderate", or "dangerous".
        enemy_template_ids: Available enemy template IDs for this region.
        game_day: Current in-game day for seed.
        system_id: Destination system ID for seed.
        distance: Travel distance in world units (default 80.0).
        player_level: Current player level. Below EARLY_GAME_LEVEL,
            encounters skew toward non-hostile types.
        encounter_reduction: Fraction (0-1) to reduce encounter chance
            (from exploration skill "encounter_reduction").
        anomaly_sense: Fraction to add to non-hostile encounter percentage
            (from exploration skill "anomaly_sense").
        anomaly_chance_bonus: Fraction to boost anomaly-type weight in
            non-hostile table (from exploration skill "anomaly_chance").

    Returns:
        EncounterRef if triggered, None otherwise.
    """
    base_chance = {
        "safe": ENCOUNTER_CHANCE_SAFE,
        "moderate": ENCOUNTER_CHANCE_MODERATE,
        "dangerous": ENCOUNTER_CHANCE_DANGEROUS,
    }.get(system_danger, ENCOUNTER_CHANCE_MODERATE)

    chance = calculate_encounter_chance(base_chance, distance)

    # Ghost identity: encounter avoidance (Phase 12A — Gap #10)
    if defensive_identity == "ghost":
        avoidance = min(30.0, 15.0)  # 15% base avoidance for Ghost ships
        chance = max(0, chance - avoidance)

    # Exploration skill: encounter_reduction lowers encounter chance
    if encounter_reduction > 0:
        chance *= 1 - encounter_reduction

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

    # Defense-in-depth (combat_balance §12 B3): strip bosses from the pool
    # even if a future caller forgets the filter. Bosses belong in
    # narrative encounters, not random travel rolls. Filtering here means
    # misuse downstream can't leak a boss.
    try:
        from spacegame.data_loader import get_data_loader

        _dl = get_data_loader()
        enemy_template_ids = [
            tid
            for tid in enemy_template_ids
            if not getattr(_dl.enemy_templates.get(tid), "is_boss", False)
        ]
    except Exception:
        # If DataLoader isn't ready (tests mocking tid strings), leave the
        # pool alone — the caller is responsible in that path.
        pass
    if not enemy_template_ids:
        return None

    # Determine encounter category: non-hostile vs hostile
    # Early-game players get a higher non-hostile ratio
    non_hostile_pct = (
        EARLY_GAME_NON_HOSTILE_CHANCE if player_level < EARLY_GAME_LEVEL else NON_HOSTILE_CHANCE
    )
    # Exploration skill: anomaly_sense increases non-hostile encounter rate
    if anomaly_sense > 0:
        non_hostile_pct = min(90, non_hostile_pct + anomaly_sense * 100)
    type_roll = rng.uniform(0, 100)
    if type_roll < non_hostile_pct:
        # Non-hostile: select specific type via weighted table
        enc_type = _select_non_hostile_type(rng, system_danger, anomaly_chance_bonus)

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

        # CE-4: pressure / variety types whose "refuse" branch leads to
        # combat need an enemy template baked into the ref so the combat
        # path has someone to fight when the player declines.
        # ``derelict_encounter`` and ``wandering_trader`` outcomes carry
        # their own enemy lists (drones, optional rob attempt) so they
        # don't need a baked enemy.
        if enc_type in ("ransom_demand", "cargo_shakedown", "distress_bait"):
            chosen_enemy = rng.choice(enemy_template_ids)
            return EncounterRef(
                enemy_template_ids=[chosen_enemy],
                encounter_seed=seed,
                encounter_type=enc_type,
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
        # Boss enemies are reserved for scripted encounters with level gates
        if getattr(template, "is_boss", False):
            continue
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
    enemy_template_ids: list[str] = field(default_factory=list)  # Boss encounters specify enemies


@dataclass
class EncounterSkillCheck:
    """A skill check attached to an encounter choice (CE-4).

    Mirrors ``dialogue.SkillCheck``'s shape so the resolution path is
    identical: pass when the player's effective skill level meets or
    exceeds ``difficulty``. Resolution uses ``SocialManager.resolve_check``
    with an empty ``npc_id`` (encounters have no persistent NPC).
    """

    skill: str
    difficulty: int
    set_flag_on_success: Optional[str] = None
    set_flag_on_failure: Optional[str] = None


@dataclass
class EncounterChoice:
    """A player choice within a non-hostile encounter.

    CE-4 additions:
    - ``skill_check`` — when set, the choice resolves through the social
      check pipeline; success returns ``outcome``, failure returns
      ``failure_outcome`` (or ``outcome`` if no failure path is authored).
    - ``failure_outcome`` — outcome branch when ``skill_check`` fails.
    - ``requires_credits`` — gates the choice; UI greys it out when
      the player can't afford it.
    """

    id: str
    label: str
    description: str
    outcome: EncounterOutcome
    skill_check: Optional["EncounterSkillCheck"] = None
    failure_outcome: Optional["EncounterOutcome"] = None
    requires_credits: int = 0


@dataclass
class EncounterContext:
    """Player/system state passed to encounter filtering."""

    encounter_type: str
    danger_level: str
    seed: int
    system_id: str = ""
    faction_id: str = ""
    player_level: int = 1
    dialogue_flags: dict[str, bool] = field(default_factory=dict)
    # RC-5: captain_ids whose rivalries the player has resolved
    # (defeated / truce / bribed_off / wanderer). Encounters attached to
    # these captains are filtered out of random selection so the player's
    # choices stick. Empty set = no filtering (backward compatible).
    resolved_captain_ids: set[str] = field(default_factory=set)


@dataclass
class EncounterDefinition:
    """Data-driven encounter template loaded from JSON.

    ``captain_id`` (CE-1) attaches a named ``EnemyCaptain`` to this
    encounter. When present, the encounter view displays the captain's
    ``pre_combat_hail`` as the description and the captain's
    ``display_name`` in the panel header, replacing the generic
    ``description`` / ``name`` fields. Encounters without a
    ``captain_id`` behave exactly as before.
    """

    id: str
    encounter_type: str
    name: str
    description: str
    choices: list[EncounterChoice]
    weight: int = 10
    danger_levels: list[str] = field(default_factory=lambda: ["moderate", "dangerous"])
    icon_color: tuple[int, int, int] = (200, 200, 200)
    only_systems: list[str] = field(default_factory=list)
    excluded_systems: list[str] = field(default_factory=list)
    required_faction: str = ""
    requires_flags: list[str] = field(default_factory=list)
    excludes_flags: list[str] = field(default_factory=list)
    unique: bool = False
    min_level: int = 0
    max_level: int = 0
    tone: str = ""
    category: str = ""
    # CE-1: named captain attached to this encounter. Optional. When set,
    # the encounter view pulls ``pre_combat_hail`` and ``display_name``
    # from the captain, replacing this definition's static fields.
    captain_id: str = ""
    # CE-3: complications attached to this encounter's combat phase.
    # Ids resolve against ``DataLoader.complications``. Empty list means
    # the encounter fights without scripted mid-fight events.
    complication_ids: list[str] = field(default_factory=list)


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


def _is_eligible(defn: EncounterDefinition, ctx: EncounterContext) -> bool:
    """Check if an encounter definition matches the given context.

    Args:
        defn: Encounter definition to check.
        ctx: Current encounter context with player/system state.

    Returns:
        True if the encounter is eligible for selection.
    """
    if defn.encounter_type != ctx.encounter_type:
        return False
    if ctx.danger_level not in defn.danger_levels:
        return False
    if defn.only_systems and ctx.system_id not in defn.only_systems:
        return False
    if ctx.system_id in defn.excluded_systems:
        return False
    if defn.required_faction and defn.required_faction != ctx.faction_id:
        return False
    if defn.min_level > 0 and ctx.player_level < defn.min_level:
        return False
    if defn.max_level > 0 and ctx.player_level > defn.max_level:
        return False
    if defn.requires_flags and not all(ctx.dialogue_flags.get(f) for f in defn.requires_flags):
        return False
    if defn.unique and ctx.dialogue_flags.get(encounter_seen(defn.id)):
        return False
    if defn.excludes_flags and any(ctx.dialogue_flags.get(f) for f in defn.excludes_flags):
        return False
    # RC-5: captain-attached encounters drop out of the random pool once
    # the player has resolved that captain (defeated/truce/bribed_off/
    # wanderer). Direct lookup via encounter_def_id bypasses _is_eligible
    # so scripted re-encounters still work.
    if defn.captain_id and defn.captain_id in ctx.resolved_captain_ids:
        return False
    return True


def _weighted_select(
    candidates: list[EncounterDefinition], seed: int
) -> Optional[EncounterDefinition]:
    """Select from candidates using weighted random.

    Args:
        candidates: Pre-filtered encounter definitions.
        seed: Deterministic seed for selection.

    Returns:
        Selected EncounterDefinition, or None if empty.
    """
    if not candidates:
        return None

    rng = _rng.Random(seed)
    weights = [c.weight for c in candidates]
    total = sum(weights)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for candidate, weight in zip(candidates, weights, strict=True):
        cumulative += weight
        if roll <= cumulative:
            return candidate
    return candidates[-1]  # Fallback for floating-point edge case


def select_encounter_definition(
    definitions: list[EncounterDefinition],
    encounter_type_or_ctx: str | EncounterContext,
    danger_level: str = "",
    seed: int = 0,
) -> Optional[EncounterDefinition]:
    """Select a weighted random encounter definition.

    Supports two calling conventions:
    - New: select_encounter_definition(definitions, context)
    - Legacy: select_encounter_definition(definitions, type, danger, seed)

    Args:
        definitions: All loaded encounter definitions.
        encounter_type_or_ctx: Either an EncounterContext or encounter type string.
        danger_level: System danger level (legacy signature only).
        seed: Deterministic seed (legacy signature only).

    Returns:
        Selected EncounterDefinition, or None if no valid definitions exist.
    """
    if isinstance(encounter_type_or_ctx, EncounterContext):
        ctx = encounter_type_or_ctx
    else:
        ctx = EncounterContext(
            encounter_type=encounter_type_or_ctx,
            danger_level=danger_level,
            seed=seed,
        )

    candidates = [d for d in definitions if _is_eligible(d, ctx)]
    return _weighted_select(candidates, ctx.seed)
