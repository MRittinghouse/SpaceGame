"""Tests for the persistent cockpit HUD overlay."""

import pygame
import pytest
from unittest.mock import MagicMock, PropertyMock

from spacegame.config import GameState
from spacegame.views.cockpit_hud import CockpitHUD, HUD_VISIBLE_STATES, HUD_BASE_HEIGHT


@pytest.fixture(autouse=True)
def _init_pygame():
    """Ensure pygame is initialized for font creation."""
    pygame.init()
    yield
    pygame.quit()


def _make_player() -> MagicMock:
    """Create a mock player with ship and progression."""
    player = MagicMock()
    player.credits = 5000
    player.ship.current_hull = 80
    player.ship.ship_type.combat_hull = 100
    player.ship.current_shields = 50
    player.ship.ship_type.combat_shields = 50
    player.ship.current_fuel = 30
    player.ship.max_fuel = 50
    player.ship.current_cargo = {"food": 10, "textiles": 5}
    player.ship.cargo_capacity = 100
    player.progression.skill_points = 0
    return player


def _make_mission_manager() -> MagicMock:
    """Create a mock mission manager."""
    mm = MagicMock()
    mm.get_missions_by_status.return_value = []
    mm.get_objective_progress.return_value = []
    return mm


def _make_hud(**overrides) -> CockpitHUD:
    """Create a CockpitHUD with mock dependencies."""
    player = overrides.get("player", _make_player())
    mm = overrides.get("mission_manager", _make_mission_manager())
    crew = overrides.get("crew_roster", None)
    return CockpitHUD(player=player, mission_manager=mm, crew_roster=crew)


class TestHUDVisibility:
    """Tests for HUD visibility based on game state."""

    def test_hidden_by_default(self) -> None:
        """HUD starts hidden until a state update."""
        hud = _make_hud()
        assert not hud.visible

    def test_visible_on_galaxy_map(self) -> None:
        """HUD should be visible on the galaxy map."""
        hud = _make_hud()
        hud.update(0.016, GameState.GALAXY_MAP)
        assert hud.visible

    def test_visible_on_station_hub(self) -> None:
        """HUD should be visible on the station hub."""
        hud = _make_hud()
        hud.update(0.016, GameState.STATION_HUB)
        assert hud.visible

    def test_visible_on_trading(self) -> None:
        """HUD should be visible during trading."""
        hud = _make_hud()
        hud.update(0.016, GameState.TRADING)
        assert hud.visible

    def test_hidden_during_combat(self) -> None:
        """HUD should be hidden during combat."""
        hud = _make_hud()
        hud.update(0.016, GameState.COMBAT)
        assert not hud.visible

    def test_hidden_during_mining(self) -> None:
        """HUD should be hidden during mining mini-game."""
        hud = _make_hud()
        hud.update(0.016, GameState.MINING)
        assert not hud.visible

    def test_hidden_during_dialogue(self) -> None:
        """HUD should be hidden during NPC dialogue."""
        hud = _make_hud()
        hud.update(0.016, GameState.DIALOGUE)
        assert not hud.visible

    def test_all_hub_states_visible(self) -> None:
        """All states in HUD_VISIBLE_STATES should show the HUD."""
        for state in HUD_VISIBLE_STATES:
            hud = _make_hud()
            hud.update(0.016, state)
            assert hud.visible, f"HUD should be visible on {state.value}"


class TestHUDNotificationBadges:
    """Tests for notification badge logic."""

    def test_skills_badge_when_points_available(self) -> None:
        """Skills button should show badge when skill points are unspent."""
        player = _make_player()
        player.progression.skill_points = 3
        hud = _make_hud(player=player)
        # Button index 1 = Skills
        assert hud._check_badge(1)

    def test_no_skills_badge_when_spent(self) -> None:
        """Skills button should NOT show badge when all points spent."""
        player = _make_player()
        player.progression.skill_points = 0
        hud = _make_hud(player=player)
        assert not hud._check_badge(1)

    def test_missions_badge_when_available(self) -> None:
        """Missions button should show badge when missions are available."""
        mm = _make_mission_manager()
        mm.get_missions_by_status.return_value = [MagicMock()]  # 1 available mission
        hud = _make_hud(mission_manager=mm)
        # Button index 3 = Missions
        assert hud._check_badge(3)

    def test_no_missions_badge_when_none_available(self) -> None:
        """Missions button should NOT show badge when no missions available."""
        hud = _make_hud()
        assert not hud._check_badge(3)

    def test_crew_badge_when_pending_companions(self) -> None:
        """Crew button should show badge when companions are pending."""
        crew = MagicMock()
        crew.pending_companion_ids = {"elena_reeves"}
        hud = _make_hud(crew_roster=crew)
        # Button index 2 = Crew
        assert hud._check_badge(2)

    def test_no_crew_badge_when_no_pending(self) -> None:
        """Crew button should NOT show badge when no pending companions."""
        crew = MagicMock()
        crew.pending_companion_ids = set()
        hud = _make_hud(crew_roster=crew)
        assert not hud._check_badge(2)


class TestHUDQuestHint:
    """Tests for quest hint display."""

    def test_empty_hint_when_no_active_missions(self) -> None:
        """Quest hint should be empty when no missions are active."""
        hud = _make_hud()
        assert hud._get_quest_hint() == ""

    def test_hint_shows_first_incomplete_objective(self) -> None:
        """Quest hint should show the first incomplete objective."""
        mission = MagicMock()
        mission.id = "test_mission"
        mission.hint = "Go to Nexus Prime"
        mission.objectives = [
            MagicMock(description="Talk to the NPC"),
            MagicMock(description="Deliver the cargo"),
        ]
        mm = _make_mission_manager()
        mm.get_missions_by_status.return_value = [mission]
        mm.get_objective_progress.return_value = [True, False]

        hud = _make_hud(mission_manager=mm)
        hint = hud._get_quest_hint()
        assert "Deliver the cargo" in hint

    def test_hint_falls_back_to_mission_hint(self) -> None:
        """Quest hint falls back to mission.hint if no objectives have progress."""
        mission = MagicMock()
        mission.id = "test_mission"
        mission.hint = "Go to Nexus Prime"
        mission.objectives = []
        mm = _make_mission_manager()
        mm.get_missions_by_status.return_value = [mission]
        mm.get_objective_progress.return_value = []

        hud = _make_hud(mission_manager=mm)
        hint = hud._get_quest_hint()
        assert "Nexus Prime" in hint


class TestHUDLayout:
    """Tests for HUD layout geometry."""

    def test_hud_height_positive(self) -> None:
        """HUD should have a positive height."""
        hud = _make_hud()
        assert hud.height > 0

    def test_hud_at_bottom_of_screen(self) -> None:
        """HUD should be positioned at the bottom of the screen."""
        from spacegame.config import WINDOW_HEIGHT
        hud = _make_hud()
        assert hud.y == WINDOW_HEIGHT - hud.height

    def test_buttons_within_screen_bounds(self) -> None:
        """All button rects should be within screen bounds."""
        from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT
        hud = _make_hud()
        for i, rect in enumerate(hud._button_rects):
            assert rect.left >= 0, f"Button {i} left edge off-screen"
            assert rect.right <= WINDOW_WIDTH, f"Button {i} right edge off-screen"
            assert rect.top >= hud.y, f"Button {i} above HUD"
            assert rect.bottom <= WINDOW_HEIGHT, f"Button {i} below screen"

    def test_five_navigation_buttons(self) -> None:
        """HUD should have exactly 5 navigation buttons."""
        hud = _make_hud()
        assert len(hud._button_rects) == 5
