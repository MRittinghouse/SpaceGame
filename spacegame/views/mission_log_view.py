"""
Mission log view.

Displays active, available, and completed missions with objectives
and rewards. Allows accepting available missions.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, scale_x, scale_y
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT
from spacegame.views.base_view import BaseView
from spacegame.models.mission import MissionManager, MissionStatus, Mission
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import FontCache, FONT_BODY, FONT_LG, FONT_MD, FONT_SECTION, FONT_XL, FONT_XS
from spacegame.utils.logger import logger

# Layout constants
PANEL_LEFT = scale_x(40)
PANEL_TOP = scale_y(90)
LIST_WIDTH = scale_x(360)
DETAIL_WIDTH = WINDOW_WIDTH - LIST_WIDTH - PANEL_LEFT * 2 - scale_x(30)
LIST_HEIGHT = WINDOW_HEIGHT - PANEL_TOP - scale_y(80) - scale_y(HUD_BASE_HEIGHT)
ITEM_HEIGHT = scale_y(44)
TAB_HEIGHT = scale_y(36)
TAB_WIDTH = scale_x(130)


class _TabButton:
    """Manually-rendered tab button."""

    def __init__(self, rect: pygame.Rect, label: str, font: pygame.font.Font) -> None:
        self.rect = rect
        self.label = label
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


_SIDE_BADGE_COLOR = (80, 140, 180)
_CAMPAIGN_BADGE_COLOR = (180, 140, 60)


class _MissionItem:
    """Clickable mission list entry."""

    def __init__(
        self,
        rect: pygame.Rect,
        mission: Mission,
        font: pygame.font.Font,
        badge_font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.mission = mission
        self.font = font
        self.badge_font = badge_font
        self.selected = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        if self.selected:
            bg = Colors.ROW_HIGHLIGHT
            text_color = Colors.TEXT_HIGHLIGHT
        elif self.hovered:
            bg = Colors.ROW_BG
            text_color = Colors.TEXT_PRIMARY
        else:
            bg = Colors.ROW_DETAIL
            text_color = Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg, self.rect, border_radius=3)
        text_surf = self.font.render(self.mission.name, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 14, self.rect.centery))
        screen.blit(text_surf, text_rect)

        # Type badge on the right
        if self.mission.mission_type == "side":
            badge_text = "SIDE"
            badge_color = _SIDE_BADGE_COLOR
        else:
            badge_text = "MAIN"
            badge_color = _CAMPAIGN_BADGE_COLOR
        badge_surf = self.badge_font.render(badge_text, True, badge_color)
        badge_rect = badge_surf.get_rect(
            midright=(self.rect.right - 10, self.rect.centery)
        )
        screen.blit(badge_surf, badge_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _AcceptButton:
    """Accept mission button shown in detail panel."""

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
        bg = (40, 80, 50) if self.hovered else (30, 60, 40)
        border = Colors.GREEN if self.hovered else (60, 100, 70)
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render("ACCEPT", True, Colors.GREEN)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class MissionLogView(BaseView):
    """Mission log showing active, available, and completed missions."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        mission_manager: Optional[MissionManager],
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.mission_manager = mission_manager
        self.next_state: Optional[GameState] = None

        # Tab state
        self._current_tab: str = "active"
        self._selected_mission_id: Optional[str] = None
        self.pending_accept_id: Optional[str] = None

        # Scroll
        self._scroll_offset: int = 0

        # Fonts
        self._title_font = FontCache.get(FONT_SECTION)
        self._tab_font = FontCache.get(FONT_BODY)
        self._name_font = FontCache.get(FONT_LG)
        self._desc_font = FontCache.get(FONT_MD)
        self._detail_title_font = FontCache.get(FONT_XL)
        self._label_font = FontCache.get(FONT_BODY)
        self._badge_font = FontCache.get(FONT_XS)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Tab buttons
        self._tabs: list[_TabButton] = []
        self._mission_items: list[_MissionItem] = []
        self._accept_btn: Optional[_AcceptButton] = None

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()
        self._build_tabs()
        self._refresh_list()
        logger.info("Entered mission log view")

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited mission log view")

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(PANEL_LEFT, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60), 120, 40),
            text="BACK",
            manager=self.ui_manager,
        )

        # Accept button in detail panel area
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        self._accept_btn = _AcceptButton(
            pygame.Rect(detail_x + 20, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 140, 140, 38),
            self._label_font,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
            self.back_button = None

    def _build_tabs(self) -> None:
        self._tabs.clear()
        tab_labels = [("active", "Active"), ("available", "Available"), ("completed", "Completed")]
        for i, (key, label) in enumerate(tab_labels):
            rect = pygame.Rect(
                PANEL_LEFT + i * (TAB_WIDTH + 8), PANEL_TOP - TAB_HEIGHT - 6, TAB_WIDTH, TAB_HEIGHT
            )
            tab = _TabButton(rect, label, self._tab_font)
            tab.active = key == self._current_tab
            self._tabs.append(tab)

    def _refresh_list(self) -> None:
        """Rebuild the mission item list for the current tab."""
        self._mission_items.clear()
        self._scroll_offset = 0

        if not self.mission_manager:
            return

        status_map = {
            "active": MissionStatus.ACTIVE,
            "available": MissionStatus.AVAILABLE,
            "completed": MissionStatus.COMPLETED,
        }
        status = status_map.get(self._current_tab, MissionStatus.ACTIVE)
        missions = self.mission_manager.get_missions_by_status(status)
        # Sort: campaign missions first, then side missions
        missions.sort(key=lambda m: (0 if m.mission_type == "campaign" else 1, m.name))

        for i, mission in enumerate(missions):
            rect = pygame.Rect(
                PANEL_LEFT + 4,
                PANEL_TOP + 4 + i * (ITEM_HEIGHT + 4),
                LIST_WIDTH - 8,
                ITEM_HEIGHT,
            )
            item = _MissionItem(rect, mission, self._name_font, self._badge_font)
            self._mission_items.append(item)

        # Auto-select first if available
        if self._mission_items:
            self._mission_items[0].selected = True
            self._selected_mission_id = self._mission_items[0].mission.id
        else:
            self._selected_mission_id = None

        # Show accept button only on available tab
        if self._accept_btn:
            self._accept_btn.visible = (
                self._current_tab == "available" and self._selected_mission_id is not None
            )

    def _select_mission(self, mission_id: str) -> None:
        self._selected_mission_id = mission_id
        for item in self._mission_items:
            item.selected = item.mission.id == mission_id
        if self._accept_btn:
            self._accept_btn.visible = (
                self._current_tab == "available" and self._selected_mission_id is not None
            )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP

        # Tab clicks
        for i, tab in enumerate(self._tabs):
            if tab.was_clicked(event):
                tab_keys = ["active", "available", "completed"]
                self._current_tab = tab_keys[i]
                for t in self._tabs:
                    t.active = False
                tab.active = True
                self._refresh_list()
                return

        # Mission item clicks
        for item in self._mission_items:
            if item.was_clicked(event):
                self._select_mission(item.mission.id)
                return

        # Accept button
        if self._accept_btn and self._accept_btn.was_clicked(event):
            if self._selected_mission_id:
                self.pending_accept_id = self._selected_mission_id
                self.next_state = GameState.GALAXY_MAP
                return

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y * 20)

    def update(self, dt: float) -> None:
        self.background.update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for tab in self._tabs:
            tab.update_hover(mouse_pos)
        for item in self._mission_items:
            item.update_hover(mouse_pos)
        if self._accept_btn:
            self._accept_btn.update_hover(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title_surf = self._title_font.render("MISSION LOG", True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (PANEL_LEFT, 30))

        # Tabs
        for tab in self._tabs:
            tab.render(screen)

        # List panel background
        list_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, LIST_HEIGHT)
        draw_panel(screen, list_rect, alpha=255)

        # Mission items (clipped to list panel)
        clip_prev = screen.get_clip()
        screen.set_clip(list_rect)
        for item in self._mission_items:
            # Apply scroll offset
            shifted_rect = item.rect.move(0, -self._scroll_offset)
            if shifted_rect.bottom < list_rect.top or shifted_rect.top > list_rect.bottom:
                continue
            orig_rect = item.rect
            item.rect = shifted_rect
            item.render(screen)
            item.rect = orig_rect
        screen.set_clip(clip_prev)

        # Detail panel
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        detail_rect = pygame.Rect(detail_x, PANEL_TOP, DETAIL_WIDTH, LIST_HEIGHT)
        draw_panel(screen, detail_rect, alpha=255)

        self._render_detail_panel(screen, detail_x, PANEL_TOP)

        # Accept button
        if self._accept_btn:
            self._accept_btn.render(screen)

    def _render_detail_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the selected mission's details."""
        if not self._selected_mission_id or not self.mission_manager:
            # Empty state
            no_sel = self._desc_font.render(
                "Select a mission to view details.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(no_sel, (x + 20, y + 30))
            return

        mission = self.mission_manager.get_mission(self._selected_mission_id)
        if not mission:
            return

        pad_x = x + 20
        cur_y = y + 18

        # Mission type label
        if mission.mission_type == "side":
            type_label = "SIDE MISSION"
            type_color = _SIDE_BADGE_COLOR
        else:
            type_label = "CAMPAIGN MISSION"
            type_color = _CAMPAIGN_BADGE_COLOR
        type_surf = self._badge_font.render(type_label, True, type_color)
        screen.blit(type_surf, (pad_x, cur_y))
        cur_y += 18

        # Mission name
        name_surf = self._detail_title_font.render(mission.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (pad_x, cur_y))
        cur_y += 34

        # Description (word-wrapped)
        cur_y = self._render_wrapped(
            screen,
            mission.description,
            self._desc_font,
            Colors.TEXT_SECONDARY,
            pad_x,
            cur_y,
            DETAIL_WIDTH - 40,
        )
        cur_y += 20

        # Objectives header
        obj_header = self._label_font.render("Objectives:", True, Colors.TEXT_PRIMARY)
        screen.blit(obj_header, (pad_x, cur_y))
        cur_y += 26

        # Objective checklist
        progress = self.mission_manager.get_objective_progress(self._selected_mission_id)
        for i, obj in enumerate(mission.objectives):
            completed = progress[i] if i < len(progress) else False
            check = "\u2611" if completed else "\u2610"
            color = Colors.GREEN if completed else Colors.TEXT_SECONDARY
            obj_text = f"{check} {obj.description}"
            obj_surf = self._desc_font.render(obj_text, True, color)
            screen.blit(obj_surf, (pad_x + 10, cur_y))
            cur_y += 22

        # Hint (actionable guidance)
        if mission.hint:
            cur_y += 12
            hint_header = self._label_font.render("Hint:", True, Colors.TEXT_PRIMARY)
            screen.blit(hint_header, (pad_x, cur_y))
            cur_y += 24
            cur_y = self._render_wrapped(
                screen,
                mission.hint,
                self._desc_font,
                (180, 200, 220),
                pad_x + 10,
                cur_y,
                DETAIL_WIDTH - 50,
            )

        cur_y += 16

        # Rewards header
        rew_header = self._label_font.render("Rewards:", True, Colors.TEXT_PRIMARY)
        screen.blit(rew_header, (pad_x, cur_y))
        cur_y += 26

        for reward in mission.rewards:
            if reward.reward_type == "credits":
                rew_text = f"+{reward.amount:,} Credits"
                color = Colors.YELLOW
            elif reward.reward_type == "xp":
                rew_text = f"+{reward.amount} XP"
                color = Colors.BLUE
            elif reward.reward_type == "modify_reputation":
                sign = "+" if reward.amount > 0 else ""
                rew_text = f"{sign}{reward.amount} {reward.target_id} rep"
                color = Colors.GREEN if reward.amount > 0 else Colors.RED
            elif reward.reward_type in ("set_flag", "remove_cargo", "deduct_credits"):
                continue  # Don't show internal flags or deductions in UI
            else:
                rew_text = f"+{reward.amount} {reward.reward_type}"
                color = Colors.TEXT_SECONDARY
            rew_surf = self._desc_font.render(rew_text, True, color)
            screen.blit(rew_surf, (pad_x + 10, cur_y))
            cur_y += 22

        # Prerequisites (if any and on available tab)
        if mission.prerequisites and self._current_tab == "available":
            cur_y += 12
            prereq_surf = self._desc_font.render(
                f"Requires: {', '.join(mission.prerequisites)}",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(prereq_surf, (pad_x, cur_y))

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
