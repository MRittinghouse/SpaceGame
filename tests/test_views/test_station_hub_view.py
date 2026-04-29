"""Tests for StationHubView — station location selection screen."""

import json
import sys
import types

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import DataLoader
from spacegame.engine.activity_registry import create_default_registry
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.station_hub_view import StationHubView


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


def _reset_telemetry_state(tel: object) -> None:
    """Reset module-level session state between tests."""
    tel._session_id = None  # type: ignore[attr-defined]
    tel._session_path = None  # type: ignore[attr-defined]


def _setup_telemetry(monkeypatch: object, tmp_path: object) -> object:
    """Enable telemetry pointing to tmp_path and return the fresh module."""
    monkeypatch.setenv("SPACEGAME_TELEMETRY", "1")
    monkeypatch.setenv("SPACEGAME_TELEMETRY_DIR", str(tmp_path))
    # Reload to pick up new env vars and clear any stale session state
    for key in list(sys.modules.keys()):
        if "spacegame.utils.telemetry" in key:
            del sys.modules[key]
    import spacegame.utils.telemetry as tel

    _reset_telemetry_state(tel)
    return tel


def _make_fake_zone(
    location_type: str, location_id: str, system_id: str = "crimson_reach"
) -> object:
    """Build a minimal fake StationZone for testing _activate_zone."""
    loc = types.SimpleNamespace(
        location_type=location_type,
        id=location_id,
        name="Test Location",
    )
    return types.SimpleNamespace(location=loc, rect=pygame.Rect(0, 0, 100, 50))


