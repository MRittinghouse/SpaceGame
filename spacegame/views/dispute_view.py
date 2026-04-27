"""SA-P2 venue dispute view.

Single :class:`BaseView` subclass with internal substates: LIST,
CORRIDOR, SESSION, COMPOSER, TALLY. Empty / locked / loading / error
states render in the LIST substate. Argument composer carries a live
"Effective N vs Difficulty M" preview that updates without rebuilding
UI elements when selections change.

Pixel-level layout deferred to SA-X10 / SA-P3 per design §11; this
sprint commits to structure (substates, lifecycle, preview wiring,
state-error coverage) only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.constants.flags import (
    seen_annual_congress_tip,
    seen_argument_composer_tip,
    seen_gray_market_arbitration_tip,
    seen_politics_venue_tip,
)
from spacegame.engine.draw_utils import draw_panel, word_wrap
from spacegame.engine.fonts import FONT_BODY, FONT_MD, FONT_TITLE, get_font
from spacegame.models.player import Player
from spacegame.models.politics_dispute import (
    ArgumentResolution,
    DisputePhase,
    PoliticsArgument,
    PoliticsDispute,
    PoliticsDisputeManager,
)
from spacegame.models.wreckers_guild import current_tier_id
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

if TYPE_CHECKING:  # pragma: no cover
    pass


# Layout constants (box-diagram aligned with design §8). Pixel layout
# tuning belongs to SA-X10; these are reasonable defaults so the view
# renders without overlap during SA-P2 testing.
PANEL_X = scale_x(60)
PANEL_W = WINDOW_WIDTH - scale_x(120)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)
BODY_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BODY_H = scale_y(420)

# Faction-standing threshold for the "locked" state in the dispute list
# (design §8.1 mock: "requires -25 or above"). SA-P3 may override per
# venue.
DEFAULT_STANDING_THRESHOLD = -25

# SA-P3 PT-M tutorial copy. Pulled byte-for-byte from
# requirements/sa_politics_design.md §9.2 and §9.3 so an authoring drift
# would surface in the view test that asserts the literal strings.
VENUE_TIP_TITLE = "Council Session"
VENUE_TIP_BODY = (
    "Council convenes here. Vote, argue your case, mediate, or step back. "
    "Disputes close on a deadline; missing the deadline counts as abstention."
)
COMPOSER_TIP_TITLE = "Argument"
COMPOSER_TIP_BODY = (
    "Argument has three parts. Framing is how you say it. Evidence is what "
    "backs it. Audience is who you're persuading. Pick what fits the room."
)
# SA-P4 Annual Congress orientation tip. Fires once on first entry to the
# Haven's Rest dispute view (and only there). Three short declarative
# sentences, supervisor register, voice-checked against the Writing Bible.
ANNUAL_CONGRESS_TIP_TITLE = "Annual Congress"
ANNUAL_CONGRESS_TIP_BODY = (
    "Congress meets once per year. Visit delegates between sessions to build "
    "votes. The bigger the coalition before the floor opens, the better the "
    "outcome."
)
# SA-P5 gray-market arbitration tip. Fires once on first entry to the
# Crimson Reach dispute view (and only there). Five short declaratives,
# supervisor register, voice-checked against the Writing Bible.
GRAY_MARKET_ARBITRATION_TIP_TITLE = "Gray-Market Arbitration"
GRAY_MARKET_ARBITRATION_TIP_BODY = (
    "The Guild settles what the law won't. Apprentices watch. "
    "Journeymen argue. Masters mediate. "
    "Earn your tier to unlock more of the room."
)

# SA-P5: Per-venue visual theme hook. Pulling palette values from the
# ReachDarkLayout register (station_layouts.py:971-973) so the Crimson
# Reach chamber reads dim-by-default. Verdant + Haven's Rest get neutral
# defaults that preserve SA-P3/SA-P4 byte-for-byte rendering.


@dataclass(frozen=True)
class VenueTheme:
    """Immutable per-venue color palette for the dispute view."""

    accent_color: tuple[int, int, int]
    bg_dim_alpha: int
    panel_bg_color: tuple[int, int, int]


_DEFAULT_VENUE_THEME = VenueTheme(
    accent_color=(100, 130, 90),
    bg_dim_alpha=120,
    panel_bg_color=(15, 25, 15),
)
_REACH_VENUE_THEME = VenueTheme(
    accent_color=(180, 50, 40),
    bg_dim_alpha=160,
    panel_bg_color=(12, 8, 8),
)
_VENUE_THEMES: dict[str, VenueTheme] = {
    "verdant_mayors_council": _DEFAULT_VENUE_THEME,
    "havens_congress_hall": _DEFAULT_VENUE_THEME,
    "crimson_wreckers_guild": _REACH_VENUE_THEME,
}

# SA-P5: text for the LOCKED_NO_MEMBERSHIP list substate. Exact string
# asserted byte-for-byte in the view tests per AC 10.
LOCKED_NO_MEMBERSHIP_TEXT = (
    "This is a Guild floor. Walk the contracts board until your name's known. "
    "Apprentices observe; journeymen argue; masters mediate."
)

# SA-P5: per-tier action button enable map for the Crimson Reach venue.
# Keys are tier ids; values are frozensets of enabled action keys.
# Applied only when venue_id == "crimson_wreckers_guild".
_TIER_ACTION_ENABLE: dict[str, frozenset[str]] = {
    "unjoined": frozenset(),  # should never reach SESSION, but safe default
    "apprentice": frozenset(),  # observer mode: all four disabled
    "journeyman": frozenset({"argue", "vote_now", "abstain"}),
    "master": frozenset({"argue", "mediate", "vote_now", "abstain"}),
}


class DisputeSubstate(Enum):
    """Internal navigation states inside the venue view."""

    LIST = "list"  # Dispute list, plus empty / locked / loading / error
    CORRIDOR = "corridor"  # Coalition pre-commit corridor
    SESSION = "session"  # In-session round view
    COMPOSER = "composer"  # Three-slot argument composer
    TALLY = "tally"  # Vote / outcome screen


class DisputeListState(Enum):
    """Sub-substates rendered inside LIST (only one is shown at a time)."""

    READY = "ready"  # active disputes listed
    EMPTY = "empty"  # no active disputes
    LOCKED = "locked"  # insufficient standing
    LOADING = "loading"  # data not yet ready
    ERROR = "error"  # data unavailable
    LOCKED_OUT_ANNUAL = "locked_out_annual"  # SA-P4: annual Congress in recess
    LOCKED_NO_MEMBERSHIP = "locked_no_membership"  # SA-P5: Reach venue, unjoined tier


class DisputeView(BaseView):
    """Venue view for politics-system disputes.

    Composition: receives a :class:`PoliticsDisputeManager` plus
    references to the player and the venue's faction. Substate
    transitions destroy and rebuild UI elements; lifecycle is the
    standard CLAUDE.md pattern.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        dispute_manager: PoliticsDisputeManager,
        venue_id: str = "verdant_mayors_council",
        venue_faction_id: str = "verdant",
        standing_threshold: int = DEFAULT_STANDING_THRESHOLD,
    ) -> None:
        """Build the view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Player whose state the manager mutates.
            dispute_manager: SA-P2 manager that owns templates +
                pending / resolved disputes.
            venue_id: Venue id (e.g., ``"verdant_mayors_council"``).
                SA-P3 themes per venue.
            venue_faction_id: Faction whose standing gates the locked
                state.
            standing_threshold: Min faction standing to participate.
        """
        super().__init__(ui_manager=ui_manager)
        self.player = player
        self.dispute_manager = dispute_manager
        self.venue_id = venue_id
        self.venue_faction_id = venue_faction_id
        self.standing_threshold = standing_threshold
        self.next_state: Optional[GameState] = None

        # Fonts (created once, reused)
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.body_font = get_font("dialogue", FONT_BODY)

        # Substate
        self.substate: DisputeSubstate = DisputeSubstate.LIST
        self.list_state: DisputeListState = DisputeListState.READY

        # Active dispute / argument state for the substate transitions.
        self.active_dispute: Optional[PoliticsDispute] = None
        self.composer_argument: PoliticsArgument = PoliticsArgument(
            framing="", audience_delegate_id=""
        )
        self.composer_resolution: Optional[ArgumentResolution] = None

        # UI element references
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.preview_label: Optional[pygame_gui.elements.UILabel] = None
        self._dispute_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._action_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._composer_buttons: dict[str, pygame_gui.elements.UIButton] = {}

        # Loading / error flags toggled by Game.py when data isn't ready.
        self._data_loading: bool = False
        self._data_error: bool = False

        # SA-P4: days-remaining count for the LOCKED_OUT_ANNUAL substate.
        # Recomputed each time ``_refresh_list_state`` runs so the body
        # text reflects the current game day. Always non-negative.
        self._annual_recess_days_remaining: int = 0

        # PT-M tutorial overlay (SA-P3). One overlay reference is enough
        # since only one tip is ever live at a time (venue tip on entry,
        # then composer tip on first composer open).
        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered dispute view (%s)", self.venue_id)
        self._refresh_list_state()
        self.substate = DisputeSubstate.LIST
        self._create_ui()
        self._maybe_show_venue_tip()
        self._maybe_show_annual_congress_tip()
        # SA-P5: Gray-market arbitration tip fires on first Reach entry.
        self._maybe_show_gray_market_arbitration_tip()
        # SA-P4: Track days remaining for the LOCKED_OUT_ANNUAL substate so
        # the body text can render "Next session in N days." dynamically.
        # Recomputed every time the list state refreshes.

    def on_exit(self) -> None:
        # End the per-session intel reveal gate; re-entering re-fires.
        self.dispute_manager.end_session()
        # Drop any active overlay reference so a re-entry constructs a
        # fresh one (the dismissal flag is what gates re-fire, not this).
        self._first_time_tip = None
        self._destroy_ui()
        super().on_exit()

    # ------------------------------------------------------------------
    # PT-M tutorial overlays (SA-P3 §9.2 + §9.3)
    # ------------------------------------------------------------------

    def _clear_dismissed_tip(self) -> None:
        """Drop the overlay reference once the player has dismissed it.

        Called from the lifecycle hooks that may want to fire a *new*
        tip immediately after a previous one was dismissed (e.g.,
        opening the composer right after closing the venue tip).
        """
        if self._first_time_tip is not None and self._first_time_tip.dismissed:
            self._first_time_tip = None

    def _maybe_show_venue_tip(self) -> None:
        """Fire the SA-P3 venue tip on first entry, never again.

        Gates on ``flags.seen_politics_venue_tip()`` in
        ``player.dialogue_flags``; on dismissal the on-dismiss callback
        sets the same flag, so the next venue entry skips the tip.
        """
        self._clear_dismissed_tip()
        if self.player.dialogue_flags.get(seen_politics_venue_tip(), False):
            return
        self._first_time_tip = FirstTimeTipOverlay(
            title=VENUE_TIP_TITLE,
            body=VENUE_TIP_BODY,
            on_dismiss=self._mark_venue_tip_seen,
        )

    def _mark_venue_tip_seen(self) -> None:
        self.player.dialogue_flags[seen_politics_venue_tip()] = True

    def _maybe_show_composer_tip(self) -> None:
        """Fire the SA-P3 composer tip on first composer open, never again."""
        self._clear_dismissed_tip()
        if self.player.dialogue_flags.get(seen_argument_composer_tip(), False):
            return
        self._first_time_tip = FirstTimeTipOverlay(
            title=COMPOSER_TIP_TITLE,
            body=COMPOSER_TIP_BODY,
            on_dismiss=self._mark_composer_tip_seen,
        )

    def _mark_composer_tip_seen(self) -> None:
        self.player.dialogue_flags[seen_argument_composer_tip()] = True

    def _maybe_show_annual_congress_tip(self) -> None:
        """SA-P4: fire the Annual Congress tip on first Haven's Rest entry.

        Gated on ``venue_id == "havens_congress_hall"`` so the same overlay
        does not fire at the Verdant venue. One-shot per save, gated on
        :func:`flags.seen_annual_congress_tip` in ``player.dialogue_flags``.
        """
        if self.venue_id != "havens_congress_hall":
            return
        self._clear_dismissed_tip()
        if self.player.dialogue_flags.get(seen_annual_congress_tip(), False):
            return
        # Suppress when another tip is already up so the player isn't hit by
        # two overlays at once on first entry.
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            return
        self._first_time_tip = FirstTimeTipOverlay(
            title=ANNUAL_CONGRESS_TIP_TITLE,
            body=ANNUAL_CONGRESS_TIP_BODY,
            on_dismiss=self._mark_annual_congress_tip_seen,
        )

    def _mark_annual_congress_tip_seen(self) -> None:
        self.player.dialogue_flags[seen_annual_congress_tip()] = True

    def _maybe_show_gray_market_arbitration_tip(self) -> None:
        """SA-P5: fire the gray-market arbitration tip on first Reach entry.

        Gated on ``venue_id == "crimson_wreckers_guild"`` so the overlay
        does not fire at the Verdant or Haven's Rest venues. One-shot per
        save, gated on :func:`flags.seen_gray_market_arbitration_tip` in
        ``player.dialogue_flags``.
        """
        if self.venue_id != "crimson_wreckers_guild":
            return
        self._clear_dismissed_tip()
        if self.player.dialogue_flags.get(seen_gray_market_arbitration_tip(), False):
            return
        # Suppress when another tip is already up so the player isn't hit
        # by two overlays at once on first entry.
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            return
        self._first_time_tip = FirstTimeTipOverlay(
            title=GRAY_MARKET_ARBITRATION_TIP_TITLE,
            body=GRAY_MARKET_ARBITRATION_TIP_BODY,
            on_dismiss=self._mark_gray_market_arbitration_tip_seen,
        )

    def _mark_gray_market_arbitration_tip_seen(self) -> None:
        self.player.dialogue_flags[seen_gray_market_arbitration_tip()] = True

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def set_loading(self, loading: bool) -> None:
        self._data_loading = loading
        self._refresh_list_state()
        if self.substate == DisputeSubstate.LIST:
            self._switch_substate(DisputeSubstate.LIST, force_recreate=True)

    def set_error(self, error: bool) -> None:
        self._data_error = error
        self._refresh_list_state()
        if self.substate == DisputeSubstate.LIST:
            self._switch_substate(DisputeSubstate.LIST, force_recreate=True)

    def _refresh_list_state(self) -> None:
        if self._data_error:
            self.list_state = DisputeListState.ERROR
            return
        if self._data_loading:
            self.list_state = DisputeListState.LOADING
            return
        # SA-P5: Reach venue requires Guild membership. Unjoined players hit
        # LOCKED_NO_MEMBERSHIP before the faction-standing check, because the
        # fictional surfaces are distinct: one is "Crimson Reach hates you"
        # and the other is "you haven't joined the Guild."
        if self.venue_id == "crimson_wreckers_guild":
            tier = current_tier_id(self.player.sub_reputation)
            if tier == "unjoined":
                self.list_state = DisputeListState.LOCKED_NO_MEMBERSHIP
                return
        standing = self.player.get_reputation(self.venue_faction_id)
        if standing < self.standing_threshold:
            self.list_state = DisputeListState.LOCKED
            return
        if not self.dispute_manager.get_pending_dispute_ids():
            # SA-P4: when no pending disputes AND any registered annual
            # template is currently in lockout, show the annual recess
            # substate with a days-remaining count rather than the generic
            # EMPTY copy.
            recess_days = self._annual_lockout_days_remaining()
            if recess_days > 0:
                self.list_state = DisputeListState.LOCKED_OUT_ANNUAL
                self._annual_recess_days_remaining = recess_days
                return
            self.list_state = DisputeListState.EMPTY
            return
        self.list_state = DisputeListState.READY

    def _annual_lockout_days_remaining(self) -> int:
        """Return days remaining on any locked-out annual template at this venue.

        Walks every registered template; for any annual template that
        isn't currently active, returns the largest remaining days count.
        Returns 0 when no annual templates are locked out (e.g., the
        Verdant venue, which has no annual templates).
        """
        templates = getattr(self.dispute_manager, "_templates", {})
        game_day = getattr(self.player, "game_day", 0)
        max_remaining = 0
        for tpl in templates.values():
            if not getattr(tpl, "is_annual_congress", False):
                continue
            if self.dispute_manager.is_dispute_active(tpl.id, game_day):
                continue
            remaining = self.dispute_manager.next_session_in_days(tpl.id, game_day)
            if remaining > max_remaining:
                max_remaining = remaining
        return max_remaining

    # ------------------------------------------------------------------
    # Substate routing
    # ------------------------------------------------------------------

    def _switch_substate(self, substate: DisputeSubstate, *, force_recreate: bool = False) -> None:
        """Tear down current UI, set the new substate, build its UI."""
        if substate == self.substate and not force_recreate:
            return
        self._destroy_ui()
        self.substate = substate
        self._create_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _create_ui(self) -> None:
        """Build pygame_gui elements for the current substate."""
        # The back button is always present.
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(140),
                PANEL_TOP_Y + scale_y(20),
                scale_x(120),
                scale_y(36),
            ),
            text="Leave",
            manager=self.ui_manager,
        )
        if self.substate == DisputeSubstate.LIST:
            self._create_ui_list()
        elif self.substate == DisputeSubstate.CORRIDOR:
            self._create_ui_corridor()
        elif self.substate == DisputeSubstate.SESSION:
            self._create_ui_session()
        elif self.substate == DisputeSubstate.COMPOSER:
            self._create_ui_composer()
        elif self.substate == DisputeSubstate.TALLY:
            self._create_ui_tally()

    def _destroy_ui(self) -> None:
        """Kill all pygame_gui elements (CLAUDE.md lifecycle invariant)."""
        if self.back_button is not None:
            self.back_button.kill()
        self.back_button = None
        if self.preview_label is not None:
            self.preview_label.kill()
        self.preview_label = None
        for btn in list(self._dispute_buttons.values()):
            btn.kill()
        self._dispute_buttons.clear()
        for btn in list(self._action_buttons.values()):
            btn.kill()
        self._action_buttons.clear()
        for btn in list(self._composer_buttons.values()):
            btn.kill()
        self._composer_buttons.clear()

    def _create_ui_list(self) -> None:
        """LIST substate: dispute list OR empty / locked / loading / error."""
        if self.list_state != DisputeListState.READY:
            # Empty / locked / loading / error: only the back button is needed.
            return
        ids = self.dispute_manager.get_pending_dispute_ids()
        for idx, dispute_id in enumerate(ids):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(20),
                    BODY_TOP_Y + scale_y(20 + idx * 50),
                    PANEL_W - scale_x(40),
                    scale_y(40),
                ),
                text=f"Enter session: {dispute_id}",
                manager=self.ui_manager,
            )
            self._dispute_buttons[dispute_id] = btn

    def _create_ui_corridor(self) -> None:
        """CORRIDOR substate: per-delegate Talk buttons + back-to-list."""
        if self.active_dispute is None:
            return
        for idx, (d_id, d) in enumerate(self.active_dispute.delegates.items()):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(20),
                    BODY_TOP_Y + scale_y(20 + idx * 50),
                    PANEL_W - scale_x(40),
                    scale_y(40),
                ),
                text=f"Talk to {d.name} (D{self.dispute_manager.get_corridor_difficulty(self.active_dispute, d_id)})",
                manager=self.ui_manager,
            )
            self._composer_buttons[d_id] = btn

    def _create_ui_session(self) -> None:
        """SESSION substate: round summary + ARGUE / MEDIATE / ABSTAIN / VOTE.

        SA-P5: when venue_id is ``"crimson_wreckers_guild"`` the four action
        buttons are enabled or disabled according to the player's Wreckers'
        Guild tier. Apprentices are observers (all four disabled). Journeymen
        can argue/vote/abstain but not mediate. Masters can do everything.
        Other venues preserve the existing all-enabled flow.
        """
        if self.active_dispute is None:
            return
        labels = ["Argue", "Mediate", "Abstain", "Vote Now"]
        # Compute per-tier enable set only at the Reach venue.
        enabled_keys: Optional[frozenset[str]] = None
        if self.venue_id == "crimson_wreckers_guild":
            tier = current_tier_id(self.player.sub_reputation)
            enabled_keys = _TIER_ACTION_ENABLE.get(tier, frozenset())
        for idx, label in enumerate(labels):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(20 + idx * 150),
                    BODY_TOP_Y + scale_y(BODY_H - 80),
                    scale_x(140),
                    scale_y(40),
                ),
                text=label,
                manager=self.ui_manager,
            )
            key = label.lower().replace(" ", "_")
            self._action_buttons[key] = btn
            # Disable buttons not in the tier's allowed set.
            if enabled_keys is not None and key not in enabled_keys:
                btn.disable()

    def _create_ui_composer(self) -> None:
        """COMPOSER substate: framing / evidence / audience selectors + preview."""
        if self.active_dispute is None:
            return
        # Framing buttons
        for idx, framing in enumerate(self.active_dispute.eligible_framings):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(20),
                    BODY_TOP_Y + scale_y(20 + idx * 36),
                    scale_x(220),
                    scale_y(32),
                ),
                text=f"Framing: {framing}",
                manager=self.ui_manager,
            )
            self._composer_buttons[f"framing:{framing}"] = btn
        # Audience buttons
        for idx, (d_id, d) in enumerate(self.active_dispute.delegates.items()):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(260),
                    BODY_TOP_Y + scale_y(20 + idx * 36),
                    scale_x(180),
                    scale_y(32),
                ),
                text=f"Audience: {d.name}",
                manager=self.ui_manager,
            )
            self._composer_buttons[f"audience:{d_id}"] = btn
        # Evidence buttons
        for idx, ev in enumerate(self.active_dispute.eligible_evidence):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + scale_x(460),
                    BODY_TOP_Y + scale_y(20 + idx * 36),
                    scale_x(220),
                    scale_y(32),
                ),
                text=f"Evidence: {ev}",
                manager=self.ui_manager,
            )
            self._composer_buttons[f"evidence:{ev}"] = btn
        # Submit button
        self._composer_buttons["submit"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(140),
                BODY_TOP_Y + scale_y(BODY_H - 80),
                scale_x(120),
                scale_y(36),
            ),
            text="Submit",
            manager=self.ui_manager,
        )
        self.preview_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                PANEL_X + scale_x(20),
                BODY_TOP_Y + scale_y(BODY_H - 80),
                scale_x(400),
                scale_y(32),
            ),
            text=self._compose_preview_text(),
            manager=self.ui_manager,
        )

    def _create_ui_tally(self) -> None:
        """TALLY substate: result panel + Continue."""
        self._action_buttons["continue"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(140),
                BODY_TOP_Y + scale_y(BODY_H - 80),
                scale_x(120),
                scale_y(36),
            ),
            text="Continue",
            manager=self.ui_manager,
        )

    # ------------------------------------------------------------------
    # Composer live preview
    # ------------------------------------------------------------------

    def _compose_preview_text(self) -> str:
        if self.active_dispute is None:
            return ""
        resolution = self.dispute_manager.preview_argument(
            self.active_dispute, self.composer_argument
        )
        self.composer_resolution = resolution
        if resolution.error:
            return self._preview_label_text_error(resolution.error)
        verdict = "PASSES" if resolution.passes else "FAILS"
        return (
            f"Effective {resolution.effective_floor} "
            f"vs Difficulty {resolution.difficulty}. {verdict}"
        )

    def _preview_label_text_error(self, error: str) -> str:
        if error == "framing_required":
            return "Pick a framing to compose this argument."
        if error == "audience_required":
            return "Pick an audience to compose this argument."
        return "Argument incomplete."

    def update_composer_selection(
        self,
        *,
        framing: Optional[str] = None,
        audience_delegate_id: Optional[str] = None,
        evidence: Optional[str] = None,
        responds_to: Optional[str] = None,
        is_mediation: Optional[bool] = None,
    ) -> None:
        """Mutate composer state and refresh the live preview text.

        Public so view tests can drive selections without simulating
        button clicks. The preview label updates in place — no UI
        rebuild — so the player sees the verdict change immediately.
        """
        if framing is not None:
            self.composer_argument.framing = framing
        if audience_delegate_id is not None:
            self.composer_argument.audience_delegate_id = audience_delegate_id
        if evidence is not None:
            self.composer_argument.evidence = evidence or None
        if responds_to is not None:
            self.composer_argument.responds_to = responds_to or None
        if is_mediation is not None:
            self.composer_argument.is_mediation = is_mediation
        self._refresh_preview_label()

    def _refresh_preview_label(self) -> None:
        if self.preview_label is None:
            return
        self.preview_label.set_text(self._compose_preview_text())

    # ------------------------------------------------------------------
    # Actions wired by the view (used by tests + Game)
    # ------------------------------------------------------------------

    def open_dispute(self, dispute_id: str) -> None:
        dispute = self.dispute_manager.get_pending_dispute(dispute_id)
        if dispute is None:
            return
        self.active_dispute = dispute
        self._switch_substate(DisputeSubstate.SESSION)

    def open_corridor(self) -> None:
        self._switch_substate(DisputeSubstate.CORRIDOR)

    def open_composer(self, *, is_mediation: bool = False) -> None:
        self.composer_argument = PoliticsArgument(
            framing="",
            audience_delegate_id="",
            is_mediation=is_mediation,
        )
        self._switch_substate(DisputeSubstate.COMPOSER)
        self._maybe_show_composer_tip()

    def submit_composer(self) -> Optional[ArgumentResolution]:
        if self.active_dispute is None:
            return None
        resolution = self.dispute_manager.submit_argument(
            self.active_dispute, self.composer_argument
        )
        self.dispute_manager.advance_round(self.active_dispute)
        if self.active_dispute.phase == DisputePhase.RESOLVED:
            self._switch_substate(DisputeSubstate.TALLY)
        else:
            self._switch_substate(DisputeSubstate.SESSION)
        return resolution

    def cast_vote(self) -> None:
        if self.active_dispute is None:
            return
        self.dispute_manager.cast_vote(self.active_dispute)
        self._switch_substate(DisputeSubstate.TALLY)

    def abstain(self) -> None:
        if self.active_dispute is None:
            return
        self.dispute_manager.abstain_round(self.active_dispute)
        if self.active_dispute.phase == DisputePhase.RESOLVED:
            self._switch_substate(DisputeSubstate.TALLY)

    def back_to_list(self) -> None:
        self.active_dispute = None
        self._refresh_list_state()
        self._switch_substate(DisputeSubstate.LIST, force_recreate=True)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        # PT-M tutorial overlay consumes input while active.
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self.substate == DisputeSubstate.LIST:
                    self.next_state = GameState.STATION_HUB
                else:
                    self.back_to_list()
                return
            for d_id, btn in list(self._dispute_buttons.items()):
                if event.ui_element == btn:
                    self.open_dispute(d_id)
                    return
            for key, btn in list(self._action_buttons.items()):
                if event.ui_element == btn:
                    if key == "argue":
                        self.open_composer(is_mediation=False)
                    elif key == "mediate":
                        self.open_composer(is_mediation=True)
                    elif key == "abstain":
                        self.abstain()
                    elif key == "vote_now":
                        self.cast_vote()
                    elif key == "continue":
                        self.back_to_list()
                    return
            for key, btn in list(self._composer_buttons.items()):
                if event.ui_element == btn:
                    if key == "submit":
                        self.submit_composer()
                    elif key.startswith("framing:"):
                        self.update_composer_selection(framing=key.split(":", 1)[1])
                    elif key.startswith("audience:"):
                        self.update_composer_selection(audience_delegate_id=key.split(":", 1)[1])
                    elif key.startswith("evidence:"):
                        self.update_composer_selection(evidence=key.split(":", 1)[1])
                    return

    # ------------------------------------------------------------------
    # Tick + render
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        # PT-M overlay tick.
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None

    def _apply_venue_theme(self, screen: pygame.Surface) -> None:
        """SA-P5: apply per-venue color palette to the background surface.

        Pulls the :class:`VenueTheme` for the current venue_id from
        :data:`_VENUE_THEMES`. Verdant + Haven's Rest receive neutral
        defaults so their SA-P3 / SA-P4 visuals are unchanged. Crimson
        Reach gets a dim red tint pulled from the ReachDarkLayout palette.
        Called once per render frame from :meth:`render` before the
        main-panel draws, so the tint sits behind all panels.
        """
        theme = _VENUE_THEMES.get(self.venue_id, _DEFAULT_VENUE_THEME)
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.panel_bg_color, theme.bg_dim_alpha))
        screen.blit(dim, (0, 0))

    def render(self, screen: pygame.Surface) -> None:
        screen.fill(Colors.BG_DARK)
        self._apply_venue_theme(screen)
        self._render_header(screen)
        if self.substate == DisputeSubstate.LIST:
            self._render_body_list(screen)
        elif self.substate == DisputeSubstate.SESSION:
            self._render_body_session(screen)
        elif self.substate == DisputeSubstate.CORRIDOR:
            self._render_body_corridor(screen)
        elif self.substate == DisputeSubstate.COMPOSER:
            self._render_body_composer(screen)
        elif self.substate == DisputeSubstate.TALLY:
            self._render_body_tally(screen)
        # PT-M overlay renders on top of pygame_gui content.
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            self._first_time_tip.render(screen)

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_header(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, PANEL_TOP_Y, PANEL_W, HEADER_H), alpha=220)
        title_text = "Council Chamber"
        title_surf = self.title_font.render(title_text, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title_surf, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(14)))

    def _render_body_list(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=200)
        if self.list_state == DisputeListState.EMPTY:
            text = "Council in recess. Next session in 3 days."
        elif self.list_state == DisputeListState.LOCKED:
            text = "You don't have standing to participate in these sessions."
        elif self.list_state == DisputeListState.LOADING:
            text = "Loading session data."
        elif self.list_state == DisputeListState.ERROR:
            text = "Session data unavailable."
        elif self.list_state == DisputeListState.LOCKED_OUT_ANNUAL:
            days = max(0, self._annual_recess_days_remaining)
            text = f"Annual Congress in recess. Next session in {days} days."
        elif self.list_state == DisputeListState.LOCKED_NO_MEMBERSHIP:
            text = LOCKED_NO_MEMBERSHIP_TEXT
        else:
            return
        for i, line in enumerate(word_wrap(text, self.body_font, PANEL_W - scale_x(40))):
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(
                surf,
                (PANEL_X + scale_x(20), BODY_TOP_Y + scale_y(40 + i * 22)),
            )

    def _render_body_session(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=200)
        if self.active_dispute is None:
            return
        round_text = (
            f"Round {self.active_dispute.current_round} of {self.active_dispute.round_count}"
        )
        surf = self.subtitle_font.render(round_text, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(surf, (PANEL_X + scale_x(20), BODY_TOP_Y + scale_y(20)))

    def _render_body_corridor(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=200)

    def _render_body_composer(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=200)

    def _render_body_tally(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=200)
        if self.active_dispute is None:
            return
        text = f"Outcome: {self.active_dispute.resolved_outcome}"
        surf = self.subtitle_font.render(text, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(surf, (PANEL_X + scale_x(20), BODY_TOP_Y + scale_y(20)))

    # ------------------------------------------------------------------
    # Helpers used by Game.py
    # ------------------------------------------------------------------

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
