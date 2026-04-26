"""Station salience — which cards deserve highlighting at a station.

Per `requirements/station_legibility.md`:

- SL-1 introduces `is_system_mission_relevant` for `unique`-card demotion.
  When a system has any active mission objective, all `unique`-typed
  locations at that system stay in the main action grid; otherwise they
  demote to the POI footer strip.

- SL-3 will extend this module with `get_recommended_card` for the
  cyan-glow highlight (reusing the cantina PT-016 pattern).

Mission objectives target *systems* (REACH_SYSTEM) or NPCs
(TALK_TO_NPC, which resolves to the NPC's home system). No objective
type targets a sub-station location ID, per data audit 2026-04-26. So
mission relevance is evaluated at the system level, and ALL `unique`
locations at a mission-relevant system are elevated together. This
matches the design intent of station_legibility.md (Fulcrum case: when
the player docks at the_fulcrum due to a campaign mission, fulcrum_core
is contextually elevated alongside any other unique cards there).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.mission import MissionManager


def is_system_mission_relevant(
    mission_manager: Optional["MissionManager"],
    system_id: str,
    npc_home_systems: Optional[dict[str, str]] = None,
) -> bool:
    """Return True if any active mission has an objective at this system.

    Used by `station_layouts.py` to decide whether `unique`-typed location
    cards stay in the main action grid (mission-relevant) or demote to
    the POI footer strip (lore-only).

    Args:
        mission_manager: The active MissionManager, or None when missions
            haven't been wired (tutorial states, dev launches, tests).
        system_id: The system to check.
        npc_home_systems: Optional mapping of NPC ID to home system ID,
            used to resolve TALK_TO_NPC objectives. When omitted,
            TALK_TO_NPC objectives are ignored.

    Returns:
        True if the system has at least one active mission objective.
    """
    if mission_manager is None:
        return False
    return system_id in mission_manager.get_active_target_systems(npc_home_systems)
