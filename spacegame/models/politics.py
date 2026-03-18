"""Political system models.

Tracks faction-to-faction relationships, centralizes reputation spillover,
and manages political events and intel reports.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from spacegame.config import (
    FACTION_RELATIONSHIP_MAX,
    FACTION_RELATIONSHIP_MIN,
    INTEL_RIVAL_BONUS_MULTIPLIER,
    POLITICAL_EVENT_DAILY_CHANCE,
    POLITICAL_EVENT_MAX_DURATION,
    POLITICAL_EVENT_MIN_DURATION,
    REP_SPILLOVER_RATIO,
)
from spacegame.models.faction import Faction, TensionLevel, get_tension_level


class PoliticalEventType(Enum):
    """Types of political events between factions."""

    TRADE_DISPUTE = "trade_dispute"
    BORDER_INCIDENT = "border_incident"
    AID_REQUEST = "aid_request"
    DIPLOMATIC_SUMMIT = "diplomatic_summit"
    SANCTION = "sanction"
    PIRATE_CRISIS = "pirate_crisis"


class PoliticalAction(Enum):
    """Player response options for political events."""

    SIDE_WITH_A = "side_with_a"
    SIDE_WITH_B = "side_with_b"
    MEDIATE = "mediate"
    IGNORE = "ignore"


class IntelQuality(Enum):
    """Quality tier of an intelligence report."""

    RUMOR = "rumor"
    REPORT = "report"
    CLASSIFIED = "classified"


# Rep reward per quality tier
_INTEL_REP_REWARDS: dict[IntelQuality, int] = {
    IntelQuality.RUMOR: 1,
    IntelQuality.REPORT: 3,
    IntelQuality.CLASSIFIED: 5,
}

# Backlash rep penalty when delivering to rival
_INTEL_BACKLASH = -3


@dataclass
class IntelReport:
    """An intelligence report about a faction.

    Attributes:
        id: Unique report identifier.
        name: Display name.
        description: Report content description.
        source_faction_id: Which faction this intel is about.
        quality: Quality tier (rumor/report/classified).
        base_value: Base credit value for delivery.
        acquired_day: Game day when acquired.
        delivered: Whether this report has been delivered.
    """

    id: str
    name: str
    description: str
    source_faction_id: str
    quality: IntelQuality
    base_value: int
    acquired_day: int
    delivered: bool = False

    def get_delivery_value(
        self, target_faction_id: str, factions: dict[str, Faction]
    ) -> int:
        """Calculate credit reward for delivering to a specific faction.

        Rival of source: 2x. Same faction: 0.5x. Other: 1x.
        """
        source = factions.get(self.source_faction_id)
        if target_faction_id == self.source_faction_id:
            return int(self.base_value * 0.5)
        if source and source.rivalry == target_faction_id:
            return int(self.base_value * INTEL_RIVAL_BONUS_MULTIPLIER)
        return self.base_value

    def get_reputation_reward(
        self, target_faction_id: str, factions: dict[str, Faction]
    ) -> int:
        """Calculate rep reward for delivering to a specific faction."""
        base_rep = _INTEL_REP_REWARDS.get(self.quality, 1)
        source = factions.get(self.source_faction_id)
        if source and source.rivalry == target_faction_id:
            return base_rep + 2  # Bonus for rival intel
        if target_faction_id == self.source_faction_id:
            return max(1, base_rep - 1)  # Less useful to source
        return base_rep

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_faction_id": self.source_faction_id,
            "quality": self.quality.value,
            "base_value": self.base_value,
            "acquired_day": self.acquired_day,
            "delivered": self.delivered,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntelReport:
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            source_faction_id=data["source_faction_id"],
            quality=IntelQuality(data["quality"]),
            base_value=data["base_value"],
            acquired_day=data["acquired_day"],
            delivered=data.get("delivered", False),
        )


# Rep changes per action type
_ACTION_REP = {
    PoliticalAction.SIDE_WITH_A: (8, -5),   # (faction_a, faction_b)
    PoliticalAction.SIDE_WITH_B: (-5, 8),
    PoliticalAction.MEDIATE: (3, 3),
    PoliticalAction.IGNORE: (0, 0),
}

# Relationship change when mediating
_MEDIATE_RELATIONSHIP_BONUS = 5


@dataclass
class FactionRelationship:
    """Bilateral relationship between two factions.

    Attributes:
        faction_a_id: First faction ID.
        faction_b_id: Second faction ID.
        value: Relationship value (-100 to +100).
    """

    faction_a_id: str
    faction_b_id: str
    value: int

    def get_key(self) -> tuple[str, str]:
        """Get sorted tuple key for symmetric lookup."""
        return tuple(sorted((self.faction_a_id, self.faction_b_id)))  # type: ignore[return-value]

    def get_tension_level(self) -> TensionLevel:
        """Get tension level for this relationship."""
        return get_tension_level(self.value)

    def modify(self, amount: int) -> None:
        """Modify relationship value, clamped to bounds.

        Args:
            amount: Amount to add (positive or negative).
        """
        self.value = max(
            FACTION_RELATIONSHIP_MIN,
            min(FACTION_RELATIONSHIP_MAX, self.value + amount),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "faction_a": self.faction_a_id,
            "faction_b": self.faction_b_id,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactionRelationship:
        """Deserialize from dict."""
        return cls(
            faction_a_id=data["faction_a"],
            faction_b_id=data["faction_b"],
            value=data["value"],
        )


@dataclass
class PoliticalEvent:
    """A political event between two factions.

    Attributes:
        id: Unique event identifier.
        event_type: Category of political event.
        faction_a_id: First affected faction.
        faction_b_id: Second affected faction.
        description: Human-readable description.
        day_started: Game day when event began.
        duration_days: How many days the event lasts.
        relationship_drift: Daily drift applied to faction relationship.
        resolved: Whether the player has responded to this event.
        player_action: The action the player chose (if resolved).
    """

    id: str
    event_type: PoliticalEventType
    faction_a_id: str
    faction_b_id: str
    description: str
    day_started: int
    duration_days: int
    relationship_drift: int
    resolved: bool = False
    player_action: Optional[PoliticalAction] = None

    def is_active(self, current_day: int) -> bool:
        """Check if this event is still active."""
        if self.resolved:
            return False
        return current_day < self.day_started + self.duration_days

    def days_remaining(self, current_day: int) -> int:
        """Get remaining days for this event."""
        remaining = (self.day_started + self.duration_days) - current_day
        return max(0, remaining)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "faction_a_id": self.faction_a_id,
            "faction_b_id": self.faction_b_id,
            "description": self.description,
            "day_started": self.day_started,
            "duration_days": self.duration_days,
            "relationship_drift": self.relationship_drift,
            "resolved": self.resolved,
            "player_action": self.player_action.value if self.player_action else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PoliticalEvent:
        """Deserialize from dict."""
        action = None
        if data.get("player_action"):
            action = PoliticalAction(data["player_action"])
        return cls(
            id=data["id"],
            event_type=PoliticalEventType(data["event_type"]),
            faction_a_id=data["faction_a_id"],
            faction_b_id=data["faction_b_id"],
            description=data["description"],
            day_started=data["day_started"],
            duration_days=data["duration_days"],
            relationship_drift=data["relationship_drift"],
            resolved=data.get("resolved", False),
            player_action=action,
        )


# Default event templates for generation when no JSON is loaded
_DEFAULT_EVENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "event_type": "trade_dispute",
        "descriptions": [
            "{a} imposes tariff surcharge on {b} shipments",
            "{a} accuses {b} of dumping commodities below cost",
        ],
        "relationship_drift": -2,
    },
    {
        "event_type": "border_incident",
        "descriptions": [
            "Armed {a} patrol confronts {b} vessel near contested route",
            "{b} freighter detained by {a} security at border checkpoint",
        ],
        "relationship_drift": -3,
    },
    {
        "event_type": "aid_request",
        "descriptions": [
            "{a} requests emergency supply shipments from {b}",
            "{b} calls for humanitarian aid in {a} territory",
        ],
        "relationship_drift": 1,
    },
    {
        "event_type": "sanction",
        "descriptions": [
            "{a} restricts export licenses for {b}-bound cargo",
            "{a} suspends preferential trade terms with {b}",
        ],
        "relationship_drift": -2,
    },
    {
        "event_type": "pirate_crisis",
        "descriptions": [
            "Pirate raids disrupt both {a} and {b} shipping lanes",
            "{a} and {b} blame each other for inadequate pirate response",
        ],
        "relationship_drift": -1,
    },
]


class PoliticsManager:
    """Manages faction relationships, reputation spillover, and political events.

    Central authority for all political operations. Ensures reputation changes
    consistently apply spillover to rival factions.
    """

    def __init__(
        self,
        relationships: list[FactionRelationship],
        factions: dict[str, Faction],
    ) -> None:
        self._factions = factions
        self._relationships: dict[tuple[str, str], FactionRelationship] = {}
        for rel in relationships:
            self._relationships[rel.get_key()] = rel
        self._active_events: list[PoliticalEvent] = []
        self._event_templates = list(_DEFAULT_EVENT_TEMPLATES)
        self._intel_reports: dict[str, IntelReport] = {}

    # --- Relationship Management ---

    def get_relationship(
        self, faction_a: str, faction_b: str
    ) -> FactionRelationship:
        """Get the relationship between two factions.

        Args:
            faction_a: First faction ID.
            faction_b: Second faction ID.

        Returns:
            The FactionRelationship instance.

        Raises:
            KeyError: If no relationship exists for this pair.
        """
        key = tuple(sorted((faction_a, faction_b)))
        return self._relationships[key]  # type: ignore[index]

    def modify_relationship(
        self, faction_a: str, faction_b: str, amount: int
    ) -> None:
        """Modify the relationship between two factions.

        Args:
            faction_a: First faction ID.
            faction_b: Second faction ID.
            amount: Amount to add (positive or negative).
        """
        rel = self.get_relationship(faction_a, faction_b)
        rel.modify(amount)

    def get_tension_level(
        self, faction_a: str, faction_b: str
    ) -> TensionLevel:
        """Get tension level between two factions."""
        return self.get_relationship(faction_a, faction_b).get_tension_level()

    # --- Centralized Reputation Spillover ---

    def apply_reputation_with_spillover(
        self,
        player: Any,  # Player, but avoid circular import
        faction_id: str,
        amount: int,
    ) -> list[tuple[str, int]]:
        """Apply reputation change with automatic rival spillover.

        When the player gains reputation with a faction, the rival faction
        loses a percentage (REP_SPILLOVER_RATIO) of that amount.

        Args:
            player: Player instance to modify reputation on.
            faction_id: Faction receiving the primary reputation change.
            amount: Amount to change (positive or negative).

        Returns:
            List of (faction_id, actual_change) tuples for all changes made.
        """
        changes: list[tuple[str, int]] = []

        # Primary change
        player.modify_reputation(faction_id, amount)
        changes.append((faction_id, amount))

        # Spillover to rival
        faction = self._factions.get(faction_id)
        if faction and faction.rivalry:
            spillover = -int(amount * REP_SPILLOVER_RATIO)
            if spillover != 0:
                player.modify_reputation(faction.rivalry, spillover)
                changes.append((faction.rivalry, spillover))

        return changes

    # --- Political Events ---

    def try_generate_event(self, current_day: int) -> Optional[PoliticalEvent]:
        """Attempt to generate a political event for this game day.

        Uses deterministic seeding so the same day always produces the same result.
        Max 2 active events at once.

        Args:
            current_day: Current game day.

        Returns:
            Generated PoliticalEvent, or None if no event triggered.
        """
        # Cap at 2 active events
        active = [e for e in self._active_events if e.is_active(current_day)]
        if len(active) >= 2:
            return None

        # Deterministic random
        seed_str = f"{current_day}_political"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = _rng.Random(seed)

        if rng.random() >= POLITICAL_EVENT_DAILY_CHANCE:
            return None

        if not self._event_templates:
            return None

        # Pick template and faction pair
        template = rng.choice(self._event_templates)
        faction_ids = list(self._factions.keys())
        if len(faction_ids) < 2:
            return None

        rng.shuffle(faction_ids)
        faction_a = faction_ids[0]
        faction_b = faction_ids[1]

        # Pick description
        descriptions = template.get("descriptions", ["Political event"])
        desc_template = rng.choice(descriptions)
        faction_a_name = self._factions[faction_a].name
        faction_b_name = self._factions[faction_b].name
        description = desc_template.format(a=faction_a_name, b=faction_b_name)

        duration = rng.randint(
            POLITICAL_EVENT_MIN_DURATION, POLITICAL_EVENT_MAX_DURATION
        )

        event = PoliticalEvent(
            id=f"political_{current_day}_{template['event_type']}",
            event_type=PoliticalEventType(template["event_type"]),
            faction_a_id=faction_a,
            faction_b_id=faction_b,
            description=description,
            day_started=current_day,
            duration_days=duration,
            relationship_drift=template.get("relationship_drift", -1),
        )
        self._active_events.append(event)
        return event

    def resolve_event(
        self,
        event: PoliticalEvent,
        action: PoliticalAction,
        player: Any,
    ) -> list[str]:
        """Apply player's chosen action to a political event.

        Args:
            event: The event to resolve.
            action: The player's chosen action.
            player: Player instance.

        Returns:
            List of notification messages.
        """
        if event.resolved:
            return []

        event.resolved = True
        event.player_action = action
        messages: list[str] = []

        rep_a, rep_b = _ACTION_REP[action]

        if rep_a != 0:
            changes = self.apply_reputation_with_spillover(
                player, event.faction_a_id, rep_a
            )
            for fid, amt in changes:
                sign = "+" if amt > 0 else ""
                fname = self._factions.get(fid)
                name = fname.name if fname else fid
                messages.append(f"{sign}{amt} reputation with {name}")

        if rep_b != 0:
            changes = self.apply_reputation_with_spillover(
                player, event.faction_b_id, rep_b
            )
            for fid, amt in changes:
                sign = "+" if amt > 0 else ""
                fname = self._factions.get(fid)
                name = fname.name if fname else fid
                messages.append(f"{sign}{amt} reputation with {name}")

        # Mediation improves the bilateral relationship
        if action == PoliticalAction.MEDIATE:
            self.modify_relationship(
                event.faction_a_id, event.faction_b_id,
                _MEDIATE_RELATIONSHIP_BONUS,
            )
            messages.append("Faction relations improved through mediation")

        return messages

    def advance_day(self, current_day: int) -> None:
        """Process daily political event effects.

        Applies relationship drift for active events and removes expired ones.

        Args:
            current_day: Current game day.
        """
        for event in self._active_events:
            if event.is_active(current_day) and event.relationship_drift != 0:
                try:
                    self.modify_relationship(
                        event.faction_a_id, event.faction_b_id,
                        event.relationship_drift,
                    )
                except KeyError:
                    pass  # Relationship pair may not exist

        # Clean up expired/resolved events
        self._active_events = [
            e for e in self._active_events if e.is_active(current_day)
        ]

    def get_active_events(self) -> list[PoliticalEvent]:
        """Get all currently active political events."""
        return list(self._active_events)

    # --- Reputation Consequences ---

    def get_docking_allowed(
        self, player: Any, system_id: str
    ) -> tuple[bool, str]:
        """Check if player can dock at a system based on faction reputation.

        HOSTILE faction systems deny docking.

        Args:
            player: Player instance.
            system_id: System to check.

        Returns:
            Tuple of (allowed, reason_message).
        """
        faction_id = player.get_faction_for_system(system_id)
        if not faction_id:
            return (True, "")

        from spacegame.models.faction import ReputationTier

        tier = player.get_reputation_tier(faction_id)
        if tier == ReputationTier.HOSTILE:
            faction = self._factions.get(faction_id)
            name = faction.name if faction else faction_id
            return (False, f"{name} refuses to grant you docking clearance")
        return (True, "")

    def get_encounter_modifier(
        self, player: Any, system_id: str
    ) -> dict[str, Any]:
        """Get encounter modifications based on faction rep at a system.

        Args:
            player: Player instance.
            system_id: System to check.

        Returns:
            Dict with hostile_attack_chance, shakedown_multiplier, protection_chance.
        """
        from spacegame.config import REP_HOSTILE_ATTACK_CHANCE
        from spacegame.models.faction import ReputationTier

        result: dict[str, Any] = {
            "hostile_attack_chance": 0,
            "shakedown_multiplier": 1.0,
            "protection_chance": 0,
        }

        faction_id = player.get_faction_for_system(system_id)
        if not faction_id:
            return result

        tier = player.get_reputation_tier(faction_id)
        if tier == ReputationTier.HOSTILE:
            result["hostile_attack_chance"] = REP_HOSTILE_ATTACK_CHANCE
            result["shakedown_multiplier"] = 2.0
        elif tier == ReputationTier.UNFRIENDLY:
            result["shakedown_multiplier"] = 1.5
        elif tier == ReputationTier.FRIENDLY:
            result["protection_chance"] = 15
        elif tier == ReputationTier.ALLIED:
            result["protection_chance"] = 30

        return result

    # --- Intel System ---

    def deliver_intel(
        self,
        intel_id: str,
        target_faction_id: str,
        player: Any,
    ) -> tuple[bool, str]:
        """Deliver an intel report to a faction for credits and reputation.

        Args:
            intel_id: ID of the intel report to deliver.
            target_faction_id: Faction to deliver the intel to.
            player: Player instance.

        Returns:
            Tuple of (success, message).
        """
        report = self._intel_reports.get(intel_id)
        if not report:
            return (False, "Intel report not found")
        if report.delivered:
            return (False, "This intel has already been delivered")

        report.delivered = True

        # Credit reward
        credits = report.get_delivery_value(target_faction_id, self._factions)
        player.add_credits(credits)

        # Rep reward with target faction (through spillover)
        rep_amount = report.get_reputation_reward(target_faction_id, self._factions)
        self.apply_reputation_with_spillover(player, target_faction_id, rep_amount)

        # Backlash: if delivering to rival, source faction finds out
        source = self._factions.get(report.source_faction_id)
        if source and source.rivalry == target_faction_id:
            self.apply_reputation_with_spillover(
                player, report.source_faction_id, _INTEL_BACKLASH
            )

        target = self._factions.get(target_faction_id)
        target_name = target.name if target else target_faction_id
        return (
            True,
            f"Delivered intel to {target_name} for {credits} credits",
        )

    def get_npc_disposition_modifier(
        self, player: Any, npc_faction_id: str
    ) -> int:
        """Get disposition modifier for NPC based on player's faction standing.

        Args:
            player: Player instance.
            npc_faction_id: The NPC's faction ID.

        Returns:
            Disposition modifier (-15 to +15).
        """
        from spacegame.models.faction import ReputationTier

        tier = player.get_reputation_tier(npc_faction_id)
        _DISPOSITION_MAP = {
            ReputationTier.HOSTILE: -15,
            ReputationTier.UNFRIENDLY: -10,
            ReputationTier.NEUTRAL: 0,
            ReputationTier.FRIENDLY: 10,
            ReputationTier.ALLIED: 15,
        }
        return _DISPOSITION_MAP.get(tier, 0)

    # --- Faction Perks ---

    def set_faction_perks(
        self, faction_perks: dict[str, dict[str, list]]
    ) -> None:
        """Set faction perks data from DataLoader.

        Args:
            faction_perks: Nested dict of faction_id -> tier -> perk list.
        """
        self._faction_perks = faction_perks

    def get_active_perks(
        self, player: Any, system_id: str
    ) -> list:
        """Get all active faction perks for the player at a system.

        Args:
            player: Player instance.
            system_id: Current system ID.

        Returns:
            List of FactionPerk instances the player qualifies for.
        """
        from spacegame.models.faction_perks import get_active_perks

        if not hasattr(self, "_faction_perks"):
            return []

        faction_id = player.get_faction_for_system(system_id)
        if not faction_id:
            return []

        tier = player.get_reputation_tier(faction_id)
        return get_active_perks(self._faction_perks, faction_id, tier)

    def get_perk_bonus(
        self, player: Any, system_id: str, perk_type: str
    ) -> float:
        """Get total numeric bonus from active perks of a given type.

        Args:
            player: Player instance.
            system_id: Current system ID.
            perk_type: Perk type to sum (e.g. "buy_price_bonus").

        Returns:
            Total bonus as a float.
        """
        from spacegame.models.faction_perks import get_perk_bonus

        active = self.get_active_perks(player, system_id)
        return get_perk_bonus(active, perk_type)

    def has_perk(
        self, player: Any, system_id: str, perk_type: str
    ) -> bool:
        """Check if a boolean perk is active at the given system.

        Args:
            player: Player instance.
            system_id: Current system ID.
            perk_type: Perk type to check (e.g. "free_repairs").

        Returns:
            True if the perk is active.
        """
        from spacegame.models.faction_perks import has_perk

        active = self.get_active_perks(player, system_id)
        return has_perk(active, perk_type)

    # --- Serialization ---

    def to_dict(self) -> dict[str, Any]:
        """Serialize political state to dict."""
        return {
            "relationships": [
                rel.to_dict() for rel in self._relationships.values()
            ],
            "active_events": [
                event.to_dict() for event in self._active_events
            ],
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], factions: dict[str, Faction]
    ) -> PoliticsManager:
        """Deserialize from dict, with defaults for missing data.

        Args:
            data: Serialized political state (may be empty for old saves).
            factions: Faction definitions for rivalry lookups.

        Returns:
            Restored PoliticsManager instance.
        """
        relationships: list[FactionRelationship] = []
        for rel_data in data.get("relationships", []):
            relationships.append(FactionRelationship.from_dict(rel_data))

        if not relationships:
            # Load defaults from data files for old saves / fresh state
            from spacegame.data_loader import get_data_loader

            loader = get_data_loader()
            if hasattr(loader, "faction_relationships"):
                relationships = list(loader.faction_relationships)

        mgr = cls(relationships=relationships, factions=factions)

        # Restore active events
        for event_data in data.get("active_events", []):
            mgr._active_events.append(PoliticalEvent.from_dict(event_data))

        return mgr
