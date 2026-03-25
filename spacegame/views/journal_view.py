"""
Journal view.

Displays auto-generated story entries and player-written notes
with tag-based filtering, creation, editing, and deletion.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_MD, FONT_SECTION, FONT_SM, get_font
from spacegame.models.journal import PLAYER_ENTRY_MAX_LENGTH, Journal, JournalEntry
from spacegame.models.mission import MissionManager
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

# Layout constants (PANEL_LEFT/TOP shared with mission_log_view, crew_roster_view)
PANEL_LEFT = scale_x(40)
PANEL_TOP = scale_y(90)
LIST_WIDTH = WINDOW_WIDTH - PANEL_LEFT * 2  # Full width (no detail panel, unlike mission_log)
LIST_HEIGHT = WINDOW_HEIGHT - PANEL_TOP - scale_y(80) - scale_y(HUD_BASE_HEIGHT)
ENTRY_CARD_HEIGHT = scale_y(80)
ENTRY_CARD_GAP = 6
TAB_HEIGHT = scale_y(32)
TAB_WIDTH = scale_x(110)
HINT_CARD_HEIGHT = scale_y(56)

# Tag filter labels
TAG_FILTERS = [
    ("all", "All"),
    ("people", "People"),
    ("places", "Places"),
    ("suspicions", "Suspicions"),
    ("goals", "Goals"),
]


class _TabButton:
    """Manually-rendered filter tab."""

    def __init__(self, rect: pygame.Rect, label: str, key: str, font: pygame.font.Font) -> None:
        self.rect = rect
        self.label = label
        self.key = key
        self.font = font
        self.active = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        if self.active:
            bg = Colors.ROW_HIGHLIGHT
            border = Colors.TEXT_HIGHLIGHT
            text_color = Colors.TEXT_HIGHLIGHT
        elif self.hovered:
            bg = Colors.ROW_BG
            border = Colors.UI_BORDER
            text_color = Colors.TEXT_PRIMARY
        else:
            bg = Colors.CARD_BG
            border = Colors.UI_BORDER
            text_color = Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render(self.label, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _EntryItem:
    """Clickable journal entry card in the list."""

    def __init__(
        self,
        rect: pygame.Rect,
        entry: JournalEntry,
        header_font: pygame.font.Font,
        body_font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.entry = entry
        self.header_font = header_font
        self.body_font = body_font
        self.selected = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        # Background color by source type
        if self.selected:
            bg = Colors.ROW_HIGHLIGHT
        elif self.hovered:
            bg = Colors.ROW_BG
        elif self.entry.source == "auto":
            bg = (18, 24, 42)
        else:
            bg = (24, 30, 48)

        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        if self.selected:
            pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, self.rect, 1, border_radius=4)

        pad_x = self.rect.x + 12
        cur_y = self.rect.y + 6

        # Header line: "Day X — System — [tag/source]"
        header_parts = [f"Day {self.entry.game_day}"]
        if self.entry.system_id:
            system_display = self.entry.system_id.replace("_", " ").title()
            header_parts.append(system_display)
        header = " \u2014 ".join(header_parts)
        header_surf = self.header_font.render(header, True, Colors.TEXT_SECONDARY)
        screen.blit(header_surf, (pad_x, cur_y))

        # Source/tag badge on the right
        badge_text = ""
        badge_color = Colors.TEXT_SECONDARY
        if self.entry.source == "auto":
            badge_text = "[auto]"
            badge_color = (100, 120, 160)
        elif self.entry.tag:
            badge_text = f"[{self.entry.tag}]"
            badge_color = Colors.TEXT_HIGHLIGHT
        if badge_text:
            badge_surf = self.header_font.render(badge_text, True, badge_color)
            badge_x = self.rect.right - badge_surf.get_width() - 12
            screen.blit(badge_surf, (badge_x, cur_y))

        cur_y += 20

        # Body text (truncated to fit)
        max_text_width = self.rect.width - 24
        display_text = self.entry.text
        # Truncate to ~2 lines
        if self.body_font.size(display_text)[0] > max_text_width * 2:
            while (
                self.body_font.size(display_text + "...")[0] > max_text_width * 2
                and len(display_text) > 0
            ):
                display_text = display_text[:-1]
            display_text += "..."

        # Word-wrap into at most 2 lines
        words = display_text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if self.body_font.size(test)[0] <= max_text_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines[:2]:
            text_color = (
                Colors.TEXT_PRIMARY if self.entry.source == "player" else Colors.TEXT_SECONDARY
            )
            line_surf = self.body_font.render(line, True, text_color)
            screen.blit(line_surf, (pad_x, cur_y))
            cur_y += self.body_font.get_linesize()

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _ActionButton:
    """Small action button (New, Edit, Delete)."""

    def __init__(
        self, rect: pygame.Rect, label: str, font: pygame.font.Font, color: tuple[int, int, int]
    ) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.color = color
        self.hovered = False
        self.visible = True

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if self.visible:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        bg = (40, 50, 70) if self.hovered else (25, 32, 52)
        border = self.color if self.hovered else Colors.UI_BORDER
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render(self.label, True, self.color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class JournalView(BaseView):
    """Journal view showing auto entries and player notes with filtering."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        journal: Optional[Journal],
        game_day: int = 1,
        system_id: str = "",
        mission_manager: Optional[MissionManager] = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.journal = journal or Journal()
        self.game_day = game_day
        self.system_id = system_id
        self.mission_manager = mission_manager
        self.next_state: Optional[GameState] = None

        # Filter state
        self._current_filter: str = "all"
        self._selected_entry_id: Optional[str] = None

        # Scroll
        self._scroll_offset: int = 0

        # Compose/edit state
        self._composing: bool = False
        self._editing: bool = False
        self._editing_entry_id: Optional[str] = None
        self._compose_text: str = ""
        self._compose_tag: str = ""

        # Fonts
        self._title_font = get_font("header", FONT_SECTION)
        self._tab_font = get_font("label", FONT_BODY)
        self._header_font = get_font("dialogue", FONT_MD)
        self._body_font = get_font("narration", FONT_MD)
        self._detail_font = get_font("narration", FONT_BODY)
        self._label_font = get_font("dialogue", FONT_LG)
        self._small_font = get_font("dialogue", FONT_SM)

        # UI elements
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self._text_entry: Optional[pygame_gui.elements.UITextEntryLine] = None

        # Custom-rendered widgets
        self._tabs: list[_TabButton] = []
        self._entry_items: list[_EntryItem] = []
        self._new_btn: Optional[_ActionButton] = None
        self._edit_btn: Optional[_ActionButton] = None
        self._delete_btn: Optional[_ActionButton] = None
        self._confirm_btn: Optional[_ActionButton] = None
        self._cancel_btn: Optional[_ActionButton] = None
        self._tag_buttons: list[_ActionButton] = []

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=88)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()
        self._build_tabs()
        self._build_action_buttons()
        self._refresh_list()
        logger.info("Entered journal view")

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited journal view")

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_LEFT, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60), 120, 40
            ),
            text="BACK",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
            self.back_button = None
        if self._text_entry:
            self._text_entry.kill()
            self._text_entry = None

    def _build_tabs(self) -> None:
        self._tabs.clear()
        for i, (key, label) in enumerate(TAG_FILTERS):
            rect = pygame.Rect(
                PANEL_LEFT + i * (TAB_WIDTH + 6),
                PANEL_TOP - TAB_HEIGHT - 6,
                TAB_WIDTH,
                TAB_HEIGHT,
            )
            tab = _TabButton(rect, label, key, self._tab_font)
            tab.active = key == self._current_filter
            self._tabs.append(tab)

    def _build_action_buttons(self) -> None:
        # Right-aligned action buttons
        btn_y = PANEL_TOP - TAB_HEIGHT - 6
        btn_w = scale_x(100)
        btn_h = TAB_HEIGHT

        self._new_btn = _ActionButton(
            pygame.Rect(WINDOW_WIDTH - PANEL_LEFT - btn_w, btn_y, btn_w, btn_h),
            "NEW (N)",
            self._tab_font,
            Colors.GREEN,
        )
        self._edit_btn = _ActionButton(
            pygame.Rect(WINDOW_WIDTH - PANEL_LEFT - btn_w * 2 - 8, btn_y, btn_w, btn_h),
            "EDIT",
            self._tab_font,
            Colors.TEXT_HIGHLIGHT,
        )
        self._edit_btn.visible = False
        self._delete_btn = _ActionButton(
            pygame.Rect(WINDOW_WIDTH - PANEL_LEFT - btn_w * 3 - 16, btn_y, btn_w, btn_h),
            "DELETE",
            self._tab_font,
            Colors.RED,
        )
        self._delete_btn.visible = False

        # Compose mode buttons (below text entry area)
        compose_y = PANEL_TOP + 60
        self._confirm_btn = _ActionButton(
            pygame.Rect(WINDOW_WIDTH - PANEL_LEFT - btn_w, compose_y + 40, btn_w, btn_h),
            "SAVE",
            self._tab_font,
            Colors.GREEN,
        )
        self._confirm_btn.visible = False
        self._cancel_btn = _ActionButton(
            pygame.Rect(WINDOW_WIDTH - PANEL_LEFT - btn_w * 2 - 8, compose_y + 40, btn_w, btn_h),
            "CANCEL",
            self._tab_font,
            Colors.RED,
        )
        self._cancel_btn.visible = False

        # Tag selection buttons for compose mode
        self._tag_buttons.clear()
        tag_labels = [
            ("", "None"),
            ("people", "People"),
            ("places", "Places"),
            ("suspicions", "Suspicions"),
            ("goals", "Goals"),
        ]
        tag_btn_w = scale_x(90)
        for i, (_tag_key, tag_label) in enumerate(tag_labels):
            rect = pygame.Rect(
                PANEL_LEFT + i * (tag_btn_w + 4),
                compose_y + 40,
                tag_btn_w,
                btn_h,
            )
            btn = _ActionButton(rect, tag_label, self._tab_font, Colors.TEXT_HIGHLIGHT)
            btn.visible = False
            self._tag_buttons.append(btn)

    def _refresh_list(self) -> None:
        """Rebuild entry item list for current filter."""
        self._entry_items.clear()
        self._scroll_offset = 0

        if self._current_filter == "all":
            entries = self.journal.get_entries()
        else:
            # Tag filter: only player entries with matching tag
            entries = self.journal.get_entries(tag_filter=self._current_filter)

        for i, entry in enumerate(entries):
            rect = pygame.Rect(
                PANEL_LEFT + 4,
                PANEL_TOP + 4 + i * (ENTRY_CARD_HEIGHT + ENTRY_CARD_GAP),
                LIST_WIDTH - 8,
                ENTRY_CARD_HEIGHT,
            )
            item = _EntryItem(rect, entry, self._header_font, self._body_font)
            self._entry_items.append(item)

        # Auto-select first
        if self._entry_items:
            self._entry_items[0].selected = True
            self._selected_entry_id = self._entry_items[0].entry.entry_id
        else:
            self._selected_entry_id = None

        self._update_action_visibility()

    def _switch_filter(self, filter_key: str) -> None:
        """Switch the active filter tab."""
        self._current_filter = filter_key
        for tab in self._tabs:
            tab.active = tab.key == filter_key
        self._refresh_list()

    def _select_entry(self, entry_id: str) -> None:
        """Select an entry by ID."""
        self._selected_entry_id = entry_id
        for item in self._entry_items:
            item.selected = item.entry.entry_id == entry_id
        self._update_action_visibility()

    def _update_action_visibility(self) -> None:
        """Show edit/delete only for selected player entries."""
        selected_entry = self._get_selected_entry()
        is_player = selected_entry is not None and selected_entry.source == "player"
        if self._edit_btn:
            self._edit_btn.visible = is_player and not self._composing
        if self._delete_btn:
            self._delete_btn.visible = is_player and not self._composing
        if self._new_btn:
            self._new_btn.visible = not self._composing

    def _get_selected_entry(self) -> Optional[JournalEntry]:
        """Get the currently selected entry."""
        if not self._selected_entry_id:
            return None
        return self.journal._find_entry(self._selected_entry_id)

    # === COMPOSE / EDIT ===

    def _start_compose(self) -> None:
        """Enter compose mode for a new entry."""
        self._composing = True
        self._editing = False
        self._editing_entry_id = None
        self._compose_text = ""
        self._compose_tag = ""
        self._show_compose_ui()

    def _start_edit(self) -> None:
        """Enter edit mode for the selected player entry."""
        entry = self._get_selected_entry()
        if not entry or entry.source != "player":
            return
        self._composing = True
        self._editing = True
        self._editing_entry_id = entry.entry_id
        self._compose_text = entry.text
        self._compose_tag = entry.tag
        self._show_compose_ui()

    def _show_compose_ui(self) -> None:
        """Show text input and tag buttons for compose/edit."""
        if self._text_entry:
            self._text_entry.kill()
        self._text_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(PANEL_LEFT, PANEL_TOP + 10, LIST_WIDTH, 36),
            manager=self.ui_manager,
        )
        self._text_entry.set_text_length_limit(PLAYER_ENTRY_MAX_LENGTH)
        if self._compose_text:
            self._text_entry.set_text(self._compose_text)

        if self._confirm_btn:
            self._confirm_btn.visible = True
        if self._cancel_btn:
            self._cancel_btn.visible = True
        for btn in self._tag_buttons:
            btn.visible = True
        self._update_action_visibility()

    def _hide_compose_ui(self) -> None:
        """Hide compose/edit UI elements."""
        if self._text_entry:
            self._text_entry.kill()
            self._text_entry = None
        if self._confirm_btn:
            self._confirm_btn.visible = False
        if self._cancel_btn:
            self._cancel_btn.visible = False
        for btn in self._tag_buttons:
            btn.visible = False

    def _confirm_compose(self) -> None:
        """Save the composed/edited entry."""
        if self._text_entry:
            self._compose_text = self._text_entry.get_text()

        if not self._compose_text.strip():
            self._cancel_compose()
            return

        if self._editing and self._editing_entry_id:
            self.journal.edit_player_entry(
                self._editing_entry_id,
                text=self._compose_text,
                tag=self._compose_tag,
            )
        else:
            self.journal.add_player_entry(
                text=self._compose_text,
                game_day=self.game_day,
                system_id=self.system_id,
                tag=self._compose_tag,
            )

        self._composing = False
        self._editing = False
        self._editing_entry_id = None
        self._compose_text = ""
        self._compose_tag = ""
        self._hide_compose_ui()
        self._refresh_list()

    def _cancel_compose(self) -> None:
        """Cancel compose/edit without saving."""
        self._composing = False
        self._editing = False
        self._editing_entry_id = None
        self._compose_text = ""
        self._compose_tag = ""
        self._hide_compose_ui()
        self._update_action_visibility()

    def _delete_selected(self) -> None:
        """Delete the selected player entry."""
        entry = self._get_selected_entry()
        if not entry or entry.source != "player":
            return
        self.journal.delete_player_entry(entry.entry_id)
        self._refresh_list()

    # === EVENT HANDLING ===

    def handle_event(self, event: pygame.event.Event) -> None:
        # Button press
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self._composing:
                    self._cancel_compose()
                else:
                    self.next_state = GameState.GALAXY_MAP

        # Keyboard
        if event.type == pygame.KEYDOWN:
            if self._composing:
                if event.key == pygame.K_ESCAPE:
                    self._cancel_compose()
                    return
                if event.key == pygame.K_RETURN:
                    self._confirm_compose()
                    return
            else:
                if event.key == pygame.K_ESCAPE:
                    self.next_state = GameState.GALAXY_MAP
                    return
                if event.key == pygame.K_n:
                    self._start_compose()
                    return
                if event.key == pygame.K_TAB:
                    self._cycle_filter()
                    return

        # Tab clicks
        if not self._composing:
            for tab in self._tabs:
                if tab.was_clicked(event):
                    self._switch_filter(tab.key)
                    return

        # Entry item clicks
        if not self._composing:
            for item in self._entry_items:
                if item.was_clicked(event):
                    self._select_entry(item.entry.entry_id)
                    return

        # Action button clicks
        if self._new_btn and self._new_btn.was_clicked(event):
            self._start_compose()
            return
        if self._edit_btn and self._edit_btn.was_clicked(event):
            self._start_edit()
            return
        if self._delete_btn and self._delete_btn.was_clicked(event):
            self._delete_selected()
            return
        if self._confirm_btn and self._confirm_btn.was_clicked(event):
            self._confirm_compose()
            return
        if self._cancel_btn and self._cancel_btn.was_clicked(event):
            self._cancel_compose()
            return

        # Tag selection during compose
        if self._composing:
            tag_keys = ["", "people", "places", "suspicions", "goals"]
            for i, btn in enumerate(self._tag_buttons):
                if btn.was_clicked(event):
                    self._compose_tag = tag_keys[i]
                    return

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y * 30)

    def _cycle_filter(self) -> None:
        """Cycle to the next filter tab."""
        keys = [k for k, _ in TAG_FILTERS]
        idx = keys.index(self._current_filter)
        next_idx = (idx + 1) % len(keys)
        self._switch_filter(keys[next_idx])

    # === UPDATE ===

    def update(self, dt: float) -> None:
        self.background.update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for tab in self._tabs:
            tab.update_hover(mouse_pos)
        for item in self._entry_items:
            item.update_hover(mouse_pos)
        if self._new_btn:
            self._new_btn.update_hover(mouse_pos)
        if self._edit_btn:
            self._edit_btn.update_hover(mouse_pos)
        if self._delete_btn:
            self._delete_btn.update_hover(mouse_pos)
        if self._confirm_btn:
            self._confirm_btn.update_hover(mouse_pos)
        if self._cancel_btn:
            self._cancel_btn.update_hover(mouse_pos)
        for btn in self._tag_buttons:
            btn.update_hover(mouse_pos)

    # === RENDER ===

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title_surf = self._title_font.render("JOURNAL", True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (PANEL_LEFT, 30))

        # Entry count
        count_text = f"{self.journal.get_entry_count()} entries"
        count_surf = self._small_font.render(count_text, True, Colors.TEXT_SECONDARY)
        screen.blit(count_surf, (PANEL_LEFT + title_surf.get_width() + 16, 40))

        # Tabs
        if not self._composing:
            for tab in self._tabs:
                tab.render(screen)

        # Action buttons
        if self._new_btn:
            self._new_btn.render(screen)
        if self._edit_btn:
            self._edit_btn.render(screen)
        if self._delete_btn:
            self._delete_btn.render(screen)

        if self._composing:
            self._render_compose_panel(screen)
        else:
            self._render_entry_list(screen)

    def _get_hint_offset(self) -> int:
        """Return vertical offset for the entry list when a hint card is shown."""
        if self.mission_manager:
            hint = self.mission_manager.get_current_hint()
            if hint:
                return HINT_CARD_HEIGHT + ENTRY_CARD_GAP
        return 0

    def _render_hint_card(self, screen: pygame.Surface) -> None:
        """Render the 'What To Do Next' hint card above the entry list."""
        if not self.mission_manager:
            return
        hint = self.mission_manager.get_current_hint()
        if not hint:
            return
        mission_name, hint_text = hint
        card_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, HINT_CARD_HEIGHT)
        pygame.draw.rect(screen, (20, 30, 50), card_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, card_rect, 1, border_radius=4)

        pad_x = card_rect.x + 12
        max_text_w = card_rect.width - 24

        # Header — truncate if needed
        header = f"WHAT TO DO NEXT \u2014 {mission_name}"
        header_surf = self._header_font.render(header, True, Colors.TEXT_HIGHLIGHT)
        if header_surf.get_width() > max_text_w:
            header = f"NEXT \u2014 {mission_name}"
            header_surf = self._header_font.render(header, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header_surf, (pad_x, card_rect.y + 6))

        # Hint text — truncate with ellipsis if needed
        display_hint = hint_text
        hint_surf = self._body_font.render(display_hint, True, Colors.TEXT_PRIMARY)
        if hint_surf.get_width() > max_text_w:
            while len(display_hint) > 3 and hint_surf.get_width() > max_text_w:
                display_hint = display_hint[:-1]
            display_hint = display_hint.rstrip() + ".."
            hint_surf = self._body_font.render(display_hint, True, Colors.TEXT_PRIMARY)
        screen.blit(hint_surf, (pad_x, card_rect.y + 28))

    def _render_entry_list(self, screen: pygame.Surface) -> None:
        """Render the scrollable list of entry cards."""
        hint_offset = self._get_hint_offset()
        if hint_offset > 0:
            self._render_hint_card(screen)
        list_rect = pygame.Rect(
            PANEL_LEFT, PANEL_TOP + hint_offset, LIST_WIDTH, LIST_HEIGHT - hint_offset
        )
        pygame.draw.rect(screen, Colors.PANEL_BG, list_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.UI_BORDER, list_rect, 1, border_radius=4)

        if not self._entry_items:
            empty_text = (
                "No entries yet."
                if self._current_filter == "all"
                else f'No entries tagged "{self._current_filter}".'
            )
            empty_surf = self._body_font.render(empty_text, True, Colors.TEXT_SECONDARY)
            screen.blit(empty_surf, (list_rect.x + 20, list_rect.y + 30))
            return

        # Clip to list area
        clip_prev = screen.get_clip()
        screen.set_clip(list_rect)
        for item in self._entry_items:
            shifted_rect = item.rect.move(0, -self._scroll_offset)
            if shifted_rect.bottom < list_rect.top or shifted_rect.top > list_rect.bottom:
                continue
            orig_rect = item.rect
            item.rect = shifted_rect
            item.render(screen)
            item.rect = orig_rect
        screen.set_clip(clip_prev)

    def _render_compose_panel(self, screen: pygame.Surface) -> None:
        """Render the compose/edit area."""
        panel_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, 100)
        pygame.draw.rect(screen, Colors.PANEL_BG, panel_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel_rect, 1, border_radius=4)

        # Label
        mode_label = "EDIT ENTRY" if self._editing else "NEW ENTRY"
        label_surf = self._label_font.render(mode_label, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(label_surf, (PANEL_LEFT + 12, PANEL_TOP - 22))

        # Tag label
        tag_label = f"Tag: {self._compose_tag if self._compose_tag else 'None'}"
        tag_surf = self._small_font.render(tag_label, True, Colors.TEXT_SECONDARY)
        screen.blit(tag_surf, (PANEL_LEFT + 12, PANEL_TOP + 52))

        # Tag buttons
        for i, btn in enumerate(self._tag_buttons):
            # Highlight active tag
            tag_keys = ["", "people", "places", "suspicions", "goals"]
            if tag_keys[i] == self._compose_tag:
                btn.color = Colors.GREEN
            else:
                btn.color = Colors.TEXT_HIGHLIGHT
            btn.render(screen)

        # Confirm/Cancel
        if self._confirm_btn:
            self._confirm_btn.render(screen)
        if self._cancel_btn:
            self._cancel_btn.render(screen)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
