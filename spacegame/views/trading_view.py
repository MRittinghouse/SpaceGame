"""
Trading interface view.

Buy and sell commodities at the current system's market.
Features dimmed animated background, panel glow borders, and transaction particles.
"""

import pygame
import pygame_gui
from typing import Optional
from spacegame.views.base_view import BaseView
from spacegame.views.table_widget import TableWidget, ColumnDef
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.models.system import StarSystem
from spacegame.models.commodity import Commodity
from spacegame.models.market import Market
from spacegame.models.faction import get_tariff_modifier
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE, ParticleConfig

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

# Trend text colors
_TREND_COLORS: dict[str, tuple[int, int, int]] = {
    "Very Low": Colors.GREEN,
    "Low": (100, 200, 130),
    "Normal": Colors.TEXT_SECONDARY,
    "High": Colors.YELLOW,
    "Very High": Colors.RED,
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
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.systems = systems
        self.commodities = commodities
        self.market: Optional[Market] = None
        self.activity_registry = activity_registry
        self.active_events: dict = active_events or {}

        # UI state
        self.selected_commodity: Optional[str] = None
        self.quantity_input: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.transaction_message: str = ""
        self.message_timer: float = 0.0
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = pygame.font.Font(None, 32)
        self.header_font = pygame.font.Font(None, 24)
        self.info_font = pygame.font.Font(None, 20)

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
        self.mine_button: Optional[pygame_gui.elements.UIButton] = None
        self.activity_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.talk_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.pending_npc_id: Optional[str] = None

        # Animated background (dimmed)
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=30)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(120)

        # Particles
        self.particles = ParticlePool(100)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info(f"Entered trading at {self.player.current_system_id}")

        current_system = self.systems[self.player.current_system_id]
        all_commodities = list(self.commodities.values())
        self.market = Market(current_system, all_commodities, self.player.game_day)

        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        # Market table — fixed-column widget (not pygame_gui)
        self.market_table = TableWidget(
            rect=pygame.Rect(20, 100, 500, 400),
            columns=[
                ColumnDef("COMMODITY", 190, "left"),
                ColumnDef("PRICE", 110, "right"),
                ColumnDef("WT", 60, "right"),
                ColumnDef("TREND", 140, "left"),
            ],
            font=self.info_font,
            header_font=self.header_font,
        )

        # Cargo table
        self.cargo_table = TableWidget(
            rect=pygame.Rect(WINDOW_WIDTH - 420, 120, 400, 380),
            columns=[
                ColumnDef("ITEM", 120, "left"),
                ColumnDef("QTY", 45, "right"),
                ColumnDef("SPC", 45, "right"),
                ColumnDef("AVG", 85, "right"),
                ColumnDef("PAID", 105, "right"),
            ],
            font=self.info_font,
            header_font=self.header_font,
            empty_message="Empty Cargo Hold",
        )

        self._refresh_tables()

        self.quantity_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(540, 150, 100, 40), manager=self.ui_manager
        )
        self.quantity_input.set_text("1")

        self.buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 200, 100, 36), text="BUY", manager=self.ui_manager
        )
        self.buy_max_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 240, 100, 36), text="BUY MAX", manager=self.ui_manager
        )
        self.sell_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 284, 100, 36), text="SELL", manager=self.ui_manager
        )
        self.sell_max_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 324, 100, 36), text="SELL MAX", manager=self.ui_manager
        )
        self.refuel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 368, 100, 36), text="REFUEL", manager=self.ui_manager
        )
        self.rest_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, 408, 100, 36), text="REST", manager=self.ui_manager
        )

        self.activity_buttons.clear()
        btn_y = 452
        if self.activity_registry:
            current_system = self.systems[self.player.current_system_id]
            activities = self.activity_registry.get_activities_for_system(
                self.player.current_system_id, current_system.type
            )
            for activity in activities:
                btn = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(540, btn_y, 100, 35),
                    text=activity.button_text,
                    manager=self.ui_manager,
                )
                self.activity_buttons[activity.id] = btn
                btn_y += 40
        elif self.player.current_system_id == "breakstone":
            self.mine_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(540, btn_y, 100, 35), text="MINE", manager=self.ui_manager
            )
            btn_y += 40

        # NPC talk buttons
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        self.talk_buttons.clear()
        npcs_here = dl.get_npcs_at_system(self.player.current_system_id)
        for npc in npcs_here:
            # Truncate name to fit button
            label = f"TALK: {npc.name}"
            if len(label) > 14:
                label = f"TALK: {npc.name.split()[0]}"
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(540, btn_y, 100, 35), text=label, manager=self.ui_manager
            )
            self.talk_buttons[npc.id] = btn
            btn_y += 40

        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(540, btn_y, 100, 40), text="BACK", manager=self.ui_manager
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
            self.mine_button,
            self.back_button,
        ]:
            if elem:
                elem.kill()
        for btn in self.activity_buttons.values():
            btn.kill()
        self.activity_buttons.clear()
        for btn in self.talk_buttons.values():
            btn.kill()
        self.talk_buttons.clear()

    def _build_market_rows(self) -> tuple[list[list[str | tuple[str, tuple]]], list[str]]:
        """Build market table rows and parallel commodity ID list."""
        rows: list[list[str | tuple[str, tuple]]] = []
        ids: list[str] = []

        for commodity_id, commodity in self.commodities.items():
            price = self.market.get_price(commodity_id)
            report = self.market.get_market_report(commodity_id)
            trend = report["trend"]
            weight = commodity.volume_per_unit
            trend_color = _TREND_COLORS.get(trend, Colors.TEXT_SECONDARY)

            rows.append(
                [
                    commodity.name,
                    f"{price:,} CR",
                    str(weight),
                    (trend, trend_color),
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
            volume = quantity * commodity.volume_per_unit
            avg_cost = self.player.ship.get_average_purchase_price(commodity_id)
            total_paid = avg_cost * quantity

            rows.append(
                [
                    commodity.name,
                    str(quantity),
                    str(volume),
                    f"{avg_cost:,} CR",
                    f"{total_paid:,} CR",
                ]
            )
            ids.append(commodity_id)

        return rows, ids

    def _refresh_tables(self) -> None:
        """Rebuild data for both tables."""
        if self.market_table:
            rows, ids = self._build_market_rows()
            self.market_table.set_data(rows)
            self._market_commodity_ids = ids

        if self.cargo_table:
            rows, ids = self._build_cargo_rows()
            self.cargo_table.set_data(rows)
            self._cargo_commodity_ids = ids

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

    def _get_adjusted_buy_price(self, commodity_id: str, quantity: int) -> int:
        base_price = self.market.get_price(commodity_id)
        discount = self.player.progression.get_bonus("buy_price_reduction")
        discount += self.player.ship.get_crew_bonus("buy_price_reduction")
        if quantity >= 10:
            discount += self.player.progression.get_bonus("bulk_discount")
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
        tariff = self._get_faction_tariff()
        # Leadership tariff reduction only reduces penalties, not discounts
        if tariff > 0:
            tariff = max(0.0, tariff - self.player.progression.get_bonus("tariff_reduction"))
        adjusted = base_price * (1.0 + bonus - tariff)
        return max(1, int(adjusted))

    def _apply_trade_reputation(self) -> None:
        """Apply reputation changes after a successful trade."""
        from spacegame.config import REP_PER_TRADE, REP_RIVAL_PENALTY_RATIO
        from spacegame.data_loader import get_data_loader

        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        if not faction_id:
            return

        # Leadership bonus to reputation gains
        rep_bonus = int(self.player.progression.get_bonus("reputation_gain_bonus"))
        rep_gain = REP_PER_TRADE + rep_bonus

        # Gain rep with current system's faction
        self.player.modify_reputation(faction_id, rep_gain)
        dl = get_data_loader()
        faction = dl.get_faction(faction_id)
        if faction:
            self._show_message(f"+{rep_gain} {faction.name}")

            # Lose rep with rival faction
            if faction.rivalry:
                rival_penalty = -int(rep_gain * REP_RIVAL_PENALTY_RATIO)
                if rival_penalty != 0:
                    self.player.modify_reputation(faction.rivalry, rival_penalty)
                    rival = dl.get_faction(faction.rivalry)
                    if rival:
                        self._show_message(f"{rival_penalty} {rival.name}")

    def _has_trade_permit(self) -> bool:
        """Check if the player has a trade permit for the current system's faction."""
        faction_id = self.player.get_faction_for_system(self.player.current_system_id)
        if not faction_id:
            return True  # Unassigned system — no permit needed
        return self.player.has_trade_permit(faction_id)

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

        price_per_unit = self._get_adjusted_buy_price(commodity_id, quantity)
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}

        success, msg = self.player.buy_commodity(
            commodity_id, quantity, price_per_unit, commodity_volumes
        )
        self._show_message(msg)

        if success:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, COLLECT_SPARKLE)
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            self._apply_trade_reputation()
            self._refresh_tables()
        else:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, FAIL_FLASH)

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

        price_per_unit = self._get_adjusted_sell_price(commodity_id)
        success, msg = self.player.sell_commodity(commodity_id, quantity, price_per_unit)
        self._show_message(msg)

        if success:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, COLLECT_SPARKLE)
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            self._apply_trade_reputation()
            self._refresh_tables()
        else:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, FAIL_FLASH)

    def _execute_buy_max(self) -> None:
        if not self._has_trade_permit():
            self._show_message("You need a bill of landing to trade here")
            return

        commodity_id = self._get_selected_market_commodity()
        if not commodity_id:
            self._show_message("Select an item from MARKET PRICES list first")
            return

        commodity = self.commodities[commodity_id]
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

        quantity = min(max_afford, max_cargo)
        if quantity <= 0:
            if max_afford <= 0:
                self._show_message("Not enough credits")
            else:
                self._show_message("Not enough cargo space")
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, FAIL_FLASH)
            return

        # Re-calculate price with actual quantity (bulk discount threshold)
        price_per_unit = self._get_adjusted_buy_price(commodity_id, quantity)
        success, msg = self.player.buy_commodity(
            commodity_id, quantity, price_per_unit, commodity_volumes
        )
        self._show_message(msg)

        if success:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, COLLECT_SPARKLE)
            from spacegame.config import XP_PER_TRADE

            xp_msgs = self.player.progression.add_xp(XP_PER_TRADE)
            for m in xp_msgs:
                self._show_message(m)
            self._apply_trade_reputation()
            self._refresh_tables()
        else:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, FAIL_FLASH)

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
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50, COLLECT_SPARKLE)
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
        success, msg = self.player.refuel_ship(quantity, fuel_price)
        self._show_message(msg)

    def _execute_rest(self) -> None:
        current_system = self.systems[self.player.current_system_id]
        rest_cost = current_system.rest_cost

        success, msg = self.player.rest_at_system(rest_cost)
        self._show_message(msg)

        if success:
            self.market.update_day(self.player.game_day)
            self._refresh_tables()

    def _show_message(self, message: str) -> None:
        self.transaction_message = message
        self.message_timer = 3.0
        logger.info(f"Transaction: {message}")

    def handle_event(self, event: pygame.event.Event) -> None:
        # Route mouse events to table widgets first
        if self.market_table:
            self.market_table.handle_event(event)
        if self.cargo_table:
            self.cargo_table.handle_event(event)

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
            elif event.ui_element == self.mine_button:
                logger.info("Opening mining mini-game")
                self.next_state = GameState.MINING
            elif event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            else:
                for activity_id, btn in self.activity_buttons.items():
                    if event.ui_element == btn:
                        if self.activity_registry:
                            activity = self.activity_registry.get_activity(activity_id)
                            if activity:
                                logger.info(f"Opening activity: {activity.name}")
                                self.next_state = activity.game_state
                        break
                for npc_id, btn in self.talk_buttons.items():
                    if event.ui_element == btn:
                        logger.info(f"Opening dialogue with NPC: {npc_id}")
                        self.pending_npc_id = npc_id
                        self.next_state = GameState.DIALOGUE
                        break

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        # Dimmed animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        current_system = self.systems[self.player.current_system_id]

        # Title
        title = self.title_font.render(
            f"TRADING - {current_system.name}", True, Colors.TEXT_HIGHLIGHT
        )
        screen.blit(title, (20, 20))

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
        stats_text = [
            f"Credits: {self.player.credits:,} CR | Day: {self.player.game_day} | Ship: {self.player.ship.name}{faction_info}",
        ]
        for text in stats_text:
            surf = self.info_font.render(text, True, Colors.TEXT)
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

        cargo_label = self.header_font.render("YOUR CARGO", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(cargo_label, (WINDOW_WIDTH - 420, 75))

        # Cargo/Fuel status
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        used_cargo = self.player.ship.get_used_cargo(commodity_volumes)
        cargo_text = f"Space: {used_cargo}/{self.player.ship.max_cargo} | Fuel: {self.player.ship.current_fuel}/{self.player.ship.max_fuel}"
        cargo_surf = self.info_font.render(cargo_text, True, Colors.TEXT_SECONDARY)
        screen.blit(cargo_surf, (WINDOW_WIDTH - 420, 95))

        # Table widgets
        if self.market_table:
            self.market_table.render(screen)
        if self.cargo_table:
            self.cargo_table.render(screen)

        # Cargo fill bar
        bar_x = WINDOW_WIDTH - 420
        bar_y = 505
        bar_w = 400
        bar_h = 8
        fill_pct = used_cargo / self.player.ship.max_cargo if self.player.ship.max_cargo > 0 else 0
        pygame.draw.rect(screen, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * fill_pct)
        fill_color = Colors.TEXT_HIGHLIGHT if fill_pct < 0.9 else Colors.RED
        pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(screen, Colors.UI_BORDER, (bar_x, bar_y, bar_w, bar_h), 1)

        # Action label
        action_label = self.header_font.render("Quantity:", True, Colors.TEXT)
        screen.blit(action_label, (540, 120))

        # Trading tips
        tip_y = 520
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
            screen.blit(tip_surf, (20, tip_y + i * 20))

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
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
            screen.blit(msg_surf, msg_rect)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
