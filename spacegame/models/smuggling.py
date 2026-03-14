"""Smuggling and contraband system models.

Defines faction law enforcement, inspection mechanics, criminal heat,
and smuggling contracts for the underground economy.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

from spacegame.models.commodity import Legality
from spacegame.models.faction import ReputationTier, get_reputation_tier

if TYPE_CHECKING:
    from spacegame.models.encounter import EncounterDefinition


class Penalty(Enum):
    """Enforcement penalty severity levels."""

    WARN = "warn"
    FINE = "fine"
    CONFISCATE = "confiscate"
    BAN = "ban"


# Penalty severity ordering for "worst penalty wins" logic
_PENALTY_SEVERITY: dict[Penalty, int] = {
    Penalty.WARN: 0,
    Penalty.FINE: 1,
    Penalty.CONFISCATE: 2,
    Penalty.BAN: 3,
}

# Heat and rep penalties by worst legality found
_HEAT_GAIN: dict[Legality, int] = {
    Legality.LEGAL: 0,
    Legality.RESTRICTED: 5,
    Legality.ILLEGAL: 15,
}

_REP_LOSS: dict[Legality, int] = {
    Legality.LEGAL: 0,
    Legality.RESTRICTED: -10,
    Legality.ILLEGAL: -30,
}

# Inspection chance floor/ceiling for enforced systems
_INSPECTION_FLOOR = 0.02
_INSPECTION_CEILING = 0.60


@dataclass
class FactionLaw:
    """How a faction enforces legality levels.

    Attributes:
        faction_id: Faction this law applies to.
        inspection_chance: Base probability of cargo scan on arrival (0.0-1.0).
        restricted_penalty: Penalty for RESTRICTED goods.
        illegal_penalty: Penalty for ILLEGAL goods.
        fine_multiplier: Multiplied by contraband cargo value to calculate fine.
    """

    faction_id: str
    inspection_chance: float
    restricted_penalty: Penalty
    illegal_penalty: Penalty
    fine_multiplier: float

    @classmethod
    def from_dict(cls, data: dict) -> FactionLaw:
        """Parse a FactionLaw from a JSON dict.

        Args:
            data: Raw JSON dict with law enforcement rules.

        Returns:
            FactionLaw instance.
        """
        return cls(
            faction_id=data["faction_id"],
            inspection_chance=data["inspection_chance"],
            restricted_penalty=Penalty(data["restricted_penalty"]),
            illegal_penalty=Penalty(data["illegal_penalty"]),
            fine_multiplier=data["fine_multiplier"],
        )


@dataclass
class InspectionResult:
    """Outcome of a customs inspection scan.

    Attributes:
        passed: True if no contraband was found.
        penalty: The worst penalty triggered.
        contraband_found: Dict of commodity_id -> quantity found.
        fine_amount: Credits to deduct as fine.
        heat_gain: Criminal heat points gained.
        reputation_loss: Faction reputation change (negative).
    """

    passed: bool
    penalty: Penalty
    contraband_found: dict[str, int]
    fine_amount: int
    heat_gain: int
    reputation_loss: int


@dataclass
class SmugglingContract:
    """A smuggling delivery job.

    Attributes:
        id: Unique contract identifier.
        client_name: Who's hiring (NPC name or alias).
        commodity_id: What to deliver.
        quantity: How much.
        source_system: Where to pick up.
        destination_system: Where to deliver.
        payment: Credits on completion.
        deadline_days: Game days to complete.
        penalty_on_failure: Credits lost if caught or expired.
        heat_on_completion: Criminal heat gained even on success.
        difficulty: "low", "medium", or "high".
    """

    id: str
    client_name: str
    commodity_id: str
    quantity: int
    source_system: str
    destination_system: str
    payment: int
    deadline_days: int
    penalty_on_failure: int
    heat_on_completion: int
    difficulty: str

    def is_expired(self, current_day: int, accepted_day: int) -> bool:
        """Check if the contract deadline has passed.

        Args:
            current_day: Current game day.
            accepted_day: Game day contract was accepted.

        Returns:
            True if deadline exceeded.
        """
        return (current_day - accepted_day) > self.deadline_days

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict with all contract fields.
        """
        return {
            "id": self.id,
            "client_name": self.client_name,
            "commodity_id": self.commodity_id,
            "quantity": self.quantity,
            "source_system": self.source_system,
            "destination_system": self.destination_system,
            "payment": self.payment,
            "deadline_days": self.deadline_days,
            "penalty_on_failure": self.penalty_on_failure,
            "heat_on_completion": self.heat_on_completion,
            "difficulty": self.difficulty,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SmugglingContract:
        """Deserialize from a JSON-compatible dict.

        Args:
            data: Dict with contract fields.

        Returns:
            SmugglingContract instance.
        """
        return cls(
            id=data["id"],
            client_name=data["client_name"],
            commodity_id=data["commodity_id"],
            quantity=data["quantity"],
            source_system=data["source_system"],
            destination_system=data["destination_system"],
            payment=data["payment"],
            deadline_days=data["deadline_days"],
            penalty_on_failure=data["penalty_on_failure"],
            heat_on_completion=data["heat_on_completion"],
            difficulty=data["difficulty"],
        )


def calculate_inspection_chance(
    faction_law: FactionLaw,
    criminal_heat: int,
    has_restricted: bool,
    has_illegal: bool,
    has_hidden_compartment: bool,
    has_signal_jammer: bool,
    has_false_transponder: bool,
    observation_level: int,
    faction_reputation: int,
) -> float:
    """Calculate the probability of a customs inspection on arrival.

    Args:
        faction_law: Local faction's enforcement rules.
        criminal_heat: Player's current criminal heat (0-100).
        has_restricted: Whether player carries RESTRICTED cargo.
        has_illegal: Whether player carries ILLEGAL cargo.
        has_hidden_compartment: Whether ship has hidden compartment upgrade.
        has_signal_jammer: Whether ship has signal jammer upgrade.
        has_false_transponder: Whether ship has false transponder upgrade.
        observation_level: Player's Observation social skill level.
        faction_reputation: Player's reputation with this faction (-100 to 100).

    Returns:
        Inspection probability (0.0 to 0.60), or 0.0 for unenforced systems.
    """
    base = faction_law.inspection_chance

    # Unenforced systems (Crimson Reach) always return 0
    if base == 0.0:
        return 0.0

    chance = base

    # Increases
    chance += criminal_heat * 0.02
    if has_restricted:
        chance += 0.05
    if has_illegal:
        chance += 0.10

    # Reputation effects
    rep_tier = get_reputation_tier(faction_reputation)
    if rep_tier in (ReputationTier.FRIENDLY, ReputationTier.ALLIED):
        chance -= 0.05
    elif rep_tier == ReputationTier.HOSTILE:
        chance += 0.10

    # Upgrade reductions
    if has_hidden_compartment:
        chance -= 0.10
    if has_signal_jammer:
        chance -= 0.05
    if has_false_transponder:
        chance -= 0.08

    # Skill reduction
    if observation_level >= 3:
        chance -= 0.03

    # Clamp to floor/ceiling
    chance = max(_INSPECTION_FLOOR, min(_INSPECTION_CEILING, chance))

    return chance


def resolve_inspection(
    faction_law: FactionLaw,
    cargo: dict[str, int],
    legality_map: dict[str, Legality],
    price_map: dict[str, int] | None = None,
) -> InspectionResult:
    """Resolve a customs inspection against the player's cargo.

    Scans all cargo, identifies contraband, and determines penalties
    based on the worst legality violation found.

    Args:
        faction_law: Local faction's enforcement rules.
        cargo: Dict of commodity_id -> quantity in main hold.
        legality_map: Dict of commodity_id -> Legality for each cargo item.
        price_map: Optional dict of commodity_id -> base_price for fine calc.

    Returns:
        InspectionResult with penalty details.
    """
    contraband: dict[str, int] = {}
    worst_legality = Legality.LEGAL

    for commodity_id, quantity in cargo.items():
        legality = legality_map.get(commodity_id, Legality.LEGAL)
        if legality != Legality.LEGAL:
            contraband[commodity_id] = quantity
            # Track worst violation
            if legality == Legality.ILLEGAL:
                worst_legality = Legality.ILLEGAL
            elif legality == Legality.RESTRICTED and worst_legality != Legality.ILLEGAL:
                worst_legality = Legality.RESTRICTED

    # Clean cargo — pass
    if not contraband:
        return InspectionResult(
            passed=True,
            penalty=Penalty.WARN,
            contraband_found={},
            fine_amount=0,
            heat_gain=0,
            reputation_loss=0,
        )

    # Determine penalty from worst violation
    if worst_legality == Legality.ILLEGAL:
        penalty = faction_law.illegal_penalty
    else:
        penalty = faction_law.restricted_penalty

    # Calculate fine
    fine_amount = 0
    if price_map and penalty in (Penalty.FINE, Penalty.CONFISCATE, Penalty.BAN):
        for commodity_id, quantity in contraband.items():
            base_price = price_map.get(commodity_id, 0)
            fine_amount += quantity * base_price
        fine_amount = int(fine_amount * faction_law.fine_multiplier)

    return InspectionResult(
        passed=False,
        penalty=penalty,
        contraband_found=contraband,
        fine_amount=fine_amount,
        heat_gain=_HEAT_GAIN[worst_legality],
        reputation_loss=_REP_LOSS[worst_legality],
    )


def should_trigger_inspection(
    faction_law: FactionLaw,
    criminal_heat: int,
    has_restricted: bool,
    has_illegal: bool,
    has_hidden_compartment: bool,
    has_signal_jammer: bool,
    has_false_transponder: bool,
    observation_level: int,
    faction_reputation: int,
    game_day: int,
    system_id: str,
) -> bool:
    """Deterministically check if a customs inspection triggers on arrival.

    Uses a seeded random roll against the calculated inspection chance.

    Args:
        faction_law: Local faction's enforcement rules.
        criminal_heat: Player's current criminal heat (0-100).
        has_restricted: Whether player carries RESTRICTED cargo.
        has_illegal: Whether player carries ILLEGAL cargo.
        has_hidden_compartment: Ship has hidden compartment upgrade.
        has_signal_jammer: Ship has signal jammer upgrade.
        has_false_transponder: Ship has false transponder upgrade.
        observation_level: Player's Observation social skill level.
        faction_reputation: Player's reputation with this faction.
        game_day: Current game day (for deterministic seed).
        system_id: Destination system ID (for deterministic seed).

    Returns:
        True if customs inspection triggers.
    """
    chance = calculate_inspection_chance(
        faction_law=faction_law,
        criminal_heat=criminal_heat,
        has_restricted=has_restricted,
        has_illegal=has_illegal,
        has_hidden_compartment=has_hidden_compartment,
        has_signal_jammer=has_signal_jammer,
        has_false_transponder=has_false_transponder,
        observation_level=observation_level,
        faction_reputation=faction_reputation,
    )

    if chance <= 0.0:
        return False

    # Deterministic seed
    seed_str = f"{game_day}_{system_id}_customs"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = _rng.Random(seed)

    roll = rng.random()
    return roll < chance


# Bribe cost as a fraction of total contraband value
_BRIBE_COST_FRACTION = 0.3

# Persuasion difficulty thresholds by worst legality
_PERSUASION_DIFFICULTY: dict[Legality, int] = {
    Legality.LEGAL: 0,
    Legality.RESTRICTED: 2,
    Legality.ILLEGAL: 4,
}

# Intimidation difficulty (always high — it's a gamble)
_INTIMIDATION_DIFFICULTY = 4


def build_inspection_encounter(
    faction_law: FactionLaw,
    faction_name: str,
    cargo: dict[str, int],
    legality_map: dict[str, Legality],
    price_map: dict[str, int],
    player_credits: int,
    persuasion_level: int,
    intimidation_level: int,
) -> EncounterDefinition:
    """Build a dynamic customs inspection encounter with player choices.

    Creates an EncounterDefinition with choices tailored to the player's
    current cargo, skills, and credits. Each choice maps to an outcome
    with appropriate rewards (penalties).

    Args:
        faction_law: Local faction's enforcement rules.
        faction_name: Display name of the inspecting faction.
        cargo: Player's cargo (commodity_id -> quantity).
        legality_map: Legality per commodity_id.
        price_map: Base price per commodity_id (for fine/bribe calc).
        player_credits: Player's current credits (for bribe affordability).
        persuasion_level: Player's Persuasion skill level.
        intimidation_level: Player's Intimidation skill level.

    Returns:
        EncounterDefinition with inspection choices and outcomes.
    """
    from spacegame.models.encounter import (
        EncounterChoice,
        EncounterDefinition,
        EncounterOutcome,
    )
    from spacegame.models.mission import MissionReward

    # Resolve what customs would find
    inspection = resolve_inspection(faction_law, cargo, legality_map, price_map)

    choices: list[EncounterChoice] = []

    # --- Choice 1: Comply (always available) ---
    if inspection.passed:
        comply_outcome = EncounterOutcome(
            description="Your cargo checks out. The inspector waves you through. All clear.",
            rewards=[],
        )
    else:
        comply_rewards: list[MissionReward] = []

        # Fine
        if inspection.fine_amount > 0 and inspection.penalty in (
            Penalty.FINE,
            Penalty.CONFISCATE,
            Penalty.BAN,
        ):
            comply_rewards.append(
                MissionReward(reward_type="deduct_credits", amount=inspection.fine_amount)
            )

        # Confiscation
        if inspection.penalty in (Penalty.CONFISCATE, Penalty.BAN):
            for commodity_id, qty in inspection.contraband_found.items():
                comply_rewards.append(
                    MissionReward(
                        reward_type="confiscate_cargo",
                        amount=qty,
                        target_id=commodity_id,
                    )
                )

        # Criminal heat
        if inspection.heat_gain > 0:
            comply_rewards.append(
                MissionReward(reward_type="add_criminal_heat", amount=inspection.heat_gain)
            )

        # Reputation loss
        if inspection.reputation_loss != 0:
            comply_rewards.append(
                MissionReward(
                    reward_type="modify_reputation",
                    amount=inspection.reputation_loss,
                    target_id=faction_law.faction_id,
                )
            )

        penalty_desc = _describe_penalty(inspection, faction_name)
        comply_outcome = EncounterOutcome(
            description=penalty_desc,
            rewards=comply_rewards,
        )

    choices.append(
        EncounterChoice(
            id="comply",
            label="Submit to inspection",
            description="Allow customs to scan your cargo.",
            outcome=comply_outcome,
        )
    )

    # --- Choice 2: Persuade ---
    worst_legality = _get_worst_legality(cargo, legality_map)
    persuasion_diff = _PERSUASION_DIFFICULTY.get(worst_legality, 2)

    if persuasion_level >= persuasion_diff:
        # Success: talk your way past
        persuade_label = f"Persuade (Lv {persuasion_level} vs {persuasion_diff})"
        persuade_outcome = EncounterOutcome(
            description=(
                "You calmly explain your business. The inspector nods, "
                "stamps your manifest, and waves you through without a full scan."
            ),
            rewards=[],
        )
    else:
        # Fail: falls back to comply outcome
        persuade_label = f"Persuade (Lv {persuasion_level} vs {persuasion_diff})"
        persuade_outcome = EncounterOutcome(
            description=(
                "The inspector isn't convinced. They proceed with a full scan. "
                + (comply_outcome.description if not inspection.passed else "Your cargo checks out.")
            ),
            rewards=list(comply_outcome.rewards),
        )

    risk_word = (
        "Likely"
        if persuasion_level >= persuasion_diff
        else "Unlikely" if persuasion_level < persuasion_diff - 1 else "Uncertain"
    )
    choices.append(
        EncounterChoice(
            id="persuade",
            label=persuade_label,
            description=f"Talk your way past the inspection. {risk_word} to succeed.",
            outcome=persuade_outcome,
        )
    )

    # --- Choice 3: Bribe ---
    contraband_value = sum(
        qty * price_map.get(cid, 0) for cid, qty in cargo.items()
        if legality_map.get(cid, Legality.LEGAL) != Legality.LEGAL
    )
    bribe_cost = max(50, int(contraband_value * _BRIBE_COST_FRACTION))
    if bribe_cost == 0:
        # Even with clean cargo, a small "convenience" bribe
        bribe_cost = 50

    if player_credits >= bribe_cost:
        choices.append(
            EncounterChoice(
                id="bribe",
                label=f"Bribe ({bribe_cost} CR)",
                description=f"Slip the inspector {bribe_cost} CR to skip the scan.",
                outcome=EncounterOutcome(
                    description=(
                        "The inspector pockets the credits and waves you through "
                        "without looking at the manifest."
                    ),
                    rewards=[
                        MissionReward(reward_type="deduct_credits", amount=bribe_cost),
                    ],
                ),
            )
        )

    # --- Choice 4: Intimidate (always available, always risky) ---
    if intimidation_level >= _INTIMIDATION_DIFFICULTY:
        # Success: scare them off
        intimidate_outcome = EncounterOutcome(
            description=(
                "You stare the inspector down. They mutter something about "
                "schedule pressure, stamp your papers, and walk away."
            ),
            rewards=[],
        )
    else:
        # Fail: double penalties
        fail_rewards: list[MissionReward] = []
        doubled_fine = inspection.fine_amount * 2
        if doubled_fine > 0:
            fail_rewards.append(
                MissionReward(reward_type="deduct_credits", amount=doubled_fine)
            )
        if inspection.penalty in (Penalty.CONFISCATE, Penalty.BAN):
            for commodity_id, qty in inspection.contraband_found.items():
                fail_rewards.append(
                    MissionReward(
                        reward_type="confiscate_cargo",
                        amount=qty,
                        target_id=commodity_id,
                    )
                )
        doubled_heat = inspection.heat_gain * 2
        if doubled_heat > 0:
            fail_rewards.append(
                MissionReward(reward_type="add_criminal_heat", amount=doubled_heat)
            )
        if inspection.reputation_loss != 0:
            fail_rewards.append(
                MissionReward(
                    reward_type="modify_reputation",
                    amount=inspection.reputation_loss * 2,
                    target_id=faction_law.faction_id,
                )
            )

        intimidate_outcome = EncounterOutcome(
            description=(
                "The inspector calls for backup. Your intimidation attempt backfires — "
                "they conduct a thorough search and double the penalties."
            ),
            rewards=fail_rewards,
        )

    risk_label = (
        "Risky" if intimidation_level < _INTIMIDATION_DIFFICULTY else "Confident"
    )
    choices.append(
        EncounterChoice(
            id="intimidate",
            label=f"Intimidate ({risk_label})",
            description=(
                f"Lv {intimidation_level} vs {_INTIMIDATION_DIFFICULTY}. "
                "A gamble — failure doubles all penalties."
            ),
            outcome=intimidate_outcome,
        )
    )

    # Build the encounter definition
    description = (
        f"{faction_name} customs hails your ship as you approach the station. "
        '"Prepare for routine cargo inspection," the officer announces.'
    )

    return EncounterDefinition(
        id="customs_inspection",
        encounter_type="customs_inspection",
        name=f"{faction_name} Customs Inspection",
        description=description,
        choices=choices,
        icon_color=(200, 160, 60),
    )


def _get_worst_legality(
    cargo: dict[str, int], legality_map: dict[str, Legality]
) -> Legality:
    """Find the worst legality level among cargo items."""
    worst = Legality.LEGAL
    for commodity_id in cargo:
        legality = legality_map.get(commodity_id, Legality.LEGAL)
        if legality == Legality.ILLEGAL:
            return Legality.ILLEGAL
        if legality == Legality.RESTRICTED:
            worst = Legality.RESTRICTED
    return worst


def _describe_penalty(inspection: InspectionResult, faction_name: str) -> str:
    """Build a human-readable description of inspection penalties."""
    parts: list[str] = [f"The {faction_name} inspector finds contraband in your hold."]
    if inspection.penalty == Penalty.WARN:
        parts.append("You receive a warning — no further action this time.")
    elif inspection.penalty == Penalty.FINE:
        parts.append(f"You are fined {inspection.fine_amount} CR.")
    elif inspection.penalty == Penalty.CONFISCATE:
        items = ", ".join(inspection.contraband_found.keys())
        parts.append(f"Your {items} are confiscated and you are fined {inspection.fine_amount} CR.")
    elif inspection.penalty == Penalty.BAN:
        items = ", ".join(inspection.contraband_found.keys())
        parts.append(
            f"Your {items} are confiscated, you are fined {inspection.fine_amount} CR, "
            "and you are temporarily banned from this station."
        )
    if inspection.heat_gain > 0:
        parts.append(f"Your criminal record worsens (+{inspection.heat_gain} heat).")
    return " ".join(parts)


# ============================================================================
# Black Market Access
# ============================================================================

# Black market price modifiers by commodity legality
_BLACK_MARKET_PRICE_MODS: dict[Legality, float] = {
    Legality.LEGAL: 0.15,       # +15% premium for anonymity
    Legality.RESTRICTED: 0.0,   # Standard price
    Legality.ILLEGAL: -0.10,    # -10% discount, plentiful supply
}


@dataclass
class BlackMarketAccess:
    """Result of checking black market availability at a station.

    Attributes:
        available: Whether the player can access the black market.
        market_name: Display name for the black market (empty if unavailable).
        reason: Explanation of why access is denied (empty if available).
    """

    available: bool
    market_name: str = ""
    reason: str = ""


# Black market rules: system_id -> (requirements, market_name)
# Each rule is a callable that checks access conditions.
_BLACK_MARKET_RULES: dict[str, tuple[str, str]] = {
    "crimson_reach": ("always", "Wrecker's Market"),
    "havens_rest": ("alliance_contact", "The Backyard"),
    "verdant": ("alliance_contact", "The Shed"),
    "nexus_prime": ("dex_heat", "The Back Room"),
    "breakstone": ("marcus_crew", "The Undershaft"),
    "stellaris_port": ("alliance_contact", "The Backyard"),
}

# Faction for Alliance systems (used by alliance_contact rule)
_ALLIANCE_FACTION = "frontier_alliance"

# Required reputation thresholds
_ALLIANCE_REP_THRESHOLD = 30
_UNION_REP_THRESHOLD = 20
_DEX_HEAT_THRESHOLD = 40


def get_black_market_name(system_id: str) -> Optional[str]:
    """Get the display name of a black market at a system.

    Args:
        system_id: System to look up.

    Returns:
        Market name string, or None if no black market exists.
    """
    rule = _BLACK_MARKET_RULES.get(system_id)
    if rule is None:
        return None
    return rule[1]


def get_black_market_systems() -> list[str]:
    """Get all system IDs that have black markets.

    Returns:
        List of system IDs with black market rules defined.
    """
    return list(_BLACK_MARKET_RULES.keys())


def check_black_market_access(
    system_id: str,
    faction_reputation: dict[str, int],
    dialogue_flags: dict[str, bool],
    crew_member_ids: list[str],
    criminal_heat: int = 0,
) -> BlackMarketAccess:
    """Check if the player can access a black market at the given system.

    Each system has different requirements based on NPC contacts,
    faction reputation, crew members, and criminal heat.

    Args:
        system_id: Current system ID.
        faction_reputation: Player's faction reputation dict.
        dialogue_flags: Player's dialogue flags dict.
        crew_member_ids: IDs of recruited crew members aboard.
        criminal_heat: Player's current criminal heat.

    Returns:
        BlackMarketAccess with availability and reason.
    """
    rule = _BLACK_MARKET_RULES.get(system_id)
    if not rule:
        return BlackMarketAccess(
            available=False,
            reason="No black market exists at this station.",
        )

    rule_type, market_name = rule

    if rule_type == "always":
        return BlackMarketAccess(available=True, market_name=market_name)

    if rule_type == "alliance_contact":
        has_contact = dialogue_flags.get("met_malia_torres", False)
        rep = faction_reputation.get(_ALLIANCE_FACTION, 0)
        if not has_contact:
            return BlackMarketAccess(
                available=False,
                reason="You need a contact in the underground network. (Meet Malia Torres)",
            )
        if rep < _ALLIANCE_REP_THRESHOLD:
            return BlackMarketAccess(
                available=False,
                reason=f"Frontier Alliance reputation too low ({rep}/{_ALLIANCE_REP_THRESHOLD}).",
            )
        return BlackMarketAccess(available=True, market_name=market_name)

    if rule_type == "dex_heat":
        has_contact = dialogue_flags.get("met_dex_halloran", False)
        if not has_contact:
            return BlackMarketAccess(
                available=False,
                reason="You need a contact who knows the local underground. (Meet Dex Halloran)",
            )
        if criminal_heat < _DEX_HEAT_THRESHOLD:
            return BlackMarketAccess(
                available=False,
                reason=f"You're not well-known enough in the underworld ({criminal_heat}/{_DEX_HEAT_THRESHOLD} heat).",
            )
        return BlackMarketAccess(available=True, market_name=market_name)

    if rule_type == "marcus_crew":
        has_marcus = "marcus_jin" in crew_member_ids
        rep = faction_reputation.get("miners_union", 0)
        if not has_marcus:
            return BlackMarketAccess(
                available=False,
                reason="You need someone who knows the miners. (Recruit Marcus Jin)",
            )
        if rep < _UNION_REP_THRESHOLD:
            return BlackMarketAccess(
                available=False,
                reason=f"Miners Union reputation too low ({rep}/{_UNION_REP_THRESHOLD}).",
            )
        return BlackMarketAccess(available=True, market_name=market_name)

    return BlackMarketAccess(available=False, reason="Unknown access rule.")


def get_black_market_price_modifier(legality: Legality) -> float:
    """Get the price modifier for a commodity at a black market.

    Args:
        legality: Commodity's legality status.

    Returns:
        Price modifier as a float (e.g., 0.15 = +15%, -0.10 = -10%).
    """
    return _BLACK_MARKET_PRICE_MODS.get(legality, 0.0)


# ============================================================================
# Smuggling Contract Manager
# ============================================================================

# Contract templates: (client_name, commodity_id, difficulty)
_CONTRACT_POOL_LOW: list[tuple[str, str, str]] = [
    ("Tomas Drifter", "contraband_medicine", "low"),
    ("Malia Torres", "weapons_components", "low"),
    ("Anonymous", "contraband_medicine", "low"),
]

_CONTRACT_POOL_MEDIUM: list[tuple[str, str, str]] = [
    ("Malia Torres", "weapons_components", "medium"),
    ("Dex Halloran", "stolen_data", "medium"),
    ("Anonymous", "restricted_tech", "medium"),
    ("Malia Torres", "combat_stims", "medium"),
]

_CONTRACT_POOL_HIGH: list[tuple[str, str, str]] = [
    ("Dex Halloran", "stolen_data", "high"),
    ("Malia Torres", "combat_stims", "high"),
    ("Anonymous", "restricted_tech", "high"),
]

# Difficulty tier unlocks by player level
_DIFFICULTY_LEVEL_THRESHOLDS: dict[str, int] = {
    "low": 1,
    "medium": 3,
    "high": 6,
}

# Payment and deadline ranges by difficulty
_CONTRACT_PARAMS: dict[str, dict] = {
    "low": {
        "quantity_range": (3, 8),
        "payment_range": (500, 800),
        "deadline_range": (8, 12),
        "penalty_range": (100, 200),
        "heat": 3,
    },
    "medium": {
        "quantity_range": (4, 10),
        "payment_range": (1000, 2000),
        "deadline_range": (6, 9),
        "penalty_range": (200, 500),
        "heat": 8,
    },
    "high": {
        "quantity_range": (5, 12),
        "payment_range": (2500, 5000),
        "deadline_range": (4, 7),
        "penalty_range": (500, 1000),
        "heat": 15,
    },
}

# All system IDs for destination selection
_SYSTEM_IDS: list[str] = [
    "nexus_prime", "stellaris_port", "breakstone", "iron_depths",
    "axiom_labs", "nova_research", "havens_rest", "verdant",
    "crimson_reach", "forgeworks",
]

# Maximum active contracts at once
_MAX_ACTIVE_CONTRACTS = 3


@dataclass
class ContractCompletionResult:
    """Result of attempting to complete a smuggling contract.

    Attributes:
        success: Whether the contract was completed.
        message: Human-readable result description.
        payment: Credits earned (0 if failed).
        heat_gain: Criminal heat gained.
        penalty: Credits lost as penalty (0 if succeeded).
    """

    success: bool
    message: str
    payment: int = 0
    heat_gain: int = 0
    penalty: int = 0


@dataclass
class _ActiveContract:
    """Internal tracking for an accepted smuggling contract."""

    contract: SmugglingContract
    accepted_day: int
    completed: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "contract": self.contract.to_dict(),
            "accepted_day": self.accepted_day,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> _ActiveContract:
        """Deserialize from dict."""
        return cls(
            contract=SmugglingContract.from_dict(data["contract"]),
            accepted_day=data["accepted_day"],
            completed=data.get("completed", False),
        )


class SmugglingContractManager:
    """Generates, tracks, and resolves smuggling delivery contracts."""

    def __init__(self) -> None:
        self._available: list[SmugglingContract] = []
        self._active: list[_ActiveContract] = []

    def generate_contracts(
        self,
        system_id: str,
        game_day: int,
        player_level: int,
    ) -> list[SmugglingContract]:
        """Generate 1-3 smuggling contracts for a black market.

        Uses deterministic seeding from system_id + game_day.
        Contracts refresh every 3 game days (seed groups by 3-day windows).

        Args:
            system_id: System where contracts are offered.
            game_day: Current game day.
            player_level: Player's current level (gates difficulty).

        Returns:
            List of newly generated contracts.
        """
        # Seed groups by 3-day windows for refresh cycle
        day_window = game_day // 3
        seed_str = f"{system_id}_{day_window}_smuggling_contracts"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = _rng.Random(seed)

        # Build pool based on player level
        pool: list[tuple[str, str, str]] = []
        for diff, threshold in _DIFFICULTY_LEVEL_THRESHOLDS.items():
            if player_level >= threshold:
                if diff == "low":
                    pool.extend(_CONTRACT_POOL_LOW)
                elif diff == "medium":
                    pool.extend(_CONTRACT_POOL_MEDIUM)
                elif diff == "high":
                    pool.extend(_CONTRACT_POOL_HIGH)

        if not pool:
            return []

        num_contracts = rng.randint(1, 3)
        new_contracts: list[SmugglingContract] = []

        for i in range(num_contracts):
            client_name, commodity_id, difficulty = rng.choice(pool)
            params = _CONTRACT_PARAMS[difficulty]

            quantity = rng.randint(*params["quantity_range"])
            payment = rng.randint(*params["payment_range"])
            deadline = rng.randint(*params["deadline_range"])
            penalty = rng.randint(*params["penalty_range"])

            # Pick destination (different from source)
            dest_options = [s for s in _SYSTEM_IDS if s != system_id]
            destination = rng.choice(dest_options)

            contract = SmugglingContract(
                id=f"smuggle_{system_id}_{day_window}_{i}",
                client_name=client_name,
                commodity_id=commodity_id,
                quantity=quantity,
                source_system=system_id,
                destination_system=destination,
                payment=payment,
                deadline_days=deadline,
                penalty_on_failure=penalty,
                heat_on_completion=params["heat"],
                difficulty=difficulty,
            )
            new_contracts.append(contract)

        # Replace available contracts for this system
        self._available = [
            c for c in self._available if c.source_system != system_id
        ]
        self._available.extend(new_contracts)

        return new_contracts

    def get_available_contracts(
        self, system_id: str
    ) -> list[SmugglingContract]:
        """Get contracts available for acceptance at a system.

        Args:
            system_id: System to filter by.

        Returns:
            List of available (unaccepted) contracts.
        """
        active_ids = {ac.contract.id for ac in self._active}
        return [
            c
            for c in self._available
            if c.source_system == system_id and c.id not in active_ids
        ]

    def get_active_contracts(self) -> list[SmugglingContract]:
        """Get all currently active (accepted, not completed) contracts.

        Returns:
            List of active contracts.
        """
        return [ac.contract for ac in self._active if not ac.completed]

    def accept_contract(
        self, contract_id: str, accepted_day: int
    ) -> tuple[bool, str]:
        """Accept a smuggling contract for delivery.

        Args:
            contract_id: ID of the contract to accept.
            accepted_day: Game day when accepted.

        Returns:
            Tuple of (success, message).
        """
        # Check max active
        active_count = sum(1 for ac in self._active if not ac.completed)
        if active_count >= _MAX_ACTIVE_CONTRACTS:
            return False, f"Maximum {_MAX_ACTIVE_CONTRACTS} active contracts allowed."

        # Check not already accepted
        if any(ac.contract.id == contract_id for ac in self._active):
            return False, "Contract already accepted."

        # Find the contract
        contract = None
        for c in self._available:
            if c.id == contract_id:
                contract = c
                break

        if contract is None:
            return False, "Contract not found."

        self._active.append(
            _ActiveContract(contract=contract, accepted_day=accepted_day)
        )
        return True, f"Contract accepted: deliver {contract.quantity} {contract.commodity_id} to {contract.destination_system}."

    def complete_contract(
        self,
        contract_id: str,
        current_system: str,
        current_day: int,
    ) -> ContractCompletionResult:
        """Attempt to complete a smuggling contract.

        Args:
            contract_id: ID of the contract to complete.
            current_system: Player's current system.
            current_day: Current game day.

        Returns:
            ContractCompletionResult with payment or penalty.
        """
        ac = None
        for a in self._active:
            if a.contract.id == contract_id and not a.completed:
                ac = a
                break

        if ac is None:
            return ContractCompletionResult(
                success=False, message="Contract not found or already completed."
            )

        contract = ac.contract

        # Check system
        if current_system != contract.destination_system:
            return ContractCompletionResult(
                success=False,
                message=f"Must be at {contract.destination_system} to complete delivery.",
            )

        # Check expiry
        if contract.is_expired(current_day, ac.accepted_day):
            ac.completed = True
            return ContractCompletionResult(
                success=False,
                message="Contract expired. Penalty applied.",
                penalty=contract.penalty_on_failure,
            )

        # Success
        ac.completed = True
        return ContractCompletionResult(
            success=True,
            message=f"Delivery complete! Earned {contract.payment} CR.",
            payment=contract.payment,
            heat_gain=contract.heat_on_completion,
        )

    def get_expired_contracts(self, current_day: int) -> list[SmugglingContract]:
        """Get active contracts that have expired.

        Args:
            current_day: Current game day.

        Returns:
            List of expired contracts.
        """
        return [
            ac.contract
            for ac in self._active
            if not ac.completed
            and ac.contract.is_expired(current_day, ac.accepted_day)
        ]

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "available": [c.to_dict() for c in self._available],
            "active": [ac.to_dict() for ac in self._active],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SmugglingContractManager:
        """Deserialize from dict.

        Args:
            data: Dict with available and active contract lists.

        Returns:
            SmugglingContractManager instance.
        """
        mgr = cls()
        mgr._available = [
            SmugglingContract.from_dict(c) for c in data.get("available", [])
        ]
        mgr._active = [
            _ActiveContract.from_dict(ac) for ac in data.get("active", [])
        ]
        return mgr


# ============================================================================
# Hidden Compartment
# ============================================================================

# Hidden hold scan detection base chance and modifiers
_HIDDEN_SCAN_BASE = 0.30
_HIDDEN_SCAN_JAMMER_REDUCTION = 0.05
_HIDDEN_SCAN_TRANSPONDER_REDUCTION = 0.08
_HIDDEN_SCAN_OBSERVATION_REDUCTION = 0.05  # At level 3+
_HIDDEN_SCAN_FLOOR = 0.05


@dataclass
class HiddenCompartment:
    """A concealed cargo compartment with lower scan detection.

    When installed, splits the ship's cargo capacity into a main hold
    and a hidden hold. The hidden hold has a lower detection chance
    during customs inspections, but penalties are doubled if found.

    Attributes:
        total_cargo_capacity: The ship's full cargo capacity.
        hidden_cargo: Dict of commodity_id -> quantity in hidden hold.
    """

    total_cargo_capacity: int
    hidden_cargo: dict[str, int] = field(default_factory=dict)

    @property
    def hidden_capacity(self) -> int:
        """Hidden hold capacity: 30% of total, min 3."""
        if self.total_cargo_capacity <= 0:
            return 0
        return max(3, int(self.total_cargo_capacity * 0.30))

    @property
    def main_capacity(self) -> int:
        """Main hold capacity: total minus hidden."""
        return self.total_cargo_capacity - self.hidden_capacity

    @property
    def hidden_used(self) -> int:
        """Total units currently in hidden hold."""
        return sum(self.hidden_cargo.values())

    def add_to_hidden(self, commodity_id: str, quantity: int) -> tuple[bool, str]:
        """Move cargo into the hidden hold.

        Args:
            commodity_id: Commodity to hide.
            quantity: Amount to transfer.

        Returns:
            Tuple of (success, message).
        """
        if self.hidden_used + quantity > self.hidden_capacity:
            return False, f"Insufficient hidden hold space ({self.hidden_capacity - self.hidden_used} free)."
        current = self.hidden_cargo.get(commodity_id, 0)
        self.hidden_cargo[commodity_id] = current + quantity
        return True, f"Moved {quantity} {commodity_id} to hidden hold."

    def remove_from_hidden(self, commodity_id: str, quantity: int) -> tuple[bool, str]:
        """Move cargo out of the hidden hold.

        Args:
            commodity_id: Commodity to retrieve.
            quantity: Amount to retrieve.

        Returns:
            Tuple of (success, message).
        """
        current = self.hidden_cargo.get(commodity_id, 0)
        if current < quantity:
            return False, f"Only {current} {commodity_id} in hidden hold."
        remaining = current - quantity
        if remaining == 0:
            del self.hidden_cargo[commodity_id]
        else:
            self.hidden_cargo[commodity_id] = remaining
        return True, f"Retrieved {quantity} {commodity_id} from hidden hold."

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "total_cargo_capacity": self.total_cargo_capacity,
            "hidden_cargo": dict(self.hidden_cargo),
        }

    @classmethod
    def from_dict(cls, data: dict) -> HiddenCompartment:
        """Deserialize from dict.

        Args:
            data: Dict with compartment fields.

        Returns:
            HiddenCompartment instance.
        """
        return cls(
            total_cargo_capacity=data.get("total_cargo_capacity", 0),
            hidden_cargo=data.get("hidden_cargo", {}),
        )


