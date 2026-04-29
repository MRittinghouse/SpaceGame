"""
Mission system models.

Defines mission objectives, rewards, and the MissionManager state machine
that tracks mission lifecycle: available -> active -> completed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from spacegame.utils.logger import logger


def _parse_soft_deadline(data: dict[str, Any]):
    """Defer import to runtime to avoid circular imports."""
    from spacegame.models.soft_deadline import SoftDeadline

    return SoftDeadline.from_dict(data)


if TYPE_CHECKING:
    from spacegame.models.player import Player
    from spacegame.models.soft_deadline import SoftDeadline


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
    ABANDONED = "abandoned"


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
    # Faction reputation gate: [{"faction_id": str, "min_reputation": int}]
    required_reputation: list[dict[str, Any]] = field(default_factory=list)
    # TW-4: optional soft deadline. When set, completing the mission
    # past the full/partial thresholds multiplies the credit reward.
    # Never zero — "drift, not fail".
    soft_deadline: Optional["SoftDeadline"] = None
    # TW follow-up: optional NPC commentary by timeliness tier. Keys:
    # "timely" | "late" | "very_late" — matching SoftDeadline.resolve_tier.
    # Authored per-mission so the delivering NPC reacts in voice to how
    # long the player took. Empty/None = no commentary.
    timeliness_comments: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        """Deserialize from dict.

        Args:
            data: Dict from to_dict() or JSON data.

        Returns:
            Mission instance with all fields populated.
        """
        objectives = [MissionObjective.from_dict(obj) for obj in data.get("objectives", [])]
        rewards = [MissionReward.from_dict(r) for r in data.get("rewards", [])]
        on_accept_cargo = [AcceptCargo.from_dict(c) for c in data.get("on_accept_cargo", [])]
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
            required_reputation=data.get("required_reputation", []),
            soft_deadline=(
                _parse_soft_deadline(data["soft_deadline"]) if "soft_deadline" in data else None
            ),
            timeliness_comments=dict(data.get("timeliness_comments", {})),
        )

    def get_target_system_ids(self) -> list[str]:
        """Get system IDs referenced by reach_system objectives."""
        return [obj.target_id for obj in self.objectives if obj.type == ObjectiveType.REACH_SYSTEM]

    def get_reward_multiplier(self, days_elapsed: int) -> float:
        """TW-4: resolve the effective reward multiplier for this mission.

        Returns 1.0 when no ``soft_deadline`` is configured. Otherwise
        delegates to the deadline's tier resolver. Never zero — the
        "drift, not fail" constraint holds.

        Args:
            days_elapsed: Days between mission accept and completion.

        Returns:
            Multiplier in [late_multiplier, 1.0].
        """
        if self.soft_deadline is None:
            return 1.0
        return self.soft_deadline.resolve_multiplier(days_elapsed)

    def get_timeliness_comment(self, days_elapsed: int) -> Optional[str]:
        """TW follow-up: resolve the NPC's voiced reaction to delivery pace.

        Returns ``None`` when no ``soft_deadline`` is configured, no
        ``timeliness_comments`` authored, or no comment matches the
        resolved tier. Callers display the returned string as its own
        narrative line so it reads as NPC dialogue, not a reward stat.

        Args:
            days_elapsed: Days between accept and completion.

        Returns:
            The authored comment for the tier, or None if absent.
        """
        if self.soft_deadline is None or not self.timeliness_comments:
            return None
        tier = self.soft_deadline.resolve_tier(days_elapsed)
        comment = self.timeliness_comments.get(tier, "").strip()
        return comment or None

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
        if self.required_reputation:
            d["required_reputation"] = self.required_reputation
        if self.soft_deadline is not None:
            d["soft_deadline"] = self.soft_deadline.to_dict()
        if self.timeliness_comments:
            d["timeliness_comments"] = dict(self.timeliness_comments)
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
        # TW follow-up: game_day when each mission transitioned AVAILABLE
        # -> ACTIVE. Used to compute soft-deadline reward multipliers at
        # completion. Missions never accepted have no entry.
        self._accepted_day: dict[str, int] = {}

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
        self,
        player_flags: Optional[dict[str, bool]] = None,
        player_reputation: Optional[dict[str, int]] = None,
        game_day: Optional[int] = None,
        player: Optional["Player"] = None,
    ) -> list[str]:
        """Check prerequisites and flags, mark eligible missions as AVAILABLE.

        For side missions, also checks available_after (campaign mission must
        be completed before the side mission becomes available).

        Args:
            player_flags: Current dialogue flags from player state.
            player_reputation: Faction ID -> reputation value mapping.
            game_day: Current game day. When auto-accept fires for an
                eligible mission, the day is recorded for soft-deadline
                multiplier resolution at completion.

        Returns:
            List of mission IDs that just became available.
        """
        completed_ids = self.get_completed_ids()
        flags = player_flags or {}
        rep = player_reputation or {}
        newly_available: list[str] = []
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.UNAVAILABLE:
                continue
            prereqs_met = all(pid in completed_ids for pid in mission.prerequisites)
            flags_met = all(flags.get(f, False) for f in mission.required_flags)
            # Side missions: check available_after campaign gate
            after_met = not mission.available_after or mission.available_after in completed_ids
            # Faction reputation gate
            rep_met = all(
                rep.get(r["faction_id"], 0) >= r["min_reputation"]
                for r in mission.required_reputation
            )
            if prereqs_met and flags_met and after_met and rep_met:
                self._status[mid] = MissionStatus.AVAILABLE
                newly_available.append(mid)
                if mission.auto_accept:
                    self.accept_mission(mid, game_day=game_day, player=player)
                    logger.debug(
                        "Mission '%s' auto-accepted (prereqs=%s, flags=%s, after=%s)",
                        mid,
                        prereqs_met,
                        flags_met,
                        after_met,
                    )
                else:
                    logger.debug("Mission '%s' now AVAILABLE", mid)
            elif mission.required_flags or mission.prerequisites or mission.available_after:
                # Log why blocked missions stay unavailable (only for gated missions)
                missing_prereqs = [p for p in mission.prerequisites if p not in completed_ids]
                missing_flags = [f for f in mission.required_flags if not flags.get(f, False)]
                missing_after = (
                    mission.available_after
                    if mission.available_after and mission.available_after not in completed_ids
                    else ""
                )
                if missing_prereqs or missing_flags or missing_after:
                    logger.debug(
                        "Mission '%s' blocked: missing_prereqs=%s, "
                        "missing_flags=%s, missing_after=%s",
                        mid,
                        missing_prereqs,
                        missing_flags,
                        missing_after,
                    )
        return newly_available

    def accept_mission(
        self,
        mission_id: str,
        game_day: Optional[int] = None,
        player: Optional["Player"] = None,
    ) -> tuple[bool, str]:
        """Move a mission from AVAILABLE to ACTIVE.

        Args:
            mission_id: Mission to accept.
            game_day: Current game day when the mission is accepted.
                Recorded so soft-deadline multipliers can be resolved
                at completion. ``None`` skips recording (tests that
                don't care about deadlines).
            player: Optional Player. When passed, records the mission's
                accept as a TW interaction — drops
                ``{mission_id}_accepted`` + ``any_mission_accepted`` into
                ``player.last_interaction_day`` so TimedThreads watching
                those keys reset their drift clocks. Also sets the
                matching dialogue_flags so existing NPC-gating consumers
                keep working consistently across all accept paths.

        Returns:
            Tuple of (success, message).
        """
        if mission_id not in self._missions:
            return (False, "Mission not found")
        if self._status[mission_id] != MissionStatus.AVAILABLE:
            return (False, f"Mission is {self._status[mission_id].value}, not available")
        self._status[mission_id] = MissionStatus.ACTIVE
        if game_day is not None:
            self._accepted_day[mission_id] = game_day
        # QA-F-1 / QA-F-3: centralize accepted-flag + TW interaction
        # recording here so every accept path (game auto-accept, cantina,
        # station hub, mission log) behaves identically. Callers no
        # longer need to remember to set the flag themselves.
        if player is not None:
            accept_flag = f"{mission_id}_accepted"
            player.dialogue_flags[accept_flag] = True
            player.record_interaction(accept_flag, game_day=game_day)
            player.record_interaction("any_mission_accepted", game_day=game_day)
        return (True, f"Accepted: {self._missions[mission_id].name}")

    def get_accepted_day(self, mission_id: str) -> Optional[int]:
        """Return the game_day when the mission was accepted, or None."""
        return self._accepted_day.get(mission_id)

    def get_timeliness_comment(self, mission_id: str, player: "Player") -> Optional[str]:
        """TW follow-up: get the voiced NPC comment about delivery pace.

        Returns None when the mission has no authored comments, no
        soft_deadline, or no accepted_day recorded (can't compute
        elapsed time — fall back to silence rather than a wrong tier).
        """
        mission = self._missions.get(mission_id)
        if mission is None:
            return None
        accepted = self._accepted_day.get(mission_id)
        if accepted is None:
            return None
        days_elapsed = max(0, player.game_day - accepted)
        return mission.get_timeliness_comment(days_elapsed)

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

    def abandon_mission(self, mission_id: str) -> tuple[bool, str]:
        """Move a side mission from ACTIVE to ABANDONED.

        Only side missions can be abandoned. Campaign missions cannot.
        No rewards are granted. Returns the mission's on_accept_cargo
        list so the caller can remove cargo from the player's ship.

        Args:
            mission_id: Mission to abandon.

        Returns:
            Tuple of (success, message).
        """
        if mission_id not in self._missions:
            return (False, "Mission not found")
        mission = self._missions[mission_id]
        if self._status[mission_id] != MissionStatus.ACTIVE:
            return (False, f"Mission is {self._status[mission_id].value}, not active")
        if mission.mission_type != "side":
            return (False, "Only side missions can be abandoned")
        self._status[mission_id] = MissionStatus.ABANDONED
        return (True, f"Abandoned: {mission.name}")

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
                    (i, obj)
                    for i, obj in enumerate(mission.objectives)
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
                        logger.warning(
                            "Auto-resolved HAS_FLAG objective '%s' for "
                            "mission '%s' — consider adding proper flag-setting "
                            "in dialogue or encounters",
                            obj.target_id,
                            mid,
                        )

            if all(self._progress[mid]):
                self._status[mid] = MissionStatus.COMPLETED
                newly_completed.append(mid)

        return newly_completed

    def _check_single_objective(self, obj: MissionObjective, player: "Player") -> bool:
        """Evaluate a single objective against player state."""
        if obj.type == ObjectiveType.REACH_SYSTEM:
            return player.current_system_id == obj.target_id
        elif obj.type == ObjectiveType.TALK_TO_NPC:
            from spacegame.constants.flags import talked_to_npc

            return player.dialogue_flags.get(talked_to_npc(obj.target_id), False)
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

        TW follow-up: when the mission has a ``soft_deadline`` and the
        player's current game_day vs recorded accept day puts it past a
        deadline threshold, credit rewards are scaled by the multiplier.
        Non-credit rewards (XP, flags, cargo, access grants) are never
        scaled — those express narrative progress and shouldn't decay.

        Args:
            mission_id: The mission whose rewards to apply.
            player: Player to receive rewards.

        Returns:
            List of human-readable reward descriptions.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            return []

        # Resolve credit multiplier from soft deadline (if set).
        credit_mult = 1.0
        accepted = self._accepted_day.get(mission_id)
        if mission.soft_deadline is not None and accepted is not None:
            days_elapsed = max(0, player.game_day - accepted)
            credit_mult = mission.get_reward_multiplier(days_elapsed)

        messages: list[str] = []
        for reward in mission.rewards:
            if reward.reward_type == "credits":
                scaled = int(reward.amount * credit_mult)
                player.add_credits(scaled)
                if credit_mult < 1.0:
                    messages.append(
                        f"+{scaled:,} Credits "
                        f"(late, {int(credit_mult * 100)}% of {reward.amount:,})"
                    )
                else:
                    messages.append(f"+{scaled:,} Credits")
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
            elif reward.reward_type == "kweon_relationship":
                # Bump Kweon trust counter. If state is None (player has never
                # visited Okafor), the bump is a no-op rather than creating
                # an empty state — SA-R3 Decision 7.
                if player.okafor_research_state is not None:
                    player.okafor_research_state.bump_relationship(reward.amount)
                messages.append(f"Kweon trust +{reward.amount}")
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

    def get_active_target_systems(
        self,
        npc_home_systems: Optional[dict[str, str]] = None,
    ) -> set[str]:
        """Get system IDs targeted by incomplete objectives in active missions.

        Includes reach_system targets and, if npc_home_systems is provided,
        the home systems of NPCs referenced by talk_to_npc objectives.

        Args:
            npc_home_systems: Mapping of NPC ID -> home system ID.

        Returns:
            Set of system IDs the player should visit.
        """
        npc_systems = npc_home_systems or {}
        systems: set[str] = set()
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.ACTIVE:
                continue
            for i, obj in enumerate(mission.objectives):
                if self._progress[mid][i]:
                    continue
                if obj.type == ObjectiveType.REACH_SYSTEM:
                    systems.add(obj.target_id)
                elif obj.type == ObjectiveType.TALK_TO_NPC and obj.target_id in npc_systems:
                    systems.add(npc_systems[obj.target_id])
        return systems

    def get_contextual_hints(
        self,
        current_system_id: str,
        npc_home_systems: Optional[dict[str, str]] = None,
    ) -> list[str]:
        """Get quest hints relevant to the player's current system.

        Args:
            current_system_id: System the player is currently docked at.
            npc_home_systems: Mapping of NPC ID -> home system ID (from data loader).

        Returns:
            List of hint strings for active missions with objectives at this system.
        """
        npc_systems = npc_home_systems or {}
        hints: list[str] = []
        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.ACTIVE:
                continue
            progress = self._progress[mid]
            for i, obj in enumerate(mission.objectives):
                if i < len(progress) and progress[i]:
                    continue  # Already complete
                if obj.type == ObjectiveType.REACH_SYSTEM and obj.target_id == current_system_id:
                    hints.append(f"{mission.name}: {obj.description}")
                elif obj.type == ObjectiveType.TALK_TO_NPC:
                    npc_system = npc_systems.get(obj.target_id, "")
                    if npc_system == current_system_id:
                        hints.append(f"{mission.name}: {obj.description}")
        return hints

    def get_active_forced_encounters(self) -> list[ForcedEncounter]:
        """Get forced encounters from all active missions."""
        return [
            m.forced_encounter
            for m in self.get_missions_by_status(MissionStatus.ACTIVE)
            if m.forced_encounter
        ]

    def get_reputation_locked_teaser(
        self,
        system_id: str,
        player_reputation: dict[str, int],
    ) -> Optional[tuple[str, str, str]]:
        """Get at most one reputation-locked mission for station board teaser.

        Returns the locked mission closest to the player's current reputation,
        or None if no missions are locked by reputation at this system.

        Args:
            system_id: Current system ID.
            player_reputation: Faction ID -> reputation value.

        Returns:
            Tuple of (mission_name, faction_name, tier_name) or None.
        """
        from spacegame.models.faction import get_reputation_tier

        best: Optional[tuple[str, str, str, int]] = None  # name, faction, tier, gap

        for mid, mission in self._missions.items():
            if self._status[mid] != MissionStatus.UNAVAILABLE:
                continue
            if not mission.required_reputation:
                continue
            if mission.available_at and system_id not in mission.available_at:
                continue

            # Check if reputation is the ONLY thing blocking this mission
            # (other gates like flags/prereqs must already be met)
            completed_ids = self.get_completed_ids()
            prereqs_ok = all(pid in completed_ids for pid in mission.prerequisites)
            after_ok = not mission.available_after or mission.available_after in completed_ids
            if not prereqs_ok or not after_ok:
                continue  # Blocked by something else, don't tease

            for req in mission.required_reputation:
                faction_id = req["faction_id"]
                min_rep = req["min_reputation"]
                current_rep = player_reputation.get(faction_id, 0)
                if current_rep < min_rep:
                    gap = min_rep - current_rep
                    tier = get_reputation_tier(min_rep)
                    faction_display = faction_id.replace("_", " ").title()
                    if best is None or gap < best[3]:
                        best = (mission.name, faction_display, tier.value, gap)

        if best:
            return (best[0], best[1], best[2])
        return None

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
        return [m for m in self._missions.values() if m.mission_type == mission_type]

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
            if s == MissionStatus.AVAILABLE and self._missions[mid].discovery_method == method
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
            "accepted_day": dict(self._accepted_day),
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
        # Restore accept days (TW follow-up). Empty for legacy saves.
        self._accepted_day = {mid: int(day) for mid, day in data.get("accepted_day", {}).items()}
