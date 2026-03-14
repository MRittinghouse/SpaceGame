"""
Dialogue system models.

NPC definitions, dialogue trees, and a state machine for managing conversations.
Supports skill checks and NPC disposition tracking via SocialManager integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.social import SocialManager


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
    auto_trigger_gate_flag: str = ""
    auto_trigger_prerequisites: list[str] = field(default_factory=list)
    hide_after_flag: str = ""

    def get_display_name(self) -> str:
        """Get formatted display name with title."""
        if self.title:
            return f"{self.name} \u2014 {self.title}"
        return self.name


@dataclass
class SkillCheck:
    """A social skill check attached to a dialogue response."""

    skill: str
    difficulty: int
    success_node_id: str
    failure_node_id: str
    set_flag_on_success: Optional[str] = None
    set_flag_on_failure: Optional[str] = None


@dataclass
class DialogueResponse:
    """A player response option in a dialogue node."""

    text: str
    next_node_id: Optional[str]
    set_flag: Optional[str] = None
    skill_check: Optional[SkillCheck] = None
    disposition_change: int = 0
    required_flags: list[str] = field(default_factory=list)
    excluded_flags: list[str] = field(default_factory=list)
    faction_reputation_changes: list[dict[str, int]] = field(default_factory=list)


@dataclass
class DialogueNode:
    """A single node in a dialogue tree — one NPC speech with player responses."""

    id: str
    speaker_id: str
    text: str
    responses: list[DialogueResponse] = field(default_factory=list)
    expression: Optional[str] = None  # Portrait expression (e.g. "happy", "angry")

    @property
    def is_terminal(self) -> bool:
        """Check if this node ends the conversation."""
        if not self.responses:
            return True
        return all(r.next_node_id is None and r.skill_check is None for r in self.responses)


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
    """Manages active dialogue state and persistent flags.

    Optionally integrates with SocialManager for skill check resolution
    and NPC disposition tracking.
    """

    def __init__(self) -> None:
        self._current_tree: Optional[DialogueTree] = None
        self._current_node_id: Optional[str] = None
        self._current_npc_id: Optional[str] = None
        self._flags: dict[str, bool] = {}
        self._social_manager: Optional[SocialManager] = None
        self._politics_manager: Optional[object] = None
        self._player: Optional[object] = None
        self._last_check_result: Optional[tuple[bool, str]] = None

    def set_social_manager(self, manager: SocialManager) -> None:
        """Set the social manager for skill check resolution."""
        self._social_manager = manager

    def set_politics_manager(self, manager: object, player: object) -> None:
        """Set the politics manager and player for faction reputation changes."""
        self._politics_manager = manager
        self._player = player

    @property
    def is_active(self) -> bool:
        """Check if a dialogue is currently in progress."""
        return self._current_tree is not None and self._current_node_id is not None

    def start_dialogue(
        self, tree: DialogueTree, npc_id: Optional[str] = None
    ) -> None:
        """Begin a new dialogue conversation.

        Args:
            tree: The dialogue tree to start.
            npc_id: Optional NPC ID for disposition tracking.
        """
        self._current_tree = tree
        self._current_node_id = tree.start_node_id
        self._current_npc_id = npc_id
        self._last_check_result = None

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
        """Get the response options for the current node, filtered by flag conditions."""
        node = self.get_current_node()
        if not node:
            return []
        return [r for r in node.responses if self._check_response_conditions(r)]

    def _check_response_conditions(self, response: DialogueResponse) -> bool:
        """Check whether a response's flag conditions are met."""
        if response.required_flags:
            if not all(self._flags.get(f, False) for f in response.required_flags):
                return False
        if response.excluded_flags:
            if any(self._flags.get(f, False) for f in response.excluded_flags):
                return False
        return True

    def get_last_check_result(self) -> Optional[tuple[bool, str]]:
        """Get the result of the most recent skill check, or None."""
        return self._last_check_result

    def select_response(self, index: int) -> Optional[DialogueNode]:
        """Select a response by index, advancing the dialogue.

        Handles skill checks and disposition changes if a SocialManager
        is configured.

        Returns:
            The next DialogueNode, or None if the dialogue ended.
        """
        available = self.get_available_responses()
        if not available or index < 0 or index >= len(available):
            return None

        response = available[index]
        self._last_check_result = None

        # Set flag if specified
        if response.set_flag:
            self.set_flag(response.set_flag)

        # Apply disposition change
        if (
            response.disposition_change != 0
            and self._social_manager
            and self._current_npc_id
        ):
            self._social_manager.modify_disposition(
                self._current_npc_id, response.disposition_change
            )

        # Apply faction reputation changes via centralized spillover
        if response.faction_reputation_changes and self._politics_manager and self._player:
            for change_dict in response.faction_reputation_changes:
                for faction_id, amount in change_dict.items():
                    self._politics_manager.apply_reputation_with_spillover(
                        self._player, faction_id, amount
                    )

        # Handle skill check
        if response.skill_check:
            return self._resolve_skill_check(response)

        # Normal response: advance or end
        if response.next_node_id is None:
            self.end_dialogue()
            return None

        self._current_node_id = response.next_node_id
        return self.get_current_node()

    def _resolve_skill_check(
        self, response: DialogueResponse
    ) -> Optional[DialogueNode]:
        """Resolve a skill check response and navigate to the appropriate node."""
        check = response.skill_check
        assert check is not None  # Caller guarantees this

        npc_id = self._current_npc_id or ""

        if self._social_manager:
            success, msg = self._social_manager.resolve_check(
                check.skill, check.difficulty, npc_id
            )
            self._last_check_result = (success, msg)
        else:
            # No social manager — fall back to success path
            success = True

        if success:
            if check.set_flag_on_success:
                self.set_flag(check.set_flag_on_success)
            next_node_id = check.success_node_id
        else:
            if check.set_flag_on_failure:
                self.set_flag(check.set_flag_on_failure)
            next_node_id = check.failure_node_id

        self._current_node_id = next_node_id
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
