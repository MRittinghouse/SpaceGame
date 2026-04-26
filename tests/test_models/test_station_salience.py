"""Tests for spacegame.models.station_salience.

SL-1 (station_legibility.md): introduces system-mission relevance for
`unique`-card demotion in the station hub view. SL-3 will extend this
module with `get_recommended_card` for per-card cyan-glow highlighting.

Mission objectives target *systems* (REACH_SYSTEM) or NPCs (TALK_TO_NPC,
which resolves to the NPC's home system). No objective type targets a
sub-station location ID, so mission relevance is evaluated at the system
level: when a system has any active mission objective, ALL `unique`-typed
locations at that system are elevated together.
"""

from __future__ import annotations

from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.station_salience import is_system_mission_relevant


def _make_manager(missions: list[Mission]) -> MissionManager:
    """Build a MissionManager with the given missions registered."""
    return MissionManager(missions)


def _reach_system_mission(mission_id: str, system_id: str) -> Mission:
    """Construct a minimal mission with a single REACH_SYSTEM objective."""
    return Mission(
        id=mission_id,
        name=f"Mission {mission_id}",
        description="",
        objectives=[
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id=system_id,
                description=f"Reach {system_id}",
            )
        ],
    )


def _talk_to_npc_mission(mission_id: str, npc_id: str) -> Mission:
    """Construct a minimal mission with a single TALK_TO_NPC objective."""
    return Mission(
        id=mission_id,
        name=f"Mission {mission_id}",
        description="",
        objectives=[
            MissionObjective(
                type=ObjectiveType.TALK_TO_NPC,
                target_id=npc_id,
                description=f"Talk to {npc_id}",
            )
        ],
    )


class TestIsSystemMissionRelevant:
    """is_system_mission_relevant — does any active mission target this system?"""

    def test_returns_false_when_mission_manager_is_none(self) -> None:
        """No mission manager (tutorial states, dev launches) → not relevant."""
        assert is_system_mission_relevant(None, "iron_depths") is False

    def test_returns_false_when_no_active_missions(self) -> None:
        """Empty manager → no relevance."""
        mgr = _make_manager([])
        assert is_system_mission_relevant(mgr, "iron_depths") is False

    def test_returns_false_when_active_mission_targets_different_system(self) -> None:
        """Active mission for system A → system B is not relevant."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "iron_depths") is False

    def test_returns_true_when_reach_system_objective_targets_this_system(self) -> None:
        """The Fulcrum case: campaign mission to reach a system makes that system relevant."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "the_fulcrum") is True

    def test_returns_true_when_talk_to_npc_objective_resolves_to_this_system(self) -> None:
        """TALK_TO_NPC at an NPC whose home system is this one → relevant."""
        m = _talk_to_npc_mission("m1", "marcus_jin")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        npc_homes = {"marcus_jin": "breakstone"}
        assert is_system_mission_relevant(mgr, "breakstone", npc_homes) is True

    def test_talk_to_npc_without_npc_home_mapping_does_not_match(self) -> None:
        """If npc_home_systems isn't passed, TALK_TO_NPC objectives don't contribute."""
        m = _talk_to_npc_mission("m1", "marcus_jin")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "breakstone") is False

    def test_completed_mission_does_not_make_system_relevant(self) -> None:
        """Only ACTIVE missions count. Completed missions don't elevate cards."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.COMPLETED
        assert is_system_mission_relevant(mgr, "the_fulcrum") is False

    def test_multiple_active_missions_any_match_returns_true(self) -> None:
        """If any active mission targets the system, return True."""
        m1 = _reach_system_mission("m1", "the_fulcrum")
        m2 = _reach_system_mission("m2", "iron_depths")
        mgr = _make_manager([m1, m2])
        mgr._status["m1"] = MissionStatus.ACTIVE
        mgr._status["m2"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "iron_depths") is True
        assert is_system_mission_relevant(mgr, "the_fulcrum") is True
        assert is_system_mission_relevant(mgr, "nexus_prime") is False
