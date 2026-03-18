"""Tests for galaxy map view: travel animation, ship icon, and encounter integration."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for GalaxyMapView tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.models.system import StarSystem, Coordinates, Station, Economy  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship, ShipType  # noqa: E402
from spacegame.models.encounter import EncounterRef  # noqa: E402
from spacegame.views.galaxy_map_view import GalaxyMapView  # noqa: E402


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player(**overrides) -> Player:
    defaults = {
        "name": "TestCaptain",
        "credits": 5000,
        "current_system_id": "nexus_prime",
        "ship": Ship(ship_type=_make_ship_type(), current_fuel=50),
    }
    defaults.update(overrides)
    return Player(**defaults)


def _make_system(
    sys_id: str = "nexus_prime",
    name: str = "Nexus Prime",
    x: float = 0.0,
    y: float = 0.0,
    danger: str = "safe",
) -> StarSystem:
    return StarSystem(
        id=sys_id,
        name=name,
        type="trade_hub",
        description="Test system",
        coordinates=Coordinates(x=x, y=y),
        danger_level=danger,
        faction="Independent",
        stations=[
            Station(
                id=f"{sys_id}_station",
                name=f"{name} Station",
                type="major",
                description="Test station",
                docking_fee=10,
                market_variety="full",
            )
        ],
        economy=Economy(
            production_tags=["food"],
            consumption_tags=["tech"],
            tariff_rate=0.05,
        ),
        rest_cost=50,
    )


def _make_systems() -> dict[str, StarSystem]:
    """Create a minimal 3-system galaxy for testing."""
    return {
        "nexus_prime": _make_system("nexus_prime", "Nexus Prime", 0, 0, "safe"),
        "breakstone": _make_system("breakstone", "Breakstone", 40, -80, "dangerous"),
        "forgeworks": _make_system("forgeworks", "Forgeworks", -70, 50, "moderate"),
    }


def _make_view(
    player: Player | None = None,
    systems: dict[str, StarSystem] | None = None,
) -> GalaxyMapView:
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    p = player or _make_player()
    s = systems or _make_systems()
    return GalaxyMapView(ui_manager, p, s)


# ============================================================================
# Travel Animation Tests
# ============================================================================


class TestTravelAnimation:
    """Tests for ship travel animation behavior."""

    def test_travel_animation_blocks_input(self) -> None:
        """Input events should be ignored during travel animation."""
        view = _make_view()
        view.on_enter()
        view._travel_animating = True

        # Try to select a system via mouse click — should be blocked
        old_selected = view.selected_system
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)
        )
        view.handle_event(event)
        assert view.selected_system == old_selected, "Selection should not change during animation"
        view.on_exit()

    def test_travel_animation_completes_to_trading(self) -> None:
        """Animation without encounter should transition to TRADING."""
        view = _make_view()
        view.on_enter()

        # Simulate travel animation state (no encounter)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.0
        view._travel_duration = 1.0
        view._travel_encounter = None
        view._travel_encounter_stop = 1.0

        # Advance past completion
        view.update(1.1)

        assert not view._travel_animating, "Animation should have ended"
        assert view.next_state == GameState.TRADING, "Should transition to TRADING"
        view.on_exit()

    def test_travel_animation_stops_on_encounter(self) -> None:
        """Animation with encounter should stop mid-route and show alert."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.0
        view._travel_duration = 1.0
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5

        # Advance to encounter point
        view.update(0.6)

        assert view._travel_alert_showing, "Alert should be showing"
        assert view._travel_animating, "Animation should still be active (alert phase)"
        assert view.next_state is None, "Should not transition yet (alert still showing)"
        view.on_exit()

    def test_encounter_alert_transitions_to_combat(self) -> None:
        """After alert timer expires, should transition to COMBAT."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0

        # Advance past alert timer
        view.update(1.3)

        assert not view._travel_animating, "Animation should have ended"
        assert view.next_state == GameState.COMBAT, "Should transition to COMBAT"
        assert view._pending_encounter is encounter, "Encounter ref should be stored"
        view.on_exit()

    def test_ship_position_interpolates_during_travel(self) -> None:
        """Ship position should lerp between origin and destination."""
        view = _make_view()
        view.on_enter()

        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter_stop = 1.0
        view._travel_duration = 1.0

        ship_x, ship_y, angle = view._get_ship_position()

        # Get origin and destination screen coords
        origin = view.systems["nexus_prime"]
        dest = view.systems["breakstone"]
        ox, oy = view._world_to_screen(origin.coordinates.x, origin.coordinates.y)
        dx, dy = view._world_to_screen(dest.coordinates.x, dest.coordinates.y)

        # At 50% progress, ship should be at midpoint
        expected_x = ox + (dx - ox) * 0.5
        expected_y = oy + (dy - oy) * 0.5
        assert abs(ship_x - expected_x) < 1.0, f"X mismatch: {ship_x} vs {expected_x}"
        assert abs(ship_y - expected_y) < 1.0, f"Y mismatch: {ship_y} vs {expected_y}"
        view.on_exit()

    def test_trade_button_does_not_trigger_travel_animation(self) -> None:
        """Clicking Trade (landing at current system) should not start travel animation."""
        view = _make_view()
        view.on_enter()

        # Simulate Trade button press
        view.next_state = GameState.TRADING

        assert not view._travel_animating, "Trade should not start travel animation"
        assert view._pending_encounter is None, "No encounter for local trade"
        view.on_exit()


# ============================================================================
# Active Route Highlight Tests
# ============================================================================


class TestActiveRouteHighlight:
    """Tests for bright route line during travel animation."""

    def test_active_route_ids_cleared_after_peaceful_travel(self) -> None:
        """Origin/dest IDs should clear when animation completes peacefully."""
        view = _make_view()
        view.on_enter()
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.0
        view._travel_duration = 1.0
        view._travel_encounter = None
        view._travel_encounter_stop = 1.0
        view.update(1.1)
        assert view._travel_origin_id is None, "Origin should clear after peaceful travel"
        assert view._travel_dest_id is None, "Dest should clear after peaceful travel"
        view.on_exit()

    def test_active_route_ids_cleared_after_encounter(self) -> None:
        """Origin/dest IDs should clear when encounter alert completes."""
        view = _make_view()
        view.on_enter()
        encounter = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0
        view.update(1.3)
        assert view._travel_origin_id is None, "Origin should clear after encounter"
        assert view._travel_dest_id is None, "Dest should clear after encounter"
        view.on_exit()


# ============================================================================
# Arrival Feedback Tests
# ============================================================================


class TestArrivalFeedback:
    """Tests for arrival particle burst and notification message."""

    def test_arrival_message_set_on_peaceful_travel(self) -> None:
        """arrival_message should contain destination name after uneventful travel."""
        view = _make_view()
        view.on_enter()
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.0
        view._travel_duration = 1.0
        view._travel_encounter = None
        view._travel_encounter_stop = 1.0
        view.update(1.1)
        assert view.arrival_message is not None
        assert "Breakstone" in view.arrival_message
        view.on_exit()

    def test_arrival_message_not_set_on_encounter(self) -> None:
        """arrival_message should not be set when encounter interrupts travel."""
        view = _make_view()
        view.on_enter()
        encounter = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0
        view.update(1.3)
        assert view.arrival_message is None
        view.on_exit()

    def test_arrival_message_reset_on_enter(self) -> None:
        """arrival_message should reset to None when view is re-entered."""
        view = _make_view()
        view.on_enter()
        view.arrival_message = "leftover"
        view.on_exit()
        view.on_enter()
        assert view.arrival_message is None
        view.on_exit()


# ============================================================================
# Travel Confirmation Dialog Tests
# ============================================================================


class TestTravelConfirmation:
    """Tests for the travel confirmation overlay."""

    def test_travel_button_shows_confirmation(self) -> None:
        """Pressing Travel should show confirmation overlay, not execute travel."""
        player = _make_player()
        view = _make_view(player=player)
        view.on_enter()
        view.selected_system = "breakstone"
        view._update_button_states()

        old_system = player.current_system_id
        view._on_travel_button()

        assert view._showing_travel_confirm, "Confirmation overlay should be visible"
        assert player.current_system_id == old_system, "Should NOT have traveled yet"
        assert not view._travel_animating, "Animation should not have started"
        view.on_exit()

    def test_confirm_executes_travel(self) -> None:
        """Pressing Confirm in the overlay should execute travel."""
        player = _make_player()
        view = _make_view(player=player)
        view.on_enter()
        view.selected_system = "breakstone"
        view._show_travel_confirmation()

        view._on_travel_confirm()

        assert not view._showing_travel_confirm, "Overlay should dismiss"
        # Travel should have started (either animating or system changed)
        assert view._travel_animating or player.current_system_id == "breakstone"
        view.on_exit()

    def test_cancel_dismisses_overlay(self) -> None:
        """Pressing Cancel should dismiss overlay without traveling."""
        player = _make_player()
        view = _make_view(player=player)
        view.on_enter()
        view.selected_system = "breakstone"
        view._show_travel_confirmation()

        view._on_travel_cancel()

        assert not view._showing_travel_confirm, "Overlay should be hidden"
        assert player.current_system_id == "nexus_prime", "Player should not have moved"
        view.on_exit()

    def test_overlay_blocks_system_selection(self) -> None:
        """Mouse clicks should not change selection while overlay is visible."""
        view = _make_view()
        view.on_enter()
        view._showing_travel_confirm = True
        old_selected = view.selected_system

        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300))
        view.handle_event(event)

        assert view.selected_system == old_selected, "Selection should not change"
        view.on_exit()

    def test_overlay_buttons_created_and_destroyed(self) -> None:
        """Confirm/Cancel buttons should follow create/destroy lifecycle."""
        view = _make_view()
        view.on_enter()
        view.selected_system = "breakstone"

        view._show_travel_confirmation()
        assert view._confirm_button is not None
        assert view._cancel_button is not None

        view._dismiss_travel_confirmation()
        assert view._confirm_button is None
        assert view._cancel_button is None
        view.on_exit()


# ============================================================================
# Danger Indicator Tests
# ============================================================================


class TestDangerIndicators:
    """Tests for danger-based route colors and info panel."""

    def test_danger_route_color_safe(self) -> None:
        color = GalaxyMapView._get_danger_route_color("safe")
        assert color == (40, 65, 45)

    def test_danger_route_color_moderate(self) -> None:
        color = GalaxyMapView._get_danger_route_color("moderate")
        assert color == (65, 55, 30)

    def test_danger_route_color_dangerous(self) -> None:
        color = GalaxyMapView._get_danger_route_color("dangerous")
        assert color == (65, 35, 35)

    def test_danger_dot_color_safe(self) -> None:
        color = GalaxyMapView._get_danger_dot_color("safe")
        assert color is not None
        assert color[1] > color[0], "Green channel should dominate for safe"

    def test_danger_dot_color_dangerous(self) -> None:
        color = GalaxyMapView._get_danger_dot_color("dangerous")
        assert color is not None
        assert color[0] > color[1], "Red channel should dominate for dangerous"


# ============================================================================
# Non-Hostile Encounter Routing Tests
# ============================================================================


class TestEncounterRouting:
    """Tests for routing encounters to ENCOUNTER or COMBAT state."""

    def test_hostile_encounter_routes_to_combat(self) -> None:
        """Hostile encounters should transition to COMBAT state."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0

        view.update(1.3)

        assert not view._travel_animating
        assert view._pending_encounter is encounter
        assert view.next_state == GameState.COMBAT
        view.on_exit()

    def test_distress_signal_routes_to_encounter(self) -> None:
        """Distress signal encounters should transition to ENCOUNTER state."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(
            enemy_template_ids=[], encounter_seed=42, encounter_type="distress_signal"
        )
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0

        view.update(1.3)

        assert not view._travel_animating
        assert view._pending_encounter_ref is encounter
        assert view.next_state == GameState.ENCOUNTER
        view.on_exit()

    def test_shakedown_routes_to_encounter(self) -> None:
        """Shakedown encounters should transition to ENCOUNTER state."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(
            enemy_template_ids=["pirate_scout"],
            encounter_seed=42,
            encounter_type="shakedown",
            shakedown_demand=150,
        )
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0

        view.update(1.3)

        assert not view._travel_animating
        assert view._pending_encounter_ref is encounter
        assert view.next_state == GameState.ENCOUNTER
        view.on_exit()

    def test_derelict_routes_to_encounter(self) -> None:
        """Derelict encounters should transition to ENCOUNTER state."""
        view = _make_view()
        view.on_enter()

        encounter = EncounterRef(
            enemy_template_ids=[], encounter_seed=42, encounter_type="derelict"
        )
        view._travel_animating = True
        view._travel_origin_id = "nexus_prime"
        view._travel_dest_id = "breakstone"
        view._travel_progress = 0.5
        view._travel_encounter = encounter
        view._travel_encounter_stop = 0.5
        view._travel_alert_showing = True
        view._travel_alert_timer = 1.2
        view._travel_duration = 1.0

        view.update(1.3)

        assert not view._travel_animating
        assert view._pending_encounter_ref is encounter
        assert view.next_state == GameState.ENCOUNTER
        view.on_exit()