class TestStationHubTelemetryHooks:
    """Telemetry events emitted by StationHubView click + dwell hooks."""

    def _make_view_entered(self, system_id: str = "crimson_reach") -> StationHubView:
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

    def _read_events(self, tmp_path: object) -> list[dict]:
        """Parse all JSONL events from any .jsonl file under tmp_path."""
        events = []
        for f in tmp_path.rglob("*.jsonl"):  # type: ignore[union-attr]
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        return events

    # --- anchor_card_clicked ---

    def test_unique_card_click_emits_anchor_card_clicked(self, monkeypatch, tmp_path) -> None:
        """Clicking a unique card records anchor_card_clicked with required fields."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("unique", "crimson_wreckers_guild", "crimson_reach")
        view._activate_zone(zone)

        events = self._read_events(tmp_path)
        clicked = [e for e in events if e.get("event_type") == "anchor_card_clicked"]
        assert len(clicked) == 1, f"Expected 1 anchor_card_clicked, got {clicked}"
        assert clicked[0]["anchor_id"] == "crimson_wreckers_guild"
        assert "system_id" in clicked[0]
        assert "game_day" in clicked[0]
        view.on_exit()

    def test_non_unique_card_click_does_not_emit(self, monkeypatch, tmp_path) -> None:
        """Clicking a market card must NOT emit anchor_card_clicked."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("market", "crimson_market", "crimson_reach")
        view._activate_zone(zone)

        events = self._read_events(tmp_path)
        clicked = [e for e in events if e.get("event_type") == "anchor_card_clicked"]
        assert clicked == [], f"Unexpected anchor_card_clicked events: {clicked}"
        view.on_exit()

    def test_unique_card_click_disabled_telemetry_no_event(self, monkeypatch, tmp_path) -> None:
        """When telemetry is disabled, clicking a unique card writes nothing."""
        monkeypatch.delenv("SPACEGAME_TELEMETRY", raising=False)
        monkeypatch.setenv("SPACEGAME_TELEMETRY_DIR", str(tmp_path))
        for key in list(sys.modules.keys()):
            if "spacegame.utils.telemetry" in key:
                del sys.modules[key]
        import spacegame.utils.telemetry as tel

        _reset_telemetry_state(tel)

        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("unique", "crimson_wreckers_guild", "crimson_reach")
        view._activate_zone(zone)

        files = list(tmp_path.rglob("*.jsonl"))
        assert files == [], f"Telemetry wrote files when disabled: {files}"
        view.on_exit()

    # --- anchor_detail_dwell (close button path) ---

    def test_detail_dwell_emitted_on_close_button(self, monkeypatch, tmp_path) -> None:
        """Closing the detail panel via close button emits anchor_detail_dwell."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("unique", "crimson_wreckers_guild", "crimson_reach")
        view._activate_zone(zone)  # opens detail panel

        # Emit dwell by calling the helper that the close button handler uses
        view._emit_detail_dwell_if_open()

        events = self._read_events(tmp_path)
        dwell = [e for e in events if e.get("event_type") == "anchor_detail_dwell"]
        assert len(dwell) == 1, f"Expected 1 anchor_detail_dwell, got {dwell}"
        assert dwell[0]["anchor_id"] == "crimson_wreckers_guild"
        assert dwell[0]["duration_ms"] >= 0
        view.on_exit()

    # --- anchor_detail_dwell (view exit path) ---

    def test_detail_dwell_emitted_on_view_exit(self, monkeypatch, tmp_path) -> None:
        """Navigating away with detail open emits anchor_detail_dwell."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("unique", "crimson_wreckers_guild", "crimson_reach")
        view._activate_zone(zone)  # opens detail panel

        view.on_exit()  # should emit dwell before destroying UI

        events = self._read_events(tmp_path)
        dwell = [e for e in events if e.get("event_type") == "anchor_detail_dwell"]
        assert len(dwell) == 1, f"Expected 1 anchor_detail_dwell on exit, got {dwell}"
        assert dwell[0]["anchor_id"] == "crimson_wreckers_guild"

    # --- anchor_detail_dwell (replacement click path) ---

    def test_detail_dwell_emitted_on_replacement_click(self, monkeypatch, tmp_path) -> None:
        """Clicking a second unique card while first detail is open emits dwell for first."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("nexus_prime")
        zone_a = _make_fake_zone("unique", "nexus_financial_exchange", "nexus_prime")
        zone_b = _make_fake_zone("unique", "nexus_financial_exchange", "nexus_prime")
        zone_b.location.id = "stellaris_auction_house"

        view._activate_zone(zone_a)  # opens detail for first anchor

        # Click a second unique card — should emit dwell for the FIRST anchor
        view._activate_zone(zone_b)

        events = self._read_events(tmp_path)
        dwell = [e for e in events if e.get("event_type") == "anchor_detail_dwell"]
        assert len(dwell) == 1, f"Expected 1 dwell for first anchor, got {dwell}"
        assert dwell[0]["anchor_id"] == "nexus_financial_exchange", (
            f"Dwell should name the CLOSED anchor, got {dwell[0]['anchor_id']}"
        )
        view.on_exit()

    # --- dwell not emitted when no panel was open ---

    def test_no_dwell_emitted_when_panel_not_open(self, monkeypatch, tmp_path) -> None:
        """Calling _emit_detail_dwell_if_open with no open panel emits nothing."""
        _setup_telemetry(monkeypatch, tmp_path)
        view = self._make_view_entered("crimson_reach")
        view._emit_detail_dwell_if_open()  # no panel open

        events = self._read_events(tmp_path)
        dwell = [e for e in events if e.get("event_type") == "anchor_detail_dwell"]
        assert dwell == []
        view.on_exit()

    # --- dwell: disabled telemetry path ---

    def test_dwell_no_event_when_telemetry_disabled(self, monkeypatch, tmp_path) -> None:
        """With telemetry disabled, dwell events are not emitted from any path."""
        monkeypatch.delenv("SPACEGAME_TELEMETRY", raising=False)
        monkeypatch.setenv("SPACEGAME_TELEMETRY_DIR", str(tmp_path))
        for key in list(sys.modules.keys()):
            if "spacegame.utils.telemetry" in key:
                del sys.modules[key]
        import spacegame.utils.telemetry as tel

        _reset_telemetry_state(tel)

        view = self._make_view_entered("crimson_reach")
        zone = _make_fake_zone("unique", "crimson_wreckers_guild", "crimson_reach")
        view._activate_zone(zone)  # opens panel (click recorded... or not, since disabled)
        view._emit_detail_dwell_if_open()  # dwell path

        files = list(tmp_path.rglob("*.jsonl"))
        assert files == [], f"Telemetry wrote files when disabled: {files}"
        view.on_exit()


class TestStationHubWreckersEnterButton:
    """SA-1: Enter button on the Wreckers' Guild Hall detail panel.

    Acceptance #1: clicking the Hall card opens a detail panel that has
    BOTH a Close button and an Enter button. Clicking Enter sets
    ``next_state = GameState.WRECKERS_GUILD``. Other unique anchors keep
    their close-only layout — no regression.
    """

    def _make_view_entered(self, system_id: str = "crimson_reach") -> StationHubView:
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

    def _open_unique(self, view: StationHubView, location_id: str) -> None:
        """Open the detail panel for a real unique location at the current system."""
        loc = next(
            (loc for loc in view.locations if loc.id == location_id),
            None,
        )
        assert loc is not None, f"Fixture: {location_id} not in system locations"
        view._detail_location = loc

    def test_wreckers_card_renders_enter_button(self) -> None:
        view = self._make_view_entered("crimson_reach")
        self._open_unique(view, "crimson_wreckers_guild")
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        assert view._detail_close_button is not None
        assert view._detail_enter_button is not None
        view.on_exit()

    def test_other_unique_card_does_not_render_enter_button(self) -> None:
        # Nexus Prime: pick any non-Hall unique. crimson_reach has only the
        # Hall as a unique, so we exercise this with another system's anchors.
        view = self._make_view_entered("nexus_prime")
        non_hall_unique = next(
            (loc for loc in view.locations if loc.location_type == "unique"),
            None,
        )
        assert non_hall_unique is not None, "Fixture: nexus_prime should have unique anchors"
        view._detail_location = non_hall_unique
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        assert view._detail_close_button is not None
        assert view._detail_enter_button is None
        view.on_exit()

    def test_enter_button_sets_wreckers_guild_state(self) -> None:
        view = self._make_view_entered("crimson_reach")
        self._open_unique(view, "crimson_wreckers_guild")
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        enter_btn = view._detail_enter_button
        assert enter_btn is not None
        evt = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": enter_btn})
        view.handle_event(evt)
        assert view.next_state == GameState.WRECKERS_GUILD
        # Detail panel should also close on enter.
        assert view._detail_location is None
        view.on_exit()

    def test_close_button_after_enter_button_present_kills_both(self) -> None:
        view = self._make_view_entered("crimson_reach")
        self._open_unique(view, "crimson_wreckers_guild")
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        close_btn = view._detail_close_button
        assert close_btn is not None
        evt = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": close_btn})
        view.handle_event(evt)
        assert view._detail_close_button is None
        assert view._detail_enter_button is None
        view.on_exit()

    def test_switching_to_other_unique_card_kills_enter_button(self) -> None:
        # Open Hall detail (with Enter), then switch to another anchor.
        view = self._make_view_entered("crimson_reach")
        self._open_unique(view, "crimson_wreckers_guild")
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        assert view._detail_enter_button is not None
        # Now switch to a non-Hall location at this system.
        other = next(
            (loc for loc in view.locations if loc.id != "crimson_wreckers_guild"),
            None,
        )
        assert other is not None
        view._detail_location = other
        view.render(screen)
        assert view._detail_enter_button is None
        view.on_exit()
