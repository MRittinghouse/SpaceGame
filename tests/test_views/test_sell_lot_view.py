"""SA-B5: SellLotView lifecycle, eligibility, and form behavior tests.

Covers acceptance #13 (lifecycle + tier-locked + empty state + tip
overlay) and #14 (declared appraisal validation, reserve-pct clamping,
fee preview, confirm gating, error-state UI).
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import (
    LISTING_RESERVE_PCT_DEFAULT,
    LISTING_RESERVE_PCT_MAX,
    LISTING_RESERVE_PCT_MIN,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    GameState,
)
from spacegame.constants.flags import (
    auction_first_listing_created,
    seen_first_listing_tip,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import compute_listing_fee
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.sell_lot_view import SellLotView


def _make_view_env(
    *,
    credits: int = 100_000,
    stellaris_rep: int = 10,
    has_cargo: bool = True,
    has_parts: bool = False,
) -> tuple[pygame_gui.UIManager, Player]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Captain Seller",
        credits=credits,
        current_system_id="stellaris_port",
        ship=ship,
    )
    player.faction_reputation["stellaris_commerce_guild"] = stellaris_rep
    if has_cargo:
        ship.add_cargo("axiom_circuit", 4, price_per_unit=1500)
    if has_parts:
        player.parts_inventory["mining_laser_mk2"] = 2
    return manager, player


def _make_view(manager: pygame_gui.UIManager, player: Player) -> SellLotView:
    return SellLotView(ui_manager=manager, player=player)


class TestLifecycle:
    def test_construct(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        assert view.active

    def test_on_exit_destroys_ui(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        # At least one UI element after on_enter.
        view.on_exit()
        # Confirm and back are nulled out after destruction.
        assert view.confirm_button is None
        assert view.back_button is None

    def test_render_does_not_raise(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.render_top(screen)


class TestFirstTimeTip:
    def test_tip_fires_on_first_entry(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        assert view._tip_overlay is not None

    def test_tip_suppressed_on_second_entry(self) -> None:
        manager, player = _make_view_env()
        player.dialogue_flags[seen_first_listing_tip()] = True
        view = _make_view(manager, player)
        view.on_enter()
        assert view._tip_overlay is None


class TestTierGate:
    def test_tier_locked_when_apprentice(self) -> None:
        manager, player = _make_view_env(stellaris_rep=-10)
        view = _make_view(manager, player)
        view.on_enter()
        assert view.is_tier_locked()

    def test_confirm_disabled_when_tier_locked(self) -> None:
        manager, player = _make_view_env(stellaris_rep=-10)
        view = _make_view(manager, player)
        view.on_enter()
        assert not view.can_confirm_listing()


class TestEligibilityFiltering:
    def test_lists_cargo_commodities(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        items = view.get_eligible_items()
        assert any(i["item_id"] == "axiom_circuit" for i in items)

    def test_lists_parts(self) -> None:
        manager, player = _make_view_env(has_parts=True)
        view = _make_view(manager, player)
        view.on_enter()
        items = view.get_eligible_items()
        assert any(i["item_id"] == "mining_laser_mk2" and i["item_kind"] == "part" for i in items)

    def test_excludes_unlocked_modules(self) -> None:
        manager, player = _make_view_env()
        # unlocked_modules is the boss-drop legendary set; if present it
        # should NOT appear in eligible items.
        if hasattr(player, "unlocked_modules"):
            player.unlocked_modules.add("legendary_kings_repeater")  # type: ignore[union-attr]
        view = _make_view(manager, player)
        view.on_enter()
        items = view.get_eligible_items()
        for i in items:
            assert i["item_id"] != "legendary_kings_repeater"


class TestEmptyState:
    def test_renders_empty_inventory_voice_line(self) -> None:
        manager, player = _make_view_env(has_cargo=False)
        view = _make_view(manager, player)
        # Install voice templates the engine usually wires in.
        view.set_voice_templates(
            {
                "consigned_lot_lines": {
                    "empty_inventory": 'Velo: "There is nothing on consignment from your hand today."'
                }
            }
        )
        view.on_enter()
        empty_line = view.empty_state_line()
        assert "consignment" in empty_line.lower() or "nothing" in empty_line.lower()


class TestFormBehavior:
    def test_default_reserve_pct(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        assert abs(view.reserve_pct - LISTING_RESERVE_PCT_DEFAULT) < 1e-6

    def test_reserve_clamps_to_floor(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.set_reserve_pct(0.1)
        assert view.reserve_pct == LISTING_RESERVE_PCT_MIN

    def test_reserve_clamps_to_ceiling(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.set_reserve_pct(0.99)
        assert view.reserve_pct == LISTING_RESERVE_PCT_MAX

    def test_appraisal_must_be_positive(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.set_declared_appraisal(0)
        assert view.declared_appraisal == 0
        assert not view.can_confirm_listing()

    def test_fee_preview_updates_with_appraisal(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.set_declared_appraisal(50_000)
        assert view.fee_preview() == compute_listing_fee(50_000)


class TestConfirmFlow:
    def _select_first_eligible(self, view: SellLotView) -> None:
        items = view.get_eligible_items()
        assert items, "expected at least one eligible item"
        view.select_item(items[0]["item_kind"], items[0]["item_id"])

    def test_confirm_creates_listing(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        self._select_first_eligible(view)
        view.set_declared_appraisal(8000)
        view.set_reserve_pct(0.7)
        ok, msg = view.confirm_listing()
        assert ok, msg
        assert player.dialogue_flags.get(auction_first_listing_created()) is True
        assert view.next_state == GameState.AUCTION

    def test_confirm_fires_on_listing_created_callback_on_first_listing(self) -> None:
        """on_listing_created callback fires exactly once on first listing (AC #14)."""
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        self._select_first_eligible(view)
        view.set_declared_appraisal(8000)
        calls: list[int] = []
        view.on_listing_created = lambda: calls.append(1)
        ok, _ = view.confirm_listing()
        assert ok
        assert len(calls) == 1
        # Second listing does not re-fire the callback.
        items = view.get_eligible_items()
        if items:
            view.select_item(items[0]["item_kind"], items[0]["item_id"])
            view.set_declared_appraisal(8000)
            view.confirm_listing()
        assert len(calls) == 1

    def test_confirm_fails_with_error_message(self) -> None:
        manager, player = _make_view_env(credits=10)  # too poor to pay fee.
        view = _make_view(manager, player)
        view.on_enter()
        self._select_first_eligible(view)
        view.set_declared_appraisal(8000)
        ok, msg = view.confirm_listing()
        assert not ok
        # Error UI is surfaced via view.error_message.
        assert view.error_message
        assert msg


class TestNavigation:
    def test_back_returns_to_auction(self) -> None:
        manager, player = _make_view_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.go_back()
        assert view.next_state == GameState.AUCTION
