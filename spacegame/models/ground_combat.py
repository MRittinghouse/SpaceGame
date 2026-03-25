"""Ground combat 'Dice & Grit' system.

Fast, dice-driven combat that resolves on the exploration grid.
Exchange-based rounds: 1d6 + modifier vs 1d6 + modifier.
Supports fight, retreat, and talk actions with special mechanics
like crits, momentum, ambush, and outnumbered penalties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.attributes import AttributeSheet
    from spacegame.models.ground_crew import GroundCrewBonuses
    from spacegame.models.progression import PlayerProgression


class CombatAction(Enum):
    """Player action choices during ground combat."""

    FIGHT = "fight"
    RETREAT = "retreat"
    TALK = "talk"


class CombatOutcome(Enum):
    """Result of a ground combat encounter."""

    IN_PROGRESS = "in_progress"
    VICTORY = "victory"
    DEFEAT = "defeat"
    RETREATED = "retreated"
    TALKED = "talked"


class SocialSkillType(Enum):
    """Social skills usable in talk attempts."""

    PERSUASION = "persuasion"
    INTIMIDATION = "intimidation"
    OBSERVATION = "observation"


@dataclass
class ExchangeResult:
    """Outcome of a single combat exchange."""

    player_damage: int = 0
    enemy_damage: int = 0
    player_crit: bool = False
    enemy_crit: bool = False
    enemy_staggers: bool = False


@dataclass
class GroundCombatantStats:
    """Combat stats for a player or enemy combatant.

    For enemies, talk_difficulty and is_automated control the talk mechanic.
    """

    hp: int
    max_hp: int
    attack_mod: int = 0
    defense_mod: int = 0
    shield: int = 0
    rerolls: int = 0
    talk_difficulty: Optional[int] = None
    name: str = ""
    is_automated: bool = False

    @property
    def is_defeated(self) -> bool:
        """Whether this combatant has been defeated."""
        return self.hp <= 0

    @property
    def is_below_quarter_hp(self) -> bool:
        """Whether HP is below 25% of max."""
        return self.hp < self.max_hp * 0.25

    def take_damage(self, amount: int) -> int:
        """Apply damage, shields absorb first.

        Args:
            amount: Raw damage to apply.

        Returns:
            Actual HP damage taken (after shield absorption).
        """
        if amount <= 0:
            return 0

        # Shield absorbs first
        if self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed

        hp_damage = min(self.hp, amount)
        self.hp = max(0, self.hp - amount)
        return hp_damage

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack_mod": self.attack_mod,
            "defense_mod": self.defense_mod,
            "shield": self.shield,
            "rerolls": self.rerolls,
            "talk_difficulty": self.talk_difficulty,
            "name": self.name,
            "is_automated": self.is_automated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundCombatantStats:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with combatant fields.

        Returns:
            GroundCombatantStats instance.
        """
        return cls(
            hp=data["hp"],
            max_hp=data["max_hp"],
            attack_mod=data.get("attack_mod", 0),
            defense_mod=data.get("defense_mod", 0),
            shield=data.get("shield", 0),
            rerolls=data.get("rerolls", 0),
            talk_difficulty=data.get("talk_difficulty"),
            name=data.get("name", ""),
            is_automated=data.get("is_automated", False),
        )


class GroundCombatEngine:
    """Static methods for resolving combat exchanges."""

    @staticmethod
    def resolve_exchange(
        player_roll: int,
        player_mod: int,
        enemy_roll: int,
        enemy_mod: int,
    ) -> ExchangeResult:
        """Resolve a single exchange between player and enemy.

        Args:
            player_roll: Player's d6 roll (1-6).
            player_mod: Player's total attack modifier.
            enemy_roll: Enemy's d6 roll (1-6).
            enemy_mod: Enemy's total defense modifier.

        Returns:
            ExchangeResult with damage and crit info.
        """
        player_crit = player_roll == 6
        enemy_crit = enemy_roll == 6

        player_total = player_roll + player_mod
        enemy_total = enemy_roll + enemy_mod

        if player_total > enemy_total:
            raw_damage = player_total - enemy_total
            enemy_damage = raw_damage * 2 if player_crit else raw_damage
            player_damage = 0
        elif enemy_total > player_total:
            raw_damage = enemy_total - player_total
            player_damage = raw_damage * 2 if enemy_crit else raw_damage
            enemy_damage = 0
        else:
            # Tie — 1 damage to both
            player_damage = 2 if enemy_crit else 1
            enemy_damage = 2 if player_crit else 1

        return ExchangeResult(
            player_damage=player_damage,
            enemy_damage=enemy_damage,
            player_crit=player_crit,
            enemy_crit=enemy_crit,
            enemy_staggers=player_crit and enemy_damage > 0,
        )


