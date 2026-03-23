"""Combat data models.

Defines core combat types: effects, moves, log entries, and result states
for the turn-based space combat system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster
    from spacegame.models.ship import Ship
    from spacegame.models.upgrades import ShipUpgradeManager


class WeaponElement(Enum):
    """Elemental damage type for combat moves."""

    KINETIC = "kinetic"    # Pure damage, no secondary effect
    PLASMA = "plasma"      # 66% upfront + stacking Burn DoT
    ION = "ion"            # 150% to shields, 75% to hull
    CRYO = "cryo"          # 85% damage + Chill stacks → Frozen at 3
    VOLTAIC = "voltaic"    # 85% damage + Suppressed stacks (reduce enemy damage)


class EffectType(Enum):
    """Types of effects a combat move can apply."""

    DAMAGE = "damage"
    SHIELD_RESTORE = "shield_restore"
    HULL_RESTORE = "hull_restore"
    EVASION_MOD = "evasion_mod"
    ACCURACY_MOD = "accuracy_mod"
    SHIELD_DRAIN = "shield_drain"
    DAMAGE_REDUCTION = "damage_reduction"
    ENERGY_DRAIN = "energy_drain"
    ENERGY_RESTORE = "energy_restore"
    DAMAGE_BOOST = "damage_boost"
    BURN = "burn"                # Plasma DoT: X damage per turn, stacks to 3
    CHILL = "chill"              # Cryo: stacks to 3, then Frozen (lose turn)
    SUPPRESSED = "suppressed"    # Voltaic: -12% damage per stack, stacks to 3
    CLEANSE = "cleanse"          # Remove all negative effects from self
    ABSORB = "absorb"            # Absorb next incoming hit completely (1 charge)


class EffectTarget(Enum):
    """Who a combat effect targets."""

    SELF = "self"
    ENEMY = "enemy"


class CombatResult(Enum):
    """Possible outcomes of a combat encounter."""

    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"
    NEGOTIATED = "negotiated"
    BRIBED = "bribed"
    IN_PROGRESS = "in_progress"


@dataclass
class CombatEffect:
    """A single effect applied by a combat move.

    Instant effects (duration=0) apply immediately.
    Duration effects persist for N rounds.
    """

    type: EffectType
    value: float
    duration: int = 0
    target: EffectTarget = EffectTarget.ENEMY

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "type": self.type.value,
            "value": self.value,
            "duration": self.duration,
            "target": self.target.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CombatEffect":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with type, value, and optional duration/target.

        Returns:
            CombatEffect instance.
        """
        return cls(
            type=EffectType(data["type"]),
            value=data["value"],
            duration=data.get("duration", 0),
            target=EffectTarget(data.get("target", "enemy")),
        )


