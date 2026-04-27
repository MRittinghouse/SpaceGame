"""SA-2: Deep Shafts memorial / pilgrimage view.

Renders the memorial vista at the Breakstone Deep Shafts, surfaces a
named-NPC dock for Sten Brygaard (and a conditional dock for Marcus
Jin), runs the first-visit scripted scene, and applies the pilgrimage
rep tick + Sora Takahashi journal unlocks. Pure presentation + thin
orchestration; the rep / cooldown / cap math lives in
:mod:`spacegame.models.deep_shafts`.
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
    marcus_father_connection_seen,
    marcus_silent_vigil_seen,
    marcus_uprising_inheritance_seen,
    met_npc,
    received_miners_blessing_first,
    seen_deep_shafts_tip,
    talked_to_sten_brygaard,
    visited_deep_shafts,
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
from spacegame.models.deep_shafts import DeepShaftsState, apply_visit
from spacegame.models.dialogue import DialogueNode, DialogueTree
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster


# Layout
PANEL_X = scale_x(60)
PANEL_W = WINDOW_WIDTH - scale_x(120)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)
BODY_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BODY_H = scale_y(420)

# Memorial accent: warm gold matches the Miners' Union faction palette.
ACCENT_COLOR = (210, 175, 100)

# Dock layout
DOCK_TOP_Y = BODY_TOP_Y + BODY_H + scale_y(12)
DOCK_H = scale_y(80)

# Authored NPC dock metadata.
STEN_DOCK_ENTRY: tuple[str, str, str, str] = (
    "sten_brygaard",
    "Old Sten",
    "Custodian",
    "sten_brygaard_deep_shafts",
)
# Marcus's venue dock has three branch trees, picked by visit-state. The
# fourth tuple slot is the "default" / first-visit dialogue id; the view
# overrides it with the right branch via :meth:`_marcus_dialogue_id`.
MARCUS_DOCK_ENTRY: tuple[str, str, str, str] = (
    "marcus_jin",
    "Marcus Jin",
    "Mining Foreman",
    "marcus_jin_deep_shafts_silent_vigil",
)


class DeepShaftsView(BaseView):
    """Memorial venue view: vista + named-NPC docks + pilgrimage tick."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        crew_roster: Optional["CrewRoster"] = None,
    ) -> None:
        """Initialize the Deep Shafts memorial view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player. Mutated on entry: visit_count
                increments, faction-rep grants apply, journal flags fire.
            crew_roster: Optional active crew roster. When provided, the
                Marcus dock visibility check uses
                :meth:`CrewRoster.get_recruited_members`. When ``None``,
                the view falls back to ``player.crew_state.get("active",
                [])`` — convenient for tests that don't build a roster.
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

        # UI element refs (created in _create_ui)
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self._npc_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._dialogue_continue_button: Optional[pygame_gui.elements.UIButton] = None

        # Active in-view dialogue panel (Sten / Marcus) — when non-None,
        # the dock is showing a dialogue node rather than the contact list.
        self._active_dialogue_tree: Optional[DialogueTree] = None
        self._active_dialogue_node_id: Optional[str] = None

        # Status / scripted-scene message
        self.message: Optional[str] = None
        self.message_timer: float = 0.0
        self._scripted_scene_lines: list[str] = []

        # First-time tip overlay (PT-M)
        self._tip_overlay: Optional[FirstTimeTipOverlay] = None

        # Last visit's outcomes (rep grant + journal unlock) — surfaced
        # as a status banner so the player knows what happened on entry.
        self._last_rep_grant: int = 0
        self._last_journal_unlock: Optional[str] = None

        # Background — quiet, low-light memorial register.
        self.background = AnimatedBackground("station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=2267)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(180)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Activate the view, advance state, fire scene + tip."""
        super().on_enter()
        logger.info("Entered the Deep Shafts memorial")
        state = self._ensure_state()
        is_first_visit = not state.scripted_scene_played
        rep_grant, journal_id = apply_visit(state, self.player.game_day)
        self._last_rep_grant = rep_grant
        self._last_journal_unlock = journal_id
        self._apply_rep_grant(rep_grant, is_first_visit)
        if journal_id is not None:
            self.player.dialogue_flags[journal_id] = True
        # Producer for the ``visited_deep_shafts`` flag. Written as a
        # literal string (not the helper) so the SI-3 scanner pairs it
        # with the consumer on ``the_silent_shaft`` mission objective.
        # The :func:`visited_deep_shafts` helper is the canonical source
        # of truth; this assignment is equivalent.
        self.player.dialogue_flags["visited_deep_shafts"] = True
        assert self.player.dialogue_flags.get(visited_deep_shafts()) is True
        if is_first_visit:
            state.scripted_scene_played = True
            self._compose_scripted_scene_lines()
        self._create_ui()
        self._maybe_show_tip()

    def on_exit(self) -> None:
        """Deactivate the view and tear down UI."""
        self._destroy_ui()
        self._tip_overlay = None
        self._active_dialogue_tree = None
        self._active_dialogue_node_id = None
        super().on_exit()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _ensure_state(self) -> DeepShaftsState:
        """Return the player's :class:`DeepShaftsState`, creating it if absent."""
        if self.player.deep_shafts_state is None:
            self.player.deep_shafts_state = DeepShaftsState()
        return self.player.deep_shafts_state

    def _apply_rep_grant(self, amount: int, is_first_visit: bool) -> None:
        """Forward the pilgrimage rep grant through ``Player.modify_reputation``.

        Sets the ``received_miners_blessing_first`` flag exactly once on
        the first-visit grant so the SI-3 scanner pairs producer +
        consumer cleanly.
        """
        if amount <= 0:
            if is_first_visit:
                # Even with a zero grant on first visit (defensive), the
                # bookkeeping flag still fires so consumers don't stall.
                self.player.dialogue_flags[received_miners_blessing_first()] = True
            return
        self.player.modify_reputation("miners_union", amount)
        if is_first_visit:
            self.player.dialogue_flags[received_miners_blessing_first()] = True

    # ------------------------------------------------------------------
    # Scripted scene composition (acceptance #2)
    # ------------------------------------------------------------------

    def _compose_scripted_scene_lines(self) -> None:
        """Build the static narration lines for the first-visit scene.

        Tone is observational — the captain reads what is in front of
        them. Marcus's silence is the load-bearing beat when he is
        present (per ``character_voices.md:119``); the player-narrator
        does not interpret it.
        """
        lines = [
            "Section 3 keeps the lights low. The walls hold a century of drill marks.",
            "A bronze plaque sits where Sora Takahashi spoke: cargo bay 7, third shift.",
            "Someone has left fresh flowers. They are not the only fresh flowers here.",
        ]
        if self._is_marcus_in_crew():
            lines.append("Marcus Jin stops in front of the plaque. He does not say anything.")
        self._scripted_scene_lines = lines

    # ------------------------------------------------------------------
    # First-time tip
    # ------------------------------------------------------------------

    def _maybe_show_tip(self) -> None:
        """Fire the PT-M overlay on first entry per save (acceptance #11)."""
        if self.player.dialogue_flags.get(seen_deep_shafts_tip()):
            return

        def _on_dismiss() -> None:
            self.player.dialogue_flags[seen_deep_shafts_tip()] = True

        self._tip_overlay = FirstTimeTipOverlay(
            title="Memorial",
            body=(
                "Visit, listen, and return. Standing with the Miners' "
                "Union builds with each pilgrimage."
            ),
            on_dismiss=_on_dismiss,
        )

    # ------------------------------------------------------------------
    # NPC dock (acceptance #4 + #5)
    # ------------------------------------------------------------------

    def _is_marcus_in_crew(self) -> bool:
        """True if Marcus Jin is currently in the player's crew.

        Tries the canonical CrewRoster path first; falls back to the
        flat ``player.crew_state.get("active", [])`` list used by tests.
        """
        if self._crew_roster is not None and hasattr(self._crew_roster, "get_recruited_members"):
            try:
                return any(
                    template.id == "marcus_jin"
                    for template, _state in self._crew_roster.get_recruited_members()
                )
            except (AttributeError, TypeError):
                # Roster not initialized — fall back to the flat list.
                pass
        active = self.player.crew_state.get("active", []) if self.player.crew_state else []
        return "marcus_jin" in active

    def get_visible_dock_speaker_ids(self) -> list[str]:
        """Return speaker_ids surfaced by the venue dock for the current state.

        Sten is always present. Marcus is gated on crew membership AND
        ``learned_father_story`` per acceptance #5.
        """
        ids = [STEN_DOCK_ENTRY[0]]
        if self._is_marcus_in_crew() and self.player.dialogue_flags.get("learned_father_story"):
            ids.append(MARCUS_DOCK_ENTRY[0])
        return ids

    def _dock_entries(self) -> list[tuple[str, str, str, str]]:
        """Return the dock-entry tuples for the currently-visible speakers."""
        visible = set(self.get_visible_dock_speaker_ids())
        entries: list[tuple[str, str, str, str]] = []
        if STEN_DOCK_ENTRY[0] in visible:
            entries.append(STEN_DOCK_ENTRY)
        if MARCUS_DOCK_ENTRY[0] in visible:
            entries.append(MARCUS_DOCK_ENTRY)
        return entries

    def _open_npc_dialogue(self, speaker_id: str) -> None:
        """Begin a venue dialogue at the tree's start node.

        No-op for unknown ids (safe boundary handling).
        """
        dialogue_id = self._dialogue_id_for_speaker(speaker_id)
        if dialogue_id is None:
            return
        tree = get_data_loader().get_dialogue(dialogue_id)
        if tree is None:
            logger.warning("Deep Shafts dialogue '%s' not found", dialogue_id)
            return
        self._active_dialogue_tree = tree
        self._active_dialogue_node_id = tree.start_node_id
        # First-meeting handshake for Sten — the canonical "met" flag.
        if speaker_id == "sten_brygaard":
            self.player.dialogue_flags.setdefault(met_npc("sten_brygaard"), True)
        self._create_ui()

    def _dialogue_id_for_speaker(self, speaker_id: str) -> Optional[str]:
        if speaker_id == "sten_brygaard":
            return STEN_DOCK_ENTRY[3]
        if speaker_id == "marcus_jin":
            return self._marcus_dialogue_id()
        return None

    def _marcus_dialogue_id(self) -> str:
        """Resolve Marcus's branch dialogue id by player state.

        Acceptance #5 ordering:
          - Branch A (silent vigil) on visit 1 (or until ``marcus_silent_vigil_seen``).
          - Branch B (father connection) once Sten has been heard.
          - Branch C (Uprising inheritance) once branch B has played AND
            ``visit_count >= 5``.
        """
        flags = self.player.dialogue_flags
        state = self._ensure_state()
        if not flags.get(marcus_silent_vigil_seen()):
            return "marcus_jin_deep_shafts_silent_vigil"
        if (
            flags.get(marcus_father_connection_seen())
            and state.visit_count >= 5
            and not flags.get(marcus_uprising_inheritance_seen())
        ):
            return "marcus_jin_deep_shafts_uprising"
        if flags.get(talked_to_sten_brygaard()) and not flags.get(marcus_father_connection_seen()):
            return "marcus_jin_deep_shafts_father_connection"
        # Default: replay the silent-vigil tree as a quiet beat if no
        # higher-tier branch is unlocked yet.
        if flags.get(marcus_uprising_inheritance_seen()):
            return "marcus_jin_deep_shafts_uprising"
        if flags.get(marcus_father_connection_seen()):
            return "marcus_jin_deep_shafts_father_connection"
        return "marcus_jin_deep_shafts_silent_vigil"

    @staticmethod
    def _name_for_speaker(speaker_id: str) -> str:
        for sid, name, _title, _did in (STEN_DOCK_ENTRY, MARCUS_DOCK_ENTRY):
            if sid == speaker_id:
                return name
        return speaker_id

    def _advance_dialogue(self) -> None:
        """Follow the first response's next_node_id; fire set_flag along the way."""
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
            logger.warning("Deep Shafts dialogue: missing next_node '%s'", next_id)
            self._close_active_dialogue()
            return
        self._active_dialogue_node_id = next_id

    def _close_active_dialogue(self) -> None:
        self._active_dialogue_tree = None
        self._active_dialogue_node_id = None
        self._create_ui()

    def get_active_dialogue_node(self) -> Optional[DialogueNode]:
        """Expose the active node for tests + the renderer."""
        tree = self._active_dialogue_tree
        node_id = self._active_dialogue_node_id
        if tree is None or node_id is None:
            return None
        return tree.nodes.get(node_id)

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

        if self._active_dialogue_tree is None:
            self._create_dock_buttons()
        else:
            self._create_dialogue_continue_button()

    def _create_dock_buttons(self) -> None:
        """Place the named-NPC buttons in the dock."""
        entries = self._dock_entries()
        if not entries:
            return
        col_w = scale_x(220)
        gap = scale_x(20)
        total_w = col_w * len(entries) + gap * (len(entries) - 1)
        start_x = PANEL_X + (PANEL_W - total_w) // 2
        for idx, (speaker_id, name, title, _dialogue_id) in enumerate(entries):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    start_x + idx * (col_w + gap),
                    DOCK_TOP_Y + scale_y(20),
                    col_w,
                    scale_y(40),
                ),
                text=f"{name} · {title}",
                manager=self.ui_manager,
            )
            self._npc_buttons[speaker_id] = btn

    def _create_dialogue_continue_button(self) -> None:
        """Single Continue button while a venue dialogue is open."""
        self._dialogue_continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(160),
                DOCK_TOP_Y + scale_y(60),
                scale_x(140),
                scale_y(36),
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
        for btn in self._npc_buttons.values():
            btn.kill()
        self._npc_buttons.clear()

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
                self._request_back()
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

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._active_dialogue_tree is not None:
                self._close_active_dialogue()
                return
            self._request_back()

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
        """Render the memorial view."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))
        self._render_header(screen)
        if self._active_dialogue_tree is not None:
            self._render_dialogue_panel(screen)
        else:
            self._render_memorial_body(screen)
        if self.message:
            self._render_banner(screen, self.message, Colors.TEXT_SECONDARY)

    def render_top(self, screen: pygame.Surface) -> None:
        """Render the first-time tip overlay above pygame_gui chrome."""
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            self._tip_overlay.render(screen)

    def _render_header(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            (PANEL_X, PANEL_TOP_Y, PANEL_W, HEADER_H),
            alpha=220,
            border_color=ACCENT_COLOR,
        )
        pygame.draw.rect(screen, ACCENT_COLOR, (PANEL_X, PANEL_TOP_Y, PANEL_W, 3))
        title = self.title_font.render("THE DEEP SHAFTS", True, ACCENT_COLOR)
        screen.blit(title, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(14)))

        state = self._ensure_state()
        sub = self.subtitle_font.render(
            f"Section 3, Breakstone  ·  Visits: {state.visit_count}  "
            f"·  Standing tribute: {state.blessing_total}",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(sub, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(56)))

        if self._last_rep_grant > 0:
            tick = self.body_font.render(
                f"+{self._last_rep_grant} Miners' Union standing.",
                True,
                ACCENT_COLOR,
            )
            screen.blit(tick, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(82)))

    def _render_memorial_body(self, screen: pygame.Surface) -> None:
        """Render the vista panel + dock chrome."""
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=210)

        body_x = PANEL_X + scale_x(20)
        body_y = BODY_TOP_Y + scale_y(18)
        body_w = PANEL_W - scale_x(40)

        # Plaque (drawn from the existing locations.json flavor text).
        plaque_lines = word_wrap(
            "A bronze plaque marks where Sora Takahashi spoke. Miners still leave flowers.",
            self.body_font,
            body_w,
        )
        for line in plaque_lines:
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (body_x, body_y))
            body_y += self.body_font.get_linesize()

        body_y += scale_y(12)
        # Scripted-scene lines (first visit only, kept around for return
        # visits as a quiet vignette so the venue isn't empty on revisit).
        scene_lines = self._scripted_scene_lines or self._return_visit_lines()
        for line in scene_lines:
            wrapped = word_wrap(line, self.body_font, body_w)
            for w in wrapped:
                surf = self.body_font.render(w, True, Colors.TEXT_SECONDARY)
                screen.blit(surf, (body_x, body_y))
                body_y += self.body_font.get_linesize()
            body_y += scale_y(4)

        # Dock chrome
        draw_panel(screen, (PANEL_X, DOCK_TOP_Y, PANEL_W, DOCK_H), alpha=200)
        label = self.label_font.render(
            "At the memorial",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(label, (PANEL_X + scale_x(20), DOCK_TOP_Y + scale_y(8)))

    def _return_visit_lines(self) -> list[str]:
        """Quiet vignette shown on return visits (no scripted scene)."""
        lines = [
            "The lights are low. The flowers have been changed since you were last here.",
        ]
        if self._is_marcus_in_crew():
            lines.append("Marcus is somewhere behind you. He'll come over when he is ready.")
        return lines

    def _render_dialogue_panel(self, screen: pygame.Surface) -> None:
        """Render the active venue dialogue node."""
        node = self.get_active_dialogue_node()
        if node is None:
            return
        draw_panel(screen, (PANEL_X, BODY_TOP_Y, PANEL_W, BODY_H), alpha=220)
        speaker = self._name_for_speaker(node.speaker_id)
        header = self.subtitle_font.render(speaker, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (PANEL_X + scale_x(20), BODY_TOP_Y + scale_y(18)))
        body_x = PANEL_X + scale_x(20)
        body_y = BODY_TOP_Y + scale_y(54)
        body_w = PANEL_W - scale_x(40)
        for line in word_wrap(node.text, self.body_font, body_w):
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (body_x, body_y))
            body_y += self.body_font.get_linesize()

    def _render_banner(
        self, screen: pygame.Surface, text: str, color: tuple[int, int, int]
    ) -> None:
        surf = self.subtitle_font.render(text, True, color)
        bg = pygame.Surface((surf.get_width() + scale_x(40), surf.get_height() + scale_y(16)))
        bg.fill((10, 14, 24))
        bg.set_alpha(220)
        x = WINDOW_WIDTH // 2 - bg.get_width() // 2
        y = WINDOW_HEIGHT - scale_y(70)
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + scale_x(20), y + scale_y(8)))

    # ------------------------------------------------------------------
    # Helpers used by tests / Game wiring
    # ------------------------------------------------------------------

    def _request_back(self) -> None:
        """Navigate back to the station hub."""
        self.next_state = GameState.STATION_HUB

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition (for the engine router)."""
        return self.next_state