@dataclass
class GroundCombatState:
    """Full state for an active ground combat encounter.

    Tracks combatants, round progress, special mechanics, and outcome.
    """

    player: GroundCombatantStats
    enemies: list[GroundCombatantStats] = field(default_factory=list)
    round_number: int = 0
    target_index: int = 0
    outcome: CombatOutcome = CombatOutcome.IN_PROGRESS
    consecutive_wins: int = 0
    enemies_defeated_count: int = 0

    # Special mechanic flags
    is_ambush: bool = False
    is_disadvantaged: bool = False
    can_retreat: bool = True
    has_last_stand: bool = False
    has_intimidating_presence: bool = False
    has_analyze_weakness: bool = False
    _analyze_weakness_used: bool = field(default=False, init=False)

    # Track used social skills (can't reuse same skill)
    used_social_skills: set[SocialSkillType] = field(default_factory=set)

    # Internal tracking
    _first_exchange: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        """Ensure target index points to a living enemy."""
        self._snap_target_to_living()

    @property
    def outnumbered_penalty(self) -> int:
        """Penalty for facing multiple enemies (-1 per enemy beyond first)."""
        alive = sum(1 for e in self.enemies if not e.is_defeated)
        return max(0, alive - 1)

    @property
    def momentum_bonus(self) -> int:
        """Attack bonus from consecutive exchange wins."""
        return 2 if self.consecutive_wins >= 2 else 0

    @property
    def last_stand_bonus(self) -> int:
        """Bonus when below 25% HP with Last Stand skill."""
        if self.has_last_stand and self.player.is_below_quarter_hp:
            return 3
        return 0

    @property
    def intimidating_presence_debuff(self) -> int:
        """Enemy roll penalty on first exchange with Intimidating Presence."""
        if self.has_intimidating_presence and self._first_exchange:
            return 2
        return 0

    @property
    def can_analyze_weakness(self) -> bool:
        """Whether Priya's analyze weakness is available."""
        return self.has_analyze_weakness and not self._analyze_weakness_used

    def use_analyze_weakness(self) -> int:
        """Use Priya's analyze weakness ability.

        Returns:
            Attack bonus (3) if available, 0 otherwise.
        """
        if not self.can_analyze_weakness:
            return 0
        self._analyze_weakness_used = True
        return 3

    @property
    def can_reroll(self) -> bool:
        """Whether the player has re-rolls available."""
        return self.player.rerolls > 0

    def use_reroll(self) -> None:
        """Consume one re-roll."""
        if self.player.rerolls > 0:
            self.player.rerolls -= 1

    def record_exchange_outcome(self, player_won: bool) -> None:
        """Update momentum tracking after an exchange.

        Args:
            player_won: Whether the player won this exchange.
        """
        if player_won:
            self.consecutive_wins += 1
        else:
            self.consecutive_wins = 0

    def cycle_target(self) -> None:
        """Cycle to the next living enemy target."""
        if not self.enemies:
            return
        start = self.target_index
        for _ in range(len(self.enemies)):
            self.target_index = (self.target_index + 1) % len(self.enemies)
            if not self.enemies[self.target_index].is_defeated:
                return
        self.target_index = start

    def _snap_target_to_living(self) -> None:
        """Ensure target index points to a living enemy."""
        if not self.enemies:
            return
        if not self.enemies[self.target_index].is_defeated:
            return
        # Find first living enemy
        for i, enemy in enumerate(self.enemies):
            if not enemy.is_defeated:
                self.target_index = i
                return

    def execute_fight(
        self, player_roll: int, enemy_roll: int, extra_attack_mod: int = 0
    ) -> ExchangeResult:
        """Execute a fight exchange against the targeted enemy.

        Args:
            player_roll: Player's d6 roll (1-6).
            enemy_roll: Enemy's d6 roll (1-6).
            extra_attack_mod: One-time attack bonus (e.g. analyze weakness).

        Returns:
            ExchangeResult with damage dealt.
        """
        enemy = self.enemies[self.target_index]

        # Calculate player modifiers
        player_mod = self.player.attack_mod + extra_attack_mod
        player_mod -= self.outnumbered_penalty
        player_mod += self.momentum_bonus
        player_mod += self.last_stand_bonus

        # Calculate enemy modifiers
        enemy_mod = enemy.defense_mod
        enemy_mod -= self.intimidating_presence_debuff

        # Ambush: +3 attack, enemy doesn't roll
        if self.is_ambush and self._first_exchange:
            player_mod += 3
            enemy_roll = 0
            enemy_mod = 0

        # Disadvantaged: -2 on first exchange
        if self.is_disadvantaged and self._first_exchange:
            player_mod -= 2

        result = GroundCombatEngine.resolve_exchange(player_roll, player_mod, enemy_roll, enemy_mod)

        # Apply damage
        if result.enemy_damage > 0:
            enemy.take_damage(result.enemy_damage)
        if result.player_damage > 0:
            self.player.take_damage(result.player_damage)

        # Track momentum
        self.record_exchange_outcome(result.enemy_damage > result.player_damage)

        # Track defeated enemies
        if enemy.is_defeated:
            self.enemies_defeated_count += 1

        # First exchange consumed
        self._first_exchange = False
        self.round_number += 1

        # Check outcome
        self._check_outcome()
        self._snap_target_to_living()

        return result

    def attempt_retreat(
        self,
        roll: int,
        retreat_mod: int,
        free_attack_rolls: Optional[list[int]] = None,
    ) -> bool:
        """Attempt to retreat from combat.

        Args:
            roll: Player's d6 roll for retreat.
            retreat_mod: Total retreat modifier.
            free_attack_rolls: Enemy attack rolls if retreat fails.

        Returns:
            True if retreat succeeded.
        """
        if not self.can_retreat:
            return False

        alive_count = sum(1 for e in self.enemies if not e.is_defeated)
        difficulty = 4 + alive_count
        total = roll + retreat_mod

        if total >= difficulty:
            self.outcome = CombatOutcome.RETREATED
            return True

        # Failed — enemies get free attacks
        if free_attack_rolls:
            self._apply_free_attacks(free_attack_rolls)

        self._check_outcome()
        return False

    def can_use_social_skill(self, skill_type: SocialSkillType) -> bool:
        """Check if a social skill can still be used.

        Args:
            skill_type: The social skill to check.

        Returns:
            True if the skill hasn't been used yet.
        """
        return skill_type not in self.used_social_skills

    def get_intimidation_bonus(self) -> int:
        """Get the intimidation bonus from defeated enemies.

        Returns:
            +2 if at least one enemy has been defeated, else 0.
        """
        return 2 if self.enemies_defeated_count > 0 else 0

    def attempt_talk(
        self,
        roll: int,
        social_mod: int,
        skill_type: SocialSkillType,
        free_attack_rolls: Optional[list[int]] = None,
    ) -> bool:
        """Attempt to talk your way out of combat.

        Args:
            roll: Player's d6 roll.
            social_mod: Total social skill modifier.
            skill_type: Which social skill is being used.
            free_attack_rolls: Enemy attack rolls if talk fails.

        Returns:
            True if talk succeeded.
        """
        # Check for automated enemies — all must be non-automated
        all_automated = all(e.is_automated for e in self.enemies if not e.is_defeated)
        if all_automated:
            return False

        # Get highest talk difficulty among living enemies
        difficulties = [
            e.talk_difficulty
            for e in self.enemies
            if not e.is_defeated and e.talk_difficulty is not None
        ]
        if not difficulties:
            return False

        difficulty = max(difficulties)
        total = roll + social_mod

        # Add intimidation bonus if using intimidation
        if skill_type == SocialSkillType.INTIMIDATION:
            total += self.get_intimidation_bonus()

        # Record skill usage (regardless of outcome)
        self.used_social_skills.add(skill_type)

        if total >= difficulty:
            self.outcome = CombatOutcome.TALKED
            return True

        # Failed — enemies get free attacks
        if free_attack_rolls:
            self._apply_free_attacks(free_attack_rolls)

        self._check_outcome()
        return False

    def _apply_free_attacks(self, attack_rolls: list[int]) -> None:
        """Apply free attacks from all living enemies.

        Args:
            attack_rolls: One roll per living enemy.
        """
        living = [e for e in self.enemies if not e.is_defeated]
        for i, enemy in enumerate(living):
            if i >= len(attack_rolls):
                break
            damage = max(1, attack_rolls[i] + enemy.attack_mod - 3)
            self.player.take_damage(damage)

    def _check_outcome(self) -> None:
        """Update outcome based on current state."""
        if self.outcome != CombatOutcome.IN_PROGRESS:
            return

        if self.player.is_defeated:
            self.outcome = CombatOutcome.DEFEAT
            return

        if all(e.is_defeated for e in self.enemies):
            self.outcome = CombatOutcome.VICTORY

    def to_dict(self) -> dict:
        """Serialize combat state to dictionary."""
        return {
            "player": self.player.to_dict(),
            "enemies": [e.to_dict() for e in self.enemies],
            "round_number": self.round_number,
            "target_index": self.target_index,
            "outcome": self.outcome.value,
            "consecutive_wins": self.consecutive_wins,
            "enemies_defeated_count": self.enemies_defeated_count,
            "is_ambush": self.is_ambush,
            "is_disadvantaged": self.is_disadvantaged,
            "can_retreat": self.can_retreat,
            "has_last_stand": self.has_last_stand,
            "has_intimidating_presence": self.has_intimidating_presence,
            "has_analyze_weakness": self.has_analyze_weakness,
            "analyze_weakness_used": self._analyze_weakness_used,
            "used_social_skills": [s.value for s in self.used_social_skills],
            "first_exchange": self._first_exchange,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundCombatState:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with combat state fields.

        Returns:
            GroundCombatState instance.
        """
        state = cls(
            player=GroundCombatantStats.from_dict(data["player"]),
            enemies=[GroundCombatantStats.from_dict(e) for e in data["enemies"]],
            round_number=data.get("round_number", 0),
            target_index=data.get("target_index", 0),
            outcome=CombatOutcome(data.get("outcome", "in_progress")),
            consecutive_wins=data.get("consecutive_wins", 0),
            enemies_defeated_count=data.get("enemies_defeated_count", 0),
            is_ambush=data.get("is_ambush", False),
            is_disadvantaged=data.get("is_disadvantaged", False),
            can_retreat=data.get("can_retreat", True),
            has_last_stand=data.get("has_last_stand", False),
            has_intimidating_presence=data.get("has_intimidating_presence", False),
            has_analyze_weakness=data.get("has_analyze_weakness", False),
            used_social_skills={SocialSkillType(s) for s in data.get("used_social_skills", [])},
        )
        state._first_exchange = data.get("first_exchange", True)
        state._analyze_weakness_used = data.get("analyze_weakness_used", False)
        return state


# ---------------------------------------------------------------------------
# Enemy type templates (from spec Section 5.4)
# ---------------------------------------------------------------------------

GROUND_ENEMY_TEMPLATES: dict[str, dict] = {
    "guild_security": {
        "name": "Guild Security",
        "hp": 4,
        "attack": 2,
        "defense": 2,
        "talk": 6,
        "loot_credits": 30,
    },
    "union_worker": {
        "name": "Union Worker",
        "hp": 3,
        "attack": 1,
        "defense": 0,
        "talk": 4,
        "loot_credits": 15,
    },
    "pirate_thug": {
        "name": "Pirate Thug",
        "hp": 5,
        "attack": 3,
        "defense": 0,
        "talk": 8,
        "loot_credits": 45,
    },
    "collective_drone": {
        "name": "Collective Drone",
        "hp": 3,
        "attack": 1,
        "defense": 3,
        "talk": None,
        "automated": True,
        "loot_credits": 10,
    },
    "alliance_scrapper": {
        "name": "Alliance Scrapper",
        "hp": 4,
        "attack": 2,
        "defense": 1,
        "talk": 5,
        "loot_credits": 25,
    },
    "elite_guard": {
        "name": "Elite Guard",
        "hp": 6,
        "attack": 3,
        "defense": 3,
        "talk": 9,
        "loot_credits": 60,
    },
    "station_sentry": {
        "name": "Station Sentry",
        "hp": 2,
        "attack": 0,
        "defense": 1,
        "talk": None,
        "automated": True,
        "loot_credits": 5,
    },
    "crimson_enforcer": {
        "name": "Crimson Enforcer",
        "hp": 5,
        "attack": 3,
        "defense": 1,
        "talk": 7,
        "loot_credits": 50,
    },
}


def make_enemy_from_template(template_id: str) -> GroundCombatantStats:
    """Create enemy combat stats from a template ID.

    Args:
        template_id: Key into GROUND_ENEMY_TEMPLATES.

    Returns:
        GroundCombatantStats for the enemy.

    Raises:
        KeyError: If template_id is not found.
    """
    t = GROUND_ENEMY_TEMPLATES[template_id]
    return GroundCombatantStats(
        hp=t["hp"],
        max_hp=t["hp"],
        attack_mod=t["attack"],
        defense_mod=t["defense"],
        talk_difficulty=t.get("talk"),
        name=t["name"],
        is_automated=t.get("automated", False),
    )


def build_player_ground_combat_stats(
    attributes: Optional[AttributeSheet] = None,
    progression: Optional[PlayerProgression] = None,
    crew_bonuses: Optional[GroundCrewBonuses] = None,
) -> GroundCombatantStats:
    """Build player ground combat stats from attributes, skills, and crew.

    Integrates:
    - RES: +1 HP per 2 pts, +1 defense per 2 pts
    - ACU: +1 attack per 2 pts
    - Scrapper skill: +1 attack
    - Tough Hide skill: +2 HP
    - Quick Reflexes skill: +1 re-roll
    - Veteran skill: +1 re-roll, +1 HP
    - Crew bonuses are tracked separately (retreat, talk, analyze) on CombatState

    Args:
        attributes: Player's attribute sheet.
        progression: Player's progression (skill tree).
        crew_bonuses: Pre-computed crew and attribute bonuses.

    Returns:
        GroundCombatantStats for the player.
    """
    from spacegame.config import GROUND_COMBAT_BASE_HP
    from spacegame.models.ground_crew import GroundCrewBonuses as _GCB

    if crew_bonuses is None:
        crew_bonuses = _GCB()

    base_hp = GROUND_COMBAT_BASE_HP
    attack_mod = 0
    defense_mod = 0
    rerolls = 0

    if attributes:
        acu = attributes.get_value("acu")
        res = attributes.get_value("res")
        base_hp += res // 2
        attack_mod += acu // 2
        defense_mod += res // 2

    if progression:
        attack_mod += int(progression.get_bonus("ground_attack_bonus"))
        base_hp += int(progression.get_bonus("ground_hp_bonus"))
        rerolls += int(progression.get_bonus("ground_reroll"))
        # Veteran adds +1 re-roll and +1 HP
        if progression.get_bonus("ground_veteran") > 0:
            rerolls += 1
            base_hp += 1

    return GroundCombatantStats(
        hp=base_hp,
        max_hp=base_hp,
        attack_mod=attack_mod,
        defense_mod=defense_mod,
        rerolls=rerolls,
    )