def calculate_hidden_scan_chance(
    has_signal_jammer: bool,
    has_false_transponder: bool,
    observation_level: int,
) -> float:
    """Calculate the probability of hidden hold being scanned.

    Args:
        has_signal_jammer: Ship has signal jammer upgrade.
        has_false_transponder: Ship has false transponder upgrade.
        observation_level: Player's Observation social skill level.

    Returns:
        Scan probability (0.05 to 0.30).
    """
    chance = _HIDDEN_SCAN_BASE

    if has_signal_jammer:
        chance -= _HIDDEN_SCAN_JAMMER_REDUCTION
    if has_false_transponder:
        chance -= _HIDDEN_SCAN_TRANSPONDER_REDUCTION
    if observation_level >= 3:
        chance -= _HIDDEN_SCAN_OBSERVATION_REDUCTION

    return max(_HIDDEN_SCAN_FLOOR, chance)


@dataclass
class InspectionResultWithHidden(InspectionResult):
    """Extended inspection result that tracks hidden hold detection.

    Attributes:
        hidden_penalty_doubled: True if hidden contraband was found (penalties doubled).
    """

    hidden_penalty_doubled: bool = False


def resolve_inspection_with_hidden(
    faction_law: FactionLaw,
    main_cargo: dict[str, int],
    hidden_cargo: dict[str, int],
    legality_map: dict[str, Legality],
    price_map: dict[str, int],
    hidden_scanned: bool,
) -> InspectionResultWithHidden:
    """Resolve a customs inspection with a hidden compartment.

    Main hold is always scanned. Hidden hold is only scanned if
    hidden_scanned is True. If contraband is found in the hidden
    hold, penalties are doubled (you tried to hide it).

    Args:
        faction_law: Local faction's enforcement rules.
        main_cargo: Cargo in main hold.
        hidden_cargo: Cargo in hidden hold.
        legality_map: Legality per commodity_id.
        price_map: Base price per commodity_id.
        hidden_scanned: Whether customs scanned the hidden hold.

    Returns:
        InspectionResultWithHidden with penalty details.
    """
    # Scan main hold (always)
    main_contraband: dict[str, int] = {}
    for commodity_id, quantity in main_cargo.items():
        legality = legality_map.get(commodity_id, Legality.LEGAL)
        if legality != Legality.LEGAL:
            main_contraband[commodity_id] = quantity

    # Scan hidden hold (only if detected)
    hidden_contraband: dict[str, int] = {}
    if hidden_scanned:
        for commodity_id, quantity in hidden_cargo.items():
            legality = legality_map.get(commodity_id, Legality.LEGAL)
            if legality != Legality.LEGAL:
                hidden_contraband[commodity_id] = quantity

    all_contraband = dict(main_contraband)
    for cid, qty in hidden_contraband.items():
        all_contraband[cid] = all_contraband.get(cid, 0) + qty

    # Clean cargo
    if not all_contraband:
        return InspectionResultWithHidden(
            passed=True,
            penalty=Penalty.WARN,
            contraband_found={},
            fine_amount=0,
            heat_gain=0,
            reputation_loss=0,
            hidden_penalty_doubled=False,
        )

    # Determine worst legality
    worst_legality = Legality.LEGAL
    all_cargo = dict(main_cargo)
    if hidden_scanned:
        for cid, qty in hidden_cargo.items():
            all_cargo[cid] = all_cargo.get(cid, 0) + qty
    for commodity_id in all_contraband:
        legality = legality_map.get(commodity_id, Legality.LEGAL)
        if legality == Legality.ILLEGAL:
            worst_legality = Legality.ILLEGAL
        elif legality == Legality.RESTRICTED and worst_legality != Legality.ILLEGAL:
            worst_legality = Legality.RESTRICTED

    # Penalty from worst violation
    if worst_legality == Legality.ILLEGAL:
        penalty = faction_law.illegal_penalty
    else:
        penalty = faction_law.restricted_penalty

    # Calculate fine
    fine_amount = 0
    if penalty in (Penalty.FINE, Penalty.CONFISCATE, Penalty.BAN):
        for commodity_id, quantity in all_contraband.items():
            base_price = price_map.get(commodity_id, 0)
            fine_amount += quantity * base_price
        fine_amount = int(fine_amount * faction_law.fine_multiplier)

    heat_gain = _HEAT_GAIN[worst_legality]
    reputation_loss = _REP_LOSS[worst_legality]

    # Double penalties for hidden contraband found
    has_hidden_found = bool(hidden_contraband)
    if has_hidden_found:
        fine_amount *= 2
        heat_gain *= 2
        reputation_loss *= 2

    return InspectionResultWithHidden(
        passed=False,
        penalty=penalty,
        contraband_found=all_contraband,
        fine_amount=fine_amount,
        heat_gain=heat_gain,
        reputation_loss=reputation_loss,
        hidden_penalty_doubled=has_hidden_found,
    )


