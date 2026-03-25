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
from spacegame.engine.particles import SPARK_BURST, ParticleConfig, ParticlePool
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.player import Player
from spacegame.models.ship import ShipType
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
        self.viewing: str = "frames"  # Default to frames tab

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
        self.frames_tab: Optional[pygame_gui.elements.UIButton] = None
        self.shop_tab: Optional[pygame_gui.elements.UIButton] = None
        self.installed_tab: Optional[pygame_gui.elements.UIButton] = None
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
        self._parts_hide_owned = True  # Default: hide owned parts to reduce clutter
        self._load_ship_anim()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    # Tab subtitle descriptions (rendered below buttons)
    _TAB_SUBTITLES: dict[str, str] = {
        "drydock": "Design Your Ship",
        "frames": "Unlock Larger Hulls",
        "parts": "Module Blueprints",
        "shop": "Buy & Manage Equipment",
    }

    def _create_ui(self) -> None:
        tab_w = 110
        tab_gap = 8
        total_tab_w = tab_w * 4 + tab_gap * 3
        btn_x = WINDOW_WIDTH // 2 - total_tab_w // 2
        self.drydock_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, 70, tab_w, 35),
            text="Drydock",
            manager=self.ui_manager,
        )
        self.frames_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + (tab_w + tab_gap), 70, tab_w, 35),
            text="Frames",
            manager=self.ui_manager,
        )
        self.parts_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + (tab_w + tab_gap) * 2, 70, tab_w, 35),
            text="Parts",
            manager=self.ui_manager,
        )
        self.shop_tab = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x + (tab_w + tab_gap) * 3, 70, tab_w, 35),
            text="Equipment",
            manager=self.ui_manager,
        )
        self.installed_tab = None  # Retired — equipment managed in Drydock EQUIP mode
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
            self.frames_tab,
            getattr(self, "parts_tab", None),
            self.shop_tab,
            self.installed_tab,
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
        if self.viewing == "frames":
            return self._get_ship_list()
        if self.viewing == "parts":
            return self._get_station_parts()
        if self.viewing == "shop":
            return self._get_shop_list()
        return self.upgrade_manager.installed

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
            elif event.ui_element == self.frames_tab:
                self.viewing = "frames"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif hasattr(self, "parts_tab") and event.ui_element == self.parts_tab:
                self.viewing = "parts"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.shop_tab:
                self.viewing = "shop"
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
            elif event.ui_element == self.buy_button:
                if self.viewing == "parts":
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
            # Parts toggle click
            if (
                self.viewing == "parts"
                and hasattr(self, "_parts_toggle_rect")
                and self._parts_toggle_rect.collidepoint(event.pos)
            ):
                self._parts_hide_owned = not self._parts_hide_owned
                self.selected_upgrade_idx = 0
                self._scroll_offset = 0
                return
            if not self._tuning_mode:
                self._handle_item_click(event.pos)

        elif event.type == pygame.MOUSEWHEEL:
            if not self._tuning_mode:
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
        if self.viewing == "frames":
            list_x = self._FRAME_LIST_X
            card_w = self._FRAME_LIST_W
            card_h = self._FRAME_CARD_H
            card_spacing = self._FRAME_CARD_SPACING
        elif self.viewing == "parts":
            list_x = 30
            card_w = WINDOW_WIDTH - 60
            card_h = scale_y(52)
            card_spacing = scale_y(52)
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
        if self.viewing == "frames":
            return self._FRAME_CARD_H, self._FRAME_CARD_SPACING
        if self.viewing == "parts":
            parts_h = scale_y(52)
            return parts_h, parts_h
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
        is_installed = False  # Retired — equipment managed in Drydock EQUIP mode
        is_frames = self.viewing == "frames"

        is_parts = self.viewing == "parts"
        if self.buy_button:
            self.buy_button.visible = (is_shop or is_parts) and not self._tuning_mode
        if self.uninstall_button:
            self.uninstall_button.visible = is_installed and not self._tuning_mode
        if self.enhance_button:
            self.enhance_button.visible = is_installed and not self._tuning_mode
        if self.buy_ship_button:
            self.buy_ship_button.visible = is_frames and not self._tuning_mode

        # Tuning buttons
        if self.tuning_btn_a:
            self.tuning_btn_a.visible = self._tuning_mode
        if self.tuning_btn_b:
            self.tuning_btn_b.visible = self._tuning_mode
        if self.tuning_cancel:
            self.tuning_cancel.visible = self._tuning_mode

        if self.viewing == "frames":
            self._render_frames(screen)
        elif self.viewing == "parts":
            self._render_parts(screen)
        elif self.viewing == "shop":
            self._render_shop(screen)
        elif self.viewing == "installed":
            # Legacy fallback — redirect to shop
            self._render_shop(screen)
        else:
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

    def _render_tab_indicators(self, screen: pygame.Surface) -> None:
        """Render active tab underline and subtitle text below each tab."""
        tab_w = 110
        tab_gap = 8
        total_tab_w = tab_w * 4 + tab_gap * 3
        btn_x = WINDOW_WIDTH // 2 - total_tab_w // 2
        tab_info = [
            ("drydock", btn_x, self.drydock_tab),
            ("frames", btn_x + (tab_w + tab_gap), self.frames_tab),
            ("parts", btn_x + (tab_w + tab_gap) * 2, getattr(self, "parts_tab", None)),
            ("shop", btn_x + (tab_w + tab_gap) * 3, self.shop_tab),
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
        """Render detail panel for the selected frame on the right side."""
        if not ships or self.selected_upgrade_idx >= len(ships):
            return

        ship_type = ships[self.selected_upgrade_idx]
        current = self.player.ship.ship_type
        locked, lock_reason = self._is_ship_locked(ship_type)

        dx = self._FRAME_DETAIL_X
        dw = self._FRAME_DETAIL_W
        dy = _LIST_Y - scale_y(10)

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

        cx = dx + scale_x(20)  # Content left margin
        cy = dy + scale_y(16)  # Start y

        # Frame name (large)
        name = self.header_font.render(ship_type.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name, (cx, cy))
        cy += scale_y(30)

        # Frame size label
        frame_label = self._get_frame_size_label(ship_type)
        frame_surf = self.info_font.render(frame_label, True, Colors.TEXT_SECONDARY)
        screen.blit(frame_surf, (cx, cy))
        cy += scale_y(28)

        # Canvas visualization — show grid outline representing the weight class
        wc_name = self._CLASS_TO_WEIGHT.get(ship_type.ship_class, "small")
        from spacegame.models.ship_build import WEIGHT_CLASSES

        wc = WEIGHT_CLASSES.get(wc_name, WEIGHT_CLASSES["small"])
        canvas_w = wc.get("canvas_w", 32)
        canvas_h = wc.get("canvas_h", 32)

        # Draw scaled grid preview
        max_preview_w = dw - scale_x(50)
        max_preview_h = scale_y(120)
        pixel_size = min(max_preview_w // canvas_w, max_preview_h // canvas_h, 6)
        grid_w = canvas_w * pixel_size
        grid_h = canvas_h * pixel_size
        grid_x = cx
        grid_y = cy

        # Grid background
        grid_surf = pygame.Surface((grid_w, grid_h), pygame.SRCALPHA)
        grid_surf.fill((20, 28, 45, 180))
        screen.blit(grid_surf, (grid_x, grid_y))
        pygame.draw.rect(screen, (50, 60, 90), (grid_x, grid_y, grid_w, grid_h), 1)

        # Grid dots for visual texture
        for gx in range(0, canvas_w, 4):
            for gy in range(0, canvas_h, 4):
                screen.set_at((grid_x + gx * pixel_size, grid_y + gy * pixel_size), (40, 50, 70))

        # Canvas dimensions label
        dim_text = f"{canvas_w} x {canvas_h} grid  |  Max weight: {wc['max_weight']}"
        dim_surf = self.small_font.render(dim_text, True, Colors.TEXT_SECONDARY)
        screen.blit(dim_surf, (grid_x, grid_y + grid_h + 4))
        cy = grid_y + grid_h + scale_y(28)

        # Separator
        pygame.draw.line(screen, (40, 48, 65), (cx, cy), (dx + dw - scale_x(20), cy), 1)
        cy += scale_y(12)

        # Stat comparison table
        stat_rows = [
            ("Cargo", ship_type.cargo_capacity, current.cargo_capacity),
            ("Fuel", ship_type.fuel_capacity, current.fuel_capacity),
            ("Hull", ship_type.combat_hull, current.combat_hull),
            ("Shields", ship_type.combat_shields, current.combat_shields),
            ("Evasion", ship_type.combat_evasion, current.combat_evasion),
            ("Speed", ship_type.combat_speed, current.combat_speed),
        ]

        # Column headers
        col_label_x = cx
        col_new_x = cx + scale_x(120)
        col_diff_x = cx + scale_x(200)

        hdr_label = self.small_font.render("Stat", True, Colors.TEXT_SECONDARY)
        hdr_new = self.small_font.render("New", True, Colors.TEXT_SECONDARY)
        hdr_diff = self.small_font.render("vs Current", True, Colors.TEXT_SECONDARY)
        screen.blit(hdr_label, (col_label_x, cy))
        screen.blit(hdr_new, (col_new_x, cy))
        screen.blit(hdr_diff, (col_diff_x, cy))
        cy += scale_y(20)

        for label, new_val, old_val in stat_rows:
            # Label
            label_surf = self.small_font.render(label, True, Colors.TEXT)
            screen.blit(label_surf, (col_label_x, cy))

            # New value
            val_surf = self.small_font.render(str(new_val), True, Colors.TEXT)
            screen.blit(val_surf, (col_new_x, cy))

            # Diff
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
            diff_surf = self.small_font.render(diff_text, True, diff_color)
            screen.blit(diff_surf, (col_diff_x, cy))

            cy += scale_y(18)

        cy += scale_y(6)

        # Slot comparison
        slot_text = (
            f"Weapon: {ship_type.weapon_slots}  "
            f"Defense: {ship_type.defense_slots}  "
            f"Utility: {ship_type.utility_slots}"
        )
        slot_surf = self.small_font.render(slot_text, True, Colors.TEXT)
        screen.blit(slot_surf, (cx, cy))
        cy += scale_y(22)

        # Separator
        pygame.draw.line(screen, (40, 48, 65), (cx, cy), (dx + dw - scale_x(20), cy), 1)
        cy += scale_y(10)

        # Description (word-wrapped)
        desc = ship_type.description
        max_text_w = dw - scale_x(40)
        desc_height = self._render_wrapped_text(
            screen, desc, cx, cy, max_text_w, Colors.TEXT_SECONDARY
        )
        cy += desc_height + scale_y(8)

        # Price section
        if locked:
            lock_surf = self.info_font.render(f"LOCKED: {lock_reason}", True, (180, 80, 80))
            screen.blit(lock_surf, (cx, cy))
        else:
            net_cost = ship_type.purchase_price - current.resale_value
            can_afford = net_cost <= self.player.credits
            price_color = Colors.SUCCESS if can_afford else Colors.RED

            price_line = f"Price: {ship_type.purchase_price:,} CR"
            trade_line = f"Trade-in: -{current.resale_value:,} CR"
            net_line = f"Net cost: {net_cost:,} CR"

            screen.blit(self.small_font.render(price_line, True, Colors.TEXT), (cx, cy))
            cy += scale_y(18)
            screen.blit(self.small_font.render(trade_line, True, Colors.TEXT_SECONDARY), (cx, cy))
            cy += scale_y(18)
            screen.blit(self.info_font.render(net_line, True, price_color), (cx, cy))

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

    # ------------------------------------------------------------------
    # Parts Tab (Phase 12 — Module Blueprints)
    # ------------------------------------------------------------------

    def _get_station_parts(self) -> list:
        """Get module blueprints available at the current station, filtered by owned toggle."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.build_sharing import get_station_modules

        dl = get_data_loader()
        catalogs = getattr(dl, "drydock_catalogs", {})
        module_catalog = getattr(dl, "ship_modules", {})
        all_parts = get_station_modules(self.player.current_system_id, catalogs, module_catalog)
        if getattr(self, "_parts_hide_owned", False):
            return [p for p in all_parts if p.id not in self.player.unlocked_modules]
        return all_parts

    def _get_station_price_modifier(self) -> float:
        """Get the price modifier for the current station."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        catalogs = getattr(dl, "drydock_catalogs", {})
        entry = catalogs.get(self.player.current_system_id, {})
        return entry.get("price_modifier", 1.0)

    def _render_parts(self, screen: pygame.Surface) -> None:
        """Render the module blueprint parts shop."""
        header = self.header_font.render("MODULE BLUEPRINTS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (40, scale_y(140)))

        # Show/Hide owned toggle
        hide_owned = getattr(self, "_parts_hide_owned", False)
        toggle_label = "Show Owned" if hide_owned else "Hide Owned"
        toggle_color = Colors.TEXT_SECONDARY if hide_owned else Colors.GREEN
        toggle_bg = (30, 35, 50) if hide_owned else (25, 45, 35)
        toggle_w = scale_x(110)
        toggle_h = scale_y(24)
        toggle_x = WINDOW_WIDTH - toggle_w - 40
        toggle_y = scale_y(142)
        toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
        pygame.draw.rect(screen, toggle_bg, toggle_rect, border_radius=3)
        pygame.draw.rect(screen, toggle_color, toggle_rect, 1, border_radius=3)
        tl_surf = self.small_font.render(toggle_label, True, toggle_color)
        screen.blit(tl_surf, (toggle_x + toggle_w // 2 - tl_surf.get_width() // 2, toggle_y + 3))
        self._parts_toggle_rect = toggle_rect

        parts = self._get_station_parts()
        if not parts:
            msg = (
                "All blueprints owned!"
                if hide_owned
                else "No module blueprints available at this station."
            )
            empty = self.info_font.render(msg, True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (60, scale_y(180)))
            return

        price_mod = self._get_station_price_modifier()
        hud_h = scale_y(HUD_BASE_HEIGHT)
        list_y = _LIST_Y
        list_h = WINDOW_HEIGHT - hud_h - list_y - scale_y(80)
        card_h = scale_y(52)
        # Clamp selection and scroll
        self.selected_upgrade_idx = max(0, min(self.selected_upgrade_idx, len(parts) - 1))

        from spacegame.data_loader import get_data_loader

        materials = getattr(get_data_loader(), "hull_materials", {})

        for i, module in enumerate(parts):
            card_y = list_y + (i * card_h) - self._scroll_offset
            if card_y + card_h < list_y or card_y > list_y + list_h:
                continue

            is_selected = i == self.selected_upgrade_idx
            is_owned = module.id in self.player.unlocked_modules
            is_locked = module.unlock_method not in ("purchase", "free")

            # Card background
            if is_selected:
                bg = (35, 55, 90)
            elif is_owned:
                bg = (20, 35, 25)
            else:
                bg = (18, 22, 35)
            pygame.draw.rect(
                screen, bg, (30, card_y, WINDOW_WIDTH - 60, card_h - 2), border_radius=4
            )
            if is_selected:
                border = Colors.TEXT_HIGHLIGHT if not is_locked else (150, 80, 80)
                pygame.draw.rect(
                    screen, border, (30, card_y, WINDOW_WIDTH - 60, card_h - 2), 1, border_radius=4
                )

            # Module mini-preview
            preview_size = scale_y(22)
            px_start = 40
            py_start = card_y + 4
            pw, ph = module.width, module.height
            if pw > 0 and ph > 0:
                ps = min(preview_size / pw, preview_size / ph)
                for lx, ly, char in module.filled_pixels():
                    mat_id = module.material_map.get(char, "")
                    mat = materials.get(mat_id)
                    color = mat.color_primary if mat else (100, 100, 100)
                    if is_locked:
                        avg = (color[0] + color[1] + color[2]) // 3
                        color = (avg // 2, avg // 2, avg // 2)
                    rx = int(px_start + lx * ps)
                    ry = int(py_start + ly * ps)
                    rw = max(1, int(ps))
                    pygame.draw.rect(screen, color, (rx, ry, rw, rw))

            # Name and manufacturer
            text_x = 48 + preview_size
            cat_colors = {
                "cockpit": (100, 180, 255),
                "engine": (255, 180, 80),
                "weapon": (255, 80, 80),
                "shield": (80, 220, 255),
                "cargo": (255, 220, 80),
                "utility": (80, 255, 120),
                "structural": (160, 160, 180),
                "crew": (120, 200, 120),
                "reactor": (180, 100, 240),
            }
            name_color = Colors.TEXT_PRIMARY if not is_locked else (80, 80, 90)
            name_surf = self.info_font.render(module.name, True, name_color)
            screen.blit(name_surf, (text_x, card_y + 4))

            mfg = module.manufacturer.replace("_", " ").title()
            cat = module.category.upper()
            cat_color = cat_colors.get(module.category, Colors.TEXT_SECONDARY)
            if is_locked:
                cat_color = (60, 60, 70)
            detail = self.small_font.render(f"{cat}  {mfg}  W:{module.weight:.1f}", True, cat_color)
            screen.blit(detail, (text_x, card_y + 20))

            # Right side: price or status
            right_x = WINDOW_WIDTH - 180
            if is_owned:
                owned_surf = self.info_font.render("\u2713 OWNED", True, Colors.GREEN)
                screen.blit(owned_surf, (right_x, card_y + 8))
            elif is_locked:
                lock_method = module.unlock_method.replace("_", " ").title()
                lock_surf = self.small_font.render(f"\U0001f512 {lock_method}", True, (150, 80, 80))
                screen.blit(lock_surf, (right_x, card_y + 4))
                if module.unlock_source:
                    src = module.unlock_source.replace("_", " ").title()
                    src_surf = self.small_font.render(src, True, (120, 70, 70))
                    screen.blit(src_surf, (right_x, card_y + 18))
            else:
                price = int(module.unlock_cost * price_mod)
                affordable = self.player.credits >= price
                price_color = Colors.TEXT_PRIMARY if affordable else (200, 80, 80)
                price_surf = self.info_font.render(f"{price:,} CR", True, price_color)
                screen.blit(price_surf, (right_x, card_y + 8))

            # Description (truncated)
            if is_selected and module.description:
                desc = module.description[:80]
                desc_surf = self.small_font.render(desc, True, Colors.TEXT_SECONDARY)
                screen.blit(desc_surf, (text_x, card_y + 34))

    def _buy_selected_part(self) -> None:
        """Purchase the selected module blueprint."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.build_sharing import purchase_module_blueprint

        parts = self._get_station_parts()
        if not parts or self.selected_upgrade_idx >= len(parts):
            return

        module = parts[self.selected_upgrade_idx]
        dl = get_data_loader()
        module_catalog = getattr(dl, "ship_modules", {})
        price_mod = self._get_station_price_modifier()

        ok, msg = purchase_module_blueprint(self.player, module.id, module_catalog, price_mod)
        if ok:
            self._show_message(msg)
            try:
                get_audio_manager().play_sfx("trade_buy")
            except Exception:
                pass
            cx = WINDOW_WIDTH - 100
            cy = 140 + self.selected_upgrade_idx * scale_y(52) - self._scroll_offset
            self.particles.emit(cx, cy, SPARK_BURST)
        else:
            self._show_message(msg)
            try:
                get_audio_manager().play_sfx("ui_error")
            except Exception:
                pass

    def _render_shop(self, screen: pygame.Surface) -> None:
        header = self.header_font.render("AVAILABLE UPGRADES", True, Colors.TEXT_HIGHLIGHT)
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