# ============================================================================
# Integration Verification Tests
# ============================================================================


class TestIntegrationVerification:
    """Verify that new features integrate correctly with existing systems."""

    def test_crew_xp_delta_works_post_travel(self) -> None:
        """player.jumps_traveled should increment after _execute_travel()."""
        player = _make_player()
        view = _make_view(player=player)
        view.on_enter()

        old_jumps = player.jumps_traveled
        view.selected_system = "breakstone"
        view._execute_travel()

        assert player.jumps_traveled == old_jumps + 1, (
            f"jumps_traveled should increment: {player.jumps_traveled} vs {old_jumps}"
        )
        view.on_exit()

    def test_arrival_message_attribute_exists(self) -> None:
        """arrival_message should be initialized to None in constructor."""
        view = _make_view()
        assert view.arrival_message is None

    def test_pending_encounter_ref_initialized(self) -> None:
        """_pending_encounter_ref should be initialized to None."""
        view = _make_view()
        assert view._pending_encounter_ref is None


# ============================================================================
# Journal Quick-Add Overlay Tests
# ============================================================================


class TestJournalQuickAdd:
    """Tests for the J-key journal quick-add overlay."""

    def _make_view_with_journal(self) -> GalaxyMapView:
        from spacegame.models.journal import Journal

        view = _make_view()
        view.journal = Journal()
        return view

    def test_j_key_opens_quick_add(self) -> None:
        """Pressing J should open the quick-add overlay."""
        view = self._make_view_with_journal()
        view.on_enter()
        assert not view._showing_journal_quick_add
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)
        view.handle_event(event)
        assert view._showing_journal_quick_add
        view.on_exit()

    def test_j_key_without_journal_no_overlay(self) -> None:
        """J key should do nothing if journal is not set."""
        view = _make_view()
        view.on_enter()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)
        view.handle_event(event)
        assert not view._showing_journal_quick_add
        view.on_exit()

    def test_escape_closes_quick_add(self) -> None:
        """Escape should close the quick-add overlay."""
        view = self._make_view_with_journal()
        view.on_enter()
        view._show_journal_quick_add()
        assert view._showing_journal_quick_add
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)
        assert not view._showing_journal_quick_add
        assert view.next_state is None  # Should not navigate away
        view.on_exit()

    def test_confirm_creates_entry(self) -> None:
        """Confirming quick-add should create a journal entry."""
        view = self._make_view_with_journal()
        view.on_enter()
        view._show_journal_quick_add()
        assert view.journal.get_entry_count() == 0
        view._quick_add_text_entry.set_text("Test quick note")
        view._on_quick_add_confirm()
        assert view.journal.get_entry_count() == 1
        assert not view._showing_journal_quick_add
        entries = view.journal.get_entries()
        assert entries[0].text == "Test quick note"
        assert entries[0].source == "player"
        view.on_exit()

    def test_cancel_discards_entry(self) -> None:
        """Canceling quick-add should not create an entry."""
        view = self._make_view_with_journal()
        view.on_enter()
        view._show_journal_quick_add()
        view._quick_add_text_entry.set_text("This will be discarded")
        view._on_quick_add_cancel()
        assert view.journal.get_entry_count() == 0
        assert not view._showing_journal_quick_add
        view.on_exit()

    def test_quick_add_blocks_other_input(self) -> None:
        """When quick-add is showing, other events should be blocked."""
        view = self._make_view_with_journal()
        view.on_enter()
        view._show_journal_quick_add()
        old_selected = view.selected_system
        click_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)
        )
        view.handle_event(click_event)
        assert view.selected_system == old_selected
        view.on_exit()


# ============================================================================
# Faction Emblem in System Info
# ============================================================================


class TestSystemInfoFactionEmblem:
    """Tests for faction emblem rendering in system info panel."""

    def test_system_info_renders_with_faction(self) -> None:
        """Drawing system info for a system with a faction should not crash."""
        systems = _make_systems()
        # Set a real faction name on one system
        systems["nexus_prime"].faction = "commerce_guild"
        player = _make_player()
        view = _make_view(player=player, systems=systems)
        view.on_enter()
        view.selected_system = "nexus_prime"
        screen = pygame.display.get_surface()
        view._draw_system_info(screen, "nexus_prime")
        view.on_exit()

    def test_system_info_renders_without_faction(self) -> None:
        """Drawing system info for an independent system should not crash."""
        systems = _make_systems()
        systems["nexus_prime"].faction = "Independent"
        player = _make_player()
        view = _make_view(player=player, systems=systems)
        view.on_enter()
        view.selected_system = "nexus_prime"
        screen = pygame.display.get_surface()
        view._draw_system_info(screen, "nexus_prime")
        view.on_exit()
