"""SA-B2: Auction venue view.

Single ``BaseView`` subclass with seven internal substates corresponding
to the auction lifecycle (PREVIEW / OPENING / LOT_OPEN / BID_WINDOW /
ROUND_CLOSE / LOT_RESOLUTION / POST_SESSION). Substate transitions
destroy and rebuild the UI panel below the persistent header.

Empty / loading / error states are rendered inside the PREVIEW substate
when ``auction_state`` lacks a populated session: respectively when the
next session is scheduled in the future, while a lot pool is being
generated, or when a data-loading error has been signaled by the engine.

The view consumes Sable's ``auction_bid_visibility`` crew bonus and the
``auction_lot_appraisal_bonus`` skill bonus per design doc §7. Sable's
ceiling estimates use the locked banker's-rounding formula from §11.12.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.constants.flags import auction_sable_ceiling_correct, seen_auction_first_session_tip
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
    PERFECT_READ_THRESHOLD,
    SABLE_CEILING_CORRECT_THRESHOLD,
    AuctionLifecycle,
    post_win_valuation_message,
    reserve_band_for_preview,
    sable_displayed_ceiling,
)
from spacegame.models.bidding_lot import AuctionLot
from spacegame.models.bidding_persona import (
    NAMED_RIVAL_IDS,
    RIVAL_DISPLAY_NAMES,
    AIBidderPersona,
)
from spacegame.models.crew import CrewRoster
from spacegame.models.player import Player
from spacegame.models.progression import PlayerProgression
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

# --- Tutorial overlay copy (design doc §9.1, byte-for-byte) -----------
TIP_TITLE = "Auction Floor"
TIP_BODY = (
    "Three-round ascending bid. Timer hits zero, highest bid takes the lot. "
    "Reserve not met means it does not sell. "
    "Hold to skip a round. Fold to exit a lot entirely."
)


# --- Layout constants -------------------------------------------------
PANEL_X = scale_x(60)
PANEL_W = WINDOW_WIDTH - scale_x(120)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)
BODY_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BTN_W = scale_x(160)
BTN_H = scale_y(36)
SPEED_BTN_W = scale_x(80)


class AuctionSubstate(str, Enum):
    """View-only substate. Driven by the underlying lifecycle."""

    PREVIEW = "preview"
    OPENING = "opening"
    LOT_OPEN = "lot_open"
    BID_WINDOW = "bid_window"
    ROUND_CLOSE = "round_close"
    LOT_RESOLUTION = "lot_resolution"
    POST_SESSION = "post_session"


def _lifecycle_to_substate(lifecycle: AuctionLifecycle) -> AuctionSubstate:
    """Map the model's lifecycle into the view's substate enum."""
    return {
        AuctionLifecycle.SCHEDULED: AuctionSubstate.PREVIEW,
        AuctionLifecycle.PREVIEW: AuctionSubstate.PREVIEW,
        AuctionLifecycle.SESSION_OPEN: AuctionSubstate.OPENING,
        AuctionLifecycle.LOT_OPEN: AuctionSubstate.LOT_OPEN,
        AuctionLifecycle.BID_WINDOW: AuctionSubstate.BID_WINDOW,
        AuctionLifecycle.ROUND_CLOSE: AuctionSubstate.ROUND_CLOSE,
        AuctionLifecycle.LOT_RESOLUTION: AuctionSubstate.LOT_RESOLUTION,
        AuctionLifecycle.SESSION_CLOSE: AuctionSubstate.POST_SESSION,
    }[lifecycle]


class AuctionView(BaseView):
    """Auction venue view shared by Stellaris (SA-B3) and Reach (SA-B4).

    The view keeps no business state of its own. It reads ``Player.auction_state``,
    drives ``tick`` / ``submit_player_bid`` / ``advance_after_resolution``,
    and renders the active substate. UI elements are scoped per substate.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        crew_roster: CrewRoster,
        progression: PlayerProgression,
        venue_id: str,
        venue_display_name: str = "Stellaris Auction House",
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.crew_roster = crew_roster
        self.progression = progression
        self.venue_id = venue_id
        self.venue_display_name = venue_display_name
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.body_font = get_font("dialogue", FONT_BODY)
        self.label_font = get_font("label", FONT_SUBTITLE)
        self.value_font = get_font("stats", FONT_LG)

        # UI element refs (created/destroyed per substate)
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.start_button: Optional[pygame_gui.elements.UIButton] = None
        self.advance_button: Optional[pygame_gui.elements.UIButton] = None
        self.next_lot_button: Optional[pygame_gui.elements.UIButton] = None
        self.raise_min_button: Optional[pygame_gui.elements.UIButton] = None
        self.raise_custom_button: Optional[pygame_gui.elements.UIButton] = None
        self.hold_button: Optional[pygame_gui.elements.UIButton] = None
        self.fold_button: Optional[pygame_gui.elements.UIButton] = None
        self._speed_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._dialog: Optional[pygame_gui.windows.UIConfirmationDialog] = None
        self._custom_amount_text: Optional[pygame_gui.elements.UITextEntryLine] = None

        # Status / feedback messages
        self.messages: list[str] = []
        self._message_timer: float = 0.0

        # First-time tip overlay (PT-M pattern)
        self._tip_overlay: Optional[FirstTimeTipOverlay] = None

        # Loading / error sentinels — set by the engine via setters.
        self._loading: bool = False
        self._error_text: Optional[str] = None

        # Active session personas (engine wires these in via
        # ``set_active_personas``; falls back to the names in
        # ``auction_state.session_personas`` for offline tests).
        self._live_personas: list[AIBidderPersona] = []

        # Custom bid input — gathered via the modal credit-input dialog.
        self._pending_custom_amount: Optional[int] = None

        # SA-B3: voice content (lot-open, "we are at", post-session social,
        # empty-state, retired-rival aside). Populated by the engine via
        # set_voice_templates from data_loader.get_auction_voices(venue).
        # Empty dict falls back to the design-doc default strings already
        # authored inline in the render helpers.
        self._voice_templates: dict[str, Any] = {}
        # Track the high-bid value last announced so the BID_WINDOW Velo
        # commentary updates when the high bid changes.
        self._last_announced_high_bid: int = -1
        # Track which rival ids we've already filed an outbid line for in
        # the active lot. Prevents the bid log from re-announcing the same
        # rival on every tick.
        self._announced_rival_bids: set[str] = set()

        # Substate tracking — last substate we built UI for; recreates
        # when the model lifecycle moves into a different substate.
        self._built_substate: Optional[AuctionSubstate] = None

        # Achievement / banter callbacks the engine wires in to bridge
        # the model's lifecycle hooks with journal / news / achievement
        # systems. Default no-ops keep the view standalone for tests.
        self.on_session_complete: Optional[Callable[[], None]] = None
        self.on_lot_won: Optional[Callable[[AuctionLot, int], None]] = None
        self.on_rivalry_formed: Optional[Callable[[str, AuctionLot], None]] = None
        self.on_headliner_sold: Optional[Callable[[AuctionLot, int], None]] = None
        self.on_headliner_withdrawn: Optional[Callable[[AuctionLot], None]] = None

        # Background — venue-neutral starfield; SA-X10 owns per-venue identity.
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=8642)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        # SA-B4 (locked decision §B4.12): the Reach floor reads dimmer
        # than Stellaris. Alpha 180 vs 150. Accent color sourced from
        # ReachDarkLayout so future palette refinements flow through.
        if venue_id == "crimson_reach":
            from spacegame.views.station_layouts import ReachDarkLayout

            self._bg_dim.set_alpha(180)
            self.venue_accent_color: tuple[int, int, int] = ReachDarkLayout.accent_color
        else:
            self._bg_dim.set_alpha(150)
            self.venue_accent_color = Colors.UI_BORDER

    # ------------------------------------------------------------------
    # External setters (engine wiring)
    # ------------------------------------------------------------------

    def set_loading(self, loading: bool) -> None:
        self._loading = loading

    def set_error(self, error_text: Optional[str]) -> None:
        self._error_text = error_text

    def set_active_personas(self, personas: list[AIBidderPersona]) -> None:
        self._live_personas = list(personas)
        self.player.auction_state.set_session_personas(personas)

    def set_voice_templates(self, templates: dict[str, Any]) -> None:
        """SA-B3: install Velo / rival / Sable / empty-state voice templates.

        Templates are loaded by the engine from
        ``data_loader.get_auction_voices(venue)``. Missing keys fall back
        to design-doc default strings inline in the render helpers, so
        the view never crashes on incomplete content.
        """
        self._voice_templates = dict(templates) if templates else {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Activate the view and fire the first-time tip if unseen."""
        super().on_enter()
        logger.info("Entered AuctionView at venue=%s", self.venue_id)
        self._maybe_show_tip()
        self._rebuild_ui_for_substate()

    def on_exit(self) -> None:
        """Deactivate; tear down UI."""
        self._destroy_all_ui()
        self._tip_overlay = None
        super().on_exit()

    def _maybe_show_tip(self) -> None:
        if self.player.dialogue_flags.get(seen_auction_first_session_tip()):
            return

        def _on_dismiss() -> None:
            self.player.dialogue_flags[seen_auction_first_session_tip()] = True

        self._tip_overlay = FirstTimeTipOverlay(
            title=TIP_TITLE,
            body=TIP_BODY,
            on_dismiss=_on_dismiss,
        )

    # ------------------------------------------------------------------
    # Update / render
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the auction model and rebuild UI on substate change."""
        self.background.update(dt)
        if self._tip_overlay is not None:
            self._tip_overlay.update(dt)
            if self._tip_overlay.dismissed:
                self._tip_overlay = None
        # Drive the model only when the player is actively in BID_WINDOW.
        st = self.player.auction_state
        prior_lifecycle = st.lifecycle
        prior_won_lots = list(st.won_lots)
        prior_history_count = len(st.session_history)
        prior_resolved_count = len(st.session_lot_results)
        prior_round_state = st.round_state
        prior_high_bidder = (
            prior_round_state.current_high_bidder_id if prior_round_state is not None else None
        )
        if st.lifecycle == AuctionLifecycle.BID_WINDOW:
            new_msgs = st.tick(dt)
            self.messages.extend(new_msgs)
            # SA-B3: when a named rival just placed a bid, replace the
            # generic AI message with the persona's voice-template line.
            new_rs = st.round_state
            if new_rs is not None:
                new_high = new_rs.current_high_bidder_id
                if (
                    new_high is not None
                    and new_high != prior_high_bidder
                    and new_high in NAMED_RIVAL_IDS
                ):
                    line = self._format_rival_bid_line(new_high, new_rs.current_high_bid)
                    if line:
                        # Drop the generic "X now leads..." line emitted
                        # this tick, surface the rival voice line instead.
                        if self.messages and new_high in self.messages[-1]:
                            self.messages[-1] = line
                        else:
                            self.messages.append(line)
        # If a lot just resolved this tick, fire callbacks BEFORE we
        # advance past LOT_RESOLUTION.
        new_resolved = len(st.session_lot_results) - prior_resolved_count
        if new_resolved > 0:
            for record in st.session_lot_results[-new_resolved:]:
                self._fire_lot_callbacks(record)
        new_won = [w for w in st.won_lots if w not in prior_won_lots]
        for lot_id in new_won:
            lot = self._lookup_lot(lot_id)
            if lot is not None and self.on_lot_won is not None:
                self.on_lot_won(
                    lot, st.session_lot_results[-1].sale_price if st.session_lot_results else 0
                )
        if len(st.session_history) > prior_history_count and self.on_session_complete is not None:
            self.on_session_complete()
        # Substate-driven UI rebuild.
        new_substate = _lifecycle_to_substate(st.lifecycle)
        if new_substate != self._built_substate:
            self._rebuild_ui_for_substate()
        # Message timer: expire after 4s.
        if self.messages:
            self._message_timer -= dt
            if self._message_timer <= 0.0:
                # Pop oldest message.
                self.messages.pop(0)
                self._message_timer = 4.0 if self.messages else 0.0
        if prior_lifecycle != st.lifecycle:
            logger.debug("Auction lifecycle: %s -> %s", prior_lifecycle.value, st.lifecycle.value)

    def render(self, screen: pygame.Surface) -> None:
        """Draw background, panel chrome, and substate-specific body."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))
        self._render_panel_chrome(screen)
        substate = _lifecycle_to_substate(self.player.auction_state.lifecycle)
        if self._error_text is not None:
            self._render_error_state(screen)
        elif self._loading:
            self._render_loading_state(screen)
        elif substate == AuctionSubstate.PREVIEW:
            self._render_body_preview(screen)
        elif substate == AuctionSubstate.OPENING:
            self._render_body_opening(screen)
        elif substate == AuctionSubstate.LOT_OPEN:
            self._render_body_lot_open(screen)
        elif substate == AuctionSubstate.BID_WINDOW:
            self._render_body_bid_window(screen)
        elif substate == AuctionSubstate.ROUND_CLOSE:
            self._render_body_round_close(screen)
        elif substate == AuctionSubstate.LOT_RESOLUTION:
            self._render_body_lot_resolution(screen)
        elif substate == AuctionSubstate.POST_SESSION:
            self._render_body_post_session(screen)
        # Status messages
        self._render_messages(screen)

    def render_top(self, screen: pygame.Surface) -> None:
        """Render the first-time tip on top of pygame_gui elements."""
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            self._tip_overlay.render(screen)

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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.next_state = GameState.STATION_HUB

    def _handle_button(self, ui_element: Any) -> None:
        if ui_element == self.back_button:
            self.next_state = GameState.STATION_HUB
            return
        if ui_element == self.start_button:
            self.player.auction_state.open_session()
            self._rebuild_ui_for_substate()
            return
        if ui_element == self.advance_button:
            self.player.auction_state.advance_after_resolution()
            self._rebuild_ui_for_substate()
            self._maybe_fire_session_complete()
            return
        if ui_element == self.next_lot_button:
            self.player.auction_state.advance_after_resolution()
            self._rebuild_ui_for_substate()
            self._maybe_fire_session_complete()
            return
        if ui_element == self.raise_min_button:
            self._submit_min_raise()
            return
        if ui_element == self.hold_button:
            _ok, msg = self.player.auction_state.player_hold()
            if msg:
                self._push_message(msg)
            return
        if ui_element == self.fold_button:
            _ok, msg = self.player.auction_state.player_fold()
            if msg:
                self._push_message(msg)
            return
        # Speed buttons
        for speed, btn in self._speed_buttons.items():
            if ui_element == btn:
                self.player.auction_state.speed_setting = speed
                self._rebuild_ui_for_substate()
                return

    def _submit_min_raise(self) -> None:
        amount = self.player.auction_state.player_min_raise_amount()
        _ok, msg = self.player.auction_state.submit_player_bid(amount)
        if msg:
            self._push_message(msg)

    def _push_message(self, msg: str) -> None:
        self.messages.append(msg)
        if self._message_timer <= 0.0:
            self._message_timer = 4.0

    # ------------------------------------------------------------------
    # Lot-resolution callback dispatch
    # ------------------------------------------------------------------

    def _maybe_fire_session_complete(self) -> None:
        """Fire on_session_complete if a session just reached SESSION_CLOSE.

        Called from the button handler after advance_after_resolution so the
        callback fires in the same event frame rather than relying on the
        view's update-delta logic (handle_event runs before update, so the
        history count is already incremented when update next checks it).
        """
        if (
            self.player.auction_state.lifecycle == AuctionLifecycle.SESSION_CLOSE
            and self.on_session_complete is not None
        ):
            self.on_session_complete()

    def _lookup_lot(self, lot_id: str) -> Optional[AuctionLot]:
        for lot in self.player.auction_state.active_session_lots:
            if lot.id == lot_id:
                return lot
        return None

    def _fire_lot_callbacks(self, record: Any) -> None:
        lot = self._lookup_lot(record.lot_id)
        if lot is None:
            return
        # First rivalry formed: any rival in rivals_bid won the lot
        # while the player also bid -> trigger.
        if (
            record.player_bid
            and record.sold
            and record.winner_id in NAMED_RIVAL_IDS
            and self.on_rivalry_formed is not None
        ):
            self.on_rivalry_formed(record.winner_id, lot)
        # Headliner news headlines
        if lot.is_headliner:
            if record.sold and self.on_headliner_sold is not None:
                self.on_headliner_sold(lot, record.sale_price)
            elif not record.sold and self.on_headliner_withdrawn is not None:
                self.on_headliner_withdrawn(lot)
        # Perfect-read achievement: player won within 2% of Sable's
        # ceiling estimate for any rival in the session.
        if (
            record.sold
            and record.winner_id == "player"
            and self.crew_roster.get_bonus("auction_bid_visibility") > 0.0
        ):
            actual = record.sale_price
            for persona in self._live_personas:
                if persona.persona_id not in NAMED_RIVAL_IDS:
                    continue
                ceiling_est = sable_displayed_ceiling(
                    persona,
                    lot,
                    self.player.auction_state.active_session_id or "_",
                    vs_player=True,
                    recent_player_categories=tuple(self.player.auction_state.recent_bid_categories),
                )
                if ceiling_est <= 0:
                    continue
                err = abs(actual - ceiling_est) / ceiling_est
                if err <= SABLE_CEILING_CORRECT_THRESHOLD:
                    self.player.dialogue_flags[auction_sable_ceiling_correct()] = True
                if err <= PERFECT_READ_THRESHOLD:
                    self.player.auction_state.auction_perfect_reads += 1
                    break

    # ------------------------------------------------------------------
    # UI lifecycle (paired _create_ui_* / _destroy_ui_*)
    # ------------------------------------------------------------------

    def _rebuild_ui_for_substate(self) -> None:
        self._destroy_all_ui()
        substate = _lifecycle_to_substate(self.player.auction_state.lifecycle)
        if self._error_text is not None or self._loading:
            self._create_ui_back_only()
            self._built_substate = substate
            return
        if substate == AuctionSubstate.PREVIEW:
            self._create_ui_preview()
        elif substate == AuctionSubstate.OPENING:
            self._create_ui_opening()
        elif substate == AuctionSubstate.LOT_OPEN:
            self._create_ui_lot_open()
        elif substate == AuctionSubstate.BID_WINDOW:
            self._create_ui_bid_window()
        elif substate == AuctionSubstate.ROUND_CLOSE:
            self._create_ui_round_close()
        elif substate == AuctionSubstate.LOT_RESOLUTION:
            self._create_ui_lot_resolution()
        elif substate == AuctionSubstate.POST_SESSION:
            self._create_ui_post_session()
        self._built_substate = substate

    def _destroy_all_ui(self) -> None:
        elements: list[Any] = [
            self.back_button,
            self.start_button,
            self.advance_button,
            self.next_lot_button,
            self.raise_min_button,
            self.raise_custom_button,
            self.hold_button,
            self.fold_button,
        ]
        elements.extend(self._speed_buttons.values())
        for elem in elements:
            if elem is not None:
                elem.kill()
        self.back_button = None
        self.start_button = None
        self.advance_button = None
        self.next_lot_button = None
        self.raise_min_button = None
        self.raise_custom_button = None
        self.hold_button = None
        self.fold_button = None
        self._speed_buttons = {}
        self._built_substate = None

    def _make_back_button(self) -> None:
        rect = pygame.Rect(
            PANEL_X + scale_x(20),
            PANEL_TOP_Y + scale_y(20),
            BTN_W,
            BTN_H,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=rect,
            text="Leave",
            manager=self.ui_manager,
        )

    def _create_ui_back_only(self) -> None:
        self._make_back_button()

    def _create_ui_preview(self) -> None:
        self._make_back_button()
        # Speed selector — four buttons across the lower header band.
        speeds = ("slow", "normal", "fast", "asap")
        x0 = PANEL_X + scale_x(220)
        y0 = PANEL_TOP_Y + scale_y(20)
        for i, speed in enumerate(speeds):
            rect = pygame.Rect(
                x0 + i * (SPEED_BTN_W + scale_x(8)),
                y0,
                SPEED_BTN_W,
                BTN_H,
            )
            label = speed.capitalize()
            if speed == self.player.auction_state.speed_setting:
                label = f"[{label}]"
            btn = pygame_gui.elements.UIButton(
                relative_rect=rect,
                text=label,
                manager=self.ui_manager,
            )
            self._speed_buttons[speed] = btn
        # Start session button (only if a session is loaded).
        if self.player.auction_state.lifecycle == AuctionLifecycle.PREVIEW:
            rect = pygame.Rect(
                PANEL_X + PANEL_W - BTN_W - scale_x(20),
                PANEL_TOP_Y + scale_y(20),
                BTN_W,
                BTN_H,
            )
            self.start_button = pygame_gui.elements.UIButton(
                relative_rect=rect,
                text="Open Session",
                manager=self.ui_manager,
            )

    def _create_ui_opening(self) -> None:
        self._make_back_button()
        # OPENING transitions immediately to LOT_OPEN/BID_WINDOW; no
        # extra buttons needed. Player can still leave.

    def _create_ui_lot_open(self) -> None:
        self._make_back_button()

    def _create_ui_bid_window(self) -> None:
        self._make_back_button()
        x0 = PANEL_X + scale_x(20)
        y0 = PANEL_TOP_Y + HEADER_H + scale_y(360)
        gap = scale_x(8)
        self.raise_min_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x0, y0, BTN_W, BTN_H),
            text="Raise (min)",
            manager=self.ui_manager,
        )
        self.hold_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x0 + (BTN_W + gap), y0, BTN_W, BTN_H),
            text="Hold",
            manager=self.ui_manager,
        )
        self.fold_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(x0 + 2 * (BTN_W + gap), y0, BTN_W, BTN_H),
            text="Fold",
            manager=self.ui_manager,
        )

    def _create_ui_round_close(self) -> None:
        self._make_back_button()

    def _create_ui_lot_resolution(self) -> None:
        self._make_back_button()
        rect = pygame.Rect(
            PANEL_X + PANEL_W - BTN_W - scale_x(20),
            PANEL_TOP_Y + scale_y(20),
            BTN_W,
            BTN_H,
        )
        self.next_lot_button = pygame_gui.elements.UIButton(
            relative_rect=rect,
            text="Next Lot",
            manager=self.ui_manager,
        )

    def _create_ui_post_session(self) -> None:
        self._make_back_button()

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_panel_chrome(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            (PANEL_X, PANEL_TOP_Y, PANEL_W, WINDOW_HEIGHT - PANEL_TOP_Y * 2),
            alpha=200,
        )
        title = self.title_font.render(self.venue_display_name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(70)))

    def _render_messages(self, screen: pygame.Surface) -> None:
        if not self.messages:
            return
        latest = self.messages[0]
        surf = self.body_font.render(latest, True, Colors.TEXT_PRIMARY)
        x = PANEL_X + scale_x(20)
        y = WINDOW_HEIGHT - PANEL_TOP_Y - scale_y(40)
        screen.blit(surf, (x, y))

    def _render_body_preview(self, screen: pygame.Surface) -> None:
        st = self.player.auction_state
        body_y = BODY_TOP_Y
        x = PANEL_X + scale_x(20)
        # Empty / pre-schedule state.
        if st.lifecycle == AuctionLifecycle.SCHEDULED:
            scheduled = st.next_auction_day.get(self.venue_id)
            current_day = self.player.game_day
            if scheduled is not None and scheduled > current_day:
                gap = scheduled - current_day
                # SA-B3: prefer the data-driven empty-state template
                # (Velo flavor) when present; fall back to the bare
                # countdown line when the voice file is missing.
                template = self._voice_templates.get("empty_state") if self._voice_templates else ""
                if template:
                    line = template.format(gap_days=gap)
                else:
                    line = f"Next session in {gap} day{'s' if gap != 1 else ''}."
            else:
                # SA-B4: demand-driven venues (Reach) have no calendar
                # date; use the venue's empty_state voice template when
                # it doesn't need a {gap_days} substitution.
                template = self._voice_templates.get("empty_state") if self._voice_templates else ""
                if isinstance(template, str) and template and "{gap_days}" not in template:
                    line = template
                else:
                    line = "No session scheduled. The floor is quiet."
            self._draw_text(screen, line, (x, body_y))
            return
        # PREVIEW with lots loaded.
        header = self.subtitle_font.render(
            f"Preview: {len(st.active_session_lots)} lots",
            True,
            Colors.TEXT_HIGHLIGHT,
        )
        screen.blit(header, (x, body_y))
        body_y += scale_y(36)
        appraiser_active = self.progression.get_bonus("auction_lot_appraisal_bonus") > 0.0
        for lot in st.active_session_lots[:6]:
            head_line = f"{lot.headline}  ({lot.category})"
            self._draw_text(screen, head_line, (x, body_y))
            body_y += scale_y(20)
            if appraiser_active:
                low, high = reserve_band_for_preview(lot.base_appraisal, lot.reserve_pct)
                self._draw_text(
                    screen,
                    f"Reserve likely: {low:,} to {high:,}.",
                    (x + scale_x(18), body_y),
                    color=Colors.TEXT_SECONDARY,
                )
                body_y += scale_y(18)
            body_y += scale_y(6)

    def _render_body_opening(self, screen: pygame.Surface) -> None:
        self._draw_text(
            screen,
            "Lot is open.",
            (PANEL_X + scale_x(20), BODY_TOP_Y),
        )

    def _render_body_lot_open(self, screen: pygame.Surface) -> None:
        self._render_body_bid_window(screen)

    def _render_body_bid_window(self, screen: pygame.Surface) -> None:
        st = self.player.auction_state
        rs = st.round_state
        if rs is None:
            return
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        lot = st.current_lot()
        if lot is None:
            return
        self._draw_text(
            screen,
            f"Lot {st.active_lot_index + 1} / {len(st.active_session_lots)}:",
            (x, y),
            color=Colors.TEXT_SECONDARY,
        )
        y += scale_y(20)
        self._draw_text(screen, lot.headline, (x, y))
        y += scale_y(28)
        # SA-B3: Velo running commentary above the timer. Reads template
        # from voice content; falls back to a tight default when missing.
        velo_line = self._velo_running_commentary(lot, rs)
        if velo_line:
            self._draw_text(screen, velo_line, (x, y), color=Colors.TEXT_HIGHLIGHT)
            y += scale_y(20)
        timer_str = f"Round {rs.round_number}: {rs.time_remaining:.1f}s remaining"
        self._draw_text(screen, timer_str, (x, y))
        y += scale_y(20)
        # Current high bid + leader
        bidder_label = self._winner_label(rs.current_high_bidder_id)
        self._draw_text(
            screen,
            f"High bid: {rs.current_high_bid:,} credits ({bidder_label})",
            (x, y),
        )
        y += scale_y(28)
        # Sable visibility panel
        if self.crew_roster.get_bonus("auction_bid_visibility") > 0.0:
            self._render_sable_panel(screen, x, y, lot)

    def _velo_running_commentary(self, lot: AuctionLot, rs: Any) -> str:
        """Return the auctioneer's running-commentary line for the active round.

        On round 1 with no high bidder yet, fires the lot-open template.
        Otherwise updates with the "we are at" template each time the
        current high bid changes.

        SA-B4 (locked decision §B4.6): reads ``auctioneer_lines`` first
        and falls back to ``velo_lines`` so SA-B3's Stellaris voice file
        keeps working unchanged. New venues author the venue-neutral
        ``auctioneer_lines`` key.
        """
        templates_dict = self._voice_templates if self._voice_templates else {}
        auctioneer = templates_dict.get("auctioneer_lines")
        if not isinstance(auctioneer, dict):
            auctioneer = templates_dict.get("velo_lines")
        lines: dict[str, str] = auctioneer if isinstance(auctioneer, dict) else {}
        if rs.current_high_bidder_id is None:
            template = lines.get("lot_open", "The lot is open. {lot_headline}.")
            return template.format(lot_headline=lot.headline)
        template = lines.get("we_are_at", "We are at {current_high_bid}. Do we hear more?")
        return template.format(
            current_high_bid=f"{rs.current_high_bid:,}",
            lot_headline=lot.headline,
        )

    def _format_rival_bid_line(self, persona_id: str, amount: int) -> Optional[str]:
        """Format a rival's flat-bid line per voice templates.

        Returns ``None`` if the persona is not a named rival or no
        template is registered.
        """
        if persona_id not in NAMED_RIVAL_IDS:
            return None
        rival_templates = self._voice_templates.get("rival_bids") if self._voice_templates else None
        bids: dict[str, str] = rival_templates if isinstance(rival_templates, dict) else {}
        template = bids.get(persona_id)
        if not template:
            # Default flat number prefixed with display name to keep the
            # bid-log informative without voice content.
            display = RIVAL_DISPLAY_NAMES.get(persona_id, persona_id)
            return f"{display}: {amount:,}."
        return template.format(amount=f"{amount:,}")

    def _render_body_round_close(self, screen: pygame.Surface) -> None:
        self._draw_text(
            screen,
            "Round closed. Tallying...",
            (PANEL_X + scale_x(20), BODY_TOP_Y),
        )

    def _render_body_lot_resolution(self, screen: pygame.Surface) -> None:
        st = self.player.auction_state
        if not st.session_lot_results:
            return
        record = st.session_lot_results[-1]
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        if record.sold:
            line = f"Sold at {record.sale_price:,} credits."
            self._draw_text(screen, line, (x, y))
            if record.winner_id == "player":
                # Post-win valuation message per §7.2 stacking.
                lot = self._lookup_lot(record.lot_id)
                if lot is not None:
                    total_bonus = self.progression.get_bonus(
                        "auction_lot_appraisal_bonus"
                    ) + self.crew_roster.get_bonus("auction_lot_appraisal_bonus")
                    sable_active = self.crew_roster.get_bonus("auction_bid_visibility") > 0.0
                    msg = post_win_valuation_message(
                        total_bonus, lot.base_appraisal, sable_active=sable_active
                    )
                    if msg:
                        self._draw_text(
                            screen,
                            msg,
                            (x, y + scale_y(28)),
                            color=Colors.TEXT_HIGHLIGHT,
                        )
        else:
            self._draw_text(
                screen,
                "Reserve not met. The lot is withdrawn.",
                (x, y),
                color=Colors.YELLOW,
            )

    def _render_body_post_session(self, screen: pygame.Surface) -> None:
        st = self.player.auction_state
        x = PANEL_X + scale_x(20)
        y = BODY_TOP_Y
        wins = sum(1 for r in st.session_lot_results if r.winner_id == "player")
        sold = sum(1 for r in st.session_lot_results if r.sold)
        self._draw_text(
            screen,
            f"Session closed. {sold} lots sold, {wins} taken by you.",
            (x, y),
        )
        y += scale_y(28)
        # SA-B3: rival commentary, Sable read, retired-rival aside.
        for line in self._post_session_lines():
            self._draw_text(screen, line, (x, y), color=Colors.TEXT_SECONDARY)
            y += scale_y(20)

    def _post_session_lines(self) -> list[str]:
        """Compose post-session social UI lines.

        One per attending named rival (outcome bucket selected from
        session_lot_results), one Sable read line if Sable on crew, one
        retired-rival aside if any named rival auto-retired this session.
        Returns voice-template lines when present; falls back to design-
        doc default strings otherwise.
        """
        st = self.player.auction_state
        lines: list[str] = []
        rival_attendees = list(st.rival_session_attendance.get(st.active_session_id or "", []))
        post_block = self._voice_templates.get("post_session") if self._voice_templates else None
        post_table: dict[str, dict] = post_block if isinstance(post_block, dict) else {}
        for rival_id in rival_attendees:
            bucket = self._post_session_bucket_for_rival(rival_id)
            display = RIVAL_DISPLAY_NAMES.get(rival_id, rival_id)
            rival_lines = post_table.get(rival_id, {}) if isinstance(post_table, dict) else {}
            options = rival_lines.get(bucket, []) if isinstance(rival_lines, dict) else []
            if options:
                lines.append(options[0])
            else:
                lines.append(self._default_post_session_line(display, bucket))
        # Sable read line (if Sable on crew).
        sable_active = self.crew_roster.get_bonus("auction_bid_visibility") > 0.0
        sable_block = self._voice_templates.get("sable_reads") if self._voice_templates else None
        sable_table: dict[str, str] = sable_block if isinstance(sable_block, dict) else {}
        if sable_active:
            if not rival_attendees:
                line = sable_table.get(
                    "no_rivals_attended",
                    "No named rivals on the floor today.",
                )
            elif self.player.dialogue_flags.get(auction_sable_ceiling_correct()):
                line = sable_table.get(
                    "ceiling_correct",
                    "Ceilings landed within the band I called.",
                )
            else:
                line = sable_table.get(
                    "ceiling_off",
                    "Two of the ceilings ran past my call. I will adjust.",
                )
            if line:
                lines.append(line)
        # Retired-rival aside (if any named rival auto-retired this session).
        retired = self._retired_rivals_this_session()
        if retired:
            template = self._voice_templates.get("retired_rival") if self._voice_templates else None
            for rival_id in retired:
                display = RIVAL_DISPLAY_NAMES.get(rival_id, rival_id)
                if isinstance(template, str) and template:
                    lines.append(template.format(display_name=display))
                else:
                    lines.append(f"{display} has not been on the floor in a while.")
        return lines

    def _post_session_bucket_for_rival(self, rival_id: str) -> str:
        """Pick the outcome bucket for a rival's post-session commentary.

        Buckets per voice schema:
        * ``rival_won`` — rival won at least one lot the player also bid on.
        * ``player_won`` — player won at least one lot the rival also bid on.
        * ``no_overlap`` — rival attended but did not engage on player lots.
        * ``absent_retired`` — rival was retired and did not attend.
        """
        st = self.player.auction_state
        if rival_id in self._retired_rivals_this_session():
            return "absent_retired"
        for record in st.session_lot_results:
            if record.winner_id == rival_id and record.player_bid:
                return "rival_won"
        for record in st.session_lot_results:
            if record.winner_id == "player" and rival_id in record.rivals_bid:
                return "player_won"
        return "no_overlap"

    def _retired_rivals_this_session(self) -> list[str]:
        """Return rival ids whose status is STATUS_WANDERER on the player record.

        Read-only: the captain memory snapshot is queried via the player's
        ``captain_memory`` dict. Empty when the snapshot is unavailable.
        """
        memory = getattr(self.player, "captain_memory", None)
        if not memory or not isinstance(memory, dict):
            return []
        try:
            from spacegame.models.captain_memory import STATUS_WANDERER
        except ImportError:  # pragma: no cover - module always exists.
            return []
        retired: list[str] = []
        for rival_id in NAMED_RIVAL_IDS:
            entry = memory.get(rival_id)
            if entry is not None and getattr(entry, "status", None) == STATUS_WANDERER:
                retired.append(rival_id)
        return retired

    def _default_post_session_line(self, display: str, bucket: str) -> str:
        """Fallback post-session line when no voice template is loaded."""
        if bucket == "rival_won":
            return f"{display} closed on a lot you bid on."
        if bucket == "player_won":
            return f"{display} watched you take the lot."
        if bucket == "absent_retired":
            return f"{display} did not attend."
        return f"{display} attended without overlap."

    def _render_loading_state(self, screen: pygame.Surface) -> None:
        self._draw_text(
            screen,
            "Loading session...",
            (PANEL_X + scale_x(20), BODY_TOP_Y),
        )

    def _render_error_state(self, screen: pygame.Surface) -> None:
        self._draw_text(
            screen,
            self._error_text or "Auction data unavailable.",
            (PANEL_X + scale_x(20), BODY_TOP_Y),
            color=Colors.RED,
        )

    def _render_sable_panel(self, screen: pygame.Surface, x: int, y: int, lot: AuctionLot) -> None:
        if not self._live_personas:
            return
        self._draw_text(
            screen,
            "Sable's read:",
            (x, y),
            color=Colors.TEXT_SECONDARY,
        )
        y += scale_y(18)
        for persona in self._live_personas:
            if persona.persona_id in NAMED_RIVAL_IDS:
                ceiling_est = sable_displayed_ceiling(
                    persona,
                    lot,
                    self.player.auction_state.active_session_id or "_",
                    vs_player=True,
                    recent_player_categories=tuple(self.player.auction_state.recent_bid_categories),
                )
                if ceiling_est > 0:
                    line = f"{persona.display_name}: ceiling approx. {ceiling_est:,}"
                else:
                    line = f"{persona.display_name}: not bidding"
                self._draw_text(
                    screen,
                    line,
                    (x + scale_x(12), y),
                    color=Colors.TEXT_SECONDARY,
                )
                y += scale_y(16)
            else:
                self._draw_text(
                    screen,
                    f"{persona.display_name}: present",
                    (x + scale_x(12), y),
                    color=Colors.TEXT_SECONDARY,
                )
                y += scale_y(16)

    def _draw_text(
        self,
        screen: pygame.Surface,
        text: str,
        pos: tuple[int, int],
        color: tuple[int, int, int] = Colors.TEXT_PRIMARY,
    ) -> None:
        surf = self.body_font.render(text, True, color)
        screen.blit(surf, pos)

    def _winner_label(self, bidder_id: Optional[str]) -> str:
        if bidder_id is None:
            return "no leader"
        if bidder_id == "player":
            return "you"
        if self.crew_roster.get_bonus("auction_bid_visibility") > 0.0:
            for persona in self._live_personas:
                if persona.persona_id == bidder_id:
                    return persona.display_name
        return "another bidder"

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
