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
from spacegame.models.ship import ShipType
from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE, ParticleConfig
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.fonts import FontCache
from spacegame.engine.audio_manager import get_audio_manager

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

# Layout constants
_LIST_X = 40
_LIST_Y = 140
_CARD_W = 600
_CARD_H = 85
_CARD_SPACING = 90
_LIST_BOTTOM = WINDOW_HEIGHT - 155  # Leave room for buttons/messages
_SCROLL_SPEED = 30


class ShipyardView(BaseView):
    """Ship upgrade shop UI with visual enhancements."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        all_upgrades: Dict[str, ShipUpgrade],
        upgrade_manager: ShipUpgradeManager,
        all_ship_types: Optional[Dict[str, "ShipType"]] = None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.all_upgrades = all_upgrades
        self.upgrade_manager = upgrade_manager
        self.all_ship_types = all_ship_types or {}
        self.next_state: Optional[GameState] = None

        self.selected_upgrade_idx: int = 0
        self.viewing: str = "ships"  # Default to ships tab

        # Scrolling
        self._scroll_offset: int = 0

        # Fonts
        self.title_font = FontCache.get(36)
        self.header_font = FontCache.get(28)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.buy_button: Optional[pygame_gui.elements.UIButton] = None
        self.uninstall_button: Optional[pygame_gui.elements.UIButton] = None
        self.ships_tab: Optional[pygame_gui.elements.UIButton] = None
        self.shop_tab: Optional[pygame_gui.elements.UIButton] = None
        self.installed_tab: Optional[pygame_gui.elements.UIButton] = None
        self.buy_ship_button: Optional[pygame_gui.elements.UIButton] = None

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

        # Ship sprite (with procedural fallback)
        self._sprite_mgr = get_sprite_manager()
        self._ship_surf = self._load_ship_sprite()

    def _load_ship_sprite(self) -> pygame.Surface:
        """Load ship sprite or generate procedural fallback."""
        ship_id = self.player.ship.ship_type.id
        sprite = self._sprite_mgr.get_ship_sprite(ship_id, scale=3)
        if sprite:
            return sprite
        # Procedural fallback
        surf = pygame.Surface((120, 60), pygame.SRCALPHA)
        points = [(10, 30), (40, 10), (110, 30), (40, 50)]
        pygame.draw.polygon(surf, (60, 80, 120), points)
        pygame.draw.polygon(surf, (100, 130, 180), points, 2)
        pygame.draw.circle(surf, (80, 150, 255, 120), (15, 30), 5)
        return surf

    def on_enter(self) -> None:
        super().on_enter()
        self._scroll_offset = 0
        self._ship_surf = self._load_ship_sprite()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        btn_x = WINDOW_WIDTH // 2 - 260
        self.ships_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, 70, 120, 35), text="Ships", manager=self.ui_manager
        )
        self.shop_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + 130, 70, 120, 35), text="Upgrades", manager=self.ui_manager
        )
        self.installed_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + 260, 70, 120, 35),
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
        self.buy_ship_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 200, WINDOW_HEIGHT - 120, 170, 40),
            text="Buy Ship",
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
            self.ships_tab,
            self.shop_tab,
            self.installed_tab,
            self.buy_ship_button,
        ]:
            if btn:
                btn.kill()

    def _get_shop_list(self) -> List[ShipUpgrade]:
        installed_ids = {u.id for u in self.upgrade_manager.installed}
        has_market = self.player.has_black_market_access(self.player.current_system_id)
        return [
            u for u in self.all_upgrades.values()
            if u.id not in installed_ids
            and (not u.requires_black_market or has_market)
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            elif event.ui_element == self.ships_tab:
                self.viewing = "ships"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.shop_tab:
                self.viewing = "shop"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.installed_tab:
                self.viewing = "installed"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.buy_button:
                self._buy_selected()
            elif event.ui_element == self.uninstall_button:
                self._uninstall_selected()
            elif event.ui_element == self.buy_ship_button:
                self._buy_selected_ship()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_item_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            self._scroll_offset -= event.y * _SCROLL_SPEED
            self._clamp_scroll()

        elif event.type == pygame.KEYDOWN:
            items = self._get_current_list()
            if event.key == pygame.K_UP:
                self.selected_upgrade_idx = max(0, self.selected_upgrade_idx - 1)
                self._ensure_selected_visible()
            elif event.key == pygame.K_DOWN:
                self.selected_upgrade_idx = min(len(items) - 1, self.selected_upgrade_idx + 1)
                self._ensure_selected_visible()

    def _max_scroll(self) -> int:
        """Maximum scroll offset based on content height."""
        items = self._get_current_list()
        content_height = len(items) * _CARD_SPACING
        visible_height = _LIST_BOTTOM - _LIST_Y
        return max(0, content_height - visible_height)

    def _clamp_scroll(self) -> None:
        """Keep scroll offset within valid bounds."""
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll()))

    def _ensure_selected_visible(self) -> None:
        """Scroll to keep the selected item visible."""
        visible_height = _LIST_BOTTOM - _LIST_Y
        item_top = self.selected_upgrade_idx * _CARD_SPACING
        item_bottom = item_top + _CARD_H

        if item_top < self._scroll_offset:
            self._scroll_offset = item_top
        elif item_bottom > self._scroll_offset + visible_height:
            self._scroll_offset = item_bottom - visible_height

        self._clamp_scroll()

    def _get_ship_list(self) -> list:
        """Get ship types available for purchase, excluding current ship."""
        current_id = self.player.ship.ship_type.id
        return [st for st in self.all_ship_types.values() if st.id != current_id]

    def _get_current_list(self):
        if self.viewing == "ships":
            return self._get_ship_list()
        if self.viewing == "shop":
            return self._get_shop_list()
        return self.upgrade_manager.installed

    def _handle_item_click(self, pos: tuple) -> None:
        items = self._get_current_list()
        for i in range(len(items)):
            card_y = _LIST_Y + i * _CARD_SPACING - self._scroll_offset
            rect = pygame.Rect(_LIST_X, card_y, _CARD_W, _CARD_H)
            if rect.collidepoint(pos) and _LIST_Y <= pos[1] <= _LIST_BOTTOM:
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
            category = self.upgrade_manager.get_category(upgrade.slot_type)
            limit = self.upgrade_manager.get_category_limit(category)
            used = self.upgrade_manager.get_category_used(category)
            self._show_message(f"No {category} slots available! ({used}/{limit})")
            return

        self.player.deduct_credits(upgrade.price)
        success, msg = self.upgrade_manager.install(upgrade)
        self._show_message(f"Bought and {msg}" if success else msg)

        if success:
            get_audio_manager().play_sfx("trade_buy")
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

    def _buy_selected_ship(self) -> None:
        """Purchase the selected ship."""
        ships = self._get_ship_list()
        if not ships or self.selected_upgrade_idx >= len(ships):
            return

        ship_type = ships[self.selected_upgrade_idx]
        success, msg = self.player.swap_ship(ship_type)
        self._show_message(msg)

        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, PURCHASE_FLASH)
            self._ship_surf = self._load_ship_sprite()

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

        # Credits and per-category slot display
        self._render_slot_summary(screen)

        # Show/hide context-sensitive buttons
        if self.buy_button:
            self.buy_button.visible = self.viewing == "shop"
        if self.uninstall_button:
            self.uninstall_button.visible = self.viewing == "installed"
        if self.buy_ship_button:
            self.buy_ship_button.visible = self.viewing == "ships"

        if self.viewing == "ships":
            self._render_ships(screen)
        elif self.viewing == "shop":
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

    def _render_slot_summary(self, screen: pygame.Surface) -> None:
        """Render credits and per-category slot counts."""
        w_used = self.upgrade_manager.get_category_used("weapon")
        w_max = self.upgrade_manager.get_category_limit("weapon")
        d_used = self.upgrade_manager.get_category_used("defense")
        d_max = self.upgrade_manager.get_category_limit("defense")
        u_used = self.upgrade_manager.get_category_used("utility")
        u_max = self.upgrade_manager.get_category_limit("utility")

        slot_text = (
            f"Credits: {self.player.credits:,} CR  |  "
            f"Weapon: {w_used}/{w_max}  "
            f"Defense: {d_used}/{d_max}  "
            f"Utility: {u_used}/{u_max}"
        )
        slot_surf = self.info_font.render(slot_text, True, Colors.TEXT)
        screen.blit(slot_surf, slot_surf.get_rect(center=(WINDOW_WIDTH // 2, 55)))

    def _render_ships(self, screen: pygame.Surface) -> None:
        """Render ship purchase list."""
        current = self.player.ship.ship_type
        header = self.header_font.render(
            f"SHIPS FOR SALE  (Current: {current.name})", True, Colors.TEXT_HIGHLIGHT
        )
        screen.blit(header, (40, 110))

        ships = self._get_ship_list()
        if not ships:
            empty = self.info_font.render("No other ships available.", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))
            return

        self._render_ship_list(screen, ships)

    def _render_shop(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("AVAILABLE UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, 110))

        shop = self._get_shop_list()
        self._render_item_list(screen, shop, show_price=True)

        if not shop:
            empty = self.info_font.render("All upgrades installed!", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    def _render_installed(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("INSTALLED UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, 110))

        installed = self.upgrade_manager.installed
        self._render_item_list(screen, installed, show_price=False)

        if not installed:
            empty = self.info_font.render("No upgrades installed", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    def _render_item_list(
        self,
        screen: pygame.Surface,
        items: list,
        show_price: bool,
    ) -> None:
        """Render a scrollable list of upgrade cards."""
        if not items:
            return

        # Clip to list area
        clip_rect = pygame.Rect(_LIST_X - 2, _LIST_Y, _CARD_W + 4, _LIST_BOTTOM - _LIST_Y)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for i, upgrade in enumerate(items):
            card_y = _LIST_Y + i * _CARD_SPACING - self._scroll_offset
            # Skip cards fully outside visible area
            if card_y + _CARD_H < _LIST_Y or card_y > _LIST_BOTTOM:
                continue

            rect = pygame.Rect(_LIST_X, card_y, _CARD_W, _CARD_H)
            is_selected = i == self.selected_upgrade_idx

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

            # Upgrade icon (small, left of name)
            icon = self._sprite_mgr.get_upgrade_icon(upgrade.id, scale=2)
            icon_offset = 0
            if icon:
                screen.blit(icon, (rect.x + 6, rect.y + 4))
                icon_offset = icon.get_width() + 4

            if show_price:
                can_afford = self.player.can_afford(upgrade.price)
                name_color = Colors.TEXT if can_afford else Colors.TEXT_SECONDARY
                name = self.info_font.render(upgrade.name, True, name_color)
                screen.blit(name, (rect.x + 10 + icon_offset, rect.y + 5))

                price_color = Colors.SUCCESS if can_afford else Colors.RED
                price = self.info_font.render(f"{upgrade.price:,} CR", True, price_color)
                screen.blit(price, (rect.right - price.get_width() - 10, rect.y + 5))

                # Slot category indicator
                category = self.upgrade_manager.get_category(upgrade.slot_type)
                avail = self.upgrade_manager.get_category_available(category)
                slot_color = Colors.TEXT_SECONDARY if avail > 0 else Colors.RED
                slot_text = self.small_font.render(
                    f"Slot: {upgrade.slot_type} ({category} {avail} free)", True, slot_color
                )
                screen.blit(slot_text, (rect.x + 10, rect.y + 50))
            else:
                name = self.info_font.render(upgrade.name, True, Colors.TEXT)
                screen.blit(name, (rect.x + 10 + icon_offset, rect.y + 5))

                refund = upgrade.price // 2
                refund_text = self.small_font.render(
                    f"Refund: {refund:,} CR", True, Colors.TEXT_SECONDARY
                )
                screen.blit(refund_text, (rect.right - refund_text.get_width() - 10, rect.y + 5))

                active = self.small_font.render("ACTIVE", True, Colors.SUCCESS)
                screen.blit(active, (rect.x + 10, rect.y + 50))

            # Truncate description to card width
            desc_text = upgrade.description
            desc = self.small_font.render(desc_text, True, Colors.TEXT_SECONDARY)
            max_desc_w = rect.width - 20
            if desc.get_width() > max_desc_w:
                while len(desc_text) > 3 and desc.get_width() > max_desc_w:
                    desc_text = desc_text[:-1]
                desc_text = desc_text.rstrip() + ".."
                desc = self.small_font.render(desc_text, True, Colors.TEXT_SECONDARY)
            screen.blit(desc, (rect.x + 10, rect.y + 30))

        screen.set_clip(old_clip)

        # Scroll indicator
        max_scroll = self._max_scroll()
        if max_scroll > 0:
            self._render_scrollbar(screen, max_scroll)

    def _render_ship_list(self, screen: pygame.Surface, ships: list) -> None:
        """Render a scrollable list of ship type cards."""
        if not ships:
            return

        clip_rect = pygame.Rect(_LIST_X - 2, _LIST_Y, _CARD_W + 4, _LIST_BOTTOM - _LIST_Y)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        current = self.player.ship.ship_type

        for i, ship_type in enumerate(ships):
            card_y = _LIST_Y + i * _CARD_SPACING - self._scroll_offset
            if card_y + _CARD_H < _LIST_Y or card_y > _LIST_BOTTOM:
                continue

            rect = pygame.Rect(_LIST_X, card_y, _CARD_W, _CARD_H)
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

            # Ship sprite icon
            icon = self._sprite_mgr.get_ship_sprite(ship_type.id, scale=2)
            icon_offset = 0
            if icon:
                screen.blit(icon, (rect.x + 6, rect.y + 8))
                icon_offset = icon.get_width() + 4

            # Name and price (ensure no overlap)
            net_cost = ship_type.purchase_price - current.resale_value
            can_afford = net_cost <= self.player.credits
            name_color = Colors.TEXT if can_afford else Colors.TEXT_SECONDARY

            price_color = Colors.SUCCESS if can_afford else Colors.RED
            price_text = f"{ship_type.purchase_price:,} CR (net: {net_cost:,})"
            price = self.info_font.render(price_text, True, price_color)
            price_x = rect.right - price.get_width() - 10
            screen.blit(price, (price_x, rect.y + 5))

            # Truncate name if it would overlap price
            name_text = f"{ship_type.name}  ({ship_type.ship_class.replace('_', ' ').title()})"
            name_x = rect.x + 10 + icon_offset
            max_name_w = price_x - name_x - 8
            name = self.info_font.render(name_text, True, name_color)
            if name.get_width() > max_name_w and max_name_w > 0:
                # Fall back to just the ship name without class
                name_text = ship_type.name
                name = self.info_font.render(name_text, True, name_color)
            screen.blit(name, (name_x, rect.y + 5))

            # Stats line
            stats_text = (
                f"Cargo: {ship_type.cargo_capacity}  "
                f"Fuel: {ship_type.fuel_capacity}  "
                f"Hull: {ship_type.combat_hull}  "
                f"Shields: {ship_type.combat_shields}  "
                f"W/D/U: {ship_type.weapon_slots}/{ship_type.defense_slots}/{ship_type.utility_slots}"
            )
            stats = self.small_font.render(stats_text, True, Colors.TEXT_SECONDARY)
            screen.blit(stats, (rect.x + 10, rect.y + 30))

            # Description
            desc = self.small_font.render(ship_type.description[:80], True, (80, 90, 110))
            screen.blit(desc, (rect.x + 10, rect.y + 50))

            # Compare indicators (green = better, red = worse)
            if is_selected:
                comparisons = [
                    ("Cargo", ship_type.cargo_capacity, current.cargo_capacity),
                    ("Fuel", ship_type.fuel_capacity, current.fuel_capacity),
                    ("Hull", ship_type.combat_hull, current.combat_hull),
                ]
                comp_x = rect.x + 10
                comp_y = rect.y + 68
                for label, new_val, old_val in comparisons:
                    diff = new_val - old_val
                    if diff > 0:
                        color = Colors.GREEN
                        text = f"{label}: +{diff}"
                    elif diff < 0:
                        color = Colors.RED
                        text = f"{label}: {diff}"
                    else:
                        continue
                    surf = self.small_font.render(text, True, color)
                    screen.blit(surf, (comp_x, comp_y))
                    comp_x += surf.get_width() + 16

        screen.set_clip(old_clip)

        max_scroll = self._max_scroll()
        if max_scroll > 0:
            self._render_scrollbar(screen, max_scroll)

    def _render_scrollbar(self, screen: pygame.Surface, max_scroll: int) -> None:
        """Draw a thin scrollbar on the right edge of the list area."""
        track_x = _LIST_X + _CARD_W + 6
        track_y = _LIST_Y
        track_h = _LIST_BOTTOM - _LIST_Y
        bar_w = 4

        # Track
        pygame.draw.rect(screen, Colors.SCROLLBAR_TRACK, (track_x, track_y, bar_w, track_h))

        # Thumb
        visible_ratio = track_h / (track_h + max_scroll)
        thumb_h = max(20, int(track_h * visible_ratio))
        scroll_ratio = self._scroll_offset / max_scroll if max_scroll > 0 else 0.0
        thumb_y = track_y + int((track_h - thumb_h) * scroll_ratio)
        pygame.draw.rect(
            screen, Colors.SCROLLBAR_THUMB, (track_x, thumb_y, bar_w, thumb_h), border_radius=2
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
