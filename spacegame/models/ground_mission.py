"""Ground mission configuration, results, and consequence curve.

Bridges campaign missions and repeatable contracts to the ground
exploration system. Defines mission configs (briefing data, rewards,
intel), outcome results, and the bell-curve failure penalty system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from spacegame.models.ground_mapgen import DifficultyTier, MissionType

# ===========================================================================
# Constants
# ===========================================================================

# Ghost run bonus: 10% extra credits for completing undetected
GHOST_RUN_BONUS_PERCENT: int = 10

# Consequence curve XP penalty for commitment zone
COMMITMENT_ZONE_XP_PENALTY: int = 5

# Fled penalty reduction factor (lighter than defeat)
FLED_PENALTY_REDUCTION: float = 0.5


# ===========================================================================
# MissionOutcome
# ===========================================================================


class MissionOutcome(Enum):
    """Outcome of a completed ground mission."""

    SUCCESS = "success"
    EXTRACTED = "extracted"
    DEFEATED = "defeated"
    FLED = "fled"

    @property
    def is_success(self) -> bool:
        """Whether this outcome counts as a full success."""
        return self == MissionOutcome.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Whether this outcome counts as a failure (penalties apply)."""
        return self in (MissionOutcome.DEFEATED, MissionOutcome.FLED)


# ===========================================================================
# IntelHint
# ===========================================================================


@dataclass
class IntelHint:
    """A briefing hint revealed if the player meets a skill threshold.

    Intel hints reward investment in observation and acuity skills
    by revealing patrol patterns, hidden paths, and hazard locations.
    """

    text: str
    required_skill: str
    required_level: int

    def is_revealed(self, skill_levels: dict[str, int]) -> bool:
        """Check if this hint is revealed given the player's skill levels.

        Args:
            skill_levels: Mapping of skill_id -> current level.

        Returns:
            True if the player meets the required skill and level.
        """
        level = skill_levels.get(self.required_skill, 0)
        return level >= self.required_level

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "text": self.text,
            "required_skill": self.required_skill,
            "required_level": self.required_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntelHint:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with text, required_skill, required_level.

        Returns:
            IntelHint instance.
        """
        return cls(
            text=data["text"],
            required_skill=data["required_skill"],
            required_level=data["required_level"],
        )


# ===========================================================================
# GroundMissionRewards
# ===========================================================================


@dataclass
class GroundMissionRewards:
    """Rewards granted on successful ground mission completion."""

    credits: int = 0
    xp: int = 0
    reputation: dict[str, int] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)
    crew_xp: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "credits": self.credits,
            "xp": self.xp,
            "reputation": dict(self.reputation),
            "items": list(self.items),
            "crew_xp": self.crew_xp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundMissionRewards:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with reward fields. Missing fields use defaults.

        Returns:
            GroundMissionRewards instance.
        """
        return cls(
            credits=data.get("credits", 0),
            xp=data.get("xp", 0),
            reputation=data.get("reputation", {}),
            items=data.get("items", []),
            crew_xp=data.get("crew_xp", 0),
        )


# ===========================================================================
# GroundMissionConfig
# ===========================================================================


@dataclass
class GroundMissionConfig:
    """Configuration for a ground mission.

    Bridges campaign missions and repeatable contracts to the ground
    exploration system. Contains everything needed for the briefing
    view and mission setup.
    """

    id: str
    name: str
    description: str
    mission_type: MissionType
    difficulty: DifficultyTier
    faction_id: str
    objectives: list[str]
    intel_hints: list[IntelHint]
    rewards: GroundMissionRewards
    campaign_mission_id: Optional[str] = None
    campaign_map_data: Optional[dict[str, Any]] = None
    seed: Optional[int] = None
    max_crew: int = 2

    @property
    def is_campaign(self) -> bool:
        """Whether this is a campaign mission (vs. repeatable contract)."""
        return self.campaign_mission_id is not None

    def get_revealed_hints(self, skill_levels: dict[str, int]) -> list[IntelHint]:
        """Filter intel hints to those the player can see.

        Args:
            skill_levels: Mapping of skill_id -> current level.

        Returns:
            List of hints where the player meets the required threshold.
        """
        return [h for h in self.intel_hints if h.is_revealed(skill_levels)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "mission_type": self.mission_type.value,
            "difficulty": self.difficulty.value,
            "faction_id": self.faction_id,
            "objectives": list(self.objectives),
            "intel_hints": [h.to_dict() for h in self.intel_hints],
            "rewards": self.rewards.to_dict(),
            "campaign_mission_id": self.campaign_mission_id,
            "campaign_map_data": self.campaign_map_data,
            "seed": self.seed,
            "max_crew": self.max_crew,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundMissionConfig:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with mission config fields.

        Returns:
            GroundMissionConfig instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            mission_type=MissionType(data["mission_type"]),
            difficulty=DifficultyTier(data["difficulty"]),
            faction_id=data["faction_id"],
            objectives=data.get("objectives", []),
            intel_hints=[IntelHint.from_dict(h) for h in data.get("intel_hints", [])],
            rewards=GroundMissionRewards.from_dict(data.get("rewards", {})),
            campaign_mission_id=data.get("campaign_mission_id"),
            campaign_map_data=data.get("campaign_map_data"),
            seed=data.get("seed"),
            max_crew=data.get("max_crew", 2),
        )


