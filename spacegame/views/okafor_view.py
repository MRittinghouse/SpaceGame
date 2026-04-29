"""SA-R1: Okafor Institute Medical Wing view (research patronage).

Renders the project board for Dr. Kweon's funded-research venue,
exposes fund / team-fund / IP-disposition actions, and surfaces a
first-visit PT-M tip overlay. Pure presentation + thin orchestration;
the project lifecycle, deterministic resolution, and royalty math
live in :mod:`spacegame.models.okafor_research`.

The skill-wiring integration test at ``tests/test_models/
test_skill_wiring_integration.py:661-662`` asserts that
``research_yield_bonus`` and ``research_risk_reduction`` are consumed
by this file specifically — that test locks the filename to
``okafor_view.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
from spacegame.constants.flags import (
    met_npc,
    okafor_collaborator_share,
    okafor_failure_debrief_shown,
    okafor_first_failure_seen,
    okafor_legacy_first_heal_seen,
    okafor_legacy_first_profit_seen,
    okafor_legacy_heal_ending_seen,
    okafor_legacy_heal_pattern_seen,
    okafor_legacy_profit_ending_seen,
    okafor_legacy_profit_pattern_seen,
    okafor_patent_disposed_first,
    okafor_project_funded_first,
    seen_okafor_tip,
)
from spacegame.data_loader import get_data_loader
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel, word_wrap
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SUBTITLE,
    FONT_TITLE,
    get_font,
)
from spacegame.models.dialogue import DialogueNode, DialogueTree
from spacegame.models.okafor_research import (
    SELL_LUMP_SUM_RATE,
    OkaforResearchState,
    PatentHolding,
    compute_team_fund_cost,
    fund_project,
    get_template,
    pending_legacy_beat,
    roll_offers,
    seed_for_window,
    transition_patent_to_licensed,
    transition_patent_to_sold,
)
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster


# Layout
PANEL_X = scale_x(40)
PANEL_W = WINDOW_WIDTH - scale_x(80)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)

# Two-column body: Kweon dock left, project board right.
BODY_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BODY_H = scale_y(380)
LEFT_W = scale_x(360)
RIGHT_X = PANEL_X + LEFT_W + scale_x(20)
RIGHT_W = PANEL_W - LEFT_W - scale_x(20)

# Holdings + active panels stack below the body.
LOWER_TOP_Y = BODY_TOP_Y + BODY_H + scale_y(12)
LOWER_H = scale_y(160)

# Accent: cool blue-violet for the Institute (medical-research palette).
ACCENT_COLOR = (140, 170, 220)


# Researcher dock metadata (locked names, banned-list-clean).
RESEARCHER_DOCK: tuple[tuple[str, str, str], ...] = (
    ("dr_iris_navarro", "Dr. Iris Navarro", "Clinical Lead"),
    ("theo_brandt", "Theo Brandt", "Bench Engineer"),
    ("sana_dey", "Sana Dey", "Junior Researcher"),
)

# NPC dock entries: (speaker_id, display_name, role, default_dialogue_id).
# Kweon's dialogue id is overridden by :meth:`_kweon_dialogue_id` based on
# the failure-debrief state. Nuri is conditionally surfaced when she is in
# the active crew.
KWEON_DOCK_ENTRY: tuple[str, str, str, str] = (
    "kweon_director",
    "Dr. Nadia Kweon",
    "Director",
    "kweon_okafor_intro",
)
NURI_DOCK_ENTRY: tuple[str, str, str, str] = (
    "nuri_solberg",
    "Nuri Solberg",
    "Independent Patron",
    "nuri_solberg_okafor_collaborator",
)
RESEARCHER_DOCK_ENTRIES: tuple[tuple[str, str, str, str], ...] = (
    ("dr_iris_navarro", "Dr. Iris Navarro", "Clinical Lead", "iris_navarro_okafor"),
    ("theo_brandt", "Theo Brandt", "Bench Engineer", "theo_brandt_okafor"),
    ("sana_dey", "Sana Dey", "Junior Researcher", "sana_dey_okafor"),
)

# SA-R2: map each arc-beat tree id → (seen_flag_fn, optional_ending_value).
# The close-handler uses this for O(1) flag dispatch without branching on
# tree id inline. Ending entries carry a non-empty string; others carry "".
_LEGACY_ARC_TREE_TO_FLAG: dict[str, tuple[str, str]] = {
    "kweon_legacy_first_heal": (okafor_legacy_first_heal_seen(), ""),
    "kweon_legacy_first_profit": (okafor_legacy_first_profit_seen(), ""),
    "kweon_legacy_heal_pattern": (okafor_legacy_heal_pattern_seen(), ""),
    "kweon_legacy_profit_pattern": (okafor_legacy_profit_pattern_seen(), ""),
    "kweon_legacy_heal_ending": (okafor_legacy_heal_ending_seen(), "heal"),
    "kweon_legacy_profit_ending": (okafor_legacy_profit_ending_seen(), "profit"),
}


class OkaforView(BaseView):
    """Project board + Kweon dock for the Okafor Institute Medical Wing."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        crew_roster: Optional["CrewRoster"] = None,
    ) -> None:
        """Initialize the Okafor Institute view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player. Mutated during fund / team-fund
                flows and IP dispositions.
            crew_roster: Optional active crew roster. Used to read the
                ``research_yield_bonus`` + ``research_risk_reduction``
                bonuses for the resolution preview. ``None`` is fine
                in tests; the engine wires it for the production path.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self._crew_roster = crew_roster
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.body_font = get_font("dialogue", FONT_BODY)
        self.label_font = get_font("label", FONT_SUBTITLE)
        self.value_font = get_font("stats", FONT_LG)

        # UI element refs
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self._fund_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._team_fund_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._license_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._sell_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        # Per-speaker NPC dock buttons (Kweon, 3 researchers, Nuri-when-crewed).
        self._npc_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._dialogue_continue_button: Optional[pygame_gui.elements.UIButton] = None

        # In-view dialogue panel state. When ``_active_dialogue_tree`` is
        # non-None, the Kweon dock area is occupied by a dialogue node
        # rather than the static dock chrome.
        self._active_dialogue_tree: Optional[DialogueTree] = None
        self._active_dialogue_node_id: Optional[str] = None
        # Tracks whether the currently-open Kweon tree is the failure
        # debrief, so the dismiss handler can set the seen flag.
        self._active_dialogue_is_failure_debrief: bool = False

        # Status / feedback
        self.message: Optional[str] = None
        self.message_timer: float = 0.0

        # First-time tip overlay (PT-M pattern)
        self._tip_overlay: Optional[FirstTimeTipOverlay] = None

        # First-failure debrief banner — True when the failure tick has
        # set ``okafor_first_failure_seen`` and Kweon's debrief tree has
        # not yet been dismissed (``okafor_failure_debrief_shown``).
        self._failure_debrief_pending: bool = False

        # Cached offer ids for the current visit.
        self._offer_template_ids: list[str] = []

        # Background — quiet, low-light institutional register.
        self.background = AnimatedBackground("station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=8842)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(170)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Activate the view, refresh the board, fire the first-time tip."""
        super().on_enter()
        logger.info("Entered Okafor Institute Medical Wing")
        # Mark Kweon as met if some other path hasn't already done so.
        self.player.dialogue_flags.setdefault(met_npc("kweon_director"), True)
        self._refresh_failure_debrief_pending()
        self._refresh_offers()
        self._create_ui()
        self._maybe_show_tip()

    def on_exit(self) -> None:
        """Deactivate the view and tear down UI."""
        self._destroy_ui()
        self._tip_overlay = None
        self._active_dialogue_tree = None
        self._active_dialogue_node_id = None
        self._active_dialogue_is_failure_debrief = False
        super().on_exit()

    def _refresh_failure_debrief_pending(self) -> None:
        """Pending = first failure has occurred AND debrief tree not yet shown."""
        flags = self.player.dialogue_flags
        self._failure_debrief_pending = bool(
            flags.get(okafor_first_failure_seen()) and not flags.get(okafor_failure_debrief_shown())
        )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _ensure_state(self) -> OkaforResearchState:
        """Return the player's :class:`OkaforResearchState`, creating it if absent."""
        if self.player.okafor_research_state is None:
            self.player.okafor_research_state = OkaforResearchState()
        return self.player.okafor_research_state

    # ------------------------------------------------------------------
    # Board state
    # ------------------------------------------------------------------

    def _refresh_offers(self) -> None:
        """Populate the offer list using the deterministic 30-day roll.

        Same-window visits return the same offers (acceptance #3);
        crossing the 30-day boundary forces a fresh roll. Already-funded
        templates are filtered out so the same template cannot be funded
        twice in one window (acceptance #4).
        """
        state = self._ensure_state()
        window = seed_for_window(self.player.game_day)
        if state.slot_seed_window != window or not state.slot_offers:
            offers = roll_offers(self.player.name, self.player.game_day)
            state.slot_seed_window = window
            state.slot_offers = offers
        active_ids = set(state.active_projects.keys())
        self._offer_template_ids = [tid for tid in state.slot_offers if tid not in active_ids]

    def get_offered_template_ids(self) -> list[str]:
        """Return cached offer template ids for tests + the renderer."""
        return list(self._offer_template_ids)

    # ------------------------------------------------------------------
    # UI lifecycle
    # ------------------------------------------------------------------

    def _create_ui(self) -> None:
        """Create all pygame_gui elements for the current state."""
        self._destroy_ui()

        # Back button — always present.
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(140),
                PANEL_TOP_Y + scale_y(20),
                scale_x(120),
                scale_y(36),
            ),
            text="Back to Station",
            manager=self.ui_manager,
        )

        # NPC dock or dialogue-panel continue button.
        if self._active_dialogue_tree is None:
            self._create_npc_dock_buttons()
        else:
            self._create_dialogue_continue_button()

        # Fund buttons — one per visible offer.
        card_h = scale_y(50)
        card_pad = scale_y(8)
        for idx, template_id in enumerate(self._offer_template_ids):
            row_y = BODY_TOP_Y + scale_y(50) + idx * (card_h + card_pad)
            fund_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    RIGHT_X + RIGHT_W - scale_x(220),
                    row_y + scale_y(8),
                    scale_x(100),
                    scale_y(34),
                ),
                text="Fund",
                manager=self.ui_manager,
            )
            team_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    RIGHT_X + RIGHT_W - scale_x(112),
                    row_y + scale_y(8),
                    scale_x(100),
                    scale_y(34),
                ),
                text="Team-fund",
                manager=self.ui_manager,
            )
            self._fund_buttons[template_id] = fund_btn
            self._team_fund_buttons[template_id] = team_btn

        # Holdings: license / sell buttons for each held / licensed patent.
        state = self._ensure_state()
        for idx, holding in enumerate(state.holdings):
            if holding.state == "sold":
                continue
            row_y = LOWER_TOP_Y + scale_y(40) + idx * scale_y(36)
            if holding.state == "held":
                license_btn = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(
                        PANEL_X + PANEL_W - scale_x(220),
                        row_y,
                        scale_x(100),
                        scale_y(28),
                    ),
                    text="License",
                    manager=self.ui_manager,
                )
                self._license_buttons[holding.holding_id] = license_btn
            sell_btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + PANEL_W - scale_x(112),
                    row_y,
                    scale_x(100),
                    scale_y(28),
                ),
                text="Sell",
                manager=self.ui_manager,
            )
            self._sell_buttons[holding.holding_id] = sell_btn

    def _create_npc_dock_buttons(self) -> None:
        """Place one button per visible speaker in the Kweon dock area."""
        entries = self._dock_entries()
        if not entries:
            return
        x = PANEL_X + scale_x(16)
        # Stack the buttons vertically inside the left dock panel under
        # Kweon's name + introductory line. Top of the button column sits
        # roughly two-thirds down the dock.
        y = BODY_TOP_Y + scale_y(160)
        button_h = scale_y(34)
        button_w = LEFT_W - scale_x(32)
        gap = scale_y(6)
        for idx, (speaker_id, name, role, _dialogue_id) in enumerate(entries):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    x,
                    y + idx * (button_h + gap),
                    button_w,
                    button_h,
                ),
                text=f"{name} · {role}",
                manager=self.ui_manager,
            )
            self._npc_buttons[speaker_id] = btn

    def _create_dialogue_continue_button(self) -> None:
        """Single Continue button while an NPC dialogue is open."""
        self._dialogue_continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + LEFT_W - scale_x(140),
                BODY_TOP_Y + BODY_H - scale_y(48),
                scale_x(124),
                scale_y(34),
            ),
            text="Continue",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all pygame_gui elements (CLAUDE.md lifecycle invariant)."""
        if self.back_button is not None:
            self.back_button.kill()
        self.back_button = None
        if self._dialogue_continue_button is not None:
            self._dialogue_continue_button.kill()
        self._dialogue_continue_button = None
        for btn in self._fund_buttons.values():
            btn.kill()
        self._fund_buttons.clear()
        for btn in self._team_fund_buttons.values():
            btn.kill()
        self._team_fund_buttons.clear()
        for btn in self._license_buttons.values():
            btn.kill()
        self._license_buttons.clear()
        for btn in self._sell_buttons.values():
            btn.kill()
        self._sell_buttons.clear()
        for btn in self._npc_buttons.values():
            btn.kill()
        self._npc_buttons.clear()

    # ------------------------------------------------------------------
    # First-time tip
    # ------------------------------------------------------------------

    def _maybe_show_tip(self) -> None:
        """Fire the PT-M overlay on first entry per save."""
        if self.player.dialogue_flags.get(seen_okafor_tip()):
            return

        def _on_dismiss() -> None:
            self.player.dialogue_flags[seen_okafor_tip()] = True

        self._tip_overlay = FirstTimeTipOverlay(
            title="Patronage",
            body=(
                "Fund a project and the days advance toward a deterministic "
                "outcome. Successes return a patent you can license or sell."
            ),
            on_dismiss=_on_dismiss,
        )

    # ------------------------------------------------------------------
    # NPC dock + dialogue panel
    # ------------------------------------------------------------------

    def _is_nuri_in_crew(self) -> bool:
        """Return True when Nuri Solberg is in the player's active crew.

        Tries the canonical CrewRoster path first; falls back to the
        flat ``player.crew_state.get("active", [])`` list used by tests.
        """
        if self._crew_roster is not None and hasattr(self._crew_roster, "get_recruited_members"):
            try:
                return any(
                    template.id == "nuri_solberg"
                    for template, _state in self._crew_roster.get_recruited_members()
                )
            except (AttributeError, TypeError):
                pass
        active = self.player.crew_state.get("active", []) if self.player.crew_state else []
        return "nuri_solberg" in active

    def get_visible_dock_speaker_ids(self) -> list[str]:
        """Return speaker_ids surfaced by the Kweon dock for the current state.

        Kweon and the three Institute researchers are always present.
        Nuri Solberg is gated on active-crew membership.
        """
        ids = [KWEON_DOCK_ENTRY[0]]
        ids.extend(speaker_id for speaker_id, _n, _r, _did in RESEARCHER_DOCK_ENTRIES)
        if self._is_nuri_in_crew():
            ids.append(NURI_DOCK_ENTRY[0])
        return ids

    def _dock_entries(self) -> list[tuple[str, str, str, str]]:
        """Return the dock-entry tuples for the currently-visible speakers."""
        visible = set(self.get_visible_dock_speaker_ids())
        entries: list[tuple[str, str, str, str]] = []
        if KWEON_DOCK_ENTRY[0] in visible:
            entries.append(KWEON_DOCK_ENTRY)
        for entry in RESEARCHER_DOCK_ENTRIES:
            if entry[0] in visible:
                entries.append(entry)
        if NURI_DOCK_ENTRY[0] in visible:
            entries.append(NURI_DOCK_ENTRY)
        return entries

    def _dialogue_id_for_speaker(self, speaker_id: str) -> Optional[str]:
        """Resolve which authored dialogue tree to open for a speaker."""
        if speaker_id == KWEON_DOCK_ENTRY[0]:
            return self._kweon_dialogue_id()
        for sid, _name, _role, dialogue_id in RESEARCHER_DOCK_ENTRIES:
            if sid == speaker_id:
                return dialogue_id
        if speaker_id == NURI_DOCK_ENTRY[0]:
            return NURI_DOCK_ENTRY[3]
        return None

    def _kweon_dialogue_id(self) -> str:
        """Pick the Kweon tree based on state.

        Priority (SA-R2 Decision 4):
          1. ``kweon_failure_debrief`` — a project has failed and the
             debrief tree has not yet been dismissed.
          2. Next pending legacy-arc beat from :func:`pending_legacy_beat`
             — ethics counter thresholds met and beat not yet seen.
          3. ``kweon_okafor_intro`` — ambient greeting.
        """
        if self._failure_debrief_pending:
            return "kweon_failure_debrief"
        state = self.player.okafor_research_state
        if state is not None:
            beat = pending_legacy_beat(state, self.player.dialogue_flags)
            if beat is not None:
                return beat
        return KWEON_DOCK_ENTRY[3]

    @staticmethod
    def _name_for_speaker(speaker_id: str) -> str:
        if speaker_id == KWEON_DOCK_ENTRY[0]:
            return KWEON_DOCK_ENTRY[1]
        for sid, name, _role, _did in RESEARCHER_DOCK_ENTRIES:
            if sid == speaker_id:
                return name
        if speaker_id == NURI_DOCK_ENTRY[0]:
            return NURI_DOCK_ENTRY[1]
        return speaker_id

    def _open_npc_dialogue(self, speaker_id: str) -> None:
        """Begin a venue dialogue at the tree's start node.

        No-op for unknown ids (safe boundary handling).
        """
        dialogue_id = self._dialogue_id_for_speaker(speaker_id)
        if dialogue_id is None:
            return
        tree = get_data_loader().get_dialogue(dialogue_id)
        if tree is None:
            logger.warning("Okafor dialogue '%s' not found", dialogue_id)
            return
        self._active_dialogue_tree = tree
        self._active_dialogue_node_id = tree.start_node_id
        self._active_dialogue_is_failure_debrief = dialogue_id == "kweon_failure_debrief"
        # First-meeting handshake — Kweon is always met on view entry, so
        # this is mostly defensive for direct-call test paths.
        if speaker_id == KWEON_DOCK_ENTRY[0]:
            self.player.dialogue_flags.setdefault(met_npc("kweon_director"), True)
        self._create_ui()

    def _advance_dialogue(self) -> None:
        """Follow the first response's next_node_id; close on null/missing."""
        tree = self._active_dialogue_tree
        node_id = self._active_dialogue_node_id
        if tree is None or node_id is None:
            return
        node = tree.nodes.get(node_id)
        if node is None or not node.responses:
            self._close_active_dialogue()
            return
        response = node.responses[0]
        if response.set_flag:
            self.player.dialogue_flags[response.set_flag] = True
        next_id = response.next_node_id
        if not next_id:
            self._close_active_dialogue()
            return
        if next_id not in tree.nodes:
            logger.warning("Okafor dialogue: missing next_node '%s'", next_id)
            self._close_active_dialogue()
            return
        self._active_dialogue_node_id = next_id

    def _close_active_dialogue(self) -> None:
        """Clear the active dialogue. Sets the debrief-shown flag if applicable.

        SA-R2: also sets the matching ``okafor_legacy_*_seen`` flag when an
        arc-beat tree closes, and writes ``legacy_ending`` for ending trees.
        """
        if self._active_dialogue_is_failure_debrief:
            self.player.dialogue_flags[okafor_failure_debrief_shown()] = True
            self._refresh_failure_debrief_pending()
        elif self._active_dialogue_tree is not None:
            tree_id = self._active_dialogue_tree.id
            entry = _LEGACY_ARC_TREE_TO_FLAG.get(tree_id)
            if entry is not None:
                seen_flag, ending = entry
                self.player.dialogue_flags[seen_flag] = True
                if ending and self.player.okafor_research_state is not None:
                    self.player.okafor_research_state.legacy_ending = ending
        self._active_dialogue_tree = None
        self._active_dialogue_node_id = None
        self._active_dialogue_is_failure_debrief = False
        self._create_ui()

    def get_active_dialogue_node(self) -> Optional[DialogueNode]:
        """Expose the active node for tests + the renderer."""
        tree = self._active_dialogue_tree
        node_id = self._active_dialogue_node_id
        if tree is None or node_id is None:
            return None
        return tree.nodes.get(node_id)

    # ------------------------------------------------------------------
    # Fund flow
    # ------------------------------------------------------------------

    def _fund_project(
        self,
        template_id: str,
        collaborators: list[str],
    ) -> bool:
        """Spend credits and insert an :class:`ActiveProject` into state.

        Returns True if the fund succeeded; False if the template is
        unknown, already active, or the player cannot afford the cost.
        """
        template = get_template(template_id)
        if template is None:
            return False
        state = self._ensure_state()
        if template_id in state.active_projects:
            self._show_message("That project is already in progress.")
            return False
        n_collaborators = len(collaborators)
        cost = compute_team_fund_cost(template.base_cost_credits, n_collaborators)
        if not self.player.can_afford(cost):
            self._show_message(f"Insufficient credits. {cost:,} CR required.")
            return False
        if not self.player.deduct_credits(cost):
            return False
        active = fund_project(state, template, self.player.game_day, collaborators)
        # Per-collaborator dialogue flag (SA-R2 hook).
        for researcher_id in collaborators:
            self.player.dialogue_flags[okafor_collaborator_share(researcher_id)] = True
        # First-funded journal trigger.
        if not self.player.dialogue_flags.get(okafor_project_funded_first()):
            self.player.dialogue_flags[okafor_project_funded_first()] = True
        # Refresh the board so the funded template no longer appears as an offer.
        self._refresh_offers()
        self._create_ui()
        self._show_message(
            f"Funded: {template.name}. {cost:,} CR. Resolves day {active.completion_day}."
        )
        return True

    # ------------------------------------------------------------------
    # IP disposition
    # ------------------------------------------------------------------

    def _license_patent(self, holding_id: str) -> bool:
        """Move a held patent to the ``"licensed"`` state."""
        state = self._ensure_state()
        holding = state.find_holding(holding_id)
        if holding is None or holding.state != "held":
            return False
        transition_patent_to_licensed(holding, self.player.game_day)
        if not self.player.dialogue_flags.get(okafor_patent_disposed_first()):
            self.player.dialogue_flags[okafor_patent_disposed_first()] = True
        self._create_ui()
        self._show_message(f"Patent licensed. Royalties begin day {holding.next_royalty_day}.")
        return True

    def _sell_patent(self, holding_id: str) -> bool:
        """Sell a held / licensed patent for the lump sum and remove it."""
        state = self._ensure_state()
        holding = state.find_holding(holding_id)
        if holding is None:
            return False
        lump = transition_patent_to_sold(holding)
        self.player.add_credits(lump)
        state.remove_holding(holding_id)
        if not self.player.dialogue_flags.get(okafor_patent_disposed_first()):
            self.player.dialogue_flags[okafor_patent_disposed_first()] = True
        self._create_ui()
        self._show_message(f"Patent sold. +{lump:,} CR.")
        return True

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process pygame_gui button presses + first-time tip overlay."""
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            if self._tip_overlay.handle_event(event):
                return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.STATION_HUB
                return
            if (
                self._dialogue_continue_button is not None
                and event.ui_element == self._dialogue_continue_button
            ):
                self._advance_dialogue()
                return
            for speaker_id, btn in list(self._npc_buttons.items()):
                if event.ui_element == btn:
                    self._open_npc_dialogue(speaker_id)
                    return
            for tid, btn in list(self._fund_buttons.items()):
                if event.ui_element == btn:
                    self._fund_project(tid, collaborators=[])
                    return
            for tid, btn in list(self._team_fund_buttons.items()):
                if event.ui_element == btn:
                    # Default team-fund pick: Nuri Solberg if available,
                    # else the senior clinical lead. The full collaborator
                    # picker is left as a follow-up surface (SA-R1-FOLLOW-2).
                    self._fund_project(tid, collaborators=["dr_iris_navarro"])
                    return
            for hid, btn in list(self._license_buttons.items()):
                if event.ui_element == btn:
                    self._license_patent(hid)
                    return
            for hid, btn in list(self._sell_buttons.items()):
                if event.ui_element == btn:
                    self._sell_patent(hid)
                    return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # Close an open dialogue panel first; only then exit the view.
            if self._active_dialogue_tree is not None:
                self._close_active_dialogue()
                return
            self.next_state = GameState.STATION_HUB

    # ------------------------------------------------------------------
    # Tick + render
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance background animation + tip overlay timer."""
        self.background.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None
        if self._tip_overlay is not None:
            self._tip_overlay.update(dt)
            if self._tip_overlay.dismissed:
                self._tip_overlay = None

    def render(self, screen: pygame.Surface) -> None:
        """Render the venue view."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))
        self._render_header(screen)
        self._render_kweon_dock(screen)
        self._render_project_board(screen)
        self._render_lower_panels(screen)
        if self.message:
            self._render_banner(screen, self.message, Colors.TEXT_SECONDARY)

    def render_top(self, screen: pygame.Surface) -> None:
        """Render the first-time tip overlay above pygame_gui chrome."""
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            self._tip_overlay.render(screen)

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_header(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            (PANEL_X, PANEL_TOP_Y, PANEL_W, HEADER_H),
            alpha=220,
            border_color=ACCENT_COLOR,
        )
        pygame.draw.rect(screen, ACCENT_COLOR, (PANEL_X, PANEL_TOP_Y, PANEL_W, 3))
        title = self.title_font.render("OKAFOR INSTITUTE", True, ACCENT_COLOR)
        screen.blit(title, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(14)))
        state = self._ensure_state()
        sub = self.subtitle_font.render(
            f"Medical Wing, Axiom Labs  ·  Funded: {state.completed_count + state.failed_count}"
            f"  ·  Trust: {state.kweon_relationship_value}/10",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(sub, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(56)))
        credits_label = self.body_font.render(
            f"Credits: {self.player.credits:,} CR",
            True,
            Colors.TEXT_PRIMARY,
        )
        screen.blit(credits_label, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(82)))

    def _render_kweon_dock(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, LEFT_W, BODY_H), alpha=210)
        if self._active_dialogue_tree is not None:
            self._render_dialogue_panel(screen)
            return
        x = PANEL_X + scale_x(16)
        y = BODY_TOP_Y + scale_y(14)
        title = self.label_font.render("AT THE INSTITUTE", True, ACCENT_COLOR)
        screen.blit(title, (x, y))
        y += scale_y(28)
        if self._failure_debrief_pending:
            body = "Kweon is at the bench. She is waiting on the project debrief."
        else:
            body = (
                "Director's office, the floor's bench engineers, the cataloging room. "
                "Speak with whoever is on shift today."
            )
        for line in word_wrap(body, self.body_font, LEFT_W - scale_x(32)):
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (x, y))
            y += self.body_font.get_linesize()

    def _render_dialogue_panel(self, screen: pygame.Surface) -> None:
        """Render the active speaker's current dialogue node inside the dock panel."""
        node = self.get_active_dialogue_node()
        if node is None:
            return
        x = PANEL_X + scale_x(16)
        y = BODY_TOP_Y + scale_y(14)
        speaker = self._name_for_speaker(node.speaker_id)
        header = self.label_font.render(speaker.upper(), True, ACCENT_COLOR)
        screen.blit(header, (x, y))
        y += scale_y(28)
        body_w = LEFT_W - scale_x(32)
        for line in word_wrap(node.text, self.body_font, body_w):
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (x, y))
            y += self.body_font.get_linesize()

    def _render_project_board(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (RIGHT_X, BODY_TOP_Y, RIGHT_W, BODY_H), alpha=210)
        x = RIGHT_X + scale_x(16)
        y = BODY_TOP_Y + scale_y(14)
        label = self.label_font.render("PROJECT BOARD", True, ACCENT_COLOR)
        screen.blit(label, (x, y))
        y += scale_y(30)
        card_h = scale_y(50)
        card_pad = scale_y(8)
        for idx, template_id in enumerate(self._offer_template_ids):
            tpl = get_template(template_id)
            if tpl is None:
                continue
            row_y = y + idx * (card_h + card_pad)
            tier_color = self._tier_color(tpl.risk_tier)
            pygame.draw.rect(
                screen,
                tier_color,
                pygame.Rect(x - scale_x(4), row_y - scale_y(2), 4, card_h),
            )
            name = self.subtitle_font.render(tpl.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (x + scale_x(8), row_y))
            cost_str = (
                f"{tpl.risk_tier.upper()}  ·  {tpl.base_cost_credits:,} CR  ·  "
                f"{tpl.base_duration_days}d  ·  payout {tpl.base_success_payout:,}"
            )
            cost_surf = self.body_font.render(cost_str, True, Colors.TEXT_SECONDARY)
            screen.blit(cost_surf, (x + scale_x(8), row_y + scale_y(22)))

    def _render_lower_panels(self, screen: pygame.Surface) -> None:
        draw_panel(screen, (PANEL_X, LOWER_TOP_Y, PANEL_W, LOWER_H), alpha=210)
        state = self._ensure_state()
        x = PANEL_X + scale_x(16)
        y = LOWER_TOP_Y + scale_y(10)
        active_label = self.label_font.render("ACTIVE PROJECTS", True, ACCENT_COLOR)
        screen.blit(active_label, (x, y))
        y += scale_y(22)
        if not state.active_projects:
            empty = self.body_font.render("No projects in progress.", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (x, y))
        else:
            for active in list(state.active_projects.values())[:3]:
                tpl = get_template(active.template_id)
                name = tpl.name if tpl else active.template_id
                line = (
                    f"{name}  ·  resolves day {active.completion_day}  ·  "
                    f"cost {active.cost_paid:,} CR"
                )
                surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
                screen.blit(surf, (x, y))
                y += self.body_font.get_linesize() + scale_y(2)
        # Holdings header on the right side of the same panel.
        hx = PANEL_X + PANEL_W // 2 + scale_x(20)
        hy = LOWER_TOP_Y + scale_y(10)
        holdings_label = self.label_font.render("HOLDINGS", True, ACCENT_COLOR)
        screen.blit(holdings_label, (hx, hy))
        hy += scale_y(22)
        if not state.holdings:
            empty = self.body_font.render("No patents on file.", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (hx, hy))
        else:
            for holding in state.holdings[:3]:
                self._render_holding_row(screen, holding, hx, hy)
                hy += self.body_font.get_linesize() + scale_y(8)

    def _render_holding_row(
        self,
        screen: pygame.Surface,
        holding: PatentHolding,
        x: int,
        y: int,
    ) -> None:
        tpl = get_template(holding.template_id)
        name = tpl.name if tpl else holding.template_id
        line = f"{name}  ·  {holding.state}  ·  payout {holding.success_payout:,}"
        if holding.state == "licensed":
            line += f"  ·  next royalty d{holding.next_royalty_day}"
        elif holding.state == "sold":
            line += f"  ·  ({int(holding.success_payout * SELL_LUMP_SUM_RATE):,} CR earned)"
        surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
        screen.blit(surf, (x, y))

    def _render_banner(self, screen: pygame.Surface, msg: str, color: tuple) -> None:
        rect = pygame.Rect(
            PANEL_X,
            WINDOW_HEIGHT - scale_y(60),
            PANEL_W,
            scale_y(40),
        )
        draw_panel(screen, (rect.x, rect.y, rect.w, rect.h), alpha=200)
        surf = self.subtitle_font.render(msg, True, color)
        screen.blit(surf, (rect.x + scale_x(16), rect.y + scale_y(10)))

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 4.0

    @staticmethod
    def _tier_color(tier: str) -> tuple[int, int, int]:
        if tier == "low":
            return (130, 200, 130)
        if tier == "high":
            return (230, 150, 130)
        return (200, 180, 110)
