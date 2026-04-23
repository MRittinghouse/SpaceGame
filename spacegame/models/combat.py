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

    KINETIC = "kinetic"  # Pure damage, no secondary effect
    PLASMA = "plasma"  # 66% upfront + stacking Burn DoT
    ION = "ion"  # 150% to shields, 75% to hull
    CRYO = "cryo"  # 85% damage + Chill stacks → Frozen at 3
    VOLTAIC = "voltaic"  # 85% damage + Suppressed stacks (reduce enemy damage)


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
    BURN = "burn"  # Plasma DoT: X damage per turn, stacks to 3
    CHILL = "chill"  # Cryo: stacks to 3, then Frozen (lose turn)
    SUPPRESSED = "suppressed"  # Voltaic: -12% damage per stack, stacks to 3
    CLEANSE = "cleanse"  # Remove all negative effects from self
    ABSORB = "absorb"  # Absorb next incoming hit completely (1 charge)
    SPAWN_REINFORCEMENT = "spawn_reinforcement"  # Append an enemy to state.enemies (Tier 3.E)


class EffectTarget(Enum):
    """Who a combat effect targets.

    ALLY (added QA Pass 5 Tier 3.D) routes to a teammate of the caster:
    for an enemy attacker, another living enemy; for the player, the player
    itself (since the player has no allies in the current combat model —
    crew are part of the PlayerCombatState). Combat engine picks the
    lowest-HP ally when multiple candidates exist.
    """

    SELF = "self"
    ENEMY = "enemy"
    ALLY = "ally"


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

    ``metadata`` (Tier 3.E) is a free-form dict for effect-specific
    payload that doesn't fit the scalar value/duration fields — e.g.,
    SPAWN_REINFORCEMENT uses ``metadata["template_id"]`` to identify
    which enemy to spawn.
    """

    type: EffectType
    value: float
    duration: int = 0
    target: EffectTarget = EffectTarget.ENEMY
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result: dict = {
            "type": self.type.value,
            "value": self.value,
            "duration": self.duration,
            "target": self.target.value,
        }
        # Only emit metadata when non-empty so existing JSON stays minimal.
        if self.metadata:
            result["metadata"] = dict(self.metadata)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "CombatEffect":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with type, value, and optional duration/target/metadata.

        Returns:
            CombatEffect instance.
        """
        return cls(
            type=EffectType(data["type"]),
            value=data["value"],
            duration=data.get("duration", 0),
            target=EffectTarget(data.get("target", "enemy")),
            metadata=dict(data.get("metadata", {})),
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
    category: str = ""  # Slot type: "weapon", "defense", "utility", etc.
    slot_key: str = ""  # Unique key per equipped slot (e.g., "phantom_cloak_3")

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
    hp_threshold: (
        float  # Phase activates when total HP ratio drops below this (1.0 = always active)
    )
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
    sprite_rotation: int = (
        0  # Degrees to rotate sprite (fix orientation, e.g., -90 for upward-facing)
    )
    trophy_drop: str = ""  # Shape/material ID dropped on first kill
    # Optional hand-authored ShipBuild (Combat C4 §11.3). When present,
    # EnemyCompositeProvider loads this build via ShipBuild.from_dict
    # instead of falling back to the procedural generator. Intended for
    # marquee bosses whose silhouettes deserve bespoke authoring.
    # Format matches ``ShipBuild.to_dict()`` output.
    composite_build: Optional[dict] = None
    # Targetable subsystems (Combat C4 §11.2). Tags drawn from the
    # canonical 6-palette in ``models/enemy_subsystems.py``. Regular
    # enemies get 1-2; bosses/elites get 3-4. Empty list = enemy has
    # no subsystem layer (legacy combat feel).
    targetable_subsystems: list[str] = field(default_factory=list)


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
    # Subsystem runtime state (Combat C4 §11.2). ``subsystem_hp`` holds
    # remaining HP per targetable tag — populated from the template at
    # :meth:`from_template`. ``subsystems_destroyed`` is the accumulating
    # set of destroyed tags (never cleared — destruction is permanent
    # for the encounter). ``engines_just_destroyed`` is a transient flag
    # consumed by the turn-skip path on the next enemy turn.
    subsystem_hp: dict[str, int] = field(default_factory=dict)
    subsystems_destroyed: set[str] = field(default_factory=set)
    engines_just_destroyed: bool = False
    # Which subsystem the player currently has focused on this enemy.
    # None = no tactical focus (attacks chip hull only, no subsystem
    # damage). Cleared when the target is no longer addressable.
    focused_subsystem: Optional[str] = None

    @classmethod
    def from_template(cls, template: EnemyShipTemplate) -> "EnemyShip":
        """Create a combat-ready enemy ship from a template.

        For boss enemies, applies the HP multiplier to hull and shields.
        Also initializes subsystem HP for every ``targetable_subsystems``
        entry declared on the template.

        Args:
            template: The enemy ship template to instantiate.

        Returns:
            EnemyShip with full health/energy and no active effects.
        """
        from spacegame.models.enemy_subsystems import subsystem_max_hp

        mult = template.boss_hp_multiplier if template.is_boss else 1
        max_hull = template.hull * mult
        subsystem_hp = {
            tag: subsystem_max_hp(tag, max_hull)
            for tag in template.targetable_subsystems
        }
        return cls(
            template=template,
            current_hull=max_hull,
            current_shields=template.shields * mult,
            current_energy=template.energy,
            active_effects=[],
            cooldowns={},
            subsystem_hp=subsystem_hp,
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

    # ---- Subsystem-aware effective stats (Combat C4 §11.2) ------------------
    # Combat engine reads these in place of raw template values when
    # subsystem destruction should modify behavior. Enemies with no
    # destroyed subsystems see identical values to the template defaults.

    @property
    def effective_evasion(self) -> int:
        """Enemy evasion after subsystem destruction. Engine destroyed → 0."""
        if "engine" in self.subsystems_destroyed:
            return 0
        return self.template.evasion

    @property
    def effective_accuracy(self) -> int:
        """Enemy accuracy after subsystem destruction. Sensor destroyed → -30."""
        accuracy = self.template.accuracy
        if "sensor_array" in self.subsystems_destroyed:
            accuracy -= 30
        return max(0, accuracy)

    @property
    def damage_multiplier(self) -> float:
        """Outgoing damage multiplier. Weapon array destroyed → 0.60."""
        if "weapon_array" in self.subsystems_destroyed:
            return 0.60
        return 1.0

    @property
    def can_flee(self) -> bool:
        """True unless engines have been destroyed."""
        return "engine" not in self.subsystems_destroyed

    @property
    def can_regen_shields(self) -> bool:
        """True unless shield generator has been destroyed."""
        return "shield_generator" not in self.subsystems_destroyed

    @property
    def can_regen_energy(self) -> bool:
        """True unless reactor has been destroyed."""
        return "reactor" not in self.subsystems_destroyed

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
                messages.append(f"{effect.type.value} effect expired on {self.template.name}")
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
    # Module combat state (Shipbuilder Upgrade Phase 9)
    module_states: list = field(default_factory=list)  # list[ModuleCombatState]
    _ship_build: object = field(default=None, repr=False)  # ShipBuild reference
    _module_catalog: dict = field(default_factory=dict, repr=False)
    # Legendary module state (Shipbuilder Upgrade — Boss Drops)
    _legendary: object = field(default=None, repr=False)  # LegendaryState
    # Dual tech state (B8.2 / B8.3) — flags set on activation, cleared at
    # end of turn or end of combat depending on the tech.
    fire_at_will_active: bool = False
    crew_sync_used: bool = False
    # Total Commitment (B8.3): next N incoming hull hits convert to armor,
    # capped by total_commitment_armor_cap.
    total_commitment_hits_remaining: int = 0
    total_commitment_armor_gained: int = 0
    # Daring Gambit (B8.3): counter-on-dodge for N more rounds.
    daring_gambit_turns: int = 0
    # Crew Sync (B8.3): player attacks this turn ignore defender armor.
    armor_pierce_active: bool = False
    # Dual tech moves (B8.4): coordinated abilities injected at combat start
    # based on crew loyalty. Rendered in the combat view's utility tab.
    dual_tech_moves: list[CombatMove] = field(default_factory=list)
    # Dialogue flags reference (B8.4 tail): used to gate first-use
    # cinematic reveals for dual techs. The engine mutates this dict
    # via check_and_mark_reveal so reveals persist across combats.
    # An ephemeral dict is fine for tests / reveals that don't persist.
    dialogue_flags: dict[str, bool] = field(default_factory=dict)

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
    # Skill tree reference for per-round bonus checks (S2a)
    progression: object = field(default=None, repr=False)

    # ----------------------------------------------------------------------
    # CE-3: Combat complications
    # ----------------------------------------------------------------------
    # Complication ids that have fired this combat — prevents re-firing
    # once-shot complications across multiple rounds.
    fired_complication_ids: set[str] = field(default_factory=set)
    # Environmental modifiers applied by ``environmental`` effect handlers.
    # Default values mean "no modifier active"; complications multiply /
    # add to these and the combat engine reads them during resolution.
    shield_regen_multiplier: float = 1.0
    player_evasion_modifier: int = 0  # added to effective evasion
    enemy_accuracy_multiplier: float = 1.0
    # Narrative flags set by ``narration`` effect handlers (morale_shift,
    # third_party_hail). Not save-persisted; purely informational for
    # per-combat UI.
    complication_flags: set[str] = field(default_factory=set)

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
    dialogue_flags: Optional[dict[str, bool]] = None,
) -> PlayerCombatState:
    """Build PlayerCombatState from existing game objects.

    If the ship has a ShipBuild with computed stats, those are used
    instead of ShipType stats. Otherwise falls back to the legacy
    ShipType + UpgradeManager path.

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

    # === Build-derived stats path (Shipyard Overhaul Phase A2) ===
    # When a ShipBuild is active, use its computed stats instead of ShipType
    from spacegame.models.ship_build import ComputedShipStats

    cs = getattr(ship, "computed_stats", None)
    if isinstance(cs, ComputedShipStats):
        crew_moves: list[CombatMove] = []
        if crew_roster:
            for template, _state in crew_roster.get_recruited_members():
                if template.id in crew_combat_moves:
                    entry = crew_combat_moves[template.id]
                    if isinstance(entry, list):
                        crew_moves.extend(entry)
                    else:
                        crew_moves.append(entry)

        flee_bonus = cs.flee_bonus
        if player_level < EARLY_GAME_LEVEL:
            flee_bonus += EARLY_GAME_FLEE_BONUS

        # Initialize combat states and extract equipment moves.
        # Two paths: new slot+part model, or legacy module model.
        module_states_list = []
        module_catalog_ref = {}
        build_ref = None
        legendary_state = None
        equipment_moves_list = []

        # === NEW: Slot+Part path ===
        if ship.build and ship.build.placed_slots:
            try:
                from spacegame.data_loader import get_data_loader
                from spacegame.models.module_combat import (
                    get_slot_equipment_moves,
                    init_slot_combat_states,
                )

                dl = get_data_loader()
                slot_defs = getattr(dl, "slot_definitions", {})
                parts_cat = getattr(dl, "ship_parts", {})

                module_states_list = init_slot_combat_states(ship.build, slot_defs)
                build_ref = ship.build

                # Extract combat moves from equipped parts
                from spacegame.utils.logger import logger as _combat_log

                equipped_count = sum(1 for ps in ship.build.placed_slots if ps.equipped_part_id)
                _combat_log.info(
                    f"Combat init: {len(ship.build.placed_slots)} slots, "
                    f"{equipped_count} equipped, {len(slot_defs)} slot_defs, "
                    f"{len(parts_cat)} parts in catalog"
                )
                for ps in ship.build.placed_slots:
                    sdef = slot_defs.get(ps.slot_def_id)
                    stype = sdef.slot_type if sdef else "?"
                    if ps.equipped_part_id:
                        part = parts_cat.get(ps.equipped_part_id)
                        has_cm = bool(part and part.combat_move) if part else False
                        _combat_log.info(
                            f"  Slot {ps.slot_def_id} ({stype}): "
                            f"equipped={ps.equipped_part_id} "
                            f"part_found={part is not None} "
                            f"combat_move={has_cm}"
                        )
                    else:
                        _combat_log.info(f"  Slot {ps.slot_def_id} ({stype}): EMPTY")
                slot_moves = get_slot_equipment_moves(ship.build, slot_defs, parts_cat)
                _combat_log.info(f"Combat moves extracted: {len(slot_moves)} from slots")
                for sm in slot_moves:
                    cm = sm.get("combat_move")
                    if cm:
                        try:
                            move = CombatMove.from_dict(cm)
                            move.category = sm.get("slot_type", "weapon")
                            slot_idx = sm.get("slot_idx", 0)
                            move.slot_key = f"{move.id}_{slot_idx}"
                            mark = sm.get("mark", 1)
                            if mark > 1:
                                mark_mult = {1: 1.0, 2: 1.25, 3: 1.50}.get(mark, 1.0)
                                for eff in move.effects:
                                    if eff.type == EffectType.DAMAGE:
                                        eff.value = eff.value * mark_mult
                            equipment_moves_list.append(move)
                        except Exception as move_err:
                            _combat_log.warning(
                                f"Skipping move from {sm.get('equipped_part_id')}: {move_err}"
                            )
            except Exception as e:
                from spacegame.utils.logger import logger

                logger.error(f"Failed to extract slot equipment moves: {e}")

            # Legendary effects from equipped parts
            try:
                for ps in ship.build.placed_slots:
                    if ps.equipped_part_id:
                        part = parts_cat.get(ps.equipped_part_id)
                        if part and part.provides:
                            # Check for legendary ability keys in provides
                            if any(
                                k in part.provides
                                for k in (
                                    "chain_fire_chance",
                                    "void_absorption_rate",
                                    "heat_hardening_per_hit",
                                    "cooldown_reduction",
                                    "phase_shift_interval",
                                )
                            ):
                                from spacegame.models.legendary_effects import (
                                    LegendaryState,
                                )

                                if legendary_state is None:
                                    legendary_state = LegendaryState()
                                p = part.provides
                                legendary_state.chain_fire_chance = max(
                                    legendary_state.chain_fire_chance,
                                    p.get("chain_fire_chance", 0),
                                )
                                legendary_state.void_absorption_rate = max(
                                    legendary_state.void_absorption_rate,
                                    p.get("void_absorption_rate", 0),
                                )
                                legendary_state.heat_hardening_per_hit = max(
                                    legendary_state.heat_hardening_per_hit,
                                    p.get("heat_hardening_per_hit", 0),
                                )
                                legendary_state.cooldown_reduction = max(
                                    legendary_state.cooldown_reduction,
                                    p.get("cooldown_reduction", 0),
                                )
                                legendary_state.phase_shift_interval = max(
                                    legendary_state.phase_shift_interval,
                                    p.get("phase_shift_interval", 0),
                                )
            except Exception as e:
                from spacegame.utils.logger import logger

                logger.error(f"Failed to extract legendary effects: {e}")

        # Fallback: use old system's combat_moves if no equipment found
        if not equipment_moves_list:
            equipment_moves_list = cs.combat_moves
            from spacegame.utils.logger import logger as _combat_log

            _combat_log.warning(
                f"No equipment moves found — fell back to cs.combat_moves "
                f"({len(cs.combat_moves)} moves)"
            )
        else:
            from spacegame.utils.logger import logger as _combat_log

            _combat_log.info(f"Final equipment moves: {[m.name for m in equipment_moves_list]}")

        # Apply skill tree bonuses (S2a — build path was missing these)
        skill_evasion = 0
        skill_armor = 0
        skill_shield_regen = 0
        skill_flee = 0
        hull_bonus_pct = 0.0
        if progression and hasattr(progression, "get_bonus"):
            skill_armor = int(progression.get_bonus("armor_bonus"))
            skill_shield_regen = int(progression.get_bonus("shield_regen_bonus"))
            skill_evasion = int(progression.get_bonus("afterburner_bonus"))
            skill_evasion += int(progression.get_bonus("dodge_chance") * 100)
            skill_flee = int(progression.get_bonus("flee_bonus") * 100)
            hull_bonus_pct = progression.get_bonus("hull_hp_bonus")
        bonus_hull = int(cs.hull * hull_bonus_pct)

        _state_result = PlayerCombatState(
            hull=ship.current_hull + bonus_hull,
            max_hull=cs.hull + bonus_hull,
            shields=ship.current_shields,
            max_shields=cs.shields,
            energy=cs.energy_pool,
            max_energy=cs.energy_pool,
            energy_regen=cs.energy_regen,
            speed=cs.speed,
            evasion=cs.evasion + skill_evasion,
            accuracy=cs.accuracy,
            equipment_moves=equipment_moves_list,
            crew_moves=crew_moves,
            active_effects=[],
            cooldowns={},
            flee_bonus=flee_bonus + skill_flee,
            armor=cs.armor + skill_armor,
            shield_regen=cs.shield_regen + skill_shield_regen,
            defensive_identity=cs.defensive_identity or "",
            ship_class_category=ship.ship_type.ship_class_category,
            module_states=module_states_list,
            _ship_build=build_ref,
            _module_catalog=module_catalog_ref,
            _legendary=legendary_state,
        )
        # B8.4: expose available dual techs so the combat view can render them.
        if crew_roster is not None:
            try:
                from spacegame.models.dual_tech import inject_available_dual_techs

                inject_available_dual_techs(_state_result, crew_roster)
            except Exception:
                pass
        # B8.4 tail: attach dialogue_flags by reference so first-use
        # reveal marks persist on the Player's dict.
        if dialogue_flags is not None:
            _state_result.dialogue_flags = dialogue_flags
        return _state_result

    # === Legacy ShipType path (backward compat) ===
    #
    # SAFETY NET — not dead code. Audited 2026-04-21 (QA Pass 5 Tier 2.4).
    # Reached when ``ship.computed_stats`` is None, which happens in:
    #
    #   1. New game where ``generate_preset_from_ship_type`` raises during
    #      ``Game.new_game`` (the try/except at engine/game.py:407-411
    #      intentionally falls through to preserve playability).
    #   2. Save-load from a corrupted file: neither ``"build"`` nor a
    #      recoverable ``ship_type_id`` (save_manager.py:770-787).
    #   3. Direct Ship construction without set_build (chiefly in tests;
    #      QA Pass 3.5 Scenario C explicitly exercises this path to verify
    #      skill bonuses apply here too — see CLAUDE.md "common pitfalls").
    #
    # Removal requires: (a) exception-free preset generation for every
    # ship_type in production data, (b) save-migration test covering the
    # malformed-save case, (c) test refactor to always set_build. Until
    # all three land, this path must stay — removing it would turn any
    # of the above into a crash.
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

    # Aggregate skill tree bonuses
    armor_from_skills = 0
    shield_regen_from_skills = 0
    evasion_from_skills = 0
    flee_from_skills = 0
    if progression and hasattr(progression, "get_bonus"):
        armor_from_skills = int(progression.get_bonus("armor_bonus"))
        shield_regen_from_skills = int(progression.get_bonus("shield_regen_bonus"))
        # Afterburner skill gives evasion
        afterburner = int(progression.get_bonus("afterburner_bonus"))
        evasion_from_skills = afterburner
        # Dodge chance skill adds evasion (5 per level)
        evasion_from_skills += int(progression.get_bonus("dodge_chance") * 100)
        # Tactical retreat skill gives flee bonus
        flee_from_skills += int(progression.get_bonus("flee_bonus") * 100)

    flee_bonus += flee_from_skills

    # Ghost identity passive: +20% base flee bonus
    if st.defensive_identity == "ghost":
        flee_bonus += 20

    # Hull HP bonus from skills (percentage increase)
    hull_bonus_pct = 0.0
    if progression and hasattr(progression, "get_bonus"):
        hull_bonus_pct = progression.get_bonus("hull_hp_bonus")
    base_hull = st.combat_hull
    bonus_hull = int(base_hull * hull_bonus_pct)

    _legacy_state = PlayerCombatState(
        hull=ship.current_hull + bonus_hull,
        max_hull=base_hull + bonus_hull,
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
    # B8.4: expose available dual techs for the combat view.
    if crew_roster is not None:
        try:
            from spacegame.models.dual_tech import inject_available_dual_techs

            inject_available_dual_techs(_legacy_state, crew_roster)
        except Exception:
            pass
    if dialogue_flags is not None:
        _legacy_state.dialogue_flags = dialogue_flags
    return _legacy_state
