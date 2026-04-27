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
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    PlayerCombatState,
    WeaponElement,
)
from spacegame.models.combat_complication import CombatComplication
from spacegame.models.complication_resolver import ComplicationResolver
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

# Tier 3.E: cap on simultaneous living enemies. Reinforcement spawns are
# silently declined above this cap so a misconfigured move can't flood
# the combat arena. Matches the combat view's tested-layout budget of up
# to 5 enemy cards (3 arena render slots + 2 on the card panel when
# necessary). Raise with care — bigger arenas need UI rework.
MAX_LIVING_ENEMIES = 5


class CombatEngine:
    """Resolves turn-based combat. All mutable state lives in CombatState."""

    def __init__(
        self,
        state: CombatState,
        seed: int = 0,
        complications: Optional[list[CombatComplication]] = None,
    ) -> None:
        self._state = state
        self._rng = random.Random(seed)
        # CE-3 Wave 2: live complication resolution. Caller resolves
        # ``EncounterDefinition.complication_ids`` against the data loader
        # and passes the actual CombatComplication instances. The engine
        # evaluates them at well-defined hook points (start of player turn
        # and end of round) so ``turn_counter`` and ``hp_threshold`` triggers
        # both fire promptly.
        self._resolver = ComplicationResolver(complications or [])

    def _skill_bonus(self, bonus_type: str) -> float:
        """Get a skill bonus from progression, or 0.0 if not available."""
        prog = self._state.progression
        if prog and hasattr(prog, "get_bonus"):
            return prog.get_bonus(bonus_type)
        return 0.0

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def execute_player_turn(
        self,
        queue: "ActionQueue",
    ) -> list[CombatLogEntry]:
        """Execute all queued player actions for this turn.

        Resolves each action in order. If a target is dead when its
        action comes up, the action is skipped and energy is refunded.

        Args:
            queue: The player's planned action queue for this turn.

        Returns:
            Combined list of combat log entries from all actions.
        """

        all_logs: list[CombatLogEntry] = []
        player = self._state.player

        # CE-3 Wave 2: evaluate complications before the player commits
        # to actions for the round. Catches turn_counter triggers on the
        # first round and any hp_threshold triggers that became true on
        # the previous round's enemy phase.
        all_logs.extend(self._evaluate_complications())

        for action in queue.actions:
            # Check if target is still valid (alive)
            if action.target_idx >= 0:
                if action.target_idx >= len(self._state.enemies):
                    continue
                target = self._state.enemies[action.target_idx]
                if not target.is_alive:
                    # Target died from earlier action — skip, refund energy
                    player.energy += action.energy_cost
                    skip_entry = CombatLogEntry(
                        round_number=self._state.round_number,
                        actor="player",
                        action=action.move_name,
                        effects_applied=[f"Target destroyed — {action.move_name} held fire"],
                        hit=False,
                    )
                    self._state.combat_log.append(skip_entry)
                    all_logs.append(skip_entry)
                    continue

            # Execute via the standard single-move pipeline
            logs = self.execute_player_move(action.move_id, action.target_idx)
            all_logs.extend(logs)

        # Fire at Will (B8.2): flag is turn-scoped. Clear after all queued
        # actions resolve so the discount doesn't leak into enemy or
        # end-of-round paths.
        if getattr(player, "fire_at_will_active", False):
            player.fire_at_will_active = False

        return all_logs

    def execute_player_move(self, move_id: str, target_idx: int = 0) -> list[CombatLogEntry]:
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

        # Check cooldown — use slot_key for per-slot independent cooldowns
        cooldown_key = getattr(move, "slot_key", "") or move_id
        if cooldown_key in player.cooldowns:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action=move.name,
                effects_applied=[f"{move.name} is on cooldown"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Dual tech (B8.2): Crew Sync is once-per-combat — reject early,
        # before energy/cooldown are spent, if already used this combat.
        if move.id == "crew_sync" and getattr(player, "crew_sync_used", False):
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action=move.name,
                effects_applied=["Crew Sync already used this combat"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Compute effective energy cost (shield_energy_discount reduces shield moves)
        effective_cost = move.energy_cost
        is_shield_move = any(e.type == EffectType.SHIELD_RESTORE for e in move.effects)
        if is_shield_move:
            discount = int(self._skill_bonus("shield_energy_discount"))
            effective_cost = max(0, effective_cost - discount)

        # Fire at Will (B8.2): when the flag is set, weapon moves fire at
        # half energy. A "weapon move" is any move with a DAMAGE effect.
        # Fire at Will itself has no DAMAGE effect, so it can't be
        # recursively discounted by its own activation.
        is_weapon_move = any(e.type == EffectType.DAMAGE for e in move.effects)
        fire_at_will_discount_applied = False
        if is_weapon_move and getattr(player, "fire_at_will_active", False):
            effective_cost = max(0, effective_cost // 2)
            fire_at_will_discount_applied = True

        # Check energy
        if player.energy < effective_cost:
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
        player.energy -= effective_cost

        # Set cooldown — per-slot so duplicate equipment has independent cooldowns.
        # Fire at Will skips cooldown assignment for weapon moves fired under it.
        if move.cooldown > 0 and not fire_at_will_discount_applied:
            player.cooldowns[cooldown_key] = move.cooldown

        # Dual tech (B8.2 / B8.3): apply activation side-effects AFTER
        # energy/cooldown accounting but BEFORE the effect pipeline runs.
        # These helpers set flags and apply immediate state changes the
        # CombatEffect system can't express.
        dual_tech_logs: list[str] = []
        _dual_tech_dispatched_ids = {
            "power_drift",
            "fire_at_will",
            "crew_sync",
            "total_commitment",
            "daring_gambit",
        }
        if move.id in _dual_tech_dispatched_ids:
            from spacegame.models.dual_tech import (
                activate_crew_sync,
                activate_daring_gambit_counter,
                activate_fire_at_will,
                activate_power_drift,
                activate_total_commitment,
            )

            if move.id == "power_drift":
                dual_tech_logs = activate_power_drift(player)
            elif move.id == "fire_at_will":
                dual_tech_logs = activate_fire_at_will(player)
            elif move.id == "crew_sync":
                _applied, dual_tech_logs = activate_crew_sync(player)
            elif move.id == "total_commitment":
                dual_tech_logs = activate_total_commitment(player)
            elif move.id == "daring_gambit":
                # Evasion buff is already in move.effects — this helper just
                # arms the counter-on-dodge window.
                dual_tech_logs = activate_daring_gambit_counter(player)

        # B8.4 tail: first-use cinematic reveal. Emit BEFORE the
        # mechanical activation log so the scene lands first in the UI.
        if move.id in _dual_tech_dispatched_ids or move.id in (
            "gun_run",
            "focused_barrage",
        ):
            try:
                from spacegame.models.dual_tech_dialogue import (
                    check_and_mark_reveal,
                )

                reveal = check_and_mark_reveal(player.dialogue_flags, move.id)
                if reveal is not None:
                    reveal_entry = CombatLogEntry(
                        round_number=self._state.round_number,
                        actor="player",
                        action=f"{move.name} (reveal)",
                        effects_applied=reveal.to_log_entries(),
                        hit=True,
                    )
                    self._state.combat_log.append(reveal_entry)
            except Exception:
                pass

        if dual_tech_logs:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action=move.name,
                effects_applied=dual_tech_logs,
                hit=True,
            )
            self._state.combat_log.append(entry)

        # Fire at Will, Power Drift, Total Commitment have no effects
        # payload — their entire work is done by the activation helpers
        # above. Skip the normal resolve pipeline so the engine doesn't
        # try to target an enemy with a zero-effect move.
        if move.id in ("fire_at_will", "power_drift", "total_commitment") and not move.effects:
            return [entry] if dual_tech_logs else []

        # Overdriven Weapon: 2x damage on next weapon attack (momentum 50% threshold)
        overdriven_active = False
        if (
            player.momentum
            and player.momentum.overdriven_available
            and any(e.type == EffectType.DAMAGE for e in move.effects)
        ):
            overdriven_active = True
            # Temporarily add a 100% damage boost
            boost = CombatEffect(
                type=EffectType.DAMAGE_BOOST,
                value=100.0,
                duration=1,
                target=EffectTarget.SELF,
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
        self,
        chosen_move_id: Optional[str] = None,
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
                            move,
                            player,
                            target,
                            f"crew:{move.id}",
                            player.get_effective_accuracy(),
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
                move,
                player,
                target,
                f"crew:{move.id}",
                player.get_effective_accuracy(),
            )
            all_logs.extend(logs)
            # Re-check survivors after each move
            surviving = self._state.surviving_enemies
            if not surviving:
                break

        return all_logs

    # ------------------------------------------------------------------
    # Crew combos
    # ------------------------------------------------------------------

    def execute_crew_combo(self, combo_id: str) -> list[CombatLogEntry]:
        """Execute a crew combo ability.

        Requires 25%+ momentum and sufficient energy. Counts as the
        crew action for this turn (replaces individual crew ability).

        Args:
            combo_id: ID of the combo to execute.

        Returns:
            Combat log entries from the combo's resolution.
        """
        from spacegame.models.crew_combos import get_combo_by_id
        from spacegame.models.momentum import THRESHOLD_CHARGED

        player = self._state.player
        combo = get_combo_by_id(combo_id)

        if combo is None:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="crew_combo",
                action="Unknown Combo",
                effects_applied=["Combo not found"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Check momentum threshold
        if player.momentum is None or player.momentum.current < THRESHOLD_CHARGED:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="crew_combo",
                action=combo.name,
                effects_applied=["Not enough momentum (need 25%)"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Check energy
        if player.energy < combo.energy_cost:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="crew_combo",
                action=combo.name,
                effects_applied=[f"Not enough energy (need {combo.energy_cost})"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Deduct energy
        player.energy -= combo.energy_cost

        # Resolve combo effects
        messages: list[str] = [f"COMBO: {combo.name}!"]
        surviving = self._state.surviving_enemies

        for effect in combo.effects:
            effect_type = effect.get("type", "")
            value = effect.get("value", 0)
            duration = effect.get("duration", 0)
            target = effect.get("target", "self")

            if effect_type == "hull_restore":
                restored = min(int(value), player.max_hull - player.hull)
                player.hull += restored
                messages.append(f"Restored {restored} hull")

            elif effect_type == "shield_restore":
                restored = min(int(value), player.max_shields - player.shields)
                player.shields += restored
                messages.append(f"Restored {restored} shields")

            elif effect_type == "energy_restore":
                restored = min(int(value), player.max_energy - player.energy)
                player.energy += restored
                messages.append(f"Restored {restored} energy")

            elif effect_type == "accuracy_mod":
                eff = CombatEffect(
                    type=EffectType.ACCURACY_MOD,
                    value=float(value),
                    duration=duration,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((eff, duration))
                messages.append(f"+{int(value)} accuracy for {duration} turn")

            elif effect_type == "damage_boost":
                eff = CombatEffect(
                    type=EffectType.DAMAGE_BOOST,
                    value=float(value),
                    duration=duration,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((eff, duration))
                messages.append(f"+{int(value)}% damage for {duration} turn")

            elif effect_type == "flee_bonus":
                player.flee_bonus += int(value)
                messages.append(f"+{int(value)}% flee chance")

            elif effect_type == "cleanse":
                # Remove negative effects (burn, chill, suppressed)
                negative_types = {EffectType.BURN, EffectType.CHILL, EffectType.SUPPRESSED}
                before = len(player.active_effects)
                player.active_effects = [
                    (eff, dur)
                    for eff, dur in player.active_effects
                    if eff.type not in negative_types
                ]
                removed = before - len(player.active_effects)
                messages.append(f"Cleansed {removed} debuffs")

            elif effect_type == "absorb":
                eff = CombatEffect(
                    type=EffectType.ABSORB,
                    value=1.0,
                    duration=1,
                    target=EffectTarget.SELF,
                )
                player.active_effects.append((eff, 99))  # Persists until consumed
                messages.append("Absorb shield deployed")

            elif effect_type == "reveal_stats":
                messages.append("All enemy stats revealed")

            elif effect_type == "energy_drain" and target == "single_enemy":
                if surviving:
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    drained = min(int(value), strongest.current_energy)
                    strongest.current_energy -= drained
                    messages.append(f"Drained {drained} energy from {strongest.template.name}")

        # Momentum: crew ability used
        self._add_player_momentum(MOMENTUM_ON_CREW_ABILITY, "crew combo")

        entry = CombatLogEntry(
            round_number=self._state.round_number,
            actor="crew_combo",
            action=f"COMBO: {combo.name}",
            effects_applied=messages,
            hit=True,
        )
        self._state.combat_log.append(entry)
        self._check_combat_end()
        return [entry]

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

        # Engine-destruction tempo skip (Combat C4 §11.2). Destroying the
        # engine subsystem grants one free turn. Mirrors the frozen path.
        from spacegame.models.enemy_subsystems import consume_engine_tempo_skip

        if consume_engine_tempo_skip(enemy):
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor=actor,
                action="Crippled",
                effects_applied=[f"{enemy.template.name} drifts, engines dark!"],
                hit=False,
            )
            self._state.combat_log.append(entry)
            return [entry]

        # Cowardly behavior: flee when hull is low (blocked if engine destroyed)
        if (
            enemy.template.behavior == EnemyBehavior.COWARDLY
            and enemy.hull_ratio <= enemy.template.flee_threshold
            and enemy.can_flee
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

        # CE-3 Wave 2: ``battle_damage_marker`` and similar environmental
        # complications scale enemy accuracy at the resolve site so the
        # multiplier composes cleanly with per-enemy effects.
        effective_accuracy = int(
            enemy.get_effective_accuracy() * self._state.enemy_accuracy_multiplier
        )
        return self._resolve_move(
            move,
            enemy,
            self._state.player,
            actor,
            effective_accuracy,
        )

    def _select_enemy_move(self, enemy: EnemyShip) -> Optional[CombatMove]:
        """Select a move based on enemy AI behavior.

        For bosses with phases, restricts available moves to the current
        phase's move_ids and uses the phase's behavior pattern.
        """
        # Boss phase-aware move filtering
        if (
            enemy.template.is_boss
            and enemy.template.phases
            and enemy.current_phase_idx < len(enemy.template.phases)
        ):
            phase = enemy.template.phases[enemy.current_phase_idx]
            phase_moves = [m for m in enemy.template.moves if m.id in phase.move_ids]
            available = [
                m
                for m in phase_moves
                if m.id not in enemy.cooldowns and enemy.current_energy >= m.energy_cost
            ]
            # Fall back to all moves if phase moves are all on cooldown
            if not available:
                available = [
                    m
                    for m in enemy.template.moves
                    if m.id not in enemy.cooldowns and enemy.current_energy >= m.energy_cost
                ]
            behavior_str = phase.behavior
        else:
            available = [
                m
                for m in enemy.template.moves
                if m.id not in enemy.cooldowns and enemy.current_energy >= m.energy_cost
            ]
            behavior_str = (
                enemy.template.behavior.value
                if hasattr(enemy.template.behavior, "value")
                else str(enemy.template.behavior)
            )

        if not available:
            return None

        # Map behavior string to enum for bosses with phase-specific behavior
        behavior = enemy.template.behavior
        if enemy.template.is_boss:
            behavior_map = {
                "aggressive": EnemyBehavior.AGGRESSIVE,
                "defensive": EnemyBehavior.DEFENSIVE,
                "evasive": EnemyBehavior.EVASIVE,
                "cowardly": EnemyBehavior.COWARDLY,
                "berserker": EnemyBehavior.AGGRESSIVE,  # Berserker = ultra-aggressive
                "tactical": EnemyBehavior.DEFENSIVE,  # Tactical = smart defensive
            }
            behavior = behavior_map.get(behavior_str, enemy.template.behavior)

        # Classify available moves
        offensive = [m for m in available if self._move_damage(m) > 0]
        defensive = [m for m in available if self._is_defensive_move(m)]
        evasive = [m for m in available if self._is_evasive_move(m)]
        debuff = [m for m in available if self._is_debuff_move(m)]

        # Player state awareness
        player = self._state.player
        player_shields_up = player.shields > 0
        player_low_hp = player.hull_ratio < 0.3

        if behavior == EnemyBehavior.AGGRESSIVE:
            # BRAWLER archetype: maximum damage, always.
            # When player is low, go for the kill with biggest hit.
            # When player shields are up, prefer shield-bypassing moves if available.
            # Counter: shields, evasion, cryo freeze
            if player_low_hp and offensive:
                # Go for the kill — pick the biggest single hit
                return max(offensive, key=lambda m: self._move_damage(m))
            if offensive:
                return max(offensive, key=lambda m: self._move_damage(m))
            return available[0]

        elif behavior == EnemyBehavior.DEFENSIVE:
            # SHIELD WALL archetype: sustain and outlast.
            # Prioritize shield/hull restore when damaged. Attack when healthy.
            # Below 30% hull: ALWAYS heal if possible.
            # Below 60% hull: 70% chance to heal, 30% to attack.
            # Above 60%: attack normally but prefer efficient moves.
            # Counter: ion weapons (melt shields), sustained pressure, voltaic suppression
            if enemy.hull_ratio < 0.3 and defensive:
                return defensive[0]
            if enemy.hull_ratio < 0.6 and defensive:
                if self._rng.random() < 0.7:
                    return defensive[0]
            # When shields are gone, prioritize shield restore over attack
            if enemy.current_shields <= 0 and defensive:
                shield_restores = [
                    m for m in defensive if any(e.type.value == "shield_restore" for e in m.effects)
                ]
                if shield_restores:
                    return shield_restores[0]
            if offensive:
                return max(offensive, key=lambda m: self._move_damage(m))
            return available[0]

        elif behavior == EnemyBehavior.EVASIVE:
            # INTERCEPTOR archetype: dodge then strike.
            # Open with evasion buff, then attack while buffed. Rebuff when it fades.
            # When healthy (>60%): alternate evasion buff and attack
            # When hurt (<40%): prioritize evasion to survive
            # Counter: AoE weapons (can't dodge), accuracy-boosted weapons
            if enemy.hull_ratio < 0.4 and evasive:
                # Survival mode — dodge everything
                return evasive[0]
            if evasive and self._state.round_number % 3 == 0:
                # Rebuff evasion every 3 rounds
                return evasive[0]
            if debuff and player_shields_up and self._rng.random() < 0.3:
                # Occasionally debuff instead of pure damage
                return debuff[0]
            if offensive:
                # Pick the highest damage attack
                return max(offensive, key=lambda m: self._move_damage(m))
            return available[0]

        # Default / COWARDLY (flee handled above; if still here, attack weakly)
        if offensive:
            # Cowardly enemies pick the cheapest (safest) attack
            return min(offensive, key=lambda m: m.energy_cost)
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
                hasattr(eff, "_frozen") and eff._frozen for eff, _ in enemy.active_effects
            )
            if is_frozen:
                enemy.telegraphed_move = None
                continue
            enemy.telegraphed_move = self._select_enemy_move(enemy)

    @staticmethod
    def _move_damage(move: CombatMove) -> float:
        """Total damage from a move's effects."""
        return sum(
            e.value
            for e in move.effects
            if e.type == EffectType.DAMAGE and e.target == EffectTarget.ENEMY
        )

    @staticmethod
    def _is_defensive_move(move: CombatMove) -> bool:
        """Whether a move is primarily defensive."""
        return any(
            e.type
            in (EffectType.SHIELD_RESTORE, EffectType.HULL_RESTORE, EffectType.DAMAGE_REDUCTION)
            for e in move.effects
        )

    @staticmethod
    def _is_evasive_move(move: CombatMove) -> bool:
        """Whether a move boosts evasion."""
        return any(
            e.type == EffectType.EVASION_MOD and e.target == EffectTarget.SELF for e in move.effects
        )

    @staticmethod
    def _is_debuff_move(move: CombatMove) -> bool:
        """Whether a move debuffs the enemy (energy drain, accuracy reduction, etc)."""
        return any(
            e.type in (EffectType.ENERGY_DRAIN, EffectType.ACCURACY_MOD, EffectType.SHIELD_DRAIN)
            and e.target == EffectTarget.ENEMY
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
                    move,
                    enemy,
                    player,
                    f"enemy:{idx}",
                    enemy.get_effective_accuracy(),
                    accuracy_penalty=FLEE_ACCURACY_PENALTY,
                )
                for log in parting_logs:
                    log.action = f"Parting Shot: {log.action}"
                logs.extend(parting_logs)

        # Flee roll
        avg_enemy_speed = sum(e.template.speed for e in self._state.surviving_enemies) / max(
            1, len(self._state.surviving_enemies)
        )
        flee_chance = max(
            FLEE_MIN_CHANCE,
            min(
                FLEE_MAX_CHANCE,
                FLEE_BASE_CHANCE
                + int((player.speed - avg_enemy_speed) * FLEE_SPEED_FACTOR)
                + player.flee_bonus,
            ),
        )
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
        base_cost = sum(e.template.bribe_cost for e in self._state.surviving_enemies)

        # Apply persuasion discount (10% per level, max 50%)
        discount = min(0.5, persuasion_level * 0.1)
        total_cost = int(base_cost * (1.0 - discount))

        if player_credits < total_cost:
            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="player",
                action="Bribe",
                effects_applied=[f"Insufficient credits ({player_credits:,} < {total_cost:,} CR)"],
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
        self,
        skill_id: str,
        social_manager: object,
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

        # Peacemaker capstone: reduce difficulty by 2 (always available)
        if self._skill_bonus("peaceful_resolution") > 0:
            difficulty = max(1, difficulty - 2)

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
                    type=EffectType.ACCURACY_MOD,
                    value=15.0,
                    duration=2,
                    target=EffectTarget.SELF,
                )
                self._state.player.active_effects.append((acc_buff, 2))
                # Reveal total bribe cost
                bribe_total = sum(e.template.bribe_cost for e in self._state.surviving_enemies)
                self._state.revealed_bribe_cost = bribe_total
                msg = (
                    f"Weakness revealed: +15 accuracy for 2 turns (bribe cost: {bribe_total:,} CR)"
                )
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

    def _evaluate_complications(self) -> list[CombatLogEntry]:
        """Run the complication resolver and surface events as log entries.

        Spawns reinforcements directly into ``state.enemies`` (respecting
        ``MAX_LIVING_ENEMIES``). Environmental and narration effects have
        already mutated ``state`` inside the resolver — this method only
        materializes player-visible output.
        """
        events = self._resolver.evaluate(self._state)
        logs: list[CombatLogEntry] = []
        if not events:
            return logs

        from spacegame.data_loader import get_data_loader

        for event in events:
            messages: list[str] = []
            if event.narration:
                messages.append(event.narration)

            if event.spawned_template_ids:
                dl = get_data_loader()
                living = sum(1 for e in self._state.enemies if e.is_alive and not e.is_fled)
                for tid in event.spawned_template_ids:
                    if living >= MAX_LIVING_ENEMIES:
                        messages.append(
                            f"Reinforcement call capped — {MAX_LIVING_ENEMIES} "
                            "enemies already engaged"
                        )
                        break
                    template = dl.enemy_templates.get(tid)
                    if template is None:
                        messages.append(f"Reinforcement call failed — unknown template '{tid}'")
                        continue
                    self._state.enemies.append(EnemyShip.from_template(template))
                    living += 1
                    messages.append(f"Reinforcement arrives: {template.name}")

            entry = CombatLogEntry(
                round_number=self._state.round_number,
                actor="system",
                action=f"Complication: {event.complication_id}",
                effects_applied=messages or [event.complication_id],
            )
            self._state.combat_log.append(entry)
            logs.append(entry)
        return logs

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

        # Dual tech (B8.3): tick turn-scoped flags and counters.
        try:
            from spacegame.models.dual_tech import tick_dual_tech_end_of_round

            messages.extend(tick_dual_tech_end_of_round(player))
        except Exception:
            pass

        # Legendary: Cooldown Reduction — extra cooldown tick
        if player._legendary:
            try:
                from spacegame.models.legendary_effects import apply_cooldown_reduction

                apply_cooldown_reduction(player._legendary, player.cooldowns)
            except Exception:
                pass

            # Legendary: Phase Shift per-round reset (spec §8).
            try:
                from spacegame.models.legendary_effects import reset_phase_shift_for_round

                reset_phase_shift_for_round(player._legendary)
            except Exception:
                pass

        # Sentinel capstone: shield break → restore 20%
        if (
            player.shield_break_vulnerable
            and player.defensive_identity == "sentinel"
            and self._skill_bonus("sentinel_capstone") > 0
            and player.max_shields > 0
        ):
            restored = int(player.max_shields * 0.20)
            player.shields += restored
            messages.append(f"Sentinel: shields restored +{restored}")

        # Passive shield regen (Phase 12A)
        if player.shield_regen > 0 and player.shields < player.max_shields:
            # CE-3 Wave 2: ``shield_harmonic`` and similar environmental
            # complications scale base regen. Floor at 0 so a degenerate
            # multiplier can't reverse the regen direction.
            base_regen = max(
                0,
                int(player.shield_regen * self._state.shield_regen_multiplier),
            )
            regen = min(base_regen, player.max_shields - player.shields)
            # Sentinel capstone: double regen when shields > 50%
            if (
                player.defensive_identity == "sentinel"
                and self._skill_bonus("sentinel_capstone") > 0
                and player.max_shields > 0
                and player.shields / player.max_shields > 0.50
            ):
                regen = min(regen * 2, player.max_shields - player.shields)
                messages.append(f"Sentinel surge: +{regen}")
            # Legendary: Forgeborn Bulwark — double regen when shields < 25%
            elif (
                player._legendary
                and player._legendary.low_shield_regen_mult > 1.0
                and player.max_shields > 0
                and player.shields / player.max_shields < 0.25
            ):
                regen = int(regen * player._legendary.low_shield_regen_mult)
                regen = min(regen, player.max_shields - player.shields)
                messages.append(f"Forgeborn regen surge: +{regen}")
            else:
                if regen > 0:
                    messages.append(f"Shield regen: +{regen}")
            if regen > 0:
                player.shields += regen

        # Reset evasion decay (Phase 12A — penalty clears each round)
        player.evasion_decay = 0

        # Reset shield break vulnerability (lasts 1 turn)
        player.shield_break_vulnerable = False

        # Sentinel Overcharge decay (shields above max decay by 10% of excess/turn)
        if player.shields > player.max_shields:
            excess = player.shields - player.max_shields
            decay = max(1, int(excess * 0.10))
            player.shields = max(player.max_shields, player.shields - decay)
            messages.append(f"Overshield decay: -{decay}")

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
        # CE-3 Wave 2: evaluate complications after the round counter
        # advances so the next round's turn_counter triggers fire here
        # rather than waiting for execute_player_turn. Idempotent thanks
        # to fired_complication_ids.
        logs.extend(self._evaluate_complications())
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

        # Separate offensive (target=ENEMY), self-buff (target=SELF),
        # ally-support (target=ALLY), and reinforcement-spawn effects.
        # Spawn effects are caster-invoked regardless of target — they
        # append to state.enemies, not hit any particular target, so
        # they bypass the target-based bucketing (Tier 3.E).
        spawn_effects = [e for e in move.effects if e.type == EffectType.SPAWN_REINFORCEMENT]
        non_spawn = [e for e in move.effects if e.type != EffectType.SPAWN_REINFORCEMENT]
        offensive_effects = [e for e in non_spawn if e.target == EffectTarget.ENEMY]
        self_effects = [e for e in non_spawn if e.target == EffectTarget.SELF]
        ally_effects = [e for e in non_spawn if e.target == EffectTarget.ALLY]

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
                    # CE-3 Wave 2: environmental complications
                    # (``asteroid_closure``, etc.) add a flat evasion delta.
                    # Floor at 0 in case multiple negative modifiers stack.
                    raw_evasion = max(0, raw_evasion + self._state.player_evasion_modifier)
                    # Ghost capstone: +30 evasion on first turn
                    if (
                        self._state.round_number == 1
                        and defender.defensive_identity == "ghost"
                        and self._skill_bonus("ghost_capstone") > 0
                    ):
                        raw_evasion += 30
                effective_evasion = raw_evasion
                if effective_evasion > 50:
                    effective_evasion = 50 + int((effective_evasion - 50) * 0.5)

                hit_chance = max(
                    HIT_CHANCE_MIN,
                    min(
                        HIT_CHANCE_MAX,
                        attacker_accuracy
                        + move.accuracy_modifier
                        - effective_evasion
                        - accuracy_penalty,
                    ),
                )

                # Legendary: Phase Shift — spec §8 "blocks first incoming
                # attack per round". Using consume_phase_shift ensures only
                # ONE dodge per round even with multi-enemy encounters.
                phase_shifted = False
                if isinstance(defender, PlayerCombatState) and defender._legendary:
                    try:
                        from spacegame.models.legendary_effects import consume_phase_shift

                        if consume_phase_shift(defender._legendary, self._state.round_number):
                            phase_shifted = True
                    except Exception:
                        pass

                if phase_shifted:
                    hit = False
                    graze = False
                    roll = 100
                    effects_applied.append("PHASE SHIFT: attack passes through empty space!")
                else:
                    roll = self._rng.randint(1, 100)
                    hit = roll <= hit_chance
                    graze = False

                # Graze system: miss by ≤10 → 30% damage.
                # Phase shift fully negates the attack — no graze leak.
                if not hit and not phase_shifted:
                    miss_margin = roll - hit_chance
                    if miss_margin <= 10:
                        graze = True
                    else:
                        # Clean miss — Ghost Counterstrike
                        if (
                            isinstance(defender, PlayerCombatState)
                            and defender.defensive_identity == "ghost"
                        ):
                            prev_stacks = defender.counterstrike_stacks
                            defender.counterstrike_stacks = min(
                                defender.counterstrike_stacks + 1, 3
                            )
                            if defender.counterstrike_stacks > prev_stacks:
                                pct = defender.counterstrike_stacks * 12
                                effects_applied.append(f"Counterstrike +{pct}%")

                        # Daring Gambit (B8.3): counter-on-dodge.
                        # If the player is the defender and the gambit
                        # counter window is open, punch 25 damage back
                        # at the attacker for the dodge.
                        if (
                            isinstance(defender, PlayerCombatState)
                            and getattr(defender, "daring_gambit_turns", 0) > 0
                            and not isinstance(attacker, PlayerCombatState)
                        ):
                            counter_msgs: list[str] = []
                            self._apply_direct_damage(
                                attacker,
                                25.0,
                                counter_msgs,
                                self._get_target_name(attacker),
                                attacker=defender,
                            )
                            effects_applied.append("Daring Gambit COUNTER: 25 damage returned")
                            effects_applied.extend(counter_msgs)

            if hit or graze:
                # Track if enemy was alive before applying effects
                enemy_was_alive = defender.is_alive if isinstance(defender, EnemyShip) else True

                # Crit system: player attacks can crit based on skill
                crit = False
                crit_mult = 1.0
                if hit and not graze and is_player_attack:
                    crit_pct = self._skill_bonus("crit_chance")  # 0.10/level
                    # Ghost capstone: consecutive unhit rounds = guaranteed crit
                    if (
                        isinstance(attacker, PlayerCombatState)
                        and attacker.defensive_identity == "ghost"
                        and self._skill_bonus("ghost_capstone") > 0
                        and attacker.counterstrike_stacks >= 2
                    ):
                        crit = True
                    elif crit_pct > 0 and self._rng.random() < crit_pct:
                        crit = True
                    # Juggernaut capstone: defender immune to crits above 75% hull
                    if (
                        crit
                        and isinstance(defender, PlayerCombatState)
                        and defender.defensive_identity == "juggernaut"
                        and defender.hull_ratio > 0.75
                        and self._skill_bonus("juggernaut_capstone") > 0
                    ):
                        crit = False  # Immunity
                    if crit:
                        crit_mult = 1.5
                        effects_applied.append("CRITICAL HIT!")

                # Graze damage: 30% normally, 15% with Light Foot level 2
                graze_mult = 0.30
                if graze and isinstance(defender, PlayerCombatState):
                    light_foot_lvl = self._skill_bonus("light_foot")
                    if light_foot_lvl >= 2:
                        graze_mult = 0.15

                # Apply effects with damage multiplier
                damage_mult = graze_mult if graze else crit_mult
                msgs = self._apply_effects(
                    offensive_effects,
                    defender,
                    actor_name,
                    attacker_state=attacker,
                    element=move.element,
                    damage_multiplier=damage_mult,
                )
                effects_applied.extend(msgs)

                if graze:
                    effects_applied.append(f"GRAZE (rolled {roll} vs {hit_chance}%)")

                # Identity passives on being hit
                if not is_player_attack and isinstance(defender, PlayerCombatState):
                    # Evasion decay: -5 evasion for 1 turn after being hit
                    # Light Foot level 1: no evasion decay
                    light_foot_lvl = self._skill_bonus("light_foot")
                    if light_foot_lvl < 1:
                        defender.evasion_decay = 5
                    # Ghost Counterstrike resets on being hit
                    if defender.defensive_identity == "ghost" and defender.counterstrike_stacks > 0:
                        defender.counterstrike_stacks = 0
                        effects_applied.append("Counterstrike reset!")
                    # Sentinel Shield Break detection
                    if (
                        defender.defensive_identity == "sentinel"
                        and defender.shields == 0
                        and not defender.shield_break_vulnerable
                    ):
                        defender.shield_break_vulnerable = True
                        effects_applied.append("SHIELDS BROKEN! +25% vulnerability")

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

            # Legendary: Chain Fire — chance for follow-up attack after a hit
            if hit and (actor_name == "player" or actor_name.startswith("crew:")):
                attacker_state = self._state.player
                if attacker_state._legendary and attacker_state._legendary.chain_fire_chance > 0:
                    try:
                        from spacegame.models.legendary_effects import process_chain_fire

                        # Get base damage from move's first DAMAGE effect
                        base_dmg = sum(e.value for e in move.effects if e.type == EffectType.DAMAGE)
                        triggered, mult = process_chain_fire(attacker_state._legendary, base_dmg)
                        if triggered:
                            chain_dmg = base_dmg * mult
                            chain_msgs: list[str] = [f"CHAIN FIRE! ({int(chain_dmg)} damage)"]
                            chain_target_name = self._get_target_name(defender)
                            self._apply_direct_damage(
                                defender,
                                chain_dmg,
                                chain_msgs,
                                chain_target_name,
                                attacker=attacker,
                            )
                            chain_entry = CombatLogEntry(
                                round_number=self._state.round_number,
                                actor=actor_name,
                                action="Chain Fire",
                                effects_applied=chain_msgs,
                                hit=True,
                            )
                            self._state.combat_log.append(chain_entry)
                            logs.append(chain_entry)
                    except Exception:
                        pass

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

        if ally_effects:
            # Pick the lowest-HP ally on the caster's team. For an enemy
            # caster, "ally" means another living enemy; for the player,
            # "ally" falls back to self (crew are part of PlayerCombatState).
            ally_target = self._select_ally_target(attacker, actor_name)
            if ally_target is None:
                # No ally available — graceful fallback: treat the caster
                # as the target (equivalent to self-heal). Logs a note so
                # players can tell the move found no teammate.
                ally_target = (
                    self._state.player
                    if actor_name == "player" or actor_name.startswith("crew:")
                    else attacker
                )
                no_ally_note = "no ally to support — redirected to self"
            else:
                no_ally_note = None

            msgs = self._apply_effects(ally_effects, ally_target, actor_name)
            if no_ally_note is not None:
                msgs = [no_ally_note, *msgs]

            # If the move ONLY contains ally effects (no offensive/self),
            # create a log entry now so the action surfaces to the player.
            if not offensive_effects and not self_effects:
                entry = CombatLogEntry(
                    round_number=self._state.round_number,
                    actor=actor_name,
                    action=move.name,
                    effects_applied=msgs,
                    hit=True,
                )
                self._state.combat_log.append(entry)
                logs.append(entry)

        if spawn_effects:
            # Reinforcement-spawn effects resolve as caster-invoked actions
            # outside the hit-roll system. Each effect spawns its configured
            # template (bounded by MAX_LIVING_ENEMIES).
            spawn_msgs: list[str] = []
            for spawn_effect in spawn_effects:
                spawn_msgs.extend(self._spawn_reinforcements(spawn_effect, actor_name))

            if not offensive_effects and not self_effects and not ally_effects:
                # Pure spawn move — log it so players see reinforcements arrive.
                entry = CombatLogEntry(
                    round_number=self._state.round_number,
                    actor=actor_name,
                    action=move.name,
                    effects_applied=spawn_msgs,
                    hit=True,
                )
                self._state.combat_log.append(entry)
                logs.append(entry)

        # Check boss phase transitions after damage resolution
        phase_logs = self._check_boss_phase_transitions()
        logs.extend(phase_logs)

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
        for i, (eff, _dur) in enumerate(target.active_effects):
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

                # Weapon Specialization skill: +10% damage per level
                if isinstance(atk, PlayerCombatState):
                    weapon_dmg_bonus = self._skill_bonus("weapon_damage")
                    if weapon_dmg_bonus > 0:
                        raw *= 1.0 + weapon_dmg_bonus

                # Crew combat damage bonus (Leadership): +15% per level
                if source_name.startswith("crew:"):
                    crew_dmg_bonus = self._skill_bonus("crew_combat_damage")
                    if crew_dmg_bonus > 0:
                        raw *= 1.0 + crew_dmg_bonus

                # Attacker identity bonuses
                if isinstance(atk, PlayerCombatState):
                    # Juggernaut: below 25% hull = damage boost
                    # Capstone upgrades +15% → +25%
                    if atk.defensive_identity == "juggernaut" and atk.hull_ratio < 0.25:
                        boost = 0.25 if self._skill_bonus("juggernaut_capstone") > 0 else 0.15
                        raw *= 1.0 + boost
                    # Ghost Counterstrike: base +12% per stack
                    # counterstrike_bonus skill adds +5% per level per stack
                    if atk.defensive_identity == "ghost" and atk.counterstrike_stacks > 0:
                        per_stack = 0.12 + self._skill_bonus("counterstrike_bonus")
                        raw *= 1.0 + per_stack * atk.counterstrike_stacks

                # Defender identity modifiers
                if isinstance(target, PlayerCombatState):
                    # Ghost Light Frame Vulnerability: +10% incoming (reduced from 15%)
                    if target.defensive_identity == "ghost":
                        raw *= 1.10
                    # Juggernaut Structural Integrity: -5% DR when hull > 75%
                    if target.defensive_identity == "juggernaut" and target.hull_ratio > 0.75:
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
                    self._apply_direct_damage(
                        target, reduced, messages, target_name, attacker=attacker_state
                    )
                    # Apply Burn stack (stacks to 3, each lasts 3 turns)
                    burn_effect = CombatEffect(
                        type=EffectType.BURN,
                        value=burn_per_turn,
                        duration=3,
                        target=EffectTarget.ENEMY,
                    )
                    self._apply_stacking_effect(target, burn_effect, max_stacks=3)
                    messages.append(f"Burn: {int(burn_per_turn)}/turn for 3 turns")
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
                    self._apply_direct_damage(
                        target, reduced, messages, target_name, attacker=attacker_state
                    )
                    chill_effect = CombatEffect(
                        type=EffectType.CHILL,
                        value=5.0,  # -5 evasion per stack
                        duration=4,
                        target=EffectTarget.ENEMY,
                    )
                    chill_count = self._apply_stacking_effect(target, chill_effect, max_stacks=3)
                    messages.append(f"Chill x{chill_count}")
                    if source_name == "player" or source_name.startswith("crew:"):
                        self._add_player_momentum(MOMENTUM_ON_STATUS_APPLIED, "chill applied")
                    if chill_count >= 3:
                        # Boss immunity: check if target is immune to frozen
                        immune_to_frozen = False
                        if isinstance(target, EnemyShip) and target.template.is_boss:
                            immune_to_frozen = "frozen" in target.template.immune_to

                        if immune_to_frozen:
                            self._clear_effect_type(target, EffectType.CHILL)
                            messages.append(f"{target_name} resists being frozen!")
                        else:
                            # Frozen! Enemy loses next turn — clear all Chill stacks
                            self._clear_effect_type(target, EffectType.CHILL)
                            # Mark frozen by setting a special 1-turn skip flag
                            frozen_effect = CombatEffect(
                                type=EffectType.CHILL,
                                value=0.0,
                                duration=1,
                                target=EffectTarget.ENEMY,
                            )
                            frozen_effect._frozen = True  # type: ignore[attr-defined]
                            target.active_effects.append((frozen_effect, 1))
                            messages.append("FROZEN! Skips next turn")

                elif eff_element == WeaponElement.VOLTAIC:
                    # 85% damage + Suppressed stack
                    reduced = raw * 0.85 * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(
                        target, reduced, messages, target_name, attacker=attacker_state
                    )
                    suppress_effect = CombatEffect(
                        type=EffectType.SUPPRESSED,
                        value=12.0,  # -12% damage per stack
                        duration=3,
                        target=EffectTarget.ENEMY,
                    )
                    # Boss-specific Suppressed cap
                    max_sup = 3
                    if isinstance(target, EnemyShip) and target.template.is_boss:
                        max_sup = target.template.max_suppressed_stacks
                    sup_count = self._apply_stacking_effect(
                        target, suppress_effect, max_stacks=max_sup
                    )
                    messages.append(f"Suppressed x{sup_count} (-{sup_count * 12}% damage)")
                    if source_name == "player" or source_name.startswith("crew:"):
                        self._add_player_momentum(MOMENTUM_ON_STATUS_APPLIED, "suppressed applied")

                else:
                    # Kinetic (default) — pure direct damage
                    reduced = raw * (1.0 - min(damage_reduction, 0.9))
                    self._apply_direct_damage(
                        target, reduced, messages, target_name, attacker=attacker_state
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
                    # Sentinel Overcharge: can push shields to 150% of max
                    shield_cap = target.max_shields
                    if target.defensive_identity == "sentinel":
                        shield_cap = int(target.max_shields * 1.5)
                    restored = min(int(effect.value), shield_cap - target.shields)
                    restored = max(0, restored)
                    target.shields += restored
                    if target.shields > target.max_shields:
                        messages.append(
                            f"Overcharged! Shields at {target.shields}/{target.max_shields}"
                        )
                else:
                    restored = min(int(effect.value), target.max_shields - target.current_shields)
                    target.current_shields += restored
                messages.append(f"Restored {restored} shields on {target_name}")

            elif effect.type == EffectType.HULL_RESTORE:
                if isinstance(target, PlayerCombatState):
                    restored = min(int(effect.value), target.max_hull - target.hull)
                    target.hull += restored
                else:
                    restored = min(int(effect.value), target.template.hull - target.current_hull)
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
                    EffectType.BURN,
                    EffectType.CHILL,
                    EffectType.SUPPRESSED,
                }
                before = len(target.active_effects)
                target.active_effects = [
                    (eff, dur)
                    for eff, dur in target.active_effects
                    if eff.type not in negative_types
                    or (eff.target == EffectTarget.SELF and eff.value >= 0)
                ]
                removed = before - len(target.active_effects)
                if removed > 0:
                    messages.append(
                        f"Cleansed {removed} negative effect{'s' if removed > 1 else ''}"
                    )
                else:
                    messages.append("No negative effects to cleanse")

            elif effect.type == EffectType.ABSORB:
                # Add absorb shield: next incoming hit is nullified
                target.active_effects.append((effect, max(1, effect.duration)))
                messages.append("Countermeasures deployed — next hit absorbed")

            # SPAWN_REINFORCEMENT is handled by _resolve_move's dedicated
            # spawn-effects bucket (Tier 3.E) — it's caster-invoked and
            # target-independent, so it doesn't flow through _apply_effects.

        return messages

    def _spawn_reinforcements(
        self,
        effect: "CombatEffect",
        source_name: str,
    ) -> list[str]:
        """Append N reinforcement enemies to state.enemies for the given effect.

        Respects ``MAX_LIVING_ENEMIES`` — spawns are silently capped so a
        badly-tuned template can't flood the arena. Caller already holds
        the move-cooldown gate; no additional rate limiting here.

        Returns per-spawn log messages (one per successful spawn, plus a
        capped-out note when the cap is hit before the requested count).
        """
        template_id = effect.metadata.get("template_id", "")
        count = max(1, int(effect.value))
        messages: list[str] = []

        if not template_id:
            messages.append("Reinforcement call failed — no template specified")
            return messages

        # Lazy import to avoid a circular dependency at module load.
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        template = dl.enemy_templates.get(template_id)
        if template is None:
            messages.append(f"Reinforcement call failed — unknown template '{template_id}'")
            return messages

        living = sum(1 for e in self._state.enemies if e.is_alive and not e.is_fled)
        spawned = 0
        for _ in range(count):
            if living >= MAX_LIVING_ENEMIES:
                messages.append(
                    f"Reinforcement call capped — {MAX_LIVING_ENEMIES} enemies already engaged"
                )
                break
            new_enemy = EnemyShip.from_template(template)
            self._state.enemies.append(new_enemy)
            living += 1
            spawned += 1
        if spawned > 0:
            messages.append(
                f"Reinforcement arrives: {template.name}" + (f" ×{spawned}" if spawned > 1 else "")
            )
        return messages

    @staticmethod
    def _apply_direct_damage(
        target: PlayerCombatState | EnemyShip,
        reduced: float,
        messages: list[str],
        target_name: str,
        attacker: "PlayerCombatState | EnemyShip | None" = None,
    ) -> None:
        """Apply direct damage to a target's shields then hull.

        Applies armor reduction (flat damage subtraction) before shield/hull split.
        Burn DoT and other bypass-armor effects should reduce damage before calling.

        Args:
            attacker: When set, B8.3 armor-pierce (Crew Sync) is checked on
                player-attacker. DOT-style callers pass None to skip the check.
        """
        # Crew Sync armor-pierce (B8.3): player attacks bypass armor this turn.
        armor_pierced = isinstance(attacker, PlayerCombatState) and getattr(
            attacker, "armor_pierce_active", False
        )

        # Armor: flat reduction per hit (minimum 1 damage)
        armor = 0
        if isinstance(target, PlayerCombatState):
            armor = target.armor
            # Juggernaut Last Stand: +2 armor when below 25% hull
            if target.defensive_identity == "juggernaut" and target.hull_ratio < 0.25:
                armor += 2
        elif hasattr(target, "template"):
            armor = getattr(target.template, "combat_armor", 0)

        if armor_pierced and armor > 0:
            messages.append(f"Armor pierce: ignored {armor} armor")
            armor = 0

        if armor > 0 and reduced > 0:
            armor_absorbed = min(armor, reduced - 1)  # Always deal at least 1
            reduced = max(1.0, reduced - armor)
            if armor_absorbed > 0:
                messages.append(f"Armor absorbed {int(armor_absorbed)}")

        if isinstance(target, PlayerCombatState):
            shield_absorbed = min(target.shields, reduced)
            hull_damage = reduced - shield_absorbed
            target.shields = max(0, target.shields - int(shield_absorbed))

            # Total Commitment (B8.3): intercept hull hits, convert to armor.
            # Must happen BEFORE Legendary Void Absorption / module-damage
            # routing so the incoming hit is logically absorbed first.
            if hull_damage > 0 and getattr(target, "total_commitment_hits_remaining", 0) > 0:
                try:
                    from spacegame.models.dual_tech import (
                        intercept_total_commitment_hull_damage,
                    )

                    remaining, tc_logs = intercept_total_commitment_hull_damage(
                        target, int(hull_damage)
                    )
                    hull_damage = float(remaining)
                    messages.extend(tc_logs)
                except Exception:
                    pass

            # Legendary: Heat Hardening — gain armor when shields absorb damage
            if shield_absorbed > 0 and target._legendary:
                try:
                    from spacegame.models.legendary_effects import process_heat_hardening

                    armor_gained = process_heat_hardening(target._legendary, int(shield_absorbed))
                    if armor_gained > 0:
                        target.armor += armor_gained
                        messages.append(
                            f"Heat Hardening: +{armor_gained} armor (stack {target._legendary.heat_stacks})"
                        )
                except Exception:
                    pass

            # Legendary: Void Absorption — store portion of hull damage as charge
            if hull_damage > 0 and target._legendary:
                try:
                    from spacegame.models.legendary_effects import process_void_absorption

                    absorbed_void = process_void_absorption(target._legendary, int(hull_damage))
                    if absorbed_void > 0:
                        messages.append(
                            f"Void Absorption: +{absorbed_void} charge (total: {target._legendary.void_charge})"
                        )
                except Exception:
                    pass

            # Module-targeted damage: route hull damage through modules
            module_hit_msg = ""
            if hull_damage > 0 and target.module_states:
                try:
                    from spacegame.models.module_combat import (
                        apply_module_damage,
                        check_severing,
                        get_disable_effects,
                        resolve_module_hit,
                    )

                    hit_idx = (
                        resolve_module_hit(
                            target._ship_build,
                            target._module_catalog,
                            target.module_states,
                        )
                        if target._ship_build
                        else None
                    )

                    if hit_idx is not None and hit_idx < len(target.module_states):
                        mod_state = target.module_states[hit_idx]
                        was_disabled = mod_state.disabled
                        module_hit_msg, excess_dmg = apply_module_damage(
                            mod_state, int(hull_damage)
                        )
                        # Apply disable effects if newly disabled
                        if mod_state.disabled and not was_disabled:
                            effects = get_disable_effects(mod_state.category)
                            if "accuracy_mult" in effects:
                                target.accuracy = int(target.accuracy * effects["accuracy_mult"])
                            if "evasion_mult" in effects:
                                target.evasion = int(target.evasion * effects["evasion_mult"])
                            if "speed_mult" in effects:
                                target.speed = int(target.speed * effects["speed_mult"])
                            if "shield_mult" in effects:
                                target.shields = int(target.shields * effects["shield_mult"])
                                target.max_shields = int(
                                    target.max_shields * effects["shield_mult"]
                                )
                            # Weapon offline: remove combat move from available moves
                            if effects.get("weapon_offline") and target._ship_build:
                                placed_mod = target._ship_build.placed_slots[mod_state.placed_index]
                                offline_uid = getattr(placed_mod, "equipped_part_id", None)
                                if offline_uid:
                                    target.equipment_moves = [
                                        m for m in target.equipment_moves if m.id != offline_uid
                                    ]
                                    module_hit_msg += f" {offline_uid} offline!"
                            # Check for structural severing
                            if target._ship_build:
                                severed = check_severing(
                                    target._ship_build,
                                    target._module_catalog,
                                    target.module_states,
                                )
                                if severed:
                                    sev_names = [target.module_states[s].category for s in severed]
                                    module_hit_msg += f" SEVERED: {', '.join(sev_names)} cut off!"

                        # Overkill propagation: excess damage → hull + chain
                        if excess_dmg > 0:
                            messages.append(f"Excess damage: {excess_dmg} to hull")
                            # Chain damage to adjacent module
                            from spacegame.models.module_combat import (
                                build_adjacency_map,
                                process_overkill_chain,
                            )

                            if not hasattr(target, "_adjacency_map"):
                                target._adjacency_map = (
                                    build_adjacency_map(
                                        target._ship_build,
                                        target._module_catalog,
                                    )
                                    if target._ship_build
                                    else {}
                                )
                            chain = process_overkill_chain(
                                excess_dmg,
                                hit_idx,
                                target.module_states,
                                target._adjacency_map,
                            )
                            if chain:
                                chain_target = target.module_states[chain["target_idx"]]
                                _chain_msg, _ = apply_module_damage(
                                    chain_target,
                                    chain["damage"],
                                )
                                messages.append(chain["message"])
                                if chain_target.disabled:
                                    chain_fx = get_disable_effects(chain_target.category)
                                    if "accuracy_mult" in chain_fx:
                                        target.accuracy = int(
                                            target.accuracy * chain_fx["accuracy_mult"]
                                        )
                                    if "evasion_mult" in chain_fx:
                                        target.evasion = int(
                                            target.evasion * chain_fx["evasion_mult"]
                                        )

                except Exception:
                    pass  # module_combat not available or error

            target.hull = max(0, target.hull - int(hull_damage))
        else:
            shield_absorbed = min(target.current_shields, reduced)
            hull_damage = reduced - shield_absorbed
            target.current_shields = max(0, target.current_shields - int(shield_absorbed))
            target.current_hull = max(0, target.current_hull - int(hull_damage))

            # Subsystem damage routing (Combat C4 §11.2). When the player
            # has a focused subsystem on this enemy, the same hull-damage
            # amount chips the subsystem's HP. Destruction applies the
            # subsystem's mechanical effect + logs it.
            focused = getattr(target, "focused_subsystem", None)
            if focused and hull_damage > 0:
                from spacegame.models.enemy_subsystems import (
                    apply_subsystem_damage,
                    apply_subsystem_destruction,
                )

                destroyed_effect = apply_subsystem_damage(target, int(hull_damage), focused)
                if destroyed_effect is not None:
                    destruction_msgs = apply_subsystem_destruction(target, destroyed_effect)
                    messages.extend(destruction_msgs)
                    # Clear focus after destruction so next attack
                    # doesn't try to re-damage a dead subsystem.
                    target.focused_subsystem = None

        module_hit_msg = module_hit_msg if isinstance(target, PlayerCombatState) else ""
        damage_msg = (
            f"Dealt {int(reduced)} damage to {target_name} "
            f"({int(shield_absorbed)} shields, {int(hull_damage)} hull)"
        )
        if module_hit_msg:
            damage_msg += f" [{module_hit_msg}]"
        messages.append(damage_msg)

    def _apply_stacking_effect(
        self,
        target: PlayerCombatState | EnemyShip,
        effect: CombatEffect,
        max_stacks: int = 3,
    ) -> int:
        """Apply a stacking status effect, enforcing the stack cap.

        Elemental Affinity skill extends duration by 1 turn when player
        applies effects to enemies.

        Returns:
            Current stack count after application.
        """
        # Elemental Affinity: +1 duration when player applies to enemy
        duration = effect.duration
        if isinstance(target, EnemyShip):
            dur_bonus = int(self._skill_bonus("elemental_duration_bonus"))
            duration += dur_bonus

        # Count existing stacks of this effect type
        current_stacks = sum(1 for eff, _ in target.active_effects if eff.type == effect.type)
        if current_stacks < max_stacks:
            target.active_effects.append((effect, duration))
            current_stacks += 1
        else:
            # Refresh the oldest stack's duration instead of adding a new one
            for i, (eff, _) in enumerate(target.active_effects):
                if eff.type == effect.type:
                    target.active_effects[i] = (effect, duration)
                    break
        return current_stacks

    @staticmethod
    def _clear_effect_type(
        target: PlayerCombatState | EnemyShip,
        effect_type: EffectType,
    ) -> None:
        """Remove all stacks of a specific effect type from a target."""
        target.active_effects = [
            (eff, dur) for eff, dur in target.active_effects if eff.type != effect_type
        ]

    def _get_target_name(self, target: PlayerCombatState | EnemyShip) -> str:
        """Get a display name for a target."""
        if isinstance(target, PlayerCombatState):
            return "Player"
        return target.template.name

    def _consume_overdriven_boost(self, player: PlayerCombatState) -> None:
        """Remove the temporary Overdriven damage boost and consume the buff."""
        player.active_effects = [
            (eff, dur)
            for eff, dur in player.active_effects
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

    def _resolve_ultimate_effects(self, ultimate: "ShipUltimate") -> list[CombatLogEntry]:
        """Resolve the mechanical effects of a ship ultimate.

        Args:
            ultimate: The ultimate ability definition.

        Returns:
            Combat log entries from the resolution.
        """

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
                    self._apply_direct_damage(enemy, float(dmg), messages, enemy.template.name)
                    messages.append(f"{enemy.template.name}: {dmg} damage")

            elif effect_type == "damage" and target == "single_enemy":
                if surviving:
                    # Target strongest (highest current HP) enemy
                    strongest = max(surviving, key=lambda e: e.current_hull + e.current_shields)
                    dmg = int(value)
                    if effect.get("ignores_shields"):
                        strongest.current_hull = max(0, strongest.current_hull - dmg)
                        messages.append(
                            f"{strongest.template.name}: {dmg} damage (bypassed shields)"
                        )
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
                        burn_eff = CombatEffect(type=EffectType.BURN, value=7.0, duration=3)
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
                    best_move = max(
                        strongest.template.moves,
                        key=lambda m: sum(
                            e.value for e in m.effects if e.type == EffectType.DAMAGE
                        ),
                        default=None,
                    )
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

    def _check_boss_phase_transitions(self) -> list[CombatLogEntry]:
        """Check if any boss enemies should transition to a new phase.

        Called after damage is dealt. Compares current total HP ratio
        against phase thresholds and advances to the next phase if needed.

        Returns:
            Log entries for phase transitions (with flavor text and effects).
        """
        logs: list[CombatLogEntry] = []
        for enemy in self._state.enemies:
            if not enemy.template.is_boss or not enemy.is_alive:
                continue
            if not enemy.template.phases:
                continue

            hp_ratio = enemy.total_hp_ratio
            phases = enemy.template.phases

            # Find the latest phase we should be in (phases are ordered by descending threshold)
            target_phase_idx = 0
            for i, phase in enumerate(phases):
                if hp_ratio <= phase.hp_threshold:
                    target_phase_idx = i

            # If we need to advance (can skip multiple phases on a huge hit)
            while enemy.current_phase_idx < target_phase_idx:
                enemy.current_phase_idx += 1
                new_phase = phases[enemy.current_phase_idx]

                messages: list[str] = [f"PHASE SHIFT: {new_phase.name}"]
                if new_phase.on_enter_text:
                    messages.append(new_phase.on_enter_text)

                # Apply on_enter_effects
                if new_phase.on_enter_effect:
                    effect_msg = self._apply_boss_phase_effect(enemy, new_phase.on_enter_effect)
                    if effect_msg:
                        messages.append(effect_msg)

                entry = CombatLogEntry(
                    round_number=self._state.round_number,
                    actor=f"boss:{enemy.template.id}",
                    action=f"Phase Shift: {new_phase.name}",
                    effects_applied=messages,
                    hit=True,
                )
                self._state.combat_log.append(entry)
                logs.append(entry)

        return logs

    def _apply_boss_phase_effect(self, enemy: EnemyShip, effect_id: str) -> str:
        """Apply a boss phase transition effect.

        Args:
            enemy: The boss enemy.
            effect_id: The effect identifier string.

        Returns:
            Human-readable message describing what happened.
        """
        if effect_id == "damage_boost_50":
            eff = CombatEffect(
                type=EffectType.DAMAGE_BOOST,
                value=50.0,
                duration=99,
                target=EffectTarget.SELF,
            )
            enemy.active_effects.append((eff, 99))
            return "Damage increased by 50%!"

        if effect_id == "damage_boost_50_defense_minus_30":
            boost = CombatEffect(
                type=EffectType.DAMAGE_BOOST,
                value=50.0,
                duration=99,
                target=EffectTarget.SELF,
            )
            enemy.active_effects.append((boost, 99))
            return "Berserk! +50% damage, defenses lowered!"

        if effect_id == "spawn_pirate_scout":
            # Conceptual — reinforcement spawning is complex (needs UI coordination)
            # For now, log the intent; actual spawn handled by view layer
            return "Reinforcements incoming!"

        return ""

    def _check_combat_end(self) -> None:
        """Check if combat has ended (victory or defeat)."""
        if self._state.result != CombatResult.IN_PROGRESS:
            return
        if not self._state.player.is_alive:
            self._state.result = CombatResult.DEFEAT
        elif self._state.all_enemies_defeated:
            self._state.result = CombatResult.VICTORY
            # Check for boss trophy drops (Phase D2)
            self._check_boss_trophy_drops()

    def _check_boss_trophy_drops(self) -> None:
        """Award trophy shapes and legendary modules from defeated boss enemies."""
        for enemy in self._state.enemies:
            if not enemy.is_alive and enemy.template.is_boss:
                trophy_id = enemy.template.trophy_drop
                if trophy_id:
                    # Store pending trophy for game.py to process
                    if not hasattr(self._state, "_pending_trophy_drops"):
                        self._state._pending_trophy_drops = []
                    self._state._pending_trophy_drops.append(
                        {
                            "shape_id": trophy_id,
                            "boss_name": enemy.template.name,
                        }
                    )
                # Legendary module trophy drop
                try:
                    from spacegame.models.builder_discovery import BOSS_TROPHY_MODULES

                    legendary_mod = BOSS_TROPHY_MODULES.get(enemy.template.id)
                    if legendary_mod:
                        if not hasattr(self._state, "_pending_module_trophy_drops"):
                            self._state._pending_module_trophy_drops = []
                        self._state._pending_module_trophy_drops.append(
                            {
                                "module_id": legendary_mod,
                                "boss_name": enemy.template.name,
                            }
                        )
                except ImportError:
                    pass

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_available_moves(self) -> list[CombatMove]:
        """Get equipment moves that are off cooldown and affordable."""
        player = self._state.player
        return [
            m
            for m in player.equipment_moves
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
        """Find a move by ID across equipment, crew, and dual tech moves."""
        for m in self._state.player.equipment_moves:
            if m.id == move_id:
                return m
        for m in self._state.player.crew_moves:
            if m.id == move_id:
                return m
        for m in getattr(self._state.player, "dual_tech_moves", []):
            if m.id == move_id:
                return m
        return None

    def _select_ally_target(
        self,
        attacker: "PlayerCombatState | EnemyShip",
        actor_name: str,
    ) -> Optional["EnemyShip"]:
        """Pick the lowest-HP living ally for an ALLY-targeted effect.

        Tier 3.D: enemies can now heal allies (e.g., medical_relay). For
        an enemy caster, "ally" means another enemy that is alive, not
        fled, and not the caster itself. Hull ratio breaks ties so
        critically-wounded teammates are prioritized over mildly damaged
        ones.

        The player side has no distinct allies in the current model —
        crew are folded into PlayerCombatState — so ally-targeted moves
        from a player source resolve to no ally (caller redirects to
        self). This keeps the API uniform but declines to invent a crew-
        selection mechanic that doesn't exist elsewhere.

        Args:
            attacker: The caster. Either PlayerCombatState or EnemyShip.
            actor_name: Actor string ("player", "crew:<id>", or enemy tag).

        Returns:
            An EnemyShip if an ally is available, else None.
        """
        # Player side: no separate allies in the model.
        if actor_name == "player" or actor_name.startswith("crew:"):
            return None

        candidates = [
            e for e in self._state.enemies if e is not attacker and e.is_alive and not e.is_fled
        ]
        if not candidates:
            return None

        def _hull_ratio(e: "EnemyShip") -> float:
            max_hull = max(1, e.template.hull)
            return e.current_hull / max_hull

        candidates.sort(key=_hull_ratio)
        return candidates[0]
