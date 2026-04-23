"""PT-J "Where missions start" regression tests.

PT-013: NPC-initiated missions should surface in dialogue, not in the
Mission Log's Available tab. Encounter-initiated missions likewise — they
reveal through gameplay, not menus.

The Cantina Station Board already filtered to discovery_method=='station_board'
before this sprint; these tests lock in that behavior and the new
Mission Log filter.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.models.mission import Mission, MissionManager, MissionStatus


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _mission(mid: str, discovery: str = "", required_flags: list[str] | None = None) -> Mission:
    return Mission(
        id=mid,
        name=mid,
        description="",
        hint="",
        objectives=[],
        rewards=[],
        mission_type="side",
        available_at=[],
        required_flags=required_flags or [],
        discovery_method=discovery,
    )


def _manager_with(*missions: Mission) -> MissionManager:
    mgr = MissionManager([])
    for m in missions:
        mgr.add_mission(m, initial_status=MissionStatus.AVAILABLE)
    return mgr


# ---------------------------------------------------------------------------
# Mission data discipline — confirm all current NPC missions are auto-accept
# (so they don't linger in the Available tab between dialogue and acceptance)
# ---------------------------------------------------------------------------


class TestMissionDataDiscipline:
    def _all_missions(self) -> list[dict]:
        base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "missions")
        out: list[dict] = []
        for fname in ("missions.json", "side_missions.json", "crew_quests.json"):
            path = os.path.join(base, fname)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            out.extend(data.get("missions", []))
        return out

    def test_all_npc_missions_have_required_flags(self) -> None:
        """A mission surfaced via NPC must gate activation on the dialogue flag;
        otherwise it would show up as AVAILABLE before the NPC encounter."""
        for m in self._all_missions():
            if m.get("discovery_method") == "npc":
                assert m.get("required_flags"), (
                    f"NPC-initiated mission {m['id']} must have required_flags "
                    f"to gate availability on the dialogue flag"
                )

    def test_all_npc_missions_auto_accept(self) -> None:
        """NPC missions should auto-accept so they go UNAVAILABLE -> ACTIVE
        on dialogue, never lingering in AVAILABLE."""
        for m in self._all_missions():
            if m.get("discovery_method") == "npc":
                assert m.get("auto_accept"), (
                    f"NPC-initiated mission {m['id']} should auto_accept=true "
                    f"so dialogue acceptance jumps it straight to ACTIVE"
                )


# ---------------------------------------------------------------------------
# MissionManager availability still respects required_flags
# (locks in existing behavior so the Available-tab filter isn't the only gate)
# ---------------------------------------------------------------------------


class TestMissionAvailabilityGating:
    def test_required_flags_block_availability(self) -> None:
        mgr = MissionManager([])
        m = _mission("test_npc_m", discovery="npc", required_flags=["met_npc"])
        mgr.add_mission(m, initial_status=MissionStatus.UNAVAILABLE)
        mgr.update_availability(player_flags={})  # flag not set
        assert mgr.get_status("test_npc_m") == MissionStatus.UNAVAILABLE

    def test_required_flags_met_unlocks(self) -> None:
        mgr = MissionManager([])
        m = _mission("test_npc_m", discovery="npc", required_flags=["met_npc"])
        mgr.add_mission(m, initial_status=MissionStatus.UNAVAILABLE)
        mgr.update_availability(player_flags={"met_npc": True})
        assert mgr.get_status("test_npc_m") == MissionStatus.AVAILABLE


# ---------------------------------------------------------------------------
# Mission Log "Available" tab filters NPC + encounter missions
# ---------------------------------------------------------------------------


class TestMissionLogAvailableTabFilter:
    def _build_log_view(self, mgr: MissionManager, tab: str = "available"):
        from spacegame.views.mission_log_view import MissionLogView

        manager = pygame_gui.UIManager((1280, 720))
        view = MissionLogView(manager, mgr, data_loader=MagicMock(), player=MagicMock())
        view.on_enter()  # initializes _abandon_btn and other UI bits
        view._current_tab = tab
        view._refresh_list()
        return view

    def test_hides_npc_initiated(self) -> None:
        mgr = _manager_with(
            _mission("board_job", discovery="station_board"),
            _mission("npc_job", discovery="npc"),
        )
        view = self._build_log_view(mgr)
        rendered_ids = {item.mission.id for item in view._mission_items}
        assert "board_job" in rendered_ids
        assert "npc_job" not in rendered_ids

    def test_hides_encounter_initiated(self) -> None:
        mgr = _manager_with(
            _mission("board_job", discovery="station_board"),
            _mission("encounter_job", discovery="encounter"),
        )
        view = self._build_log_view(mgr)
        rendered_ids = {item.mission.id for item in view._mission_items}
        assert "encounter_job" not in rendered_ids

    def test_shows_campaign_missions_with_empty_discovery(self) -> None:
        """Campaign missions use empty discovery_method; they should stay
        visible in the Available tab since there's no other surface for them."""
        mgr = _manager_with(
            _mission("campaign_m", discovery=""),
        )
        view = self._build_log_view(mgr)
        rendered_ids = {item.mission.id for item in view._mission_items}
        assert "campaign_m" in rendered_ids

    def test_active_tab_shows_npc_missions(self) -> None:
        """Once accepted, NPC missions are ACTIVE and SHOULD appear in the
        log — the filter is Available-only."""
        mgr = MissionManager([])
        m = _mission("npc_active", discovery="npc")
        mgr.add_mission(m, initial_status=MissionStatus.ACTIVE)
        view = self._build_log_view(mgr, tab="active")
        rendered_ids = {item.mission.id for item in view._mission_items}
        assert "npc_active" in rendered_ids


# ---------------------------------------------------------------------------
# Cantina Station Board already filters — lock in the behavior
# ---------------------------------------------------------------------------


class TestCantinaBoardFilter:
    """The cantina Station Board filters to discovery_method=='station_board'
    at cantina_view.py:216. This test asserts the filter expression stays
    in that file — if it disappears, NPC missions would leak to the board."""

    def test_cantina_filters_board_discovery_method(self) -> None:
        from pathlib import Path

        source = Path("spacegame/views/cantina_view.py").read_text(encoding="utf-8")
        assert 'm.discovery_method == "station_board"' in source, (
            "Cantina board must filter on discovery_method == station_board "
            "to prevent NPC-initiated missions from leaking to the board"
        )
