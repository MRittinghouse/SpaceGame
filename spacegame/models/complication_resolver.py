"""CE-3: combat complication resolver.

Evaluates attached ``CombatComplication`` instances against the current
``CombatState`` at well-defined points in combat resolution. When a
complication's trigger fires, the resolver dispatches to the matching
effect handler and records the firing on the state so it doesn't
re-fire for once-shot complications.

Called by ``CombatEngine`` at:
- Round start (``turn_counter`` + ``hp_threshold`` triggers)

Wave 1 handler coverage:
- ``spawn_reinforcement`` — append enemies via template ids
- ``environmental`` — apply persistent modifiers (shield regen, evasion,
  enemy accuracy). Modifiers accumulate multiplicatively / additively.
- ``narration`` — set a flag on ``CombatState.complication_flags``,
  return the narration line for the log.

Deferred to wave 2:
- ``choice_prompt`` — requires mid-combat modal UI.
- ``iff_change`` — requires reputation / heat state wiring.

The resolver is pure business logic. It mutates ``CombatState`` and
returns narration strings; it does not touch UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.combat import CombatState
    from spacegame.models.combat_complication import CombatComplication


@dataclass
class ComplicationEvent:
    """The result of one complication firing.

    Attributes:
        complication_id: Id of the complication that fired.
        narration: Line to append to the combat log. May be empty.
        spawned_template_ids: Enemy template ids to spawn (if any). The
            combat engine performs the actual spawn so it can wire the
            new enemies into its turn queue.
    """

    complication_id: str
    narration: str = ""
    spawned_template_ids: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.spawned_template_ids is None:
            self.spawned_template_ids = []


class ComplicationResolver:
    """Evaluates complications against a combat state each round.

    Instantiated per-combat with the encounter's attached complications
    (resolved from ``EncounterDefinition.complication_ids`` by
    ``CombatEngine``). The resolver doesn't re-resolve ids itself;
    callers pass the already-looked-up complications.
    """

    def __init__(self, complications: list["CombatComplication"]) -> None:
        self._complications = list(complications)

    def evaluate(self, state: "CombatState") -> list[ComplicationEvent]:
        """Evaluate every attached complication against current state.

        Fires any whose trigger is satisfied and that haven't fired yet.
        Mutates ``state.fired_complication_ids`` and any environmental
        modifiers. Returns events for the caller to display / action.

        Args:
            state: Current combat state. Mutated by environmental and
                narration effects.

        Returns:
            List of events for complications that fired this call.
        """
        events: list[ComplicationEvent] = []
        for comp in self._complications:
            if comp.id in state.fired_complication_ids:
                continue
            if not self._trigger_satisfied(comp, state):
                continue
            event = self._apply_effect(comp, state)
            state.fired_complication_ids.add(comp.id)
            if event is not None:
                events.append(event)
        return events

    # ------------------------------------------------------------------
    # Trigger evaluation
    # ------------------------------------------------------------------

    def _trigger_satisfied(
        self, comp: "CombatComplication", state: "CombatState"
    ) -> bool:
        """Return True if ``comp`` should fire given ``state``."""
        t = comp.trigger_type
        p = comp.trigger_params or {}

        if t == "turn_counter":
            target = int(p.get("turn", 1))
            return state.round_number >= target

        if t == "hp_threshold":
            # Supports "target": "player" | "enemy" (defaults to player).
            # "hp_pct" in (0.0, 1.0].
            target = p.get("target", "player")
            threshold = float(p.get("hp_pct", 0.5))
            if target == "player":
                max_hp = max(1, state.player.max_hull)
                current_pct = state.player.hull / max_hp
                return current_pct <= threshold
            if target == "enemy":
                # Any surviving enemy below threshold qualifies — a single
                # damaged ship is enough to trip "battle damage" effects.
                # EnemyShip stores live hp on ``current_hull`` (field), with
                # ``max_hull`` exposed as a property.
                for enemy in state.surviving_enemies:
                    max_hp = max(1, enemy.max_hull)
                    if enemy.current_hull / max_hp <= threshold:
                        return True
                return False

        if t == "random":
            # Wave 1 doesn't use random triggers — they need a seeded
            # RNG that callers haven't threaded in yet. Future CE work.
            return False

        if t == "player_action":
            # Wave 1 doesn't dispatch on specific player actions. Deferred.
            return False

        return False

    # ------------------------------------------------------------------
    # Effect dispatch
    # ------------------------------------------------------------------

    def _apply_effect(
        self, comp: "CombatComplication", state: "CombatState"
    ) -> Optional[ComplicationEvent]:
        """Dispatch to the handler matching ``comp.effect_type``.

        Returns an event when the handler produces player-visible output.
        """
        e = comp.effect_type
        if e == "spawn_reinforcement":
            return self._effect_spawn_reinforcement(comp, state)
        if e == "environmental":
            return self._effect_environmental(comp, state)
        if e == "narration":
            return self._effect_narration(comp, state)
        # choice_prompt / iff_change deferred to wave 2 — fire a
        # narration-only event so authored content still reads correctly
        # in logs even when the full effect isn't wired yet.
        if e in ("choice_prompt", "iff_change"):
            return ComplicationEvent(
                complication_id=comp.id,
                narration=comp.narration or comp.description,
            )
        return None

    def _effect_spawn_reinforcement(
        self, comp: "CombatComplication", state: "CombatState"
    ) -> ComplicationEvent:
        """Return the list of template_ids for the engine to spawn.

        Does not spawn directly — the combat engine owns enemy spawning
        (it coordinates turn queue, UI reveals, etc).
        """
        templates = list(comp.effect_params.get("template_ids", []))
        return ComplicationEvent(
            complication_id=comp.id,
            narration=comp.narration,
            spawned_template_ids=templates,
        )

    def _effect_environmental(
        self, comp: "CombatComplication", state: "CombatState"
    ) -> ComplicationEvent:
        """Apply persistent environmental modifiers to combat state.

        Each parameter accumulates:
          - ``shield_regen_multiplier`` multiplies onto existing
          - ``player_evasion_modifier`` adds to existing
          - ``enemy_accuracy_multiplier`` multiplies onto existing

        Escalating complications (``asteroid_closure``) apply the same
        modifier each round they fire — but since we prevent re-firing,
        escalation needs a different mechanic (future work; wave 1
        treats every complication as once-fire with a fixed modifier).
        """
        params = comp.effect_params
        if "shield_regen_multiplier" in params:
            state.shield_regen_multiplier *= float(params["shield_regen_multiplier"])
        if "player_evasion_modifier" in params:
            state.player_evasion_modifier += int(params["player_evasion_modifier"])
        if "enemy_accuracy_multiplier" in params:
            state.enemy_accuracy_multiplier *= float(params["enemy_accuracy_multiplier"])
        return ComplicationEvent(
            complication_id=comp.id,
            narration=comp.narration,
        )

    def _effect_narration(
        self, comp: "CombatComplication", state: "CombatState"
    ) -> ComplicationEvent:
        """Set a flag on ``state.complication_flags``. Produce narration."""
        flag_name = comp.effect_params.get("flag_name", comp.id)
        state.complication_flags.add(flag_name)
        return ComplicationEvent(
            complication_id=comp.id,
            narration=comp.narration,
        )
