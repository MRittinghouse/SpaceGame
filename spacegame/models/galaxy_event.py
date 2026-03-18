"""
Galaxy event system.

Heavyweight events that reshape gameplay dynamics — embargoes block trade,
festivals boost reputation, strikes halt production, breakthroughs cheapen
tech, pirate surges increase encounter danger. These interact with player
skills to create situational opportunities for different character builds.
"""

from __future__ import annotations

import hashlib
import random as _rng
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from spacegame.config import (
    GALAXY_EVENT_DAILY_CHANCE,
    GALAXY_EVENT_MAX_ACTIVE,
    GALAXY_EVENT_MIN_DURATION,
    GALAXY_EVENT_MAX_DURATION,
)


class GalaxyEventType(Enum):
    """Type of galaxy-wide event."""

    EMBARGO = "embargo"
    FESTIVAL = "festival"
    LABOR_STRIKE = "labor_strike"
    RESEARCH_BREAKTHROUGH = "research_breakthrough"
    PIRATE_SURGE = "pirate_surge"


@dataclass
class GalaxyEvent:
    """A galaxy event that changes how a system behaves for a limited time.

    Unlike MarketEvent (single price multiplier), galaxy events have complex,
    type-dependent effects: embargoes block commodities, festivals grant rep,
    strikes halt production, surges increase encounter danger.
    """

    id: str
    event_type: GalaxyEventType
    system_id: str
    faction_id: str
    description: str
    flavor_text: str
    day_started: int
    duration_days: int
    # Type-dependent effects
    blocked_commodities: list[str] = field(default_factory=list)
    price_modifiers: dict[str, float] = field(default_factory=dict)
    shutdown_tags: list[str] = field(default_factory=list)
    encounter_chance_modifier: float = 1.0
    danger_modifier: int = 0
    rep_bonus_faction: str = ""
    rep_bonus_amount: int = 0
    skill_opportunity: str = ""
    # Chaining
    chain_id: str = ""
    chain_step: int = 0

    def is_active(self, current_day: int) -> bool:
        """Check if event is still active."""
        return current_day < (self.day_started + self.duration_days)

    def days_remaining(self, current_day: int) -> int:
        """Get days remaining for this event."""
        remaining = (self.day_started + self.duration_days) - current_day
        return max(0, remaining)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for save system."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "system_id": self.system_id,
            "faction_id": self.faction_id,
            "description": self.description,
            "flavor_text": self.flavor_text,
            "day_started": self.day_started,
            "duration_days": self.duration_days,
            "blocked_commodities": self.blocked_commodities,
            "price_modifiers": self.price_modifiers,
            "shutdown_tags": self.shutdown_tags,
            "encounter_chance_modifier": self.encounter_chance_modifier,
            "danger_modifier": self.danger_modifier,
            "rep_bonus_faction": self.rep_bonus_faction,
            "rep_bonus_amount": self.rep_bonus_amount,
            "skill_opportunity": self.skill_opportunity,
            "chain_id": self.chain_id,
            "chain_step": self.chain_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GalaxyEvent:
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            event_type=GalaxyEventType(data["event_type"]),
            system_id=data["system_id"],
            faction_id=data["faction_id"],
            description=data["description"],
            flavor_text=data["flavor_text"],
            day_started=data["day_started"],
            duration_days=data["duration_days"],
            blocked_commodities=data.get("blocked_commodities", []),
            price_modifiers=data.get("price_modifiers", {}),
            shutdown_tags=data.get("shutdown_tags", []),
            encounter_chance_modifier=data.get("encounter_chance_modifier", 1.0),
            danger_modifier=data.get("danger_modifier", 0),
            rep_bonus_faction=data.get("rep_bonus_faction", ""),
            rep_bonus_amount=data.get("rep_bonus_amount", 0),
            skill_opportunity=data.get("skill_opportunity", ""),
            chain_id=data.get("chain_id", ""),
            chain_step=data.get("chain_step", 0),
        )


