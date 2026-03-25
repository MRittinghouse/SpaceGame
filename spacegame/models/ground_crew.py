"""Ground crew, equipment, & attribute bonuses for ground missions.

Pre-computes all crew ability bonuses, equipment effects, and
attribute modifiers for ground exploration and combat. One object
flows through the system instead of scattered conditionals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.attributes import AttributeSheet

# Crew member IDs that provide ground bonuses
_ELENA = "elena_reeves"
_MARCUS = "marcus_jin"
_PRIYA = "dr_priya_osei"
_TOMAS = "tomas_drifter"

# ING threshold for noise reduction
_ING_NOISE_THRESHOLD = 4

# Equipment effect keys (must match ground_equipment.py constants)
_EFF_VISION = "vision_bonus"
_EFF_NOISE = "noise_reduction"
_EFF_SILENT = "silent_doors"
_EFF_HP = "hp_bonus"
_EFF_LOCKPICK = "lockpick"
_EFF_EMP = "emp_disable_turns"
_EFF_ABSORB = "absorb_first_hit"


@dataclass
class GroundCrewBonuses:
    """Pre-computed bonuses from crew selection, equipment, and attributes.

    Computed once at mission start and passed through exploration
    and combat systems.
    """

    # Exploration bonuses
    vision_radius_bonus: int = 0
    noise_reduction: int = 0
    silent_doors: bool = False
    reveal_patrol_routes: bool = False

    # Combat bonuses
    retreat_bonus: int = 0
    talk_bonus: int = 0
    analyze_weakness_available: bool = False

    # Equipment-based bonuses
    hp_bonus: int = 0
    absorb_first_hit: bool = False
    has_lockpick: bool = False
    emp_disable_turns: int = 0

    @classmethod
    def compute(
        cls,
        crew_ids: list[str],
        attributes: Optional[AttributeSheet] = None,
        equipment_ids: Optional[list[str]] = None,
    ) -> GroundCrewBonuses:
        """Build bonuses from crew selection, equipment, and attributes.

        Args:
            crew_ids: IDs of crew members on this ground mission.
            attributes: Player's attribute sheet.
            equipment_ids: IDs of equipped ground equipment.

        Returns:
            GroundCrewBonuses with all modifiers computed.
        """
        vision = 0
        noise_red = 0
        silent = False
        reveal_patrol = False
        retreat = 0
        talk = 0
        analyze = False
        hp = 0
        absorb = False
        lockpick = False
        emp_turns = 0

        # --- Crew abilities ---
        for cid in crew_ids:
            if cid == _ELENA:
                vision += 1
                reveal_patrol = True
                retreat += 2
            elif cid == _MARCUS:
                silent = True
            elif cid == _PRIYA:
                analyze = True
            elif cid == _TOMAS:
                noise_red += 1
                talk += 2

        # --- Equipment effects ---
        if equipment_ids:
            from spacegame.data_loader import get_data_loader

            dl = get_data_loader()
            for eq_id in equipment_ids:
                eq = dl.ground_equipment.get(eq_id)
                if not eq:
                    continue
                effects = eq.effects
                vision += int(effects.get(_EFF_VISION, 0))
                noise_red += int(effects.get(_EFF_NOISE, 0))
                if effects.get(_EFF_SILENT, 0):
                    silent = True
                hp += int(effects.get(_EFF_HP, 0))
                if effects.get(_EFF_ABSORB, 0):
                    absorb = True
                if effects.get(_EFF_LOCKPICK, 0):
                    lockpick = True
                emp_turns = max(emp_turns, int(effects.get(_EFF_EMP, 0)))

        # --- Attribute bonuses ---
        if attributes:
            acu = attributes.get_value("acu")
            syn = attributes.get_value("syn")
            ing = attributes.get_value("ing")

            vision += acu // 2
            talk += syn // 2
            if ing >= _ING_NOISE_THRESHOLD:
                noise_red += 1

        return cls(
            vision_radius_bonus=vision,
            noise_reduction=noise_red,
            silent_doors=silent,
            reveal_patrol_routes=reveal_patrol,
            retreat_bonus=retreat,
            talk_bonus=talk,
            analyze_weakness_available=analyze,
            hp_bonus=hp,
            absorb_first_hit=absorb,
            has_lockpick=lockpick,
            emp_disable_turns=emp_turns,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "vision_radius_bonus": self.vision_radius_bonus,
            "noise_reduction": self.noise_reduction,
            "silent_doors": self.silent_doors,
            "reveal_patrol_routes": self.reveal_patrol_routes,
            "retreat_bonus": self.retreat_bonus,
            "talk_bonus": self.talk_bonus,
            "analyze_weakness_available": self.analyze_weakness_available,
            "hp_bonus": self.hp_bonus,
            "absorb_first_hit": self.absorb_first_hit,
            "has_lockpick": self.has_lockpick,
            "emp_disable_turns": self.emp_disable_turns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GroundCrewBonuses:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with bonus fields.

        Returns:
            GroundCrewBonuses instance.
        """
        return cls(
            vision_radius_bonus=data.get("vision_radius_bonus", 0),
            noise_reduction=data.get("noise_reduction", 0),
            silent_doors=data.get("silent_doors", False),
            reveal_patrol_routes=data.get("reveal_patrol_routes", False),
            retreat_bonus=data.get("retreat_bonus", 0),
            talk_bonus=data.get("talk_bonus", 0),
            analyze_weakness_available=data.get("analyze_weakness_available", False),
            hp_bonus=data.get("hp_bonus", 0),
            absorb_first_hit=data.get("absorb_first_hit", False),
            has_lockpick=data.get("has_lockpick", False),
            emp_disable_turns=data.get("emp_disable_turns", 0),
        )