@dataclass
class CombatMove:
    """An action available during combat.

    Each equipped weapon/defense provides one move. Crew companions
    also contribute unique moves.
    """

    id: str
    name: str
    description: str
    effects: list[CombatEffect]
    energy_cost: int = 0
    cooldown: int = 0
    accuracy_modifier: int = 0
    element: WeaponElement = WeaponElement.KINETIC
    aoe: bool = False  # True = hits all enemies (Broadside etc.)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effects": [e.to_dict() for e in self.effects],
            "energy_cost": self.energy_cost,
            "cooldown": self.cooldown,
            "accuracy_modifier": self.accuracy_modifier,
        }
        if self.element != WeaponElement.KINETIC:
            result["element"] = self.element.value
        if self.aoe:
            result["aoe"] = True
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "CombatMove":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with id, name, description, effects, and
                optional energy_cost/cooldown/accuracy_modifier/element.

        Returns:
            CombatMove instance.
        """
        element_str = data.get("element", "kinetic")
        try:
            element = WeaponElement(element_str)
        except ValueError:
            element = WeaponElement.KINETIC

        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            effects=[CombatEffect.from_dict(e) for e in data.get("effects", [])],
            energy_cost=data.get("energy_cost", 0),
            cooldown=data.get("cooldown", 0),
            accuracy_modifier=data.get("accuracy_modifier", 0),
            element=element,
            aoe=data.get("aoe", False),
        )


@dataclass
class CombatLogEntry:
    """Record of a single action taken during combat."""

    round_number: int
    actor: str
    action: str
    effects_applied: list[str]
    hit: bool = True


class EnemyBehavior(Enum):
    """AI behavior patterns for enemy ships."""

    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    COWARDLY = "cowardly"
    EVASIVE = "evasive"


@dataclass
class BossPhase:
    """A single phase in a boss encounter.

    Bosses change behavior at HP thresholds. Each phase defines
    which moves are available, what behavior to use, and optional
    transition effects.
    """

    name: str
    hp_threshold: float  # Phase activates when total HP ratio drops below this (1.0 = always active)
    behavior: str  # "aggressive", "defensive", "evasive", "berserker", "tactical"
    move_ids: list[str] = field(default_factory=list)  # IDs of moves available in this phase
    on_enter_text: str = ""  # Dialogue/flavor text shown on transition
    on_enter_effect: str = ""  # Special effect on transition (e.g., "spawn_pirate_scout")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hp_threshold": self.hp_threshold,
            "behavior": self.behavior,
            "move_ids": self.move_ids,
            "on_enter_text": self.on_enter_text,
            "on_enter_effect": self.on_enter_effect,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BossPhase":
        return cls(
            name=data["name"],
            hp_threshold=data["hp_threshold"],
            behavior=data.get("behavior", "aggressive"),
            move_ids=data.get("move_ids", data.get("moves", [])),
            on_enter_text=data.get("on_enter_text", ""),
            on_enter_effect=data.get("on_enter_effect", ""),
        )


@dataclass
class EnemyShipTemplate:
    """Immutable template defining an enemy ship type.

    Used by DataLoader to define enemy archetypes. Runtime instances
    are created via EnemyShip.from_template().
    """

    id: str
    name: str
    description: str
    behavior: EnemyBehavior
    hull: int
    shields: int
    energy: int
    energy_regen: int
    speed: int
    evasion: int
    accuracy: int
    moves: list[CombatMove]
    loot_table: list[dict]
    negotiate_difficulty: int = 3
    flee_threshold: float = 0.4
    xp_reward: int = 20
    faction_id: str = ""
    danger_tier: str = "moderate"
    bribe_cost: int = 0
    credit_reward: int = 0
    rare_loot: list[dict] = field(default_factory=list)
    combat_armor: int = 0
    # Boss encounter fields (Phase 10)
    is_boss: bool = False
    boss_hp_multiplier: int = 1
    phases: list[BossPhase] = field(default_factory=list)
    immune_to: list[str] = field(default_factory=list)  # Effect types the boss is immune to
    max_suppressed_stacks: int = 3  # Default 3, bosses may cap lower
    trophy_drop: str = ""  # Shape/material ID dropped on first kill


@dataclass
class EnemyShip:
    """Mutable runtime state for an enemy ship in combat.

    Created from an EnemyShipTemplate at the start of each encounter.
    Tracks current hull, shields, energy, active effects, and cooldowns.
    """

    template: EnemyShipTemplate
    current_hull: int
    current_shields: int
    current_energy: int
    active_effects: list[tuple[CombatEffect, int]]
    cooldowns: dict[str, int]
    is_fled: bool = False
    telegraphed_move: Optional["CombatMove"] = None  # What enemy plans to do next
    # Boss state (Phase 10)
    current_phase_idx: int = 0

    @classmethod
    def from_template(cls, template: EnemyShipTemplate) -> "EnemyShip":
        """Create a combat-ready enemy ship from a template.

        For boss enemies, applies the HP multiplier to hull and shields.

        Args:
            template: The enemy ship template to instantiate.

        Returns:
            EnemyShip with full health/energy and no active effects.
        """
        mult = template.boss_hp_multiplier if template.is_boss else 1
        return cls(
            template=template,
            current_hull=template.hull * mult,
            current_shields=template.shields * mult,
            current_energy=template.energy,
            active_effects=[],
            cooldowns={},
        )

    @property
    def is_alive(self) -> bool:
        """Whether this enemy still has hull points remaining."""
        return self.current_hull > 0

    @property
    def max_hull(self) -> int:
        """Maximum hull HP (applies boss multiplier)."""
        mult = self.template.boss_hp_multiplier if self.template.is_boss else 1
        return self.template.hull * mult

    @property
    def max_shields(self) -> int:
        """Maximum shield HP (applies boss multiplier)."""
        mult = self.template.boss_hp_multiplier if self.template.is_boss else 1
        return self.template.shields * mult

    @property
    def total_hp_ratio(self) -> float:
        """Combined hull+shields as fraction of max (for boss phase thresholds)."""
        max_total = self.max_hull + self.max_shields
        if max_total <= 0:
            return 0.0
        current_total = self.current_hull + self.current_shields
        return max(0.0, current_total / max_total)

    @property
    def hull_ratio(self) -> float:
        """Current hull as a fraction of maximum (0.0 to 1.0)."""
        if self.max_hull <= 0:
            return 0.0
        return max(0.0, self.current_hull / self.max_hull)

    def get_effective_evasion(self) -> int:
        """Base evasion plus all active evasion modifiers."""
        total = self.template.evasion
        for effect, _ in self.active_effects:
            if effect.type == EffectType.EVASION_MOD:
                total += int(effect.value)
        return max(0, total)

    def get_effective_accuracy(self) -> int:
        """Base accuracy plus all active accuracy modifiers."""
        total = self.template.accuracy
        for effect, _ in self.active_effects:
            if effect.type == EffectType.ACCURACY_MOD:
                total += int(effect.value)
        return total

    def tick_effects(self) -> list[str]:
        """Decrement active effect durations, apply DoTs, and remove expired.

        Returns:
            List of human-readable messages about effects ticking/expiring.
        """
        messages: list[str] = []
        remaining: list[tuple[CombatEffect, int]] = []

        for effect, turns_left in self.active_effects:
            # Burn DoT: deal damage each tick
            if effect.type == EffectType.BURN:
                burn_dmg = int(effect.value)
                self.current_hull = max(0, self.current_hull - burn_dmg)
                messages.append(f"Burn: {burn_dmg} damage to {self.template.name}")

            new_turns = turns_left - 1
            if new_turns <= 0:
                messages.append(
                    f"{effect.type.value} effect expired on {self.template.name}"
                )
            else:
                remaining.append((effect, new_turns))
        self.active_effects = remaining
        return messages

    def tick_cooldowns(self) -> None:
        """Decrement all cooldowns by 1 and remove those that reach 0."""
        expired = []
        for move_id in self.cooldowns:
            self.cooldowns[move_id] -= 1
            if self.cooldowns[move_id] <= 0:
                expired.append(move_id)
        for move_id in expired:
            del self.cooldowns[move_id]

    def regenerate_energy(self) -> None:
        """Regenerate energy up to the template's maximum."""
        self.current_energy = min(
            self.template.energy,
            self.current_energy + self.template.energy_regen,
        )


