"""
Achievement data model.

Pure data container for achievement definitions loaded from JSON.
"""

from dataclasses import dataclass


@dataclass
class Achievement:
    """A single achievement definition."""

    id: str
    name: str
    description: str
    category: str
    stat_key: str
    threshold: int
    reward_type: str  # "xp", "credits", "skill_point", "upgrade"
    reward_value: int  # Amount for xp/credits, count for skill_point
    hidden: bool = False
