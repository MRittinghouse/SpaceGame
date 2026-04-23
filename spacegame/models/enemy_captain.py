"""Enemy captain model — named personalities attached to combat encounters.

CE-1 foundation for the Combat Encounters Non-Generic phase. A captain is
a character attached to a combat encounter: named, voiced, tied to a home
sector and a signature ship template. Pre-combat hails, surrender lines,
retreat/victory/defeat lines live on the captain, not the encounter.

Ship templates and captains are **independent**. A single
``pirate_raider`` template can be the ship under Captain Vela's boots in
Haven's Rest and under Captain Hadrian's in Iron Depths. Captains carry
the voice; templates carry the stats. Encounters reference captains by
``captain_id`` (on ``EncounterDefinition``).

CE-1 ships two captains as stub data. CE-2 scales the roster to 15-20.
``is_recurring`` defaults to False — RC will flip specific captains to
True when the rival-captain system lands.

**Future behavior-variance hooks** (intentional, not implemented in CE-1):
- ``retreat_hp_threshold`` (RC-2): hull percentage below which the
  captain flees rather than fights to destruction.
- ``personality_tags`` (RC-5+): list like ``["honorable", "ruthless",
  "coward"]`` that lets AI behavior / dialogue pickers key off captain
  personality.
- ``surrender_willingness`` (CE-3+): probability-or-flag controlling
  whether a captain's surrender complication fires at low HP.

These stay out of the dataclass until RC/CE-3 actually need them — but
the expansion direction is documented so future sprints see the hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EnemyCaptain:
    """A named captain attached to one or more combat encounters.

    Attributes:
        id: Stable identifier used by ``EncounterDefinition.captain_id``.
            snake_case; suffix with short descriptors when helpful
            (``vela_wolfs_ear``).
        name: Display name (``"Captain Vela"``).
        nickname: Ship / callsign nickname (``"Wolf's Ear"``). May be
            empty for captains without a notable ship name.
        home_sector: The system where this captain is most often
            encountered. Used for spawn-weighting (CE-3+).
        signature_ship_template: Enemy template id the captain flies.
            (``"pirate_raider"``). Not enforced as a foreign key at load
            time — templates live in enemy definitions.
        pre_combat_hail: Line shown as the encounter description when
            this captain's encounter triggers.
        surrender_line: Delivered if the player's path leads the captain
            to surrender. Optional.
        retreat_line: Delivered when the captain flees (RC-2 retreat
            mechanic). Optional in CE-1, required by RC.
        victory_line: Delivered on captain victory (player defeat).
            Optional.
        defeat_line: Delivered on captain defeat (player victory).
            Optional.
        is_recurring: True only for rival captains (RC phase). False
            for the flavor-tier captains CE-2 authors.
    """

    id: str
    name: str
    nickname: str
    home_sector: str
    signature_ship_template: str
    pre_combat_hail: str
    surrender_line: str = ""
    retreat_line: str = ""
    victory_line: str = ""
    defeat_line: str = ""
    is_recurring: bool = False

    @property
    def display_name(self) -> str:
        """Panel-header text: 'Captain Vela' or 'Captain Vela — Wolf's Ear'."""
        if self.nickname:
            return f"{self.name} \u2014 {self.nickname}"
        return self.name

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnemyCaptain":
        """Parse an ``EnemyCaptain`` from its JSON representation.

        Args:
            data: Raw dict from ``data/combat/captains.json``.

        Returns:
            ``EnemyCaptain`` instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            nickname=data.get("nickname", ""),
            home_sector=data["home_sector"],
            signature_ship_template=data["signature_ship_template"],
            pre_combat_hail=data["pre_combat_hail"],
            surrender_line=data.get("surrender_line", ""),
            retreat_line=data.get("retreat_line", ""),
            victory_line=data.get("victory_line", ""),
            defeat_line=data.get("defeat_line", ""),
            is_recurring=bool(data.get("is_recurring", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "id": self.id,
            "name": self.name,
            "nickname": self.nickname,
            "home_sector": self.home_sector,
            "signature_ship_template": self.signature_ship_template,
            "pre_combat_hail": self.pre_combat_hail,
            "surrender_line": self.surrender_line,
            "retreat_line": self.retreat_line,
            "victory_line": self.victory_line,
            "defeat_line": self.defeat_line,
            "is_recurring": self.is_recurring,
        }


def lookup_captain(
    captains: dict[str, EnemyCaptain], captain_id: Optional[str]
) -> Optional[EnemyCaptain]:
    """Look up a captain by id, gracefully handling None / missing ids.

    Args:
        captains: ``DataLoader.captains`` mapping.
        captain_id: Id to look up, or ``None``.

    Returns:
        The ``EnemyCaptain`` or ``None``.
    """
    if not captain_id:
        return None
    return captains.get(captain_id)