# ============================================================================
# Bounty Hunter System
# ============================================================================


class BountyHunterTier(Enum):
    """Bounty hunter difficulty tiers based on criminal heat."""

    FREELANCE = "freelance"   # Heat 26-50: solo trackers, bribable
    LICENSED = "licensed"     # Heat 51-75: 1-2 ships, not bribable
    ELITE = "elite"           # Heat 76-100: 2-3 ships, faction enforcers


# Heat thresholds for each tier
_BOUNTY_TIER_THRESHOLDS: dict[BountyHunterTier, tuple[int, int]] = {
    BountyHunterTier.FREELANCE: (26, 50),
    BountyHunterTier.LICENSED: (51, 75),
    BountyHunterTier.ELITE: (76, 100),
}

# Base encounter chance per tier
_BOUNTY_TIER_CHANCES: dict[BountyHunterTier, float] = {
    BountyHunterTier.FREELANCE: 0.05,
    BountyHunterTier.LICENSED: 0.10,
    BountyHunterTier.ELITE: 0.15,
}

# Bounty hunter chance modifiers
_BOUNTY_JAMMER_REDUCTION = 0.03
_BOUNTY_TRANSPONDER_REDUCTION = 0.05
_BOUNTY_CHANCE_FLOOR = 0.01

# Enemy template pools per tier
_BOUNTY_ENEMY_POOL: dict[BountyHunterTier, list[str]] = {
    BountyHunterTier.FREELANCE: ["bounty_tracker", "bounty_enforcer"],
    BountyHunterTier.LICENSED: ["bounty_enforcer", "bounty_vanguard"],
    BountyHunterTier.ELITE: ["bounty_vanguard", "bounty_ace", "faction_enforcer"],
}