class GalaxyEventGenerator:
    """Generates galaxy events from data-driven templates.

    Uses deterministic seeding so the same game day always produces the
    same result. Respects a global cap on active events.
    """

    def __init__(
        self,
        templates: list[dict[str, Any]],
        chains: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self._templates = templates
        self._template_by_id = {t["id"]: t for t in templates}
        self._chains = chains or []
        self._chain_by_id = {c["chain_id"]: c for c in self._chains}
        self._pending_chain_events: list[tuple[int, str]] = []  # (fire_day, template_id)

    def check_chain_triggers(
        self, expired_event: GalaxyEvent, current_day: int
    ) -> None:
        """Queue chain follow-up events when an event expires.

        Args:
            expired_event: The event that just expired.
            current_day: Current game day.
        """
        if not expired_event.chain_id:
            return
        chain = self._chain_by_id.get(expired_event.chain_id)
        if not chain:
            return
        next_step = expired_event.chain_step + 1
        for step in chain.get("steps", []):
            if step.get("step") == next_step:
                delay = step.get("delay_days", 0)
                fire_day = current_day + delay
                self._pending_chain_events.append((fire_day, step["event_id"]))
                break

    def _try_fire_chain_event(
        self, current_day: int
    ) -> Optional[GalaxyEvent]:
        """Check if any pending chain events should fire.

        Args:
            current_day: Current game day.

        Returns:
            GalaxyEvent if a chain event fires, None otherwise.
        """
        for i, (fire_day, template_id) in enumerate(self._pending_chain_events):
            if current_day >= fire_day:
                template = self._template_by_id.get(template_id)
                if template:
                    self._pending_chain_events.pop(i)
                    return self._build_event_from_template(template, current_day)
        return None

    def _build_event_from_template(
        self, template: dict[str, Any], current_day: int
    ) -> GalaxyEvent:
        """Build a GalaxyEvent from a template dict.

        Args:
            template: Template dict from galaxy_events.json.
            current_day: Current game day.

        Returns:
            Constructed GalaxyEvent.
        """
        rng = _rng.Random(current_day)
        event_type = GalaxyEventType(template["event_type"])
        duration = rng.randint(
            template.get("duration_min", GALAXY_EVENT_MIN_DURATION),
            template.get("duration_max", GALAXY_EVENT_MAX_DURATION),
        )
        descriptions = template.get("descriptions", ["A galaxy event occurs"])
        target_systems = template.get("target_systems", [])
        system_id = rng.choice(target_systems) if target_systems else ""
        description = rng.choice(descriptions).format(system=system_id)
        flavor_texts = template.get("flavor_texts", [""])
        flavor_text = rng.choice(flavor_texts)

        return GalaxyEvent(
            id=f"{template['id']}_{current_day}",
            event_type=event_type,
            system_id=system_id,
            faction_id=template.get("faction_id", ""),
            description=description,
            flavor_text=flavor_text,
            day_started=current_day,
            duration_days=duration,
            blocked_commodities=list(template.get("blocked_commodities", [])),
            price_modifiers=dict(template.get("price_modifiers", {})),
            shutdown_tags=list(template.get("shutdown_tags", [])),
            encounter_chance_modifier=template.get("encounter_chance_modifier", 1.0),
            danger_modifier=template.get("danger_modifier", 0),
            rep_bonus_faction=template.get("rep_bonus_faction", ""),
            rep_bonus_amount=template.get("rep_bonus_amount", 0),
            skill_opportunity=template.get("skill_opportunity", ""),
            chain_id=template.get("chain_id", ""),
            chain_step=template.get("chain_step", 0),
        )

    def try_generate_event(
        self,
        current_day: int,
        active_events: dict[str, list[GalaxyEvent]],
    ) -> Optional[GalaxyEvent]:
        """Attempt to generate a galaxy event.

        Checks pending chain events first, then tries random generation.

        Args:
            current_day: Current game day.
            active_events: Dict of system_id -> list of active galaxy events.

        Returns:
            GalaxyEvent if generated, None otherwise.
        """
        # Check chain events first (these bypass the daily chance roll)
        chain_event = self._try_fire_chain_event(current_day)
        if chain_event:
            return chain_event

        if not self._templates:
            return None

        # Count total active events across all systems
        total_active = sum(len(evts) for evts in active_events.values())
        if total_active >= GALAXY_EVENT_MAX_ACTIVE:
            return None

        # Deterministic random
        seed_str = f"{current_day}_galaxy"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = _rng.Random(seed)

        if rng.random() >= GALAXY_EVENT_DAILY_CHANCE:
            return None

        # Weighted template selection
        weights = [t.get("weight", 10) for t in self._templates]
        total_weight = sum(weights)
        roll = rng.uniform(0, total_weight)
        cumulative = 0.0
        template = self._templates[0]
        for t, w in zip(self._templates, weights):
            cumulative += w
            if roll <= cumulative:
                template = t
                break

        # Select target system
        target_systems = template.get("target_systems", [])
        if not target_systems:
            return None

        # Override the RNG in _build_event_from_template by using this seed
        return self._build_event_from_template(template, current_day)
