"""
Mission system models.

Defines mission objectives, rewards, and the MissionManager state machine
that tracks mission lifecycle: available -> active -> completed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from spacegame.models.player import Player


class ObjectiveType(Enum):
    """Types of mission objectives."""

    REACH_SYSTEM = "reach_system"
    TALK_TO_NPC = "talk_to_npc"
    HAVE_CREDITS = "have_credits"
    COLLECT_CARGO = "collect_cargo"
    HAS_FLAG = "has_flag"
    COMPLETE_TRADE = "complete_trade"
    WIN_COMBAT = "win_combat"


class MissionStatus(Enum):
    """Lifecycle status of a mission."""

    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MissionObjective:
    """A single objective within a mission."""

    type: ObjectiveType
    target_id: str
    target_quantity: int = 1
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "type": self.type.value,
            "target_id": self.target_id,
            "target_quantity": self.target_quantity,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionObjective":
        """Deserialize from dict."""
        return cls(
            type=ObjectiveType(data["type"]),
            target_id=data["target_id"],
            target_quantity=data.get("target_quantity", 1),
            description=data.get("description", ""),
        )


@dataclass
class MissionReward:
    """A reward granted on mission completion."""

    reward_type: str
    amount: int
    target_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        d: dict[str, Any] = {"reward_type": self.reward_type, "amount": self.amount}
        if self.target_id:
            d["target_id"] = self.target_id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionReward":
        """Deserialize from dict."""
        return cls(
            reward_type=data["reward_type"],
            amount=data["amount"],
            target_id=data.get("target_id", ""),
        )


@dataclass
class AcceptCargo:
    """Cargo granted to the player when a mission is accepted."""

    commodity_id: str
    quantity: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {"commodity_id": self.commodity_id, "quantity": self.quantity}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptCargo":
        """Deserialize from dict."""
        return cls(commodity_id=data["commodity_id"], quantity=data["quantity"])


@dataclass
class ForcedEncounter:
    """A scripted encounter triggered during travel when a mission is active."""

    encounter_type: str  # "hostile" or "distress_signal"
    enemy_template_ids: list[str] = field(default_factory=list)
    trigger_flag: str = ""  # Set after trigger to prevent repeat
    encounter_def_id: str = ""  # Direct reference to EncounterDefinition.id

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        d: dict[str, Any] = {
            "encounter_type": self.encounter_type,
            "enemy_template_ids": list(self.enemy_template_ids),
            "trigger_flag": self.trigger_flag,
        }
        if self.encounter_def_id:
            d["encounter_def_id"] = self.encounter_def_id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForcedEncounter":
        """Deserialize from dict."""
        return cls(
            encounter_type=data["encounter_type"],
            enemy_template_ids=data.get("enemy_template_ids", []),
            trigger_flag=data.get("trigger_flag", ""),
            encounter_def_id=data.get("encounter_def_id", ""),
        )


@dataclass
class Mission:
    """A mission definition with objectives, rewards, and prerequisites."""

    id: str
    name: str
    description: str
    objectives: list[MissionObjective] = field(default_factory=list)
    rewards: list[MissionReward] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    on_accept_cargo: list[AcceptCargo] = field(default_factory=list)
    required_flags: list[str] = field(default_factory=list)
    forced_encounter: Optional[ForcedEncounter] = None
    auto_accept: bool = False
    hint: str = ""
    ground_mission_id: str = ""
    ground_mission_system_id: str = ""
    ground_mission_complete_flag: str = ""
    # Side mission framework fields
    mission_type: str = "campaign"  # "campaign" or "side"
    available_at: list[str] = field(default_factory=list)  # Systems where available
    available_after: str = ""  # Campaign mission ID prerequisite
    available_before: str = ""  # Expires after this campaign mission completes
    repeatable: bool = False
    discovery_method: str = ""  # "npc", "station_board", "encounter", "automatic"
    discovery_text: str = ""  # First-person narrative hook for journal when mission unlocks
    crew_member_id: str = ""  # Crew member required in party for quest progression

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        """Deserialize from dict.

        Args:
            data: Dict from to_dict() or JSON data.

        Returns:
            Mission instance with all fields populated.
        """
        objectives = [
            MissionObjective.from_dict(obj) for obj in data.get("objectives", [])
        ]
        rewards = [
            MissionReward.from_dict(r) for r in data.get("rewards", [])
        ]
        on_accept_cargo = [
            AcceptCargo.from_dict(c) for c in data.get("on_accept_cargo", [])
        ]
        forced_encounter = None
        if "forced_encounter" in data:
            forced_encounter = ForcedEncounter.from_dict(data["forced_encounter"])
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            objectives=objectives,
            rewards=rewards,
            prerequisites=data.get("prerequisites", []),
            on_accept_cargo=on_accept_cargo,
            required_flags=data.get("required_flags", []),
            forced_encounter=forced_encounter,
            auto_accept=data.get("auto_accept", False),
            hint=data.get("hint", ""),
            ground_mission_id=data.get("ground_mission_id", ""),
            ground_mission_system_id=data.get("ground_mission_system_id", ""),
            ground_mission_complete_flag=data.get("ground_mission_complete_flag", ""),
            mission_type=data.get("mission_type", "campaign"),
            available_at=data.get("available_at", []),
            available_after=data.get("available_after", ""),
            available_before=data.get("available_before", ""),
            repeatable=data.get("repeatable", False),
            discovery_method=data.get("discovery_method", ""),
            discovery_text=data.get("discovery_text", ""),
            crew_member_id=data.get("crew_member_id", ""),
        )

    def get_target_system_ids(self) -> list[str]:
        """Get system IDs referenced by reach_system objectives."""
        return [obj.target_id for obj in self.objectives if obj.type == ObjectiveType.REACH_SYSTEM]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "rewards": [r.to_dict() for r in self.rewards],
            "prerequisites": list(self.prerequisites),
        }
        if self.hint:
            d["hint"] = self.hint
        if self.on_accept_cargo:
            d["on_accept_cargo"] = [c.to_dict() for c in self.on_accept_cargo]
        if self.required_flags:
            d["required_flags"] = list(self.required_flags)
        if self.forced_encounter:
            d["forced_encounter"] = self.forced_encounter.to_dict()
        if self.ground_mission_id:
            d["ground_mission_id"] = self.ground_mission_id
            d["ground_mission_system_id"] = self.ground_mission_system_id
            d["ground_mission_complete_flag"] = self.ground_mission_complete_flag
        # Side mission fields
        if self.mission_type != "campaign":
            d["mission_type"] = self.mission_type
        if self.available_at:
            d["available_at"] = list(self.available_at)
        if self.available_after:
            d["available_after"] = self.available_after
        if self.available_before:
            d["available_before"] = self.available_before
        if self.repeatable:
            d["repeatable"] = self.repeatable
        if self.discovery_method:
            d["discovery_method"] = self.discovery_method
        if self.discovery_text:
            d["discovery_text"] = self.discovery_text
        if self.crew_member_id:
            d["crew_member_id"] = self.crew_member_id
        return d


class MissionManager:
    """Manages mission lifecycle: available -> active -> completed.

    Holds mission definitions as immutable templates and tracks runtime state
    (status, objective progress) separately. Provides get_state/load_state
    for save/load persistence.
    """

    def __init__(self, missions: list[Mission]) -> None:
        """Initialize with mission definitions.

        Args:
            missions: All mission definitions from data loader.
        """
        self._missions: dict[str, Mission] = {m.id: m for m in missions}
        self._status: dict[str, MissionStatus] = {m.id: MissionStatus.UNAVAILABLE for m in missions}
        self._progress: dict[str, list[bool]] = {
            m.id: [False] * len(m.objectives) for m in missions
        }

    def add_mission(
        self,
        mission: Mission,
        initial_status: MissionStatus = MissionStatus.AVAILABLE,
    ) -> tuple[bool, str]:
        """Add a mission at runtime (e.g. procedurally generated).

        Args:
            mission: Mission definition to add.
            initial_status: Starting status (default AVAILABLE).

        Returns:
            Tuple of (success, message).
        """
        if mission.id in self._missions:
            return (False, f"Mission '{mission.id}' already exists")
        self._missions[mission.id] = mission
        self._status[mission.id] = initial_status
        self._progress[mission.id] = [False] * len(mission.objectives)
        return (True, f"Added: {mission.name}")

    def remove_mission(self, mission_id: str) -> bool:
        """Remove a mission (e.g. expired procedural contract).

        Only removes missions that are AVAILABLE or UNAVAILABLE.
        Active/completed missions cannot be removed.

        Args:
            mission_id: ID of mission to remove.

        Returns:
            True if removed, False otherwise.
        """
        if mission_id not in self._missions:
            return False
        status = self._status[mission_id]
        if status in (MissionStatus.ACTIVE, MissionStatus.COMPLETED):
            return False
        del self._missions[mission_id]
        del self._status[mission_id]
        del self._progress[mission_id]
        return True

    def update_availability(
        self, player_flags: Optional[dict[str, bool]] = None
    ) -> list[str]:
        """Check prerequisites and flags, mark eligible missions as AVAILABLE.

        For side missions, also checks available_after (campaign mission must
        be completed before the side mission becomes available).

        Args:
            player_flags: Current dialogue flags from player state.

        Returns:
            List of mission IDs that just became available.
        """
        completed_ids = self.get_completed_ids()
        flags = player_flags or {}
        newly_available: list[str] = []
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.UNAVAILABLE:
                continue
            prereqs_met = all(pid in completed_ids for pid in mission.prerequisites)
            flags_met = all(flags.get(f, False) for f in mission.required_flags)
            # Side missions: check available_after campaign gate
            after_met = (
                not mission.available_after
                or mission.available_after in completed_ids
            )
            if prereqs_met and flags_met and after_met:
                self._status[mid] = MissionStatus.AVAILABLE
                newly_available.append(mid)
                if mission.auto_accept:
                    self.accept_mission(mid)
        return newly_available

    def accept_mission(self, mission_id: str) -> tuple[bool, str]:
        """Move a mission from AVAILABLE to ACTIVE.

        Args:
            mission_id: Mission to accept.

        Returns:
            Tuple of (success, message).
        """
        if mission_id not in self._missions:
            return (False, "Mission not found")
        if self._status[mission_id] != MissionStatus.AVAILABLE:
            return (False, f"Mission is {self._status[mission_id].value}, not available")
        self._status[mission_id] = MissionStatus.ACTIVE
        return (True, f"Accepted: {self._missions[mission_id].name}")

    def get_status(self, mission_id: str) -> Optional[MissionStatus]:
        """Get the current status of a mission.

        Args:
            mission_id: Mission to check.

        Returns:
            MissionStatus if found, None if mission doesn't exist.
        """
        return self._status.get(mission_id)

    def fail_mission(self, mission_id: str) -> tuple[bool, str]:
        """Move a mission from ACTIVE to FAILED.

        Args:
            mission_id: Mission to fail.

        Returns:
            Tuple of (success, message).
        """
        if mission_id not in self._missions:
            return (False, "Mission not found")
        if self._status[mission_id] != MissionStatus.ACTIVE:
            return (False, f"Mission is {self._status[mission_id].value}, not active")
        self._status[mission_id] = MissionStatus.FAILED
        return (True, f"Failed: {self._missions[mission_id].name}")

    def check_objectives(
        self,
        player: "Player",
        recruited_crew_ids: Optional[set[str]] = None,
    ) -> list[str]:
        """Check all active mission objectives against current player state.

        Args:
            player: Current player state.
            recruited_crew_ids: Set of currently recruited crew template IDs.
                Crew quests whose crew_member_id is not in this set are skipped.

        Returns:
            List of mission IDs that just completed (all objectives met).
        """
        newly_completed: list[str] = []
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.ACTIVE:
                continue

            # Skip crew quests when their crew member is not in the party
            if (
                mission.crew_member_id
                and recruited_crew_ids is not None
                and mission.crew_member_id not in recruited_crew_ids
            ):
                continue

            for i, obj in enumerate(mission.objectives):
                if self._progress[mid][i] and obj.type != ObjectiveType.COLLECT_CARGO:
                    continue  # Skip completed (except cargo — must re-evaluate)
                self._progress[mid][i] = self._check_single_objective(obj, player)

            # Auto-resolve for side missions: if every objective except HAS_FLAG
            # ones are complete, set the missing flags so the mission can finish.
            # This handles delivery/resolution flags that have no NPC dialogue yet.
            # Campaign missions are excluded — their flags are set by specific
            # game events (dialogue, ground missions, encounters).
            if mission.mission_type == "side":
                incomplete = [
                    (i, obj) for i, obj in enumerate(mission.objectives)
                    if not self._progress[mid][i]
                ]
                has_non_flag_objectives = any(
                    obj.type != ObjectiveType.HAS_FLAG for obj in mission.objectives
                )
                if (
                    incomplete
                    and has_non_flag_objectives
                    and all(obj.type == ObjectiveType.HAS_FLAG for _, obj in incomplete)
                ):
                    for i, obj in incomplete:
                        player.dialogue_flags[obj.target_id] = True
                        self._progress[mid][i] = True

            if all(self._progress[mid]):
                self._status[mid] = MissionStatus.COMPLETED
                newly_completed.append(mid)

        return newly_completed

    def _check_single_objective(self, obj: MissionObjective, player: "Player") -> bool:
        """Evaluate a single objective against player state."""
        if obj.type == ObjectiveType.REACH_SYSTEM:
            return player.current_system_id == obj.target_id
        elif obj.type == ObjectiveType.TALK_TO_NPC:
            return player.dialogue_flags.get(f"talked_to_{obj.target_id}", False)
        elif obj.type == ObjectiveType.HAVE_CREDITS:
            return player.credits >= obj.target_quantity
        elif obj.type == ObjectiveType.COLLECT_CARGO:
            return player.ship.get_cargo_quantity(obj.target_id) >= obj.target_quantity
        elif obj.type == ObjectiveType.HAS_FLAG:
            return player.dialogue_flags.get(obj.target_id, False)
        elif obj.type == ObjectiveType.COMPLETE_TRADE:
            return player.trades_completed >= obj.target_quantity
        elif obj.type == ObjectiveType.WIN_COMBAT:
            return player.combats_won >= obj.target_quantity
        return False

    def apply_rewards(self, mission_id: str, player: "Player") -> list[str]:
        """Apply all rewards from a mission to the player.

        Args:
            mission_id: The mission whose rewards to apply.
            player: Player to receive rewards.

        Returns:
            List of human-readable reward descriptions.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            return []
        messages: list[str] = []
        for reward in mission.rewards:
            if reward.reward_type == "credits":
                player.add_credits(reward.amount)
                messages.append(f"+{reward.amount:,} Credits")
            elif reward.reward_type == "xp":
                player.progression.add_xp(reward.amount)
                messages.append(f"+{reward.amount} XP")
            elif reward.reward_type == "deduct_credits":
                player.deduct_credits(reward.amount)
                messages.append(f"-{reward.amount:,} Credits")
            elif reward.reward_type == "remove_cargo":
                player.ship.remove_cargo(reward.target_id, reward.amount)
                messages.append(f"Delivered {reward.amount} {reward.target_id}")
            elif reward.reward_type == "set_flag":
                player.dialogue_flags[reward.target_id] = True
                messages.append(f"Progress: {reward.target_id}")
            elif reward.reward_type == "black_market_access":
                player.grant_black_market_access(reward.target_id)
                messages.append(f"Black Market Access: {reward.target_id}")
        return messages

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission definition by ID."""
        return self._missions.get(mission_id)

    def get_missions_by_status(self, status: MissionStatus) -> list[Mission]:
        """Get all missions with a given status."""
        return [self._missions[mid] for mid, s in self._status.items() if s == status]

    def get_objective_progress(self, mission_id: str) -> list[bool]:
        """Get objective completion flags for a mission."""
        return list(self._progress.get(mission_id, []))

    def get_active_target_systems(self) -> set[str]:
        """Get system IDs targeted by incomplete reach_system objectives in active missions."""
        systems: set[str] = set()
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.ACTIVE:
                continue
            for i, obj in enumerate(mission.objectives):
                if obj.type == ObjectiveType.REACH_SYSTEM and not self._progress[mid][i]:
                    systems.add(obj.target_id)
        return systems

    def get_active_forced_encounters(self) -> list[ForcedEncounter]:
        """Get forced encounters from all active missions."""
        return [
            m.forced_encounter
            for m in self.get_missions_by_status(MissionStatus.ACTIVE)
            if m.forced_encounter
        ]

    def get_ground_mission_trigger(
        self,
        current_system_id: str,
        dialogue_flags: dict[str, bool],
    ) -> Optional[tuple[str, str]]:
        """Check if an active mission has a ground mission at the current system.

        Args:
            current_system_id: The system the player just arrived at.
            dialogue_flags: Player's dialogue flags for checking completion.

        Returns:
            Tuple of (ground_mission_id, complete_flag), or None.
        """
        for mission in self.get_missions_by_status(MissionStatus.ACTIVE):
            if (
                mission.ground_mission_id
                and mission.ground_mission_system_id == current_system_id
                and not dialogue_flags.get(mission.ground_mission_complete_flag, False)
            ):
                return (mission.ground_mission_id, mission.ground_mission_complete_flag)
        return None

    def get_current_hint(self) -> Optional[tuple[str, str]]:
        """Get the hint for the current primary mission.

        Prioritizes campaign missions over side missions, and active over
        available within each type. Skips missions with no hint text.

        Returns:
            Tuple of (mission_name, hint_text), or None if no hinted mission.
        """
        # Campaign first, then side; active first, then available
        for mission_type in ("campaign", "side"):
            for status in (MissionStatus.ACTIVE, MissionStatus.AVAILABLE):
                for mid, mission in self._missions.items():
                    if (
                        self._status[mid] == status
                        and mission.hint
                        and mission.mission_type == mission_type
                    ):
                        return (mission.name, mission.hint)
        return None

    def get_completed_ids(self) -> set[str]:
        """Get IDs of all completed missions."""
        return {mid for mid, s in self._status.items() if s == MissionStatus.COMPLETED}

    def get_missions_by_type(self, mission_type: str) -> list[Mission]:
        """Get all missions of a given type (campaign or side).

        Args:
            mission_type: "campaign" or "side".

        Returns:
            List of missions matching the type.
        """
        return [
            m for m in self._missions.values()
            if m.mission_type == mission_type
        ]

    def get_available_at_system(self, system_id: str) -> list[Mission]:
        """Get available side missions at a specific system.

        Missions with empty available_at are available everywhere.

        Args:
            system_id: Current system ID.

        Returns:
            List of available missions at this system.
        """
        return [
            self._missions[mid]
            for mid, s in self._status.items()
            if s == MissionStatus.AVAILABLE
            and (
                not self._missions[mid].available_at
                or system_id in self._missions[mid].available_at
            )
        ]

    def get_missions_by_discovery(self, method: str) -> list[Mission]:
        """Get available missions with a specific discovery method.

        Args:
            method: Discovery method (e.g. "encounter", "station_board", "npc").

        Returns:
            List of available missions matching the discovery method.
        """
        return [
            self._missions[mid]
            for mid, s in self._status.items()
            if s == MissionStatus.AVAILABLE
            and self._missions[mid].discovery_method == method
        ]

    def expire_missions(self) -> list[str]:
        """Expire side missions whose available_before campaign mission is completed.

        Only expires AVAILABLE missions — active and completed missions are
        not affected.

        Returns:
            List of mission IDs that were expired.
        """
        completed_ids = self.get_completed_ids()
        expired: list[str] = []
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.AVAILABLE:
                continue
            if mission.available_before and mission.available_before in completed_ids:
                self._status[mid] = MissionStatus.UNAVAILABLE
                expired.append(mid)
        return expired

    def get_state(self) -> dict[str, Any]:
        """Serialize all mission runtime state for saving."""
        return {
            "status": {mid: s.value for mid, s in self._status.items()},
            "progress": {mid: list(p) for mid, p in self._progress.items()},
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore mission runtime state from saved data.

        Args:
            data: Dict from get_state().
        """
        status_data = data.get("status", {})
        progress_data = data.get("progress", {})
        for mid in self._missions:
            if mid in status_data:
                self._status[mid] = MissionStatus(status_data[mid])
            if mid in progress_data:
                saved_progress = progress_data[mid]
                for i in range(min(len(saved_progress), len(self._progress[mid]))):
                    self._progress[mid][i] = saved_progress[i]
