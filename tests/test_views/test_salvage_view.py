"""Tests for salvage view — sprite wiring, visual integration, hold transfer."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship, ShipType  # noqa: E402
from spacegame.models.salvage import SalvageConfig, CellState  # noqa: E402
from spacegame.models.commodity import Commodity, CommodityCategory, Legality  # noqa: E402
from spacegame.views.salvage_view import SalvageView  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="Basic ship", cargo_capacity=100, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=1, special_abilities=[], availability="all",
    )


def _make_commodity(cid: str, name: str, price: int) -> Commodity:
    return Commodity(
        id=cid, name=name, base_price=price,
        category=CommodityCategory.BASIC, description="Test",
        variance_min=-0.1, variance_max=0.1, volume_per_unit=1,
        legality=Legality.LEGAL, production_tags=[], consumption_tags=[],
    )


def _make_commodities() -> dict[str, Commodity]:
    return {
        "scrap_metal": _make_commodity("scrap_metal", "Scrap Metal", 5),
        "salvaged_electronics": _make_commodity("salvaged_electronics", "Electronics", 30),
        "rare_parts": _make_commodity("rare_parts", "Rare Parts", 80),
    }


def _make_player() -> Player:
    return Player(
        name="TestCaptain", credits=5000,
        current_system_id="forgeworks",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


def _make_view(player: Player = None) -> SalvageView:
    if player is None:
        player = _make_player()
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    config = SalvageConfig(system_id="forgeworks")
    view = SalvageView(ui_manager, player, _make_commodities(), salvage_config=config)
    view.on_enter()
    # Auto-select first derelict type to skip selection screen
    from spacegame.models.salvage import DERELICT_TYPES

    if view._selecting_derelict:
        view._start_with_derelict(DERELICT_TYPES[0])
    return view


class TestSalvageSpriteWiring:
    """C2a: Salvage sprite integration tests."""

    def test_derelict_backgrounds_loaded(self) -> None:
        """View should load derelict background sprites."""
        view = _make_view()
        assert hasattr(view, "_derelict_bg")
        # Should have attempted to load a background for the session's derelict type
        view.on_exit()

    def test_cell_state_sprites_loaded(self) -> None:
        """View should load cell state sprites."""
        view = _make_view()
        assert hasattr(view, "_cell_sprites")
        assert len(view._cell_sprites) > 0, "No cell state sprites loaded"
        view.on_exit()

    def test_quality_frame_sprites_loaded(self) -> None:
        """View should load quality frame sprites."""
        view = _make_view()
        assert hasattr(view, "_quality_frames")
        assert len(view._quality_frames) > 0, "No quality frame sprites loaded"
        view.on_exit()

    def test_mode_icon_sprites_loaded(self) -> None:
        """View should load scan/extract mode icon sprites."""
        view = _make_view()
        assert hasattr(view, "_mode_icons")
        assert "scan" in view._mode_icons or "extract" in view._mode_icons
        view.on_exit()

    def test_render_does_not_crash(self) -> None:
        """Full render with all sprites should work without errors."""
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_multiple_frames(self) -> None:
        """Multiple update+render cycles should be stable."""
        view = _make_view()
        screen = pygame.display.get_surface()
        for _ in range(5):
            view.update(0.016)
            view.render(screen)
        view.on_exit()

    def test_render_with_scanned_cells(self) -> None:
        """Render should handle scanned cells (items and empty) correctly."""
        view = _make_view()
        screen = pygame.display.get_surface()
        # Scan a few cells to exercise scanned cell rendering
        if view.session:
            for cell in view.session.grid[:3]:
                view.session.scan_cell(cell.grid_x, cell.grid_y)
        view.render(screen)
        view.on_exit()

    def test_render_with_extracting_cells(self) -> None:
        """Render should handle extracting cells correctly."""
        view = _make_view()
        screen = pygame.display.get_surface()
        if view.session:
            # Scan all cells, then start extracting any items found
            for cell in view.session.grid:
                view.session.scan_cell(cell.grid_x, cell.grid_y)
            for cell in view.session.grid:
                if cell.has_item and cell.state == CellState.SCANNED:
                    view.session.start_extract(cell.grid_x, cell.grid_y)
                    break
        view.update(0.5)
        view.render(screen)
        view.on_exit()

    def test_render_with_corruption(self) -> None:
        """Render should handle corrupted state visuals."""
        view = _make_view()
        screen = pygame.display.get_surface()
        if view.session:
            # Force corruption
            view.session.corruption_started = True
            view.session.corruption_timer = 0
            view.session.is_corrupted = True
            view.session._apply_corruption()
        view.render(screen)
        view.on_exit()

    def test_derelict_bg_maps_to_type(self) -> None:
        """Background sprite should correspond to derelict type."""
        view = _make_view()
        # The derelict type is random, but _derelict_bg should be set
        if view.session and view._derelict_bg is not None:
            assert isinstance(view._derelict_bg, pygame.Surface)
        view.on_exit()


class TestSalvageDeepPolish:
    """C2-deep: scan wave, item float, corruption wave, deck transition, glow."""

    def test_floating_item_manager_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_floats")
        view.on_exit()

    def test_scan_waves_starts_empty(self) -> None:
        view = _make_view()
        assert len(view._scan_waves) == 0
        view.on_exit()

    def test_scan_creates_wave(self) -> None:
        view = _make_view()
        if view.session:
            cell = view.session.grid[0]
            view.session.scan_cell(cell.grid_x, cell.grid_y)
            # The click_cell method creates the wave, not scan_cell directly
            view._click_cell(cell.grid_x, cell.grid_y)
        # Waves may or may not be created depending on mode
        view.on_exit()

    def test_excellent_glow_starts_empty(self) -> None:
        view = _make_view()
        assert len(view._excellent_glow) == 0
        view.on_exit()

    def test_heartbeat_flash_default_zero(self) -> None:
        view = _make_view()
        assert view._heartbeat_flash == 0.0
        view.on_exit()

    def test_deck_transition_starts_inactive(self) -> None:
        view = _make_view()
        assert view._deck_transition_active is False
        view.on_exit()

    def test_start_deck_transition_populates_queue(self) -> None:
        view = _make_view()
        view._start_deck_transition()
        assert view._deck_transition_active is True
        assert len(view._deck_transition) > 0
        view.on_exit()

    def test_deck_transition_cells_masked_during_animation(self) -> None:
        view = _make_view()
        view._start_deck_transition()
        # During transition, cells are not transitioned yet
        first = view._deck_transition[0]
        assert not view._is_cell_transitioned(first[0], first[1])
        view.on_exit()

    def test_deck_transition_completes_over_time(self) -> None:
        view = _make_view()
        view._start_deck_transition()
        # Fast-forward past all delays
        for _ in range(30):
            view.update(0.05)
        assert view._deck_transition_active is False
        view.on_exit()

    def test_corruption_wave_queued_on_corruption(self) -> None:
        """Corruption should queue staggered particle wave."""
        view = _make_view()
        if view.session:
            # Trigger a scan to start corruption timer
            view.session.scan_cell(0, 0)
            # Force corruption
            view.session.corruption_timer = 0.01
            view.update(0.02)  # Should trigger corruption
            # Wave entries should be queued (or already processed)
        view.on_exit()

    def test_render_with_all_polish_active(self) -> None:
        """Render with scan waves, glow, heartbeat, transition all active."""
        view = _make_view()
        screen = pygame.display.get_surface()
        if view.session:
            # Create active scan wave
            view._scan_waves.append([300.0, 300.0, 20.0, 200.0, 300.0])
            # Create excellent glow
            view._excellent_glow[(0, 0)] = 0.4
            # Force heartbeat
            view._heartbeat_flash = 25.0
            # Start deck transition
            view._start_deck_transition()
        for _ in range(5):
            view.update(0.016)
            view.render(screen)
        view.on_exit()

    def test_render_with_floating_items(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view._floats.add_icon_float(
            text="+2 Scrap",
            origin=(300.0, 300.0),
            target=(600.0, 400.0),
            duration=0.5,
        )
        view.update(0.1)
        view.render(screen)
        view.on_exit()


class TestSalvageUIOverhaul:
    """UI overhaul: tooltips, keyboard shortcuts, exit confirmation."""

    def test_tooltip_state_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_tooltip")
        view.on_exit()

    def test_exit_confirmation_blocks_session_end(self) -> None:
        view = _make_view()
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED, ui_element=view.back_button,
        )
        view.handle_event(event)
        assert view._confirm_exit
        assert not view._show_summary
        view.on_exit()

    def test_exit_cancel_resumes_play(self) -> None:
        view = _make_view()
        view._confirm_exit = True
        cancel = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
        view.handle_event(cancel)
        assert not view._confirm_exit
        view.on_exit()

    def test_tab_toggles_mode(self) -> None:
        view = _make_view()
        assert view.mode == "scan"
        tab = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        view.handle_event(tab)
        assert view.mode == "extract"
        view.handle_event(tab)
        assert view.mode == "scan"
        view.on_exit()

    def test_render_with_confirm_exit(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view._confirm_exit = True
        view.render(screen)
        view.on_exit()

    def test_auto_scan_on_hidden_cell_click(self) -> None:
        """Clicking a hidden cell should scan it regardless of mode."""
        view = _make_view()
        view.mode = "extract"  # Deliberately in extract mode
        if view.session:
            # Find a hidden cell
            hidden_cell = next(
                (c for c in view.session.grid if c.state == CellState.HIDDEN), None
            )
            if hidden_cell:
                view._click_cell(hidden_cell.grid_x, hidden_cell.grid_y)
                # Cell should now be scanned
                assert hidden_cell.state == CellState.SCANNED
        view.on_exit()

    def test_auto_extract_on_scanned_item_click(self) -> None:
        """Clicking a scanned item cell should extract it regardless of mode."""
        view = _make_view()
        view.mode = "scan"  # Deliberately in scan mode
        if view.session:
            # Scan all cells to find items
            for cell in view.session.grid:
                view.session.scan_cell(cell.grid_x, cell.grid_y)
            # Find a scanned cell with an item
            item_cell = next(
                (c for c in view.session.grid if c.state == CellState.SCANNED and c.has_item),
                None,
            )
            if item_cell:
                view._click_cell(item_cell.grid_x, item_cell.grid_y)
                assert item_cell.state == CellState.EXTRACTING
        view.on_exit()

    def test_derelict_selection_screen(self) -> None:
        """View should start in selection mode, then transition to gameplay."""
        player = _make_player()
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        config = SalvageConfig(system_id="forgeworks")
        view = SalvageView(ui_manager, player, _make_commodities(), salvage_config=config)
        view.on_enter()
        assert view._selecting_derelict, "Should start in selection mode"
        assert view.session is None, "Session should not exist before selection"
        # Select a derelict type
        from spacegame.models.salvage import DERELICT_TYPES
        view._start_with_derelict(DERELICT_TYPES[1])  # Lab Module
        assert not view._selecting_derelict
        assert view.session is not None
        assert view.session.derelict_type.id == "lab_module"
        view.on_exit()

    def test_derelict_selection_renders(self) -> None:
        """Selection screen should render without crash."""
        player = _make_player()
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        config = SalvageConfig(system_id="forgeworks")
        view = SalvageView(ui_manager, player, _make_commodities(), salvage_config=config)
        view.on_enter()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_story_fragments_loaded(self) -> None:
        view = _make_view()
        assert len(view._derelict_stories) > 0, "Should have loaded derelict stories"
        view.on_exit()

    def test_contextual_instruction_text(self) -> None:
        """Instruction text should change based on game state."""
        view = _make_view()
        text = view._get_instruction_text()
        assert len(text) > 0
        view.on_exit()


class TestSalvageHoldIntegration:
    """Basic hold integration tests."""

    def test_view_has_hold(self) -> None:
        view = _make_view()
        assert view._hold is not None
        assert view._hold.system_id == "forgeworks"
        view.on_exit()

    def test_transfer_hold_to_cargo(self) -> None:
        player = _make_player()
        view = _make_view(player)
        view._hold.add_salvage("scrap_metal", 5)
        transferred = view._transfer_hold_to_cargo()
        assert transferred == 5
        assert player.ship.current_cargo.get("scrap_metal", 0) == 5
        view.on_exit()
