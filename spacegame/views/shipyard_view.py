"""
Shipyard view for purchasing and managing ship upgrades.
Features styled upgrade cards, purchase particles, tab glow states, procedural ship silhouette.
"""

import pygame
import pygame_gui
import math
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE, ParticleConfig

# Green flash for purchase
PURCHASE_FLASH = ParticleConfig(
    count=15,
    speed_min=30,
    speed_max=80,
    life_min=0.3,
    life_max=0.8,
    color_start=(80, 255, 120),
    color_end=(40, 180, 80),
    alpha_start=255,
    alpha_end=0,
    size_start=2.5,
    size_end=0.5,
    gravity=-15.0,
    spread=360.0,
    glow=True,
)


class ShipyardView(BaseView):
    """Ship upgrade shop UI with visual enhancements."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        all_upgrades: Dict[str, ShipUpgrade],
        upgrade_manager: ShipUpgradeManager,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.all_upgrades = all_upgrades
        self.upgrade_manager = upgrade_manager
        self.next_state: Optional[GameState] = None

        self.selected_upgrade_idx: int = 0
        self.viewing: str = "shop"

        # Fonts
        self.title_font = pygame.font.Font(None, 36)
        self.header_font = pygame.font.Font(None, 28)
        self.info_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.buy_button: Optional[pygame_gui.elements.UIButton] = None
        self.uninstall_button: Optional[pygame_gui.elements.UIButton] = None
        self.shop_tab: Optional[pygame_gui.elements.UIButton] = None
        self.installed_tab: Optional[pygame_gui.elements.UIButton] = None

        # Message
        self.message: str = ""
        self.message_timer: float = 0.0

        # Visual
        self.background = AnimatedBackground("industrial", WINDOW_WIDTH, WINDOW_HEIGHT, seed=90)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(100)

        self.particles = ParticlePool(100)
        self._glow_time = 0.0

        # Procedural ship silhouette
        self._ship_surf = self._generate_ship_silhouette()

    def _generate_ship_silhouette(self) -> pygame.Surface:
        """Generate a simple procedural ship polygon."""
        surf = pygame.Surface((120, 60), pygame.SRCALPHA)
        # Simple arrow/ship shape
        points = [(10, 30), (40, 10), (110, 30), (40, 50)]
        pygame.draw.polygon(surf, (60, 80, 120), points)
        pygame.draw.polygon(surf, (100, 130, 180), points, 2)
        # Engine glow
        pygame.draw.circle(surf, (80, 150, 255, 120), (15, 30), 5)
        return surf

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        btn_x = WINDOW_WIDTH // 2 - 200
        self.shop_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, 70, 120, 35), text="Shop", manager=self.ui_manager
        )
        self.installed_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + 130, 70, 120, 35),
            text="Installed",
            manager=self.ui_manager,
        )
        self.buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 200, WINDOW_HEIGHT - 120, 170, 40),
            text="Buy & Install",
            manager=self.ui_manager,
        )
        self.uninstall_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 200, WINDOW_HEIGHT - 70, 170, 40),
            text="Uninstall",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - 60, 150, 40),
            text="Back",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [
            self.back_button,
            self.buy_button,
            self.uninstall_button,
            self.shop_tab,
            self.installed_tab,
        ]:
            if btn:
                btn.kill()

    def _get_shop_list(self) -> List[ShipUpgrade]:
        installed_ids = {u.id for u in self.upgrade_manager.installed}
        return [u for u in self.all_upgrades.values() if u.id not in installed_ids]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            elif event.ui_element == self.shop_tab:
                self.viewing = "shop"
                self.selected_upgrade_idx = 0
            elif event.ui_element == self.installed_tab:
                self.viewing = "installed"
                self.selected_upgrade_idx = 0
            elif event.ui_element == self.buy_button:
                self._buy_selected()
            elif event.ui_element == self.uninstall_button:
                self._uninstall_selected()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_item_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_upgrade_idx = max(0, self.selected_upgrade_idx - 1)
            elif event.key == pygame.K_DOWN:
                items = self._get_current_list()
                self.selected_upgrade_idx = min(len(items) - 1, self.selected_upgrade_idx + 1)

    def _get_current_list(self):
        if self.viewing == "shop":
            return self._get_shop_list()
        return self.upgrade_manager.installed

    def _handle_item_click(self, pos: tuple) -> None:
        items = self._get_current_list()
        y_start = 130
        for i in range(len(items)):
            rect = pygame.Rect(40, y_start + i * 90, 600, 85)
            if rect.collidepoint(pos):
                self.selected_upgrade_idx = i
                break

    def _buy_selected(self) -> None:
        shop = self._get_shop_list()
        if not shop or self.selected_upgrade_idx >= len(shop):
            return

        upgrade = shop[self.selected_upgrade_idx]

        if not self.player.can_afford(upgrade.price):
            self._show_message(f"Cannot afford {upgrade.name} ({upgrade.price:,} CR)")
            return

        if not self.upgrade_manager.can_install(upgrade):
            self._show_message("No upgrade slots available!")
            return

        self.player.deduct_credits(upgrade.price)
        success, msg = self.upgrade_manager.install(upgrade)
        self._show_message(f"Bought and {msg}" if success else msg)

        if success:
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, PURCHASE_FLASH)

    def _uninstall_selected(self) -> None:
        installed = self.upgrade_manager.installed
        if not installed or self.selected_upgrade_idx >= len(installed):
            return

        upgrade = installed[self.selected_upgrade_idx]
        refund = upgrade.price // 2
        success, msg = self.upgrade_manager.uninstall(upgrade.id)
        if success:
            self.player.add_credits(refund)
            self._show_message(f"{msg} Refunded {refund:,} CR")
            self.selected_upgrade_idx = max(0, self.selected_upgrade_idx - 1)
        else:
            self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("SHIPYARD", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Ship silhouette in header
        screen.blit(self._ship_surf, (WINDOW_WIDTH - 160, 15))

        # Credits and slots
        credits_text = self.info_font.render(
            f"Credits: {self.player.credits:,} CR  |  "
            f"Upgrade Slots: {self.upgrade_manager.slots_used}/{self.upgrade_manager.max_slots}",
            True,
            Colors.TEXT,
        )
        screen.blit(credits_text, credits_text.get_rect(center=(WINDOW_WIDTH // 2, 55)))

        if self.viewing == "shop":
            self._render_shop(screen)
        else:
            self._render_installed(screen)

        # Particles
        self.particles.render(screen)

        # Message
        if self.message_timer > 0:
            color = (
                Colors.SUCCESS
                if "Installed" in self.message or "Bought" in self.message
                else Colors.YELLOW
            )
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(
                msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 140))
            )

    def _render_shop(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("AVAILABLE UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, 110))

        shop = self._get_shop_list()
        y = 140
        for i, upgrade in enumerate(shop):
            rect = pygame.Rect(40, y, 600, 85)
            is_selected = i == self.selected_upgrade_idx
            can_afford = self.player.can_afford(upgrade.price)

            # Styled card with gradient
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if is_selected:
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(28 + 12 * t)
                    g = int(38 + 12 * t)
                    b = int(58 + 12 * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            border_color = Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            name_color = Colors.TEXT if can_afford else Colors.TEXT_SECONDARY
            name = self.info_font.render(upgrade.name, True, name_color)
            screen.blit(name, (rect.x + 10, rect.y + 5))

            price_color = Colors.SUCCESS if can_afford else Colors.RED
            price = self.info_font.render(f"{upgrade.price:,} CR", True, price_color)
            screen.blit(price, (rect.right - price.get_width() - 10, rect.y + 5))

            desc = self.small_font.render(upgrade.description, True, Colors.TEXT_SECONDARY)
            screen.blit(desc, (rect.x + 10, rect.y + 30))

            slot_text = self.small_font.render(f"Slot: {upgrade.slot_type}", True, Colors.BLUE)
            screen.blit(slot_text, (rect.x + 10, rect.y + 50))

            y += 90

        if not shop:
            empty = self.info_font.render("All upgrades installed!", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    def _render_installed(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("INSTALLED UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, 110))

        installed = self.upgrade_manager.installed
        y = 140
        for i, upgrade in enumerate(installed):
            rect = pygame.Rect(40, y, 600, 85)
            is_selected = i == self.selected_upgrade_idx

            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if is_selected:
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(28 + 12 * t)
                    g = int(38 + 12 * t)
                    b = int(58 + 12 * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            border_color = Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            name = self.info_font.render(upgrade.name, True, Colors.TEXT)
            screen.blit(name, (rect.x + 10, rect.y + 5))

            refund = upgrade.price // 2
            refund_text = self.small_font.render(
                f"Refund: {refund:,} CR", True, Colors.TEXT_SECONDARY
            )
            screen.blit(refund_text, (rect.right - refund_text.get_width() - 10, rect.y + 5))

            desc = self.small_font.render(upgrade.description, True, Colors.TEXT_SECONDARY)
            screen.blit(desc, (rect.x + 10, rect.y + 30))

            active = self.small_font.render("ACTIVE", True, Colors.SUCCESS)
            screen.blit(active, (rect.x + 10, rect.y + 50))

            y += 90

        if not installed:
            empty = self.info_font.render("No upgrades installed", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
