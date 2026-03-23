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
    WeaponElement,
)
from spacegame.models.momentum import (
    MOMENTUM_ON_CREW_ABILITY,
    MOMENTUM_ON_CRITICAL_HP,
    MOMENTUM_ON_HIT,
    MOMENTUM_ON_HULL_DAMAGE,
    MOMENTUM_ON_KILL,
    MOMENTUM_ON_STATUS_APPLIED,
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

        # Overdriven Weapon: 2x damage on next weapon attack (momentum 50% threshold)
        overdriven_active = False
        if (player.momentum and player.momentum.overdriven_available
                and any(e.type == EffectType.DAMAGE for e in move.effects)):
            overdriven_active = True
            # Temporarily add a 100% damage boost
            boost = CombatEffect(
                type=EffectType.DAMAGE_BOOST, value=100.0,
                duration=1, target=EffectTarget.SELF,
            )
            player.active_effects.append((boost, 1))

        # AOE moves hit all surviving enemies
        if move.aoe:
            all_logs: list[CombatLogEntry] = []
            for enemy in self._state.surviving_enemies:
                logs = self._resolve_move(
                    move, player, enemy, "player", player.get_effective_accuracy()
                )
                all_logs.extend(logs)
            if overdriven_active:
                self._consume_overdriven_boost(player)
            return all_logs

        # Single-target: determine target
        target_idx = min(target_idx, len(self._state.enemies) - 1)
        target_enemy = self._state.enemies[target_idx]

        # Resolve
        result = self._resolve_move(
            move, player, target_enemy, "player", player.get_effective_accuracy()
        )
        if overdriven_active:
            self._consume_overdriven_boost(player)
        return result

    def execute_crew_moves(
        self, chosen_move_id: Optional[str] = None,
        skip_ids: Optional[set[str]] = None,
    ) -> list[CombatLogEntry]:
        """Execute a single chosen crew combat move.

        With the crew tactical choice system, the player selects ONE crew
        ability per turn (or none to save energy). The chosen move is
        executed against the first surviving enemy.

        Args:
            chosen_move_id: ID of the crew move the player selected, or
                None to skip crew abilities this turn.
            skip_ids: Legacy — set of move IDs to skip (backward compat).

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

        # If a specific move was chosen, execute only that one
        if chosen_move_id is not None:
            for move in player.crew_moves:
                if move.id == chosen_move_id and move.id not in skip_ids:
                    if player.energy >= move.energy_cost:
                        # Deduct energy cost
                        player.energy -= move.energy_cost
                        # Set cooldown if applicable
                        if move.cooldown > 0:
                            player.cooldowns[move.id] = move.cooldown
                        target = surviving[0]
                        logs = self._resolve_move(
                            move, player, target,
                            f"crew:{move.id}", player.get_effective_accuracy(),
                        )
                        all_logs.extend(logs)
                        # Momentum: crew ability used
                        self._add_player_momentum(MOMENTUM_ON_CREW_ABILITY, "crew ability")
                    break
            return all_logs

        # Legacy fallback: execute all crew moves (old behavior)
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

        # Check if frozen (Cryo 3-stack effect) — skip turn entirely
        for eff, _ in enemy.active_effects:
            if hasattr(eff, "_frozen") and eff._frozen:
                entry = CombatLogEntry(
                    round_number=self._state.round_number,
                    actor=actor,
                    action="Frozen",
                    effects_applied=[f"{enemy.template.name} is frozen solid!"],
                    hit=False,
                )
                self._state.combat_log.append(entry)
                return [entry]

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

    def telegraph_enemy_moves(self) -> None:
        """Pre-compute and store each enemy's next intended move.

        Called at the start of the player input phase so the player
        can see what's coming and react accordingly.
        """
        for enemy in self._state.enemies:
            if not enemy.is_alive or enemy.is_fled:
                enemy.telegraphed_move = None
                continue
            # Frozen enemies can't act — clear telegraph
            is_frozen = any(
                hasattr(eff, "_frozen") and eff._frozen
                for eff, _ in enemy.active_effects
            )
            if is_frozen:
                enemy.telegraphed_move = None
                continue
            enemy.telegraphed_move = self._select_enemy_move(enemy)

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
        player = self._state.player
        messages = player.tick_effects()
        player.tick_cooldowns()
        player.regenerate_energy()

        # Passive shield regen (Phase 12A)
        if player.shield_regen > 0 and player.shields < player.max_shields:
            regen = min(player.shield_regen, player.max_shields - player.shields)
            player.shields += regen
            messages.append(f"Shield regen: +{regen}")

        # Reset evasion decay (Phase 12A — penalty clears each round)
        player.evasion_decay = 0

        # Reset shield break vulnerability (lasts 1 turn)
        player.shield_break_vulnerable = False

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
            is_player_attack = actor_name == "player" or actor_name.startswith("crew:")

            # AoE moves always hit — skip evasion roll entirely
            if move.aoe:
                hit = True
                graze = False
                roll = 0
                hit_chance = 100
            else:
                # Evasion with diminishing returns above 50
                raw_evasion = (
                    defender.get_effective_evasion()
                    if hasattr(defender, "get_effective_evasion")
                    else 0
                )
                # Apply evasion decay (temporary penalty after being hit)
                if isinstance(defender, PlayerCombatState):
                    raw_evasion = max(0, raw_evasion - defender.evasion_decay)
                effective_evasion = raw_evasion
                if effective_evasion > 50:
                    effective_evasion = 50 + int((effective_evasion - 50) * 0.5)

                hit_chance = max(HIT_CHANCE_MIN, min(HIT_CHANCE_MAX,
                    attacker_accuracy + move.accuracy_modifier - effective_evasion - accuracy_penalty
                ))
                roll = self._rng.randint(1, 100)
                hit = roll <= hit_chance
                graze = False

                # Graze system: miss by ≤10 → 30% damage
                if not hit:
                    miss_margin = roll - hit_chance
                    if miss_margin <= 10:
                        graze = True
                    else:
                        # Clean miss — Ghost Counterstrike
                        if (isinstance(defender, PlayerCombatState)
                                and defender.defensive_identity == "ghost"):
                            defender.counterstrike_stacks = min(
                                defender.counterstrike_stacks + 1, 3
                            )

            if hit or graze:
                # Track if enemy was alive before applying effects
                enemy_was_alive = (
                    defender.is_alive
                    if isinstance(defender, EnemyShip)
                    else True
                )

                # Apply effects with graze damage multiplier
                msgs = self._apply_effects(
                    offensive_effects, defender, actor_name,
                    attacker_state=attacker, element=move.element,
                    damage_multiplier=0.30 if graze else 1.0,
                )
                effects_applied.extend(msgs)

                if graze:
                    effects_applied.append(f"GRAZE (rolled {roll} vs {hit_chance}%)")

                # Identity passives on being hit
                if not is_player_attack and isinstance(defender, PlayerCombatState):
                    # Evasion decay: -5 evasion for 1 turn after being hit
                    defender.evasion_decay = 5
                    # Ghost Counterstrike resets on being hit
                    if defender.defensive_identity == "ghost":
                        defender.counterstrike_stacks = 0
                    # Sentinel Shield Break detection
                    if (defender.defensive_identity == "sentinel"
                            and defender.shields == 0
                            and not defender.shield_break_vulnerable):
                        defender.shield_break_vulnerable = True

                # Momentum: player dealt a hit
                if is_player_attack and isinstance(defender, EnemyShip):
                    momentum_msgs = self._add_player_momentum(MOMENTUM_ON_HIT, "hit")
                    effects_applied.extend(momentum_msgs)
                    if enemy_was_alive and not defender.is_alive:
                        kill_msgs = self._add_player_momentum(MOMENTUM_ON_KILL, "kill")
                        effects_applied.extend(kill_msgs)

                # Momentum: player took hull damage (enemy hit the player)
                if not is_player_attack and isinstance(defender, PlayerCombatState):
                    hull_msgs = self._add_player_momentum(MOMENTUM_ON_HULL_DAMAGE, "took damage")
                    effects_applied.extend(hull_msgs)
                    crit_msgs = self._check_critical_hp_surge()
                    effects_applied.extend(crit_msgs)
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
        attacker_state: Optional[PlayerCombatState | EnemyShip] = None,
        element: Optional["WeaponElement"] = None,
        damage_multiplier: float = 1.0,
    ) -> list[str]:
        """Apply a list of effects to a target.

        Args:
            effects: Effects to apply.
            target: The entity receiving the effects.
            source_name: Name of the actor for log messages.
            attacker_state: The attacking entity (for self-referencing effects
                like energy_restore and damage_boost checks). If None, uses target.
            element: Weapon element for elemental damage resolution.

        Returns:
            Human-readable descriptions of what happened.
        """
        messages: list[str] = []
        target_name = self._get_target_name(target)
        atk = attacker_state if attacker_state is not None else target

        # Calculate active damage reduction on the target
        damage_reduction = 0.0
        for eff, _ in target.active_effects:
            if eff.type == EffectType.DAMAGE_REDUCTION:
                damage_reduction += eff.value

        # Check attacker's damage boost (from Overcharge etc.)
        damage_boost_pct = 0.0
        if hasattr(atk, "active_effects"):
            for eff, _ in atk.active_effects:
                if eff.type == EffectType.DAMAGE_BOOST:
                    damage_boost_pct += eff.value

        # Check attacker's Suppressed stacks (from Voltaic weapons)
        # Each stack reduces the attacker's outgoing damage by its value percent
        suppressed_reduction = 0.0
        if hasattr(atk, "active_effects"):
            for eff, _ in atk.active_effects:
                if eff.type == EffectType.SUPPRESSED:
                    suppressed_reduction += eff.value / 100.0
        suppressed_reduction = min(suppressed_reduction, 0.9)  # Cap at 90%

        # Check for ABSORB (countermeasures) — nullify first incoming damage
        absorb_idx = None
        for i, (eff, dur) in enumerate(target.active_effects):
            if eff.type == EffectType.ABSORB:
                absorb_idx = i
                break

        if absorb_idx is not None:
            # Check if this effect set has damage
            has_incoming_dmg = any(e.type == EffectType.DAMAGE for e in effects)
            if has_incoming_dmg:
                target.active_effects.pop(absorb_idx)
                messages.append("Countermeasures absorbed the hit!")
                # Process non-damage effects only
                effects = [e for e in effects if e.type != EffectType.DAMAGE]
                if not effects:
                    return messages

        # Determine effective element (default Kinetic if none specified)
        eff_element = element if element is not None else WeaponElement.KINETIC

        # Check if target has Suppressed stacks (reduce their damage, not ours)
        # Suppressed affects the TARGET's outgoing damage, handled separately in enemy turn

        for effect in effects:
            if effect.type == EffectType.DAMAGE:
                raw = effect.value
                if damage_boost_pct > 0:
                    raw *= 1.0 + damage_boost_pct / 100.0
                if suppressed_reduction > 0:
                    raw *= 1.0 - suppressed_reduction

                # Graze multiplier (0.30 for near-miss, 1.0 for full hit)
                raw *= damage_multiplier

                # Attacker identity bonuses
                if isinstance(atk, PlayerCombatState):
                    # Juggernaut Last Stand: +15% damage below 25% hull
                    if (atk.defensive_identity == "juggernaut"
                            and atk.hull_ratio < 0.25):
                        raw *= 1.15
                    # Ghost Counterstrike: +10% per stack
                    if (atk.defensive_identity == "ghost"
                            and atk.counterstrike_stacks > 0):
                        raw *= 1.0 + 0.10 * atk.counterstrike_stacks

                # Defender identity modifiers
                if isinstance(target, PlayerCombatState):
                    # Ghost Light Frame Vulnerability: +15% incoming damage
                    if target.defensive_identity == "ghost":
                        raw *= 1.15
                    # Juggernaut Structural Integrity: -5% DR when hull > 75%
                    if (target.defensive_identity == "juggernaut"
                            and target.hull_ratio > 0.75):
                        damage_reduction = min(0.9, damage_reduction + 0.05)
                    # Sentinel Shield Break Vulnerability: +25% damage when shields broken
                    if target.shield_break_vulnerable:
                        raw *= 1.25

                # === Elemental damage resolution ===
                if eff_element == WeaponElement.PLASMA:
                    # 66% upfront, remainder becomes Burn DoT
                    upfront = raw * 0.66
                    burn_per_turn = raw * 0.34 * 1.15  # 34% + 15% bonus
                    reduced = upfront * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(target, reduced, messages, target_name)
                    # Apply Burn stack (stacks to 3, each lasts 3 turns)
                    burn_effect = CombatEffect(
                        type=EffectType.BURN, value=burn_per_turn,
                        duration=3, target=EffectTarget.ENEMY,
                    )
                    self._apply_stacking_effect(target, burn_effect, max_stacks=3)
                    messages.append(
                        f"Burn: {int(burn_per_turn)}/turn for 3 turns"
                    )
                    # Momentum: elemental status applied by player
                    if source_name == "player" or source_name.startswith("crew:"):
                        self._add_player_momentum(MOMENTUM_ON_STATUS_APPLIED, "burn applied")

                elif eff_element == WeaponElement.ION:
                    # 150% to shields, 75% to hull
                    reduced = raw * (1.0 - min(damage_reduction, 0.9))
                    if isinstance(target, PlayerCombatState):
                        shields = target.shields
                        ion_shield_dmg = min(shields, reduced * 1.5)
                        remaining = max(0, reduced - shields / 1.5)
                        hull_dmg = remaining * 0.75
                        target.shields = max(0, shields - int(ion_shield_dmg))
                        target.hull = max(0, target.hull - int(hull_dmg))
                    else:
                        shields = target.current_shields
                        ion_shield_dmg = min(shields, reduced * 1.5)
                        remaining = max(0, reduced - shields / 1.5)
                        hull_dmg = remaining * 0.75
                        target.current_shields = max(0, shields - int(ion_shield_dmg))
                        target.current_hull = max(0, target.current_hull - int(hull_dmg))
                    messages.append(
                        f"Ion: {int(ion_shield_dmg)} shield / {int(hull_dmg)} hull to {target_name}"
                    )

                elif eff_element == WeaponElement.CRYO:
                    # 85% damage + Chill stack
                    reduced = raw * 0.85 * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(target, reduced, messages, target_name)
                    chill_effect = CombatEffect(
                        type=EffectType.CHILL, value=5.0,  # -5 evasion per stack
                        duration=4, target=EffectTarget.ENEMY,
                    )
                    chill_count = self._apply_stacking_effect(target, chill_effect, max_stacks=3)
                    messages.append(f"Chill x{chill_count}")
                    if source_name == "player" or source_name.startswith("crew:"):
                        self._add_player_momentum(MOMENTUM_ON_STATUS_APPLIED, "chill applied")
                    if chill_count >= 3:
                        # Frozen! Enemy loses next turn — clear all Chill stacks
                        self._clear_effect_type(target, EffectType.CHILL)
                        # Mark frozen by setting a special 1-turn skip flag
                        frozen_effect = CombatEffect(
                            type=EffectType.CHILL, value=0.0,
                            duration=1, target=EffectTarget.ENEMY,
                        )
                        frozen_effect._frozen = True  # type: ignore[attr-defined]
                        target.active_effects.append((frozen_effect, 1))
                        messages.append("FROZEN! Enemy loses next turn")

                elif eff_element == WeaponElement.VOLTAIC:
                    # 85% damage + Suppressed stack
                    reduced = raw * 0.85 * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(target, reduced, messages, target_name)
                    suppress_effect = CombatEffect(
                        type=EffectType.SUPPRESSED, value=12.0,  # -12% damage per stack
                        duration=3, target=EffectTarget.ENEMY,
                    )
                    sup_count = self._apply_stacking_effect(target, suppress_effect, max_stacks=3)
                    messages.append(f"Suppressed x{sup_count} (-{sup_count * 12}% damage)")
                    if source_name == "player" or source_name.startswith("crew:"):
                        self._add_player_momentum(MOMENTUM_ON_STATUS_APPLIED, "suppressed applied")

                else:
                    # Kinetic (default) — pure direct damage
                    reduced = raw * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(target, reduced, messages, target_name)

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

            elif effect.type == EffectType.ENERGY_RESTORE:
                # Restore energy to the target (self-targeting in practice)
                if isinstance(target, PlayerCombatState):
                    restored = min(int(effect.value), target.max_energy - target.energy)
                    target.energy += restored
                else:
                    max_e = getattr(target, "max_energy", 999)
                    cur_e = getattr(target, "current_energy", 0)
                    restored = min(int(effect.value), max_e - cur_e)
                    if hasattr(target, "current_energy"):
                        target.current_energy += restored
                if restored > 0:
                    messages.append(f"Restored {restored} energy")

            elif effect.type == EffectType.DAMAGE_BOOST:
                # Buff that increases next attack damage (duration-based, on self)
                duration = max(1, effect.duration)
                target.active_effects.append((effect, duration))
                messages.append(
                    f"+{int(effect.value)}% damage for {duration} turn{'s' if duration > 1 else ''}"
                )

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

            elif effect.type == EffectType.CLEANSE:
                # Remove all negative effects from target (self-buff)
                negative_types = {
                    EffectType.BURN, EffectType.CHILL, EffectType.SUPPRESSED,
                }
                before = len(target.active_effects)
                target.active_effects = [
                    (eff, dur) for eff, dur in target.active_effects
                    if eff.type not in negative_types
                    or (eff.target == EffectTarget.SELF and eff.value >= 0)
                ]
                removed = before - len(target.active_effects)
                if removed > 0:
                    messages.append(f"Cleansed {removed} negative effect{'s' if removed > 1 else ''}")
                else:
                    messages.append("No negative effects to cleanse")

            elif effect.type == EffectType.ABSORB:
                # Add absorb shield: next incoming hit is nullified
                target.active_effects.append((effect, max(1, effect.duration)))
                messages.append("Countermeasures deployed — next hit absorbed")

        return messages

    @staticmethod
    def _apply_direct_damage(
        target: PlayerCombatState | EnemyShip,
        reduced: float,
        messages: list[str],
        target_name: str,
    ) -> None:
        """Apply direct damage to a target's shields then hull.

        Applies armor reduction (flat damage subtraction) before shield/hull split.
        Burn DoT and other bypass-armor effects should reduce damage before calling.
        """
        # Armor: flat reduction per hit (minimum 1 damage)
        armor = 0
        if isinstance(target, PlayerCombatState):
            armor = target.armor
            # Juggernaut Last Stand: +2 armor when below 25% hull
            if (target.defensive_identity == "juggernaut"
                    and target.hull_ratio < 0.25):
                armor += 2
        elif hasattr(target, "template"):
            armor = getattr(target.template, "combat_armor", 0)

        if armor > 0 and reduced > 0:
            armor_absorbed = min(armor, reduced - 1)  # Always deal at least 1
            reduced = max(1.0, reduced - armor)
            if armor_absorbed > 0:
                messages.append(f"Armor absorbed {int(armor_absorbed)}")

        if isinstance(target, PlayerCombatState):
            shield_absorbed = min(target.shields, reduced)
            hull_damage = reduced - shield_absorbed
            target.shields = max(0, target.shields - int(shield_absorbed))
            target.hull = max(0, target.hull - int(hull_damage))
        else:
            shield_absorbed = min(target.current_shields, reduced)
            hull_damage = reduced - shield_absorbed
            target.current_shields = max(0, target.current_shields - int(shield_absorbed))
            target.current_hull = max(0, target.current_hull - int(hull_damage))
        messages.append(
            f"Dealt {int(reduced)} damage to {target_name} "
            f"({int(shield_absorbed)} shields, {int(hull_damage)} hull)"
        )

    @staticmethod
    def _apply_stacking_effect(
        target: PlayerCombatState | EnemyShip,
        effect: CombatEffect,
        max_stacks: int = 3,
    ) -> int:
        """Apply a stacking status effect, enforcing the stack cap.

        Returns:
            Current stack count after application.
        """
        # Count existing stacks of this effect type
        current_stacks = sum(
            1 for eff, _ in target.active_effects
            if eff.type == effect.type
        )
        if current_stacks < max_stacks:
            target.active_effects.append((effect, effect.duration))
            current_stacks += 1
        else:
            # Refresh the oldest stack's duration instead of adding a new one
            for i, (eff, _) in enumerate(target.active_effects):
                if eff.type == effect.type:
                    target.active_effects[i] = (effect, effect.duration)
                    break
        return current_stacks

    @staticmethod
    def _clear_effect_type(
        target: PlayerCombatState | EnemyShip,
        effect_type: EffectType,
    ) -> None:
        """Remove all stacks of a specific effect type from a target."""
        target.active_effects = [
            (eff, dur) for eff, dur in target.active_effects
            if eff.type != effect_type
        ]

    def _get_target_name(self, target: PlayerCombatState | EnemyShip) -> str:
        """Get a display name for a target."""
        if isinstance(target, PlayerCombatState):
            return "Player"
        return target.template.name

    def _consume_overdriven_boost(self, player: PlayerCombatState) -> None:
        """Remove the temporary Overdriven damage boost and consume the buff."""
        player.active_effects = [
            (eff, dur) for eff, dur in player.active_effects
            if not (eff.type == EffectType.DAMAGE_BOOST and eff.value == 100.0 and dur == 1)
        ]
        if player.momentum:
            player.momentum.consume_overdriven()

    def _add_player_momentum(self, amount: float, reason: str = "") -> list[str]:
        """Add momentum to the player gauge and return threshold messages.

        Args:
            amount: Momentum to add (0.0 to 1.0 scale).
            reason: Debug/log description of why momentum was added.

        Returns:
            List of human-readable messages about crossed thresholds.
        """
        player = self._state.player
        if player.momentum is None:
            return []
        crossed = player.momentum.add(amount)
        messages: list[str] = []
        for threshold in crossed:
            if threshold == "charged":
                messages.append("Momentum: CHARGED! Crew combos unlocked.")
            elif threshold == "surging":
                messages.append("Momentum: SURGING! Overdriven Weapon ready.")
            elif threshold == "overload":
                messages.append("Momentum: OVERLOAD! Systems overclocked (+3 regen, 2 turns)")
                # Immediately restore 3 energy as a burst, then add regen buff
                # that the engine processes in end_round for 2 more turns
                player.energy = min(player.max_energy, player.energy + 3)
                overclock_eff = CombatEffect(
                    type=EffectType.ENERGY_RESTORE,
                    value=3.0,
                    duration=2,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((overclock_eff, 2))
            elif threshold == "ultimate":
                messages.append("Momentum: ULTIMATE READY!")
        return messages

    def _check_critical_hp_surge(self) -> list[str]:
        """Check if player just dropped below 25% hull for the first time.

        Returns:
            Momentum messages if the surge fires.
        """
        player = self._state.player
        if player.critical_hp_surge_fired:
            return []
        if player.hull_ratio < 0.25 and player.hull > 0:
            player.critical_hp_surge_fired = True
            return self._add_player_momentum(MOMENTUM_ON_CRITICAL_HP, "critical HP")
        return []

    def _check_enemy_killed_momentum(self, enemy: EnemyShip) -> list[str]:
        """Add momentum if an enemy was just killed.

        Args:
            enemy: The enemy to check.

        Returns:
            Momentum messages if kill momentum fires.
        """
        if not enemy.is_alive:
            return self._add_player_momentum(MOMENTUM_ON_KILL, f"killed {enemy.template.name}")
        return []

    def execute_ultimate(self) -> list[CombatLogEntry]:
        """Execute the player's ship ultimate ability.

        Requires 100% momentum. Resets momentum to 0 after use.

        Returns:
            Combat log entries from the ultimate's effects.
        """
        from spacegame.data_loader import get_data_loader

        player = self._state.player
        if player.momentum is None or not player.momentum.ultimate_available:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Ultimate",
                effects_applied=["Ultimate not ready"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        dl = get_data_loader()
        ultimate = dl.ship_ultimates.get(player.ship_class_category)
        if ultimate is None:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Ultimate",
                effects_applied=["No ultimate defined for this ship class"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Consume momentum
        player.momentum.consume_ultimate()

        # Resolve ultimate effects
        logs = self._resolve_ultimate_effects(ultimate)
        return logs

    def _resolve_ultimate_effects(
        self, ultimate: "ShipUltimate"
    ) -> list[CombatLogEntry]:
        """Resolve the mechanical effects of a ship ultimate.

        Args:
            ultimate: The ultimate ability definition.

        Returns:
            Combat log entries from the resolution.
        """
        from spacegame.models.momentum import ShipUltimate

        player = self._state.player
        messages: list[str] = [f"ULTIMATE: {ultimate.name}!"]
        surviving = self._state.surviving_enemies

        for effect in ultimate.effects:
            effect_type = effect.get("type", "")
            value = effect.get("value", 0)
            target = effect.get("target", "")
            duration = effect.get("duration", 0)

            if effect_type == "damage" and target == "all_enemies":
                for enemy in surviving:
                    dmg = int(value)
                    self._apply_direct_damage(
                        enemy, float(dmg), messages, enemy.template.name
                    )
                    messages.append(f"{enemy.template.name}: {dmg} damage")

            elif effect_type == "damage" and target == "single_enemy":
                if surviving:
                    # Target strongest (highest current HP) enemy
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    dmg = int(value)
                    if effect.get("ignores_shields"):
                        strongest.current_hull = max(0, strongest.current_hull - dmg)
                        messages.append(f"{strongest.template.name}: {dmg} damage (bypassed shields)")
                    else:
                        self._apply_direct_damage(
                            strongest, float(dmg), messages, strongest.template.name
                        )
                        messages.append(f"{strongest.template.name}: {dmg} damage")

            elif effect_type == "guaranteed_flee":
                self._state.result = CombatResult.FLED

            elif effect_type == "hull_restore" and target == "self_percent":
                restore = int(player.max_hull * value)
                player.hull = min(player.max_hull, player.hull + restore)
                messages.append(f"Restored {restore} hull")

            elif effect_type == "damage_immunity":
                eff = CombatEffect(
                    type=EffectType.DAMAGE_REDUCTION,
                    value=100.0,
                    duration=duration,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((eff, duration))
                messages.append(f"Damage immunity for {duration} turns")

            elif effect_type == "skip_turn" and target == "all_enemies":
                for enemy in surviving:
                    # Mark enemies to skip turns using frozen-like mechanic
                    skip_count = int(value)
                    eff = CombatEffect(
                        type=EffectType.EVASION_MOD,
                        value=-999,
                        duration=skip_count,
                    )
                    enemy.active_effects.append((eff, skip_count))
                    if not hasattr(enemy, "_frozen"):
                        enemy._frozen = True
                    else:
                        enemy._frozen = True
                messages.append(f"All enemies stunned for {int(value)} turns")

            elif effect_type == "evasion_mod" and target == "all_enemies":
                for enemy in surviving:
                    eff = CombatEffect(
                        type=EffectType.EVASION_MOD,
                        value=value,
                        duration=duration,
                    )
                    enemy.active_effects.append((eff, duration))
                messages.append(f"All enemies: {int(value)} evasion for {duration} turns")

            elif effect_type == "accuracy_mod" and target == "self":
                eff = CombatEffect(
                    type=EffectType.ACCURACY_MOD,
                    value=value,
                    duration=duration,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((eff, duration))
                messages.append(f"+{int(value)} accuracy for {duration} turns")

            elif effect_type == "energy_drain" and target == "all_enemies":
                for enemy in surviving:
                    drained = min(int(value), enemy.current_energy)
                    enemy.current_energy -= drained
                messages.append(f"Drained {int(value)} energy from all enemies")

            elif effect_type == "sacrifice_cargo":
                messages.append(f"Jettisoned {int(value)} cargo units")
                # Actual cargo removal happens in the view layer (needs player model)

            elif effect_type == "free_action":
                messages.append("Free action next turn!")
                # Tracked via flag in combat state, resolved in view

            elif effect_type == "reset_cooldowns":
                player.cooldowns.clear()
                messages.append("All cooldowns reset!")

            elif effect_type == "momentum_refund":
                refund = value
                player.momentum.add(refund)
                messages.append(f"Momentum refunded to {int(player.momentum.current * 100)}%")

            elif effect_type == "burn" and target == "single_enemy":
                if surviving:
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    for _ in range(int(value)):
                        burn_eff = CombatEffect(
                            type=EffectType.BURN, value=7.0, duration=3
                        )
                        self._apply_stacking_effect(strongest, burn_eff)
                    messages.append(f"{strongest.template.name}: {int(value)} Burn stacks applied")

            elif effect_type == "immobilize":
                if surviving:
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    strongest._frozen = True
                    eff = CombatEffect(
                        type=EffectType.EVASION_MOD,
                        value=-999,
                        duration=int(value),
                    )
                    strongest.active_effects.append((eff, int(value)))
                    messages.append(f"{strongest.template.name} immobilized for {int(value)} turns")

            elif effect_type == "energy_lock":
                messages.append(f"High-cost abilities locked for {duration} turns")
                # Engine enforces this in enemy move selection

            elif effect_type == "reveal_stats":
                messages.append("All enemy stats revealed")
                # View layer reads this flag for display

            elif effect_type == "copy_best_move":
                if surviving:
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    best_move = max(strongest.template.moves, key=lambda m: sum(
                        e.value for e in m.effects if e.type == EffectType.DAMAGE
                    ), default=None)
                    if best_move:
                        player.equipment_moves.append(best_move)
                        messages.append(f"Copied {best_move.name} from {strongest.template.name}")

        entry = CombatLogEntry(
            round_number=self._state.round_number,
            actor="player",
            action=f"ULTIMATE: {ultimate.name}",
            effects_applied=messages,
            hit=True,
        )
        self._state.combat_log.append(entry)

        self._check_combat_end()
        return [entry]

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
