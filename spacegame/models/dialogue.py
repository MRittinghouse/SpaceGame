"""
Dialogue system models.

NPC definitions, dialogue trees, and a state machine for managing conversations.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NPC:
    """An NPC character that the player can interact with."""

    id: str
    name: str
    title: str
    portrait_color: tuple[int, int, int]
    home_system_id: str
    dialogue_id: str
    faction_id: str = ""

    def get_display_name(self) -> str:
        """Get formatted display name with title."""
        if self.title:
            return f"{self.name} \u2014 {self.title}"
        return self.name


@dataclass
class DialogueResponse:
    """A player response option in a dialogue node."""

    text: str
    next_node_id: Optional[str]
    set_flag: Optional[str] = None


@dataclass
class DialogueNode:
    """A single node in a dialogue tree — one NPC speech with player responses."""

    id: str
    speaker_id: str
    text: str
    responses: list[DialogueResponse] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        """Check if this node ends the conversation."""
        if not self.responses:
            return True
        return all(r.next_node_id is None for r in self.responses)


@dataclass
class DialogueTree:
    """A complete dialogue conversation tree."""

    id: str
    start_node_id: str
    nodes: dict[str, DialogueNode] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[DialogueNode]:
        """Get a node by ID, or None if not found."""
        return self.nodes.get(node_id)

    def get_start_node(self) -> Optional[DialogueNode]:
        """Get the starting node of this dialogue."""
        return self.nodes.get(self.start_node_id)


class DialogueManager:
    """Manages active dialogue state and persistent flags."""

    def __init__(self) -> None:
        self._current_tree: Optional[DialogueTree] = None
        self._current_node_id: Optional[str] = None
        self._flags: dict[str, bool] = {}

    @property
    def is_active(self) -> bool:
        """Check if a dialogue is currently in progress."""
        return self._current_tree is not None and self._current_node_id is not None

    def start_dialogue(self, tree: DialogueTree) -> None:
        """Begin a new dialogue conversation."""
        self._current_tree = tree
        self._current_node_id = tree.start_node_id

    def end_dialogue(self) -> None:
        """End the current dialogue."""
        self._current_tree = None
        self._current_node_id = None

    def get_current_node(self) -> Optional[DialogueNode]:
        """Get the current dialogue node."""
        if not self._current_tree or not self._current_node_id:
            return None
        return self._current_tree.get_node(self._current_node_id)

    def get_available_responses(self) -> list[DialogueResponse]:
        """Get the response options for the current node."""
        node = self.get_current_node()
        if not node:
            return []
        return node.responses

    def select_response(self, index: int) -> Optional[DialogueNode]:
        """Select a response by index, advancing the dialogue.

        Returns:
            The next DialogueNode, or None if the dialogue ended.
        """
        node = self.get_current_node()
        if not node or index < 0 or index >= len(node.responses):
            return None

        response = node.responses[index]

        # Set flag if specified
        if response.set_flag:
            self.set_flag(response.set_flag)

        # Advance or end
        if response.next_node_id is None:
            self.end_dialogue()
            return None

        self._current_node_id = response.next_node_id
        return self.get_current_node()

    def set_flag(self, key: str, value: bool = True) -> None:
        """Set a dialogue flag."""
        self._flags[key] = value

    def get_flag(self, key: str) -> bool:
        """Get a dialogue flag value, defaulting to False."""
        return self._flags.get(key, False)

    def get_flags(self) -> dict[str, bool]:
        """Get all flags for serialization."""
        return dict(self._flags)

    def load_flags(self, flags: dict[str, bool]) -> None:
        """Load flags from deserialized data."""
        self._flags = dict(flags)
