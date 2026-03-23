"""
Tutorial system for new players.

5-step guided tutorial that auto-triggers on new game with skip and replay options.
"""

from typing import Optional

# Tutorial step definitions
TUTORIAL_STEPS = [
    {
        "id": 0,
        "title": "Welcome to Aurelia!",
        "description": (
            "You are a trader in a galaxy of opportunity. "
            "Your goal is to buy low, sell high, and build your fortune.\n\n"
            "The Galaxy Map shows all star systems you can visit. "
            "Click a system to see its details, then use the buttons to trade or travel."
        ),
        "trigger": "galaxy_map",
    },
    {
        "id": 1,
        "title": "Trading Basics",
        "description": (
            "At any system, you can buy and sell commodities at the local market.\n\n"
            "Prices vary by system — buy where prices are LOW, "
            "travel to a system where they're HIGH, and sell for profit.\n\n"
            "Watch for price trends shown in the market list."
        ),
        "trigger": "trading",
    },
    {
        "id": 2,
        "title": "Traveling the Galaxy",
        "description": (
            "To travel, select a destination system on the Galaxy Map "
            "and click 'Travel'. Each jump costs fuel and advances one day.\n\n"
            "Market prices change daily, so plan your route carefully. "
            "You can also REST at a system to wait for better prices."
        ),
        "trigger": "after_first_trade",
    },
    {
        "id": 3,
        "title": "Activities: Mining, Salvage & Refining",
        "description": (
            "Some systems offer special activities:\n\n"
            "Mining: Drill asteroids to extract valuable ores.\n"
            "Salvage: Scan debris fields to find useful materials.\n"
            "Refining: Process raw materials into higher-value goods.\n\n"
            "Check the trading screen for available activities."
        ),
        "trigger": "activity",
    },
    {
        "id": 4,
        "title": "Your Journey Ahead",
        "description": (
            "You're all set! Here are some goals to work toward:\n\n"
            "- Earn achievements for trading, exploring, and crafting\n"
            "- Level up to unlock powerful skills\n"
            "- Upgrade your ship at the Shipyard\n"
            "- Visit all 10 systems in the galaxy\n\n"
            "Check your progress in the Statistics and Achievements screens "
            "(accessible from the pause menu)."
        ),
        "trigger": "after_first_travel",
    },
]


# Contextual hints shown once per mini-game (independent of the 5-step tutorial)
MINIGAME_HINTS: dict[str, dict[str, str]] = {
    "mining": {
        "title": "Asteroid Mining",
        "description": (
            "Click rocks to mine them! Each rock has a hardness rating "
            "that determines how long it takes to break.\n\n"
            "LEFT-CLICK: Free click — mine at normal power.\n"
            "RIGHT-CLICK: Empowered click — uses energy, deals 3x damage.\n\n"
            "The energy bar refills over time. Drones (if unlocked) mine automatically. "
            "When your cargo hold is full, mining stops.\n\n"
            "Use 'Regenerate Field' to dig deeper for rarer ores."
        ),
    },
    "salvage": {
        "title": "Salvage Operations",
        "description": (
            "Explore derelict hulls to find valuable salvage!\n\n"
            "SCAN MODE: Click cells to reveal their contents. Each scan costs a charge "
            "(charges regenerate over time). Numbers show how many items are nearby.\n\n"
            "EXTRACT MODE: Click revealed items to begin extraction. "
            "Extraction takes time — multiple items can extract in parallel.\n\n"
            "Watch out for corruption! Once triggered, a timer counts down "
            "and corrupted cells are lost forever."
        ),
    },
    "refining": {
        "title": "Refining",
        "description": (
            "Process raw materials into valuable refined goods.\n\n"
            "Select a recipe from the list on the left. "
            "Recipes show what materials are NEEDED and what they MAKE.\n\n"
            "Click 'Start' to queue a job. Jobs process in real-time — "
            "you can queue multiple jobs and watch them complete. "
            "Use +/- to batch multiple copies of the same recipe.\n\n"
            "Refined goods sell for much more than raw materials!"
        ),
    },
}


