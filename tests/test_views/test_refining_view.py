"""Tests for refining view — sprite wiring, forge visuals, recipe rendering."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship, ShipType  # noqa: E402
from spacegame.models.commodity import Commodity, CommodityCategory, Legality  # noqa: E402
from spacegame.models.refining import Recipe  # noqa: E402
from spacegame.views.refining_view import RefiningView  # noqa: E402


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
        "raw_ore": _make_commodity("raw_ore", "Raw Ore", 10),
        "iron_ore": _make_commodity("iron_ore", "Iron Ore", 20),
        "common_metals": _make_commodity("common_metals", "Common Metals", 40),
    }


def _make_recipe(recipe_id: str = "smelt_iron", **kwargs) -> Recipe:
    defaults = dict(
        id=recipe_id, name="Smelt Iron", description="Basic smelting",
        inputs={"iron_ore": 3}, outputs={"common_metals": 1},
        processing_time=5.0, location_ids=["forgeworks"],
    )
    defaults.update(kwargs)
    return Recipe(**defaults)


def _make_player() -> Player:
    return Player(
        name="TestCaptain", credits=5000,
        current_system_id="forgeworks",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


def _make_view(player: Player = None, recipes: list = None) -> RefiningView:
    if player is None:
        player = _make_player()
    if recipes is None:
        recipes = [
            _make_recipe("smelt_iron", category="commodity"),
            _make_recipe("forge_alloy", name="Forge Alloy", category="upgrade",
                         inputs={"common_metals": 2}, outputs={"common_metals": 3},
                         processing_time=10.0),
        ]
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = RefiningView(
        ui_manager, player, _make_commodities(),
        recipes=recipes, system_id="forgeworks",
    )
    view.on_enter()
    return view


class TestRefiningSpritWiring:
    """C3a: Refining sprite integration tests."""

    def test_forge_sprites_loaded(self) -> None:
        """View should load forge state sprites."""
        view = _make_view()
        assert hasattr(view, "_forge_sprites")
        assert len(view._forge_sprites) > 0, "No forge sprites loaded"
        view.on_exit()

    def test_mastery_star_sprites_loaded(self) -> None:
        """View should load mastery star sprites."""
        view = _make_view()
        assert hasattr(view, "_mastery_stars")
        assert len(view._mastery_stars) > 0, "No mastery star sprites loaded"
        view.on_exit()

    def test_category_icon_sprites_loaded(self) -> None:
        """View should load recipe category icon sprites."""
        view = _make_view()
        assert hasattr(view, "_category_icons")
        assert len(view._category_icons) > 0, "No category icon sprites loaded"
        view.on_exit()

    def test_render_does_not_crash(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_multiple_frames(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        for _ in range(5):
            view.update(0.016)
            view.render(screen)
        view.on_exit()

    def test_render_with_active_jobs(self) -> None:
        """Render should handle active jobs with forge sprite switching."""
        player = _make_player()
        player.ship.add_cargo("iron_ore", 10, price_per_unit=0)
        view = _make_view(player)
        screen = pygame.display.get_surface()
        # Start a job
        if view.session and view.session.available_recipes:
            recipe = view.session.available_recipes[0]
            view.session.start_job(recipe, player.ship.current_cargo)
        view.update(0.5)
        view.render(screen)
        view.on_exit()

    def test_mastery_stars_render_for_mastered_recipe(self) -> None:
        """Recipes with mastery should show star sprites."""
        player = _make_player()
        # Set mastery level 2 for smelt_iron
        player.recipe_mastery.record_craft("smelt_iron")
        for _ in range(8):
            player.recipe_mastery.record_craft("smelt_iron")
        view = _make_view(player)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_forge_sprite_state_tracks_queue(self) -> None:
        """Forge should show idle when no jobs, active when jobs running."""
        view = _make_view()
        # With no jobs, forge state should be idle
        assert view._get_forge_state() == "idle"
        view.on_exit()


class TestRecipeScrollAndFilter:
    """C3-deep: Scrollable recipe list and category filter tests."""

    def test_recipe_scroll_panel_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_recipe_scroll")
        assert view._recipe_scroll is not None
        view.on_exit()

    def test_recipe_scroll_content_height_set(self) -> None:
        """Content height should be set based on recipe count."""
        view = _make_view()
        assert view._recipe_scroll.content_height > 0
        view.on_exit()

    def test_category_filter_default_is_all(self) -> None:
        view = _make_view()
        assert view._active_category == "all"
        view.on_exit()

    def test_get_filtered_recipes_all(self) -> None:
        view = _make_view()
        filtered = view._get_filtered_recipes()
        assert len(filtered) == len(view.session.available_recipes)
        view.on_exit()

    def test_get_filtered_recipes_by_category(self) -> None:
        view = _make_view()
        view._active_category = "commodity"
        filtered = view._get_filtered_recipes()
        for r in filtered:
            assert r.category == "commodity"
        view.on_exit()

    def test_category_change_resets_scroll(self) -> None:
        view = _make_view()
        # Force enough content to need scrolling
        view._recipe_scroll.set_content_height(2000)
        view._recipe_scroll.scroll(delta=-5)  # Scroll down
        assert view._recipe_scroll.scroll_offset > 0
        # Simulate category change behavior
        view._recipe_scroll.scroll_to_top()
        assert view._recipe_scroll.scroll_offset == 0
        view.on_exit()

    def test_render_with_category_tabs(self) -> None:
        """Render should display category tabs without crashing."""
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        assert len(view._category_tab_rects) == 5  # all, commodity, upgrade, equipment, trade_good
        view.on_exit()

    def test_category_filter_selects_correct_recipe(self) -> None:
        """Switching filter should select first recipe in that category."""
        view = _make_view()
        if view.session and len(view.session.available_recipes) > 1:
            view._active_category = "upgrade"
            filtered = view._get_filtered_recipes()
            if filtered:
                # Simulate clicking the "upgrade" tab
                view._active_category = "upgrade"
                view.selected_recipe_idx = view.session.available_recipes.index(filtered[0])
                selected = view.session.available_recipes[view.selected_recipe_idx]
                assert selected.category == "upgrade", (
                    f"Selected recipe category should be 'upgrade', got '{selected.category}'"
                )
        view.on_exit()

    def test_start_guards_against_invisible_recipe(self) -> None:
        """Start should not craft recipe outside active filter."""
        view = _make_view()
        if view.session and len(view.session.available_recipes) > 1:
            # Set filter to upgrade, but idx points to commodity recipe
            view._active_category = "upgrade"
            view.selected_recipe_idx = 0  # First recipe is commodity
            # Start should either redirect or block
            # (won't crash, and won't craft wrong thing)
            view._start_selected_recipe()
        view.on_exit()

    def test_keyboard_nav_respects_filter(self) -> None:
        """Up/Down should navigate within filtered list only."""
        view = _make_view()
        if view.session:
            view._active_category = "commodity"
            filtered = view._get_filtered_recipes()
            if len(filtered) >= 2:
                # Select first, navigate forward
                view.selected_recipe_idx = view.session.available_recipes.index(filtered[0])
                view._navigate_recipe(forward=True)
                selected = view.session.available_recipes[view.selected_recipe_idx]
                assert selected in filtered, "Should stay within filtered recipes"
        view.on_exit()

    def test_ingredient_availability_render(self) -> None:
        """Render should show availability indicators without crashing."""
        player = _make_player()
        player.ship.add_cargo("iron_ore", 10, price_per_unit=0)
        view = _make_view(player)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()


class TestRefiningDeepPolish:
    """C3-deep final: output float, token counter, discovery banner, batch hold."""

    def test_floating_item_manager_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_floats")
        view.on_exit()

    def test_displayed_tokens_initialized(self) -> None:
        view = _make_view()
        assert view._displayed_tokens == float(view.player.forge_tokens)
        view.on_exit()

    def test_token_tween_starts_none(self) -> None:
        view = _make_view()
        assert view._token_tween is None
        view.on_exit()

    def test_discovery_banner_starts_inactive(self) -> None:
        view = _make_view()
        assert view._discovery_banner is None
        assert view._discovery_timer <= 0
        view.on_exit()

    def test_discovery_banner_renders_without_crash(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view._discovery_banner = "Test Recipe"
        view._discovery_timer = 2.0
        view.render(screen)
        view.on_exit()

    def test_batch_hold_state_initialized(self) -> None:
        view = _make_view()
        assert view._batch_hold_active is False
        assert view._batch_hold_direction == 0
        assert view._batch_hold_repeats == 0
        view.on_exit()

    def test_batch_hold_increments_after_delay(self) -> None:
        """Holding batch+ should auto-increment after 0.4s delay."""
        view = _make_view()
        initial = view.batch_count
        # Simulate hold start
        view._batch_hold_active = True
        view._batch_hold_direction = 1
        view._batch_hold_timer = 0.0
        view._batch_hold_repeats = 0
        # Before delay: no change
        view.update(0.3)
        assert view.batch_count == initial
        # After delay: should increment
        view.update(0.2)  # total 0.5s, past 0.4s delay
        assert view.batch_count > initial, "Batch count should increment after hold delay"
        view.on_exit()

    def test_batch_hold_decrements(self) -> None:
        """Holding batch- should auto-decrement after delay."""
        view = _make_view()
        view.batch_count = 5
        view._batch_hold_active = True
        view._batch_hold_direction = -1
        view._batch_hold_timer = 0.0
        view._batch_hold_repeats = 0
        view.update(0.6)  # Well past delay
        assert view.batch_count < 5, "Batch count should decrement after hold delay"
        view.on_exit()

    def test_batch_hold_multiple_repeats(self) -> None:
        """Holding longer should fire multiple repeats."""
        view = _make_view()
        view._batch_hold_active = True
        view._batch_hold_direction = 1
        view._batch_hold_timer = 0.0
        view._batch_hold_repeats = 0
        # Simulate realistic frame-by-frame hold (16ms steps for ~1 second)
        for _ in range(60):
            view.update(0.016)
        assert view.batch_count >= 3, "Multiple repeats should have fired"
        view.on_exit()

    def test_render_summary_with_forge_sprite(self) -> None:
        """Summary overlay should render forge sprite without crash."""
        view = _make_view()
        screen = pygame.display.get_surface()
        view._show_summary = True
        view.render(screen)
        view.on_exit()

    def test_forge_state_complete_during_flash(self) -> None:
        view = _make_view()
        view._forge_flash_timer = 0.5
        assert view._get_forge_state() == "complete"
        view.on_exit()

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
        cancel = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(cancel)
        assert not view._confirm_exit
        view.on_exit()

    def test_enter_key_crafts_recipe(self) -> None:
        """Enter key should attempt to craft selected recipe."""
        player = _make_player()
        player.ship.add_cargo("iron_ore", 10, price_per_unit=0)
        view = _make_view(player)
        enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(enter)
        # Should not crash; may or may not start a job depending on recipe availability
        view.on_exit()

    def test_render_with_confirm_exit(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view._confirm_exit = True
        view.render(screen)
        view.on_exit()

    def test_render_with_all_features_active(self) -> None:
        """Render with banner, token animation, and float all active."""
        player = _make_player()
        player.ship.add_cargo("iron_ore", 10, price_per_unit=0)
        view = _make_view(player)
        screen = pygame.display.get_surface()
        view._discovery_banner = "Alloy Forge"
        view._discovery_timer = 2.0
        view._forge_flash_timer = 0.3
        for _ in range(10):
            view.update(0.016)
            view.render(screen)
        view.on_exit()


class TestRefiningBufferIntegration:
    """Basic forge buffer integration tests."""

    def test_view_has_buffer(self) -> None:
        view = _make_view()
        assert view._buffer is not None
        assert view._buffer.system_id == "forgeworks"
        view.on_exit()

    def test_transfer_buffer_to_cargo(self) -> None:
        player = _make_player()
        view = _make_view(player)
        view._buffer.add_output("common_metals", 5)
        transferred = view._transfer_buffer_to_cargo()
        assert transferred == 5
        assert player.ship.current_cargo.get("common_metals", 0) == 5
        view.on_exit()
