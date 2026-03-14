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

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effects": [e.to_dict() for e in self.effects],
            "energy_cost": self.energy_cost,
            "cooldown": self.cooldown,
            "accuracy_modifier": self.accuracy_modifier,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CombatMove":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with id, name, description, effects, and
                optional energy_cost/cooldown/accuracy_modifier.

        Returns:
            CombatMove instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            effects=[CombatEffect.from_dict(e) for e in data.get("effects", [])],
            energy_cost=data.get("energy_cost", 0),
            cooldown=data.get("cooldown", 0),
            accuracy_modifier=data.get("accuracy_modifier", 0),
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

    @classmethod
    def from_template(cls, template: EnemyShipTemplate) -> "EnemyShip":
        """Create a combat-ready enemy ship from a template.

        Args:
            template: The enemy ship template to instantiate.

        Returns:
            EnemyShip with full health/energy and no active effects.
        """
        return cls(
            template=template,
            current_hull=template.hull,
            current_shields=template.shields,
            current_energy=template.energy,
            active_effects=[],
            cooldowns={},
        )

    @property
    def is_alive(self) -> bool:
        """Whether this enemy still has hull points remaining."""
        return self.current_hull > 0

    @property
    def hull_ratio(self) -> float:
        """Current hull as a fraction of maximum (0.0 to 1.0)."""
        if self.template.hull <= 0:
            return 0.0
        return max(0.0, self.current_hull / self.template.hull)

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
        """Decrement active effect durations and remove expired ones.

        Returns:
            List of human-readable messages about expired effects.
        """
        messages: list[str] = []
        remaining: list[tuple[CombatEffect, int]] = []
        for effect, turns_left in self.active_effects:
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
        """Decrement active effect durations and remove expired ones.

        Returns:
            List of human-readable messages about expired effects.
        """
        messages: list[str] = []
        remaining: list[tuple[CombatEffect, int]] = []
        for effect, turns_left in self.active_effects:
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
    crew_combat_moves: dict[str, CombatMove],
) -> PlayerCombatState:
    """Build PlayerCombatState from existing game objects.

    Pulls base combat stats from ShipType, equipment moves from
    ShipUpgradeManager, and crew moves from the provided mapping.

    Args:
        ship: Player's ship instance (uses current_hull/current_shields).
        upgrade_manager: Installed upgrades (provides equipment combat moves).
        crew_roster: Recruited crew (provides crew move IDs). May be None.
        crew_combat_moves: Mapping of crew template_id to their CombatMove.

    Returns:
        Fully initialized PlayerCombatState.
    """
    st = ship.ship_type

    # Equipment moves from installed upgrades
    equipment_moves = upgrade_manager.get_combat_moves()

    # Crew moves from recruited members
    crew_moves: list[CombatMove] = []
    if crew_roster:
        for template, _state in crew_roster.get_recruited_members():
            if template.id in crew_combat_moves:
                crew_moves.append(crew_combat_moves[template.id])

    return PlayerCombatState(
        hull=ship.current_hull,
        max_hull=st.combat_hull,
        shields=ship.current_shields,
        max_shields=st.combat_shields,
        energy=st.combat_energy,
        max_energy=st.combat_energy,
        energy_regen=st.combat_energy_regen,
        speed=st.combat_speed,
        evasion=st.combat_evasion,
        accuracy=st.combat_accuracy,
        equipment_moves=equipment_moves,
        crew_moves=crew_moves,
        active_effects=[],
        cooldowns={},
        flee_bonus=int(upgrade_manager.get_bonus("flee_bonus")),
    )