# Enemy count ranges per tier
_BOUNTY_ENEMY_COUNTS: dict[BountyHunterTier, tuple[int, int]] = {
    BountyHunterTier.FREELANCE: (1, 1),
    BountyHunterTier.LICENSED: (1, 2),
    BountyHunterTier.ELITE: (2, 3),
}

# Negotiate difficulty per tier
_BOUNTY_NEGOTIATE_DIFFICULTY: dict[BountyHunterTier, int] = {
    BountyHunterTier.FREELANCE: 3,
    BountyHunterTier.LICENSED: 4,
    BountyHunterTier.ELITE: 5,
}

# Surrender cost: heat × multiplier, minimum 200
_SURRENDER_COST_MULTIPLIER = 15
_SURRENDER_COST_MINIMUM = 200

# Heat reduction on surrender
_SURRENDER_HEAT_REDUCTION = 15

# Bribe cost: fraction of surrender cost
_BRIBE_FRACTION_OF_SURRENDER = 0.5

# Bounty immunity duration (days)
_BOUNTY_IMMUNITY_DAYS = 5

# Systems where bounty hunters don't operate
_BOUNTY_SAFE_HAVENS = {"crimson_reach"}

# Tier display info
_BOUNTY_TIER_NAMES: dict[BountyHunterTier, str] = {
    BountyHunterTier.FREELANCE: "Freelance Tracker",
    BountyHunterTier.LICENSED: "Licensed Bounty Hunter",
    BountyHunterTier.ELITE: "Elite Faction Enforcer",
}

