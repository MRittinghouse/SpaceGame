"""
Shipyard view for purchasing and managing ship upgrades.
Features styled upgrade cards, purchase particles, tab glow states, procedural ship silhouette,
faction/quest gating, and the Mk1→Mk3 enhancement system with tuning specialization.
"""

from typing import Dict, List, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_LG, FONT_MD, FONT_TITLE, FONT_XL, get_font
from spacegame.engine.particles import ParticleConfig, ParticlePool
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.player import Player
from spacegame.models.ship import ShipType
from spacegame.models.ship_build import WEIGHT_CLASSES, ComputedShipStats, ShipStatsComputer
from spacegame.models.slot_definition import _SIZE_DISPLAY, _TYPE_DISPLAY, SlotDefinition
from spacegame.models.upgrades import MARK_MULTIPLIERS, ShipUpgrade, ShipUpgradeManager
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

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
_LIST_X = scale_x(40)
_LIST_Y = scale_y(165)
_CARD_W = scale_x(600)
_CARD_H = scale_y(85)
_CARD_SPACING = scale_y(90)
_LIST_BOTTOM = (
    WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(155)
)  # Leave room for buttons/messages
_SCROLL_SPEED = 30

# Mark label colors
_MARK_COLORS = {1: Colors.TEXT_SECONDARY, 2: (100, 180, 255), 3: (255, 200, 80)}


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
        self.viewing: str = "shop"  # Default to shop tab
        self._shop_sub_tab: str = "frames"  # Sub-tab within Shop

        # Scrolling
        self._scroll_offset: int = 0

        # Enhancement/tuning state
        self._tuning_mode: bool = False
        self._tuning_upgrade_id: Optional[str] = None
        self._tuning_options: list[dict] = []

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.header_font = get_font("header", FONT_XL)
        self.info_font = get_font("dialogue", FONT_LG)
        self.small_font = get_font("stats", FONT_MD)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.buy_button: Optional[pygame_gui.elements.UIButton] = None
        self.uninstall_button: Optional[pygame_gui.elements.UIButton] = None
        self.enhance_button: Optional[pygame_gui.elements.UIButton] = None
        self.drydock_tab: Optional[pygame_gui.elements.UIButton] = None
        self.shop_tab: Optional[pygame_gui.elements.UIButton] = None
        self.loadout_tab: Optional[pygame_gui.elements.UIButton] = None
        self.buy_ship_button: Optional[pygame_gui.elements.UIButton] = None
        self.tuning_btn_a: Optional[pygame_gui.elements.UIButton] = None
        self.tuning_btn_b: Optional[pygame_gui.elements.UIButton] = None
        self.tuning_cancel: Optional[pygame_gui.elements.UIButton] = None

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

        # Loadout tab state
        self._loadout_selected_slot_idx: Optional[int] = None
        self._loadout_scroll: int = 0
        self._loadout_stats: Optional[ComputedShipStats] = None
        self._loadout_hover_slot_idx: Optional[int] = None
        self._loadout_unequip_rect: Optional[pygame.Rect] = None
        self._loadout_part_rects: list[tuple[str, pygame.Rect]] = []

        # Ship sprite (animated with procedural fallback)
        self._sprite_mgr = get_sprite_manager()
        self._ship_anim: Optional[AnimatedSprite] = None
        self._ship_fallback: Optional[pygame.Surface] = None
        self._load_ship_anim()

    def _load_ship_anim(self) -> None:
        """Load ship sprite — composite first, then stock, then fallback."""
        # Prefer composite from player's build (the ship they designed)
        # Force recompute to ensure composite is fresh after builder changes
        if self.player and self.player.ship.build:
            try:
                self.player.ship._recompute_stats()
            except Exception:
                pass
        composite = getattr(self.player.ship, "_composite", None) if self.player else None
        if composite and hasattr(composite, "get_surface"):
            self._ship_anim = None
            self._ship_fallback = composite.get_surface(scale=res_scale(3))
            return

        ship_id = self.player.ship.ship_type.id
        self._ship_anim = self._sprite_mgr.get_ship_animated(ship_id, scale=res_scale(3))
        if self._ship_anim is None:
            # Procedural fallback
            surf = pygame.Surface((120, 60), pygame.SRCALPHA)
            points = [(10, 30), (40, 10), (110, 30), (40, 50)]
            pygame.draw.polygon(surf, (60, 80, 120), points)
            pygame.draw.polygon(surf, (100, 130, 180), points, 2)
            pygame.draw.circle(surf, (80, 150, 255, 120), (15, 30), 5)
            self._ship_fallback = surf
        else:
            self._ship_fallback = None

    def on_enter(self) -> None:
        super().on_enter()
        self._scroll_offset = 0
        self._tuning_mode = False
        self._load_ship_anim()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    # Tab subtitle descriptions (rendered below buttons)
    _TAB_SUBTITLES: dict[str, str] = {
        "drydock": "Design Your Ship",
        "shop": "Buy Frames & Parts",
        "loadout": "Equip Your Ship",
    }

    def _create_ui(self) -> None:
        tab_w = 110
        tab_gap = 8
        total_tab_w = tab_w * 3 + tab_gap * 2
        btn_x = WINDOW_WIDTH // 2 - total_tab_w // 2
        self.drydock_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, 70, tab_w, 35),
            text="Drydock",
            manager=self.ui_manager,
        )
        self.shop_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + (tab_w + tab_gap), 70, tab_w, 35),
            text="Shop",
            manager=self.ui_manager,
        )
        self.loadout_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + (tab_w + tab_gap) * 2, 70, tab_w, 35),
            text="Loadout",
            manager=self.ui_manager,
        )
        hud_h = scale_y(HUD_BASE_HEIGHT)
        self.buy_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - 200, WINDOW_HEIGHT - hud_h - scale_y(120), 170, 40
            ),
            text="Buy & Install",
            manager=self.ui_manager,
        )
        self.uninstall_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - 200, WINDOW_HEIGHT - hud_h - scale_y(70), 170, 40
            ),
            text="Uninstall",
            manager=self.ui_manager,
        )
        self.enhance_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - 200, WINDOW_HEIGHT - hud_h - scale_y(120), 170, 40
            ),
            text="Enhance",
            manager=self.ui_manager,
        )
        self.buy_ship_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - 200, WINDOW_HEIGHT - hud_h - scale_y(120), 170, 40
            ),
            text="Buy Frame",
            manager=self.ui_manager,
        )
        # Tuning choice buttons (hidden by default)
        tuning_y = WINDOW_HEIGHT // 2 - 30
        self.tuning_btn_a = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 - 200, tuning_y, 180, 40),
            text="Option A",
            manager=self.ui_manager,
        )
        self.tuning_btn_b = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 + 20, tuning_y, 180, 40),
            text="Option B",
            manager=self.ui_manager,
        )
        self.tuning_cancel = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 - 60, tuning_y + 50, 120, 35),
            text="Cancel",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - hud_h - scale_y(60), 150, 40),
            text="Back",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [
            self.back_button,
            self.buy_button,
            self.uninstall_button,
            self.enhance_button,
            self.drydock_tab,
            self.shop_tab,
            self.loadout_tab,
            self.buy_ship_button,
            self.tuning_btn_a,
            self.tuning_btn_b,
            self.tuning_cancel,
        ]:
            if btn:
                btn.kill()

    # ========================================================================
    # Gating helpers
    # ========================================================================

    def _is_upgrade_locked(self, upgrade: ShipUpgrade) -> tuple[bool, str]:
        """Check if an upgrade is locked by faction rep, quest, or system availability."""
        if (
            upgrade.available_systems
            and self.player.current_system_id not in upgrade.available_systems
        ):
            system_names = ", ".join(s.replace("_", " ").title() for s in upgrade.available_systems)
            return (True, f"Available at: {system_names}")
        if upgrade.faction_required:
            rep = self.player.get_reputation(upgrade.faction_required)
            if rep < upgrade.faction_rep_required:
                return (
                    True,
                    f"Requires {upgrade.faction_required} rep {upgrade.faction_rep_required}",
                )
        if upgrade.unlock_condition:
            if not self.player.dialogue_flags.get(upgrade.unlock_condition, False):
                return (True, f"Requires: {upgrade.unlock_condition.replace('_', ' ').title()}")
        return (False, "")

    def _is_ship_locked(self, ship_type: ShipType) -> tuple[bool, str]:
        """Check if a ship is locked by faction rep or quest."""
        if ship_type.faction_required:
            rep = self.player.get_reputation(ship_type.faction_required)
            if rep < ship_type.faction_rep_required:
                return (
                    True,
                    f"Requires {ship_type.faction_required} rep {ship_type.faction_rep_required}",
                )
        if ship_type.unlock_condition:
            if not self.player.dialogue_flags.get(ship_type.unlock_condition, False):
                return (True, f"Requires: {ship_type.unlock_condition.replace('_', ' ').title()}")
        return (False, "")

    # ========================================================================
    # List builders
    # ========================================================================

    def _get_shop_list(self) -> List[ShipUpgrade]:
        """Get upgrades available in the shop (includes locked items for aspirational display)."""
        installed_ids = {u.id for u in self.upgrade_manager.installed}
        has_market = self.player.has_black_market_access(self.player.current_system_id)
        return [
            u
            for u in self.all_upgrades.values()
            if u.id not in installed_ids and (not u.requires_black_market or has_market)
        ]

    # Frame size labels for ship class display (replaces "Early Game" etc.)
    _FRAME_SIZE_LABELS: dict[str, str] = {
        "starter": "Tiny Frame",
        "early_game": "Small Frame",
        "mid_game": "Medium Frame",
        "late_game": "Large Frame",
        "faction": "Faction Frame",
    }

    def _get_frame_size_label(self, ship_type: object) -> str:
        """Get player-facing frame size label for a ship type."""
        return self._FRAME_SIZE_LABELS.get(
            ship_type.ship_class, ship_type.ship_class.replace("_", " ").title()
        )

    def _get_ship_list(self) -> list:
        """Get ship types available for purchase, excluding current ship."""
        current_id = self.player.ship.ship_type.id
        return [st for st in self.all_ship_types.values() if st.id != current_id]

    def _get_current_list(self) -> list:
        if self.viewing == "shop":
            if self._shop_sub_tab == "frames":
                return self._get_ship_list()
            return self._get_filtered_parts()
        if self.viewing == "loadout":
            return self.upgrade_manager.installed
        # Legacy fallback
        return self._get_shop_list()

    # ========================================================================
    # Enhancement helpers
    # ========================================================================

    def _get_enhance_cost(self, upgrade: ShipUpgrade, target_mark: int) -> int:
        """Calculate credit cost to enhance to target mark."""
        if target_mark == 2:
            return upgrade.price
        elif target_mark == 3:
            return upgrade.price * 2
        return 0

    def _get_mark_label(self, upgrade_id: str) -> str:
        """Get mark label string for an installed upgrade."""
        inst = self.upgrade_manager.get_installed(upgrade_id)
        if not inst:
            return ""
        mark = inst.mark
        label = f"Mk{mark}"
        if inst.tuning:
            # Find tuning name from upgrade
            for u in self.upgrade_manager.installed:
                if u.id == upgrade_id:
                    opt = u.get_tuning_option(inst.tuning)
                    if opt:
                        label += f" [{opt['name']}]"
                    break
        return label

    # ========================================================================
    # Event handling
    # ========================================================================

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Tuning mode buttons take priority
            if self._tuning_mode:
                if event.ui_element == self.tuning_btn_a and len(self._tuning_options) >= 1:
                    self._apply_tuning(self._tuning_options[0]["id"])
                elif event.ui_element == self.tuning_btn_b and len(self._tuning_options) >= 2:
                    self._apply_tuning(self._tuning_options[1]["id"])
                elif event.ui_element == self.tuning_cancel:
                    self._exit_tuning_mode()
                return

            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            elif event.ui_element == self.drydock_tab:
                self.next_state = GameState.SHIP_BUILDER
            elif event.ui_element == self.shop_tab:
                self.viewing = "shop"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.loadout_tab:
                self.viewing = "loadout"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
                self._loadout_selected_slot_idx = None
                self._loadout_scroll = 0
                self._recompute_loadout_stats()
            elif event.ui_element == self.buy_button:
                if self.viewing == "shop" and self._shop_sub_tab != "frames":
                    self._buy_selected_part()
                else:
                    self._buy_selected()
            elif event.ui_element == self.uninstall_button:
                self._uninstall_selected()
            elif event.ui_element == self.enhance_button:
                self._enhance_selected()
            elif event.ui_element == self.buy_ship_button:
                self._buy_selected_ship()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Loadout tab has its own click handler
            if self.viewing == "loadout":
                self._handle_loadout_click(event.pos)
                return
            # Sub-tab click handling for shop view
            if self.viewing == "shop" and hasattr(self, "_sub_tab_rects"):
                for sub_id, rect in self._sub_tab_rects.items():
                    if rect.collidepoint(event.pos):
                        self._shop_sub_tab = sub_id
                        self.selected_upgrade_idx = 0
                        self._scroll_offset = 0
                        return
            if not self._tuning_mode:
                self._handle_item_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.viewing == "loadout":
                # Scroll the compatible parts list
                self._loadout_scroll -= event.y * _SCROLL_SPEED
                self._loadout_scroll = max(0, self._loadout_scroll)
            elif not self._tuning_mode:
                self._scroll_offset -= event.y * _SCROLL_SPEED
                self._clamp_scroll()

        elif event.type == pygame.KEYDOWN:
            if self._tuning_mode:
                if event.key == pygame.K_ESCAPE:
                    self._exit_tuning_mode()
                return
            items = self._get_current_list()
            if event.key == pygame.K_UP:
                self.selected_upgrade_idx = max(0, self.selected_upgrade_idx - 1)
                self._ensure_selected_visible()
            elif event.key == pygame.K_DOWN:
                self.selected_upgrade_idx = min(len(items) - 1, self.selected_upgrade_idx + 1)
                self._ensure_selected_visible()

    def _handle_item_click(self, pos: tuple) -> None:
        items = self._get_current_list()
        # Use tab-specific layout dimensions
        if self.viewing == "shop" and self._shop_sub_tab == "frames":
            list_x = self._FRAME_LIST_X
            card_w = self._FRAME_LIST_W
            card_h = self._FRAME_CARD_H
            card_spacing = self._FRAME_CARD_SPACING
        elif self.viewing == "shop" and self._shop_sub_tab != "frames":
            list_x = self._FRAME_LIST_X
            card_w = self._FRAME_LIST_W
            card_h = self._PART_CARD_H
            card_spacing = self._PART_CARD_SPACING
        else:
            list_x = _LIST_X
            card_w = _CARD_W
            card_h = _CARD_H
            card_spacing = _CARD_SPACING
        for i in range(len(items)):
            card_y = _LIST_Y + i * card_spacing - self._scroll_offset
            rect = pygame.Rect(list_x, card_y, card_w, card_h)
            if rect.collidepoint(pos) and _LIST_Y <= pos[1] <= _LIST_BOTTOM:
                self.selected_upgrade_idx = i
                break

    # ========================================================================
    # Actions
    # ========================================================================

    def _buy_selected(self) -> None:
        shop = self._get_shop_list()
        if not shop or self.selected_upgrade_idx >= len(shop):
            return

        upgrade = shop[self.selected_upgrade_idx]

        # Check gating
        locked, reason = self._is_upgrade_locked(upgrade)
        if locked:
            self._show_message(f"LOCKED: {reason}")
            return

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

    def _enhance_selected(self) -> None:
        """Enhance the selected installed upgrade to the next mark."""
        installed = self.upgrade_manager.installed
        if not installed or self.selected_upgrade_idx >= len(installed):
            return

        upgrade = installed[self.selected_upgrade_idx]
        inst = self.upgrade_manager.get_installed(upgrade.id)
        if not inst:
            return

        target_mark = inst.mark + 1
        if target_mark > upgrade.max_mark:
            self._show_message(f"{upgrade.name} is already at maximum mark")
            return

        # Check cost
        cost = self._get_enhance_cost(upgrade, target_mark)
        if not self.player.can_afford(cost):
            self._show_message(
                f"Enhancement costs {cost:,} CR (need {cost - self.player.credits:,} more)"
            )
            return

        # If Mk2 and has tuning options, enter tuning selection mode
        if target_mark == 2 and upgrade.tuning_options:
            self._enter_tuning_mode(upgrade.id, upgrade.tuning_options, cost)
            return

        # Direct enhancement (no tuning needed)
        self.player.deduct_credits(cost)
        success, msg = self.upgrade_manager.enhance(upgrade.id, mark=target_mark)
        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, PURCHASE_FLASH)
        self._show_message(msg)

    def _enter_tuning_mode(self, upgrade_id: str, options: list, cost: int) -> None:
        """Show tuning selection UI."""
        self._tuning_mode = True
        self._tuning_upgrade_id = upgrade_id
        self._tuning_options = options
        self._tuning_cost = cost
        # Update button labels
        if self.tuning_btn_a and len(options) >= 1:
            self.tuning_btn_a.set_text(options[0]["name"])
        if self.tuning_btn_b and len(options) >= 2:
            self.tuning_btn_b.set_text(options[1]["name"])

    def _apply_tuning(self, tuning_id: str) -> None:
        """Apply tuning choice and enhance to Mk2."""
        if not self._tuning_upgrade_id:
            return
        cost = getattr(self, "_tuning_cost", 0)
        self.player.deduct_credits(cost)
        success, msg = self.upgrade_manager.enhance(
            self._tuning_upgrade_id, mark=2, tuning=tuning_id
        )
        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, PURCHASE_FLASH)
        self._show_message(msg)
        self._exit_tuning_mode()

    def _exit_tuning_mode(self) -> None:
        self._tuning_mode = False
        self._tuning_upgrade_id = None
        self._tuning_options = []

    def _buy_selected_ship(self) -> None:
        """Purchase the selected ship."""
        ships = self._get_ship_list()
        if not ships or self.selected_upgrade_idx >= len(ships):
            return

        ship_type = ships[self.selected_upgrade_idx]

        # Check gating
        locked, reason = self._is_ship_locked(ship_type)
        if locked:
            self._show_message(f"LOCKED: {reason}")
            return

        success, msg = self.player.swap_ship(ship_type)
        self._show_message(msg)

        if success:
            get_audio_manager().play_sfx("trade_buy")
            self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, PURCHASE_FLASH)
            self._load_ship_anim()

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    # ========================================================================
    # Scrolling
    # ========================================================================

    def _get_card_dimensions(self) -> tuple[int, int]:
        """Return (card_height, card_spacing) for current tab."""
        if self.viewing == "shop" and self._shop_sub_tab == "frames":
            return self._FRAME_CARD_H, self._FRAME_CARD_SPACING
        if self.viewing == "shop" and self._shop_sub_tab != "frames":
            return self._PART_CARD_H, self._PART_CARD_SPACING
        return _CARD_H, _CARD_SPACING

    def _max_scroll(self) -> int:
        """Maximum scroll offset based on content height."""
        items = self._get_current_list()
        _, spacing = self._get_card_dimensions()
        content_height = len(items) * spacing
        visible_height = _LIST_BOTTOM - _LIST_Y
        return max(0, content_height - visible_height)

    def _clamp_scroll(self) -> None:
        """Keep scroll offset within valid bounds."""
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll()))

    def _ensure_selected_visible(self) -> None:
        """Scroll to keep the selected item visible."""
        card_h, spacing = self._get_card_dimensions()
        visible_height = _LIST_BOTTOM - _LIST_Y
        item_top = self.selected_upgrade_idx * spacing
        item_bottom = item_top + card_h

        if item_top < self._scroll_offset:
            self._scroll_offset = item_top
        elif item_bottom > self._scroll_offset + visible_height:
            self._scroll_offset = item_bottom - visible_height

        self._clamp_scroll()

    # ========================================================================
    # Update & Render
    # ========================================================================

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        if self._ship_anim:
            self._ship_anim.update(dt)
        self._glow_time += dt
        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("SHIPYARD", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Ship composite in header (player's designed ship only)
        if self._ship_fallback and not self._ship_anim:
            # Composite was loaded — show it
            screen.blit(self._ship_fallback, (WINDOW_WIDTH - 160, 15))
        elif self._ship_anim:
            # Only show animated sprite if no composite exists (legacy save)
            ship_surf = self._ship_anim.get_surface()
            if ship_surf:
                screen.blit(ship_surf, (WINDOW_WIDTH - 160, 15))

        # Credits and per-category slot display
        self._render_slot_summary(screen)

        # Tab active indicator and subtitles
        self._render_tab_indicators(screen)

        # Show/hide context-sensitive buttons
        is_shop = self.viewing == "shop"
        is_frames_sub = is_shop and self._shop_sub_tab == "frames"
        is_parts_sub = is_shop and self._shop_sub_tab != "frames"

        if self.buy_button:
            self.buy_button.visible = is_parts_sub and not self._tuning_mode
            if is_parts_sub:
                self.buy_button.set_text("Buy Part")
        if self.uninstall_button:
            self.uninstall_button.visible = False
        if self.enhance_button:
            self.enhance_button.visible = False
        if self.buy_ship_button:
            self.buy_ship_button.visible = is_frames_sub and not self._tuning_mode

        # Tuning buttons
        if self.tuning_btn_a:
            self.tuning_btn_a.visible = self._tuning_mode
        if self.tuning_btn_b:
            self.tuning_btn_b.visible = self._tuning_mode
        if self.tuning_cancel:
            self.tuning_cancel.visible = self._tuning_mode

        if self.viewing == "shop":
            self._render_shop_sub_tabs(screen)
            if self._shop_sub_tab == "frames":
                self._render_frames(screen)
            else:
                self._render_parts_shop(screen)
        elif self.viewing == "loadout":
            self._render_loadout(screen)
        else:
            # Legacy fallback
            self._render_shop(screen)

        # Tuning overlay
        if self._tuning_mode:
            self._render_tuning_overlay(screen)

        # Particles
        self.particles.render(screen)

        # Message
        if self.message_timer > 0:
            color = (
                Colors.SUCCESS
                if "Installed" in self.message
                or "Bought" in self.message
                or "Enhanced" in self.message
                else Colors.YELLOW
            )
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(
                msg_surf,
                msg_surf.get_rect(
                    center=(
                        WINDOW_WIDTH // 2,
                        WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(140),
                    )
                ),
            )

    def _render_slot_summary(self, screen: pygame.Surface) -> None:
        """Render credits and equipped/total slot counts from the ship build."""
        from spacegame.data_loader import get_data_loader

        # Count slots from the actual build (placed_slots system)
        build = self.player.ship.build if self.player.ship else None
        slot_defs = getattr(get_data_loader(), "slot_definitions", {})

        slot_counts: dict[str, tuple[int, int]] = {}  # type -> (equipped, total)
        if build and build.placed_slots:
            for ps in build.placed_slots:
                sd = slot_defs.get(ps.slot_def_id)
                stype = sd.slot_type if sd else ps.slot_def_id.split("_")[0]
                total, equipped = slot_counts.get(stype, (0, 0))
                total += 1
                if ps.equipped_part_id:
                    equipped += 1
                slot_counts[stype] = (total, equipped)

        # Build summary string with key slot types
        parts = [f"Credits: {self.player.credits:,} CR"]
        display_types = ["weapon", "defense", "engine", "cargo"]
        for stype in display_types:
            total, equipped = slot_counts.get(stype, (0, 0))
            if total > 0:
                label = stype.title()[:3]
                parts.append(f"{label}: {equipped}/{total}")

        slot_text = "  |  ".join(parts)
        slot_surf = self.small_font.render(slot_text, True, Colors.TEXT)
        screen.blit(slot_surf, slot_surf.get_rect(center=(WINDOW_WIDTH // 2, 55)))

    def _render_tab_indicators(self, screen: pygame.Surface) -> None:
        """Render active tab underline and subtitle text below each tab."""
        tab_w = 110
        tab_gap = 8
        total_tab_w = tab_w * 3 + tab_gap * 2
        btn_x = WINDOW_WIDTH // 2 - total_tab_w // 2
        tab_info = [
            ("drydock", btn_x, self.drydock_tab),
            ("shop", btn_x + (tab_w + tab_gap), self.shop_tab),
            ("loadout", btn_x + (tab_w + tab_gap) * 2, self.loadout_tab),
        ]
        for tab_id, x, btn in tab_info:
            if not btn:
                continue
            # Active underline (drydock navigates away, so never active here)
            is_active = tab_id == self.viewing
            if is_active:
                pygame.draw.line(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (x + 2, 107),
                    (x + tab_w - 2, 107),
                    2,
                )
            # Subtitle — only show for the active tab
            if is_active:
                subtitle = self._TAB_SUBTITLES.get(tab_id, "")
                if subtitle:
                    sub_surf = self.small_font.render(subtitle, True, Colors.TEXT_SECONDARY)
                    screen.blit(sub_surf, sub_surf.get_rect(center=(WINDOW_WIDTH // 2, 118)))

    # Sub-tab definitions for the Shop tab
    _SHOP_SUB_TABS: list[tuple[str, str]] = [
        ("frames", "Frames"),
        ("weapon", "Weapons"),
        ("defense", "Defense"),
        ("engine", "Engines"),
        ("utility", "Utility"),
        ("cargo", "Cargo"),
        ("crew_quarters", "Crew"),
        ("reactor", "Reactors"),
    ]

    def _render_shop_sub_tabs(self, screen: pygame.Surface) -> None:
        """Render second row of sub-tab buttons below main tabs when viewing Shop."""
        btn_w = scale_x(90)
        btn_h = scale_y(24)
        gap = scale_x(4)
        total_w = len(self._SHOP_SUB_TABS) * btn_w + (len(self._SHOP_SUB_TABS) - 1) * gap
        start_x = WINDOW_WIDTH // 2 - total_w // 2
        y = 130

        self._sub_tab_rects: dict[str, pygame.Rect] = {}

        for i, (sub_id, label) in enumerate(self._SHOP_SUB_TABS):
            x = start_x + i * (btn_w + gap)
            rect = pygame.Rect(x, y, btn_w, btn_h)
            self._sub_tab_rects[sub_id] = rect

            is_active = self._shop_sub_tab == sub_id

            # Background
            if is_active:
                pygame.draw.rect(screen, (40, 55, 80), rect, border_radius=3)
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, rect, 1, border_radius=3)
            else:
                pygame.draw.rect(screen, (20, 25, 38), rect, border_radius=3)
                pygame.draw.rect(screen, (45, 52, 72), rect, 1, border_radius=3)

            text_color = Colors.TEXT_HIGHLIGHT if is_active else Colors.TEXT_SECONDARY
            text_surf = self.small_font.render(label, True, text_color)
            screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    # Parts layout constants (same split as frames)
    _PART_CARD_H = scale_y(48)
    _PART_CARD_SPACING = scale_y(52)

    # Size badge colors
    _SIZE_BADGE_COLORS: dict[str, tuple] = {
        "small": (80, 180, 80),
        "medium": (100, 160, 255),
        "large": (255, 180, 80),
    }
    _SIZE_BADGE_LABELS: dict[str, str] = {
        "small": "S",
        "medium": "M",
        "large": "L",
    }

    def _get_filtered_parts(self) -> list:
        """Get ShipParts filtered by the active sub-tab slot_type.

        Returns parts sorted with owned-first, then by base_cost ascending.
        """
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        all_parts = [
            p
            for p in dl.ship_parts.values()
            if p.slot_type == self._shop_sub_tab
            and not p.legendary  # Legendary parts are boss drops, not shop items
        ]
        # Sort: owned first, then by base_cost ascending
        all_parts.sort(
            key=lambda p: (0 if self.player.get_part_count(p.id) > 0 else 1, p.base_cost)
        )
        return all_parts

    def _render_parts_shop(self, screen: pygame.Surface) -> None:
        """Render parts shop for the selected sub-tab category (split layout)."""
        parts = self._get_filtered_parts()
        if not parts:
            empty = self.info_font.render(
                "No parts available in this category.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(empty, (40, 200))
            return

        self._render_parts_list(screen, parts)
        self._render_part_detail(screen, parts)

    def _render_parts_list(self, screen: pygame.Surface, parts: list) -> None:
        """Render compact scrollable parts list on the left side."""
        lx = self._FRAME_LIST_X
        lw = self._FRAME_LIST_W
        ch = self._PART_CARD_H
        cs = self._PART_CARD_SPACING

        # Section header
        header = self.info_font.render("AVAILABLE PARTS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (lx, scale_y(145)))

        clip_rect = pygame.Rect(lx - 2, _LIST_Y, lw + 4, _LIST_BOTTOM - _LIST_Y)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for i, part in enumerate(parts):
            card_y = _LIST_Y + i * cs - self._scroll_offset
            if card_y + ch < _LIST_Y or card_y > _LIST_BOTTOM:
                continue

            rect = pygame.Rect(lx, card_y, lw, ch)
            is_selected = i == self.selected_upgrade_idx
            owned_count = self.player.get_part_count(part.id)

            # Card background
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if is_selected:
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(28 + 12 * t)
                    g = int(38 + 12 * t)
                    b = int(58 + 12 * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            elif owned_count > 0:
                card_surf.fill((20, 35, 25, 200))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            border_color = Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            # Size badge
            badge_label = self._SIZE_BADGE_LABELS.get(part.min_size, "?")
            badge_color = self._SIZE_BADGE_COLORS.get(part.min_size, (120, 120, 120))
            badge_w = scale_x(20)
            badge_h = scale_y(16)
            badge_x = rect.x + 8
            badge_y = rect.y + 5
            pygame.draw.rect(
                screen, badge_color, (badge_x, badge_y, badge_w, badge_h), border_radius=3
            )
            badge_surf = self.small_font.render(badge_label, True, (0, 0, 0))
            screen.blit(
                badge_surf,
                badge_surf.get_rect(center=(badge_x + badge_w // 2, badge_y + badge_h // 2)),
            )

            # Part name (after badge)
            name_x = badge_x + badge_w + 6
            name = self.info_font.render(part.name, True, Colors.TEXT)
            screen.blit(name, (name_x, rect.y + 3))

            # Manufacturer (small, below name)
            mfg = part.manufacturer.replace("_", " ").title()
            mfg_surf = self.small_font.render(mfg, True, Colors.TEXT_SECONDARY)
            screen.blit(mfg_surf, (name_x, rect.y + 24))

            # Owned count badge
            if owned_count > 0:
                own_text = f"x{owned_count}"
                own_surf = self.small_font.render(own_text, True, Colors.GREEN)
                own_x = name_x + name.get_width() + 6
                screen.blit(own_surf, (own_x, rect.y + 5))

            # Price (right-aligned)
            can_afford = part.base_cost <= self.player.credits
            price_color = Colors.SUCCESS if can_afford else Colors.RED
            price_text = f"{part.base_cost:,} CR"
            price = self.small_font.render(price_text, True, price_color)
            screen.blit(price, (rect.right - price.get_width() - 10, rect.y + 14))

        screen.set_clip(old_clip)

        # Scrollbar
        content_height = len(parts) * cs
        visible_height = _LIST_BOTTOM - _LIST_Y
        if content_height > visible_height:
            bar_x = lx + lw + 4
            bar_h = max(20, int(visible_height * visible_height / content_height))
            max_scroll = max(1, content_height - visible_height)
            bar_y = _LIST_Y + int(self._scroll_offset / max_scroll * (visible_height - bar_h))
            pygame.draw.rect(
                screen, (40, 45, 60), (bar_x, _LIST_Y, 6, visible_height), border_radius=3
            )
            pygame.draw.rect(screen, (80, 90, 120), (bar_x, bar_y, 6, bar_h), border_radius=3)

    def _render_part_detail(self, screen: pygame.Surface, parts: list) -> None:
        """Render detail panel for the selected part (two-column layout)."""
        if not parts or self.selected_upgrade_idx >= len(parts):
            return

        part = parts[self.selected_upgrade_idx]

        dx = self._FRAME_DETAIL_X
        dw = self._FRAME_DETAIL_W
        dy = _LIST_Y - scale_y(10)
        pad = scale_x(16)

        # Panel background
        panel_h = _LIST_BOTTOM - dy + scale_y(10)
        panel_surf = pygame.Surface((dw, panel_h), pygame.SRCALPHA)
        panel_surf.fill((14, 18, 32, 220))
        screen.blit(panel_surf, (dx, dy))
        pygame.draw.rect(screen, (45, 52, 72), (dx, dy, dw, panel_h), 1, border_radius=6)

        # Accent line at top
        pygame.draw.line(
            screen, Colors.TEXT_HIGHLIGHT, (dx + 10, dy + 2), (dx + dw - 10, dy + 2), 2
        )

        # === TITLE (full width, centered) ===
        title_y = dy + scale_y(10)
        name = self.header_font.render(part.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name, name.get_rect(centerx=dx + dw // 2, top=title_y))
        content_top = title_y + name.get_height() + scale_y(8)

        # Vertical divider position
        half_w = dw // 2
        divider_x = dx + half_w

        # Draw vertical divider line
        pygame.draw.line(
            screen,
            (40, 48, 65),
            (divider_x, content_top),
            (divider_x, dy + panel_h - pad),
            1,
        )

        # ============================================================
        # LEFT COLUMN: size, manufacturer, description, key stats
        # ============================================================
        lx_col = dx + pad
        lw_col = half_w - pad * 2
        ly = content_top

        # Size label (e.g. "Medium Weapon")
        size_label = f"{part.min_size.title()} {part.slot_type.replace('_', ' ').title()}"
        size_surf = self.small_font.render(size_label, True, Colors.TEXT_SECONDARY)
        screen.blit(size_surf, (lx_col, ly))
        ly += size_surf.get_height() + scale_y(4)

        # Manufacturer
        mfg = part.manufacturer.replace("_", " ").title()
        mfg_surf = self.small_font.render(f"Mfg: {mfg}", True, Colors.TEXT_SECONDARY)
        screen.blit(mfg_surf, (lx_col, ly))
        ly += mfg_surf.get_height() + scale_y(8)

        # Weight
        weight_surf = self.small_font.render(
            f"Weight: {part.weight:.1f}", True, Colors.TEXT_SECONDARY
        )
        screen.blit(weight_surf, (lx_col, ly))
        ly += weight_surf.get_height() + scale_y(8)

        # Description (word-wrapped)
        if part.description:
            ly += self._render_wrapped_text(
                screen, part.description, lx_col, ly, lw_col, Colors.TEXT_SECONDARY
            )
            ly += scale_y(8)

        # Key stat highlights (top 3 provides values, excluding slot_type)
        provides = {k: v for k, v in part.provides.items() if k != "slot_type"}
        if provides:
            ly += scale_y(4)
            highlight_label = self.small_font.render("Key Stats:", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(highlight_label, (lx_col, ly))
            ly += highlight_label.get_height() + scale_y(4)

            for stat_key, stat_val in list(provides.items())[:3]:
                stat_name = stat_key.replace("_", " ").title()
                stat_text = f"{stat_name}: {stat_val}"
                stat_surf = self.small_font.render(stat_text, True, Colors.TEXT)
                screen.blit(stat_surf, (lx_col + scale_x(8), ly))
                ly += stat_surf.get_height() + scale_y(2)

        # ============================================================
        # RIGHT COLUMN: combat stats, provides table, price, inventory
        # ============================================================
        rx = divider_x + pad
        ry = content_top

        # Combat move section (shown above provides for weapon/defense parts)
        cm = part.combat_move
        if cm:
            combat_label = self.small_font.render("COMBAT", True, (255, 180, 80))
            screen.blit(combat_label, (rx, ry))
            ry += combat_label.get_height() + scale_y(4)

            # Move name
            move_name = cm.get("name", "Unknown")
            screen.blit(
                self.small_font.render(f"  {move_name}", True, Colors.TEXT_HIGHLIGHT),
                (rx, ry),
            )
            ry += scale_y(15)

            # Damage (from effects list)
            effects = cm.get("effects", [])
            for eff in effects:
                if eff.get("type") == "damage":
                    dmg_val = eff.get("amount", 0)
                    screen.blit(
                        self.small_font.render(f"  Damage: {dmg_val}", True, Colors.TEXT),
                        (rx, ry),
                    )
                    ry += scale_y(15)
                    break

            # Energy cost
            energy_cost = cm.get("energy_cost", 0)
            screen.blit(
                self.small_font.render(f"  Energy: {energy_cost}", True, Colors.TEXT),
                (rx, ry),
            )
            ry += scale_y(15)

            # Accuracy modifier
            acc_mod = cm.get("accuracy_modifier", 0)
            acc_sign = "+" if acc_mod >= 0 else ""
            screen.blit(
                self.small_font.render(f"  Accuracy: {acc_sign}{acc_mod}", True, Colors.TEXT),
                (rx, ry),
            )
            ry += scale_y(15) + scale_y(6)

        # Stats header
        stats_label = self.small_font.render("Stats:", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(stats_label, (rx, ry))
        ry += stats_label.get_height() + scale_y(4)

        # Full provides table
        col_val_x = rx + scale_x(120)
        for stat_key, stat_val in provides.items():
            stat_name = stat_key.replace("_", " ").title()
            screen.blit(self.small_font.render(stat_name, True, Colors.TEXT), (rx, ry))
            val_str = f"{stat_val:.1f}" if isinstance(stat_val, float) else str(stat_val)
            screen.blit(
                self.small_font.render(val_str, True, Colors.TEXT_HIGHLIGHT), (col_val_x, ry)
            )
            ry += scale_y(15)

        ry += scale_y(8)

        # Mark
        mark_text = f"Mark: Mk{part.mark}"
        if part.legendary:
            mark_text += "  (LEGENDARY)"
        mark_color = (255, 200, 80) if part.legendary else Colors.TEXT_SECONDARY
        screen.blit(self.small_font.render(mark_text, True, mark_color), (rx, ry))
        ry += scale_y(18)

        # Separator before price
        pygame.draw.line(screen, (40, 48, 65), (rx, ry), (dx + dw - pad, ry), 1)
        ry += scale_y(8)

        # Price
        can_afford = part.base_cost <= self.player.credits
        price_color = Colors.SUCCESS if can_afford else Colors.RED
        price_line = f"Price: {part.base_cost:,} CR"
        screen.blit(self.info_font.render(price_line, True, price_color), (rx, ry))
        ry += scale_y(20)

        # Inventory count
        owned_count = self.player.get_part_count(part.id)
        own_text = f"You own: {owned_count}"
        own_color = Colors.GREEN if owned_count > 0 else Colors.TEXT_SECONDARY
        screen.blit(self.small_font.render(own_text, True, own_color), (rx, ry))

    # ========================================================================
    # Loadout tab — grid + parts assignment
    # ========================================================================

    # Slot type letter abbreviations for grid rendering
    _SLOT_TYPE_LETTERS: dict[str, str] = {
        "weapon": "W",
        "defense": "D",
        "engine": "E",
        "utility": "U",
        "cargo": "C",
        "crew_quarters": "Q",
        "reactor": "R",
    }

    def _recompute_loadout_stats(self) -> None:
        """Recompute ship stats from the current build for the loadout stats bar."""
        build = self.player.ship.build
        if not build:
            self._loadout_stats = None
            return
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        materials = getattr(dl, "hull_materials", {})
        slot_defs = getattr(dl, "slot_definitions", {})
        parts_cat = getattr(dl, "ship_parts", {})
        equipment = getattr(dl, "upgrades", {})
        module_cat = getattr(dl, "ship_modules", {})
        self._loadout_stats = ShipStatsComputer.compute(
            build,
            materials,
            equipment=equipment,
            module_catalog=module_cat,
            slot_definitions=slot_defs,
            parts_catalog=parts_cat,
            ship_type=self.player.ship.ship_type,
        )

    def _get_loadout_grid_params(self) -> Optional[dict]:
        """Calculate grid rendering parameters for the loadout tab.

        Returns:
            Dict with grid_x, grid_y, cell_size, canvas_w, canvas_h, or None.
        """
        build = self.player.ship.build
        if not build or not build.placed_slots:
            return None

        canvas_w = build.canvas_w
        canvas_h = build.canvas_h

        grid_area_x = scale_x(30)
        grid_area_y = scale_y(170)
        grid_area_w = scale_x(550)
        grid_area_h = scale_y(380)

        cell_w = grid_area_w // canvas_w
        cell_h = grid_area_h // canvas_h
        cell_size = min(cell_w, cell_h, scale_x(16))

        # Center the grid within the available area
        total_grid_w = canvas_w * cell_size
        total_grid_h = canvas_h * cell_size
        grid_x = grid_area_x + (grid_area_w - total_grid_w) // 2
        grid_y = grid_area_y + (grid_area_h - total_grid_h) // 2

        return {
            "grid_x": grid_x,
            "grid_y": grid_y,
            "cell_size": cell_size,
            "canvas_w": canvas_w,
            "canvas_h": canvas_h,
            "total_w": total_grid_w,
            "total_h": total_grid_h,
        }

    def _get_slot_def_for_placed(self, placed_slot: object) -> Optional[SlotDefinition]:
        """Look up the SlotDefinition for a PlacedSlot."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        return dl.slot_definitions.get(placed_slot.slot_def_id)

    def _slot_screen_rect(
        self, placed_slot: object, slot_def: SlotDefinition, gp: dict
    ) -> pygame.Rect:
        """Get the screen-space rect for a placed slot on the grid."""
        sx = gp["grid_x"] + placed_slot.x * gp["cell_size"]
        sy = gp["grid_y"] + placed_slot.y * gp["cell_size"]
        sw = slot_def.footprint_w * gp["cell_size"]
        sh = slot_def.footprint_h * gp["cell_size"]
        return pygame.Rect(sx, sy, sw, sh)

    def _render_loadout(self, screen: pygame.Surface) -> None:
        """Render the full Loadout tab: grid + parts panel + stats bar."""
        build = self.player.ship.build
        if not build or not build.placed_slots:
            text = "No ship build with slots. Visit Drydock first."
            surf = self.info_font.render(text, True, Colors.TEXT_SECONDARY)
            screen.blit(surf, surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))
            return

        gp = self._get_loadout_grid_params()
        if not gp:
            return

        self._render_loadout_grid(screen, build, gp)
        self._render_loadout_parts_panel(screen, build, gp)
        self._render_loadout_stats_bar(screen)

    def _render_loadout_grid(self, screen: pygame.Surface, build: object, gp: dict) -> None:
        """Render the ship grid with hull pixels and clickable slots."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        materials = getattr(dl, "hull_materials", {})
        cell = gp["cell_size"]
        gx, gy = gp["grid_x"], gp["grid_y"]

        # Grid background
        grid_bg = pygame.Rect(gx - 2, gy - 2, gp["total_w"] + 4, gp["total_h"] + 4)
        pygame.draw.rect(screen, (10, 12, 22), grid_bg, border_radius=4)
        pygame.draw.rect(screen, (35, 40, 55), grid_bg, 1, border_radius=4)

        # Hull pixels
        for pixel in build.pixels:
            mat = materials.get(pixel.material_id)
            color = mat.color_primary if mat else (60, 60, 60)
            px = gx + pixel.x * cell
            py = gy + pixel.y * cell
            pygame.draw.rect(screen, color, (px, py, cell - 1, cell - 1))

        # Placed slots
        mouse_pos = pygame.mouse.get_pos()
        for idx, ps in enumerate(build.placed_slots):
            slot_def = self._get_slot_def_for_placed(ps)
            if not slot_def:
                continue

            rect = self._slot_screen_rect(ps, slot_def, gp)
            is_selected = idx == self._loadout_selected_slot_idx
            is_hovered = rect.collidepoint(mouse_pos) and not is_selected

            # Slot fill — dim version of slot color
            base_color = slot_def.color
            if ps.equipped_part_id:
                fill_color = (
                    min(255, base_color[0] + 30),
                    min(255, base_color[1] + 30),
                    min(255, base_color[2] + 30),
                )
            else:
                fill_color = (
                    base_color[0] // 3,
                    base_color[1] // 3,
                    base_color[2] // 3,
                )

            slot_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            slot_surf.fill((*fill_color, 160))
            screen.blit(slot_surf, rect.topleft)

            # Border
            if is_selected:
                pygame.draw.rect(screen, (255, 220, 80), rect, 2, border_radius=2)
            elif is_hovered:
                pygame.draw.rect(screen, (180, 180, 200), rect, 1, border_radius=2)
            else:
                border_c = base_color if ps.equipped_part_id else (60, 65, 80)
                pygame.draw.rect(screen, border_c, rect, 1, border_radius=2)

            # Type letter centered in slot
            letter = self._SLOT_TYPE_LETTERS.get(slot_def.slot_type, "?")
            letter_surf = self.small_font.render(letter, True, Colors.TEXT)
            screen.blit(letter_surf, letter_surf.get_rect(center=rect.center))

            # Equipped indicator — small dot if part is installed
            if ps.equipped_part_id:
                dot_x = rect.right - 5
                dot_y = rect.top + 5
                pygame.draw.circle(screen, Colors.GREEN, (dot_x, dot_y), 3)

    def _render_loadout_parts_panel(self, screen: pygame.Surface, build: object, gp: dict) -> None:
        """Render the right-side panel: slot info + compatible parts list."""
        panel_x = WINDOW_WIDTH // 2 + scale_x(20)
        panel_w = WINDOW_WIDTH // 2 - scale_x(40)
        panel_y = scale_y(170)
        panel_h = scale_y(380)

        # Panel background
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((14, 18, 32, 220))
        screen.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(
            screen, (45, 52, 72), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6
        )

        if self._loadout_selected_slot_idx is None:
            hint = "Click a slot on the ship to assign parts."
            hint_surf = self.info_font.render(hint, True, Colors.TEXT_SECONDARY)
            screen.blit(
                hint_surf,
                hint_surf.get_rect(center=(panel_x + panel_w // 2, panel_y + panel_h // 2)),
            )
            return

        # Validate selected index
        if self._loadout_selected_slot_idx >= len(build.placed_slots):
            self._loadout_selected_slot_idx = None
            return

        ps = build.placed_slots[self._loadout_selected_slot_idx]
        slot_def = self._get_slot_def_for_placed(ps)
        if not slot_def:
            return

        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        pad = scale_x(12)
        cx = panel_x + pad
        cy = panel_y + pad
        content_w = panel_w - pad * 2

        # --- Slot Info Header ---
        type_name = _TYPE_DISPLAY.get(slot_def.slot_type, slot_def.slot_type.title())
        size_label = _SIZE_DISPLAY.get(slot_def.size, slot_def.size[0].upper())
        header_text = f"{type_name} Slot ({size_label})"
        header_surf = self.info_font.render(header_text, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header_surf, (cx, cy))
        cy += header_surf.get_height() + scale_y(6)

        # Current equipment
        if ps.equipped_part_id:
            part = dl.ship_parts.get(ps.equipped_part_id)
            equip_name = part.name if part else ps.equipped_part_id
            equip_surf = self.small_font.render(f"Equipped: {equip_name}", True, Colors.GREEN)
            screen.blit(equip_surf, (cx, cy))
            cy += equip_surf.get_height() + scale_y(4)

            # Key stat of equipped part
            if part and part.provides:
                top_stat = next(iter(part.provides.items()), None)
                if top_stat:
                    stat_name = top_stat[0].replace("_", " ").title()
                    stat_surf = self.small_font.render(
                        f"  {stat_name}: {top_stat[1]}", True, Colors.TEXT_SECONDARY
                    )
                    screen.blit(stat_surf, (cx, cy))
                    cy += stat_surf.get_height() + scale_y(4)

            # Unequip button area
            unequip_rect = pygame.Rect(cx, cy, scale_x(100), scale_y(22))
            pygame.draw.rect(screen, (80, 40, 40), unequip_rect, border_radius=3)
            pygame.draw.rect(screen, (180, 80, 80), unequip_rect, 1, border_radius=3)
            unequip_text = self.small_font.render("Unequip", True, Colors.TEXT)
            screen.blit(
                unequip_text,
                unequip_text.get_rect(center=unequip_rect.center),
            )
            # Store rect for click detection
            self._loadout_unequip_rect = unequip_rect
            cy += unequip_rect.height + scale_y(8)
        else:
            empty_surf = self.small_font.render("Empty", True, Colors.TEXT_SECONDARY)
            screen.blit(empty_surf, (cx, cy))
            cy += empty_surf.get_height() + scale_y(6)
            self._loadout_unequip_rect = None

        # --- Separator ---
        pygame.draw.line(screen, (40, 48, 65), (cx, cy), (cx + content_w, cy), 1)
        cy += scale_y(6)

        # --- Compatible Parts Header ---
        compat_header = self.small_font.render("COMPATIBLE PARTS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(compat_header, (cx, cy))
        cy += compat_header.get_height() + scale_y(6)

        # --- Build compatible parts list ---
        compatible = self._get_compatible_parts(slot_def)
        if not compatible:
            none_surf = self.small_font.render(
                "No compatible parts in inventory.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(none_surf, (cx, cy))
            self._loadout_part_rects = []
            return

        # Scrollable parts list
        list_top = cy
        list_bottom = panel_y + panel_h - pad
        visible_h = list_bottom - list_top
        entry_h = scale_y(36)

        # Clamp scroll
        max_scroll = max(0, len(compatible) * entry_h - visible_h)
        self._loadout_scroll = max(0, min(self._loadout_scroll, max_scroll))

        clip_rect = pygame.Rect(cx - 2, list_top, content_w + 4, visible_h)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        self._loadout_part_rects = []
        for i, part in enumerate(compatible):
            ey = list_top + i * entry_h - self._loadout_scroll
            if ey + entry_h < list_top or ey > list_bottom:
                self._loadout_part_rects.append((part.id, pygame.Rect(0, 0, 0, 0)))
                continue

            entry_rect = pygame.Rect(cx, ey, content_w, entry_h - 2)
            self._loadout_part_rects.append((part.id, entry_rect))

            # Entry background
            mouse_pos = pygame.mouse.get_pos()
            is_hovered = entry_rect.collidepoint(mouse_pos)
            bg_color = (30, 38, 55, 200) if is_hovered else (20, 25, 40, 180)
            entry_surf = pygame.Surface((entry_rect.width, entry_rect.height), pygame.SRCALPHA)
            entry_surf.fill(bg_color)
            screen.blit(entry_surf, entry_rect.topleft)
            pygame.draw.rect(
                screen,
                (60, 70, 90) if is_hovered else (40, 48, 65),
                entry_rect,
                1,
                border_radius=3,
            )

            # Size badge
            badge_label = self._SIZE_BADGE_LABELS.get(part.min_size, "?")
            badge_color = self._SIZE_BADGE_COLORS.get(part.min_size, (120, 120, 120))
            badge_w = scale_x(18)
            badge_h = scale_y(14)
            badge_x = entry_rect.x + 4
            badge_y = entry_rect.y + 3
            pygame.draw.rect(
                screen,
                badge_color,
                (badge_x, badge_y, badge_w, badge_h),
                border_radius=2,
            )
            badge_surf = self.small_font.render(badge_label, True, (0, 0, 0))
            screen.blit(
                badge_surf,
                badge_surf.get_rect(center=(badge_x + badge_w // 2, badge_y + badge_h // 2)),
            )

            # Part name
            name_x = badge_x + badge_w + 6
            name_surf = self.small_font.render(part.name, True, Colors.TEXT)
            screen.blit(name_surf, (name_x, entry_rect.y + 2))

            # Key stat + owned count on second line
            owned = self.player.get_part_count(part.id)
            stat_text = ""
            cm = part.combat_move
            if cm:
                # For weapon/defense parts, show damage and energy cost
                dmg_val = 0
                for eff in cm.get("effects", []):
                    if eff.get("type") == "damage":
                        dmg_val = eff.get("amount", 0)
                        break
                energy_cost = cm.get("energy_cost", 0)
                stat_text = f"Dmg: {dmg_val} | E: {energy_cost}"
            elif part.provides:
                top_stat = next(iter(part.provides.items()), None)
                if top_stat:
                    stat_name = top_stat[0].replace("_", " ").title()
                    stat_text = f"{stat_name}: {top_stat[1]}"
            stat_line = f"{stat_text}  |  x{owned}" if stat_text else f"x{owned}"
            stat_surf = self.small_font.render(stat_line, True, Colors.TEXT_SECONDARY)
            screen.blit(stat_surf, (name_x, entry_rect.y + 17))

        screen.set_clip(old_clip)

        # Scrollbar for parts list
        if max_scroll > 0:
            bar_x = panel_x + panel_w - scale_x(8)
            bar_total_h = visible_h
            bar_h = max(15, int(bar_total_h * visible_h / (len(compatible) * entry_h)))
            bar_y = list_top + int(
                self._loadout_scroll / max(1, max_scroll) * (bar_total_h - bar_h)
            )
            pygame.draw.rect(
                screen,
                (40, 45, 60),
                (bar_x, list_top, 5, bar_total_h),
                border_radius=2,
            )
            pygame.draw.rect(
                screen,
                (80, 90, 120),
                (bar_x, bar_y, 5, bar_h),
                border_radius=2,
            )

    def _get_compatible_parts(self, slot_def: SlotDefinition) -> list:
        """Get parts from inventory compatible with the given slot definition."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        compatible = []
        for part_id, count in self.player.parts_inventory.items():
            if count <= 0:
                continue
            part = dl.ship_parts.get(part_id)
            if not part:
                continue
            if part.slot_type != slot_def.slot_type:
                continue
            if not part.fits_in_slot_size(slot_def.size):
                continue
            compatible.append(part)
        # Sort by base_cost ascending
        compatible.sort(key=lambda p: p.base_cost)
        return compatible

    def _render_loadout_stats_bar(self, screen: pygame.Surface) -> None:
        """Render the horizontal stats summary bar below the grid."""
        stats = self._loadout_stats
        if not stats:
            return

        bar_y = WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60)
        bar_x = scale_x(30)
        bar_w = WINDOW_WIDTH - scale_x(60)

        # Background
        bar_rect = pygame.Rect(bar_x, bar_y, bar_w, scale_y(32))
        bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
        bar_surf.fill((14, 18, 32, 220))
        screen.blit(bar_surf, bar_rect.topleft)
        pygame.draw.rect(screen, (45, 52, 72), bar_rect, 1, border_radius=4)

        stat_items = [
            ("Hull", stats.hull),
            ("Shields", stats.shields),
            ("Armor", stats.armor),
            ("Speed", stats.speed),
            ("Fuel", stats.fuel_capacity),
            ("Cargo", stats.cargo_capacity),
            ("Power", stats.power_max),
        ]

        text_parts = "  |  ".join(f"{name}: {val}" for name, val in stat_items)
        stat_surf = self.small_font.render(text_parts, True, Colors.TEXT)
        screen.blit(stat_surf, stat_surf.get_rect(center=bar_rect.center))

    def _handle_loadout_click(self, pos: tuple) -> None:
        """Handle mouse click in loadout tab — grid slots, parts list, unequip."""
        build = self.player.ship.build
        if not build or not build.placed_slots:
            return

        gp = self._get_loadout_grid_params()
        if not gp:
            return

        # Check unequip button
        if (
            hasattr(self, "_loadout_unequip_rect")
            and self._loadout_unequip_rect
            and self._loadout_unequip_rect.collidepoint(pos)
        ):
            self._loadout_unequip()
            return

        # Check parts list clicks
        if hasattr(self, "_loadout_part_rects"):
            for part_id, rect in self._loadout_part_rects:
                if rect.width > 0 and rect.collidepoint(pos):
                    self._loadout_equip(part_id)
                    return

        # Check grid slot clicks
        for idx, ps in enumerate(build.placed_slots):
            slot_def = self._get_slot_def_for_placed(ps)
            if not slot_def:
                continue
            rect = self._slot_screen_rect(ps, slot_def, gp)
            if rect.collidepoint(pos):
                self._loadout_selected_slot_idx = idx
                self._loadout_scroll = 0
                return

    def _loadout_equip(self, part_id: str) -> None:
        """Equip a part from inventory into the selected slot."""
        build = self.player.ship.build
        if (
            not build
            or self._loadout_selected_slot_idx is None
            or self._loadout_selected_slot_idx >= len(build.placed_slots)
        ):
            return

        ps = build.placed_slots[self._loadout_selected_slot_idx]

        # If slot already has a part, unequip it first
        if ps.equipped_part_id:
            self.player.add_part(ps.equipped_part_id)

        # Remove part from inventory and equip
        success, msg = self.player.remove_part(part_id)
        if not success:
            self._show_message(f"Cannot equip: {msg}")
            return

        ps.equipped_part_id = part_id
        self.player.ship.set_build(build)
        self._recompute_loadout_stats()

        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        part = dl.ship_parts.get(part_id)
        part_name = part.name if part else part_id
        self._show_message(f"Equipped {part_name}")

        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass

    def _loadout_unequip(self) -> None:
        """Unequip the part from the selected slot back to inventory."""
        build = self.player.ship.build
        if (
            not build
            or self._loadout_selected_slot_idx is None
            or self._loadout_selected_slot_idx >= len(build.placed_slots)
        ):
            return

        ps = build.placed_slots[self._loadout_selected_slot_idx]
        if not ps.equipped_part_id:
            return

        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        part = dl.ship_parts.get(ps.equipped_part_id)
        part_name = part.name if part else ps.equipped_part_id

        self.player.add_part(ps.equipped_part_id)
        ps.equipped_part_id = None
        self.player.ship.set_build(build)
        self._recompute_loadout_stats()
        self._show_message(f"Unequipped {part_name}")

        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass

    def _render_tuning_overlay(self, screen: pygame.Surface) -> None:
        """Draw the tuning selection overlay."""
        # Dim background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        # Panel
        panel_w, panel_h = 460, 200
        panel_x = WINDOW_WIDTH // 2 - panel_w // 2
        panel_y = WINDOW_HEIGHT // 2 - panel_h // 2 - 20
        pygame.draw.rect(
            screen, (20, 25, 40), (panel_x, panel_y, panel_w, panel_h), border_radius=8
        )
        pygame.draw.rect(
            screen, Colors.TEXT_HIGHLIGHT, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8
        )

        title = self.header_font.render("Choose Tuning Specialization", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 25)))

        # Show tuning option descriptions
        for i, opt in enumerate(self._tuning_options[:2]):
            x = panel_x + 20 + i * 220
            y = panel_y + 55
            desc = self.small_font.render(opt.get("description", ""), True, Colors.TEXT)
            screen.blit(desc, (x, y))
            bonus_text = f"{opt.get('bonus_type', '')}: +{opt.get('bonus_value', 0)}"
            bonus = self.small_font.render(bonus_text, True, Colors.TEXT_SECONDARY)
            screen.blit(bonus, (x, y + 22))

    # Ship class → weight class mapping for frame detail panel
    _CLASS_TO_WEIGHT: dict[str, str] = {
        "starter": "tiny",
        "early_game": "small",
        "mid_game": "medium",
        "late_game": "large",
        "faction": "large",
    }

    # ========================================================================
    # Frames tab (split layout: list left, detail right)
    # ========================================================================

    # Frames layout constants
    _FRAME_LIST_X = scale_x(30)
    _FRAME_LIST_W = scale_x(420)
    _FRAME_CARD_H = scale_y(52)
    _FRAME_CARD_SPACING = scale_y(56)
    _FRAME_DETAIL_X = scale_x(480)
    _FRAME_DETAIL_W = WINDOW_WIDTH - scale_x(480) - scale_x(30)

    def _render_frames(self, screen: pygame.Surface) -> None:
        """Render frame upgrade list with split layout."""
        ships = self._get_ship_list()
        if not ships:
            empty = self.info_font.render(
                "No frame upgrades available.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(empty, (40, 160))
            return

        self._render_frame_list(screen, ships)
        self._render_frame_detail(screen, ships)

    def _render_frame_list(self, screen: pygame.Surface, ships: list) -> None:
        """Render compact scrollable frame list on the left side."""
        lx = self._FRAME_LIST_X
        lw = self._FRAME_LIST_W
        ch = self._FRAME_CARD_H
        cs = self._FRAME_CARD_SPACING

        # Section header
        header = self.info_font.render("AVAILABLE FRAMES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (lx, scale_y(145)))

        clip_rect = pygame.Rect(lx - 2, _LIST_Y, lw + 4, _LIST_BOTTOM - _LIST_Y)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        current = self.player.ship.ship_type

        for i, ship_type in enumerate(ships):
            card_y = _LIST_Y + i * cs - self._scroll_offset
            if card_y + ch < _LIST_Y or card_y > _LIST_BOTTOM:
                continue

            rect = pygame.Rect(lx, card_y, lw, ch)
            is_selected = i == self.selected_upgrade_idx
            locked, lock_reason = self._is_ship_locked(ship_type)

            # Card background
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if locked:
                card_surf.fill((12, 12, 20, 200))
            elif is_selected:
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(28 + 12 * t)
                    g = int(38 + 12 * t)
                    b = int(58 + 12 * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            border_color = (
                (60, 30, 30) if locked else (Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72))
            )
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            if locked:
                name_text = f"{ship_type.name}  ({self._get_frame_size_label(ship_type)})"
                name = self.small_font.render(name_text, True, (80, 60, 60))
                screen.blit(name, (rect.x + 10, rect.y + 5))
                lock_surf = self.small_font.render(lock_reason, True, (180, 80, 80))
                screen.blit(lock_surf, (rect.x + 10, rect.y + 26))
            else:
                # Name + frame size
                name_text = f"{ship_type.name}"
                name = self.info_font.render(name_text, True, Colors.TEXT)
                screen.blit(name, (rect.x + 10, rect.y + 4))

                frame_label = self._get_frame_size_label(ship_type)
                frame_surf = self.small_font.render(frame_label, True, Colors.TEXT_SECONDARY)
                screen.blit(frame_surf, (rect.x + 10, rect.y + 28))

                # Net price on the right
                net_cost = ship_type.purchase_price - current.resale_value
                can_afford = net_cost <= self.player.credits
                price_color = Colors.SUCCESS if can_afford else Colors.RED
                price_text = f"{net_cost:,} CR"
                price = self.small_font.render(price_text, True, price_color)
                screen.blit(price, (rect.right - price.get_width() - 10, rect.y + 16))

        screen.set_clip(old_clip)

        # Scrollbar
        content_height = len(ships) * cs
        visible_height = _LIST_BOTTOM - _LIST_Y
        if content_height > visible_height:
            bar_x = lx + lw + 4
            bar_h = max(20, int(visible_height * visible_height / content_height))
            max_scroll = max(1, content_height - visible_height)
            bar_y = _LIST_Y + int(self._scroll_offset / max_scroll * (visible_height - bar_h))
            pygame.draw.rect(
                screen, (40, 45, 60), (bar_x, _LIST_Y, 6, visible_height), border_radius=3
            )
            pygame.draw.rect(screen, (80, 90, 120), (bar_x, bar_y, 6, bar_h), border_radius=3)

    def _render_frame_detail(self, screen: pygame.Surface, ships: list) -> None:
        """Render detail panel for the selected frame — two-column layout.

        Left column: frame label, grid preview, grid info, slots, description.
        Right column: stat comparison table, price/trade-in/net cost.
        Title spans the full width at top.
        """
        if not ships or self.selected_upgrade_idx >= len(ships):
            return

        ship_type = ships[self.selected_upgrade_idx]
        current = self.player.ship.ship_type
        locked, lock_reason = self._is_ship_locked(ship_type)

        dx = self._FRAME_DETAIL_X
        dw = self._FRAME_DETAIL_W
        dy = _LIST_Y - scale_y(10)
        pad = scale_x(16)

        # Panel background
        panel_h = _LIST_BOTTOM - dy + scale_y(10)
        panel_surf = pygame.Surface((dw, panel_h), pygame.SRCALPHA)
        panel_surf.fill((14, 18, 32, 220))
        screen.blit(panel_surf, (dx, dy))
        pygame.draw.rect(screen, (45, 52, 72), (dx, dy, dw, panel_h), 1, border_radius=6)

        # Accent line at top
        pygame.draw.line(
            screen, Colors.TEXT_HIGHLIGHT, (dx + 10, dy + 2), (dx + dw - 10, dy + 2), 2
        )

        # === TITLE (full width, centered) ===
        title_y = dy + scale_y(10)
        name = self.header_font.render(ship_type.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name, name.get_rect(centerx=dx + dw // 2, top=title_y))
        content_top = title_y + name.get_height() + scale_y(8)

        # Vertical divider position
        half_w = dw // 2
        divider_x = dx + half_w

        # Draw vertical divider line
        pygame.draw.line(
            screen,
            (40, 48, 65),
            (divider_x, content_top),
            (divider_x, dy + panel_h - pad),
            1,
        )

        # ============================================================
        # LEFT COLUMN: frame info, grid preview, slots, description
        # ============================================================
        lx = dx + pad
        lw = half_w - pad * 2
        ly = content_top

        # Frame size label
        frame_label = self._get_frame_size_label(ship_type)
        frame_surf = self.small_font.render(frame_label, True, Colors.TEXT_SECONDARY)
        screen.blit(frame_surf, (lx, ly))
        ly += frame_surf.get_height() + scale_y(6)

        # Canvas visualization
        wc_name = self._CLASS_TO_WEIGHT.get(ship_type.ship_class, "small")

        wc = WEIGHT_CLASSES.get(wc_name, WEIGHT_CLASSES["small"])
        canvas_w = wc.get("canvas_w", 32)
        canvas_h = wc.get("canvas_h", 32)

        max_preview_w = lw
        max_preview_h = scale_y(80)
        pixel_size = min(max_preview_w // canvas_w, max_preview_h // canvas_h, 4)
        grid_w = canvas_w * pixel_size
        grid_h = canvas_h * pixel_size

        grid_surf = pygame.Surface((grid_w, grid_h), pygame.SRCALPHA)
        grid_surf.fill((20, 28, 45, 180))
        screen.blit(grid_surf, (lx, ly))
        pygame.draw.rect(screen, (50, 60, 90), (lx, ly, grid_w, grid_h), 1)

        for gx in range(0, canvas_w, 4):
            for gy in range(0, canvas_h, 4):
                screen.set_at((lx + gx * pixel_size, ly + gy * pixel_size), (40, 50, 70))

        ly += grid_h + scale_y(4)

        # Grid dimensions
        dim_text = f"Grid: {canvas_w} x {canvas_h}"
        screen.blit(self.small_font.render(dim_text, True, Colors.TEXT_SECONDARY), (lx, ly))
        ly += scale_y(14)

        # Max weight
        weight_text = f"Max Weight: {wc['max_weight']}"
        screen.blit(self.small_font.render(weight_text, True, Colors.TEXT_SECONDARY), (lx, ly))
        ly += scale_y(14)

        # Slot counts
        slot_text = (
            f"Weapon: {ship_type.weapon_slots} | "
            f"Defense: {ship_type.defense_slots} | "
            f"Utility: {ship_type.utility_slots}"
        )
        screen.blit(self.small_font.render(slot_text, True, Colors.TEXT), (lx, ly))
        ly += scale_y(18)

        # Description (word-wrapped in left column)
        desc = ship_type.description
        self._render_wrapped_text(screen, desc, lx, ly, lw, Colors.TEXT_SECONDARY)

        # ============================================================
        # RIGHT COLUMN: stats table, price section
        # ============================================================
        rx = divider_x + pad
        ry = content_top

        # Stats header
        stats_label = self.small_font.render("Stats:", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(stats_label, (rx, ry))
        ry += stats_label.get_height() + scale_y(4)

        # Column positions (relative to right column)
        col_new_x = rx + scale_x(90)
        col_diff_x = rx + scale_x(155)

        hdr_new = self.small_font.render("New", True, Colors.TEXT_SECONDARY)
        hdr_diff = self.small_font.render("Current", True, Colors.TEXT_SECONDARY)
        screen.blit(hdr_new, (col_new_x, ry))
        screen.blit(hdr_diff, (col_diff_x, ry))
        ry += scale_y(16)

        stat_rows = [
            ("Cargo", ship_type.cargo_capacity, current.cargo_capacity),
            ("Fuel", ship_type.fuel_capacity, current.fuel_capacity),
            ("Hull", ship_type.combat_hull, current.combat_hull),
            ("Shields", ship_type.combat_shields, current.combat_shields),
            ("Evasion", ship_type.combat_evasion, current.combat_evasion),
            ("Speed", ship_type.combat_speed, current.combat_speed),
        ]

        for label, new_val, old_val in stat_rows:
            screen.blit(self.small_font.render(label, True, Colors.TEXT), (rx, ry))
            screen.blit(self.small_font.render(str(new_val), True, Colors.TEXT), (col_new_x, ry))

            diff = new_val - old_val
            if diff > 0:
                diff_color = Colors.GREEN
                diff_text = f"+{diff}"
            elif diff < 0:
                diff_color = Colors.RED
                diff_text = str(diff)
            else:
                diff_color = Colors.TEXT_SECONDARY
                diff_text = "="
            screen.blit(self.small_font.render(diff_text, True, diff_color), (col_diff_x, ry))
            ry += scale_y(15)

        ry += scale_y(8)

        # Separator before price
        pygame.draw.line(screen, (40, 48, 65), (rx, ry), (dx + dw - pad, ry), 1)
        ry += scale_y(8)

        # Price section (right column, bottom)
        if locked:
            lock_surf = self.small_font.render(f"LOCKED: {lock_reason}", True, (180, 80, 80))
            screen.blit(lock_surf, (rx, ry))
        else:
            net_cost = ship_type.purchase_price - current.resale_value
            can_afford = net_cost <= self.player.credits
            price_color = Colors.SUCCESS if can_afford else Colors.RED

            price_line = f"Price: {ship_type.purchase_price:,} CR"
            trade_line = f"Trade-in: -{current.resale_value:,} CR"
            net_line = f"Net cost: {net_cost:,} CR"

            screen.blit(self.small_font.render(price_line, True, Colors.TEXT), (rx, ry))
            ry += scale_y(15)
            screen.blit(self.small_font.render(trade_line, True, Colors.TEXT_SECONDARY), (rx, ry))
            ry += scale_y(15)
            screen.blit(self.info_font.render(net_line, True, price_color), (rx, ry))

    def _render_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
        color: tuple,
    ) -> int:
        """Render word-wrapped text, return total height used."""
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if self.small_font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i, line in enumerate(lines[:3]):  # Max 3 lines
            surf = self.small_font.render(line, True, color)
            screen.blit(surf, (x, y + i * scale_y(18)))
        return len(lines) * scale_y(18)

    # ========================================================================
    # Shop tab
    # ========================================================================

    def _buy_selected_part(self) -> None:
        """Purchase the selected ShipPart into inventory."""
        parts = self._get_filtered_parts()
        if not parts or self.selected_upgrade_idx >= len(parts):
            return

        part = parts[self.selected_upgrade_idx]

        if part.base_cost > self.player.credits:
            self._show_message(
                f"Cannot afford {part.name} ({part.base_cost:,} CR, "
                f"need {part.base_cost - self.player.credits:,} more)"
            )
            try:
                get_audio_manager().play_sfx("ui_error")
            except Exception:
                pass
            return

        self.player.deduct_credits(part.base_cost)
        self.player.add_part(part.id)
        self._show_message(f"Bought {part.name} for {part.base_cost:,} CR")

        try:
            get_audio_manager().play_sfx("trade_buy")
        except Exception:
            pass
        cx = self._FRAME_LIST_X + self._FRAME_LIST_W // 2
        cy = _LIST_Y + self.selected_upgrade_idx * self._PART_CARD_SPACING - self._scroll_offset
        self.particles.emit(cx, cy, PURCHASE_FLASH)

    def _render_shop(self, screen: pygame.Surface) -> None:
        header = self.info_font.render("AVAILABLE UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, scale_y(140)))

        shop = self._get_shop_list()
        self._render_item_list(screen, shop, show_price=True)

        if not shop:
            empty = self.info_font.render("All upgrades installed!", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    # ========================================================================
    # Installed tab
    # ========================================================================

    def _render_installed(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("INSTALLED UPGRADES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, 110))

        installed = self.upgrade_manager.installed
        self._render_item_list(screen, installed, show_price=False)

        if not installed:
            empty = self.info_font.render("No upgrades installed", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (40, 160))

    # ========================================================================
    # Shared card list renderer
    # ========================================================================

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

            # Check if locked (shop only)
            locked = False
            lock_reason = ""
            if show_price:
                locked, lock_reason = self._is_upgrade_locked(upgrade)

            # Styled card with gradient
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if locked:
                card_surf.fill((12, 12, 20, 200))
            elif is_selected:
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(28 + 12 * t)
                    g = int(38 + 12 * t)
                    b = int(58 + 12 * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            border_color = (
                (60, 30, 30) if locked else (Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72))
            )
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            # Upgrade icon (small, left of name)
            icon = self._sprite_mgr.get_upgrade_icon(upgrade.id, scale=res_scale(2))
            icon_offset = 0
            if icon:
                screen.blit(icon, (rect.x + 6, rect.y + 4))
                icon_offset = icon.get_width() + 4

            if show_price:
                if locked:
                    # Locked upgrade display
                    name = self.info_font.render(upgrade.name, True, (80, 60, 60))
                    screen.blit(name, (rect.x + 10 + icon_offset, rect.y + 5))
                    lock_surf = self.small_font.render(lock_reason, True, (180, 80, 80))
                    screen.blit(lock_surf, (rect.x + 10, rect.y + 50))
                    price = self.info_font.render(f"{upgrade.price:,} CR", True, (80, 60, 60))
                    screen.blit(price, (rect.right - price.get_width() - 10, rect.y + 5))
                else:
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
                # Installed tab — show mark indicator
                mark_label = self._get_mark_label(upgrade.id)
                inst = self.upgrade_manager.get_installed(upgrade.id)
                mark = inst.mark if inst else 1
                mark_color = _MARK_COLORS.get(mark, Colors.TEXT_SECONDARY)

                name = self.info_font.render(upgrade.name, True, Colors.TEXT)
                screen.blit(name, (rect.x + 10 + icon_offset, rect.y + 5))

                # Mark badge
                if mark_label:
                    mark_surf = self.small_font.render(mark_label, True, mark_color)
                    screen.blit(
                        mark_surf, (rect.x + 14 + icon_offset + name.get_width(), rect.y + 8)
                    )

                # Refund and enhance cost info
                refund = upgrade.price // 2
                right_text_parts = [f"Refund: {refund:,} CR"]
                if inst and inst.mark < upgrade.max_mark:
                    next_cost = self._get_enhance_cost(upgrade, inst.mark + 1)
                    right_text_parts.append(f"Enhance: {next_cost:,} CR")
                right_text = "  |  ".join(right_text_parts)
                right_surf = self.small_font.render(right_text, True, Colors.TEXT_SECONDARY)
                screen.blit(right_surf, (rect.right - right_surf.get_width() - 10, rect.y + 5))

                # Status line
                if inst and inst.mark >= upgrade.max_mark:
                    status = self.small_font.render("MAX MARK", True, (255, 200, 80))
                else:
                    status = self.small_font.render("ACTIVE", True, Colors.SUCCESS)
                screen.blit(status, (rect.x + 10, rect.y + 50))

                # Show effective bonus
                if upgrade.bonus_type and upgrade.bonus_value > 0:
                    multiplier = MARK_MULTIPLIERS.get(mark, 1.0)
                    effective = upgrade.bonus_value * multiplier
                    bonus_text = f"{upgrade.bonus_type}: {effective:.1f}"
                    if inst and inst.tuning:
                        opt = upgrade.get_tuning_option(inst.tuning)
                        if opt:
                            tuning_val = opt["bonus_value"]
                            if mark >= 3:
                                tuning_val *= 2.0
                            bonus_text += f" + {opt['bonus_type']}: {tuning_val:.1f}"
                    bonus_surf = self.small_font.render(bonus_text, True, mark_color)
                    screen.blit(bonus_surf, (rect.x + 80, rect.y + 50))

            # Truncate description to card width
            desc_text = upgrade.description
            desc = self.small_font.render(
                desc_text, True, Colors.TEXT_SECONDARY if not locked else (50, 45, 45)
            )
            max_desc_w = rect.width - 20
            if desc.get_width() > max_desc_w:
                while len(desc_text) > 3 and desc.get_width() > max_desc_w:
                    desc_text = desc_text[:-1]
                desc_text = desc_text.rstrip() + ".."
                desc = self.small_font.render(
                    desc_text, True, Colors.TEXT_SECONDARY if not locked else (50, 45, 45)
                )
            screen.blit(desc, (rect.x + 10, rect.y + 30))

        screen.set_clip(old_clip)

        # Scroll indicator
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