# ===========================================================================
# GroundMissionResult
# ===========================================================================


@dataclass
class GroundMissionResult:
    """Outcome of a completed ground mission.

    Contains all data needed for the result view and reward/penalty
    application. The consequence curve determines penalties for
    failed missions based on progress depth.
    """

    config: GroundMissionConfig
    outcome: MissionOutcome
    objectives_completed: int
    objectives_total: int
    turns_taken: int
    enemies_defeated: int
    enemies_talked: int
    loot_credits: int
    loot_items: list[str]
    loot_commodities: dict[str, int] = field(default_factory=dict)
    progress_percent: float = 0.0
    crew_ids: list[str] = field(default_factory=list)
    detected: bool = False

    @property
    def is_ghost_run(self) -> bool:
        """Whether the player completed the mission without being detected."""
        return self.outcome == MissionOutcome.SUCCESS and not self.detected

    @property
    def all_objectives_completed(self) -> bool:
        """Whether all mission objectives were completed."""
        return self.objectives_completed >= self.objectives_total

    @property
    def total_credits(self) -> int:
        """Calculate total credits earned, accounting for outcome and penalties.

        Returns:
            Net credits earned (mission reward + loot - penalties + ghost bonus).
        """
        if self.outcome == MissionOutcome.SUCCESS:
            base = self.config.rewards.credits + self.loot_credits
            if self.is_ghost_run:
                base += int(self.config.rewards.credits * GHOST_RUN_BONUS_PERCENT / 100)
            return base

        if self.outcome == MissionOutcome.EXTRACTED:
            # Voluntary extraction: keep loot, no mission reward
            return self.loot_credits

        # Failure: apply consequence curve
        penalties = self.calculate_penalties()
        kept_loot = int(self.loot_credits * penalties["loot_kept_percent"] / 100)
        return kept_loot

    def calculate_penalties(self) -> dict[str, int]:
        """Calculate failure penalties based on the progress bell curve.

        The consequence curve penalizes based on how deep into the mission
        the player was when they failed. Penalties peak in the middle
        (commitment zone) and ease off at both ends.

        Returns:
            Dict with credit_loss_percent, loot_kept_percent, xp_penalty.
        """
        # Success and extraction have no penalties
        if not self.outcome.is_failure:
            return {"credit_loss_percent": 0, "loot_kept_percent": 100, "xp_penalty": 0}

        # Clamp progress to valid range
        progress = max(0.0, min(1.0, self.progress_percent))

        # Determine base penalties from consequence curve
        if progress < 0.15:
            # Grace zone
            credit_loss = 5
            loot_kept = 100
            xp_penalty = 0
        elif progress < 0.40:
            # Escalating zone — interpolate credit loss 10-15%
            t = (progress - 0.15) / 0.25
            credit_loss = int(10 + t * 5)
            loot_kept = 10
            xp_penalty = 0
        elif progress < 0.65:
            # Commitment zone — peak penalty
            t = (progress - 0.40) / 0.25
            credit_loss = int(15 + t * 5)
            loot_kept = 0
            xp_penalty = COMMITMENT_ZONE_XP_PENALTY
        elif progress < 0.85:
            # Easing zone
            credit_loss = 10
            loot_kept = 50
            xp_penalty = 0
        else:
            # So close zone
            credit_loss = 5
            loot_kept = 80
            xp_penalty = 0

        # Fled is lighter than defeated
        if self.outcome == MissionOutcome.FLED:
            credit_loss = int(credit_loss * FLED_PENALTY_REDUCTION)
            loot_kept = min(100, loot_kept + 20)

        return {
            "credit_loss_percent": credit_loss,
            "loot_kept_percent": loot_kept,
            "xp_penalty": xp_penalty,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "config": self.config.to_dict(),
            "outcome": self.outcome.value,
            "objectives_completed": self.objectives_completed,
            "objectives_total": self.objectives_total,
            "turns_taken": self.turns_taken,
            "enemies_defeated": self.enemies_defeated,
            "enemies_talked": self.enemies_talked,
            "loot_credits": self.loot_credits,
            "loot_items": list(self.loot_items),
            "loot_commodities": dict(self.loot_commodities),
            "progress_percent": self.progress_percent,
            "crew_ids": list(self.crew_ids),
            "detected": self.detected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundMissionResult:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with result fields.

        Returns:
            GroundMissionResult instance.
        """
        return cls(
            config=GroundMissionConfig.from_dict(data["config"]),
            outcome=MissionOutcome(data["outcome"]),
            objectives_completed=data["objectives_completed"],
            objectives_total=data["objectives_total"],
            turns_taken=data["turns_taken"],
            enemies_defeated=data["enemies_defeated"],
            enemies_talked=data["enemies_talked"],
            loot_credits=data["loot_credits"],
            loot_items=data.get("loot_items", []),
            loot_commodities=data.get("loot_commodities", {}),
            progress_percent=data["progress_percent"],
            crew_ids=data.get("crew_ids", []),
            detected=data.get("detected", False),
        )
