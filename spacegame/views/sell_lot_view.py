"""SA-B5: SellLotView — player consignment screen at the Stellaris floor.

A two-pane view: the left pane lists eligible cargo + parts the player
can consign, the right pane is the listing form (declared appraisal,
reserve-pct, fee preview, confirm). The view writes to
``Player.auction_state.create_listing(...)`` and routes back to
``GameState.AUCTION`` on confirm or back.

Empty state, loading state, error state are handled per
``views/CLAUDE.md``. The first-time tip overlay (PT-M pattern) explains
that the listing fee is non-refundable and that the reserve is the
"no thanks" floor.
"""

from __future__ import annotations

from typing import Any, Optional

import pygame
import pygame_gui

from spacegame.config import (
    LISTING_RESERVE_PCT_DEFAULT,
    LISTING_RESERVE_PCT_MAX,
    LISTING_RESERVE_PCT_MIN,
    MAX_ACTIVE_LISTINGS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.constants.flags import (
    auction_first_listing_created,
    seen_first_listing_tip,
)
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SUBTITLE,
    FONT_TITLE,
    get_font,
)
from spacegame.models.bidding import (
    compute_listing_fee,
    stellaris_tier_for_standing,
)
from spacegame.models.bidding_lot import LOT_CATEGORY_FACTION_COMMODITY
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

# --- Tutorial overlay copy (decision §B5.11) -------------------------
TIP_TITLE = "Consign a Lot"
TIP_BODY = "Listing fee is charged whether the lot sells or not. Set a reserve to refuse low bids."


# --- Layout constants ------------------------------------------------
PANEL_X = scale_x(60)
PANEL_W = WINDOW_WIDTH - scale_x(120)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)
BODY_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BTN_W = scale_x(160)
BTN_H = scale_y(36)
LIST_PANE_W = scale_x(360)
RESERVE_STEP = 0.05


