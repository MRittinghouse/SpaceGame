"""
Activity registry for data-driven mini-game availability.

Maps system tags/IDs to available activities, making it trivial to add
new mini-games to different systems.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from spacegame.config import GameState


@dataclass
class ActivityDefinition:
    """Definition of an activity available at certain systems."""

    id: str
    name: str
    description: str
    game_state: GameState
    button_text: str
    # Which systems this activity is available at (by system ID)
    system_ids: List[str] = field(default_factory=list)
    # Which system types this activity is available at
    system_types: List[str] = field(default_factory=list)

    def is_available_at(self, system_id: str, system_type: str) -> bool:
        """Check if this activity is available at a given system."""
        if system_id in self.system_ids:
            return True
        if system_type in self.system_types:
            return True
        return False


class ActivityRegistry:
    """
    Registry of all activities that can be performed at star systems.

    Provides a data-driven way to determine what mini-games/activities
    are available at each system, replacing hard-coded checks.
    """

    def __init__(self):
        self._activities: Dict[str, ActivityDefinition] = {}

    def register(self, activity: ActivityDefinition) -> None:
        """Register an activity."""
        self._activities[activity.id] = activity

    def unregister(self, activity_id: str) -> None:
        """Remove an activity from the registry."""
        self._activities.pop(activity_id, None)

    def get_activities_for_system(
        self, system_id: str, system_type: str
    ) -> List[ActivityDefinition]:
        """
        Get all activities available at a given system.

        Args:
            system_id: The system's unique ID
            system_type: The system's type (e.g., 'mining', 'industrial')

        Returns:
            List of available ActivityDefinitions
        """
        return [
            activity
            for activity in self._activities.values()
            if activity.is_available_at(system_id, system_type)
        ]

    def get_activity(self, activity_id: str) -> Optional[ActivityDefinition]:
        """Get a specific activity by ID."""
        return self._activities.get(activity_id)

    def get_all_activities(self) -> List[ActivityDefinition]:
        """Get all registered activities."""
        return list(self._activities.values())


def create_default_registry() -> ActivityRegistry:
    """Create the default activity registry with all standard activities."""
    registry = ActivityRegistry()

    # Mining - available at mining systems
    registry.register(
        ActivityDefinition(
            id="mining",
            name="Asteroid Mining",
            description="Mine asteroids for ore and minerals",
            game_state=GameState.MINING,
            button_text="MINE",
            system_ids=["breakstone", "iron_depths"],
            system_types=["mining"],
        )
    )

    # Salvaging - available at industrial systems
    registry.register(
        ActivityDefinition(
            id="salvaging",
            name="Salvage Operations",
            description="Scan and extract components from derelict hulls",
            game_state=GameState.SALVAGING,
            button_text="SALVAGE",
            system_ids=["forgeworks", "crimson_reach"],
            system_types=["industrial"],
        )
    )

    # Refining - available at industrial and research systems
    registry.register(
        ActivityDefinition(
            id="refining",
            name="Refining",
            description="Process raw materials into valuable goods",
            game_state=GameState.REFINING,
            button_text="REFINE",
            system_ids=["forgeworks", "axiom_labs", "nova_research"],
            system_types=[],
        )
    )

    return registry
