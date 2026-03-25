"""Tests for crew hire UI in station hub cantina.

Verifies that hireable crew appear at their home system, hiring works,
slots are enforced, and dismissed/recruited crew are excluded from the hire list.
"""

import pygame
import pygame_gui

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.data_loader import DataLoader
from spacegame.models.crew import CrewRoster, CrewTemplate, CrewAbility
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.station_hub_view import StationHubView
from spacegame.engine.activity_registry import create_default_registry


def _make_test_env(
    system_id: str = "nexus_prime",
    credits: int = 5000,
) -> tuple[pygame_gui.UIManager, Player, DataLoader, CrewRoster]:
    """Create test environment with player, data loader, and crew roster."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    loader = DataLoader()
    loader.load_all()

    ship_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    ship.current_hull = ship_type.combat_hull
    player = Player("Test Captain", credits, system_id, ship)
    crew_roster = CrewRoster(loader.crew_templates)
    return manager, player, loader, crew_roster


def _make_view(
    system_id: str = "nexus_prime",
    credits: int = 5000,
) -> tuple[StationHubView, Player, CrewRoster]:
    """Create a StationHubView with crew_roster wired in."""
    manager, player, loader, crew_roster = _make_test_env(system_id, credits)
    system = loader.get_system(system_id)
    locations = loader.get_locations_for_system(system_id)
    registry = create_default_registry()
    view = StationHubView(
        ui_manager=manager,
        player=player,
        system=system,
        locations=locations,
        activity_registry=registry,
        data_loader=loader,
        crew_roster=crew_roster,
    )
    return view, player, crew_roster


class TestCrewHireAvailability:
    """Tests for available crew appearing at correct systems."""

    def test_available_crew_appear_at_home_system(self) -> None:
        """Non-companion crew with home_system_id=nexus_prime should be available there."""
        view, player, crew_roster = _make_view("nexus_prime")
        available = crew_roster.get_available_crew_at_system("nexus_prime")
        # nexus_prime has kai_torren (cargo handler) and sol_maren (document forger)
        assert len(available) >= 1, "Nexus Prime should have hireable crew"
        ids = [t.id for t in available]
        assert "kai_torren" in ids, "Kai Torren should be available at nexus_prime"

    def test_available_crew_not_at_wrong_system(self) -> None:
        """Crew at nexus_prime should not appear at breakstone."""
        view, player, crew_roster = _make_view("breakstone")
        available = crew_roster.get_available_crew_at_system("breakstone")
        ids = [t.id for t in available]
        assert "kai_torren" not in ids, "Kai Torren should not be at breakstone"

    def test_companions_not_in_hire_list(self) -> None:
        """Companions (is_companion=true) should not appear in available crew."""
        view, player, crew_roster = _make_view("stellaris_port")
        available = crew_roster.get_available_crew_at_system("stellaris_port")
        ids = [t.id for t in available]
        assert "elena_reeves" not in ids, "Companion Elena Reeves should not be hireable"

    def test_already_recruited_not_in_hire_list(self) -> None:
        """Crew already recruited should not appear in available list."""
        view, player, crew_roster = _make_view("nexus_prime")
        crew_slots = player.ship.ship_type.crew_slots
        crew_roster.recruit("kai_torren", crew_slots)
        available = crew_roster.get_available_crew_at_system("nexus_prime")
        ids = [t.id for t in available]
        assert "kai_torren" not in ids, "Recruited crew should not appear as available"

    def test_dismissed_crew_not_in_hire_list(self) -> None:
        """Dismissed crew should appear in re-recruit section, not hire section."""
        view, player, crew_roster = _make_view("nexus_prime")
        crew_slots = player.ship.ship_type.crew_slots
        crew_roster.recruit("kai_torren", crew_slots)
        crew_roster.dismiss("kai_torren")
        available = crew_roster.get_available_crew_at_system("nexus_prime")
        ids = [t.id for t in available]
        assert "kai_torren" not in ids, "Dismissed crew should not appear in hire list"
        # But they should be in dismissed list
        dismissed = crew_roster.get_dismissed_at_system("nexus_prime")
        dismissed_ids = [t.id for t, _s in dismissed]
        assert "kai_torren" in dismissed_ids, "Dismissed crew should be in re-recruit list"

    def test_breakstone_has_available_crew(self) -> None:
        """Breakstone should have crew members (bram_kovac at least)."""
        view, player, crew_roster = _make_view("breakstone")
        available = crew_roster.get_available_crew_at_system("breakstone")
        assert len(available) >= 1, "Breakstone should have hireable crew"
        ids = [t.id for t in available]
        assert "bram_okeke" in ids, "Bram Okeke should be available at breakstone"


class TestCrewHireAction:
    """Tests for the hire button action in station hub."""

    def test_hire_succeeds_with_available_slots(self) -> None:
        """Hiring a crew member should succeed when slots are available."""
        view, player, crew_roster = _make_view("nexus_prime")

        crew_slots = player.ship.ship_type.crew_slots + int(
            player.progression.get_bonus("crew_slot_bonus")
        )
        success, msg = crew_roster.recruit("kai_torren", crew_slots)
        assert success, f"Hire should succeed: {msg}"
        assert crew_roster.is_recruited("kai_torren")

    def test_hire_fails_when_no_slots(self) -> None:
        """Hiring should fail when all crew slots are full."""
        view, player, crew_roster = _make_view("nexus_prime")
        # Fill all crew slots
        crew_slots = player.ship.ship_type.crew_slots + int(
            player.progression.get_bonus("crew_slot_bonus")
        )
        # Recruit enough crew to fill slots
        all_templates = list(crew_roster._templates.keys())
        non_companion = [
            tid for tid in all_templates if not crew_roster._templates[tid].is_companion
        ]
        for i in range(crew_slots):
            if i < len(non_companion):
                crew_roster.recruit(non_companion[i], crew_slots)

        # Now try to hire another
        remaining = [tid for tid in non_companion if not crew_roster.is_recruited(tid)]
        if remaining:
            success, msg = crew_roster.recruit(remaining[0], crew_slots)
            assert not success, "Hire should fail when slots full"
            assert "No crew slots" in msg

        view.on_exit() if view.active else None

    def test_hire_is_free(self) -> None:
        """First-time crew hire should cost zero credits."""
        view, player, crew_roster = _make_view("nexus_prime", credits=0)
        # get_recruit_cost returns 0 for non-dismissed crew
        cost = crew_roster.get_recruit_cost("kai_torren")
        assert cost == 0, "First-time hire should be free"

    def test_handle_hire_recruits_and_refreshes(self) -> None:
        """_handle_hire should recruit crew and refresh cantina buttons."""
        from spacegame.views.cantina_view import CantinaView

        manager, player, loader, crew_roster = _make_test_env("nexus_prime")
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        cantina_loc = next(loc for loc in locations if loc.location_type == "cantina")
        cantina = CantinaView(
            ui_manager=manager,
            player=player,
            system=system,
            location=cantina_loc,
            data_loader=loader,
            crew_roster=crew_roster,
        )
        cantina.on_enter()

        # Verify hire buttons were created
        assert len(cantina._hire_buttons) > 0, "Should have hire buttons at nexus_prime"
        assert "kai_torren" in cantina._hire_buttons, "Should have hire button for kai_torren"

        # Trigger hire
        cantina._handle_hire("kai_torren")
        assert crew_roster.is_recruited("kai_torren"), "Kai should be recruited after hire"

        # After hire, buttons should be refreshed and kai_torren removed
        assert "kai_torren" not in cantina._hire_buttons, (
            "Hired crew should be removed from buttons"
        )
        cantina.on_exit()

    def test_hire_buttons_disabled_when_slots_full(self) -> None:
        """Hire buttons should be disabled when no crew slots available."""
        from spacegame.views.cantina_view import CantinaView

        manager, player, loader, crew_roster = _make_test_env("nexus_prime")

        # Fill all slots
        crew_slots = player.ship.ship_type.crew_slots + int(
            player.progression.get_bonus("crew_slot_bonus")
        )
        non_companion = [tid for tid, t in crew_roster._templates.items() if not t.is_companion]
        for i in range(min(crew_slots, len(non_companion))):
            crew_roster.recruit(non_companion[i], crew_slots)

        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        cantina_loc = next(loc for loc in locations if loc.location_type == "cantina")
        cantina = CantinaView(
            ui_manager=manager,
            player=player,
            system=system,
            location=cantina_loc,
            data_loader=loader,
            crew_roster=crew_roster,
        )
        cantina.on_enter()

        # Any remaining hire buttons should be disabled
        for btn in cantina._hire_buttons.values():
            assert not btn.is_enabled, "Hire buttons should be disabled when slots full"
        cantina.on_exit()

    def test_pending_hire_id_set_on_hire(self) -> None:
        """Hiring should set pending_hire_id for game.py notification."""
        from spacegame.views.cantina_view import CantinaView

        manager, player, loader, crew_roster = _make_test_env("nexus_prime")
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        cantina_loc = next(loc for loc in locations if loc.location_type == "cantina")
        cantina = CantinaView(
            ui_manager=manager,
            player=player,
            system=system,
            location=cantina_loc,
            data_loader=loader,
            crew_roster=crew_roster,
        )
        cantina.on_enter()
        cantina._handle_hire("kai_torren")
        assert cantina.pending_hire_id == "kai_torren", "pending_hire_id should be set after hire"
        cantina.on_exit()