class SellLotView(BaseView):
    """Player-as-seller consignment screen at the Stellaris Auction House."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
    ) -> None:
        """Initialize the SellLotView.

        Args:
            ui_manager: Active pygame_gui UIManager.
            player: Player whose auction_state we mutate on confirm.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.body_font = get_font("dialogue", FONT_BODY)
        self.label_font = get_font("label", FONT_SUBTITLE)
        self.value_font = get_font("stats", FONT_LG)

        # UI element refs
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.confirm_button: Optional[pygame_gui.elements.UIButton] = None
        self.appraisal_field: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.reserve_down_button: Optional[pygame_gui.elements.UIButton] = None
        self.reserve_up_button: Optional[pygame_gui.elements.UIButton] = None
        self._item_buttons: list[tuple[dict[str, Any], pygame_gui.elements.UIButton]] = []

        # Form state
        self.declared_appraisal: int = 0
        self.reserve_pct: float = LISTING_RESERVE_PCT_DEFAULT
        self.selected_item: Optional[dict[str, Any]] = None
        self.error_message: Optional[str] = None

        # First-time tip overlay (PT-M pattern, mirrors AuctionView).
        self._tip_overlay: Optional[FirstTimeTipOverlay] = None

        # Engine callback fired on first successful listing (mirrors
        # on_player_lot_sold in AuctionView). The engine uses this to
        # trigger the auto_auction_first_listing_created journal entry.
        self.on_listing_created: Optional[Any] = None

        # Voice templates injected by the engine.
        self._voice_templates: dict[str, Any] = {}

        # Background — neutral station theme.
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=8643)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(150)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered SellLotView")
        self._maybe_show_tip()
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        self._tip_overlay = None
        super().on_exit()

    def _maybe_show_tip(self) -> None:
        """Fire the FirstTimeTipOverlay on first entry per save."""
        if self.player.dialogue_flags.get(seen_first_listing_tip()):
            return

        def _on_dismiss() -> None:
            self.player.dialogue_flags[seen_first_listing_tip()] = True

        self._tip_overlay = FirstTimeTipOverlay(
            title=TIP_TITLE,
            body=TIP_BODY,
            on_dismiss=_on_dismiss,
        )

    # ------------------------------------------------------------------
    # External setters (engine wiring)
    # ------------------------------------------------------------------

    def set_voice_templates(self, templates: dict[str, Any]) -> None:
        """Install voice templates loaded from data/auctions/stellaris_voices.json."""
        self._voice_templates = dict(templates) if templates else {}

    # ------------------------------------------------------------------
    # Tier / eligibility gates
    # ------------------------------------------------------------------

    def is_tier_locked(self) -> bool:
        """Return True when the player's Stellaris standing is below regular."""
        rep = self.player.faction_reputation.get("stellaris_commerce_guild", 0)
        tier = stellaris_tier_for_standing(rep)
        return tier in ("apprentice", "none")

    def get_eligible_items(self) -> list[dict[str, Any]]:
        """Return the list of consignable items (cargo + parts).

        Each row is a dict with ``item_kind``, ``item_id``, ``quantity``,
        ``label``. Excludes ``unlocked_modules`` (boss-drop legendary set
        per locked decision §B5.1).
        """
        rows: list[dict[str, Any]] = []
        # Cargo commodities.
        for cid, qty in self.player.ship.current_cargo.items():
            if qty <= 0:
                continue
            label = f"{cid.replace('_', ' ').title()} (cargo, {qty})"
            rows.append(
                {
                    "item_kind": "commodity",
                    "item_id": cid,
                    "quantity": qty,
                    "label": label,
                }
            )
        # Parts inventory — excluding any boss-drop legendary modules.
        unlocked: set[str] = getattr(self.player, "unlocked_modules", set())
        for pid, qty in self.player.parts_inventory.items():
            if qty <= 0:
                continue
            if pid in unlocked:
                continue
            label = f"{pid.replace('_', ' ').title()} (part, {qty})"
            rows.append(
                {
                    "item_kind": "part",
                    "item_id": pid,
                    "quantity": qty,
                    "label": label,
                }
            )
        return rows

    def empty_state_line(self) -> str:
        """Return the Velo empty-inventory line, or a sane fallback."""
        block = self._voice_templates.get("consigned_lot_lines") or {}
        line = block.get("empty_inventory") if isinstance(block, dict) else None
        if isinstance(line, str) and line:
            return line
        return "Nothing on consignment from your hand today."

    # ------------------------------------------------------------------
    # Form mutators
    # ------------------------------------------------------------------

    def set_declared_appraisal(self, value: int) -> None:
        """Set the declared appraisal; non-positive values are kept as-is."""
        self.declared_appraisal = int(value) if value > 0 else 0
        self.error_message = None

    def set_reserve_pct(self, value: float) -> None:
        """Clamp ``value`` into the locked [0.50, 0.95] reserve band."""
        clamped = max(LISTING_RESERVE_PCT_MIN, min(LISTING_RESERVE_PCT_MAX, value))
        self.reserve_pct = clamped
        self.error_message = None

    def select_item(self, item_kind: str, item_id: str) -> None:
        """Select a row from the eligible-items list."""
        for row in self.get_eligible_items():
            if row["item_kind"] == item_kind and row["item_id"] == item_id:
                self.selected_item = row
                self.error_message = None
                return

    # ------------------------------------------------------------------
    # Confirm gating + flow
    # ------------------------------------------------------------------

    def fee_preview(self) -> int:
        """Return the live fee preview based on the current declared appraisal."""
        return compute_listing_fee(self.declared_appraisal)

    def can_confirm_listing(self) -> bool:
        """Return True iff every confirm-gate passes.

        Gates: tier >= regular AND slot count < MAX_ACTIVE_LISTINGS AND
        an item is selected AND declared appraisal > 0 AND reserve in
        the valid band AND credits >= computed fee.
        """
        if self.is_tier_locked():
            return False
        state = self.player.auction_state
        if len(state.active_listings) >= MAX_ACTIVE_LISTINGS:
            return False
        if self.selected_item is None:
            return False
        if self.declared_appraisal <= 0:
            return False
        if not (LISTING_RESERVE_PCT_MIN <= self.reserve_pct <= LISTING_RESERVE_PCT_MAX):
            return False
        if self.player.credits < self.fee_preview():
            return False
        return True

    def confirm_listing(self) -> tuple[bool, str]:
        """Submit the form via ``AuctionState.create_listing``.

        On success: sets the first-listing flag on its first call,
        clears the form, and routes back to GameState.AUCTION. On
        failure: stores the error message for the error-state UI.
        """
        if self.selected_item is None:
            self.error_message = "Pick an item to consign first."
            return (False, self.error_message)
        ok, msg, _listing = self.player.auction_state.create_listing(
            player=self.player,
            item_kind=self.selected_item["item_kind"],
            item_id=self.selected_item["item_id"],
            quantity=1,
            declared_appraisal=self.declared_appraisal,
            reserve_pct=self.reserve_pct,
            current_day=self.player.game_day,
            category=LOT_CATEGORY_FACTION_COMMODITY,
        )
        if not ok:
            self.error_message = msg
            return (False, msg)
        # First-listing flag + engine callback (journal/banter trigger).
        if not self.player.dialogue_flags.get(auction_first_listing_created()):
            self.player.dialogue_flags[auction_first_listing_created()] = True
            if self.on_listing_created is not None:
                self.on_listing_created()
        self.error_message = None
        self.next_state = GameState.AUCTION
        return (True, msg)

    def go_back(self) -> None:
        """Return to the AuctionView without listing anything."""
        self.next_state = GameState.AUCTION

    # ------------------------------------------------------------------
    # UI lifecycle
    # ------------------------------------------------------------------

    def _create_ui(self) -> None:
        self._destroy_ui()
        # Back button (always present).
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + scale_x(20),
                PANEL_TOP_Y + scale_y(20),
                BTN_W,
                BTN_H,
            ),
            text="Leave",
            manager=self.ui_manager,
        )
        if self.is_tier_locked():
            # No form; leave-only UI.
            return
        # Item-selection list (left pane).
        list_x = PANEL_X + scale_x(20)
        list_y = BODY_TOP_Y + scale_y(40)
        for row in self.get_eligible_items():
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(list_x, list_y, LIST_PANE_W, scale_y(28)),
                text=row["label"],
                manager=self.ui_manager,
            )
            self._item_buttons.append((row, btn))
            list_y += scale_y(34)
        # Listing form (right pane).
        form_x = PANEL_X + LIST_PANE_W + scale_x(60)
        form_y = BODY_TOP_Y + scale_y(40)
        self.appraisal_field = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(form_x, form_y, scale_x(180), scale_y(32)),
            manager=self.ui_manager,
        )
        if self.appraisal_field is not None and self.declared_appraisal > 0:
            self.appraisal_field.set_text(str(self.declared_appraisal))
        # Reserve-pct stepper buttons.
        reserve_y = form_y + scale_y(80)
        self.reserve_down_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(form_x, reserve_y, scale_x(40), BTN_H),
            text="-",
            manager=self.ui_manager,
        )
        self.reserve_up_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(form_x + scale_x(140), reserve_y, scale_x(40), BTN_H),
            text="+",
            manager=self.ui_manager,
        )
        # Confirm button (bottom right).
        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(form_x, reserve_y + scale_y(120), BTN_W, BTN_H),
            text="Confirm Listing",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        elements: list[Any] = [
            self.back_button,
            self.confirm_button,
            self.appraisal_field,
            self.reserve_down_button,
            self.reserve_up_button,
        ]
        for elem in elements:
            if elem is not None:
                elem.kill()
        for _row, btn in self._item_buttons:
            btn.kill()
        self._item_buttons = []
        self.back_button = None
        self.confirm_button = None
        self.appraisal_field = None
        self.reserve_down_button = None
        self.reserve_up_button = None

    # ------------------------------------------------------------------
    # Update + render
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.background.update(dt)
        if self._tip_overlay is not None:
            self._tip_overlay.update(dt)
            if self._tip_overlay.dismissed:
                self._tip_overlay = None
        # Pull declared-appraisal value live from the entry field.
        if self.appraisal_field is not None:
            text = self.appraisal_field.get_text().strip()
            if text.isdigit():
                self.set_declared_appraisal(int(text))
            elif text == "":
                self.declared_appraisal = 0

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))
        self._render_panel_chrome(screen)
        if self.is_tier_locked():
            self._render_tier_locked(screen)
            return
        items = self.get_eligible_items()
        if not items:
            self._render_empty_state(screen)
            self._render_form(screen)
            return
        self._render_item_list_header(screen, items)
        self._render_form(screen)
        if self.error_message:
            self._render_error(screen)

    def render_top(self, screen: pygame.Surface) -> None:
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            self._tip_overlay.render(screen)

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_panel_chrome(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            (PANEL_X, PANEL_TOP_Y, PANEL_W, WINDOW_HEIGHT - PANEL_TOP_Y * 2),
            alpha=200,
        )
        title = self.title_font.render("Consign a Lot", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(70)))

    def _render_tier_locked(self, screen: pygame.Surface) -> None:
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        msg = "Stellaris regular standing required."
        self._draw_text(screen, msg, (x, y), color=Colors.YELLOW)

    def _render_empty_state(self, screen: pygame.Surface) -> None:
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        self._draw_text(screen, self.empty_state_line(), (x, y))

    def _render_item_list_header(self, screen: pygame.Surface, items: list[dict[str, Any]]) -> None:
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        header = self.subtitle_font.render(
            f"Eligible items ({len(items)})", True, Colors.TEXT_HIGHLIGHT
        )
        screen.blit(header, (x, y))

    def _render_form(self, screen: pygame.Surface) -> None:
        x = PANEL_X + LIST_PANE_W + scale_x(60)
        y = BODY_TOP_Y
        self._draw_text(
            screen,
            "Declared appraisal (credits):",
            (x, y),
            color=Colors.TEXT_SECONDARY,
        )
        # The actual UITextEntryLine is anchored below via _create_ui.
        y += scale_y(80)
        self._draw_text(
            screen,
            f"Reserve: {int(self.reserve_pct * 100)}% of appraisal",
            (x, y),
            color=Colors.TEXT_SECONDARY,
        )
        y += scale_y(40)
        fee_line = f"Listing fee preview: {self.fee_preview():,} credits"
        self._draw_text(screen, fee_line, (x, y))
        y += scale_y(28)
        if self.selected_item is not None:
            self._draw_text(
                screen,
                f"Selected: {self.selected_item['label']}",
                (x, y),
                color=Colors.TEXT_HIGHLIGHT,
            )

    def _render_error(self, screen: pygame.Surface) -> None:
        x = PANEL_X + scale_x(20)
        y = WINDOW_HEIGHT - PANEL_TOP_Y - scale_y(60)
        self._draw_text(
            screen,
            self.error_message or "",
            (x, y),
            color=Colors.RED,
        )

    def _draw_text(
        self,
        screen: pygame.Surface,
        text: str,
        pos: tuple[int, int],
        color: tuple[int, int, int] = Colors.TEXT_PRIMARY,
    ) -> None:
        surf = self.body_font.render(text, True, color)
        screen.blit(surf, pos)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            consumed = self._tip_overlay.handle_event(event)
            if consumed:
                return
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_button(event.ui_element)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.go_back()

    def _handle_button(self, ui_element: Any) -> None:
        if ui_element == self.back_button:
            self.go_back()
            return
        if ui_element == self.confirm_button:
            self.confirm_listing()
            return
        if ui_element == self.reserve_down_button:
            self.set_reserve_pct(self.reserve_pct - RESERVE_STEP)
            return
        if ui_element == self.reserve_up_button:
            self.set_reserve_pct(self.reserve_pct + RESERVE_STEP)
            return
        for row, btn in self._item_buttons:
            if ui_element == btn:
                self.select_item(row["item_kind"], row["item_id"])
                return

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