_BOUNTY_TIER_DESCRIPTIONS: dict[BountyHunterTier, str] = {
    BountyHunterTier.FREELANCE: (
        "A freelance tracker drops out of hyperspace ahead of you. "
        '"Got a ping on your transponder, friend. We can do this the easy way or the hard way."'
    ),
    BountyHunterTier.LICENSED: (
        "Two ships bearing licensed bounty hunter transponders move to intercept. "
        "The lead ship hails you: \"You're flagged for criminal activity. Stand down and prepare to be boarded.\""
    ),
    BountyHunterTier.ELITE: (
        "A formation of faction enforcement vessels locks weapons on your ship. "
        "\"By authority of the sector council, you are ordered to surrender. Resistance will be met with force.\""
    ),
}


def get_bounty_hunter_tier(criminal_heat: int) -> BountyHunterTier | None:
    """Determine bounty hunter tier from criminal heat.

    Args:
        criminal_heat: Player's current heat (0-100).

    Returns:
        BountyHunterTier or None if heat is too low.
    """
    for tier, (low, high) in _BOUNTY_TIER_THRESHOLDS.items():
        if low <= criminal_heat <= high:
            return tier
    return None


def calculate_bounty_hunter_chance(
    criminal_heat: int,
    has_signal_jammer: bool = False,
    has_false_transponder: bool = False,
    system_id: str = "",
) -> float:
    """Calculate the probability of a bounty hunter encounter per jump.

    Args:
        criminal_heat: Player's current heat.
        has_signal_jammer: Ship has signal jammer upgrade.
        has_false_transponder: Ship has false transponder upgrade.
        system_id: Destination system (safe havens have 0% chance).

    Returns:
        Encounter probability (0.0 to 0.15).
    """
    if system_id in _BOUNTY_SAFE_HAVENS:
        return 0.0

    tier = get_bounty_hunter_tier(criminal_heat)
    if tier is None:
        return 0.0

    chance = _BOUNTY_TIER_CHANCES[tier]

    if has_signal_jammer:
        chance -= _BOUNTY_JAMMER_REDUCTION
    if has_false_transponder:
        chance -= _BOUNTY_TRANSPONDER_REDUCTION

    return max(_BOUNTY_CHANCE_FLOOR, chance)


