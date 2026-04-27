"""Combat action queue for multi-action turns.

Allows players to queue multiple combat actions per turn, gated by
energy budget, cooldowns, and once-per-weapon-per-turn rules.
The queue is built during the player's action phase and then
executed sequentially before enemies act.

Part of Systems Unification — Phase U2.5a.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spacegame.models.combat import CombatMove


@dataclass
class QueuedAction:
    """A single action queued for execution this turn."""

    move_id: str
    target_idx: int  # -1 for self-targeted abilities
    energy_cost: int
    move_name: str = ""
    slot_key: str = ""  # Per-slot unique key for cooldown/dedup tracking


class ActionQueue:
    """Manages the player's queued actions for a single combat turn.

    The queue validates each action against energy budget, cooldown
    state, and the once-per-weapon-per-turn rule. Actions are resolved
    in order by the combat engine.

    Args:
        energy_available: Player's current energy at start of turn.
        cooldowns: Current cooldown dict {move_id: turns_remaining}.
    """

    def __init__(
        self,
        energy_available: int,
        cooldowns: Optional[dict[str, int]] = None,
        extra_action: bool = False,
    ) -> None:
        self._energy_available = energy_available
        self._energy_committed = 0
        self._cooldowns = dict(cooldowns) if cooldowns else {}
        self._actions: list[QueuedAction] = []
        self._used_this_turn: set[str] = set()
        self._extra_action_available = extra_action  # Volley Commander skill
        # B8.4: once Fire at Will is queued, subsequent weapon adds apply
        # the 50% energy discount so the player can pre-plan bigger alphas.
        self._fire_at_will_queued: bool = False

    @property
    def actions(self) -> list[QueuedAction]:
        """The ordered list of queued actions."""
        return list(self._actions)

    @property
    def energy_remaining(self) -> int:
        """Energy available after all queued actions."""
        return self._energy_available - self._energy_committed

    @property
    def energy_committed(self) -> int:
        """Total energy spent by queued actions."""
        return self._energy_committed

    @property
    def is_empty(self) -> bool:
        """Whether the queue has no actions."""
        return len(self._actions) == 0

    def get_queued_move_ids(self) -> set[str]:
        """Get the set of move IDs currently queued."""
        return set(self._used_this_turn)

    def add(
        self,
        move_id: str,
        target_idx: int,
        move: CombatMove,
    ) -> tuple[bool, str]:
        """Add an action to the queue.

        Validates energy budget, cooldown, and once-per-turn rule.

        Args:
            move_id: The combat move ID.
            target_idx: Target enemy index (-1 for self-targeted).
            move: The CombatMove object for energy cost reference.

        Returns:
            (success, message) tuple.
        """
        # Use slot_key for per-slot independent cooldowns/once-per-turn
        queue_key = getattr(move, "slot_key", "") or move_id

        # Once-per-turn check (per slot, not per move name)
        # Volley Commander: allow one weapon to bypass this restriction
        if queue_key in self._used_this_turn:
            if self._extra_action_available:
                self._extra_action_available = False  # Consumed
            else:
                return False, f"{move.name} already queued this turn"

        # Cooldown check (per slot)
        if queue_key in self._cooldowns and self._cooldowns[queue_key] > 0:
            remaining = self._cooldowns[queue_key]
            return False, f"{move.name} on cooldown ({remaining} turns)"

        # B8.4: apply Fire at Will discount to weapons queued after FAW.
        effective_cost = self._effective_cost(move)

        # Energy check
        if effective_cost > self.energy_remaining:
            return False, (
                f"Not enough energy for {move.name} "
                f"({effective_cost} needed, {self.energy_remaining} available)"
            )

        # Add to queue
        action = QueuedAction(
            move_id=move_id,
            target_idx=target_idx,
            energy_cost=effective_cost,
            move_name=move.name,
            slot_key=queue_key,
        )
        self._actions.append(action)
        self._energy_committed += effective_cost
        self._used_this_turn.add(queue_key)

        if move_id == "fire_at_will":
            self._fire_at_will_queued = True

        return True, f"Queued: {move.name}"

    def _effective_cost(self, move: CombatMove) -> int:
        """Return the energy cost after any queued-earlier dual tech discounts."""
        base = int(move.energy_cost)
        # Fire at Will halves weapon energy when queued earlier this turn.
        # A weapon is any move with a damage effect.
        if self._fire_at_will_queued:
            is_weapon = any(
                getattr(e, "type", None) is not None and getattr(e.type, "value", "") == "damage"
                for e in move.effects
            )
            if is_weapon:
                return max(0, base // 2)
        return base

    def remove_last(self) -> bool:
        """Remove the last queued action and refund its energy.

        Returns:
            True if an action was removed, False if queue was empty.
        """
        if not self._actions:
            return False

        removed = self._actions.pop()
        self._energy_committed -= removed.energy_cost
        self._used_this_turn.discard(removed.slot_key or removed.move_id)
        return True

    def clear(self) -> None:
        """Clear all queued actions and refund all energy."""
        self._actions.clear()
        self._energy_committed = 0
        self._used_this_turn.clear()
        self._fire_at_will_queued = False

    def can_add(
        self,
        move_id: str,
        move: CombatMove,
    ) -> tuple[bool, str]:
        """Check if a move can be added without actually adding it.

        Args:
            move_id: The combat move ID.
            move: The CombatMove for cost reference.

        Returns:
            (can_add, reason) tuple.
        """
        queue_key = getattr(move, "slot_key", "") or move_id
        if queue_key in self._used_this_turn:
            return False, "Already queued this turn"
        if queue_key in self._cooldowns and self._cooldowns[queue_key] > 0:
            return False, f"On cooldown ({self._cooldowns[queue_key]})"
        if self._effective_cost(move) > self.energy_remaining:
            return False, "Not enough energy"
        return True, "OK"
