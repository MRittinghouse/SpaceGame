"""
Crew roster view.

Displays recruited crew members with their stats, abilities, and loyalty.
Allows dismissing crew members from the roster.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.views.base_view import BaseView
from spacegame.models.crew import CrewRoster, CrewTemplate
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.utils.logger import logger

# Layout constants
PANEL_LEFT = 40
PANEL_TOP = 90
LIST_WIDTH = 360
DETAIL_WIDTH = WINDOW_WIDTH - LIST_WIDTH - PANEL_LEFT * 2 - 30
LIST_HEIGHT = WINDOW_HEIGHT - PANEL_TOP - 80
ITEM_HEIGHT = 44


class _CrewItem:
    """Clickable crew list entry showing name and level."""

    def __init__(
        self,
        rect: pygame.Rect,
        template: CrewTemplate,
        state: dict,
        font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.template = template
        self.state = state
        self.font = font
        self.selected = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        if self.selected:
            bg = (40, 55, 90)
            text_color = Colors.TEXT_HIGHLIGHT
        elif self.hovered:
            bg = (30, 40, 65)
            text_color = Colors.TEXT_PRIMARY
        else:
            bg = (22, 30, 50)
            text_color = Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg, self.rect, border_radius=3)

        # Crew name on left
        name_surf = self.font.render(self.template.name, True, text_color)
        name_rect = name_surf.get_rect(midleft=(self.rect.x + 14, self.rect.centery))
        screen.blit(name_surf, name_rect)

        # Level on right
        level = self.state.get("level", 1)
        level_surf = self.font.render(f"Lv {level}", True, Colors.TEXT_SECONDARY)
        level_rect = level_surf.get_rect(midright=(self.rect.right - 14, self.rect.centery))
        screen.blit(level_surf, level_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _DismissButton:
    """Dismiss crew button shown in detail panel."""

    def __init__(self, rect: pygame.Rect, font: pygame.font.Font) -> None:
        self.rect = rect
        self.font = font
        self.hovered = False
        self.visible = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if self.visible:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        bg = (80, 40, 40) if self.hovered else (60, 30, 30)
        border = Colors.RED if self.hovered else (100, 50, 50)
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render("DISMISS", True, Colors.RED)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class CrewRosterView(BaseView):
    """Crew roster showing recruited members with stats and abilities."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        crew_roster: Optional[CrewRoster],
        crew_slots: int,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.crew_roster = crew_roster
        self.crew_slots = crew_slots
        self.next_state: Optional[GameState] = None

        # Selection state
        self._selected_crew_id: Optional[str] = None
        self.pending_dismiss_id: Optional[str] = None

        # Scroll
        self._scroll_offset: int = 0

        # Fonts
        self._title_font = pygame.font.Font(None, 40)
        self._name_font = pygame.font.Font(None, 24)
        self._desc_font = pygame.font.Font(None, 20)
        self._detail_title_font = pygame.font.Font(None, 28)
        self._label_font = pygame.font.Font(None, 22)
        self._slot_font = pygame.font.Font(None, 24)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Manual widgets
        self._crew_items: list[_CrewItem] = []
        self._dismiss_btn: Optional[_DismissButton] = None

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=88)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()
        self._refresh_list()
        logger.info("Entered crew roster view")

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited crew roster view")

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(PANEL_LEFT, WINDOW_HEIGHT - 60, 120, 40),
            text="BACK",
            manager=self.ui_manager,
        )

        # Dismiss button in detail panel area
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        self._dismiss_btn = _DismissButton(
            pygame.Rect(detail_x + 20, WINDOW_HEIGHT - 140, 140, 38),
            self._label_font,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
            self.back_button = None

    def _refresh_list(self) -> None:
        """Rebuild the crew item list from the roster."""
        self._crew_items.clear()
        self._scroll_offset = 0

        if not self.crew_roster:
            self._selected_crew_id = None
            if self._dismiss_btn:
                self._dismiss_btn.visible = False
            return

        members = self.crew_roster.get_recruited_members()

        for i, (template, state) in enumerate(members):
            rect = pygame.Rect(
                PANEL_LEFT + 4,
                PANEL_TOP + 4 + i * (ITEM_HEIGHT + 4),
                LIST_WIDTH - 8,
                ITEM_HEIGHT,
            )
            item = _CrewItem(rect, template, state, self._name_font)
            self._crew_items.append(item)

        # Auto-select first if available
        if self._crew_items:
            self._crew_items[0].selected = True
            self._selected_crew_id = self._crew_items[0].template.id
        else:
            self._selected_crew_id = None

        # Show dismiss button when crew is selected
        if self._dismiss_btn:
            self._dismiss_btn.visible = self._selected_crew_id is not None

    def _select_crew(self, crew_id: str) -> None:
        """Select a crew member by template ID."""
        self._selected_crew_id = crew_id
        for item in self._crew_items:
            item.selected = item.template.id == crew_id
        if self._dismiss_btn:
            self._dismiss_btn.visible = self._selected_crew_id is not None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP

        # Crew item clicks
        for item in self._crew_items:
            if item.was_clicked(event):
                self._select_crew(item.template.id)
                return

        # Dismiss button
        if self._dismiss_btn and self._dismiss_btn.was_clicked(event):
            if self._selected_crew_id:
                self.pending_dismiss_id = self._selected_crew_id
                self.next_state = GameState.GALAXY_MAP
                return

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y * 20)

    def update(self, dt: float) -> None:
        self.background.update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for item in self._crew_items:
            item.update_hover(mouse_pos)
        if self._dismiss_btn:
            self._dismiss_btn.update_hover(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title_surf = self._title_font.render("CREW ROSTER", True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (PANEL_LEFT, 30))

        # Slot counter (top right area)
        recruited_count = len(self._crew_items)
        slot_text = f"Slots: {recruited_count}/{self.crew_slots}"
        slot_surf = self._slot_font.render(slot_text, True, Colors.TEXT_SECONDARY)
        slot_rect = slot_surf.get_rect(topright=(WINDOW_WIDTH - PANEL_LEFT, 34))
        screen.blit(slot_surf, slot_rect)

        # List panel background
        list_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, LIST_HEIGHT)
        pygame.draw.rect(screen, (15, 20, 35), list_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.UI_BORDER, list_rect, 1, border_radius=4)

        # Crew items (clipped to list panel)
        clip_prev = screen.get_clip()
        screen.set_clip(list_rect)
        if self._crew_items:
            for item in self._crew_items:
                # Apply scroll offset
                shifted_rect = item.rect.move(0, -self._scroll_offset)
                if shifted_rect.bottom < list_rect.top or shifted_rect.top > list_rect.bottom:
                    continue
                orig_rect = item.rect
                item.rect = shifted_rect
                item.render(screen)
                item.rect = orig_rect
        else:
            # Empty state inside the list panel
            empty_surf = self._desc_font.render(
                "No crew members recruited yet.", True, Colors.TEXT_SECONDARY
            )
            empty_rect = empty_surf.get_rect(center=(list_rect.centerx, list_rect.top + 40))
            screen.blit(empty_surf, empty_rect)
        screen.set_clip(clip_prev)

        # Detail panel
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        detail_rect = pygame.Rect(detail_x, PANEL_TOP, DETAIL_WIDTH, LIST_HEIGHT)
        pygame.draw.rect(screen, (15, 20, 35), detail_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.UI_BORDER, detail_rect, 1, border_radius=4)

        self._render_detail_panel(screen, detail_x, PANEL_TOP)

        # Dismiss button
        if self._dismiss_btn:
            self._dismiss_btn.render(screen)

    def _render_detail_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the selected crew member's details."""
        if not self._selected_crew_id or not self.crew_roster:
            # Empty state
            no_sel = self._desc_font.render(
                "Select a crew member to view details.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(no_sel, (x + 20, y + 30))
            return

        template = self.crew_roster.get_template(self._selected_crew_id)
        state = self.crew_roster.get_member_state(self._selected_crew_id)
        if not template or not state:
            return

        pad_x = x + 20
        cur_y = y + 18

        # Portrait: colored rectangle with first letter of name
        portrait_rect = pygame.Rect(pad_x, cur_y, 40, 40)
        portrait_color = (
            tuple(template.portrait_color) if template.portrait_color else (80, 80, 120)
        )
        pygame.draw.rect(screen, portrait_color, portrait_rect, border_radius=4)
        pygame.draw.rect(screen, Colors.UI_BORDER, portrait_rect, 1, border_radius=4)
        initial_surf = self._detail_title_font.render(
            template.name[0].upper(), True, Colors.TEXT_PRIMARY
        )
        initial_rect = initial_surf.get_rect(center=portrait_rect.center)
        screen.blit(initial_surf, initial_rect)

        # Name (to the right of portrait)
        name_surf = self._detail_title_font.render(template.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (pad_x + 54, cur_y + 2))

        # Role subtitle
        role_surf = self._label_font.render(template.role, True, Colors.TEXT_SECONDARY)
        screen.blit(role_surf, (pad_x + 54, cur_y + 24))
        cur_y += 56

        # Description (word-wrapped)
        cur_y = self._render_wrapped(
            screen,
            template.description,
            self._desc_font,
            Colors.TEXT_SECONDARY,
            pad_x,
            cur_y,
            DETAIL_WIDTH - 40,
        )
        cur_y += 20

        # Level and XP
        level = state.get("level", 1)
        xp = state.get("xp", 0)
        if level < template.max_level and level < len(template.xp_thresholds):
            xp_threshold = template.xp_thresholds[level]
            xp_text = f"Level: {level}  XP: {xp}/{xp_threshold}"
        else:
            xp_text = f"Level: {level}  XP: MAX"
        xp_surf = self._label_font.render(xp_text, True, Colors.TEXT_PRIMARY)
        screen.blit(xp_surf, (pad_x, cur_y))
        cur_y += 28

        # Loyalty bar
        loyalty = state.get("loyalty", 50)
        loyalty_label = self._label_font.render(f"Loyalty:", True, Colors.TEXT_PRIMARY)
        screen.blit(loyalty_label, (pad_x, cur_y))

        # Bar dimensions
        bar_x = pad_x + 70
        bar_width = 160
        bar_height = 14
        bar_y = cur_y + 3

        # Bar background
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (30, 30, 45), bar_bg_rect, border_radius=3)

        # Bar fill
        fill_width = int(bar_width * (loyalty / 100.0))
        if loyalty >= 70:
            bar_color = Colors.GREEN
        elif loyalty >= 40:
            bar_color = Colors.YELLOW
        else:
            bar_color = Colors.RED
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height)
            pygame.draw.rect(screen, bar_color, fill_rect, border_radius=3)

        pygame.draw.rect(screen, Colors.UI_BORDER, bar_bg_rect, 1, border_radius=3)

        # Loyalty value
        loyalty_val_surf = self._desc_font.render(str(loyalty), True, Colors.TEXT_SECONDARY)
        screen.blit(loyalty_val_surf, (bar_x + bar_width + 8, cur_y + 2))
        cur_y += 32

        # Abilities section
        abilities_header = self._label_font.render("Abilities:", True, Colors.TEXT_PRIMARY)
        screen.blit(abilities_header, (pad_x, cur_y))
        cur_y += 26

        for ability in template.abilities:
            if ability.unlock_level <= level:
                # Unlocked
                bonus_sign = "+" if ability.bonus_value >= 0 else ""
                bonus_display = ability.bonus_value
                if bonus_display == int(bonus_display):
                    bonus_display = int(bonus_display)
                ability_text = f"\u2713 {ability.description} ({bonus_sign}{bonus_display})"
                color = Colors.GREEN
            else:
                # Locked
                ability_text = f"\U0001f512 {ability.description} (Lv {ability.unlock_level})"
                color = Colors.TEXT_SECONDARY
            ability_surf = self._desc_font.render(ability_text, True, color)
            screen.blit(ability_surf, (pad_x + 10, cur_y))
            cur_y += 22

    def _render_wrapped(
        self,
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
    ) -> int:
        """Render word-wrapped text, return y position after last line."""
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, y))
            y += font.get_linesize()
        return y

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