@dataclass
class PlayerCombatState:
    """Mutable player state during a combat encounter.

    Built from Ship + ShipUpgradeManager + CrewRoster at combat start.
    Mirrors EnemyShip's interface for symmetric damage resolution.
    """

    hull: int
    max_hull: int
    shields: int
    max_shields: int
    energy: int
    max_energy: int
    energy_regen: int
    speed: int
    evasion: int
    accuracy: int
    equipment_moves: list[CombatMove]
    crew_moves: list[CombatMove]
    active_effects: list[tuple[CombatEffect, int]]
    cooldowns: dict[str, int]
    flee_bonus: int = 0
    # Defensive identity system (Phase 12A)
    armor: int = 0
    shield_regen: int = 0
    defensive_identity: str = ""  # "juggernaut", "sentinel", "ghost", or ""
    counterstrike_stacks: int = 0
    shield_break_vulnerable: bool = False
    evasion_decay: int = 0  # Temporary evasion penalty after being hit
    # Momentum system (Phase 8)
    ship_class_category: str = ""
    momentum: "MomentumGauge | None" = field(default=None, repr=False)
    critical_hp_surge_fired: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize momentum gauge if not provided."""
        if self.momentum is None:
            from spacegame.models.momentum import MomentumGauge
            self.momentum = MomentumGauge()

    @property
    def is_alive(self) -> bool:
        """Whether the player still has hull points remaining."""
        return self.hull > 0

    @property
    def hull_ratio(self) -> float:
        """Current hull as a fraction of maximum (0.0 to 1.0)."""
        if self.max_hull <= 0:
            return 0.0
        return max(0.0, self.hull / self.max_hull)

    def get_effective_evasion(self) -> int:
        """Base evasion plus all active evasion modifiers."""
        total = self.evasion
        for effect, _ in self.active_effects:
            if effect.type == EffectType.EVASION_MOD:
                total += int(effect.value)
        return max(0, total)

    def get_effective_accuracy(self) -> int:
        """Base accuracy plus all active accuracy modifiers."""
        total = self.accuracy
        for effect, _ in self.active_effects:
            if effect.type == EffectType.ACCURACY_MOD:
                total += int(effect.value)
        return total

    def tick_effects(self) -> list[str]:
        """Decrement active effect durations, apply DoTs, and remove expired.

        Returns:
            List of human-readable messages about effects ticking/expiring.
        """
        messages: list[str] = []
        remaining: list[tuple[CombatEffect, int]] = []

        for effect, turns_left in self.active_effects:
            # Burn DoT: deal damage each tick
            if effect.type == EffectType.BURN:
                burn_dmg = int(effect.value)
                self.hull = max(0, self.hull - burn_dmg)
                messages.append(f"Burn: {burn_dmg} damage")

            # Energy restore over time (Overclock regen buff)
            if effect.type == EffectType.ENERGY_RESTORE and effect.duration > 0:
                restored = min(int(effect.value), self.max_energy - self.energy)
                if restored > 0:
                    self.energy += restored
                    messages.append(f"Overclock: +{restored} energy")

            new_turns = turns_left - 1
            if new_turns <= 0:
                messages.append(f"{effect.type.value} effect expired")
            else:
                remaining.append((effect, new_turns))
        self.active_effects = remaining
        return messages

    def tick_cooldowns(self) -> None:
        """Decrement all cooldowns by 1 and remove those that reach 0."""
        expired = []
        for move_id in self.cooldowns:
            self.cooldowns[move_id] -= 1
            if self.cooldowns[move_id] <= 0:
                expired.append(move_id)
        for move_id in expired:
            del self.cooldowns[move_id]

    def regenerate_energy(self) -> None:
        """Regenerate energy up to maximum."""
        self.energy = min(self.max_energy, self.energy + self.energy_regen)


@dataclass
class CombatEncounter:
    """Definition of a combat encounter before it begins.

    Specifies which enemies to face and provides a seed for
    deterministic RNG in tests.
    """

    enemy_templates: list[EnemyShipTemplate]
    encounter_seed: int


@dataclass
class CombatState:
    """Full mutable state of an in-progress combat encounter.

    Owned by CombatEngine. Tracks player, enemies, round number,
    result, combat log, and whether negotiation has been attempted.
    """

    player: PlayerCombatState
    enemies: list[EnemyShip]
    encounter: CombatEncounter
    combat_log: list[CombatLogEntry]
    round_number: int = 1
    result: CombatResult = CombatResult.IN_PROGRESS
    negotiate_used: bool = False
    bribe_used: bool = False

    # Enhanced negotiation outcome flags (set by CombatEngine)
    negotiate_partial_loot: bool = False
    negotiate_rival_rep: bool = False
    revealed_bribe_cost: int = -1  # -1 = not revealed

    @property
    def all_enemies_defeated(self) -> bool:
        """Whether all enemies are dead or fled."""
        return all(not e.is_alive or e.is_fled for e in self.enemies)

    @property
    def surviving_enemies(self) -> list[EnemyShip]:
        """Enemies that are alive and have not fled."""
        return [e for e in self.enemies if e.is_alive and not e.is_fled]


def build_player_combat_state(
    ship: Ship,
    upgrade_manager: ShipUpgradeManager,
    crew_roster: Optional[CrewRoster],
    crew_combat_moves: dict[str, list[CombatMove] | CombatMove],
    player_level: int = 0,
    progression: Optional[object] = None,
) -> PlayerCombatState:
    """Build PlayerCombatState from existing game objects.

    Pulls base combat stats from ShipType, equipment moves from
    ShipUpgradeManager, crew moves from the provided mapping, and
    skill bonuses from PlayerProgression.

    Args:
        ship: Player's ship instance (uses current_hull/current_shields).
        upgrade_manager: Installed upgrades (provides equipment combat moves).
        crew_roster: Recruited crew (provides crew move IDs). May be None.
        crew_combat_moves: Mapping of crew template_id to their CombatMove or
            list of CombatMoves (for the crew tactical choice system).
        player_level: Current player level (early-game flee bonus applied).
        progression: PlayerProgression for skill bonuses. May be None.

    Returns:
        Fully initialized PlayerCombatState.
    """
    from spacegame.models.encounter import EARLY_GAME_FLEE_BONUS, EARLY_GAME_LEVEL

    st = ship.ship_type

    # Equipment moves from installed upgrades
    equipment_moves = upgrade_manager.get_combat_moves()

    # Crew moves from recruited members (supports both single and multiple moves)
    crew_moves: list[CombatMove] = []
    if crew_roster:
        for template, _state in crew_roster.get_recruited_members():
            if template.id in crew_combat_moves:
                entry = crew_combat_moves[template.id]
                if isinstance(entry, list):
                    crew_moves.extend(entry)
                else:
                    crew_moves.append(entry)

    flee_bonus = int(upgrade_manager.get_bonus("flee_bonus"))
    if player_level < EARLY_GAME_LEVEL:
        flee_bonus += EARLY_GAME_FLEE_BONUS

    # Aggregate defensive bonuses from upgrades (Phase 12B)
    armor_from_upgrades = int(upgrade_manager.get_bonus("armor_bonus"))
    shield_regen_from_upgrades = int(upgrade_manager.get_bonus("shield_regen_bonus"))
    evasion_from_upgrades = int(upgrade_manager.get_bonus("evasion_bonus"))
    shield_max_from_upgrades = int(upgrade_manager.get_bonus("shield_bonus"))

    # Aggregate skill tree bonuses (Phase 12C gap fix)
    armor_from_skills = 0
    shield_regen_from_skills = 0
    evasion_from_skills = 0
    flee_from_skills = 0
    if progression and hasattr(progression, "get_bonus"):
        armor_from_skills = int(progression.get_bonus("armor_bonus"))
        shield_regen_from_skills = int(progression.get_bonus("shield_regen_bonus"))
        # Afterburner skill gives evasion + flee
        afterburner = int(progression.get_bonus("afterburner_bonus"))
        evasion_from_skills = afterburner
        flee_from_skills = afterburner  # Same value for both
        # Slippery skill gives flee + encounter avoidance
        flee_from_skills += int(progression.get_bonus("slippery_bonus") * 100)
        # Tactical retreat (existing skill)
        flee_from_skills += int(progression.get_bonus("flee_bonus") * 100)

    flee_bonus += flee_from_skills

    # Ghost identity Slippery passive: +20% base flee bonus
    if st.defensive_identity == "ghost":
        flee_bonus += 20

    return PlayerCombatState(
        hull=ship.current_hull,
        max_hull=st.combat_hull,
        shields=ship.current_shields,
        max_shields=st.combat_shields + shield_max_from_upgrades,
        energy=st.combat_energy,
        max_energy=st.combat_energy,
        energy_regen=st.combat_energy_regen,
        speed=st.combat_speed,
        evasion=st.combat_evasion + evasion_from_upgrades + evasion_from_skills,
        accuracy=st.combat_accuracy,
        equipment_moves=equipment_moves,
        crew_moves=crew_moves,
        active_effects=[],
        cooldowns={},
        flee_bonus=flee_bonus,
        armor=st.combat_armor + armor_from_upgrades + armor_from_skills,
        shield_regen=st.combat_shield_regen + shield_regen_from_upgrades + shield_regen_from_skills,
        defensive_identity=st.defensive_identity,
        ship_class_category=st.ship_class_category,
    )