def should_trigger_bounty_hunter(
    criminal_heat: int,
    game_day: int,
    system_id: str,
    has_signal_jammer: bool = False,
    has_false_transponder: bool = False,
) -> bool:
    """Deterministically check if a bounty hunter encounter triggers.

    Args:
        criminal_heat: Player's current heat.
        game_day: Current game day.
        system_id: Destination system.
        has_signal_jammer: Ship has signal jammer upgrade.
        has_false_transponder: Ship has false transponder upgrade.

    Returns:
        True if bounty hunter encounter triggers.
    """
    chance = calculate_bounty_hunter_chance(
        criminal_heat=criminal_heat,
        has_signal_jammer=has_signal_jammer,
        has_false_transponder=has_false_transponder,
        system_id=system_id,
    )

    if chance <= 0.0:
        return False

    seed_str = f"{game_day}_{system_id}_bounty_hunter"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = _rng.Random(seed)

    return rng.random() < chance


def get_bounty_hunter_enemies(tier: BountyHunterTier, seed: int) -> list[str]:
    """Select enemy template IDs for a bounty hunter encounter.

    Args:
        tier: Bounty hunter tier.
        seed: Random seed for deterministic selection.

    Returns:
        List of enemy template IDs.
    """
    rng = _rng.Random(seed)
    pool = _BOUNTY_ENEMY_POOL[tier]
    min_count, max_count = _BOUNTY_ENEMY_COUNTS[tier]
    count = rng.randint(min_count, max_count)

    return [rng.choice(pool) for _ in range(count)]