class TutorialManager:
    """Manages the tutorial progression and state."""

    def __init__(self) -> None:
        """Initialize tutorial in not-started state."""
        self.current_step: int = 0
        self.completed: bool = False
        self.skipped: bool = False
        self.active: bool = False
        self._show_step: bool = False
        self.hints_dismissed: set[str] = set()

    def should_show_step(self, trigger: str) -> bool:
        """Check if a tutorial step should show for the given trigger.

        Args:
            trigger: The trigger context (e.g., "galaxy_map", "trading").

        Returns:
            True if the current step matches this trigger and should show.
        """
        if self.completed or self.skipped or not self.active:
            return False
        if self.current_step >= len(TUTORIAL_STEPS):
            return False
        step = TUTORIAL_STEPS[self.current_step]
        return step["trigger"] == trigger and not self._show_step

    def start_step(self) -> Optional[dict]:
        """Begin showing the current step.

        Returns:
            Step content dict, or None if no step to show.
        """
        if self.completed or self.skipped or not self.active:
            return None
        if self.current_step >= len(TUTORIAL_STEPS):
            self.completed = True
            return None
        self._show_step = True
        return TUTORIAL_STEPS[self.current_step]

    def advance_step(self) -> Optional[dict]:
        """Advance to the next tutorial step.

        Returns:
            Next step content dict, or None if tutorial is complete.
        """
        self.current_step += 1
        self._show_step = False
        if self.current_step >= len(TUTORIAL_STEPS):
            self.completed = True
            return None
        return TUTORIAL_STEPS[self.current_step]

    def skip_tutorial(self) -> None:
        """Skip the rest of the tutorial."""
        self.skipped = True
        self._show_step = False

    def reset_tutorial(self) -> None:
        """Reset tutorial for replay."""
        self.current_step = 0
        self.completed = False
        self.skipped = False
        self.active = True
        self._show_step = False

    def is_showing(self) -> bool:
        """Check if a tutorial step is currently being shown."""
        return self._show_step and self.active and not self.completed and not self.skipped

    def get_current_step(self) -> Optional[dict]:
        """Get the current step content if showing.

        Returns:
            Current step dict or None.
        """
        if not self.is_showing():
            return None
        if self.current_step >= len(TUTORIAL_STEPS):
            return None
        return TUTORIAL_STEPS[self.current_step]

    def should_show_hint(self, hint_id: str) -> bool:
        """Check if a contextual hint should show.

        Args:
            hint_id: ID of the hint (e.g., 'mining', 'salvage', 'refining').

        Returns:
            True if the hint exists and hasn't been dismissed yet.
        """
        return hint_id in MINIGAME_HINTS and hint_id not in self.hints_dismissed

    def get_hint(self, hint_id: str) -> Optional[dict]:
        """Get hint content by ID.

        Args:
            hint_id: ID of the hint.

        Returns:
            Hint dict with 'title' and 'description', or None.
        """
        return MINIGAME_HINTS.get(hint_id)

    def dismiss_hint(self, hint_id: str) -> None:
        """Mark a contextual hint as dismissed.

        Args:
            hint_id: ID of the hint to dismiss.
        """
        self.hints_dismissed.add(hint_id)

    def to_dict(self) -> dict:
        """Serialize tutorial state."""
        return {
            "current_step": self.current_step,
            "completed": self.completed,
            "skipped": self.skipped,
            "active": self.active,
            "hints_dismissed": list(self.hints_dismissed),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TutorialManager":
        """Deserialize tutorial state.

        Args:
            data: Serialized tutorial state dict.

        Returns:
            Restored TutorialManager instance.
        """
        tm = cls()
        tm.current_step = data.get("current_step", 0)
        tm.completed = data.get("completed", False)
        tm.skipped = data.get("skipped", False)
        tm.active = data.get("active", False)
        tm.hints_dismissed = set(data.get("hints_dismissed", []))
        return tm
