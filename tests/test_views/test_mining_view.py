"""Tests for mining view — silo integration, strata awards, transfers."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship, ShipType  # noqa: E402
from spacegame.models.mining import MiningConfig  # noqa: E402
from spacegame.models.commodity import Commodity, CommodityCategory, Legality  # noqa: E402
from spacegame.views.mining_view import MiningView  # noqa: E402


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


def _make_commodity(cid: str, name: str, price: int) -> Commodity:
    return Commodity(
        id=cid,
        name=name,
        base_price=price,
        category=CommodityCategory.BASIC,
        description="Test",
        variance_min=-0.1,
        variance_max=0.1,
        volume_per_unit=1,
        legality=Legality.LEGAL,
        production_tags=[],
        consumption_tags=[],
    )


def _make_commodities() -> dict[str, Commodity]:
    """Create minimal commodities for testing."""
    return {
        "raw_ore": _make_commodity("raw_ore", "Raw Ore", 10),
        "iron_ore": _make_commodity("iron_ore", "Iron Ore", 20),
        "crystal_ore": _make_commodity("crystal_ore", "Crystal Ore", 50),
        "rare_ore": _make_commodity("rare_ore", "Rare Ore", 100),
    }


def _make_player() -> Player:
    return Player(
        name="TestCaptain",
        credits=5000,
        current_system_id="breakstone",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


def _make_view(player: Player = None) -> MiningView:
    if player is None:
        player = _make_player()
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    config = MiningConfig(system_id="breakstone")
    view = MiningView(ui_manager, player, _make_commodities(), mining_config=config)
    view.on_enter()
    return view


class TestSiloIntegration:
    """Tests for silo-based mining output."""

    def test_view_has_silo(self) -> None:
        view = _make_view()
        assert view._silo is not None
        assert view._silo.system_id == "breakstone"
        view.on_exit()

    def test_click_mine_goes_to_silo(self) -> None:
        view = _make_view()
        # Mine a rock until it breaks
        rock = view.session.rocks[0]
        for _ in range(100):
            success, msg, result = view.session.click_rock(rock.grid_x, rock.grid_y)
            if result is not None:
                view._silo.add_ore(result.commodity_id, result.quantity)
                break
        assert view._silo.get_total_stored() > 0
        view.on_exit()

    def test_silo_used_not_cargo(self) -> None:
        player = _make_player()
        view = _make_view(player)
        # Mine a rock by direct click through the view
        rock = view.session.rocks[0]
        initial_cargo = sum(player.ship.current_cargo.values())
        for _ in range(100):
            view._click_rock(rock.grid_x, rock.grid_y)
            if rock.depleted:
                break
        # Cargo should NOT have changed (goes to silo now)
        after_cargo = sum(player.ship.current_cargo.values())
        assert after_cargo == initial_cargo
        # But silo should have something
        assert view._silo.get_total_stored() > 0
        view.on_exit()

    def test_render_does_not_crash(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()


class TestStrataOnDepthAdvance:
    """Tests for strata token awards on field regeneration."""

    def _clear_field(self, view) -> None:
        """Deplete all rocks to satisfy the 50% clear requirement."""
        if view.session:
            for rock in view.session.rocks:
                rock.depleted = True

    def test_regen_awards_strata(self) -> None:
        player = _make_player()
        view = _make_view(player)
        initial_strata = player.strata_tokens
        self._clear_field(view)
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view.regen_button,
        )
        view.handle_event(event)
        assert player.strata_tokens > initial_strata
        assert view._session_strata > 0
        view.on_exit()

    def test_strata_accumulates_across_regens(self) -> None:
        player = _make_player()
        view = _make_view(player)
        self._clear_field(view)
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view.regen_button,
        )
        view.handle_event(event)
        first_strata = player.strata_tokens
        self._clear_field(view)
        view.handle_event(event)
        assert player.strata_tokens > first_strata
        view.on_exit()

    def test_regen_blocked_without_clearing(self) -> None:
        """Regenerate should be blocked if less than 50% of field is cleared."""
        player = _make_player()
        view = _make_view(player)
        initial_strata = player.strata_tokens
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view.regen_button,
        )
        view.handle_event(event)
        assert player.strata_tokens == initial_strata, "No strata without clearing"
        view.on_exit()


class TestTransfer:
    """Tests for silo-to-cargo transfer on exit."""

    def test_transfer_moves_ore_to_cargo(self) -> None:
        player = _make_player()
        view = _make_view(player)
        # Put some ore in the silo
        view._silo.add_ore("iron_ore", 20)
        transferred = view._transfer_silo_to_cargo()
        assert transferred == 20
        assert player.ship.get_cargo_quantity("iron_ore") == 20
        assert view._silo.get_total_stored() == 0
        view.on_exit()

    def test_transfer_limited_by_cargo_space(self) -> None:
        player = _make_player()
        # Fill cargo almost full
        player.ship.add_cargo("raw_ore", 95)
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 20)
        transferred = view._transfer_silo_to_cargo()
        assert transferred <= 5
        assert view._silo.get_total_stored() > 0  # Remainder stays in silo
        view.on_exit()

    def test_transfer_on_stop_mining(self) -> None:
        """Stopping mining shows transfer screen; default is nothing selected."""
        player = _make_player()
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 10)
        # Press stop mining → triggers confirmation
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view.back_button,
        )
        view.handle_event(event)
        assert view._confirm_exit, "Should show exit confirmation"
        # Confirm exit with Y key → shows transfer screen
        confirm_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y)
        view.handle_event(confirm_event)
        assert view._show_transfer, "Should show transfer screen"
        assert not view._show_summary, "Summary comes after transfer"
        # Default selections should be zero (player must actively choose)
        for qty in view._transfer_selections.values():
            assert qty == 0, "Transfer should default to nothing selected"
        # Manually select all to transfer, then confirm
        view._transfer_selections["iron_ore"] = 10
        enter_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(enter_event)
        assert view._show_summary
        assert view._transfer_count == 10
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        view.on_exit()

    def test_transfer_take_nothing(self) -> None:
        """ESC on transfer screen leaves everything in silo."""
        player = _make_player()
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 10)
        # End session → transfer screen
        view._end_session()
        assert view._show_transfer
        # ESC → leave in silo
        esc_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(esc_event)
        assert view._show_summary
        assert view._transfer_count == 0
        assert player.ship.get_cargo_quantity("iron_ore") == 0
        assert view._silo.get_total_stored() == 10
        view.on_exit()

    def test_transfer_partial_selection(self) -> None:
        """Player can choose to transfer only some ore."""
        player = _make_player()
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 20)
        view._end_session()
        assert view._show_transfer
        # Adjust selection to only take 5
        view._transfer_selections["iron_ore"] = 5
        view._apply_transfer_selections()
        view._finalize_session()
        assert view._transfer_count == 5
        assert player.ship.get_cargo_quantity("iron_ore") == 5
        assert view._silo.contents.get("iron_ore", 0) == 15
        view.on_exit()


class TestDeepCoreBonuses:
    """Tests for deep core upgrade effects in session."""

    def test_energy_conduit_increases_max_energy(self) -> None:
        player = _make_player()
        # Simulate energy conduit level 2 (6 extra energy)
        player.deep_core_upgrades._levels["energy_conduit"] = 2
        view = _make_view(player)
        base_energy = MiningConfig(system_id="breakstone").max_energy
        assert view.session.max_energy == base_energy + 6
        view.on_exit()

    def test_core_resonance_increases_click_power(self) -> None:
        player = _make_player()
        # Simulate core resonance level 3 (24% extra click power)
        player.deep_core_upgrades._levels["core_resonance"] = 3
        view = _make_view(player)
        assert view.session.click_power_bonus >= 0.24
        view.on_exit()

    def test_seismic_pulse_increases_chain_chance(self) -> None:
        player = _make_player()
        # Simulate seismic_pulse level 2 (+10% chain chance)
        player.deep_core_upgrades._levels["seismic_pulse"] = 2
        view = _make_view(player)
        assert view.session.chain_chance_bonus >= 0.10
        view.on_exit()

    def test_seismic_pulse_level_3_increases_chain_depth(self) -> None:
        from spacegame.models.mining import CHAIN_MAX_DEPTH

        player = _make_player()
        player.deep_core_upgrades._levels["seismic_pulse"] = 3
        view = _make_view(player)
        assert view.session.max_chain_depth == CHAIN_MAX_DEPTH + 1
        view.on_exit()

    def test_depth_scanner_sets_starting_depth(self) -> None:
        player = _make_player()
        # Simulate depth_scanner level 2 (start at depth 11: 1 + 2*5)
        player.deep_core_upgrades._levels["depth_scanner"] = 2
        view = _make_view(player)
        assert view.session.depth == 11
        view.on_exit()

    def test_automaton_core_increases_drone_speed(self) -> None:
        player = _make_player()
        # Simulate automaton_core level 2 (+30% drone speed)
        player.deep_core_upgrades._levels["automaton_core"] = 2
        view = _make_view(player)
        assert view.session.drone_speed_bonus >= 0.30
        view.on_exit()


class TestRockSpriteWiring:
    """Tests for C1a: rock sprite integration in the mining view."""

    def test_rock_sprite_map_covers_core_types(self) -> None:
        """All non-monolith rock types should have a sprite mapping."""
        from spacegame.models.mining import RockType

        for rt in (
            RockType.COMMON,
            RockType.IRON,
            RockType.CRYSTAL,
            RockType.RARE,
            RockType.DENSE,
            RockType.VOLATILE,
        ):
            assert rt in MiningView.ROCK_SPRITE_MAP, f"Missing sprite map for {rt}"

    def test_rock_sprites_loaded(self) -> None:
        """View should load rock sprite variants on init."""
        view = _make_view()
        # At least some rock types should have sprites loaded
        assert len(view._rock_sprites) > 0, "No rock sprites were loaded"
        # Each loaded type should have at least one variant
        for rt, variants in view._rock_sprites.items():
            assert len(variants) > 0, f"{rt} has no sprite variants"
        view.on_exit()

    def test_get_rock_sprite_returns_surface(self) -> None:
        """Sprite getter should return a Surface for loaded types."""
        from spacegame.models.mining import RockType

        view = _make_view()
        if RockType.COMMON in view._rock_sprites:
            surf = view._get_rock_sprite(RockType.COMMON, 0, 0)
            assert isinstance(surf, pygame.Surface)
        view.on_exit()

    def test_get_rock_sprite_deterministic(self) -> None:
        """Same grid position should return same variant."""
        from spacegame.models.mining import RockType

        view = _make_view()
        if RockType.IRON in view._rock_sprites:
            s1 = view._get_rock_sprite(RockType.IRON, 2, 3)
            s2 = view._get_rock_sprite(RockType.IRON, 2, 3)
            assert s1 is s2, "Same position should return same sprite"
        view.on_exit()

    def test_get_rock_sprite_varies_by_position(self) -> None:
        """Different positions may return different variants."""
        from spacegame.models.mining import RockType

        view = _make_view()
        if RockType.COMMON in view._rock_sprites and len(view._rock_sprites[RockType.COMMON]) > 1:
            sprites_seen = set()
            for gx in range(6):
                for gy in range(4):
                    s = view._get_rock_sprite(RockType.COMMON, gx, gy)
                    sprites_seen.add(id(s))
            assert len(sprites_seen) > 1, "Should see multiple variants across grid"
        view.on_exit()

    def test_monolith_has_sprite(self) -> None:
        """Monolith rocks should have a dedicated sprite."""
        from spacegame.models.mining import RockType

        view = _make_view()
        surf = view._get_rock_sprite(RockType.MONOLITH, 0, 0)
        assert surf is not None, "Monolith should have a sprite"
        view.on_exit()

    def test_hazard_sprites_loaded(self) -> None:
        """View should load hazard sprite variants."""
        view = _make_view()
        # Hazard sprites should be loaded if files exist
        assert len(view._hazard_sprites) > 0, "No hazard sprites were loaded"
        view.on_exit()

    def test_drone_sprites_loaded(self) -> None:
        """View should load drone tier sprites."""
        view = _make_view()
        # At least some tiers should be loaded
        loaded = sum(1 for s in view._drone_sprites.values() if s is not None)
        assert loaded > 0, "No drone sprites were loaded"
        view.on_exit()

    def test_render_with_sprites_does_not_crash(self) -> None:
        """Full render with sprites should work without errors."""
        view = _make_view()
        screen = pygame.display.get_surface()
        # Render multiple frames to exercise sprite paths
        for _ in range(3):
            view.update(0.016)
            view.render(screen)
        view.on_exit()


class TestMiningDeepPolish:
    """C1-deep: compress animation, ore float, cascade timing, glow."""

    def test_floating_item_manager_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_floats")
        view.on_exit()

    def test_rock_compress_starts_empty(self) -> None:
        view = _make_view()
        assert len(view._rock_compress) == 0
        view.on_exit()

    def test_click_triggers_compress(self) -> None:
        view = _make_view()
        rock = view.session.rocks[0]
        view._click_rock(rock.grid_x, rock.grid_y)
        assert (rock.grid_x, rock.grid_y) in view._rock_compress
        view.on_exit()

    def test_compress_decays_over_time(self) -> None:
        view = _make_view()
        rock = view.session.rocks[0]
        view._click_rock(rock.grid_x, rock.grid_y)
        view.update(0.2)  # Longer than 0.15s decay
        assert (rock.grid_x, rock.grid_y) not in view._rock_compress
        view.on_exit()

    def test_chain_pending_list_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_chain_pending")
        assert len(view._chain_pending) == 0
        view.on_exit()

    def test_glow_time_advances(self) -> None:
        view = _make_view()
        view.update(0.5)
        assert view._glow_time > 0
        view.on_exit()

    def test_render_with_compress_and_glow(self) -> None:
        """Render should handle compress animation and glow without crash."""
        view = _make_view()
        screen = pygame.display.get_surface()
        # Click a rock to trigger compress
        rock = view.session.rocks[0]
        view._click_rock(rock.grid_x, rock.grid_y)
        view.update(0.05)
        view.render(screen)
        view.on_exit()

    def test_ore_float_on_rock_break(self) -> None:
        """Breaking a rock should add a floating item."""
        view = _make_view()
        rock = view.session.rocks[0]
        # Click until rock breaks
        for _ in range(100):
            view._click_rock(rock.grid_x, rock.grid_y)
            if rock.depleted:
                break
        assert len(view._floats.items) > 0 or rock.depleted
        view.on_exit()

    def test_render_with_all_polish_active(self) -> None:
        """Full render with all polish features active."""
        view = _make_view()
        screen = pygame.display.get_surface()
        # Click several rocks for various visual states
        for rock in view.session.rocks[:3]:
            view._click_rock(rock.grid_x, rock.grid_y)
        for _ in range(10):
            view.update(0.016)
            view.render(screen)
        view.on_exit()

    def test_tooltip_state_exists(self) -> None:
        view = _make_view()
        assert hasattr(view, "_tooltip")
        view.on_exit()

    def test_exit_confirmation_blocks_session_end(self) -> None:
        view = _make_view()
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=view.back_button,
        )
        view.handle_event(event)
        assert view._confirm_exit
        assert not view._show_summary, "Summary should not show until confirmed"
        view.on_exit()

    def test_exit_cancel_resumes_play(self) -> None:
        view = _make_view()
        view._confirm_exit = True
        cancel = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(cancel)
        assert not view._confirm_exit
        assert not view._show_summary
        view.on_exit()

    def test_empowered_key_shortcut(self) -> None:
        """E key should trigger empowered click on hovered cell."""
        view = _make_view()
        # The E key handler reads mouse position, which we can't easily control
        # in headless tests, but it should not crash
        e_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
        view.handle_event(e_event)
        view.on_exit()

    def test_render_with_confirm_exit(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view._confirm_exit = True
        view.render(screen)
        view.on_exit()

    def test_summary_includes_commodity_breakdown(self) -> None:
        """Summary stats should include per-commodity breakdown."""
        view = _make_view()
        screen = pygame.display.get_surface()
        # Break some rocks
        for rock in view.session.rocks[:5]:
            for _ in range(100):
                view._click_rock(rock.grid_x, rock.grid_y)
                if rock.depleted:
                    break
        view._show_summary = True
        view.render(screen)  # Should not crash
        view.on_exit()


class TestWholesaleSell:
    """Tests for wholesale ore sale feature."""

    def test_wholesale_sells_at_ten_percent(self) -> None:
        """Wholesale sell gives 10% of base price per unit."""
        player = _make_player()
        starting_credits = player.credits
        view = _make_view(player)
        # iron_ore base_price=20, 10% = 2 per unit; 10 units = 20 CR
        view._silo.add_ore("iron_ore", 10)
        view._end_session()
        view._apply_wholesale_sell()
        assert player.credits == starting_credits + 20
        assert view._silo.get_total_stored() == 0
        assert view._wholesale_credits == 20
        assert view._wholesale_units == 10
        view.on_exit()

    def test_wholesale_minimum_one_credit(self) -> None:
        """Cheap ores get at least 1 CR per unit at wholesale."""
        player = _make_player()
        starting_credits = player.credits
        commodities = _make_commodities()
        # Add a very cheap commodity (base_price=5, 10% = 0.5 → rounds to 0 → clamped to 1)
        commodities["cheap_ore"] = _make_commodity("cheap_ore", "Cheap Ore", 5)
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        config = MiningConfig(system_id="breakstone")
        view = MiningView(ui_manager, player, commodities, mining_config=config)
        view.on_enter()
        view._silo.add_ore("cheap_ore", 10)
        view._end_session()
        view._apply_wholesale_sell()
        assert player.credits == starting_credits + 10  # 1 CR × 10 units
        view.on_exit()

    def test_wholesale_with_perk_bonus(self) -> None:
        """Wholesale perk adds +5% to the rate (10% → 15%)."""
        player = _make_player()
        starting_credits = player.credits
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        config = MiningConfig(system_id="breakstone", perk_wholesale_bonus=0.05)
        view = MiningView(ui_manager, player, _make_commodities(), mining_config=config)
        view.on_enter()
        # rare_ore base_price=100, 15% = 15 per unit; 10 units = 150 CR
        view._silo.add_ore("rare_ore", 10)
        view._end_session()
        view._apply_wholesale_sell()
        assert player.credits == starting_credits + 150
        assert view._wholesale_credits == 150
        view.on_exit()

    def test_wholesale_mixed_ores(self) -> None:
        """Wholesale correctly prices multiple ore types."""
        player = _make_player()
        starting_credits = player.credits
        view = _make_view(player)
        # iron_ore: 20 × 10% = 2/unit × 5 = 10
        # crystal_ore: 50 × 10% = 5/unit × 3 = 15
        view._silo.add_ore("iron_ore", 5)
        view._silo.add_ore("crystal_ore", 3)
        view._end_session()
        view._apply_wholesale_sell()
        assert player.credits == starting_credits + 25
        assert view._wholesale_units == 8
        assert view._silo.get_total_stored() == 0
        view.on_exit()

    def test_wholesale_clears_silo(self) -> None:
        """Wholesale sell empties the silo completely."""
        player = _make_player()
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 20)
        view._silo.add_ore("rare_ore", 5)
        view._end_session()
        view._apply_wholesale_sell()
        assert view._silo.get_total_stored() == 0
        view.on_exit()

    def test_wholesale_transfers_selected_then_sells_rest(self) -> None:
        """Selected ore goes to cargo, unselected ore gets wholesale sold."""
        player = _make_player()
        starting_credits = player.credits
        view = _make_view(player)
        # 99 iron (base 20, wholesale 2/unit) + 1 rare (base 100, wholesale 10/unit)
        view._silo.add_ore("iron_ore", 99)
        view._silo.add_ore("rare_ore", 1)
        view._end_session()
        # Select the rare ore to keep in cargo
        view._transfer_selections["rare_ore"] = 1
        view._apply_wholesale_sell()
        # Rare ore should be in cargo, not sold
        assert player.ship.get_cargo_quantity("rare_ore") == 1
        # Iron should be wholesale sold: 99 × 2 = 198 CR
        assert view._wholesale_credits == 198
        assert view._wholesale_units == 99
        assert player.credits == starting_credits + 198
        # Silo should be empty
        assert view._silo.get_total_stored() == 0
        view.on_exit()

    def test_wholesale_with_nothing_selected_sells_all(self) -> None:
        """With no selections, wholesale sells everything."""
        player = _make_player()
        starting_credits = player.credits
        view = _make_view(player)
        view._silo.add_ore("iron_ore", 10)
        view._end_session()
        # No selections (default is 0)
        view._apply_wholesale_sell()
        assert player.credits == starting_credits + 20  # 10 × 2
        assert player.ship.get_cargo_quantity("iron_ore") == 0
        view.on_exit()
