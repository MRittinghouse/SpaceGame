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

        # AOE moves hit all surviving enemies
        if move.aoe:
            all_logs: list[CombatLogEntry] = []
            for enemy in self._state.surviving_enemies:
                logs = self._resolve_move(
                    move, player, enemy, "player", player.get_effective_accuracy()
                )
                all_logs.extend(logs)
            return all_logs

        # Single-target: determine target
        target_idx = min(target_idx, len(self._state.enemies) - 1)
        target_enemy = self._state.enemies[target_idx]

        # Resolve
        return self._resolve_move(
            move, player, target_enemy, "player", player.get_effective_accuracy()
        )

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
                msgs = self._apply_effects(
                    offensive_effects, defender, actor_name,
                    attacker_state=attacker, element=move.element,
                )
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
        attacker_state: Optional[PlayerCombatState | EnemyShip] = None,
        element: Optional["WeaponElement"] = None,
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
        """Apply direct damage to a target's shields then hull."""
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
