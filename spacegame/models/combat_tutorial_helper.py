"""Combat tutorial helper — provides contextual crew guidance during first fights.

Observes CombatState after each round and emits appropriate guidance strings.
The combat view renders these in a non-blocking narration panel. Hints are
contextual: if shields weren't hit, the shield hint never fires.
"""


class CombatTutorialHelper:
    """Generates contextual combat guidance based on actual battle events."""

    def __init__(self) -> None:
        self._shown_hints: set[str] = set()
        self._current_hint: str = ""
        self._round_count: int = 0

    def get_current_hint(self) -> str:
        """Get the current guidance text to display."""
        return self._current_hint

    def on_round_start(self, state: object) -> None:
        """Called at the start of each player input phase."""
        self._round_count += 1

        # Round 1: basic weapon guidance
        if self._round_count == 1 and "weapon" not in self._shown_hints:
            self._current_hint = (
                "Select a weapon from the action panel. Click to queue it, then Execute."
            )
            self._shown_hints.add("weapon")
            return

    def on_round_end(self, state: object) -> None:
        """Called after enemy actions resolve. Check what happened and advise."""
        player = state.player

        # Shield damage hint
        if player.shields < player.max_shields * 0.7 and "shields" not in self._shown_hints:
            self._current_hint = "Shields took damage. Queue a defense action to restore them."
            self._shown_hints.add("shields")
            return

        # Hull damage hint
        if player.hull < player.max_hull * 0.8 and "hull" not in self._shown_hints:
            self._current_hint = "Hull damage is permanent until you repair. Watch your health bar."
            self._shown_hints.add("hull")
            return

        # Momentum hint
        if (
            hasattr(player, "momentum")
            and player.momentum
            and player.momentum.current >= 25
            and "momentum" not in self._shown_hints
        ):
            self._current_hint = "Momentum building. At 25%, your crew can use special abilities."
            self._shown_hints.add("momentum")
            return

        # Energy management hint (round 2+)
        if (
            self._round_count >= 2
            and player.energy < player.max_energy * 0.3
            and "energy" not in self._shown_hints
        ):
            self._current_hint = (
                "Energy is low. Some actions cost more than others. Plan your queue."
            )
            self._shown_hints.add("energy")
            return

        # General encouragement for later rounds
        if self._round_count >= 3 and "general" not in self._shown_hints:
            self._current_hint = "You're getting the hang of it. Finish them off."
            self._shown_hints.add("general")
            return

    def on_combat_end(self, victory: bool) -> None:
        """Called when combat resolves."""
        if victory:
            self._current_hint = "Well done. Combat gets harder in dangerous systems."
        else:
            self._current_hint = "Tough break. Repair at the nearest station."
