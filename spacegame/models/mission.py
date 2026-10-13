"""
Mission system models.

Defines mission objectives, rewards, and the MissionManager state machine
that tracks mission lifecycle: available -> active -> completed.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from spacegame.utils.logger import logger


def _parse_soft_deadline(data: dict[str, Any]):
    """Defer import to runtime to avoid circular imports."""
    from spacegame.models.soft_deadline import SoftDeadline

    return SoftDeadline.from_dict(data)


if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster
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
    # BB-6: a "Return to X" leg. It counts only after the ship has left the system where
    # the mission was accepted, and only once every earlier objective that is not a
    # has_flag objective is met.
    after_departure: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        d: dict[str, Any] = {
            "type": self.type.value,
            "target_id": self.target_id,
            "target_quantity": self.target_quantity,
            "description": self.description,
        }
        if self.after_departure:
            d["after_departure"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionObjective":
        """Deserialize from dict."""
        return cls(
            type=ObjectiveType(data["type"]),
            target_id=data["target_id"],
            target_quantity=data.get("target_quantity", 1),
            description=data.get("description", ""),
            after_departure=bool(data.get("after_departure", False)),
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
    # Polish design 6: a one-line receipt shown after the completion notice (the Grand
    # Bazaar's for Drifter's Delivery). Content only: to_dict never writes it.
    receipt: str = ""
    # BB-6: the last objective counts only when every earlier objective is met in the same
    # check, and never locks (a delivery's destination comes after its goods).
    ordered_final: bool = False

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
            ordered_final=bool(data.get("ordered_final", False)),
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
        if self.ordered_final:
            d["ordered_final"] = True
        return d


CREW_XP_PER_MISSION = 20
CREW_LOYALTY_PER_MISSION = 5
# Campaign completion counts that set a milestone flag. The flags gate a number of
# campaign encounters; see qa_pass_2_findings.md.
CAMPAIGN_MILESTONES = (5, 10, 15, 20)


@dataclass
class MissionCompletion:
    """Everything completing one mission changed, for the caller to announce."""

    mission_id: str
    reward_messages: list[str]
    crew_joined: list[str] = field(default_factory=list)
    crew_pending: list[str] = field(default_factory=list)
    permits: list[str] = field(default_factory=list)
    reputation_changes: list[tuple[str, int]] = field(default_factory=list)
    milestone_flags: list[str] = field(default_factory=list)
    bonus_xp: int = 0
    crew_levelups: list[str] = field(default_factory=list)
    loyalty_flags: list[str] = field(default_factory=list)


class MissionManager:
    """Manages mission lifecycle: available -> active -> completed.

    Holds mission definitions as immutable templates and tracks runtime state
    (status, objective progress) separately. Provides get_state/load_state
    for save/load persistence.
    """

    def __init__(
        self, missions: list[Mission], produced_flags: Optional[frozenset[str]] = None
    ) -> None:
        """Initialize with mission definitions.

        Args:
            missions: All mission definitions from data loader.
            produced_flags: The flags content sets outside missions, from
                ``content_flag_producers``. None keeps the auto-resolve setting every
                unmet flag.
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
        # Missions added at runtime (procedural contracts). Their definitions
        # are not in the data files, so get_state saves them in full.
        self._runtime_ids: list[str] = []
        # BB-6: for each active mission, the system where it was accepted, whether the ship
        # has left that system since, and the lifetime counters at the accept.
        self._accept_system: dict[str, str] = {}
        self._departed: set[str] = set()
        self._baselines: dict[str, dict[str, int]] = {}
        # BB-11: the landing (game day, system) that last paid a survey's or salvage's
        # route fuel; a second contract finishing there pays its fee alone.
        self._route_fuel_landing: Optional[tuple[int, str]] = None
        # BB-19: flags some content can set, which the auto-resolve leaves to their scenes.
        # None keeps the auto-resolve setting every flag, for callers that pass no content.
        self._produced_flags: Optional[frozenset[str]] = None
        if produced_flags is not None:
            triggers = {
                m.forced_encounter.trigger_flag
                for m in missions
                if m.forced_encounter is not None and m.forced_encounter.trigger_flag
            }
            self._produced_flags = frozenset(produced_flags) | frozenset(triggers)
        # Which missions set each flag as a reward (another mission's reward is a producer).
        self._flag_rewarders: dict[str, set[str]] = {}
        for m in missions:
            for reward in m.rewards:
                if reward.reward_type == "set_flag" and reward.target_id:
                    self._flag_rewarders.setdefault(reward.target_id, set()).add(m.id)
        # BB-19: NPCs spoken to since each active mission was accepted.
        self._talked_since_accept: dict[str, set[str]] = {}

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
        self._runtime_ids.append(mission.id)
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
        if mission_id in self._runtime_ids:
            self._runtime_ids.remove(mission_id)
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
        self._forget_run(mission_id)
        if player is not None:
            self._accept_system[mission_id] = player.current_system_id
            self._baselines[mission_id] = {
                "combats_won": player.combats_won,
                "trades_completed": player.trades_completed,
            }
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

    def record_conversation(self, npc_id: str) -> None:
        """Note a finished conversation for each active mission that awaits it (BB-19).

        A talk objective after a mission's first objective counts only a conversation
        noted here after the mission was accepted, so the conversation that accepts a
        mission never completes its later talk objectives. Only an active mission with
        such an objective for this NPC notes it, which keeps the saved state small. Call
        it when a dialogue ends, before the availability pass that may accept new missions.

        Args:
            npc_id: The NPC the conversation was with.
        """
        for mid, status in self._status.items():
            if status != MissionStatus.ACTIVE:
                continue
            later = self._missions[mid].objectives[1:]
            if any(o.type == ObjectiveType.TALK_TO_NPC and o.target_id == npc_id for o in later):
                self._talked_since_accept.setdefault(mid, set()).add(npc_id)

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
        self._forget_run(mission_id)
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
        self._forget_run(mission_id)
        return (True, f"Abandoned: {mission.name}")

    def _accept_units(self, mission_id: str, commodity_id: str) -> int:
        """Units of a good one mission's accept cargo holds."""
        return sum(
            cargo.quantity
            for cargo in self._missions[mission_id].on_accept_cargo
            if cargo.commodity_id == commodity_id
        )

    def reserved_units(self, commodity_id: str, except_mission: str = "") -> int:
        """Units of a good the active missions' accept cargo holds (bug bash BB-1, BB-11).

        A mission's ``on_accept_cargo`` belongs to it while it is active: another mission's
        collect leg and hand-over, Sell All, Sell Max, refining, the auction house and the
        Wreckers' Guild leave those units aboard. Python keeps counts, so the reserved
        count stands in for the port's owned cargo lots.

        Args:
            commodity_id: The good.
            except_mission: A mission whose own accept cargo is not counted.

        Returns:
            The reserved units, which can exceed what is aboard after a loss.
        """
        return sum(
            self._accept_units(mid, commodity_id)
            for mid, status in self._status.items()
            if status == MissionStatus.ACTIVE and mid != except_mission
        )

    def sealed_units(self, commodity_id: str) -> int:
        """Units of a good an active board contract's accept cargo holds (bug bash BB-11).

        A board contract (a runtime mission) seals its own cargo while it runs: a sale that
        would draw it is refused, where a campaign or authored mission's cargo may be sold
        when the captain names it.

        Args:
            commodity_id: The good.

        Returns:
            The sealed units.
        """
        return sum(
            self._accept_units(mid, commodity_id)
            for mid in self._runtime_ids
            if self._status.get(mid) == MissionStatus.ACTIVE
        )

    def free_units(self, player: "Player", commodity_id: str, except_mission: str = "") -> int:
        """Units of a good in the main hold that no active mission's accept cargo holds.

        The hidden compartment counts as aboard (``held_units``) and the captain's own
        units go first, so a reserved unit hidden there leaves one of the captain's own
        free in the main hold, where every disposal draws.

        Args:
            player: The player whose hold is read.
            commodity_id: The good.
            except_mission: A mission whose own accept cargo counts as free.

        Returns:
            The free units in the main hold, never below 0.
        """
        main = player.ship.get_cargo_quantity(commodity_id)
        own = held_units(player, commodity_id) - self.reserved_units(commodity_id, except_mission)
        return max(0, min(main, own))

    def sale_draws_sealed(self, player: "Player", commodity_id: str, quantity: int) -> bool:
        """Whether selling units would draw an active board contract's sealed cargo (BB-11).

        The captain's own units go first and the hidden compartment counts as aboard, so a
        sale draws the seal only when it sells more than the held units above the sealed
        count. A sale larger than the main hold is the sell path's own refusal, not a seal.

        Args:
            player: The player whose holds are read.
            commodity_id: The good.
            quantity: The units the captain names.

        Returns:
            True when the sale is refused for sealed cargo.
        """
        aboard = player.ship.get_cargo_quantity(commodity_id)
        held = held_units(player, commodity_id)
        return aboard >= quantity > held - self.sealed_units(commodity_id)

    def free_cargo(self, player: "Player") -> dict[str, int]:
        """The main hold with every reserved unit held back, goods with nothing free left out.

        Args:
            player: The player whose hold is read.

        Returns:
            Commodity id to free units, in the hold's order.
        """
        free: dict[str, int] = {}
        for commodity_id in player.ship.current_cargo:
            units = self.free_units(player, commodity_id)
            if units > 0:
                free[commodity_id] = units
        return free

    def _delivery_share(self, mission: Mission, player: "Player") -> Optional[tuple[int, int]]:
        """The units the mission's deliver_cargo will hand over, and the units it names.

        None when the mission has no deliver_cargo reward. The mission's own accept cargo
        counts with the captain's units; another active mission's does not (BB-1). The units
        are counted in both holds (held_units), as the job's state and the scale count them.
        """
        for reward in mission.rewards:
            if reward.reward_type == "deliver_cargo":
                mine = max(
                    0,
                    held_units(player, reward.target_id)
                    - self.reserved_units(reward.target_id, except_mission=mission.id),
                )
                return min(mine, reward.amount), reward.amount
        return None

    @staticmethod
    def _credit_line(
        scaled: int, amount: int, credit_mult: float, short: Optional[tuple[int, int]]
    ) -> str:
        """A credits reward's notice: the late clause first, then the delivered fraction."""
        clauses: list[str] = []
        if credit_mult < 1.0:
            clauses.append(f"late, {int(credit_mult * 100)}% of {amount:,}")
        if short is not None:
            clauses.append(f"{short[0]} of {short[1]} delivered")
        if not clauses:
            return f"+{scaled:,} Credits"
        return f"+{scaled:,} Credits ({', '.join(clauses)})"

    def check_objectives(
        self,
        player: "Player",
        recruited_crew_ids: Optional[set[str]] = None,
    ) -> list[str]:
        """Check all active mission objectives against current player state.

        Three rules order the legs (BB-6). An ``after_departure`` leg counts only after the
        ship has left the system where the mission was accepted, and only once every earlier
        non-flag objective is met. An ``ordered_final`` mission's last leg counts only when
        every earlier leg is met, and is evaluated again on every check. Combat and trade
        counters count only what happened since the accept.

        Args:
            player: Current player state.
            recruited_crew_ids: Set of currently recruited crew template IDs.
                Crew quests whose crew_member_id is not in this set are skipped.

        Returns:
            The id of the one mission this check completed, in a list, or an empty list. A
            mission completes per call, the first in content order; the caller pays it before
            the next call reads the hold (bug bash BB-11).
        """
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

            self._note_position(mid, player)
            for i in range(len(mission.objectives)):
                if self._progress[mid][i] and not self._rechecked(mission, i):
                    continue  # Skip met objectives (cargo and an ordered final leg re-evaluate)
                self._progress[mid][i] = self._objective_met(mid, mission, i, player)

            # Auto-resolve for side missions: if every objective except HAS_FLAG
            # ones are complete, set the missing flags so the mission can finish.
            # This handles delivery/resolution flags that have no NPC dialogue yet.
            # Campaign missions are excluded — their flags are set by specific
            # game events (dialogue, ground missions, encounters). It sets only flags
            # no content produces (BB-19); the rest wait for their scenes.
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
                        if not self._auto_resolvable(mid, obj.target_id):
                            continue
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
                self._forget_run(mid)
                # BB-11: one mission completes per check, in content order, so the next check
                # reads the hold after this one's hand-over
                return [mid]

        return []

    def _forget_run(self, mission_id: str) -> None:
        """Drop what one run of a mission recorded: accept system, departure, counters."""
        self._accept_system.pop(mission_id, None)
        self._departed.discard(mission_id)
        self._baselines.pop(mission_id, None)
        self._talked_since_accept.pop(mission_id, None)

    def _note_position(self, mission_id: str, player: "Player") -> None:
        """Record the accept system late, or note that the ship has left it (BB-6).

        An accept without a player (``game.check_missions``) records no system, so the first
        check after it records where the ship stands.
        """
        accepted_at = self._accept_system.get(mission_id)
        if accepted_at is None:
            self._accept_system[mission_id] = player.current_system_id
        elif player.current_system_id != accepted_at:
            self._departed.add(mission_id)

    @staticmethod
    def _rechecked(mission: Mission, index: int) -> bool:
        """Whether a met objective is evaluated again on every check.

        Cargo can leave the hold, and an ordered final leg never locks (BB-6).
        """
        if mission.objectives[index].type == ObjectiveType.COLLECT_CARGO:
            return True
        return mission.ordered_final and index == len(mission.objectives) - 1

    def _earlier_legs_met(self, mission_id: str, mission: Mission, index: int) -> bool:
        """Whether every objective before ``index`` that is not has_flag is met this check."""
        progress = self._progress[mission_id]
        return all(
            progress[j]
            for j in range(index)
            if mission.objectives[j].type != ObjectiveType.HAS_FLAG
        )

    def _objective_met(
        self, mission_id: str, mission: Mission, index: int, player: "Player"
    ) -> bool:
        """Evaluate one objective under the ordering rules (BB-6)."""
        obj = mission.objectives[index]
        if mission.ordered_final and index == len(mission.objectives) - 1:
            if not all(self._progress[mission_id][:index]):
                return False
        if obj.after_departure:
            if mission_id not in self._departed:
                return False
            if not self._earlier_legs_met(mission_id, mission, index):
                return False
        if obj.type == ObjectiveType.TALK_TO_NPC and index > 0:
            # BB-19: a conversation counts only once the legs before it are done; one
            # held while an earlier leg is open is dropped.
            if not self._earlier_legs_met(mission_id, mission, index):
                self._talked_since_accept.get(mission_id, set()).discard(obj.target_id)
                return False
        return self._check_single_objective(mission_id, index, obj, player)

    def _since_accept(self, mission_id: str, counter: str, value: int) -> int:
        """A lifetime counter minus its value at the accept (0 when no accept recorded it)."""
        return value - self._baselines.get(mission_id, {}).get(counter, 0)

    def _auto_resolvable(self, mission_id: str, flag: str) -> bool:
        """Whether the side-mission auto-resolve may set this flag (BB-19).

        It may unless some content produces the flag: a dialogue, an encounter, an NPC
        gate, a forced encounter, or another mission's reward.
        """
        if self._produced_flags is None:
            return True
        if flag in self._produced_flags:
            return False
        return not (self._flag_rewarders.get(flag, set()) - {mission_id})

    def _check_single_objective(
        self, mission_id: str, index: int, obj: MissionObjective, player: "Player"
    ) -> bool:
        """Evaluate a single objective against player state."""
        if obj.type == ObjectiveType.REACH_SYSTEM:
            return player.current_system_id == obj.target_id
        elif obj.type == ObjectiveType.TALK_TO_NPC:
            if index > 0:
                return obj.target_id in self._talked_since_accept.get(mission_id, set())
            from spacegame.constants.flags import talked_to_npc

            return player.dialogue_flags.get(talked_to_npc(obj.target_id), False)
        elif obj.type == ObjectiveType.HAVE_CREDITS:
            return player.credits >= obj.target_quantity
        elif obj.type == ObjectiveType.COLLECT_CARGO:
            # BB-1: another active mission's accept cargo never fills this leg
            free = self.free_units(player, obj.target_id, except_mission=mission_id)
            return free >= obj.target_quantity
        elif obj.type == ObjectiveType.HAS_FLAG:
            return player.dialogue_flags.get(obj.target_id, False)
        elif obj.type == ObjectiveType.COMPLETE_TRADE:
            done = self._since_accept(mission_id, "trades_completed", player.trades_completed)
            return done >= obj.target_quantity
        elif obj.type == ObjectiveType.WIN_COMBAT:
            won = self._since_accept(mission_id, "combats_won", player.combats_won)
            return won >= obj.target_quantity
        return False

    def apply_rewards(self, mission_id: str, player: "Player") -> list[str]:
        """Apply all rewards from a mission to the player.

        TW follow-up: when the mission has a ``soft_deadline`` and the
        player's current game_day vs recorded accept day puts it past a
        deadline threshold, credit rewards are scaled by the multiplier.

        A ``deliver_cargo`` reward takes the mission's own accept cargo and the
        captain's units, up to its amount, and when it takes fewer it scales
        every credit reward by the share delivered (bug bash BB-1, BB-11). XP,
        flags and access grants are never scaled, since they express narrative
        progress and shouldn't decay.

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

        # BB-1, BB-11: a hand-over pays on the units it takes. Every credits reward scales by
        # delivered over named, multiplying before dividing, and only when short, so a full
        # load pays exactly what it always paid. XP and flags never scale.
        share = self._delivery_share(mission, player)
        short = share if share is not None and share[0] < share[1] else None

        messages: list[str] = []
        for reward in mission.rewards:
            if reward.reward_type == "credits":
                if short is not None:
                    scaled = int(reward.amount * credit_mult * short[0] / short[1])
                else:
                    scaled = int(reward.amount * credit_mult)
                player.add_credits(scaled)
                messages.append(self._credit_line(scaled, reward.amount, credit_mult, short))
            elif reward.reward_type == "xp":
                player.progression.add_xp(reward.amount)
                messages.append(f"+{reward.amount} XP")
            elif reward.reward_type == "deduct_credits":
                player.deduct_credits(reward.amount)
                messages.append(f"-{reward.amount:,} Credits")
            elif reward.reward_type == "remove_cargo":
                player.ship.remove_cargo(reward.target_id, reward.amount)
                messages.append(f"Delivered {reward.amount} {reward.target_id}")
            elif reward.reward_type == "deliver_cargo":
                delivered = share[0] if share is not None else 0
                from_main = min(delivered, player.ship.get_cargo_quantity(reward.target_id))
                if from_main > 0:
                    player.ship.remove_cargo(reward.target_id, from_main)
                if delivered > from_main and player.hidden_compartment is not None:
                    player.hidden_compartment.remove_from_hidden(
                        reward.target_id, delivered - from_main
                    )
                messages.append(f"Delivered {delivered} {reward.target_id}")
            elif reward.reward_type == "route_fuel":
                landing = (player.game_day, player.current_system_id)
                if self._route_fuel_landing != landing:
                    self._route_fuel_landing = landing
                    player.add_credits(reward.amount)
                    messages.append(f"+{reward.amount:,} Credits (route fuel)")
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

    def complete_mission(
        self,
        mission_id: str,
        player: "Player",
        *,
        crew_roster: Optional["CrewRoster"] = None,
        faction_ids: Sequence[str] = (),
        apply_reputation: Optional[Callable[[str, int], list[tuple[str, int]]]] = None,
    ) -> MissionCompletion:
        """Pay out a completed mission, in the order game.check_missions used.

        Args:
            mission_id: A mission ``check_objectives`` just completed.
            player: The player.
            crew_roster: The roster for crew rewards and the per-mission crew XP.
            faction_ids: Every faction id, for a universal (``"all"``) trade permit.
            apply_reputation: Spillover-aware hook returning the changes it made;
                None applies the reward to the named faction only.

        Returns:
            The completion record.
        """
        from spacegame.constants.flags import campaign_mission_milestone

        done = MissionCompletion(mission_id, self.apply_rewards(mission_id, player))
        mission = self._missions.get(mission_id)
        if mission is None:
            return done
        if mission.mission_type == "side":
            player.side_missions_completed += 1
        if mission.mission_type == "campaign":
            campaign_completed = sum(
                1
                for mid in self.get_completed_ids()
                if (m := self.get_mission(mid)) is not None and m.mission_type == "campaign"
            )
            for milestone in CAMPAIGN_MILESTONES:
                flag = campaign_mission_milestone(milestone)
                if campaign_completed >= milestone and not player.dialogue_flags.get(flag):
                    player.dialogue_flags[flag] = True
                    done.milestone_flags.append(flag)
        if mission.crew_member_id:
            player.crew_quests_completed += 1
            xp_mult = player.progression.get_bonus("crew_quest_xp_bonus")
            if xp_mult > 0:
                base_xp = sum(r.amount for r in mission.rewards if r.reward_type == "xp")
                bonus_xp = int(base_xp * xp_mult)
                if bonus_xp > 0:
                    player.progression.add_xp(bonus_xp)
                    done.bonus_xp = bonus_xp
        for reward in mission.rewards:
            if reward.reward_type == "crew" and reward.target_id and crew_roster is not None:
                crew_slots = player.get_crew_slots()
                success, crew_msg = crew_roster.recruit(reward.target_id, crew_slots)
                if success:
                    done.crew_joined.append(crew_msg)
                else:
                    template = crew_roster.get_template(reward.target_id)
                    if template and template.is_companion:
                        crew_roster.add_pending_companion(reward.target_id)
                        done.crew_pending.append(reward.target_id)
            if reward.reward_type == "trade_permit" and reward.target_id:
                targets = list(faction_ids) if reward.target_id == "all" else [reward.target_id]
                for faction_id in targets:
                    player.grant_trade_permit(faction_id)
                done.permits.append(reward.target_id)
            if reward.reward_type in ("reputation", "modify_reputation") and reward.target_id:
                if apply_reputation is not None:
                    done.reputation_changes.extend(
                        apply_reputation(reward.target_id, reward.amount)
                    )
                else:
                    player.modify_reputation(reward.target_id, reward.amount)
                    done.reputation_changes.append((reward.target_id, reward.amount))
        if crew_roster is not None:
            done.crew_levelups = crew_roster.add_xp_to_all(CREW_XP_PER_MISSION)
            done.loyalty_flags = crew_roster.adjust_loyalty_all(CREW_LOYALTY_PER_MISSION)
        return done

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission definition by ID."""
        return self._missions.get(mission_id)

    def get_missions_by_status(self, status: MissionStatus) -> list[Mission]:
        """Get all missions with a given status."""
        return [self._missions[mid] for mid, s in self._status.items() if s == status]

    def open_missions(self) -> list[Mission]:
        """Missions available or active, in content order (bug bash BB-38's keep rule)."""
        return [
            self._missions[mid]
            for mid, status in self._status.items()
            if status in (MissionStatus.AVAILABLE, MissionStatus.ACTIVE)
        ]

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
            "accept_system": dict(self._accept_system),
            "departed": sorted(self._departed),
            "baselines": {mid: dict(counters) for mid, counters in self._baselines.items()},
            "talked_since_accept": {
                mid: sorted(npcs) for mid, npcs in self._talked_since_accept.items() if npcs
            },
            "runtime_missions": [self._missions[mid].to_dict() for mid in self._runtime_ids],
            "route_fuel_landing": list(self._route_fuel_landing)
            if self._route_fuel_landing
            else [],
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore mission runtime state from saved data.

        Args:
            data: Dict from get_state().
        """
        for mission_data in data.get("runtime_missions", []):
            mission = Mission.from_dict(mission_data)
            if mission.id in self._missions:
                continue
            self._missions[mission.id] = mission
            self._status[mission.id] = MissionStatus.UNAVAILABLE
            self._progress[mission.id] = [False] * len(mission.objectives)
            self._runtime_ids.append(mission.id)
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
        # BB-6 run state; older saves have none, and the first check records the system.
        self._accept_system = {
            str(mid): str(system_id) for mid, system_id in data.get("accept_system", {}).items()
        }
        self._departed = {str(mid) for mid in data.get("departed", [])}
        self._baselines = {
            str(mid): {str(name): int(value) for name, value in counters.items()}
            for mid, counters in data.get("baselines", {}).items()
        }
        self._talked_since_accept = {
            str(mid): {str(npc) for npc in npcs}
            for mid, npcs in data.get("talked_since_accept", {}).items()
        }
        # BB-11; older saves hold none
        landing = data.get("route_fuel_landing", [])
        self._route_fuel_landing = (int(landing[0]), str(landing[1])) if len(landing) == 2 else None


def held_units(player: "Player", commodity_id: str) -> int:
    """Units of a good aboard, the hidden compartment's included (bug bash BB-1, BB-11).

    Hiding moves units between the ship's two holds, so a reserved unit in the hidden
    compartment is still aboard: the reserved count, a board contract's seal and the iron
    job's sale sensor read both holds.

    Args:
        player: The player whose holds are read.
        commodity_id: The good.

    Returns:
        The main hold's units plus the hidden compartment's.
    """
    compartment = player.hidden_compartment
    hidden = compartment.hidden_cargo.get(commodity_id, 0) if compartment else 0
    return player.ship.get_cargo_quantity(commodity_id) + hidden
