"""
Trading interface view.

Buy and sell commodities at the current system's market.
Features dimmed animated background, panel glow borders, and transaction particles.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar
from spacegame.engine.fonts import FONT_BODY, FONT_HEADING, FONT_LG, FONT_MD, get_font
from spacegame.engine.particles import COLLECT_SPARKLE, ParticleConfig, ParticlePool
from spacegame.engine.sprites import get_sprite_manager, res_scale
from spacegame.models.commodity import Commodity
from spacegame.models.faction import get_tariff_modifier
from spacegame.models.market import Market
from spacegame.models.player import Player
from spacegame.models.system import StarSystem
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT
from spacegame.views.table_widget import ColumnDef, TableWidget

# Red flash for failed transactions
FAIL_FLASH = ParticleConfig(
    count=8,
    speed_min=20,
    speed_max=60,
    life_min=0.2,
    life_max=0.5,
    color_start=(220, 50, 50),
    color_end=(150, 30, 30),
    alpha_start=200,
    alpha_end=0,
    size_start=2.0,
    size_end=0.5,
    gravity=0.0,
    spread=360.0,
    glow=True,
)

# Trend text colors (supply/demand-based)
_TREND_COLORS: dict[str, tuple[int, int, int]] = {
    "Very Low": Colors.GREEN,
    "Low": (100, 200, 130),
    "Normal": Colors.TEXT_SECONDARY,
    "High": Colors.YELLOW,
    "Very High": Colors.RED,
}

# Price history trend display
_HISTORY_TREND_DISPLAY: dict[str, tuple[str, tuple[int, int, int]]] = {
    "rising": ("\u25b2 Rising", Colors.GREEN),
    "falling": ("\u25bc Falling", Colors.RED),
    "stable": ("- Stable", Colors.TEXT_SECONDARY),
}


class TradingView(BaseView):
    """Trading interface for buying and selling commodities."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        systems: dict[str, StarSystem],
        commodities: dict[str, Commodity],
        activity_registry=None,
        active_events: Optional[dict] = None,
        price_history=None,
        black_market_name: Optional[str] = None,
        smuggling_contract_manager=None,
        politics_manager=None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.systems = systems
        self.commodities = commodities
        self.market: Optional[Market] = None
        self.activity_registry = activity_registry
        self.active_events: dict = active_events or {}
        self.price_history = price_history
        self.smuggling_contracts = smuggling_contract_manager
        self.politics_manager = politics_manager

        # Black market mode — resolved dynamically in on_enter()
        self._black_market_name: Optional[str] = black_market_name
        self._black_market_mode: bool = False
        self._has_black_market: bool = black_market_name is not None

        # Trading tutorial state (driven by player.dialogue_flags)
        self._tutorial_narration_font = get_font("narration", FONT_BODY)

        # PT-M: first-time tip overlay
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

        # UI state
        self.selected_commodity: Optional[str] = None
        self.quantity_input: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.transaction_message: str = ""
        self.message_timer: float = 0.0
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_HEADING)
        self.header_font = get_font("header", FONT_LG)
        self.info_font = get_font("dialogue", FONT_MD)

        # Table widgets (created in _create_ui, rendered manually)
        self.market_table: Optional[TableWidget] = None
        self.cargo_table: Optional[TableWidget] = None
        self._market_commodity_ids: list[str] = []
        self._cargo_commodity_ids: list[str] = []

        # pygame_gui buttons
        self.buy_button: Optional[pygame_gui.elements.UIButton] = None
        self.buy_max_button: Optional[pygame_gui.elements.UIButton] = None
        self.sell_button: Optional[pygame_gui.elements.UIButton] = None
        self.sell_max_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.refuel_button: Optional[pygame_gui.elements.UIButton] = None
        self.rest_button: Optional[pygame_gui.elements.UIButton] = None
        self.sell_all_button: Optional[pygame_gui.elements.UIButton] = None
        self.mine_button: Optional[pygame_gui.elements.UIButton] = None
        self.activity_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.talk_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.pending_npc_id: Optional[str] = None
        self.black_market_button: Optional[pygame_gui.elements.UIButton] = None
        self.hide_cargo_button: Optional[pygame_gui.elements.UIButton] = None
        self.retrieve_cargo_button: Optional[pygame_gui.elements.UIButton] = None
        self._contract_buttons: list[pygame_gui.elements.UIButton] = []
        self._displayed_contracts: list = []  # SmugglingContract list

        # Animated background (dimmed)
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=30)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(120)

        # Trade reputation: once per landing
        self._trade_rep_awarded: bool = False

        # Sprite manager for commodity icons
        self._sprite_mgr = get_sprite_manager()
        self._commodity_icons: dict[str, Optional[pygame.Surface]] = {}

        # Particles
        self.particles = ParticlePool(100)

    def on_enter(self) -> None:
        super().on_enter()
        self._trade_rep_awarded = False
        self._maybe_show_tip()
        logger.info(f"Entered trading at {self.player.current_system_id}")

    def _maybe_show_tip(self) -> None:
        """PT-M: first-time trading view tip."""
        if self.player is None:
            return
        if self.player.dialogue_flags.get("seen_tip_trading", False):
            return
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip = FirstTimeTipOverlay(
            title="Trading",
            body=(
                "Prices shift by system. Buy low in one port, sell high in "
                "another. The LEG column flags restricted goods: R is "
                "restricted here, ! is outright illegal."
            ),
            on_dismiss=self._mark_trading_tip_seen,
        )

    def _mark_trading_tip_seen(self) -> None:
        if self.player is not None:
            self.player.dialogue_flags["seen_tip_trading"] = True

        current_system = self.systems[self.player.current_system_id]
        all_commodities = list(self.commodities.values())
        self.market = Market(current_system, all_commodities, self.player.game_day)
        self.market.initialize_stock(current_system, all_commodities)

        # Resolve black market access for current system
        from spacegame.models.smuggling import get_black_market_name

        system_id = self.player.current_system_id
        # Underworld Contacts skill grants black market access at all stations
        has_contacts = self.player.progression.get_bonus("underworld_contacts") > 0
        if has_contacts or self.player.has_black_market_access(system_id):
            self._black_market_name = get_black_market_name(system_id)
            self._has_black_market = self._black_market_name is not None
        else:
            self._black_market_name = None
            self._has_black_market = False
        self._black_market_mode = False

        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        # Market table — fixed-column widget (not pygame_gui).
        # LEG (legality) is a dedicated narrow column showing "R" or "!"
        # for restricted/illegal cargo. Sprint 3c flagged the prior design
        # (text suffix appended to commodity name) as overflow-prone — 44
        # of 61 commodities could not show their RESTRICTED label within
        # the name column budget. A badge column keeps the marker visible
        # regardless of name length.
        self.market_table = TableWidget(
            rect=pygame.Rect(scale_x(20), scale_y(100), scale_x(620), scale_y(400)),
            columns=[
                ColumnDef("COMMODITY", scale_x(240), "left"),
                ColumnDef("LEG", scale_x(35), "center"),
                ColumnDef("PRICE", scale_x(85), "right"),
                ColumnDef("STOCK", scale_x(60), "right"),
                ColumnDef("WT", scale_x(40), "right"),
                ColumnDef("TREND", scale_x(120), "left"),
            ],
            font=self.info_font,
            header_font=self.header_font,
        )

        # Cargo table
        self.cargo_table = TableWidget(
            rect=pygame.Rect(WINDOW_WIDTH - scale_x(420), scale_y(120), scale_x(400), scale_y(380)),
            columns=[
                ColumnDef("ITEM", scale_x(130), "left"),
                ColumnDef("QTY", scale_x(50), "right"),
                ColumnDef("COST", scale_x(100), "right"),
                ColumnDef("P/L", scale_x(100), "right"),
            ],
            font=self.info_font,
            header_font=self.header_font,
            empty_message="Empty Cargo Hold",
        )

        self._refresh_tables()

        self.quantity_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(scale_x(650), scale_y(150), scale_x(100), scale_y(40)),
            manager=self.ui_manager,
        )
        self.quantity_input.set_text("1")

        self.buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(200), scale_x(100), scale_y(36)),
            text="[B] BUY",
            manager=self.ui_manager,
        )
        self.buy_max_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(240), scale_x(100), scale_y(36)),
            text="[M] MAX BUY",
            manager=self.ui_manager,
        )
        self.sell_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(284), scale_x(100), scale_y(36)),
            text="[S] SELL",
            manager=self.ui_manager,
        )
        self.sell_max_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(324), scale_x(100), scale_y(36)),
            text="[X] MAX SELL",
            manager=self.ui_manager,
        )
        self.refuel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(368), scale_x(100), scale_y(36)),
            text="[R] REFUEL",
            manager=self.ui_manager,
        )
        self.rest_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(408), scale_x(100), scale_y(36)),
            text="[T] REST",
            manager=self.ui_manager,
        )
        self.sell_all_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(650), scale_y(452), scale_x(100), scale_y(36)),
            text="[A] SELL ALL",
            manager=self.ui_manager,
        )

        # Activity and NPC buttons have moved to StationHubView
        self.activity_buttons.clear()
        self.talk_buttons.clear()

        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(650),
                WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60),
                scale_x(100),
                scale_y(40),
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        # Hidden compartment transfer buttons (when upgrade installed)
        if self.player.hidden_compartment:
            self.hide_cargo_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    WINDOW_WIDTH - scale_x(420), scale_y(510), scale_x(95), scale_y(28)
                ),
                text="HIDE \u2192",
                manager=self.ui_manager,
            )
            self.retrieve_cargo_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    WINDOW_WIDTH - scale_x(320), scale_y(510), scale_x(95), scale_y(28)
                ),
                text="\u2190 RETRIEVE",
                manager=self.ui_manager,
            )

        # Black market toggle (only shown when player has access)
        if self._has_black_market:
            self.black_market_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(scale_x(650), scale_y(496), scale_x(100), scale_y(36)),
                text="BLACK MKT",
                manager=self.ui_manager,
            )

    def _destroy_ui(self) -> None:
        # Tables are plain objects — no .kill() needed
        self.market_table = None
        self.cargo_table = None

        for elem in [
            self.quantity_input,
            self.buy_button,
            self.buy_max_button,
            self.sell_button,
            self.sell_max_button,
            self.refuel_button,
            self.rest_button,
            self.sell_all_button,
            self.mine_button,
            self.back_button,
            self.black_market_button,
            self.hide_cargo_button,
            self.retrieve_cargo_button,
        ]:
            if elem:
                elem.kill()
        for btn in self.activity_buttons.values():
            btn.kill()
        self.activity_buttons.clear()
        for btn in self.talk_buttons.values():
            btn.kill()
        self.talk_buttons.clear()
        for btn in self._contract_buttons:
            btn.kill()
        self._contract_buttons.clear()

    def _build_market_rows(self) -> tuple[list[list[str | tuple[str, tuple]]], list[str]]:
        """Build market table rows and parallel commodity ID list."""
        from spacegame.models.commodity import Legality

        rows: list[list[str | tuple[str, tuple]]] = []
        ids: list[str] = []
        system_id = self.player.current_system_id

        # Use market's filtered commodity list (regional availability)
        market_commodities = self.market.commodities if self.market else self.commodities

        for commodity_id, commodity in market_commodities.items():
            # Skip quest items (base_price=0) from market display
            if commodity.base_price <= 0:
                continue
            if self._black_market_mode:
                price = self._get_black_market_buy_price(commodity_id)
            else:
                price = self.market.get_price(commodity_id)
            weight = commodity.volume_per_unit

            # Prefer price history trend over supply/demand trend
            has_trend_skill = self.player.progression.get_bonus("trend_visibility") > 0
            if not has_trend_skill:
                trend_text = "?"
                trend_color = Colors.TEXT_SECONDARY
            elif self.price_history:
                history_trend = self.price_history.get_trend(system_id, commodity_id)
                trend_text, trend_color = _HISTORY_TREND_DISPLAY.get(
                    history_trend, ("- Stable", Colors.TEXT_SECONDARY)
                )
            else:
                report = self.market.get_market_report(commodity_id)
                trend_text = report["trend"]
                trend_color = _TREND_COLORS.get(trend_text, Colors.TEXT_SECONDARY)

            # Legality: name is colored to match risk; LEG column carries
            # the shape-based indicator ("R"/"!") so the signal survives
            # name-column truncation and colorblind profiles (per
            # ui_design_standards.md principle 6). The smugglers_eye skill
            # is reflected in the LEG cell by an emphatic marker.
            has_smugglers_eye = self.player.progression.get_bonus("smugglers_eye") > 0
            name_display: str | tuple[str, tuple] = commodity.name
            leg_display: str | tuple[str, tuple] = ""
            if commodity.legality == Legality.RESTRICTED:
                name_display = (commodity.name, Colors.YELLOW)
                leg_display = ("R*" if has_smugglers_eye else "R", Colors.YELLOW)
            elif commodity.legality == Legality.ILLEGAL:
                name_display = (commodity.name, Colors.RED)
                leg_display = ("!*" if has_smugglers_eye else "!", Colors.RED)

            # Specialty indicator (shows player where the good deals are)
            report = self.market.get_market_report(commodity_id)
            if report.get("is_specialty_export"):
                trend_text = "BUY HERE"
                trend_color = Colors.GREEN
            elif report.get("is_specialty_import"):
                trend_text = "SELL HERE"
                trend_color = Colors.YELLOW

            # trade_instinct skill: show estimated profit margin next to specialty
            has_trade_instinct = self.player.progression.get_bonus("trade_instinct") > 0
            if has_trade_instinct and (
                report.get("is_specialty_export") or report.get("is_specialty_import")
            ):
                base = report.get("base_price", 0)
                if base > 0 and price > 0:
                    margin_pct = (
                        int(((base - price) / price) * 100)
                        if report.get("is_specialty_export")
                        else int(((price - base) / base) * 100)
                    )
                    if margin_pct > 0:
                        trend_text += f" (~{margin_pct}%)"

            # Stock display
            stock = self.market.get_stock(commodity_id)
            base_stock = self.market.get_base_stock(commodity_id)
            if base_stock > 0:
                stock_color = (
                    Colors.GREEN
                    if stock > base_stock * 0.5
                    else (Colors.YELLOW if stock > 0 else Colors.RED)
                )
                stock_text: str | tuple[str, tuple] = (f"{stock}/{base_stock}", stock_color)
            else:
                stock_text = "-"

            # Player impact indicator on price
            player_mod = 0.0
            try:
                raw = self.market._player_supply_demand.get(commodity_id, 0.0)
                if isinstance(raw, (int, float)):
                    player_mod = raw
            except (AttributeError, TypeError):
                pass
            if abs(player_mod) >= 0.01:
                pct = int(player_mod * 100)
                if pct > 0:
                    price_display: str | tuple[str, tuple] = (
                        f"{price:,} CR (+{pct}%)",
                        Colors.RED,
                    )
                else:
                    price_display = (f"{price:,} CR ({pct}%)", Colors.GREEN)
            else:
                price_display = f"{price:,} CR"

            rows.append(
                [
                    name_display,
                    leg_display,
                    price_display,
                    stock_text,
                    str(weight),
                    (trend_text, trend_color),
                ]
            )
            ids.append(commodity_id)

        return rows, ids

    def _build_cargo_rows(self) -> tuple[list[list[str | tuple[str, tuple]]], list[str]]:
        """Build cargo table rows and parallel commodity ID list."""
        rows: list[list[str | tuple[str, tuple]]] = []
        ids: list[str] = []

        for commodity_id, quantity in self.player.ship.current_cargo.items():
            commodity = self.commodities[commodity_id]
            avg_cost = self.player.ship.get_average_purchase_price(commodity_id)

            # Profit/loss vs current market sell price
            if self.market and avg_cost > 0:
                sell_price = self.market.get_sell_price(commodity_id)
                delta = sell_price - avg_cost
                if delta > 0:
                    pnl_display: str | tuple[str, tuple] = (f"+{delta * quantity:,}", Colors.GREEN)
                elif delta < 0:
                    pnl_display = (f"{delta * quantity:,}", Colors.RED)
                else:
                    pnl_display = ("0", Colors.TEXT_SECONDARY)
            else:
                pnl_display = ("-", Colors.TEXT_SECONDARY)

            rows.append(
                [
                    commodity.name,
                    str(quantity),
                    f"{avg_cost:,} CR",
                    pnl_display,
                ]
            )
            ids.append(commodity_id)

        return rows, ids

    def _get_commodity_icon(self, commodity_id: str) -> Optional[pygame.Surface]:
        """Get a cached commodity icon surface, scaled to fit table rows."""
        if commodity_id not in self._commodity_icons:
            # Scale=1 gives native 16x16, which fits nicely in 26px row height
            self._commodity_icons[commodity_id] = self._sprite_mgr.get_commodity_icon(
                commodity_id, scale=res_scale(1)
            )
        return self._commodity_icons.get(commodity_id)

    def _build_row_icons(self, commodity_ids: list[str]) -> list[Optional[pygame.Surface]]:
        """Build icon list matching row order for table widget."""
        return [self._get_commodity_icon(cid) for cid in commodity_ids]

    def _refresh_tables(self) -> None:
        """Rebuild data for both tables."""
        if self.market_table:
            rows, ids = self._build_market_rows()
            self.market_table.set_data(rows, row_icons=self._build_row_icons(ids))
            self._market_commodity_ids = ids

        if self.cargo_table:
            rows, ids = self._build_cargo_rows()
            self.cargo_table.set_data(rows, row_icons=self._build_row_icons(ids))
            self._cargo_commodity_ids = ids

        # Sprint 5b follow-up: pre-emptive disable of Buy/Sell when the
        # action cannot succeed, with a tooltip explaining why. Replaces
        # most click-then-error paths per ui_design_standards.md.
        self._refresh_button_states()

    def _refresh_button_states(self) -> None:
        """Enable or disable Buy/Sell/Max buttons based on current state.

        Disabled buttons carry a ``tool_tip_text`` that surfaces the reason
        on hover. This preempts the click-then-error pattern for the most
        common failure modes (no permit, no selection, out of stock, can't
        afford, hold's full, nothing to sell).
        """
        if self.buy_button:
            reason = self._why_cannot_buy()
            if reason is not None:
                self.buy_button.disable()
                self.buy_button.tool_tip_text = reason
                if self.buy_max_button:
                    self.buy_max_button.disable()
                    self.buy_max_button.tool_tip_text = reason
            else:
                self.buy_button.enable()
                self.buy_button.tool_tip_text = None
                if self.buy_max_button:
                    self.buy_max_button.enable()
                    self.buy_max_button.tool_tip_text = None

        if self.sell_button:
            reason = self._why_cannot_sell()
            if reason is not None:
                self.sell_button.disable()
                self.sell_button.tool_tip_text = reason
                if self.sell_max_button:
                    self.sell_max_button.disable()
                    self.sell_max_button.tool_tip_text = reason
            else:
                self.sell_button.enable()
                self.sell_button.tool_tip_text = None
                if self.sell_max_button:
                    self.sell_max_button.enable()
                    self.sell_max_button.tool_tip_text = None

    def _why_cannot_buy(self) -> Optional[str]:
        """Return an in-voice reason Buy is disabled, or None if valid."""
        if not self._has_trade_permit():
            return "No trade permit here."
        commodity_id = self._get_selected_market_commodity()
        if not commodity_id:
            return "Pick a commodity."
        commodity = self.commodities.get(commodity_id)
        if commodity is None:
            return "Pick a commodity."
        if self.market.get_stock(commodity_id) <= 0:
            return "Out of stock."
        # Can we afford one unit at current price?
        if self._black_market_mode:
            price = self._get_black_market_buy_price(commodity_id)
        else:
            price = self._get_adjusted_buy_price(commodity_id, 1)
        if self.player.credits < price:
            return "Can't afford it."
        # Is there cargo space for one unit?
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        if not self.player.ship.can_carry(commodity_id, 1, commodity_volumes):
            return "Hold's full."
        return None

    def _why_cannot_sell(self) -> Optional[str]:
        """Return an in-voice reason Sell is disabled, or None if valid."""
        if not self._has_trade_permit():
            return "No trade permit here."
        commodity_id = self._get_selected_cargo_commodity()
        if not commodity_id:
            return "Pick something from your cargo."
        qty = self.player.ship.get_cargo_quantity(commodity_id)
        if qty <= 0:
            return "Nothing of that kind aboard."
        return None

    def _get_selected_market_commodity(self) -> Optional[str]:
        if not self.market_table:
            return None
        idx = self.market_table.get_selected_index()
        if idx is not None and idx < len(self._market_commodity_ids):
            return self._market_commodity_ids[idx]
        return None

    def _get_selected_cargo_commodity(self) -> Optional[str]:
        if not self.cargo_table:
            return None
        idx = self.cargo_table.get_selected_index()
        if idx is not None and idx < len(self._cargo_commodity_ids):
            return self._cargo_commodity_ids[idx]
        return None

    def _get_faction_tariff(self) -> float:
        """Get the tariff modifier for the current system's faction."""
        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        if not faction_id:
            return 0.0
        return get_tariff_modifier(self.player.get_reputation(faction_id))

    def _get_route_bonus(self) -> float:
        """Get trade route efficiency bonus for current route."""
        if not self.player.previous_system_id:
            return 0.0
        return self.player.trade_route_tracker.get_efficiency_bonus(
            self.player.previous_system_id, self.player.current_system_id
        )

    def _get_adjusted_buy_price(self, commodity_id: str, quantity: int) -> int:
        base_price = self.market.get_price(commodity_id)
        discount = self.player.progression.get_bonus("buy_price_reduction")
        discount += self.player.ship.get_crew_bonus("buy_price_reduction")
        discount += self._get_route_bonus()
        # Faction perk buy discount
        if self.politics_manager:
            discount += self.politics_manager.get_perk_bonus(
                self.player, self.player.current_system_id, "buy_price_bonus"
            )
        tariff = self._get_faction_tariff()
        # Leadership tariff reduction only reduces penalties, not discounts
        if tariff > 0:
            tariff = max(0.0, tariff - self.player.progression.get_bonus("tariff_reduction"))
        adjusted = base_price * (1.0 - discount + tariff)
        return max(1, int(adjusted))

    def _get_adjusted_sell_price(self, commodity_id: str) -> int:
        base_price = self.market.get_sell_price(commodity_id)
        bonus = self.player.progression.get_bonus("sell_price_bonus")
        bonus += self.player.ship.get_crew_bonus("sell_price_bonus")
        bonus += self._get_route_bonus()
        # Faction perk sell bonus
        if self.politics_manager:
            bonus += self.politics_manager.get_perk_bonus(
                self.player, self.player.current_system_id, "sell_price_bonus"
            )
        tariff = self._get_faction_tariff()
        # Leadership tariff reduction only reduces penalties, not discounts
        if tariff > 0:
            tariff = max(0.0, tariff - self.player.progression.get_bonus("tariff_reduction"))
        adjusted = base_price * (1.0 + bonus - tariff)
        return max(1, int(adjusted))

    def _apply_trade_reputation(self) -> None:
        """Apply reputation change once per landing after a successful trade."""
        if self._trade_rep_awarded:
            return
        self._trade_rep_awarded = True

        from spacegame.config import REP_PER_TRADE
        from spacegame.data_loader import get_data_loader

        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        if not faction_id:
            return

        # Leadership bonus to reputation gains
        rep_bonus = int(self.player.progression.get_bonus("reputation_gain_bonus"))
        rep_gain = REP_PER_TRADE + rep_bonus
        # Faction Ambassador: double all rep gains
        ambassador_lvl = self.player.progression.get_bonus("faction_rep_multiplier")
        if ambassador_lvl > 0:
            rep_gain = int(rep_gain * (1.0 + ambassador_lvl))

        dl = get_data_loader()

        if self.politics_manager:
            # Centralized spillover handles rival penalty
            changes = self.politics_manager.apply_reputation_with_spillover(
                self.player, faction_id, rep_gain
            )
            for fid, amt in changes:
                faction = dl.get_faction(fid)
                fname = faction.name if faction else fid
                sign = "+" if amt > 0 else ""
                self._show_message(f"{sign}{amt} {fname}")
        else:
            # Fallback: direct reputation change (no spillover)
            self.player.modify_reputation(faction_id, rep_gain)
            faction = dl.get_faction(faction_id)
            if faction:
                self._show_message(f"+{rep_gain} {faction.name}")

    def _has_trade_permit(self) -> bool:
        """Check if the player has a trade permit for the current system's faction."""
        if self._black_market_mode:
            return True  # Black market bypasses trade permits
        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        if not faction_id:
            return True  # Unassigned system — no permit needed
        return self.player.has_trade_permit(faction_id)

    def _toggle_black_market_mode(self) -> None:
        """Toggle between normal trading and black market mode."""
        self._black_market_mode = not self._black_market_mode
        if self.black_market_button:
            self.black_market_button.set_text("NORMAL" if self._black_market_mode else "BLACK MKT")
        self._refresh_tables()
        self._refresh_contract_buttons()

    def _refresh_contract_buttons(self) -> None:
        """Rebuild smuggling contract accept buttons for black market mode."""
        # Clear old buttons
        for btn in self._contract_buttons:
            btn.kill()
        self._contract_buttons.clear()
        self._displayed_contracts.clear()

        if not self._black_market_mode or not self.smuggling_contracts:
            return

        system_id = self.player.current_system_id

        # Generate contracts if needed
        self.smuggling_contracts.generate_contracts(
            system_id, self.player.game_day, self.player.progression.level
        )

        available = self.smuggling_contracts.get_available_contracts(system_id)
        active = self.smuggling_contracts.get_active_contracts()

        # Show available contracts as accept buttons
        base_y = 540
        for i, contract in enumerate(available[:3]):
            already_active = contract.id in [c.id for c in active]
            label = (
                f"{contract.commodity_id}: {contract.quantity}x → "
                f"{contract.destination_system} | {contract.payment} CR"
            )
            if already_active:
                label = f"[ACTIVE] {label}"
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, base_y + i * 30, 500, 26),
                text=label,
                manager=self.ui_manager,
            )
            if already_active:
                btn.disable()
            self._contract_buttons.append(btn)
            self._displayed_contracts.append(contract)

    def _handle_contract_accept(self, button_index: int) -> None:
        """Accept a smuggling contract."""
        if not self.smuggling_contracts:
            return
        if button_index >= len(self._displayed_contracts):
            return

        contract = self._displayed_contracts[button_index]
        success, msg = self.smuggling_contracts.accept_contract(
            contract.id, accepted_day=self.player.game_day
        )
        self._show_message(msg if not success else f"Contract accepted: {contract.client_name}")
        self._refresh_contract_buttons()

    def _execute_hide_cargo(self) -> None:
        """Move selected cargo to hidden hold."""
        if not self.player.hidden_compartment:
            return
        commodity_id = self._get_selected_cargo_commodity()
        if not commodity_id:
            self._show_message("Select cargo to hide")
            return
        try:
            quantity = int(self.quantity_input.get_text())
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            quantity = 1

        # Check player has enough in main hold
        main_qty = self.player.ship.get_cargo_quantity(commodity_id)
        quantity = min(quantity, main_qty)
        if quantity <= 0:
            self._show_message("No cargo to hide")
            return

        success, msg = self.player.hidden_compartment.add_to_hidden(commodity_id, quantity)
        if success:
            self.player.ship.remove_cargo(commodity_id, quantity)
            self._refresh_tables()
        self._show_message(msg)

    def _execute_retrieve_cargo(self) -> None:
        """Move cargo from hidden hold back to main hold."""
        if not self.player.hidden_compartment:
            return
        # Find first hidden cargo item (or use selected)
        commodity_id = self._get_selected_cargo_commodity()
        if not commodity_id and self.player.hidden_compartment.hidden_cargo:
            commodity_id = next(iter(self.player.hidden_compartment.hidden_cargo))
        if not commodity_id:
            self._show_message("No hidden cargo to retrieve")
            return
        try:
            quantity = int(self.quantity_input.get_text())
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            quantity = 1

        hidden_qty = self.player.hidden_compartment.hidden_cargo.get(commodity_id, 0)
        quantity = min(quantity, hidden_qty)
        if quantity <= 0:
            self._show_message(f"No {commodity_id} in hidden hold")
            return

        success, msg = self.player.hidden_compartment.remove_from_hidden(commodity_id, quantity)
        if success:
            self.player.ship.add_cargo(commodity_id, quantity, 0)
            self._refresh_tables()
        self._show_message(msg)

    def _get_black_market_buy_price(self, commodity_id: str) -> int:
        """Get buy price in black market mode (modifier-based, no tariff)."""
        from spacegame.models.smuggling import get_black_market_price_modifier

        base_price = self.market.get_price(commodity_id)
        commodity = self.commodities.get(commodity_id)
        if not commodity:
            return base_price
        modifier = get_black_market_price_modifier(commodity.legality)
        return max(1, int(base_price * (1.0 + modifier)))

    def _get_black_market_sell_price(self, commodity_id: str) -> int:
        """Get sell price in black market mode (modifier-based, no tariff)."""
        from spacegame.models.smuggling import get_black_market_price_modifier

        base_price = self.market.get_sell_price(commodity_id)
        commodity = self.commodities.get(commodity_id)
        if not commodity:
            return base_price
        modifier = get_black_market_price_modifier(commodity.legality)
        # Commerce skill: black_market_sell_bonus increases sell prices
        modifier += self.player.progression.get_bonus("black_market_sell_bonus")
        return max(1, int(base_price * (1.0 + modifier)))

    def _execute_buy(self) -> None:
        if not self._has_trade_permit():
            self._show_message("You need a bill of landing to trade here")
            return

        commodity_id = self._get_selected_market_commodity()
        if not commodity_id:
            self._show_message("Select an item from MARKET PRICES list first")
            return

        try:
            quantity = int(self.quantity_input.get_text())
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            self._show_message("Enter a valid quantity to buy")
            return

        # Check stock availability
        stock = self.market.get_stock(commodity_id)
        if stock > 0 and quantity > stock:
            quantity = stock
        elif stock == 0 and self.market.get_base_stock(commodity_id) > 0:
            self._show_message("Out of stock. Check back tomorrow.")
            get_audio_manager().play_sfx("trade_fail")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, FAIL_FLASH
            )
            return

        if self._black_market_mode:
            price_per_unit = self._get_black_market_buy_price(commodity_id)
        else:
            price_per_unit = self._get_adjusted_buy_price(commodity_id, quantity)
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}

        success, msg = self.player.buy_commodity(
            commodity_id, quantity, price_per_unit, commodity_volumes
        )
        self._show_message(msg)

        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, COLLECT_SPARKLE
            )
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            if not self._black_market_mode:
                self._apply_trade_reputation()
            self.market.record_buy(commodity_id, quantity)
            self.market.deplete_stock(commodity_id, quantity)
            self._refresh_tables()
        else:
            get_audio_manager().play_sfx("trade_fail")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, FAIL_FLASH
            )

    def _execute_sell(self) -> None:
        if not self._has_trade_permit():
            self._show_message("You need a bill of landing to trade here")
            return

        commodity_id = self._get_selected_cargo_commodity()
        if not commodity_id:
            self._show_message("Select an item from YOUR CARGO list first")
            return

        try:
            quantity = int(self.quantity_input.get_text())
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            self._show_message("Enter a valid quantity to sell")
            return

        if self._black_market_mode:
            price_per_unit = self._get_black_market_sell_price(commodity_id)
        else:
            price_per_unit = self._get_adjusted_sell_price(commodity_id)

        # First-trade bonus: double profit on literal first sale
        first_trade_bonus = False
        if self.player.dialogue_flags.get("first_trade_bonus_available"):
            price_per_unit = int(
                price_per_unit * 1.5
            )  # 50% bonus (not full double to stay balanced)
            first_trade_bonus = True

        success, msg = self.player.sell_commodity(commodity_id, quantity, price_per_unit)
        self._show_message(msg)

        if success:
            if first_trade_bonus:
                self.player.dialogue_flags["first_trade_bonus_available"] = False
                self._show_message("Beginner's luck! Premium price on your first sale.")
            get_audio_manager().play_sfx("trade_sell")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, COLLECT_SPARKLE
            )
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            if not self._black_market_mode:
                self._apply_trade_reputation()
            self.market.record_sell(commodity_id, quantity)
            self._refresh_tables()
        else:
            get_audio_manager().play_sfx("trade_fail")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, FAIL_FLASH
            )

    def _execute_buy_max(self) -> None:
        if not self._has_trade_permit():
            self._show_message("You need a bill of landing to trade here")
            return

        commodity_id = self._get_selected_market_commodity()
        if not commodity_id:
            self._show_message("Select an item from MARKET PRICES list first")
            return

        commodity = self.commodities[commodity_id]
        if self._black_market_mode:
            price_per_unit = self._get_black_market_buy_price(commodity_id)
        else:
            price_per_unit = self._get_adjusted_buy_price(commodity_id, 10)
        if price_per_unit <= 0:
            return

        # Max affordable
        max_afford = self.player.credits // price_per_unit

        # Max cargo space
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        available_space = self.player.ship.get_available_cargo(commodity_volumes)
        max_cargo = (
            available_space // commodity.volume_per_unit if commodity.volume_per_unit > 0 else 0
        )

        # Clamp to available stock
        stock = self.market.get_stock(commodity_id)
        if stock > 0:
            quantity = min(max_afford, max_cargo, stock)
        else:
            quantity = min(max_afford, max_cargo)
        if quantity <= 0:
            if stock == 0 and self.market.get_base_stock(commodity_id) > 0:
                self._show_message("Out of stock. Check back tomorrow.")
            elif max_afford <= 0:
                self._show_message("Can't afford it.")
            else:
                self._show_message("Hold's full.")
            get_audio_manager().play_sfx("trade_fail")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, FAIL_FLASH
            )
            return

        # Re-calculate price with actual quantity (bulk discount threshold)
        if self._black_market_mode:
            price_per_unit = self._get_black_market_buy_price(commodity_id)
        else:
            price_per_unit = self._get_adjusted_buy_price(commodity_id, quantity)
        success, msg = self.player.buy_commodity(
            commodity_id, quantity, price_per_unit, commodity_volumes
        )
        self._show_message(msg)

        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, COLLECT_SPARKLE
            )
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            if not self._black_market_mode:
                self._apply_trade_reputation()
            self.market.record_buy(commodity_id, quantity)
            self.market.deplete_stock(commodity_id, quantity)
            self._refresh_tables()
        else:
            get_audio_manager().play_sfx("trade_fail")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, FAIL_FLASH
            )

    def _execute_sell_max(self) -> None:
        commodity_id = self._get_selected_cargo_commodity()
        if not commodity_id:
            self._show_message("Select an item from YOUR CARGO list first")
            return

        quantity = self.player.ship.get_cargo_quantity(commodity_id)
        if quantity <= 0:
            self._show_message("No cargo to sell")
            return

        price_per_unit = self._get_adjusted_sell_price(commodity_id)
        success, msg = self.player.sell_commodity(commodity_id, quantity, price_per_unit)
        self._show_message(msg)

        if success:
            get_audio_manager().play_sfx("trade_sell")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, COLLECT_SPARKLE
            )
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            self._apply_trade_reputation()
            self.market.record_sell(commodity_id, quantity)
            self._refresh_tables()

    def _execute_refuel(self) -> None:
        fuel_needed = self.player.ship.max_fuel - self.player.ship.current_fuel
        if fuel_needed == 0:
            self._show_message("Fuel tank is full")
            return

        try:
            quantity = int(self.quantity_input.get_text())
            if quantity <= 0:
                raise ValueError()
            quantity = min(quantity, fuel_needed)
        except ValueError:
            quantity = fuel_needed

        fuel_price = self.market.get_price("fuel")
        # Free fuel perk
        if self.politics_manager and self.politics_manager.has_perk(
            self.player, self.player.current_system_id, "free_fuel"
        ):
            fuel_price = 0
        success, msg = self.player.refuel_ship(quantity, fuel_price)
        if success:
            get_audio_manager().play_sfx("trade_refuel")
        self._show_message(msg)

    def _execute_sell_all(self) -> None:
        """Sell all cargo at current market prices."""
        if not self._has_trade_permit():
            self._show_message("You need a bill of landing to trade here")
            return
        cargo = dict(self.player.ship.current_cargo)
        if not cargo:
            self._show_message("No cargo to sell")
            return
        total_credits = 0
        total_items = 0
        for commodity_id, quantity in cargo.items():
            if quantity <= 0:
                continue
            if self._black_market_mode:
                sell_price = self._get_black_market_sell_price(commodity_id)
            else:
                sell_price = self.market.get_sell_price(commodity_id)
            commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
            success, _msg = self.player.sell_commodity(
                commodity_id, quantity, sell_price, commodity_volumes
            )
            if success:
                total_credits += sell_price * quantity
                total_items += quantity
                if not self._black_market_mode:
                    self.market.record_sell(commodity_id, quantity)
        if total_items > 0:
            self._show_message(f"Sold {total_items} items for {total_credits:,} CR")
            get_audio_manager().play_sfx("trade_sell")
            self.particles.emit(
                WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50, COLLECT_SPARKLE
            )
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            self._refresh_tables()

    def _execute_rest(self) -> None:
        current_system = self.systems[self.player.current_system_id]
        rest_cost = current_system.rest_cost

        # Add configurable daily rest fee from balance config
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        rest_fee = int(dl.get_balance_value("economy", "rest_cost_per_day", default=0))
        rest_cost = max(rest_cost, rest_fee)

        success, msg = self.player.rest_at_system(rest_cost)
        self._show_message(msg)

        if success:
            self.market.update_day(self.player.game_day)
            self.market.regenerate_stock()
            self._refresh_tables()

    def _show_message(self, message: str) -> None:
        self.transaction_message = message
        self.message_timer = 3.0
        logger.info(f"Transaction: {message}")

    def handle_event(self, event: pygame.event.Event) -> None:
        # PT-M: first-time tip consumes events while active
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return
        # Route mouse events to table widgets first
        if self.market_table:
            self.market_table.handle_event(event)
        if self.cargo_table:
            self.cargo_table.handle_event(event)

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                self._execute_buy()
                return
            if event.key == pygame.K_m:
                self._execute_buy_max()
                return
            if event.key == pygame.K_s:
                self._execute_sell()
                return
            if event.key == pygame.K_x:
                self._execute_sell_max()
                return
            if event.key == pygame.K_r:
                self._execute_refuel()
                return
            if event.key == pygame.K_t:
                self._execute_rest()
                return
            if event.key == pygame.K_a:
                self._execute_sell_all()
                return
            if event.key == pygame.K_TAB:
                # Toggle focus between market and cargo tables
                if self.market_table and self.cargo_table:
                    if self.market_table._selected_index >= 0:
                        # Switch to cargo table
                        self.cargo_table._selected_index = 0
                        self.market_table._selected_index = -1
                    else:
                        # Switch to market table
                        self.market_table._selected_index = 0
                        self.cargo_table._selected_index = -1
                return
            if event.key == pygame.K_ESCAPE:
                self.next_state = GameState.STATION_HUB
                return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.buy_button:
                self._execute_buy()
            elif event.ui_element == self.buy_max_button:
                self._execute_buy_max()
            elif event.ui_element == self.sell_button:
                self._execute_sell()
            elif event.ui_element == self.sell_max_button:
                self._execute_sell_max()
            elif event.ui_element == self.refuel_button:
                self._execute_refuel()
            elif event.ui_element == self.rest_button:
                self._execute_rest()
            elif event.ui_element == self.sell_all_button:
                self._execute_sell_all()
            elif event.ui_element == self.mine_button:
                logger.info("Opening mining mini-game")
                self.next_state = GameState.MINING
            elif event.ui_element == self.back_button:
                self.next_state = GameState.STATION_HUB
            elif event.ui_element == self.black_market_button:
                self._toggle_black_market_mode()
            elif event.ui_element == self.hide_cargo_button:
                self._execute_hide_cargo()
            elif event.ui_element == self.retrieve_cargo_button:
                self._execute_retrieve_cargo()
            else:
                # Check contract accept buttons
                for i, btn in enumerate(self._contract_buttons):
                    if event.ui_element == btn:
                        self._handle_contract_accept(i)
                        break

    def update(self, dt: float) -> None:
        # PT-M: tick tip overlay; clear once dismissed
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None
        self.background.update(dt)
        self.particles.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt

        # Per-frame button state refresh so selection changes and price
        # drift (black-market toggle, tariff updates) reflect immediately.
        # Cheap (a few dict lookups); pygame_gui's enable/disable is
        # idempotent for already-matching state.
        self._refresh_button_states()

        # Trading tutorial state machine
        flags = self.player.dialogue_flags
        if (
            flags.get("trading_tutorial_buy_pending")
            and self.player.ship.get_cargo_quantity("food") >= 5
        ):
            flags["trading_tutorial_buy_pending"] = False
            flags["trading_tutorial_sell_pending"] = True
            logger.info("Trading tutorial: buy step complete")

        if flags.get("trading_tutorial_complete") and flags.get("trading_tutorial_sell_pending"):
            flags["trading_tutorial_sell_pending"] = False
            flags["trading_tutorial_just_completed"] = True
            logger.info("Trading tutorial: complete")

    def render(self, screen: pygame.Surface) -> None:
        # Dimmed animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        current_system = self.systems[self.player.current_system_id]

        # Title
        if self._black_market_mode and self._black_market_name:
            title_text = f"{self._black_market_name} - {current_system.name}"
            title_color = Colors.GOLD  # Gold for black market
        else:
            title_text = f"TRADING - {current_system.name}"
            title_color = Colors.TEXT_HIGHLIGHT
        title = self.title_font.render(title_text, True, title_color)
        screen.blit(title, (20, 20))

        # Route bonus indicator
        route_bonus = self._get_route_bonus()
        if route_bonus > 0:
            bonus_pct = int(route_bonus * 100)
            bonus_text = f"Route Bonus: {bonus_pct}%"
            bonus_surf = self.info_font.render(bonus_text, True, Colors.GREEN)
            screen.blit(bonus_surf, (20, 42))

        # Player stats
        stats_y = 55
        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        faction_info = ""
        if faction_id:
            from spacegame.data_loader import get_data_loader

            faction = get_data_loader().get_faction(faction_id)
            if faction:
                tier = self.player.get_reputation_tier(faction_id)
                faction_info = f" | {faction.name}: {tier.value}"
        stats_line = f"Credits: {self.player.credits:,} CR | Day: {self.player.game_day} | Ship: {self.player.ship.name}{faction_info}"
        surf = self.info_font.render(stats_line, True, Colors.TEXT)
        # Truncate if too wide for screen
        if surf.get_width() > WINDOW_WIDTH - 40:
            stats_line = f"Credits: {self.player.credits:,} CR | Day: {self.player.game_day} | {self.player.ship.name}"
            surf = self.info_font.render(stats_line, True, Colors.TEXT)
        screen.blit(surf, (20, stats_y))

        # Active event banner for current system
        event = self.active_events.get(self.player.current_system_id)
        if event and event.is_active(self.player.game_day):
            commodity = self.commodities.get(event.commodity_id)
            commodity_name = commodity.name if commodity else event.commodity_id
            days_left = event.days_remaining(self.player.game_day)
            pct = int((event.price_multiplier - 1.0) * 100)
            sign = "+" if pct >= 0 else ""
            event_text = (
                f"EVENT: {event.event_type.value.upper()}: "
                f"{commodity_name} {sign}{pct}% | {days_left}d remaining"
            )
            event_surf = self.info_font.render(event_text, True, Colors.YELLOW)
            screen.blit(event_surf, (20, 75))
            # Shift section labels down
            market_label_y = 95
        else:
            market_label_y = 75

        # Section labels
        market_label = self.header_font.render("MARKET PRICES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(market_label, (20, market_label_y))

        # Player impact hint (only show when player has had an effect)
        has_impact = False
        if self.market and hasattr(self.market, "_player_supply_demand"):
            has_impact = any(abs(v) >= 0.01 for v in self.market._player_supply_demand.values())
        if has_impact:
            impact_hint = self.info_font.render(
                "Your trades are affecting local prices", True, Colors.TEXT_SECONDARY
            )
            screen.blit(impact_hint, (scale_x(160), market_label_y + scale_y(4)))

        cargo_label = self.header_font.render("YOUR CARGO", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(cargo_label, (WINDOW_WIDTH - scale_x(420), scale_y(75)))

        # Cargo/Fuel status
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        used_cargo = self.player.ship.get_used_cargo(commodity_volumes)
        cargo_text = f"Space: {used_cargo}/{self.player.ship.max_cargo} | Fuel: {self.player.ship.current_fuel}/{self.player.ship.max_fuel}"
        cargo_surf = self.info_font.render(cargo_text, True, Colors.TEXT_SECONDARY)
        screen.blit(cargo_surf, (WINDOW_WIDTH - scale_x(420), scale_y(95)))

        # Table widgets
        if self.market_table:
            self.market_table.render(screen)
        if self.cargo_table:
            self.cargo_table.render(screen)

        # Cargo fill bar
        bar_x = WINDOW_WIDTH - scale_x(420)
        bar_y = scale_y(505)
        bar_w = scale_x(400)
        bar_h = scale_y(8)
        fill_pct = used_cargo / self.player.ship.max_cargo if self.player.ship.max_cargo > 0 else 0
        fill_color = Colors.TEXT_HIGHLIGHT if fill_pct < 0.9 else Colors.RED
        draw_bar(
            screen,
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            used_cargo,
            self.player.ship.max_cargo,
            fill_color,
            show_value=False,
        )

        # Hidden compartment status (when upgrade installed)
        if self.player.hidden_compartment:
            hc = self.player.hidden_compartment
            hidden_text = f"Hidden Hold: {hc.hidden_used}/{hc.hidden_capacity}"
            hidden_surf = self.info_font.render(hidden_text, True, (180, 140, 200))
            screen.blit(hidden_surf, (WINDOW_WIDTH - scale_x(220), bar_y + scale_y(14)))

        # Action label
        action_label = self.header_font.render("Quantity:", True, Colors.TEXT)
        screen.blit(action_label, (scale_x(650), scale_y(120)))

        # Trading tips (normal) or active contracts (black market)
        tip_y = scale_y(520)
        if self._black_market_mode and self.smuggling_contracts:
            active = self.smuggling_contracts.get_active_contracts()
            header = self.header_font.render(
                f"SMUGGLING CONTRACTS ({len(active)}/3 active)", True, Colors.GOLD
            )
            screen.blit(header, (scale_x(20), tip_y))
            # Contract list buttons are rendered by pygame_gui below the header
        else:
            tip_lines = [
                "TRADING TIPS:",
                "- Buy LOW and Sell HIGH",
                "- Prices change when you TRAVEL or REST",
                f"- REST here: {current_system.rest_cost} CR (updates market)",
                "- Use quantity input for partial refueling",
            ]
            for i, tip in enumerate(tip_lines):
                color = Colors.TEXT_HIGHLIGHT if i == 0 else Colors.TEXT_SECONDARY
                tip_surf = self.info_font.render(tip, True, color)
                screen.blit(tip_surf, (scale_x(20), tip_y + i * scale_y(20)))

        # Particles
        self.particles.render(screen)

        # Transaction message
        if self.message_timer > 0:
            msg_color = (
                Colors.SUCCESS
                if any(
                    w in self.transaction_message.lower()
                    for w in ["success", "purchased", "sold", "added"]
                )
                else Colors.ERROR
            )
            msg_surf = self.header_font.render(self.transaction_message, True, msg_color)
            msg_rect = msg_surf.get_rect(
                center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 50)
            )
            screen.blit(msg_surf, msg_rect)

        # Trading tutorial narration (Elena's Lesson)
        self._render_trading_tutorial(screen)

    def _check_trading_tutorial_buy(self, commodity_id: str) -> None:
        """Advance trading tutorial after a successful purchase."""
        if not self.player.dialogue_flags.get("trading_tutorial_buy_pending"):
            return
        if commodity_id == "food" and self.player.ship.get_cargo_quantity("food") >= 5:
            self.player.dialogue_flags["trading_tutorial_buy_pending"] = False
            self.player.dialogue_flags["trading_tutorial_sell_pending"] = True
            logger.info("Trading tutorial: buy step complete (5+ food purchased)")

    def _render_trading_tutorial(self, screen: pygame.Surface) -> None:
        """Render Elena's guided trading narration when tutorial flags are active."""
        if not hasattr(self, "player") or not self.player:
            return
        flags = self.player.dialogue_flags

        # Determine tutorial state from flags
        if flags.get("trading_tutorial_buy_pending"):
            narration = "Five units of food. That's what a mining family eats in a week. Buy it here, bring it to Breakstone."
            speaker = "Elena: "
        elif flags.get("trading_tutorial_sell_pending"):
            narration = "Miners can't grow food underground. What you're carrying is worth more to them than it is to you. Fly."
            speaker = "Elena: "
        elif flags.get("trading_tutorial_just_completed"):
            narration = "Credits in your account. That's how you survive out here. Move things where they're needed."
            speaker = "Elena: "
            # Clear the completion flag after showing it once
            flags["trading_tutorial_just_completed"] = False
        else:
            return  # No active tutorial

        panel_w = WINDOW_WIDTH - scale_x(160)
        panel_h = scale_y(45)
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = scale_y(8)

        from spacegame.engine.draw_utils import draw_panel

        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=220)
        sp_surf = self._tutorial_narration_font.render(speaker, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(sp_surf, (panel_x + 16, panel_y + 12))
        txt_surf = self._tutorial_narration_font.render(narration, True, Colors.TEXT_PRIMARY)
        screen.blit(txt_surf, (panel_x + 16 + sp_surf.get_width(), panel_y + 12))

    def render_top(self, screen: pygame.Surface) -> None:
        """PT-M: draw the first-time tip above pygame_gui elements."""
        if self._first_time_tip is not None:
            self._first_time_tip.render(screen)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
