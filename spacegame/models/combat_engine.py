"""Combat engine — resolves turn-based space combat.

All mutable state lives in CombatState. The engine provides methods for
executing player moves, crew moves, enemy turns, fleeing, negotiating,
and end-of-round processing.
"""

from __future__ import annotations

import random
from typing import Optional

from spacegame.models.combat import (
    CombatEffect,
    CombatLogEntry,
    CombatMove,
    CombatResult,
    CombatState,
    EnemyBehavior,
    EnemyShip,
    EffectTarget,
    EffectType,
    PlayerCombatState,
)

# Hit chance bounds
HIT_CHANCE_MIN = 5
HIT_CHANCE_MAX = 95

# Flee formula constants
FLEE_BASE_CHANCE = 30
FLEE_SPEED_FACTOR = 3
FLEE_MIN_CHANCE = 10
FLEE_MAX_CHANCE = 90
FLEE_ACCURACY_PENALTY = 20


class CombatEngine:
    """Resolves turn-based combat. All mutable state lives in CombatState."""

    def __init__(self, state: CombatState, seed: int = 0) -> None:
        self._state = state
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def execute_player_move(
        self, move_id: str, target_idx: int = 0
    ) -> list[CombatLogEntry]:
        """Execute a player equipment or crew move.

        Args:
            move_id: ID of the move to execute.
            target_idx: Index of the enemy to target (for offensive moves).

        Returns:
            List of combat log entries produced.
        """
        player = self._state.player
        move = self._find_player_move(move_id)
        if move is None:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Unknown Move",
                effects_applied=["Move not found"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Check cooldown
        if move_id in player.cooldowns:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action=move.name,
                effects_applied=[f"{move.name} is on cooldown"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Check energy
        if player.energy < move.energy_cost:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action=move.name,
                effects_applied=[f"Not enough energy for {move.name}"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Spend energy
        player.energy -= move.energy_cost

        # Set cooldown
        if move.cooldown > 0:
            player.cooldowns[move_id] = move.cooldown

        # Determine target
        target_idx = min(target_idx, len(self._state.enemies) - 1)
        target_enemy = self._state.enemies[target_idx]

        # Resolve
        return self._resolve_move(
            move, player, target_enemy, "player", player.get_effective_accuracy()
        )

    def execute_crew_moves(
        self, skip_ids: Optional[set[str]] = None
    ) -> list[CombatLogEntry]:
        """Execute all crew combat moves (crew phase).

        Args:
            skip_ids: Set of move IDs to skip.

        Returns:
            List of combat log entries produced.
        """
        if skip_ids is None:
            skip_ids = set()

        all_logs: list[CombatLogEntry] = []
        player = self._state.player
        surviving = self._state.surviving_enemies
        if not surviving:
            return all_logs

        for move in player.crew_moves:
            if move.id in skip_ids:
                continue
            target = surviving[0]
            logs = self._resolve_move(
                move, player, target,
                f"crew:{move.id}", player.get_effective_accuracy(),
            )
            all_logs.extend(logs)
            # Re-check survivors after each move
            surviving = self._state.surviving_enemies
            if not surviving:
                break

        return all_logs

    # ------------------------------------------------------------------
    # Enemy actions
    # ------------------------------------------------------------------

    def execute_enemy_turns(self) -> list[CombatLogEntry]:
        """Execute enemy phase — each surviving enemy takes one action.

        Returns:
            List of combat log entries produced.
        """
        all_logs: list[CombatLogEntry] = []
        for idx, enemy in enumerate(self._state.enemies):
            if not enemy.is_alive or enemy.is_fled:
                continue
            logs = self._resolve_enemy_turn(idx)
            all_logs.extend(logs)
        return all_logs

    def _resolve_enemy_turn(self, enemy_idx: int) -> list[CombatLogEntry]:
        """Resolve a single enemy's turn based on AI behavior."""
        enemy = self._state.enemies[enemy_idx]
        actor = f"enemy:{enemy_idx}"

        # Cowardly behavior: flee when hull is low
        if (
            enemy.template.behavior == EnemyBehavior.COWARDLY
            and enemy.hull_ratio <= enemy.template.flee_threshold
        ):
            enemy.is_fled = True
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor=actor,
                action="Fled",
                effects_applied=[f"{enemy.template.name} fled combat"],
            )
            self._state.combat_log.append(entry)
            return [entry]

        move = self._select_enemy_move(enemy)
        if move is None:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor=actor,
                action="No Action",
                effects_applied=["No available moves"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Spend energy
        enemy.current_energy -= move.energy_cost
        if move.cooldown > 0:
            enemy.cooldowns[move.id] = move.cooldown

        return self._resolve_move(
            move, enemy, self._state.player, actor,
            enemy.get_effective_accuracy(),
        )

    def _select_enemy_move(self, enemy: EnemyShip) -> Optional[CombatMove]:
        """Select a move based on enemy AI behavior."""
        available = [
            m for m in enemy.template.moves
            if m.id not in enemy.cooldowns and enemy.current_energy >= m.energy_cost
        ]
        if not available:
            return None

        behavior = enemy.template.behavior

        if behavior == EnemyBehavior.AGGRESSIVE:
            # Always pick the highest-damage move
            return max(available, key=lambda m: self._move_damage(m))

        elif behavior == EnemyBehavior.DEFENSIVE:
            if enemy.hull_ratio < 0.5:
                # Prefer defensive moves when low
                defensive = [m for m in available if self._is_defensive_move(m)]
                if defensive:
                    return defensive[0]
            return max(available, key=lambda m: self._move_damage(m))

        elif behavior == EnemyBehavior.EVASIVE:
            # Alternate: evasion move if available and not on cooldown, else attack
            evasive = [m for m in available if self._is_evasive_move(m)]
            if evasive and self._state.round_number % 2 == 0:
                return evasive[0]
            offensive = [m for m in available if self._move_damage(m) > 0]
            return offensive[0] if offensive else available[0]

        # Default / COWARDLY (shouldn't reach here for cowardly, handled above)
        return available[0]

    @staticmethod
    def _move_damage(move: CombatMove) -> float:
        """Total damage from a move's effects."""
        return sum(
            e.value for e in move.effects
            if e.type == EffectType.DAMAGE and e.target == EffectTarget.ENEMY
        )

    @staticmethod
    def _is_defensive_move(move: CombatMove) -> bool:
        """Whether a move is primarily defensive."""
        return any(
            e.type in (EffectType.SHIELD_RESTORE, EffectType.HULL_RESTORE,
                       EffectType.DAMAGE_REDUCTION)
            for e in move.effects
        )

    @staticmethod
    def _is_evasive_move(move: CombatMove) -> bool:
        """Whether a move boosts evasion."""
        return any(
            e.type == EffectType.EVASION_MOD and e.target == EffectTarget.SELF
            for e in move.effects
        )

    # ------------------------------------------------------------------
    # Special actions
    # ------------------------------------------------------------------

    def attempt_flee(self) -> tuple[bool, list[CombatLogEntry]]:
        """Attempt to flee combat.

        Surviving enemies get parting shots at reduced accuracy,
        then flee roll is resolved.

        Returns:
            Tuple of (success, log_entries).
        """
        logs: list[CombatLogEntry] = []
        player = self._state.player

        # Parting shots from surviving enemies
        for idx, enemy in enumerate(self._state.enemies):
            if not enemy.is_alive or enemy.is_fled:
                continue
            move = self._select_enemy_move(enemy)
            if move and self._move_damage(move) > 0:
                parting_logs = self._resolve_move(
                    move, enemy, player, f"enemy:{idx}",
                    enemy.get_effective_accuracy(),
                    accuracy_penalty=FLEE_ACCURACY_PENALTY,
                )
                for log in parting_logs:
                    log.action = f"Parting Shot: {log.action}"
                logs.extend(parting_logs)

        # Flee roll
        avg_enemy_speed = sum(
            e.template.speed for e in self._state.surviving_enemies
        ) / max(1, len(self._state.surviving_enemies))
        flee_chance = max(FLEE_MIN_CHANCE, min(FLEE_MAX_CHANCE,
            FLEE_BASE_CHANCE
            + int((player.speed - avg_enemy_speed) * FLEE_SPEED_FACTOR)
            + player.flee_bonus
        ))
        roll = self._rng.randint(1, 100)
        success = roll <= flee_chance

        if success:
            self._state.result = CombatResult.FLED
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Flee",
                effects_applied=[f"Escaped! (rolled {roll} vs {flee_chance}%)"],
            )
        else:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Flee",
                effects_applied=[f"Failed to escape (rolled {roll} vs {flee_chance}%)"],
                hit=False,
            )
        self._state.combat_log.append(entry)
        logs.append(entry)
        return success, logs

    def attempt_bribe(
        self, player_credits: int, persuasion_level: int = 0
    ) -> tuple[bool, int, list[CombatLogEntry]]:
        """Attempt to bribe enemies to end combat.

        Cost is the sum of surviving enemies' bribe_cost, reduced by
        persuasion level (10% per level, max 50% discount). Always
        succeeds if player can afford it. One attempt per encounter.

        Args:
            player_credits: Player's current credits.
            persuasion_level: Player's persuasion skill level (0-5+).

        Returns:
            Tuple of (success, total_cost, log_entries).
        """
        logs: list[CombatLogEntry] = []

        if self._state.bribe_used:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Bribe",
                effects_applied=["Already attempted bribe this encounter"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            logs.append(entry)
            return False, 0, logs

        self._state.bribe_used = True

        # Calculate total cost from surviving enemies
        base_cost = sum(
            e.template.bribe_cost for e in self._state.surviving_enemies
        )

        # Apply persuasion discount (10% per level, max 50%)
        discount = min(0.5, persuasion_level * 0.1)
        total_cost = int(base_cost * (1.0 - discount))

        if player_credits < total_cost:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Bribe",
                effects_applied=[
                    f"Insufficient credits ({player_credits:,} < {total_cost:,} CR)"
                ],
                hit=False,
            )
            self._state.combat_log.append(entry)
            logs.append(entry)
            return False, total_cost, logs

        # Success
        self._state.result = CombatResult.BRIBED
        entry = CombatLogEntry(
            round_number=self._state.round_number,
            actor="player",
            action="Bribe",
            effects_applied=[f"Paid {total_cost:,} CR — enemies stand down"],
        )
        self._state.combat_log.append(entry)
        logs.append(entry)
        return True, total_cost, logs

    def attempt_negotiate(
        self, skill_id: str, social_manager: object,
        faction_reputation_tier: Optional[str] = None,
    ) -> tuple[bool, str, list[CombatLogEntry]]:
        """Attempt to negotiate with enemies.

        Args:
            skill_id: Social skill to use (persuasion/intimidation/observation).
            social_manager: SocialManager instance (or None).
            faction_reputation_tier: ReputationTier value string for difficulty modifier.

        Returns:
            Tuple of (success, message, log_entries).
        """
        if self._state.negotiate_used:
            return False, "Already attempted negotiation", []

        self._state.negotiate_used = True

        if social_manager is None:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Negotiate",
                effects_applied=["No social skills available"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return False, "No social skills available", [entry]

        # Find the first surviving enemy for negotiate difficulty
        surviving = self._state.surviving_enemies
        if not surviving:
            return False, "No enemies to negotiate with", []

        target = surviving[0]
        base_difficulty = target.template.negotiate_difficulty

        # Scale difficulty by enemy health
        if target.hull_ratio < 0.3:
            difficulty = max(1, base_difficulty - 2)
        elif target.hull_ratio < 0.6:
            difficulty = max(1, base_difficulty - 1)
        else:
            difficulty = base_difficulty

        # Apply faction reputation modifier
        _TIER_MODIFIERS = {
            "Allied": -2,
            "Friendly": -1,
            "Neutral": 0,
            "Unfriendly": 1,
            "Hostile": 2,
        }
        if faction_reputation_tier:
            modifier = _TIER_MODIFIERS.get(faction_reputation_tier, 0)
            difficulty = max(1, difficulty + modifier)

        # Use social manager's can_pass_check
        # We use empty npc_id since enemies aren't NPCs
        success = social_manager.can_pass_check(skill_id, difficulty, "")

        if success:
            if skill_id == "intimidation":
                # Enemy flees, no loot — but set rival rep flag
                for e in surviving:
                    e.is_fled = True
                msg = "Enemies retreated"
                self._state.result = CombatResult.NEGOTIATED
                self._state.negotiate_rival_rep = True
            elif skill_id == "observation":
                # Reveal weakness — buff player + reveal bribe cost
                acc_buff = CombatEffect(
                    type=EffectType.ACCURACY_MOD, value=15.0,
                    duration=2, target=EffectTarget.SELF,
                )
                self._state.player.active_effects.append((acc_buff, 2))
                # Reveal total bribe cost
                bribe_total = sum(
                    e.template.bribe_cost for e in self._state.surviving_enemies
                )
                self._state.revealed_bribe_cost = bribe_total
                msg = f"Weakness revealed: +15 accuracy for 2 turns (bribe cost: {bribe_total:,} CR)"
            else:
                # Persuasion: enemy surrenders with partial loot
                self._state.result = CombatResult.NEGOTIATED
                self._state.negotiate_partial_loot = True
                msg = "Enemies surrendered"
        else:
            msg = f"{skill_id.capitalize()} check failed (difficulty {difficulty})"

        entry = CombatLogEntry(
            round_number=self._state.round_number,
            actor="player",
            action=f"Negotiate ({skill_id})",
            effects_applied=[msg],
            hit=success,
        )
        self._state.combat_log.append(entry)
        return success, msg, [entry]

    # ------------------------------------------------------------------
    # Round management
    # ------------------------------------------------------------------

    def end_round(self) -> list[CombatLogEntry]:
        """Process end of round: tick effects, regen energy, check win/lose.

        Returns:
            Log entries for expired effects.
        """
        logs: list[CombatLogEntry] = []

        # Tick player effects
        messages = self._state.player.tick_effects()
        self._state.player.tick_cooldowns()
        self._state.player.regenerate_energy()

        # Tick enemy effects
        for enemy in self._state.enemies:
            if enemy.is_alive and not enemy.is_fled:
                messages.extend(enemy.tick_effects())
                enemy.tick_cooldowns()
                enemy.regenerate_energy()

        if messages:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="system",
                action="End of Round",
                effects_applied=messages,
            )
            self._state.combat_log.append(entry)
            logs.append(entry)

        self._state.round_number += 1
        self._check_combat_end()
        return logs

    # ------------------------------------------------------------------
    # Core resolution (private)
    # ------------------------------------------------------------------

    def _resolve_move(
        self,
        move: CombatMove,
        attacker: PlayerCombatState | EnemyShip,
        defender: PlayerCombatState | EnemyShip,
        actor_name: str,
        attacker_accuracy: int,
        accuracy_penalty: int = 0,
    ) -> list[CombatLogEntry]:
        """Resolve a single move against a target.

        Handles hit/miss, damage, effects, and logging.
        """
        logs: list[CombatLogEntry] = []
        effects_applied: list[str] = []

        # Separate offensive (target=ENEMY) and self-buff (target=SELF) effects
        offensive_effects = [e for e in move.effects if e.target == EffectTarget.ENEMY]
        self_effects = [e for e in move.effects if e.target == EffectTarget.SELF]

        # Resolve offensive effects (require hit roll)
        if offensive_effects:
            defender_evasion = (
                defender.get_effective_evasion()
                if hasattr(defender, "get_effective_evasion")
                else 0
            )
            hit_chance = max(HIT_CHANCE_MIN, min(HIT_CHANCE_MAX,
                attacker_accuracy + move.accuracy_modifier - defender_evasion - accuracy_penalty
            ))
            roll = self._rng.randint(1, 100)
            hit = roll <= hit_chance

            if hit:
                msgs = self._apply_effects(offensive_effects, defender, actor_name)
                effects_applied.extend(msgs)
            else:
                effects_applied.append(f"Missed (rolled {roll} vs {hit_chance}%)")

            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor=actor_name,
                action=move.name,
                effects_applied=list(effects_applied),
                hit=hit,
            )
            self._state.combat_log.append(entry)
            logs.append(entry)

        # Self-buff effects always apply (no hit roll needed)
        if self_effects:
            # Determine the "self" target
            if actor_name == "player" or actor_name.startswith("crew:"):
                self_target = self._state.player
            else:
                # Enemy self-buff targets the enemy
                self_target = attacker

            msgs = self._apply_effects(self_effects, self_target, actor_name)
            effects_applied_self = msgs

            if not offensive_effects:
                # Pure self-buff move — create a single log entry
                entry = CombatLogEntry(
                    round_number=self._state.round_number,
                    actor=actor_name,
                    action=move.name,
                    effects_applied=effects_applied_self,
                    hit=True,
                )
                self._state.combat_log.append(entry)
                logs.append(entry)

        self._check_combat_end()
        return logs

    def _apply_effects(
        self,
        effects: list[CombatEffect],
        target: PlayerCombatState | EnemyShip,
        source_name: str,
    ) -> list[str]:
        """Apply a list of effects to a target.

        Returns:
            Human-readable descriptions of what happened.
        """
        messages: list[str] = []
        target_name = self._get_target_name(target)

        # Calculate active damage reduction on the target
        damage_reduction = 0.0
        for eff, _ in target.active_effects:
            if eff.type == EffectType.DAMAGE_REDUCTION:
                damage_reduction += eff.value

        for effect in effects:
            if effect.type == EffectType.DAMAGE:
                raw = effect.value
                reduced = raw * (1.0 - min(damage_reduction, 0.9))
                if isinstance(target, PlayerCombatState):
                    shield_absorbed = min(target.shields, reduced)
                    hull_damage = reduced - shield_absorbed
                    target.shields -= int(shield_absorbed)
                    target.hull -= int(hull_damage)
                else:
                    shield_absorbed = min(target.current_shields, reduced)
                    hull_damage = reduced - shield_absorbed
                    target.current_shields -= int(shield_absorbed)
                    target.current_hull -= int(hull_damage)
                messages.append(
                    f"Dealt {int(reduced)} damage to {target_name} "
                    f"({int(shield_absorbed)} shields, {int(hull_damage)} hull)"
                )

            elif effect.type == EffectType.SHIELD_DRAIN:
                if isinstance(target, PlayerCombatState):
                    drained = min(target.shields, int(effect.value))
                    target.shields -= drained
                else:
                    drained = min(target.current_shields, int(effect.value))
                    target.current_shields -= drained
                messages.append(f"Drained {drained} shields from {target_name}")

            elif effect.type == EffectType.SHIELD_RESTORE:
                if isinstance(target, PlayerCombatState):
                    restored = min(int(effect.value), target.max_shields - target.shields)
                    target.shields += restored
                else:
                    restored = min(int(effect.value),
                                   target.template.shields - target.current_shields)
                    target.current_shields += restored
                messages.append(f"Restored {restored} shields on {target_name}")

            elif effect.type == EffectType.HULL_RESTORE:
                if isinstance(target, PlayerCombatState):
                    restored = min(int(effect.value), target.max_hull - target.hull)
                    target.hull += restored
                else:
                    restored = min(int(effect.value),
                                   target.template.hull - target.current_hull)
                    target.current_hull += restored
                messages.append(f"Restored {restored} hull on {target_name}")

            elif effect.type == EffectType.ENERGY_DRAIN:
                if isinstance(target, PlayerCombatState):
                    drained = min(target.energy, int(effect.value))
                    target.energy -= drained
                else:
                    drained = min(target.current_energy, int(effect.value))
                    target.current_energy -= drained
                messages.append(f"Drained {drained} energy from {target_name}")

            elif effect.type in (
                EffectType.EVASION_MOD,
                EffectType.ACCURACY_MOD,
                EffectType.DAMAGE_REDUCTION,
            ):
                if effect.duration > 0:
                    target.active_effects.append((effect, effect.duration))
                    messages.append(
                        f"{effect.type.value} {'+' if effect.value > 0 else ''}"
                        f"{int(effect.value)} on {target_name} for {effect.duration} turns"
                    )
                else:
                    # Instant modifier — apply once via active_effects with 1 turn
                    target.active_effects.append((effect, 1))
                    messages.append(
                        f"{effect.type.value} {'+' if effect.value > 0 else ''}"
                        f"{int(effect.value)} on {target_name}"
                    )

        return messages

    def _get_target_name(self, target: PlayerCombatState | EnemyShip) -> str:
        """Get a display name for a target."""
        if isinstance(target, PlayerCombatState):
            return "Player"
        return target.template.name

    def _check_combat_end(self) -> None:
        """Check if combat has ended (victory or defeat)."""
        if self._state.result != CombatResult.IN_PROGRESS:
            return
        if not self._state.player.is_alive:
            self._state.result = CombatResult.DEFEAT
        elif self._state.all_enemies_defeated:
            self._state.result = CombatResult.VICTORY

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_available_moves(self) -> list[CombatMove]:
        """Get equipment moves that are off cooldown and affordable."""
        player = self._state.player
        return [
            m for m in player.equipment_moves
            if m.id not in player.cooldowns and player.energy >= m.energy_cost
        ]

    def get_available_crew_moves(self) -> list[CombatMove]:
        """Get crew moves (always available, no energy cost)."""
        return list(self._state.player.crew_moves)

    def is_combat_over(self) -> bool:
        """Whether combat has ended."""
        return self._state.result != CombatResult.IN_PROGRESS

    def get_state(self) -> CombatState:
        """Get the current combat state."""
        return self._state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_player_move(self, move_id: str) -> Optional[CombatMove]:
        """Find a move by ID across equipment and crew moves."""
        for m in self._state.player.equipment_moves:
            if m.id == move_id:
                return m
        for m in self._state.player.crew_moves:
            if m.id == move_id:
                return m
        return None