def calculate_surrender_cost(criminal_heat: int) -> int:
    """Calculate the credit cost of surrendering to bounty hunters.

    Args:
        criminal_heat: Player's current heat.

    Returns:
        Credits required to surrender.
    """
    cost = criminal_heat * _SURRENDER_COST_MULTIPLIER
    return max(_SURRENDER_COST_MINIMUM, cost)


def build_bounty_hunter_encounter(
    tier: BountyHunterTier,
    criminal_heat: int,
    player_credits: int,
    persuasion_level: int,
    seed: int,
) -> "EncounterDefinition":
    """Build a bounty hunter pre-combat encounter with player choices.

    Creates an EncounterDefinition with choices based on the bounty
    hunter tier: Fight (always), Surrender (pay bounty + reduce heat),
    Negotiate (persuasion check for temporary immunity), and
    Bribe (tier 1 only, cheaper but no heat reduction).

    Args:
        tier: Bounty hunter tier.
        criminal_heat: Player's current heat.
        player_credits: Player's available credits.
        persuasion_level: Player's Persuasion social skill level.
        seed: Random seed for deterministic choices.

    Returns:
        EncounterDefinition with bounty hunter choices.
    """
    from spacegame.models.encounter import (
        EncounterChoice,
        EncounterDefinition,
        EncounterOutcome,
    )
    from spacegame.models.mission import MissionReward

    choices: list[EncounterChoice] = []
    surrender_cost = calculate_surrender_cost(criminal_heat)
    negotiate_diff = _BOUNTY_NEGOTIATE_DIFFICULTY[tier]
    enemy_ids = get_bounty_hunter_enemies(tier, seed)

    # --- Fight (always available) ---
    choices.append(
        EncounterChoice(
            id="fight",
            label="Fight",
            description=f"Engage {len(enemy_ids)} hostile ship{'s' if len(enemy_ids) > 1 else ''} in combat.",
            outcome=EncounterOutcome(
                description="You power up weapons and prepare for combat.",
                rewards=[
                    MissionReward(
                        reward_type="start_bounty_combat",
                        amount=0,
                        target_id=",".join(enemy_ids),
                    ),
                ],
            ),
        )
    )

    # --- Surrender (if affordable) ---
    if player_credits >= surrender_cost:
        choices.append(
            EncounterChoice(
                id="surrender",
                label=f"Surrender ({surrender_cost:,} CR)",
                description=f"Pay the bounty and clear some heat. Costs {surrender_cost:,} CR, reduces heat by {_SURRENDER_HEAT_REDUCTION}.",
                outcome=EncounterOutcome(
                    description=(
                        "You power down your engines and transmit payment. "
                        "The hunter verifies the transfer and disengages. "
                        "\"Pleasure doing business. Stay clean.\""
                    ),
                    rewards=[
                        MissionReward(reward_type="deduct_credits", amount=surrender_cost),
                        MissionReward(reward_type="reduce_criminal_heat", amount=_SURRENDER_HEAT_REDUCTION),
                    ],
                ),
            )
        )

    # --- Negotiate (always available, skill-gated) ---
    if persuasion_level >= negotiate_diff:
        negotiate_outcome = EncounterOutcome(
            description=(
                "You convince the hunter there's a bigger target worth pursuing. "
                "They recalibrate their sensors and jump away. "
                "You have a few days before they realize the lead was cold."
            ),
            rewards=[
                MissionReward(reward_type="bounty_immunity", amount=_BOUNTY_IMMUNITY_DAYS),
            ],
        )
    else:
        negotiate_outcome = EncounterOutcome(
            description=(
                "The hunter isn't convinced. \"Nice try, but my contract says otherwise.\" "
                "They power up weapons."
            ),
            rewards=[
                MissionReward(
                    reward_type="start_bounty_combat",
                    amount=0,
                    target_id=",".join(enemy_ids),
                ),
            ],
        )

    risk_word = (
        "Likely"
        if persuasion_level >= negotiate_diff
        else "Unlikely" if persuasion_level < negotiate_diff - 1 else "Uncertain"
    )
    choices.append(
        EncounterChoice(
            id="negotiate",
            label=f"Negotiate (Lv {persuasion_level} vs {negotiate_diff})",
            description=(
                f"Talk your way out. {risk_word} to succeed. "
                f"Success grants {_BOUNTY_IMMUNITY_DAYS} days of bounty immunity."
            ),
            outcome=negotiate_outcome,
        )
    )

    # --- Bribe (tier 1 only) ---
    if tier == BountyHunterTier.FREELANCE:
        bribe_cost = max(100, int(surrender_cost * _BRIBE_FRACTION_OF_SURRENDER))
        if player_credits >= bribe_cost:
            choices.append(
                EncounterChoice(
                    id="bribe",
                    label=f"Bribe ({bribe_cost:,} CR)",
                    description=f"Slip them {bribe_cost:,} CR to look the other way. Cheaper, but doesn't reduce heat.",
                    outcome=EncounterOutcome(
                        description=(
                            "The tracker eyes the credit transfer, shrugs, and kills the "
                            "tracking signal. \"Didn't see you. Won't remember your face.\""
                        ),
                        rewards=[
                            MissionReward(reward_type="deduct_credits", amount=bribe_cost),
                        ],
                    ),
                )
            )

    tier_name = _BOUNTY_TIER_NAMES[tier]
    description = _BOUNTY_TIER_DESCRIPTIONS[tier]

    return EncounterDefinition(
        id="bounty_hunter_encounter",
        encounter_type="bounty_hunter",
        name=f"{tier_name} Encounter",
        description=description,
        choices=choices,
        icon_color=(200, 60, 60),
    )
