"""
Random market events system.

Events that cause dramatic price fluctuations for specific commodities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import random


class EventType(Enum):
    """Type of market event."""

    SHORTAGE = "shortage"
    SURPLUS = "surplus"
    DISASTER = "disaster"
    BOOM = "boom"


@dataclass
class MarketEvent:
    """
    A random event affecting commodity prices.

    Events create dramatic price swings for a single commodity
    at a specific system for a limited duration.
    """

    event_type: EventType
    commodity_id: str
    system_id: str
    price_multiplier: float  # Applied to base price (e.g., 2.0 = double, 0.5 = half)
    duration_days: int  # How many days the event lasts
    day_started: int  # Game day when event began
    description: str

    def is_active(self, current_day: int) -> bool:
        """
        Check if event is still active.

        Args:
            current_day: Current game day

        Returns:
            True if event is still in effect
        """
        return current_day < (self.day_started + self.duration_days)

    def days_remaining(self, current_day: int) -> int:
        """
        Get days remaining for this event.

        Args:
            current_day: Current game day

        Returns:
            Days remaining, or 0 if expired
        """
        remaining = (self.day_started + self.duration_days) - current_day
        return max(0, remaining)


class EventGenerator:
    """
    Generates random market events.

    Events have a low probability of occurring each day,
    but create significant market opportunities when they do.
    """

    # Event probability per day (5%)
    EVENT_CHANCE = 0.05

    # Event duration ranges (in days)
    MIN_DURATION = 3
    MAX_DURATION = 7

    # Price multiplier ranges for each event type
    EVENT_EFFECTS = {
        EventType.SHORTAGE: (1.5, 2.5),  # 50-150% price increase
        EventType.SURPLUS: (0.3, 0.6),  # 40-70% price decrease
        EventType.DISASTER: (2.0, 4.0),  # 100-300% price increase
        EventType.BOOM: (0.2, 0.4),  # 60-80% price decrease
    }

    # Event description templates
    EVENT_DESCRIPTIONS = {
        EventType.SHORTAGE: [
            "Supply chain disruption causes {commodity} shortage",
            "Labor strike halts {commodity} production",
            "Transport delays create {commodity} scarcity",
        ],
        EventType.SURPLUS: [
            "Bumper harvest floods market with {commodity}",
            "Overproduction creates {commodity} glut",
            "Canceled contracts leave excess {commodity}",
        ],
        EventType.DISASTER: [
            "Factory explosion devastates {commodity} supply",
            "Asteroid strike destroys {commodity} stockpiles",
            "Epidemic cripples {commodity} production",
        ],
        EventType.BOOM: [
            "New technology makes {commodity} obsolete",
            "Synthetic alternative floods {commodity} market",
            "Trade agreement dumps cheap {commodity}",
        ],
    }

    def __init__(self, commodities: list[str], systems: list[str]):
        """
        Initialize event generator.

        Args:
            commodities: List of commodity IDs
            systems: List of system IDs
        """
        self.commodities = commodities
        self.systems = systems

    def try_generate_event(
        self, current_day: int, commodity_names: dict[str, str]
    ) -> Optional[MarketEvent]:
        """
        Attempt to generate a random event.

        Args:
            current_day: Current game day
            commodity_names: Dict mapping commodity_id to display name

        Returns:
            MarketEvent if generated, None otherwise
        """
        # Check if event should occur
        if random.random() > self.EVENT_CHANCE:
            return None

        # Select random event parameters
        event_type = random.choice(list(EventType))
        commodity_id = random.choice(self.commodities)
        system_id = random.choice(self.systems)
        duration = random.randint(self.MIN_DURATION, self.MAX_DURATION)

        # Get price multiplier for this event type
        min_mult, max_mult = self.EVENT_EFFECTS[event_type]
        price_multiplier = random.uniform(min_mult, max_mult)

        # Generate description
        commodity_name = commodity_names.get(commodity_id, commodity_id)
        template = random.choice(self.EVENT_DESCRIPTIONS[event_type])
        description = template.format(commodity=commodity_name)

        return MarketEvent(
            event_type=event_type,
            commodity_id=commodity_id,
            system_id=system_id,
            price_multiplier=price_multiplier,
            duration_days=duration,
            day_started=current_day,
            description=description,
        )
