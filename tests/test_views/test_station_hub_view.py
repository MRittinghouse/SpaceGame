"""Tests for StationHubView — station location selection screen."""

import pygame
import pygame_gui
from spacegame.config import GameState, WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.data_loader import DataLoader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.location import Location
from spacegame.views.station_hub_view import StationHubView
from spacegame.engine.activity_registry import create_default_registry


def _make_test_env(
    system_id: str = "nexus_prime",
) -> tuple[pygame_gui.UIManager, Player, DataLoader]:
    """Create test environment with player at given system."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    loader = DataLoader()
    loader.load_all()

    ship_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    ship.current_hull = ship_type.combat_hull
    player = Player("Test Captain", 5000, system_id, ship)
    return manager, player, loader


class TestStationHubConstruction:
    """Tests for StationHubView creation."""

    def test_create_station_hub_view(self) -> None:
        manager, player, loader = _make_test_env()
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        registry = create_default_registry()
        view = StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )
        assert view is not None
        assert view.next_state is None

    def test_stores_system_reference(self) -> None:
        manager, player, loader = _make_test_env()
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        registry = create_default_registry()
        view = StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )
        assert view.system.id == "nexus_prime"

    def test_stores_locations(self) -> None:
        manager, player, loader = _make_test_env()
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        registry = create_default_registry()
        view = StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )
        assert len(view.locations) > 0


class TestStationHubLifecycle:
    """Tests for on_enter/on_exit lifecycle."""

    def _make_view(self, system_id: str = "nexus_prime") -> StationHubView:
        manager, player, loader = _make_test_env(system_id)
        system = loader.get_system(system_id)
        locations = loader.get_locations_for_system(system_id)
        registry = create_default_registry()
        return StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )

    def test_on_enter_sets_active(self) -> None:
        view = self._make_view()
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_clears_active(self) -> None:
        view = self._make_view()
        view.on_enter()
        view.on_exit()
        assert not view.active

    def test_get_next_state_returns_none_initially(self) -> None:
        view = self._make_view()
        assert view.get_next_state() is None

    def test_shields_restored_on_enter(self) -> None:
        """Docking at station should restore shields."""
        manager, player, loader = _make_test_env()
        player.ship.current_shields = 0
        system = loader.get_system("nexus_prime")
        locations = loader.get_locations_for_system("nexus_prime")
        registry = create_default_registry()
        view = StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )
        view.on_enter()
        assert player.ship.current_shields == player.ship.ship_type.combat_shields
        view.on_exit()


class TestStationHubLocationCards:
    """Tests for location card rendering and data."""

    def _make_view(self, system_id: str = "nexus_prime") -> StationHubView:
        manager, player, loader = _make_test_env(system_id)
        system = loader.get_system(system_id)
        locations = loader.get_locations_for_system(system_id)
        registry = create_default_registry()
        return StationHubView(
            ui_manager=manager,
            player=player,
            system=system,
            locations=locations,
            activity_registry=registry,
            data_loader=loader,
        )

    def test_nexus_prime_has_market_card(self) -> None:
        view = self._make_view("nexus_prime")
        types = [loc.location_type for loc in view.locations]
        assert "market" in types

    def test_nexus_prime_has_unique_location(self) -> None:
        view = self._make_view("nexus_prime")
        types = [loc.location_type for loc in view.locations]
        assert "unique" in types

    def test_breakstone_has_mining_card(self) -> None:
        view = self._make_view("breakstone")
        types = [loc.location_type for loc in view.locations]
        assert "mining" in types

    def test_forgeworks_has_salvage_and_refine(self) -> None:
        view = self._make_view("forgeworks")
        types = [loc.location_type for loc in view.locations]
        assert "salvaging" in types
        assert "refining" in types

    def test_crimson_reach_has_salvage(self) -> None:
        view = self._make_view("crimson_reach")
        types = [loc.location_type for loc in view.locations]
        assert "salvaging" in types


class TestStationHubNavigation:
    """Tests for navigation state transitions."""

    def _make_view_entered(self, system_id: str = "nexus_prime") -> StationHubView:
        manager, player, loader = _make_test_env(system_id)
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
        )
        view.on_enter()
        return view

    def test_back_returns_galaxy_map(self) -> None:
        view = self._make_view_entered()
        view._request_back()
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_select_market_goes_to_trading(self) -> None:
        view = self._make_view_entered()
        view._select_location_type("market")
        assert view.get_next_state() == GameState.TRADING
        view.on_exit()

    def test_select_repair_bay_goes_to_repair(self) -> None:
        view = self._make_view_entered()
        view._select_location_type("repair_bay")
        assert view.get_next_state() == GameState.REPAIR_BAY
        view.on_exit()

    def test_select_mining_goes_to_mining(self) -> None:
        view = self._make_view_entered("breakstone")
        view._select_location_type("mining")
        assert view.get_next_state() == GameState.MINING
        view.on_exit()

    def test_select_salvaging_goes_to_salvaging(self) -> None:
        view = self._make_view_entered("crimson_reach")
        view._select_location_type("salvaging")
        assert view.get_next_state() == GameState.SALVAGING
        view.on_exit()

    def test_select_refining_goes_to_refining(self) -> None:
        view = self._make_view_entered("forgeworks")
        view._select_location_type("refining")
        assert view.get_next_state() == GameState.REFINING
        view.on_exit()

    def test_select_shipyard_goes_to_shipyard(self) -> None:
        view = self._make_view_entered()
        view._select_location_type("shipyard")
        assert view.get_next_state() == GameState.SHIPYARD
        view.on_exit()

    def test_select_cantina_goes_to_cantina(self) -> None:
        """Cantina transitions to dedicated cantina view."""
        view = self._make_view_entered()
        view._select_location_type("cantina")
        assert view.get_next_state() == GameState.CANTINA
        view.on_exit()

    def test_select_unique_does_not_transition(self) -> None:
        """Unique locations show lore panel, no state change."""
        view = self._make_view_entered()
        view._select_location_type("unique")
        assert view.get_next_state() is None
        view.on_exit()


class TestStationHubCantina:
    """Tests for cantina transition to dedicated view."""

    def _make_view_entered(self, system_id: str = "nexus_prime") -> StationHubView:
        manager, player, loader = _make_test_env(system_id)
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
        )
        view.on_enter()
        return view

    def test_cantina_transitions_to_cantina_state(self) -> None:
        """Selecting cantina triggers transition to CANTINA state."""
        view = self._make_view_entered()
        view._select_location_type("cantina")
        assert view.get_next_state() == GameState.CANTINA
        view.on_exit()

    def test_nexus_prime_has_npcs_in_cantina(self) -> None:
        """Nexus Prime should have NPCs available (via station hub legacy helper)."""
        view = self._make_view_entered("nexus_prime")
        npcs = view._get_cantina_npcs()
        assert len(npcs) > 0
        view.on_exit()

    def test_select_npc_sets_pending_and_transitions(self) -> None:
        view = self._make_view_entered("nexus_prime")
        npcs = view._get_cantina_npcs()
        if npcs:
            view._select_npc(npcs[0].id)
            assert view.pending_npc_id == npcs[0].id
            assert view.get_next_state() == GameState.DIALOGUE
        view.on_exit()
