"""Investment view — per-system passive income management.

Displays current investment status and allows investing, upgrading, and
collecting accumulated returns.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    Colors,
    GameState,
)
from spacegame.views.base_view import BaseView
from spacegame.models.player import Player
from spacegame.models.investment import InvestmentManager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import FontCache
from spacegame.utils.logger import logger


# Layout
PANEL_W = 520
PANEL_H = 420
PANEL_X = WINDOW_WIDTH // 2 - PANEL_W // 2
PANEL_Y = WINDOW_HEIGHT // 2 - PANEL_H // 2
CONTENT_X = PANEL_X + 30
CONTENT_W = PANEL_W - 60
BUTTON_W = 200
BUTTON_H = 40
ACCENT_COLOR = (200, 180, 80)  # Gold


class InvestmentView(BaseView):
    """Per-system investment management view.

    Shows investment status, allows invest/upgrade/collect actions.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        investment_manager: InvestmentManager,
        system_id: str,
    ) -> None:
        """Initialize investment view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player.
            investment_manager: Investment manager with templates and active state.
            system_id: Current system ID.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.investment_manager = investment_manager
        self.system_id = system_id
        self.next_state: Optional[GameState] = None

        # Message feedback
        self.message: Optional[str] = None
        self.message_timer: float = 0.0
        self.message_color: tuple[int, int, int] = Colors.TEXT_PRIMARY

        # Fonts
        self.title_font = FontCache.get(36)
        self.subtitle_font = FontCache.get(22)
        self.label_font = FontCache.get(26)
        self.value_font = FontCache.get(24)
        self.tier_font = FontCache.get(30)
        self.msg_font = FontCache.get(22)

        # UI element refs
        self.invest_button: Optional[pygame_gui.elements.UIButton] = None
        self.upgrade_button: Optional[pygame_gui.elements.UIButton] = None
        self.collect_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Background
        self.background = AnimatedBackground(
            "station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=8888
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        """Activate view and create UI."""
        super().on_enter()
        logger.info(f"Entered investment view for {self.system_id}")
        self.message = None
        self.message_timer = 0.0
        self._create_ui()

    def on_exit(self) -> None:
        """Deactivate and clean up."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create action buttons based on current investment state."""
        self._destroy_ui()

        inv = self.investment_manager.get_investment(self.system_id)
        template = self.investment_manager.get_template(self.system_id)
        btn_x = PANEL_X + PANEL_W // 2 - BUTTON_W // 2
        btn_y = PANEL_Y + PANEL_H - 140

        if not inv and template:
            # No investment — show Invest button
            tier_1 = template.get_tier(1)
            cost = tier_1.cost if tier_1 else 1000
            self.invest_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                text=f"INVEST ({cost:,} CR)",
                manager=self.ui_manager,
            )
        elif inv and template:
            # Has investment — show Upgrade and Collect
            next_tier = template.get_tier(inv.tier + 1)
            if next_tier:
                self.upgrade_button = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                    text=f"UPGRADE ({next_tier.cost:,} CR)",
                    manager=self.ui_manager,
                )

            if inv.accumulated_returns > 0:
                self.collect_button = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(btn_x, btn_y + 46, BUTTON_W, BUTTON_H),
                    text="COLLECT RETURNS",
                    manager=self.ui_manager,
                )

        # Back button
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                btn_x, PANEL_Y + PANEL_H - 50, BUTTON_W, BUTTON_H,
            ),
            text="BACK",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        for elem in [self.invest_button, self.upgrade_button,
                     self.collect_button, self.back_button]:
            if elem:
                elem.kill()
        self.invest_button = None
        self.upgrade_button = None
        self.collect_button = None
        self.back_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button clicks."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.invest_button:
                self._execute_invest()
            elif event.ui_element == self.upgrade_button:
                self._execute_upgrade()
            elif event.ui_element == self.collect_button:
                self._execute_collect()
            elif event.ui_element == self.back_button:
                self._request_back()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._request_back()

    def update(self, dt: float) -> None:
        """Update background and message timer."""
        self.background.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

    def render(self, screen: pygame.Surface) -> None:
        """Render investment interface."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel
        draw_panel(screen, (PANEL_X, PANEL_Y, PANEL_W, PANEL_H), alpha=230)
        # Gold accent bar
        pygame.draw.rect(screen, ACCENT_COLOR, (PANEL_X, PANEL_Y, PANEL_W, 3))

        template = self.investment_manager.get_template(self.system_id)
        inv = self.investment_manager.get_investment(self.system_id)

        if not template:
            title = self.title_font.render(
                "NO INVESTMENT AVAILABLE", True, Colors.TEXT_SECONDARY
            )
            screen.blit(
                title,
                (PANEL_X + PANEL_W // 2 - title.get_width() // 2, PANEL_Y + 20),
            )
            return

        # Title — investment name
        title = self.title_font.render(
            template.name.upper(), True, ACCENT_COLOR
        )
        screen.blit(
            title,
            (PANEL_X + PANEL_W // 2 - title.get_width() // 2, PANEL_Y + 12),
        )

        # Description
        desc = self.subtitle_font.render(
            template.description, True, Colors.TEXT_SECONDARY
        )
        screen.blit(
            desc,
            (PANEL_X + PANEL_W // 2 - desc.get_width() // 2, PANEL_Y + 42),
        )

        y = PANEL_Y + 80

        if inv:
            # Current tier
            tier_info = template.get_tier(inv.tier)
            tier_label = self.tier_font.render(
                f"Tier {inv.tier}", True, ACCENT_COLOR
            )
            screen.blit(tier_label, (CONTENT_X, y))
            y += 34

            # Daily returns
            if tier_info:
                if tier_info.returns_type == "commodity" and tier_info.returns_commodity:
                    ret_text = f"{tier_info.daily_return_amount} {tier_info.returns_commodity.replace('_', ' ')}/day"
                else:
                    ret_text = f"{tier_info.daily_return_amount:,} CR/day"
                returns_label = self.label_font.render(
                    f"Daily Returns: {ret_text}", True, Colors.TEXT_PRIMARY
                )
                screen.blit(returns_label, (CONTENT_X, y))
                y += 30

            # Accumulated returns
            acc = inv.accumulated_returns
            if acc > 0:
                if tier_info and tier_info.returns_type == "commodity" and tier_info.returns_commodity:
                    acc_text = f"{acc} {tier_info.returns_commodity.replace('_', ' ')}"
                else:
                    acc_text = f"{acc:,} CR"
                acc_label = self.label_font.render(
                    f"Uncollected: {acc_text}", True, Colors.GREEN
                )
            else:
                acc_label = self.label_font.render(
                    "Uncollected: None", True, Colors.TEXT_SECONDARY
                )
            screen.blit(acc_label, (CONTENT_X, y))
            y += 30

            # Halted status
            if inv.halted_until_day > 0:
                halt_label = self.value_font.render(
                    "Returns halted by disaster event", True, Colors.RED
                )
                screen.blit(halt_label, (CONTENT_X, y))
                y += 26

        else:
            # No investment yet — show tier overview
            no_inv = self.label_font.render(
                "No investment at this system.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(no_inv, (CONTENT_X, y))
            y += 34

            # Tier overview table
            for tier_info in template.tiers:
                if tier_info.returns_type == "commodity" and tier_info.returns_commodity:
                    ret = f"{tier_info.daily_return_amount} {tier_info.returns_commodity.replace('_', ' ')}/day"
                else:
                    ret = f"{tier_info.daily_return_amount:,} CR/day"
                row = self.value_font.render(
                    f"Tier {tier_info.tier}: {tier_info.cost:,} CR → {ret}",
                    True, Colors.TEXT_PRIMARY,
                )
                screen.blit(row, (CONTENT_X + 10, y))
                y += 24

        # Credits display
        credits_y = PANEL_Y + PANEL_H - 160
        credits_text = self.value_font.render(
            f"Credits: {self.player.credits:,} CR", True, Colors.TEXT_SECONDARY
        )
        screen.blit(credits_text, (CONTENT_X, credits_y))

        # Message
        if self.message and self.message_timer > 0:
            msg_surf = self.msg_font.render(self.message, True, self.message_color)
            screen.blit(
                msg_surf,
                (
                    PANEL_X + PANEL_W // 2 - msg_surf.get_width() // 2,
                    PANEL_Y + PANEL_H - 30,
                ),
            )

    # === Actions ===

    def _execute_invest(self) -> None:
        """Attempt to create a new investment."""
        success, msg = self.investment_manager.invest(
            self.player.credits, self.system_id, self.player.game_day
        )
        if success:
            tier_info = self.investment_manager.get_template(self.system_id).get_tier(1)
            self.player.deduct_credits(tier_info.cost)
            self.player.investments_owned += 1
            self.message = msg
            self.message_color = Colors.GREEN
            self.message_timer = 3.0
            self._create_ui()
            logger.info(msg)
        else:
            self.message = msg
            self.message_color = Colors.RED
            self.message_timer = 3.0

    def _execute_upgrade(self) -> None:
        """Attempt to upgrade existing investment."""
        inv = self.investment_manager.get_investment(self.system_id)
        if not inv:
            return
        template = self.investment_manager.get_template(self.system_id)
        next_tier = template.get_tier(inv.tier + 1) if template else None

        success, msg = self.investment_manager.upgrade(
            self.player.credits, self.system_id
        )
        if success and next_tier:
            self.player.deduct_credits(next_tier.cost)
            self.message = msg
            self.message_color = Colors.GREEN
            self.message_timer = 3.0
            self._create_ui()
            logger.info(msg)
        else:
            self.message = msg
            self.message_color = Colors.RED
            self.message_timer = 3.0

    def _execute_collect(self) -> None:
        """Attempt to collect accumulated returns."""
        success, msg, credits, commodity, qty = self.investment_manager.collect_returns(
            self.system_id
        )
        if success:
            if credits > 0:
                self.player.add_credits(credits)
            if commodity and qty and qty > 0:
                self.player.ship.add_cargo(commodity, qty)
            self.message = msg
            self.message_color = Colors.GREEN
            self.message_timer = 3.0
            self._create_ui()
            logger.info(msg)
        else:
            self.message = msg
            self.message_color = Colors.RED
            self.message_timer = 3.0

    def _request_back(self) -> None:
        """Navigate back to station hub."""
        self.next_state = GameState.STATION_HUB

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state
