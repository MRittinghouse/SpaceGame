"""SL-5 scenario: faction-first-dock orientation tip.

A one-time orientation tip fires when the player first docks at each
faction's territory. Five tips total, one per layout key
(guild / union / collective / frontier / reach). Per-faction state
tracked via the ``seen_faction_tip_<layout_key>`` dialogue flag.

Suppression: the tip is suppressed if a mission-objective highlight is
already drawing the player's eye on this dock — defer to the next dock
at this faction so two pieces of new information don't stack.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.constants.flags import seen_faction_tip
from spacegame.data_loader import get_data_loader
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.views.station_hub_view import StationHubView
from tests.test_scenarios._helpers import fresh_player


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """station_hub_view requires pygame fonts and a UIManager."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()


def _make_hub_view(player, system_id: str, mission_manager=None) -> StationHubView:
    dl = get_data_loader()
    dl.load_all()
    ui_mgr = pygame_gui.UIManager((1280, 800))
    return StationHubView(
        ui_manager=ui_mgr,
        player=player,
        system=dl.systems[system_id],
        locations=list(dl.locations.get(system_id, [])),
        activity_registry=None,
        data_loader=dl,
        mission_manager=mission_manager,
    )


# Each system + the layout key its station should map to.
# SYSTEM_LAYOUT_MAP in spacegame/views/station_layouts.py.
_SYSTEM_LAYOUT_PAIRS: list[tuple[str, str]] = [
    ("nexus_prime", "guild"),
    ("breakstone", "union"),
    ("axiom_labs", "collective"),
    ("havens_rest", "frontier"),
    ("crimson_reach", "reach"),
]


class TestFactionTipFiresOnFirstDock:
    """Each faction's tip fires on the player's first dock there."""

    @pytest.mark.parametrize("system_id, layout_key", _SYSTEM_LAYOUT_PAIRS)
    def test_tip_fires_for_each_faction(self, system_id: str, layout_key: str) -> None:
        player = fresh_player()
        view = _make_hub_view(player, system_id)
        view.on_enter()
        assert view._faction_tip is not None, (
            f"Tip should fire on first dock at {layout_key} ({system_id})"
        )

    @pytest.mark.parametrize("system_id, layout_key", _SYSTEM_LAYOUT_PAIRS)
    def test_tip_uses_correct_faction_title(self, system_id: str, layout_key: str) -> None:
        """The tip title names the faction whose territory the player is in."""
        player = fresh_player()
        view = _make_hub_view(player, system_id)
        view.on_enter()
        # Title and body live on the FirstTimeTipOverlay instance.
        from spacegame.views.station_hub_view import _FACTION_TIPS

        expected_title, expected_body = _FACTION_TIPS[layout_key]
        assert view._faction_tip is not None
        assert view._faction_tip.title == expected_title
        assert view._faction_tip.body == expected_body


class TestFactionTipDoesNotRefire:
    """Once dismissed, the tip never fires again at the same faction."""

    def test_already_seen_flag_suppresses_tip(self) -> None:
        player = fresh_player()
        player.dialogue_flags[seen_faction_tip("guild")] = True
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        assert view._faction_tip is None

    def test_dismiss_callback_sets_the_flag(self) -> None:
        """Dismissing the tip persists the seen-state via the flag registry helper."""
        player = fresh_player()
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        assert view._faction_tip is not None
        flag = seen_faction_tip("guild")
        assert player.dialogue_flags.get(flag, False) is False
        # Simulate dismissal.
        view._faction_tip._dismiss()
        assert player.dialogue_flags.get(flag, False) is True


class TestFactionTipPerFactionScoping:
    """Seeing one faction's tip does not silence another faction's tip."""

    def test_seeing_guild_tip_still_fires_union_tip(self) -> None:
        player = fresh_player()
        player.dialogue_flags[seen_faction_tip("guild")] = True
        # Different faction. Tip should still fire.
        view = _make_hub_view(player, "breakstone")
        view.on_enter()
        assert view._faction_tip is not None
        from spacegame.views.station_hub_view import _FACTION_TIPS

        union_title, _ = _FACTION_TIPS["union"]
        assert view._faction_tip.title == union_title


class TestFactionTipSuppressedByMissionObjective:
    """Suppression rule: don't stack the tip on top of a MISSION_OBJECTIVE glow."""

    def test_active_talk_to_npc_objective_suppresses_tip(self) -> None:
        """When a mission-objective highlight is active, defer the tip."""
        # Build a mission whose TALK_TO_NPC target lives at Nexus Prime
        # so get_recommended_card returns a MISSION_OBJECTIVE source.
        dl = get_data_loader()
        dl.load_all()
        # Pick any NPC whose home_system_id is nexus_prime.
        nexus_npc_id = next(
            (npc_id for npc_id, npc in dl.npcs.items() if npc.home_system_id == "nexus_prime"),
            None,
        )
        if nexus_npc_id is None:
            pytest.skip("No NPC home-system'd at nexus_prime in current data")

        m = Mission(
            id="sl5_test_mission",
            name="Test Talk",
            description="",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.TALK_TO_NPC,
                    target_id=nexus_npc_id,
                    description="Talk",
                )
            ],
        )
        mgr = MissionManager([m])
        mgr._status["sl5_test_mission"] = MissionStatus.ACTIVE

        player = fresh_player()
        view = _make_hub_view(player, "nexus_prime", mission_manager=mgr)
        view.on_enter()

        # Tip should be suppressed; the seen flag should NOT be set
        # (player still hasn't seen the tip; it'll fire on next dock).
        assert view._faction_tip is None
        assert player.dialogue_flags.get(seen_faction_tip("guild"), False) is False

    def test_no_mission_does_not_suppress_tip(self) -> None:
        """Sanity: without a mission, the tip fires normally."""
        player = fresh_player()
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        assert view._faction_tip is not None


class TestSeenFactionTipFlagHelper:
    """The flag-registry helper produces stable, parametrized names."""

    def test_returns_layout_keyed_string(self) -> None:
        assert seen_faction_tip("guild") == "seen_faction_tip_guild"
        assert seen_faction_tip("union") == "seen_faction_tip_union"
        assert seen_faction_tip("collective") == "seen_faction_tip_collective"
        assert seen_faction_tip("frontier") == "seen_faction_tip_frontier"
        assert seen_faction_tip("reach") == "seen_faction_tip_reach"
