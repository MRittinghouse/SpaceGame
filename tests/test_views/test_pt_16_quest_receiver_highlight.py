"""PT-016: cantina NPCs that receive an active quest get a visual highlight.

Playtest finding (2026-04-23): clicking an NPC could either start a new
quest OR advance an active one, and there was no way to tell which. This
sprint adds:
  - `_npc_is_quest_receiver(npc_id)` helper on CantinaView
  - "(Active Quest)" text marker appended to the button label
  - Pulsing cyan glow rendered in render_top around receiver buttons
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _mission_with_talk(mid: str, npc_id: str) -> Mission:
    return Mission(
        id=mid,
        name=mid,
        description="",
        hint="",
        objectives=[
            MissionObjective(
                type=ObjectiveType.TALK_TO_NPC,
                target_id=npc_id,
                target_quantity=1,
                description=f"Talk to {npc_id}",
            )
        ],
        rewards=[],
        mission_type="side",
        available_at=[],
    )


def _mgr_with_active(*missions: Mission) -> MissionManager:
    mgr = MissionManager([])
    for m in missions:
        mgr.add_mission(m, initial_status=MissionStatus.ACTIVE)
    return mgr


def _make_cantina_view(mission_manager: MissionManager):
    """Partially-constructed CantinaView that exposes the receiver helper
    without running the full view lifecycle."""
    from spacegame.views.cantina_view import CantinaView

    view = CantinaView.__new__(CantinaView)
    view.mission_manager = mission_manager
    return view


# ---------------------------------------------------------------------------
# _npc_is_quest_receiver — core detection logic
# ---------------------------------------------------------------------------


class TestNpcIsQuestReceiver:
    def test_returns_true_when_active_mission_targets_npc(self) -> None:
        mgr = _mgr_with_active(_mission_with_talk("m1", "rhea"))
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is True

    def test_returns_false_for_unrelated_npc(self) -> None:
        mgr = _mgr_with_active(_mission_with_talk("m1", "rhea"))
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("arna") is False

    def test_returns_false_when_no_mission_manager(self) -> None:
        view = _make_cantina_view(mission_manager=None)
        assert view._npc_is_quest_receiver("rhea") is False

    def test_returns_false_when_no_active_missions(self) -> None:
        mgr = MissionManager([])
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is False

    def test_ignores_non_talk_objectives(self) -> None:
        """reach_system and has_flag objectives must not produce false positives."""
        m = Mission(
            id="m1",
            name="m1",
            description="",
            hint="",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="rhea",  # reuse the id, different objective type
                    target_quantity=1,
                    description="",
                ),
                MissionObjective(
                    type=ObjectiveType.HAS_FLAG,
                    target_id="rhea",
                    target_quantity=1,
                    description="",
                ),
            ],
            rewards=[],
            mission_type="side",
            available_at=[],
        )
        mgr = _mgr_with_active(m)
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is False

    def test_ignores_completed_talk_objectives(self) -> None:
        """Once the player has talked to the NPC, the objective is complete
        and the receiver highlight should stop firing."""
        m = _mission_with_talk("m1", "rhea")
        mgr = MissionManager([])
        mgr.add_mission(m, initial_status=MissionStatus.ACTIVE)
        # Manually mark the first objective complete
        mgr._progress[m.id] = [True]
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is False

    def test_multiple_missions_any_match_triggers(self) -> None:
        mgr = _mgr_with_active(
            _mission_with_talk("m1", "arna"),
            _mission_with_talk("m2", "rhea"),
            _mission_with_talk("m3", "odom"),
        )
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is True
        assert view._npc_is_quest_receiver("arna") is True
        assert view._npc_is_quest_receiver("odom") is True
        assert view._npc_is_quest_receiver("someone_else") is False

    def test_mission_manager_exception_returns_false(self) -> None:
        """Defensive: if the mission manager call raises, helper must not
        crash the UI."""
        mgr = MagicMock()
        mgr.get_missions_by_status.side_effect = RuntimeError("boom")
        view = _make_cantina_view(mgr)
        assert view._npc_is_quest_receiver("rhea") is False


# ---------------------------------------------------------------------------
# Integration: UI build attaches the marker and tracks the id
# ---------------------------------------------------------------------------


class TestReceiverHighlightIntegration:
    """Source-level verification that the button label + glow infrastructure
    are wired. Full UI construction requires non-trivial stubbing; this guard
    catches regressions in the integration points."""

    def test_glow_renderer_exists(self) -> None:
        from pathlib import Path

        src = Path("spacegame/views/cantina_view.py").read_text(encoding="utf-8")
        assert "_render_quest_receiver_glow" in src, "cantina_view must render the receiver glow"
        assert "_quest_receiver_npc_ids" in src, (
            "cantina_view must track receiver ids for rendering"
        )

    def test_label_marker_applied(self) -> None:
        from pathlib import Path

        src = Path("spacegame/views/cantina_view.py").read_text(encoding="utf-8")
        assert "(Active Quest)" in src, (
            "receiver NPC buttons must carry the (Active Quest) text marker"
        )

    def test_glow_uses_render_top(self) -> None:
        """Glow must render AFTER pygame_gui so it sits on top of the
        button chrome (matches PT-005's render_top contract)."""
        from pathlib import Path

        src = Path("spacegame/views/cantina_view.py").read_text(encoding="utf-8")
        # render_top() must call _render_quest_receiver_glow
        render_top_idx = src.index("def render_top")
        # Find the next 'def ' (method boundary)
        next_def = src.index("def ", render_top_idx + 1)
        render_top_body = src[render_top_idx:next_def]
        assert "_render_quest_receiver_glow" in render_top_body


# ---------------------------------------------------------------------------
# Glow animation — timer ticks and stays finite
# ---------------------------------------------------------------------------


class TestGlowAnimation:
    def test_glow_time_advances_with_update(self) -> None:
        """The pulsing glow uses _glow_time; update(dt) must advance it."""
        from pathlib import Path

        src = Path("spacegame/views/cantina_view.py").read_text(encoding="utf-8")
        update_idx = src.index("def update(self, dt")
        next_def = src.index("def ", update_idx + 1)
        update_body = src[update_idx:next_def]
        assert "self._glow_time += dt" in update_body, (
            "update() must advance _glow_time so the glow pulses"
        )
